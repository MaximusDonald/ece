from celery import Celery
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any
import json
import asyncio

from app.core.config import get_settings
from app.models.legal import RiskFinding, ReportVersion, RiskLevel, ConfidenceLevel
from app.models.document import DocumentExtraction, DocumentAnalysis
from app.services.llm_client import get_llm_client
from app.services.diff_engine import compute_diff
from app.workers.celery_app import celery_app

settings = get_settings()

sync_engine = create_async_engine(
    settings.database_url.replace("+asyncpg", ""),
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(sync_engine, class_=AsyncSession, expire_on_commit=False)

llm = get_llm_client()


async def run_incremental_update(report_version_id: UUID, context_data: Dict[str, Any]) -> None:
    """Run incremental update based on complementary context."""
    async with SyncSession() as session:
        old_report = await session.get(ReportVersion, report_version_id)
        if not old_report:
            return
        
        try:
            # Get current extraction and analysis
            extraction = await session.get(DocumentExtraction, old_report.project.documents[0].extraction.id) if old_report.project.documents else None
            if not extraction:
                return
            
            analysis = await session.get(DocumentAnalysis, extraction.id)
            
            # Update analysis with new context (in practice, would re-run semantic on affected parts)
            # For POC, we'll add the context to vague_zones resolution
            updated_vague_zones = []
            for zone in analysis.vague_zones:
                zone_key = zone.get("clause_ref", "").lower()
                if any(k in zone_key for k in context_data.keys()):
                    # This zone is resolved by new context
                    zone["resolved"] = True
                    zone["resolution"] = context_data
                updated_vague_zones.append(zone)
            
            analysis.vague_zones = updated_vague_zones
            session.add(analysis)
            
            # Re-run legal research only for affected findings
            affected_findings = await session.execute(
                select(RiskFinding).where(
                    RiskFinding.report_version_id == report_version_id,
                    RiskFinding.clause_ref.in_([z["clause_ref"] for z in updated_vague_zones if z.get("resolved")])
                )
            )
            affected_findings = affected_findings.scalars().all()
            
            # For each affected finding, re-run consensus with new context
            for finding in affected_findings:
                # Build updated prompt with context
                new_finding = await re_run_consensus_for_finding(finding, context_data, extraction, analysis)
                if new_finding:
                    finding.finding_text = new_finding["finding_text"]
                    finding.risk_level = RiskLevel(new_finding["risk_level"])
                    finding.confidence = ConfidenceLevel(new_finding["confidence"])
                    finding.matched_sources = new_finding.get("matched_sources", [])
                    finding.obsolescence_flag = new_finding.get("obsolescence_flag", False)
                    finding.conflict_flag = new_finding.get("conflict_flag", False)
                    finding.conflict_details = new_finding.get("conflict_details")
                    finding.recommendation = new_finding["recommendation"]
            
            # Create new report version
            new_version_num = increment_version(old_report.version)
            
            # Regenerate reports
            all_findings = await session.execute(
                select(RiskFinding).where(RiskFinding.report_version_id == report_version_id)
            )
            all_findings = all_findings.scalars().all()
            
            findings_data = [{
                "clause_ref": f.clause_ref,
                "finding_text": f.finding_text,
                "risk_level": f.risk_level.value,
                "confidence": f.confidence.value,
                "matched_sources": f.matched_sources,
                "obsolescence_flag": f.obsolescence_flag,
                "conflict_flag": f.conflict_flag,
                "conflict_details": f.conflict_details,
                "recommendation": f.recommendation,
            } for f in all_findings]
            
            # Calculate new scores
            severity_counts = {"critique": 0, "eleve": 0, "modere": 0, "a_surveiller": 0, "conforme": 0}
            for f in all_findings:
                severity_counts[f.risk_level.value] = severity_counts.get(f.risk_level.value, 0) + 1
            
            weights = {"critique": 25, "eleve": 15, "modere": 10, "a_surveiller": 5, "conforme": 0}
            raw_score = sum(weights.get(level, 0) * count for level, count in severity_counts.items())
            global_score = min(100, raw_score)
            
            # Generate new reports
            report1_md = generate_findings_report(findings_data, extraction, analysis)
            report2_md = generate_legal_synthesis_report(findings_data)
            
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
            
            # Copy findings to new version
            for f in all_findings:
                new_finding = RiskFinding(
                    report_version_id=new_report.id,
                    clause_ref=f.clause_ref,
                    finding_text=f.finding_text,
                    risk_level=f.risk_level,
                    confidence=f.confidence,
                    matched_sources=f.matched_sources,
                    obsolescence_flag=f.obsolescence_flag,
                    conflict_flag=f.conflict_flag,
                    conflict_details=f.conflict_details,
                    recommendation=f.recommendation,
                )
                session.add(new_finding)
            
            await session.commit()
            
            # Generate diffs
            diff1 = compute_diff(old_report.report1_markdown, new_report.report1_markdown)
            diff2 = compute_diff(old_report.report2_markdown, new_report.report2_markdown)
            
            # Store diffs (could be in separate table or computed on demand)
            # For POC, we'll just ensure the diff engine works
            
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
def incremental_update_task(self, report_version_id: str, context_data: dict):
    """Celery task for incremental update."""
    try:
        asyncio.run(run_incremental_update(UUID(report_version_id), context_data))
    except Exception as exc:
        self.retry(exc=exc, countdown=60)