"""ANANKÉ — expérience relationnelle exacte du problème gravitationnel à trois corps.

Ce module ne modifie pas l'inférence linguistique. Il ajoute une logique physique
explicite, en régime 1D rationnel exact, afin de tester l'hypothèse suivante :

    deux états consécutifs S_n, S_{n+1} + les masses + la loi gravitationnelle
    suffisent à générer S_{n+2} et à reconstruire S_{n-1}.

Le propagateur est la récurrence temporellement symétrique de Störmer--Verlet :

    x_{k+1} = 2 x_k - x_{k-1} + a(x_k) dt².

Les positions signées sont absolutisées par une jauge de centre de masse et des
écarts adjacents strictement positifs. Les relations de distance et du noyau
gravitationnel sont contrôlées par les cellules distributives existantes :

    rho_s = (d_{k+1}/d_k)²,
    rho_g = ((1/d_{k+1})/(1/d_k))³,
    rho_g² rho_s³ = 1.

Aucun flottant, logarithme, exponentielle ni racine irrationnelle n'est utilisé.
Cette preuve expérimentale est exacte mais limitée au cas colinéaire sans collision.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from typing import Iterable, Sequence

from .distributive import (
    ClosureCoordinate,
    MemoryCell,
    cell_holds,
    chain_state,
    closure_epsilon,
    memory_cell,
)


BodyVector = tuple[Fraction, Fraction, Fraction]


def _fraction(value: int | str | Fraction) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(value)


def _vector(values: Sequence[int | str | Fraction]) -> BodyVector:
    if len(values) != 3:
        raise ValueError("Le système exige exactement trois corps.")
    return tuple(_fraction(value) for value in values)  # type: ignore[return-value]


@dataclass(frozen=True)
class ThreeBodyParameters:
    masses: BodyVector
    gravitational_constant: Fraction = Fraction(1, 1)
    dt: Fraction = Fraction(1, 10)

    def __post_init__(self) -> None:
        if any(mass <= 0 for mass in self.masses):
            raise ValueError("Chaque masse doit être strictement positive.")
        if self.gravitational_constant <= 0:
            raise ValueError("La constante gravitationnelle doit être positive.")
        if self.dt <= 0:
            raise ValueError("Le pas temporel doit être positif.")


@dataclass(frozen=True)
class ThreeBodyState:
    """Positions signées de trois corps sur une droite physique."""

    positions: BodyVector

    @classmethod
    def from_values(cls, values: Sequence[int | str | Fraction]) -> "ThreeBodyState":
        return cls(_vector(values))


@dataclass(frozen=True)
class RelationalFrame:
    """Absolutisation relationnelle reconstructible d'un état.

    - ``order`` conserve l'orientation/topologie des corps sur la droite ;
    - ``center_of_mass`` fixe la jauge absolue ;
    - ``gaps`` porte les deux coordonnées multiplicatives strictement positives.
    """

    order: tuple[int, int, int]
    center_of_mass: Fraction
    gaps: tuple[Fraction, Fraction]

    def __post_init__(self) -> None:
        if sorted(self.order) != [0, 1, 2]:
            raise ValueError("L'ordre doit être une permutation des trois corps.")
        if any(gap <= 0 for gap in self.gaps):
            raise ValueError("Les écarts relationnels doivent être strictement positifs.")


@dataclass(frozen=True)
class PairRelationAudit:
    pair: tuple[int, int]
    distance_power_cell: MemoryCell
    inverse_distance_power_cell: MemoryCell
    temporal_power_closure: ClosureCoordinate
    distance_chain_target: Fraction | None
    inverse_chain_target: Fraction | None

    @property
    def holds(self) -> bool:
        return (
            cell_holds(self.distance_power_cell)
            and cell_holds(self.inverse_distance_power_cell)
            and self.temporal_power_closure.holds
            and self.distance_chain_target is not None
            and self.inverse_chain_target is not None
        )


@dataclass(frozen=True)
class TransitionAudit:
    pairs: tuple[PairRelationAudit, ...]

    @property
    def holds(self) -> bool:
        return all(item.holds for item in self.pairs)


def center_of_mass(state: ThreeBodyState, parameters: ThreeBodyParameters) -> Fraction:
    total_mass = sum(parameters.masses, Fraction(0))
    return sum(
        (mass * position for mass, position in zip(parameters.masses, state.positions)),
        Fraction(0),
    ) / total_mass


def encode_relational_frame(state: ThreeBodyState, parameters: ThreeBodyParameters) -> RelationalFrame:
    order = tuple(sorted(range(3), key=lambda index: (state.positions[index], index)))
    ordered = [state.positions[index] for index in order]
    if ordered[0] == ordered[1] or ordered[1] == ordered[2]:
        raise ZeroDivisionError("Collision : deux corps occupent la même position.")
    return RelationalFrame(
        order=order,  # type: ignore[arg-type]
        center_of_mass=center_of_mass(state, parameters),
        gaps=(ordered[1] - ordered[0], ordered[2] - ordered[1]),
    )


def decode_relational_frame(frame: RelationalFrame, parameters: ThreeBodyParameters) -> ThreeBodyState:
    first, second = frame.gaps
    i0, i1, i2 = frame.order
    m0, m1, m2 = (parameters.masses[index] for index in frame.order)
    total_mass = m0 + m1 + m2

    # y1 = y0+d01 ; y2 = y0+d01+d12 ; Σm_i y_i = M C.
    y0 = frame.center_of_mass - (m1 * first + m2 * (first + second)) / total_mass
    ordered_positions = (y0, y0 + first, y0 + first + second)
    positions = [Fraction(0), Fraction(0), Fraction(0)]
    for body_index, position in zip((i0, i1, i2), ordered_positions):
        positions[body_index] = position
    return ThreeBodyState(tuple(positions))  # type: ignore[arg-type]


def accelerations(state: ThreeBodyState, parameters: ThreeBodyParameters) -> BodyVector:
    """Accélérations newtoniennes exactes en 1D.

    (x_j-x_i)/|x_j-x_i|³ = signe(x_j-x_i)/|x_j-x_i|².
    """

    result = [Fraction(0), Fraction(0), Fraction(0)]
    for i, j in combinations(range(3), 2):
        difference = state.positions[j] - state.positions[i]
        if difference == 0:
            raise ZeroDivisionError("Collision gravitationnelle non régularisée.")
        distance = abs(difference)
        direction = Fraction(1 if difference > 0 else -1, 1)
        kernel = parameters.gravitational_constant * direction / (distance**2)
        result[i] += parameters.masses[j] * kernel
        result[j] -= parameters.masses[i] * kernel
    return tuple(result)  # type: ignore[return-value]


def seed_next_state(
    initial: ThreeBodyState,
    velocities: Sequence[int | str | Fraction],
    parameters: ThreeBodyParameters,
) -> ThreeBodyState:
    """Construit S_1 depuis S_0 et v_0 avec un demi-terme d'accélération."""

    velocity = _vector(velocities)
    acceleration = accelerations(initial, parameters)
    dt = parameters.dt
    return ThreeBodyState(tuple(
        position + speed * dt + acceleration_i * dt * dt / 2
        for position, speed, acceleration_i in zip(initial.positions, velocity, acceleration)
    ))  # type: ignore[arg-type]


def verlet_forward(
    previous: ThreeBodyState,
    current: ThreeBodyState,
    parameters: ThreeBodyParameters,
) -> ThreeBodyState:
    acceleration = accelerations(current, parameters)
    dt_squared = parameters.dt**2
    return ThreeBodyState(tuple(
        2 * current_position - previous_position + acceleration_i * dt_squared
        for previous_position, current_position, acceleration_i in zip(
            previous.positions, current.positions, acceleration
        )
    ))  # type: ignore[arg-type]


def verlet_backward(
    current: ThreeBodyState,
    following: ThreeBodyState,
    parameters: ThreeBodyParameters,
) -> ThreeBodyState:
    acceleration = accelerations(current, parameters)
    dt_squared = parameters.dt**2
    return ThreeBodyState(tuple(
        2 * current_position - following_position + acceleration_i * dt_squared
        for current_position, following_position, acceleration_i in zip(
            current.positions, following.positions, acceleration
        )
    ))  # type: ignore[arg-type]


def transition_audit(previous: ThreeBodyState, current: ThreeBodyState) -> TransitionAudit:
    audits: list[PairRelationAudit] = []
    for i, j in combinations(range(3), 2):
        previous_distance = abs(previous.positions[j] - previous.positions[i])
        current_distance = abs(current.positions[j] - current.positions[i])
        if previous_distance == 0 or current_distance == 0:
            raise ZeroDivisionError("Une collision ne possède pas de rapport multiplicatif défini.")

        distance_cell = memory_cell(
            f"distance²:{i}-{j}",
            previous_distance,
            current_distance - previous_distance,
            2,
        )
        previous_inverse = Fraction(1, 1) / previous_distance
        current_inverse = Fraction(1, 1) / current_distance
        inverse_cell = memory_cell(
            f"distance⁻³:{i}-{j}",
            previous_inverse,
            current_inverse - previous_inverse,
            3,
        )
        # rho_g = (d_n/d_{n+1})³ et rho_s = (d_{n+1}/d_n)².
        # Donc rho_g² rho_s³ = 1, sans racine ni exposant fractionnaire.
        power_closure = closure_epsilon(
            inverse_cell.ratio**2 * distance_cell.ratio**3,
            Fraction(1, 1),
            f"gravity_power:{i}-{j}",
        )
        audits.append(PairRelationAudit(
            pair=(i, j),
            distance_power_cell=distance_cell,
            inverse_distance_power_cell=inverse_cell,
            temporal_power_closure=power_closure,
            distance_chain_target=chain_state(previous_distance, [distance_cell], 2),
            inverse_chain_target=chain_state(previous_inverse, [inverse_cell], 3),
        ))
    return TransitionAudit(tuple(audits))


def frame_transition_audit(
    previous_frame: RelationalFrame,
    current_frame: RelationalFrame,
    parameters: ThreeBodyParameters,
) -> TransitionAudit:
    return transition_audit(
        decode_relational_frame(previous_frame, parameters),
        decode_relational_frame(current_frame, parameters),
    )


def _require_same_order(first: RelationalFrame, second: RelationalFrame) -> None:
    if first.order != second.order:
        raise ValueError(
            "Le prolongement multiplicatif local exige un ordre topologique stable ; "
            "un croisement/collision doit ouvrir une nouvelle branche relationnelle."
        )


def extrapolate_ratio_forward(
    previous_frame: RelationalFrame,
    current_frame: RelationalFrame,
    parameters: ThreeBodyParameters,
) -> RelationalFrame:
    """Témoin ANANKÉ sans loi physique : répète le rapport observé une fois."""

    _require_same_order(previous_frame, current_frame)
    ratios = tuple(
        current / previous
        for previous, current in zip(previous_frame.gaps, current_frame.gaps)
    )
    next_gaps = tuple(current * ratio for current, ratio in zip(current_frame.gaps, ratios))
    # Le centre de masse est inertiel : C_{n+2}=2C_{n+1}-C_n.
    next_center = 2 * current_frame.center_of_mass - previous_frame.center_of_mass
    return RelationalFrame(current_frame.order, next_center, next_gaps)  # type: ignore[arg-type]


def extrapolate_ratio_backward(
    current_frame: RelationalFrame,
    following_frame: RelationalFrame,
    parameters: ThreeBodyParameters,
) -> RelationalFrame:
    """Inverse local du témoin multiplicatif à rapport constant."""

    _require_same_order(current_frame, following_frame)
    ratios = tuple(
        following / current
        for current, following in zip(current_frame.gaps, following_frame.gaps)
    )
    previous_gaps = tuple(current / ratio for current, ratio in zip(current_frame.gaps, ratios))
    previous_center = 2 * current_frame.center_of_mass - following_frame.center_of_mass
    return RelationalFrame(current_frame.order, previous_center, previous_gaps)  # type: ignore[arg-type]


class RelationalThreeBodyPredictor:
    """Prédicteur ANANKÉ : états encodés en frames, loi appliquée après rappel."""

    def __init__(self, parameters: ThreeBodyParameters):
        self.parameters = parameters

    def encode(self, state: ThreeBodyState) -> RelationalFrame:
        return encode_relational_frame(state, self.parameters)

    def decode(self, frame: RelationalFrame) -> ThreeBodyState:
        return decode_relational_frame(frame, self.parameters)

    def predict_next(self, previous_frame: RelationalFrame, current_frame: RelationalFrame) -> RelationalFrame:
        previous = self.decode(previous_frame)
        current = self.decode(current_frame)
        predicted = verlet_forward(previous, current, self.parameters)
        return self.encode(predicted)

    def predict_previous(self, current_frame: RelationalFrame, following_frame: RelationalFrame) -> RelationalFrame:
        current = self.decode(current_frame)
        following = self.decode(following_frame)
        predicted = verlet_backward(current, following, self.parameters)
        return self.encode(predicted)

    def ratio_only_next(self, previous_frame: RelationalFrame, current_frame: RelationalFrame) -> RelationalFrame:
        return extrapolate_ratio_forward(previous_frame, current_frame, self.parameters)

    def ratio_only_previous(self, current_frame: RelationalFrame, following_frame: RelationalFrame) -> RelationalFrame:
        return extrapolate_ratio_backward(current_frame, following_frame, self.parameters)


def max_absolute_error(left: ThreeBodyState, right: ThreeBodyState) -> Fraction:
    return max(abs(a - b) for a, b in zip(left.positions, right.positions))


def states_equal(left: ThreeBodyState, right: ThreeBodyState) -> bool:
    return left.positions == right.positions


def all_transition_audits_hold(states: Iterable[ThreeBodyState]) -> bool:
    sequence = list(states)
    return all(transition_audit(sequence[index], sequence[index + 1]).holds for index in range(len(sequence) - 1))

# ==========================================================================
# Équations relationnelles évolutives
# ==========================================================================

@dataclass(frozen=True)
class GapEquationCoordinate:
    """Une composante de l'équation locale qui change à chaque pas.

    ``observed`` porte la relation réellement observée d_{n-1} -> d_n.
    ``relative_acceleration`` est l'accélération de l'écart au temps n.
    ``generated`` porte la NOUVELLE relation d_n -> d_{n+1}.
    """

    gap_index: int
    observed: MemoryCell
    relative_acceleration: Fraction
    generated: MemoryCell
    update_closure: ClosureCoordinate

    @property
    def holds(self) -> bool:
        return (
            cell_holds(self.observed)
            and cell_holds(self.generated)
            and self.update_closure.holds
        )

    @property
    def observed_ratio(self) -> Fraction:
        return self.observed.ratio

    @property
    def generated_ratio(self) -> Fraction:
        return self.generated.ratio


@dataclass(frozen=True)
class DynamicRelationalEquation:
    """Équation locale E_n construite depuis deux états consécutifs.

    Elle ne répète pas le rapport observé. Elle calcule une nouvelle relation
    depuis l'accélération relationnelle de l'état courant :

        h_{n+1} = h_n + b_n dt²
        d_{n+1} = d_n + h_{n+1}
        rho_{n+1} = d_{n+1}/d_n

    où b_n est la différence d'accélération entre les deux corps bordant
    l'écart considéré.
    """

    previous: RelationalFrame
    current: RelationalFrame
    following: RelationalFrame
    coordinates: tuple[GapEquationCoordinate, GapEquationCoordinate]
    center_inertia_closure: ClosureCoordinate
    current_transition_audit: TransitionAudit
    generated_transition_audit: TransitionAudit

    @property
    def observed_ratios(self) -> tuple[Fraction, Fraction]:
        return tuple(item.observed_ratio for item in self.coordinates)  # type: ignore[return-value]

    @property
    def generated_ratios(self) -> tuple[Fraction, Fraction]:
        return tuple(item.generated_ratio for item in self.coordinates)  # type: ignore[return-value]

    @property
    def relative_accelerations(self) -> tuple[Fraction, Fraction]:
        return tuple(item.relative_acceleration for item in self.coordinates)  # type: ignore[return-value]

    @property
    def equation_changed(self) -> bool:
        return self.generated_ratios != self.observed_ratios

    @property
    def holds(self) -> bool:
        return (
            all(item.holds for item in self.coordinates)
            and self.center_inertia_closure.holds
            and self.current_transition_audit.holds
            and self.generated_transition_audit.holds
        )

    def signature(self) -> tuple[Fraction, ...]:
        """Signature numérique de E_n, utile pour vérifier E_{n+1} != E_n."""
        return (
            *self.observed_ratios,
            *self.relative_accelerations,
            *self.generated_ratios,
        )


def _ordered_relative_accelerations(
    frame: RelationalFrame,
    parameters: ThreeBodyParameters,
) -> tuple[Fraction, Fraction]:
    state = decode_relational_frame(frame, parameters)
    acceleration_by_body = accelerations(state, parameters)
    ordered = tuple(acceleration_by_body[index] for index in frame.order)
    return ordered[1] - ordered[0], ordered[2] - ordered[1]


def derive_dynamic_equation(
    previous_frame: RelationalFrame,
    current_frame: RelationalFrame,
    parameters: ThreeBodyParameters,
) -> DynamicRelationalEquation:
    """Construit E_n et génère simultanément la relation suivante.

    La forme de la loi reste stable, mais les coefficients numériques de
    l'équation (rapports et accélérations relatives) sont recalculés depuis
    l'état courant. Un croisement ouvre une autre branche relationnelle.
    """

    _require_same_order(previous_frame, current_frame)
    relative_acceleration = _ordered_relative_accelerations(current_frame, parameters)
    dt_squared = parameters.dt**2

    equation_coordinates: list[GapEquationCoordinate] = []
    next_gaps: list[Fraction] = []
    for index, (previous_gap, current_gap, gap_acceleration) in enumerate(
        zip(previous_frame.gaps, current_frame.gaps, relative_acceleration)
    ):
        observed_step = current_gap - previous_gap
        observed_cell = memory_cell(
            f"equation:gap:{index}:observed",
            previous_gap,
            observed_step,
            1,
        )
        generated_step = observed_step + gap_acceleration * dt_squared
        next_gap = current_gap + generated_step
        if next_gap <= 0:
            raise ValueError(
                "Le pas généré provoque un croisement/collision ; "
                "une nouvelle branche topologique est requise."
            )
        generated_cell = memory_cell(
            f"equation:gap:{index}:generated",
            current_gap,
            generated_step,
            1,
        )
        update_closure = closure_epsilon(
            generated_cell.h,
            observed_cell.h + gap_acceleration * dt_squared,
            f"equation_update:gap:{index}",
        )
        equation_coordinates.append(
            GapEquationCoordinate(
                gap_index=index,
                observed=observed_cell,
                relative_acceleration=gap_acceleration,
                generated=generated_cell,
                update_closure=update_closure,
            )
        )
        next_gaps.append(next_gap)

    next_center = 2 * current_frame.center_of_mass - previous_frame.center_of_mass
    following_frame = RelationalFrame(
        order=current_frame.order,
        center_of_mass=next_center,
        gaps=tuple(next_gaps),  # type: ignore[arg-type]
    )
    center_closure = closure_epsilon(
        following_frame.center_of_mass
        - 2 * current_frame.center_of_mass
        + previous_frame.center_of_mass,
        Fraction(0),
        "center_of_mass_inertia",
    )
    return DynamicRelationalEquation(
        previous=previous_frame,
        current=current_frame,
        following=following_frame,
        coordinates=tuple(equation_coordinates),  # type: ignore[arg-type]
        center_inertia_closure=center_closure,
        current_transition_audit=frame_transition_audit(previous_frame, current_frame, parameters),
        generated_transition_audit=frame_transition_audit(current_frame, following_frame, parameters),
    )


def advance_dynamic_equation(
    equation: DynamicRelationalEquation,
    parameters: ThreeBodyParameters,
) -> DynamicRelationalEquation:
    """Passe de E_n à E_{n+1} en recalculant tous les coefficients."""

    return derive_dynamic_equation(equation.current, equation.following, parameters)


def retrodict_dynamic_equation(
    current_frame: RelationalFrame,
    following_frame: RelationalFrame,
    parameters: ThreeBodyParameters,
) -> DynamicRelationalEquation:
    """Reconstruit E_{n-1} puis S_{n-1} depuis S_n,S_{n+1}."""

    _require_same_order(current_frame, following_frame)
    relative_acceleration = _ordered_relative_accelerations(current_frame, parameters)
    dt_squared = parameters.dt**2
    previous_gaps: list[Fraction] = []
    for current_gap, following_gap, gap_acceleration in zip(
        current_frame.gaps,
        following_frame.gaps,
        relative_acceleration,
    ):
        generated_step = following_gap - current_gap
        observed_step = generated_step - gap_acceleration * dt_squared
        previous_gap = current_gap - observed_step
        if previous_gap <= 0:
            raise ValueError("La rétrodiction franchit une collision/croisement.")
        previous_gaps.append(previous_gap)
    previous_center = 2 * current_frame.center_of_mass - following_frame.center_of_mass
    previous_frame = RelationalFrame(
        order=current_frame.order,
        center_of_mass=previous_center,
        gaps=tuple(previous_gaps),  # type: ignore[arg-type]
    )
    equation = derive_dynamic_equation(previous_frame, current_frame, parameters)
    if equation.following != following_frame:
        raise ArithmeticError("La fermeture réversible de l'équation a échoué.")
    return equation


def frozen_equation_forward(
    equation: DynamicRelationalEquation,
    steps: int,
) -> list[RelationalFrame]:
    """Témoin volontairement faux : conserve E_n inchangée sur plusieurs pas.

    Il applique toujours les mêmes rapports générés, précisément l'erreur
    dénoncée par l'utilisateur. Le centre de masse reste inertiel.
    """

    if steps < 0:
        raise ValueError("steps doit être positif.")
    frames = [equation.previous, equation.current]
    ratios = equation.generated_ratios
    center_step = equation.current.center_of_mass - equation.previous.center_of_mass
    current = equation.current
    for _ in range(steps):
        next_frame = RelationalFrame(
            order=current.order,
            center_of_mass=current.center_of_mass + center_step,
            gaps=tuple(gap * ratio for gap, ratio in zip(current.gaps, ratios)),  # type: ignore[arg-type]
        )
        frames.append(next_frame)
        current = next_frame
    return frames
