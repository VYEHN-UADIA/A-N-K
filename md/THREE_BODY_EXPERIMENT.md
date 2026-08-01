# ANANKÉ — Expérience relationnelle du problème à trois corps

## Question testée

À partir de deux états consécutifs seulement, `S_n` et `S_{n+1}`, ANANKÉ peut-elle :

1. générer `S_{n+2}` ;
2. reconstruire `S_{n-1}` ;
3. maintenir exactement les rapports de puissance du noyau gravitationnel ;
4. distinguer une simple prolongation de ratio d'une évolution physiquement fermée ?

## Régime expérimental

La première preuve est volontairement stricte et bornée :

- trois corps colinéaires ;
- masses, positions et vitesses initiales aléatoires ;
- gravitation newtonienne ;
- arithmétique `Fraction` exacte ;
- aucun flottant, logarithme, exponentielle ou racine ;
- absence de collision et ordre topologique conservé sur la courte séquence.

Le mouvement est régi par la récurrence symétrique de Störmer–Verlet :

```text
x_(k+1) = 2 x_k - x_(k-1) + a(x_k) dt²
```

Elle permet aussi la rétrodiction :

```text
x_(k-1) = 2 x_k - x_(k+1) + a(x_k) dt²
```

Les deux états observés suffisent donc à condition que les masses, `G`, `dt` et la loi gravitationnelle soient connus.

## Absolutisation relationnelle

Un état signé est transformé en :

```text
(order, centre_de_masse, écart_01, écart_12)
```

Les écarts sont strictement positifs et appartiennent au référentiel multiplicatif. Le centre de masse constitue la jauge qui permet de reconstruire exactement les trois positions signées.

Pour chaque paire de corps, ANANKÉ construit deux cellules distributives :

```text
rho_s = (d_(n+1) / d_n)²
rho_g = ((1/d_(n+1)) / (1/d_n))³
```

La loi de puissance gravitationnelle ferme exactement par :

```text
rho_g² × rho_s³ = 1
```

Cette relation ne contient aucune racine ni puissance fractionnaire.

## Résultats internes exacts

Benchmark multi-graines : 500 systèmes aléatoires.

| Contrôle | Résultat |
|---|---:|
| Génération `S_(n+2)` avec fermeture physique | 500 / 500 exactes |
| Reconstruction `S_(n-1)` avec fermeture physique | 500 / 500 exactes |
| Fermeture distributive des rapports gravitationnels | 500 / 500 exactes |
| Deux pas générés puis retour exact | 500 / 500 |
| Prolongation du seul ratio vers le futur | 0 / 500 exactes |
| Inversion du seul ratio vers le passé | 0 / 500 exactes |

Ces égalités exactes valident la cohérence et la réversibilité de la loi discrète implémentée. Elles ne constituent pas, à elles seules, une validation contre l'équation différentielle continue.

## Validation contre une référence continue indépendante

Référence : intégrateur RK4 en `Decimal`, avec 160 sous-pas par intervalle observé. Quarante systèmes aléatoires ont été testés pour chaque pas temporel.

| `dt` | Erreur moyenne future, ANANKÉ physique | Erreur moyenne passée, ANANKÉ physique | Erreur moyenne future, ratio seul |
|---:|---:|---:|---:|
| 1/10 | 3,67 × 10⁻¹¹ | 3,67 × 10⁻¹¹ | 3,03 × 10⁻⁵ |
| 1/20 | 2,72 × 10⁻¹² | 2,72 × 10⁻¹² | 8,62 × 10⁻⁶ |
| 1/40 | 2,32 × 10⁻¹³ | 2,32 × 10⁻¹³ | 1,97 × 10⁻⁶ |

La fermeture physique est entre environ `8,3 × 10^5` et `8,5 × 10^6` fois plus précise que la répétition brute du rapport selon le pas testé.

## Conclusion scientifique

Le résultat est positif, mais précisément délimité :

- **oui**, ANANKÉ peut représenter deux états sous forme relationnelle, reconstruire leurs coordonnées, générer un futur court et retrouver un passé court ;
- **oui**, les rapports de puissances gravitationnelles peuvent être maintenus exactement sans matérialiser de racine irrationnelle ;
- **non**, le seul rapport observé `n → n+1` ne contient pas la dynamique complète ; il doit être fermé par la loi gravitationnelle et ses paramètres ;
- **non encore démontré**, le cas spatial générique 2D/3D, les changements d'ordre, les collisions, les nombres algébriques généraux et les horizons chaotiques longs.

Le prototype démontre donc un **solveur relationnel réversible à loi physique déclarée**, et non une découverte autonome de la loi à partir d'une transition unique.

## Fichiers ajoutés

- `ananke_core/three_body.py` — représentation, fermeture, génération et rétrodiction ;
- `tests/test_three_body_relational.py` — six tests dédiés ;
- `scripts/simulate_three_body.py` — benchmark rationnel exact ;
- `scripts/validate_three_body_continuous.py` — comparaison à une référence continue RK4.

## Exécution

```bash
cd html/AnankeAI
python3 -m unittest discover -s tests -v
python3 scripts/simulate_three_body.py --trials 200
python3 scripts/validate_three_body_continuous.py --trials 40 --substeps 160
```
