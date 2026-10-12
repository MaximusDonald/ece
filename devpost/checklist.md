---
doc: checklist
status: approved
---

# Build Checklist

Build mode: mixte (learn for RAG/scoring/incremental, fast for auth/CRUD/UI)

## Slices

- [x] **1. Full-stack bootstrap + Auth + Create Project + Dashboard**
  Becomes usable: `docker-compose up` starts all services; user can sign up, log in, create a project (name, country=BJ, sector, treatments), and land on a dashboard showing the project list with KPIs.
  Why now: Proves the entire infrastructure (PostgreSQL, Redis, MinIO, FastAPI, Next.js) works end-to-end before adding domain logic. Bootstrapping lives inside slice one.
  PRD ref: `prd.md > The Core Journey` (steps 1-3), `prd.md > Screens and Layout` (01-landing-auth, 02-onboarding, 03-dashboard, 04-new-project)
  Spec ref: `spec.md > Components` (1, 2), `spec.md > File Structure` (backend/app, frontend/src/app), `spec.md > Where It Runs`
  Build: Write docker-compose.yml with postgres, redis, minio, backend, frontend. Scaffold FastAPI app with SQLModel models (User, Organization, Project), fastapi-users auth (JWT + OAuth Google/GitHub), project CRUD endpoints. Scaffold Next.js 15 App Router with shadcn-ui, Tailwind (bleu souverain palette), TanStack Query. Pages: login, dashboard (sidebar, KPI cards, project table), new project form. Wire frontend → backend API.
  Verify (mechanical): `docker-compose up --build` → all containers healthy. Open http://localhost:3000 → sign up → create project "StockOpti — Bénin" → see it in dashboard table with correct badges.
  Learner check: Open the app, sign up, create a project, and confirm the flow feels smooth and the UI matches the sovereign aesthetic.
  Commit: `Scaffold full stack: docker-compose, FastAPI+Next.js, auth, project CRUD, dashboard`

- [x] **2. Document Upload + Extraction + Progress UI**
  Becomes usable: In a project, user uploads a PDF/DOCX/Markdown file (drag-drop, ≤50 MB), sees a 5-step progress stepper (Extraction → Semantic Analysis → Legal Research → Scoring → Report Generation) with estimated time, and can view the extracted structured Markdown with quality score.
  Why now: First domain behavior — proves file storage (MinIO), async workers (Celery), and extraction pipeline work. Extraction is the gateway to all downstream analysis.
  PRD ref: `prd.md > The Core Journey` (steps 4-5), `prd.md > Screens and Layout` (05-project-overview, 06-doc-upload, 07-analysis-progress)
  Spec ref: `spec.md > Components` (2, 3), `spec.md > Data Model` (Document, DocumentExtraction), `spec.md > External Services` (MinIO)
  Build: MinIO client service, Celery app + Redis broker. `POST /projects/{id}/documents` multipart → stores file in MinIO (bucket `org-{org_id}-documents`), creates Document row, enqueues `extract_document` task. Worker: downloads from MinIO → PyMuPDF / python-docx / markdown-it-py → saves DocumentExtraction (markdown, quality_score, page_count, language). Frontend: upload modal, progress stepper polling `/jobs/{job_id}`, extraction viewer page.
  Verify (mechanical): Upload sample PDF → job progresses through all 5 steps → extraction page shows Markdown with headings/clauses preserved + quality score > 0.8.
  Learner check: Upload your StockOpti architecture PDF, watch the stepper, and verify the extracted text looks correct.
  Commit: `Document upload, MinIO storage, Celery extraction worker, progress UI`

- [x] **3. Semantic Analysis + Legal Research (RAG Kernel) + Scoring — LEARN MODE**
  Becomes usable: After extraction, the pipeline runs: NER + clause classification → embeddings → PGVector hybrid search (filtered by country=BJ + level) → LLM consensus prompt → confidence badges (High/Medium/Low), obsolescence flags, conflict detection (CEDEAO vs national) → deterministic scoring (5 levels) → findings persisted.
  Why now: **This is the unique kernel** — sovereign RAG with consensus, confidence, obsolescence, and conflict detection. Building it early proves the core value and surfaces LLM/prompt issues while time remains.
  PRD ref: `prd.md > The Core Journey` (step 6), `prd.md > Features and Behavior` (3. Recherche Juridique, Consensus & Badge de Confiance, 4. Double Rapport, 5. Complément d'Information)
  Spec ref: `spec.md > Components` (4, 5, 6), `spec.md > Data Model` (DocumentAnalysis, LegalSource, RiskFinding), `spec.md > Decisions and Open Issues` (genuine learner uncertainty: RAG/consensus/scoring)
  Build: Seed ~30 legal texts (LegalSource rows with embeddings) via seed script. Workers: `semantic.py` (spaCy NER + LLM clause classification → DocumentAnalysis), `legal_research.py` (embed chunks → PGVector search → build context → LLM structured output for consensus → confidence badge + obsolescence + conflict flags), `scoring.py` (deterministic weights + RAG outputs → RiskFinding rows with level + explanation). All findings linked to ReportVersion (created in next slice).
  Verify (mechanical): Run pipeline on seeded extraction → RiskFinding rows created with correct levels, confidence badges, matched_sources populated, at least one conflict_flag or obsolescence_flag demonstrated on test corpus.
  Learner check: We'll walk through the prompt templates, chunking strategy, retrieval filters, consensus logic, and confidence thresholds together — you validate each design choice before code is written.
  Commit: `RAG kernel: semantic analysis, legal research with consensus badges, conflict detection, scoring`

- [x] **4. Double Report Generation + Report Dashboard (3 tabs)**
  Becomes usable: Worker generates two Markdown reports (Report 1: Findings per clause; Report 2: Legal Synthesis with article citations, URLs, SHA-256 hashes) + PDFs via WeasyPrint → stored in MinIO. Dashboard shows global score (0-100), global confidence, severity breakdown (Critical/High/Medium/Low), and 3 tabs: Findings, Legal Sources, Recommendations.
  Why now: Completes the core journey — user sees the full audit output. Report generation is the deliverable; dashboard is the consumption surface.
  PRD ref: `prd.md > The Core Journey` (step 6), `prd.md > Screens and Layout` (08-report-dashboard)
  Spec ref: `spec.md > Components` (7), `spec.md > Data Model` (ReportVersion), `spec.md > Look and Feel` (badges, severity colors, tabs)
  Build: `report.py` worker: Jinja2 templates for Report 1 & 2 → HTML → WeasyPrint → PDF → MinIO. `ReportVersion` row with both Markdown + PDF paths, global_score, severity_counts, confidence_global. Frontend: report dashboard page with tabs, severity chips, confidence badge, source citations with links.
  Verify (mechanical): Pipeline produces ReportVersion v1.0 → both Markdown files render correctly → PDFs open → dashboard tabs show data → severity counts match RiskFinding rows.
  Learner check: View the generated double report for your StockOpti doc — verify Findings tab shows clause-level issues, Legal Sources tab cites real articles with hashes, Recommendations tab has actionable items.
  Commit: `Double report generation (Markdown+PDF), report dashboard with 3 tabs`

- [ ] **5. Complementary Context + Incremental Update + Version Diff**
  Becomes usable: On a vague zone (e.g., "Lieu d'hébergement non précisé"), user clicks "Add Complementary Context", fills a targeted form (hosting location, subcontractor, transfer details) → system re-runs Legal Research + Scoring **only for affected findings** → creates ReportVersion v1.1 → Diff page shows side-by-side comparison with `[Nouveau]`, `[Résolu]`, `[Mis à jour]` markers.
  Why now: Proves the incremental update kernel — a key differentiator. Avoids full re-analysis, shows surgical diff.
  PRD ref: `prd.md > The Core Journey` (steps 7-8), `prd.md > Screens and Layout` (09-complementary-info, 10-history-comparison)
  Spec ref: `spec.md > Components` (8), `spec.md > Data Model` (ReportVersion.parent_version_id), `spec.md > Services` (diff_engine.py)
  Build: `POST /reports/{id}/context` → enqueues `incremental_update` task. Worker: identifies affected RiskFinding IDs from context field → re-runs legal_research + scoring for those only → creates new ReportVersion with parent_version_id. Diff engine: compares v1.0 vs v1.1 Markdown → line-level diff with markers. Frontend: context form, version selector, diff view.
  Verify (mechanical): Add "Hébergement: Cotonou, Bénin" → new version created in <30s → only hosting-related findings changed → diff page shows only those clauses marked.
  Learner check: Add complementary info for your doc, verify the update is fast and the diff highlights exactly what changed.
  Commit: `Incremental update via complementary context, version diff with markers`

- [ ] **6. Admin Governance Console**
  Becomes usable: `platform_admin` user accesses `/admin/*` pages: Sources table (validate, mark abrogated, replace, verify URL), Scoring Rules editor (weights, thresholds, preview), LLM Config (provider, model, temperature, system prompt version), Country Modules (activate/deactivate, link corpus), Users table (roles, orgs, quotas), Audit Logs (immutable action trail).
  Why now: Completes the sovereign governance story — corpus curation, rule transparency, auditability. Required for demo credibility.
  PRD ref: `prd.md > The Core Journey` (step 9), `prd.md > Screens and Layout` (11-admin-governance)
  Spec ref: `spec.md > Components` (9), `spec.md > Data Model` (LegalSource, ScoringRule, LLMConfig, CountryModule, AuditLog)
  Build: Admin API endpoints (role-guarded). Frontend: admin layout with sidebar, 6 pages with tables/forms. Seed creates one `platform_admin` user.
  Verify (mechanical): Log in as admin → validate a LegalSource → change a scoring weight → toggle a country module → audit log shows all actions with diffs.
  Learner check: Explore the admin console — verify you can manage the corpus and scoring rules without code changes.
  Commit: `Admin governance console: sources, rules, models, countries, users, audit logs`

- [ ] **7. End-to-end Polish + Final Verification**
  Becomes usable: Full core journey works smoothly: sign up → create project → upload doc → watch analysis → view double report → add context → see diff → admin manages corpus. Edge cases handled (empty states, errors, loading).
  Why now: Final integration slice — catches cross-cutting bugs, polishes UX to demo quality.
  PRD ref: `prd.md > What We're Building` (all 11 items), `prd.md > States and Boundaries`
  Spec ref: `spec.md > Important Failure Modes`, `spec.md > Look and Feel`
  Build: Fix any failing mechanical verifications. Add loading skeletons, error toasts, empty states. Ensure all 11 screens render per mockups. Run full journey manually.
  Verify (mechanical): Complete core journey on fresh `docker-compose up` with no errors. All 4 failure modes from spec have fallbacks triggered and working.
  Learner check: Walk the entire demo script (sign up → StockOpti project → upload PDF → report → context → diff) and note any friction.
  Commit: `Polish, edge cases, full journey verified`

## Hands-on Checkpoints

- [ ] Early feedback — after slice 3 (RAG kernel working), learner reviews consensus logic and badges
- [ ] Final kick-the-tires — after slice 7, full journey exploration and feedback

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: 
Route and stops: 
Edit outcome: 
Reflection: 
Activity mode: 

## Revisions