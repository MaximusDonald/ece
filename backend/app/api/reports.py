from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from minio.error import S3Error

from app.core.database import get_async_session
from app.core.security import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.models.legal import (
    ReportVersion, RiskFinding, LegalSource,
    RiskLevel, ConfidenceLevel, LegalLevel, SourceStatus
)
from app.schemas.legal import (
    ReportVersionRead, ReportVersionListItem, RiskFindingRead,
    LegalSourceRead, LegalSourceCreate, LegalSourceUpdate,
    ReportDiff, DiffLine
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
    current_user = Depends(get_current_active_user),
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
    current_user = Depends(get_current_active_user),
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
    current_user = Depends(get_current_active_user),
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
            sources_map[UUID(str(sid))]
            for sid in (f.matched_sources or [])
            if UUID(str(sid)) in sources_map
        ]
        item.articles_details = [
            articles_map[UUID(str(aid))]
            for aid in (f.matched_articles or [])
            if UUID(str(aid)) in articles_map
        ]
        response_items.append(item)

    return response_items


@router.post("/{report_version_id}/context", status_code=status.HTTP_202_ACCEPTED)
async def add_complementary_context(
    report_version_id: UUID,
    context_data: dict,
    current_user = Depends(get_current_active_user),
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
    
    # Enqueue incremental update task
    from app.workers.incremental import incremental_update_task
    task = incremental_update_task.delay(str(report_version_id), context_data)
    
    return {"job_id": task.id, "message": "Incremental update queued"}


@router.get("/{report_version_id}/diff", response_model=ReportDiff)
async def get_report_diff(
    report_version_id: UUID,
    compare_with: UUID = Query(..., description="Version ID to compare with"),
    report_type: str = Query("report1", pattern="^(report1|report2)$"),
    current_user = Depends(get_current_active_user),
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


@router.get("/{report_version_id}/export")
async def export_report(
    report_version_id: UUID,
    format: str = Query("pdf", pattern="^(pdf|markdown)$"),
    type: str = Query("report1", pattern="^(report1|report2)$"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Export report as PDF or Markdown."""
    report = await session.get(ReportVersion, report_version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    from app.models.user import Project
    project = await session.get(Project, report.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if format == "pdf":
        # Return presigned URL for PDF download
        minio_client = get_minio_client()
        bucket_name = get_bucket_name(str(project.org_id), "reports")
        
        pdf_path = report.report1_pdf_minio if type == "report1" else report.report2_pdf_minio
        if not pdf_path:
            raise HTTPException(status_code=404, detail="PDF not yet generated")
        
        url = get_presigned_url(minio_client, bucket_name, pdf_path, expires_seconds=3600)
        return {"url": url, "filename": f"ece_{type}_v{report.version}.pdf"}
    else:
        # Return Markdown content
        content = report.report1_markdown if type == "report1" else report.report2_markdown
        filename = f"ece_{type}_v{report.version}.md"
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )


@router.get("/{report_version_id}/download")
async def download_report_pdf(
    report_version_id: UUID,
    type: str = Query("report1", pattern="^(report1|report2)$"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Stream a report PDF through the authenticated API, not an internal MinIO URL."""
    report = await session.get(ReportVersion, report_version_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    from app.models.user import Project
    project = await session.get(Project, report.project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    object_name = report.report1_pdf_minio if type == "report1" else report.report2_pdf_minio
    if not object_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not yet generated")

    minio_client = get_minio_client()
    bucket_name = get_bucket_name(str(project.org_id), "reports")
    try:
        minio_client.stat_object(bucket_name, object_name)
        response = minio_client.get_object(bucket_name, object_name)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF introuvable dans le stockage") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stockage des rapports indisponible") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Stockage des rapports indisponible") from exc

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
        headers={"Content-Disposition": f'attachment; filename="ece_{type}_v{report.version}.pdf"'},
    )


from app.models.user import Project
