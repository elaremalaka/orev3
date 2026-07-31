"""Deterministic RFC-011 Phase 2 allocation materialization."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from orev3.strategy_lab.deployment import (
    DeploymentAllocation,
    DeploymentDecision,
)
from orev3.strategy_lab.economics import (
    SQUARE_COUNT,
    EconomicScenario,
    LamportApportionmentRule,
)


@dataclass(frozen=True, slots=True)
class AllocationMaterializer:
    """Convert one abstract deployment decision into exact lamports."""

    def materialize(
        self,
        decision: DeploymentDecision,
        scenario: EconomicScenario,
    ) -> tuple[int, ...]:
        """Return one immutable 25-square proposed deployment vector."""

        if not isinstance(decision, DeploymentDecision):
            raise TypeError("decision must be a DeploymentDecision")
        if not isinstance(scenario, EconomicScenario):
            raise TypeError("scenario must be an EconomicScenario")
        if scenario.lamport_apportionment_rule is not (
            LamportApportionmentRule
            .LARGEST_REMAINDER_CANDIDATE_ORDER_V1
        ):
            raise ValueError("unsupported lamport apportionment rule")

        allocations = tuple(decision)
        square_identifiers: set[int] = set()
        amounts: list[Fraction] = []
        weights: list[Fraction] = []
        amount_floats: list[float] = []

        for allocation in allocations:
            if not isinstance(allocation, DeploymentAllocation):
                raise TypeError(
                    "decision must contain only DeploymentAllocation values"
                )
            square_identifier = allocation.square_identifier
            if isinstance(square_identifier, bool) or not isinstance(
                square_identifier,
                int,
            ):
                raise TypeError("square_identifier must be an integer")
            if not 0 <= square_identifier < SQUARE_COUNT:
                raise ValueError(
                    "square_identifier must be between 0 and 24"
                )
            if square_identifier in square_identifiers:
                raise ValueError("duplicate square identifier")
            square_identifiers.add(square_identifier)

            amount, amount_float = _finite_nonnegative_fraction(
                "allocation_amount",
                allocation.allocation_amount,
            )
            weight, _ = _finite_nonnegative_fraction(
                "allocation_weight",
                allocation.allocation_weight,
            )
            if weight > 1:
                raise ValueError("allocation_weight must be at most 1")
            if (amount == 0) != (weight == 0):
                raise ValueError(
                    "allocation amount and weight support is inconsistent"
                )
            amounts.append(amount)
            weights.append(weight)
            amount_floats.append(amount_float)

        total_amount = _canonical_float_total(amount_floats)
        if total_amount > 1:
            raise ValueError("total allocation amount must not exceed one")

        exact_amount_total = sum(amounts, start=Fraction())
        exact_weight_total = sum(weights, start=Fraction())
        if exact_amount_total == 0:
            if exact_weight_total != 0:
                raise ValueError(
                    "allocation amount and weight totals are inconsistent"
                )
            return (0,) * SQUARE_COUNT
        if exact_weight_total == 0:
            raise ValueError(
                "positive allocation amount requires positive weight"
            )
        for amount, weight in zip(amounts, weights, strict=True):
            if amount * exact_weight_total != weight * exact_amount_total:
                raise ValueError(
                    "allocation amount and weight distributions "
                    "are inconsistent"
                )

        budget = scenario.per_round_deployment_budget_lamports
        target_lamports = _floor_fraction(total_amount * budget)
        quotas = tuple(
            Fraction(target_lamports) * amount / exact_amount_total
            for amount in amounts
        )
        apportioned = [_floor_fraction(quota) for quota in quotas]
        remainder_count = target_lamports - sum(apportioned)
        if not 0 <= remainder_count < max(1, len(apportioned)):
            raise ValueError("lamport allocation is unrepresentable")

        remainder_order = sorted(
            range(len(quotas)),
            key=lambda index: (-_fractional_part(quotas[index]), index),
        )
        for index in remainder_order[:remainder_count]:
            apportioned[index] += 1

        if any(
            amount > 0 and lamports == 0
            for amount, lamports in zip(
                amounts,
                apportioned,
                strict=True,
            )
        ):
            raise ValueError(
                "positive allocation is unrepresentable in lamports"
            )

        proposed = [0] * SQUARE_COUNT
        for allocation, lamports in zip(
            allocations,
            apportioned,
            strict=True,
        ):
            proposed[allocation.square_identifier] = lamports
        if sum(proposed) != target_lamports or sum(proposed) > budget:
            raise ValueError("lamport materialization is inconsistent")
        return tuple(proposed)


def _finite_nonnegative_fraction(
    name: str,
    value: object,
) -> tuple[Fraction, float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    try:
        normalized = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be representable") from exc
    if not math.isfinite(normalized) or normalized < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return Fraction(str(normalized)), normalized


def _canonical_float_total(values: list[float]) -> Fraction:
    try:
        total = math.fsum(values)
    except (OverflowError, ValueError) as exc:
        raise ValueError(
            "total allocation amount must be representable"
        ) from exc
    if not math.isfinite(total):
        raise ValueError("total allocation amount must be finite")
    return Fraction(str(total))


def _floor_fraction(value: Fraction) -> int:
    return value.numerator // value.denominator


def _fractional_part(value: Fraction) -> Fraction:
    return value - _floor_fraction(value)


__all__ = ("AllocationMaterializer",)
