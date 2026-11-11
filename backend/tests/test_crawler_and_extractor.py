import pytest
import asyncio
from app.services.crawler import (
    validate_public_https_url,
    score_link_priority,
    is_same_or_subdomain,
)
from app.services.legal_extractor import LegalLLMExtractor

def test_url_ssrf_validation():
    # Public https valid
    validate_public_https_url("https://service.apdp.bj/documentation")
    validate_public_https_url("https://www.bceao.int/fr/lois")

    # Local / Private blocked
    with pytest.raises(ValueError):
        validate_public_https_url("http://localhost:8000")
    with pytest.raises(ValueError):
        validate_public_https_url("https://127.0.0.1")
    with pytest.raises(ValueError):
        validate_public_https_url("https://192.168.1.1/test")
    with pytest.raises(ValueError):
        validate_public_https_url("http://service.apdp.bj")  # non-https

def test_domain_filtering():
    assert is_same_or_subdomain("service.apdp.bj", "apdp.bj") is True
    assert is_same_or_subdomain("apdp.bj", "apdp.bj") is True
    assert is_same_or_subdomain("evil.com", "apdp.bj") is False
    assert is_same_or_subdomain("apdp.bj.attacker.com", "apdp.bj") is False

def test_link_priority_scoring():
    # PDF with legal keyword scores high
    high_score = score_link_priority("https://service.apdp.bj/docs/loi_numerique.pdf", "Télécharger la loi")
    low_score = score_link_priority("https://service.apdp.bj/contact", "Contactez-nous")
    assert high_score > low_score
    assert high_score >= 60

@pytest.mark.asyncio
async def test_legal_extractor_analysis():
    extractor = LegalLLMExtractor()
    sample_legal_text = """
    RÉPUBLIQUE DU BÉNIN
    Loi n° 2017-20 portant Code du numérique en République du Bénin
    Livre V : De la protection des données à caractère personnel
    
    Article 380 : Définition
    Au sens du présent livre, on entend par :
    - Données à caractère personnel : toute information relative à une personne physique identifiée ou identifiable.
    - Responsable de traitement : la personne physique ou morale, publique ou privée, qui détermine les finalités et les moyens du traitement.
    
    Article 384 : Consentement
    Le traitement des données à caractère personnel ne peut être effectué que si la personne concernée a indubitablement donné son consentement.
    Tout manquement est passible d'une amende administrative de 10 000 000 à 100 000 000 de francs CFA.
    """
    
    result = await extractor.analyze_document(sample_legal_text, "loi_2017_20_benin.pdf")
    assert result.is_legal_norm is True
    assert "2017-20" in result.official_title or "2017-20" in (result.act_number or "")
    assert len(result.legal_terms) > 0
    assert len(result.key_articles) > 0

def test_crawler_filename_deduplication():
    from app.services.crawler import LegalCrawlerEngine
    # Setup crawler with known existing filenames for the parent source
    known_filenames = {"code_du_numerique_2017.pdf", "decret_apdp_2019.pdf"}
    crawler = LegalCrawlerEngine(
        root_url="https://service.apdp.bj/",
        max_depth=2,
        existing_filenames=known_filenames,
    )
    # Check that filename comparison is case-insensitive
    assert "code_du_numerique_2017.pdf" in crawler.existing_filenames
    assert "CODE_DU_NUMERIQUE_2017.PDF".lower() in crawler.existing_filenames
    # A new PDF should NOT be in existing_filenames
    assert "nouvelle_decision_2026.pdf" not in crawler.existing_filenames
