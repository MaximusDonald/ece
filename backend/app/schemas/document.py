from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.document import DocumentStatus
from enum import Enum


# Document Schemas
class DocumentBase(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int


class DocumentCreate(BaseModel):
    # Multipart upload handled separately
    pass


class DocumentRead(DocumentBase):
    id: UUID
    project_id: UUID
    status: DocumentStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


# Document Extraction Schemas
class DocumentExtractionBase(BaseModel):
    markdown: str
    quality_score: float = Field(ge=0.0, le=1.0)
    page_count: int
    language: str


class DocumentExtractionRead(DocumentExtractionBase):
    id: UUID
    document_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


# Document Analysis Schemas
class VagueZone(BaseModel):
    clause_ref: str
    description: str
    suggested_fields: List[str] = []


class DocumentAnalysisBase(BaseModel):
    entities: Dict[str, Any] = {}
    vague_zones: List[VagueZone] = []


class DocumentAnalysisRead(DocumentAnalysisBase):
    id: UUID
    extraction_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


# Job Status Schemas
class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStep(BaseModel):
    step: int
    name: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    steps: List[JobStep] = []
    estimated_remaining_seconds: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


from enum import Enum