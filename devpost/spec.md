---
doc: spec
status: approved
---

# ECO-Compliance Engine (ECE) — Technical Spec

> Blueprint for the sovereign B2B compliance audit platform. Implements the PRD's 11 screens, double report, incremental update, and admin governance console.

---

## How This Works, In Plain Language

The system is a **FastAPI backend + Next.js frontend** running locally via **docker-compose** (PostgreSQL, Redis, MinIO). 

**User flow**: You sign in → create a project (pick country, sector, treatments) → upload a PDF/DOCX/Markdown → the backend spins up an async job (Celery) that: extracts text → finds legal entities & vague clauses → searches a curated legal corpus (PostgreSQL + PGVector) filtered by your project's country → runs a RAG pipeline with an LLM to match clauses to laws, compute a confidence badge (High/Medium/Low), detect obsolete texts or conflicts between CEDEAO and national law → scores each finding (5 levels) → generates two Markdown/PDF reports (document analysis + legal synthesis). You view the report in the dashboard with tabs (Findings, Legal Sources, Recommendations). If something's vague (e.g., "hosting location not specified"), you add the missing info → the system re-runs **only the affected chunks** and shows a diff between report versions. Admins manage the legal corpus, scoring rules, LLM config, and country modules via a dedicated console.

**Why this shape**: 
- Single PostgreSQL for relational data + vector search (no separate vector DB to operate)
- Celery/Redis for async jobs keeps the API responsive
- MinIO gives S3-compatible object storage locally
- FastAPI + SQLModel = type-safe, auto-documented API
- Next.js App Router + shadcn-ui = accessible, themeable UI with minimal custom CSS

---

## The Core Journey Through the System

PRD ref: `prd.md > The Core Journey`

1. **Auth** (`01-landing-auth.html`) → `POST /auth/login` → JWT in HttpOnly cookie → frontend stores user/org context.
2. **Dashboard** (`03-dashboard.html`) → `GET /projects` → lists user's projects with KPIs.
3. **Create Project** (`04-new-project.html`) → `POST /projects` {name, country, sector, treatments[]} → returns project ID.
4. **Upload Document** (`06-doc-upload.html`) → `POST /projects/{id}/documents` (multipart) → file to MinIO → `Celery task: extract_document` queued → returns job ID.
5. **Progress** (`07-analysis-progress.html`) → `GET /jobs/{job_id}` (polling) → stepper: Extraction → Semantic Analysis → Legal Research → Scoring → Report Generation.
6. **Report Dashboard** (`08-report-dashboard.html`) → `GET /projects/{id}/reports/latest` → score global, severity breakdown, 3 tabs (Findings, Legal Sources, Recommendations).
7. **Complementary Context** (`09-complementary-info.html`) → `POST /reports/{id}/context` {field, value} → `Celery task: incremental_update` → new report version.
8. **Version Comparison** (`10-history-comparison.html`) → `GET /reports/{id}/versions` → list + `GET /reports/{id}/diff?v1=1.0&v2=1.1` → side-by-side diff.
9. **Admin Governance** (`11-admin-governance.html`) → CRUD on `LegalSource`, `ScoringRule`, `LLMConfig`, `CountryModule`, users, audit logs (role `platform_admin` only).

---

## Stack

| Layer | Choice | Version | Rationale / Tradeoff |
|-------|--------|---------|----------------------|
| **Backend API** | FastAPI | 0.115+ | Async, auto OpenAPI, type-safe with Pydantic |
| **ORM** | SQLModel | 0.0.22+ | SQLAlchemy + Pydantic unified, ideal for FastAPI |
| **Auth** | fastapi-users | 12.4+ | JWT + OAuth2 (Google, GitHub), role-based, battle-tested |
| **Async Tasks** | Celery | 5.4+ | Robust, scalable, Redis broker; standard for long-running jobs |
| **Message Broker** | Redis | 7-alpine | Celery broker + caching + rate limiting |
| **Database** | PostgreSQL | 16-alpine | Relational + PGVector extension for embeddings |
| **Vector Search** | PGVector | 0.7+ | Single DB, ACID, hybrid SQL + vector queries, no extra infra |
| **File Storage** | MinIO | RELEASE.2024 | S3-compatible, local, buckets per org, versioning |
| **PDF/DOCX Extraction** | PyMuPDF (fitz) + python-docx | 1.24+ / 1.1+ | Fast, reliable, handles native PDF & DOCX |
| **Markdown** | markdown-it-py | 3.0+ | CommonMark compliant |
| **LLM Client** | openai / anthropic SDK | latest | Single provider for POC (configurable via env) |
| **PDF Generation** | weasyprint | 62+ | HTML→PDF via CSS, good for report templates |
| **Frontend Framework** | Next.js | 15 (App Router) | RSC, streaming, modern React patterns |
| **UI Components** | shadcn-ui (Radix UI) | latest | Accessible, copy-paste components, Tailwind-native |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first, themeable (bleu souverain palette) |
| **Forms/Validation** | React Hook Form + Zod | 7.5+ / 3.23+ | Shared schemas with backend (Pydantic ↔ Zod) |
| **State/Data Fetching** | TanStack Query (React Query) | 5.6+ | Server state, caching, polling for job status |
| **Diff/Comparison** | diff-match-patch / custom | - | Line-level diff for report versions |
| **Containerization** | Docker + docker-compose | - | Local dev + demo recording, single command up |

**Doc links**:
- FastAPI: https://fastapi.tiangolo.com
- SQLModel: https://sqlmodel.tiangolo.com
- fastapi-users: https://fastapi-users.github.io/fastapi-users/
- Celery: https://docs.celeryq.dev
- PGVector: https://github.com/pgvector/pgvector
- MinIO: https://min.io/docs/minio/linux/developers/python/API.html
- Next.js: https://nextjs.org/docs
- shadcn-ui: https://ui.shadcn.com
- TanStack Query: https://tanstack.com/query/latest

---

## Where It Runs and How Someone Tries It

**Runtime**: Local machine with Docker Desktop (or Docker Engine + compose plugin).

**Prerequisites**:
- Docker & docker-compose v2
- `.env` file at repo root with:
  ```
  # Required for LLM calls
  OPENAI_API_KEY=sk-...   # or ANTHROPIC_API_KEY
  # Generated once
  SECRET_KEY=...          # openssl rand -hex 32
  MINIO_ROOT_USER=minioadmin
  MINIO_ROOT_PASSWORD=minioadmin
  ```

**Start command**:
```bash
docker-compose up --build
```

**What opens**:
- Frontend: http://localhost:3000
- Backend API (Swagger): http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- PostgreSQL: localhost:5432 (postgres/postgres, db: ece)

**Demo recording**: Run `docker-compose up`, open http://localhost:3000, walk the Core Journey (sign up → create project "StockOpti — Bénin" → upload sample PDF → watch progress → view double report → add context "Cotonou" → see diff). Record screen (~2-3 min). Push repo to GitHub public.

**Deployment (optional, post-POC)**: Frontend → Vercel; Backend + workers → Railway/Render/Fly.io; PostgreSQL + Redis → managed instances; MinIO → S3/MinIO hosted.

---

## Look and Feel

PRD ref: `prd.md > Look and Feel` + `scope.md > Inspiration & Identity`

- **Palette** (Tailwind config):
  ```js
  // tailwind.config.ts
  colors: {
    sovereign: { 50: '#E8F1FA', 500: '#0052A5', 600: '#003D7A' },
    success: { 50: '#E8F5ED', 500: '#007B3F' },
    warning: { 50: '#FFF8E1', 500: '#E6A800' },
    danger: { 50: '#FDEDEA', 500: '#C41E3A' },
    slate: { ... } // default Tailwind slate
  }
  ```
- **Typography**: `Inter` (via `next/font/google`), headings `font-semibold`, body `font-normal`, mono for hashes/article refs.
- **Density**: Spacious — 8px base spacing, generous padding in tables/cards, clear visual hierarchy for audit readability.
- **Tone**: Institutional, precise, French-first. Copy: "Analyse terminée", "Fiabilité : Haute (2 sources concordantes)", "Conflit de normes détecté".
- **Components**: shadcn-ui primitives (Button, Card, Table, Tabs, Badge, Select, Dialog, Toast, Progress, Sidebar, Avatar, DropdownMenu).
- **Icons**: Lucide React (consistent, tree-shakeable).
- **Dark mode**: Not in POC (light only per mockups).

---

## Components

### 1. API Gateway & Auth (`backend/app/api/`, `backend/app/core/security.py`)
- FastAPI app factory, CORS, middleware for JWT verification, role guards.
- `fastapi-users` routers: `/auth/jwt/login`, `/auth/register`, `/auth/oauth2/{google,github}`.
- Implements: `prd.md > Features and Behavior > 1. Gestion des Utilisateurs & Espaces Projets`

### 2. Project & Document Management (`backend/app/api/projects.py`, `backend/app/api/documents.py`)
- CRUD projects (country, sector, treatments), documents (multipart upload to MinIO, metadata in DB).
- Triggers Celery extraction task on upload.
- Implements: `prd.md > Features and Behavior > 1-2`

### 3. Extraction Worker (`backend/app/workers/extraction.py`)
- Celery task: downloads from MinIO → PyMuPDF / python-docx / markdown-it → structured Markdown + quality score → saves `DocumentExtraction` row.
- Implements: `prd.md > Features and Behavior > 2`

### 4. Semantic Analysis Worker (`backend/app/workers/semantic.py`)
- NER (spaCy `fr_core_news_lg` + custom patterns) + LLM clause classification → entities, treatments, data types, vague zones → saves `DocumentAnalysis`.
- Implements: `prd.md > Features and Behavior > 3 (détection)`

### 5. Legal Research & RAG Worker (`backend/app/workers/legal_research.py`)
- Embeds analysis chunks (OpenAI `text-embedding-3-small` or equivalent) → PGVector similarity search filtered by `country` + `level` (communautaire/national) → builds context → LLM prompt for consensus → outputs: matched sources, confidence badge, obsolescence flags, conflict flags.
- Implements: `prd.md > Features and Behavior > 3 (Recherche Juridique, Consensus & Badge de Confiance)`

### 6. Scoring Worker (`backend/app/workers/scoring.py`)
- Deterministic rules (weights per severity, confidence thresholds) + RAG outputs → `RiskFinding` rows with level (Conforme..Critique) + explanations.
- Implements: `prd.md > Features and Behavior > 3 (Scoring) + 4`

### 7. Report Generation Worker (`backend/app/workers/report.py`)
- Renders Jinja2/Markdown templates for Report 1 (Findings) & Report 2 (Legal Synthesis) → HTML → WeasyPrint → PDF → stores both in MinIO + `ReportVersion` metadata.
- Implements: `prd.md > Features and Behavior > 4`

### 8. Incremental Update Worker (`backend/app/workers/incremental.py`)
- Receives complementary context → identifies affected `RiskFinding` IDs → re-runs only Legal Research + Scoring for those → creates new `ReportVersion` → computes diff (added/removed/modified clauses).
- Implements: `prd.md > Features and Behavior > 5 + 6`

### 9. Admin Governance API (`backend/app/api/admin.py`)
- Role-checked (`platform_admin`) CRUD: `LegalSource`, `ScoringRule`, `LLMConfig`, `CountryModule`, `User`, `AuditLog`.
- Implements: `prd.md > Features and Behavior > 6`

### 10. Frontend App Shell (`frontend/app/`, `frontend/components/`)
- Next.js App Router: `(auth)/login`, `(dashboard)/layout` (sidebar), `/dashboard`, `/projects/[id]`, `/projects/[id]/upload`, `/projects/[id]/analysis/[jobId]`, `/projects/[id]/reports/[version]`, `/projects/[id]/reports/[version]/context`, `/projects/[id]/reports/[version]/diff`, `/admin/*`.
- TanStack Query for all server state, polling on `/jobs/{id}`.
- Implements: all 11 screens from `prd.md > Screens and Layout`

### 11. Shared Types & Schemas (`shared/` or generated via `openapi-typescript`)
- Zod schemas mirrored from Pydantic models for end-to-end type safety.
- Implements: cross-cutting validation.

---

## Data Model

**PostgreSQL Tables (SQLModel)**:

```python
# User & Org (fastapi-users extended)
class User(UserDatabase, BaseUUID):
    email: str
    hashed_password: str
    is_active: bool
    is_superuser: bool
    org_id: UUID | None = Field(foreign_key="organization.id")
    role: UserRole  # org_admin, analyst, reader, external_auditor

class Organization(BaseUUID):
    name: str
    plan: PlanType = Field(default=PlanType.POC)

# Project & Config
class Project(BaseUUID):
    org_id: UUID = Field(foreign_key="organization.id")
    name: str
    country_code: str  # ISO alpha-2, e.g. "BJ"
    sector: str
    treatments: list[str]  # JSON array

# Document & Extraction
class Document(BaseUUID):
    project_id: UUID = Field(foreign_key="project.id")
    filename: str
    mime_type: str
    minio_bucket: str
    minio_object: str
    size_bytes: int
    status: DocumentStatus  # uploaded, extracting, extracted, failed

class DocumentExtraction(BaseUUID):
    document_id: UUID = Field(foreign_key="document.id", unique=True)
    markdown: str
    quality_score: float  # 0.0-1.0
    page_count: int
    language: str

# Analysis & Findings
class DocumentAnalysis(BaseUUID):
    extraction_id: UUID = Field(foreign_key="document_extraction.id")
    entities: dict  # JSON: {persons, orgs, locations, data_types, treatments}
    vague_zones: list[VagueZone]  # {clause_ref, description, suggested_fields}

class LegalSource(BaseUUID):
    title: str
    authority: str
    country_code: str | None  # None = supranational (CEDEAO, OHADA)
    level: LegalLevel  # loi, décret, règlement, directive, acte, instruction, décision, recommandation, formulaire, guide
    article_ref: str
    url_official: str
    content_hash: str  # SHA-256
    content_text: str  # for embedding
    status: SourceStatus  # verified, to_verify, replaced, archived, disputed, unofficial
    effective_date: date | None
    abrogated_date: date | None
    embedding: list[float]  # PGVector column

class RiskFinding(BaseUUID):
    report_version_id: UUID = Field(foreign_key="report_version.id")
    clause_ref: str
    finding_text: str
    risk_level: RiskLevel  # conforme, a_surveiller, modere, eleve, critique
    confidence: ConfidenceLevel  # high, medium, low
    matched_sources: list[UUID]  # LegalSource IDs
    obsolescence_flag: bool
    conflict_flag: bool
    conflict_details: str | None
    recommendation: str

# Reports & Versions
class ReportVersion(BaseUUID):
    project_id: UUID = Field(foreign_key="project.id")
    version: str  # "1.0", "1.1", "2.0"
    global_score: int  # 0-100
    confidence_global: ConfidenceLevel
    severity_counts: dict  # {critique: 2, eleve: 5, ...}
    report1_markdown: str  # Findings
    report2_markdown: str  # Legal Synthesis
    report1_pdf_minio: str | None
    report2_pdf_minio: str | None
    parent_version_id: UUID | None  # for incremental chain

class AuditLog(BaseUUID):
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    diff: dict | None
    timestamp: datetime
```

**MinIO Buckets**: `org-{org_id}-documents` (originals), `org-{org_id}-reports` (PDFs/Markdown).

**Persistence**: All user data survives container restarts (PostgreSQL + MinIO volumes). Job state in Redis (ephemeral, recreated on retry).

---

## File Structure

```
ece/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml / requirements.txt
│   ├── alembic/                 # migrations
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings from .env
│   │   │   ├── security.py      # JWT, password hashing, role deps
│   │   │   └── database.py      # engine, session, PGVector init
│   │   ├── models/              # SQLModel tables
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── api/
│   │   │   ├── deps.py          # common dependencies
│   │   │   ├── auth.py          # fastapi-users routers
│   │   │   ├── projects.py
│   │   │   ├── documents.py
│   │   │   ├── reports.py
│   │   │   ├── jobs.py          # job status polling
│   │   │   └── admin.py         # platform_admin only
│   │   ├── workers/
│   │   │   ├── celery_app.py
│   │   │   ├── extraction.py
│   │   │   ├── semantic.py
│   │   │   ├── legal_research.py
│   │   │   ├── scoring.py
│   │   │   ├── report.py
│   │   │   └── incremental.py
│   │   ├── services/
│   │   │   ├── minio_client.py
│   │   │   ├── llm_client.py
│   │   │   ├── embedding.py
│   │   │   ├── pdf_generator.py
│   │   │   └── diff_engine.py
│   │   └── seed/
│   │       ├── legal_corpus.py  # loads ~30 seed texts
│   │       └── admin_user.py
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.mjs
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/login/page.tsx
│   │   │   ├── (dashboard)/
│   │   │   │   ├── layout.tsx   # sidebar + header
│   │   │   │   ├── dashboard/page.tsx
│   │   │   │   ├── projects/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── new/page.tsx
│   │   │   │   │   └── [id]/
│   │   │   │   │       ├── layout.tsx
│   │   │   │   │       ├── page.tsx          # workspace
│   │   │   │   │       ├── upload/page.tsx
│   │   │   │   │       ├── analysis/[jobId]/page.tsx
│   │   │   │   │       ├── reports/
│   │   │   │   │       │   ├── [version]/page.tsx
│   │   │   │   │       │   ├── [version]/context/page.tsx
│   │   │   │   │       │   └── [version]/diff/page.tsx
│   │   │   │   └── admin/
│   │   │   │       ├── layout.tsx
│   │   │   │       ├── sources/page.tsx
│   │   │   │       ├── rules/page.tsx
│   │   │   │       ├── models/page.tsx
│   │   │   │       ├── countries/page.tsx
│   │   │   │       ├── users/page.tsx
│   │   │   │       └── audit/page.tsx
│   │   │   ├── globals.css
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/              # shadcn-ui components
│   │   │   ├── project/
│   │   │   ├── report/
│   │   │   └── admin/
│   │   ├── lib/
│   │   │   ├── api.ts           # TanStack Query hooks + fetch wrappers
│   │   │   ├── schemas.ts       # Zod schemas (generated or manual)
│   │   │   └── utils.ts
│   │   └── hooks/
│   └── public/
├── shared/                      # optional: generated types
└── devpost/                     # learning workspace (not in build)
    ├── learner-profile.md
    ├── scope.md
    ├── prd.md
    └── spec.md
```

---

## External Services and Dependencies

| Service | Purpose | Calls / Config | Keys / Limits |
|---------|---------|----------------|---------------|
| **OpenAI / Anthropic** | LLM for RAG consensus, entity extraction, clause classification | `chat.completions.create` (structured output), `embeddings.create` | API key in `.env`; rate limit ~3k RPM; cost ~$0.01-0.03 per analysis |
| **MinIO (local)** | Object storage for uploads & generated reports | `put_object`, `get_object`, `presigned_get_object` | Root creds in `.env`; no rate limit local |
| **PostgreSQL + PGVector** | Relational + vector storage | SQLAlchemy ORM + raw `vector` ops | Local container; no external key |
| **Redis (local)** | Celery broker + result backend | Celery config `broker_url`, `result_backend` | Local container |
| **OAuth Providers** | Google / GitHub login | `fastapi-users` OAuth2 flow | Client ID/Secret in `.env` (optional for POC) |

---

## Important Failure Modes

| What Breaks | Fallback / User Experience |
|-------------|----------------------------|
| **LLM API unavailable / rate limited** | Job fails → UI shows "Analyse temporairement indisponible, réessayez dans quelques minutes" + retry button (re-queues Celery task with exponential backoff). |
| **MinIO disk full / permission error** | Upload rejects with 500 → toast "Impossible de stocker le fichier, contactez l'admin" → audit log entry. |
| **PGVector query timeout** | Search falls back to keyword-only (SQL `ILIKE` on `content_text`) → badge confidence downgraded to *Low* with note "Recherche vectorielle indisponible". |
| **Celery worker crash mid-pipeline** | Job stuck in `PROCESSING` → dashboard shows stalled stepper → admin can "Requeue from step X" via UI (idempotent tasks). |

---

## What Was Simplified and Why

| Simpler Thing Built | Instead of Fuller Thing | Why |
|---------------------|-------------------------|-----|
| **Seed corpus (~30 texts)** | Automated ingestion/scraping from official sites | POC proves RAG + consensus on curated data; scraping is ops-heavy, brittle, out of scope |
| **Single LLM provider (OpenAI/Anthropic)** | Multi-provider abstraction + local LLM (Ollama/vLLM) | Configurable via env; local LLM needs GPU, model serving infra — deferred |
| **No OCR (Tesseract)** | OCR for scanned PDFs | Scope explicitly cuts scanned PDFs; native PDF/DOCX/MD cover POC |
| **Polling for job status** | WebSockets / Server-Sent Events | Polling (2s interval) is simpler, sufficient for demo; SSE adds backend complexity |
| **WeasyPrint HTML→PDF** | Professional PDF engine (Prince, DocRaptor) | WeasyPrint is free, local, CSS-based; good enough for POC report export |
| **Single `platform_admin` seed** | Full RBAC UI for promoting users | Admin console manages data, not user promotion; one superuser enough for demo |
| **No webhooks** | Webhook delivery with retry/signature | Polling covers demo; webhooks are integration feature (deferred) |
| **Basic diff (line-level)** | Semantic diff (clause-aware) | Line diff via `diff-match-patch` is fast to implement; clause-aware needs AST of report |

---

## Decisions and Open Issues

**Decisions Made Here** (learner choices):
1. **Mixte build mode** — learn for RAG/scoring/incremental, fast for auth/CRUD/UI. *Tradeoff: slower on core IP, faster on boilerplate.*
2. **Local Docker only for demo** — no deployment requirement. *Tradeoff: can't share live link, but video satisfies submission.*
3. **SQLModel + PGVector** — single Postgres for relational + vector. *Tradeoff: PGVector less feature-rich than Pinecone/Weaviate, but zero extra infra.*
4. **MinIO for object storage** — S3-compatible local. *Tradeoff: one more container, but realistic prod parity.*
5. **Next.js 15 App Router + shadcn-ui + Tailwind** — modern, accessible, themeable. *Tradeoff: App Router learning curve if unfamiliar; mitigated by fast mode on UI.*
6. **Celery + Redis** — standard async. *Tradeoff: heavier than RQ/Dramatiq; but robust, monitored, familiar.*
7. **Seed legal corpus** — ~30 texts hardcoded/JSON. *Tradeoff: no live updates; POC proves pipeline, not ingestion ops.*

**Genuine Learner Uncertainty (Learning Goal)**:
> **Orchestration RAG + Consensus + Scoring** — how to structure prompts, chunking strategy, retrieval filters, consensus logic (multi-source agreement), confidence calibration, conflict detection between legal levels.
> **Clarification plan**: In `5-build`, we'll implement this pipeline step-by-step in **learn mode** — I'll explain each design choice (prompt template, few-shot examples, temperature, chunk size/overlap, hybrid search weights, confidence thresholds) and you'll validate before code is written. Evidence: working pipeline with test corpus producing expected badges/conflicts.

**Open Questions from PRD**:
- *Export PDF format*: Include raw legal source excerpts or only synthesis? → Decide in `4-spec` review or early `5-build` (recommendation: both — synthesis in main body, excerpts in appendix).

---

*Ready for review. Does this look good, or would you change anything?*