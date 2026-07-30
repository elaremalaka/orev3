"""Deterministic experiment-level metrics for RFC-010 Phase 5."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from orev3.strategy_lab.evaluation import EvaluationResult


@dataclass(frozen=True, slots=True)
class ExperimentMetrics:
    """Immutable factual aggregation of completed evaluation results."""

    evaluation_count: int
    hit_count: int
    miss_count: int
    square_deployment_counts: tuple[int, ...]

    def __post_init__(self) -> None:
        _validate_nonnegative_integer("evaluation_count", self.evaluation_count)
        _validate_nonnegative_integer("hit_count", self.hit_count)
        _validate_nonnegative_integer("miss_count", self.miss_count)
        counts = tuple(self.square_deployment_counts)
        if len(counts) != 25:
            raise ValueError(
                "square_deployment_counts must contain exactly 25 values"
            )
        for count in counts:
            _validate_nonnegative_integer("square deployment count", count)
        if self.hit_count + self.miss_count != self.evaluation_count:
            raise ValueError(
                "hit_count and miss_count must equal evaluation_count"
            )
        object.__setattr__(self, "square_deployment_counts", counts)

    @property
    def hit_rate(self) -> float | None:
        if self.evaluation_count == 0:
            return None
        return self.hit_count / self.evaluation_count

    @property
    def miss_rate(self) -> float | None:
        if self.evaluation_count == 0:
            return None
        return self.miss_count / self.evaluation_count


@dataclass(frozen=True, slots=True)
class MetricsEngine:
    """Aggregate immutable per-decision results without influencing execution."""

    def aggregate(
        self,
        results: Iterable[EvaluationResult],
    ) -> ExperimentMetrics:
        completed = tuple(results)
        if not all(isinstance(result, EvaluationResult) for result in completed):
            raise TypeError(
                "results must contain only EvaluationResult instances"
            )
        round_identifiers = tuple(
            result.observation.round_identifier for result in completed
        )
        if len(set(round_identifiers)) != len(round_identifiers):
            raise ValueError(
                "an experiment cannot contain duplicate round evaluations"
            )

        hit_count = sum(result.hit for result in completed)
        square_counts = [0] * 25
        for result in completed:
            for allocation in result.deployment_decision:
                if allocation.allocation_amount > 0:
                    square_counts[allocation.square_identifier] += 1

        return ExperimentMetrics(
            evaluation_count=len(completed),
            hit_count=hit_count,
            miss_count=len(completed) - hit_count,
            square_deployment_counts=tuple(square_counts),
        )


def _validate_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


__all__ = ("ExperimentMetrics", "MetricsEngine")
