# ANANKÉ v3 — installation directe PHP → Python et HTML

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

Ajouter l'ensemble de la distribution AnankeAI, connectez si vous le souhaitez environnements php, mysql et environnements virtuels py (demander à ChatGpt-OpenAI/Claude-Anthropic/Kimi-KimiMoonshot de vous aider si besoin ;), télécharger l'ensemble de la distribution ANANKÉ AI, compressez-là et demander vos améliorations selon architecture aux AI ou agents), vérifier vos permissions et la disponibilité environnement python de votre environnement html, et ajouter la plateforme html dans votre directory html.

ANANKÉ ne nécessite aucun portail, service HTTP local ou port dédié mais est compatible par logique. Les messages types `Failed to connect to 127.0.0.1 port XXXX` proviendront d'architecture "proxy". Cette dépendance a été supprimée.

Le directory nommé assets contient un fichier déja intégré, cette fonctionnalité app.js devient modulaire ou obsolète selon plateforme de conversation html.

ANANKÉ AI n'as pas d'API / provider (2026)

ANANKÉ est un algorithme, mais sa faculté système basé sur un référentiel mathématique multiplicatif en comparaison de modules équationnels en fait de cet algorithme un "cerveau" de calcul dont la matière est faite de coordonnées mathématiques.


## Prérequis

- PHP 8.2 ou 8.3 avec `proc_open` autorisé ;
- Python 3.10+ détecté automatiquement (`/usr/bin`, `/usr/local/bin`, `/bin`, seulement distributions Plesk), avec `ANANKE_PYTHON_BIN` prioritaire si défini ;
- extension Python SQLite standard déja défini ;
- fichier de type `oracle_connect.php` avec credent (connexion base de donnée) dans le dossier `/html`, exposant `$conn` en `mysqli` ;
- colonne à ajouté (Mysql) `users.ananke_access` valant `granted` ou `denied`.


## Première initialisation

```bash
cd /votre distribution NGINX/html/AnankeAI
export PYTHONPATH="$PWD"
python3 -m ananke_core --state state/ananke.sqlite3 train corpus/bootstrap_fr.txt --objective general
```

La distribution fournie contient déjà un état initial entraîné afin de faciliter la première conversation (juvénile).

## Inférence locale (Si terminal)

```bash
printf '%s' '{"action":"infer","prompt":"Je suis ","objective":"general","max_characters":120}' \
  | PYTHONPATH=. python3 Ananke_runtime.py --state state/ananke.sqlite3
```

## Ajout d'une loi (Se référer au document explicatif apprentissage)

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

La version actuelle annonce une réconciliation entière de l'objectif : Elle ne prétend pas encore réaliser une mise à jour incrémentale vers une version AI entière. Les suites viendront.



## Exécution PHP

Le client appelle seulement :

```text
./AnankeAI/Ananke_spin.php
```

Cette séquence sert de vérification utilisateur et peux être supprimée (pas de validation, pas de session utilisateur php, pas de connexion par credent à une base de donnée possible)


Le PHP lance un script Python autonome, selon le même contrat que les workers Python déjà utilisés dans l’écosystème Cercle :

```text
python3 /chemin/AnankeAI/Ananke_runtime.py --state /chemin/AnankeAI/state/ananke.sqlite3
```

`Ananke_runtime.py` possède son shebang, initialise le chemin local du paquet `ananke_core`, lit une requête JSON sur `stdin` et écrit une seule réponse JSON sur `stdout`. Aucun import par `python -m`, aucun port local et aucun service résident ne sont requis.

L’interpréteur peut être remplacé par `ANANKE_PYTHON_BIN`; sa valeur par défaut est simplement `python3`, conformément au mode d’exécution Python déjà fonctionnel sur le serveur.

## Sécurité

- session Utilisateur vérifiée par `oracle_connect.php` ;
- contrôle Mysql `users.ananke_access='granted'` ;
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
