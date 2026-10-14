from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from fastapi_users import schemas as fastapi_users_schemas
from app.models.user import UserRole, PlanType, ProjectStatus


# Auth Schemas
class UserCreate(fastapi_users_schemas.BaseUserCreate):
    pass


class UserRead(fastapi_users_schemas.BaseUser[UUID]):
    role: UserRole
    org_id: Optional[UUID] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(fastapi_users_schemas.BaseUserUpdate):
    pass


# Organization Schemas
class OrganizationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationRead(OrganizationBase):
    id: UUID
    plan: PlanType
    created_at: datetime
    
    class Config:
        from_attributes = True


# Project Schemas
class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country_code: str = Field(min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    sector: str = Field(min_length=1, max_length=100)
    treatments: List[str] = Field(default=[])


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    sector: Optional[str] = Field(default=None, min_length=1, max_length=100)
    treatments: Optional[List[str]] = None
    status: Optional[ProjectStatus] = None


class ProjectRead(ProjectBase):
    id: UUID
    org_id: UUID
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectListItem(BaseModel):
    id: UUID
    name: str
    country_code: str
    sector: str
    status: ProjectStatus
    risk_score: Optional[int] = None
    last_analysis: Optional[datetime] = None
    
    class Config:
        from_attributes = True
