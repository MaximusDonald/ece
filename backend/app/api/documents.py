from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime
import os

from app.core.database import get_async_session
from app.core.security import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.models.document import Document, DocumentExtraction, DocumentAnalysis, DocumentStatus
from app.models.legal import ReportVersion
from app.schemas.document import DocumentRead, DocumentExtractionRead, DocumentAnalysisRead, JobResponse, JobStatus, JobStep
from app.services.minio_client import get_minio_client
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/markdown",
    "text/plain",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def validate_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: PDF, DOCX, Markdown, Text"
        )
    # Note: size check happens on read


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Upload a document for analysis."""
    # Verify project access
    from app.models.user import Project
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permissions
    if current_user.role not in [UserRole.ORG_ADMIN, UserRole.ANALYST]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Validate file
    validate_file(file)
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB"
        )
    
    # Generate unique object name
    import uuid
    file_ext = os.path.splitext(file.filename)[1].lower()
    object_name = f"{uuid.uuid4()}{file_ext}"
    
    # Upload to MinIO
    minio_client = get_minio_client()
    bucket_name = f"org-{current_user.org_id}-documents"
    
    # Ensure bucket exists
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
    
    minio_client.put_object(
        bucket_name,
        object_name,
        io.BytesIO(content),
        len(content),
        content_type=file.content_type,
    )
    
    # Create document record
    document = Document(
        project_id=project_id,
        filename=file.filename,
        mime_type=file.content_type,
        minio_bucket=bucket_name,
        minio_object=object_name,
        size_bytes=len(content),
        status=DocumentStatus.UPLOADED,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    
    # Enqueue extraction task
    from app.workers.extraction import extract_document_task
    task = extract_document_task.delay(str(document.id))
    
    # Update document with job ID (we could store this in a separate job table)
    # For now, we'll track via the task ID returned
    
    return document


@router.get("", response_model=List[DocumentRead])
async def list_documents(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List documents for a project."""
    # Verify project access
    from app.models.user import Project
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    result = await session.execute(query)
    documents = result.scalars().all()
    
    return documents


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get document details."""
    # Verify project access
    from app.models.user import Project
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document


@router.get("/{document_id}/extraction", response_model=DocumentExtractionRead)
async def get_document_extraction(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get document extraction results."""
    # Verify project access
    from app.models.user import Project
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    extraction = await session.get(DocumentExtraction, document_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    return extraction


@router.get("/{document_id}/analysis", response_model=DocumentAnalysisRead)
async def get_document_analysis(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get document analysis results."""
    # Verify project access
    from app.models.user import Project
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get extraction first
    extraction = await session.get(DocumentExtraction, document_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    analysis = await session.get(DocumentAnalysis, extraction.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis


# Job status endpoint
@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    project_id: UUID,
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get job status for polling."""
    # Verify project access
    from app.models.user import Project
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get Celery task result
    task_result = celery_app.AsyncResult(str(job_id))
    
    steps = [
        JobStep(step=1, name="Extraction"),
        JobStep(step=2, name="Semantic Analysis"),
        JobStep(step=3, name="Legal Research"),
        JobStep(step=4, name="Scoring"),
        JobStep(step=5, name="Report Generation"),
    ]
    
    if task_result.state == "PENDING":
        job_status = JobStatus.PENDING
    elif task_result.state == "STARTED":
        job_status = JobStatus.PROCESSING
        # Could parse task info for current step
    elif task_result.state == "SUCCESS":
        job_status = JobStatus.COMPLETED
        for s in steps:
            s.status = JobStatus.COMPLETED
            s.completed_at = datetime.utcnow()
    elif task_result.state == "FAILURE":
        job_status = JobStatus.FAILED
    else:
        job_status = JobStatus.PROCESSING
    
    return JobResponse(
        job_id=job_id,
        status=job_status,
        steps=steps,
        result=task_result.result if task_result.state == "SUCCESS" else None,
        error=str(task_result.info) if task_result.state == "FAILURE" else None,
    )


import io