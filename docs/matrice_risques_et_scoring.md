# Matrice des Risques, Hiérarchie Normative et Scoring

## 1. Grille canonique à 4 facettes juridiques

Tout audit projet est structuré autour de 4 facettes obligatoires afin de garantir une couverture homogène et reproductible :

| Clé canonique | Domaine couvert | Exemples de points contrôlés |
| :--- | :--- | :--- |
| `donnees_manipulees` | Données manipulées | Données sensibles (santé, biométrie, mineurs), licéité, minimisation, consentement |
| `flux_et_architecture` | Flux, hébergement et architecture | Localisation des serveurs, transferts hors CEDEAO / États tiers, cloud, API |
| `securite_et_droits` | Sécurité, conservation et droits | Chiffrement, RBAC, journalisation, durée de conservation, DPO, formalités APDP/CDP |
| `relations_contractuelles_et_fintech` | Contrats, sous-traitants et Fintech | Clauses de responsabilité, DPA sous-traitants, agréments BCEAO, LCB/FT, KYC |

Le moteur impose une consolidation thématique (au maximum 1 à 2 constats consolidés par facette) et déduplique automatiquement les constats partageant exactement le même couple `(facet, matched_articles)`.

---

## 2. Hiérarchie des normes et validité temporelle

1. **Validité temporelle** : tout texte dont `status = 'abrogated'` ou dont la `publication_date` est future est exclu de la recherche RAG active. Si un texte révisé ou obsolète est référencé, `obsolescence_flag` est activé.
2. **Primauté hiérarchique** :
   - Rang 1 : Normes communautaires contraignantes (`OHADA`, `UEMOA`, `CEDEAO`, `OAPI`, `UA`)
   - Rang 2 : Lois nationales et Codes
   - Rang 3 : Décrets et Arrêtés d'application
   - Rang 4 : Directives sectorielles et Recommandations
3. **Détection des conflits** : en présence d'un concours entre une norme supranationale et un texte national, ou entre deux juridictions nationales sur un flux transfrontalier, `conflict_flag` est activé et la règle de primauté est précisée dans `conflict_details`.

---

## 3. Formule de scoring stabilisée

Le score global de risque (`0` = aucun risque détecté, `100` = exposition maximale) est calculé de manière déterministe dans `compute_initial_severity_and_score` à partir de la `ScoringRule` applicable (pays puis domaine, sinon règle globale) :

### Étape 1 — Poids de base par sévérité
- `critique` : `weight_critique × 25`
- `eleve` : `weight_eleve × 20`
- `modere` : `weight_modere × 12`
- `a_surveiller` : `weight_a_surveiller × 5`
- `conforme` : `weight_conforme × 0`

### Étape 2 — Rendements décroissants par facette juridique
Les constats non conformes sont regroupés par facette (`donnees_manipulees`, `flux_et_architecture`, `securite_et_droits`, `relations_contractuelles_et_fintech`, ou `general`), triés par poids décroissant, puis multipliés par `0,5^i` (`100 %`, `50 %`, `25 %`, `12,5 %`…). Ainsi, scinder un constat en deux dans le même domaine ne provoque pas d'inflation artificielle du score.

### Étape 3 — Malus de sanctions légales dédupliqué
Pour chaque **article de loi unique** cité dans un constat non conforme et portant `has_sanction = true` :
- `+8 pts` si la sanction est de nature pénale / privative de liberté (`sanction_nature` ou `sanction_details` mentionnant `penale`, `pénale`, `prison`, `emprisonnement`) ;
- `+4 pts` pour une sanction administrative ou pécuniaire.

Un même article cité dans plusieurs constats n'est compté **qu'une seule fois**. Le cumul total du malus est plafonné à `+25 pts`.

### Étape 4 — Plancher de précaution et compression graduée
- Si tous les constats sont `conforme`, le score est `0/100`.
- Si `raw_score > 70`, une compression exponentielle douce est appliquée :
  $$\text{score}_{\text{compressé}} = 70 + 30 \cdot \left(1 - e^{-\frac{\text{raw\_score} - 70}{45}}\right)$$
  afin d'éviter la saturation prématurée à `100`.
- **Principe de précaution** : si au moins un constat `critique` non mitigé subsiste, le score final est relevé au minimum à `50/100`.

---

## 4. Qualification juridique et piste d'audit

Chaque constat (`RiskFinding`) dispose :
- d'une **nature juridique** (`legal_nature`) :
  - `non_conformite_imperative` : manquement à une obligation légale ou réglementaire impérative ;
  - `risque_contractuel` : lacune de clause ou exposition de responsabilité entre parties ;
  - `bonne_pratique` : recommandation préventive ou point conforme.
- d'un **statut de validation humaine** (`review_status`) : `pending`, `validated`, `mitigated_by_evidence`, `dismissed`, accompagné de `reviewed_by`, `reviewed_at` et `review_note`.

Lors de la génération d'une nouvelle version du rapport, les constats déjà validés ou classés par un juriste sont transmis au moteur et automatiquement préservés sur les constats correspondants en l'absence d'élément contradictoire.
