from __future__ import annotations

import random
import unittest
from fractions import Fraction

from ananke_core.three_body import (
    RelationalThreeBodyPredictor,
    ThreeBodyParameters,
    ThreeBodyState,
    all_transition_audits_hold,
    decode_relational_frame,
    encode_relational_frame,
    max_absolute_error,
    seed_next_state,
    states_equal,
    transition_audit,
    verlet_forward,
)


class ThreeBodyRelational(unittest.TestCase):
    def setUp(self):
        self.parameters = ThreeBodyParameters(
            masses=(Fraction(2), Fraction(3), Fraction(5)),
            gravitational_constant=Fraction(1, 40),
            dt=Fraction(1, 10),
        )
        self.s0 = ThreeBodyState.from_values((-9, 1, 12))
        self.s1 = seed_next_state(
            self.s0,
            (Fraction(1, 20), Fraction(-1, 25), Fraction(1, 50)),
            self.parameters,
        )
        self.s2 = verlet_forward(self.s0, self.s1, self.parameters)
        self.s3 = verlet_forward(self.s1, self.s2, self.parameters)

    def test_frame_is_exactly_reconstructible(self):
        frame = encode_relational_frame(self.s1, self.parameters)
        self.assertEqual(decode_relational_frame(frame, self.parameters), self.s1)

    def test_distributive_gravity_relation_closes(self):
        audit = transition_audit(self.s1, self.s2)
        self.assertTrue(audit.holds)
        self.assertTrue(all(pair.temporal_power_closure.epsilon == 0 for pair in audit.pairs))

    def test_forward_and_backward_from_two_states_are_exact(self):
        predictor = RelationalThreeBodyPredictor(self.parameters)
        f1 = predictor.encode(self.s1)
        f2 = predictor.encode(self.s2)
        predicted_s3 = predictor.decode(predictor.predict_next(f1, f2))
        predicted_s0 = predictor.decode(predictor.predict_previous(f1, f2))
        self.assertEqual(predicted_s3, self.s3)
        self.assertEqual(predicted_s0, self.s0)

    def test_ratio_only_is_not_the_gravitational_law(self):
        predictor = RelationalThreeBodyPredictor(self.parameters)
        f1 = predictor.encode(self.s1)
        f2 = predictor.encode(self.s2)
        ratio_prediction = predictor.decode(predictor.ratio_only_next(f1, f2))
        self.assertGreater(max_absolute_error(ratio_prediction, self.s3), 0)

    def test_exact_round_trip(self):
        predictor = RelationalThreeBodyPredictor(self.parameters)
        states = [self.s0, self.s1]
        for _ in range(2):
            states.append(verlet_forward(states[-2], states[-1], self.parameters))
        self.assertTrue(all_transition_audits_hold(states))

        current_frame = predictor.encode(states[-2])
        following_frame = predictor.encode(states[-1])
        recovered = [states[-1], states[-2]]
        for _ in range(len(states) - 2):
            previous_frame = predictor.predict_previous(current_frame, following_frame)
            previous = predictor.decode(previous_frame)
            recovered.append(previous)
            following_frame, current_frame = current_frame, previous_frame
        self.assertEqual(list(reversed(recovered)), states)

    def test_random_short_sequences(self):
        rng = random.Random(73421)
        successes = 0
        attempts = 0
        while successes < 6 and attempts < 150:
            attempts += 1
            masses = tuple(Fraction(rng.randint(1, 7)) for _ in range(3))
            x0 = Fraction(rng.randint(-18, -10))
            x1 = x0 + rng.randint(5, 9)
            x2 = x1 + rng.randint(5, 9)
            parameters = ThreeBodyParameters(
                masses=masses,  # type: ignore[arg-type]
                gravitational_constant=Fraction(1, rng.randint(35, 80)),
                dt=Fraction(1, rng.randint(8, 16)),
            )
            initial = ThreeBodyState((x0, x1, x2))
            velocities = tuple(Fraction(rng.randint(-4, 4), rng.randint(30, 80)) for _ in range(3))
            try:
                first = seed_next_state(initial, velocities, parameters)
                second = verlet_forward(initial, first, parameters)
                third = verlet_forward(first, second, parameters)
                frames = [encode_relational_frame(item, parameters) for item in (initial, first, second, third)]
                if len({frame.order for frame in frames}) != 1:
                    continue
                predictor = RelationalThreeBodyPredictor(parameters)
                self.assertTrue(states_equal(predictor.decode(predictor.predict_next(frames[1], frames[2])), third))
                self.assertTrue(states_equal(predictor.decode(predictor.predict_previous(frames[1], frames[2])), initial))
                self.assertTrue(transition_audit(first, second).holds)
                successes += 1
            except (ZeroDivisionError, ValueError):
                continue
        self.assertEqual(successes, 6)


if __name__ == "__main__":
    unittest.main()
