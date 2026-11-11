"""Seed script for legal corpus."""
import hashlib
from datetime import date
from uuid import UUID, uuid4
from sqlmodel import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

from app.core.config import get_settings
from app.models.legal import LegalSource, LegalLevel, SourceStatus, SourceCollectionRun
from app.services.llm_client import get_llm_client

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

llm = get_llm_client()


DEFAULT_SYSTEM_PROMPT = """Tu es l'auditeur juridique et réglementaire référent d'ECO-Compliance Engine (ECE), spécialisé en droit du numérique, protection des données personnelles, cybersécurité et réglementation financière pour l'Afrique de l'Ouest (République du Bénin, espace CEDEAO, UEMOA, OHADA, BCEAO).

TON RÔLE & MISSION :
1. Analyser avec une rigueur juridique absolue les documents contractuels, techniques et opérationnels soumis par les organisations.
2. Évaluer la stricte conformité au regard des normes impératives en vigueur (Loi n° 2017-20 portant Code du numérique au Bénin, délibérations de l'APDP Bénin, Acte additionnel CEDEAO A/SA.1/01/10, Règlement UEMOA 09/2010, Instructions BCEAO, Actes uniformes OHADA).
3. Détecter les infractions, clauses abusives, manquements et zones de flou juridique.
4. Établir des constats objectifs, proportionnés et directement étayés par des sources juridiques officielles primaires.

DIRECTIVES DÉONTOLOGIQUES & D'EXÉCUTION :
- RÈGLE D'OR : N'invente JAMAIS d'article, de loi, de numéro d'acte ou de disposition réglementaire. Si une information est absente ou incertaine, qualifie-la explicitement en "zone floue" avec un niveau de confiance "low".
- TRAÇABILITÉ : Chaque constat doit être rattaché aux identifiants exacts des sources fournies et citer nommément le texte officiel, son autorité et le fichier PDF ou article applicable.
- HIÉRARCHIE DES NORMES : Identifie et signale tout conflit de normes entre le niveau supranational communautaire (CEDEAO / UEMOA / OHADA) et le niveau national souverain béninois.
- SANCTIONS : Mentionne systématiquement les régimes de sanctions administratives (amendes forfaitaires ou % de chiffre d'affaires prévues par l'APDP) et pénales applicables en cas de non-conformité.
- FORMAT STRICT : Respecte scrupuleusement la structure JSON demandée sans texte superflu hors du JSON."""


BASE_PORTAL_SOURCES = [
    {
        "title": "APDP Bénin - Autorité de Protection des Données Personnelles",
        "authority": "APDP Bénin",
        "country_code": "BJ",
        "level": LegalLevel.LOI,
        "article_ref": "Portail officiel APDP",
        "url_official": "https://service.apdp.bj/",
        "is_portal": True,
        "crawl_depth": 2,
        "collection_enabled": True,
        "content_text": """Portail officiel de l'Autorité de Protection des Données Personnelles (APDP) de la République du Bénin (https://service.apdp.bj/).
        L'APDP est l'autorité administrative indépendante chargée de veiller à ce que les traitements de données à caractère personnel soient mis en œuvre conformément à la loi n° 2017-20 portant Code du numérique.
        Missions : réception des déclarations et demandes d'autorisation, tenue du registre public des traitements, information des personnes concernées et des responsables de traitement, contrôle sur pièces et sur place, instruction des plaintes, prononcé de sanctions administratives et saisine de la justice pénale.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2018, 6, 13),
    },
    {
        "title": "Portail Officiel du Gouvernement du Bénin (Secrétariat Général du Gouvernement)",
        "authority": "République du Bénin",
        "country_code": "BJ",
        "level": LegalLevel.LOI,
        "article_ref": "Portail officiel Lois & Décrets",
        "url_official": "https://www.gouv.bj/",
        "is_portal": True,
        "crawl_depth": 2,
        "collection_enabled": True,
        "content_text": """Portail officiel du Gouvernement de la République du Bénin.
        Publication officielle des lois votées par l'Assemblée nationale et des décrets pris en Conseil des ministres.
        Textes fondamentaux applicables : Loi n° 2017-20 du 13 juin 2018 portant Code du numérique, Loi n° 2018-34 portant lutte contre la cybercriminalité, Décrets d'application relatifs à l'identification électronique, aux transactions électroniques et à la sécurité des systèmes d'information.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2018, 6, 13),
    },
    {
        "title": "CEDEAO - Commission de la Communauté Économique des États de l'Afrique de l'Ouest",
        "authority": "CEDEAO",
        "country_code": None,
        "level": LegalLevel.ACTE,
        "article_ref": "Portail officiel communautaire",
        "url_official": "https://ecowas.int/",
        "is_portal": True,
        "crawl_depth": 2,
        "collection_enabled": True,
        "content_text": """Portail institutionnel officiel de la CEDEAO (Communauté Économique des États de l'Afrique de l'Ouest).
        Cadre juridique communautaire contraignant pour les 15 États membres : Acte additionnel A/SA.1/01/10 relatif à la protection des données à caractère personnel, Directive C/DIR.1/08/11 sur la lutte contre la cybercriminalité, Directive sur les transactions électroniques.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2010, 2, 16),
    },
    {
        "title": "UEMOA - Commission de l'Union Économique et Monétaire Ouest Africaine",
        "authority": "UEMOA",
        "country_code": None,
        "level": LegalLevel.REGLEMENT,
        "article_ref": "Portail officiel UEMOA",
        "url_official": "https://www.uemoa.int/",
        "is_portal": True,
        "crawl_depth": 2,
        "collection_enabled": True,
        "content_text": """Portail officiel de la Commission de l'UEMOA (Union Économique et Monétaire Ouest Africaine).
        Textes réglementaires d'application directe : Règlement n° 09/2010/CM/UEMOA relatif à la protection des données personnelles dans l'espace UEMOA, directives relatives aux services de la société de l'information et au commerce électronique.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2010, 12, 20),
    },
    {
        "title": "BCEAO - Banque Centrale des États de l'Afrique de l'Ouest",
        "authority": "BCEAO",
        "country_code": None,
        "level": LegalLevel.INSTRUCTION,
        "article_ref": "Portail Réglementation Bancaire & Financière",
        "url_official": "https://www.bceao.int/",
        "is_portal": True,
        "crawl_depth": 2,
        "collection_enabled": True,
        "content_text": """Portail officiel de la BCEAO (Banque Centrale des États de l'Afrique de l'Ouest).
        Réglementation prudentielle, bancaire et financière applicable aux 8 pays de l'UMOA : Règlement relatif à l'émission de monnaie électronique, Instructions encadrant les prestataires de services de paiement, dispositions relatives à la lutte contre le blanchiment de capitaux et le financement du terrorisme (LBC/FT).""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2015, 7, 1),
    },
    {
        "title": "OHADA - Organisation pour l'Harmonisation en Afrique du Droit des Affaires",
        "authority": "OHADA",
        "country_code": None,
        "level": LegalLevel.ACTE,
        "article_ref": "Portail officiel Actes Uniformes",
        "url_official": "https://www.ohada.org/",
        "is_portal": True,
        "crawl_depth": 2,
        "collection_enabled": True,
        "content_text": """Portail officiel du Secrétariat Permanent de l'OHADA.
        Droit uniforme directement applicable dans les 17 États parties : Acte uniforme sur le droit commercial général (contrats électroniques, registres du commerce), Acte uniforme relatif au droit des sociétés commerciales et du GIE, Acte uniforme portant organisation des sûretés.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2010, 1, 1),
    },
]

# Backward compatibility alias
SEED_TEXTS = BASE_PORTAL_SOURCES


async def seed_legal_corpus() -> None:
    """Seed and harmonize base official portal sources, cleaning redundant specific sub-URLs."""
    async with SyncSession() as session:
        # 1. Clean up redundant, obsolete or overly specific legacy URLs
        legacy_redundant_urls = [
            "https://apiprod.apdp.bj/storage/df9c83eb5048b2f9dace428ae6ee710a/FORMULAIRE-UNIQUE.pdf",
            "https://archive.apdp.bj/wp-content/uploads/2022/10/1PROTECTION-DES-DONNEES-PERSONNELLES-AU-BENIN-ET-GRANDS-PRINCIPES-DE-LA-PROTECTION-DES-DONNEES-PERSONNELLES.pdf",
            "https://anssi.gouv.ci/reglementations/textes-communautaires/?sous_cat=cedeao",
            "https://www.bceao.int/fr/reglementations/reglementation-des-systemes-de-paiement",
            "https://apdp.bj/",
            "https://apdp.bj",
        ]
        
        for old_url in legacy_redundant_urls:
            old_rows = await session.execute(
                select(LegalSource.id).where(LegalSource.url_official == old_url)
            )
            row_ids = old_rows.scalars().all()
            for r_id in row_ids:
                await session.execute(
                    delete(SourceCollectionRun).where(SourceCollectionRun.source_id == r_id)
                )
                await session.execute(
                    delete(LegalSource).where(LegalSource.parent_source_id == r_id)
                )
                await session.execute(
                    delete(LegalSource).where(LegalSource.id == r_id)
                )

        await session.commit()

        # 2. Upsert each base official portal source
        seeded_count = 0
        for text_data in BASE_PORTAL_SOURCES:
            existing = await session.execute(
                select(LegalSource).where(
                    (LegalSource.url_official == text_data["url_official"])
                    | (LegalSource.authority == text_data["authority"])
                    | (LegalSource.title == text_data["title"])
                )
            )
            source = existing.scalars().first()

            # Compute hash
            content_hash = hashlib.sha256(text_data["content_text"].encode("utf-8")).hexdigest()

            if source:
                # Update existing portal to ensure base URL and portal flag are correct
                source.title = text_data["title"]
                source.authority = text_data["authority"]
                source.country_code = text_data["country_code"]
                source.level = text_data["level"]
                source.url_official = text_data["url_official"]
                source.article_ref = text_data["article_ref"]
                source.is_portal = True
                source.crawl_depth = text_data.get("crawl_depth", 2)
                source.collection_enabled = text_data.get("collection_enabled", True)
                source.status = text_data["status"]
                source.content_text = text_data["content_text"]
                source.content_hash = content_hash
            else:
                embedding = await llm.get_embeddings([text_data["content_text"]])
                embedding_vec = embedding[0] if embedding else [0.0] * 1536

                source = LegalSource(
                    title=text_data["title"],
                    authority=text_data["authority"],
                    country_code=text_data["country_code"],
                    level=text_data["level"],
                    article_ref=text_data["article_ref"],
                    url_official=text_data["url_official"],
                    content_hash=content_hash,
                    content_text=text_data["content_text"],
                    status=text_data["status"],
                    effective_date=text_data.get("effective_date"),
                    embedding=embedding_vec,
                    is_portal=True,
                    crawl_depth=text_data.get("crawl_depth", 2),
                    collection_enabled=text_data.get("collection_enabled", True),
                )
                session.add(source)
                seeded_count += 1

        await session.commit()
        print(f"Seeded/Harmonized base official portals (added {seeded_count}).")


async def seed_admin_user() -> None:
    """Ensure the documented bootstrap platform admin exists."""
    from app.models.user import User, Organization, UserRole
    from app.core.security import get_password_hash
    
    async with SyncSession() as session:
        existing = await session.execute(select(User).where(User.email == "admin@ece.local"))
        admin = existing.scalar_one_or_none()
        if admin:
            admin.role = UserRole.PLATFORM_ADMIN
            admin.is_superuser = True
            admin.is_active = True
            admin.is_verified = True
            if admin.org_id is None:
                org_result = await session.execute(
                    select(Organization).where(Organization.name == "ECE Platform Administration")
                )
                admin_org = org_result.scalar_one_or_none()
                if admin_org is None:
                    admin_org = Organization(name="ECE Platform Administration", plan="enterprise")
                    session.add(admin_org)
                    await session.flush()
                admin.org_id = admin_org.id
            await session.commit()
            print("Bootstrap platform admin already exists.")
            return
        
        # Create admin organization
        admin_org = Organization(name="ECE Platform Administration", plan="enterprise")
        session.add(admin_org)
        await session.flush()
        
        # Create admin user
        admin = User(
            email="admin@ece.local",
            hashed_password=get_password_hash("admin123"),  # Change in production!
            is_active=True,
            is_superuser=True,
            is_verified=True,
            role=UserRole.PLATFORM_ADMIN,
            org_id=admin_org.id,
        )
        session.add(admin)
        await session.commit()
        print("Created platform admin user: admin@ece.local / admin123")


async def seed_country_modules() -> None:
    """Seed country modules."""
    from app.models.admin import CountryModule
    
    countries = [
        ("BJ", "Bénin", True),
        ("SN", "Sénégal", False),
        ("CI", "Côte d'Ivoire", False),
        ("TG", "Togo", False),
        ("BF", "Burkina Faso", False),
        ("NE", "Niger", False),
        ("ML", "Mali", False),
        ("GN", "Guinée", False),
        ("GW", "Guinée-Bissau", False),
        ("CV", "Cap-Vert", False),
        ("GH", "Ghana", False),
        ("NG", "Nigéria", False),
        ("LR", "Libéria", False),
        ("SL", "Sierra Leone", False),
        ("GM", "Gambie", False),
    ]
    
    async with SyncSession() as session:
        for code, name, active in countries:
            existing = await session.execute(select(CountryModule).where(CountryModule.country_code == code))
            if not existing.scalar_one_or_none():
                module = CountryModule(country_code=code, country_name=name, is_active=active)
                session.add(module)
        
        await session.commit()
        print("Seeded country modules.")


async def seed_scoring_rules() -> None:
    """Seed default scoring rules."""
    from app.models.admin import ScoringRule
    
    rules = [
        ScoringRule(
            name="Global Data Protection",
            domain="data_protection",
            country_code=None,
            weight_critique=1.0,
            weight_eleve=0.7,
            weight_modere=0.4,
            weight_a_surveiller=0.1,
            confidence_threshold_high=0.8,
            confidence_threshold_medium=0.5,
        ),
        ScoringRule(
            name="Bénin Data Protection",
            domain="data_protection",
            country_code="BJ",
            weight_critique=1.0,
            weight_eleve=0.7,
            weight_modere=0.4,
            weight_a_surveiller=0.1,
            confidence_threshold_high=0.8,
            confidence_threshold_medium=0.5,
        ),
        ScoringRule(
            name="Global Payment Services",
            domain="payment_services",
            country_code=None,
            weight_critique=1.2,
            weight_eleve=0.8,
            weight_modere=0.5,
            weight_a_surveiller=0.2,
            confidence_threshold_high=0.85,
            confidence_threshold_medium=0.6,
        ),
    ]
    
    async with SyncSession() as session:
        for rule in rules:
            existing = await session.execute(select(ScoringRule).where(ScoringRule.name == rule.name))
            if not existing.scalar_one_or_none():
                session.add(rule)
        await session.commit()
        print("Seeded scoring rules.")


async def seed_llm_config() -> None:
    """Seed one known chat model for each provider declared in code with clear detailed system prompt."""
    from app.core.config import get_settings
    from app.models.admin import LLMConfig, LLMProvider
    from app.services.llm_registry import PROVIDER_REGISTRY

    settings = get_settings()
    system_prompt = DEFAULT_SYSTEM_PROMPT
    provider_models = [
        (LLMProvider.OPENAI, PROVIDER_REGISTRY[LLMProvider.OPENAI].default_model, "OpenAI GPT-4o-mini", True),
        (LLMProvider.ANTHROPIC, PROVIDER_REGISTRY[LLMProvider.ANTHROPIC].default_model, "Anthropic Claude Haiku", False),
        (LLMProvider.GEMINI, settings.gemini_model or PROVIDER_REGISTRY[LLMProvider.GEMINI].default_model, "Google Gemini Flash", False),
        (LLMProvider.GROQ, settings.groq_model or PROVIDER_REGISTRY[LLMProvider.GROQ].default_model, "Groq Llama 3.3", False),
    ]

    async with SyncSession() as session:
        for provider, model, name, is_default in provider_models:
            existing = await session.execute(
                select(LLMConfig).where(
                    (LLMConfig.provider == provider.value)
                    & (LLMConfig.model == model)
                    | (LLMConfig.name == name),
                )
            )
            config = existing.scalar_one_or_none()
            if not config:
                session.add(LLMConfig(
                    name=name,
                    provider=provider.value,
                    model=model,
                    temperature=0.1,
                    max_tokens=4000,
                    system_prompt_version="v2",
                    system_prompt=system_prompt,
                    is_active=True,
                    is_default=is_default,
                ))
            else:
                # Upgrade prompt to v2 if it had the old short generic prompt
                if len(config.system_prompt.strip()) < 200 or config.system_prompt_version == "v1":
                    config.system_prompt = system_prompt
                    config.system_prompt_version = "v2"

        defaults = await session.execute(select(LLMConfig).where(LLMConfig.is_default.is_(True)))
        if not defaults.scalars().first():
            primary = await session.execute(
                select(LLMConfig).where(LLMConfig.provider == LLMProvider.OPENAI.value).limit(1)
            )
            default_config = primary.scalar_one_or_none()
            if default_config:
                default_config.is_default = True
        await session.commit()
        print("Seeded/Updated LLM configs with detailed system prompt.")


async def run_all_seeds():
    """Run all seed functions."""
    await seed_country_modules()
    await seed_scoring_rules()
    await seed_llm_config()
    await seed_admin_user()
    await seed_legal_corpus()
    print("All seeds completed.")


if __name__ == "__main__":
    asyncio.run(run_all_seeds())
