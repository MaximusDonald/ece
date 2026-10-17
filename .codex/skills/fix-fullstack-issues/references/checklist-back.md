# Checklist Back (FastAPI)

- Schémas Pydantic en entrée et sortie : `response_model` défini, aucun champ sensible renvoyé (hashed_password, secrets, tokens).
- Routes protégées par la bonne dépendance fastapi-users (`current_active_user`, superuser). Vérifier aussi l'autorisation sur la ressource (l'utilisateur ne peut accéder qu'à ses propres données), pas seulement l'authentification.
- OAuth Google/GitHub : URLs de redirection, `FRONTEND_URL`, gestion des erreurs de callback.
- Code bloquant (I/O synchrone, appels LLM synchrones, traitement de gros fichiers) dans des routes `async def` : déplacer vers Celery ou un threadpool.
- Sessions DB async : fermées correctement, pas de lazy loading hors session.
- Appels aux API LLM (OpenAI, Anthropic, Gemini, Groq) : timeouts, gestion des erreurs et limites de débit, clés manquantes.
- Validation des entrées et des fichiers uploadés (type, taille).
- Codes HTTP cohérents, messages d'erreur utiles sans fuite d'information interne.
- CORS aligné avec l'URL du front. Secrets et URLs via variables d'environnement (pydantic-settings), jamais en dur.
