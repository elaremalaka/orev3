"""Immutable deployment-model interfaces for RFC-010 Phase 3."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field

from orev3.strategy_lab.interfaces import (
    RankedCandidateSet,
    StructuredValue,
    _freeze_mapping,
)


@dataclass(frozen=True, slots=True)
class DeploymentAllocation:
    """One immutable allocation within a deployment decision."""

    square_identifier: int
    allocation_amount: float
    allocation_weight: float
    metadata: Mapping[str, StructuredValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.square_identifier, bool) or not isinstance(
            self.square_identifier,
            int,
        ):
            raise TypeError("square_identifier must be an integer")
        if not 0 <= self.square_identifier <= 24:
            raise ValueError("square_identifier must be between 0 and 24")
        amount = _finite_nonnegative_float(
            "allocation_amount",
            self.allocation_amount,
        )
        weight = _finite_nonnegative_float(
            "allocation_weight",
            self.allocation_weight,
        )
        if weight > 1.0:
            raise ValueError("allocation_weight must be at most 1")
        object.__setattr__(self, "allocation_amount", amount)
        object.__setattr__(self, "allocation_weight", weight)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True, init=False)
class DeploymentDecision:
    """Immutable ordered collection produced by a Deployment Model."""

    allocations: tuple[DeploymentAllocation, ...]

    def __init__(self, allocations: Iterable[DeploymentAllocation]) -> None:
        ordered = tuple(allocations)
        if not all(
            isinstance(allocation, DeploymentAllocation)
            for allocation in ordered
        ):
            raise TypeError(
                "allocations must contain only DeploymentAllocation instances"
            )
        square_identifiers = tuple(
            allocation.square_identifier for allocation in ordered
        )
        if len(set(square_identifiers)) != len(square_identifiers):
            raise ValueError(
                "a DeploymentDecision cannot allocate one square more than once"
            )
        object.__setattr__(self, "allocations", ordered)

    def __iter__(self) -> Iterator[DeploymentAllocation]:
        return iter(self.allocations)

    def __len__(self) -> int:
        return len(self.allocations)

    def __getitem__(self, index: int) -> DeploymentAllocation:
        return self.allocations[index]


class DeploymentModel(ABC):
    """Convert strategy preference into deterministic deployment conviction."""

    @abstractmethod
    def allocate(self, candidates: RankedCandidateSet) -> DeploymentDecision:
        """Return an immutable deployment decision for ranked candidates."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class EqualWeightDeploymentModel(DeploymentModel):
    """Split a deterministic unit allocation equally across all candidates."""

    def allocate(self, candidates: RankedCandidateSet) -> DeploymentDecision:
        if not isinstance(candidates, RankedCandidateSet):
            raise TypeError("candidates must be a RankedCandidateSet")
        if not candidates:
            return DeploymentDecision(())

        share = 1.0 / len(candidates)
        return DeploymentDecision(
            DeploymentAllocation(
                square_identifier=candidate.square_identifier,
                allocation_amount=share,
                allocation_weight=share,
                metadata={
                    "deployment_model": "equal_weight",
                    "candidate_rank": rank,
                },
            )
            for rank, candidate in enumerate(candidates, start=1)
        )


def _finite_nonnegative_float(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return normalized


__all__ = (
    "DeploymentAllocation",
    "DeploymentDecision",
    "DeploymentModel",
    "EqualWeightDeploymentModel",
)
