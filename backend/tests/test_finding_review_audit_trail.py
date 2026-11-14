"""Tests for Phase 4: Finding legal_nature qualification, human review API, and inter-version lock."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.core.database import async_engine, async_session_maker
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.legal import ConfidenceLevel, ReportVersion, RiskFinding, RiskLevel
from app.models.user import Organization, Project, User, UserRole
from app.services.compliance_auditor import (
    AuditExecutionResult,
    ProjectDossier,
    persist_audit_report_version,
)


@pytest.mark.asyncio(loop_scope="module")
async def test_finding_review_api_and_inter_version_preservation():
    """Human review status/note is persisted via API and preserved across report regeneration."""
    await async_engine.dispose()

    async with async_session_maker() as session:
        org = Organization(name=f"AuditOrg_{uuid4().hex[:6]}")
        session.add(org)
        await session.flush()

        user = User(
            email=f"jurist_{uuid4().hex[:6]}@example.org",
            hashed_password=get_password_hash("JuristPass123!"),
            role=UserRole.ANALYST,
            org_id=org.id,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        project = Project(
            name="Audit Trail Test Project",
            country_code="BJ",
            sector="fintech",
            represented_entity_type="entreprise",
            org_id=org.id,
        )
        session.add(project)
        await session.flush()

        rv1 = ReportVersion(
            project_id=project.id,
            version="1.0",
            global_score=55,
            confidence_global=ConfidenceLevel.HIGH,
            severity_counts={"critique": 1},
            report1_markdown="# R1",
            report2_markdown="# R2",
        )
        session.add(rv1)
        await session.flush()

        finding1 = RiskFinding(
            report_version_id=rv1.id,
            clause_ref="Transfert Cloud AWS",
            finding_text="Hébergement hors CEDEAO sans preuve APDP.",
            risk_level=RiskLevel.CRITIQUE,
            confidence=ConfidenceLevel.HIGH,
            matched_articles=[],
            recommendation="Fournir l'autorisation APDP.",
        )
        session.add(finding1)
        await session.commit()
        await session.refresh(finding1)

        user_id = user.id
        project_id = project.id
        rv1_id = rv1.id
        finding1_id = finding1.id
        role_val = user.role.value

    token = create_access_token(data={"sub": str(user_id), "role": role_val})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/reports/findings/{finding1_id}/review",
            json={
                "review_status": "mitigated_by_evidence",
                "legal_nature": "risque_contractuel",
                "review_note": "Récépissé APDP n°2026-042 vérifié en annexe.",
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["review_status"] == "mitigated_by_evidence"
        assert data["legal_nature"] == "risque_contractuel"
        assert data["review_note"] == "Récépissé APDP n°2026-042 vérifié en annexe."
        assert data["reviewed_by"] == str(user_id)
        assert data["reviewed_at"] is not None

    # Regenerate v2.0 with parent_version_id=rv1_id and verify lock preservation
    async with async_session_maker() as session:
        dummy_dossier = ProjectDossier(
            project_id=project_id,
            project_name="Audit Trail Test Project",
            country_code="BJ",
            sector="fintech",
            project_treatments=[],
            documents=[],
        )
        audit_result = AuditExecutionResult(
            dossier=dummy_dossier,
            facets=[],
            articles_map={},
            findings=[
                {
                    "clause_ref": "Transfert Cloud AWS",
                    "finding_text": "Hébergement hors CEDEAO.",
                    "risk_level": RiskLevel.MODERE,
                    "confidence": ConfidenceLevel.HIGH,
                    "matched_sources": [],
                    "matched_articles": [],
                    "obsolescence_flag": False,
                    "conflict_flag": False,
                    "conflict_details": None,
                    "legal_nature": "non_conformite_imperative",
                    "recommendation": "Maintenir la preuve.",
                }
            ],
            report1_markdown="# R1 v2",
            report2_markdown="# R2 v2",
        )
        rv2 = await persist_audit_report_version(
            session,
            project_id,
            audit_result,
            version="2.0",
            parent_version_id=rv1_id,
        )
        findings_v2 = (
            await session.execute(
                select(RiskFinding).where(RiskFinding.report_version_id == rv2.id)
            )
        ).scalars().all()
        assert len(findings_v2) == 1
        f2 = findings_v2[0]
        assert f2.review_status == "mitigated_by_evidence"
        assert f2.legal_nature == "risque_contractuel"
        assert f2.review_note == "Récépissé APDP n°2026-042 vérifié en annexe."
        assert f2.reviewed_by == user_id
        assert f2.reviewed_at is not None
