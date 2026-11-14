# Cahier des Charges — ECO-Compliance Engine (ECE)

## 1. Contexte et problématique

Les entreprises numériques, fintechs, éditeurs SaaS et prestataires techniques opérant en Afrique de l'Ouest sont soumis à un empilement normatif complexe :
- **Droit communautaire et régional** : Actes uniformes OHADA, Règlements et Instructions UEMOA/BCEAO, Actes additionnels CEDEAO, accords OAPI, Convention de Malabo (Union Africaine).
- **Droit national** : Codes du numérique, lois sur la protection des données à caractère personnel, cybersécurité et transactions électroniques (ex. Loi n° 2017-20 au Bénin, lois équivalentes au Sénégal, Côte d'Ivoire, Togo, etc.).

L'audit manuel d'un dossier projet multi-documents (cahier des charges, politique de confidentialité, CGU, contrats de sous-traitance, architecture cloud) est long, coûteux et sujet aux oublis lorsqu'une mesure compensatoire figure dans un document distinct du document principal.

---

## 2. Objectifs du système

1. **Centraliser et croiser l'ensemble des pièces d'un projet** dans une analyse holistique unique (aucun document analysé isolément sans vision du reste du dossier).
2. **Ancrer chaque constat sur des articles de loi réels et en vigueur**, avec citation exacte du texte, de l'article, de la juridiction et des sanctions encourues.
3. **Éliminer les faux positifs et les faux négatifs** grâce à la détection des *parades d'annulation* inter-documents et à l'application stricte du principe de précaution.
4. **Fournir un score de risque stable, explicable et paramétrable**, insensible au découpage rédactionnel du LLM.
5. **Garantir l'opposabilité du rapport** via la qualification juridique des constats, la validation humaine horodatée (piste d'audit) et un export PDF unifié.

---

## 3. Acteurs et contrôle d'accès (RBAC)

| Rôle | Périmètre autorisé | Restrictions |
| :--- | :--- | :--- |
| **Analyste / Juriste** (`analyst`, `org_admin`) | Création de projets, dépôt de documents, gestion du contexte complémentaire, lancement d'audits, qualification/validation des constats, export PDF/Markdown. | Cloisonné strictement aux projets de son organisation (`org_id`). |
| **Lecteur / Auditeur externe** (`reader`, `external_auditor`) | Consultation des projets et rapports autorisés. | Pas de modification de configuration globale. |
| **Administrateur Plateforme** (`platform_admin`) | Gouvernance du corpus juridique (`LegalText`, articles), règles de scoring, configuration des LLM, modules pays, consultation des journaux d'audit. | **Interdiction stricte** d'accéder aux projets, documents et rapports privés des organisations clientes (retourne `403 Forbidden`). |

---

## 4. Exigences fonctionnelles

### EF-01 — Paramétrage du projet et perspective d'analyse
- Chaque projet définit : `name`, `country_code` (ISO 3166-1 alpha-2), `sector`, `treatments`, ainsi que **l'entité représentée** (`entreprise`, `developpeur_engage`, `prestataire_externe`, `dpo_juriste`, ou `autre` avec libellé obligatoire) et des précisions optionnelles sur le rôle.
- Le moteur d'audit adapte la lecture des responsabilités, risques et recommandations à cette perspective.

### EF-02 — Ingestion multi-documents et suivi temps réel
- Téléversement groupé (PDF, DOCX, Markdown, TXT, jusqu'à 50 Mo par fichier) vers MinIO.
- Pipeline asynchrone par document (Extraction -> Analyse sémantique) avec suivi d'avancement par étape sur l'interface utilisateur.

### EF-03 — Barrière de synchronisation projet
- La recherche juridique, le scoring et la génération du rapport commun ne démarrent que lorsque **tous** les documents non échoués du projet ont terminé leur extraction et leur analyse sémantique.

### EF-04 — Contexte complémentaire consultable et modifiable
- L'ajout de contexte complémentaire crée ou met à jour un document dédié (`document_type = "contexte_complementaire"`), consultable et éditable depuis l'interface.
- Lors d'une régénération de rapport, ce document de contexte ainsi que le résumé de la version précédente du rapport sont injectés dans l'analyse.

### EF-05 — Rapport unifié et export
- Génération de deux vues complémentaires (Analyse documentaire & Synthèse juridique) consolidées lors du téléchargement en **un seul rapport maître PDF (WeasyPrint) ou Markdown** proprement structuré.

### EF-06 — Qualification juridique et piste d'audit
- Chaque constat porte une nature juridique (`non_conformite_imperative`, `risque_contractuel`, `bonne_pratique`) et un statut de revue humaine (`pending`, `validated`, `mitigated_by_evidence`, `dismissed`) avec auteur, horodatage et note justificative, préservés lors des régénérations ultérieures sans contradiction nouvelle.

---

## 5. Exigences non fonctionnelles

- **Traçabilité** : rejet automatique de tout UUID d'article halluciné par le LLM ; résolution déterministe vers les UUID réels du référentiel PostgreSQL.
- **Validité temporelle** : exclusion stricte des textes marqués `abrogated` ou dont la date de publication est postérieure à la date courante.
- **Passages longs** : préservation des clauses critiques situées au cœur de documents volumineux (> 100 000 caractères) grâce au découpage par sections Markdown et au scoring de pertinence.
- **Isolation et déploiement** : exécution complète reproductible via Docker Compose (`postgres`, `redis`, `minio`, `backend`, `celery-worker`, `celery-beat`, `frontend`).
