# ANANKÉ v3.3.4 — distribution complète avec équations dynamiques trois-corps

## Contenu livré

Cette archive contient l’intégralité de la distribution ANANKÉ :

- `/html/Ananke.html` ;
- `/html/AnankeAI/Ananke_spin.php` ;
- le noyau Python `ananke_core/` ;
- l’interface et ses ressources ;
- les migrations et contrôles d’accès ;
- le corpus initial ;
- l’état SQLite initial déjà entraîné ;
- le module expérimental `ananke_core/three_body.py` ;
- les scripts de simulation et de validation ;
- les tests et résultats du retest à équations dynamiques.

## Portée exacte de « déjà entraînée »

L’état `state/ananke.sqlite3` est l’état relationnel initial d’ANANKÉ, entraîné sur
`corpus/bootstrap_fr.txt` pour l’objectif `general`.

État vérifié lors de l’emballage :

- version du référentiel : 1 ;
- lignes d’apprentissage : 1 ;
- objets : 28 ;
- coordonnées : 420 ;
- règles relationnelles : 929 ;
- observations de règles : 1 091 ;
- intégrité SQLite : `ok`.

Le module trois-corps n’est pas un réseau statistique préentraîné. Il constitue une
extension physique déterministe qui régénère l’équation relationnelle à chaque état
et qui a été soumise aux simulations et tests inclus dans `validation/`.

Cette distinction est volontaire : les résultats physiques ne sont pas présentés
comme appris lorsqu’ils proviennent encore de la loi newtonienne explicitement
implantée.

## Régime physique actuellement couvert

- trois corps colinéaires ;
- masses positives ;
- arithmétique rationnelle exacte ;
- ordre des corps stable ;
- absence de collision ;
- propagation et rétrodiction courtes par équations relationnelles dynamiques.

## Installation

Copier `html/Ananke.html` et le dossier `html/AnankeAI/` dans le dossier HTML cible.
Le fichier `AnankeAI/README.md` décrit le branchement PHP → Python et le contrôle
`users.ananke_access`.

## Validation locale

```bash
cd html/AnankeAI
export PYTHONPATH="$PWD"
python3 -m unittest discover -s tests -v
python3 scripts/simulate_three_body_dynamic_equations.py \
  --exact-trials 500 \
  --continuous-trials 30 \
  --future-steps 4
```
