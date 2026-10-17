from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.core.database import get_async_session
from app.core.security import get_current_active_user, get_password_hash, require_role
from app.models.user import User, Organization, Project, ProjectStatus, UserRole
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectRead, ProjectListItem,
    OrganizationCreate, OrganizationRead, OrganizationUpdate,
    OrganizationMemberCreate, OrganizationMemberRead,
)

router = APIRouter(prefix="/projects", tags=["projects"])


async def get_organization_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role not in (UserRole.ORG_ADMIN, UserRole.PLATFORM_ADMIN) and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul un administrateur peut gérer l’organisation.")
    return current_user


# Organization endpoints
@router.post("/organization", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create organization for the current user."""
    # Check if user already has an org
    if current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already belongs to an organization"
        )
    
    org = Organization(name=org_data.name)
    session.add(org)
    await session.flush()
    
    # Assign user to org as admin
    current_user.org_id = org.id
    if current_user.role != UserRole.PLATFORM_ADMIN and not current_user.is_superuser:
        current_user.role = UserRole.ORG_ADMIN
    await session.commit()
    await session.refresh(org)
    
    return org


@router.get("/organization/me", response_model=OrganizationRead)
async def get_my_organization(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get current user's organization."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not belong to any organization"
        )
    
    org = await session.get(Organization, current_user.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.patch("/organization/me", response_model=OrganizationRead)
async def update_my_organization(
    organization_data: OrganizationUpdate,
    current_user: User = Depends(get_organization_admin),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune organisation n’est associée à ce compte.")
    org = await session.get(Organization, current_user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation introuvable.")
    org.name = organization_data.name.strip()
    org.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(org)
    return org


@router.get("/organization/members", response_model=List[OrganizationMemberRead])
async def list_organization_members(
    current_user: User = Depends(get_organization_admin),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune organisation n’est associée à ce compte.")
    result = await session.execute(
        select(User).where(User.org_id == current_user.org_id).order_by(User.created_at.asc())
    )
    return result.scalars().all()


@router.post("/organization/members", response_model=OrganizationMemberRead, status_code=status.HTTP_201_CREATED)
async def create_organization_member(
    member_data: OrganizationMemberCreate,
    current_user: User = Depends(get_organization_admin),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune organisation n’est associée à ce compte.")
    if member_data.role == UserRole.PLATFORM_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Le rôle administrateur plateforme ne peut pas être attribué depuis une organisation.")

    email = str(member_data.email).strip().lower()
    existing = await session.execute(select(User.id).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette adresse e-mail est déjà utilisée.")

    member = User(
        email=email,
        hashed_password=get_password_hash(member_data.password),
        role=member_data.role,
        org_id=current_user.org_id,
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    session.add(member)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette adresse e-mail est déjà utilisée.")
    await session.refresh(member)
    return member


# Project endpoints
@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new project."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization"
        )
    
    project = Project(
        org_id=current_user.org_id,
        name=project_data.name,
        country_code=project_data.country_code.upper(),
        sector=project_data.sector,
        treatments=project_data.treatments,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    
    return project


@router.get("", response_model=List[ProjectListItem])
async def list_projects(
    status_filter: Optional[ProjectStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List projects for current user's organization."""
    if not current_user.org_id:
        return []
    
    query = select(Project).where(Project.org_id == current_user.org_id)
    
    if status_filter:
        query = query.where(Project.status == status_filter)
    
    query = query.order_by(Project.updated_at.desc())
    
    result = await session.execute(query)
    projects = result.scalars().all()
    
    # Add risk_score and last_analysis from latest report
    items = []
    for p in projects:
        # Get latest report version
        from app.models.legal import ReportVersion
        latest_report_query = select(ReportVersion).where(
            ReportVersion.project_id == p.id
        ).order_by(ReportVersion.created_at.desc()).limit(1)
        latest_report_result = await session.execute(latest_report_query)
        latest_report = latest_report_result.scalar_one_or_none()
        
        items.append(ProjectListItem(
            id=p.id,
            name=p.name,
            country_code=p.country_code,
            sector=p.sector,
            status=p.status,
            risk_score=latest_report.global_score if latest_report else None,
            last_analysis=latest_report.created_at if latest_report else None,
        ))
    
    return items


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get project details."""
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update project."""
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permissions
    if current_user.role not in [UserRole.ORG_ADMIN, UserRole.ANALYST]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    project.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(project)
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(require_role(UserRole.ORG_ADMIN)),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete project (org admin only)."""
    if not current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = await session.get(Project, project_id)
    if not project or project.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await session.delete(project)
    await session.commit()
