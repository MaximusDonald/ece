"""Unit & integration tests for Hybrid Article-RAG (HNSW + GIN FTS + Jurisdiction filter)."""

import pytest

from app.core.database import async_engine
from app.services.article_rag import (
    _build_or_tsquery,
    expand_legal_query,
    hybrid_search_articles,
    jurisdictions_for_country,
)


def test_jurisdictions_for_country_benin():
    scopes = jurisdictions_for_country("bj")
    assert scopes == ["BJ", "UA", "CEDEAO", "UEMOA", "OHADA", "OAPI"]


def test_build_or_tsquery_removes_french_stopwords():
    tsq = _build_or_tsquery("hébergement des données personnelles en France")
    assert "hébergement" in tsq
    assert "données" in tsq
    assert "france" in tsq
    assert "des" not in tsq.split(" | ")
    assert "en" not in tsq.split(" | ")


def test_expand_legal_query_adds_transfer_terms():
    expanded = expand_legal_query("hébergement données en France")
    assert "État tiers" in expanded
    assert "APDP" in expanded


@pytest.mark.asyncio
async def test_hybrid_search_cross_border_hosting_and_jurisdiction_filter():
    try:
        results = await hybrid_search_articles(
            "hébergement données en France",
            jurisdictions=jurisdictions_for_country("BJ"),
            limit=5,
            alpha=0.65,
        )
        assert len(results) >= 1
        top_numbers = [r.article_number for r in results[:3]]
        top_texts = " ".join(r.full_text.lower() for r in results[:3])
        assert any(num in top_numbers for num in ("Article 391", "Article 392", "Article 36"))
        assert "tiers" in top_texts or "transfert" in top_texts

        cedeao_only = await hybrid_search_articles(
            "données personnelles",
            jurisdictions=["CEDEAO"],
            limit=5,
            alpha=0.65,
        )
        assert len(cedeao_only) >= 1
        assert all(r.jurisdiction == "CEDEAO" for r in cedeao_only)
    finally:
        await async_engine.dispose()
