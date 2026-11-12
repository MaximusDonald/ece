"""Structured deterministic + AI semantic tagging for parsed LegalArticle rows."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from app.models.corpus import ComplianceRuleType, LegalArticle

logger = logging.getLogger(__name__)

_SANCTION_RE = re.compile(
    r"(est\s+puni\w*|sera\s+puni\w*|emprisonnement|r[ée]clusion|amende\s+de|francs\s+CFA|FCFA|"
    r"sanction\s+p[ée]cuniaire|sanctions?\s+administratives?|retrait\s+d['’]agr[ée]ment|"
    r"astreinte\s+de|peines?\s+encourues?)",
    re.I,
)
_PROHIBITION_RE = re.compile(
    r"\b(est\s+interdit|sont\s+interdit|il\s+est\s+interdit|ne\s+peut\s+(?:en\s+aucun\s+cas|pas)|"
    r"nul\s+ne\s+peut|interdiction\s+de)\b",
    re.I,
)
_CONDITIONAL_RE = re.compile(
    r"\b(sous\s+r[ée]serve|autorisation\s+pr[ée]alable|d[ée]claration\s+pr[ée]alable|"
    r"agr[ée]ment\s+pr[ée]alable|[àa]\s+condition\s+que|ne\s+peuvent\s+[êe]tre\s+.*?\s+que\s+si|"
    r"lorsque|sauf\s+(?:si|cas))\b",
    re.I,
)
_MANDATORY_RE = re.compile(
    r"\b(est\s+tenu\w*\s+de|sont\s+tenu\w*\s+de|doit\b|doivent\b|obligatoire\w*|il\s+incombe|"
    r"veille\s+[àa]|prend\s+(?:les\s+)?mesures)\b",
    re.I,
)
_DEFINITION_RE = re.compile(
    r"(au\s+sens\s+du\s+pr[ée]sent|on\s+entend\s+par|est\s+entend[ue]\s+par|d[ée]finitions?)",
    re.I,
)


class ArticleTagPayload(BaseModel):
    """Structured AI output schema for a single LegalArticle."""

    article_id: str
    topics: List[str] = Field(default_factory=list, max_length=6)
    actors: List[str] = Field(default_factory=list, max_length=5)
    has_sanction: bool = False
    sanction_details: Optional[str] = None
    compliance_rule_type: ComplianceRuleType = ComplianceRuleType.MANDATORY


class BatchTaggingPayload(BaseModel):
    """Wrapper schema for batched LegalArticle semantic tagging."""

    items: List[ArticleTagPayload] = Field(default_factory=list)


def extract_deterministic_signals(full_text: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Extract deterministic baseline compliance signals (sanctions & rule type) without LLM calls."""
    combined = f"{title or ''}\n{full_text}".strip()
    has_sanction = bool(_SANCTION_RE.search(combined))

    sanction_details: Optional[str] = None
    if has_sanction:
        sentences = re.split(r"(?<=[\.\!\?])\s+", full_text.replace("\n", " "))
        matched = [s.strip() for s in sentences if _SANCTION_RE.search(s)]
        if matched:
            sanction_details = " ".join(matched)[:600]

    if _DEFINITION_RE.search(combined[:300]):
        rule_type = ComplianceRuleType.DEFINITION.value
    elif has_sanction and re.search(r"\b(est\s+puni|sera\s+puni|passible\s+d['’]une)\b", combined, re.I):
        rule_type = ComplianceRuleType.SANCTION.value
    elif _PROHIBITION_RE.search(combined):
        rule_type = ComplianceRuleType.PROHIBITION.value
    elif _CONDITIONAL_RE.search(combined):
        rule_type = ComplianceRuleType.CONDITIONAL.value
    elif _MANDATORY_RE.search(combined):
        rule_type = ComplianceRuleType.MANDATORY.value
    else:
        rule_type = ComplianceRuleType.RECOMMENDATION.value

    return {
        "has_sanction": has_sanction,
        "sanction_details": sanction_details,
        "compliance_rule_type": rule_type,
    }


def _normalize_slugs(values: Sequence[str], max_items: int) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for val in values:
        slug = re.sub(r"[^a-z0-9_]+", "_", val.strip().lower()).strip("_")
        if slug and slug not in seen:
            seen.add(slug)
            cleaned.append(slug[:60])
        if len(cleaned) >= max_items:
            break
    return cleaned


def _build_batch_prompt(articles: Sequence[LegalArticle], breadcrumbs: Dict[UUID, str]) -> str:
    payload = []
    for art in articles:
        payload.append(
            {
                "article_id": str(art.id),
                "article_number": art.article_number,
                "section": breadcrumbs.get(art.section_id, "") if art.section_id else "",
                "text": art.full_text[:1800],
            }
        )
    return (
        "Tu es un juriste expert en droit du numérique, protection des données, cybersécurité, "
        "fintech UEMOA/BCEAO, propriété intellectuelle OAPI et droit OHADA.\n"
        "Pour CHAQUE article ci-dessous, retourne un objet JSON exact respectant ce schéma :\n"
        '{"items": [{"article_id": "...", "topics": ["snake_case_tag"], "actors": ["snake_case_actor"], '
        '"has_sanction": true|false, "sanction_details": "texte exact de la peine/amende ou null", '
        '"compliance_rule_type": "mandatory|prohibition|conditional|recommendation|definition|sanction"}]}\n\n'
        "Règles strictes :\n"
        "- Garde exactement le même `article_id`.\n"
        "- `topics` : 1 à 5 mots-clés normalisés en français snake_case (ex: transfert_transfrontalier, autorisation_prealable, donnees_sante, monnaie_electronique, signature_electronique, conservation_donnees, notification_violation, brevet_logiciel).\n"
        "- `actors` : 1 à 4 acteurs concernés en snake_case (ex: responsable_traitement, sous_traitant, apdp, anssi, bceao, personne_concernee, emetteur_monnaie_electronique, operateur, autorite_judiciaire).\n"
        "- `has_sanction` : true uniquement si l'article prévoit une peine, amende, sanction administrative ou astreinte.\n"
        "- `sanction_details` : résume fidèlement les montants/durées cités dans l'article sans inventer, sinon null.\n"
        "- Réponds UNIQUEMENT avec du JSON valide.\n\n"
        f"ARTICLES :\n{json.dumps(payload, ensure_ascii=False)}"
    )


async def _call_gemini_json(prompt: str) -> str:
    """Call Gemini directly with structured JSON mode and model fallback on transient 503/429."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY non configurée pour le balisage IA.")

    client = genai.Client(api_key=api_key)
    models = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.6-flash", "gemini-3.8-flash"]
    last_err: Optional[Exception] = None
    for model_name in models:
        try:
            resp = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
            text = (resp.text or "").strip()
            if text:
                return text
        except Exception as exc:
            last_err = exc
            logger.warning("AI tagging fallback from %s: %s", model_name, str(exc)[:180])
            await asyncio.sleep(1.5)
    raise RuntimeError(f"Échec de tous les modèles LLM pour le balisage: {last_err}")


async def tag_articles_batch(
    articles: Sequence[LegalArticle],
    breadcrumbs: Dict[UUID, str],
) -> int:
    """Run Pydantic-validated AI tagging on a batch of LegalArticle objects; returns tagged count."""
    if not articles:
        return 0

    prompt = _build_batch_prompt(articles, breadcrumbs)
    raw_json = await _call_gemini_json(prompt)
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.S).strip()

    try:
        parsed = BatchTaggingPayload.model_validate_json(cleaned)
    except ValidationError as exc:
        logger.error("Invalid Pydantic JSON in batch tagging: %s", exc)
        return 0

    by_id = {str(a.id): a for a in articles}
    updated = 0
    for item in parsed.items:
        art = by_id.get(item.article_id)
        if not art:
            continue
        art.topics = _normalize_slugs(item.topics, 6)
        art.actors = _normalize_slugs(item.actors, 5)
        art.has_sanction = bool(item.has_sanction)
        art.sanction_details = item.sanction_details.strip()[:800] if item.sanction_details else None
        art.compliance_rule_type = item.compliance_rule_type.value
        art.ai_tagged = True
        updated += 1
    return updated
