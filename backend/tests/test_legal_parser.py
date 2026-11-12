"""Unit tests for the deterministic legal parser and baseline compliance signal extraction."""

from pathlib import Path

from app.models.corpus import ComplianceRuleType
from app.services.legal_parser import (
    MASTER_CORPUS_CATALOG,
    load_master_text_file,
    parse_legal_text,
)
from app.services.legal_tagger import extract_deterministic_signals

CORPUS_DIR = Path(__file__).resolve().parents[1] / "corpus_sources"
CATALOG_BY_CODE = {item.code: item for item in MASTER_CORPUS_CATALOG}


def test_parse_benin_code_numerique_lossless():
    meta = CATALOG_BY_CODE["BJ-NUM-2017"]
    raw = load_master_text_file(CORPUS_DIR, meta)
    parsed = parse_legal_text(raw, meta)

    assert len(parsed.sections) >= 130
    assert len(parsed.articles) >= 640

    by_num = {a.article_number: a for a in parsed.articles}
    for required in ("Article 1er", "Article 121", "Article 247", "Article 418", "Article 499", "Article 550", "Article 647"):
        assert required in by_num, f"Missing {required} in parsed Code du Numérique"
        assert len(by_num[required].full_text) >= 40

    # Ensure Table of Contents dotted lines were excluded
    for art in parsed.articles:
        assert "........" not in art.full_text
        assert len(art.full_text) >= 25

    art418 = by_num["Article 418"]
    sec = next((s for s in parsed.sections if s.order_index == art418.section_order_index), None)
    assert sec is not None
    assert "LIVRE CINQUIEME" in sec.breadcrumb.upper()


def test_parse_benin_amending_law_keeps_quoted_articles_inside_article_1er():
    meta = CATALOG_BY_CODE["BJ-NUM-2021"]
    raw = load_master_text_file(CORPUS_DIR, meta)
    parsed = parse_legal_text(raw, meta)

    assert [a.article_number for a in parsed.articles] == [
        "Article 1er",
        "Article 2",
        "Article 3",
        "Article 4",
    ]
    assert "Article 121 nouveau" in parsed.articles[0].full_text
    assert "Article 464 nouveau" in parsed.articles[0].full_text


def test_parse_regional_acts_exact_article_counts():
    ced_dat = parse_legal_text(load_master_text_file(CORPUS_DIR, CATALOG_BY_CODE["CED-DAT-2010"]), CATALOG_BY_CODE["CED-DAT-2010"])
    assert len(ced_dat.articles) == 49
    assert ced_dat.articles[0].article_number == "Article 1er"
    assert ced_dat.articles[-1].article_number == "Article 49"

    ced_tra = parse_legal_text(load_master_text_file(CORPUS_DIR, CATALOG_BY_CODE["CED-TRA-2010"]), CATALOG_BY_CODE["CED-TRA-2010"])
    assert len(ced_tra.articles) == 41
    assert any(a.article_number == "Article 37" for a in ced_tra.articles)

    ced_cyb = parse_legal_text(load_master_text_file(CORPUS_DIR, CATALOG_BY_CODE["CED-CYB-2011"]), CATALOG_BY_CODE["CED-CYB-2011"])
    assert len(ced_cyb.articles) == 35

    ua_mal = parse_legal_text(load_master_text_file(CORPUS_DIR, CATALOG_BY_CODE["UA-MAL-2014"]), CATALOG_BY_CODE["UA-MAL-2014"])
    assert len(ua_mal.articles) == 38
    assert any(a.article_number == "Article 31" for a in ua_mal.articles)


def test_deterministic_sanction_and_rule_type_extraction():
    sig = extract_deterministic_signals(
        "Quiconque accède frauduleusement à un système informatique est puni d'un emprisonnement "
        "de six mois à deux ans et d'une amende de 2 000 000 à 10 000 000 francs CFA."
    )
    assert sig["has_sanction"] is True
    assert "2 000 000" in (sig["sanction_details"] or "")
    assert sig["compliance_rule_type"] == ComplianceRuleType.SANCTION.value

    cond = extract_deterministic_signals(
        "Le transfert de données vers un pays tiers est soumis à l'autorisation préalable de l'APDP."
    )
    assert cond["has_sanction"] is False
    assert cond["compliance_rule_type"] == ComplianceRuleType.CONDITIONAL.value
