#!/usr/bin/env python3
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
    DynamicRelationalEquation,
    ThreeBodyParameters,
    ThreeBodyState,
    advance_dynamic_equation,
    decode_relational_frame,
    derive_dynamic_equation,
    encode_relational_frame,
    frozen_equation_forward,
    max_absolute_error,
    retrodict_dynamic_equation,
    seed_next_state,
    verlet_forward,
)

getcontext().prec = 60
D = Decimal


def compact_fraction(value: Fraction) -> str:
    if value.numerator.bit_length() < 220 and value.denominator.bit_length() < 220:
        return f"{value.numerator}/{value.denominator}"
    return f"~{float(value):.12e} [bits={value.numerator.bit_length()}/{value.denominator.bit_length()}]"


def state_payload(state: ThreeBodyState) -> list[str]:
    return [compact_fraction(value) for value in state.positions]


def equation_payload(equation: DynamicRelationalEquation) -> dict:
    return {
        "observed_ratios": [compact_fraction(value) for value in equation.observed_ratios],
        "relative_accelerations": [compact_fraction(value) for value in equation.relative_accelerations],
        "generated_ratios": [compact_fraction(value) for value in equation.generated_ratios],
        "equation_changed": equation.equation_changed,
        "closure": equation.holds,
    }


def generate_exact_case(rng: random.Random):
    for _ in range(3000):
        masses = tuple(Fraction(rng.randint(1, 9)) for _ in range(3))
        first = Fraction(rng.randint(-40, -25))
        second = first + rng.randint(10, 20)
        third = second + rng.randint(10, 20)
        parameters = ThreeBodyParameters(
            masses=masses,  # type: ignore[arg-type]
            gravitational_constant=Fraction(1, rng.randint(500, 2000)),
            dt=Fraction(1, rng.randint(35, 80)),
        )
        state0 = ThreeBodyState((first, second, third))
        velocities = tuple(Fraction(rng.randint(-5, 5), rng.randint(80, 200)) for _ in range(3))
        try:
            state1 = seed_next_state(state0, velocities, parameters)
            frame0 = encode_relational_frame(state0, parameters)
            frame1 = encode_relational_frame(state1, parameters)
            equation = derive_dynamic_equation(frame0, frame1, parameters)
            if not equation.holds:
                continue
            return parameters, velocities, state0, state1, equation
        except (ValueError, ZeroDivisionError, ArithmeticError):
            continue
    raise RuntimeError("Aucun cas exact admissible généré.")


def exact_benchmark(seed: int, trials: int, future_steps: int) -> dict:
    rng = random.Random(seed)
    forward_exact = 0
    backward_exact = 0
    closures_exact = 0
    equation_continuity_exact = 0
    equations_changed = 0
    equation_steps = 0
    frozen_final_exact = 0
    frozen_final_errors: list[Fraction] = []
    example = None

    for trial in range(trials):
        parameters, velocities, state0, state1, first_equation = generate_exact_case(rng)

        # Référence discrète indépendante de l'objet Equation : Verlet direct.
        reference_states = [state0, state1]
        for _ in range(future_steps):
            reference_states.append(verlet_forward(reference_states[-2], reference_states[-1], parameters))

        equation = first_equation
        dynamic_frames = [equation.previous, equation.current, equation.following]
        equation_chain = [equation]
        for _ in range(future_steps - 1):
            next_equation = advance_dynamic_equation(equation, parameters)
            equation_continuity_exact += int(equation.generated_ratios == next_equation.observed_ratios)
            equation_steps += 1
            equations_changed += int(equation.signature() != next_equation.signature())
            equation_chain.append(next_equation)
            dynamic_frames.append(next_equation.following)
            equation = next_equation

        dynamic_states = [decode_relational_frame(frame, parameters) for frame in dynamic_frames]
        forward_ok = dynamic_states == reference_states
        forward_exact += int(forward_ok)
        closures_exact += int(all(item.holds for item in equation_chain))

        # Retour depuis les deux derniers états, en reconstruisant E_{k-1} à chaque pas.
        recovered_frames = [dynamic_frames[-1], dynamic_frames[-2]]
        following = dynamic_frames[-1]
        current = dynamic_frames[-2]
        for _ in range(len(dynamic_frames) - 2):
            recovered_equation = retrodict_dynamic_equation(current, following, parameters)
            previous = recovered_equation.previous
            recovered_frames.append(previous)
            following, current = current, previous
        recovered_frames.reverse()
        backward_ok = recovered_frames == dynamic_frames
        backward_exact += int(backward_ok)

        frozen_frames = frozen_equation_forward(first_equation, future_steps)
        frozen_final = decode_relational_frame(frozen_frames[-1], parameters)
        frozen_error = max_absolute_error(frozen_final, reference_states[-1])
        frozen_final_errors.append(frozen_error)
        frozen_final_exact += int(frozen_error == 0)

        if trial == 0:
            example = {
                "masses": [compact_fraction(value) for value in parameters.masses],
                "G": compact_fraction(parameters.gravitational_constant),
                "dt": compact_fraction(parameters.dt),
                "initial_velocities": [compact_fraction(value) for value in velocities],
                "states": [state_payload(state) for state in reference_states],
                "equations": [equation_payload(item) for item in equation_chain],
                "dynamic_final": state_payload(dynamic_states[-1]),
                "frozen_final": state_payload(frozen_final),
                "frozen_final_error": compact_fraction(frozen_error),
                "forward_exact": forward_ok,
                "backward_exact": backward_ok,
            }

    return {
        "regime": "1D collinear, exact rational arithmetic, stable body order",
        "trials": trials,
        "future_steps_after_S1": future_steps,
        "dynamic_equation_forward_exact": forward_exact,
        "dynamic_equation_backward_exact": backward_exact,
        "all_equation_closures_exact": closures_exact,
        "equation_to_equation_continuity_exact": equation_continuity_exact,
        "equation_transition_count": equation_steps,
        "equation_signature_changed": equations_changed,
        "frozen_equation_final_exact": frozen_final_exact,
        "frozen_equation_mean_final_error": compact_fraction(sum(frozen_final_errors, Fraction(0)) / trials),
        "frozen_equation_max_final_error": compact_fraction(max(frozen_final_errors)),
        "example": example,
    }


# --------------------------------------------------------------------------
# Référence continue indépendante : ODE Newton + RK4 Decimal
# --------------------------------------------------------------------------
def dec_acceleration(position, masses, gravitational_constant):
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


def add_scaled(values, increments, scale):
    return tuple(value + scale * increment for value, increment in zip(values, increments))


def rk4_step(position, velocity, masses, gravitational_constant, step):
    k1x = velocity
    k1v = dec_acceleration(position, masses, gravitational_constant)

    p2 = add_scaled(position, k1x, step / 2)
    v2 = add_scaled(velocity, k1v, step / 2)
    k2x = v2
    k2v = dec_acceleration(p2, masses, gravitational_constant)

    p3 = add_scaled(position, k2x, step / 2)
    v3 = add_scaled(velocity, k2v, step / 2)
    k3x = v3
    k3v = dec_acceleration(p3, masses, gravitational_constant)

    p4 = add_scaled(position, k3x, step)
    v4 = add_scaled(velocity, k3v, step)
    k4x = v4
    k4v = dec_acceleration(p4, masses, gravitational_constant)

    next_position = tuple(
        value + step * (a + 2*b + 2*c + d) / 6
        for value, a, b, c, d in zip(position, k1x, k2x, k3x, k4x)
    )
    next_velocity = tuple(
        value + step * (a + 2*b + 2*c + d) / 6
        for value, a, b, c, d in zip(velocity, k1v, k2v, k3v, k4v)
    )
    return next_position, next_velocity


def integrate(position, velocity, masses, gravitational_constant, interval, substeps):
    step = interval / D(substeps)
    for _ in range(substeps):
        position, velocity = rk4_step(position, velocity, masses, gravitational_constant, step)
    return position, velocity


def decimal_to_state(position) -> ThreeBodyState:
    return ThreeBodyState(tuple(Fraction(str(value)).limit_denominator(10**12) for value in position))  # type: ignore[arg-type]


def fraction_decimal(value: Fraction) -> Decimal:
    return D(value.numerator) / D(value.denominator)


def decimal_state_error(state: ThreeBodyState, reference) -> Decimal:
    return max(abs(fraction_decimal(value) - expected) for value, expected in zip(state.positions, reference))


def continuous_case(rng: random.Random, dt: Fraction, future_steps: int, substeps: int):
    masses_i = tuple(rng.randint(1, 9) for _ in range(3))
    masses_d = tuple(D(value) for value in masses_i)
    masses_f = tuple(Fraction(value) for value in masses_i)
    first = D(rng.randint(-40, -25))
    second = first + D(rng.randint(10, 20))
    third = second + D(rng.randint(10, 20))
    position0 = (first, second, third)
    velocity0 = tuple(D(rng.randint(-5, 5)) / D(rng.randint(80, 200)) for _ in range(3))
    g_fraction = Fraction(1, rng.randint(500, 2000))
    g_decimal = D(g_fraction.numerator) / D(g_fraction.denominator)
    dt_decimal = D(dt.numerator) / D(dt.denominator)

    # Passé indépendant t=-dt.
    past_position, _ = integrate(position0, velocity0, masses_d, g_decimal, -dt_decimal, substeps)

    positions = [position0]
    current_position, current_velocity = position0, velocity0
    for _ in range(future_steps + 1):
        current_position, current_velocity = integrate(
            current_position, current_velocity, masses_d, g_decimal, dt_decimal, substeps
        )
        positions.append(current_position)

    all_positions = [past_position] + positions
    if any(not (p[0] < p[1] < p[2]) for p in all_positions):
        raise ValueError("ordre modifié")

    parameters = ThreeBodyParameters(masses=masses_f, gravitational_constant=g_fraction, dt=dt)
    frame0 = encode_relational_frame(decimal_to_state(positions[0]), parameters)
    frame1 = encode_relational_frame(decimal_to_state(positions[1]), parameters)
    equation = derive_dynamic_equation(frame0, frame1, parameters)
    first_equation = equation
    dynamic_frames = [frame0, frame1]
    for _ in range(future_steps):
        dynamic_frames.append(equation.following)
        equation = advance_dynamic_equation(equation, parameters)

    dynamic_final = decode_relational_frame(dynamic_frames[-1], parameters)
    frozen_final = decode_relational_frame(
        frozen_equation_forward(first_equation, future_steps)[-1], parameters
    )
    past_equation = retrodict_dynamic_equation(frame0, frame1, parameters)
    dynamic_past = decode_relational_frame(past_equation.previous, parameters)

    return {
        "dynamic_forward": decimal_state_error(dynamic_final, positions[future_steps + 1]),
        "frozen_forward": decimal_state_error(frozen_final, positions[future_steps + 1]),
        "dynamic_backward": decimal_state_error(dynamic_past, past_position),
    }


def summarize_decimals(values: list[Decimal]) -> dict:
    ordered = sorted(values)
    return {
        "mean": format(sum(values, D(0)) / D(len(values)), ".12E"),
        "median": format(ordered[len(ordered)//2], ".12E"),
        "max": format(max(values), ".12E"),
    }


def continuous_benchmark(seed: int, trials: int, future_steps: int, substeps: int) -> dict:
    rng = random.Random(seed)
    report = {}
    for dt in (Fraction(1, 20), Fraction(1, 40), Fraction(1, 80)):
        metrics = {name: [] for name in ("dynamic_forward", "frozen_forward", "dynamic_backward")}
        accepted = 0
        attempts = 0
        while accepted < trials and attempts < trials * 30:
            attempts += 1
            try:
                result = continuous_case(rng, dt, future_steps, substeps)
            except (ValueError, ZeroDivisionError, ArithmeticError):
                continue
            for name, value in result.items():
                metrics[name].append(value)
            accepted += 1
        dynamic_mean = sum(metrics["dynamic_forward"], D(0)) / D(accepted)
        frozen_mean = sum(metrics["frozen_forward"], D(0)) / D(accepted)
        report[f"dt={dt.numerator}/{dt.denominator}"] = {
            "accepted": accepted,
            "final_horizon": f"{future_steps + 1}*dt from S0",
            "errors": {name: summarize_decimals(values) for name, values in metrics.items()},
            "mean_gain_dynamic_vs_frozen": format(frozen_mean / dynamic_mean, ".6E"),
        }
    return {
        "regime": "continuous 1D Newtonian reference",
        "reference": f"Decimal RK4, {substeps} substeps per dt",
        "trials_per_dt": trials,
        "future_steps_after_observed_S1": future_steps,
        "results": report,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=271828)
    parser.add_argument("--exact-trials", type=int, default=200)
    parser.add_argument("--continuous-trials", type=int, default=30)
    parser.add_argument("--future-steps", type=int, default=4)
    parser.add_argument("--substeps", type=int, default=120)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = {
        "experiment": "ANANKE dynamic equation three-body retest",
        "principle": "E_n is regenerated at every state; no ratio is reused as E_(n+1)",
        "seed": args.seed,
        "exact_discrete": exact_benchmark(args.seed, args.exact_trials, args.future_steps),
        "continuous_reference": continuous_benchmark(
            args.seed + 1,
            args.continuous_trials,
            args.future_steps,
            args.substeps,
        ),
        "interpretation_guard": (
            "This tests equation regeneration from two observed states plus masses, G and dt. "
            "It does not infer Newton's law from a single transition."
        ),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
