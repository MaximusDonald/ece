# ECO-Compliance Engine (ECE)

Plateforme B2B souveraine d'audit documentaire automatisé et de vérification de conformité juridique et technique pour l'espace **CEDEAO / UEMOA / OHADA / OAPI / Union Africaine** et les droits nationaux associés.

---

## Stack & Environnements

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.4+-37814A?style=for-the-badge&logo=celery&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16_+_pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-S3_Storage-C72E49?style=for-the-badge&logo=minio&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

---

## Présentation

**ECO-Compliance Engine** permet aux entreprises, fintechs, éditeurs de logiciels et cabinets d'audit de soumettre un dossier multi-documents (cahier des charges, politique de confidentialité, CGU, contrat sous-traitant, architecture technique) et de produire un **rapport d'audit juridique unifié, traçable et versionné**, ancré exclusivement sur un corpus normatif officiel curaté.

### Principes directeurs du moteur

- **Corpus curaté et vérifiable** : recherche hybride **Article-RAG** (pgvector HNSW + PostgreSQL French GIN FTS) limitée aux textes officiels indexés.
- **Hiérarchie des normes et validité temporelle** : exclusion stricte des textes abrogés ou non encore en vigueur ; priorité aux normes communautaires contraignantes (`OHADA`, `UEMOA/BCEAO`, `CEDEAO`, `OAPI`, `UA`) sur la loi nationale et les décrets, avec signalement automatique des conflits de normes.
- **Principe de précaution et parade d'annulation** : lecture conjointe de tous les documents du projet ; aucun point n'est classé conforme sans preuve explicite détectée dans le dossier.
- **Scoring stabilisé par domaine** : calcul par rendements décroissants sur 4 facettes juridiques canoniques, malus de sanction dédupliqué par article unique (plafonné à +25 pts), plancher à `50/100` sur risque critique non mitigé et compression graduée au-delà de `70/100`.
- **Sélection ciblée sur gros dossiers** : découpage par sections Markdown et sélection prioritaire des clauses critiques pour éviter les troncatures aveugles du milieu de document.
- **Qualification juridique et piste d'audit** : typage des constats (`non_conformite_imperative`, `risque_contractuel`, `bonne_pratique`), revue humaine horodatée (`validated`, `mitigated_by_evidence`, `dismissed`) et verrouillage inter-versions.

---

## Documentation du projet

L'ensemble de la documentation de référence est regroupé dans le répertoire [`docs/`](./docs/) :

| Document | Description | Lien |
| :--- | :--- | :--- |
| Cahier des charges | Périmètre fonctionnel, exigences, rôles RBAC et critères d'acceptation | [docs/cahier_des_charges.md](./docs/cahier_des_charges.md) |
| Architecture technique | Services Docker, pipeline Celery, Article-RAG hybride et modèle de données | [docs/architecture_technique.md](./docs/architecture_technique.md) |
| Matrice de risques & scoring | Facettes juridiques, hiérarchie des normes, formule stabilisée et piste d'audit | [docs/matrice_risques_et_scoring.md](./docs/matrice_risques_et_scoring.md) |
| Manuel utilisateur | Guide opérationnel Analyste / Juriste et Administrateur Plateforme | [docs/manuel_utilisateur.md](./docs/manuel_utilisateur.md) |
| Guide de déploiement | Configuration `.env`, migrations Alembic, démarrage Docker et tests | [docs/guide_deploiement.md](./docs/guide_deploiement.md) |

---

## Architecture du dépôt

```text
.
├── backend/                    # API FastAPI, SQLModel, Alembic, Workers Celery
│   ├── alembic/versions/       # Migrations PostgreSQL (corpus, alertes, audit trail)
│   ├── app/
│   │   ├── api/                # Endpoints REST (auth, projects, documents, reports, admin)
│   │   ├── models/             # Modèles SQLModel (User, Project, LegalText, RiskFinding...)
│   │   ├── schemas/            # Schémas Pydantic v2
│   │   ├── services/           # Article-RAG, compliance_auditor, pdf_generator, llm_client
│   │   ├── workers/            # Pipeline asynchrone Celery (5 étapes + barrière projet)
│   │   └── seed/               # Corpus juridique initial et règles de scoring
│   └── tests/                  # Suite Pytest (RAG, hiérarchie, scoring, audit trail, gros dossiers)
├── frontend/                   # Application Next.js 15 (App Router) + Tailwind + TanStack Query
│   └── src/
│       ├── app/                # Pages Dashboard, Projets, Rapports, Administration
│       ├── components/         # Composants UI réutilisables
│       ├── hooks/              # Hooks TanStack Query
│       └── lib/                # Client HTTP Axios & types TypeScript
├── docs/                       # Documentation projet complète
├── docker-compose.yml          # Stack complète (postgres, redis, minio, backend, worker, beat, frontend)
└── .env.example                # Modèle des variables d'environnement
```

---

## Démarrage rapide

### Prérequis

- Docker et Docker Compose v2
- Clé API LLM configurée (Gemini / OpenAI / Anthropic selon le fournisseur actif)

### Lancement

```bash
cp .env.example .env
# Renseigner les clés API et secrets dans .env

docker compose up -d --build
docker compose exec backend alembic upgrade head
```

### Points d'accès locaux

| Service | URL |
| :--- | :--- |
| Interface Web | http://localhost:3000 |
| Documentation API (Swagger) | http://localhost:8000/docs |
| Console MinIO | http://localhost:9001 |

### Compte administrateur initial (environnement local)

- **Email** : `admin@ece.local`
- **Mot de passe** : `admin123`
- **Rôle** : `platform_admin` (gouvernance du corpus, règles de scoring, configuration LLM et audit). Changer ce mot de passe dès le premier déploiement hors développement.

---

## Vérification et tests

```bash
# Tests backend (scoring, hiérarchie des normes, gros dossiers, piste d'audit, RAG)
docker compose exec -T backend pytest -v

# Vérification TypeScript frontend
docker compose exec -T frontend npx tsc --noEmit
```
