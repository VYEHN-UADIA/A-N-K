#!/usr/bin/env python3
"""Validation externe du module ANANKÉ-3 corps contre l'ODE newtonienne.

La référence est un RK4 Decimal fortement sous-échantillonné. ANANKÉ ne reçoit
que deux positions consécutives, les masses, G et dt. Les erreurs ne sont donc
plus nulles : elles mesurent l'écart entre la fermeture discrète Verlet et la
solution continue de référence.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ananke_core.three_body import (  # noqa: E402
    RelationalThreeBodyPredictor,
    ThreeBodyParameters,
    ThreeBodyState,
)

getcontext().prec = 50

D = Decimal


def acceleration(position, masses, gravitational_constant):
    result = [D(0), D(0), D(0)]
    for i in range(3):
        for j in range(3):
            if i == j:
                continue
            difference = position[j] - position[i]
            if difference == 0:
                raise ZeroDivisionError("collision")
            direction = D(1) if difference > 0 else D(-1)
            result[i] += gravitational_constant * masses[j] * direction / (abs(difference) ** 2)
    return tuple(result)


def derivative(position, velocity, masses, gravitational_constant):
    return tuple(velocity), acceleration(position, masses, gravitational_constant)


def add_scaled(values, increments, scale):
    return tuple(value + scale * increment for value, increment in zip(values, increments))


def rk4_step(position, velocity, masses, gravitational_constant, step):
    k1x, k1v = derivative(position, velocity, masses, gravitational_constant)
    k2x, k2v = derivative(
        add_scaled(position, k1x, step / 2),
        add_scaled(velocity, k1v, step / 2),
        masses,
        gravitational_constant,
    )
    k3x, k3v = derivative(
        add_scaled(position, k2x, step / 2),
        add_scaled(velocity, k2v, step / 2),
        masses,
        gravitational_constant,
    )
    k4x, k4v = derivative(
        add_scaled(position, k3x, step),
        add_scaled(velocity, k3v, step),
        masses,
        gravitational_constant,
    )
    next_position = tuple(
        value + step * (a + 2*b + 2*c + d) / 6
        for value, a, b, c, d in zip(position, k1x, k2x, k3x, k4x)
    )
    next_velocity = tuple(
        value + step * (a + 2*b + 2*c + d) / 6
        for value, a, b, c, d in zip(velocity, k1v, k2v, k3v, k4v)
    )
    return next_position, next_velocity


def integrate_interval(position, velocity, masses, gravitational_constant, interval, substeps):
    step = interval / substeps
    for _ in range(substeps):
        position, velocity = rk4_step(position, velocity, masses, gravitational_constant, step)
    return position, velocity


def to_fraction(value: Decimal) -> Fraction:
    return Fraction(str(value))


def to_state(position) -> ThreeBodyState:
    return ThreeBodyState(tuple(to_fraction(value) for value in position))  # type: ignore[arg-type]


def fraction_to_decimal(value: Fraction) -> Decimal:
    return D(value.numerator) / D(value.denominator)


def state_error(predicted: ThreeBodyState, reference) -> Decimal:
    return max(
        abs(fraction_to_decimal(value) - target)
        for value, target in zip(predicted.positions, reference)
    )


def one_case(rng, dt: Fraction, substeps: int):
    masses_i = tuple(rng.randint(1, 9) for _ in range(3))
    masses_d = tuple(D(value) for value in masses_i)
    masses_f = tuple(Fraction(value) for value in masses_i)
    first = D(rng.randint(-25, -12))
    second = first + D(rng.randint(6, 12))
    third = second + D(rng.randint(6, 12))
    position = (first, second, third)
    velocity = tuple(D(rng.randint(-5, 5)) / D(rng.randint(30, 100)) for _ in range(3))
    g_fraction = Fraction(1, rng.randint(30, 90))
    g_decimal = D(g_fraction.numerator) / D(g_fraction.denominator)
    dt_decimal = D(dt.numerator) / D(dt.denominator)

    positions = [position]
    current_position, current_velocity = position, velocity
    for _ in range(3):
        current_position, current_velocity = integrate_interval(
            current_position, current_velocity, masses_d, g_decimal, dt_decimal, substeps
        )
        positions.append(current_position)

    if any(
        not (positions[k][0] < positions[k][1] < positions[k][2])
        for k in range(4)
    ):
        raise ValueError("ordre changé")

    parameters = ThreeBodyParameters(masses=masses_f, gravitational_constant=g_fraction, dt=dt)
    predictor = RelationalThreeBodyPredictor(parameters)
    state1, state2 = to_state(positions[1]), to_state(positions[2])
    frame1, frame2 = predictor.encode(state1), predictor.encode(state2)
    predicted3 = predictor.decode(predictor.predict_next(frame1, frame2))
    predicted0 = predictor.decode(predictor.predict_previous(frame1, frame2))
    ratio3 = predictor.decode(predictor.ratio_only_next(frame1, frame2))
    ratio0 = predictor.decode(predictor.ratio_only_previous(frame1, frame2))

    return {
        "physics_forward": state_error(predicted3, positions[3]),
        "physics_backward": state_error(predicted0, positions[0]),
        "ratio_forward": state_error(ratio3, positions[3]),
        "ratio_backward": state_error(ratio0, positions[0]),
    }


def summarize(values):
    ordered = sorted(values)
    return {
        "mean": format(sum(values, D(0)) / len(values), ".12E"),
        "median": format(ordered[len(ordered)//2], ".12E"),
        "max": format(max(values), ".12E"),
    }


def run(seed: int, trials: int, substeps: int):
    rng = random.Random(seed)
    report = {}
    for dt in (Fraction(1, 10), Fraction(1, 20), Fraction(1, 40)):
        metrics = {name: [] for name in ("physics_forward", "physics_backward", "ratio_forward", "ratio_backward")}
        accepted = 0
        attempts = 0
        while accepted < trials and attempts < trials * 20:
            attempts += 1
            try:
                result = one_case(rng, dt, substeps)
            except (ValueError, ZeroDivisionError):
                continue
            for name, value in result.items():
                metrics[name].append(value)
            accepted += 1
        report[f"dt={dt.numerator}/{dt.denominator}"] = {
            "accepted": accepted,
            "metrics_max_position_error": {name: summarize(values) for name, values in metrics.items()},
            "physics_vs_ratio_mean_gain_forward": format(
                (sum(metrics["ratio_forward"], D(0)) / sum(metrics["physics_forward"], D(0))), ".6E"
            ),
            "physics_vs_ratio_mean_gain_backward": format(
                (sum(metrics["ratio_backward"], D(0)) / sum(metrics["physics_backward"], D(0))), ".6E"
            ),
        }
    return {
        "experiment": "ANANKE three-body continuous-reference validation",
        "reference": f"Decimal RK4, {substeps} substeps per observed interval",
        "seed": seed,
        "trials_per_dt": trials,
        "results": report,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=161803)
    parser.add_argument("--trials", type=int, default=40)
    parser.add_argument("--substeps", type=int, default=160)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run(args.seed, args.trials, args.substeps)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
