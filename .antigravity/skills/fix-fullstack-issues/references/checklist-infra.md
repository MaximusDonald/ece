# Checklist Infra (Docker Compose)

- Image MinIO : `sourcemation/minio:latest` est une image tierce non officielle. Images officielles : `minio/minio` ou `quay.io/minio/minio`. Éviter `latest` : épingler une version. Signaler, ne pas modifier sans accord.
- MinIO sans healthcheck (`service_started` seulement) : le backend peut démarrer avant que MinIO soit prêt.
- Aucun bucket créé au démarrage : vérifier que le code ou un script le crée.
- Alembic : aucune commande de migration dans le compose. Vérifier comment et quand les migrations sont appliquées.
- Extension pgvector : vérifier que `CREATE EXTENSION IF NOT EXISTS vector` est exécuté (migration ou init).
- `SECRET_KEY` absent du service `celery-worker` : vérifier si une tâche en a besoin.
- Clés API sans valeur par défaut (`${OPENAI_API_KEY}`...) : si .env est absent, elles sont vides. Le code doit échouer proprement et clairement.
- `passlib[bcrypt]==1.7.4` avec une version récente de `bcrypt` (non épinglée) : erreurs possibles au hash/login. Vérifier si l'auth échoue.
- spaCy : le modèle de langue doit être téléchargé (Dockerfile). weasyprint : bibliothèques système (Pango, etc.) nécessaires. Ces points peuvent casser au runtime sans casser le build.
- Volumes `./backend:/app` et `./frontend:/app` : attention aux conflits avec les dépendances installées dans l'image (node_modules, .next déjà isolés dans le compose).
- Ports exposés (5432, 6379, 9000, 9001) et credentials par défaut : acceptables en local, à ne pas reprendre en production.
