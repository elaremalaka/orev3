"""Reproducible baseline experiments for the RFC-010 Strategy Laboratory."""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from orev3.dataset.management import (
    DEFAULT_DATASET_PATH,
    inspect_replay_dataset,
)
from orev3.strategy_lab.experiment import (
    ExecutableExperiment,
    ExperimentExecution,
)
from orev3.strategy_lab.readiness import (
    ReplayReadiness,
    ReplayReadinessAssessment,
    assess_replay_readiness,
)
from orev3.strategy_lab.registry import ExperimentRegistry
from orev3.strategy_lab.run import (
    DEPLOYMENTS,
    IMPLEMENTATION_IDENTIFIER,
    STRATEGIES,
    _configuration_identifier,
)
from orev3.strategy_lab.runner import (
    ExperimentConfiguration,
    ExperimentRunner,
)


@dataclass(frozen=True, slots=True)
class _BaselineExecution:
    strategy_name: str
    deployment_name: str
    runtime_seconds: float
    execution: ExperimentExecution


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return _parser().parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        _execute(args)
    except (OSError, TypeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


def _execute(args: argparse.Namespace) -> None:
    dataset_path = args.dataset.resolve()
    inspection = inspect_replay_dataset(
        dataset_path,
        dataset_path.with_suffix(".metadata.json"),
    )
    readiness = assess_replay_readiness(inspection)
    if readiness.readiness is ReplayReadiness.INVALID:
        raise ValueError(
            "dataset replay integrity is invalid: "
            + "; ".join(readiness.reasons)
        )
    if readiness.readiness is ReplayReadiness.PARTIAL:
        print(
            "WARNING: partial replay; baseline experiments evaluate only "
            "replay-eligible rounds with finalized outcomes.",
            file=sys.stderr,
        )

    runner = ExperimentRunner(
        ExperimentConfiguration(
            dataset_path=dataset_path,
            requested_slots_remaining=5,
            max_slot_distance=3,
            skip_missing_outcomes=(
                readiness.readiness is ReplayReadiness.PARTIAL
            ),
            skip_unavailable_replay_points=(
                readiness.readiness is ReplayReadiness.PARTIAL
            ),
        )
    )
    with tempfile.TemporaryDirectory(
        prefix="orev3-strategy-lab-baselines-"
    ) as temporary_directory:
        registry = ExperimentRegistry(
            Path(temporary_directory) / "experiments.jsonl"
        )
        executions = tuple(
            _run_baseline(
                strategy_name=strategy_name,
                deployment_name=deployment_name,
                runner=runner,
                registry=registry,
                dataset_sha256=inspection.metadata.dataset_sha256,
                dataset_version=inspection.metadata.dataset_version,
                readiness=readiness,
            )
            for strategy_name, deployment_name in product(
                sorted(STRATEGIES),
                sorted(DEPLOYMENTS),
            )
        )

    _print_report(
        dataset_version=inspection.metadata.dataset_version,
        readiness=readiness,
        executions=executions,
    )


def _run_baseline(
    *,
    strategy_name: str,
    deployment_name: str,
    runner: ExperimentRunner,
    registry: ExperimentRegistry,
    dataset_sha256: str,
    dataset_version: str,
    readiness: ReplayReadinessAssessment,
) -> _BaselineExecution:
    configuration_identifier = _configuration_identifier(
        dataset_sha256=dataset_sha256,
        dataset_version=dataset_version,
        strategy=strategy_name,
        deployment=deployment_name,
        requested_slots_remaining=5,
        max_slot_distance=3,
        replay_readiness=readiness.readiness.value,
        finalized_outcome_count=readiness.finalized_outcome_count,
        skipped_round_count=readiness.skipped_round_count,
    )
    experiment_identifier = str(
        uuid5(
            NAMESPACE_URL,
            (
                "orev3:rfc010:"
                f"{configuration_identifier}:"
                f"{IMPLEMENTATION_IDENTIFIER}"
            ),
        )
    )
    experiment = ExecutableExperiment(
        runner=runner,
        deployment_model=DEPLOYMENTS[deployment_name](),
        registry=registry,
        configuration_identifier=configuration_identifier,
        implementation_identifier=IMPLEMENTATION_IDENTIFIER,
    )
    started_at = time.perf_counter()
    execution = experiment.execute(
        STRATEGIES[strategy_name](),
        experiment_identifier=experiment_identifier,
    )
    return _BaselineExecution(
        strategy_name=strategy_name,
        deployment_name=deployment_name,
        runtime_seconds=time.perf_counter() - started_at,
        execution=execution,
    )


def _print_report(
    *,
    dataset_version: str,
    readiness: ReplayReadinessAssessment,
    executions: tuple[_BaselineExecution, ...],
) -> None:
    evaluated_counts = {
        baseline.execution.metrics.evaluation_count for baseline in executions
    }
    if len(evaluated_counts) != 1:
        raise ValueError(
            "baseline experiments produced inconsistent evaluation counts"
        )
    evaluated_rounds = next(iter(evaluated_counts))

    print("ORE Miner V3 — Strategy Lab Baseline Research Suite")
    print("Dataset")
    print(f"  dataset_version: {dataset_version}")
    print(f"  replay_readiness: {readiness.readiness.value}")
    print(
        "  dataset_completeness: "
        f"{readiness.completeness_percentage:.6f}%"
    )
    print(f"  evaluated_rounds: {evaluated_rounds}")
    print("Experiments")
    for index, baseline in enumerate(executions, start=1):
        metrics = baseline.execution.metrics
        print(f"  Experiment {index}")
        print(f"    strategy: {baseline.strategy_name}")
        print(f"    deployment: {baseline.deployment_name}")
        print(f"    evaluations: {metrics.evaluation_count}")
        print(f"    hits: {metrics.hit_count}")
        print(f"    misses: {metrics.miss_count}")
        print(f"    hit_rate: {_format_rate(metrics.hit_rate)}")
        print(f"    runtime_seconds: {baseline.runtime_seconds:.6f}")
        print(
            "    experiment_uuid: "
            f"{baseline.execution.record.experiment_identifier}"
        )

    print("Comparison")
    print(
        "  strategy | deployment | evaluations | hits | misses | hit_rate "
        "| runtime_seconds | experiment_uuid"
    )
    for baseline in executions:
        metrics = baseline.execution.metrics
        print(
            f"  {baseline.strategy_name} | {baseline.deployment_name} | "
            f"{metrics.evaluation_count} | {metrics.hit_count} | "
            f"{metrics.miss_count} | {_format_rate(metrics.hit_rate)} | "
            f"{baseline.runtime_seconds:.6f} | "
            f"{baseline.execution.record.experiment_identifier}"
        )


def _format_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Execute every built-in RFC-010 Strategy Lab baseline experiment."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help=(
            "Managed replay dataset JSONL. Default: "
            f"{DEFAULT_DATASET_PATH}."
        ),
    )
    return parser


if __name__ == "__main__":
    main()


__all__ = ("main", "parse_args")
