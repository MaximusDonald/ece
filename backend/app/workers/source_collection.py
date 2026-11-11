"""Collect, recursively crawl, archive to MinIO, and extract legal sources with AI."""

import hashlib
import html
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlparse
from uuid import UUID

import fitz
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.legal import (
    LegalLevel,
    LegalSource,
    SourceCollectionRun,
    SourceCollectionRunStatus,
    SourceStatus,
)
from app.services.crawler import (
    DiscoveredDocument,
    LegalCrawlerEngine,
    validate_public_https_url,
)
from app.services.legal_extractor import LegalLLMExtractor
from app.services.llm_client import get_llm_client
from app.services.minio_client import ensure_bucket_exists, get_minio_client, upload_file
from app.workers.async_runner import run_async_task
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)
MINIO_BUCKET_LEGAL = "legal-sources"


async def _generate_embeddings(text: str) -> List[float]:
    """Generate 1536-dimensional embeddings with fallback."""
    llm = get_llm_client()
    try:
        embeddings = await llm.get_embeddings([text[:12000]])
        if embeddings and len(embeddings[0]) == 1536 and any(abs(v) > 1e-10 for v in embeddings[0]):
            return embeddings[0]
    except Exception as exc:
        logger.warning("Embeddings provider fallback: %s", exc)
    return [0.0] * 1536


async def _collect(run_id: UUID, source_id: UUID) -> None:
    """Execute intelligent recursive crawl, MinIO storage, and AI analysis."""
    extractor = LegalLLMExtractor()
    minio_client = get_minio_client()
    ensure_bucket_exists(minio_client, MINIO_BUCKET_LEGAL)

    async with Session() as session:
        run = await session.get(SourceCollectionRun, run_id)
        source = await session.get(LegalSource, source_id)
        if not run or not source:
            return

        run.status = SourceCollectionRunStatus.RUNNING
        run.started_at = datetime.utcnow()
        source.last_collection_at = run.started_at
        source.last_collection_status = run.status
        await session.commit()

    try:
        discovered_docs: List[DiscoveredDocument] = []
        is_direct_pdf = source.url_official.lower().endswith(".pdf")

        # Collect existing filenames under this specific parent source to prevent re-collecting duplicates
        existing_filenames = set()
        async with Session() as session:
            existing_children = await session.execute(
                select(LegalSource.original_filename)
                .where(LegalSource.parent_source_id == source_id)
            )
            for row in existing_children.scalars().all():
                if row and row.strip():
                    existing_filenames.add(row.strip().lower())

        if is_direct_pdf:
            filename = source.original_filename or source.url_official.split("/")[-1] or "document.pdf"
            if filename.strip().lower() in existing_filenames:
                logger.info("PDF direct '%s' déjà collecté pour cette source parent. Téléchargement ignoré.", filename)
            else:
                # Direct PDF document collection
                validate_public_https_url(source.url_official)
                async with httpx.AsyncClient(timeout=httpx.Timeout(45.0), follow_redirects=True) as client:
                    resp = await client.get(source.url_official)
                    resp.raise_for_status()
                    content_bytes = resp.content
                    sha256 = hashlib.sha256(content_bytes).hexdigest()
                    minio_obj = f"{(source.country_code or 'bj').lower()}/{sha256[:12]}_{filename}"
                    upload_file(minio_client, MINIO_BUCKET_LEGAL, minio_obj, content_bytes, "application/pdf")

                    # Extract text
                    doc = fitz.open(stream=content_bytes, filetype="pdf")
                    try:
                        text_parts = [p.get_text("text") for p in doc]
                        full_text = "\n".join(text_parts).strip()
                    finally:
                        doc.close()

                    discovered_docs.append(
                        DiscoveredDocument(
                            download_url=source.url_official,
                            original_filename=filename,
                            content_type="application/pdf",
                            content_hash=sha256,
                            content_text=full_text,
                            minio_path=f"{MINIO_BUCKET_LEGAL}/{minio_obj}",
                            source_page_url=source.url_official,
                            anchor_text=source.title,
                            file_size_bytes=len(content_bytes),
                        )
                    )
        else:
            # Recursive web crawl on portal with filename deduplication filter
            crawler = LegalCrawlerEngine(
                root_url=source.url_official,
                max_depth=source.crawl_depth or 2,
                country_code=source.country_code or "bj",
                existing_filenames=existing_filenames,
            )
            discovered_docs = await crawler.crawl()

        # Process each newly discovered legal document with AI
        ai_processed = 0
        async with Session() as session:
            # Reload source & run
            run = await session.get(SourceCollectionRun, run_id)
            source = await session.get(LegalSource, source_id)
            if not run or not source:
                return

            run.discovered_urls_count = len(crawler.visited_urls) if not is_direct_pdf else 1
            run.downloaded_files_count = len(discovered_docs)

            for doc in discovered_docs:
                try:
                    doc_filename_clean = doc.original_filename.strip().lower()

                    # Deduplication check by filename, download URL or hash under this parent source
                    existing_result = await session.execute(
                        select(LegalSource).where(
                            (LegalSource.parent_source_id == source.id) &
                            (
                                (func.lower(LegalSource.original_filename) == doc_filename_clean) |
                                (LegalSource.download_url == doc.download_url) |
                                (LegalSource.content_hash == doc.content_hash)
                            )
                        )
                    )
                    child_source = existing_result.scalar_one_or_none()

                    if child_source:
                        logger.info(
                            "Le document PDF '%s' existe déjà pour ce portail. Analyse IA ignorée.",
                            doc.original_filename
                        )
                        continue

                    # Run AI legal analysis for genuinely new document
                    analysis = await extractor.analyze_document(
                        text=doc.content_text,
                        original_filename=doc.original_filename,
                        source_hint=f"{source.authority} - {doc.anchor_text}",
                    )

                    # Compute vector embedding
                    embedding = await _generate_embeddings(doc.content_text)

                    # Create new child legal document
                    new_child = LegalSource(
                        title=analysis.official_title,
                        authority=analysis.authority or source.authority,
                        country_code=source.country_code,
                        level=LegalLevel(analysis.legal_level),
                        article_ref=analysis.act_number or doc.original_filename,
                        url_official=doc.download_url,
                        download_url=doc.download_url,
                        original_filename=doc.original_filename,
                        minio_object_path=doc.minio_path,
                        content_hash=doc.content_hash,
                        content_text=doc.content_text,
                        status=SourceStatus.VERIFIED,
                        embedding=embedding,
                        is_portal=False,
                        parent_source_id=source.id,
                        summary=analysis.executive_summary,
                        legal_terms={"terms": analysis.legal_terms},
                        extracted_articles=analysis.key_articles,
                        crawl_depth=1,
                    )
                    session.add(new_child)
                    existing_filenames.add(doc_filename_clean)
                    ai_processed += 1
                except Exception as doc_exc:
                    logger.warning("Error analyzing document %s: %s", doc.original_filename, doc_exc)

            # Update parent source
            source.is_portal = True
            source.status = SourceStatus.VERIFIED
            source.last_successful_collection_at = datetime.utcnow()
            source.last_collection_status = SourceCollectionRunStatus.SUCCEEDED.value
            source.last_collection_run_id = run.id

            run.ai_processed_count = ai_processed
            run.status = SourceCollectionRunStatus.SUCCEEDED.value
            run.finished_at = datetime.utcnow()
            run.changed = len(discovered_docs) > 0
            await session.commit()

    except Exception as exc:
        logger.exception("Source collection failed for source %s: %s", source_id, exc)
        async with Session() as session:
            run = await session.get(SourceCollectionRun, run_id)
            source = await session.get(LegalSource, source_id)
            if run:
                run.status = SourceCollectionRunStatus.FAILED.value
                run.finished_at = datetime.utcnow()
                run.error_message = str(exc)[:2000]
            if source:
                source.last_collection_at = datetime.utcnow()
                source.last_collection_status = SourceCollectionRunStatus.FAILED.value
                source.last_collection_run_id = run_id
            await session.commit()


@celery_app.task(name="app.workers.source_collection.collect_source")
def collect_source(run_id: str, source_id: str) -> None:
    lock_key = f"ece:source-collection-lock:{source_id}"
    redis = celery_app.backend.client
    if not redis.set(lock_key, run_id, nx=True, ex=60 * 60):
        run_async_task(
            _mark_failed(UUID(run_id), UUID(source_id), "Une autre collecte de cette source est déjà en cours."),
            engine,
        )
        return
    try:
        run_async_task(_collect(UUID(run_id), UUID(source_id)), engine)
    finally:
        redis.delete(lock_key)


async def _mark_failed(run_id: UUID, source_id: UUID, message: str) -> None:
    async with Session() as session:
        run = await session.get(SourceCollectionRun, run_id)
        source = await session.get(LegalSource, source_id)
        if run:
            run.status = SourceCollectionRunStatus.FAILED.value
            run.finished_at = datetime.utcnow()
            run.error_message = message
        if source:
            source.last_collection_at = datetime.utcnow()
            source.last_collection_status = SourceCollectionRunStatus.FAILED.value
            source.last_collection_run_id = run_id
        await session.commit()


async def _queue_enabled_sources() -> int:
    async with Session() as session:
        result = await session.execute(
            select(LegalSource).where(
                LegalSource.collection_enabled.is_(True),
                LegalSource.status.notin_([SourceStatus.ARCHIVED, SourceStatus.REPLACED]),
            )
        )
        sources = result.scalars().all()
        run_ids: list[tuple[UUID, UUID]] = []
        for source in sources:
            active = await session.execute(
                select(SourceCollectionRun).where(
                    SourceCollectionRun.source_id == source.id,
                    SourceCollectionRun.status.in_([SourceCollectionRunStatus.QUEUED.value, SourceCollectionRunStatus.RUNNING.value]),
                ).order_by(SourceCollectionRun.requested_at.desc()).limit(1)
            )
            active_run = active.scalar_one_or_none()
            if active_run and active_run.requested_at > datetime.utcnow() - timedelta(hours=1):
                continue
            if active_run:
                active_run.status = SourceCollectionRunStatus.FAILED.value
                active_run.finished_at = datetime.utcnow()
                active_run.error_message = "La tâche est restée active plus d’une heure; elle sera retentée au prochain cycle."
            run = SourceCollectionRun(source_id=source.id, trigger_type="scheduled")
            session.add(run)
            await session.flush()
            source.last_collection_at = run.requested_at
            source.last_collection_status = SourceCollectionRunStatus.QUEUED.value
            source.last_collection_run_id = run.id
            run_ids.append((run.id, source.id))
        await session.commit()

    for run_id, source_id in run_ids:
        try:
            collect_source.delay(str(run_id), str(source_id))
        except Exception as exc:
            await _mark_failed(run_id, source_id, f"Impossible de mettre la collecte en file : {str(exc)[:500]}")
    return len(run_ids)


@celery_app.task(name="app.workers.source_collection.collect_enabled_sources")
def collect_enabled_sources() -> int:
    """Queue the weekly refresh for all enabled official URLs."""
    return run_async_task(_queue_enabled_sources(), engine)
