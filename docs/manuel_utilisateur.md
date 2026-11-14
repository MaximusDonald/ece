# Manuel Utilisateur — ECO-Compliance Engine

## 1. Espace Analyste / Juriste

### 1.1 Créer un projet d'audit
1. Connectez-vous à l'interface (`http://localhost:3000`).
2. Dans **Projets**, cliquez sur **Nouveau projet**.
3. Renseignez :
   - le **nom du projet** ;
   - le **pays principal** (ex. Bénin `BJ`, Sénégal `SN`, Côte d'Ivoire `CI`, Togo `TG`) ;
   - le **secteur d'activité** et les **traitements** concernés ;
   - **l'entité représentée** (champ obligatoire : Entreprise, Développeur engagé, Prestataire externe, DPO / Juriste, ou Autre à préciser) ainsi que des précisions optionnelles sur le rôle.

> La perspective choisie oriente l'analyse des responsabilités et des recommandations dans le rapport.

### 1.2 Déposer les documents du dossier
1. Ouvrez l'onglet **Documents** du projet.
2. Sélectionnez ou déposez **un ou plusieurs fichiers simultanément** (PDF, DOCX, Markdown, TXT, max 50 Mo/fichier).
3. Suivez la progression du pipeline par document :
   - *Extraction* -> *Analyse sémantique* -> *Recherche juridique* -> *Scoring* -> *Génération du rapport*.
4. La génération du rapport commun démarre automatiquement une fois que **tous** les documents non échoués du projet sont prêts.

### 1.3 Consulter, qualifier et valider les constats
1. Ouvrez l'onglet **Rapports**.
2. Sélectionnez la version souhaitée (`v1.0`, `v1.1`, etc.).
3. Chaque fiche de constat affiche :
   - la sévérité (`CRITIQUE`, `ELEVE`, `MODERE`, `A_SURVEILLER`, `CONFORME`) et le niveau de confiance ;
   - la **nature juridique** (`Non-conformité impérative`, `Risque contractuel`, `Bonne pratique`) et le **statut de revue** ;
   - les alertes éventuelles : *Source potentiellement abrogée* (`obsolescence_flag`) ou *Conflit de normes* (`conflict_flag` + encart `conflict_details`).
4. Cliquez sur **Qualifier / Valider** sur un constat pour :
   - ajuster la nature juridique ;
   - saisir une note justificative (ex. référence d'un récépissé APDP ou d'un contrat signé) ;
   - enregistrer le statut (`Valider`, `Mitigé par preuve`, `Écarter`).
   La piste d'audit horodatée est enregistrée et préservée lors des futures régénérations.

### 1.4 Ajouter ou modifier le contexte complémentaire
- Cliquez sur **Ajouter contexte** pour répondre aux zones floues identifiées ou fournir des précisions supplémentaires.
- Ce contexte est automatiquement stocké dans un document dédié du projet, consultable et modifiable à tout moment via **Consulter / Modifier contexte**.
- Chaque soumission déclenche une réévaluation complète tenant compte de tous les documents, du contexte enregistré et de la version précédente du rapport.

### 1.5 Télécharger le rapport unifié
- Utilisez le bouton de téléchargement PDF ou Markdown pour obtenir **le rapport maître complet** fusionnant l'analyse documentaire par clause, la synthèse juridique, les citations d'articles et les recommandations.

---

## 2. Espace Administrateur Plateforme

> L'administrateur plateforme accède aux vues `/dashboard/admin/*` et ne peut pas consulter les projets ou rapports privés des organisations.

### 2.1 Règles de scoring (`/dashboard/admin/rules`)
- Visualisez le récapitulatif de la politique stabilisée (poids de base, rendements décroissants par facette, sanctions dédupliquées, plancher 50 et compression > 70).
- Créez ou modifiez une règle par **pays** et **domaine**.
- Utilisez le **simulateur en direct** intégré à la modale pour vérifier l'impact des coefficients sur trois profils types avant d'enregistrer.

### 2.2 Corpus juridique, LLM, pays et audit
- **Corpus (`/dashboard/admin/corpus`)** : import, indexation, mise à jour du statut (`in_force`, `revised`, `abrogated`) et vectorisation des articles.
- **Modèles LLM (`/dashboard/admin/llm`)** : configuration des fournisseurs actifs (Gemini, OpenAI, Anthropic) et seuils.
- **Pays (`/dashboard/admin/countries`)** : activation des modules nationaux.
- **Journaux d'audit (`/dashboard/admin/audit-logs`)** : traçabilité des actions d'administration.
