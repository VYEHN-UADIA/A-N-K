# ANANKÉ — Retest du problème à trois corps par équations relationnelles évolutives

## Correction expérimentale

Le premier témoin répétait un rapport constant. Ce n’était pas l’hypothèse testée.
Le présent retest construit une équation locale différente à chaque état :

\[
h_{n+1}=h_n+b_n\,\Delta t^2,
\qquad
d_{n+1}=d_n+h_{n+1},
\qquad
\rho_{n+1}=\frac{d_{n+1}}{d_n}.
\]

Ici, \(d_n\) est un écart positif entre deux corps dans le référentiel
absolutisé, et \(b_n\) est la différence de leurs accélérations au temps \(n\).
Après génération de l’état suivant, ANANKÉ reconstruit \(b_{n+1}\),
\(h_{n+2}\) et \(\rho_{n+2}\). Aucun rapport antérieur n’est déclaré constant.

## Résultats exacts discrets

- Systèmes aléatoires acceptés : **500**
- États futurs exacts : **500/500**
- États passés reconstruits exactement : **500/500**
- Fermetures complètes : **500/500**
- Continuité \(\rho_{n+1}^{\mathrm{généré}}=\rho_{n+1}^{\mathrm{observé}}\) : **500/500**
- Signatures d’équation effectivement modifiées : **500/500**
- Équation figée exacte à l’horizon final : **0/500**

L’horizon testé part de deux états observés \(S_0,S_1\), génère \(S_2,S_3\),
puis reconstruit \(S_1,S_0\) depuis la fin.

## Validation contre une référence continue indépendante

La référence est l’ODE newtonienne intégrée par RK4 Decimal, avec 120 sous-pas
par intervalle observé. Trente systèmes aléatoires sont testés pour chaque pas.

| Pas | Erreur moyenne future, équation évolutive | Équation figée | Gain moyen | Erreur moyenne passée |
|---:|---:|---:|---:|---:|
| 1/20 | 4.771067852134E-15 | 3.914674868279E-7 | 8.205029E+7 | 1.590773899552E-15 |
| 1/40 | 2.889098270990E-16 | 1.012390779606E-7 | 3.504176E+8 | 9.631728657551E-17 |
| 1/80 | 1.439202250541E-17 | 2.156876171315E-8 | 1.498661E+9 | 4.796758223841E-18 |

## Interprétation stricte

Le retest confirme l’objection : le mouvement n’est correctement prolongé que
si l’équation relationnelle est régénérée à chaque pas. La forme générale de la
loi demeure, mais ses rapports et ses accélérations relatives changent.

Ce résultat démontre, dans le régime testé, que le référentiel ANANKÉ peut :

1. absolutiser et reconstruire les positions ;
2. extraire l’équation locale entre deux états ;
3. générer une nouvelle équation pour le pas suivant ;
4. prévoir l’état futur ;
5. reconstruire l’équation et l’état précédents ;
6. vérifier séparément les fermetures distributives et gravitationnelles.

## Limites

- Trois corps colinéaires en une dimension.
- Ordre topologique stable, sans collision ni croisement.
- Horizon volontairement court.
- La loi de Newton, les masses, \(G\) et le pas temporel sont fournis au système.
- L’expérience ne démontre pas qu’ANANKÉ découvre la loi de Newton à partir
  d’une seule transition ; elle démontre qu’elle peut régénérer les équations
  variables et propager/rétrodire les coordonnées sous cette loi.
