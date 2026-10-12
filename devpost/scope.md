---
doc: scope
status: approved
---

# ECO-Compliance Engine (ECE)

Plateforme B2B souveraine d'audit documentaire automatisé — l'entrepreneur dépose son cahier des charges / politique de confidentialité et reçoit un double rapport traçable, sourcé et noté en confiance, ancré sur le droit CEDEAO/UEMOA/OHADA + droit national (Bénin en premier, architecture extensible par paramètre `pays`).

## The Unique Kernel

Ce qui le rend non remplaçable par "coller un PDF dans ChatGPT" : **sources prédéfinies et curatorées uniquement** (pas de web ouvert), **gestion explicite de l'obsolescence** (un texte de 2015 ne ressort pas comme valide sans vérification), **principe de non-hallucination** (badge de confiance + niveau de consensus, le modèle avoue ce qu'il ne sait pas), **architecture incrémentale multi-niveaux** (socle global CEDEAO/UEMOA/OHADA + module national sélectionné via `pays`) et **détection des conflits entre textes de niveaux différents** au lieu de choisir silencieusement. Le tout expliqué, sourcé jusqu'à l'article, avec empreinte et URL officielle.

## Who It's For

**Toi, porteur d'un projet logiciel d'optimisation et gestion de stock au Bénin, juste avant déploiement.** Tu as l'architecture, tu veux construire, mais tu ignores : est-ce que je risque du pénal / une suspension ? Les données que je collecte sont-elles personnelles/confidentielles ? Faut-il une autorisation APDP/BCEAO avant de mettre en ligne ? Aujourd'hui tu ferais : recherche manuelle éparse ou prompt ChatGPT générique, sans traçabilité, sans mise à jour, sans distinction Bénin vs CEDEAO.

Il sert aussi, par extension du même flux, tout fondateur fintech, CTO d'agence ou éditeur qui doit valider un cahier des charges avant d'aller voir un régulateur.

## The Core Loop

L'utilisateur crée un **projet** (pays cible parmi CEDEAO via paramètre `pays` + secteur + type de service/traitement), **dépose un document** (PDF natif, DOCX, Markdown/texte), le système **extrait et structure** (titres, clauses, qualité d'extraction), **détecte** termes légaux / traitements / données / zones floues ou trop génériques, **interroge le corpus** (global + module Bénin), **calcule consensus/confiance**, **détecte obsolescence et conflits**, puis **génère deux rapports** : 1) analyse du document fourni, 2) synthèse juridique sourcée. Il **consulte le dashboard** (scores, risques, sources, recommandations, limites), **ajoute une info complémentaire** si demandé → le système vérifie si un apport réel existe et **met à jour incrémentalement** uniquement les pages impactées en signalant ce qui a changé.

Pourquoi on revient : pour lever une incertitude, ajouter une précision, ou re-vérifier avant une mise en prod / une levée / un audit externe.

## Inspiration & Identity

Sobre, souverain, auditeur — pas chatbot. Tableaux de bord de compliance / legaltech où chaque affirmation pointe vers sa source. Ton, badges et traçabilité inspirés des rapports d'audit : lisible par un tech et un juriste. Références à préciser en PRD (exemples d'APDP Bénin, portail Service Public Bénin, BCEAO).

## Why This Matters to the Learner

Tu veux comprendre la meilleure façon de travailler avec un agent et surtout **repartir avec un projet qui marche**, pas une maquette. ECE est ta porte d'entrée souveraine pour l'écosystème ouest-africain : prouver qu'un audit traçable et multi-niveaux peut éviter suspension, sanction ou prison à un entrepreneur, en partant de ton propre cas (gestion de stock).

## What "Working" Looks Like

Démo en ~1 minute : tu crées le projet "StockOpti — Bénin", choisis `pays = BJ`, déposes l'architecture PDF de ton app de gestion de stock. Le système affiche l'extraction structurée + qualité, lance l'analyse, puis rend **deux rapports avec badges** (ex: "Fiabilité : 94% — Validé sur 3 sources officielles, aucune contradiction" vs "Fiabilité : 62% — 1 source, conflit CEDEAO/national détecté, à vérifier"). On voit : risques par catégorie, clauses concernées, textes applicables avec article/URL/hash, zones floues signalées ("point trop générique : lieu d'hébergement non précisé — info complémentaire demandée"), et un conflit mis en évidence. Tu ajoutes "hébergement chez X à Cotonou" → le système ne régénère pas tout : il **met à jour incrémentalement** et surligne les pages modifiées dans chaque rapport. C'est le "oh, that's cool" : traçabilité + incrémental, pas une régénération aveugle.

## The POC Boundary

**In — le vertical complet qui prouve le kernel (sans limite artificielle 2-4h, on construit tranquillement) :**
- Auth + organisations/projets, paramètre `pays` (liste CEDEAO, seul Bénin alimenté en corpus réel)
- Dépôt PDF natif / DOCX / Markdown-texte, extraction + normalisation Markdown, segmentation, détection langue/qualité
- Corpus minimal viable : Acte additionnel CEDEAO protection des données + textes Bénin (Code du numérique, APDP, formalités) + 2-3 textes BCEAO prioritaires, avec métadonnées complètes (autorité, date, URL, hash SHA-256, statut vérifiée/à vérifier)
- Recherche vectorielle + mots-clés (PostgreSQL + PGVector), filtrage par pays/domaine/niveau
- RAG orchestration + consensus (score de confiance, détection contradictions, gestion obsolescence, information manquante explicite)
- Scoring risque (Conforme / À surveiller / Risque modéré / Élevé / Critique) avec pondération
- Double rapport structuré avec badges, sources, extraits, limites et recommandations
- Mise à jour incrémentale à partir d'infos complémentaires (diff des pages impactées)
- Dashboard : projets, statut traitement, score, filtres risque/domaine, historique, export Markdown/PDF
- API FastAPI documentée (OpenAPI) + suivi asynchrone des tâches (job id + polling/webhook)
- Sécurité de base : isolation par organisation, chiffrement transit, rétention configurable, logs d'accès

## Later

- Alimentation complète des autres pays CEDEAO (Sénégal, Côte d'Ivoire, Togo, etc.) sans refonte — simple extension du module `pays`
- OCR (PDF scannés, Tesseract/service souverain) + tableaux/listes avancés
- Veille réglementaire et alertes sur mise à jour d'un texte
- Comparaison de deux versions d'un contrat, revue collaborative, commentaires/assignations
- Notifications webhook/email, intégrations Jira/Linear
- Déploiement on-premise / modèle local souverain, signature/horodatage renforcé des rapports

## Explicitly Cut

- **Moteur Q&A grand public autonome** (cas d'usage 1) : remplaçable par un moteur de recherche, hors cœur entrepreneurial
- **Certification ou garantie légale** : le score reste un indicateur d'aide à la décision, pas un avis d'avocat
- **Couverture exhaustive CEDEAO dès la V1** : on prouve l'architecture multi-niveaux avec Bénin, on n'ingère pas 15 juridictions d'un coup
- **OCR complexe et HTML/bureautique étendu en V1** : on sécurise le flux PDF natif/DOCX d'abord
