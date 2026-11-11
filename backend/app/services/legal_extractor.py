"""AI-powered legal analysis, structured qualification, and normative extraction."""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.legal import LegalLevel
from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

LEGAL_ANALYSIS_SYSTEM_PROMPT = """Tu es un juriste expert et auditeur en droit du numérique africain (République du Bénin, espace CEDEAO, UEMOA, OHADA, BCEAO).

TA MISSION D'EXTRACTION & QUALIFICATION :
Analyser avec une rigueur absolue le document juridique extrait lors de la collecte robotisée sur un portail officiel institutionnel, qualifier sa portée légale et en extraire la structure normative sans RIEN inventer.

DIRECTIVES D'ANALYSE STRICTES :
1. QUALIFICATION NORMATIVE ("is_legal_norm") :
   - Détermine si le document constitue une norme juridique authentique (loi, décret, arrêté, décision, délibération, directive, guide officiel ou formulaire obligatoire = true).
   - Indique false s'il s'agit d'une simple page d'actualité, d'un billet de blog ou d'un communiqué informatif sans portée légale.
2. TITRE & RÉFÉRENCE FORMELLE :
   - Extrais le titre officiel complet et exact.
   - Extrais le numéro d'acte officiel exact (ex: "Loi n° 2017-20", "Décret n° 2020-045", "Délibération n° 2021-02", "Instruction n° 001-01-2018").
3. NIVEAU NORMATIF & DOMAINE :
   - "legal_level" : "loi", "décret", "règlement", "directive", "acte", "instruction", "décision", "recommandation", "guide", "formulaire".
   - "domain" : "data_protection", "cybersecurity", "ecommerce", "payment_services", "digital_identity" ou "global".
4. SYNTHÈSE EXÉCUTIVE ("executive_summary") :
   - Rédige une synthèse juridique claire (3 à 5 phrases) définissant l'objet du texte, ses destinataires assujettis et les obligations de conformité imposées.
5. GLOSSAIRE JURIDIQUE ("legal_terms") :
   - Extrais les définitions formelles énoncées dans le texte (termes juridiques clés tels que "Responsable de traitement", "Données sensibles", "Violation de données", "Émetteur de monnaie électronique", etc.).
6. DÉCOUPAGE DES ARTICLES & RÉGIMES DE SANCTIONS ("key_articles") :
   - Pour chaque article identifié : sa référence ("Article 12", "Article 384"), son intitulé, l'obligation imposée et TRÈS PRÉCISÉMENT les sanctions applicables (amendes forfaitaires en FCFA, peines de prison, amendes jusqu'à 4% du CA, astreintes ou interdictions).

Tu dois renvoyer UNIQUEMENT un objet JSON valide conforme à ce schéma :
{
  "is_legal_norm": true,
  "official_title": "string",
  "act_number": "string ou null",
  "legal_level": "loi | décret | règlement | directive | acte | instruction | décision | recommandation | guide | formulaire",
  "authority": "string (ex: APDP Bénin, Assemblée Nationale, BCEAO, etc.)",
  "effective_date": "YYYY-MM-DD ou null",
  "domain": "data_protection | cybersecurity | ecommerce | payment_services | digital_identity | global",
  "executive_summary": "string",
  "legal_terms": [
    {
      "term": "string",
      "definition": "string"
    }
  ],
  "key_articles": [
    {
      "article_ref": "string",
      "title": "string",
      "obligation": "string",
      "sanctions": "string ou null"
    }
  ]
}
"""


class LegalAnalysisResult(BaseModel):
    is_legal_norm: bool = True
    official_title: str
    act_number: Optional[str] = None
    legal_level: str = "loi"
    authority: str
    effective_date: Optional[str] = None
    domain: str = "data_protection"
    executive_summary: str
    legal_terms: List[Dict[str, str]] = Field(default_factory=list)
    key_articles: List[Dict[str, Any]] = Field(default_factory=list)


class LegalLLMExtractor:
    def __init__(self):
        self.llm_client = get_llm_client()

    async def analyze_document(
        self, text: str, original_filename: str, source_hint: str = ""
    ) -> LegalAnalysisResult:
        """Analyze legal document using LLM with structured JSON output and fallback heuristics."""
        # Trim text excerpt for prompt
        sample_text = text[:15000]

        prompt = (
            f"Fichier source : {original_filename}\n"
            f"Indice source : {source_hint}\n\n"
            f"Extrait du document juridique officiel :\n"
            f"\"\"\"\n{sample_text}\n\"\"\"\n\n"
            f"Remplis le schéma JSON d'analyse juridique :"
        )

        try:
            raw_response = await self.llm_client.chat_completion(
                prompt=prompt,
                response_format="json",
                system_prompt=LEGAL_ANALYSIS_SYSTEM_PROMPT,
                temperature=0.1,
            )

            # Clean JSON formatting if wrapped in code blocks
            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                clean_json = re.sub(r"\s*```$", "", clean_json)

            data = json.loads(clean_json)
            level = self._normalize_level(data.get("legal_level", "loi"))

            return LegalAnalysisResult(
                is_legal_norm=bool(data.get("is_legal_norm", True)),
                official_title=str(data.get("official_title") or original_filename),
                act_number=data.get("act_number"),
                legal_level=level,
                authority=str(data.get("authority") or "Autorité de Régulation"),
                effective_date=data.get("effective_date"),
                domain=str(data.get("domain") or "data_protection"),
                executive_summary=str(data.get("executive_summary") or "Texte juridique extrait."),
                legal_terms=data.get("legal_terms", []),
                key_articles=data.get("key_articles", []),
            )
        except Exception as exc:
            logger.warning("LLM legal extraction fallback triggered: %s", exc)
            return self._heuristic_fallback(text, original_filename)

    def _normalize_level(self, level_str: str) -> str:
        s = level_str.lower().strip()
        for enum_val in LegalLevel:
            if enum_val.value in s:
                return enum_val.value
        if "loi" in s or "code" in s:
            return LegalLevel.LOI.value
        if "decret" in s or "décret" in s:
            return LegalLevel.DECRET.value
        if "deliberat" in s or "délibérat" in s or "decis" in s or "décis" in s:
            return LegalLevel.DECISION.value
        if "reglement" in s or "règlement" in s:
            return LegalLevel.REGLEMENT.value
        return LegalLevel.LOI.value

    def _heuristic_fallback(self, text: str, original_filename: str) -> LegalAnalysisResult:
        """Deterministic heuristic extraction when LLM API keys are unset or throttled."""
        first_lines = [l.strip() for l in text.splitlines() if l.strip()][:10]
        first_block = " ".join(first_lines)

        # Detect act number
        act_match = re.search(
            r'(Loi\s+n°?\s*[\d\-]+|Décret\s+n°?\s*[\d\-]+|Délibération\s+n°?\s*[\d\-]+|Arrêté\s+n°?\s*[\d\-]+)',
            first_block,
            re.IGNORECASE,
        )
        act_number = act_match.group(1) if act_match else None

        # Level
        level = "loi"
        if act_number:
            lower_act = act_number.lower()
            if "décret" in lower_act or "decret" in lower_act:
                level = "décret"
            elif "délibération" in lower_act or "decision" in lower_act:
                level = "décision"

        # Detect articles via flexible regex
        article_matches = re.findall(
            r'(Article\s+\d+[\w\-]*)[\s:\.\-]*([^\n\r]*)',
            text,
            re.IGNORECASE,
        )
        key_articles = []
        for ref, title_part in article_matches[:15]:
            clean_ref = ref.strip()
            clean_title = title_part.strip() or f"Dispositions de l'{clean_ref}"
            key_articles.append({
                "article_ref": clean_ref,
                "title": clean_title,
                "obligation": f"Dispositions normatives relatives à {clean_title}",
                "sanctions": None,
            })

        # Key terms based on legal vocabulary presence
        terms_found = []
        potential_terms = [
            ("Données à caractère personnel", "Toute information relative à une personne physique identifiée ou identifiable."),
            ("Responsable de traitement", "Personne morale ou physique qui détermine les finalités et moyens du traitement."),
            ("Sous-traitant", "Personne qui traite des données pour le compte du responsable."),
            ("Consentement préalable", "Manifestation de volonté libre, spécifique, éclairée et univoque."),
            ("Délégué à la protection des données", "Personne chargée de veiller à la conformité interne."),
        ]
        for term, definition in potential_terms:
            if term.lower() in text.lower():
                terms_found.append({"term": term, "definition": definition})

        clean_title = act_number or original_filename.replace("_", " ").replace(".pdf", "").title()

        return LegalAnalysisResult(
            is_legal_norm=True,
            official_title=clean_title,
            act_number=act_number,
            legal_level=level,
            authority="Autorité Nationale (APDP / République du Bénin)",
            domain="data_protection",
            executive_summary=f"Cadre légal extrait automatiquement : {clean_title}. Comprend {len(article_matches)} articles identifiés.",
            legal_terms=terms_found,
            key_articles=key_articles,
        )
