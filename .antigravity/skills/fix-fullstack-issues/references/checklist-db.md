# Checklist PostgreSQL / pgvector

- Alembic : migrations cohérentes avec les modèles SQLModel, une seule tête, applicables sur une base vide ET sur la base existante.
- Extension `vector` créée ; dimension des colonnes vectorielles cohérente avec le modèle d'embedding utilisé ; index vectoriels (ivfflat/hnsw) si recherche volumineuse.
- Index sur les colonnes filtrées/jointes, FK, UNIQUE, NOT NULL, types de colonnes, valeurs par défaut.
- Transactions : commit/rollback explicites, pas d'écritures partielles.
- Requêtes N+1, pagination, tris stables.
- Données orphelines (lignes sans parent, objets MinIO sans ligne en base et inversement).
- Deux drivers présents (asyncpg et psycopg2) : vérifier lequel sert à quoi (app vs Alembic) et que les URLs de connexion sont correctes.
