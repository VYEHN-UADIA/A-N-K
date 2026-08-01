#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ananke_core.three_body import (  # noqa: E402
    RelationalThreeBodyPredictor,
    ThreeBodyParameters,
    ThreeBodyState,
    max_absolute_error,
    seed_next_state,
    transition_audit,
    verlet_forward,
)


def encoded(value: Fraction) -> str:
    # Les fractions exactes peuvent grossir très vite sous gravitation itérée.
    # On conserve la forme exacte tant qu'elle reste lisible, sinon une vue
    # scientifique bornée ; les comparaisons d'égalité restent, elles, exactes.
    if value.numerator.bit_length() <= 384 and value.denominator.bit_length() <= 384:
        return f"{value.numerator}/{value.denominator}"
    return f"~{float(value):.12e} [fraction_bits={value.numerator.bit_length()}/{value.denominator.bit_length()}]"


def state_payload(state: ThreeBodyState) -> list[str]:
    return [encoded(value) for value in state.positions]


def generate_case(rng: random.Random):
    for _ in range(1000):
        masses = tuple(Fraction(rng.randint(1, 9)) for _ in range(3))
        first = Fraction(rng.randint(-25, -12))
        second = first + rng.randint(6, 12)
        third = second + rng.randint(6, 12)
        parameters = ThreeBodyParameters(
            masses=masses,  # type: ignore[arg-type]
            gravitational_constant=Fraction(1, rng.randint(30, 90)),
            dt=Fraction(1, rng.randint(8, 18)),
        )
        initial = ThreeBodyState((first, second, third))
        velocities = tuple(Fraction(rng.randint(-5, 5), rng.randint(30, 100)) for _ in range(3))
        try:
            state1 = seed_next_state(initial, velocities, parameters)
            state2 = verlet_forward(initial, state1, parameters)
            state3 = verlet_forward(state1, state2, parameters)
            frames = [
                RelationalThreeBodyPredictor(parameters).encode(item)
                for item in (initial, state1, state2, state3)
            ]
            if len({frame.order for frame in frames}) != 1:
                continue
            return parameters, velocities, (initial, state1, state2, state3)
        except (ZeroDivisionError, ValueError):
            continue
    raise RuntimeError("Impossible de générer un cas non collisionnel stable.")


def run(seed: int, trials: int) -> dict:
    rng = random.Random(seed)
    forward_exact = 0
    backward_exact = 0
    closure_exact = 0
    ratio_forward_exact = 0
    ratio_backward_exact = 0
    two_step_forward_exact = 0
    two_step_round_trip_exact = 0
    ratio_forward_errors: list[Fraction] = []
    ratio_backward_errors: list[Fraction] = []
    example = None

    for trial in range(trials):
        parameters, velocities, states = generate_case(rng)
        state0, state1, state2, state3 = states
        predictor = RelationalThreeBodyPredictor(parameters)
        frame0, frame1, frame2, frame3 = [predictor.encode(state) for state in states]

        predicted3 = predictor.decode(predictor.predict_next(frame1, frame2))
        predicted0 = predictor.decode(predictor.predict_previous(frame1, frame2))
        ratio3 = predictor.decode(predictor.ratio_only_next(frame1, frame2))
        ratio0 = predictor.decode(predictor.ratio_only_previous(frame1, frame2))

        # Deux pas consécutifs à partir du seul socle S0,S1, puis retour exact.
        generated_frame2 = predictor.predict_next(frame0, frame1)
        generated_frame3 = predictor.predict_next(frame1, generated_frame2)
        recovered_frame1 = predictor.predict_previous(generated_frame2, generated_frame3)
        recovered_frame0 = predictor.predict_previous(recovered_frame1, generated_frame2)

        forward_error = max_absolute_error(predicted3, state3)
        backward_error = max_absolute_error(predicted0, state0)
        ratio_forward_error = max_absolute_error(ratio3, state3)
        ratio_backward_error = max_absolute_error(ratio0, state0)

        forward_exact += int(forward_error == 0)
        backward_exact += int(backward_error == 0)
        closure_exact += int(transition_audit(state1, state2).holds)
        ratio_forward_exact += int(ratio_forward_error == 0)
        ratio_backward_exact += int(ratio_backward_error == 0)
        two_step_forward_exact += int(
            predictor.decode(generated_frame2) == state2
            and predictor.decode(generated_frame3) == state3
        )
        two_step_round_trip_exact += int(
            predictor.decode(recovered_frame1) == state1
            and predictor.decode(recovered_frame0) == state0
        )
        ratio_forward_errors.append(ratio_forward_error)
        ratio_backward_errors.append(ratio_backward_error)

        if trial == 0:
            example = {
                "masses": [encoded(value) for value in parameters.masses],
                "G": encoded(parameters.gravitational_constant),
                "dt": encoded(parameters.dt),
                "initial_velocities": [encoded(value) for value in velocities],
                "S_n_minus_1": state_payload(state0),
                "S_n": state_payload(state1),
                "S_n_plus_1": state_payload(state2),
                "reference_S_n_plus_2": state_payload(state3),
                "ananke_physics_S_n_plus_2": state_payload(predicted3),
                "ananke_reconstructed_S_n_minus_1": state_payload(predicted0),
                "ratio_only_S_n_plus_2": state_payload(ratio3),
                "physics_forward_error": encoded(forward_error),
                "physics_backward_error": encoded(backward_error),
                "ratio_only_forward_error": encoded(ratio_forward_error),
                "relation_closure": transition_audit(state1, state2).holds,
            }

    average_ratio_forward = sum(ratio_forward_errors, Fraction(0)) / trials
    average_ratio_backward = sum(ratio_backward_errors, Fraction(0)) / trials
    return {
        "experiment": "ANANKE three-body exact relational benchmark",
        "regime": "three collinear bodies, rational exact arithmetic, no collision",
        "seed": seed,
        "trials": trials,
        "results": {
            "physics_closed_forward_exact": forward_exact,
            "physics_closed_backward_exact": backward_exact,
            "distributive_relation_closure_exact": closure_exact,
            "ratio_only_forward_exact": ratio_forward_exact,
            "ratio_only_backward_exact": ratio_backward_exact,
            "physics_closed_two_step_forward_exact": two_step_forward_exact,
            "physics_closed_two_step_round_trip_exact": two_step_round_trip_exact,
            "ratio_only_forward_mean_abs_error": encoded(average_ratio_forward),
            "ratio_only_backward_mean_abs_error": encoded(average_ratio_backward),
            "ratio_only_forward_max_abs_error": encoded(max(ratio_forward_errors)),
            "ratio_only_backward_max_abs_error": encoded(max(ratio_backward_errors)),
        },
        "example": example,
        "interpretation": {
            "works": "La génération et la rétrodiction sont exactes lorsque la fermeture newtonienne est une loi interne.",
            "does_not_work": "La répétition du seul rapport n→n+1 n'est pas une loi suffisante pour une dynamique accélérée.",
            "scope": "Ce résultat valide le socle relationnel réversible en 1D rationnelle ; il ne prouve pas encore le cas spatial générique irrationnel/algébrique.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run(args.seed, args.trials)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
