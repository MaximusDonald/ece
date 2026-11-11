from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from fastapi_users import schemas as fastapi_users_schemas
from app.models.user import UserRole, PlanType, ProjectStatus
from app.core.password_strength import password_strength_score


# Auth Schemas
class UserCreate(fastapi_users_schemas.BaseUserCreate):
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def require_strong_password(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Le mot de passe ne peut pas dépasser 72 octets.")
        score = password_strength_score(password)
        if score < 7:
            raise ValueError(
                f"Le mot de passe doit atteindre au moins 7/10 (score actuel : {score}/10)."
            )
        return password


class UserRead(fastapi_users_schemas.BaseUser[UUID]):
    # The local bootstrap account uses an internal .local address. Keep
    # response serialization permissive; registration/update still validate
    # deliverable email addresses through their own schemas.
    email: str
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


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationMemberCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.ANALYST


class OrganizationMemberRead(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
