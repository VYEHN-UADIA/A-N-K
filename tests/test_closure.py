from __future__ import annotations

import dataclasses
import unittest
from fractions import Fraction

from ananke_core.distributive import (
    ClosureCoordinate, closure_epsilon, closure_of_step,
    cell_closure, cell_holds, combine_holds, scalar_defect, admits_step,
    memory_cell, MemoryCell,
)


class Closure(unittest.TestCase):
    def test_residual_and_holds(self):
        t = closure_epsilon(1, 1)
        self.assertTrue(t.holds); self.assertEqual(t.epsilon, 0)
        f = closure_epsilon(1, 2)
        self.assertFalse(f.holds); self.assertEqual(f.epsilon, Fraction(-1))

    def test_epsilon_measures_the_gap(self):
        self.assertEqual(abs(closure_epsilon(1, 2).epsilon), 1)
        self.assertEqual(abs(closure_epsilon(5, 12).epsilon), 7)

    def test_zero_is_allowed_here(self):
        self.assertEqual(closure_epsilon(4, 4).epsilon, 0)

    def test_truth_is_derived_never_stored(self):
        # Point 3 : aucun état impossible (ε=0, faux) n'est représentable.
        names = {f.name for f in dataclasses.fields(ClosureCoordinate)}
        self.assertEqual(names, {"epsilon", "label"})
        self.assertNotIn("truth", names)
        self.assertEqual(ClosureCoordinate(Fraction(0)).truth, 1)
        self.assertEqual(ClosureCoordinate(Fraction(3)).truth, 0)

    def test_step_assertion_and_generation_guard(self):
        self.assertTrue(admits_step(3, 1, 3, 37))
        self.assertFalse(admits_step(3, 1, 3, 38))
        self.assertEqual(closure_of_step(3, 1, 3, 38).epsilon, Fraction(-1))

    def test_cell_closure_all_zero_when_true(self):
        gamma = cell_closure(memory_cell("v", 3, 1, 3))
        self.assertTrue(all(component.holds for component in gamma))
        self.assertTrue(cell_holds(memory_cell("v", 3, 1, 3)))

    def test_cell_closure_detects_delta_falsification(self):
        bad = MemoryCell("v", Fraction(3), Fraction(1), 3, Fraction(38), Fraction(64, 27))
        e_delta, e_ratio, e_bridge = cell_closure(bad)
        self.assertEqual(e_delta.epsilon, Fraction(1))   # (27+38)-64
        self.assertFalse(cell_holds(bad))

    def test_cell_closure_detects_ratio_only_falsification(self):
        # LE test absent en v3.3.3 : Δ correct, ρ falsifié seul → doit être détecté.
        bad = MemoryCell("v", Fraction(3), Fraction(1), 3, Fraction(37), Fraction(65, 27))
        e_delta, e_ratio, e_bridge = cell_closure(bad)
        self.assertTrue(e_delta.holds)                    # ε_Δ = 0 (Δ correct)
        self.assertEqual(e_ratio.epsilon, Fraction(1))    # ε_ρ = 27·65/27 - 64 = 1
        self.assertEqual(e_bridge.epsilon, Fraction(-1, 27))  # 64/27 - 65/27
        self.assertFalse(cell_holds(bad))                 # détecté (échouait en v3.3.3)

    def test_composition_is_vector_not_blind_sum(self):
        good = [closure_epsilon(2, 2), closure_epsilon(5, 5)]
        self.assertTrue(combine_holds(good))
        mixed = [closure_epsilon(2, 2), closure_epsilon(1, 3)]
        self.assertFalse(combine_holds(mixed))
        self.assertEqual(scalar_defect(mixed), 2)  # métrique optionnelle, résidus homogènes


if __name__ == "__main__":
    unittest.main()
