Original URL: https://www.perplexity.ai/search/f5f50bb6-42cf-44f1-82db-3705b7592982
Conversation Time: 07/10/2026 16:51:28
Export Time: 07/10/2026 18:00:43

**[USER]**

Voici-ci dessous une étude de faisabilité de mon projet j'aimerais que tu le mette à jour en intégrant considérant les changement suivants: la pertinence si on se recentre sur les boutiques de maison et autres , et non les marchés ? A part, ça, pour le reste , c'était bien ça . Mais est-ce que c'est bon comme ça ? L'état de l'art de solutions pareilles. 






## Étude de faisabilité : comptabilité vocale en fon pour commerçants peu lettrés


Système étudié : le commerçant parle en fon → l'application identifie la transaction (vente, achat, crédit + produit, quantité, montant) → la transaction est enregistrée et affichée en français → une confirmation audio est jouée en fon → bilans et export PDF.


Date de l'étude : octobre 2026. Sources : le document « Faisabilité et état de l'art » fourni, vérifié et complété par des recherches indépendantes (fiches des modèles, articles scientifiques, statistiques officielles).


## 1. Synthèse et verdict


| Niveau d'ambition | Faisabilité | Commentaire |
| --- | --- | --- |
| Prototype de démonstration (soutenance, environnement calme, Élevée vocabulaire fermé, 10–30 produits) | reconnaissance des montants. | Toutes les briques existent ; le risque principal est la |
| Pilote terrain (20–50 commerçants réels, Moyenne marché bruyant, plusieurs accents) Faible à Produit commercial à grande échelle moyenne |   | Nécessite un corpus métier propre, une boucle de confirmation systématique et un mode hors ligne. Bloqué par les licences non commerciales des modèles Meta MMS, le manque de données de parole spontanée et |
| aujourd'hui |   | les contraintes d'équipement des usagers. |


Verdict : GO conditionnel. Le projet est réaliste comme prototype et comme pilote, à condition de :


- 1. traiter les nombres et les montants comme un sous-problème à part entière (c'est la variable qui décide du succès ou de l'échec) ;


- 2. ne jamais enregistrer une transaction sans confirmation vocale du commerçant ;


- 3. constituer un petit corpus de parole commerciale réelle (marchés, plusieurs locuteurs, plusieurs accents) ;


- 4. choisir dès le départ des modèles dont la licence est compatible avec l'usage visé.


## 2. Vérification du document de départ


Plusieurs affirmations du document fourni doivent être corrigées ou nuancées avant d'être reprises dans un mémoire ou devant un jury.



| Affirmation du document | Ce que disent les sources | Conséquence |
| --- | --- | --- |
|   | Le corpus contient un sous-ensemble de | Les deux voies sont |
| FFSTC‑2 relie l'audio fon directement au texte | 36 h avec transcriptions en fon | possibles ; la cascade (avec |
| français, « sans texte fon dans la boucle » | (pour l'ASR et la cascade) et 48 h pour la | texte fon) donne même les |
|   | traduction parole → français (IWSLT | meilleurs résultats. |
|   | 2025) |   |
|   | 17,02 % est obtenu sans diacritiques |   |
|   | ; les auteurs précisent que ce chiffre | Citer 22 % comme référence |
| « WER ≈ 17 % » pour FFSTC‑2 | n'est pas directement comparable. Avec | honnête. |
|   | diacritiques, le WER est de 21,98 % |   |
|   | (Interspeech 2025) |   |
|   | Meilleure cascade : BLEU 39,60 ; | La traduction libre reste |
|   | meilleur système end-to-end : BLEU | imparfaite, ce qui confirme |
| Résultats de traduction | d'environ 28 (IWSLT 2025). La première | l'intérêt du vocabulaire |
|   | version FFSTC n'atteignait que BLEU | fermé. |
|   | 8,96 (arXiv FFSTC) |   |
| Modèles | Ces noms apparaissent dans une liste |   |
| fortunedavis/ffstc_asr_base et | de recherche Hugging Face, mais leur | À considérer comme non |
|   | fiche n'a pas pu être consultée : ni | vérifiés tant qu'ils n'ont |
| fongbe-ffstc-asr « utilisables directement | contenu, ni performances, ni licence | pas été testés. |
| » | vérifiés |   |
|   |   | Usage académique |
|   | La page du dataset n'affiche aucune | défendable ; usage |
| Le corpus FFSTC‑2 est librement réutilisable | licence explicite, et une discussion | commercial ou |
|   | ouverte pose justement la question | redistribution à clarifier |
|   |   | avec les auteurs. |
|   | facebook/mms-300m, mms-1b- |   |
|   | all et mms-tts-fon sont sous | Bloquant pour une |
| Les modèles MMS sont des briques libres | licence CC‑BY‑NC 4.0 (non | commercialisation (voir |
|   | commerciale) (mms-300m, | section 5.7). |
|   | mms-1b-all, mms-tts-fon) |   |
|   | La fiche est incohérente : elle |   |
| speechbrain/asr-wav2vec2-dvoice- | mentionne aussi un affinage sur la | À retester soi-même avant |
| fongbe est un ASR fongbe fiable (WER 9 %) | darija et un jeu de données darija (fiche | de le citer. |
|   | SpeechBrain) |   |
|   | Whisper ne prend pas en charge le | Seules les variantes affinées |
| Whisper est une option pour le fon | fongbe et bascule vers une transcription | par la communauté (LoRA) |
|   | en français (arXiv 2606.22274) | sont envisageables. |


Point méthodologique essentiel : les corpus FFSTC‑2 sont de la parole lue, enregistrée en environnement contrôlé ; les enregistrements bruités ont été rejetés, et les locuteurs à accent mahi ou gungbe ont été exclus (IWSLT 2025). Les phrases viennent de Common Voice traduites en fon, sans vocabulaire commercial. Le terrain visé (marché, parole spontanée, accents variés, mélange fon‑français) est donc hors de la distribution de ces données. [URL 🔗](https://aclanthology.org/2025.iwslt-1.13.pdf)



## 3. Cadre social


## 3.1 Les usagers visés


- Alphabétisation : environ 51 % des 15 ans et plus savent lire et écrire, selon la fiche pays du ministère français des Affaires étrangères (Banque mondiale 2022). D'autres estimations donnent 47,1 %, avec un écart marqué entre hommes (57,9 %) et femmes (36,4 %) (Alliance biblique). [URL 🔗](https://www.diplomatie.gouv.fr/fr/information-par-pays/benin/presentation-du-benin)


- Informalité : le taux d'informalité des entreprises reste de 85,9 % en 2023 (INStaD) ; environ 90 % de la population travaille dans l'informel, qui pèse 60 à 70 % du PIB (OHADA). [URL 🔗](https://www.ohada.com/actualite/2551/le-benin-premier-pays-membre-de-lohada-a-mettre-en-oeuvre-le-statut-de-lentreprenant-un-regime-simplifie-et-gratuit-pour-promouvoir-la-formalisation-des-micro-et-petites-entreprises.html?langue=fr)


- Un public surtout féminin : le commerce occupe 54 % des femmes interrogées dans une enquête d'ONU Femmes, et les femmes représentent environ 74,5 % du commerce de détail selon l'INStaD. [URL 🔗](https://data.unwomen.org/sites/default/files/documents/Publications/Rapport_UNWOMEN_BENIN.pdf)


Conséquence de conception : l'utilisatrice type est une commerçante qui ne lit ni le fon ni le français et a un accès limité au numérique. L'interface doit fonctionner entièrement à la voix et avec des icônes. Le texte français ne sert qu'aux tiers (famille, agent de microfinance, administration).


## 3.2 La langue


- Le fon compte environ 2,3 millions de locuteurs natifs (Wikipedia EN) et sert de langue véhiculaire dans le sud du pays (Wikipedia FR). [URL 🔗](https://fr.wikipedia.org/wiki/Fon_(langue))


- Il existe plusieurs variétés (agbome, arohun, gun, gbekon, kpase) (Wikipedia). Dans les marchés de Cotonou, on entend aussi le goun, le mina, le yoruba et l'adja. [URL 🔗](https://en.wikipedia.org/wiki/Fon_language)


- L'alternance fon‑français est courante à Cotonou, Abomey-Calavi et Abomey (thèse Zossou, UnB). Les noms de produits et les montants sont donc souvent dits en français au milieu d'une phrase en fon. [URL 🔗](https://repositorio.unb.br/bitstream/10482/43067/1/2021_AlbanAminouZossou.pdf)


- Le fon dispose d'un alphabet officiel (décret 2008-576), mais peu de commerçants l'écrivent. C'est un argument fort en faveur d'une approche qui ne demande jamais d'écrire. [URL 🔗](https://sgg.gouv.bj/doc/decret-2008-576/download)


## 3.3 Accès au numérique et à l'énergie


| Indicateur Valeur Source Utilisateurs d'internet (fin 2025) 4,80 millions, soit 32,2 % de la population DataReportal 2026 Utilisateurs réguliers d'internet 28 % de la population, 48 % des adultes GSMA via Agence Ecofin mobile (2023) Possession d'un smartphone 39 % (contre 76 % pour un téléphone mobile) Digital Virgo Près de 100 % en ville, 63 % de la population Couverture 4G Agence Ecofin rurale couverte |
| --- |
| Banque mondiale, Mission 300, Accès à l'électricité (2024) 42,6 %, moins de 13 % en milieu rural Mongabay Coût de la data ex. 995 FCFA pour 1 Go valable 3 jours chez MTN MTN Bénin |


## Conséquences :



- Environ six commerçantes sur dix n'ont pas de smartphone. Il faut prévoir un mode partagé (un téléphone pour un groupement, une association ou une tontine) ou un canal par appel téléphonique (serveur vocal) pour atteindre les téléphones basiques.


- La connexion n'est ni continue ni gratuite : il faut une architecture hors ligne d'abord, avec synchronisation, et des envois audio compressés.


- La batterie et la recharge comptent : le traitement sur le téléphone doit rester léger.


## 3.4 Confiance, sensibilité des données et cadre légal


- Les transactions de « crédit » contiennent des noms de clients et des dettes, donc des données personnelles. Elles relèvent du Livre 5 de la loi n° 2017‑20 portant Code du numérique, sous le contrôle de l'APDP. [URL 🔗](https://archive.apdp.bj/lois/la-loi-n-2017-20-portant-code-du-numerique-en-republique-du-benin/)


- Il faut prévoir : un consentement oral enregistré, un stockage chiffré, la possibilité de supprimer ses données, et une déclaration auprès de l'APDP si le service est déployé. La collecte de voix pour l'entraînement doit faire l'objet d'un consentement distinct.


- Pour être adopté, l'outil doit être plus fiable que le cahier ou la mémoire du commerçant. Une seule erreur sur un montant de crédit peut créer un conflit avec un client et faire abandonner l'outil.


## 3.5 Cadre comptable : une vraie valeur ajoutée


- Le Système Minimal de Trésorerie (SMT) du SYSCOHADA s'applique aux très petites entreprises (au Bénin, un seuil de 30 millions FCFA de chiffre d'affaires est cité). Il exige un journal de caisse chronologique et deux états annuels : l'état des recettes et des dépenses, et l'état de situation patrimoniale (Keematch). [URL 🔗](https://keematch.com/blog/le-systeme-minimal-de-tresorerie-smt-ohada-guide-complet-pour-les-tpe-en-2026)


- Le Bénin a été le premier pays de l'OHADA à mettre en œuvre le statut gratuit de l'entreprenant, avec un accompagnement à la tenue des comptes (OHADA). [URL 🔗](https://www.ohada.com/actualite/2551/le-benin-premier-pays-membre-de-lohada-a-mettre-en-oeuvre-le-statut-de-lentreprenant-un-regime-simplifie-et-gratuit-pour-promouvoir-la-formalisation-des-micro-et-petites-entreprises.html?langue=fr)


Opportunité : si l'export PDF reprend le format du journal de caisse SMT, le projet devient un outil d'accès au crédit et de formalisation, ce qui intéresse les institutions de microfinance, les ONG et l'État. C'est un argument social fort pour un jury.


## 3.6 Écosystème : partenaires et concurrents


| Acteur Ce qu'il fait Lien avec le projet ASIN / IIDiA – Collecte citoyenne de voix en fon, dendi, yoruba, bariba et Partenaire et source de JaimeMaLangue (lancé le 10 mina pour une base vocale « souveraine » ; les applications données potentiels novembre 2025) bancaires vocales font partie des usages visés (gouv.bj) IIDiA – modèle voix‑à‑voix Prototype prévu en 9 mois, avec un cas d'usage de Concurrent ou fournisseur en fon (juin 2025) consultation de solde Mobile Money (Financial Afrik) futur de briques |
| --- |
| Comptabilité vocale pour commerçants (pidgin, yoruba, Référence de performance Intron – SautiLedger / Koko anglais) ; sur de l'audio réel avec mélange de langues, réaliste seulement 47 % de transactions exactes (Intron) Même concept : ASR, extraction par LLM, confirmation Buku (Kenya) Architecture comparable vocale ; Flutter + FastAPI (Lanfrica) |



| Acteur | Ce qu'il fait | Lien avec le projet |
| --- | --- | --- |
|   | Application comptable avec guidage vocal en langues | Montre qu'un guidage vocal |
| Odwadini (Ghana) | ghanéennes (Google Play) | sans reconnaissance libre est |
|   |   | déjà utile |
| Vambo AI | API commerciales de traduction, synthèse et | Solution de repli payante |
|   | reconnaissance vocale incluant le fon (Vambo) |   |


Lecture : le concept de « voice bookkeeping » existe déjà. La contribution originale du projet est l'application au fon, avec une conception pour non-lecteurs et une sortie conforme au SMT. Le chiffre de 47 % de transactions exactes obtenu par Intron, avec un modèle commercial bien plus entraîné, montre l'ampleur de la difficulté en conditions réelles.


## 4. Faisabilité technique : état des briques


| Performance Brique Meilleure option vérifiée Licence Évaluation publiée WER 9,48 %, CER Bon point de Professor/mms-300m- 3,96 % sur le test Base départ, mais testé ASR fon (300M) fongbe ALFFA, parole lue ( CC‑BY‑NC uniquement sur de fiche) la parole propre WER 19,27 % sur 7 CC‑BY‑4.0 locuteurs inconnus ; inesassia/fonbench-mms- affichée, Trop lourd pour un ASR fon (1B) non adapté au bruit 1b-fon-ft mais base téléphone ni à l'alternance CC‑BY‑NC fon‑français (fiche) Donne l'ordre de WER 21,7 % sur grandeur ASR fon + modèle asrDIL/mms-fongbe- parole lue, 43,7 % Non indiquée réaliste en de langue finetuned-v4 sur parole conditions spontanée (fiche) terrain Utile pour pré- Corpus fon ↔ FFSTC‑2, 61 h, 5,66 Go — Non indiquée adapter le modèle ; français hors domaine wav2vec2-xls-r-300m Encodeurs à Voie à suivre pour (Apache‑2.0, 128 langues) ; w2v- licence À affiner soi-même Permissive un usage bert-2.0 (MIT, 600M) (XLS‑R, permissive commercial w2v‑BERT) Facile dans un Règles et grammaire, Snips NLU, ou Compréhension domaine fermé, une tête de classification sur — Open source de l'intention sauf pour les l'encodeur nombres |
| --- |
| Aucune évaluation publiée ; voix Préférer des Synthèse vocale facebook/mms-tts-fon unique ; sortie CC‑BY‑NC phrases fon (36M paramètres) variable d'une préenregistrées exécution à l'autre ( fiche, export ONNX) |



| Brique | Meilleure option vérifiée | Performance | Licence | Évaluation |
| --- | --- | --- | --- | --- |
|   |   | publiée |   |   |
| Exécution sur | sherpa‑onnx (Android, hors ligne) ( |   |   |   |
|   |   | — | Apache‑2.0 | Mature |
| téléphone | GitHub) |   |   |   |
| Application, base | Flutter, FastAPI, SQLite, WeasyPrint | — | Libres | Aucun risque |
| de données, PDF |   |   |   |   |


Conclusion : aucune brique ne manque. Le risque ne vient pas de l'existence des outils, mais de l'écart entre les conditions de test publiées (parole lue, propre) et les conditions réelles (marché, spontané, mélange de langues).


## 5. Difficultés techniques majeures


## 5.1 Les nombres et les montants (risque n° 1)


- La numération traditionnelle fon n'est pas décimale : elle combine des bases 5, 20, 40 et 200 (De Gruyter, grammaire du fongbe). Exemples : 20 = ko, 40 = kanɖé, 80 = kanwe (40 × 2), 100 = kanwe-ko (80 + 20), 200 = afɔɖé, 1 000 = afɔ-atɔ́ɔn (MPI-EVA, numéraux). [URL 🔗](https://api.pageplace.de/preview/DT0400.9783110880182_A19978731/preview-9783110880182_A19978731.pdf)


- En pratique, les commerçants mélangent probablement nombres fon et nombres français (« cinq mille »). Il est aussi possible que certaines habitudes de comptage monétaire diffèrent du décompte en francs CFA : c'est à vérifier sur le terrain avec des linguistes et des commerçants.


- Les systèmes de reconnaissance vocale sont réputés fragiles sur les nombres, même dans les langues bien dotées (Google Research). [URL 🔗](https://research.google/pubs/improving-performance-of-end-to-end-asr-on-numeric-sequences/)


- Une erreur sur un montant ne se voit pas, alors qu'une erreur sur un nom de produit se remarque facilement. C'est pourtant l'erreur la plus coûteuse pour l'usager.


## Parades :


- un module dédié qui convertit les nombres fon et français en chiffres, avec une grammaire explicite ;


- une relecture systématique du montant (« 5 000 francs, c'est bien ça ? ») avec une réponse oui ou non ;


- un contrôle de vraisemblance : prix unitaire habituel du produit, alerte si l'écart est trop grand ;


- en dernier recours, une saisie sur un clavier numérique avec des billets et des pièces illustrés.


## 5.2 Le décalage entre corpus et terrain


Tous les modèles disponibles ont été entraînés sur de la parole lue et propre. Le passage de 21,7 % à 43,7 % de WER entre parole lue et parole spontanée (asrDIL) donne l'ordre de grandeur de la dégradation. Le bruit des marchés (moteurs, appels de vendeurs, musique) s'y ajoute, et la fiche de mms-300m-fongbe prévient elle-même d'une baisse de performance en milieu bruyant. [URL 🔗](https://huggingface.co/asrDIL/mms-fongbe-finetuned-v4)



Parade : constituer un corpus métier de 1 500 à 3 000 énoncés (hypothèse de travail), auprès de 30 à 50 locuteurs, hommes et femmes, de différents accents, enregistrés en partie sur les marchés, avec un téléphone d'entrée de gamme. Ajouter des données augmentées (bruit de marché superposé).


## 5.3 Tons, diacritiques et orthographe


Les modèles ne restituent pas correctement les distinctions tonales (fiche fonbench), et les conventions de diacritiques varient d'un jeu de données à l'autre (arXiv 2605.22828). Pour ce projet, c'est un problème moins grave qu'il n'y paraît : on ne cherche pas à produire du fon écrit correct, mais à reconnaître un petit nombre de mots-clés. Il est conseillé de normaliser en supprimant les diacritiques avant l'étape de compréhension. [URL 🔗](https://arxiv.org/html/2605.22828v1)


## 5.4 Accents, variétés et mélange de langues


FFSTC‑2 a exclu les accents mahi et gungbe. Or, à Cotonou et Porto-Novo, beaucoup de commerçants parlent goun. Le mélange fon‑français ne figure dans aucun corpus d'entraînement disponible. Il faut tester par variété et prévoir un lexique de produits bilingue (« savon », « riz », « sac » sont souvent dits en français).


## 5.5 Choix d'architecture


| Option | Avantages | Inconvénients | Recommandation |
| --- | --- | --- | --- |
| A. ASR fon → règles et grammaire → | Lisible, facile à déboguer, | Les erreurs de l'ASR se |   |
| structure | peu de données nécessaires | propagent | Version 1 |
|   | Résiste mieux aux erreurs de | Les nombres restent |   |
| B. Encodeur gelé + tête de | transcription ; peut | difficiles à classer (trop de | Version 2, pour |
| classification (intention + produit) | fonctionner sans texte fon | valeurs possibles) | l'intention et le produit |
| C. Hybride : B pour l'intention et le |   |   |   |
| produit, A pour les nombres, plus | Combine les forces des deux | Plus complexe | Cible du pilote |
| un dialogue de confirmation |   |   |   |
|   |   | BLEU de 28 à 40 |   |
| D. Traduction parole → français | État de l'art académique | seulement, modèles | À citer comme |
| façon FFSTC‑2, puis extraction |   | lourds, poids non publiés | perspective |


Un dialogue guidé (« Vente ou achat ? », « Quel produit ? », « Combien ? ») réduit fortement l'espace des réponses possibles à chaque étape. Il est moins naturel qu'une phrase libre, mais bien plus fiable. Il est recommandé comme mode de secours lorsque le niveau de confiance du modèle est faible.


## 5.6 Déploiement : sur le téléphone ou sur un serveur


- Taille estimée des modèles : environ 1,2 Go en FP32 pour un modèle de 300M paramètres, environ 300 Mo après quantification int8 (estimation) ; le modèle de 1B pèse 3,6 Go (asrDIL), ce qui est irréaliste sur un téléphone d'entrée de gamme. [URL 🔗](https://huggingface.co/asrDIL/mms-fongbe-finetuned-v4)


## Recommandation :


- pour le prototype, traitement sur serveur via FastAPI ;



- pour le pilote, un modèle 300M quantifié exécuté sur le téléphone avec sherpa‑onnx ou ONNX Runtime, et une synchronisation des données quand la connexion le permet ;


- en parallèle, explorer un canal par appel téléphonique pour les téléphones basiques.


## 5.7 Licences : variable bloquante pour une commercialisation


Les modèles MMS (y compris les versions affinées pour le fon qui en dérivent) et MMS‑TTS sont sous licence CC‑BY‑NC. Ils conviennent pour un mémoire ou un pilote non lucratif, mais pas pour un produit payant.


Voie de sortie : réaffiner un encodeur sous licence permissive (XLS‑R en Apache‑2.0, w2v‑BERT 2.0 en MIT) sur des données dont la licence est claire (ALFFA, JaimeMaLangue si un accord est obtenu, corpus métier propre). Il faut aussi obtenir des auteurs une licence écrite pour FFSTC‑2.


## 5.8 Réponse vocale en fon


- Phrases préenregistrées par un locuteur natif : c'est l'option la plus fiable.


- La difficulté est de prononcer les montants : il faut enregistrer les briques de la numération (unités, ko, kanɖé, afɔɖé, milliers…) et les assembler, ce qui demande une validation par un linguiste.


- MMS‑TTS peut servir pour les phrases rares, mais sa qualité n'a pas été évaluée et sa licence est non commerciale.


## 6. Variables à fort impact


|   |   |   | Probabilité d'un Mesure d'atténuation |
| --- | --- | --- | --- |
| # | Variable | Impact | problème |
|   | Exactitude des montants | Critique | Module numérique dédié, confirmation, Élevée |
| 1 |   |   | contrôle de vraisemblance |
|   |   |   | Corpus terrain, augmentation par du bruit, |
| 2 | Bruit et parole spontanée | Élevé | Élevée appui sur le bouton pendant qu'on parle, |
|   |   |   | micro proche |
|   | Accents et variétés (goun, |   | Moyenne à |
| 3 | mahi…) | Élevé | Échantillonnage stratifié, tests par variété élevée |
| 4 | Mélange fon‑français | Élevé | Élevée Lexique bilingue, données mixtes |
|   | Possession d'un | Élevé pour | Mode partagé, canal par appel téléphonique, |
| 5 |   |   | Certaine partenariat avec des groupements de |
|   | smartphone (39 %) | l'adoption | commerçantes |
|   | Connectivité, électricité, |   | Fonctionnement hors ligne, modèle quantifié, |
| 6 | coût de la data | Moyen à élevé | Élevée synchronisation différée |
|   | Licences des modèles et | Critique (si | Certaine pour |
| 7 | des données | commercial) | Encodeurs Apache ou MIT, accords écrits MMS |



|   |   | Probabilité d'un Mesure d'atténuation |
| --- | --- | --- |
| # | Variable | Impact |
|   |   | problème |
|   | Confiance et | Consentement, chiffrement, conformité APDP, |
| 8 | confidentialité (crédits | Élevé Moyenne transparence |
|   | clients) |   |
|   | Taille du corpus métier | Collecte rémunérée, partenariat avec Élevé Moyenne |
| 9 |   | JaimeMaLangue ou une université |
|   | Variété des produits | Catalogue fermé et personnalisable, ajout de Moyen Moyenne |
| 10 | (nombre de références) | produit par la voix avec validation |
|   | Temps et compétences | Élevé Moyenne Périmètre limité, architecture A d'abord |
| 11 | (projet solo) |   |
|   | Arrivée d'un concurrent | Se positionner sur le SMT et l'inclusion Moyen Moyenne |
| 12 | (IIDiA, Intron) | financière, ouverture à des partenariats |


Analyse de sensibilité. Le taux d'adoption dépend surtout de la proportion de transactions enregistrées sans correction. Les retours d'expérience des applications comparables suggèrent qu'en dessous d'environ 80 % de réussite après confirmation, l'usager revient au cahier (hypothèse à valider). Avec une ASR à 40 % de WER sur le terrain, seule une approche par mots- clés, appuyée par une confirmation et un dialogue de secours, permet d'atteindre ce seuil.


## 7. Faisabilité organisationnelle et économique (ordres de grandeur)


| Poste | Besoin | Commentaire |
| --- | --- | --- |
| Calcul | GPU type T4 ou A100 dans le cloud (Colab, | L'affinage d'un modèle de 300M prend environ 2 h sur |
| Kaggle) |   | une H100 (arXiv 2606.22274) ; c'est accessible |
| Collecte de | 30 à 50 locuteurs rémunérés, consentement écrit | Poste le plus coûteux en temps |
| données | et oral, 2 à 4 semaines |   |
| Annotation | Étiquetage intention, produit, quantité, | Les annotateurs n'ont pas besoin d'écrire le fon |
|   | montant, plus validation par un locuteur natif | (étiquettes en français) |
| Linguistique | Un linguiste du fon pour la numération et les | Indispensable pour les montants |
|   | phrases de réponse |   |
| Matériel de test | 3 à 5 téléphones Android d'entrée de gamme | Pour tester dans les vraies conditions |
| Juridique | Déclaration APDP pour le pilote | Faible coût, mais à anticiper |


## Planning indicatif (environ 20 semaines)


- 1. Semaines 1–3 : cadrage terrain. Entretiens avec 15 à 20 commerçantes, liste des produits, observation de la façon dont elles disent les montants.


- 2. Semaines 3–6 : collecte et annotation du corpus métier.


- 3. Semaines 6–10 : ASR (MMS‑300M‑fongbe ou XLS‑R) affiné sur FFSTC‑2, ALFFA et le corpus métier ; module de compréhension et module numérique.



- 4. Semaines 10–13 : application (enregistrement, confirmation, tableau, PDF au format SMT), phrases audio.


- 5. Semaines 13–17 : test terrain avec 10 à 20 utilisateurs, mesures et itérations.


- 6. Semaines 17–20 : consolidation, rédaction, préparation de la démonstration.


## 8. Critères de réussite (go / no-go)


| Indicateur | Seuil prototype (calme) | Seuil pilote (marché) |
| --- | --- | --- |
| Exactitude de l'intention (vente / achat / crédit) | ≥ 95 % | ≥ 90 % |
| Exactitude du produit | ≥ 90 % | ≥ 80 % |
| Exactitude du montant après confirmation | ≥ 98 % | ≥ 95 % |
| Transaction entièrement correcte du premier coup | ≥ 75 % | ≥ 50 % (à comparer aux 47 % de SautiLedger) |
| Transaction correcte après dialogue | ≥ 95 % | ≥ 85 % |
| Temps de traitement d'une transaction | < 3 s < 5 s |   |
| Satisfaction (questionnaire oral) | — | ≥ 70 % favorables |


Il faut toujours mesurer la transaction complète et pas seulement le WER : un WER de 30 % peut suffire si les mots-clés et les nombres sont reconnus.


## 9. Recommandations


- 1. Restreindre le périmètre : 3 intentions, 20 à 30 produits personnalisables, montants jusqu'à 1 000 000 FCFA, et un seul marché pilote.


- 2. Traiter les nombres comme un module à part, validé par un linguiste et confirmé à chaque transaction.


- 3. Concevoir pour les non-lecteurs : icônes, couleurs, réponses audio, aucun texte obligatoire ; le français ne sert qu'au PDF et aux tiers.


- 4. Fonctionner hors ligne d'abord, avec un modèle quantifié de 300M au maximum.


- 5. Clarifier les licences dès le début : MMS pour le mémoire, XLS‑R ou w2v‑BERT et des données sous licence claire pour la suite.


- 6. Collecter de la parole réelle de marché : c'est la contribution la plus durable du projet.


- 7. Positionner l'export PDF sur le journal de caisse SMT, pour faire de l'outil un levier d'accès au crédit.


- 8. Contacter l'écosystème : les auteurs de FFSTC‑2 (licence et poids des modèles), ASIN/IIDiA (JaimeMaLangue) et des institutions de microfinance (pilote, financement).


- 9. En soutenance, présenter les chiffres honnêtes : 22 % de WER (et non 17 %), corpus de parole lue, et les 47 % de transactions exactes de SautiLedger comme repère de la difficulté réelle.



## 10. Conclusion


Techniquement, le projet est faisable. Les briques (ASR fon, corpus FFSTC‑2, outils de compréhension, synthèse vocale, outils mobiles) existent, et la littérature récente valide l'idée de partir de la voix plutôt que du fon écrit.


Sa réussite ne dépend pourtant pas de l'IA « en général ». Elle dépend de quatre variables concrètes :


- l'exactitude des montants dans une numération non décimale ;


- la robustesse au bruit et à la parole spontanée des marchés ;


- l'accès réel des commerçantes à un smartphone, à l'énergie et à la data ;


- la licence des modèles si l'on vise un usage commercial.


Un prototype bien cadré est très atteignable. Un pilote terrain l'est aussi, au prix d'un corpus métier et d'une conception centrée sur la confirmation. La commercialisation demande de reconstruire la chaîne sur des briques à licence permissive.

---

**[USER]**

Pour le hors-ligne, on veut faire quoi ? Ce n'est pas commercial. C'est juste pour que ce soit un bon truc pour ma soutenance de licence. Et FFSTC2 n'est vraiment pas utilisable hors-ligne ? Moi je pensais que la version pour commercialiser c'est genre tout le truc est avec l'appareil sur lequel , ça va marcher . Donc ?

---

**[USER]**

Pour FFSTC2 là, je parlais du mod-le que ça a utilisé pour avoir ses performances. Et quand je parle d'appareil, c'ets qu'on vend l'appareil + le modèle + l'interface ensemble.  Quelle en est la pertinence ?

---

**[USER]**

Euh donc au final je fais de l'edge ai ou juste l'interface avec le modèle ? Ou comment je présente ça ? Dis moi.

---

**[USER]**

Oui mais je n'ai pas envie de faire de l'Edge AI ou ce sera sur un téléphone ? Et c'ets une licence en IA et applications ?

---

**[USER]**

Je vais utiliser hors-ligne là.

---

**[USER]**

I l y a le modèle cascade que les gars qui ont travaillé sur FFSTC2 ont utilisé.

---

**[USER]**

Au final, on a fait quels modifs ?




healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5