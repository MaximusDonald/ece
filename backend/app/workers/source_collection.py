"""Regulatory Sentinel worker: checks official feeds for ETag/SHA-256 changes and creates pending alerts."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.corpus import RegulatoryAlert, RegulatoryAlertStatus
from app.models.legal import (
    AuditLog,
    LegalSource,
    SourceCollectionRun,
    SourceCollectionRunStatus,
    SourceStatus,
)
from app.services.crawler import RegulatorySentinel, SentinelCheckResult
from app.workers.async_runner import run_async_task
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def run_sentinel_check(
    run_id: UUID,
    source_id: UUID,
    *,
    session_factory=Session,
    sentinel_override: Optional[RegulatorySentinel] = None,
) -> int:
    """Inspect a watched official URL via ETag/SHA-256 diffing and create admin review alerts."""
    created_alerts = 0
    async with session_factory() as session:
        run = await session.get(SourceCollectionRun, run_id)
        source = await session.get(LegalSource, source_id)
        if not run or not source:
            return 0

        run.status = SourceCollectionRunStatus.RUNNING.value
        run.started_at = datetime.utcnow()
        source.last_collection_at = run.started_at
        source.last_collection_status = SourceCollectionRunStatus.RUNNING.value
        previous_hash = source.content_hash if source.content_hash and set(source.content_hash) != {"0"} else None
        previous_snapshot = source.content_text or None
        previous_etag = source.source_etag
        previous_last_modified = source.source_last_modified
        await session.commit()

    try:
        async with session_factory() as session:
            known_urls_res = await session.execute(
                select(RegulatoryAlert.detected_url).where(RegulatoryAlert.source_id == source_id)
            )
            known_urls = {row[0] for row in known_urls_res.all() if row[0]}

        sentinel = sentinel_override or RegulatorySentinel(source.url_official)
        result: SentinelCheckResult = await sentinel.check_for_updates(
            previous_etag=previous_etag,
            previous_last_modified=previous_last_modified,
            previous_hash=previous_hash,
            previous_snapshot=previous_snapshot,
            known_urls=known_urls,
        )

        async with session_factory() as session:
            run = await session.get(SourceCollectionRun, run_id)
            source = await session.get(LegalSource, source_id)
            if not run or not source:
                return 0

            run.http_status_code = result.status_code
            run.previous_hash = previous_hash
            run.collected_hash = result.new_hash or previous_hash
            run.finished_at = datetime.utcnow()

            if not result.changed:
                run.changed = False
                run.status = SourceCollectionRunStatus.UNCHANGED.value
                source.last_successful_collection_at = run.finished_at
                source.last_collection_status = SourceCollectionRunStatus.UNCHANGED.value
                source.last_collection_run_id = run.id
                if result.etag:
                    source.source_etag = result.etag
                if result.last_modified:
                    source.source_last_modified = result.last_modified
                await session.commit()
                return 0

            # Page or feed fingerprint changed -> record new fingerprint and raise alerts for admin review
            source.content_hash = result.new_hash
            if result.page_snapshot:
                source.content_text = result.page_snapshot[:60000]
            source.source_etag = result.etag
            source.source_last_modified = result.last_modified
            source.last_successful_collection_at = run.finished_at
            source.last_collection_status = SourceCollectionRunStatus.SUCCEEDED.value
            source.last_collection_run_id = run.id
            source.is_portal = True

            jurisdiction = (source.country_code or "CEDEAO").upper()
            candidates_to_alert = result.candidates[:8]
            if not candidates_to_alert:
                from app.services.crawler import NormativeCandidate
                candidates_to_alert = [
                    NormativeCandidate(
                        url=source.url_official,
                        title=f"Modification détectée sur {source.title}",
                        filename=None,
                        reason="Diff textuel détecté sur la source surveillée",
                    )
                ]

            for cand in candidates_to_alert:
                existing_alert = (
                    await session.execute(
                        select(RegulatoryAlert).where(
                            RegulatoryAlert.source_id == source.id,
                            RegulatoryAlert.detected_url == cand.url[:1000],
                            RegulatoryAlert.new_hash == result.new_hash,
                        )
                    )
                ).scalar_one_or_none()
                if existing_alert:
                    continue

                alert = RegulatoryAlert(
                    source_id=source.id,
                    collection_run_id=run.id,
                    jurisdiction=jurisdiction,
                    authority=source.authority,
                    title=cand.title[:500],
                    detected_url=cand.url[:1000],
                    document_filename=cand.filename[:500] if cand.filename else None,
                    previous_hash=previous_hash,
                    new_hash=result.new_hash,
                    etag=result.etag,
                    change_summary=(
                        f"{cand.reason}\n\n{result.change_summary}"
                        if cand.reason
                        else result.change_summary
                    ),
                    status=RegulatoryAlertStatus.PENDING_REVIEW.value,
                )
                session.add(alert)
                await session.flush()
                session.add(
                    AuditLog(
                        action="regulatory_alert_created",
                        entity_type="regulatory_alert",
                        entity_id=alert.id,
                        diff={
                            "source_id": str(source.id),
                            "detected_url": alert.detected_url,
                            "title": alert.title,
                        },
                    )
                )
                created_alerts += 1

            run.changed = True
            run.discovered_urls_count = len(result.candidates)
            run.downloaded_files_count = 0  # Sentinel does not auto-download/ingest without admin approval
            run.ai_processed_count = created_alerts
            run.status = SourceCollectionRunStatus.SUCCEEDED.value
            await session.commit()
            return created_alerts

    except Exception as exc:
        logger.exception("Sentinel check failed for source %s: %s", source_id, exc)
        await _mark_failed(run_id, source_id, str(exc)[:2000], session_factory=session_factory)
        return 0


async def _mark_failed(
    run_id: UUID,
    source_id: UUID,
    message: str,
    *,
    session_factory=Session,
) -> None:
    async with session_factory() as session:
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


@celery_app.task(name="app.workers.source_collection.collect_source")
def collect_source(run_id: str, source_id: str) -> None:
    lock_key = f"ece:source-collection-lock:{source_id}"
    redis = celery_app.backend.client
    if not redis.set(lock_key, run_id, nx=True, ex=60 * 60):
        run_async_task(
            _mark_failed(UUID(run_id), UUID(source_id), "Une autre vérification Sentinelle est déjà en cours."),
            engine,
        )
        return
    try:
        run_async_task(run_sentinel_check(UUID(run_id), UUID(source_id)), engine)
    finally:
        redis.delete(lock_key)


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
                    SourceCollectionRun.status.in_(
                        [SourceCollectionRunStatus.QUEUED.value, SourceCollectionRunStatus.RUNNING.value]
                    ),
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
            await _mark_failed(run_id, source_id, f"Impossible de mettre la veille en file : {str(exc)[:500]}")
    return len(run_ids)


@celery_app.task(name="app.workers.source_collection.collect_enabled_sources")
def collect_enabled_sources() -> int:
    """Queue weekly Regulatory Sentinel checks for all enabled official watch feeds."""
    return run_async_task(_queue_enabled_sources(), engine)
