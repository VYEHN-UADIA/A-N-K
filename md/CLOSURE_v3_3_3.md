# ANANKÉ v3.3.3 — coordonnée de fermeture ε (vérité réifiée)

La vérité devient une DONNÉE de première classe, pas un simple `stop`.

## Principe
ε = membre_gauche − membre_droite d'une contrainte, EXACT (rationnel).
- ε = 0  ⇔  vrai (cohérent)          → truth = 1
- ε ≠ 0  ⇔  faux, et |ε| mesure DE COMBIEN (1=2 → ε=−1, pas seulement « non »)

ε est une coordonnée ADDITIVE (un écart), HORS du référentiel multiplicatif ℚ⁺.
C'est pourquoi 0 est AUTORISÉ ici (l'état « vrai »), alors que 0 reste interdit
comme coordonnée MULTIPLICATIVE. Deux régimes, deux espaces, aucune contradiction.

## API (dans ananke_core/distributive.py)
- `ClosureCoordinate(epsilon, truth, label)` — .holds ⇔ truth==1. Transportable, composable.
- `closure_epsilon(left, right)` — vérité réifiée d'une égalité.
- `closure_of_step(x, h, n, delta_claim)` — vérité de « (x+h)^n − x^n == delta_claim ».
- `cell_closure(cell)` — fermeture d'une MemoryCell : ε = (x^n+Δ) − (x+h)^n.
- `combine_closures([...])` — composition : ET logique ; défaut total Σ|ε_i|.
- `admits_step(x, h, n, delta_claim)` — RÉGIME SÛR : un pas n'est admis que si ε=0
  (contrainte de génération : le système ne peut pas produire un pas faux).

## Ce qui n'est PAS ici (piste séparée, assumée)
Le régime où ce paramètre « change la nature d'une discussion » relève de la
pragmatique, pas de la vérité mathématique fermée par contrainte. Gardé hors de
ce module tant qu'il n'est pas exact.

## Note d'intégration au store (à décider ensemble)
Persister ε dans la table `coordinates` heurterait `positive_fraction` (ε peut être
0/négatif). Il faut donc soit une table additive dédiée (`kind='closure'`), soit un
champ propre sur la cellule — décision de schéma à trancher avant persistance.
Les primitives ci-dessus sont exactes et testées indépendamment de ce choix.
