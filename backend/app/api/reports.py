from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime

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
    
    return findings


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


from app.models.user import Project