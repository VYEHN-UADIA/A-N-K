from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from functools import lru_cache


@lru_cache(maxsize=200000)
def _factor_tuple(value: int) -> tuple[tuple[int, int], ...]:
    value = abs(value)
    factors: dict[int, int] = {}
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            factors[divisor] = factors.get(divisor, 0) + 1
            value //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        factors[value] = factors.get(value, 0) + 1
    return tuple(sorted(factors.items()))


def factor_integer(value: int) -> dict[int, int]:
    # Copie fraîche à chaque appel : les appelants (exponents) mutent le dict.
    return dict(_factor_tuple(abs(value)))


def exponents(value: Fraction) -> dict[int, int]:
    result = factor_integer(value.numerator)
    for prime, exponent in factor_integer(value.denominator).items():
        result[prime] = result.get(prime, 0) - exponent
    return {prime: exponent for prime, exponent in result.items() if exponent}


def canonical_power_shape(values: list[Fraction]) -> str:
    exponent_maps = [exponents(value) for value in values]
    non_zero = [abs(exp) for mapping in exponent_maps for exp in mapping.values() if exp]
    divisor = 0
    for exponent in non_zero:
        divisor = math.gcd(divisor, exponent)
    divisor = max(1, divisor)
    payload = [
        sorted((prime, exponent // divisor) for prime, exponent in mapping.items())
        for mapping in exponent_maps
    ]
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def common_power_scale(reference: list[Fraction], observed: list[Fraction]) -> Fraction | None:
    """Retourne λ si observed[i] = reference[i]**λ pour toute la famille.

    La comparaison travaille dans les exposants premiers exacts. Elle ne calcule
    ni logarithme ni exponentielle.
    """
    if len(reference) != len(observed) or not reference:
        return None
    scale: Fraction | None = None
    for left, right in zip(reference, observed):
        left_map = exponents(left)
        right_map = exponents(right)
        primes = set(left_map) | set(right_map)
        for prime in primes:
            a = left_map.get(prime, 0)
            b = right_map.get(prime, 0)
            if a == 0:
                if b != 0:
                    return None
                continue
            current = Fraction(b, a)
            if scale is None:
                scale = current
            elif current != scale:
                return None
    return scale if scale is not None and scale > 0 else None
