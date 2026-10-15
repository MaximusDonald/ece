# ECO-Compliance Engine (ECE)

> Plateforme B2B souveraine d'audit documentaire automatisé et de vérification de conformité juridique et technique pour la zone CEDEAO/UEMOA.

## 🎯 Vision

L'ECO-Compliance Engine permet aux entrepreneurs, fintechs et éditeurs de logiciels de déposer leurs documents stratégiques (cahier des charges, politique de confidentialité, contrats) et d'obtenir un **double rapport traçable, sourcé et noté en confiance** ancré sur le droit CEDEAO/UEMOA/OHADA + droit national (Bénin en premier).

### Noyau distinctif (Unique Kernel)

- **Sources prédéfinies et curatorées uniquement** — pas de web ouvert
- **Gestion explicite de l'obsolescence** — un texte abrogé ne ressort pas comme valide
- **Principe de non-hallucination** — badges de confiance (High/Medium/Low), le modèle avoue ce qu'il ne sait pas
- **Architecture incrémentale multi-niveaux** — socle communautaire CEDEAO/UEMOA/OHADA + module national via paramètre `pays`
- **Détection des conflits de normes** — entre textes de niveaux différents (CEDEAO vs national) au lieu de choisir silencieusement

## 🏗️ Architecture

```
ece/
├── docker-compose.yml          # Orchestration locale
├── .env.example                # Variables d'environnement
├── backend/                    # FastAPI + Celery + PostgreSQL + MinIO
│   ├── app/
│   │   ├── api/               # Routes REST (auth, projects, documents, reports, admin)
│   │   ├── core/              # Config, DB, Security
│   │   ├── models/            # SQLModel (User, Project, Document, LegalSource, RiskFinding...)
│   │   ├── workers/           # Celery tasks (extraction, semantic, legal_research, scoring, report, incremental)
│   │   ├── services/          # MinIO, LLM, PDF, Diff
│   │   └── seed/              # Corpus juridique initial (~30 textes)
│   └── requirements.txt
├── frontend/                   # Next.js 15 + shadcn-ui + Tailwind
│   ├── src/
│   │   ├── app/               # App Router (dashboard, admin, auth)
│   │   ├── components/        # UI components (shadcn-ui based)
│   │   ├── hooks/             # TanStack Query hooks
│   │   └── lib/               # API client, utils
│   └── package.json
└── devpost/                    # Documentation Devpost Learn
    ├── learner-profile.md
    ├── scope.md
    ├── prd.md
    ├── spec.md
    └── checklist.md
```

## 🚀 Démarrage rapide

### Prérequis

- Docker & Docker Compose v2
- Clé API OpenAI ou Anthropic (pour le LLM)

### Installation

```bash
# Cloner le repo
git clone <votre-repo>
cd ece

# Configurer l'environnement
cp .env.example .env
# Éditer .env et ajouter OPENAI_API_KEY ou ANTHROPIC_API_KEY

# Lancer la stack complète
docker-compose up --build
```

### Accès

- **Frontend** : http://localhost:3000
- **API (Swagger)** : http://localhost:8000/docs
- **MinIO Console** : http://localhost:9001 (minioadmin / minioadmin)

### Compte admin par défaut

- Email : `admin@ece.local`
- Mot de passe : `admin123`
- Role: `platform_admin` (governance administrator). This account can open global administration and create other platform administrators. Change the default password after the first login outside local development.

## 🔄 Parcours utilisateur (Core Journey)

1. **Inscription/Connexion** → JWT + OAuth (Google, GitHub)
2. **Création projet** → Nom, pays (BJ pré-sélectionné), secteur, traitements
3. **Téléversement document** → PDF/DOCX/Markdown (≤50 Mo) → MinIO
4. **Analyse asynchrone** (5 étapes) :
   - Extraction (PyMuPDF, python-docx)
   - Analyse sémantique (spaCy NER + LLM)
   - Recherche juridique (PGVector + RAG + consensus LLM)
   - Scoring (règles déterministes + pondérations)
   - Génération rapport (WeasyPrint PDF)
5. **Double rapport** :
   - Rapport 1 : Analyse documentaire (constats par clause)
   - Rapport 2 : Synthèse juridique (citations articles, URLs, SHA-256)
6. **Contexte complémentaire** → Mise à jour incrémentale → Diff v1.0 → v1.1
7. **Admin** → Gestion corpus, règles scoring, modèles LLM, pays, audit logs

## 🛠️ Stack technique

| Couche | Technologie | Version |
|--------|-------------|---------|
| API | FastAPI | 0.115+ |
| ORM | SQLModel | 0.0.22+ |
| Auth | fastapi-users | 12.4+ |
| Async | Celery + Redis | 5.4+ / 7 |
| DB | PostgreSQL + PGVector | 16 / 0.7+ |
| Stockage | MinIO | RELEASE.2024 |
| Extraction | PyMuPDF, python-docx | 1.24+ / 1.1+ |
| LLM | OpenAI / Anthropic SDK | Latest |
| PDF | WeasyPrint | 62+ |
| Frontend | Next.js 15 (App Router) | 15 |
| UI | shadcn-ui + Tailwind | Latest |
| State | TanStack Query | 5.6+ |

## 📊 Corpus juridique initial (POC)

- **CEDEAO** : Acte additionnel A/SA.1/01/10 (protection données), Directive transactions électroniques
- **UEMOA** : Règlement 09/2010/CM/UEMOA
- **OHADA** : Acte uniforme droit commercial général
- **BCEAO** : Instruction services de paiement, Règlement monnaie électronique, Instruction LCB/FT
- **Bénin** : Code du numérique (Loi 2017-20), Décret APDP, Formulaire unique APDP, Guide APDP, Loi cybercriminalité

## 🔐 Sécurité & Souveraineté

- Isolation par organisation (multi-tenant)
- Chiffrement en transit (TLS) + au repos (PostgreSQL, MinIO)
- JWT HttpOnly cookies + rotation refresh tokens
- RBAC : org_admin, analyst, reader, external_auditor, platform_admin
- Journaux d'audit immuables (toutes actions sensibles)
- Pas d'accès web ouvert — corpus interne uniquement
- Suppression configurable des documents originaux

## 🧪 Tests & Qualité

```bash
# Backend tests
cd backend && pytest

# Frontend lint
cd frontend && npm run lint

# Type checking
cd frontend && npx tsc --noEmit
```

## 📦 Déploiement (optionnel)

Le POC tourne en local via Docker Compose. Pour la production :

- **Frontend** → Vercel / Netlify
- **Backend + Workers** → Railway / Render / Fly.io
- **PostgreSQL + Redis** → Managed instances (Neon, Supabase, Upstash)
- **MinIO** → AWS S3 / MinIO hosted / Cloudflare R2

## 📚 Documentation Devpost Learn

Le dossier `devpost/` contient la traçabilité complète du processus de planification :

- `learner-profile.md` — Profil apprenant (expérience, objectifs)
- `scope.md` — Cadrage POC (noyau, utilisateur, boucle, frontière)
- `prd.md` — Spécifications produit détaillées (11 écrans, comportements, états)
- `spec.md` — Spécifications techniques (stack, data model, file structure, composants)
- `checklist.md` — Plan de build par tranches (slices) avec vérifications

## 🤝 Contribution

Ce projet a été développé dans le cadre du hackathon **Devpost Learn - Build With AI: Basics**.

## 📄 Licence

Propriétaire — POC pour démonstration hackathon.

---

**ECE** — *Faire de la conformité un levier, pas un fardeau.*
