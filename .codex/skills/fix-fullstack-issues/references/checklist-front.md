# Checklist Front (Next.js / React)

- États loading, erreur et vide gérés ; validation des formulaires.
- Appels API : URL de base via `NEXT_PUBLIC_API_URL` (variable inlinée au build/démarrage, redémarrer le front après changement), méthode, payload, en-têtes.
- Gestion du token : stockage, expiration, réponse 401, redirection vers login ; flux OAuth Google/GitHub et retour sur `FRONTEND_URL`.
- Erreurs réseau et erreurs serveur affichées clairement à l'utilisateur.
- Race conditions : requêtes concurrentes, cleanup des `useEffect`, double soumission.
- Server components vs client components (`"use client"`) : hooks/APIs navigateur seulement côté client ; erreurs d'hydratation.
- Aucun secret dans le bundle : toute variable `NEXT_PUBLIC_*` est publique.
- `npm run build` sans erreur de types ni d'imports ; accessibilité de base (labels, focus).
