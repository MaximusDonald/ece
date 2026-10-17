"""Seed script for legal corpus."""
import hashlib
from datetime import date
from uuid import UUID, uuid4
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

from app.core.config import get_settings
from app.models.legal import LegalSource, LegalLevel, SourceStatus
from app.services.llm_client import get_llm_client

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,  # Ne supprimez pas +asyncpg ici
    echo=False,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

llm = get_llm_client()


SEED_TEXTS = [
    # CEDEAO / Supranational
    {
        "title": "Acte additionnel A/SA.1/01/10 relatif à la protection des données à caractère personnel dans l'espace CEDEAO",
        "authority": "CEDEAO",
        "country_code": None,
        "level": LegalLevel.ACTE,
        "article_ref": "Article 1-25",
        "url_official": "https://anssi.gouv.ci/reglementations/textes-communautaires/?sous_cat=cedeao",
        "content_text": """L'Acte additionnel A/SA.1/01/10 établit le cadre juridique de protection des données personnelles dans l'espace CEDEAO. 
        Il définit les principes de licéité, loyauté, transparence, proportionnalité, exactitude, conservation limitée, intégrité et confidentialité.
        Tout traitement de données personnelles doit être fondé sur le consentement de la personne concernée ou sur une base légale.
        Les responsables de traitement doivent mettre en œuvre des mesures techniques et organisationnelles appropriées.
        Les transferts de données hors de l'espace CEDEAO nécessitent des garanties adéquates.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2010, 2, 16),
    },
    {
        "title": "Directive CEDEAO sur les transactions électroniques",
        "authority": "CEDEAO",
        "country_code": None,
        "level": LegalLevel.DIRECTIVE,
        "article_ref": "Articles 1-30",
        "url_official": "https://www.cedeao.int/",
        "content_text": """La directive CEDEAO sur les transactions électroniques harmonise le cadre juridique des transactions électroniques.
        Elle établit la reconnaissance juridique des écritures et signatures électroniques.
        Les prestataires de services de certification doivent être accrédités.
        La conservation des données de trafic est encadrée.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2010, 2, 16),
    },
    # UEMOA
    {
        "title": "Règlement UEMOA n°09/2010/CM/UEMOA relatif à la protection des données personnelles",
        "authority": "UEMOA",
        "country_code": None,
        "level": LegalLevel.REGLEMENT,
        "article_ref": "Articles 1-40",
        "url_official": "https://www.uemoa.int/",
        "content_text": """Le règlement UEMOA transpose l'Acte additionnel CEDEAO au niveau de l'Union.
        Il renforce les obligations des responsables de traitement.
        L'autorité de protection des données de chaque État membre assure le contrôle.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2010, 12, 20),
    },
    # OHADA
    {
        "title": "Acte uniforme OHADA relatif au droit commercial général",
        "authority": "OHADA",
        "country_code": None,
        "level": LegalLevel.ACTE,
        "article_ref": "Articles 1-200",
        "url_official": "https://www.ohada.org/",
        "content_text": """L'Acte uniforme OHADA sur le droit commercial général s'applique dans les 17 États parties.
        Il régit les actes de commerce, les commerçants, les sociétés commerciales.
        Les contrats électroniques y sont reconnus.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2010, 1, 1),
    },
    # BCEAO
    {
        "title": "Instruction BCEAO n°001-01-2018 relative aux services de paiement",
        "authority": "BCEAO",
        "country_code": None,
        "level": LegalLevel.INSTRUCTION,
        "article_ref": "Articles 1-50",
        "url_official": "https://www.bceao.int/fr/reglementations/reglementation-des-systemes-de-paiement",
        "content_text": """L'instruction BCEAO encadre les services de paiement dans l'UMOA.
        Les établissements de paiement doivent être agréés.
        La protection des données des clients est obligatoire.
        Les fonds des clients doivent être séparés des fonds propres.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2018, 1, 1),
    },
    {
        "title": "Règlement BCEAO relatif à la monnaie électronique",
        "authority": "BCEAO",
        "country_code": None,
        "level": LegalLevel.REGLEMENT,
        "article_ref": "Articles 1-60",
        "url_official": "https://www.bceao.int/fr/reglementations",
        "content_text": """Le règlement BCEAO sur la monnaie électronique définit les conditions d'émission et de gestion.
        Les émetteurs doivent être agréés par la BCEAO.
        La protection des utilisateurs et la lutte contre le blanchiment sont renforcées.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2015, 7, 1),
    },
    # Bénin - National
    {
        "title": "Loi n°2017-20 du 13 juin 2018 portant Code du numérique en République du Bénin",
        "authority": "Assemblée nationale du Bénin",
        "country_code": "BJ",
        "level": LegalLevel.LOI,
        "article_ref": "Articles 1-500",
        "url_official": "https://www.gouv.bj/",
        "content_text": """Le Code du numérique du Bénin est le texte fondateur du droit numérique béninois.
        Il couvre : commerce électronique, protection des données, cybersécurité, signature électronique, noms de domaine.
        L'APDP (Autorité de Protection des Données Personnelles) est instituée comme autorité de contrôle.
        Les traitements de données sensibles font l'objet d'autorisation préalable.
        L'hébergement des données au Bénin est encouragé.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2018, 6, 13),
    },
    {
        "title": "Décret n°2019-101 portant attributions de l'APDP",
        "authority": "Présidence de la République du Bénin",
        "country_code": "BJ",
        "level": LegalLevel.DECRET,
        "article_ref": "Articles 1-20",
        "url_official": "https://apdp.bj/",
        "content_text": """Le décret définit les missions, l'organisation et le fonctionnement de l'APDP.
        L'APDP reçoit les déclarations de traitements, délivre les autorisations, contrôle et sanctionne.
        Elle tient le registre des traitements déclarés.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2019, 4, 15),
    },
    {
        "title": "Formulaire unique APDP - Déclaration de traitement de données personnelles",
        "authority": "APDP Bénin",
        "country_code": "BJ",
        "level": LegalLevel.FORMULAIRE,
        "article_ref": "Formulaire unique",
        "url_official": "https://apiprod.apdp.bj/storage/df9c83eb5048b2f9dace428ae6ee710a/FORMULAIRE-UNIQUE.pdf",
        "content_text": """Formulaire officiel de déclaration de traitement de données personnelles auprès de l'APDP.
        Doit être complété par tout responsable de traitement avant mise en œuvre.
        Comprend : identification du responsable, finalités, catégories de données, destinataires, transferts, mesures de sécurité, durée de conservation.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2020, 1, 1),
    },
    {
        "title": "Guide APDP - Protection des données personnelles au Bénin : grands principes",
        "authority": "APDP Bénin",
        "country_code": "BJ",
        "level": LegalLevel.GUIDE,
        "article_ref": "Guide 2022",
        "url_official": "https://archive.apdp.bj/wp-content/uploads/2022/10/1PROTECTION-DES-DONNEES-PERSONNELLES-AU-BENIN-ET-GRANDS-PRINCIPES-DE-LA-PROTECTION-DES-DONNEES-PERSONNELLES.pdf",
        "content_text": """Guide pédagogique de l'APDP expliquant les grands principes de la protection des données au Bénin.
        Couvre : consentement, droits des personnes, obligations des responsables, transferts internationaux, sanctions.
        Indique que les sanctions peuvent aller jusqu'à 4% du chiffre d'affaires mondial.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2022, 10, 1),
    },
    {
        "title": "Loi n°2018-34 du 5 octobre 2018 portant lutte contre la cybercriminalité",
        "authority": "Assemblée nationale du Bénin",
        "country_code": "BJ",
        "level": LegalLevel.LOI,
        "article_ref": "Articles 1-80",
        "url_official": "https://www.gouv.bj/",
        "content_text": """La loi béninoise sur la cybercriminalité réprime les infractions liées aux systèmes d'information.
        Couvre : accès frauduleux, interception, atteinte à l'intégrité, vol de données, escroquerie en ligne.
        Prévoit des peines de prison et amendes.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2018, 10, 5),
    },
    # Additional BCEAO texts
    {
        "title": "Instruction BCEAO sur la lutte contre le blanchiment de capitaux et le financement du terrorisme",
        "authority": "BCEAO",
        "country_code": None,
        "level": LegalLevel.INSTRUCTION,
        "article_ref": "Articles 1-80",
        "url_official": "https://www.bceao.int/fr/reglementations",
        "content_text": """Obligations de vigilance pour les établissements financiers et de paiement.
        Identification du client, connaissance du client (KYC), déclaration de soupçons.
        Conservation des documents pendant 5 ans après la fin de la relation.""",
        "status": SourceStatus.VERIFIED,
        "effective_date": date(2018, 1, 1),
    },
]


async def seed_legal_corpus() -> None:
    """Seed the legal corpus with initial texts."""
    async with SyncSession() as session:
        # Check if already seeded
        existing = await session.execute(select(LegalSource).limit(1))
        if existing.scalar_one_or_none():
            print("Legal corpus already seeded, skipping.")
            return
        
        for text_data in SEED_TEXTS:
            # Compute hash
            content_hash = hashlib.sha256(text_data["content_text"].encode()).hexdigest()
            
            # Get embedding
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
            )
            session.add(source)
        
        await session.commit()
        print(f"Seeded {len(SEED_TEXTS)} legal sources.")


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
    """Seed one known chat model for each provider declared in code."""
    from app.core.config import get_settings
    from app.models.admin import LLMConfig, LLMProvider
    from app.services.llm_registry import PROVIDER_REGISTRY

    settings = get_settings()
    system_prompt = (
        "You are a legal expert specialized in ECOWAS, WAEMU, OHADA and Beninese law. "
        "Answer precisely and never invent legal references."
    )
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
                    LLMConfig.provider == provider.value,
                    LLMConfig.model == model,
                )
            )
            if not existing.scalar_one_or_none():
                session.add(LLMConfig(
                    name=name,
                    provider=provider.value,
                    model=model,
                    temperature=0.1,
                    max_tokens=4000,
                    system_prompt_version="v1",
                    system_prompt=system_prompt,
                    is_active=True,
                    is_default=is_default,
                ))
        defaults = await session.execute(select(LLMConfig).where(LLMConfig.is_default.is_(True)))
        if not defaults.scalars().first():
            primary = await session.execute(
                select(LLMConfig).where(LLMConfig.provider == LLMProvider.OPENAI.value).limit(1)
            )
            default_config = primary.scalar_one_or_none()
            if default_config:
                default_config.is_default = True
        await session.commit()
        print("Seeded LLM config.")


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
