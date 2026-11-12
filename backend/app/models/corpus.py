"""Hierarchical legal knowledge models: LegalText -> LegalSection -> LegalArticle."""

import enum
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Column, Field, Relationship, SQLModel


class LegalTextStatus(str, enum.Enum):
    """Lifecycle status of a sovereign master legal text."""

    IN_FORCE = "in_force"
    REVISED = "revised"
    ABROGATED = "abrogated"


class ComplianceRuleType(str, enum.Enum):
    """Normative nature of a parsed legal article."""

    MANDATORY = "mandatory"
    PROHIBITION = "prohibition"
    CONDITIONAL = "conditional"
    RECOMMENDATION = "recommendation"
    DEFINITION = "definition"
    SANCTION = "sanction"


class LegalText(SQLModel, table=True):
    """Top-level master legal instrument (code, law, treaty, directive, regulation)."""

    __tablename__ = "legal_text"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(max_length=60, unique=True, index=True)
    title: str = Field(max_length=500)
    jurisdiction: str = Field(max_length=32, index=True)
    authority: str = Field(max_length=255)
    level: str = Field(default="loi", max_length=50, index=True)
    publication_date: Optional[date] = Field(default=None, sa_column=Column(Date))
    status: str = Field(
        default=LegalTextStatus.IN_FORCE.value,
        sa_column=Column(String(20), nullable=False, index=True),
    )
    official_url: Optional[str] = Field(default=None, max_length=1000)
    minio_bucket: str = Field(default="legal-corpus", max_length=100)
    pdf_path: Optional[str] = Field(default=None, max_length=500)
    text_path: Optional[str] = Field(default=None, max_length=500)
    sha256_hash: Optional[str] = Field(default=None, max_length=64, index=True)
    total_articles: int = Field(default=0)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )

    sections: List["LegalSection"] = Relationship(
        back_populates="legal_text",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    articles: List["LegalArticle"] = Relationship(
        back_populates="legal_text",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class LegalSection(SQLModel, table=True):
    """Structural division within a LegalText (Livre, Titre, Chapitre, Section, Annexe)."""

    __tablename__ = "legal_section"
    __table_args__ = (
        UniqueConstraint("text_id", "order_index", name="uq_legal_section_text_order"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    text_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("legal_text.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    parent_section_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("legal_section.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    level_name: str = Field(max_length=120)
    title: str = Field(max_length=500)
    breadcrumb: str = Field(default="", max_length=1000)
    order_index: int = Field(default=0, index=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )

    legal_text: LegalText = Relationship(back_populates="sections")
    parent_section: Optional["LegalSection"] = Relationship(
        back_populates="child_sections",
        sa_relationship_kwargs={"remote_side": "LegalSection.id"},
    )
    child_sections: List["LegalSection"] = Relationship(back_populates="parent_section")
    articles: List["LegalArticle"] = Relationship(back_populates="section")


class LegalArticle(SQLModel, table=True):
    """Atomic normative unit containing the verbatim article text, metadata, and embedding."""

    __tablename__ = "legal_article"
    __table_args__ = (
        UniqueConstraint("text_id", "order_index", name="uq_legal_article_text_order"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    text_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("legal_text.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    section_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("legal_section.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    article_number: str = Field(max_length=80, index=True)
    order_index: int = Field(default=0, index=True)
    title: Optional[str] = Field(default=None, max_length=500)
    full_text: str = Field(sa_column=Column(Text, nullable=False))
    topics: List[str] = Field(default=[], sa_column=Column(JSON, nullable=False))
    actors: List[str] = Field(default=[], sa_column=Column(JSON, nullable=False))
    has_sanction: bool = Field(default=False, index=True)
    sanction_details: Optional[str] = Field(default=None, sa_column=Column(Text))
    compliance_rule_type: Optional[str] = Field(
        default=None,
        sa_column=Column(String(30), index=True),
    )
    ai_tagged: bool = Field(default=False, index=True)
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False),
    )

    legal_text: LegalText = Relationship(back_populates="articles")
    section: Optional[LegalSection] = Relationship(back_populates="articles")


class RegulatoryAlertStatus(str, enum.Enum):
    """Lifecycle status of a sentinel regulatory change alert awaiting admin validation."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    DISMISSED = "dismissed"


class RegulatoryAlert(SQLModel, table=True):
    """Alert generated when a watched official URL changes or publishes a new normative act."""

    __tablename__ = "regulatory_alert"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("legal_source.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    collection_run_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("source_collection_run.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    jurisdiction: str = Field(default="BJ", max_length=32, index=True)
    authority: str = Field(default="", max_length=255)
    title: str = Field(max_length=500)
    detected_url: str = Field(max_length=1000)
    document_filename: Optional[str] = Field(default=None, max_length=500)
    previous_hash: Optional[str] = Field(default=None, max_length=64)
    new_hash: str = Field(max_length=64, index=True)
    etag: Optional[str] = Field(default=None, max_length=255)
    change_summary: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(
        default=RegulatoryAlertStatus.PENDING_REVIEW.value,
        sa_column=Column(String(30), nullable=False, index=True),
    )
    review_note: Optional[str] = Field(default=None, sa_column=Column(Text))
    reviewed_by: Optional[UUID] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, nullable=False, index=True),
    )
