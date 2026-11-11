---
name: fix-fullstack-issues
description: Explore, diagnostique et corrige des bugs, fonctionnalités absentes ou faiblesses que l'utilisateur a déjà identifiés, en traçant le problème de bout en bout (front Next.js/React, back FastAPI, Celery/Redis, PostgreSQL/pgvector, MinIO, Docker Compose). À utiliser dès que l'utilisateur mentionne un bug, une erreur, une absence, une faiblesse, "ça ne marche pas", "vérifie le front et le back", "corrige", ou veut un audit ciblé d'un problème, même s'il ne précise pas quelle couche est en cause.
---

# Correction de problèmes full-stack

## Stack du projet
- Back : Python, FastAPI, fastapi-users (auth, OAuth Google/GitHub), SQLModel/SQLAlchemy async (asyncpg), Alembic, Celery, Redis, MinIO, PostgreSQL avec pgvector
- Front : Next.js (React), lancé avec `npm run dev`, API via `NEXT_PUBLIC_API_URL`
- Local : Docker Compose. Services : `postgres`, `redis`, `minio`, `backend` (:8000), `frontend` (:3000), `celery-worker`
- Aucun test automatisé n'existe pour l'instant : l'utilisateur teste manuellement

## Principes
- Ne jamais corriger sur une hypothèse : reproduire ou prouver d'abord.
- Suivre le flux complet (UI -> appel API -> route -> service -> DB/Redis/MinIO/Celery -> réponse -> affichage) avant de désigner la couche fautive.
- Corriger la cause racine, pas le symptôme. Changements minimaux et ciblés.
- Un problème = un correctif = une preuve de vérification. Ne pas mélanger les sujets.

## Étape 1 : Cadrer
1. Lister les problèmes signalés (symptôme, où, quand, comportement attendu).
2. Si une information bloquante manque, poser UNE seule question groupée. Sinon continuer.
3. Lire README, docker-compose.yml, requirements.txt, package.json, modèles et migrations.

## Étape 2 : État de l'environnement
1. `docker compose up -d --build` puis `docker compose ps` : tous les services doivent tourner.
2. `docker compose logs --tail=100 backend celery-worker frontend postgres minio`.
Un build réussi ne garantit pas un démarrage réussi : chercher crashs, retries de connexion, migrations non appliquées.

## Étape 3 : Cartographier
Pour chaque problème, tracer le chemin et noter fichier:ligne à chaque couche (utiliser `rg` sur routes, fonctions, tables, messages d'erreur).

## Étape 4 : Diagnostiquer
Lire les checklists selon les couches touchées :
- `references/checklist-front.md`
- `references/checklist-back.md`
- `references/checklist-celery.md`
- `references/checklist-db.md`
- `references/checklist-storage.md`
- `references/checklist-infra.md` (toujours lire au premier passage)
Vérifier aussi : variables d'environnement, CORS, auth, formats de données entre couches (noms de champs, types, dates), gestion d'erreurs, logs.

## Étape 5 : Reproduire (sans suite de tests existante)
Dans l'ordre de préférence :
1. Commande reproductible : `curl`/`httpx` sur l'endpoint, ou `docker compose exec backend python -c "..."`.
2. Si le bug est reproductible côté API, écrire un test `pytest` ciblé dans `backend/tests/` (pytest, pytest-asyncio et httpx sont déjà dans requirements.txt) et le conserver.
3. Si le bug est visuel/interactif, décrire des étapes manuelles précises (page, actions, attendu vs observé).
Ne jamais déclarer un bug corrigé sans l'une de ces preuves.

## Étape 6 : Corriger
- Modifier le minimum de fichiers, respecter les conventions existantes.
- Pas de nouvelle dépendance sans justification.

## Étape 7 : Vérifier
- Services : relancer, `docker compose ps`, logs sans erreur.
- Back : `docker compose exec backend ruff check .` ; `docker compose exec backend pytest` si des tests existent ; `curl http://localhost:8000/docs`.
- Front : `docker compose exec frontend npm run lint` et `npm run build`.
- Celery : déclencher l'action concernée et lire les logs de `celery-worker`.
- Si une vérification n'est possible que manuellement, écrire "non vérifié automatiquement" et fournir le scénario de test manuel (voir rapport). Ne jamais sous-entendre le contraire.
- Une commande qui échoue pour une raison sans lien : la signaler, ne pas la masquer.

## Étape 8 : Rapport
Pour chaque problème :
- **Cause racine** (fichier:ligne)
- **Correctif** (résumé du diff)
- **Vérification** (commande + résultat, ou "non vérifié automatiquement")
- **Scénario de test manuel** : 3 à 5 étapes à exécuter par l'utilisateur, avec le résultat attendu à chaque étape
- **Risques / à surveiller**
Terminer par la liste des faiblesses repérées mais NON corrigées (hors périmètre).

## Garde-fous
- Aucune commande destructive sans accord explicite : `docker compose down -v`, DROP/DELETE, reset de base, suppression de bucket, suppression de volume. Préférer des migrations réversibles.
- Ne pas modifier docker-compose.yml, les Dockerfile ni requirements.txt sans l'expliquer et obtenir un accord.
- Ne jamais écrire de secrets en clair ni committer de .env ou de clés API.
- Travailler en local uniquement, jamais sur une base de production.
- Demander confirmation avant tout changement de schéma, d'API publique ou de contrat entre couches.
- Ne pas refactorer au-delà de ce que le correctif exige.
