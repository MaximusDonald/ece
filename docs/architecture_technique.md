# Architecture Technique — ECO-Compliance Engine

## 1. Vue d'ensemble des services

La plateforme repose sur une architecture conteneurisée à 7 services orchestrés par `docker-compose.yml` :

| Service | Technologie | Rôle |
| :--- | :--- | :--- |
| `frontend` | Next.js 15 (App Router), React, Tailwind CSS, TanStack Query | Interface utilisateur (projets, documents, rapports, qualification, administration) |
| `backend` | FastAPI, SQLModel, SQLAlchemy Async, Pydantic v2 | API REST, authentification JWT/RBAC, orchestration des tâches |
| `celery-worker` | Celery 5.4+ | Exécution asynchrone du pipeline d'audit en 5 étapes |
| `celery-beat` | Celery Beat | Tâches planifiées (veille réglementaire / sentinel) |
| `postgres` | PostgreSQL 16 + extension `pgvector` | Base relationnelle, index vectoriel HNSW et index plein texte français GIN |
| `redis` | Redis 7 | Broker Celery et backend de résultats / verrous distribués |
| `minio` | MinIO (S3 compatible) | Stockage objet des documents bruts, textes extraits et PDF générés |

---

## 2. Pipeline d'audit asynchrone (5 étapes + barrière projet)

```text
[Upload Multi-Documents]
        │
        ▼ (par document, en parallèle)
1. Extraction (workers/extraction.py)
   - PyMuPDF / python-docx / Markdown -> texte normalisé + hash SHA-256
        │
        ▼
2. Analyse Sémantique (workers/semantic.py)
   - Extraction des entités, traitements et zones floues (vague_zones)
        │
        ▼
[Barrière de Synchronisation Projet — get_project_analysis_readiness]
   - Vérifie que tous les documents non échoués du projet sont EXTRACTED + analysés
   - Déclenche la suite une seule fois via verrou Redis
        │
        ▼
3. Recherche Juridique & Audit Holistique (workers/legal_research.py -> compliance_auditor.py)
   - Déconstruction en 4 facettes canoniques
   - Recherche hybride Article-RAG (HNSW cosinus + GIN FTS français + pondération hiérarchique)
   - Détection des conflits de normes et vérification des parades inter-documents
        │
        ▼
4. Scoring Déterministe Stabilisé (workers/scoring.py -> compute_initial_severity_and_score)
   - Application de la ScoringRule (pays / domaine)
   - Rendements décroissants par facette, malus sanctions dédupliqué, compression > 70
        │
        ▼
5. Génération & Export du Rapport (workers/report.py -> pdf_generator.py)
   - Rédaction Markdown structurée + rendu PDF WeasyPrint + stockage MinIO
```

---

## 3. Moteur Article-RAG hybride (`backend/app/services/article_rag.py`)

### Recherche hybride
Pour chaque facette identifiée sur le dossier, `hybrid_search_articles` combine :
- **Score dense** (`alpha = 0.65`) : similarité cosinus sur les vecteurs `1536` dimensions stockés dans `legal_article.embedding` (index HNSW).
- **Score lexical** (`1 - alpha = 0.35`) : `ts_rank_cd` PostgreSQL avec analyseur `french` sur titre, numéro d'article et texte intégral.
- **Filtrage de validité temporelle** : `t.status = 'in_force'` et `(t.publication_date IS NULL OR t.publication_date <= CURRENT_DATE)`.

### Pondération hiérarchique et conflits
Les candidats sont reclassés par `apply_normative_ranking` selon la hiérarchie normative :
1. Normes communautaires / supranationales (`OHADA`, `UEMOA`, `CEDEAO`, `OAPI`, `UA`) : `× 1.18`
2. Lois nationales / Codes / Ordonnances : `× 1.08`
3. Décrets / Arrêtés : `× 1.00`
4. Directives / Circulaires / Recommandations sectorielles : `× 0.94`

`detect_normative_conflicts` identifie les concours entre niveaux différents ou juridictions nationales distinctes sur des thématiques communes et active automatiquement `conflict_flag` et `conflict_details`.

---

## 4. Gestion des gros dossiers (`format_dossier_for_prompt`)

Afin d'éviter la perte de clauses situées au milieu de documents volumineux (`> 60 000` caractères) :
1. `_split_markdown_passages` segmente le document selon ses titres Markdown (`#` à `####`) puis par paragraphes.
2. `_select_relevant_document_passages` attribue un score à chaque passage en fonction des mots-clés réglementaires des 4 facettes, des `vague_zones`, des `entities` et des ancres structurelles (début/fin).
3. Les passages les plus pertinents sont retenus dans un budget proportionnel à la taille de chaque document, puis réassemblés dans leur ordre chronologique d'origine.

---

## 5. Modèle de données principal

- `organization` / `user` : cloisonnement multi-tenant (`org_id`) et rôles RBAC (`UserRole`).
- `project` : paramètres juridictionnels, secteur, traitements et perspective (`represented_entity_type`, `represented_entity_other`, `represented_role_details`).
- `document` / `document_extraction` / `document_analysis` : cycle de vie des pièces déposées et du document de contexte complémentaire (`contexte_complementaire`).
- `legal_text` / `legal_section` / `legal_article` : référentiel hiérarchique du corpus juridique.
- `report_version` / `risk_finding` : versions de rapports, score global, distribution de sévérité, `legal_nature`, `review_status`, `reviewed_by`, `reviewed_at`, `review_note`.
- `scoring_rule` / `llm_config` / `country_module` / `audit_log` : gouvernance plateforme.
