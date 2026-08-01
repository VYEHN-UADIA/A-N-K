from __future__ import annotations

from fractions import Fraction

BASE_DIMENSIONS = ("x", "y", "z")


def object_kind(value: str) -> str:
    if len(value) == 1:
        if value.isspace():
            return "space"
        if value.isalpha():
            return "letter"
        if value.isdigit():
            return "digit"
        return "character"
    return "object"


def measured_base_coordinates(total: int, left_diversity: int, right_diversity: int) -> dict[str, Fraction]:
    """Coordonnées fondamentales mesurées, jamais dérivées d'un hash.

    x = fréquence observée + 1
    y = diversité des contextes gauches + 1
    z = diversité des contextes droits + 1
    """
    return {
        "x": Fraction(total + 1, 1),
        "y": Fraction(left_diversity + 1, 1),
        "z": Fraction(right_diversity + 1, 1),
    }


def measured_logic_coordinate(count: int) -> Fraction:
    return Fraction(count + 1, 1)
