from uuid import UUID
from datetime import datetime, date
from typing import Optional, List, Dict, Literal, Any, Union
from pydantic import BaseModel, Field
from app.models.legal import RiskLevel, ConfidenceLevel, LegalLevel, SourceStatus, SourceCollectionRunStatus


# Legal Source Schemas
class LegalSourceBase(BaseModel):
    title: str = Field(max_length=500)
    authority: str = Field(max_length=255)
    country_code: Optional[str] = Field(default=None, max_length=2)
    level: LegalLevel
    article_ref: str = Field(max_length=255)
    url_official: str = Field(max_length=1000)
    content_hash: str = Field(max_length=64)
    content_text: str
    status: SourceStatus = SourceStatus.TO_VERIFY
    effective_date: Optional[Union[datetime, date]] = None
    abrogated_date: Optional[Union[datetime, date]] = None
    is_portal: bool = False
    parent_source_id: Optional[UUID] = None
    original_filename: Optional[str] = None
    download_url: Optional[str] = None
    minio_object_path: Optional[str] = None
    legal_terms: Optional[Dict[str, Any]] = None
    extracted_articles: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    crawl_depth: int = 2


class LegalSourceCreate(LegalSourceBase):
    content_text: Optional[str] = None
    content_hash: Optional[str] = None
    collection_enabled: bool = False


class LegalSourceUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    authority: Optional[str] = Field(default=None, max_length=255)
    country_code: Optional[str] = Field(default=None, max_length=2)
    level: Optional[LegalLevel] = None
    article_ref: Optional[str] = Field(default=None, max_length=255)
    url_official: Optional[str] = Field(default=None, max_length=1000)
    content_text: Optional[str] = None
    status: Optional[SourceStatus] = None
    abrogated_date: Optional[Union[datetime, date]] = None
    replacement_source_id: Optional[UUID] = None
    collection_enabled: Optional[bool] = None
    is_portal: Optional[bool] = None
    crawl_depth: Optional[int] = None


class LegalSourceRead(LegalSourceBase):
    id: UUID
    embedding: List[float] = []
    collection_enabled: bool = False
    last_collection_at: Optional[datetime] = None
    last_successful_collection_at: Optional[datetime] = None
    last_collection_status: Optional[str] = None
    last_collection_run_id: Optional[UUID] = None
    source_etag: Optional[str] = None
    source_last_modified: Optional[str] = None
    child_documents_count: Optional[int] = 0
    parent_title: Optional[str] = None
    parent_authority: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SourceCollectionRunRead(BaseModel):
    id: UUID
    source_id: UUID
    trigger_type: str
    triggered_by: Optional[UUID] = None
    status: SourceCollectionRunStatus
    requested_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    http_status_code: Optional[int] = None
    previous_hash: Optional[str] = None
    collected_hash: Optional[str] = None
    changed: Optional[bool] = None
    discovered_urls_count: int = 0
    downloaded_files_count: int = 0
    ai_processed_count: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class SourceVerificationResult(BaseModel):
    source: LegalSourceRead
    message: str


# Risk Finding Schemas
class MatchedSourceDetail(BaseModel):
    id: UUID
    title: str
    authority: str
    original_filename: Optional[str] = None
    download_url: Optional[str] = None
    level: Optional[str] = None
    article_ref: Optional[str] = None


class MatchedArticleDetail(BaseModel):
    id: UUID
    text_code: str
    text_title: str
    jurisdiction: str
    authority: str
    article_number: str
    title: Optional[str] = None
    section_breadcrumb: str = ""
    full_text: str
    has_sanction: bool = False
    sanction_details: Optional[str] = None
    compliance_rule_type: Optional[str] = None
    official_url: Optional[str] = None


class RiskFindingBase(BaseModel):
    clause_ref: str
    finding_text: str
    risk_level: RiskLevel
    confidence: ConfidenceLevel
    matched_sources: List[UUID] = []
    matched_articles: List[UUID] = []
    obsolescence_flag: bool = False
    conflict_flag: bool = False
    conflict_details: Optional[str] = None
    recommendation: str
    legal_nature: str = "non_conformite_imperative"
    review_status: str = "pending"


class RiskFindingRead(RiskFindingBase):
    id: UUID
    report_version_id: UUID
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    created_at: datetime
    sources_details: List[MatchedSourceDetail] = []
    articles_details: List[MatchedArticleDetail] = []
    
    class Config:
        from_attributes = True


class RiskFindingReviewUpdate(BaseModel):
    review_status: Literal["pending", "validated", "mitigated_by_evidence", "dismissed"]
    legal_nature: Optional[Literal["non_conformite_imperative", "risque_contractuel", "bonne_pratique"]] = None
    review_note: Optional[str] = None


# Report Version Schemas
class ReportVersionBase(BaseModel):
    version: str
    global_score: int = Field(ge=0, le=100)
    confidence_global: ConfidenceLevel
    severity_counts: Dict[str, int] = {}


class ReportVersionCreate(ReportVersionBase):
    report1_markdown: str
    report2_markdown: str
    report1_pdf_minio: Optional[str] = None
    report2_pdf_minio: Optional[str] = None
    parent_version_id: Optional[UUID] = None


class ReportVersionRead(ReportVersionBase):
    id: UUID
    project_id: UUID
    report1_markdown: str
    report2_markdown: str
    report1_pdf_minio: Optional[str]
    report2_pdf_minio: Optional[str]
    parent_version_id: Optional[UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReportVersionListItem(BaseModel):
    id: UUID
    version: str
    global_score: int
    confidence_global: ConfidenceLevel
    severity_counts: Dict[str, int]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Diff Schemas
class DiffLine(BaseModel):
    type: str  # "added", "removed", "unchanged", "modified"
    content: str
    line_number_old: Optional[int] = None
    line_number_new: Optional[int] = None


class ReportDiff(BaseModel):
    version_old: str
    version_new: str
    report_type: str  # "report1" or "report2"
    diff_lines: List[DiffLine]
    summary: Dict[str, int]  # {added: 3, removed: 1, modified: 2}
