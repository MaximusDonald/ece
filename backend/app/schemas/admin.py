from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic import EmailStr
from app.models.admin import LLMProvider


class PlatformAdminCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


# Scoring Rule Schemas
class ScoringRuleBase(BaseModel):
    name: str = Field(max_length=100)
    domain: str = Field(max_length=100)
    country_code: Optional[str] = Field(default=None, max_length=2)
    weight_critique: float = Field(default=1.0, ge=0)
    weight_eleve: float = Field(default=0.7, ge=0)
    weight_modere: float = Field(default=0.4, ge=0)
    weight_a_surveiller: float = Field(default=0.1, ge=0)
    weight_conforme: float = Field(default=0.0, ge=0)
    confidence_threshold_high: float = Field(default=0.8, ge=0, le=1)
    confidence_threshold_medium: float = Field(default=0.5, ge=0, le=1)
    is_active: bool = True


class ScoringRuleCreate(ScoringRuleBase):
    pass


class ScoringRuleUpdate(BaseModel):
    weight_critique: Optional[float] = Field(default=None, ge=0)
    weight_eleve: Optional[float] = Field(default=None, ge=0)
    weight_modere: Optional[float] = Field(default=None, ge=0)
    weight_a_surveiller: Optional[float] = Field(default=None, ge=0)
    weight_conforme: Optional[float] = Field(default=None, ge=0)
    confidence_threshold_high: Optional[float] = Field(default=None, ge=0, le=1)
    confidence_threshold_medium: Optional[float] = Field(default=None, ge=0, le=1)
    is_active: Optional[bool] = None


class ScoringRuleRead(ScoringRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# LLM Config Schemas
class LLMConfigBase(BaseModel):
    name: str = Field(max_length=100)
    provider: LLMProvider
    model: str = Field(max_length=100)
    temperature: float = Field(default=0.1, ge=0, le=2)
    max_tokens: int = Field(default=4000, gt=0)
    system_prompt_version: str = Field(max_length=50, default="v1")
    system_prompt: str
    is_active: bool = True
    is_default: bool = False


class LLMConfigCreate(LLMConfigBase):
    pass


class LLMConfigUpdate(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    system_prompt_version: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class LLMConfigRead(LLMConfigBase):
    id: UUID
    available: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LLMProviderAvailability(BaseModel):
    provider: LLMProvider
    label: str
    available: bool
    default_model: str


# Country Module Schemas
class CountryModuleBase(BaseModel):
    country_code: str = Field(max_length=2, min_length=2)
    country_name: str = Field(max_length=100)
    is_active: bool = False


class CountryModuleUpdate(BaseModel):
    is_active: Optional[bool] = None


class CountryModuleRead(CountryModuleBase):
    id: UUID
    legal_sources_count: int
    last_sync: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Audit Log Schemas
class AuditLogRead(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    entity_type: str
    entity_id: Optional[UUID]
    diff: Optional[Dict[str, Any]]
    timestamp: datetime
    
    class Config:
        from_attributes = True
