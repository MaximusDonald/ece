from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import async_session_maker
from app.models import (
    Organization,
    Project,
    ReportVersion,
    RiskFinding,
    LegalText,
    LegalArticle,
    User,
    UserRole,
    RiskLevel,
    ConfidenceLevel,
)
from app.core.security import create_access_token, get_password_hash


@pytest.mark.asyncio(loop_scope="module")
async def test_unified_report_export_and_findings_pydantic_clean():
    from app.core.database import async_engine
    await async_engine.dispose()
    async with async_session_maker() as session:
        # 1. Create org, user, project
        org = Organization(id=uuid.uuid4(), name="Test Org Unified")
        session.add(org)

        user = User(
            id=uuid.uuid4(),
            email=f"analyste_{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=get_password_hash("Secret123!"),
            org_id=org.id,
            role=UserRole.ANALYST,
            is_active=True,
        )
        session.add(user)

        project = Project(
            id=uuid.uuid4(),
            org_id=org.id,
            name="Projet Audit Déploiement IA",
            country_code="CI",
            sector="Banque",
            treatments=["score_credit", "biometrie"],
            status="active",
        )
        session.add(project)

        unique_code = f"TEST-LOI-{uuid.uuid4().hex[:6]}"
        text = LegalText(
            id=uuid.uuid4(),
            country_code="CI",
            code=unique_code,
            title="Loi relative à la protection des données à caractère personnel",
            authority="ARTCI",
            level="loi",
            jurisdiction="nationale",
            status="in_force",
        )
        session.add(text)

        art = LegalArticle(
            id=uuid.uuid4(),
            text_id=text.id,
            article_number="Art. 42",
            title="Obligation de sécurité",
            full_text="Le responsable du traitement met en oeuvre les mesures techniques appropriées.",
            has_sanction=True,
            sanction_details="Sanction pénale de 1 à 5 ans d'emprisonnement et 10.000.000 FCFA d'amende.",
        )
        session.add(art)

        report = ReportVersion(
            id=uuid.uuid4(),
            project_id=project.id,
            version="1.0",
            global_score=78,
            confidence_global=ConfidenceLevel.HIGH,
            report1_markdown="# DIAGNOSTIC SYNTHÉTIQUE\n\nConformité globale acceptable sous réserves.",
            report2_markdown="# EXTRAITS DES TEXTES DE LOI\n\nArt. 42 de la Loi 2013-450.",
            severity_counts={"eleve": 1},
        )
        session.add(report)

        finding = RiskFinding(
            id=uuid.uuid4(),
            report_version_id=report.id,
            clause_ref="Clause 4.2 - Chiffrement",
            finding_text="Absence de chiffrement au repos des données bancaires.",
            risk_level=RiskLevel.ELEVE,
            confidence=ConfidenceLevel.HIGH,
            recommendation="Mettre en oeuvre un chiffrement AES-256.",
            matched_articles=[str(art.id)],
        )
        session.add(finding)
        await session.commit()

        token = create_access_token(
            data={"sub": str(user.id), "org_id": str(org.id), "role": user.role.value}
        )
        report_id = report.id

    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # A. Test findings endpoint (should return 200 with typed MatchedArticleDetail without serializer warning)
        res_findings = await ac.get(f"/api/reports/{report_id}/findings", headers=headers)
        assert res_findings.status_code == 200
        findings_data = res_findings.json()
        assert len(findings_data) == 1
        assert len(findings_data[0]["articles_details"]) == 1
        assert findings_data[0]["articles_details"][0]["article_number"] == "Art. 42"
        assert findings_data[0]["articles_details"][0]["has_sanction"] is True
        assert "Sanction pénale" in findings_data[0]["articles_details"][0]["sanction_details"]

        # B. Test markdown export with type=full (Grand Rapport Unifié)
        res_export_md = await ac.get(
            f"/api/reports/{report_id}/export?format=markdown&type=full", headers=headers
        )
        assert res_export_md.status_code == 200
        md_text = res_export_md.text
        assert "RAPPORT GLOBAL DE CONFORMITÉ RÉGLEMENTAIRE" in md_text
        assert "PROJET AUDIT DÉPLOIEMENT IA" in md_text.upper()
        assert "Art. 42" in md_text
        assert "Absence de chiffrement" in md_text
        assert "Sanction pénale" in md_text

        # C. Test markdown export with type=report1 (rétrocompatibilité)
        res_export_r1 = await ac.get(
            f"/api/reports/{report_id}/export?format=markdown&type=report1", headers=headers
        )
        assert res_export_r1.status_code == 200
        assert "DIAGNOSTIC SYNTHÉTIQUE" in res_export_r1.text

        # D. Test download PDF endpoint with type=full
        res_download = await ac.get(f"/api/reports/{report_id}/download?type=full", headers=headers)
        assert res_download.status_code == 200
        assert res_download.headers["content-type"] == "application/pdf"
        assert len(res_download.content) > 1000
