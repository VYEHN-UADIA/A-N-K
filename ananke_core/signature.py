from __future__ import annotations

import hashlib
import json
from fractions import Fraction

from .numbers import decode_fraction, encode_fraction
from .power import canonical_power_shape
from .store import AnankeStore


def relation_vector(store: AnankeStore, source_id: int, target_id: int, dimensions: list[str]) -> dict[str, Fraction]:
    source = store.coordinates(source_id, dimensions)
    target = store.coordinates(target_id, dimensions)
    return {
        dimension: target[dimension] / source[dimension]
        for dimension in dimensions
        if dimension in source and dimension in target
    }


def encode_vector(vector: dict[str, Fraction]) -> str:
    return json.dumps(
        {dimension: encode_fraction(value) for dimension, value in sorted(vector.items())},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def decode_vector(raw: str) -> dict[str, Fraction]:
    payload = json.loads(raw)
    return {str(dimension): decode_fraction(str(value)) for dimension, value in payload.items()}


def trajectory_signature(store: AnankeStore, object_ids: list[int], dimensions: list[str],
                         power_dimensions: list[str] | None = None) -> tuple[str, str, str, list[Fraction]]:
    if len(object_ids) < 2:
        raise ValueError("Une trajectoire relationnelle exige au moins deux objets.")
    # Déviance de deuxième ordre corrigée : l'homologie de puissance (mise à
    # l'échelle globale exacte dans le réseau des exposants) n'a de sens que sur
    # des lois multiplicatives DÉSIGNÉES. Sur des coordonnées MESURÉES (comptages,
    # diversité), une même direction d'exposants est un accident arithmétique.
    # On n'émet donc de power_hash que sur les dimensions relationnelles.
    # power_dimensions=None => toutes (compatibilité ascendante).
    power_set = set(dimensions if power_dimensions is None else power_dimensions)
    rows: list[dict[str, str]] = []
    flattened: list[Fraction] = []
    for index in range(1, len(object_ids)):
        vector = relation_vector(store, object_ids[index - 1], object_ids[index], dimensions)
        rows.append({dimension: encode_fraction(value) for dimension, value in sorted(vector.items())})
        flattened.extend(value for dimension, value in sorted(vector.items()) if dimension in power_set)
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    exact_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    power_hash = canonical_power_shape(flattened) if flattened else ""
    return exact_hash, power_hash, raw, flattened


def next_relation_signature(store: AnankeStore, source_id: int, target_id: int, dimensions: list[str]) -> tuple[str, str, dict[str, Fraction]]:
    vector = relation_vector(store, source_id, target_id, dimensions)
    raw = encode_vector(vector)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest(), raw, vector
