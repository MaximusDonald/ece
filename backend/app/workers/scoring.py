from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker
from uuid import UUID
from datetime import datetime

from app.core.config import get_settings
from app.core.utils import ensure_uuid
from app.models.legal import RiskFinding, ReportVersion, RiskLevel, ConfidenceLevel
from app.models.admin import ScoringRule
from app.workers.celery_app import celery_app
from app.workers.async_runner import run_async_task
from app.workers.task_dispatch import enqueue_document_task
from app.workers.pipeline_tracker import complete_step, fail_step, get_document_for_report, start_step

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def run_scoring(report_version_id: UUID) -> None:
    """Apply deterministic scoring rules to findings."""
    document_id = get_document_for_report(report_version_id)
    if document_id:
        start_step(document_id, 4, "Calcul du score de risque et de la confiance")
    async with SyncSession() as session:
        result = await session.execute(
            select(ReportVersion)
            .options(selectinload(ReportVersion.project))
            .where(ReportVersion.id == report_version_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise RuntimeError("Rapport introuvable pour le calcul du score")
        
        findings = await session.execute(
            select(RiskFinding).where(RiskFinding.report_version_id == report_version_id)
        )
        findings = findings.scalars().all()
        
        # Get applicable scoring rule and calculate calibrated score
        from app.services.compliance_auditor import compute_initial_severity_and_score, resolve_applicable_scoring_rule
        from app.models.corpus import LegalArticle

        article_ids = set()
        for f in findings:
            for uid_str in (f.matched_articles or []):
                try:
                    article_ids.add(UUID(str(uid_str)))
                except Exception:
                    pass

        articles_map = {}
        if article_ids:
            arts_res = await session.execute(select(LegalArticle).where(LegalArticle.id.in_(article_ids)))
            articles_map = {a.id: a for a in arts_res.scalars().all()}

        applicable_rule = await resolve_applicable_scoring_rule(
            session,
            country_code=report.project.country_code if report.project else None,
            sector=report.project.sector if report.project else None,
            treatments=report.project.treatments if report.project else None,
        )

        findings_dicts = [
            {
                "risk_level": f.risk_level,
                "confidence": f.confidence,
                "matched_articles": f.matched_articles or [],
            }
            for f in findings
        ]

        severity_counts, global_score, global_confidence = compute_initial_severity_and_score(
            findings_dicts,
            rule=applicable_rule,
            articles_map=articles_map,
        )

        # Update report
        report.global_score = global_score
        report.confidence_global = global_confidence
        report.severity_counts = severity_counts
        await session.commit()
        
        # Chain to report generation
        if document_id:
            complete_step(document_id, 4, "Score global et niveaux de confiance calcules")
            start_step(document_id, 5, "Preparation des rapports et fichiers PDF")
        from app.workers.report import report_generation_task
        try:
            enqueue_document_task(report_generation_task, report_version_id, "report")
        except Exception as exc:
            print(f"Unable to queue report generation for {report_version_id}: {exc}")
            if document_id:
                fail_step(document_id, 5)


@celery_app.task(bind=True, max_retries=2)
def scoring_task(self, report_version_id):
    """Celery task for scoring."""
    try:
        run_async_task(run_scoring(ensure_uuid(report_version_id)), async_engine)
    except Exception as exc:
        document_id = get_document_for_report(str(report_version_id))
        if document_id:
            fail_step(str(document_id), 4, retrying=self.request.retries < self.max_retries)
        self.retry(exc=exc, countdown=60)


