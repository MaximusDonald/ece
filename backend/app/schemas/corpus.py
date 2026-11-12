"""Pydantic schemas for the hierarchical legal corpus (Text -> Section -> Article)."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.corpus import ComplianceRuleType, LegalTextStatus


class LegalTextBase(BaseModel):
    code: str = Field(max_length=60)
    title: str = Field(max_length=500)
    jurisdiction: str = Field(max_length=32)
    authority: str = Field(max_length=255)
    level: str = Field(default="loi", max_length=50)
    publication_date: Optional[date] = None
    status: LegalTextStatus = LegalTextStatus.IN_FORCE
    official_url: Optional[str] = Field(default=None, max_length=1000)
    minio_bucket: str = Field(default="legal-corpus", max_length=100)
    pdf_path: Optional[str] = Field(default=None, max_length=500)
    text_path: Optional[str] = Field(default=None, max_length=500)


class LegalTextRead(LegalTextBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sha256_hash: Optional[str] = None
    total_articles: int
    created_at: datetime
    updated_at: datetime


class LegalSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text_id: UUID
    parent_section_id: Optional[UUID] = None
    level_name: str
    title: str
    breadcrumb: str
    order_index: int
    created_at: datetime


class LegalArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text_id: UUID
    section_id: Optional[UUID] = None
    article_number: str
    order_index: int
    title: Optional[str] = None
    full_text: str
    topics: List[str] = []
    actors: List[str] = []
    has_sanction: bool = False
    sanction_details: Optional[str] = None
    compliance_rule_type: Optional[ComplianceRuleType] = None
    ai_tagged: bool = False
    created_at: datetime
    updated_at: datetime


class CorpusSectionNode(LegalSectionRead):
    article_count: int = 0


class CorpusArticleDetail(LegalArticleRead):
    text_code: str
    text_title: str
    jurisdiction: str
    authority: str
    section_breadcrumb: str = ""
    official_url: Optional[str] = None
    prev_article_id: Optional[UUID] = None
    next_article_id: Optional[UUID] = None
    score: Optional[float] = None


class CorpusArticlePage(BaseModel):
    items: List[CorpusArticleDetail]
    total: int
    skip: int
    limit: int
    mode: str = "keyword"


class CorpusSummary(BaseModel):
    total_texts: int
    total_sections: int
    total_articles: int
    sanctioned_articles: int
    ai_tagged_articles: int
    jurisdictions: List[str] = []


class RegulatoryAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    collection_run_id: Optional[UUID] = None
    jurisdiction: str
    authority: str
    title: str
    detected_url: str
    document_filename: Optional[str] = None
    previous_hash: Optional[str] = None
    new_hash: str
    etag: Optional[str] = None
    change_summary: str
    status: str
    review_note: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    detected_at: datetime


class RegulatoryAlertReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|dismiss)$")
    note: Optional[str] = Field(default=None, max_length=1000)
