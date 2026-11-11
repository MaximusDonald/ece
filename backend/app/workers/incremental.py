from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any
import json

from app.core.config import get_settings
from app.core.utils import ensure_uuid
from app.models.legal import RiskFinding, ReportVersion, RiskLevel, ConfidenceLevel
from app.models.document import Document, DocumentExtraction, DocumentAnalysis
from app.models.user import Project
from app.services.llm_client import get_llm_client
from app.services.diff_engine import compute_diff
from app.workers.celery_app import celery_app
from app.workers.async_runner import run_async_task
from app.workers.task_dispatch import enqueue_document_task

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

llm = get_llm_client()


async def run_incremental_update(report_version_id: UUID, context_data: Dict[str, Any]) -> None:
    """Run incremental update based on complementary context."""
    async with SyncSession() as session:
        result = await session.execute(
            select(ReportVersion)
            .options(
                selectinload(ReportVersion.project).selectinload(Project.documents).selectinload(Document.extraction)
            )
            .where(ReportVersion.id == report_version_id)
        )
        old_report = result.scalar_one_or_none()
        if not old_report or not old_report.project:
            return
        
        try:
            # Get current extraction and analysis
            extraction = None
            if old_report.project.documents and old_report.project.documents[0].extraction:
                extraction = old_report.project.documents[0].extraction
            else:
                # Fallback fetch extraction via project document
                doc_res = await session.execute(
                    select(Document).where(Document.project_id == old_report.project_id)
                )
                first_doc = doc_res.scalars().first()
                if first_doc:
                    ext_res = await session.execute(
                        select(DocumentExtraction).where(DocumentExtraction.document_id == first_doc.id)
                    )
                    extraction = ext_res.scalar_one_or_none()

            if not extraction:
                return
            
            analysis_res = await session.execute(
                select(DocumentAnalysis).where(DocumentAnalysis.extraction_id == extraction.id)
            )
            analysis = analysis_res.scalar_one_or_none()
            if not analysis:
                return
            
            # Update analysis with new context (in practice, would re-run semantic on affected parts)
            # For POC, we'll add the context to vague_zones resolution
            updated_vague_zones = []
            for zone in (analysis.vague_zones or []):
                zone_key = zone.get("clause_ref", "").lower()
                if any(k in zone_key for k in context_data.keys()):
                    # This zone is resolved by new context
                    zone["resolved"] = True
                    zone["resolution"] = context_data
                updated_vague_zones.append(zone)
            
            analysis.vague_zones = updated_vague_zones
            session.add(analysis)
            
            # Re-run legal research only for affected findings without modifying existing report findings
            all_findings = (
                await session.execute(
                    select(RiskFinding).where(RiskFinding.report_version_id == report_version_id)
                )
            ).scalars().all()

            resolved_refs = {z["clause_ref"] for z in updated_vague_zones if z.get("resolved")}
            
            new_findings_data = []
            for f in all_findings:
                f_data = {
                    "clause_ref": f.clause_ref,
                    "finding_text": f.finding_text,
                    "risk_level": f.risk_level.value,
                    "confidence": f.confidence.value,
                    "matched_sources": f.matched_sources,
                    "obsolescence_flag": f.obsolescence_flag,
                    "conflict_flag": f.conflict_flag,
                    "conflict_details": f.conflict_details,
                    "recommendation": f.recommendation,
                }
                if f.clause_ref in resolved_refs:
                    updated_data = await re_run_consensus_for_finding(f, context_data, extraction, analysis)
                    if updated_data:
                        f_data.update(updated_data)
                new_findings_data.append(f_data)
            
            # Create new report version
            new_version_num = increment_version(old_report.version)
            
            # Calculate new scores
            severity_counts = {"critique": 0, "eleve": 0, "modere": 0, "a_surveiller": 0, "conforme": 0}
            for f_data in new_findings_data:
                lvl = f_data["risk_level"]
                severity_counts[lvl] = severity_counts.get(lvl, 0) + 1
            
            weights = {"critique": 25, "eleve": 15, "modere": 10, "a_surveiller": 5, "conforme": 0}
            raw_score = sum(weights.get(level, 0) * count for level, count in severity_counts.items())
            global_score = min(100, raw_score)
            
            # Generate new reports
            report1_md = generate_findings_report(new_findings_data, extraction, analysis)
            report2_md = generate_legal_synthesis_report(new_findings_data)
            
            new_report = ReportVersion(
                project_id=old_report.project_id,
                version=new_version_num,
                global_score=global_score,
                confidence_global=old_report.confidence_global,
                severity_counts=severity_counts,
                report1_markdown=report1_md,
                report2_markdown=report2_md,
                parent_version_id=old_report.id,
            )
            session.add(new_report)
            await session.flush()
            
            # Save new findings instances for new report version
            for f_data in new_findings_data:
                new_finding = RiskFinding(
                    report_version_id=new_report.id,
                    clause_ref=f_data["clause_ref"],
                    finding_text=f_data["finding_text"],
                    risk_level=RiskLevel(f_data["risk_level"]),
                    confidence=ConfidenceLevel(f_data["confidence"]),
                    matched_sources=f_data.get("matched_sources", []),
                    obsolescence_flag=f_data.get("obsolescence_flag", False),
                    conflict_flag=f_data.get("conflict_flag", False),
                    conflict_details=f_data.get("conflict_details"),
                    recommendation=f_data["recommendation"],
                )
                session.add(new_finding)
            
            await session.commit()
            
            # Trigger PDF generation for the new version
            from app.workers.report import report_generation_task
            try:
                enqueue_document_task(report_generation_task, new_report.id, "report")
            except Exception as exc:
                print(f"Unable to queue PDF generation for new report {new_report.id}: {exc}")
            
        except Exception as e:
            print(f"Incremental update error: {e}")


async def re_run_consensus_for_finding(
    finding: RiskFinding,
    context_data: Dict[str, Any],
    extraction: DocumentExtraction,
    analysis: DocumentAnalysis
) -> Dict[str, Any]:
    """Re-run consensus for a single finding with new context."""
    # Simplified: return updated finding based on context
    # In production, would re-run full LLM consensus
    
    updated = {
        "finding_text": finding.finding_text,
        "risk_level": finding.risk_level.value,
        "confidence": finding.confidence.value,
        "matched_sources": finding.matched_sources,
        "obsolescence_flag": finding.obsolescence_flag,
        "conflict_flag": finding.conflict_flag,
        "conflict_details": finding.conflict_details,
        "recommendation": finding.recommendation,
    }
    
    # If context resolves hosting location, update relevant findings
    if "hosting_location" in context_data or "localisation_hebergement" in context_data:
        if "hebergement" in finding.clause_ref.lower() or "stockage" in finding.finding_text.lower():
            updated["risk_level"] = "conforme"
            updated["confidence"] = "high"
            updated["recommendation"] = f"Localisation d'hébergement confirmée : {context_data.get('hosting_location', context_data.get('localisation_hebergement'))}"
    
    return updated


def increment_version(version: str) -> str:
    """Increment version number (1.0 -> 1.1, 1.9 -> 2.0)."""
    parts = version.split(".")
    if len(parts) == 2:
        major, minor = int(parts[0]), int(parts[1])
        if minor >= 9:
            return f"{major + 1}.0"
        return f"{major}.{minor + 1}"
    return f"{version}.1"


def generate_findings_report(findings: List[Dict], extraction: DocumentExtraction, analysis: DocumentAnalysis) -> str:
    """Generate Report 1: Findings (Document Analysis)."""
    from datetime import datetime
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
            md.append(f"\n⚠️ **Conflit de normes** : {f.get('conflict_details', 'Conflit détecté')}")
        if f.get("matched_sources"):
            md.append("\n**Sources** :")
            for sid in f["matched_sources"]:
                md.append(f"- {sid}")
        md.append("\n---\n")
    
    if analysis.vague_zones:
        md.append("## Zones floues nécessitant des précisions\n")
        for z in analysis.vague_zones:
            resolved = " ✅ RÉSOLUE" if z.get("resolved") else ""
            md.append(f"- **{z['clause_ref']}** : {z['description']}{resolved}")
            if z['suggested_fields']:
                md.append(f"  *Champs suggérés* : {', '.join(z['suggested_fields'])}")
    
    return "\n".join(md)


def generate_legal_synthesis_report(findings: List[Dict]) -> str:
    """Generate Report 2: Legal Synthesis."""
    from datetime import datetime
    md = ["# Rapport 2 : Synthèse Juridique & Réglementaire\n"]
    md.append(f"**Date** : {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}\n")
    md.append("## Textes juridiques applicables\n")
    
    source_findings = {}
    for f in findings:
        for sid in f.get("matched_sources", []):
            if sid not in source_findings:
                source_findings[sid] = []
            source_findings[sid].append(f)
    
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
def incremental_update_task(self, report_version_id, context_data: dict):
    """Celery task for incremental update."""
    try:
        run_async_task(run_incremental_update(ensure_uuid(report_version_id), context_data), async_engine)
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
