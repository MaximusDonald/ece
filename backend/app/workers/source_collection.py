"""Collect and re-index explicitly registered official legal document URLs."""

import hashlib
import html
import ipaddress
import re
import socket
from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from uuid import UUID

import fitz
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.legal import LegalSource, SourceCollectionRun, SourceCollectionRunStatus, SourceStatus
from app.services.llm_client import get_llm_client
from app.workers.celery_app import celery_app
from app.workers.async_runner import run_async_task


MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_REDIRECTS = 5
settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)


class _VisibleHTMLText(HTMLParser):
    _ignored = {"script", "style", "noscript", "svg", "nav", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._ignored:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._ignored and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())


def _validate_public_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Seules les URL HTTPS publiques sont autorisées.")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Les hôtes locaux ne peuvent pas être collectés.")
    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            raise ValueError("Le domaine de l’URL ne peut pas être résolu.") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("L’URL doit pointer uniquement vers des adresses IP publiques.")


def _extract_content(body: bytes, content_type: str, url: str) -> str:
    path = urlparse(url).path.lower()
    if "pdf" in content_type.lower() or path.endswith(".pdf"):
        document = fitz.open(stream=body, filetype="pdf")
        try:
            text = "\n".join(page.get_text("text") for page in document)
        finally:
            document.close()
    elif "html" in content_type.lower() or "xhtml" in content_type.lower() or body.lstrip().startswith(b"<"):
        parser = _VisibleHTMLText()
        parser.feed(body.decode("utf-8", errors="replace"))
        text = "\n".join(parser.parts)
    else:
        raise ValueError(f"Format non pris en charge ({content_type or 'inconnu'}). Utilisez une page HTML ou un PDF.")

    normalized = "\n".join(re.sub(r"\s+", " ", line).strip() for line in html.unescape(text).splitlines())
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if len(normalized) < 100:
        raise ValueError("La page ne contient pas assez de texte juridique exploitable.")
    return normalized


async def _download(url: str, etag: str | None, last_modified: str | None) -> tuple[int, str, str, str | None, str | None, int]:
    current_url = url
    initial_host = urlparse(url).hostname
    headers = {"User-Agent": "ECE-LegalCorpusCollector/1.0", "Accept": "text/html,application/xhtml+xml,application/pdf"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    async with httpx.AsyncClient(timeout=httpx.Timeout(45), follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _validate_public_https_url(current_url)
            if urlparse(current_url).hostname != initial_host:
                headers.pop("If-None-Match", None)
                headers.pop("If-Modified-Since", None)
            async with client.stream("GET", current_url, headers=headers) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirection sans destination.")
                    current_url = urljoin(current_url, location)
                    continue
                if response.status_code == 304:
                    return 304, "", current_url, etag, last_modified, 0
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Le document dépasse la limite de collecte de 25 Mo.")
                text = _extract_content(bytes(body), content_type, current_url)
                return (
                    response.status_code,
                    text,
                    current_url,
                    response.headers.get("etag"),
                    response.headers.get("last-modified"),
                    len(body),
                )
    raise ValueError("Trop de redirections lors de la collecte.")


async def _collect(run_id: UUID, source_id: UUID) -> None:
    try:
        async with Session() as session:
            run = await session.get(SourceCollectionRun, run_id)
            source = await session.get(LegalSource, source_id)
            if not run or not source:
                return
            run.status = SourceCollectionRunStatus.RUNNING
            run.started_at = datetime.utcnow()
            source.last_collection_at = run.started_at
            source.last_collection_status = run.status.value
            await session.commit()

            status_code, collected_text, final_url, etag, last_modified, _ = await _download(
                source.url_official, source.source_etag, source.source_last_modified
            )
            run.http_status_code = status_code
            run.previous_hash = source.content_hash
            source.source_etag = etag or source.source_etag
            source.source_last_modified = last_modified or source.source_last_modified

            if status_code == 304:
                run.collected_hash = source.content_hash
                run.changed = False
                run.status = SourceCollectionRunStatus.UNCHANGED
                source.status = SourceStatus.VERIFIED
            else:
                new_hash = hashlib.sha256(collected_text.encode("utf-8")).hexdigest()
                run.collected_hash = new_hash
                run.changed = new_hash != source.content_hash
                if run.changed:
                    embeddings = await get_llm_client().get_embeddings([collected_text[:12000]])
                    if not embeddings or len(embeddings[0]) != 1536 or not any(abs(value) > 1e-10 for value in embeddings[0]):
                        raise RuntimeError("Le fournisseur d’embeddings n’a pas retourné un vecteur exploitable de 1536 dimensions.")
                    source.content_text = collected_text
                    source.content_hash = new_hash
                    source.embedding = embeddings[0]
                    source.status = SourceStatus.VERIFIED
                    source.updated_at = datetime.utcnow()
                else:
                    source.status = SourceStatus.VERIFIED
                run.status = SourceCollectionRunStatus.SUCCEEDED if run.changed else SourceCollectionRunStatus.UNCHANGED
                # A successful HTTP 200 confirms the current contents even when unchanged.
            run.finished_at = datetime.utcnow()
            source.last_successful_collection_at = run.finished_at
            source.last_collection_status = run.status.value
            source.last_collection_run_id = run.id
            await session.commit()
    except Exception as exc:
        # A failure before the initial RUNNING commit must also leave a terminal
        # run state; use a fresh session in the current task loop for recovery.
        async with Session() as session:
            run = await session.get(SourceCollectionRun, run_id)
            source = await session.get(LegalSource, source_id)
            if run:
                run.status = SourceCollectionRunStatus.FAILED
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
            run.status = SourceCollectionRunStatus.FAILED
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
                    SourceCollectionRun.status.in_([SourceCollectionRunStatus.QUEUED, SourceCollectionRunStatus.RUNNING]),
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
