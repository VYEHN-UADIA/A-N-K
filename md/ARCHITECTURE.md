# ANANKÉ — Architecture générative relationnelle multiplicative

ANANKÉ est féminine. Son nom désigne la nécessité : ce qui ne peut pas être autrement. Elle ne sélectionne donc un caractère que lorsqu'une configuration relationnelle le rend nécessaire dans la version active du référentiel. Si plusieurs sorties restent également admissibles, elle retourne une abstention plutôt qu'un choix arbitraire.

## Nature

ANANKÉ n'est pas un Transformer. Elle est une génératrice relationnelle dont l'unité de calcul est le rapport multiplicatif entre deux positions positives.

Pour une dimension active `d` :

```
r(A → B | d) = C(B,d) / C(A,d)
```

L'orientation canonique est toujours `cible / source`.

## Équation centrale d'inférence

Pour une ligne de caractères `Γ = (a1, …, an)`, ANANKÉ calcule sa trajectoire de relations locales :

```
μ(k,d) = C(ak,d) / C(a(k-1),d)
```

L'apprentissage n'enregistre pas directement le prochain caractère. Il enregistre :

```
trajectoire_relationnelle → relation_suivante
```

À l'inférence :

```
C(candidat,d) = C(an,d) × relation_suivante(d)
```

Le caractère est ensuite résolu parmi les objets qui occupent exactement cette position. La table `relation_rules` ne contient aucune colonne `next_object_id`.

## Coordonnées

Les dimensions fondamentales ne proviennent plus d'un hash :

- `x` = fréquence observée + 1 ;
- `y` = diversité des contextes gauches + 1 ;
- `z` = diversité des contextes droits + 1.

Les dimensions logiques mesurées décrivent notamment la position dans le mot, les espaces, la ponctuation, la casse et les diversités contextuelles. Les dimensions de loi explicites sont résolues à partir de contraintes multiplicatives et contrôlées par cohérence des cycles.

L'identité technique d'un objet est son identifiant SQLite. Elle est séparée de sa position logique ; une collision de coordonnées n'efface donc jamais l'identité.

## Activation logique

Lorsqu'une logique possède des dimensions relationnelles explicites, celles-ci deviennent prioritaires pour reconnaître la trajectoire. À défaut, les dimensions mesurées du corpus sont utilisées.

## Cohérence

Pour tout cycle fermé :

```
Π r = 1
```

Une contradiction annule la transaction entière.

## Abstention

ANANKÉ retourne `⊥` dans quatre situations principales :

- caractère d'entrée inconnu ;
- aucune loi relationnelle applicable ;
- position cible non occupée ;
- plusieurs candidats non dominés possédant exactement les mêmes critères.

Le dernier cas est nommé `contingent_frontier` : un choix reste possible, donc aucune nécessité n'est démontrée.

## Exécution

Il n'existe aucun serveur HTTP interne, aucun port 7138 et aucun démon résident. `Ananke_spin.php` lance directement Python avec `proc_open`, transmet une requête JSON par l'entrée standard et lit la réponse JSON sur la sortie standard.

L'inférence ouvre SQLite physiquement en lecture seule (`mode=ro`). Seuls les cycles d'apprentissage explicites ouvrent le référentiel en écriture.
