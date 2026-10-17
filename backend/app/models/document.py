import enum
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import DateTime, String, Enum as SQLEnum, Text, Index
from pgvector.sqlalchemy import Vector


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    FAILED = "failed"


class Document(SQLModel, table=True):
    __tablename__ = "document"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    filename: str = Field(max_length=255)
    document_type: Optional[str] = Field(default=None, max_length=50)
    mime_type: str = Field(max_length=100)
    minio_bucket: str = Field(max_length=100)
    minio_object: str = Field(max_length=255)
    size_bytes: int
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED, sa_column=Column(SQLEnum(DocumentStatus)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    project: "Project" = Relationship(back_populates="documents")
    extraction: Optional["DocumentExtraction"] = Relationship(back_populates="document")


class DocumentExtraction(SQLModel, table=True):
    __tablename__ = "document_extraction"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="document.id", unique=True, index=True)
    markdown: str = Field(sa_column=Column(Text))
    quality_score: float = Field(default=0.0)  # 0.0-1.0
    page_count: int = Field(default=0)
    language: str = Field(default="fr", max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    document: "Document" = Relationship(back_populates="extraction")
    analysis: Optional["DocumentAnalysis"] = Relationship(back_populates="extraction")


class DocumentAnalysis(SQLModel, table=True):
    __tablename__ = "document_analysis"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    extraction_id: UUID = Field(foreign_key="document_extraction.id", unique=True, index=True)
    entities: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # {persons, orgs, locations, data_types, treatments}
    vague_zones: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))  # [{clause_ref, description, suggested_fields}]
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    extraction: "DocumentExtraction" = Relationship(back_populates="analysis")
