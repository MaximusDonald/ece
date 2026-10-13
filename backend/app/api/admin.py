from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.core.database import get_async_session
from app.core.security import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.models.legal import LegalSource, SourceStatus, LegalLevel, AuditLog
from app.models.admin import ScoringRule, LLMConfig, LLMProvider, CountryModule
from app.schemas.admin import (
    ScoringRuleRead, ScoringRuleCreate, ScoringRuleUpdate,
    LLMConfigRead, LLMConfigCreate, LLMConfigUpdate,
    CountryModuleRead, CountryModuleUpdate,
    AuditLogRead
)
from app.schemas.legal import (
    LegalSourceRead, LegalSourceCreate, LegalSourceUpdate,
)
from app.services.llm_client import get_llm_client
import hashlib

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(UserRole.PLATFORM_ADMIN))])


# Legal Sources CRUD
@router.get("/sources", response_model=List[LegalSourceRead])
async def list_legal_sources(
    status_filter: Optional[SourceStatus] = Query(None),
    country_code: Optional[str] = Query(None),
    level: Optional[LegalLevel] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List legal sources with filters."""
    query = select(LegalSource)
    
    if status_filter:
        query = query.where(LegalSource.status == status_filter)
    if country_code:
        query = query.where(LegalSource.country_code == country_code.upper())
    if level:
        query = query.where(LegalSource.level == level)
    
    query = query.order_by(LegalSource.updated_at.desc()).offset(skip).limit(limit)
    
    result = await session.execute(query)
    sources = result.scalars().all()
    
    return sources


@router.post("/sources", response_model=LegalSourceRead, status_code=status.HTTP_201_CREATED)
async def create_legal_source(
    source_data: LegalSourceCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new legal source."""
    # Compute hash
    content_hash = hashlib.sha256(source_data.content_text.encode()).hexdigest()
    
    # Get embedding
    llm = get_llm_client()
    embedding = await llm.get_embeddings([source_data.content_text])
    embedding_vec = embedding[0] if embedding else [0.0] * 1536
    
    source = LegalSource(
        **source_data.model_dump(),
        content_hash=content_hash,
        embedding=embedding_vec,
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="create_source",
        entity_type="legal_source",
        entity_id=source.id,
        diff=source_data.model_dump(),
    )
    session.add(audit)
    await session.commit()
    
    return source


@router.patch("/sources/{source_id}", response_model=LegalSourceRead)
async def update_legal_source(
    source_id: UUID,
    source_data: LegalSourceUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a legal source (e.g., mark as verified, abrogated)."""
    source = await session.get(LegalSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    update_data = source_data.model_dump(exclude_unset=True)
    
    # Handle replacement
    if source_data.replacement_source_id:
        source.status = SourceStatus.REPLACED
        source.abrogated_date = datetime.utcnow().date()
        # Could link to replacement
    
    for field, value in update_data.items():
        if field != "replacement_source_id":
            setattr(source, field, value)
    
    source.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(source)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="update_source",
        entity_type="legal_source",
        entity_id=source.id,
        diff=update_data,
    )
    session.add(audit)
    await session.commit()
    
    return source


@router.post("/sources/{source_id}/verify", response_model=LegalSourceRead)
async def verify_source_url(
    source_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Verify source URL is accessible and content matches hash."""
    import httpx
    
    source = await session.get(LegalSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(source.url_official, follow_redirects=True)
            response.raise_for_status()
            
            # Check if content matches (simplified)
            current_hash = hashlib.sha256(response.text.encode()).hexdigest()
            
            if current_hash == source.content_hash:
                source.status = SourceStatus.VERIFIED
                message = "Source verified - content matches hash"
            else:
                source.status = SourceStatus.DISPUTED
                message = "Source disputed - content hash mismatch"
            
            source.updated_at = datetime.utcnow()
            await session.commit()
            
            # Audit log
            audit = AuditLog(
                user_id=current_user.id,
                action="verify_source",
                entity_type="legal_source",
                entity_id=source.id,
                diff={"url": source.url_official, "hash_match": current_hash == source.content_hash},
            )
            session.add(audit)
            await session.commit()
            
            return {"source": source, "message": message}
            
    except Exception as e:
        return {"source": source, "message": f"Verification failed: {str(e)}"}


# Scoring Rules CRUD
@router.get("/rules", response_model=List[ScoringRuleRead])
async def list_scoring_rules(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all scoring rules."""
    query = select(ScoringRule).order_by(ScoringRule.country_code.is_(None).desc(), ScoringRule.domain)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/rules", response_model=ScoringRuleRead, status_code=status.HTTP_201_CREATED)
async def create_scoring_rule(
    rule_data: ScoringRuleCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a scoring rule."""
    rule = ScoringRule(**rule_data.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=ScoringRuleRead)
async def update_scoring_rule(
    rule_id: UUID,
    rule_data: ScoringRuleUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a scoring rule."""
    rule = await session.get(ScoringRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    rule.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rule)
    return rule


# LLM Config CRUD
@router.get("/models", response_model=List[LLMConfigRead])
async def list_llm_configs(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List LLM configurations."""
    query = select(LLMConfig).order_by(LLMConfig.is_default.desc(), LLMConfig.name)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/models", response_model=LLMConfigRead, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    config_data: LLMConfigCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create LLM configuration."""
    # Ensure only one default
    if config_data.is_default:
        await session.execute(
            select(LLMConfig).where(LLMConfig.is_default == True)
        )
        # Would update existing default to False
    
    config = LLMConfig(**config_data.model_dump())
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


@router.patch("/models/{config_id}", response_model=LLMConfigRead)
async def update_llm_config(
    config_id: UUID,
    config_data: LLMConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update LLM configuration."""
    config = await session.get(LLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    update_data = config_data.model_dump(exclude_unset=True)
    
    if config_data.is_default:
        # Unset other defaults
        result = await session.execute(
            select(LLMConfig).where(LLMConfig.is_default == True, LLMConfig.id != config_id)
        )
        for c in result.scalars().all():
            c.is_default = False
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    config.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(config)
    return config


# Country Modules
@router.get("/countries", response_model=List[CountryModuleRead])
async def list_country_modules(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List country modules."""
    query = select(CountryModule).order_by(CountryModule.country_code)
    result = await session.execute(query)
    return result.scalars().all()


@router.patch("/countries/{country_code}", response_model=CountryModuleRead)
async def update_country_module(
    country_code: str,
    module_data: CountryModuleUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Activate/deactivate a country module."""
    module = await session.get(CountryModule, country_code.upper())
    if not module:
        raise HTTPException(status_code=404, detail="Country module not found")
    
    if module_data.is_active is not None:
        module.is_active = module_data.is_active
        module.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(module)
    
    return module


# Users (admin view)
@router.get("/users", response_model=List[dict])
async def list_all_users(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all users across organizations (platform admin only)."""
    query = select(User).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()
    
    return [{
        "id": u.id,
        "email": u.email,
        "role": u.role,
        "is_active": u.is_active,
        "org_id": u.org_id,
        "created_at": u.created_at,
        "last_login": getattr(u, 'last_login', None),
    } for u in users]


# Audit Logs
@router.get("/audit", response_model=List[AuditLogRead])
async def list_audit_logs(
    entity_type: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List audit logs."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()


import hashlib