from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole, PlanType, ProjectStatus


# Auth Schemas
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)
    role: UserRole = UserRole.ANALYST


class UserRead(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    is_verified: bool
    role: UserRole
    org_id: Optional[UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


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