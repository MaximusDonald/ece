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
from app.core.utils import ensure_uuid
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
        findings, global_confidence, sources_map = await run_consensus(
            document_id, extraction, analysis, unique_matches, country_code
        )
        report_version = await create_report_version(
            session, project_id, findings, extraction, analysis, global_confidence, sources_map
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
    """Hybrid search: vector similarity + keyword, prioritizing extracted laws and decrees."""
    # Get embedding for query
    query_embedding = await llm.get_embeddings([query])
    if not query_embedding:
        return []
    
    vec = query_embedding[0]
    
    # Vector similarity search with filters
    # Prioritizes extracted concrete documents (parent_source_id is not null) over generic portals
    sql = text("""
        SELECT id, title, authority, country_code, level, article_ref, url_official, 
               content_hash, content_text, status, effective_date, abrogated_date,
               is_portal, parent_source_id, original_filename, download_url,
               legal_terms, extracted_articles, summary,
               1 - (embedding <=> :vec) AS similarity
        FROM legal_source
        WHERE (country_code = :country OR country_code IS NULL)
          -- SQLAlchemy stores enum member names in PostgreSQL by default.
          AND status::text IN ('VERIFIED', 'TO_VERIFY')
          AND vector_norm(embedding) > 0
          AND (is_portal IS FALSE OR is_portal IS NULL OR parent_source_id IS NOT NULL)
        ORDER BY (CASE WHEN parent_source_id IS NOT NULL THEN 0 ELSE 1 END), embedding <=> :vec
        LIMIT 12
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
                "content_text": row["content_text"][:2000] if row["content_text"] else "",
                "status": row["status"],
                "effective_date": row["effective_date"],
                "abrogated_date": row["abrogated_date"],
                "is_portal": row.get("is_portal", False),
                "parent_source_id": row.get("parent_source_id"),
                "original_filename": row.get("original_filename"),
                "download_url": row.get("download_url"),
                "legal_terms": row.get("legal_terms") or {},
                "extracted_articles": row.get("extracted_articles") or [],
                "summary": row.get("summary"),
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
) -> Tuple[List[Dict], str, Dict[str, Dict]]:
    """Run LLM consensus to match document clauses to legal sources."""
    sources_map: Dict[str, Dict] = {}
    formatted_sources: List[str] = []

    for i, s in enumerate(sources[:15]):
        sid_str = str(s["source_id"])
        sources_map[sid_str] = s
        
        lines = [
            f"SOURCE {i+1} [ID: {sid_str}] (similarité: {s['similarity']:.2f}):",
            f"Titre officiel: {s['title']}",
            f"Autorité: {s['authority']} (Juridiction: {s['country_code'] or 'Supranational'})",
            f"Niveau normatif: {s['level']}",
            f"Référence légale: {s['article_ref']}",
        ]
        if s.get("original_filename"):
            lines.append(f"Fichier PDF d'origine: {s['original_filename']}")
        if s.get("download_url"):
            lines.append(f"URL de téléchargement direct: {s['download_url']}")
        if s.get("summary"):
            lines.append(f"Synthèse du texte: {s['summary']}")
        
        arts = s.get("extracted_articles") or []
        if arts:
            lines.append("Articles & Régimes de sanctions extraits :")
            for art in arts[:8]:
                sanct = f" -> [SANCTION/AMENDE: {art.get('sanction_details')}]" if art.get("has_sanction") else ""
                lines.append(f"  * {art.get('article_ref', '')}: {art.get('title', '')} - {art.get('content_summary', '')}{sanct}")
        elif s.get("content_text"):
            lines.append(f"Extrait textuel: {s['content_text'][:1200]}")
            
        formatted_sources.append("\n".join(lines))
        
    sources_text = "\n\n".join(formatted_sources)
    
    vague_zones_text = "\n".join([
        f"- {z['clause_ref']}: {z['description']} (champs manquants: {', '.join(z['suggested_fields'])})"
        for z in analysis.vague_zones
    ])
    
    prompt = f"""Tu es un collège d'experts et auditeurs juridiques assermentés en conformité réglementaire numérique (Bénin, CEDEAO, UEMOA, BCEAO, OHADA).

TA MISSION D'AUDIT CONTRADICTOIRE :
Confronter avec une rigueur absolue chaque clause du document analysé aux sources juridiques et réglementaires officielles fournies ci-dessous afin de qualifier précisément les risques de non-conformité, d'identifier les sanctions encourues et de prescrire des recommandations correctives.

NATURE DU DOCUMENT AUDITÉ : {extraction.document.document_type or "Document contractuel / technique"}

EXTRAIT DU DOCUMENT AUDITÉ :
\"\"\"
{extraction.markdown[:10000]}
\"\"\"

ZONES FLOUES & OMISSIONS DÉTECTÉES EN ANALYSE PRÉALABLE :
{vague_zones_text or "Aucune omission flagrante détectée"}

CORPUS JURIDIQUE OFFICIEL DE RÉFÉRENCE (SOURCES VALIDÉES) :
{sources_text or "Aucune source spécifique disponible"}

MÉTHODOLOGIE D'ÉVALUATION DES RISQUES :
- CRITIQUE : Violation directe d'une obligation légale impérative sanctionnée pénalement ou administrativement (ex: défaut de consentement ou d'autorisation APDP pour des données sensibles, défaut d'agrément monétique BCEAO, absence totale de base légale).
- ELEVE : Manquement majeur susceptible d'entraîner une mise en demeure ou une sanction pécuniaire (ex: transfert hors CEDEAO sans garanties adéquates, sous-traitance sans convention conforme à l'article 394 du Code du numérique).
- MODERE : Exigence réglementaire satisfaite de manière lacunaire ou mesures de sécurité insuffisantes au regard de la sensibilité des données.
- A_SURVEILLER : Formulation contractuelle perfectible ou ambiguïté rédactionnelle pouvant susciter un différend lors d'un contrôle d'autorité.
- CONFORME : Respect rigoureux, explicite et vérifié des exigences normatives.

MÉTHODOLOGIE DE CONFIANCE :
- HIGH : Au moins 2 sources officielles concordantes, disposition textuelle directe sans ambiguïté.
- MEDIUM : 1 source officielle directe, ou exigence partiellement explicite dans le texte.
- LOW : Omission documentaire, zone floue, ou source générale nécessitant interprétation.

RÈGLES DE TRAÇABILITÉ ET DE PRESCRIPTION :
1. Dans "matched_source_ids", reporte scrupuleusement les IDs exacts des sources fournies qui soutiennent juridiquement ton constat.
2. Dans "finding_text", explicite l'écart juridique constaté entre la clause et la règle légale en citant le texte, l'autorité et le nom du fichier PDF d'origine.
3. Dans "recommendation", rédige une directive corrective opérationnelle claire indiquant la clause de remplacement ou la démarche réglementaire (ex: déclaration préalable auprès de l'APDP Bénin, avenant contractuel sous-traitant).
4. Signale si la source utilisée est potentiellement abrogée ("obsolescence_flag": true) ou s'il existe une divergence de normes entre droit communautaire et national ("conflict_flag": true).

RÉPONDS STRICTEMENT EN JSON CONFORME AU FORMAT :
{{
  "findings": [
    {{
      "clause_ref": "Section ou intitulé de la clause (ex: Section 4.2 - Transferts de données)",
      "finding_text": "Exposé motivé du constat de conformité citant la loi et l'article applicable",
      "risk_level": "conforme" | "a_surveiller" | "modere" | "eleve" | "critique",
      "confidence": "high" | "medium" | "low",
      "matched_source_ids": ["uuid_source_1", "uuid_source_2"],
      "obsolescence_flag": false,
      "conflict_flag": false,
      "conflict_details": null,
      "recommendation": "Recommandation concrète, opérationnelle et prescriptive"
    }}
  ],
  "global_confidence": "high" | "medium" | "low"
}}"""
    
    try:
        response = await llm.chat_completion(prompt, response_format="json")
        result = json.loads(response)
        
        # Convert source IDs back to UUIDs
        for finding in result.get("findings", []):
            finding["matched_sources"] = [
                UUID(sid) for sid in finding.get("matched_source_ids", [])
                if sid in sources_map
            ]
        
        return result.get("findings", []), result.get("global_confidence", "medium"), sources_map
    except Exception as e:
        print(f"Consensus error: {e}")
        add_warning(document_id, "L'analyse de consensus a échoué; les rapports présenteront des constats limités.")
        return [], "low", sources_map


async def create_report_version(
    session: AsyncSession,
    project_id: UUID,
    findings: List[Dict],
    extraction: DocumentExtraction,
    analysis: DocumentAnalysis,
    global_confidence: str = "medium",
    sources_map: Optional[Dict[str, Dict]] = None,
) -> ReportVersion:
    """Create initial report version with rich legal source tracing."""
    if sources_map is None:
        sources_map = {}
        
    # Calculate global score
    severity_counts = {"critique": 0, "eleve": 0, "modere": 0, "a_surveiller": 0, "conforme": 0}
    for f in findings:
        severity_counts[f["risk_level"]] = severity_counts.get(f["risk_level"], 0) + 1
    
    # Simple scoring: critique=25, eleve=15, modere=10, a_surveiller=5, conforme=0
    weights = {"critique": 25, "eleve": 15, "modere": 10, "a_surveiller": 5, "conforme": 0}
    raw_score = sum(weights.get(f["risk_level"], 0) for f in findings)
    global_score = min(100, raw_score)
    
    # Generate report markdown
    report1_md = generate_findings_report(findings, extraction, analysis, sources_map)
    report2_md = generate_legal_synthesis_report(findings, sources_map)
    
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


def generate_findings_report(
    findings: List[Dict],
    extraction: DocumentExtraction,
    analysis: DocumentAnalysis,
    sources_map: Optional[Dict[str, Dict]] = None,
) -> str:
    """Generate Report 1: Findings (Document Analysis)."""
    if sources_map is None:
        sources_map = {}
        
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
            md.append("\n**Sources juridiques de référence** :")
            for sid in f["matched_sources"]:
                src = sources_map.get(str(sid))
                if src:
                    pdf_tag = f" *(Fichier PDF : `{src['original_filename']}`)*" if src.get("original_filename") else ""
                    md.append(f"- **{src['title']}**{pdf_tag} — {src['authority']} ({src.get('article_ref', '')})")
                else:
                    md.append(f"- Source ID : `{sid}`")
        
        md.append("\n---\n")
    
    # Vague zones
    if analysis.vague_zones:
        md.append("## Zones floues nécessitant des précisions\n")
        for z in analysis.vague_zones:
            md.append(f"- **{z['clause_ref']}** : {z['description']}")
            if z['suggested_fields']:
                md.append(f"  *Champs suggérés* : {', '.join(z['suggested_fields'])}")
    
    return "\n".join(md)


def generate_legal_synthesis_report(
    findings: List[Dict],
    sources_map: Optional[Dict[str, Dict]] = None,
) -> str:
    """Generate Report 2: Legal Synthesis."""
    if sources_map is None:
        sources_map = {}
        
    md = ["# Rapport 2 : Synthèse Juridique & Réglementaire\n"]
    md.append(f"**Date** : {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}\n")
    
    # Group by source
    source_findings = {}
    for f in findings:
        for sid in f.get("matched_sources", []):
            sid_str = str(sid)
            if sid_str not in source_findings:
                source_findings[sid_str] = []
            source_findings[sid_str].append(f)
    
    md.append("## Textes juridiques applicables\n")
    if source_findings:
        for sid_str, source_findings_list in source_findings.items():
            src = sources_map.get(sid_str)
            if src:
                pdf_tag = f" *(Fichier PDF : `{src['original_filename']}`)*" if src.get("original_filename") else ""
                md.append(f"### {src['title']}{pdf_tag}")
                md.append(f"**Autorité** : {src['authority']} | **Niveau** : {src['level']} | **Référence légale** : {src.get('article_ref', 'N/A')}\n")
                if src.get("download_url"):
                    md.append(f"**Téléchargement source** : [{src['download_url']}]({src['download_url']})\n")
                if src.get("summary"):
                    md.append(f"> **Synthèse légale** : {src['summary']}\n")
            else:
                md.append(f"### Source : `{sid_str}`\n")
                
            for f in source_findings_list:
                md.append(f"- **{f['clause_ref']}** ({f['risk_level'].upper()}) : {f['finding_text']}")
            md.append("")
    else:
        md.append("*Aucune source juridique spécifique rattachée directement.* \n")
    
    md.append("\n## Recommandations consolidées\n")
    for f in findings:
        if f["risk_level"] in ["critique", "eleve", "modere"]:
            md.append(f"- **{f['clause_ref']}** : {f['recommendation']}")
    
    return "\n".join(md)


@celery_app.task(bind=True, max_retries=2)
def legal_research_task(self, document_id):
    """Celery task for legal research."""
    try:
        run_async_task(run_legal_research(ensure_uuid(document_id)), async_engine)
    except Exception as exc:
        fail_step(str(document_id), 3, retrying=self.request.retries < self.max_retries)
        self.retry(exc=exc, countdown=60)
