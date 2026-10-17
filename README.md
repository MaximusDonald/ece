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

## Équipe et paramètres

- La page **Équipe** est réservée aux administrateurs d’organisation. Elle liste les membres de l’organisation courante et permet d’en ajouter avec un rôle `org_admin`, `analyst`, `reader` ou `external_auditor`. Le rôle global `platform_admin` ne peut pas être attribué depuis une organisation.
- API d’équipe : `GET /api/projects/organization/members` liste les membres ; `POST /api/projects/organization/members` crée un membre (e-mail, mot de passe initial de 8 caractères minimum, rôle). Les deux routes sont limitées à l’organisation de l’administrateur authentifié.
- La page **Paramètres** permet à chaque utilisateur de modifier son e-mail et son mot de passe via `PATCH /api/auth/users/me`. Un administrateur d’organisation peut aussi renommer son organisation via `PATCH /api/projects/organization/me`.
- Le premier projet d’un utilisateur sans organisation crée d’abord son organisation avec le nom saisi dans le formulaire, puis le projet.
- Les membres ajoutés reçoivent un mot de passe initial communiqué par l’administrateur ; aucun courriel d’invitation ni réinitialisation obligatoire n’est encore intégré.
## Cycle d'analyse documentaire

L'upload accepte les PDF, DOCX, Markdown et fichiers texte jusqu'a 50 Mo. La nature du document est stockee dans `document.document_type` (50 caracteres maximum) et enrichit les requetes de recherche juridique. Le suivi authentifie `GET /api/projects/{project_id}/documents/{document_id}/pipeline` expose les cinq etapes, leur progression, les avertissements/erreurs et l'identifiant du rapport. `POST .../resume` relance l'etape manquante apres une interruption.

Les rapports PDF sont transmis par `GET /api/reports/{report_version_id}/download?type=report1|report2`; les boutons du frontend utilisent cette route authentifiee au lieu d'une URL MinIO interne. Les rapports Markdown restent disponibles via les routes d'export existantes.

La base locale est mise a jour de façon additive au demarrage. Les scripts SQL reversibles se trouvent dans `backend/migrations/20261016_add_document_type.sql` et `backend/migrations/20261016_remove_document_type.sql`. Le retour arriere supprime la colonne et donc les valeurs de nature deja enregistrees.

## Veille des sources juridiques

Depuis l’administration, chaque source peut être collectée à la demande ou incluse dans le cycle hebdomadaire. L’URL doit pointer directement vers un document public en HTTPS (HTML ou PDF); le collecteur n’explore pas les liens d’un site. L’historique conserve le déclencheur, les dates, le statut, le hash précédent/nouveau et les erreurs. Le texte courant et son embedding ne sont recalculés que si le texte extrait change.

Celery Beat exécute la collecte hebdomadaire le lundi à 02:00 UTC (03:00 au Bénin). Seules les sources dont « collecte automatique hebdomadaire » est activée sont traitées. Les colonnes et la table d’historique sont ajoutées au démarrage; les scripts de migration sont `backend/migrations/20261016_add_source_collection.sql` et `backend/migrations/20261016_remove_source_collection.sql`.

- API de collecte : `POST /api/admin/sources/{source_id}/collect` met une collecte manuelle en file (202); `GET /api/admin/sources/{source_id}/collections` renvoie les 20 executions les plus recentes. `PATCH /api/admin/sources/{source_id}` modifie notamment `collection_enabled`. Ces routes exigent le role `platform_admin`.

## Modèles LLM et fournisseurs

Les fournisseurs autorisés sont déclarés dans `backend/app/services/llm_registry.py`. L’API admin calcule leur disponibilité à partir d’une clé API non vide et ne transmet jamais les clés au frontend. Les nouvelles configurations sont testées avec un appel court avant insertion. Le routeur des appels de discussion consulte les modèles actifs en base et tente au plus trois modèles disponibles, par défaut puis dans un ordre stable. Le fallback couvre les timeouts, erreurs de connexion, réponses HTTP 5xx, limites de débit et erreurs d’authentification; les erreurs de requête 4xx ne sont pas réessayées.

La migration Alembic `backend/alembic/versions/20261017_01_expand_llm_providers.py` convertit l’enum PostgreSQL fournisseur en texte et ajoute de façon idempotente les modèles Anthropic, Gemini et Groq sans remplacer la configuration OpenAI existante. Pour une base locale existante, depuis le dossier `backend`, exécuter `alembic -c alembic.ini upgrade head`. Le downgrade refuse de convertir si des lignes Gemini/Groq existent, afin de ne pas perdre leur configuration; exporter ou supprimer explicitement ces lignes avant un retour arrière.
