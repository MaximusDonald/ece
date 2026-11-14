# Guide de Déploiement et d'Exploitation

## 1. Prérequis

- **Docker** 24+ et **Docker Compose** v2
- Ports disponibles localement : `3000` (Frontend), `8000` (API), `5432` (PostgreSQL), `6379` (Redis), `9000` / `9001` (MinIO)
- Clé API valide pour le fournisseur LLM configuré (`GEMINI_API_KEY`, `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`)

---

## 2. Configuration de l'environnement

Copier le fichier modèle et renseigner les variables obligatoires :

```bash
cp .env.example .env
```

Variables principales à vérifier dans `.env` :

| Variable | Description |
| :--- | :--- |
| `DATABASE_URL` | Chaîne de connexion PostgreSQL asynchrone (`postgresql+asyncpg://...`) |
| `REDIS_URL` | URL Redis utilisée par Celery et les verrous de barrière projet |
| `SECRET_KEY` | Clé secrète JWT (à remplacer impérativement en production) |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Accès au stockage objet MinIO |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Clé(s) d'accès aux modèles d'embeddings et de complétion |

---

## 3. Démarrage et migrations

```bash
# Construction et démarrage de tous les services
docker compose up -d --build

# Application des migrations PostgreSQL (dont 20261114_04 pour l'audit trail)
docker compose exec backend alembic upgrade head
```

Vérifier l'état des services :

```bash
docker compose ps
```

---

## 4. Vérification de la stack et tests

### Backend (`pytest`)
```bash
docker compose exec -T backend pytest -v \
  tests/test_finding_review_audit_trail.py \
  tests/test_large_dossier_selection.py \
  tests/test_normative_hierarchy.py \
  tests/test_rbac_and_scoring_policy.py \
  tests/test_compliance_auditor.py
```

### Frontend (`TypeScript`)
```bash
docker compose exec -T frontend npx tsc --noEmit
```

---

## 5. Sauvegarde et maintenance

- **Base PostgreSQL** : sauvegarder régulièrement le volume `postgres_data` via `pg_dump`.
- **Stockage MinIO** : sauvegarder le volume `minio_data` contenant les documents sources et les rapports PDF.
- **Journaux d'exécution** : consulter les logs des workers via `docker compose logs -f celery-worker backend`.
