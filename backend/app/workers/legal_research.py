from celery import Celery
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker
from sqlalchemy import text
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any, Tuple
import json

from app.core.config import get_settings
from app.models.document import Document, DocumentExtraction, DocumentAnalysis
from app.models.legal import LegalSource, RiskFinding, ReportVersion, RiskLevel, ConfidenceLevel
from app.services.llm_client import get_llm_client
from app.workers.celery_app import celery_app
from app.workers.async_runner import run_async_task
from app.workers.task_dispatch import enqueue_document_task
from app.workers.pipeline_tracker import add_warning, bind_report, complete_step, fail_step, start_step

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

llm = get_llm_client()


async def run_legal_research(document_id: UUID) -> None:
    """Run legal research (RAG) on analyzed document."""
    start_step(document_id, 3, "Recherche des sources applicables")
    async with SyncSession() as session:
        result = await session.execute(
            select(DocumentExtraction)
            .options(
                selectinload(DocumentExtraction.document).selectinload(Document.project),
                selectinload(DocumentExtraction.analysis),
            )
            .where(DocumentExtraction.document_id == document_id)
        )
        extraction = result.scalar_one_or_none()
        if not extraction:
            raise RuntimeError("Extraction introuvable pour la recherche juridique")
        analysis = extraction.analysis
        if not analysis:
            raise RuntimeError("Analyse semantique introuvable pour la recherche juridique")

        project_id = extraction.document.project_id
        country_code = extraction.document.project.country_code
        queries = build_search_queries(analysis, extraction)
        all_matches = []
        for query in queries:
            all_matches.extend(await hybrid_search(session, query, country_code))
        unique_matches = deduplicate_matches(all_matches)
        findings, global_confidence = await run_consensus(
            document_id, extraction, analysis, unique_matches, country_code
        )
        report_version = await create_report_version(
            session, project_id, findings, extraction, analysis, global_confidence
        )
        bind_report(document_id, report_version.id)
        complete_step(
            document_id,
            3,
            "Les constats et les deux rapports Markdown sont enregistres",
            report_version.id,
        )
        start_step(document_id, 4, "Calcul du score et du niveau de confiance")
        from app.workers.scoring import scoring_task
        try:
            enqueue_document_task(scoring_task, report_version.id, "scoring")
        except Exception as exc:
            print(f"Unable to queue scoring for report {report_version.id}: {exc}")
            fail_step(document_id, 4)


def build_search_queries(analysis: DocumentAnalysis, extraction: DocumentExtraction) -> List[str]:
    """Build search queries from analysis."""
    queries = []
    doc_type = extraction.document.document_type or "document non precise"
    
    # From vague zones
    for zone in analysis.vague_zones:
        queries.append(f"{doc_type} {zone.get('description', '')} {zone.get('clause_ref', '')}")
    
    # From entities
    for data_type in analysis.entities.get("data_types", []):
        queries.append(f"{doc_type} protection {data_type} {extraction.document.project.country_code}")
    
    for treatment in analysis.entities.get("treatments", []):
        queries.append(f"{treatment} conformité {extraction.document.project.country_code}")
    
    # Default queries based on project config
    project = extraction.document.project
    if "data_protection" in project.treatments:
        queries.append(f"protection données personnelles {project.country_code}")
    if "payment_services" in project.treatments:
        queries.append(f"services paiement monnaie électronique {project.country_code}")
    
    return queries[:10]  # Limit queries


async def hybrid_search(session: AsyncSession, query: str, country_code: str) -> List[Dict]:
    """Hybrid search: vector similarity + keyword."""
    # Get embedding for query
    query_embedding = await llm.get_embeddings([query])
    if not query_embedding:
        return []
    
    vec = query_embedding[0]
    
    # Vector similarity search with filters
    # PGVector cosine similarity: 1 - (embedding <=> query_vec)
    sql = text("""
        SELECT id, title, authority, country_code, level, article_ref, url_official, 
               content_hash, content_text, status, effective_date, abrogated_date,
               1 - (embedding <=> :vec) AS similarity
        FROM legal_source
        WHERE (country_code = :country OR country_code IS NULL)
          AND status IN ('verified', 'to_verify')
          AND vector_norm(embedding) > 0
        ORDER BY embedding <=> :vec
        LIMIT 10
    """)
    
    result = await session.execute(sql, {"vec": vec, "country": country_code})
    rows = result.mappings().all()
    
    matches = []
    for row in rows:
        if row["similarity"] > 0.3:  # Threshold
            matches.append({
                "source_id": row["id"],
                "title": row["title"],
                "authority": row["authority"],
                "country_code": row["country_code"],
                "level": row["level"],
                "article_ref": row["article_ref"],
                "url_official": row["url_official"],
                "content_hash": row["content_hash"],
                "content_text": row["content_text"][:2000],  # Truncate
                "status": row["status"],
                "effective_date": row["effective_date"],
                "abrogated_date": row["abrogated_date"],
                "similarity": float(row["similarity"]),
            })
    
    return matches


def deduplicate_matches(matches: List[Dict]) -> List[Dict]:
    """Deduplicate matches by source_id, keeping highest similarity."""
    seen = {}
    for m in matches:
        sid = m["source_id"]
        if sid not in seen or m["similarity"] > seen[sid]["similarity"]:
            seen[sid] = m
    return list(seen.values())


async def run_consensus(
    document_id: UUID,
    extraction: DocumentExtraction,
    analysis: DocumentAnalysis,
    sources: List[Dict],
    country_code: str
) -> Tuple[List[Dict], str]:
    """Run LLM consensus to match document clauses to legal sources."""
    
    # Prepare context for LLM
    sources_text = "\n\n".join([
        f"SOURCE {i+1} (similarité: {s['similarity']:.2f}):\n"
        f"Titre: {s['title']}\n"
        f"Autorité: {s['authority']}\n"
        f"Pays: {s['country_code'] or 'Supranational'}\n"
        f"Niveau: {s['level']}\n"
        f"Article: {s['article_ref']}\n"
        f"URL: {s['url_official']}\n"
        f"Hash: {s['content_hash']}\n"
        f"Statut: {s['status']}\n"
        f"Date entrée en vigueur: {s['effective_date']}\n"
        f"Date abrogation: {s['abrogated_date']}\n"
        f"Extrait: {s['content_text']}"
        for i, s in enumerate(sources[:15])  # Limit context
    ])
    
    vague_zones_text = "\n".join([
        f"- {z['clause_ref']}: {z['description']} (champs manquants: {', '.join(z['suggested_fields'])})"
        for z in analysis.vague_zones
    ])
    
    prompt = f"""Tu es un auditeur juridique expert CEDEAO/UEMOA/OHADA/Bénin.
Analyse le document ci-dessous et les sources juridiques fournies pour produire des constats de conformité.

NATURE DU DOCUMENT : {extraction.document.document_type or "Non precise"}

DOCUMENT ANALYSÉ :
{extraction.markdown[:10000]}

ZONES FLOUES DÉTECTÉES :
{vague_zones_text or "Aucune"}

SOURCES JURIDIQUES DISPONIBLES :
{sources_text or "Aucune source trouvée"}

INSTRUCTIONS :
Pour chaque clause pertinente du document, détermine :
1. Le niveau de risque (conforme, a_surveiller, modere, eleve, critique)
2. Le niveau de confiance (high: ≥2 sources concordantes sans ambiguïté, medium: 1 source ou info partielle, low: info manquante/zone floue)
3. Les sources correspondantes (IDs)
4. Si le texte source est abrogé (obsolescence_flag)
5. S'il y a conflit entre niveau communautaire et national (conflict_flag)
6. Une recommandation concrète

RÈGLES DE CONFIANCE :
- HIGH : Au moins 2 sources officielles concordantes, pas d'ambiguïté
- MEDIUM : 1 source officielle, ou info partiellement explicite dans le document
- LOW : Information manquante, zone floue, ou source unique non vérifiée

CONFLITS : Signale si une source CEDEAO/UEMOA/OHADA contredit une source nationale béninoise.

RÉPONDS EN JSON STRICT :
{{
  "findings": [
    {{
      "clause_ref": "section 1.1",
      "finding_text": "Description du constat",
      "risk_level": "modere",
      "confidence": "medium",
      "matched_source_ids": ["uuid1", "uuid2"],
      "obsolescence_flag": false,
      "conflict_flag": false,
      "conflict_details": null,
      "recommendation": "Action recommandée"
    }}
  ],
  "global_confidence": "medium"
}}"""
    
    try:
        response = await llm.chat_completion(prompt, response_format="json")
        result = json.loads(response)
        
        # Convert source IDs back to UUIDs
        for finding in result.get("findings", []):
            finding["matched_sources"] = [
                UUID(sid) for sid in finding.get("matched_source_ids", [])
            ]
        
        return result.get("findings", []), result.get("global_confidence", "medium")
    except Exception as e:
        print(f"Consensus error: {e}")
        add_warning(document_id, "L'analyse de consensus a échoué; les rapports présenteront des constats limités.")
        return [], "low"


async def create_report_version(
    session: AsyncSession,
    project_id: UUID,
    findings: List[Dict],
    extraction: DocumentExtraction,
    analysis: DocumentAnalysis,
    global_confidence: str = "medium",
) -> ReportVersion:
    """Create initial report version."""
    # Calculate global score
    severity_counts = {"critique": 0, "eleve": 0, "modere": 0, "a_surveiller": 0, "conforme": 0}
    for f in findings:
        severity_counts[f["risk_level"]] = severity_counts.get(f["risk_level"], 0) + 1
    
    # Simple scoring: critique=25, eleve=15, modere=10, a_surveiller=5, conforme=0
    weights = {"critique": 25, "eleve": 15, "modere": 10, "a_surveiller": 5, "conforme": 0}
    raw_score = sum(weights.get(f["risk_level"], 0) for f in findings)
    global_score = min(100, raw_score)
    
    # Generate report markdown
    report1_md = generate_findings_report(findings, extraction, analysis)
    report2_md = generate_legal_synthesis_report(findings)
    
    report_version = ReportVersion(
        project_id=project_id,
        version="1.0",
        global_score=global_score,
        confidence_global=ConfidenceLevel(global_confidence),
        severity_counts=severity_counts,
        report1_markdown=report1_md,
        report2_markdown=report2_md,
    )
    session.add(report_version)
    await session.flush()
    
    # Save findings
    for f in findings:
        risk_finding = RiskFinding(
            report_version_id=report_version.id,
            clause_ref=f["clause_ref"],
            finding_text=f["finding_text"],
            risk_level=RiskLevel(f["risk_level"]),
            confidence=ConfidenceLevel(f["confidence"]),
            matched_sources=f.get("matched_sources", []),
            obsolescence_flag=f.get("obsolescence_flag", False),
            conflict_flag=f.get("conflict_flag", False),
            conflict_details=f.get("conflict_details"),
            recommendation=f["recommendation"],
        )
        session.add(risk_finding)
    
    await session.commit()
    await session.refresh(report_version)
    
    return report_version


def generate_findings_report(findings: List[Dict], extraction: DocumentExtraction, analysis: DocumentAnalysis) -> str:
    """Generate Report 1: Findings (Document Analysis)."""
    md = ["# Rapport 1 : Analyse Documentaire Interne\n"]
    md.append(f"**Document** : {extraction.document.filename}")
    md.append(f"**Qualité extraction** : {extraction.quality_score:.0%}")
    md.append(f"**Pages** : {extraction.page_count}")
    md.append(f"**Langue** : {extraction.language}")
    md.append(f"**Date** : {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}\n")
    
    md.append("## Constats par clause\n")
    
    for f in findings:
        risk_emoji = {
            "critique": "🔴", "eleve": "🟠", "modere": "🟡",
            "a_surveiller": "🔵", "conforme": "🟢"
        }.get(f["risk_level"], "⚪")
        
        conf_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(f["confidence"], "⚪")
        
        md.append(f"### {risk_emoji} {f['clause_ref']} — {f['risk_level'].upper()} ({conf_emoji} {f['confidence']})")
        md.append(f"\n**Constat** : {f['finding_text']}")
        md.append(f"\n**Recommandation** : {f['recommendation']}")
        
        if f.get("obsolescence_flag"):
            md.append("\n⚠️ **Attention** : Source potentiellement abrogée détectée")
        if f.get("conflict_flag"):
            md.append(f"\n⚠️ **Conflit de normes** : {f.get('conflict_details', 'Conflit détecté entre sources')}")
        
        if f.get("matched_sources"):
            md.append("\n**Sources** :")
            for sid in f["matched_sources"]:
                md.append(f"- {sid}")
        
        md.append("\n---\n")
    
    # Vague zones
    if analysis.vague_zones:
        md.append("## Zones floues nécessitant des précisions\n")
        for z in analysis.vague_zones:
            md.append(f"- **{z['clause_ref']}** : {z['description']}")
            if z['suggested_fields']:
                md.append(f"  *Champs suggérés* : {', '.join(z['suggested_fields'])}")
    
    return "\n".join(md)


def generate_legal_synthesis_report(findings: List[Dict]) -> str:
    """Generate Report 2: Legal Synthesis."""
    md = ["# Rapport 2 : Synthèse Juridique & Réglementaire\n"]
    md.append(f"**Date** : {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}\n")
    
    # Group by source
    source_findings = {}
    for f in findings:
        for sid in f.get("matched_sources", []):
            if sid not in source_findings:
                source_findings[sid] = []
            source_findings[sid].append(f)
    
    md.append("## Textes juridiques applicables\n")
    for sid, source_findings_list in source_findings.items():
        md.append(f"### Source : {sid}")
        for f in source_findings_list:
            md.append(f"- **{f['clause_ref']}** ({f['risk_level']}) : {f['finding_text'][:100]}...")
    
    md.append("\n## Recommandations consolidées\n")
    for f in findings:
        if f["risk_level"] in ["critique", "eleve", "modere"]:
            md.append(f"- **{f['clause_ref']}** : {f['recommendation']}")
    
    return "\n".join(md)


@celery_app.task(bind=True, max_retries=2)
def legal_research_task(self, document_id: str):
    """Celery task for legal research."""
    try:
        run_async_task(run_legal_research(UUID(document_id)), async_engine)
    except Exception as exc:
        fail_step(document_id, 3, retrying=self.request.retries < self.max_retries)
        self.retry(exc=exc, countdown=60)
