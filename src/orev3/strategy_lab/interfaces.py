"""Immutable public interfaces defined by RFC-010 Phase 1."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias


StructuredScalar: TypeAlias = str | int | float | bool | None
StructuredValue: TypeAlias = (
    StructuredScalar
    | tuple["StructuredValue", ...]
    | Mapping[str, "StructuredValue"]
)


def _freeze_structured_value(value: object) -> StructuredValue:
    """Copy structured data into a deterministic, deeply immutable form."""
    if isinstance(value, Mapping):
        frozen: dict[str, StructuredValue] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise TypeError("structured mapping keys must be strings")
            frozen[key] = _freeze_structured_value(nested_value)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_structured_value(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("structured floating-point values must be finite")
        return value
    raise TypeError(
        "structured values must contain only mappings, sequences, "
        "strings, integers, finite floats, booleans, or null"
    )


def _freeze_mapping(
    value: Mapping[str, object],
) -> Mapping[str, StructuredValue]:
    frozen = _freeze_structured_value(value)
    if not isinstance(frozen, Mapping):
        raise TypeError("structured payload must be a mapping")
    return frozen


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Strategy-visible information available immediately before a decision.

    The context deliberately contains no replay object, finalized outcome, or
    future-information field. A later RFC-010 phase will construct contexts
    from historical replay through this interface.
    """

    information: Mapping[str, StructuredValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "information",
            _freeze_mapping(self.information),
        )


@dataclass(frozen=True, slots=True)
class Explanation:
    """Opaque, immutable explanation produced and owned by a strategy."""

    payload: Mapping[str, StructuredValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "payload",
            _freeze_mapping(self.payload),
        )


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """One square in a strategy-defined preference ordering."""

    square_identifier: int
    preference_score: float
    explanation: Explanation | None = None

    def __post_init__(self) -> None:
        if isinstance(self.square_identifier, bool) or not isinstance(
            self.square_identifier,
            int,
        ):
            raise TypeError("square_identifier must be an integer")
        if not 0 <= self.square_identifier <= 24:
            raise ValueError("square_identifier must be between 0 and 24")
        if isinstance(self.preference_score, bool) or not isinstance(
            self.preference_score,
            (int, float),
        ):
            raise TypeError("preference_score must be numeric")
        score = float(self.preference_score)
        if not math.isfinite(score):
            raise ValueError("preference_score must be finite")
        object.__setattr__(self, "preference_score", score)
        if self.explanation is not None and not isinstance(
            self.explanation,
            Explanation,
        ):
            raise TypeError("explanation must be an Explanation or None")


@dataclass(frozen=True, slots=True, init=False)
class RankedCandidateSet:
    """An immutable strategy-owned ordering of ranked candidates."""

    candidates: tuple[RankedCandidate, ...]

    def __init__(self, candidates: Iterable[RankedCandidate]) -> None:
        ordered = tuple(candidates)
        if not all(isinstance(candidate, RankedCandidate) for candidate in ordered):
            raise TypeError(
                "candidates must contain only RankedCandidate instances"
            )
        object.__setattr__(self, "candidates", ordered)

    def __iter__(self) -> Iterator[RankedCandidate]:
        return iter(self.candidates)

    def __len__(self) -> int:
        return len(self.candidates)

    def __getitem__(self, index: int) -> RankedCandidate:
        return self.candidates[index]


class Strategy(ABC):
    """Abstract lifecycle for one deterministic RFC-010 strategy."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize deterministic strategy state."""
        raise NotImplementedError

    @abstractmethod
    def choose(self, context: DecisionContext) -> RankedCandidateSet:
        """Return the strategy's ordered preferences for one decision."""
        raise NotImplementedError

    @abstractmethod
    def update(self, result: object) -> None:
        """Update deterministic state after the current outcome is revealed."""
        raise NotImplementedError

    @abstractmethod
    def finalize(self) -> None:
        """Finalize deterministic strategy state after all decisions."""
        raise NotImplementedError
