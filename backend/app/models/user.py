import enum
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import DateTime, String, Enum as SQLEnum


class UserRole(str, enum.Enum):
    ORG_ADMIN = "org_admin"
    ANALYST = "analyst"
    READER = "reader"
    EXTERNAL_AUDITOR = "external_auditor"
    PLATFORM_ADMIN = "platform_admin"


class PlanType(str, enum.Enum):
    POC = "poc"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Organization(SQLModel, table=True):
    __tablename__ = "organization"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=255)
    plan: PlanType = Field(default=PlanType.POC, sa_column=Column(SQLEnum(PlanType)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    users: List["User"] = Relationship(back_populates="organization")
    projects: List["Project"] = Relationship(back_populates="organization")


class User(SQLModel, table=True):
    __tablename__ = "user"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.ANALYST, sa_column=Column(SQLEnum(UserRole)))
    org_id: Optional[UUID] = Field(default=None, foreign_key="organization.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    organization: Optional[Organization] = Relationship(back_populates="users")
    
    # For fastapi-users compatibility
    @property
    def is_anonymous(self) -> bool:
        return False
    
    @property
    def is_authenticated(self) -> bool:
        return True


# Project & Config Models
class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class Project(SQLModel, table=True):
    __tablename__ = "project"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(foreign_key="organization.id", index=True)
    name: str = Field(max_length=255)
    country_code: str = Field(max_length=2, index=True)  # ISO alpha-2, e.g., "BJ"
    sector: str = Field(max_length=100)
    treatments: List[str] = Field(default=[], sa_column=Column(JSON))
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, sa_column=Column(SQLEnum(ProjectStatus)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    
    # Relationships
    organization: Organization = Relationship(back_populates="projects")
    documents: List["Document"] = Relationship(back_populates="project")
    report_versions: List["ReportVersion"] = Relationship(back_populates="project")