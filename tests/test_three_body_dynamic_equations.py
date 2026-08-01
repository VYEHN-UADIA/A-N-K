from __future__ import annotations

import random
import unittest
from fractions import Fraction

from ananke_core.three_body import (
    ThreeBodyParameters,
    ThreeBodyState,
    advance_dynamic_equation,
    derive_dynamic_equation,
    encode_relational_frame,
    retrodict_dynamic_equation,
    seed_next_state,
    verlet_forward,
)


class ThreeBodyDynamicEquations(unittest.TestCase):
    def setUp(self):
        self.parameters = ThreeBodyParameters(
            masses=(Fraction(2), Fraction(3), Fraction(5)),
            gravitational_constant=Fraction(1, 50),
            dt=Fraction(1, 10),
        )
        self.state0 = ThreeBodyState.from_values((-9, 1, 12))
        self.state1 = seed_next_state(
            self.state0,
            (Fraction(1, 20), Fraction(-1, 30), Fraction(1, 40)),
            self.parameters,
        )

    def test_equation_is_regenerated(self):
        frame0 = encode_relational_frame(self.state0, self.parameters)
        frame1 = encode_relational_frame(self.state1, self.parameters)
        equation1 = derive_dynamic_equation(frame0, frame1, self.parameters)
        equation2 = advance_dynamic_equation(equation1, self.parameters)
        self.assertTrue(equation1.holds)
        self.assertTrue(equation2.holds)
        self.assertEqual(equation1.generated_ratios, equation2.observed_ratios)
        self.assertNotEqual(equation1.signature(), equation2.signature())

    def test_matches_discrete_reference(self):
        state2 = verlet_forward(self.state0, self.state1, self.parameters)
        frame0 = encode_relational_frame(self.state0, self.parameters)
        frame1 = encode_relational_frame(self.state1, self.parameters)
        equation1 = derive_dynamic_equation(frame0, frame1, self.parameters)
        self.assertEqual(
            equation1.following,
            encode_relational_frame(state2, self.parameters),
        )

    def test_backward_reconstructs_previous_equation(self):
        frame0 = encode_relational_frame(self.state0, self.parameters)
        frame1 = encode_relational_frame(self.state1, self.parameters)
        equation1 = derive_dynamic_equation(frame0, frame1, self.parameters)
        recovered = retrodict_dynamic_equation(frame1, equation1.following, self.parameters)
        self.assertEqual(recovered.previous, frame0)
        self.assertEqual(recovered.current, frame1)
        self.assertEqual(recovered.following, equation1.following)

    def test_random_equation_chains(self):
        rng = random.Random(19071987)
        accepted = 0
        attempts = 0
        while accepted < 12 and attempts < 500:
            attempts += 1
            parameters = ThreeBodyParameters(
                masses=tuple(Fraction(rng.randint(1, 9)) for _ in range(3)),  # type: ignore[arg-type]
                gravitational_constant=Fraction(1, rng.randint(500, 1500)),
                dt=Fraction(1, rng.randint(30, 70)),
            )
            first = Fraction(rng.randint(-30, -15))
            second = first + rng.randint(7, 14)
            third = second + rng.randint(7, 14)
            state0 = ThreeBodyState((first, second, third))
            velocity = tuple(Fraction(rng.randint(-5, 5), rng.randint(40, 120)) for _ in range(3))
            try:
                state1 = seed_next_state(state0, velocity, parameters)
                frame0 = encode_relational_frame(state0, parameters)
                frame1 = encode_relational_frame(state1, parameters)
                equation = derive_dynamic_equation(frame0, frame1, parameters)
                signatures = [equation.signature()]
                for _ in range(2):
                    self.assertTrue(equation.holds)
                    next_equation = advance_dynamic_equation(equation, parameters)
                    self.assertEqual(equation.generated_ratios, next_equation.observed_ratios)
                    signatures.append(next_equation.signature())
                    equation = next_equation
                self.assertGreater(len(set(signatures)), 1)
                recovered = retrodict_dynamic_equation(equation.current, equation.following, parameters)
                self.assertEqual(recovered.previous, equation.previous)
                accepted += 1
            except (ValueError, ZeroDivisionError, ArithmeticError):
                continue
        self.assertEqual(accepted, 12)


if __name__ == "__main__":
    unittest.main()
