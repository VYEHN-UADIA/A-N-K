from __future__ import annotations

import re
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from .coordinates import measured_base_coordinates, measured_logic_coordinate, object_kind
from .ingestion import extract_content
from .signature import next_relation_signature, trajectory_signature
from .store import AnankeStore

VOWELS = set("aeiouyàâäéèêëîïôöùûüÿœAEIOUYÀÂÄÉÈÊËÎÏÔÖÙÛÜŸŒ")
WORD_RE = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)
AUTO_FEATURES = (
    "frequency", "after_space", "before_space", "word_start", "word_end",
    "uppercase", "vowel", "punctuation", "digit", "whitespace",
    "left_diversity", "right_diversity",
)
AUTO_LABELS = {
    "frequency": "Fréquence observée",
    "after_space": "Présence après espace",
    "before_space": "Présence avant espace",
    "word_start": "Début de mot",
    "word_end": "Fin de mot",
    "uppercase": "Majuscule",
    "vowel": "Voyelle",
    "punctuation": "Ponctuation",
    "digit": "Chiffre",
    "whitespace": "Espace",
    "left_diversity": "Diversité contextuelle gauche",
    "right_diversity": "Diversité contextuelle droite",
}


class AnankeTrainer:
    def __init__(self, store: AnankeStore, max_context: int = 18):
        self.store = store
        self.max_context = max(2, max_context)

    def train_file(self, path: str | Path, objective: str = "general", user_id: int | None = None) -> dict:
        content = extract_content(path)
        with self.store.transaction() as connection:
            version = self.store.next_version(connection)
            relations = [
                self.add_relation_in_transaction(connection, relation, version, objective, reconcile=False)
                for relation in content["relations"]
            ]
            metrics = self._add_line_and_reconcile(
                connection, content["text"], objective, Path(path).name, user_id, version, content["bytes"]
            )
            self.store.journal(connection, version, "train_file", {
                "file": str(path), "objective": objective, "relations": relations, "metrics": metrics
            })
        return {"version": version, "relations_added": len(relations), **metrics, "stats": self.store.stats()}

    def _ensure_characters(self, connection, text: str, version: int) -> list[int]:
        return [
            self.store.ensure_object(ch, object_kind(ch), version, label="Caractère encodé", connection=connection)
            for ch in text
        ]

    def _add_line_and_reconcile(self, connection, text: str, objective: str, source: str,
                                user_id: int | None, version: int, source_bytes: int = 0) -> dict:
        if not text:
            raise ValueError("Le corpus est vide.")
        self._ensure_characters(connection, text, version)
        connection.execute(
            "INSERT INTO lines(objective,text,source,source_bytes,user_id,version) VALUES(?,?,?,?,?,?)",
            (objective, text, source, source_bytes, user_id, version),
        )
        return self._reconcile_objective(connection, objective, version)

    def _context_lengths(self, available: int) -> list[int]:
        if available < 2:
            return []
        if available <= 8:
            return list(range(2, available + 1))
        return sorted({value for value in (2, 3, 5, 8, 13, self.max_context, available) if 2 <= value <= available})

    def _reconcile_objective(self, connection, objective: str, version: int) -> dict:
        """Recalcule honnêtement l'objectif complet.

        Cette version n'affirme pas être incrémentale : toute modification des
        coordonnées peut modifier les lois dérivées. Le cycle est donc une
        réconciliation transactionnelle complète de l'objectif concerné.
        """
        line_rows = connection.execute(
            "SELECT id,text FROM lines WHERE objective=? ORDER BY id", (objective,)
        ).fetchall()
        connection.execute("DELETE FROM object_stats WHERE objective=?", (objective,))
        connection.execute("DELETE FROM neighbor_observations WHERE objective=?", (objective,))
        connection.execute("DELETE FROM relation_rules WHERE objective=?", (objective,))

        stats: dict[int, Counter[str]] = defaultdict(Counter)
        neighbors: Counter[tuple[int, int]] = Counter()
        encoded_lines: list[tuple[int, str, list[int]]] = []
        for row in line_rows:
            text = str(row["text"])
            ids = self._ensure_characters(connection, text, version)
            encoded_lines.append((int(row["id"]), text, ids))
            for index, (object_id, ch) in enumerate(zip(ids, text)):
                item = stats[object_id]
                item["total"] += 1
                item["after_space"] += int(index == 0 or text[index - 1].isspace())
                item["before_space"] += int(index + 1 == len(text) or text[index + 1].isspace())
                item["word_start"] += int(index == 0 or not text[index - 1].isalpha())
                item["word_end"] += int(index + 1 == len(text) or not text[index + 1].isalpha())
                item["uppercase"] += int(ch.isupper())
                item["vowel"] += int(ch in VOWELS)
                item["punctuation"] += int(not ch.isalnum() and not ch.isspace())
                item["digit"] += int(ch.isdigit())
                item["whitespace"] += int(ch.isspace())
                if index + 1 < len(ids):
                    neighbors[(object_id, ids[index + 1])] += 1

        left_sets: dict[int, set[int]] = defaultdict(set)
        right_sets: dict[int, set[int]] = defaultdict(set)
        for (source_id, target_id), support in neighbors.items():
            connection.execute(
                "INSERT INTO neighbor_observations(objective,source_object_id,target_object_id,support) VALUES(?,?,?,?)",
                (objective, source_id, target_id, support),
            )
            right_sets[source_id].add(target_id)
            left_sets[target_id].add(source_id)

        for object_id, item in stats.items():
            connection.execute(
                """INSERT INTO object_stats(object_id,objective,total,after_space,before_space,word_start,word_end,uppercase,vowel,punctuation,digit,whitespace)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (object_id, objective, item["total"], item["after_space"], item["before_space"],
                 item["word_start"], item["word_end"], item["uppercase"], item["vowel"],
                 item["punctuation"], item["digit"], item["whitespace"]),
            )

        self._rebuild_measured_coordinates(connection, objective, version, left_sets, right_sets)
        dimensions = self.store.inference_dimensions(objective)
        power_dimensions = self.store.relation_dimensions(dimensions)
        rules = 0
        occurrences = 0
        for _, _, ids in encoded_lines:
            for next_index in range(2, len(ids)):
                next_id = ids[next_index]
                for length in self._context_lengths(min(self.max_context, next_index)):
                    context = ids[next_index - length:next_index]
                    trajectory_hash, power_hash, trajectory_json, _ = trajectory_signature(self.store, context, dimensions, power_dimensions)
                    relation_hash, relation_json, _ = next_relation_signature(self.store, context[-1], next_id, dimensions)
                    if relation_json == "{}":
                        continue
                    connection.execute(
                        """INSERT INTO relation_rules(objective,context_length,trajectory_hash,trajectory_power_hash,trajectory_json,
                           next_relation_hash,next_relation_json,support,last_version)
                           VALUES(?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(objective,context_length,trajectory_hash,next_relation_hash) DO UPDATE SET
                             support=relation_rules.support+1,
                             trajectory_power_hash=excluded.trajectory_power_hash,
                             trajectory_json=excluded.trajectory_json,
                             next_relation_json=excluded.next_relation_json,
                             last_version=excluded.last_version""",
                        (objective, length, trajectory_hash, power_hash, trajectory_json,
                         relation_hash, relation_json, 1, version),
                    )
                    rules += 1
                occurrences += 1
        family_count = int(connection.execute(
            "SELECT COUNT(*) FROM relation_rules WHERE objective=?", (objective,)
        ).fetchone()[0])
        return {
            "objective": objective,
            "lines_reconciled": len(encoded_lines),
            "characters_reconciled": sum(len(ids) for _, _, ids in encoded_lines),
            "relation_observations": occurrences,
            "relation_rule_insertions": rules,
            "relation_rule_families": family_count,
            "reconciliation": "full-objective-transactional",
        }

    def _rebuild_measured_coordinates(self, connection, objective: str, version: int,
                                      left_sets: dict[int, set[int]], right_sets: dict[int, set[int]]) -> None:
        parent = f"objective/{objective}"
        self.store.ensure_dimension(parent, objective, "logic", version, label=f"Objectif logique · {objective}", connection=connection)
        for feature in AUTO_FEATURES:
            self.store.ensure_dimension(
                f"objective/{objective}/{feature}", objective, "measured", version,
                parent, AUTO_LABELS[feature], connection,
            )

        objective_rows = connection.execute(
            "SELECT * FROM object_stats WHERE objective=?", (objective,)
        ).fetchall()
        for row in objective_rows:
            object_id = int(row["object_id"])
            counts = {feature: int(row[feature]) for feature in AUTO_FEATURES if feature not in ("frequency", "left_diversity", "right_diversity")}
            counts["frequency"] = int(row["total"])
            counts["left_diversity"] = len(left_sets.get(object_id, set()))
            counts["right_diversity"] = len(right_sets.get(object_id, set()))
            for feature, count in counts.items():
                self.store.set_coordinate(
                    object_id, f"objective/{objective}/{feature}", measured_logic_coordinate(count),
                    "measured-corpus", version, connection,
                )

        # x/y/z sont globaux : ils agrègent toutes les observations disponibles.
        objects = connection.execute("SELECT id FROM objects").fetchall()
        for object_row in objects:
            object_id = int(object_row["id"])
            total = int(connection.execute(
                "SELECT COALESCE(SUM(total),0) FROM object_stats WHERE object_id=?", (object_id,)
            ).fetchone()[0])
            left_diversity = int(connection.execute(
                "SELECT COUNT(DISTINCT source_object_id) FROM neighbor_observations WHERE target_object_id=?", (object_id,)
            ).fetchone()[0])
            right_diversity = int(connection.execute(
                "SELECT COUNT(DISTINCT target_object_id) FROM neighbor_observations WHERE source_object_id=?", (object_id,)
            ).fetchone()[0])
            for address, coordinate in measured_base_coordinates(total, left_diversity, right_diversity).items():
                self.store.set_coordinate(object_id, address, coordinate, "measured-corpus", version, connection)

    def add_relation_in_transaction(self, connection, relation: dict, version: int,
                                    default_logic: str, reconcile: bool = True) -> dict:
        source = str(relation["source"])
        target = str(relation["target"])
        dimension = str(relation["dimension"])
        factor = Fraction(str(relation["factor"]))
        if factor <= 0:
            raise ValueError("Le facteur doit être strictement positif.")
        logic = str(relation.get("logic") or default_logic)
        label = str(relation.get("label") or dimension)
        source_id = self.store.ensure_object(source, version=version, connection=connection)
        target_id = self.store.ensure_object(target, version=version, connection=connection)
        dimension_id = self.store.ensure_dimension(
            dimension, logic, "relation", version, label=label, connection=connection
        )
        current = connection.execute(
            "SELECT factor FROM relations WHERE source_object_id=? AND target_object_id=? AND dimension_id=?",
            (source_id, target_id, dimension_id),
        ).fetchone()
        if current is not None and Fraction(str(current[0])) != factor:
            raise ValueError(f"Contradiction: {source}→{target} vaut déjà {current[0]} dans {dimension}.")
        connection.execute(
            """INSERT INTO relations(source_object_id,target_object_id,dimension_id,factor,support,source,version)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(source_object_id,target_object_id,dimension_id) DO UPDATE SET
                 support=relations.support+1, version=excluded.version, source=excluded.source""",
            (source_id, target_id, dimension_id, str(factor), 1, str(relation.get("source_name") or "manual"), version),
        )
        self._solve_dimension(connection, dimension_id, dimension, version)
        if reconcile:
            objectives = {logic, "general"}
            for objective in objectives:
                if connection.execute("SELECT 1 FROM lines WHERE objective=? LIMIT 1", (objective,)).fetchone():
                    self._reconcile_objective(connection, objective, version)
        return {"source": source, "target": target, "dimension": dimension, "factor": str(factor), "logic": logic}

    def _solve_dimension(self, connection, dimension_id: int, address: str, version: int) -> None:
        edges = connection.execute(
            "SELECT source_object_id,target_object_id,factor FROM relations WHERE dimension_id=?", (dimension_id,)
        ).fetchall()
        graph: dict[int, list[tuple[int, Fraction]]] = defaultdict(list)
        for edge in edges:
            factor = Fraction(str(edge["factor"]))
            source = int(edge["source_object_id"])
            target = int(edge["target_object_id"])
            graph[source].append((target, factor))
            graph[target].append((source, Fraction(1, 1) / factor))
        assigned: dict[int, Fraction] = {}
        for root in sorted(graph):
            if root in assigned:
                continue
            assigned[root] = Fraction(1, 1)
            stack = [root]
            while stack:
                current = stack.pop()
                for neighbour, factor in graph[current]:
                    expected = assigned[current] * factor
                    if neighbour in assigned and assigned[neighbour] != expected:
                        raise ValueError(f"Contradiction multiplicative dans {address}: {assigned[neighbour]} != {expected}")
                    if neighbour not in assigned:
                        assigned[neighbour] = expected
                        stack.append(neighbour)
        for object_id, coordinate in assigned.items():
            self.store.set_coordinate(object_id, address, coordinate, "relation", version, connection)
