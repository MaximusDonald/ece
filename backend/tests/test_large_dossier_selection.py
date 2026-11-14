"""Tests for Phase 3: Intelligent passage selection on large documents (>100k chars)."""

from __future__ import annotations

from uuid import uuid4

from app.services.compliance_auditor import (
    DocumentEvidence,
    ProjectDossier,
    _select_relevant_document_passages,
    format_dossier_for_prompt,
)


def test_large_document_preserves_middle_critical_compliance_clause():
    """A critical clause at the 50th percentile of a >100k char document must not be dropped."""
    filler_section = (
        "\n\n## Section Annexe Technique\n"
        + ("Description générale de l'ergonomie de l'interface utilisateur et des couleurs du bouton. " * 25)
    )
    half_len = 50
    critical_middle_clause = (
        "\n\n## Article 42 — Transfert hors CEDEAO et Hébergement Cloud\n"
        "Les données biométriques et de santé des patients sont transférées vers des serveurs AWS hors CEDEAO "
        "sans chiffrement au repos ni autorisation préalable de l'APDP, et sans clause de responsabilité du sous-traitant.\n"
    )
    large_markdown = (
        "# Contrat Cadre et Cahier des Charges\n\nObjet : plateforme numérique.\n"
        + (filler_section * half_len)
        + critical_middle_clause
        + (filler_section * half_len)
    )
    assert len(large_markdown) > 100_000

    selected = _select_relevant_document_passages(large_markdown, budget=12000)
    assert len(selected) <= 12500
    assert "Article 42 — Transfert hors CEDEAO" in selected
    assert "données biométriques" in selected
    assert "autorisation préalable de l'APDP" in selected

    dossier = ProjectDossier(
        project_id=uuid4(),
        project_name="Gros Dossier Test",
        country_code="BJ",
        sector="healthtech",
        project_treatments=["biometrie", "transfert_international"],
        documents=[
            DocumentEvidence(
                document_id=uuid4(),
                filename="contrat_100k.pdf",
                doc_type="contrat",
                markdown=large_markdown,
                vague_zones=[{"zone": "Transfert AWS hors CEDEAO"}],
            )
        ],
    )
    prompt_text = format_dossier_for_prompt(dossier, max_total_chars=20000)
    assert "Article 42 — Transfert hors CEDEAO" in prompt_text
    assert "données biométriques" in prompt_text
