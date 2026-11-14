"""Manage complementary textual context as a consultable, editable project Document."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentAnalysis, DocumentExtraction, DocumentStatus
from app.models.user import Project
from app.services.minio_client import get_bucket_name, get_minio_client, upload_file

logger = logging.getLogger(__name__)

CONTEXT_DOC_TYPE = "contexte_complementaire"
CONTEXT_DOC_FILENAME = "contexte-complementaire.md"

FIELD_LABELS = {
    "vague_zone": "Zone floue / clause concernée",
    "hosting_location": "Localisation d'hébergement",
    "subcontractor": "Sous-traitant principal",
    "transfer_details": "Détails sur les transferts de données",
}


def format_context_entry_markdown(
    context_data: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> str:
    """Format a complementary context payload into structured French Markdown."""
    ts = (timestamp or datetime.utcnow()).strftime("%d/%m/%Y %H:%M UTC")
    lines = [f"## Précision contextuelle — {ts}", ""]
    for key, value in context_data.items():
        if value is None or str(value).strip() == "":
            continue
        label = FIELD_LABELS.get(key, key.replace("_", " ").capitalize())
        lines.append(f"- **{label}** : {str(value).strip()}")
    if len(lines) == 2:
        lines.append("- *(Aucune précision textuelle saisie)*")
    lines.append("")
    return "\n".join(lines)


async def get_context_document(
    session: AsyncSession,
    project_id: UUID,
) -> Optional[tuple[Document, Optional[DocumentExtraction], Optional[DocumentAnalysis]]]:
    """Return the project's complementary context document with extraction and analysis."""
    res = await session.execute(
        select(Document)
        .options(selectinload(Document.extraction).selectinload(DocumentExtraction.analysis))
        .where(
            Document.project_id == project_id,
            Document.document_type == CONTEXT_DOC_TYPE,
        )
        .order_by(Document.created_at.desc())
    )
    doc = res.scalars().first()
    if not doc:
        return None
    ext = doc.extraction
    ana = ext.analysis if ext else None
    return doc, ext, ana


async def upsert_context_document(
    session: AsyncSession,
    project: Project,
    *,
    context_data: Optional[Dict[str, Any]] = None,
    markdown_override: Optional[str] = None,
    replace: bool = False,
) -> tuple[Document, DocumentExtraction, DocumentAnalysis]:
    """Create or update the project's complementary context Document, Extraction, and Analysis."""
    now = datetime.utcnow()
    existing = await get_context_document(session, project.id)
    cleaned_data = {
        k: v
        for k, v in (context_data or {}).items()
        if v is not None and str(v).strip() != ""
    }

    if markdown_override is not None:
        new_markdown = markdown_override.strip() or "# Contexte complémentaire du projet\n"
    else:
        entry_md = format_context_entry_markdown(cleaned_data, now)
        if existing and existing[1] and existing[1].markdown and not replace:
            new_markdown = existing[1].markdown.rstrip() + "\n\n" + entry_md
        else:
            new_markdown = "# Contexte complémentaire du projet\n\n" + entry_md

    md_bytes = new_markdown.encode("utf-8")
    bucket_name = get_bucket_name(str(project.org_id), "documents")
    object_key = f"{project.id}/{CONTEXT_DOC_FILENAME}"

    try:
        minio_client = get_minio_client()
        upload_file(minio_client, bucket_name, object_key, md_bytes, "text/markdown")
    except Exception as exc:
        logger.warning("MinIO upload skipped for context document %s: %s", project.id, exc)

    if existing:
        doc, ext, ana = existing
        doc.size_bytes = len(md_bytes)
        doc.status = DocumentStatus.EXTRACTED
        doc.updated_at = now
        session.add(doc)
    else:
        doc = Document(
            project_id=project.id,
            filename=CONTEXT_DOC_FILENAME,
            document_type=CONTEXT_DOC_TYPE,
            mime_type="text/markdown",
            minio_bucket=bucket_name,
            minio_object=object_key,
            size_bytes=len(md_bytes),
            status=DocumentStatus.EXTRACTED,
            created_at=now,
            updated_at=now,
        )
        session.add(doc)
        await session.flush()
        ext = None
        ana = None

    if ext is None:
        ext = DocumentExtraction(
            document_id=doc.id,
            markdown=new_markdown,
            quality_score=1.0,
            page_count=1,
            language="fr",
            created_at=now,
        )
        session.add(ext)
        await session.flush()
    else:
        ext.markdown = new_markdown
        ext.quality_score = 1.0
        session.add(ext)

    existing_entities = dict((ana.entities if ana else None) or {})
    entries: List[Dict[str, Any]] = [] if replace else list(existing_entities.get("entries") or [])
    if cleaned_data:
        entries.append({**cleaned_data, "submitted_at": now.isoformat()})

    new_entities: Dict[str, Any] = {
        "entries": entries,
        "latest_context": cleaned_data or existing_entities.get("latest_context") or {},
        "raw_markdown": new_markdown,
    }

    if ana is None:
        ana = DocumentAnalysis(
            extraction_id=ext.id,
            entities=new_entities,
            vague_zones=[],
            created_at=now,
        )
        session.add(ana)
    else:
        ana.entities = new_entities
        session.add(ana)

    await session.flush()
    return doc, ext, ana
