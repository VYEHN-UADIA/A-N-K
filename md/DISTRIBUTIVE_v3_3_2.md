# ANANKÉ v3.3.2 — strate distributive + mémoire relationnelle

Base : consolidation v3.3.1. Ajout d'une **primitive quantitative exacte**,
OBLIGATOIRE (API de première classe) mais **accessible selon besoin logique** :
dormante par défaut, hors du chemin linguistique, réveillée uniquement lorsqu'un
objet ou une relation DÉCLARE un degré n. Le degré n'est jamais inféré.
Aucun log/exp, aucun flottant. Suite : 31/31.

## Ce que la strate fait (et ne fait pas)
Elle NE maintient PAS les ratios (la couche relationnelle le fait déjà).
Elle établit le pont exact **déplacement additif → rapport multiplicatif gradué** :
    ρ_n(x,h) = ((x+h)/x)^n      (rapport)      Δ_n(x,h) = (x+h)^n − x^n   (variation)
Le degré fait partie de la relation : 3→4 vaut ×4/3 (ligne), ×16/9 (aire),
×64/27 (volume).

## Module `ananke_core/distributive.py`
- `distributive_coordinate(x,h,n)` — mode COMPACT (une exponentiation par côté,
  pas de développement) ; x>0, n entier ≥1, (x+h)>0.
- `distributive_expansion(x,h,n)` — mode EXPLICATIF (termes de Pascal), matérialisé
  seulement pour expliquer / fermer terme à terme / comparer.
- Pascal : constantes pour n≤4, cache partagé au-delà (construit une fois, pas de
  reconstruction par appel).
- **Fermetures par contrainte**, chacune EXACTE ∧ UNIQUE sinon `None` (⊥ → abstention) :
  `close_ratio`, `close_delta` (toujours exactes) ; `close_coefficient` (κ masqué,
  None si Δ=0) ; `close_step` (h via racine n-ième rationnelle exacte, None sinon) ;
  `close_degree` (n sélectionné PARMI les degrés déclarés, unique ou None).

## Cellule mémoire (MemoryCell)
- `MemoryCell(identité, x, h, n, Δ, ρ, prev, next)` : mémorise une
  situation reconstructible, pas une valeur.
- `is_coherent()` : checksum relationnel — x^n+Δ = (x+h)^n = x^n·ρ et 1+Δ/x^n = ρ.
  Toute altération casse la fermeture (détection d'erreur intrinsèque).
- `recall_masked(...)` : rappel par contrainte (un champ masqué reconstruit), ⊥ sinon.
- `chain_state(x0, cellules, n)` : rejoue une trajectoire par les DEUX chemins
  (Π ρ_i additif vs Σ Δ_i) ; retourne x_m^n s'ils coïncident, None sinon.
- `associates(a,b)` : mémoire associative par loi (même degré, même ρ).

## Frontières (verrouillées par tests)
- DORMANTE : l'inférence linguistique ne crée jamais de dimension `kind='distributive'`
  (`test_dormant_outside_linguistic_path`).
- Degré = rang discret `int`, jamais un rationnel, jamais dans `resolve_coordinates`.
- Sous-détermination = `None` = abstention, jamais une approximation.
- Aucun appelant actuel : primitive posée en avance, activée le jour où un domaine
  introduit une grandeur graduée (échelle, aire, volume, sphère relationnelle).

## Limite honnête (note 8)
κ (ex. 4π/3) n'est reconstructible qu'avec une mesure d'ancrage (ΔV) : la
distributivité fournit la STRUCTURE (x^n), la mesure fournit le FACTEUR, la
fermeture reconstruit le masqué. Sans ancrage → sous-déterminé → ⊥.
