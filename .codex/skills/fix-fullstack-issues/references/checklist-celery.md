# Checklist Celery + Redis

- Le worker démarre et se connecte au broker (logs `celery-worker`). L'app Celery est bien `app.workers.celery_app`.
- Les tâches sont découvertes/importées (pas de tâche "unregistered").
- Tâches idempotentes ; retries, timeouts et `acks_late` définis selon le besoin.
- Arguments sérialisables : passer des IDs, jamais des objets ORM ou des fichiers en mémoire.
- Le worker a la même config que l'API (DB, Redis, MinIO, clés API). Comparer les variables d'environnement des deux services.
- Code async (asyncpg) appelé depuis une tâche Celery synchrone : vérifier la gestion de la boucle d'événements.
- Statut et résultat de la tâche remontés à l'utilisateur (polling, champ en base, etc.). Erreurs loguées et état final cohérent en cas d'échec.
- `--concurrency=2` : vérifier l'absence de contention sur ressources partagées.
