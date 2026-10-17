import spacy
import json
from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import UUID
from datetime import datetime

from app.core.config import get_settings
from app.models.document import DocumentExtraction, DocumentAnalysis
from app.services.llm_client import get_llm_client
from app.workers.celery_app import celery_app
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

            vague_zones = await classify_clauses_with_llm(extraction.markdown)
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


async def classify_clauses_with_llm(markdown: str) -> list[dict]:
    """Use LLM to classify clauses and detect vague zones."""
    llm = get_llm_client()
    
    prompt = f"""Analyse ce document juridique et identifie :
1. Les clauses liées à la protection des données personnelles
2. Les clauses liées aux services de paiement / monnaie électronique
3. Les zones floues ou trop générales qui nécessitent des précisions

Document (extrait) :
{markdown[:15000]}

Réponds en JSON strict :
{{
  "clauses": [
    {{"ref": "section 1.2", "type": "data_protection", "content": "...", "is_vague": false}},
    {{"ref": "section 2.1", "type": "payment_services", "content": "...", "is_vague": true, "missing_fields": ["localisation_hebergement", "sous_traitant"]}}
  ]
}}"""
    
    try:
        response = await llm.chat_completion(prompt, response_format="json")
        result = json.loads(response)
        vague_zones = []
        for clause in result.get("clauses", []):
            if clause.get("is_vague"):
                vague_zones.append({
                    "clause_ref": clause.get("ref", ""),
                    "description": f"Clause {clause.get('type', '')} trop générale",
                    "suggested_fields": clause.get("missing_fields", []),
                })
        return vague_zones
    except Exception as e:
        print(f"LLM clause classification error: {e}")
        add_warning(document_id, "La détection automatique des zones floues est indisponible; le reste de l’analyse continue.")
        return []


@celery_app.task(bind=True, max_retries=2)
def semantic_analysis_task(self, document_id: str):
    """Celery task for semantic analysis."""
    try:
        asyncio.run(run_semantic_analysis(UUID(document_id)))
    except Exception as exc:
        fail_step(document_id, 2, retrying=self.request.retries < self.max_retries)
        self.retry(exc=exc, countdown=60)


import asyncio
