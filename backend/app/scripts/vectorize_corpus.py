"""CLI to compute unit embeddings for LegalArticle rows within strict TPM/RPM limits."""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text

from app.core.database import async_session_maker, init_db
from app.services.article_rag import vectorize_articles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def print_status() -> None:
    async with async_session_maker() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT t.code, count(a.id) AS total, count(a.embedding) AS embedded "
                    "FROM legal_text t LEFT JOIN legal_article a ON a.text_id = t.id "
                    "GROUP BY t.code ORDER BY t.code"
                )
            )
        ).all()
        tot, emb = 0, 0
        for code, t_cnt, e_cnt in rows:
            tot += t_cnt
            emb += e_cnt
            print(f"  {code:16s} | embedded={e_cnt:4d}/{t_cnt:4d}")
        print(f"TOTAL EMBEDDED: {emb}/{tot}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Vectorize LegalArticle rows for Hybrid Article-RAG.")
    parser.add_argument("--codes", nargs="*", help="Subset of LegalText codes to vectorize.")
    parser.add_argument("--limit", type=int, default=None, help="Max number of articles to embed in this run.")
    parser.add_argument("--max-tpm", type=int, default=24000, help="Token-per-minute budget (Gemini free tier = 30K).")
    parser.add_argument("--status-only", action="store_true", help="Print embedding coverage and exit.")
    args = parser.parse_args()

    await init_db()
    if args.status_only:
        await print_status()
        return

    count = await vectorize_articles(
        text_codes=args.codes,
        limit=args.limit,
        max_tpm=args.max_tpm,
    )
    logger.info("Vectorization run complete: %d articles embedded.", count)
    await print_status()


if __name__ == "__main__":
    asyncio.run(main())
