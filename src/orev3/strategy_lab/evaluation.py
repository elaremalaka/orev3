"""Deterministic factual evaluation for RFC-010 Phase 4."""

from __future__ import annotations

from dataclasses import dataclass

from orev3.strategy_lab.deployment import (
    DeploymentAllocation,
    DeploymentDecision,
)


@dataclass(frozen=True, slots=True)
class EvaluationObservation:
    """Immutable historical facts corresponding to one replayed decision."""

    round_identifier: int
    winning_square_identifier: int

    def __post_init__(self) -> None:
        _validate_nonnegative_integer("round_identifier", self.round_identifier)
        if isinstance(self.winning_square_identifier, bool) or not isinstance(
            self.winning_square_identifier,
            int,
        ):
            raise TypeError("winning_square_identifier must be an integer")
        if not 0 <= self.winning_square_identifier <= 24:
            raise ValueError(
                "winning_square_identifier must be between 0 and 24"
            )


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Immutable factual result for exactly one replayed deployment decision."""

    observation: EvaluationObservation
    deployment_decision: DeploymentDecision
    hit: bool
    winning_allocation: DeploymentAllocation | None

    def __post_init__(self) -> None:
        if not isinstance(self.observation, EvaluationObservation):
            raise TypeError("observation must be an EvaluationObservation")
        if not isinstance(self.deployment_decision, DeploymentDecision):
            raise TypeError(
                "deployment_decision must be a DeploymentDecision"
            )
        if not isinstance(self.hit, bool):
            raise TypeError("hit must be a boolean")

        expected = _winning_allocation(
            self.deployment_decision,
            self.observation.winning_square_identifier,
        )
        if self.winning_allocation != expected or self.hit != (expected is not None):
            raise ValueError(
                "EvaluationResult does not match the factual deployment outcome"
            )


@dataclass(frozen=True, slots=True)
class Evaluator:
    """Compare one immutable deployment decision with one historical outcome."""

    def evaluate(
        self,
        deployment_decision: DeploymentDecision,
        observation: EvaluationObservation,
    ) -> EvaluationResult:
        if not isinstance(deployment_decision, DeploymentDecision):
            raise TypeError(
                "deployment_decision must be a DeploymentDecision"
            )
        if not isinstance(observation, EvaluationObservation):
            raise TypeError("observation must be an EvaluationObservation")

        winning_allocation = _winning_allocation(
            deployment_decision,
            observation.winning_square_identifier,
        )
        return EvaluationResult(
            observation=observation,
            deployment_decision=deployment_decision,
            hit=winning_allocation is not None,
            winning_allocation=winning_allocation,
        )


def _winning_allocation(
    decision: DeploymentDecision,
    winning_square_identifier: int,
) -> DeploymentAllocation | None:
    return next(
        (
            allocation
            for allocation in decision
            if (
                allocation.square_identifier == winning_square_identifier
                and allocation.allocation_amount > 0
            )
        ),
        None,
    )


def _validate_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


__all__ = ("EvaluationObservation", "EvaluationResult", "Evaluator")
