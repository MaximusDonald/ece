"""Incremental compliance re-audit worker preserving Article-RAG citations and parades."""

from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker
from sqlmodel import select

from app.core.config import get_settings
from app.core.utils import ensure_uuid
from app.models.document import Document, DocumentAnalysis, DocumentExtraction
from app.models.legal import ReportVersion
from app.models.user import Project
from app.services.compliance_auditor import (
    persist_audit_report_version,
    run_holistic_compliance_audit,
)
from app.workers.async_runner import run_async_task
from app.workers.celery_app import celery_app
from app.workers.task_dispatch import enqueue_document_task

logger = logging.getLogger(__name__)
settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def increment_version(version: str) -> str:
    """Increment version number (1.0 -> 1.1, 1.9 -> 2.0)."""
    parts = version.split(".")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        major, minor = int(parts[0]), int(parts[1])
        if minor >= 9:
            return f"{major + 1}.0"
        return f"{major}.{minor + 1}"
    return f"{version}.1"


async def run_incremental_update(report_version_id: UUID, context_data: Dict[str, Any]) -> None:
    """Re-run holistic Article-RAG audit when complementary context is submitted."""
    async with SyncSession() as session:
        result = await session.execute(
            select(ReportVersion)
            .options(
                selectinload(ReportVersion.project)
                .selectinload(Project.documents)
                .selectinload(Document.extraction)
            )
            .where(ReportVersion.id == report_version_id)
        )
        old_report = result.scalar_one_or_none()
        if not old_report or not old_report.project:
            return

        try:
            extraction = None
            if old_report.project.documents and old_report.project.documents[0].extraction:
                extraction = old_report.project.documents[0].extraction
            else:
                doc_res = await session.execute(
                    select(Document).where(Document.project_id == old_report.project_id)
                )
                first_doc = doc_res.scalars().first()
                if first_doc:
                    ext_res = await session.execute(
                        select(DocumentExtraction).where(DocumentExtraction.document_id == first_doc.id)
                    )
                    extraction = ext_res.scalar_one_or_none()

            if extraction:
                analysis_res = await session.execute(
                    select(DocumentAnalysis).where(DocumentAnalysis.extraction_id == extraction.id)
                )
                analysis = analysis_res.scalar_one_or_none()
                if analysis:
                    updated_vague_zones = []
                    for zone in (analysis.vague_zones or []):
                        zone_key = str(zone.get("clause_ref", "")).lower()
                        if any(k.lower() in zone_key for k in context_data.keys()):
                            zone["resolved"] = True
                            zone["resolution"] = context_data
                        updated_vague_zones.append(zone)
                    analysis.vague_zones = updated_vague_zones
                    session.add(analysis)
                    await session.flush()

            new_version_num = increment_version(old_report.version)
            audit_result = await run_holistic_compliance_audit(
                session,
                old_report.project_id,
                incremental_context=context_data,
                previous_report_id=old_report.id,
            )
            new_report = await persist_audit_report_version(
                session,
                old_report.project_id,
                audit_result,
                version=new_version_num,
                parent_version_id=old_report.id,
            )

            from app.workers.report import report_generation_task

            try:
                enqueue_document_task(report_generation_task, new_report.id, "report")
            except Exception as exc:
                logger.warning("Unable to queue PDF generation for new report %s: %s", new_report.id, exc)

        except Exception as exc:
            logger.error("Incremental update error for report %s: %s", report_version_id, exc)
            raise


@celery_app.task(bind=True, max_retries=2)
def incremental_update_task(self, report_version_id, context_data: dict):
    """Celery task for incremental context-aware compliance update."""
    try:
        run_async_task(run_incremental_update(ensure_uuid(report_version_id), context_data), async_engine)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
