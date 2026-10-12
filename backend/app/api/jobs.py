from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.core.database import get_async_session
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.document import JobResponse, JobStatus, JobStep

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get job status for polling."""
    from app.workers.celery_app import celery_app
    
    task_result = celery_app.AsyncResult(str(job_id))
    
    steps = [
        JobStep(step=1, name="Extraction"),
        JobStep(step=2, name="Analyse Sémantique"),
        JobStep(step=3, name="Recherche Juridique"),
        JobStep(step=4, name="Scoring"),
        JobStep(step=5, name="Génération Rapport"),
    ]
    
    if task_result.state == "PENDING":
        job_status = JobStatus.PENDING
    elif task_result.state == "STARTED":
        job_status = JobStatus.PROCESSING
        # Could parse task info for current step from task.info
    elif task_result.state == "SUCCESS":
        job_status = JobStatus.COMPLETED
        for s in steps:
            s.status = JobStatus.COMPLETED
            s.completed_at = datetime.utcnow()
    elif task_result.state == "FAILURE":
        job_status = JobStatus.FAILED
    elif task_result.state == "RETRY":
        job_status = JobStatus.PROCESSING
    else:
        job_status = JobStatus.PROCESSING
    
    return JobResponse(
        job_id=job_id,
        status=job_status,
        steps=steps,
        result=task_result.result if task_result.state == "SUCCESS" else None,
        error=str(task_result.info) if task_result.state == "FAILURE" else None,
    )


@router.post("/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: UUID,
    current_user = Depends(get_current_active_user),
):
    """Retry a failed job."""
    from app.workers.celery_app import celery_app
    
    task_result = celery_app.AsyncResult(str(job_id))
    
    if task_result.state != "FAILURE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed jobs can be retried"
        )
    
    # Retry the task
    task_result.retry()
    
    return {"message": "Job requeued", "job_id": job_id}