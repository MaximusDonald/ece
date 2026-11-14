"""Holistic Phase 5 Compliance Auditor backed by Article-RAG and multi-document mitigation checks."""

from __future__ import annotations

from collections import defaultdict
import json
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin import ScoringRule
from app.models.corpus import LegalArticle
from app.models.document import Document, DocumentAnalysis, DocumentExtraction, DocumentStatus
from app.models.legal import ConfidenceLevel, ReportVersion, RiskFinding, RiskLevel
from app.models.user import Project
from app.services.article_rag import (
    ArticleSearchResult,
    hybrid_search_articles,
    jurisdictions_for_country,
)
from app.services.llm_client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

FACET_KEYS = (
    "donnees_manipulees",
    "flux_et_architecture",
    "securite_et_droits",
    "relations_contractuelles_et_fintech",
)

FACET_LABELS = {
    "donnees_manipulees": "1. Données manipulées",
    "flux_et_architecture": "2. Flux, hébergement & architecture technique",
    "securite_et_droits": "3. Sécurité, conservation & droits / formalités",
    "relations_contractuelles_et_fintech": "4. Sous-traitants, paiements Fintech & contrats",
}

SearchArticlesFn = Callable[..., Awaitable[List[ArticleSearchResult]]]


@dataclass
class DocumentEvidence:
    """Extracted text and structured metadata for one document in the project dossier."""

    document_id: UUID
    filename: str
    doc_type: str
    markdown: str
    entities: Dict[str, Any] = field(default_factory=dict)
    vague_zones: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ProjectDossier:
    """Complete multi-document project context loaded for holistic compliance evaluation."""

    project_id: UUID
    project_name: str
    country_code: str
    sector: str
    project_treatments: List[str]
    documents: List[DocumentEvidence]
    incremental_context: Optional[Dict[str, Any]] = None
    stored_context_markdown: Optional[str] = None
    previous_report_summary: Optional[str] = None
    represented_entity_type: str = "entreprise"
    represented_entity_other: Optional[str] = None
    represented_role_details: Optional[str] = None


@dataclass
class FacetSignal:
    """Single operational fact or compliance question extracted under one of the 4 facets."""

    facet: str
    summary: str
    rag_query: str
    source_docs: List[str] = field(default_factory=list)


@dataclass
class AuditExecutionResult:
    """Complete output of a holistic project compliance audit."""

    dossier: ProjectDossier
    facets: List[FacetSignal]
    articles_map: Dict[UUID, ArticleSearchResult]
    findings: List[Dict[str, Any]]
    report1_markdown: str
    report2_markdown: str


def _parse_json_object(raw: str) -> Dict[str, Any]:
    """Parse JSON safely even if wrapped in markdown fences or surrounding prose."""
    text = (raw or "").strip()
    if not text:
        return {}
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


async def _load_previous_report_summary(
    session: AsyncSession,
    project_id: UUID,
    previous_report_id: Optional[UUID] = None,
) -> Optional[str]:
    """Build a bounded summary of the previous ReportVersion and its findings for continuity."""
    if previous_report_id is not None:
        res = await session.execute(
            select(ReportVersion)
            .options(selectinload(ReportVersion.findings))
            .where(ReportVersion.id == previous_report_id)
        )
        prev = res.scalar_one_or_none()
    else:
        res = await session.execute(
            select(ReportVersion)
            .options(selectinload(ReportVersion.findings))
            .where(ReportVersion.project_id == project_id)
            .order_by(ReportVersion.created_at.desc())
        )
        prev = res.scalars().first()

    if not prev:
        return None

    lines = [
        f"Version précédente : v{prev.version} | Score global : {prev.global_score}/100 | Confiance : {prev.confidence_global.value}",
    ]
    if prev.severity_counts:
        lines.append(f"Répartition sévérité : {json.dumps(prev.severity_counts, ensure_ascii=False)}")
    findings = list(prev.findings or [])
    if findings:
        lines.append(f"Constats de la version précédente ({len(findings)}) :")
        for idx, f in enumerate(findings[:20], start=1):
            lines.append(
                f"  {idx}. [{f.risk_level.value}] {f.clause_ref} — {f.finding_text[:240]}"
            )
    summary = "\n".join(lines)
    return summary[:3800]


async def load_project_dossier(
    session: AsyncSession,
    project_id: UUID,
    *,
    focus_document_id: Optional[UUID] = None,
    incremental_context: Optional[Dict[str, Any]] = None,
    previous_report_id: Optional[UUID] = None,
) -> ProjectDossier:
    """Load the project and ALL its documents (extractions + analyses) for holistic cross-doc checks."""
    project = await session.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    docs_result = await session.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.asc())
    )
    all_docs = list(docs_result.scalars().all())
    if not all_docs and focus_document_id is not None:
        focus_doc = await session.get(Document, focus_document_id)
        if focus_doc:
            all_docs = [focus_doc]

    doc_ids = [d.id for d in all_docs]
    extractions_by_doc: Dict[UUID, DocumentExtraction] = {}
    analyses_by_doc: Dict[UUID, DocumentAnalysis] = {}

    if doc_ids:
        ext_res = await session.execute(
            select(DocumentExtraction).where(DocumentExtraction.document_id.in_(doc_ids))
        )
        for ext in ext_res.scalars().all():
            extractions_by_doc[ext.document_id] = ext

        ext_ids = [ext.id for ext in extractions_by_doc.values()]
        if ext_ids:
            ana_res = await session.execute(
                select(DocumentAnalysis).where(DocumentAnalysis.extraction_id.in_(ext_ids))
            )
            for ana in ana_res.scalars().all():
                analyses_by_doc[ana.extraction_id] = ana

    evidences: List[DocumentEvidence] = []
    stored_context_parts: List[str] = []
    for doc in all_docs:
        ext = extractions_by_doc.get(doc.id)
        ana = analyses_by_doc.get(ext.id) if ext else None
        markdown = (ext.markdown if ext else "") or ""
        if not markdown and not ana:
            continue
        if doc.document_type == "contexte_complementaire" and markdown.strip():
            stored_context_parts.append(markdown.strip())
        evidences.append(
            DocumentEvidence(
                document_id=doc.id,
                filename=doc.filename,
                doc_type=doc.document_type or "general",
                markdown=markdown,
                entities=(ana.entities if ana else {}) or {},
                vague_zones=(ana.vague_zones if ana else []) or [],
            )
        )

    previous_report_summary = await _load_previous_report_summary(
        session,
        project_id,
        previous_report_id=previous_report_id,
    )

    return ProjectDossier(
        project_id=project.id,
        project_name=project.name,
        country_code=project.country_code,
        sector=project.sector,
        project_treatments=list(project.treatments or []),
        documents=evidences,
        incremental_context=incremental_context,
        stored_context_markdown="\n\n".join(stored_context_parts) if stored_context_parts else None,
        previous_report_summary=previous_report_summary,
        represented_entity_type=getattr(project, "represented_entity_type", "entreprise") or "entreprise",
        represented_entity_other=getattr(project, "represented_entity_other", None),
        represented_role_details=getattr(project, "represented_role_details", None),
    )


REPRESENTED_ROLE_LABELS = {
    "entreprise": "L'entreprise / maître d'ouvrage (responsable du traitement)",
    "developpeur_engage": "Un développeur engagé / salarié / stagiaire (évaluation de sa responsabilité et de ses obligations propres)",
    "prestataire_externe": "Un prestataire externe / sous-traitant (évaluation des risques contractuels et réglementaires encourus par le prestataire)",
    "dpo_juriste": "Un DPO / juriste / auditeur interne",
}


def format_dossier_for_prompt(dossier: ProjectDossier, max_total_chars: int = 44000) -> str:
    """Serialize all project documents fairly into a bounded multi-document context string."""
    if dossier.represented_entity_type == "autre":
        role_label = f"Autre : {dossier.represented_entity_other or 'Non précisé'}"
    else:
        role_label = REPRESENTED_ROLE_LABELS.get(
            dossier.represented_entity_type,
            dossier.represented_entity_type,
        )

    parts = [
        f"PROJET : {dossier.project_name}",
        f"PAYS / JURIDICTION PRINCIPALE : {dossier.country_code}",
        f"SECTEUR : {dossier.sector}",
        f"TRAITEMENTS DÉCLARÉS : {', '.join(dossier.project_treatments) if dossier.project_treatments else 'Non précisé'}",
        f"ENTITÉ / RÔLE REPRÉSENTÉ POUR L'ANALYSE : {role_label}",
    ]
    if dossier.represented_role_details:
        parts.append(f"PRÉCISIONS SUR LE RÔLE REPRÉSENTÉ : {dossier.represented_role_details}")
    parts.append(
        "CONSIGNE DE PERSPECTIVE : Évalue la conformité, la responsabilité juridique et les recommandations spécifiquement du point de vue de l'entité/rôle représenté ci-dessus."
    )
    if dossier.stored_context_markdown:
        parts.append(
            "DOCUMENT DE CONTEXTE COMPLÉMENTAIRE DU PROJET :\n"
            + dossier.stored_context_markdown[:4000]
        )
    if dossier.incremental_context:
        parts.append(
            "NOUVEAU CONTEXTE COMPLÉMENTAIRE SOUMIS :\n"
            + json.dumps(dossier.incremental_context, ensure_ascii=False, indent=2)
        )
    if dossier.previous_report_summary:
        parts.append(
            "ANCIENNE VERSION DU RAPPORT (RÉFÉRENCE POUR CONTINUITÉ ET RÉÉVALUATION) :\n"
            + dossier.previous_report_summary
        )

    doc_count = max(len(dossier.documents), 1)
    per_doc_budget = max(2500, min(14000, max_total_chars // doc_count))

    parts.append(f"\nDOSSIER COMPLET ({len(dossier.documents)} document(s) à inspecter conjointement) :")
    for idx, doc in enumerate(dossier.documents, start=1):
        snippet = doc.markdown.strip()
        if len(snippet) > per_doc_budget:
            head = int(per_doc_budget * 0.72)
            tail = per_doc_budget - head - 40
            snippet = (
                snippet[:head].rstrip()
                + "\n[... passage intermédiaire tronqué ...]\n"
                + snippet[-max(tail, 0):].lstrip()
            )
        doc_block = [
            f"\n--- DOCUMENT #{idx} : {doc.filename} (type={doc.doc_type}) ---",
            f"TEXTE EXTRAIT :\n{snippet or '[Aucun texte extrait]'}",
        ]
        if doc.entities:
            doc_block.append(f"ENTITÉS DÉTECTÉES : {json.dumps(doc.entities, ensure_ascii=False)[:1200]}")
        if doc.vague_zones:
            doc_block.append(f"ZONES FLOUES DÉTECTÉES : {json.dumps(doc.vague_zones, ensure_ascii=False)[:1200]}")
        parts.append("\n".join(doc_block))

    return "\n".join(parts)


def _deterministic_fallback_facets(dossier: ProjectDossier) -> List[FacetSignal]:
    """Extract deterministic 4-facet signals if LLM JSON deconstruction returns empty or fails."""
    corpus_text = " ".join(
        [dossier.sector, " ".join(dossier.project_treatments)]
        + [doc.markdown[:4000] for doc in dossier.documents]
    ).lower()
    all_filenames = [doc.filename for doc in dossier.documents]

    signals: List[FacetSignal] = []

    if any(k in corpus_text for k in ("santé", "sante", "médical", "medical", "patient", "biomét", "biomet", "donnée", "donnee", "mineur")):
        signals.append(
            FacetSignal(
                facet="donnees_manipulees",
                summary="Traitement de données personnelles et/ou sensibles (santé, biométrie, identité ou mineurs).",
                rag_query="traitement données personnelles sensibles santé biométrie consentement préalable personne concernée",
                source_docs=all_filenames,
            )
        )
    else:
        signals.append(
            FacetSignal(
                facet="donnees_manipulees",
                summary="Collecte et traitement de données à caractère personnel des utilisateurs.",
                rag_query="collecte traitement licite données à caractère personnel finalité proportionnalité",
                source_docs=all_filenames,
            )
        )

    if any(k in corpus_text for k in ("aws", "ovh", "azure", "gcp", "paris", "europe", "états-unis", "etranger", "étranger", "cloud", "hors", "transfert")):
        signals.append(
            FacetSignal(
                facet="flux_et_architecture",
                summary="Hébergement cloud / transfert potentiel de données hors du territoire national ou de la CEDEAO.",
                rag_query="transfert données à caractère personnel vers un Etat tiers pays étranger hébergement APDP autorisation",
                source_docs=all_filenames,
            )
        )
    else:
        signals.append(
            FacetSignal(
                facet="flux_et_architecture",
                summary="Architecture d'hébergement et localisation des serveurs de traitement.",
                rag_query="hébergement localisation serveurs transfert international données personnelles sécurité",
                source_docs=all_filenames,
            )
        )

    signals.append(
        FacetSignal(
            facet="securite_et_droits",
            summary="Formalités APDP, sécurité/chiffrement, durée de conservation, droits des personnes et DPO.",
            rag_query="déclaration autorisation préalable APDP délégué protection données DPO sécurité confidentialité violation",
            source_docs=all_filenames,
        )
    )

    if any(k in corpus_text for k in ("paiement", "mobile money", "monnaie", "fintech", "mtn", "moov", "wave", "carte", "virement", "banque", "bceao")):
        signals.append(
            FacetSignal(
                facet="relations_contractuelles_et_fintech",
                summary="Services de paiement, monnaie électronique, encaissements ou sous-traitance fintech.",
                rag_query="monnaie électronique établissement paiement BCEAO agrément prestataire services paiement sous-traitant",
                source_docs=all_filenames,
            )
        )
    else:
        signals.append(
            FacetSignal(
                facet="relations_contractuelles_et_fintech",
                summary="Relations avec sous-traitants techniques, contrats électroniques et propriété intellectuelle.",
                rag_query="sous-traitant contrat écrit responsabilité commerce électronique preuve signature logicielle",
                source_docs=all_filenames,
            )
        )

    return signals


async def deconstruct_project_facets(
    dossier: ProjectDossier,
    llm_client: LLMClient,
) -> List[FacetSignal]:
    """Step 1: Deconstruct the full project dossier into 4 structured compliance facets."""
    dossier_prompt = format_dossier_for_prompt(dossier, max_total_chars=32000)
    prompt = f"""Analyse l'ensemble du dossier projet ci-dessous et décompose-le en facettes réglementaires concrètes selon les 4 axes suivants :
1. "donnees_manipulees" : nature des données traitées (santé, biométrie, paiement, mineurs, identité, géolocalisation, etc.).
2. "flux_et_architecture" : lieu d'hébergement, prestataires cloud (AWS/OVH/GCP/on-premise), transferts transfrontaliers hors {dossier.country_code} ou CEDEAO.
3. "securite_et_droits" : chiffrement, contrôle d'accès, notification de faille, durée de conservation, consentement, DPO, formalités APDP.
4. "relations_contractuelles_et_fintech" : sous-traitants, services de paiement / mobile money / monnaie électronique, contrats électroniques OHADA, propriété intellectuelle.

Pour chaque fait technique ou métier concret identifié, fournis :
- "facet": exactement une des 4 clés ci-dessus
- "summary": description précise du fait projet
- "rag_query": requête de recherche juridique dense en français (8 à 16 mots clés juridiques + opérationnels) pour retrouver les articles de loi exacts applicables en {dossier.country_code} / CEDEAO / UEMOA / OHADA.
- "source_docs": liste des noms de fichiers concernés.

Retourne UNIQUEMENT un objet JSON de la forme :
{{"items": [{{"facet": "...", "summary": "...", "rag_query": "...", "source_docs": ["..."]}}]}}

{dossier_prompt}"""

    parsed: Dict[str, Any] = {}
    try:
        raw = await llm_client.chat_completion(prompt, response_format="json_object")
        parsed = _parse_json_object(raw)
    except Exception as exc:
        logger.warning("Facet deconstruction LLM call failed (%s); using deterministic fallback.", exc)

    signals: List[FacetSignal] = []
    seen_queries: set[str] = set()
    for item in parsed.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        facet = str(item.get("facet", "")).strip()
        if facet not in FACET_KEYS:
            continue
        summary = str(item.get("summary", "")).strip()
        rag_query = str(item.get("rag_query", "") or summary).strip()
        if not summary or not rag_query:
            continue
        norm_q = rag_query.lower()
        if norm_q in seen_queries:
            continue
        seen_queries.add(norm_q)
        source_docs = [str(s) for s in (item.get("source_docs") or []) if s]
        signals.append(
            FacetSignal(
                facet=facet,
                summary=summary,
                rag_query=rag_query,
                source_docs=source_docs or [d.filename for d in dossier.documents],
            )
        )

    # Ensure every core baseline facet has at least minimal coverage via fallback signals
    fallback = _deterministic_fallback_facets(dossier)
    present_facets = {s.facet for s in signals}
    for fb in fallback:
        if fb.facet not in present_facets:
            signals.append(fb)

    return signals[:12]


async def retrieve_articles_for_facets(
    dossier: ProjectDossier,
    facets: Sequence[FacetSignal],
    *,
    limit_per_facet: int = 4,
    max_total_articles: int = 24,
    search_fn: Optional[SearchArticlesFn] = None,
) -> tuple[Dict[UUID, ArticleSearchResult], Dict[str, List[UUID]]]:
    """Step 2: Run Hybrid Article-RAG per facet, filtered by jurisdiction, deduplicating articles."""
    rag_fn = search_fn or hybrid_search_articles
    jurisdictions = jurisdictions_for_country(dossier.country_code)

    articles_by_id: Dict[UUID, ArticleSearchResult] = {}
    facet_article_ids: Dict[str, List[UUID]] = {k: [] for k in FACET_KEYS}

    for signal in facets:
        try:
            hits = await rag_fn(
                signal.rag_query,
                jurisdictions=jurisdictions,
                limit=limit_per_facet,
            )
        except Exception as exc:
            logger.warning("Article-RAG query failed for facet %s (%s): %s", signal.facet, signal.rag_query, exc)
            hits = []

        for hit in hits:
            existing = articles_by_id.get(hit.article_id)
            if existing is None or hit.score > existing.score:
                articles_by_id[hit.article_id] = hit
            if hit.article_id not in facet_article_ids.setdefault(signal.facet, []):
                facet_article_ids[signal.facet].append(hit.article_id)

    # Cap total articles sent into evaluation prompt by highest hybrid score
    sorted_articles = sorted(articles_by_id.values(), key=lambda a: a.score, reverse=True)[:max_total_articles]
    capped_map = {a.article_id: a for a in sorted_articles}
    return capped_map, facet_article_ids


def _format_articles_catalog(articles_map: Dict[UUID, ArticleSearchResult]) -> str:
    """Serialize candidate statutory articles with UUIDs, hierarchy breadcrumbs, text and sanctions."""
    ordered = sorted(
        articles_map.values(),
        key=lambda a: (a.jurisdiction, a.text_code, -a.score),
    )
    blocks: List[str] = []
    for art in ordered:
        body = art.full_text.strip()
        if len(body) > 1300:
            body = body[:1280].rstrip() + " [...]"
        sanction_line = (
            f"SANCTION PRÉVUE : {art.sanction_details}"
            if art.has_sanction and art.sanction_details
            else ("SANCTION PRÉVUE : Oui (voir texte intégral)" if art.has_sanction else "SANCTION : Administrative / Civile selon texte")
        )
        blocks.append(
            f"[{art.article_id}] {art.text_code} ({art.jurisdiction} - {art.authority}) | {art.article_number}"
            + (f" — {art.title}" if art.title else "")
            + f"\nHiérarchie : {art.section_breadcrumb or 'Corps principal'}"
            + f"\n{sanction_line}"
            + f"\nTexte officiel :\n{body}"
        )
    return "\n\n".join(blocks)


def _normalize_risk_level(value: Any) -> RiskLevel:
    raw = str(value or "").strip().lower()
    mapping = {
        "critique": RiskLevel.CRITIQUE,
        "critical": RiskLevel.CRITIQUE,
        "eleve": RiskLevel.ELEVE,
        "élevé": RiskLevel.ELEVE,
        "high": RiskLevel.ELEVE,
        "modere": RiskLevel.MODERE,
        "modéré": RiskLevel.MODERE,
        "medium": RiskLevel.MODERE,
        "a_surveiller": RiskLevel.A_SURVEILLER,
        "a_verifier": RiskLevel.A_SURVEILLER,
        "faible": RiskLevel.A_SURVEILLER,
        "low": RiskLevel.A_SURVEILLER,
        "conforme": RiskLevel.CONFORME,
        "compliant": RiskLevel.CONFORME,
    }
    return mapping.get(raw, RiskLevel.MODERE)


def _normalize_confidence(value: Any) -> ConfidenceLevel:
    raw = str(value or "").strip().lower()
    if raw in ("high", "eleve", "élevé", "haute"):
        return ConfidenceLevel.HIGH
    if raw in ("low", "faible", "basse"):
        return ConfidenceLevel.LOW
    return ConfidenceLevel.MEDIUM


def _build_article_lookup_index(
    articles_map: Dict[UUID, ArticleSearchResult],
) -> Dict[tuple[str, str], UUID]:
    """Allow resolving LLM references like ('BJ-NUM-2017', 'Article 391') or '391' back to real UUIDs."""
    index: Dict[tuple[str, str], UUID] = {}
    for aid, art in articles_map.items():
        code_norm = art.text_code.upper().strip()
        num_norm = re.sub(r"\s+", " ", art.article_number.lower()).strip()
        index[(code_norm, num_norm)] = aid
        digits = re.sub(r"^(?:article|art\.?)\s*", "", num_norm).strip()
        if digits:
            index[(code_norm, digits)] = aid
    return index


def _resolve_matched_articles(
    raw_finding: Dict[str, Any],
    articles_map: Dict[UUID, ArticleSearchResult],
    lookup_index: Dict[tuple[str, str], UUID],
) -> List[UUID]:
    """Validate and resolve UUIDs of cited LegalArticle records, rejecting any hallucinated UUIDs."""
    resolved: List[UUID] = []

    def _add_if_valid(uid: UUID) -> None:
        if uid in articles_map and uid not in resolved:
            resolved.append(uid)

    for candidate in (raw_finding.get("matched_articles") or []):
        try:
            _add_if_valid(UUID(str(candidate).strip()))
        except ValueError:
            continue

    # Also match explicit article_refs objects like {"text_code": "BJ-NUM-2017", "article_number": "Article 391"}
    for ref in (raw_finding.get("article_refs") or []):
        if isinstance(ref, dict):
            code = str(ref.get("text_code", "")).upper().strip()
            num = re.sub(r"\s+", " ", str(ref.get("article_number", "")).lower()).strip()
            digits = re.sub(r"^(?:article|art\.?)\s*", "", num).strip()
            if (code, num) in lookup_index:
                _add_if_valid(lookup_index[(code, num)])
            elif (code, digits) in lookup_index:
                _add_if_valid(lookup_index[(code, digits)])

    # Last-resort scan of clause/finding text against known text codes & article numbers
    if not resolved:
        haystack = " ".join(
            str(raw_finding.get(k, ""))
            for k in ("finding_text", "constat", "exigence_legale", "recommendation")
        ).lower()
        for (code_norm, num_norm), aid in lookup_index.items():
            if num_norm.startswith("article ") and code_norm.lower() in haystack and num_norm in haystack:
                _add_if_valid(aid)

    return resolved


def _is_parade_absent_or_uncertain(parade_text: str) -> bool:
    norm = (parade_text or "").strip().lower()
    if not norm:
        return True
    absence_markers = (
        "aucune parade",
        "aucun justificatif",
        "non prouv",
        "non détecté",
        "non detecte",
        "absent",
        "aucune preuve",
        "à vérifier",
        "a verifier",
        "incertain",
        "non mentionné",
        "non mentionne",
    )
    return any(m in norm for m in absence_markers)


def _normalize_findings(
    raw_findings: Sequence[Dict[str, Any]],
    articles_map: Dict[UUID, ArticleSearchResult],
) -> List[Dict[str, Any]]:
    """Validate LLM audit findings, resolve article UUIDs, and enforce the precautionary rule."""
    lookup_index = _build_article_lookup_index(articles_map)
    normalized: List[Dict[str, Any]] = []

    for item in raw_findings:
        if not isinstance(item, dict):
            continue

        matched_ids = _resolve_matched_articles(item, articles_map, lookup_index)
        parade_detectee = str(
            item.get("parade_detectee") or "Aucune parade d'annulation prouvée dans les documents du projet."
        ).strip()
        parade_proven = bool(item.get("parade_prouvee", False)) and not _is_parade_absent_or_uncertain(parade_detectee)

        risk_level = _normalize_risk_level(item.get("risk_level"))
        verdict = str(item.get("verdict") or "").strip().lower()

        # Precautionary fail-safe rule: never downgrade to 'conforme' unless an explicit mitigation was proven
        if not parade_proven and risk_level == RiskLevel.CONFORME:
            risk_level = RiskLevel.MODERE
        if not parade_proven and verdict == "conforme":
            verdict = "a_verifier"
        if not verdict:
            verdict = "conforme" if risk_level == RiskLevel.CONFORME else (
                "a_verifier" if risk_level == RiskLevel.A_SURVEILLER else "non_conforme"
            )

        article_labels = [
            f"{articles_map[aid].text_code} — {articles_map[aid].article_number}"
            for aid in matched_ids
        ]
        sanction_notes = [
            articles_map[aid].sanction_details
            for aid in matched_ids
            if articles_map[aid].has_sanction and articles_map[aid].sanction_details
        ]

        constat = str(item.get("finding_text") or item.get("constat") or "").strip()
        if not constat:
            continue

        legal_risk = str(item.get("legal_risk") or ("; ".join(sanction_notes[:2]) if sanction_notes else "")).strip()
        raw_facet = str(item.get("facet") or item.get("domain") or "").strip()
        facet = raw_facet if raw_facet in FACET_KEYS else _infer_finding_domain(
            {
                "facet": raw_facet,
                "clause_ref": item.get("clause_ref"),
                "finding_text": constat,
            }
        )

        enriched_finding_parts = [constat]
        if verdict == "conforme" and parade_proven:
            enriched_finding_parts.append(f"Parade d'annulation vérifiée : {parade_detectee}")
        else:
            enriched_finding_parts.append(f"Parade d'annulation : {parade_detectee}")
        if article_labels:
            enriched_finding_parts.append(f"Articles applicables : {', '.join(article_labels)}")
        if legal_risk:
            enriched_finding_parts.append(f"Risque légal encouru : {legal_risk}")

        recommendation = str(item.get("recommendation") or item.get("action_corrective") or "").strip()
        if not recommendation:
            recommendation = (
                "Maintenir la preuve de conformité dans le dossier d'audit."
                if verdict == "conforme"
                else "Fournir les pièces justificatives ou mettre en œuvre la mesure de mise en conformité requise avant mise en production."
            )

        normalized.append(
            {
                "clause_ref": str(item.get("clause_ref") or FACET_LABELS.get(facet, "Dossier Projet")).strip(),
                "facet": facet,
                "verdict": verdict,
                "parade_prouvee": parade_proven,
                "parade_detectee": parade_detectee,
                "legal_risk": legal_risk,
                "finding_text": "\n".join(enriched_finding_parts),
                "risk_level": risk_level,
                "confidence": _normalize_confidence(item.get("confidence")),
                "matched_sources": [],  # Legacy legal_source empty in new Article-RAG engine
                "matched_articles": matched_ids,
                "obsolescence_flag": bool(item.get("obsolescence_flag", False)),
                "conflict_flag": bool(item.get("conflict_flag", False)),
                "conflict_details": item.get("conflict_details"),
                "recommendation": recommendation,
            }
        )

    # Deduplicate findings targeting the exact same (facet, matched_articles) pair, keeping highest severity
    severity_rank = {
        RiskLevel.CRITIQUE: 4,
        RiskLevel.ELEVE: 3,
        RiskLevel.MODERE: 2,
        RiskLevel.A_SURVEILLER: 1,
        RiskLevel.CONFORME: 0,
    }
    deduped: List[Dict[str, Any]] = []
    seen_keys: Dict[tuple, int] = {}
    for entry in normalized:
        article_sig = frozenset(entry["matched_articles"])
        if not article_sig:
            deduped.append(entry)
            continue
        key = (entry["facet"], article_sig)
        if key not in seen_keys:
            seen_keys[key] = len(deduped)
            deduped.append(entry)
        else:
            existing_idx = seen_keys[key]
            if severity_rank.get(entry["risk_level"], 0) > severity_rank.get(deduped[existing_idx]["risk_level"], 0):
                deduped[existing_idx] = entry

    return deduped


async def evaluate_project_compliance(
    dossier: ProjectDossier,
    facets: Sequence[FacetSignal],
    articles_map: Dict[UUID, ArticleSearchResult],
    llm_client: LLMClient,
) -> List[Dict[str, Any]]:
    """Step 3: Holistic multi-doc check with 'parade d'annulation' verification & precautionary fail-safe."""
    if not articles_map:
        logger.warning("No canonical legal articles retrieved for project %s; returning precautionary finding.", dossier.project_id)
        return [
            {
                "clause_ref": "Couverture Corpus",
                "facet": "securite_et_droits",
                "verdict": "a_verifier",
                "parade_prouvee": False,
                "parade_detectee": "Aucune correspondance d'article indexée pour ce profil.",
                "legal_risk": "Vérification juridique manuelle requise par précaution.",
                "finding_text": "Aucun article normatif exact n'a été remonté automatiquement ; une revue manuelle reste nécessaire avant lancement.",
                "risk_level": RiskLevel.MODERE,
                "confidence": ConfidenceLevel.LOW,
                "matched_sources": [],
                "matched_articles": [],
                "obsolescence_flag": False,
                "conflict_flag": False,
                "conflict_details": None,
                "recommendation": "Compléter la description technique et vérifier les obligations APDP / BCEAO applicables.",
            }
        ]

    dossier_prompt = format_dossier_for_prompt(dossier, max_total_chars=36000)
    articles_catalog = _format_articles_catalog(articles_map)
    facets_json = json.dumps(
        [{"facet": f.facet, "summary": f.summary, "source_docs": f.source_docs} for f in facets],
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""Tu es un auditeur juridique senior spécialisé en droit du numérique, protection des données, cybersécurité et fintech en Afrique de l'Ouest ({dossier.country_code}, CEDEAO, UEMOA/BCEAO, OHADA, OAPI, Union Africaine).

RÈGLE D'OR N°1 — LECTURE HOLISTIQUE MULTI-DOCUMENTS & PARADE D'ANNULATION :
Pour chaque exigence ou risque potentiel (ex: hébergement cloud à l'étranger, collecte de données de santé, paiement mobile money, absence de mention DPO), tu DOIS inspecter **TOUS les documents du projet ci-dessous conjointement**.
Si un autre document du dossier (ex: Politique de confidentialité, CGU, Annexe technique, Contrat sous-traitant, Récépissé ou Autorisation APDP) apporte une **parade d'annulation / mesure compensatoire explicite et prouvée** (exemple : autorisation préalable APDP dûment référencée, clause expresse de consentement éclairé au transfert hors CEDEAO, anonymisation irréversible prouvée, agrément BCEAO fourni), tu dois l'indiquer dans `parade_detectee`, mettre `parade_prouvee: true`, `verdict: "conforme"` (ou `"a_verifier"` si partiel) et `risk_level: "conforme"` ou `"a_surveiller"`.

RÈGLE D'OR N°2 — PRINCIPE DE PRÉCAUTION ("UN FAUX CONSEIL VAUT MIEUX QUE PAS DE CONSEIL") :
Si aucune parade explicite et probante n'apparaît dans AUCUN document du dossier, OU en cas de doute / ambiguïté / promesse générique sans preuve vérifiable :
- NE JAMAIS conclure à la conformité !
- Mettre `parade_prouvee: false`, `verdict: "non_conforme"` ou `"a_verifier"`, et un `risk_level` d'alerte (`critique`, `eleve`, ou `modere`).
- Toujours signaler la contrainte et citer l'article de loi + la sanction encourue.

RÈGLE D'OR N°3 — TRAÇABILITÉ STRICTE PAR UUID D'ARTICLE :
Chaque constat DOIT référencer un ou plusieurs `matched_articles` choisis EXCLUSIVEMENT parmi les UUID `[...]` listés dans le RÉFÉRENTIEL D'ARTICLES DE LOI ci-dessous. N'invente jamais d'UUID ni de numéro d'article absent du référentiel.

RÈGLE D'OR N°4 — CONSOLIDATION THÉMATIQUE PAR FACETTE (ANTI-FRAGMENTATION) :
Regroupe les constats par thématique juridique (au maximum 1 à 2 constats consolidés par facette : `donnees_manipulees`, `flux_et_architecture`, `securite_et_droits`, `relations_contractuelles_et_fintech`). Ne scinde pas une même obligation ou un même article en plusieurs constats redondants.

FACETTES IDENTIFIÉES :
{facets_json}

{dossier_prompt}

RÉFÉRENTIEL D'ARTICLES DE LOI DISPONIBLES (avec UUID réels) :
{articles_catalog}

Produis un objet JSON strict contenant `"findings"` (entre 4 et 8 constats consolidés couvrant les 4 facettes clés, incluant aussi les points où une parade d'annulation a évité un faux positif) :
{{
  "findings": [
    {{
      "clause_ref": "Nom document / section ou facette concernée",
      "facet": "donnees_manipulees | flux_et_architecture | securite_et_droits | relations_contractuelles_et_fintech",
      "finding_text": "Description factuelle précise du constat croisant les documents du projet.",
      "verdict": "non_conforme | a_verifier | conforme",
      "parade_prouvee": false,
      "parade_detectee": "Preuve exacte tirée d'un document du dossier OU 'Aucune parade d'annulation détectée dans les documents du projet.'",
      "risk_level": "critique | eleve | modere | a_surveiller | conforme",
      "confidence": "high | medium | low",
      "matched_articles": ["uuid-exact-de-l-article"],
      "article_refs": [{{"text_code": "BJ-NUM-2017", "article_number": "Article 391"}}],
      "legal_risk": "Sanction financière ou pénale exacte issue de l'article cité.",
      "obsolescence_flag": false,
      "conflict_flag": false,
      "conflict_details": null,
      "recommendation": "Action juridique ou technique concrète et vérifiable avant lancement."
    }}
  ]
}}"""

    raw = await llm_client.chat_completion(prompt, response_format="json_object")
    parsed = _parse_json_object(raw)
    raw_findings = parsed.get("findings") or []
    normalized = _normalize_findings(raw_findings, articles_map)

    if not normalized:
        logger.warning("LLM returned zero usable findings for project %s; emitting precautionary fallback.", dossier.project_id)
        top_articles = sorted(articles_map.values(), key=lambda a: a.score, reverse=True)[:3]
        return _normalize_findings(
            [
                {
                    "clause_ref": "Revue Globale du Dossier",
                    "facet": "securite_et_droits",
                    "finding_text": "L'analyse automatique nécessite une confirmation documentaire des formalités réglementaires et mesures de transfert applicables.",
                    "verdict": "a_verifier",
                    "parade_prouvee": False,
                    "parade_detectee": "Aucune parade d'annulation formelle prouvée dans le dossier projet.",
                    "risk_level": "eleve",
                    "confidence": "low",
                    "matched_articles": [str(a.article_id) for a in top_articles],
                    "recommendation": "Vérifier et joindre les preuves de formalités APDP, consentement explicite et garanties contractuelles.",
                }
            ],
            articles_map,
        )

    return normalized


def build_audit_reports(
    dossier: ProjectDossier,
    facets: Sequence[FacetSignal],
    findings: Sequence[Dict[str, Any]],
    articles_map: Dict[UUID, ArticleSearchResult],
) -> tuple[str, str]:
    """Step 4: Generate Report 1 (Project Matrix with Parades) & Report 2 (Canonical Article Synthesis)."""
    severity_rank = {
        RiskLevel.CRITIQUE: 0,
        RiskLevel.ELEVE: 1,
        RiskLevel.MODERE: 2,
        RiskLevel.A_SURVEILLER: 3,
        RiskLevel.CONFORME: 4,
    }
    sorted_findings = sorted(findings, key=lambda f: severity_rank.get(f["risk_level"], 2))

    # --- Report 1: Matrice d'Écart & Parades d'Annulation ---
    r1_lines = [
        f"# Rapport d'Analyse Documentaire & Conformité — {dossier.project_name}",
        "",
        f"- **Juridiction principale** : `{dossier.country_code}` (incluant textes communautaires CEDEAO / UEMOA / OHADA / OAPI / UA applicables)",
        f"- **Secteur** : {dossier.sector}",
        f"- **Périmètre inspecté** : {len(dossier.documents)} document(s) analysé(s) conjointement ({', '.join(d.filename for d in dossier.documents) or 'Contexte projet'})",
        "",
        "## 1. Déconstruction Multi-Axes du Projet",
        "",
    ]
    for sig in facets:
        r1_lines.append(f"- **{FACET_LABELS.get(sig.facet, sig.facet)}** : {sig.summary}")

    r1_lines.extend(["", "## 2. Matrice d'Écart & Détection des Parades d'Annulation", ""])

    for idx, f in enumerate(sorted_findings, start=1):
        rl = f["risk_level"].value if isinstance(f["risk_level"], RiskLevel) else str(f["risk_level"])
        conf = f["confidence"].value if isinstance(f["confidence"], ConfidenceLevel) else str(f["confidence"])
        badge = "CONFORME (PARADE PROUVÉE)" if f.get("parade_prouvee") else rl.upper()
        r1_lines.append(f"### {idx}. [{badge}] {f['clause_ref']}")
        r1_lines.append(f"- **Verdict** : `{f.get('verdict', 'a_verifier')}` | **Confiance** : `{conf}`")
        r1_lines.append(f"- **Parade d'annulation** : {f.get('parade_detectee', 'Aucune')}")
        r1_lines.append(f"\n{f['finding_text']}\n")
        if f.get("conflict_flag") and f.get("conflict_details"):
            r1_lines.append(f"- **Conflit normatif signalé** : {f['conflict_details']}")
        r1_lines.append(f"- **Action corrective recommandée** : {f['recommendation']}")
        if f.get("matched_articles"):
            r1_lines.append("- **Articles légaux cités** :")
            for aid in f["matched_articles"]:
                art = articles_map.get(aid if isinstance(aid, UUID) else UUID(str(aid)))
                if art:
                    r1_lines.append(
                        f"  - `{art.text_code}` — **{art.article_number}** ({art.section_breadcrumb or art.authority})"
                    )
        r1_lines.append("")

    # --- Report 2: Synthèse Juridique & Articles Mobilisés ---
    r2_lines = [
        f"# Synthèse Juridique & Référentiel des Articles — {dossier.project_name}",
        "",
        f"Base normative mobilisée par Article-RAG hybride pour la juridiction `{dossier.country_code}`.",
        "",
        "## Articles de Loi Mobilisés",
        "",
    ]
    cited_ids: List[UUID] = []
    for f in sorted_findings:
        for raw_aid in f.get("matched_articles", []):
            uid = raw_aid if isinstance(raw_aid, UUID) else UUID(str(raw_aid))
            if uid in articles_map and uid not in cited_ids:
                cited_ids.append(uid)

    if not cited_ids:
        r2_lines.append("_Aucun article statutaire n'a été rattaché directement aux constats de cette version._")
    else:
        for aid in cited_ids:
            art = articles_map[aid]
            r2_lines.append(f"### {art.text_code} — {art.article_number}" + (f" : {art.title}" if art.title else ""))
            r2_lines.append(f"- **Texte** : {art.text_title}")
            r2_lines.append(f"- **Autorité / Juridiction** : {art.authority} (`{art.jurisdiction}`)")
            r2_lines.append(f"- **Position hiérarchique** : {art.section_breadcrumb or 'Corps principal'}")
            if art.has_sanction and art.sanction_details:
                r2_lines.append(f"- **Sanction prévue** : {art.sanction_details}")
            excerpt = art.full_text.strip()
            if len(excerpt) > 900:
                excerpt = excerpt[:880].rstrip() + " [...]"
            r2_lines.append(f"\n> {excerpt.replace(chr(10), chr(10) + '> ')}\n")

    return "\n".join(r1_lines), "\n".join(r2_lines)


async def run_holistic_compliance_audit(
    session: AsyncSession,
    project_id: UUID,
    *,
    focus_document_id: Optional[UUID] = None,
    incremental_context: Optional[Dict[str, Any]] = None,
    previous_report_id: Optional[UUID] = None,
    llm_client: Optional[LLMClient] = None,
    search_fn: Optional[SearchArticlesFn] = None,
) -> AuditExecutionResult:
    """Execute the full 4-stage Phase 5 audit: Load All Docs -> 4 Facets -> Article-RAG -> Parades Check."""
    client = llm_client or get_llm_client()
    dossier = await load_project_dossier(
        session,
        project_id,
        focus_document_id=focus_document_id,
        incremental_context=incremental_context,
        previous_report_id=previous_report_id,
    )
    facets = await deconstruct_project_facets(dossier, client)
    articles_map, _ = await retrieve_articles_for_facets(
        dossier,
        facets,
        search_fn=search_fn,
    )
    findings = await evaluate_project_compliance(dossier, facets, articles_map, client)
    report1_md, report2_md = build_audit_reports(dossier, facets, findings, articles_map)

    return AuditExecutionResult(
        dossier=dossier,
        facets=facets,
        articles_map=articles_map,
        findings=findings,
        report1_markdown=report1_md,
        report2_markdown=report2_md,
    )


async def resolve_applicable_scoring_rule(
    session: AsyncSession,
    *,
    country_code: Optional[str] = None,
    sector: Optional[str] = None,
    treatments: Optional[Sequence[str]] = None,
) -> Optional[ScoringRule]:
    """Fetch the most specific active ScoringRule for the project's jurisdiction and sector."""
    stmt = select(ScoringRule).where(ScoringRule.is_active == True)
    res = await session.execute(stmt)
    all_rules = list(res.scalars().all())
    if not all_rules:
        return None

    treatments_set = set(t.lower() for t in (treatments or []))
    if sector:
        treatments_set.add(sector.lower())

    def rule_priority(r: ScoringRule) -> int:
        score = 0
        if country_code and r.country_code and r.country_code.upper() == country_code.upper():
            score += 10
        elif r.country_code is None:
            score += 2
        else:
            return -1  # Rule specifically for a different country

        domain_lower = (r.domain or "").lower()
        if domain_lower in treatments_set or (sector and domain_lower == sector.lower()):
            score += 5
        elif domain_lower == "global":
            score += 1
        return score

    eligible = [(rule_priority(r), r) for r in all_rules if rule_priority(r) >= 0]
    if not eligible:
        return None
    eligible.sort(key=lambda x: x[0], reverse=True)
    return eligible[0][1]


def _infer_finding_domain(finding: Dict[str, Any]) -> str:
    """Resolve a finding's canonical facet/domain for diminishing-returns scoring."""
    raw = str(finding.get("domain") or finding.get("facet") or "").strip().lower()
    if raw in FACET_KEYS:
        return raw

    haystack = " ".join(
        [
            raw,
            str(finding.get("clause_ref") or ""),
            str(finding.get("finding_text") or ""),
        ]
    ).lower()

    if any(k in haystack for k in ("donnees", "données", "biomet", "biomèt", "santé", "sante", "mineur", "sensible", "collecte")):
        return "donnees_manipulees"
    if any(k in haystack for k in ("flux", "héberg", "heberg", "transfert", "architecture", "cloud", "aws", "serveur", "hors cedeao", "international")):
        return "flux_et_architecture"
    if any(k in haystack for k in ("sécurit", "securit", "chiffrement", "droit", "conservation", "durée", "duree", "apdp", "cdp", "dpo", "consentement", "notification", "formalit")):
        return "securite_et_droits"
    if any(k in haystack for k in ("sous-trait", "contrat", "fintech", "paiement", "bceao", "kyc", "lbc", "ft", "mobile money", "prestataire")):
        return "relations_contractuelles_et_fintech"
    return "general"


def compute_initial_severity_and_score(
    findings: Sequence[Dict[str, Any]],
    *,
    rule: Optional[ScoringRule] = None,
    articles_map: Optional[Dict[UUID, Any]] = None,
) -> tuple[Dict[str, int], int, ConfidenceLevel]:
    """Compute severity distribution, rule-calibrated bounded score, and aggregate confidence.

    Politique de scoring juridique ECE :
    - Non-hasardeux : piloté par ScoringRule (weights par domaine & juridiction).
    - Rendements décroissants par domaine (1.0, 0.5, 0.25...) pour éviter la volatilité
      lorsque le LLM scinde un constat en plusieurs sous-constats du même domaine.
    - Sanctions légales dédupliquées par article unique : majoration proportionnée si
      l'article enfreint comporte une sanction pénale (+8 pts) ou administrative (+4 pts),
      plafonnée à +25 pts.
    - Principe de précaution : si un risque critique subsiste (non-mitigé), le score global
      est plancher à 50/100 au minimum.
    - Compression graduée au-delà de 70/100 pour éviter la saturation prématurée à 100.
    - Zéro risque si tout est conforme : score de 0/100.
    """
    severity_counts = {
        "critique": 0,
        "eleve": 0,
        "modere": 0,
        "a_surveiller": 0,
        "conforme": 0,
    }

    w_critique = (rule.weight_critique * 25.0) if rule else 25.0
    w_eleve = (rule.weight_eleve * 20.0) if rule else 15.0
    w_modere = (rule.weight_modere * 12.0) if rule else 10.0
    w_surveiller = (rule.weight_a_surveiller * 5.0) if rule else 5.0
    w_conforme = (rule.weight_conforme * 0.0) if rule else 0.0

    weight_by_level = {
        "critique": w_critique,
        "eleve": w_eleve,
        "modere": w_modere,
        "a_surveiller": w_surveiller,
        "conforme": w_conforme,
    }

    conf_scores = {ConfidenceLevel.HIGH: 3, ConfidenceLevel.MEDIUM: 2, ConfidenceLevel.LOW: 1}
    total_conf = 0
    has_unmitigated_critical = False
    has_non_conforme = False
    domain_weights: Dict[str, List[float]] = defaultdict(list)
    seen_sanctioned_articles: set[UUID] = set()
    sanction_penalty = 0.0

    for f in findings:
        rl = f["risk_level"].value if isinstance(f["risk_level"], RiskLevel) else str(f["risk_level"])
        conf = f["confidence"] if isinstance(f["confidence"], ConfidenceLevel) else ConfidenceLevel(str(f["confidence"]))
        severity_counts[rl] = severity_counts.get(rl, 0) + 1
        total_conf += conf_scores.get(conf, 2)

        if rl == "critique":
            has_unmitigated_critical = True
            has_non_conforme = True
        elif rl in ("eleve", "modere", "a_surveiller"):
            has_non_conforme = True

        domain = _infer_finding_domain(f)
        if rl != "conforme":
            domain_weights[domain].append(weight_by_level.get(rl, 0.0))
        elif w_conforme:
            domain_weights[domain].append(w_conforme)

        # Evaluation des sanctions légales réelles attachées aux articles (dédupliquées par article unique)
        if rl != "conforme" and articles_map:
            for uid in (f.get("matched_articles") or []):
                try:
                    uuid_obj = uid if isinstance(uid, UUID) else UUID(str(uid))
                    if uuid_obj in seen_sanctioned_articles:
                        continue
                    art = articles_map.get(uuid_obj)
                    if art and getattr(art, "has_sanction", False):
                        seen_sanctioned_articles.add(uuid_obj)
                        nature = str(getattr(art, "sanction_nature", "") or "").lower()
                        if "penale" in nature or "prison" in nature:
                            sanction_penalty += 8.0
                        else:
                            sanction_penalty += 4.0
                        break
                except Exception:
                    pass

    # Rendements décroissants par domaine juridique (1.0, 0.5, 0.25, ...)
    raw_score = 0.0
    for weights in domain_weights.values():
        for idx, weight in enumerate(sorted(weights, reverse=True)):
            raw_score += weight * (0.5 ** idx)

    # Plafonnement du malus de sanction légale à +25 max (par article unique)
    raw_score += min(25.0, sanction_penalty)

    if not has_non_conforme:
        global_score = 0
    else:
        # Compression graduée au-delà de 70 pour éviter la saturation prématurée à 100
        if raw_score <= 70.0:
            compressed_score = raw_score
        else:
            compressed_score = 70.0 + 30.0 * (1.0 - math.exp(-(raw_score - 70.0) / 45.0))

        global_score = min(100, max(0, round(compressed_score)))
        if has_unmitigated_critical and global_score < 50:
            global_score = 50

    # Confiance agrégée étalonnée sur les seuils configurés
    avg_conf = (total_conf / len(findings)) if findings else 2.0
    thresh_high = (rule.confidence_threshold_high * 3.0) if rule else 2.5
    thresh_med = (rule.confidence_threshold_medium * 3.0) if rule else 1.5

    if avg_conf >= thresh_high:
        global_confidence = ConfidenceLevel.HIGH
    elif avg_conf >= thresh_med:
        global_confidence = ConfidenceLevel.MEDIUM
    else:
        global_confidence = ConfidenceLevel.LOW

    return severity_counts, global_score, global_confidence


async def persist_audit_report_version(
    session: AsyncSession,
    project_id: UUID,
    audit_result: AuditExecutionResult,
    *,
    version: str = "1.0",
    parent_version_id: Optional[UUID] = None,
) -> ReportVersion:
    """Persist a ReportVersion and its RiskFinding rows (storing matched_articles UUIDs)."""
    project = await session.get(Project, project_id)
    applicable_rule: Optional[ScoringRule] = None
    if project:
        applicable_rule = await resolve_applicable_scoring_rule(
            session,
            country_code=project.country_code,
            sector=project.sector,
            treatments=project.treatments,
        )

    severity_counts, global_score, global_confidence = compute_initial_severity_and_score(
        audit_result.findings,
        rule=applicable_rule,
        articles_map=audit_result.articles_map,
    )

    report_version = ReportVersion(
        project_id=project_id,
        version=version,
        global_score=global_score,
        confidence_global=global_confidence,
        severity_counts=severity_counts,
        report1_markdown=audit_result.report1_markdown,
        report2_markdown=audit_result.report2_markdown,
        parent_version_id=parent_version_id,
    )
    session.add(report_version)
    await session.flush()

    for f in audit_result.findings:
        rl = f["risk_level"] if isinstance(f["risk_level"], RiskLevel) else RiskLevel(str(f["risk_level"]))
        conf = f["confidence"] if isinstance(f["confidence"], ConfidenceLevel) else ConfidenceLevel(str(f["confidence"]))
        matched_article_strs = [str(uid) for uid in (f.get("matched_articles") or [])]
        matched_source_strs = [str(uid) for uid in (f.get("matched_sources") or [])]

        session.add(
            RiskFinding(
                report_version_id=report_version.id,
                clause_ref=f["clause_ref"],
                finding_text=f["finding_text"],
                risk_level=rl,
                confidence=conf,
                matched_sources=matched_source_strs,
                matched_articles=matched_article_strs,
                obsolescence_flag=bool(f.get("obsolescence_flag", False)),
                conflict_flag=bool(f.get("conflict_flag", False)),
                conflict_details=f.get("conflict_details"),
                recommendation=f["recommendation"],
            )
        )

    await session.commit()
    await session.refresh(report_version)
    return report_version


async def get_project_analysis_readiness(
    session: AsyncSession,
    project_id: UUID,
) -> tuple[list[UUID], list[UUID]]:
    """Return (ready_doc_ids, pending_doc_ids) for non-failed documents in a project."""
    docs_res = await session.execute(
        select(Document)
        .options(selectinload(Document.extraction).selectinload(DocumentExtraction.analysis))
        .where(Document.project_id == project_id, Document.status != DocumentStatus.FAILED)
        .order_by(Document.created_at.asc())
        .execution_options(populate_existing=True)
    )
    docs = docs_res.scalars().all()
    ready_doc_ids: list[UUID] = []
    pending_doc_ids: list[UUID] = []
    for doc in docs:
        if (
            doc.status == DocumentStatus.EXTRACTED
            and doc.extraction is not None
            and doc.extraction.analysis is not None
        ):
            ready_doc_ids.append(doc.id)
        else:
            pending_doc_ids.append(doc.id)
    return ready_doc_ids, pending_doc_ids
