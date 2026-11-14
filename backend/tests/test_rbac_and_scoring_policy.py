"""Tests for Platform Admin workspace prohibition and rule-calibrated scoring policy."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.core.database import async_engine, async_session_maker
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.admin import ScoringRule
from app.models.corpus import ComplianceRuleType, LegalArticle
from app.models.legal import ConfidenceLevel, RiskLevel
from app.models.user import Organization, User, UserRole
from app.services.compliance_auditor import (
    compute_initial_severity_and_score,
    resolve_applicable_scoring_rule,
)


@pytest.mark.asyncio(loop_scope="module")
async def test_platform_admin_forbidden_from_user_workspace_endpoints():
    """Platform admin cannot create, list or access user projects/documents/reports."""
    await async_engine.dispose()

    # 1. Ensure a platform admin and a regular user exist
    async with async_session_maker() as session:
        admin_user = (
            await session.execute(
                select(User).where(User.is_active.is_(True), User.role == UserRole.PLATFORM_ADMIN)
            )
        ).scalars().first()
        if not admin_user:
            admin_user = User(
                email=f"admin_test_{uuid4().hex[:6]}@example.org",
                hashed_password=get_password_hash("AdminPass123!"),
                role=UserRole.PLATFORM_ADMIN,
                is_active=True,
                is_superuser=True,
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)

    admin_token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role.value})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Platform admin attempting to access user project endpoints
        res_list = await client.get("/api/projects", headers=admin_headers)
        assert res_list.status_code == 403
        assert "administrateurs plateforme" in res_list.json()["detail"].lower()

        res_create = await client.post(
            "/api/projects",
            json={"name": "Forbidden Project", "country_code": "BJ", "sector": "fintech"},
            headers=admin_headers,
        )
        assert res_create.status_code == 403

        fake_proj_id = uuid4()
        res_reports = await client.get(
            f"/api/reports/projects/{fake_proj_id}",
            headers=admin_headers,
        )
        assert res_reports.status_code == 403


@pytest.mark.asyncio
async def test_calibrated_scoring_policy_with_sanctions_and_precaution():
    """Scoring respects rule weights, penalizes sanctioned articles, and enforces fail-safe."""
    rule_bj = ScoringRule(
        name="Test BJ Rule",
        domain="data_protection",
        country_code="BJ",
        weight_critique=1.2,
        weight_eleve=0.85,
        weight_modere=0.45,
        weight_a_surveiller=0.15,
        weight_conforme=0.0,
        confidence_threshold_high=0.8,
        confidence_threshold_medium=0.5,
    )

    art_penal_id = uuid4()
    art_penal = LegalArticle(
        id=art_penal_id,
        section_id=uuid4(),
        article_number="ART-418",
        full_text="Est puni d'un emprisonnement de 2 ans quiconque...",
        has_sanction=True,
        sanction_details="Sanction pénale : emprisonnement de 2 ans et amende",
        compliance_rule_type=ComplianceRuleType.SANCTION.value,
    )
    articles_map = {art_penal_id: art_penal}

    # 1. All conforme findings -> score 0
    conforme_findings = [
        {"risk_level": RiskLevel.CONFORME, "confidence": ConfidenceLevel.HIGH, "matched_articles": []},
        {"risk_level": RiskLevel.CONFORME, "confidence": ConfidenceLevel.HIGH, "matched_articles": []},
    ]
    _, score_conforme, conf_conforme = compute_initial_severity_and_score(
        conforme_findings,
        rule=rule_bj,
        articles_map=articles_map,
    )
    assert score_conforme == 0
    assert conf_conforme == ConfidenceLevel.HIGH

    # 2. Critical breach on sanctioned article -> includes weight_critique (1.2*25=30) + penal penalty (8) = 38,
    # but precautionary fail-safe elevates it to minimum 50!
    critical_findings = [
        {
            "risk_level": RiskLevel.CRITIQUE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [art_penal_id],
        }
    ]
    _, score_critique, _ = compute_initial_severity_and_score(
        critical_findings,
        rule=rule_bj,
        articles_map=articles_map,
    )
    assert score_critique >= 50, f"Expected precautionary score >= 50, got {score_critique}"

    # 3. High + moderate breaches on sanctioned articles without critical -> base weights + sanction bonus
    mixed_findings = [
        {
            "risk_level": RiskLevel.ELEVE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [art_penal_id],  # +8 penal
        },
        {
            "risk_level": RiskLevel.MODERE,
            "confidence": ConfidenceLevel.MEDIUM,
            "matched_articles": [],
        },
    ]
    # base: 0.85*20 = 17 + 0.45*12 = 5.4 -> 22.4 + 8 = 30.4 -> 30
    _, score_mixed, _ = compute_initial_severity_and_score(
        mixed_findings,
        rule=rule_bj,
        articles_map=articles_map,
    )
    assert 25 <= score_mixed <= 45


@pytest.mark.asyncio(loop_scope="module")
async def test_resolve_applicable_scoring_rule_prefers_jurisdiction():
    """Specific country rule takes precedence over global rule for a country project."""
    await async_engine.dispose()
    async with async_session_maker() as session:
        rule_bj = await resolve_applicable_scoring_rule(
            session,
            country_code="BJ",
            sector="fintech",
            treatments=["data_protection", "biometrie"],
        )
        assert rule_bj is not None
        assert rule_bj.country_code == "BJ"

        rule_global = await resolve_applicable_scoring_rule(
            session,
            country_code="SN",  # Senegal (no specific SN rule seeded -> fallback to global/domain)
            sector="fintech",
            treatments=["payment_services"],
        )
        assert rule_global is not None
        assert rule_global.domain in ("payment_services", "global")


@pytest.mark.asyncio
async def test_diminishing_returns_unique_sanction_and_compression():
    """Verify domain diminishing returns, unique-article sanction cap, and compression > 70."""
    rule_default = ScoringRule(
        name="Default Stabilized",
        domain="global",
        country_code=None,
        weight_critique=1.0,
        weight_eleve=1.0,
        weight_modere=1.0,
        weight_a_surveiller=1.0,
        weight_conforme=0.0,
        confidence_threshold_high=0.8,
        confidence_threshold_medium=0.5,
    )

    art_penal_id = uuid4()
    art_penal = LegalArticle(
        id=art_penal_id,
        section_id=uuid4(),
        article_number="ART-418",
        full_text="Sanction pénale.",
        has_sanction=True,
        sanction_details="Sanction pénale : emprisonnement",
        compliance_rule_type=ComplianceRuleType.SANCTION.value,
    )
    articles_map = {art_penal_id: art_penal}

    # 1. Splitting into two ELEVE findings in the SAME domain should apply 1.0 + 0.5 = 1.5x (30 pts), not 2.0x (40 pts)
    same_domain_split = [
        {
            "facet": "donnees_manipulees",
            "risk_level": RiskLevel.ELEVE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [],
        },
        {
            "facet": "donnees_manipulees",
            "risk_level": RiskLevel.ELEVE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [],
        },
    ]
    _, score_same_domain, _ = compute_initial_severity_and_score(
        same_domain_split,
        rule=rule_default,
        articles_map=articles_map,
    )
    assert score_same_domain == 30

    # 2. Same two ELEVE findings in DIFFERENT domains should apply 1.0 + 1.0 = 40 pts
    diff_domain_split = [
        {
            "facet": "donnees_manipulees",
            "risk_level": RiskLevel.ELEVE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [],
        },
        {
            "facet": "flux_et_architecture",
            "risk_level": RiskLevel.ELEVE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [],
        },
    ]
    _, score_diff_domain, _ = compute_initial_severity_and_score(
        diff_domain_split,
        rule=rule_default,
        articles_map=articles_map,
    )
    assert score_diff_domain == 40
    assert score_same_domain < score_diff_domain

    # 3. Citing the same sanctioned article in two different findings must count the +8 penalty only once
    duplicated_sanction = [
        {
            "facet": "donnees_manipulees",
            "risk_level": RiskLevel.ELEVE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [art_penal_id],
        },
        {
            "facet": "flux_et_architecture",
            "risk_level": RiskLevel.ELEVE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [art_penal_id],
        },
    ]
    _, score_dedup_sanction, _ = compute_initial_severity_and_score(
        duplicated_sanction,
        rule=rule_default,
        articles_map=articles_map,
    )
    # 20 + 20 + 8 (counted once, not 16) = 48
    assert score_dedup_sanction == 48

    # 4. Three CRITIQUE findings across 3 distinct domains + penal sanction = raw 83 -> compressed strictly < 100 (70 + 30*(1-exp(-13/45)) ~ 78)
    three_criticals = [
        {
            "facet": "donnees_manipulees",
            "risk_level": RiskLevel.CRITIQUE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [art_penal_id],
        },
        {
            "facet": "flux_et_architecture",
            "risk_level": RiskLevel.CRITIQUE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [],
        },
        {
            "facet": "securite_et_droits",
            "risk_level": RiskLevel.CRITIQUE,
            "confidence": ConfidenceLevel.HIGH,
            "matched_articles": [],
        },
    ]
    _, score_three_crit, _ = compute_initial_severity_and_score(
        three_criticals,
        rule=rule_default,
        articles_map=articles_map,
    )
    assert 75 <= score_three_crit < 85, f"Expected compressed score in [75, 85), got {score_three_crit}"
