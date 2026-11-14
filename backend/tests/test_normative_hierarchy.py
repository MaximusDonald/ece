"""Tests for Phase 2: Normative hierarchy, temporal validity filtering, and conflict detection."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.article_rag import (
    ArticleSearchResult,
    apply_normative_ranking,
    detect_normative_conflicts,
    hybrid_search_articles,
)
from app.services.compliance_auditor import _normalize_findings


def _make_article(
    *,
    code: str,
    jurisdiction: str,
    level: str,
    status: str = "in_force",
    score: float = 0.8,
    topics: list[str] | None = None,
    rule_type: str = "mandatory",
    is_obsolete: bool = False,
) -> ArticleSearchResult:
    return ArticleSearchResult(
        article_id=uuid4(),
        text_id=uuid4(),
        text_code=code,
        text_title=f"Texte {code}",
        jurisdiction=jurisdiction,
        authority="Autorité test",
        section_breadcrumb="Titre I",
        article_number="Art. 1",
        title="Obligation",
        full_text="Contenu normatif de test.",
        topics=topics or [],
        actors=[],
        has_sanction=True,
        sanction_details="Amende administrative",
        compliance_rule_type=rule_type,
        score=score,
        text_level=level,
        text_status=status,
        publication_date="2020-01-01",
        is_obsolete=is_obsolete,
    )


def test_abrogated_and_obsolete_texts_excluded_and_hierarchy_prioritized():
    """Abrogated texts are filtered out and supranational norms outrank national/regulatory norms."""
    abrogated = _make_article(
        code="BJ-OLD-2001",
        jurisdiction="BJ",
        level="loi",
        status="abrogated",
        score=0.99,
    )
    decret = _make_article(
        code="BJ-DEC-2020",
        jurisdiction="BJ",
        level="decret",
        score=0.80,
    )
    loi = _make_article(
        code="BJ-NUM-2017",
        jurisdiction="BJ",
        level="loi",
        score=0.80,
    )
    uemoa = _make_article(
        code="BCEAO-EME-2015",
        jurisdiction="UEMOA",
        level="reglement",
        score=0.80,
    )

    ranked = apply_normative_ranking([abrogated, decret, loi, uemoa])
    codes = [r.text_code for r in ranked]

    assert "BJ-OLD-2001" not in codes
    assert codes == ["BCEAO-EME-2015", "BJ-NUM-2017", "BJ-DEC-2020"]
    assert ranked[0].normative_rank == 1
    assert ranked[1].normative_rank == 2
    assert ranked[2].normative_rank == 3


def test_detect_normative_conflicts_propagates_to_findings():
    """Conflicting supranational vs national articles trigger conflict_flag & hierarchy details."""
    uemoa_art = _make_article(
        code="BCEAO-EME-2015",
        jurisdiction="UEMOA",
        level="reglement",
        topics=["paiement", "monnaie_electronique"],
        rule_type="mandatory",
    )
    bj_art = _make_article(
        code="BJ-DEC-2022",
        jurisdiction="BJ",
        level="decret",
        topics=["monnaie_electronique"],
        rule_type="prohibition",
    )
    articles_map = {uemoa_art.article_id: uemoa_art, bj_art.article_id: bj_art}

    conflicts = detect_normative_conflicts([uemoa_art, bj_art])
    assert len(conflicts) == 1
    assert conflicts[0]["dominant_code"] == "BCEAO-EME-2015"
    assert conflicts[0]["subordinate_code"] == "BJ-DEC-2022"
    assert "Primauté" in conflicts[0]["hierarchy_rule"]

    normalized = _normalize_findings(
        [
            {
                "facet": "relations_contractuelles_et_fintech",
                "clause_ref": "Module Paiement",
                "finding_text": "Conditions d'émission de monnaie électronique.",
                "verdict": "non_conforme",
                "parade_prouvee": False,
                "risk_level": "eleve",
                "confidence": "high",
                "matched_articles": [str(uemoa_art.article_id), str(bj_art.article_id)],
                "conflict_flag": False,
            }
        ],
        articles_map,
        detected_conflicts=conflicts,
    )
    assert len(normalized) == 1
    assert normalized[0]["conflict_flag"] is True
    assert "BCEAO-EME-2015" in (normalized[0]["conflict_details"] or "")


@pytest.mark.asyncio
async def test_live_hybrid_search_returns_in_force_with_hierarchy_metadata():
    """Live hybrid search returns only in_force texts populated with hierarchy rank/weight."""
    from app.core.database import async_engine
    await async_engine.dispose()
    hits = await hybrid_search_articles(
        "transfert données personnelles hors CEDEAO autorisation APDP",
        jurisdictions=["BJ", "CEDEAO", "UEMOA", "UA"],
        limit=5,
    )
    assert len(hits) > 0
    for hit in hits:
        assert hit.text_status == "in_force"
        assert hit.normative_rank in (1, 2, 3, 4)
        assert hit.normative_weight > 0.0
