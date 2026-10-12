import enum
from datetime import datetime, date
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import DateTime, String, Enum as SQLEnum, Text, Date, Index, ForeignKey
from pgvector.sqlalchemy import Vector


class LegalLevel(str, enum.Enum):
    LOI = "loi"
    DECRET = "décret"
    REGLEMENT = "règlement"
    DIRECTIVE = "directive"
    ACTE = "acte"
    INSTRUCTION = "instruction"
    DECISION = "décision"
    RECOMMENDATION = "recommandation"
    FORMULAIRE = "formulaire"
    GUIDE = "guide"


class SourceStatus(str, enum.Enum):
    VERIFIED = "verified"
    TO_VERIFY = "to_verify"
    REPLACED = "replaced"
    ARCHIVED = "archived"
    DISPUTED = "disputed"
    UNOFFICIAL = "unofficial"


class LegalSource(SQLModel, table=True):
    __tablename__ = "legal_source"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=500)
    authority: str = Field(max_length=255)
    country_code: Optional[str] = Field(default=None, max_length=2, index=True)  # None = supranational
    level: LegalLevel = Field(sa_column=Column(SQLEnum(LegalLevel), index=True))
    article_ref: str = Field(max_length=100)
    url_official: str = Field(max_length=1000)
    content_hash: str = Field(max_length=64, index=True)  # SHA-256
    content_text: str = Field(sa_column=Column(Text))  # for embedding
    status: SourceStatus = Field(default=SourceStatus.TO_VERIFY, sa_column=Column(SQLEnum(SourceStatus), index=True))
    effective_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    abrogated_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    embedding: List[float] = Field(default=[], sa_column=Column(Vector(1536)))  # OpenAI text-embedding-3-small
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # For vector similarity search
    __table_args__ = (
        Index("ix_legal_source_embedding_cosine", "embedding", postgresql_using="ivfflat", postgresql_with={"lists": 100}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )


class RiskLevel(str, enum.Enum):
    CONFORME = "conforme"
    A_SURVEILLER = "a_surveiller"
    MODERE = "modere"
    ELEVE = "eleve"
    CRITIQUE = "critique"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskFinding(SQLModel, table=True):
    __tablename__ = "risk_finding"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    report_version_id: UUID = Field(foreign_key="report_version.id", index=True)
    clause_ref: str = Field(max_length=200)
    finding_text: str = Field(sa_column=Column(Text))
    risk_level: RiskLevel = Field(sa_column=Column(SQLEnum(RiskLevel), index=True))
    confidence: ConfidenceLevel = Field(sa_column=Column(SQLEnum(ConfidenceLevel)))
    matched_sources: List[UUID] = Field(default=[], sa_column=Column(JSON))  # LegalSource IDs
    obsolescence_flag: bool = Field(default=False)
    conflict_flag: bool = Field(default=False)
    conflict_details: Optional[str] = Field(default=None, sa_column=Column(Text))
    recommendation: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    report_version: "ReportVersion" = Relationship(back_populates="findings")


class ReportVersion(SQLModel, table=True):
    __tablename__ = "report_version"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    version: str = Field(max_length=20)  # "1.0", "1.1", "2.0"
    global_score: int = Field(default=0)  # 0-100
    confidence_global: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, sa_column=Column(SQLEnum(ConfidenceLevel)))
    severity_counts: Dict[str, int] = Field(default={}, sa_column=Column(JSON))  # {critique: 2, eleve: 5, ...}
    report1_markdown: str = Field(sa_column=Column(Text))  # Findings
    report2_markdown: str = Field(sa_column=Column(Text))  # Legal Synthesis
    report1_pdf_minio: Optional[str] = Field(default=None, max_length=255)
    report2_pdf_minio: Optional[str] = Field(default=None, max_length=255)
    parent_version_id: Optional[UUID] = Field(default=None, foreign_key="report_version.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    project: "Project" = Relationship(back_populates="report_versions")
    findings: List[RiskFinding] = Relationship(back_populates="report_version")
    parent_version: Optional["ReportVersion"] = Relationship(
        back_populates="child_versions",
        sa_relationship_kwargs={"remote_side": "ReportVersion.id"}
    )
    child_versions: List["ReportVersion"] = Relationship(
        back_populates="parent_version",
        sa_relationship_kwargs={"foreign_keys": "ReportVersion.parent_version_id"}
    )


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", index=True)
    action: str = Field(max_length=100)
    entity_type: str = Field(max_length=50)
    entity_id: Optional[UUID] = Field(default=None, index=True)
    diff: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False, index=True))
    
    __table_args__ = (
        Index("ix_audit_log_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
    )