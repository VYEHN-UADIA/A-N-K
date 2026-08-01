from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ananke_core.engine import AnankeEngine
from ananke_core.runtime import execute


class AnankeV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "ananke.sqlite3"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _relation(self, engine: AnankeEngine, source: str, target: str, factor: str) -> None:
        with engine.store.transaction() as connection:
            version = engine.store.next_version(connection)
            engine.trainer.add_relation_in_transaction(connection, {
                "source": source,
                "target": target,
                "dimension": "logic/analogy",
                "factor": factor,
                "logic": "analogy",
            }, version, "analogy", reconcile=False)

    def test_relational_induction_without_seen_target_line(self) -> None:
        engine = AnankeEngine(self.state)
        try:
            # Une seule ligne est apprise : ab → x. La ligne cd → y n'est jamais fournie.
            for source, target, factor in (
                ("a", "b", "2"), ("c", "d", "2"),
                ("b", "x", "3"), ("d", "y", "3"),
                ("a", "c", "5"),
            ):
                self._relation(engine, source, target, factor)
            corpus = self.root / "corpus.txt"
            corpus.write_text("abx\n", encoding="utf-8")
            engine.trainer.train_file(corpus, "analogy")
        finally:
            engine.close()

        result = execute(self.state, {
            "action": "infer", "prompt": "cd", "objective": "analogy", "max_characters": 1,
        })
        self.assertEqual(result["output"], "y")
        self.assertEqual(result["generator"], "relation-to-position-to-character")

    def test_inference_is_physically_read_only(self) -> None:
        engine = AnankeEngine(self.state)
        corpus = self.root / "corpus.txt"
        corpus.write_text("Je suis là.\n", encoding="utf-8")
        engine.trainer.train_file(corpus, "general")
        before = engine.stats()["objects"]
        engine.close()
        result = execute(self.state, {"action": "infer", "prompt": "ΩΩ", "objective": "general"})
        self.assertTrue(result["abstained"])
        connection = sqlite3.connect(self.state)
        after = connection.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
        connection.close()
        self.assertEqual(before, after)

    def test_rules_never_store_next_object_identity(self) -> None:
        engine = AnankeEngine(self.state)
        engine.close()
        connection = sqlite3.connect(self.state)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(relation_rules)")}
        connection.close()
        self.assertNotIn("next_object_id", columns)
        self.assertIn("next_relation_json", columns)

    def test_base_coordinates_are_measured_not_hashed(self) -> None:
        engine = AnankeEngine(self.state)
        corpus = self.root / "corpus.txt"
        corpus.write_text("aaaaab\n", encoding="utf-8")
        engine.trainer.train_file(corpus, "general")
        rows = engine.store._connection.execute(
            """SELECT d.address,c.source,c.value FROM coordinates c JOIN dimensions d ON d.id=c.dimension_id
               WHERE d.address IN ('x','y','z')"""
        ).fetchall()
        engine.close()
        self.assertTrue(rows)
        self.assertTrue(all(row["source"] == "measured-corpus" for row in rows))

    def test_relation_dimension_is_activated_as_relation(self) -> None:
        engine = AnankeEngine(self.state)
        self._relation(engine, "a", "b", "2")
        row = engine.store._connection.execute(
            "SELECT kind FROM dimensions WHERE address='logic/analogy'"
        ).fetchone()
        engine.close()
        self.assertEqual(row[0], "relation")

    def test_contradictory_cycle_rolls_back(self) -> None:
        engine = AnankeEngine(self.state)
        self._relation(engine, "a", "b", "2")
        self._relation(engine, "b", "c", "3")
        version_before = engine.store.version()
        with self.assertRaises(ValueError):
            self._relation(engine, "a", "c", "5")
        self.assertEqual(engine.store.version(), version_before)
        engine.close()


if __name__ == "__main__":
    unittest.main()
