"""Celery worker step 3: Holistic multi-document compliance audit backed by Article-RAG."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker
from sqlmodel import select

from app.core.config import get_settings
from app.core.utils import ensure_uuid
from app.models.document import Document, DocumentExtraction
from app.models.legal import ReportVersion
from app.services.compliance_auditor import (
    get_project_analysis_readiness,
    persist_audit_report_version,
    run_holistic_compliance_audit,
)
from app.workers.async_runner import run_async_task
from app.workers.celery_app import celery_app
from app.workers.pipeline_tracker import bind_report_documents, complete_step, fail_step, start_step
from app.workers.task_dispatch import enqueue_document_task

logger = logging.getLogger(__name__)
settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def _next_project_version(latest: Optional[ReportVersion]) -> tuple[str, Optional[UUID]]:
    """Compute the next semantic report version string when multiple documents trigger audits."""
    if not latest:
        return "1.0", None
    parts = latest.version.split(".")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        major, minor = int(parts[0]), int(parts[1]) + 1
        if minor >= 10:
            major += 1
            minor = 0
        return f"{major}.{minor}", latest.id
    return f"{latest.version}.1", latest.id


async def run_legal_research(document_id: UUID) -> None:
    """Run holistic project-wide Article-RAG compliance audit triggered by an analyzed document."""
    start_step(document_id, 3, "Audit holistique multi-documents & Article-RAG")
    async with SyncSession() as session:
        result = await session.execute(
            select(DocumentExtraction)
            .options(
                selectinload(DocumentExtraction.document).selectinload(Document.project),
                selectinload(DocumentExtraction.analysis),
            )
            .where(DocumentExtraction.document_id == document_id)
        )
        extraction = result.scalar_one_or_none()
        if not extraction:
            raise RuntimeError("Extraction introuvable pour la recherche juridique")
        if not extraction.analysis:
            raise RuntimeError("Analyse semantique introuvable pour la recherche juridique")

        project_id = extraction.document.project_id

        ready_doc_ids, pending_doc_ids = await get_project_analysis_readiness(session, project_id)
        if pending_doc_ids:
            start_step(
                document_id,
                3,
                f"En attente de l'analyse de {len(pending_doc_ids)} autre(s) document(s) du projet",
            )
            return
        if not ready_doc_ids:
            return

        for ready_doc_id in ready_doc_ids:
            start_step(ready_doc_id, 3, "Recherche des textes applicables au pays et au secteur")

        latest_res = await session.execute(
            select(ReportVersion)
            .where(ReportVersion.project_id == project_id)
            .order_by(ReportVersion.created_at.desc())
        )
        latest_report = latest_res.scalars().first()
        next_version, parent_id = _next_project_version(latest_report)

        audit_result = await run_holistic_compliance_audit(
            session,
            project_id,
            focus_document_id=document_id,
        )
        report_version = await persist_audit_report_version(
            session,
            project_id,
            audit_result,
            version=next_version,
            parent_version_id=parent_id,
        )

        bind_report_documents(ready_doc_ids, report_version.id)
        for ready_doc_id in ready_doc_ids:
            complete_step(
                ready_doc_id,
                3,
                "Les constats multi-documents et les citations d'articles sont enregistrés",
                report_version.id,
            )
            start_step(ready_doc_id, 4, "Calcul du score et du niveau de confiance")
        from app.workers.scoring import scoring_task

        try:
            enqueue_document_task(scoring_task, report_version.id, "scoring")
        except Exception as exc:
            logger.warning("Unable to queue scoring for report %s: %s", report_version.id, exc)
            for ready_doc_id in ready_doc_ids:
                fail_step(ready_doc_id, 4)


@celery_app.task(bind=True, max_retries=2)
def legal_research_task(self, document_id):
    """Celery task wrapper for holistic Article-RAG legal research."""
    try:
        run_async_task(run_legal_research(ensure_uuid(document_id)), async_engine)
    except Exception as exc:
        logger.error("Legal research error for document %s: %s", document_id, exc)
        raise self.retry(exc=exc, countdown=30)
