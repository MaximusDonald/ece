import enum
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import DateTime, String, Text


class ScoringRule(SQLModel, table=True):
    __tablename__ = "scoring_rule"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    domain: str = Field(max_length=100, index=True)  # e.g., "data_protection", "payment_services"
    country_code: Optional[str] = Field(default=None, max_length=2, index=True)  # None = global
    weight_critique: float = Field(default=1.0)
    weight_eleve: float = Field(default=0.7)
    weight_modere: float = Field(default=0.4)
    weight_a_surveiller: float = Field(default=0.1)
    weight_conforme: float = Field(default=0.0)
    confidence_threshold_high: float = Field(default=0.8)
    confidence_threshold_medium: float = Field(default=0.5)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"


class LLMConfig(SQLModel, table=True):
    __tablename__ = "llm_config"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    # Providers are validated by the application registry; VARCHAR lets the
    # registry grow without coupling PostgreSQL enum deployments to code.
    provider: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    model: str = Field(max_length=100)  # e.g., "gpt-4o", "claude-3-5-sonnet"
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=4000)
    system_prompt_version: str = Field(max_length=50, default="v1")
    system_prompt: str = Field(sa_column=Column(Text))
    rpm_limit: Optional[int] = Field(default=None)  # Requests Per Minute
    tpm_limit: Optional[int] = Field(default=None)  # Tokens Per Minute
    rpd_limit: Optional[int] = Field(default=None)  # Requests Per Day
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))


class CountryModule(SQLModel, table=True):
    __tablename__ = "country_module"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    country_code: str = Field(max_length=2, unique=True, index=True)
    country_name: str = Field(max_length=100)
    is_active: bool = Field(default=False)
    legal_sources_count: int = Field(default=0)
    last_sync: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
