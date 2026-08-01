# ANANKÉ v3 — installation directe PHP → Python

## Distribution

```text
/html/Ananke.html
/html/AnankeAI/
  Ananke_spin.php
  ananke_core/
  assets/
  corpus/
  private/
  state/
```

ANANKÉ ne nécessite aucun portail, service HTTP local ou port dédié. Le message `Failed to connect to 127.0.0.1 port 7138` provenait de l'ancienne architecture proxy. Cette dépendance a été supprimée.

## Prérequis

- PHP 8.2 ou 8.3 avec `proc_open` autorisé ;
- Python 3.10+ détecté automatiquement (`/usr/bin`, `/usr/local/bin`, `/bin`, distributions Plesk), avec `ANANKE_PYTHON_BIN` prioritaire si défini ;
- extension Python SQLite standard ;
- `oracle_connect.php` dans le dossier `/html`, exposant `$conn` en `mysqli` ;
- colonne `users.ananke_access` valant `granted` ou `denied`.

## Première initialisation

```bash
cd /var/www/vhosts/uadia.fr/cercle.uadia.fr/main/src/html/AnankeAI
export PYTHONPATH="$PWD"
python3 -m ananke_core --state state/ananke.sqlite3 train corpus/bootstrap_fr.txt --objective general
```

La distribution fournie contient déjà un état initial entraîné afin de permettre la première conversation.

## Inférence locale

```bash
printf '%s' '{"action":"infer","prompt":"Je suis ","objective":"general","max_characters":120}' \
  | PYTHONPATH=. python3 Ananke_runtime.py --state state/ananke.sqlite3
```

## Ajout d'une loi

```bash
python3 -m ananke_core --state state/ananke.sqlite3 relation \
  "je" "suis" "grammaire/personne/1" "2" --logic grammaire
```

La dimension est enregistrée avec `kind='relation'`, ce qui corrige le défaut de la première version où elle était étiquetée `manual` et n'était pas activée correctement.

## Cycle d'apprentissage depuis l'interface

1. dépôt d'un fichier de 50 Mio maximum ;
2. analyse sans modification ;
3. KPI, contradictions et dimensions proposées ;
4. validation explicite ;
5. réconciliation transactionnelle complète de l'objectif ;
6. création d'une nouvelle version.

La version actuelle annonce honnêtement une réconciliation complète de l'objectif. Elle ne prétend pas encore réaliser une mise à jour incrémentale.

## Exécution PHP

Le client appelle seulement :

```text
./AnankeAI/Ananke_spin.php
```

Le PHP lance un script Python autonome, selon le même contrat que les workers Python déjà utilisés dans l’écosystème Cercle :

```text
python3 /chemin/AnankeAI/Ananke_runtime.py --state /chemin/AnankeAI/state/ananke.sqlite3
```

`Ananke_runtime.py` possède son shebang, initialise le chemin local du paquet `ananke_core`, lit une requête JSON sur `stdin` et écrit une seule réponse JSON sur `stdout`. Aucun import par `python -m`, aucun port local et aucun service résident ne sont requis.

L’interpréteur peut être remplacé par `ANANKE_PYTHON_BIN`; sa valeur par défaut est simplement `python3`, conformément au mode d’exécution Python déjà fonctionnel sur le serveur.

## Sécurité

- session Cercle vérifiée par `oracle_connect.php` ;
- contrôle `users.ananke_access='granted'` ;
- requête préparée `mysqli` ;
- CSRF obligatoire ;
- inférence SQLite en lecture seule ;
- apprentissage transactionnel ;
- aucun secret MySQL dupliqué dans ANANKÉ.

## Limite scientifique actuelle

Le mécanisme central est désormais relationnel : les lois stockent des facteurs suivants et non des caractères suivants. Un petit corpus peut néanmoins encore être reproduit textuellement lorsque sa trajectoire relationnelle conduit exactement aux mêmes positions. La preuve de généralisation devra être mesurée sur des relations analogues absentes des lignes d'entraînement, face à une baseline n-gramme séparée.


## Runtime autonome — v3.2

Le correctif définit désormais un fichier exécutable public au moteur local :

```text
AnankeAI/Ananke_runtime.py
```

Le contrôleur PHP l’appelle directement avec `python3`. Cette forme évite les restrictions et ambiguïtés rencontrées avec l’exécution d’un paquet par `-m`, tout en conservant le protocole JSON `stdin/stdout` et les journaux locaux dans `state/`.
