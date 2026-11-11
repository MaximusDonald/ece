import spacy
import json
import re
from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import UUID
from datetime import datetime

from app.core.config import get_settings
from app.core.utils import ensure_uuid
from app.models.document import DocumentExtraction, DocumentAnalysis
from app.services.llm_client import get_llm_client
from app.workers.celery_app import celery_app
from app.workers.async_runner import run_async_task
from app.workers.task_dispatch import enqueue_document_task
from app.workers.pipeline_tracker import add_warning, complete_step, fail_step, start_step

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Load spaCy model (install with: python -m spacy download fr_core_news_lg)
try:
    nlp = spacy.load("fr_core_news_lg")
except OSError:
    # Fallback to small model or blank
    nlp = spacy.blank("fr")


async def run_semantic_analysis(document_id: UUID) -> None:
    """Run semantic analysis on extracted document."""
    start_step(document_id, 2, "Repérage des entités et zones à clarifier")
    async with SyncSession() as session:
        # The task receives a document ID; DocumentExtraction has a separate primary key.
        extraction_result = await session.execute(
            select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
        )
        extraction = extraction_result.scalar_one_or_none()
        if not extraction:
            raise RuntimeError("Extraction introuvable pour l’analyse sémantique")

        existing_analysis = await session.execute(
            select(DocumentAnalysis.id).where(DocumentAnalysis.extraction_id == extraction.id)
        )
        if existing_analysis.scalar_one_or_none():
            complete_step(document_id, 2, "L’analyse du contenu est déjà disponible")
        else:
            doc = nlp(extraction.markdown[:100000])
            entities = {
                "persons": [], "organizations": [], "locations": [], "dates": [],
                "money": [], "data_types": [], "treatments": [],
            }
            for ent in doc.ents:
                if ent.label_ in ["PER", "PERSON"]:
                    entities["persons"].append(ent.text)
                elif ent.label_ == "ORG":
                    entities["organizations"].append(ent.text)
                elif ent.label_ in ["LOC", "GPE"]:
                    entities["locations"].append(ent.text)
                elif ent.label_ == "DATE":
                    entities["dates"].append(ent.text)
                elif ent.label_ == "MONEY":
                    entities["money"].append(ent.text)
            for key in entities:
                entities[key] = list(set(entities[key]))

            vague_zones, llm_entities = await classify_clauses_with_llm(
                extraction.markdown, document_id
            )
            for key, values in llm_entities.items():
                entities[key] = list(dict.fromkeys(entities[key] + values))
            analysis = DocumentAnalysis(
                extraction_id=extraction.id,
                entities=entities,
                vague_zones=vague_zones,
            )
            session.add(analysis)
            await session.commit()
            complete_step(document_id, 2, "Entités et zones à clarifier enregistrées")

        start_step(document_id, 3, "Recherche des textes applicables au pays et au secteur")
        from app.workers.legal_research import legal_research_task
        try:
            enqueue_document_task(legal_research_task, document_id, "legal_research")
        except Exception as exc:
            print(f"Unable to queue legal research for {document_id}: {exc}")
            fail_step(document_id, 3)


async def classify_clauses_with_llm(markdown: str, document_id: UUID) -> tuple[list[dict], dict[str, list[str]]]:
    """Extract semantic entities and vague clauses, with verified source excerpts."""
    llm = get_llm_client()

    prompt = f"""Tu es un auditeur juridique senior certifié en conformité numérique et protection des données (Bénin, CEDEAO, UEMOA).

TA MISSION D'AUDIT SÉMANTIQUE :
Analyser avec rigueur le document contractuel ou technique fourni, extraire l'ensemble des entités formelles mentionnées et identifier méthodiquement les clauses à risque ainsi que les omissions légales et zones de flou juridique ("is_vague").

DOCUMENT SOUMIS À L'AUDIT (Extrait textuel) :
\"\"\"
{markdown[:15000]}
\"\"\"

DIRECTIVES PRÉCISES :
1. ENTITÉS NOMMÉES :
   - Extrais : personnes physiques, personnes morales / organisations (responsable de traitement, sous-traitants, destinataires), juridictions / lieux (pays d'hébergement, pays de transfert), dates (durées de conservation, dates d'effet), montants financiers (plafonds, amendes).
   - Catégorise les types de données personnelles mentionnées (ex: état civil, biométrie, coordonnées bancaires, données de santé, logs IP, données de géolocalisation).
   - Recense les traitements décrits (ex: collecte, profilage, conservation en cloud, transfert transfrontalier).

2. CLAUSES & DÉTECTION DES ZONES FLOUES ("is_vague") :
   - Analyse chaque clause relative à la protection des données, à la cybersécurité ou aux flux financiers.
   - Déclare "is_vague": true lorsqu'une clause est incomplète, évasive ou omet des garanties légales impératives prescrites par le Code du numérique ou le RGPD/CEDEAO (ex: absence de finalité précise, absence de durée chiffrée de conservation, formules évasives comme "nous mettons en œuvre des mesures adaptées" sans précision, absence d'information sur les droits d'accès ou les recours APDP).
   - Pour chaque zone floue, remplis impérativement "missing_fields" avec la liste des informations manquantes requises.
   - RÈGLE D'INTÉGRITÉ STRICTE : Le champ "quote" doit être recopié mot à mot depuis le document sans aucune altération ni paraphrase.

RÉPONDS STRICTEMENT EN JSON SELON CE SCHÉMA :
{{
  "entities": {{
    "persons": ["nom"],
    "organizations": ["société / autorité"],
    "locations": ["pays / ville"],
    "dates": ["date / durée"],
    "money": ["montant"],
    "data_types": ["données d'identification", "données bancaires"],
    "treatments": ["hébergement", "partage tiers"]
  }},
  "clauses": [
    {{
      "ref": "Section ou intitulé de la clause",
      "quote": "Extrait textuel exact recopié mot à mot du document",
      "type": "data_protection" | "payment_services" | "cybersecurity" | "general",
      "content": "Résumé fonctionnel de la clause",
      "is_vague": true | false,
      "missing_fields": ["champ_manquant_1", "champ_manquant_2"]
    }}
  ]
}}"""

    try:
        response = await llm.chat_completion(prompt, response_format="json")
        result = json.loads(response)
        raw_entities = result.get("entities", {})
        allowed_entity_types = {
            "persons", "organizations", "locations", "dates", "money", "data_types", "treatments"
        }
        extracted_entities = {
            key: [value.strip() for value in raw_entities.get(key, []) if isinstance(value, str) and value.strip()]
            for key in allowed_entity_types
            if isinstance(raw_entities, dict) and isinstance(raw_entities.get(key, []), list)
        }

        type_labels = {
            "data_protection": "protection des donnees personnelles",
            "payment_services": "services de paiement",
        }
        vague_zones = []
        for clause in result.get("clauses", []):
            if not clause.get("is_vague"):
                continue
            clause_type = clause.get("type", "")
            excerpt, page_number, is_exact = _locate_clause_excerpt(
                markdown, clause.get("quote", ""), clause.get("ref", "")
            )
            description = (
                f"La clause de {type_labels.get(clause_type, 'conformite juridique')} reste trop generale."
            )
            if excerpt:
                location = f"Page {page_number}. " if page_number else ""
                excerpt_label = "Extrait exact" if is_exact else "Passage autour du repere"
                description += f"\n{location}{excerpt_label} : \"{excerpt}\""
            else:
                reference = clause.get("ref") or "non precise"
                description += (
                    f"\nLe repere \"{reference}\" n'a pas ete retrouve dans le texte extrait; "
                    "verifiez cette indication dans le document original."
                )
            vague_zones.append({
                "clause_ref": clause.get("ref", ""),
                "description": description,
                "suggested_fields": clause.get("missing_fields", []),
            })
        return vague_zones, extracted_entities
    except Exception as e:
        print(f"LLM clause classification error: {e}")
        add_warning(document_id, "La detection automatique des zones floues est indisponible; le reste de l'analyse continue.")
        return [], {}


def _locate_clause_excerpt(markdown: str, quote: str, reference: str) -> tuple[str | None, int | None, bool]:
    """Verify the quoted text against extraction before presenting it as a source excerpt."""
    match = None
    excerpt = ""
    is_exact = False
    if quote and len(quote.strip()) >= 12:
        tokens = quote.split()
        pattern = r"\s+".join(re.escape(token) for token in tokens)
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            excerpt = re.sub(r"\s+", " ", match.group()).strip()
            is_exact = True

    if not match and reference:
        reference_match = re.search(re.escape(reference), markdown, re.IGNORECASE)
        if not reference_match:
            section_number = re.search(r"\d+(?:\.\d+)+", reference)
            if section_number:
                heading_pattern = (
                    rf"(?im)^\s*(?:#{{1,6}}\s*)?(?:section\s+)?"
                    rf"{re.escape(section_number.group())}\b.*$"
                )
                reference_match = re.search(heading_pattern, markdown)
        if reference_match:
            excerpt = re.sub(
                r"\s+", " ", markdown[reference_match.start():reference_match.start() + 280]
            ).strip()
            match = reference_match

    if not match:
        return None, None, False

    page_number = None
    for page_heading in re.finditer(r"(?im)^\s*#{1,6}\s*Page\s+(\d+)\s*$", markdown[:match.start()]):
        page_number = int(page_heading.group(1))
    return excerpt[:280], page_number, is_exact


@celery_app.task(bind=True, max_retries=2)
def semantic_analysis_task(self, document_id):
    """Celery task for semantic analysis."""
    try:
        run_async_task(run_semantic_analysis(ensure_uuid(document_id)), async_engine)
    except Exception as exc:
        fail_step(str(document_id), 2, retrying=self.request.retries < self.max_retries)
        self.retry(exc=exc, countdown=60)


