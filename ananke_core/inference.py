from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction

from .coordinates import object_kind
from .numbers import decode_fraction, rational_power_exact
from .power import common_power_scale
from .signature import decode_vector, trajectory_signature
from .store import AnankeStore


@dataclass
class CandidateEvidence:
    object_id: int
    exact_depth: int = 0
    exact_support: int = 0
    power_depth: int = 0
    power_support: int = 0
    dimension_coverage: int = 0
    objective_hits: int = 0

    def criteria(self) -> tuple[int, int, int, int, int, int]:
        return (
            self.exact_depth,
            self.dimension_coverage,
            self.exact_support,
            self.power_depth,
            self.power_support,
            self.objective_hits,
        )

    def dominates(self, other: "CandidateEvidence") -> bool:
        left, right = self.criteria(), other.criteria()
        return all(a >= b for a, b in zip(left, right)) and any(a > b for a, b in zip(left, right))


def _flatten_trajectory(raw: str) -> list[Fraction]:
    rows = json.loads(raw)
    values: list[Fraction] = []
    for row in rows:
        for dimension in sorted(row):
            values.append(decode_fraction(str(row[dimension])))
    return values


class ReferentialInference:
    """Inférence relationnelle en lecture seule.

    Les règles stockent une relation suivante, jamais l'identité du caractère
    suivant. La sortie est résolue depuis la position multiplicative calculée.
    """

    def __init__(self, store: AnankeStore, max_context: int = 18):
        if not store.read_only:
            # Le code fonctionne aussi en écriture pour les tests internes, mais
            # le runtime public ouvre toujours le store en mode SQLite ro.
            pass
        self.store = store
        self.max_context = max(2, max_context)

    def _context_lengths(self, available: int) -> list[int]:
        if available < 2:
            return []
        if available <= 8:
            return list(range(2, available + 1))
        return sorted({v for v in (2, 3, 5, 8, 13, self.max_context, available) if 2 <= v <= available})

    def _apply_relation(self, source_id: int, relation: dict[str, Fraction]) -> tuple[dict[str, Fraction], list[str]]:
        dimensions = sorted(relation)
        source = self.store.coordinates(source_id, dimensions)
        target = {
            dimension: source[dimension] * factor
            for dimension, factor in relation.items()
            if dimension in source
        }
        usable = sorted(target)
        return target, usable

    def _register_candidates(self, evidence: dict[int, CandidateEvidence], relation: dict[str, Fraction],
                             source_id: int, depth: int, support: int, exact: bool,
                             objective_weight: int, traces: list[dict], mode: str) -> None:
        target, usable = self._apply_relation(source_id, relation)
        if not usable:
            return
        resolved = self.store.resolve_coordinates(target, usable)
        resolved_chars = []
        for object_id in resolved:
            value = self.store.object_value(object_id)
            if len(value) != 1:
                continue
            resolved_chars.append(value)
            item = evidence.setdefault(object_id, CandidateEvidence(object_id))
            if exact:
                item.exact_depth = max(item.exact_depth, depth)
                item.exact_support += support
            else:
                item.power_depth = max(item.power_depth, depth)
                item.power_support += support
            item.dimension_coverage = max(item.dimension_coverage, len(usable))
            item.objective_hits += objective_weight
        traces.append({
            "mode": mode,
            "depth": depth,
            "dimensions": usable,
            "resolved": resolved_chars[:24],
            "support": support,
        })

    def next_character(self, context: str, objective: str = "general") -> tuple[str | None, dict]:
        if len(context) < 2:
            return None, {"reason": "insufficient_relational_context"}
        ids: list[int] = []
        normalizations: list[dict[str, str | int]] = []
        sentence_start = True
        for index, ch in enumerate(context):
            object_id = self.store.object_id(ch, object_kind(ch))
            if object_id is None and sentence_start and ch.isalpha():
                # Un utilisateur peut commencer naturellement par une minuscule
                # alors que le corpus possède la majuscule de début de phrase.
                # L'alias n'altère pas le référentiel et reste déclaré dans la trace.
                alias = ch.upper()
                alias_id = self.store.object_id(alias, object_kind(alias))
                if alias_id is not None:
                    object_id = alias_id
                    normalizations.append({"index": index, "from": ch, "to": alias})
            if object_id is None:
                return None, {"reason": "unknown_object", "object": ch, "normalizations": normalizations}
            ids.append(object_id)
            if ch in ".!?\n\r":
                sentence_start = True
            elif not ch.isspace():
                sentence_start = False

        objectives = [objective] + ([] if objective == "general" else ["general"])
        evidence: dict[int, CandidateEvidence] = {}
        traces: list[dict] = []
        for objective_index, current_objective in enumerate(objectives):
            dimensions = self.store.inference_dimensions(current_objective)
            if not dimensions:
                continue
            power_dimensions = self.store.relation_dimensions(dimensions)
            for length in sorted(self._context_lengths(min(self.max_context, len(ids))), reverse=True):
                suffix = ids[-length:]
                exact_hash, power_hash, query_raw, query_values = trajectory_signature(self.store, suffix, dimensions, power_dimensions)
                exact_rows = self.store._connection.execute(
                    """SELECT next_relation_json,support FROM relation_rules
                       WHERE objective=? AND context_length=? AND trajectory_hash=?""",
                    (current_objective, length, exact_hash),
                ).fetchall()
                for row in exact_rows:
                    self._register_candidates(
                        evidence, decode_vector(str(row["next_relation_json"])), suffix[-1], length,
                        int(row["support"]), True, 2 if objective_index == 0 else 1,
                        traces, f"exact:{current_objective}",
                    )

                power_rows = self.store._connection.execute(
                    """SELECT trajectory_json,next_relation_json,support FROM relation_rules
                       WHERE objective=? AND context_length=? AND trajectory_power_hash=? AND trajectory_hash<>?""",
                    (current_objective, length, power_hash, exact_hash),
                ).fetchall() if power_hash else []
                for row in power_rows:
                    stored_values = _flatten_trajectory(str(row["trajectory_json"]))
                    scale = common_power_scale(stored_values, query_values)
                    if scale is None:
                        continue
                    base_relation = decode_vector(str(row["next_relation_json"]))
                    transformed: dict[str, Fraction] = {}
                    valid = True
                    for dimension, factor in base_relation.items():
                        powered = rational_power_exact(factor, scale)
                        if powered is None:
                            valid = False
                            break
                        transformed[dimension] = powered
                    if valid:
                        self._register_candidates(
                            evidence, transformed, suffix[-1], length, int(row["support"]), False,
                            2 if objective_index == 0 else 1, traces,
                            f"power:{current_objective}:{scale.numerator}/{scale.denominator}",
                        )

        if not evidence:
            return None, {"reason": "no_resolved_relation", "traces": traces, "normalizations": normalizations}
        items = list(evidence.values())
        frontier = [item for item in items if not any(other.dominates(item) for other in items if other.object_id != item.object_id)]
        frontier.sort(key=lambda item: (item.criteria(), -item.object_id), reverse=True)
        if len(frontier) > 1 and frontier[0].criteria() == frontier[1].criteria():
            return None, {
                "reason": "contingent_frontier",
                "candidates": [self.store.object_value(item.object_id) for item in frontier[:24]],
                "criteria": frontier[0].criteria(),
                "traces": traces,
                "normalizations": normalizations,
            }
        selected = frontier[0]
        value = self.store.object_value(selected.object_id)
        return value, {
            "selected": value,
            "criteria": selected.criteria(),
            "frontier": [self.store.object_value(item.object_id) for item in frontier[:24]],
            "traces": traces,
            "normalizations": normalizations,
        }

    def generate(self, prompt: str, objective: str = "general", max_characters: int = 512,
                 include_trace: bool = False) -> dict:
        generated = ""
        trace: list[dict] = []
        seen_suffixes: defaultdict[str, int] = defaultdict(int)
        for step in range(max(1, max_characters)):
            next_value, decision = self.next_character(prompt + generated, objective)
            trace.append({"step": step, **decision})
            if next_value is None:
                break
            generated += next_value
            suffix = (prompt + generated)[-64:]
            seen_suffixes[suffix] += 1
            if seen_suffixes[suffix] > 2:
                break
            if next_value in ("\n", "\r") and generated.strip():
                break
        last_decision = trace[-1] if trace else {"reason": "no_decision"}
        result = {
            "output": generated,
            "objective": objective,
            "characters": len(generated),
            "decisions": len(trace),
            "abstained": not bool(generated),
            "generator": "relation-to-position-to-character",
            "stop_reason": last_decision.get("reason", "completed"),
        }
        if last_decision.get("reason") == "unknown_object":
            result["unknown_object"] = last_decision.get("object")
        if last_decision.get("normalizations"):
            result["normalizations"] = last_decision["normalizations"]
        if include_trace:
            result["trace"] = trace
        return result
