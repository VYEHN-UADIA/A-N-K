# ANANKÉ — Consolidation v3.3.1

Base : v3.3. Objectif : résoudre la déviance mathématique de deuxième ordre
restante, durcir la robustesse, et verrouiller les invariants par des tests.
Aucune régression : suite complète 18/18 (14 d'origine + 4 de consolidation).

## 1. Déviance mathématique de 2e ordre — homologie de puissance restreinte aux lois
Problème : en régime *mesuré* (aucune loi explicite), `trajectory_signature`
émettait un `power_hash` calculé sur les coordonnées MESURÉES (fréquence,
diversité). Or « même direction dans le réseau des exposants premiers » n'a de
sens que sur des lois multiplicatives DÉSIGNÉES ; sur des comptages, c'est un
accident arithmétique → appariements de puissance fallacieux + coût de
factorisation sur de grands entiers de comptage.

Correctif : `power_hash` calculé uniquement sur les dimensions `kind='relation'`
(nouvelle aide `store.relation_dimensions`). S'accorde exactement à la hiérarchie
`inference_dimensions` déjà présente :
- régime mesuré  → `power_hash = ""` → chemin de puissance inactif (appariement
  exact seul) ;
- régime relationnel → homologie active sur les lois, là où elle est fondée.

Fichiers : `ananke_core/{signature,store,inference,trainer}.py`.
Vérifié : sur le bootstrap, tous les `trajectory_power_hash` sont vides ;
l'induction analogique (`cd → y` sans « cdy ») reste verte.

## 2. Robustesse — factorisation mémoïsée
`power.factor_integer` : mémoïsation (`lru_cache`) via un tuple immuable, avec
copie fraîche à chaque appel (les appelants mutent le dict). `power.py`.

## 3. Tests de non-régression (`tests/test_consolidation.py`)
- couverture : état livré ⊇ caractères du corpus (invariant d'empaquetage) ;
- `power_hash` vide en régime mesuré ;
- bascule du gating dès qu'une loi existe ;
- sensibilité à l'ordre (`cf ≠ fc`) : la commutativité de ℚ⁺ ne fusionne pas les
  trajectoires ordonnées.

## 4. État réentraîné
`state/ananke.sqlite3` réentraîné sur `corpus/bootstrap_fr.txt`, cohérence
désormais garantie par le test de couverture.

## Correction d'une conclusion antérieure
L'abstention sur « La grammaire… » (`unknown_object: L`) n'est PAS une désynchro
état/corpus : le corpus bootstrap (28 caractères) ne contient pas le 'L'
majuscule. État et corpus sont cohérents ; l'abstention est le comportement
CORRECT. Il n'y a donc pas de bug d'empaquetage à ce sujet.

## Déjà sain en v3.3 (non modifié)
Bug relation `kind='relation'` (corrigé en v3.3), inférence lecture seule,
abstention sur front contingent, suppression de la redondance `anchor = ∏ μ`.

## Reste ouvert — leviers, pas bugs
- Richesse des coordonnées mesurées : séparer les caractères rares (aujourd'hui
  empilés sur la cellule (2,2,2)) pour réduire l'abstention forcée.
- Couche de probabilité optionnelle à partir des `support` (mode non
  déterministe, en gardant le déterministe par défaut).
- Réconciliation incrémentale (aujourd'hui complète par objectif, assumée).
