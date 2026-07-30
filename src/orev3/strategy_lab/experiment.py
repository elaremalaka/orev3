"""Executable end-to-end research experiment for RFC-010 Phase 6."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from orev3.strategy_lab.deployment import (
    DeploymentDecision,
    DeploymentModel,
)
from orev3.strategy_lab.evaluation import (
    EvaluationObservation,
    EvaluationResult,
    Evaluator,
)
from orev3.strategy_lab.interfaces import (
    DecisionContext,
    RankedCandidateSet,
    Strategy,
)
from orev3.strategy_lab.metrics import ExperimentMetrics, MetricsEngine
from orev3.strategy_lab.registry import ExperimentRecord, ExperimentRegistry
from orev3.strategy_lab.runner import ExperimentRunner


@dataclass(frozen=True, slots=True)
class ExperimentExecution:
    """Immutable evidence returned by one complete Strategy Lab execution."""

    ranked_candidate_sets: tuple[RankedCandidateSet, ...]
    deployment_decisions: tuple[DeploymentDecision, ...]
    evaluation_results: tuple[EvaluationResult, ...]
    metrics: ExperimentMetrics
    record: ExperimentRecord


@dataclass(frozen=True, slots=True)
class ExecutableExperiment:
    """Compose existing RFC-010 components without taking over their duties."""

    runner: ExperimentRunner
    deployment_model: DeploymentModel
    registry: ExperimentRegistry
    configuration_identifier: str
    implementation_identifier: str
    evaluator: Evaluator = field(default_factory=Evaluator)
    metrics_engine: MetricsEngine = field(default_factory=MetricsEngine)

    def execute(
        self,
        strategy: Strategy,
        *,
        experiment_identifier: str,
    ) -> ExperimentExecution:
        if not isinstance(strategy, Strategy):
            raise TypeError("strategy must implement the Strategy interface")
        if not isinstance(self.deployment_model, DeploymentModel):
            raise TypeError(
                "deployment_model must implement the DeploymentModel interface"
            )
        if not isinstance(self.runner, ExperimentRunner):
            raise TypeError("runner must be an ExperimentRunner")
        if not isinstance(self.registry, ExperimentRegistry):
            raise TypeError("registry must be an ExperimentRegistry")
        if not isinstance(self.evaluator, Evaluator):
            raise TypeError("evaluator must be an Evaluator")
        if not isinstance(self.metrics_engine, MetricsEngine):
            raise TypeError("metrics_engine must be a MetricsEngine")

        lifecycle = _PipelineLifecycle(
            strategy=strategy,
            deployment_model=self.deployment_model,
            evaluator=self.evaluator,
        )
        decisions = self.runner.run(lifecycle)
        results = tuple(lifecycle.evaluation_results)
        metrics = self.metrics_engine.aggregate(results)
        record = ExperimentRecord(
            experiment_identifier=experiment_identifier,
            configuration_identifier=self.configuration_identifier,
            implementation_identifier=self.implementation_identifier,
            metrics=metrics,
        )
        self.registry.register(record)
        return ExperimentExecution(
            ranked_candidate_sets=decisions,
            deployment_decisions=tuple(lifecycle.deployment_decisions),
            evaluation_results=results,
            metrics=metrics,
            record=record,
        )


@dataclass(slots=True)
class _PipelineLifecycle(Strategy):
    strategy: Strategy
    deployment_model: DeploymentModel
    evaluator: Evaluator
    deployment_decisions: list[DeploymentDecision] = field(default_factory=list)
    evaluation_results: list[EvaluationResult] = field(default_factory=list)
    _pending_round_identifier: int | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def initialize(self) -> None:
        self.deployment_decisions.clear()
        self.evaluation_results.clear()
        self._pending_round_identifier = None
        self.strategy.initialize()

    def choose(self, context: DecisionContext) -> RankedCandidateSet:
        if self._pending_round_identifier is not None:
            raise RuntimeError("previous decision has not been evaluated")
        candidates = self.strategy.choose(context)
        if not isinstance(candidates, RankedCandidateSet):
            raise TypeError("Strategy.choose() must return RankedCandidateSet")
        round_identifier = context.information.get("round_id")
        if (
            isinstance(round_identifier, bool)
            or not isinstance(round_identifier, int)
            or round_identifier < 0
        ):
            raise ValueError("context round_id must be a nonnegative integer")
        self.deployment_decisions.append(
            self.deployment_model.allocate(candidates)
        )
        self._pending_round_identifier = round_identifier
        return candidates

    def update(self, result: object) -> None:
        if self._pending_round_identifier is None:
            raise RuntimeError("no deployment decision is awaiting evaluation")
        if not isinstance(result, Mapping):
            raise TypeError("historical outcome must be an immutable mapping")
        winning_square = result.get("winning_square")
        if (
            isinstance(winning_square, bool)
            or not isinstance(winning_square, int)
        ):
            raise ValueError(
                "historical winning_square must be an integer"
            )
        evaluation = self.evaluator.evaluate(
            self.deployment_decisions[-1],
            EvaluationObservation(
                round_identifier=self._pending_round_identifier,
                winning_square_identifier=winning_square,
            ),
        )
        self.evaluation_results.append(evaluation)
        self._pending_round_identifier = None
        self.strategy.update(evaluation)

    def finalize(self) -> None:
        self.strategy.finalize()


__all__ = ("ExecutableExperiment", "ExperimentExecution")
