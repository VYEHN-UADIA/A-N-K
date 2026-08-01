from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from ananke_core.engine import AnankeEngine
from ananke_core.coordinates import object_kind
from ananke_core.signature import trajectory_signature

DIST = Path(__file__).resolve().parents[1]

class Consolidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "s.sqlite3"
    def tearDown(self):
        self.temp.cleanup()

    def test_delivered_state_covers_corpus(self):
        # L'artefact livré doit être cohérent : tout caractère du corpus est un objet.
        state = DIST / "state" / "ananke.sqlite3"
        corpus = DIST / "corpus" / "bootstrap_fr.txt"
        if not state.exists() or not corpus.exists():
            self.skipTest("état ou corpus absent")
        engine = AnankeEngine(state, read_only=True)
        try:
            text = corpus.read_text(encoding="utf-8")
            missing = sorted({c for c in set(text) if engine.store.object_id(c, object_kind(c)) is None})
            self.assertEqual(missing, [], f"caractères du corpus absents du référentiel: {missing}")
        finally:
            engine.close()

    def test_power_hash_off_in_measured_regime(self):
        # Sans loi, aucune homologie de puissance : trajectory_power_hash doit être vide.
        engine = AnankeEngine(self.state)
        f = self.root / "c.txt"; f.write_text("Je suis là. Tu es là.\n", encoding="utf-8")
        engine.trainer.train_file(f, "general")
        hashes = {r[0] for r in engine.store._connection.execute(
            "SELECT DISTINCT trajectory_power_hash FROM relation_rules WHERE objective='general'")}
        engine.close()
        self.assertEqual(hashes, {""}, f"power_hash non vide en régime mesuré: {hashes}")

    def test_power_gating_switches_with_relations(self):
        # Dès qu'une loi existe, l'inférence bascule sur les dimensions relationnelles,
        # et celles-ci sont exactement les dimensions d'homologie de puissance.
        engine = AnankeEngine(self.state)
        with engine.store.transaction() as cx:
            v = engine.store.next_version(cx)
            engine.trainer.add_relation_in_transaction(cx, {
                "source": "je", "target": "suis", "dimension": "loi/x", "factor": "2", "logic": "general",
            }, v, "general", reconcile=False)
        dims = engine.store.inference_dimensions("general")
        power = engine.store.relation_dimensions(dims)
        engine.close()
        self.assertTrue(dims and power == dims, f"dims={dims} power={power}")

    def test_trajectory_is_order_sensitive(self):
        # cf ≠ fc : l'appariement exact préserve l'ordre.
        engine = AnankeEngine(self.state)
        f = self.root / "c.txt"; f.write_text("abcabc abcabc\n", encoding="utf-8")
        engine.trainer.train_file(f, "general")
        s = engine.store
        a, b, c = (s.object_id("a", "letter"), s.object_id("b", "letter"), s.object_id("c", "letter"))
        dims = s.inference_dimensions("general")
        h1 = trajectory_signature(s, [a, b, c], dims)[0]
        h2 = trajectory_signature(s, [c, b, a], dims)[0]
        engine.close()
        self.assertNotEqual(h1, h2, "ordre non discriminé (commutativité indésirable)")

if __name__ == "__main__":
    unittest.main()
