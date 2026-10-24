from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_async_session
from app.core.config import get_settings
from app.core.security import get_current_active_user, require_role
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.legal import (
    LegalSource, SourceStatus, LegalLevel, AuditLog,
    SourceCollectionRun, SourceCollectionRunStatus,
)
from app.models.admin import ScoringRule, LLMConfig, LLMProvider, CountryModule
from app.schemas.admin import (
    ScoringRuleRead, ScoringRuleCreate, ScoringRuleUpdate,
    LLMConfigRead, LLMConfigCreate, LLMConfigUpdate,
    LLMProviderAvailability,
    CountryModuleRead, CountryModuleUpdate,
    AuditLogRead
)
from app.schemas.admin import PlatformAdminCreate
from app.schemas.legal import (
    LegalSourceRead, LegalSourceCreate, LegalSourceUpdate,
    SourceCollectionRunRead, SourceVerificationResult,
)
from app.services.llm_client import get_llm_client
from app.services.llm_registry import (
    get_provider,
    list_provider_availability,
    provider_availability,
    provider_error_message,
)
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
    content_text = (source_data.content_text or "").strip()
    content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
    embedding_vec = [0.0] * 1536
    if content_text:
        embeddings = await get_llm_client().get_embeddings([content_text[:12000]])
        if not embeddings or len(embeddings[0]) != 1536 or not any(abs(value) > 1e-10 for value in embeddings[0]):
            raise HTTPException(status_code=503, detail="Le calcul de l’embedding a échoué.")
        embedding_vec = embeddings[0]

    source = LegalSource(
        **source_data.model_dump(exclude={"content_hash", "content_text"}),
        content_text=content_text,
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
        diff={"title": source.title, "url_official": source.url_official, "content_hash": source.content_hash},
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
    content_was_updated = (
        "content_text" in update_data
        and update_data["content_text"] is not None
        and update_data["content_text"].strip() != source.content_text
    )
    if content_was_updated:
        new_text = update_data["content_text"].strip()
        update_data["content_text"] = new_text
        source.content_hash = hashlib.sha256(new_text.encode("utf-8")).hexdigest()
        if new_text:
            embeddings = await get_llm_client().get_embeddings([new_text[:12000]])
            if not embeddings or len(embeddings[0]) != 1536 or not any(abs(value) > 1e-10 for value in embeddings[0]):
                raise HTTPException(status_code=503, detail="Le calcul de l’embedding a échoué.")
            source.embedding = embeddings[0]
        else:
            source.embedding = [0.0] * 1536
        source.status = SourceStatus.TO_VERIFY
    if "url_official" in update_data and update_data["url_official"] != source.url_official:
        source.source_etag = None
        source.source_last_modified = None
        source.last_collection_status = None
    
    # Handle replacement
    if source_data.replacement_source_id:
        source.status = SourceStatus.REPLACED
        source.abrogated_date = datetime.utcnow().date()
        # Could link to replacement
    
    for field, value in update_data.items():
        if field not in {"replacement_source_id", "content_hash"}:
            setattr(source, field, value)
    if content_was_updated:
        source.status = SourceStatus.TO_VERIFY
    
    source.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(source)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="update_source",
        entity_type="legal_source",
        entity_id=source.id,
        diff={key: value for key, value in update_data.items() if key != "content_text"},
    )
    session.add(audit)
    await session.commit()
    
    return source


@router.post(
    "/sources/{source_id}/collect",
    response_model=SourceCollectionRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def collect_legal_source(
    source_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Queue a one-off collection of a registered official document URL."""
    source = await session.get(LegalSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    active = await session.execute(
        select(SourceCollectionRun).where(
            SourceCollectionRun.source_id == source_id,
            SourceCollectionRun.status.in_([SourceCollectionRunStatus.QUEUED, SourceCollectionRunStatus.RUNNING]),
        ).order_by(SourceCollectionRun.requested_at.desc()).limit(1)
    )
    active_run = active.scalar_one_or_none()
    if active_run and active_run.requested_at > datetime.utcnow() - timedelta(hours=1):
        raise HTTPException(status_code=409, detail="Une collecte de cette source est déjà en cours.")
    if active_run:
        active_run.status = SourceCollectionRunStatus.FAILED.value
        active_run.finished_at = datetime.utcnow()
        active_run.error_message = "La tâche est restée active plus d’une heure; une nouvelle collecte peut être lancée."

    run = SourceCollectionRun(source_id=source_id, trigger_type="manual", triggered_by=current_user.id)
    session.add(run)
    await session.flush()
    source.last_collection_at = run.requested_at
    source.last_collection_status = SourceCollectionRunStatus.QUEUED.value
    source.last_collection_run_id = run.id
    session.add(AuditLog(
        user_id=current_user.id,
        action="collect_source",
        entity_type="legal_source",
        entity_id=source_id,
        diff={"run_id": str(run.id), "trigger_type": "manual"},
    ))
    await session.commit()
    await session.refresh(run)

    try:
        from app.workers.source_collection import collect_source
        collect_source.delay(str(run.id), str(source_id))
    except Exception as exc:
        run.status = SourceCollectionRunStatus.FAILED
        run.finished_at = datetime.utcnow()
        run.error_message = f"Impossible de démarrer la tâche de collecte : {str(exc)[:1800]}"
        source.last_collection_status = SourceCollectionRunStatus.FAILED.value
        await session.commit()
        raise HTTPException(status_code=503, detail="La collecte n’a pas pu être mise en file.") from exc

    return run


@router.get("/sources/{source_id}/collections", response_model=List[SourceCollectionRunRead])
async def list_source_collections(
    source_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not await session.get(LegalSource, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    result = await session.execute(
        select(SourceCollectionRun)
        .where(SourceCollectionRun.source_id == source_id)
        .order_by(SourceCollectionRun.requested_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/sources/{source_id}/verify", response_model=SourceVerificationResult)
async def verify_source_url(
    source_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Check that the normalized official document still matches the corpus."""
    source = await session.get(LegalSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        from app.workers.source_collection import _download
        status_code, text, _, _, _, _ = await _download(source.url_official, None, None)
        matches = status_code == 304 or hashlib.sha256(text.encode("utf-8")).hexdigest() == source.content_hash
        source.status = SourceStatus.VERIFIED if matches else SourceStatus.DISPUTED
        source.updated_at = datetime.utcnow()
        message = "Le contenu officiel correspond au corpus." if matches else "Le contenu officiel a changé. Lancez une collecte pour actualiser le texte."
        session.add(AuditLog(
            user_id=current_user.id,
            action="verify_source",
            entity_type="legal_source",
            entity_id=source.id,
            diff={"url": source.url_official, "hash_match": matches},
        ))
        await session.commit()
        await session.refresh(source)
        return {"source": source, "message": message}
    except Exception as e:
        return {"source": source, "message": f"Vérification impossible : {str(e)[:500]}"}


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
    query = select(LLMConfig).order_by(LLMConfig.is_default.desc(), LLMConfig.created_at, LLMConfig.name)
    result = await session.execute(query)
    return [
        LLMConfigRead.model_validate(config).model_copy(
            update={"available": provider_availability(config.provider)}
        )
        for config in result.scalars().all()
    ]


@router.get("/models/providers", response_model=List[LLMProviderAvailability])
async def list_llm_providers(
    current_user: User = Depends(get_current_active_user),
):
    """Expose registry metadata and key presence, never credentials."""
    return list_provider_availability()


@router.post("/models", response_model=LLMConfigRead, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    config_data: LLMConfigCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Test a provider/model before persisting its configuration."""
    existing_name = await session.execute(
        select(LLMConfig.id).where(LLMConfig.name == config_data.name)
    )
    if existing_name.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Un modèle porte déjà ce nom.")

    definition = get_provider(config_data.provider)
    if not definition.is_available(get_settings()):
        raise HTTPException(status_code=409, detail="Ce fournisseur n'a pas de clé API configurée.")
    if config_data.is_default and not config_data.is_active:
        raise HTTPException(status_code=409, detail="Un modèle inactif ne peut pas être défini par défaut.")
    try:
        await definition.test_model(config_data.model)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Test du modèle échoué : {provider_error_message(exc)} Aucun modèle n'a été enregistré.",
        ) from exc

    if config_data.is_default:
        result = await session.execute(
            select(LLMConfig).where(LLMConfig.is_default == True)
        )
        for existing in result.scalars().all():
            existing.is_default = False
    
    config = LLMConfig(**config_data.model_dump())
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return LLMConfigRead.model_validate(config).model_copy(
        update={"available": definition.is_available(get_settings())}
    )


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

    will_be_active = update_data.get("is_active", config.is_active)
    will_be_default = update_data.get("is_default", config.is_default)
    if update_data.get("is_active") is False and "is_default" not in update_data:
        will_be_default = False
    if will_be_active and not provider_availability(config.provider):
        raise HTTPException(status_code=409, detail="Ce modèle ne peut pas être activé : la clé API du fournisseur est absente.")
    if will_be_default and not will_be_active:
        raise HTTPException(status_code=409, detail="Un modèle inactif ne peut pas être défini par défaut.")
    
    if update_data.get("is_default") is True:
        # Unset other defaults
        result = await session.execute(
            select(LLMConfig).where(LLMConfig.is_default == True, LLMConfig.id != config_id)
        )
        for other_config in result.scalars().all():
            other_config.is_default = False

    if update_data.get("is_active") is False:
        config.is_default = False
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    config.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(config)
    return LLMConfigRead.model_validate(config).model_copy(
        update={"available": provider_availability(config.provider)}
    )


# Country Modules
@router.get("/countries", response_model=List[CountryModuleRead])
async def list_country_modules(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List country modules."""
    query = select(CountryModule).order_by(CountryModule.country_code)
    result = await session.execute(query)
    modules = result.scalars().all()

    source_counts = await session.execute(
        select(
            LegalSource.country_code,
            func.count(LegalSource.id),
            func.max(LegalSource.last_successful_collection_at),
        )
        .where(LegalSource.country_code.is_not(None))
        .group_by(LegalSource.country_code)
    )
    stats_by_country = {
        country_code: (count, last_sync)
        for country_code, count, last_sync in source_counts.all()
    }
    for module in modules:
        module.legal_sources_count, module.last_sync = stats_by_country.get(
            module.country_code, (0, None)
        )
    return modules


@router.patch("/countries/{country_code}", response_model=CountryModuleRead)
async def update_country_module(
    country_code: str,
    module_data: CountryModuleUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Activate/deactivate a country module."""
    result = await session.execute(
        select(CountryModule).where(CountryModule.country_code == country_code.upper())
    )
    module = result.scalar_one_or_none()
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


@router.post("/users/admins", status_code=status.HTTP_201_CREATED)
async def create_platform_admin(
    admin_data: PlatformAdminCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create another platform administrator. The router enforces admin-only access."""
    normalized_email = str(admin_data.email).strip().lower()
    existing = await session.execute(select(User).where(User.email == normalized_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette adresse e-mail est déjà utilisée.")

    new_admin = User(
        email=normalized_email,
        hashed_password=get_password_hash(admin_data.password),
        is_active=True,
        is_superuser=True,
        is_verified=True,
        role=UserRole.PLATFORM_ADMIN,
        org_id=current_user.org_id,
    )
    session.add(new_admin)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette adresse e-mail est déjà utilisée.")
    await session.refresh(new_admin)
    return {
        "id": new_admin.id,
        "email": new_admin.email,
        "role": new_admin.role,
        "is_active": new_admin.is_active,
        "org_id": new_admin.org_id,
        "created_at": new_admin.created_at,
        "last_login": None,
    }


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
