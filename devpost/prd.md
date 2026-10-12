---
doc: prd
status: approved
---

# ECO-Compliance Engine (ECE) — Product Requirements

> Plateforme B2B souveraine d'audit documentaire automatisé et de vérification de conformité juridique et technique pour la zone CEDEAO/UEMOA (départ Bénin).
> Source: `scope.md > ECO-Compliance Engine (ECE)` et `scope.md > The Unique Kernel`.

---

## The Core Journey

Source: `scope.md > The Core Loop` et `scope.md > What "Working" Looks Like`.

1. **Arrival & Authentication (`01-landing-auth.html`)**: L'utilisateur accède à la plateforme ECE. Il se connecte avec son e-mail/mot de passe ou via OAuth (Google / GitHub) pour accéder à son espace d'organisation.
2. **Onboarding / Dashboard (`02-onboarding.html`, `03-dashboard.html`)**: En premier usage, un rapide guide d'accueil ("Create your first project") présente la logique d'analyse par pays et domaine. Sur le tableau de bord principal, l'utilisateur voit ses métriques clés (analyses effectuées, risques ouverts, score moyen) et la liste de ses projets actifs.
3. **Création de Projet (`04-new-project.html`)**: L'utilisateur clique sur "New Project". Il renseigne le nom ("StockOpti — Bénin"), la juridiction cible (Bénin pré-sélectionné dans la liste CEDEAO `pays`), le secteur (ex: Commerce / FinTech / Services Numériques) et coche les types de traitement applicables (Protection des données, Services de paiement, etc.).
4. **Dépôt de Document (`05-project-overview.html`, `06-doc-upload.html`)**: Dans l'onglet *Documents* du projet, il clique sur "Upload Document". Il glisse-dépose son cahier des charges ou sa politique de confidentialité en PDF natif, DOCX ou Markdown (jusqu'à 50 Mo) et lance l'analyse.
5. **Traitement Asynchrone (`07-analysis-progress.html`)**: L'écran affiche la progression en 5 étapes clés (Extraction → Analyse sémantique → Recherche juridique → Scoring → Génération de rapport) avec un indicateur de temps restant.
6. **Consultation du Double Rapport (`08-report-dashboard.html`)**: Une fois terminé, le tableau de bord du rapport s'affiche. L'utilisateur voit le score global de risque (ex: 65/100, Risque modéré), la répartition par sévérité (Critique, Élevé, Modéré, Faible) et explore les 3 vues :
   - **Findings**: les non-conformités et zones floues détectées dans le document original ;
   - **Legal Sources**: les textes juridiques officiels appliqués (avec niveau de confiance, statut d'obsolescence et conflits de normes) ;
   - **Recommendations**: les actions correctives administratives et techniques.
7. **Ajout de Contexte Complémentaire (`09-complementary-info.html`)**: Pour lever une zone floue (ex: lieu d'hébergement non précisé), l'utilisateur clique sur "Add Complementary Context". Il sélectionne la localisation exacte de l'hébergement (ex: Cotonou, Bénin).
8. **Mise à Jour Incrémentale & Comparaison (`10-history-comparison.html`)**: Le système re-vérifie le contexte, effectue une **mise à jour incrémentale** des rapports et affiche la comparaison entre v1.0 et v1.1 : seules les pages et clauses modifiées/résolues sont surlignées en diff (`[Nouveau]`, `[Résolu]`, `[Mis à jour]`).

---

## Screens and Layout

Basé directement sur la suite de mockups validés (`ece-mockups/screens/*.html`) :

1. **01-landing-auth.html — Landing & Auth Screen**:
   - Panneau latéral gauche bleu roi souverain présentant la proposition de valeur ECE (traçabilité, souveraineté, CEDEAO/UEMOA).
   - Formulaire droit avec bascule *Sign In* / *Create Account*, saisie e-mail/password, bouton "Remember me" et boutons OAuth (Google, GitHub).
2. **02-onboarding.html — Onboarding Guide**:
   - Guide pas à pas minimaliste expliquant l'organisation par projet, pays et type de service, avec bouton "Skip tour" et bouton "Next".
3. **03-dashboard.html — Main Dashboard**:
   - Sidebar de navigation (Dashboard, Reports, Team, Settings).
   - En-tête avec bouton principal `+ New Project`.
   - 3 cartes KPI supérieures : *Analyses completed*, *Open risks*, *Avg. compliance score*.
   - Table dynamique des projets avec filtres (*All*, *Active*, *Completed*, *Archived*), colonnes : *Project Name*, *Country*, *Sector*, *Status*, *Risk Score Badge*, *Last Analysis*.
4. **04-new-project.html — New Project Form**:
   - Formulaire épuré : Nom du projet (Champ texte *ex: Benin Fintech Licence Application*), Pays cible (Select box avec Bénin pré-sélectionné parmi les 15 états CEDEAO), Secteur (Select box), Type de service/traitement (Cases à cocher *Data Protection*, *Payment Services*, *E-commerce*, etc.).
5. **05-project-overview.html — Single Project Workspace**:
   - En-tête de projet avec badges de métadonnées (Bénin, FinTech, Data Protection, Active).
   - Boutons d'action : `Upload Document`, `Manage Team`, `Settings`.
   - Onglets de navigation : *Documents*, *Analyses*, *Reports*, *Settings*.
   - Table des documents téléversés avec format (PDF, DOCX), taille, date, statut (*Completed*, *Processing*) et actions (*View*, *Download*, *Delete*).
6. **06-doc-upload.html — Upload Document Modal/Screen**:
   - Titre du document (optionnel), Type de document (détection auto / sélection manuel).
   - Zone de Drag & Drop pour fichiers PDF, DOCX, Markdown (jusqu'à 50 Mo) avec bouton d'exploration.
7. **07-analysis-progress.html — Analysis Progress Stepper**:
   - Stepper visuel à 5 étiquettes numérotées : 1. Extraction → 2. Semantic Analysis → 3. Legal Research → 4. Scoring → 5. Report Generation.
   - Barre de progression animée avec temps estimé restant (*ex: 45 seconds*).
8. **08-report-dashboard.html — Compliance Report Dashboard**:
   - En-tête avec score de risque global (*Score/100* + Badge de couleur *ex: Risque modéré*).
   - Bloc synthétique : Nombre de risques détectés, obligations trouvées, sources utilisées, et **Niveau de confiance global (High / Medium / Low)**.
   - Ventilation par sévérité : *Critical* (Rouge), *High* (Orange), *Medium* (Jaune), *Low* (Gris).
   - Navigation par onglets : *Findings* (Constats), *Legal Sources* (Textes juridiques), *Recommendations* (Actions).
9. **09-complementary-info.html — Complementary Context Screen**:
   - Formulaire ciblé pour lever les ambiguïtés : sélection de la localisation d'hébergement, nom du sous-traitant principal, détails de transfert.
   - Encadré pédagogique expliquant l'impact de ces précisions sur le score final.
10. **10-history-comparison.html — Report History & Version Comparison**:
    - Historique des versions du rapport (ex: v1.0, v2.0, v2.1) avec leurs scores respectifs.
    - Vue comparative côte à côte highlighting les clauses modifiées, résolues ou ajoutées.
11. **11-admin-governance.html — Admin & Governance Console** (accès réservé rôle `platform_admin`) :
    - Sidebar dédiée : *Sources*, *Règles de scoring*, *Modèles*, *Pays/Juridictions*, *Utilisateurs*, *Audit Logs*.
    - **Sources** : Table des textes juridiques ingérés (Titre, Autorité, Pays, Niveau, Statut *Vérifiée/À vérifier/Archivée*, Date collecte, Hash SHA-256, URL). Actions : *Valider*, *Marquer abrogé*, *Remplacer*, *Vérifier URL*.
    - **Règles de scoring** : Éditeur de règles déterministes (pondérations par niveau de risque, seuils de confiance) avec prévisualisation d'impact.
    - **Modèles** : Sélection du modèle LLM utilisé (API externe / local), paramètres de température, max tokens, prompt système versionné.
    - **Pays/Juridictions** : Activation/désactivation des modules pays, liaison corpus national ↔ socle communautaire.
    - **Utilisateurs** : Liste, rôle (admin org / analyste / lecteur / auditeur externe / platform_admin), organisation, dernier accès, quotas.
    - **Audit Logs** : Traçabilité des actions sensibles (upload, analyse, export, validation source, modification règle).

---

## Look and Feel

- **Direction visuelle**: Esthétique institutionnelle B2B souveraine, sobre et auditable. Inspirée des outils de legaltech et de gouvernance de données. *Note : la palette et le design visuel sont indicatifs et peuvent évoluer lors de la phase de build sans impacter le périmètre fonctionnel.*
- **Palette de couleurs** (proposition initiale, ajustable) :
  - Primaire : Bleu Souverain (`#0052A5`, sombre `#003D7A`, clair `#E8F1FA`).
  - Succès / Conforme : Vert Émeraude (`#007B3F`, clair `#E8F5ED`).
  - Avertissement / À surveiller / Modéré : Jaune/Ambre (`#E6A800`, clair `#FFF8E1`).
  - Risque Élevé / Critique : Rouge Rubis (`#C41E3A`, clair `#FDEDEA`).
  - Neutres : Neutres Slate (`#0F172A` à `#F8FAFC`).
- **Typographie**: Police système propre (`Inter`, -apple-system, sans-serif), grande lisibilité des chiffres et des badges.
- **Composants d'audit**: Badges pilules colorés, indicateurs de confiance explicites, codes de couleurs par niveau de sévérité, cartouches de citation d'articles de loi.

---

## Features and Behavior

### 1. Gestion des Utilisateurs & Espaces Projets
- L'utilisateur s'authentifie pour accéder à ses organisations et projets.
- Chaque projet isole ses documents, ses analyses et ses rapports.
- La création de projet exige la sélection d'un pays membre de la CEDEAO (paramètre `pays`), avec le **Bénin** pré-sélectionné et activement alimenté pour le POC.

### 2. Ingestion & Extraction Documentaire
- Prise en charge des formats **PDF natif**, **DOCX** et **Markdown / Texte brut**.
- Normalisation du contenu en Markdown structuré avec préservation des titres, clauses et paragraphes.
- Calcul automatique d'un score de qualité d'extraction (signalement si page illisible ou incomplète).

### 3. Recherche Juridique, Consensus & Badge de Confiance
- Interrogation du corpus sur deux niveaux :
  1. **Socle communautaire** (CEDEAO / UEMOA / OHADA) ;
  2. **Module national** (Bénin : Code du Numérique, APDP, textes BCEAO).
- Filtrage strict par le paramètre `pays` du projet.
- calcul d'un **Badge de Confiance** pour chaque constat :
  - *High (Haute)* : Validé sur au moins 2 sources officielles concordance sans ambiguïté ;
  - *Medium (Moyenne)* : Source unique ou information partiellement explicite dans le document ;
  - *Low (Faible / Incertain)* : Information manquante ou zone floue nécessitant un complément d'information.
- Détection explicite de l'**Obsolescence** (un texte abrogé est marqué `[Abrogé/Ancien]`) et des **Conflits de Normes** (désaccord entre texte communautaire CEDEAO et texte national Bénin affiché au lieu d'être masqué).

### 4. Double Rapport de Conformité
- **Rapport 1 : Analyse Documentaire Interne** :
  - Liste des clauses analysées, repérage des manquements (ex: absence de clause de rétention), détection des termes trop vagues ou trop généraux.
- **Rapport 2 : Synthèse Juridique & Réglementaire** :
  - Correspondance entre le projet et les textes officiels applicables avec citation exacte de l'article de loi, l'autorité émettrice, l'URL officielle et le hash SHA-256 du texte source.
- Classification des risques selon 5 niveaux : *Conforme*, *À surveiller*, *Risque modéré*, *Risque élevé*, *Critique*.

### 5. Complément d'Information & Mise à Jour Incrémentale
- Lorsqu'une zone floue est détectée (ex: "Lieu d'hébergement non précisé"), le rapport propose le bouton "Add Complementary Context".
- L'utilisateur saisit l'information manquante dans un formulaire dédié.
- Le système re-évalue **uniquement le contexte modifié** sans réanalyser l'intégralité du document et réalise une **mise à jour incrémentale** du rapport.
- L'écran d'historique (`10-history-comparison.html`) surligne les diffs entre versions (anciennes vs nouvelles clauses).

### 6. Console d'Administration & Gouvernance (`11-admin-governance.html`)
- Accessible uniquement aux comptes dotés du rôle `platform_admin`.
- **Gestion du corpus juridique** : Validation, marquage d'obsolescence, remplacement, vérification d'intégrité (hash SHA-256 vs URL officielle) des textes sources.
- **Configuration du moteur de scoring** : Édition des pondérations, seuils de confiance, règles déterministes par domaine/pays.
- **Gestion des modèles LLM** : Choix du fournisseur (API / local), version du prompt système, paramètres de génération.
- **Activation des modules pays** : Bascule d'activation des juridictions nationales, liaison avec le socle communautaire CEDEAO/UEMOA/OHADA.
- **Supervision utilisateurs & organisations** : Vue agrégée, rôles, quotas, derniers accès.
- **Journaux d'audit immuables** : Traçabilité complète des actions critiques (ingestion source, validation règle, lancement analyse, export rapport).

---

## States and Boundaries

- **First Use (Nouveau projet)**: Le tableau de bord affiche le guide d'accueil ("Create your first project"). La table des documents est vide avec un bouton d'action principal bien en vue.
- **Analysis In Progress (Traitement asynchrone)**: L'utilisateur voit l'animation du stepper à 5 étapes avec estimation du temps restant. Les actions d'édition du document sont bloquées pendant le traitement.
- **Empty State (Aucun document)**: L'onglet *Documents* du projet affiche une zone de glisser-déposer invitant au téléversement.
- **Zone Floue / Information Manquante**: Si le document ne contient pas assez de détails sur un point critique, le rapport génère un constat avec le statut `Incomplet / Action Requise` et un lien vers le formulaire de complément.
- **Conflit Juridique Détecté**: Si deux textes de loi se contredisent, le rapport affiche un encadré ambre `Conflit de normes` avec les deux articles cités côte à côte.
- **Persistence & Isolation**: Les documents et rapports sont persistés en base de données relationnelle et associés de manière isolée à l'organisation de l'utilisateur.

---

## Product Decisions

- **Sélection du Périmètre POC** : Priorité absolue sur le cas d'usage **Audit Entrepreneurial** (validateurs de cahier des charges) plutôt que le moteur de recherche grand public Q&A. *Raison : valeur métier élevée, problème critique de responsabilité pénale/administrative pour les éditeurs.*
- **Architecture Multi-Pays par Paramètre `pays`** : Conception d'un sélecteur CEDEAO complet dans l'I/O, tout en restreignant l'ingestion du corpus national réel au **Bénin** pour le POC. *Raison : prouve l'extensibilité régionale sans diluer l'effort sur 15 législations.*
- **Transparence de l'Incertitude** : Affichage explicite des badges de confiance et des informations manquantes plutôt que d'autoriser le modèle LLM à forcer une conclusion incertaine. *Raison : exigence fondamentale de traçabilité d'un auditeur souverain.*
- **Mise à Jour Incrémentale** : Conservation des versions antérieures de rapport et comparaison par diff de pages/clauses. *Raison : gain de temps majeurs pour l'utilisateur qui modifie un paragraphe de son contrat.*

---

## What We're Building

1. **Interface Web Complète (11 écrans)** basés sur les mockups fournis (Auth, Onboarding, Dashboard, New Project, Workspace, Upload, Processing, Report, Complementary Info, Version Comparison, **Admin Governance**).
2. **Module d'Auth & Organisation** (Inscription/Connexion, isolation des espaces de travail, rôles utilisateur).
3. **Module de Dépôt & Extraction Documentaire** (Upload PDF/DOCX/Markdown, extraction structurée).
4. **Corpus Juridique Initial Bénin + CEDEAO/UEMOA/BCEAO** avec métadonnées complètes (URL, autorité, article, SHA-256).
5. **Moteur d'Analyse RAG Traçable & Consensus** avec scoring de confiance, détection d'obsolescence et de conflits de normes.
6. **Moteur de Scoring de Risque** (5 niveaux : Conforme à Critique).
7. **Double Rapport de Conformité** (Analyse documentaire + Synthèse juridique) exportable.
8. **Module de Mise à Jour Incrémentale** (Formulaire de complément contextuel + diff de versions).
9. **Console d'Administration & Gouvernance** (Gestion sources, règles scoring, modèles LLM, modules pays, audit logs).
10. **API FastAPI documentée (OpenAPI)** gérant le traitement asynchrone des analyses.

---

## Deferred From the POC

- **Alimentation du corpus juridique complet des 14 autres pays de la CEDEAO** (Sénégal, Côte d'Ivoire, Togo, etc.) — *différé pour le post-POC*.
- **OCR complexe pour PDF scannés de mauvaise qualité** — *flux limité aux PDF natifs et DOCX/Markdown*.
- **Abonnements payants et quotas Stripe/Paystack** — *toutes les fonctionnalités sont ouvertes en mode POC*.
- **Veille réglementaire automatisée par scraping quotidien** — *remplacé par un corpus fixe vérifié pour le POC*.

---

## Possible Later Enhancements

- Module de relecture collaborative de contrat avec commentaires par équipe.
- Intégration par webhook vers Slack, Jira ou Linear pour créer des tickets de non-conformité automatisés.
- Déploiement souverain On-Premise avec modèle de langage LLM local.

---

## Non-Goals

- **Aucune délivrance de certification juridique légale** : ECE est un outil d'aide à la décision et d'audit documentaire automatisé ; il ne se substitue pas à l'avis d'un avocat inscrit au barreau.
- **Pas d'accès au web ouvert non contrôlé lors des analyses** : le RAG interroge uniquement le corpus juridique interne vérifié et horodaté.
- **Pas de réécriture aveugle de tout le rapport lors d'un ajout de contexte** : le système procède strictement par mise à jour incrémentale.

---

## Open Questions

- *Format d'export privilégié* : L'export PDF du rapport doit-il inclure les extraits de code source juridique bruts ou uniquement le résumé synthétique ? (Peut être tranché en `4-spec`).
