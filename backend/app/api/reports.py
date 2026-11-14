import re
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional, Dict, Sequence
from datetime import datetime
from minio.error import S3Error

from app.core.database import get_async_session
from app.core.security import get_current_active_user, get_current_workspace_user, require_role
from app.models.user import User, UserRole, Project
from app.models.legal import (
    ReportVersion, RiskFinding, LegalSource,
    RiskLevel, ConfidenceLevel, LegalLevel, SourceStatus
)
from app.schemas.legal import (
    ReportVersionRead, ReportVersionListItem, RiskFindingRead, RiskFindingReviewUpdate,
    LegalSourceRead, LegalSourceCreate, LegalSourceUpdate,
    ReportDiff, DiffLine,
    MatchedSourceDetail, MatchedArticleDetail,
)
from app.schemas.admin import (
    ScoringRuleRead, ScoringRuleCreate, ScoringRuleUpdate,
    LLMConfigRead, LLMConfigCreate, LLMConfigUpdate,
    CountryModuleRead, CountryModuleUpdate,
    AuditLogRead
)
from app.services.diff_engine import compute_diff, compute_diff_summary
from app.services.minio_client import get_minio_client, get_bucket_name, get_presigned_url
from app.services.pdf_generator import generate_pdf_from_markdown

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/projects/{project_id}", response_model=List[ReportVersionListItem])
async def list_report_versions(
    project_id: UUID,
    current_user = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all report versions for a project."""
    from app.models.user import Project
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = select(ReportVersion).where(
        ReportVersion.project_id == project_id
    ).order_by(ReportVersion.created_at.desc())
    
    result = await session.execute(query)
    versions = result.scalars().all()
    
    return versions


@router.get("/{report_version_id}", response_model=ReportVersionRead)
async def get_report_version(
    report_version_id: UUID,
    current_user = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get full report version with findings."""
    report = await session.get(ReportVersion, report_version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Verify org access
    from app.models.user import Project
    project = await session.get(Project, report.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Load findings
    findings_query = select(RiskFinding).where(
        RiskFinding.report_version_id == report_version_id
    )
    findings_result = await session.execute(findings_query)
    findings = findings_result.scalars().all()
    
    report_data = ReportVersionRead.model_validate(report)
    # Note: findings would be loaded separately or via relationship
    
    return report_data


@router.get("/{report_version_id}/findings", response_model=List[RiskFindingRead])
async def get_report_findings(
    report_version_id: UUID,
    risk_level: Optional[RiskLevel] = Query(None),
    confidence: Optional[ConfidenceLevel] = Query(None),
    current_user = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get findings for a report version with filters."""
    report = await session.get(ReportVersion, report_version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    from app.models.user import Project
    project = await session.get(Project, report.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    query = select(RiskFinding).where(RiskFinding.report_version_id == report_version_id)
    
    if risk_level:
        query = query.where(RiskFinding.risk_level == risk_level)
    if confidence:
        query = query.where(RiskFinding.confidence == confidence)
    
    query = query.order_by(RiskFinding.risk_level.desc())
    
    result = await session.execute(query)
    findings = result.scalars().all()
    
    # Batch load matched legal sources (legacy) and canonical LegalArticle citations
    all_source_ids = set()
    all_article_ids = set()
    for f in findings:
        for sid in (f.matched_sources or []):
            try:
                all_source_ids.add(UUID(str(sid)))
            except (ValueError, TypeError):
                continue
        for aid in (f.matched_articles or []):
            try:
                all_article_ids.add(UUID(str(aid)))
            except (ValueError, TypeError):
                continue

    sources_map = {}
    if all_source_ids:
        from app.models.legal import LegalSource
        src_res = await session.execute(select(LegalSource).where(LegalSource.id.in_(all_source_ids)))
        for src in src_res.scalars().all():
            sources_map[src.id] = {
                "id": src.id,
                "title": src.title,
                "authority": src.authority,
                "original_filename": src.original_filename,
                "download_url": src.download_url or src.url_official,
                "level": src.level.value if hasattr(src.level, "value") else str(src.level),
                "article_ref": src.article_ref,
            }

    articles_map = {}
    if all_article_ids:
        from app.models.corpus import LegalArticle, LegalSection, LegalText
        art_stmt = (
            select(LegalArticle, LegalText, LegalSection)
            .join(LegalText, LegalArticle.text_id == LegalText.id)
            .outerjoin(LegalSection, LegalArticle.section_id == LegalSection.id)
            .where(LegalArticle.id.in_(all_article_ids))
        )
        art_res = await session.execute(art_stmt)
        for art, text_obj, sec in art_res.all():
            rule_val = (
                art.compliance_rule_type.value
                if hasattr(art.compliance_rule_type, "value")
                else art.compliance_rule_type
            )
            articles_map[art.id] = {
                "id": art.id,
                "text_code": text_obj.code,
                "text_title": text_obj.title,
                "jurisdiction": text_obj.jurisdiction,
                "authority": text_obj.authority,
                "article_number": art.article_number,
                "title": art.title,
                "section_breadcrumb": sec.breadcrumb if sec else "",
                "full_text": art.full_text,
                "has_sanction": bool(art.has_sanction),
                "sanction_details": art.sanction_details,
                "compliance_rule_type": rule_val,
                "official_url": text_obj.official_url,
            }

    response_items = []
    for f in findings:
        item = RiskFindingRead.model_validate(f)
        item.sources_details = [
            MatchedSourceDetail(**sources_map[UUID(str(sid))])
            for sid in (f.matched_sources or [])
            if UUID(str(sid)) in sources_map
        ]
        item.articles_details = [
            MatchedArticleDetail(**articles_map[UUID(str(aid))])
            for aid in (f.matched_articles or [])
            if UUID(str(aid)) in articles_map
        ]
        response_items.append(item)

    return response_items


@router.patch("/findings/{finding_id}/review", response_model=RiskFindingRead)
async def review_risk_finding(
    finding_id: UUID,
    payload: RiskFindingReviewUpdate,
    current_user=Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Record a human jurist/analyst validation status & legal qualification on a finding."""
    finding = await session.get(RiskFinding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Constat introuvable")

    report = await session.get(ReportVersion, finding.report_version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")

    project = await session.get(Project, report.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    if project.org_id != current_user.org_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Accès refusé à ce constat")

    finding.review_status = payload.review_status
    if payload.legal_nature is not None:
        finding.legal_nature = payload.legal_nature
    if payload.review_note is not None:
        finding.review_note = payload.review_note.strip() or None
    finding.reviewed_by = current_user.id
    finding.reviewed_at = datetime.utcnow()

    session.add(finding)
    await session.commit()
    await session.refresh(finding)
    return RiskFindingRead.model_validate(finding)


@router.post("/{report_version_id}/context", status_code=status.HTTP_202_ACCEPTED)
async def add_complementary_context(
    report_version_id: UUID,
    context_data: dict,
    current_user = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Add complementary context to trigger incremental update."""
    report = await session.get(ReportVersion, report_version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    from app.models.user import Project
    project = await session.get(Project, report.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Check permissions
    if current_user.role not in [UserRole.ORG_ADMIN, UserRole.ANALYST]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Persist complementary context into a consultable/editable project Document
    from app.services.context_document import upsert_context_document
    doc, _ext, _ana = await upsert_context_document(
        session,
        project,
        context_data=context_data,
    )
    await session.commit()

    # Enqueue incremental update task
    from app.workers.incremental import incremental_update_task
    task = incremental_update_task.delay(str(report_version_id), context_data)
    
    return {
        "job_id": task.id,
        "context_document_id": str(doc.id),
        "message": "Incremental update queued",
    }


@router.get("/{report_version_id}/diff", response_model=ReportDiff)
async def get_report_diff(
    report_version_id: UUID,
    compare_with: UUID = Query(..., description="Version ID to compare with"),
    report_type: str = Query("report1", pattern="^(report1|report2)$"),
    current_user = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get diff between two report versions."""
    v1 = await session.get(ReportVersion, compare_with)
    v2 = await session.get(ReportVersion, report_version_id)
    
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Report version not found")
    
    # Verify org access
    from app.models.user import Project
    project = await session.get(Project, v1.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    old_text = v1.report1_markdown if report_type == "report1" else v1.report2_markdown
    new_text = v2.report1_markdown if report_type == "report1" else v2.report2_markdown
    
    diff_lines = compute_diff(old_text, new_text)
    summary = compute_diff_summary(diff_lines)
    
    return ReportDiff(
        version_old=v1.version,
        version_new=v2.version,
        report_type=report_type,
        diff_lines=[line.to_dict() for line in diff_lines],
        summary=summary,
    )


def build_unified_master_report_markdown(
    report: ReportVersion,
    project: Project,
    findings: Sequence[RiskFinding],
    articles_map: Dict[UUID, MatchedArticleDetail],
) -> str:
    """Build a comprehensive unified audit report combining executive summary, analysis, articles, and action matrix."""
    lines: List[str] = []
    lines.append("# RAPPORT GLOBAL DE CONFORMITÉ RÉGLEMENTAIRE & AUDIT JURIDIQUE")
    lines.append("**Plateforme Souveraine d’Audit Documentaire ECO-Compliance Engine (ECE)**\n")

    # 1. Identification
    lines.append("## 1. FICHE D’IDENTIFICATION DE L’AUDIT")
    lines.append(f"- **Projet audité** : {project.name}")
    lines.append(f"- **Juridiction applicable** : {project.country_code or 'Espace Communautaire (Bénin / CEDEAO / UEMOA / OHADA)'}")
    lines.append(f"- **Secteur d’activité** : {project.sector or 'Général / Non spécifié'}")
    treatments_str = ", ".join(project.treatments or []) if project.treatments else "Non spécifiés"
    lines.append(f"- **Traitements de données déclarés** : {treatments_str}")
    lines.append(f"- **Version d’audit** : v{report.version}")
    lines.append(f"- **Date d’audit** : {report.created_at.strftime('%d/%m/%Y à %H:%M:%S UTC')}")

    risk_label = (
        "RISQUE CRITIQUE (Non-conformité majeure / Sanction encourue)"
        if report.global_score >= 70
        else (
            "RISQUE ÉLEVÉ (Formalités préalables obligatoires requises)"
            if report.global_score >= 40
            else "RISQUE MODÉRÉ / SITUATION MAÎTRISÉE"
        )
    )
    conf_val = report.confidence_global.value if hasattr(report.confidence_global, "value") else str(report.confidence_global)
    lines.append(f"- **Score Global de Risque** : **{report.global_score} / 100** — *{risk_label}*")
    lines.append(f"- **Indice de Confiance de l’Évaluation** : **{conf_val.upper()}**\n")

    sev = report.severity_counts or {}
    lines.append("### Répartition des constats de conformité :")
    lines.append(f"- 🔴 **Critique** : {sev.get('critique', 0)}")
    lines.append(f"- 🟠 **Élevé** : {sev.get('eleve', 0)}")
    lines.append(f"- 🟡 **Modéré** : {sev.get('modere', 0)}")
    lines.append(f"- 🔵 **À surveiller** : {sev.get('a_surveiller', 0)}")
    lines.append(f"- 🟢 **Conforme** : {sev.get('conforme', 0)}\n")

    lines.append("---\n")
    lines.append("## 2. SYNTHÈSE EXÉCUTIVE & ANALYSE DOCUMENTAIRE MULTI-AXES")
    lines.append(report.report1_markdown.strip())
    lines.append("\n\n---\n")

    lines.append("## 3. RÉFÉRENTIEL JURIDIQUE & OPPOSABILITÉ DES ARTICLES DE LOI")
    lines.append(report.report2_markdown.strip())
    lines.append("\n\n---\n")

    lines.append("## 4. MATRICE DES CONSTATS DÉTAILLÉS, SANCTIONS ET RECOMMANDATIONS\n")
    if findings:
        for idx, f in enumerate(findings, 1):
            rl = f.risk_level.value if hasattr(f.risk_level, "value") else str(f.risk_level)
            conf = f.confidence.value if hasattr(f.confidence, "value") else str(f.confidence)
            lines.append(f"### Constat {idx} : {f.clause_ref}")
            lines.append(f"- **Niveau de risque** : `{rl.upper()}` | **Confiance** : `{conf.upper()}`")
            lines.append(f"- **Diagnostic** : {f.finding_text}")

            if f.matched_articles:
                lines.append(f"- **Articles applicables** :")
                for aid_str in f.matched_articles:
                    try:
                        aid = UUID(str(aid_str))
                        art = articles_map.get(aid)
                        if art:
                            sanction_tag = ""
                            if art.has_sanction:
                                sanction_tag = f" ⚠️ **[SANCTION : {art.sanction_details or 'Sanction légale pénale ou administrative'}]**"
                            lines.append(f"  - **{art.text_code} - {art.article_number}** ({art.authority}) : *{art.title or ''}*{sanction_tag}")
                    except Exception:
                        pass

            lines.append(f"- **Recommandation opérationnelle** : {f.recommendation}\n")
    else:
        lines.append("*Aucun constat spécifique n’a été relevé pour cette version.*\n")

    lines.append("---\n")
    lines.append("## 5. MENTION LÉGALE & OPPOSABILITÉ")
    lines.append(
        "Ce rapport d’audit global est généré par le moteur **ECO-Compliance Engine (ECE)**. "
        "Les conclusions et citations légales reposent sur les textes normatifs du Master Corpus en vigueur "
        "(Code du Numérique de la République du Bénin, Actes Additionnels et Directives de la CEDEAO, "
        "Réglementation BCEAO / UEMOA sur les services de paiement et Actes Uniformes de l’OHADA). "
        "Ce document consolidé est destiné aux analystes, DPO et directeurs juridiques pour piloter "
        "la conformité réglementaire effective du projet."
    )
    return "\n".join(lines)


@router.get("/{report_version_id}/export")
async def export_report(
    report_version_id: UUID,
    format: str = Query("pdf", pattern="^(pdf|markdown)$"),
    type: str = Query("full", pattern="^(full|report1|report2)$"),
    current_user = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Export a consolidated master report (default: full) or modular report as PDF or Markdown."""
    report = await session.get(ReportVersion, report_version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    project = await session.get(Project, report.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Report not found")

    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", project.name)[:30]

    if type == "full":
        findings_res = await session.execute(
            select(RiskFinding).where(RiskFinding.report_version_id == report_version_id)
        )
        findings = findings_res.scalars().all()

        all_article_ids = set()
        for f in findings:
            for aid in (f.matched_articles or []):
                try:
                    all_article_ids.add(UUID(str(aid)))
                except (ValueError, TypeError):
                    continue

        articles_map: Dict[UUID, MatchedArticleDetail] = {}
        if all_article_ids:
            from app.models.corpus import LegalArticle, LegalSection, LegalText
            art_stmt = (
                select(LegalArticle, LegalText, LegalSection)
                .join(LegalText, LegalArticle.text_id == LegalText.id)
                .outerjoin(LegalSection, LegalArticle.section_id == LegalSection.id)
                .where(LegalArticle.id.in_(all_article_ids))
            )
            art_res = await session.execute(art_stmt)
            for art, text_obj, sec in art_res.all():
                rule_val = (
                    art.compliance_rule_type.value
                    if hasattr(art.compliance_rule_type, "value")
                    else art.compliance_rule_type
                )
                articles_map[art.id] = MatchedArticleDetail(
                    id=art.id,
                    text_code=text_obj.code,
                    text_title=text_obj.title,
                    jurisdiction=text_obj.jurisdiction,
                    authority=text_obj.authority,
                    article_number=art.article_number,
                    title=art.title,
                    section_breadcrumb=sec.breadcrumb if sec else "",
                    full_text=art.full_text,
                    has_sanction=bool(art.has_sanction),
                    sanction_details=art.sanction_details,
                    compliance_rule_type=rule_val,
                    official_url=text_obj.official_url,
                )

        content = build_unified_master_report_markdown(report, project, findings, articles_map)
        filename_base = f"rapport_conformite_complet_{safe_name}_v{report.version}"
    elif type == "report1":
        content = report.report1_markdown
        filename_base = f"ece_analyse_documentaire_{safe_name}_v{report.version}"
    else:
        content = report.report2_markdown
        filename_base = f"ece_synthese_juridique_{safe_name}_v{report.version}"

    if format == "pdf":
        pdf_bytes = generate_pdf_from_markdown(
            content,
            title=f"Rapport d’Audit de Conformité — {project.name} v{report.version}",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )
    else:
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.md"'},
        )


@router.get("/{report_version_id}/download")
async def download_report_pdf(
    report_version_id: UUID,
    type: str = Query("full", pattern="^(full|report1|report2)$"),
    current_user = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Stream a consolidated audit report PDF (default: full unified report) through the authenticated API."""
    report = await session.get(ReportVersion, report_version_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    project = await session.get(Project, report.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", project.name)[:30]

    # If full unified report is requested, generate/render the complete unified document
    if type == "full":
        findings_res = await session.execute(
            select(RiskFinding).where(RiskFinding.report_version_id == report_version_id)
        )
        findings = findings_res.scalars().all()

        all_article_ids = set()
        for f in findings:
            for aid in (f.matched_articles or []):
                try:
                    all_article_ids.add(UUID(str(aid)))
                except (ValueError, TypeError):
                    continue

        articles_map: Dict[UUID, MatchedArticleDetail] = {}
        if all_article_ids:
            from app.models.corpus import LegalArticle, LegalSection, LegalText
            art_stmt = (
                select(LegalArticle, LegalText, LegalSection)
                .join(LegalText, LegalArticle.text_id == LegalText.id)
                .outerjoin(LegalSection, LegalArticle.section_id == LegalSection.id)
                .where(LegalArticle.id.in_(all_article_ids))
            )
            art_res = await session.execute(art_stmt)
            for art, text_obj, sec in art_res.all():
                rule_val = (
                    art.compliance_rule_type.value
                    if hasattr(art.compliance_rule_type, "value")
                    else art.compliance_rule_type
                )
                articles_map[art.id] = MatchedArticleDetail(
                    id=art.id,
                    text_code=text_obj.code,
                    text_title=text_obj.title,
                    jurisdiction=text_obj.jurisdiction,
                    authority=text_obj.authority,
                    article_number=art.article_number,
                    title=art.title,
                    section_breadcrumb=sec.breadcrumb if sec else "",
                    full_text=art.full_text,
                    has_sanction=bool(art.has_sanction),
                    sanction_details=art.sanction_details,
                    compliance_rule_type=rule_val,
                    official_url=text_obj.official_url,
                )

        unified_md = build_unified_master_report_markdown(report, project, findings, articles_map)
        pdf_bytes = generate_pdf_from_markdown(
            unified_md,
            title=f"Rapport d’Audit de Conformité — {project.name} v{report.version}",
        )
        filename = f"rapport_conformite_complet_{safe_name}_v{report.version}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Modular legacy report download
    object_name = report.report1_pdf_minio if type == "report1" else report.report2_pdf_minio
    if not object_name:
        source_md = report.report1_markdown if type == "report1" else report.report2_markdown
        title = "Rapport d'Analyse Documentaire" if type == "report1" else "Synthèse Juridique & Réglementaire"
        pdf_bytes = generate_pdf_from_markdown(source_md, title=f"{title} — {project.name}")
        filename = f"ece_{type}_{safe_name}_v{report.version}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    minio_client = get_minio_client()
    bucket_name = get_bucket_name(str(project.org_id), "reports")
    try:
        minio_client.stat_object(bucket_name, object_name)
        response = minio_client.get_object(bucket_name, object_name)
    except Exception:
        source_md = report.report1_markdown if type == "report1" else report.report2_markdown
        title = "Rapport d'Analyse Documentaire" if type == "report1" else "Synthèse Juridique & Réglementaire"
        pdf_bytes = generate_pdf_from_markdown(source_md, title=f"{title} — {project.name}")
        filename = f"ece_{type}_{safe_name}_v{report.version}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def stream_pdf():
        try:
            while chunk := response.read(1024 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(
        stream_pdf(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ece_{type}_{safe_name}_v{report.version}.pdf"'},
    )
