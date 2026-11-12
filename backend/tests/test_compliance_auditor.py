"""Automated Phase 5 tests: 4-facet Article-RAG, multi-doc mitigation ('parade'), and fail-safe."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest

from app.core.database import async_engine, async_session_maker
from app.models.document import Document, DocumentAnalysis, DocumentExtraction, DocumentStatus
from app.models.legal import ConfidenceLevel, ReportVersion, RiskFinding, RiskLevel
from app.models.user import Organization, Project
from app.schemas.legal import MatchedArticleDetail, RiskFindingRead
from app.services.compliance_auditor import (
    DocumentEvidence,
    FacetSignal,
    ProjectDossier,
    _normalize_findings,
    evaluate_project_compliance,
    format_dossier_for_prompt,
    load_project_dossier,
    persist_audit_report_version,
    retrieve_articles_for_facets,
    run_holistic_compliance_audit,
)
from app.services.llm_client import LLMClient


class ScriptedAuditLLM(LLMClient):
    """Deterministic LLM double simulating 4-facet extraction and parade-aware evaluation."""

    def __init__(self, *, simulate_optimistic_hallucination: bool = False) -> None:
        self.simulate_optimistic_hallucination = simulate_optimistic_hallucination
        self.prompts_seen: list[str] = []

    async def chat_completion(self, prompt: str, response_format: str | None = None, **kwargs) -> str:
        self.prompts_seen.append(prompt)

        # Call 1: 4-Facet Deconstruction
        if "décompose-le en facettes réglementaires" in prompt:
            return json.dumps(
                {
                    "items": [
                        {
                            "facet": "donnees_manipulees",
                            "summary": "Traitement de dossiers médicaux patients (données de santé sensibles).",
                            "rag_query": "données de santé sensibles traitement interdiction exception consentement",
                            "source_docs": ["architecture.md"],
                        },
                        {
                            "facet": "flux_et_architecture",
                            "summary": "Hébergement des données sur AWS Paris (hors du Bénin / CEDEAO).",
                            "rag_query": "transfert données personnelles vers Etat tiers étranger APDP autorisation",
                            "source_docs": ["architecture.md"],
                        },
                        {
                            "facet": "securite_et_droits",
                            "summary": "Désignation d'un DPO et notification de violation de données.",
                            "rag_query": "délégué protection données DPO notification violation sécurité",
                            "source_docs": ["architecture.md"],
                        },
                        {
                            "facet": "relations_contractuelles_et_fintech",
                            "summary": "Encaissement par Mobile Money (MTN/Moov) sans mention d'agrément BCEAO.",
                            "rag_query": "monnaie électronique paiement BCEAO agrément établissement",
                            "source_docs": ["architecture.md"],
                        },
                    ]
                },
                ensure_ascii=False,
            )

        # Call 2: Holistic Multi-Document Evaluation
        has_apdp_parade = (
            "APDP-BJ-2026-8841" in prompt
            and "consentement exprès et éclairé" in prompt
        )

        # Pick first real BJ-NUM-2017 Article 391 UUID from prompt catalog if present
        import re
        match_391 = re.search(r"\[([0-9a-f-]{36})\]\s+BJ-NUM-2017[^\n]*Article 391\b", prompt)
        art_391_uuid = match_391.group(1) if match_391 else None
        any_uuids = re.findall(r"\[([0-9a-f-]{36})\]", prompt)

        if self.simulate_optimistic_hallucination:
            # Simulates an over-optimistic LLM trying to mark unmitigated cloud transfer "conforme"
            return json.dumps(
                {
                    "findings": [
                        {
                            "clause_ref": "architecture.md — Hébergement AWS Paris",
                            "facet": "flux_et_architecture",
                            "finding_text": "Données patients hébergées à Paris hors du Bénin.",
                            "verdict": "conforme",
                            "parade_prouvee": False,
                            "parade_detectee": "Aucune parade d'annulation détectée dans les documents du projet.",
                            "risk_level": "conforme",
                            "confidence": "medium",
                            "matched_articles": [art_391_uuid] if art_391_uuid else any_uuids[:1],
                            "recommendation": "RAS.",
                        }
                    ]
                },
                ensure_ascii=False,
            )

        findings = [
            {
                "clause_ref": "architecture.md — Transfert hors Bénin (AWS Paris)",
                "facet": "flux_et_architecture",
                "finding_text": "Les données médicales sont stockées sur AWS eu-west-3 (Paris, hors CEDEAO).",
                "verdict": "conforme" if has_apdp_parade else "non_conforme",
                "parade_prouvee": has_apdp_parade,
                "parade_detectee": (
                    "Parade détectée dans politique_confidentialite.md : référence d'autorisation APDP n° APDP-BJ-2026-8841 et clause de consentement exprès et éclairé."
                    if has_apdp_parade
                    else "Aucune parade d'annulation détectée dans les documents du projet."
                ),
                "risk_level": "conforme" if has_apdp_parade else "critique",
                "confidence": "high",
                "matched_articles": [art_391_uuid] if art_391_uuid else any_uuids[:1],
                "article_refs": [{"text_code": "BJ-NUM-2017", "article_number": "Article 391"}],
                "recommendation": (
                    "Conserver le récépissé APDP-BJ-2026-8841 et les journaux de consentement dans le dossier d'audit."
                    if has_apdp_parade
                    else "Solliciter une autorisation préalable de l'APDP Bénin et recueillir un consentement exprès ou relocaliser au Bénin."
                ),
            },
            {
                "clause_ref": "architecture.md — Paiement Mobile Money",
                "facet": "relations_contractuelles_et_fintech",
                "finding_text": "Le module fintech encaisse via Mobile Money sans justificatif de partenariat PSFP / Établissement de Monnaie Électronique.",
                "verdict": "non_conforme",
                "parade_prouvee": False,
                "parade_detectee": "Aucune parade d'annulation détectée dans les documents du projet.",
                "risk_level": "eleve",
                "confidence": "high",
                "matched_articles": any_uuids[1:2] if len(any_uuids) > 1 else any_uuids[:1],
                "recommendation": "Fournir le contrat d'agrégation ou l'agrément BCEAO du partenaire de paiement.",
            },
        ]
        return json.dumps({"findings": findings}, ensure_ascii=False)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 3072 for _ in texts]


@pytest.mark.asyncio(loop_scope="module")
async def test_four_facet_article_rag_retrieval_against_live_corpus():
    """Verify real 2,142-article PostgreSQL hybrid search returns canonical Benin/ECOWAS articles."""
    await async_engine.dispose()
    dossier = ProjectDossier(
        project_id=uuid4(),
        project_name="SantePay BJ",
        country_code="BJ",
        sector="healthtech",
        project_treatments=["hébergement données de santé", "mobile money"],
        documents=[
            DocumentEvidence(
                document_id=uuid4(),
                filename="architecture.md",
                doc_type="technique",
                markdown="Stockage dossiers patients sur AWS Paris et paiement Mobile Money.",
            )
        ],
    )
    llm = ScriptedAuditLLM()
    from app.services.compliance_auditor import deconstruct_project_facets

    facets = await deconstruct_project_facets(dossier, llm)
    assert {f.facet for f in facets} == {
        "donnees_manipulees",
        "flux_et_architecture",
        "securite_et_droits",
        "relations_contractuelles_et_fintech",
    }

    articles_map, facet_ids = await retrieve_articles_for_facets(dossier, facets, limit_per_facet=4)
    assert len(articles_map) >= 4
    article_labels = {(a.text_code, a.article_number) for a in articles_map.values()}
    assert ("BJ-NUM-2017", "Article 391") in article_labels
    assert facet_ids["flux_et_architecture"]


@pytest.mark.asyncio(loop_scope="module")
async def test_precautionary_failsafe_blocks_unmitigated_conforme():
    """Precautionary rule: never leave risk_level='conforme' if no parade is proven."""
    dossier = ProjectDossier(
        project_id=uuid4(),
        project_name="Fintech BJ",
        country_code="BJ",
        sector="fintech",
        project_treatments=["transfert cloud"],
        documents=[
            DocumentEvidence(
                document_id=uuid4(),
                filename="architecture.md",
                doc_type="technique",
                markdown="Hébergement sur AWS Paris.",
            )
        ],
    )
    facets = [
        FacetSignal(
            facet="flux_et_architecture",
            summary="Hébergement hors Bénin.",
            rag_query="transfert données à caractère personnel vers un Etat tiers APDP",
        )
    ]
    articles_map, _ = await retrieve_articles_for_facets(dossier, facets, limit_per_facet=3)
    optimistic_llm = ScriptedAuditLLM(simulate_optimistic_hallucination=True)

    findings = await evaluate_project_compliance(dossier, facets, articles_map, optimistic_llm)
    assert len(findings) == 1
    f = findings[0]
    assert f["parade_prouvee"] is False
    # Over-optimistic 'conforme' must be escalated under precautionary principle
    assert f["risk_level"] != RiskLevel.CONFORME
    assert f["verdict"] != "conforme"
    assert len(f["matched_articles"]) >= 1
    assert all(isinstance(uid, UUID) and uid in articles_map for uid in f["matched_articles"])


def test_normalize_findings_rejects_hallucinated_uuids_and_resolves_text_refs():
    """Hallucinated UUIDs are dropped; valid (text_code, article_number) refs resolve to real UUIDs."""
    from app.services.article_rag import ArticleSearchResult

    real_id = uuid4()
    fake_id = uuid4()
    articles_map = {
        real_id: ArticleSearchResult(
            article_id=real_id,
            text_id=uuid4(),
            text_code="BJ-NUM-2017",
            text_title="Code du Numérique du Bénin",
            jurisdiction="BJ",
            authority="APDP",
            section_breadcrumb="Livre V > Chapitre IV",
            article_number="Article 391",
            title="Transfert vers un État tiers",
            full_text="Le responsable du traitement ne peut transférer de données que si l'État assure un niveau suffisant.",
            topics=["transfert"],
            actors=["responsable_traitement"],
            has_sanction=True,
            sanction_details="Sanction pécuniaire et administrative APDP",
            compliance_rule_type="autorisation_prealable",
            dense_score=0.71,
            bm25_score=0.45,
            score=0.62,
        )
    }
    normalized = _normalize_findings(
        [
            {
                "clause_ref": "Doc 1 — Cloud",
                "facet": "flux_et_architecture",
                "finding_text": "Transfert vers cloud étranger sans mention APDP.",
                "parade_prouvee": False,
                "parade_detectee": "Aucune parade identifiée.",
                "risk_level": "critique",
                "confidence": "high",
                "matched_articles": [str(fake_id)],
                "article_refs": [{"text_code": "BJ-NUM-2017", "article_number": "Article 391"}],
                "recommendation": "Déposer une demande d'autorisation APDP.",
            }
        ],
        articles_map,
    )
    assert normalized[0]["matched_articles"] == [real_id]
    assert "BJ-NUM-2017 — Article 391" in normalized[0]["finding_text"]


@pytest.mark.asyncio(loop_scope="module")
async def test_holistic_multi_doc_parade_prevents_false_positive_and_persists():
    """End-to-end DB test: Doc 1 + Doc 2 (APDP parade) avoids false positive and persists matched_articles."""
    llm = ScriptedAuditLLM()

    async with async_session_maker() as session:
        org = Organization(name=f"Test Org Audit {uuid4().hex[:8]}", country_code="BJ", sector="healthtech")
        session.add(org)
        await session.flush()

        project = Project(
            org_id=org.id,
            name="E-Santé Bénin Audit Test",
            country_code="BJ",
            sector="healthtech",
            treatments=["dossier_medical", "mobile_money"],
        )
        session.add(project)
        await session.flush()

        doc1 = Document(
            project_id=project.id,
            filename="architecture.md",
            document_type="architecture",
            mime_type="text/markdown",
            minio_bucket="test",
            minio_object=f"test/{uuid4()}.md",
            size_bytes=120,
            status=DocumentStatus.EXTRACTED,
        )
        doc2 = Document(
            project_id=project.id,
            filename="politique_confidentialite.md",
            document_type="politique",
            mime_type="text/markdown",
            minio_bucket="test",
            minio_object=f"test/{uuid4()}.md",
            size_bytes=220,
            status=DocumentStatus.EXTRACTED,
        )
        session.add(doc1)
        session.add(doc2)
        await session.flush()

        ext1 = DocumentExtraction(
            document_id=doc1.id,
            markdown="Les données médicales des patients sont hébergées sur AWS Paris (eu-west-3) et payées par Mobile Money.",
            quality_score=0.95,
            page_count=2,
        )
        ext2 = DocumentExtraction(
            document_id=doc2.id,
            markdown="Parade légale : Transfert encadré par autorisation APDP n° APDP-BJ-2026-8841 et consentement exprès et éclairé du patient avant envoi.",
            quality_score=0.98,
            page_count=3,
        )
        session.add(ext1)
        session.add(ext2)
        await session.flush()

        ana1 = DocumentAnalysis(
            extraction_id=ext1.id,
            entities={"data_types": ["santé"], "locations": ["Paris"]},
            vague_zones=[{"clause_ref": "hébergement", "description": "Localisation AWS Paris", "suggested_fields": ["autorisation APDP"]}],
        )
        ana2 = DocumentAnalysis(
            extraction_id=ext2.id,
            entities={"authorizations": ["APDP-BJ-2026-8841"]},
            vague_zones=[],
        )
        session.add(ana1)
        session.add(ana2)
        await session.commit()

        report_id = None
        try:
            # Verify load_project_dossier gathers BOTH documents together
            dossier = await load_project_dossier(session, project.id)
            assert [d.filename for d in dossier.documents] == ["architecture.md", "politique_confidentialite.md"]
            prompt_blob = format_dossier_for_prompt(dossier)
            assert "APDP-BJ-2026-8841" in prompt_blob
            assert "AWS Paris" in prompt_blob

            audit_result = await run_holistic_compliance_audit(
                session,
                project.id,
                llm_client=llm,
            )
            assert len(audit_result.findings) == 2

            # AWS Paris finding is mitigated by Doc 2's APDP authorization & explicit consent
            transfer_finding = next(f for f in audit_result.findings if f["facet"] == "flux_et_architecture")
            assert transfer_finding["parade_prouvee"] is True
            assert transfer_finding["risk_level"] == RiskLevel.CONFORME
            assert len(transfer_finding["matched_articles"]) >= 1

            # Fintech Mobile Money lacks any proof across both docs -> flagged eleve
            fintech_finding = next(f for f in audit_result.findings if f["facet"] == "relations_contractuelles_et_fintech")
            assert fintech_finding["parade_prouvee"] is False
            assert fintech_finding["risk_level"] == RiskLevel.ELEVE

            # Persist ReportVersion + RiskFindings and verify schema hydration
            report = await persist_audit_report_version(session, project.id, audit_result, version="1.0")
            report_id = report.id

            from sqlmodel import select
            saved_findings = (
                await session.execute(select(RiskFinding).where(RiskFinding.report_version_id == report.id))
            ).scalars().all()
            assert len(saved_findings) == 2
            assert all(len(sf.matched_articles) >= 1 for sf in saved_findings)

            # Validate RiskFindingRead + MatchedArticleDetail serialization
            read_item = RiskFindingRead.model_validate(saved_findings[0])
            assert len(read_item.matched_articles) >= 1
            art0 = audit_result.articles_map[read_item.matched_articles[0]]
            detail = MatchedArticleDetail(
                id=art0.article_id,
                text_code=art0.text_code,
                text_title=art0.text_title,
                jurisdiction=art0.jurisdiction,
                authority=art0.authority,
                article_number=art0.article_number,
                title=art0.title,
                section_breadcrumb=art0.section_breadcrumb,
                full_text=art0.full_text,
                has_sanction=art0.has_sanction,
                sanction_details=art0.sanction_details,
                compliance_rule_type=art0.compliance_rule_type,
            )
            assert detail.text_code == "BJ-NUM-2017"
            assert "APDP-BJ-2026-8841" in audit_result.report1_markdown
            assert "Article 391" in audit_result.report2_markdown
        finally:
            # Clean temporary test entities so the database stays clean
            from sqlalchemy import delete
            if report_id is not None:
                await session.execute(delete(RiskFinding).where(RiskFinding.report_version_id == report_id))
                await session.execute(delete(ReportVersion).where(ReportVersion.id == report_id))
            await session.execute(delete(DocumentAnalysis).where(DocumentAnalysis.extraction_id.in_([ext1.id, ext2.id])))
            await session.execute(delete(DocumentExtraction).where(DocumentExtraction.document_id.in_([doc1.id, doc2.id])))
            await session.execute(delete(Document).where(Document.project_id == project.id))
            await session.execute(delete(Project).where(Project.id == project.id))
            await session.execute(delete(Organization).where(Organization.id == org.id))
            await session.commit()
    await async_engine.dispose()
