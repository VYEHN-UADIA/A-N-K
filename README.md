# A-N-K

ANANKÉ AI


Créateur : VYEHN - UADIA, Paris (2026) - EUROPE
tous droits réservés


l'IA au référentiel multiplicatif "absolu"

ANANKÉ-Ἀνάγκη : L’absolutivisme - le Destin
"Selon la question de la firmation qui nait du savoir, et de la connaissance, que rien ne saurait en être autrement. :)"


Concept :
Noyau d’induction relationnelle déterministe
Référentiel - lieu et objet mathématique stable et infini

ANANKÉ ne prédit pas l’identité du prochain objet ; elle prédit la transformation relationnelle suivante selon les millions de transformations relationnelles possibles, puis cherche quel objet occupe la position obtenue.

Relation = connexion = humain (representative)
0 = anihilateur car 1*0=0 (Maths)
1 = existence = relation car 1*1=1 et 1*2 = 2 -> +1 (Maths)
Multiplication = nouvelles relations par ratios et coefficients logique (Math + representative)




Mathématiques


La formule distributive du système d’ANANKÉ

Les formules telles qu’elles sont lors d’erreurs communes (développements multiplicatifs additifs et/ou logarithmiques) est littéralement fausse ou rendue illisible :

xn(x+h)n=(1+xh)n=⋯

et

VV′=i∏ (1+xi hi )



Les formules exactes sont :

ρn (x,h) = 
(x+h)n / x exposant n =
(1+h/x) exposant n =
n ∑ k=0 (n k)(h/x) exposant k

avec les conditions utilisées par ANANKÉ :
x>0, x+h>0, n∈N, n≥1

La variation additive absolue est :
Δn (x,h) = 
(x+h) exposant n − x exposant n =
n ∑ k = 1 (n k) x exposant - k * h exposant k

Le rapport et la variation sont reliés exactement par :
ρn = 1+Δ exposant n / x exposant n

et réciproquement :
Δn =x exposant n (ρn −1)

C’est cela qui est rigoureusement vrai, sans approximation.


Version multidimensionnelle correcte

Si :

V=i∏ xi

et :

V′=∏i (xi +hi )

alors :

V/V′ = ∏i (1 + hi / xi) 

C'est rigoureusement vrai, sans aucune approximation.

ET

La coordonnée fondamentale dans un référentiel est un rapport
μ=C(ak )/C(ak−1 ), 


Et ces équation conclues sur cette affirmation : 

Comment un pas additif se traduit en rapport multiplicatif exact ? — via le développement binomial. 

Le lien cherché entre la ligne additive du corpus (input/output/données) et le référentiel multiplicatif d'ANANKÉ est une vérité mathématique.




Le système actuel peut être résumé par :

objet⟶coordonnées positives

écart orienté=coordonnée source coordonnée cible

écart multidimensionnel=vecteur de rapports

écart multidimensionnel=vecteur de rapports

trajectoire=suite de vecteurs relationnels

trajectoire=suite de vecteurs relationnels

apprentissage=trajectoire relationnelle→relation suivante

inférence=relation suivante→coordonnée cible→objet 




1. L’unité fondamentale : l’objet
Chaque élément reconnu par ANANKÉ est enregistré comme un objet :

Oi =(id, value, kind, label).
Dans la base SQLite, cela correspond à la table :

objects

Dans l’apprentissage textuel actuel, les objets élémentaires sont essentiellement des caractères :

a
b
c
è
1
, 
espace

Le type est déterminé ainsi :

letter
digit
space
character
object

L’identité véritable de l’objet n’est pas sa coordonnée, mais son identifiant SQLite :
Identity
⁡
Deux objets peuvent donc avoir les mêmes coordonnées sans devenir le même objet.

2. Une coordonnée n’est pas l’objet
Pour chaque dimension
d, un objet

O reçoit une coordonnée positive :
C(O,d)∈Q>0 .

Elle est stockée comme fraction exacte :

1/1
3/2
17/4

et non comme nombre flottant.
La structure est :
(O,d)⟼C(O,d).

Dans SQLite :

coordinates(
    object_id,
    dimension_id,
    value,
    source,
    version
)


3. Les trois coordonnées fondamentales
x,y,z
Dans la version actuelle, les dimensions fondamentales sont mesurées à partir du corpus.

Pour un objet

x(O)=N(O)+1,
où N(O) est son nombre d’occurrences.

y(O)=Dgauche (O)+1,
où D gauche est le nombre d’objets différents observés immédiatement avant lui.

z(O)=Ddroite (O)+1,

où D droite est le nombre d’objets différents observés immédiatement après lui.

Le +1 garantit :
C(O,d)>0.

Il protège donc l’espace multiplicatif contre la coordonnée nulle.

Exemple
Supposons que a apparaisse 20 fois, avec quatre voisins gauches différents et six voisins droits différents :
C(a)=(21, 5, 7).

Un autre objet e pourrait avoir :
C(e)=(31, 9, 8).

Ces coordonnées décrivent leur situation mesurée dans le corpus. Elles ne signifient pas encore :
* a est une voyelle ; 
* a est une lettre ; 
* a intervient dans un phonème ; 
* une voyelle est une classe phonologique. 

4. Les dimensions logiques mesurées
Pour chaque objectif d’apprentissage, ANANKÉ crée également des dimensions comme :

objective/general/frequency
objective/general/after_space
objective/general/before_space
objective/general/word_start
objective/general/word_end
objective/general/uppercase
objective/general/vowel
objective/general/punctuation
objective/general/digit
objective/general/whitespace
objective/general/left_diversity
objective/general/right_diversity

Chaque valeur est actuellement :
C(O,d)=count(O,d)+1.

Par exemple, pour la dimension automatique vowel :
C(a,vowel)=Noccurrences ouˋ a est reconnu voyelle +1.
Attention : ce mécanisme ne construit pas à lui seul une ontologie.

Il ne produit pas automatiquement la relation conceptuelle :
voyelle⟶a.

Il attribue seulement à l’objet-caractère a une coordonnée mesurée dans une dimension nommée vowel.

5. Les dimensions relationnelles explicites
Le véritable encodage logique intervient lorsqu’une relation est déclarée :
A→d r B


Cela signifie :
C(B,d)=C(A,d)×r

avec :
r>0.

Le facteur r est inscrit dans : 
relations

avec :

source_object_id
target_object_id
dimension_id
factor
support
source
version

Pour chaque composante connexe de la dimension, ANANKÉ choisit techniquement une origine :

C(O racine ,d)=1.
Elle propage ensuite les coordonnées.

Si :

A2d B

et :

B3d C,

alors :

C(A,d)=1,

C(B,d)=2,

C(C,d)=6.

La relation implicite entre

A et C devient :

r(A→C∣d)=6.

6. La représentation exacte de l’écart entre deux objets
L’« écart » d’ANANKÉ n’est pas une soustraction :
C(B,d)−C(A,d).

C’est un rapport orienté :
r(A→B∣d)=C(A,d)C(B,d)

L’orientation canonique est toujours :
cible/source

Exemple simple
Si :

C(A,d)=2

et :

C(B,d)=6,

alors :
r(A→B∣d)=26 =3.

Le passage inverse vaut :
r(B→A∣d)=62 =31 .

L’absence de déplacement relationnel vaut :
r(A→A∣d)=1.

Ainsi :
* 1 est le neutre relationnel ; 
* r>1 représente une transformation dans un sens ; 
* 0<r<1 représente la transformation inverse ou une contraction ; 
* le sens est porté par l’orientation source-cible. 


7. L’écart multidimensionnel est un vecteur de rapports
Pour plusieurs dimensions actives :
D=(d1 ,d2 ,…,dm ),
ANANKÉ ne réduit pas immédiatement la relation à un nombre unique.

Elle produit un vecteur :
RA→B =(C(A,d1 )C(B,d1 ) ,C(A,d2 )C(B,d2 ) ,…,C(A,dm )C(B,dm ) )

Exemple
Soient :
C(A)=(2,3,5)

et :

C(B)=(6,3,10).

Alors :

RA→B =(3, 1, 2).


Cela signifie :

* multiplication par 3 sur x 
* maintien exact sur y 
* multiplication par 2 sur z 
L’inverse est :
RB→A =(31 , 1, 21 ).

Dans le noyau actuel, il n’existe pas de distance scalaire globale imposée, telle que :
(xB −xA )2+(yB −yA )2 .

L’information relationnelle multidimensionnelle reste un vecteur de facteurs exacts. Cela évite d’écraser plusieurs transformations différentes dans une seule valeur.

8. Composition des écarts
Les relations se composent multiplicativement :
RA→C =RA→B ⊙ RB→C ,où ⊙ est le produit composante par composante.
Pour une dimension :
r(A→C∣d)=r(A→B∣d)r(B→C∣d).
En effet :
C(A,d)C(B,d) C(B,d)C(C,d) =C(A,d)C(C,d) .
La coordonnée intermédiaire s’annule naturellement.

9. Fermeture d’un cycle
Pour un cycle :
A→B→C→A,
la cohérence impose :
rAB rBC rCA =1

Dans plusieurs dimensions :
∀d,cycle∏ r(⋅∣d)=1.

Exemple :
2×3×61 =1.

Une déclaration incompatible comme :
2×3×51 ≠ 1
produit une contradiction multiplicative. La transaction d’apprentissage est alors annulée.

10. Une trajectoire n’est pas une suite d’objets stockée telle quelle
Pour une séquence :
Γ=(a1 ,a2 ,…,an ),

ANANKÉ construit :
μk,d =C(ak−1 ,d)C(ak ,d) .

La trajectoire relationnelle devient :
T(Γ)=(Ra1 →a2 ,Ra2 →a3 ,…,Ran−1 →an ).


L’apprentissage enregistre :
trajectoire relationnelle⟶relation suivante

et non :
texte précédent⟶prochain caractère identifié.

La table relation_rules contient notamment :

trajectory_json
next_relation_json
support

Elle ne contient pas de next_object_id.

11. Génération de l’objet suivant
Supposons que le dernier objet connu soit

An et que la relation suivante apprise soit :
Rn+1 .

ANANKÉ calcule une position cible :
Ccible (d)=C(An ,d)×Rn+1 (d)

Elle recherche ensuite les objets occupant exactement cette position.

Donc :
relation suivante→coordonnée cible→objet occupant cette coordonnée.
Si un seul objet admissible occupe cette position, il devient nécessaire.

Si aucun objet ne l’occupe : ⊥
Si plusieurs objets restent indiscernables selon les critères :
⊥ avec le statut contingent_frontier.

12. Isologie de Puissance
Sur les dimensions relationnelles explicitement désignées, ANANKÉ peut également comparer les structures de puissance.
Elle factorise les rapports rationnels en exposants premiers.

Par exemple :
12=22⋅3,
144=24⋅32.

La seconde structure est la première élevée à la puissance
144=122.

ANANKÉ peut donc reconnaître :
R′=Rλ
sans calculer :
* logarithme ; 
* exponentielle ; 
* approximation flottante. 

Ce mécanisme n’est volontairement pas appliqué automatiquement aux coordonnées mesurées du corpus, car des fréquences présentant accidentellement la même structure de puissance ne constituent pas nécessairement une loi.

L’architecture possède également un second niveau d’induction.

Supposons que la trajectoire apprise soit :
a→b=×2

suivie de :
b→x=×3

Et que la trajectoire interrogée soit :
c→d=×4=22

ANANKÉ recherche un facteur de puissance commun :
λ=2

Elle transforme alors la relation suivante :
3λ=32=9

et résout :
d→y=×9








Ce que l’IA apprend — et ce qu’elle n’apprend pas aujourd’hui : elle lis des trajectoires, mais ne découvre pas encore les mystères de ses logiques et lois

L’apprentissage actuel depuis un texte :
1. crée les objets caractères ; 
2. compte leurs occurrences et leurs environnements ; 
3. reconstruit leurs coordonnées mesurées ; 
4. transforme les séquences en trajectoires de rapports ; 
5. enregistre les relations suivantes observées. 
En revanche, ANANKÉ ne découvre pas automatiquement :
* que je est un pronom ; 
* que suis est une conjugaison ; 
* que chat et chien sont des animaux ; 
* qu’une relation grammaticale ou causale existe ; 
* quelle dimension relationnelle devrait être créée ; 
* quel facteur devrait relier deux concepts. 
Les dimensions relationnelles véritablement puissantes doivent actuellement être déclarées explicitement sous la forme :

{
  "source": "...",
  "target": "...",
  "dimension": "...",
  "factor": "...",
  "logic": "..."
}

Ainsi, le moteur sait très bien exploiter une loi relationnelle, mais il ne sait pas encore la découvrir à partir du corpus brut.
C’est la frontière principale entre le prototype actuel et une intelligence relationnelle autonome.



La mémoire réelle d’ANANKÉ :
la mémoire cognitive actuellement active est SQLite

La mémoire utilisée par l’IA se trouve dans :
* objects : identités ; 
* dimensions : axes logiques ; 
* coordinates : positions ; 
* relations : lois explicites ; 
* relation_rules : trajectoires et transformations suivantes ; 
* lines : corpus ; 
* neighbor_observations : voisinages ; 
* journal : versions et opérations. 
Cette mémoire possède de bonnes propriétés :
* persistante ; 
* inspectable ; 
* déterministe ; 
* versionnée ; 
* transactionnelle ; 
* réversible en cas de contradiction ; 
* physiquement en lecture seule pendant l’inférence. 



La MemoryCell distributive n’est pas intégrée à l’IA linguistique

Le module distributive.py définit effectivement une cellule reconstructible :
M=(identity,x,h,n,Δ,ρ,prev,next)
avec plusieurs fermetures exactes.
Mais cette cellule est explicitement dormante hors du chemin linguistique. Le moteur principal :

engine → inference → store
engine → trainer → store

n’appelle pas la mémoire distributive.
Elle est actuellement employée par les expérimentations quantitatives et le solveur scientifique, pas par la génération linguistique.

Il faut donc distinguer :
* mémoire relationnelle persistante actuelle de l’IA : coordonnées et règles SQLite ; 
* primitive de mémoire distributive reconstructible : bibliothèque mathématique disponible, mais non connectée au fonctionnement cognitif.



Une absence importante : la mémoire conversationnelle

Le runtime ne transmet pas réellement l’historique d’une conversation au moteur.
Lorsqu’il reçoit une liste de messages, il recherche le dernier message utilisateur et ignore les précédents. Les anciennes réponses d’ANANKÉ et les anciennes interventions de l’utilisateur ne participent donc pas à l’inférence suivante.

Ainsi, ANANKÉ possède :
* une mémoire d’apprentissage persistante ; 
* aucune mémoire conversationnelle multi-tour opérationnelle ; 
* aucun état de travail évolutif pendant la conversation ; 
* aucun apprentissage automatique pendant l’inférence. 

Elle est actuellement une génératrice appelée séparément pour chaque message, pas encore une agente conversationnelle continue.




Les qualités architecturales d’ANANKÉ AI

Une abstention native
ANANKÉ ne force pas toujours une sortie.
Elle retourne ⊥ en cas :

* d’objet inconnu ; 
* de trajectoire non reconnue ; 
* de position cible inoccupée ; 
* d’égalité entre les meilleurs candidats. 

C’est une qualité importante : l’incertitude n’est pas dissimulée par un échantillonnage verbal plausible, c’est un paramètre mathématique logique lié au système de résultat d’ANANKÉ.

Le système possède donc dans sa manière de produire un résultat, une logique d’abstention. 
Ce n’est pas Oui/Non, c’est le résultat ⊥ traduit par représentation : « Je m’abstients ». 


Une traçabilité complète
Chaque décision peut exposer :
* la profondeur du contexte reconnu ; 
* les dimensions utilisées ; 
* le mode exact ou puissance ; 
* le support ; 
* les objets résolus ; 
* la frontière des candidats. 
Il est donc possible d’expliquer pourquoi un caractère a été produit.

Une arithmétique exacte
Les rapports sont des Fraction rationnelles. L’isologie de puissance travaille sur les exposants premiers.
Cela donne :
* aucune dérive flottante ; 
* aucune approximation silencieuse ; 
* une contradiction précisément détectable ; 
* une reproductibilité complète. 


Une séparation correcte entre identité et position

Deux objets ne peuvent avoir la même position dans ce référentiel, mais deux objets peuvent aussi avoir la même position sans être fusionnés. Cette arithmétique conceptuelle en dehors du système logique absolutiste peut être source de nouveaux prototypes, leur identité mémoire SQLite reste distincte : c’est conceptuellement exempt d’erreur : une collision de coordonnées devient une ambiguïté épistémique, pas une destruction d’identité.

