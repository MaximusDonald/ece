"""Tests for stored complementary context document and prompt inclusion with prior report."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.database import async_engine, async_session_maker
from app.models.document import DocumentStatus
from app.models.legal import ConfidenceLevel, ReportVersion, RiskFinding, RiskLevel
from app.models.user import Organization, Project
from app.services.compliance_auditor import format_dossier_for_prompt, load_project_dossier
from app.services.context_document import (
    CONTEXT_DOC_FILENAME,
    CONTEXT_DOC_TYPE,
    get_context_document,
    upsert_context_document,
)


@pytest.mark.asyncio(loop_scope="module")
async def test_context_document_upsert_edit_and_prompt_inclusion():
    await async_engine.dispose()
    async with async_session_maker() as session:
        org = Organization(name=f"Context Org {uuid4().hex[:6]}")
        session.add(org)
        await session.flush()

        project = Project(
            org_id=org.id,
            name="Projet Contexte",
            country_code="BJ",
            sector="Finance",
        )
        session.add(project)
        await session.flush()

        # Previous report version with a finding
        prev_report = ReportVersion(
            project_id=project.id,
            version="1.0",
            global_score=62,
            confidence_global=ConfidenceLevel.MEDIUM,
            severity_counts={"eleve": 1},
            report1_markdown="# R1",
            report2_markdown="# R2",
        )
        session.add(prev_report)
        await session.flush()

        session.add(
            RiskFinding(
                report_version_id=prev_report.id,
                clause_ref="Art. 5 Hébergement",
                finding_text="Localisation des serveurs non précisée dans le contrat.",
                risk_level=RiskLevel.ELEVE,
                confidence=ConfidenceLevel.MEDIUM,
                recommendation="Préciser le pays d'hébergement.",
            )
        )
        await session.commit()

        # 1. Create context document from structured context_data
        doc, ext, ana = await upsert_context_document(
            session,
            project,
            context_data={
                "vague_zone": "Art. 5 Hébergement",
                "hosting_location": "Cotonou, Bénin (Datacenter SBIN)",
                "subcontractor": "SBIN",
            },
        )
        await session.commit()

        assert doc.document_type == CONTEXT_DOC_TYPE
        assert doc.filename == CONTEXT_DOC_FILENAME
        assert doc.status == DocumentStatus.EXTRACTED
        assert "Cotonou, Bénin" in ext.markdown
        assert len(ana.entities["entries"]) == 1

        # 2. Update markdown directly (simulating user edit in UI)
        updated_md = ext.markdown + "\n- **Certification** : ISO 27001 confirmée\n"
        doc2, ext2, ana2 = await upsert_context_document(
            session,
            project,
            markdown_override=updated_md,
        )
        await session.commit()
        assert doc2.id == doc.id
        assert "ISO 27001 confirmée" in ext2.markdown
        assert "ISO 27001 confirmée" in ana2.entities["raw_markdown"]

        found = await get_context_document(session, project.id)
        assert found is not None
        assert found[0].id == doc.id

        # 3. Verify load_project_dossier + format_dossier_for_prompt include both context & prior report
        dossier = await load_project_dossier(
            session,
            project.id,
            previous_report_id=prev_report.id,
        )
        prompt_text = format_dossier_for_prompt(dossier)

        assert "DOCUMENT DE CONTEXTE COMPLÉMENTAIRE DU PROJET" in prompt_text
        assert "Cotonou, Bénin (Datacenter SBIN)" in prompt_text
        assert "ISO 27001 confirmée" in prompt_text
        assert "ANCIENNE VERSION DU RAPPORT" in prompt_text
        assert "v1.0" in prompt_text
        assert "62/100" in prompt_text
        assert "Art. 5 Hébergement" in prompt_text


def test_project_represented_role_validation_and_prompt():
    from pydantic import ValidationError
    from app.schemas.project import ProjectCreate
    from app.services.compliance_auditor import ProjectDossier

    with pytest.raises(ValidationError):
        ProjectCreate(
            name="Test",
            country_code="BJ",
            sector="FinTech",
            treatments=["data_protection"],
            represented_entity_type="autre",
            represented_entity_other="   ",
        )

    valid = ProjectCreate(
        name="Test",
        country_code="BJ",
        sector="FinTech",
        treatments=["data_protection"],
        represented_entity_type="prestataire_externe",
        represented_role_details="Prestataire technique responsable uniquement de l'hébergement.",
    )
    assert valid.represented_entity_type == "prestataire_externe"

    dossier = ProjectDossier(
        project_id=uuid4(),
        project_name="Test",
        country_code="BJ",
        sector="FinTech",
        project_treatments=["data_protection"],
        documents=[],
        represented_entity_type="autre",
        represented_entity_other="Investisseur institutionnel",
        represented_role_details="Audit pré-investissement",
    )
    prompt_text = format_dossier_for_prompt(dossier)
    assert "Autre : Investisseur institutionnel" in prompt_text
    assert "Audit pré-investissement" in prompt_text
