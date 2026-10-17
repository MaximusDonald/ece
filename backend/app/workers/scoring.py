from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker
from uuid import UUID
from datetime import datetime

from app.core.config import get_settings
from app.models.legal import RiskFinding, ReportVersion, RiskLevel, ConfidenceLevel
from app.models.admin import ScoringRule
from app.workers.celery_app import celery_app
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
        
        # Get applicable scoring rules
        rules = await session.execute(
            select(ScoringRule).where(
                ScoringRule.is_active == True
            ).order_by(ScoringRule.country_code.is_(None).desc())  # Global first, then country-specific
        )
        rules = rules.scalars().all()
        
        # Apply rules to adjust confidence and risk levels
        for finding in findings:
            applicable_rules = [
                r for r in rules
                if (r.country_code is None or r.country_code == report.project.country_code)
                and (r.domain in ["global"] or any(d in r.domain for d in report.project.treatments))
            ]
            
            if applicable_rules:
                rule = applicable_rules[0]  # Most specific rule
                
                # Adjust confidence based on thresholds
                if finding.confidence == ConfidenceLevel.HIGH:
                    # High confidence findings keep their level
                    pass
                elif finding.confidence == ConfidenceLevel.MEDIUM:
                    if rule.confidence_threshold_high > 0.7:
                        pass  # Keep medium
                elif finding.confidence == ConfidenceLevel.LOW:
                    # Low confidence findings downgraded
                    if finding.risk_level in [RiskLevel.ELEVE, RiskLevel.CRITIQUE]:
                        # Downgrade high-severity low-confidence findings
                        if finding.risk_level == RiskLevel.CRITIQUE:
                            finding.risk_level = RiskLevel.ELEVE
                        elif finding.risk_level == RiskLevel.ELEVE:
                            finding.risk_level = RiskLevel.MODERE
        
        # Recalculate global score
        severity_counts = {"critique": 0, "eleve": 0, "modere": 0, "a_surveiller": 0, "conforme": 0}
        for f in findings:
            severity_counts[f.risk_level.value] = severity_counts.get(f.risk_level.value, 0) + 1
        
        weights = {"critique": 25, "eleve": 15, "modere": 10, "a_surveiller": 5, "conforme": 0}
        raw_score = sum(weights.get(level, 0) * count for level, count in severity_counts.items())
        global_score = min(100, raw_score)
        
        # Determine global confidence
        high_conf_count = sum(1 for f in findings if f.confidence == ConfidenceLevel.HIGH)
        total_findings = len(findings)
        if total_findings > 0 and high_conf_count / total_findings > 0.6:
            global_confidence = ConfidenceLevel.HIGH
        elif total_findings > 0 and high_conf_count / total_findings > 0.3:
            global_confidence = ConfidenceLevel.MEDIUM
        else:
            global_confidence = ConfidenceLevel.LOW
        
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
def scoring_task(self, report_version_id: str):
    """Celery task for scoring."""
    try:
        asyncio.run(run_scoring(UUID(report_version_id)))
    except Exception as exc:
        document_id = get_document_for_report(report_version_id)
        if document_id:
            fail_step(document_id, 4, retrying=self.request.retries < self.max_retries)
        self.retry(exc=exc, countdown=60)


import asyncio
