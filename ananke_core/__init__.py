"""ANANKÉ — génératrice relationnelle multiplicative."""

from .engine import AnankeEngine
from .distributive import (
    DistributiveCoordinate, MemoryCell,
    distributive_coordinate, distributive_expansion, memory_cell,
    close_ratio, close_delta, close_coefficient, close_step, close_degree,
    recall_masked, chain_state, associates,
    ClosureCoordinate, closure_epsilon, closure_of_step,
    cell_closure, cell_holds, combine_holds, scalar_defect, admits_step,
)

__all__ = [
    "AnankeEngine",
    "DistributiveCoordinate", "MemoryCell",
    "distributive_coordinate", "distributive_expansion", "memory_cell",
    "close_ratio", "close_delta", "close_coefficient", "close_step", "close_degree",
    "recall_masked", "chain_state", "associates",
    "ClosureCoordinate", "closure_epsilon", "closure_of_step",
    "cell_closure", "cell_holds", "combine_holds", "scalar_defect", "admits_step",
]

# Extension expérimentale : dynamique gravitationnelle relationnelle exacte (1D).
from .three_body import (
    RelationalFrame,
    RelationalThreeBodyPredictor,
    ThreeBodyParameters,
    ThreeBodyState,
    transition_audit,
    verlet_backward,
    verlet_forward,
)

from .three_body import (
    DynamicRelationalEquation, GapEquationCoordinate,
    derive_dynamic_equation, advance_dynamic_equation,
    retrodict_dynamic_equation, frozen_equation_forward,
)
