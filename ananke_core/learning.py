from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

from .coordinates import object_kind
from .ingestion import extract_content
from .store import AnankeStore
from .trainer import AUTO_FEATURES, AnankeTrainer


class LearningCycle:
    def __init__(self, store: AnankeStore, trainer: AnankeTrainer):
        self.store = store
        self.trainer = trainer

    def analyze_file(self, path: str | Path, objective: str, user_id: int, filename: str) -> dict:
        started = time.perf_counter()
        content = extract_content(path)
        text = content["text"]
        explicit_relations = content["relations"]
        unique_chars = sorted(set(text))
        existing_values = {
            str(row[0]) for row in self.store._connection.execute(
                "SELECT value FROM objects WHERE kind IN ('letter','character','digit','space')"
            ).fetchall()
        }
        existing_chars = existing_values.intersection(unique_chars)
        pair_counts = Counter(zip(text, text[1:]))
        observed_pairs = max(0, len(text) - 1)
        known_pairs = 0
        for (source, target), support in pair_counts.items():
            source_id = self.store.object_id(source, object_kind(source))
            target_id = self.store.object_id(target, object_kind(target))
            if source_id is not None and target_id is not None:
                row = self.store._connection.execute(
                    "SELECT 1 FROM neighbor_observations WHERE objective=? AND source_object_id=? AND target_object_id=?",
                    (objective, source_id, target_id),
                ).fetchone()
                if row:
                    known_pairs += support
        contradictions: list[dict] = []
        valid_explicit = 0
        for relation in explicit_relations:
            try:
                source = str(relation["source"])
                target = str(relation["target"])
                dimension = str(relation["dimension"])
                factor = Fraction(str(relation["factor"]))
                row = self.store._connection.execute(
                    """SELECT r.factor FROM relations r
                       JOIN objects s ON s.id=r.source_object_id
                       JOIN objects t ON t.id=r.target_object_id
                       JOIN dimensions d ON d.id=r.dimension_id
                       WHERE s.value=? AND t.value=? AND d.address=?""",
                    (source, target, dimension),
                ).fetchone()
                if row is not None and Fraction(str(row[0])) != factor:
                    contradictions.append({
                        "source": source, "target": target, "dimension": dimension,
                        "existing": str(row[0]), "proposed": str(factor),
                    })
                else:
                    valid_explicit += 1
            except Exception as exc:
                contradictions.append({"invalid_relation": relation, "error": str(exc)})

        existing_dimensions = {
            str(row[0]) for row in self.store._connection.execute("SELECT address FROM dimensions").fetchall()
        }
        proposed_dimensions = [f"objective/{objective}"] + [f"objective/{objective}/{feature}" for feature in AUTO_FEATURES]
        dimensions_to_add = [address for address in proposed_dimensions if address not in existing_dimensions]
        coverage = len(existing_chars) / max(1, len(unique_chars)) * 100
        reuse = known_pairs / max(1, observed_pairs) * 100
        compression = observed_pairs / max(1, len(pair_counts))
        payload = {
            "file": {"name": filename, "bytes": content["bytes"], "extension": content["extension"]},
            "objective": objective,
            "base_version": self.store.version(),
            "characters": len(text),
            "unique_characters": len(unique_chars),
            "objects_existing": len(existing_chars),
            "objects_new": len(set(unique_chars) - existing_values),
            "relations_observed": observed_pairs,
            "relation_families": len(pair_counts),
            "relations_reused": known_pairs,
            "relation_families_new": max(0, len(pair_counts) - len({pair for pair in pair_counts if pair[0] in existing_values and pair[1] in existing_values})),
            "explicit_relations": len(explicit_relations),
            "explicit_relations_valid": valid_explicit,
            "contradictions": contradictions,
            "dimensions_active": len(self.store.active_dimensions(objective)),
            "dimensions_to_add": dimensions_to_add,
            "coordinates_proposed": len(unique_chars) * (3 + len(AUTO_FEATURES)),
            "object_coverage_percent": round(coverage, 2),
            "relation_reuse_percent": round(reuse, 2),
            "compression_ratio": round(compression, 3),
            "text_digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "commit_allowed": not contradictions,
            "reconciliation": "full-objective-transactional",
        }
        analysis_id = self.store.create_analysis(user_id, objective, filename, str(path), payload)
        return {"analysis_id": analysis_id, **payload}

    def discard(self, analysis_id: str, user_id: int) -> dict:
        row = self.store.analysis(analysis_id, user_id)
        if row is None:
            raise KeyError("Analyse introuvable.")
        if str(row["status"]) != "analyzed":
            raise ValueError("Cette analyse n'est plus supprimable.")
        staging_path = Path(str(row["staging_path"]))
        with self.store.transaction() as connection:
            connection.execute("UPDATE learning_analyses SET status='discarded' WHERE id=?", (analysis_id,))
        staging_path.unlink(missing_ok=True)
        return {"analysis_id": analysis_id, "status": "discarded"}

    def commit(self, analysis_id: str, user_id: int) -> dict:
        row = self.store.analysis(analysis_id, user_id)
        if row is None:
            raise KeyError("Analyse introuvable.")
        if str(row["status"]) != "analyzed":
            raise ValueError("Cette analyse n'est plus validable.")
        if self.store.version() != int(row["base_version"]):
            raise RuntimeError("Le référentiel a changé depuis l'analyse. Recalculez le cycle comparatif.")
        payload = json.loads(str(row["payload_json"]))
        if payload.get("contradictions"):
            raise ValueError("L'analyse contient des contradictions non résolues.")
        content = extract_content(str(row["staging_path"]))
        before = self.store.stats()
        with self.store.transaction() as connection:
            version = self.store.next_version(connection)
            relations_added = [
                self.trainer.add_relation_in_transaction(
                    connection, relation, version, str(row["objective"]), reconcile=False
                )
                for relation in content["relations"]
            ]
            training = self.trainer._add_line_and_reconcile(
                connection, content["text"], str(row["objective"]), str(row["filename"]),
                user_id, version, int(payload.get("file", {}).get("bytes", 0)),
            )
            connection.execute(
                "UPDATE learning_analyses SET status='committed',committed_at=CURRENT_TIMESTAMP WHERE id=?",
                (analysis_id,),
            )
            self.store.journal(connection, version, "learning_commit", {
                "analysis_id": analysis_id, "user_id": user_id,
                "relations": relations_added, "training": training,
            })
        after = self.store.stats()
        return {
            "analysis_id": analysis_id,
            "version_before": before["version"],
            "version_after": after["version"],
            "objects_added": after["objects"] - before["objects"],
            "dimensions_added": after["dimensions"] - before["dimensions"],
            "coordinates_added": after["coordinates"] - before["coordinates"],
            "relation_rules_added": after["relation_rules"] - before["relation_rules"],
            "patterns_added": 0,
            "relations_added": len(relations_added),
            "training": training,
            "stats": after,
        }
