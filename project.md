
### 5.2. Composants techniques possibles

| Besoin                 | Technologie envisageable                            |
|------------------------|-----------------------------------------------------|
| API backend            | FastAPI                                             |
| Validation des données | Pydantic                                            |
| Base relationnelle     | PostgreSQL                                          |
| Recherche vectorielle  | PGVector ou ChromaDB                                |
| Tâches asynchrones     | Celery, RQ, Dramatiq ou solution équivalente        |
| Broker de messages     | Redis ou RabbitMQ                                   |
| Parsing PDF            | PyMuPDF, Marker ou outil équivalent                 |
| Parsing DOCX           | bibliothèque DOCX spécialisée                       |
| OCR                    | Tesseract ou service OCR souverain                  |
| Stockage objet         | MinIO ou stockage compatible S3                     |
| Conteneurisation       | Docker                                              |
| Reverse proxy          | Nginx ou Traefik                                    |
| Observabilité          | Prometheus, Grafana et centralisation des logs      |
| Authentification       | OAuth2/OIDC, JWT ou fournisseur d’identité maîtrisé |
| CI/CD                  | GitHub Actions, GitLab CI ou solution auto-hébergée |

> Le choix définitif doit tenir compte du niveau de souveraineté recherché, du coût d’exploitation, de la disponibilité des modèles et de la sensibilité des documents traités.

---

## 6. Workflow utilisateur

### Étape 1 : Création du projet

L’utilisateur crée un projet et renseigne :

- le pays cible ;
- le secteur d’activité ;
- le type de service ;
- le niveau de sensibilité ;
- les objectifs de l’analyse ;
- les éventuels sous-traitants ou fournisseurs concernés.

### Étape 2 : Dépôt du document

L’utilisateur téléverse un document, par exemple le cahier des charges d’une application fintech.

La plateforme vérifie :

- le format ;
- la taille ;
- la lisibilité ;
- la présence éventuelle de données personnelles ;
- la compatibilité avec le périmètre d’analyse.

### Étape 3 : Extraction et préparation

Le système :

- extrait le texte ;
- reconstruit la structure ;
- segmente le document ;
- détecte les passages exploitables ;
- calcule la qualité de l’extraction ;
- signale les pages illisibles ou ambiguës.

### Étape 4 : Analyse juridique et technique

Le moteur :

- détecte les traitements et obligations ;
- recherche les textes pertinents ;
- filtre les résultats selon le pays ;
- croise les sources ;
- applique les règles ;
- calcule le niveau de risque ;
- identifie les points nécessitant une revue humaine.

### Étape 5 : Restitution

Le tableau de bord affiche :

- le score global ;
- les risques par catégorie ;
- les clauses concernées ;
- les textes applicables ;
- les sources officielles ;
- les recommandations ;
- les autorités compétentes ;
- les limites et incertitudes.

#### Exemple de résultat

**Élément détecté :** stockage de données transactionnelles sur une infrastructure externe.

**Analyse :** le document semble prévoir le traitement de données financières et potentiellement personnelles par un prestataire tiers.

**Résultat :** risque élevé à vérifier selon le pays, la nature exacte des données, le prestataire, le lieu d’hébergement et le régime applicable.

**Actions proposées :**

- documenter la localisation de l’hébergement ;
- identifier le sous-traitant ;
- vérifier les formalités applicables auprès de l’autorité compétente ;
- vérifier les exigences sectorielles de paiement ;
- formaliser les clauses de sécurité et de protection des données ;
- contrôler les règles relatives aux transferts internationaux.

> Le système devra éviter de transformer automatiquement ce type d’analyse en affirmation absolue d’« obligation d’hébergement local » sans avoir vérifié le texte exact, sa portée et les conditions d’application.

---

## 7. Fonctionnalités nécessaires

### 7.1. Fonctionnalités du MVP

Le premier produit exploitable devrait inclure :

- création de compte et d’organisation ;
- gestion des projets ;
- sélection du pays cible ;
- téléversement de PDF et DOCX ;
- extraction de texte ;
- analyse de documents ;
- recherche dans un corpus juridique limité ;
- détection des sujets de conformité ;
- score de risque ;
- recommandations ;
- rapport structuré ;
- citation des sources ;
- historique des analyses ;
- suppression des documents ;
- journalisation des actions ;
- API FastAPI documentée avec OpenAPI.

### 7.2. Fonctionnalités de sécurité

- authentification forte ;
- contrôle d’accès par organisation ;
- chiffrement en transit ;
- chiffrement au repos ;
- expiration des fichiers temporaires ;
- suppression sécurisée ;
- limitation de taille et de fréquence ;
- analyse antivirus des fichiers ;
- protection contre les fichiers malveillants ;
- protection contre les prompt injections dans les documents ;
- isolation des tâches d’analyse ;
- journalisation des accès ;
- rotation des secrets ;
- sauvegardes chiffrées ;
- procédure de restauration testée.

### 7.3. Fonctionnalités de qualité et de fiabilité

- indication des sources utilisées ;
- score de confiance ;
- indication des informations manquantes ;
- détection des conflits entre textes ;
- versionnement du corpus ;
- versionnement des rapports ;
- explication du calcul du score ;
- validation humaine des règles critiques ;
- tests de non-régression sur un corpus de documents ;
- suivi des hallucinations ou citations incorrectes ;
- possibilité de marquer un résultat comme incorrect.

### 7.4. Fonctionnalités avancées

À envisager après validation du MVP :

- comparaison entre deux versions d’un contrat ;
- analyse multi-pays ;
- espace de revue collaborative ;
- commentaires et assignation d’actions ;
- notifications par e-mail ou webhook ;
- intégration avec Jira, Linear ou outils de ticketing ;
- API pour cabinets d’avocats et consultants ;
- génération de modèles de clauses ;
- recommandations de mesures techniques ;
- analyse des architectures cloud ;
- veille réglementaire ;
- alertes lors de la mise à jour d’un texte ;
- déploiement on-premise ;
- modèle de langage local ;
- signature ou horodatage renforcé des rapports.

---

## 8. Sources documentaires à intégrer

Les sources doivent être ingérées à partir de sites officiels ou de dépôts institutionnels vérifiables. Le système devra stocker l’URL, la date de collecte, l’autorité, le type de texte, la juridiction et le hash du document.

### 8.1. CEDEAO

- Textes communautaires de la CEDEAO publiés par l’ANSSI Côte d’Ivoire
- Acte additionnel CEDEAO relatif à la protection des données personnelles — référence listée par l’ANSSI Côte d’Ivoire

> L’Acte additionnel A/SA.1/01/10 relatif à la protection des données à caractère personnel dans l’espace CEDEAO constitue notamment une source communautaire à intégrer et à relier aux textes nationaux. *[anssi.gouv]*

### 8.2. Bénin

- Gouvernement du Bénin — mentions légales et références au Code du numérique
- Service public du Bénin — politique de confidentialité et formalités liées aux données personnelles
- APDP Bénin — mentions légales
- APDP Bénin — espace d’information
- APDP Bénin — formulaire unique relatif aux formalités
- APDP Bénin — document pédagogique sur la protection des données

> Le portail du Service public du Bénin rappelle notamment que les traitements de données personnelles sont soumis à des formalités préalables selon leur nature, et renvoie aux articles concernés du Code du numérique ainsi qu’à l’APDP. *[service-public]*

### 8.3. BCEAO et UEMOA

- BCEAO — FinTech et digitalisation des services financiers dans l’UEMOA
- BCEAO — cadre réglementaire des FinTech dans l’UMOA
- BCEAO — réglementation des systèmes de paiement
- BCEAO — ensemble des réglementations
- BCEAO — réglementation bancaire

> La BCEAO regroupe notamment des textes relatifs aux systèmes de paiement, à la monnaie électronique, aux services financiers décentralisés, à la réglementation bancaire et à la lutte contre le blanchiment. *[bceao]*

### 8.4. OHADA

Sources à prévoir dans le catalogue officiel :

- site officiel OHADA ;
- Acte uniforme relatif au droit commercial général ;
- Acte uniforme relatif aux sociétés commerciales et au groupement d’intérêt économique ;
- Acte uniforme portant organisation des procédures collectives ;
- Actes uniformes relatifs aux sûretés et au droit comptable ;
- jurisprudence ou documents officiels lorsqu’ils sont disponibles.

> Le corpus OHADA doit être traité séparément du corpus de protection des données et du corpus financier, car les niveaux de compétence, la terminologie et les effets juridiques ne sont pas identiques.

### 8.5. Autres autorités nationales

Pour l’extension régionale, le système devra intégrer progressivement :

- autorités de protection des données ;
- banques centrales et autorités financières ;
- autorités de régulation des communications électroniques ;
- autorités de cybersécurité ;
- ministères de la Justice et du Numérique ;
- portails officiels de publication des lois et règlements.

Pour chaque pays, une fiche de gouvernance des sources devra préciser :

- les domaines couverts ;
- les autorités reconnues ;
- les formats disponibles ;
- la fréquence de mise à jour ;
- le responsable de validation ;
- la procédure de correction.

---

## 9. Étude de faisabilité

### 9.1. Faisabilité technique

Le projet est techniquement réalisable avec FastAPI comme backend. Les principaux composants nécessaires sont disponibles et compatibles avec une architecture moderne :

- FastAPI pour l’API ;
- PostgreSQL pour les données métier ;
- PGVector ou ChromaDB pour la recherche sémantique ;
- PyMuPDF ou Marker pour l’extraction ;
- Docker pour l’isolation ;
- un système de tâches asynchrones pour les traitements longs ;
- un modèle de langage accessible via API ou hébergé localement.

> La principale difficulté ne réside pas dans la création de l’API, mais dans la **qualité du corpus juridique**, la validation des sources et la maîtrise des erreurs du moteur d’intelligence artificielle.

### 9.2. Faisabilité fonctionnelle

Le MVP est raisonnablement réalisable si le périmètre est limité à :

- un nombre réduit de pays ;
- quelques domaines juridiques ;
- des documents PDF et DOCX ;
- une première version de scoring ;
- une restitution avec sources et avertissements ;
- une revue humaine des résultats sensibles.

Il serait risqué de promettre dès la première version une couverture complète de toute la CEDEAO. Les législations nationales, les pratiques administratives, les formats des sources et les règles sectorielles sont trop hétérogènes pour une automatisation totale immédiate.

### 9.3. Faisabilité juridique

Le produit est faisable comme outil d’aide à la conformité, à condition de présenter clairement ses limites :

- il ne doit pas se présenter comme un cabinet d’avocats ;
- il ne doit pas garantir une conformité juridique absolue ;
- il doit distinguer analyse automatisée et validation professionnelle ;
- il doit conserver les preuves utilisées ;
- il doit afficher la date de dernière vérification des textes ;
- il doit signaler les zones d’incertitude ;
- il doit prévoir un mécanisme de correction.

Les rapports devront comporter une mention indiquant que l’analyse est documentaire et automatisée, et qu’une validation par un professionnel compétent peut être nécessaire avant une décision critique.

### 9.4. Faisabilité opérationnelle

Le principal enjeu opérationnel est la **maintenance du corpus** :

- les textes changent ;
- certaines sources officielles sont difficiles à automatiser ;
- des documents peuvent être publiés sous des formats irréguliers ;
- les textes peuvent être remplacés ou modifiés ;
- les interprétations administratives peuvent évoluer.

Il faudra donc prévoir une fonction de curation juridique, avec des personnes responsables de la collecte, de la vérification et de la mise à jour des sources.

### 9.5. Faisabilité économique

Le coût variera principalement selon :

- le volume de documents analysés ;
- le recours à des modèles externes ou locaux ;
- le coût du stockage et de l’OCR ;
- le niveau de haute disponibilité ;
- le nombre de pays couverts ;
- la nécessité d’une revue juridique humaine ;
- les exigences d’hébergement souverain.

Un modèle économique progressif peut être envisagé :

- offre d’essai limitée ;
- abonnement par organisation ;
- tarification par volume d’analyses ;
- offre entreprise avec espace isolé ;
- licence on-premise ;
- API pour cabinets et intégrateurs.

---

## 10. Risques principaux et mesures de réduction

| Risque                             | Impact        | Mesure recommandée                                                |
|------------------------------------|---------------|-------------------------------------------------------------------|
| Hallucination juridique            | Très élevé    | Réponse obligatoire avec sources, extraits et niveau de confiance |
| Source obsolète                    | Élevé         | Versionnement, date de vérification et veille réglementaire       |
| Mauvaise extraction PDF            | Élevé         | Score de qualité, OCR et signalement des passages incertains      |
| Confusion entre pays               | Très élevé    | Juridiction obligatoire dans chaque analyse                       |
| Source non officielle              | Élevé         | Validation éditoriale et classification des sources               |
| Empoisonnement du corpus           | Très élevé    | Hash SHA-256, provenance et workflow d’approbation                |
| Fuite d’un document client         | Très élevé    | Chiffrement, isolation et politique de rétention stricte          |
| Prompt injection dans un fichier   | Élevé         | Séparation instructions/contenu et filtrage des documents         |
| Surconfiance de l’utilisateur      | Élevé         | Mention claire des limites et validation humaine                  |
| Coût élevé des modèles IA          | Moyen à élevé | Mise en cache, modèles spécialisés et quotas                      |
| Difficulté de couverture régionale | Élevé         | Déploiement progressif pays par pays                              |

---

## 11. Sécurité et souveraineté

### 11.1. Protection des documents

Les documents utilisateurs doivent être considérés comme sensibles par défaut. Le système doit prévoir :

- chiffrement TLS ;
- chiffrement du stockage ;
- isolation logique par organisation ;
- suppression automatique des fichiers temporaires ;
- contrôle des accès par rôle ;
- journalisation des consultations ;
- absence d’utilisation des documents pour entraîner un modèle sans consentement explicite.

### 11.2. Protection du corpus juridique

Chaque texte juridique doit avoir :

- une empreinte SHA-256 ;
- une URL de provenance ;
- une autorité émettrice ;
- une date de collecte ;
- une date de dernière vérification ;
- une version ;
- un statut de validation ;
- une relation avec les textes précédents ou remplaçants.

### 11.3. Protection contre les attaques sur le moteur IA

Le système doit traiter les documents comme des données non fiables. Il faut notamment :

- isoler les instructions système du contenu analysé ;
- empêcher un document de modifier la politique du modèle ;
- filtrer les tentatives de prompt injection ;
- limiter les appels externes déclenchés par le contenu ;
- contrôler les outils accessibles à l’orchestrateur ;
- journaliser les décisions de l’agent ;
- appliquer des limites de temps, de coût et de profondeur.

---

## 12. API FastAPI — capacités attendues

L’API devra exposer des opérations autour des concepts suivants :

- utilisateurs ;
- organisations ;
- projets ;
- documents ;
- tâches d’analyse ;
- résultats ;
- risques ;
- recommandations ;
- sources juridiques ;
- règles ;
- rapports ;
- webhooks ;
- administration.

Les endpoints devront respecter les principes suivants :

- validation stricte des entrées ;
- réponses structurées ;
- pagination ;
- filtrage ;
- authentification ;
- contrôle d’accès ;
- gestion uniforme des erreurs ;
- documentation OpenAPI ;
- identifiants non prévisibles ;
- suivi de l’état des traitements asynchrones.

> Pour les analyses longues, l’API devrait retourner immédiatement un identifiant de tâche. Le client pourra ensuite consulter le statut ou recevoir une notification via webhook.

---

## 13. Roadmap recommandée

### Phase 1 — Socle technique
- API FastAPI
- Authentification
- Organisations et projets
- Dépôt de fichiers
- Stockage temporaire sécurisé
- Extraction PDF et DOCX
- Traitement asynchrone
- Premières métriques et journaux

### Phase 2 — Corpus initial
- Sélection des sources officielles
- Ingestion des textes béninois
- Intégration du corpus CEDEAO pertinent
- Intégration des sources BCEAO prioritaires
- Métadonnées, versionnement et hash
- Interface d’administration des sources

### Phase 3 — Première analyse de conformité
- Détection des entités
- Recherche vectorielle
- Règles de protection des données
- Analyse des clauses
- Score de risque
- Rapport avec citations
- Tableau de bord initial

### Phase 4 — Validation terrain
- Tests avec des documents réalistes
- Revue par des juristes et experts conformité
- Mesure de la précision
- Correction des faux positifs
- Amélioration des règles
- Tests de sécurité
- Tests de charge

### Phase 5 — Extension régionale
- Ajout de nouveaux pays
- Ajout des réglementations sectorielles
- Analyse multi-juridictions
- Veille réglementaire
- API partenaire
- Offre entreprise et déploiement souverain

---

## 14. Critères de réussite

Le projet pourra être considéré comme suffisamment mature lorsque :

- chaque conclusion critique est reliée à une source vérifiable ;
- les documents sont supprimés selon une politique contrôlable ;
- les utilisateurs peuvent comprendre pourquoi un risque a été détecté ;
- le système distingue clairement les pays et les domaines juridiques ;
- les résultats incertains sont explicitement signalés ;
- le corpus est versionné et administrable ;
- le temps d’analyse est acceptable ;
- les rapports sont exploitables par une équipe technique et une équipe juridique ;
- les faux positifs sont mesurés et réduits ;
- l’API est documentée et intégrable ;
- la plateforme résiste aux tests de sécurité et de confidentialité.

---

## 15. Conclusion

L’**ECO-Compliance Engine** est un projet techniquement réalisable et potentiellement pertinent pour l’écosystème numérique ouest-africain. Sa valeur ne reposera pas uniquement sur l’utilisation d’un modèle d’intelligence artificielle, mais sur la combinaison de quatre éléments :

1. un **corpus juridique fiable et maintenu** ;
2. une **analyse RAG contrôlée et traçable** ;
3. un **moteur de règles adapté aux juridictions** ;
4. une **architecture sécurisée et souveraine**.

> **Recommandation principale :** démarrer avec un périmètre contrôlé — **Bénin, protection des données, services numériques et fintech** — puis étendre progressivement le corpus et les pays couverts. Cette approche permettra de tester la qualité des résultats, la pertinence du scoring et la valeur réelle du produit avant d’engager une couverture complète de la CEDEAO.