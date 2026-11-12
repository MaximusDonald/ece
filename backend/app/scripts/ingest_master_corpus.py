"""Idempotent Master Corpus ingestion script (Phase 3): parse, store hierarchy, and tag."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from sqlmodel import delete, select

from app.core.database import async_session_maker, init_db
from app.models.corpus import LegalArticle, LegalSection, LegalText, LegalTextStatus
from app.services.legal_parser import (
    MASTER_CORPUS_CATALOG,
    MasterTextMetadata,
    load_master_text_file,
    parse_legal_text,
)
from app.services.legal_tagger import extract_deterministic_signals, tag_articles_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def ingest_single_text(
    corpus_dir: Path,
    meta: MasterTextMetadata,
    force: bool = False,
) -> tuple[LegalText, int, int]:
    """Parse one Master Corpus text deterministically and store its sections & articles."""
    raw_text = load_master_text_file(corpus_dir, meta)
    parsed = parse_legal_text(raw_text, meta)

    async with async_session_maker() as session:
        existing = (
            await session.execute(select(LegalText).where(LegalText.code == meta.code))
        ).scalar_one_or_none()

        if existing and not force and existing.sha256_hash == parsed.sha256_hash and existing.total_articles > 0:
            logger.info("Skipping %s (already ingested, %d articles).", meta.code, existing.total_articles)
            return existing, len(parsed.sections), existing.total_articles

        if existing:
            await session.execute(delete(LegalArticle).where(LegalArticle.text_id == existing.id))
            await session.execute(delete(LegalSection).where(LegalSection.text_id == existing.id))
            legal_text = existing
            legal_text.title = meta.title
            legal_text.jurisdiction = meta.jurisdiction
            legal_text.authority = meta.authority
            legal_text.level = meta.level
            legal_text.publication_date = meta.publication_date
            legal_text.official_url = meta.official_url
            legal_text.pdf_path = f"pdfs/{meta.pdf_filename}"
            legal_text.text_path = f"texts/{meta.text_filename}"
            legal_text.sha256_hash = parsed.sha256_hash
            legal_text.updated_at = datetime.utcnow()
        else:
            legal_text = LegalText(
                code=meta.code,
                title=meta.title,
                jurisdiction=meta.jurisdiction,
                authority=meta.authority,
                level=meta.level,
                publication_date=meta.publication_date,
                status=LegalTextStatus.IN_FORCE.value,
                official_url=meta.official_url,
                minio_bucket="legal-corpus",
                pdf_path=f"pdfs/{meta.pdf_filename}",
                text_path=f"texts/{meta.text_filename}",
                sha256_hash=parsed.sha256_hash,
            )
            session.add(legal_text)
        await session.flush()

        # Insert sections in order so parents always resolve cleanly
        section_id_by_order: Dict[int, UUID] = {}
        for psec in parsed.sections:
            parent_id = section_id_by_order.get(psec.parent_order_index) if psec.parent_order_index else None
            sec = LegalSection(
                text_id=legal_text.id,
                parent_section_id=parent_id,
                level_name=psec.level_name,
                title=psec.title,
                breadcrumb=psec.breadcrumb,
                order_index=psec.order_index,
            )
            session.add(sec)
            await session.flush()
            section_id_by_order[psec.order_index] = sec.id

        # Insert articles with deterministic baseline compliance signals
        for part in parsed.articles:
            signals = extract_deterministic_signals(part.full_text, part.title)
            art = LegalArticle(
                text_id=legal_text.id,
                section_id=section_id_by_order.get(part.section_order_index) if part.section_order_index else None,
                article_number=part.article_number,
                order_index=part.order_index,
                title=part.title,
                full_text=part.full_text,
                topics=[],
                actors=[],
                has_sanction=signals["has_sanction"],
                sanction_details=signals["sanction_details"],
                compliance_rule_type=signals["compliance_rule_type"],
                ai_tagged=False,
            )
            session.add(art)

        legal_text.total_articles = len(parsed.articles)
        legal_text.updated_at = datetime.utcnow()
        await session.commit()
        logger.info(
            "Ingested %s: %d sections, %d articles.",
            meta.code,
            len(parsed.sections),
            len(parsed.articles),
        )
        return legal_text, len(parsed.sections), len(parsed.articles)


async def run_ai_tagging(
    text_codes: Optional[List[str]] = None,
    limit: Optional[int] = None,
    batch_size: int = 10,
    delay_seconds: float = 4.2,
) -> int:
    """Run Pydantic-constrained AI semantic tagging on untagged LegalArticle rows."""
    async with async_session_maker() as session:
        sec_rows = (await session.execute(select(LegalSection))).scalars().all()
        breadcrumbs = {s.id: s.breadcrumb for s in sec_rows}

        query = select(LegalArticle).where(LegalArticle.ai_tagged.is_(False))
        if text_codes:
            text_ids = (
                await session.execute(select(LegalText.id).where(LegalText.code.in_(text_codes)))
            ).scalars().all()
            if not text_ids:
                return 0
            query = query.where(LegalArticle.text_id.in_(text_ids))

        query = query.order_by(LegalArticle.text_id, LegalArticle.order_index)
        if limit:
            query = query.limit(limit)

        articles = (await session.execute(query)).scalars().all()
        if not articles:
            logger.info("No untagged articles matching criteria.")
            return 0

        total_tagged = 0
        for idx in range(0, len(articles), batch_size):
            batch = articles[idx : idx + batch_size]
            count = await tag_articles_batch(batch, breadcrumbs)
            for art in batch:
                art.updated_at = datetime.utcnow()
                session.add(art)
            await session.commit()
            total_tagged += count
            logger.info("AI tagging batch %d-%d: tagged %d/%d", idx + 1, idx + len(batch), count, len(batch))
            if idx + batch_size < len(articles):
                await asyncio.sleep(delay_seconds)

        return total_tagged


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Master Corpus texts and run semantic tagging.")
    parser.add_argument("--corpus-dir", default="/app/corpus_sources")
    parser.add_argument("--force", action="store_true", help="Re-parse and replace existing parsed rows.")
    parser.add_argument("--codes", nargs="*", help="Optional subset of text codes to process.")
    parser.add_argument("--ai-limit", type=int, default=0, help="Number of untagged articles to AI-tag (0 = skip, -1 = all).")
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    await init_db()
    corpus_dir = Path(args.corpus_dir)

    selected = [m for m in MASTER_CORPUS_CATALOG if not args.codes or m.code in args.codes]
    for meta in selected:
        await ingest_single_text(corpus_dir, meta, force=args.force)

    if args.ai_limit != 0:
        limit = None if args.ai_limit < 0 else args.ai_limit
        tagged = await run_ai_tagging(
            text_codes=args.codes,
            limit=limit,
            batch_size=args.batch_size,
        )
        logger.info("AI semantic tagging completed: %d articles tagged.", tagged)


if __name__ == "__main__":
    asyncio.run(main())
