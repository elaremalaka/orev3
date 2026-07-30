"""Deterministic reference strategies for RFC-010 Phase 6."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from orev3.strategy_lab.interfaces import (
    DecisionContext,
    Explanation,
    RankedCandidate,
    RankedCandidateSet,
    Strategy,
)


@dataclass(slots=True)
class RandomStrategy(Strategy):
    """Rank every square by a stable digest of seed, round, and square."""

    seed: int = 0
    _active: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")

    def initialize(self) -> None:
        self._active = True

    def choose(self, context: DecisionContext) -> RankedCandidateSet:
        _require_active(self._active)
        round_identifier = _round_identifier(context)
        ranked = sorted(
            (
                (
                    hashlib.sha256(
                        f"{self.seed}:{round_identifier}:{square}".encode()
                    ).hexdigest(),
                    square,
                )
                for square in range(25)
            ),
            reverse=True,
        )
        return RankedCandidateSet(
            RankedCandidate(
                square_identifier=square,
                preference_score=float(25 - rank),
                explanation=Explanation(
                    {
                        "strategy": "deterministic_random",
                        "seed": self.seed,
                        "ranking_digest": digest,
                    }
                ),
            )
            for rank, (digest, square) in enumerate(ranked)
        )

    def update(self, result: object) -> None:
        _require_active(self._active)

    def finalize(self) -> None:
        self._active = False


@dataclass(slots=True)
class LeastCrowdedStrategy(Strategy):
    """Prefer squares with the fewest contemporaneously observed miners."""

    _active: bool = field(default=False, init=False, repr=False)

    def initialize(self) -> None:
        self._active = True

    def choose(self, context: DecisionContext) -> RankedCandidateSet:
        _require_active(self._active)
        miner_counts = _miner_counts(context)
        ordered = sorted(range(25), key=lambda square: (miner_counts[square], square))
        return RankedCandidateSet(
            RankedCandidate(
                square_identifier=square,
                preference_score=float(-miner_counts[square]),
                explanation=Explanation(
                    {
                        "strategy": "least_crowded",
                        "miner_count": miner_counts[square],
                    }
                ),
            )
            for square in ordered
        )

    def update(self, result: object) -> None:
        _require_active(self._active)

    def finalize(self) -> None:
        self._active = False


@dataclass(slots=True)
class EqualDistributionStrategy(Strategy):
    """Express equal preference for every square in canonical square order."""

    _active: bool = field(default=False, init=False, repr=False)

    def initialize(self) -> None:
        self._active = True

    def choose(self, context: DecisionContext) -> RankedCandidateSet:
        _require_active(self._active)
        _round_identifier(context)
        return RankedCandidateSet(
            RankedCandidate(
                square_identifier=square,
                preference_score=1.0,
                explanation=Explanation(
                    {
                        "strategy": "equal_distribution",
                        "canonical_square_order": square,
                    }
                ),
            )
            for square in range(25)
        )

    def update(self, result: object) -> None:
        _require_active(self._active)

    def finalize(self) -> None:
        self._active = False


def _require_active(active: bool) -> None:
    if not active:
        raise RuntimeError("strategy must be initialized before lifecycle use")


def _round_identifier(context: DecisionContext) -> int:
    if not isinstance(context, DecisionContext):
        raise TypeError("context must be a DecisionContext")
    value = context.information.get("round_id")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("context round_id must be a nonnegative integer")
    return value


def _miner_counts(context: DecisionContext) -> tuple[int, ...]:
    _round_identifier(context)
    round_information = context.information.get("round")
    if not isinstance(round_information, Mapping):
        raise ValueError("context round information is required")
    raw_counts = round_information.get("miner_counts")
    if (
        not isinstance(raw_counts, Sequence)
        or isinstance(raw_counts, (str, bytes))
        or len(raw_counts) != 25
    ):
        raise ValueError("context miner_counts must contain exactly 25 values")
    counts: list[int] = []
    for value in raw_counts:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("context miner_counts must be nonnegative integers")
        counts.append(value)
    return tuple(counts)


__all__ = (
    "EqualDistributionStrategy",
    "LeastCrowdedStrategy",
    "RandomStrategy",
)
