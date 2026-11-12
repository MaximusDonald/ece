from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from urllib.parse import quote
from minio.error import S3Error
import os
import io
import uuid

from app.core.database import get_async_session
from app.core.security import get_current_active_user, get_current_workspace_user, require_role
from app.models.user import User, UserRole, Project
from app.models.document import Document, DocumentExtraction, DocumentAnalysis, DocumentStatus
from app.models.legal import ReportVersion
from app.schemas.document import DocumentRead, DocumentExtractionRead, DocumentAnalysisRead, DocumentPipelineRead, JobResponse, JobStatus, JobStep
from app.services.minio_client import get_minio_client
from app.workers.celery_app import celery_app
from app.workers.extraction import extract_document_task
from app.workers.task_dispatch import enqueue_document_task
from app.workers.pipeline_tracker import (
    STAGES,
    get_pipeline_state,
    initialize_pipeline,
    start_step,
)

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
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Upload a document for analysis."""
    # Verify project access
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
        document_type=(document_type.strip()[:50] or None) if document_type else None,
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
    initialize_pipeline(document.id, document.filename)
    enqueue_document_task(extract_document_task, document.id, "extraction")
    
    return document


@router.get("", response_model=List[DocumentRead])
async def list_documents(
    project_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List documents for a project."""
    # Verify project access
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
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get document details."""
    # Verify project access
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document


@router.get("/{document_id}/download")
async def download_document(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Stream an uploaded document after validating its organization and project scope."""
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    minio_client = get_minio_client()
    try:
        minio_client.stat_object(document.minio_bucket, document.minio_object)
        response = minio_client.get_object(document.minio_bucket, document.minio_object)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable dans le stockage") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Le stockage des fichiers est indisponible") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Le stockage des fichiers est indisponible") from exc

    def stream_file():
        try:
            while chunk := response.read(1024 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(
        stream_file(),
        media_type=document.mime_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(document.filename, safe='')}"},
    )


@router.get("/{document_id}/extraction", response_model=DocumentExtractionRead)
async def get_document_extraction(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get document extraction results."""
    # Verify project access
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Document not found")

    extraction_result = await session.execute(
        select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
    )
    extraction = extraction_result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    return extraction


@router.get("/{document_id}/analysis", response_model=DocumentAnalysisRead)
async def get_document_analysis(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get document analysis results."""
    # Verify project access
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")

    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # The route receives a document ID, while DocumentExtraction has its own
    # primary key. Look up the extraction through its document_id foreign key.
    extraction_result = await session.execute(
        select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
    )
    extraction = extraction_result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    analysis_result = await session.execute(
        select(DocumentAnalysis).where(DocumentAnalysis.extraction_id == extraction.id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis


@router.get("/{document_id}/pipeline", response_model=DocumentPipelineRead)
async def get_document_pipeline(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return document-level progress for the full five-stage analysis."""
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    state = get_pipeline_state(document_id)
    if state:
        return state

    # Older uploads predate the Redis progress record. The UI will call resume
    # once for these documents, and the resume route reconstructs the next step.
    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": "not_started",
        "current_step": None,
        "progress": 0,
        "steps": [
            {"step": n, "key": key, "label": label, "status": "pending", "message": "En attente"}
            for n, key, label in STAGES
        ],
        "error": None,
        "warnings": [],
        "report_version_id": None,
        "updated_at": document.updated_at,
    }


@router.post("/{document_id}/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_document_pipeline(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Resume the next missing or stalled stage without duplicating an active task."""
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pipeline = get_pipeline_state(document_id)
    if pipeline and pipeline.get("status") == "completed":
        return {"status": "completed", "stage": None, "job_id": None}

    extraction_result = await session.execute(
        select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
    )
    extraction = extraction_result.scalar_one_or_none()
    analysis_exists = False
    if extraction:
        analysis_result = await session.execute(
            select(DocumentAnalysis.id).where(DocumentAnalysis.extraction_id == extraction.id)
        )
        analysis_exists = analysis_result.scalar_one_or_none() is not None

    if not pipeline:
        initialize_pipeline(document.id, document.filename)
        pipeline = get_pipeline_state(document_id)

    # Reconcile progress against persisted products first. Redis task state is
    # only an execution aid; documents, analyses and reports remain the source of truth.
    step = pipeline.get("current_step")
    if not extraction:
        step = 1
    elif not analysis_exists:
        step = 2
    elif step not in {4, 5}:
        step = 3

    if step == 1:
        task, stage, task_argument = extract_document_task, "extraction", document_id
    elif step == 2:
        from app.workers.semantic import semantic_analysis_task
        task, stage, task_argument = semantic_analysis_task, "semantic", document_id
    elif step == 3:
        from app.workers.legal_research import legal_research_task
        task, stage, task_argument = legal_research_task, "legal_research", document_id
    else:
        report_id = pipeline.get("report_version_id")
        report = await session.get(ReportVersion, UUID(report_id)) if report_id else None
        if not report:
            from app.workers.legal_research import legal_research_task
            task, stage, task_argument = legal_research_task, "legal_research", document_id
            step = 3
        elif step == 4:
            from app.workers.scoring import scoring_task
            task, stage, task_argument = scoring_task, "scoring", report.id
        else:
            from app.workers.report import report_generation_task
            task, stage, task_argument = report_generation_task, "report", report.id
            step = 5

    start_step(document_id, step, "Reprise de l etape en attente")
    task_id, queued = enqueue_document_task(task, task_argument, stage)
    return {
        "status": "queued" if queued else "already_in_progress",
        "stage": stage,
        "job_id": task_id or None,
    }


# Job status endpoint
@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    project_id: UUID,
    job_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get job status for polling."""
    # Verify project access
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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: UUID,
    document_id: UUID,
    current_user: User = Depends(get_current_workspace_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a document and its associated storage and records."""
    # Verify project access
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")

    document = await session.get(Document, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # 1. Try to remove object from MinIO
    try:
        minio_client = get_minio_client()
        if minio_client.bucket_exists(document.minio_bucket):
            minio_client.remove_object(document.minio_bucket, document.minio_path)
    except Exception:
        # Pass or log if MinIO file already absent
        pass

    # 2. Delete extractions and analyses
    extractions = (
        await session.execute(
            select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
        )
    ).scalars().all()

    for ext in extractions:
        analyses = (
            await session.execute(
                select(DocumentAnalysis).where(DocumentAnalysis.extraction_id == ext.id)
            )
        ).scalars().all()
        for analysis in analyses:
            await session.delete(analysis)
        await session.delete(ext)

    # 3. Delete document itself
    await session.delete(document)
    await session.commit()
    return None
