from __future__ import annotations

import tempfile, unittest
from fractions import Fraction
from pathlib import Path

from ananke_core.distributive import (
    distributive_coordinate, distributive_expansion, binomial_row,
    close_ratio, close_delta, close_coefficient, close_step, close_degree,
    memory_cell, recall_masked, chain_state, associates,
)
from ananke_core.engine import AnankeEngine


class Distributive(unittest.TestCase):
    def test_coordinate_3_to_4_volume(self):
        c = distributive_coordinate(Fraction(3), Fraction(1), 3)
        self.assertEqual((c.source_power, c.target_power, c.delta, c.ratio),
                         (27, 64, 37, Fraction(64, 27)))

    def test_ratio_depends_on_degree(self):
        self.assertEqual(distributive_coordinate(3, 1, 1).ratio, Fraction(4, 3))
        self.assertEqual(distributive_coordinate(3, 1, 2).ratio, Fraction(16, 9))
        self.assertEqual(distributive_coordinate(3, 1, 3).ratio, Fraction(64, 27))

    def test_expansion_sums_to_delta(self):
        for x, h, n in [(3, 1, 3), (5, 2, 4), (7, Fraction(1, 2), 2)]:
            terms = distributive_expansion(x, h, n)
            self.assertEqual(sum(v for _, v in terms), distributive_coordinate(x, h, n).delta)

    def test_pascal_rows(self):
        self.assertEqual(binomial_row(3), (1, 3, 3, 1))
        self.assertEqual(binomial_row(6), (1, 6, 15, 20, 15, 6, 1))  # au-delà des constantes

    def test_closure_delta_ratio_roundtrip(self):
        c = distributive_coordinate(3, 1, 3)
        self.assertEqual(close_ratio(3, 3, c.delta), c.ratio)
        self.assertEqual(close_delta(3, 3, c.ratio), c.delta)

    def test_close_coefficient_rational(self):
        # ΔV = κ·Δ_n avec κ rationnel exact ⇒ κ reconstruit exactement.
        kappa = Fraction(7, 2)
        delta_absolute = kappa * distributive_coordinate(3, 1, 3).delta  # = 7/2 · 37
        self.assertEqual(close_coefficient(delta_absolute, 3, 1, 3), kappa)

    def test_close_step_exact_and_abstains(self):
        self.assertEqual(close_step(3, 3, 37), Fraction(1))   # 27+37=64=4^3
        self.assertIsNone(close_step(3, 3, 38))               # 65 non cube parfait → ⊥

    def test_close_degree_unique_and_abstains(self):
        self.assertEqual(close_degree(3, 1, Fraction(64, 27), [1, 2, 3, 4]), 3)
        self.assertIsNone(close_degree(3, 1, Fraction(64, 27), [1, 2]))  # 3 non autorisé → ⊥
        self.assertIsNone(close_degree(3, 0, Fraction(1), [1, 2, 3]))    # q=1 → ambigu → ⊥

    def test_memory_cell_integrity(self):
        cell = memory_cell("v", 3, 1, 3)
        self.assertTrue(cell.is_coherent())
        tampered = cell.__class__(cell.identity, cell.x, cell.h, cell.degree, Fraction(38), cell.ratio)
        self.assertFalse(tampered.is_coherent())  # checksum relationnel détecte l'altération

    def test_recall_masked(self):
        self.assertEqual(recall_masked(3, 3, delta=37)["ratio"], Fraction(64, 27))
        self.assertEqual(recall_masked(3, 3, ratio=Fraction(64, 27))["delta"], 37)
        self.assertIsNone(recall_masked(3, 3))                          # rien masqué → ⊥
        self.assertIsNone(recall_masked(3, 3, delta=37, ratio=Fraction(64, 27)))  # 2 fournis → ⊥

    def test_chain_two_path_consistency(self):
        # 3 → 4 → 5 en degré 3 ; rappel additif et multiplicatif doivent coïncider.
        c1 = memory_cell("a", 3, 1, 3)
        c2 = memory_cell("b", 4, 1, 3)
        self.assertEqual(chain_state(3, [c1, c2], 3), Fraction(125))   # 5^3
        bad = c2.__class__(c2.identity, c2.x, c2.h, c2.degree, Fraction(60), c2.ratio)
        self.assertIsNone(chain_state(3, [c1, bad], 3))               # incohérence → ⊥

    def test_associative_by_law(self):
        self.assertTrue(associates(memory_cell("a", 3, 1, 1), memory_cell("b", 6, 2, 1)))  # même ρ=4/3
        self.assertFalse(associates(memory_cell("a", 3, 1, 1), memory_cell("b", 3, 1, 2)))

    def test_dormant_outside_linguistic_path(self):
        # L'inférence linguistique ne crée JAMAIS de dimension distributive.
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.sqlite3"
            engine = AnankeEngine(state)
            corpus = Path(tmp) / "c.txt"; corpus.write_text("Je suis là. Tu es là.\n", encoding="utf-8")
            engine.trainer.train_file(corpus, "general")
            count = engine.store._connection.execute(
                "SELECT COUNT(*) FROM dimensions WHERE kind='distributive'").fetchone()[0]
            engine.close()
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
