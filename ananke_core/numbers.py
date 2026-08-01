from __future__ import annotations

from fractions import Fraction
from math import isqrt


def positive_fraction(value: str | int | Fraction) -> Fraction:
    result = value if isinstance(value, Fraction) else Fraction(value)
    if result <= 0:
        raise ValueError("Une coordonnée multiplicative doit être strictement positive.")
    return result


def encode_fraction(value: Fraction) -> str:
    value = positive_fraction(value)
    return f"{value.numerator}/{value.denominator}"


def decode_fraction(value: str) -> Fraction:
    return positive_fraction(Fraction(value))


def exact_nth_root(value: int, degree: int) -> int | None:
    if value < 0 or degree <= 0:
        return None
    if value in (0, 1) or degree == 1:
        return value
    low, high = 1, 1
    while high**degree < value:
        high *= 2
    while low <= high:
        middle = (low + high) // 2
        powered = middle**degree
        if powered == value:
            return middle
        if powered < value:
            low = middle + 1
        else:
            high = middle - 1
    return None


def rational_power_exact(value: Fraction, exponent: Fraction) -> Fraction | None:
    """Calcule value**exponent seulement si le résultat est rationnel exact.

    Aucun logarithme, aucune exponentielle et aucune approximation flottante.
    """
    value = positive_fraction(value)
    numerator_power = exponent.numerator
    root_degree = exponent.denominator
    powered = value ** abs(numerator_power)
    if numerator_power < 0:
        powered = Fraction(1, 1) / powered
    root_num = exact_nth_root(powered.numerator, root_degree)
    root_den = exact_nth_root(powered.denominator, root_degree)
    if root_num is None or root_den is None:
        return None
    return positive_fraction(Fraction(root_num, root_den))
