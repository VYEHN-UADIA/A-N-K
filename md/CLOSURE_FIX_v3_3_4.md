# ANANKÉ v3.3.4 — corrections de la coordonnée de fermeture (review v3.3.3)

Quatre corrections, dont un vrai bug de cohérence. Suite : 40/40.

## 1. Terminologie (ε=0 ≠ vérité absolue)
`ClosureCoordinate` = RÉSIDU EXACT DE CONTRAINTE. ε=0 signifie « cette contrainte
déterminée ferme exactement avec les données fournies » (cohérence algébrique
locale), PAS une vérité sémantique/empirique. « La montagne est belle » n'a pas
deux membres rationnels. Le mot « vérité réifiée » est abandonné.

## 2. Bug corrigé — cell_closure() ignorait ρ
Avant : `cell_closure` ne vérifiait que ε_Δ. Une cellule à Δ correct mais ρ
falsifié (ex. 65/27) était déclarée cohérente à tort (`is_coherent()`=False mais
fermeture=vraie). Aucun test ne falsifiait ρ seul → passé inaperçu.
Après : fermeture VECTORIELLE Γ(M) = (ε_Δ, ε_ρ, ε_Δρ), cohérente SSI (0,0,0).
    ε_Δ  = (x^n + Δ)   − (x+h)^n
    ε_ρ  = (x^n · ρ)   − (x+h)^n
    ε_Δρ = (1 + Δ/x^n) − ρ
Un résidu non nul LOCALISE la corruption (quel chemin, de combien).
Exemple ρ=65/27 : Γ = (0, 1, −1/27). `cell_holds()` = False.
Test ajouté : `test_cell_closure_detects_ratio_only_falsification`.

## 3. `truth` dérivé, jamais stocké
`ClosureCoordinate` ne porte plus qu'`epsilon` (+ `label`). `holds`/`truth` sont
des PROPRIÉTÉS dérivées. L'état impossible (ε=0, faux) n'est plus représentable.

## 4. Composition vectorielle, pas somme aveugle
`combine_closures` (somme Σ|ε_i|) supprimé : additionner un résidu de longueur,
de volume et de rapport n'a aucun sens dimensionnel. Remplacé par :
- `combine_holds([...])` — ET logique (cohérent ⇔ tout ferme) ;
- `scalar_defect([...])` — métrique scalaire Σ|ε_i| OPTIONNELLE, valide seulement
  sur des résidus homogènes (après typage dimensionnel explicite).

## Reste à décider ensemble (persistance = organe A)
La table `ananke_closures` (object_id, constraint_kind, dimension_id, degree,
epsilon_num/den, label) proposée par la review est la bonne cible, mais c'est la
PERSISTANCE — séparée du multiplicatif (ε=0/négatif incompatible avec
positive_fraction). Décision de schéma à trancher avant de coder le SQL.
