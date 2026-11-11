# Checklist MinIO

- Credentials via variables d'environnement ; `MINIO_SECURE` cohérent avec l'endpoint.
- Bucket existant au démarrage ou créé par le code.
- URLs présignées : le hostname doit être accessible depuis le navigateur (`minio:9000` n'est résolvable que dans le réseau Docker). Vérifier l'endpoint utilisé pour les URLs données au front.
- Expiration des URLs présignées adaptée.
- Validation du type et de la taille des fichiers uploadés ; noms d'objets sûrs et uniques.
- Nettoyage des objets orphelins à la suppression d'une ressource.
- Gros fichiers : upload/streaming sans tout charger en mémoire.
