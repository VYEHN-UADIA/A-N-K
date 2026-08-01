"""ANANKÉ — strate distributive (module quantitatif) + mémoire relationnelle.

OBLIGATOIRE dans la distribution, ACCESSIBLE SELON BESOIN LOGIQUE :
primitive de première classe d'ANANKÉ, mais DORMANTE par défaut. Jamais
consultée par l'inférence linguistique. Réveillée uniquement lorsqu'un objet
ou une relation DÉCLARE explicitement un degré n. Le degré n'est jamais
inféré par le moteur.

Aucun log, aucun exp, aucun flottant. Rationnels exacts. Toute fermeture est
soit EXACTE ET UNIQUE, soit None (⊥) → abstention, jamais une approximation.

Pont fondamental (distributivité / binôme) :
    ρ_n(x,h) = ((x+h)/x)**n = Σ_k C(n,k) (h/x)**k        (rapport multiplicatif)
    Δ_n(x,h) = (x+h)**n - x**n = Σ_{k≥1} C(n,k) x**(n-k) h**k   (variation absolue)
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .numbers import exact_nth_root, positive_fraction

# --- Pascal : constantes pour petits degrés + cache partagé (construit une fois) ---
_SMALL: dict[int, tuple[int, ...]] = {
    0: (1,), 1: (1, 1), 2: (1, 2, 1), 3: (1, 3, 3, 1), 4: (1, 4, 6, 4, 1),
}
_CACHE: list[tuple[int, ...]] = [_SMALL[i] for i in range(5)]


def binomial_row(n: int) -> tuple[int, ...]:
    """Ligne n du triangle de Pascal. Constantes pour n≤4, sinon cache partagé
    étendu par addition pure une seule fois (aucune reconstruction par appel)."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("Le degré doit être un entier positif.")
    if n in _SMALL:
        return _SMALL[n]
    while len(_CACHE) <= n:
        prev = _CACHE[-1]
        _CACHE.append((1,) + tuple(prev[i] + prev[i + 1] for i in range(len(prev) - 1)) + (1,))
    return _CACHE[n]


def rational_nth_root(value: Fraction, degree: int) -> Fraction | None:
    """Racine n-ième RATIONNELLE EXACTE d'un rationnel positif, ou None.
    Aucun flottant : racine entière exacte du numérateur et du dénominateur."""
    value = positive_fraction(value)
    root_num = exact_nth_root(value.numerator, degree)
    root_den = exact_nth_root(value.denominator, degree)
    if root_num is None or root_den is None:
        return None
    return Fraction(root_num, root_den)


@dataclass(frozen=True)
class DistributiveCoordinate:
    x: Fraction            # position source (strictement positive)
    h: Fraction            # pas additif (signé)
    degree: int            # rang dimensionnel discret (jamais un rationnel)
    source_power: Fraction  # x**n
    target_power: Fraction  # (x+h)**n
    delta: Fraction         # Δ_n = (x+h)**n - x**n
    ratio: Fraction         # ρ_n = (x+h)**n / x**n


def distributive_coordinate(x, h, degree: int) -> DistributiveCoordinate:
    """Mode COMPACT (défaut) : une seule exponentiation par côté, pas de
    développement binomial. x>0, degré entier ≥1, cible (x+h)>0."""
    x = positive_fraction(x)
    if not isinstance(degree, int) or degree < 1:
        raise ValueError("Le degré doit être un entier ≥ 1.")
    h = Fraction(h)
    target = x + h
    if target <= 0:
        raise ValueError("La position cible (x+h) doit rester strictement positive.")
    source_power = x ** degree
    target_power = target ** degree
    return DistributiveCoordinate(
        x=x, h=h, degree=degree,
        source_power=source_power, target_power=target_power,
        delta=target_power - source_power, ratio=target_power / source_power,
    )


def distributive_expansion(x, h, degree: int) -> list[tuple[int, Fraction]]:
    """Mode EXPLICATIF : termes de Δ_n, (k, C(n,k) x^{n-k} h^k) pour k=1..n.
    Leur somme reconstruit exactement Δ_n. Matérialisé seulement pour expliquer,
    fermer terme à terme, ou comparer deux structures distributives."""
    x = positive_fraction(x)
    h = Fraction(h)
    coefficients = binomial_row(degree)
    return [(k, Fraction(coefficients[k]) * x ** (degree - k) * h ** k) for k in range(1, degree + 1)]


# ---------------------------------------------------------------------------
# Fermetures par contrainte — chacune EXACTE ET UNIQUE, sinon None (⊥ → abstention)
# ---------------------------------------------------------------------------
def close_ratio(x, degree: int, delta) -> Fraction:
    """ρ reconstruit depuis Δ : ρ = 1 + Δ/x^n. Toujours exact."""
    x = positive_fraction(x)
    return Fraction(1) + Fraction(delta) / (x ** degree)


def close_delta(x, degree: int, ratio) -> Fraction:
    """Δ reconstruit depuis ρ : Δ = x^n (ρ-1). Toujours exact."""
    x = positive_fraction(x)
    return (x ** degree) * (Fraction(ratio) - 1)


def close_coefficient(delta_absolute, x, h, degree: int) -> Fraction | None:
    """Facteur de forme masqué κ (ex. 4π/3) : ΔV = κ·Δ_n ⇒ κ = ΔV/Δ_n.
    None si Δ_n = 0 (sous-déterminé). NB : κ n'est reconstructible qu'avec une
    mesure d'ancrage ΔV — cf. limite de sous-détermination."""
    structural = distributive_coordinate(x, h, degree).delta
    if structural == 0:
        return None
    return Fraction(delta_absolute) / structural


def close_step(x, degree: int, delta) -> Fraction | None:
    """h reconstruit depuis Δ : (x+h)^n = x^n+Δ ⇒ h = (x^n+Δ)^{1/n} - x.
    None si la racine n-ième n'est pas rationnelle exacte. Solution unique
    (racine positive)."""
    x = positive_fraction(x)
    target_power = x ** degree + Fraction(delta)
    if target_power <= 0:
        return None
    root = rational_nth_root(target_power, degree)
    if root is None:
        return None
    return root - x


def close_degree(x, h, ratio, allowed_degrees: Sequence[int]) -> int | None:
    """n reconstruit depuis ρ : recherche discrète bornée PARMI les degrés
    DÉCLARÉS. Retourne l'unique n exact, sinon None. Jamais au-delà des degrés
    autorisés (le degré n'est pas inventé, il est sélectionné par contrainte)."""
    x = positive_fraction(x)
    quotient = (x + Fraction(h)) / x
    if quotient == 1:
        return None  # ρ=1 pour tout n → ambigu (ou impossible)
    target = Fraction(ratio)
    hits = [n for n in allowed_degrees if int(n) >= 1 and quotient ** int(n) == target]
    return int(hits[0]) if len(hits) == 1 else None


# ---------------------------------------------------------------------------
# Cellule de Mémoire Relationnelle Distributive  — mémoire par fermeture
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MemoryCell:
    """Cellule mémoire. Ne mémorise pas une valeur, mais une SITUATION reconstructible :
    (identité, x, h, n, Δ, ρ) + liens. Redondance = preuve d'intégrité."""
    identity: str
    x: Fraction
    h: Fraction
    degree: int
    delta: Fraction
    ratio: Fraction
    prev: str | None = None
    next: str | None = None

    def is_coherent(self) -> bool:
        """Fermeture triple : x^n+Δ = (x+h)^n = x^n·ρ, et 1+Δ/x^n = ρ."""
        source_power = self.x ** self.degree
        target_power = (self.x + self.h) ** self.degree
        return (
            source_power + self.delta == target_power
            and source_power * self.ratio == target_power
            and Fraction(1) + self.delta / source_power == self.ratio
        )


def memory_cell(identity: str, x, h, degree: int,
                prev: str | None = None, next: str | None = None) -> MemoryCell:
    coordinate = distributive_coordinate(x, h, degree)
    return MemoryCell(
        identity=str(identity), x=coordinate.x, h=coordinate.h, degree=degree,
        delta=coordinate.delta, ratio=coordinate.ratio, prev=prev, next=next,
    )


def recall_masked(x, degree: int, *, delta=None, ratio=None) -> dict | None:
    """Rappel par contrainte : reconstruit le champ manquant entre Δ et ρ.
    Exactement UN des deux doit être masqué, sinon ⊥ (None)."""
    if (delta is None) == (ratio is None):
        return None  # ni 0 ni 2 champs manquants gérés ici → sous/sur-déterminé
    if ratio is None:
        return {"ratio": close_ratio(x, degree, delta)}
    return {"delta": close_delta(x, degree, ratio)}


def chain_state(x0, cells: Sequence[MemoryCell], degree: int) -> Fraction | None:
    """Rejoue une trajectoire à degré fixe par les DEUX chemins :
    x_m^n = x_0^n · Π ρ_i  (multiplicatif) = x_0^n + Σ Δ_i  (additif).
    Retourne x_m^n si les deux coïncident et chaque cellule ferme, sinon None."""
    x = positive_fraction(x0)
    multiplicative = x ** degree
    additive = x ** degree
    for cell in cells:
        if cell.degree != degree or cell.x != x or not cell.is_coherent():
            return None
        multiplicative *= cell.ratio
        additive += cell.delta
        x = x + cell.h
    return multiplicative if multiplicative == additive else None


def associates(a: MemoryCell, b: MemoryCell) -> bool:
    """Mémoire associative : deux cellules s'associent si même degré et même
    rapport multiplicatif (même loi distributive), indépendamment de leur position."""
    return a.degree == b.degree and a.ratio == b.ratio


# ===========================================================================
# Coordonnée de fermeture ε — la VÉRITÉ réifiée comme donnée de première classe
# ---------------------------------------------------------------------------
# ε = membre_gauche − membre_droite d'une contrainte, EXACT.
#   ε = 0  ⇔  la réalité mathématique est vraie (cohérente) → truth = 1
#   ε ≠ 0  ⇔  fausse, ET |ε| mesure DE COMBIEN (1=2 → ε=-1, pas seulement « non »)
# ε est une coordonnée ADDITIVE (un écart), HORS du référentiel multiplicatif ℚ⁺ :
# c'est pourquoi ε=0 est AUTORISÉ ici — 0 est l'état « vrai », le sol du système —
# alors que 0 reste interdit comme coordonnée MULTIPLICATIVE. Les deux régimes ne se
# contredisent pas : ils vivent dans deux espaces (additif vs multiplicatif).
# ===========================================================================

@dataclass(frozen=True)
class ClosureCoordinate:
    """Résidu exact d'une contrainte. ε=0 signifie « cette contrainte déterminée
    FERME exactement avec les données fournies » — une cohérence algébrique locale,
    PAS une vérité sémantique/absolue. Le prédicat est DÉRIVÉ de ε, jamais stocké :
    aucun état impossible (ε=0, faux) n'est représentable."""
    epsilon: Fraction   # écart exact (peut être nul ou négatif)
    label: str = ""

    @property
    def holds(self) -> bool:
        return self.epsilon == 0

    @property
    def truth(self) -> int:  # compat lecture seule : dérivé, jamais un champ
        return int(self.epsilon == 0)


def closure_epsilon(left, right, label: str = "") -> ClosureCoordinate:
    """Résidu exact d'une égalité : ε = left − right. holds ⇔ ε=0."""
    return ClosureCoordinate(epsilon=Fraction(left) - Fraction(right), label=label)


def closure_of_step(x, h, degree: int, delta_claim, label: str = "step") -> ClosureCoordinate:
    """Vérité de l'assertion « (x+h)^n − x^n == delta_claim » : ε = Δ_vrai − delta_claim."""
    true_delta = distributive_coordinate(x, h, degree).delta
    return closure_epsilon(true_delta, Fraction(delta_claim), label)


def cell_closure(cell: MemoryCell) -> tuple[ClosureCoordinate, ClosureCoordinate, ClosureCoordinate]:
    """Fermeture VECTORIELLE d'une cellule : Γ(M) = (ε_Δ, ε_ρ, ε_Δρ).
    La cellule est cohérente SSI Γ = (0, 0, 0). Un résidu non nul LOCALISE la
    corruption (quel chemin, de combien) — bien plus informatif qu'un booléen.
        ε_Δ  = (x^n + Δ)      − (x+h)^n
        ε_ρ  = (x^n · ρ)      − (x+h)^n
        ε_Δρ = (1 + Δ/x^n)    − ρ
    Corrige le défaut de la v3.3.3 : un ρ falsifié seul n'était pas détecté."""
    source_power = cell.x ** cell.degree
    target_power = (cell.x + cell.h) ** cell.degree
    return (
        closure_epsilon(source_power + cell.delta, target_power, "cell.delta"),
        closure_epsilon(source_power * cell.ratio, target_power, "cell.ratio"),
        closure_epsilon(Fraction(1) + cell.delta / source_power, cell.ratio, "cell.delta_ratio"),
    )


def cell_holds(cell: MemoryCell) -> bool:
    """Cohérence complète : les TROIS résidus de Γ(M) sont nuls."""
    return all(component.holds for component in cell_closure(cell))


def combine_holds(items: Sequence[ClosureCoordinate]) -> bool:
    """Composition SÛRE : cohérent ⇔ TOUT ferme (ET logique). Aucune addition de
    résidus hétérogènes — un résidu de longueur, de volume et de rapport ne
    s'additionnent pas (dimensions incompatibles)."""
    return all(item.holds for item in items)


def scalar_defect(items: Sequence[ClosureCoordinate]) -> Fraction:
    """Métrique scalaire OPTIONNELLE Σ|ε_i|, valide UNIQUEMENT si les résidus sont
    homogènes (même espace/dimension). À n'utiliser qu'après typage dimensionnel
    explicite ; sinon préférer combine_holds (vecteur)."""
    return sum((abs(item.epsilon) for item in items), Fraction(0))


def admits_step(x, h, degree: int, delta_claim) -> bool:
    """Régime SÛR : un pas n'est admis QUE si sa fermeture est exacte (ε=0).
    Contrainte de génération : empêche structurellement de produire un pas faux."""
    return closure_of_step(x, h, degree, delta_claim).holds
