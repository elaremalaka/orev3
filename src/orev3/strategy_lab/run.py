"""Command-line execution for deterministic RFC-010 experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
import sys
from collections.abc import Callable
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from orev3.dataset.management import inspect_replay_dataset
from orev3.strategy_lab.deployment import (
    DeploymentModel,
    EqualWeightDeploymentModel,
    TopRankedDeploymentModel,
)
from orev3.strategy_lab.experiment import ExecutableExperiment
from orev3.strategy_lab.registry import ExperimentRegistry
from orev3.strategy_lab.readiness import (
    ReplayReadiness,
    assess_replay_readiness,
)
from orev3.strategy_lab.runner import (
    ExperimentConfiguration,
    ExperimentRunner,
)
from orev3.strategy_lab.strategies import (
    EqualDistributionStrategy,
    LeastCrowdedStrategy,
    RandomStrategy,
)
from orev3.strategy_lab.interfaces import Strategy


StrategyFactory = Callable[[], Strategy]
DeploymentFactory = Callable[[], DeploymentModel]

STRATEGIES: dict[str, StrategyFactory] = {
    "equal-distribution": EqualDistributionStrategy,
    "least-crowded": LeastCrowdedStrategy,
    "random": RandomStrategy,
}

DEPLOYMENTS: dict[str, DeploymentFactory] = {
    "equal-weight": EqualWeightDeploymentModel,
    "top-ranked": TopRankedDeploymentModel,
}

IMPLEMENTATION_IDENTIFIER = "rfc010-strategy-lab-cli-v2"


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = _parser()
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
) -> None:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.list_strategies:
        _print_registry("strategies", STRATEGIES)
    if args.list_deployments:
        _print_registry(
            "deployments",
            DEPLOYMENTS,
        )
    if (
        args.list_strategies
        or args.list_deployments
    ):
        return

    if args.dataset is None:
        parser.error(
            "--dataset is required to execute an experiment"
        )
    if args.strategy is None:
        parser.error(
            "--strategy is required to execute an experiment"
        )
    if args.deployment is None:
        parser.error(
            "--deployment is required to execute an experiment"
        )

    try:
        _execute(args)
    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        parser.exit(
            2,
            f"error: {exc}\n",
        )


def _execute(
    args: argparse.Namespace,
) -> None:
    dataset_path = args.dataset.resolve()
    metadata_path = dataset_path.with_suffix(
        ".metadata.json"
    )
    inspection = inspect_replay_dataset(
        dataset_path,
        metadata_path,
    )
    readiness = assess_replay_readiness(
        inspection
    )
    if (
        readiness.readiness
        is ReplayReadiness.INVALID
    ):
        raise ValueError(
            "dataset replay integrity is invalid: "
            + "; ".join(readiness.reasons)
        )
    if (
        readiness.readiness
        is ReplayReadiness.PARTIAL
    ):
        print(
            "WARNING: partial replay; only replay-eligible "
            "rounds with finalized outcomes will be evaluated.",
            file=sys.stderr,
        )

    strategy = STRATEGIES[
        args.strategy
    ]()
    deployment_model = DEPLOYMENTS[
        args.deployment
    ]()
    configuration_identifier = (
        _configuration_identifier(
            dataset_sha256=(
                inspection.metadata
                .dataset_sha256
            ),
            dataset_version=(
                inspection.metadata
                .dataset_version
            ),
            strategy=args.strategy,
            deployment=args.deployment,
            requested_slots_remaining=(
                args.slots_remaining
            ),
            max_slot_distance=(
                args.max_slot_distance
            ),
            replay_readiness=(
                readiness.readiness.value
            ),
            finalized_outcome_count=(
                readiness.finalized_outcome_count
            ),
            skipped_round_count=(
                readiness.skipped_round_count
            ),
        )
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
    runner = ExperimentRunner(
        ExperimentConfiguration(
            dataset_path=dataset_path,
            requested_slots_remaining=(
                args.slots_remaining
            ),
            max_slot_distance=(
                args.max_slot_distance
            ),
            skip_missing_outcomes=(
                readiness.readiness
                is ReplayReadiness.PARTIAL
            ),
            skip_unavailable_replay_points=(
                readiness.readiness
                is ReplayReadiness.PARTIAL
            ),
        )
    )

    started_at = time.perf_counter()

    if args.output is None:
        with tempfile.TemporaryDirectory(
            prefix="orev3-strategy-lab-"
        ) as temporary_directory:
            execution = _run_experiment(
                runner=runner,
                strategy=strategy,
                deployment_model=deployment_model,
                registry_path=(
                    Path(temporary_directory)
                    / "experiments.jsonl"
                ),
                configuration_identifier=(
                    configuration_identifier
                ),
                experiment_identifier=(
                    experiment_identifier
                ),
            )
    else:
        execution = _run_experiment(
            runner=runner,
            strategy=strategy,
            deployment_model=deployment_model,
            registry_path=args.output,
            configuration_identifier=(
                configuration_identifier
            ),
            experiment_identifier=(
                experiment_identifier
            ),
        )

    runtime_seconds = (
        time.perf_counter() - started_at
    )
    validation = inspection.validation
    metrics = execution.metrics
    skipped_round_count = (
        readiness.replay_round_count
        - metrics.evaluation_count
    )

    print("ORE Miner V3 — Strategy Lab Experiment")
    print("Dataset")
    print(
        "  dataset_version: "
        f"{inspection.metadata.dataset_version}"
    )
    print(
        "  replay_rounds: "
        f"{validation.replay_round_count}"
    )
    print(
        "  replay_readiness: "
        f"{readiness.readiness.value}"
    )
    print(
        "  dataset_integrity: "
        + (
            "valid"
            if readiness.integrity_valid
            else "invalid"
        )
    )
    print(
        "  dataset_completeness: "
        f"{readiness.completeness_percentage:.6f}%"
    )
    print(
        "  date_range: "
        f"{validation.first_observed_at_utc} .. "
        f"{validation.last_observed_at_utc}"
    )
    print("Experiment")
    print(f"  strategy: {args.strategy}")
    print(
        "  deployment_model: "
        f"{args.deployment}"
    )
    print(
        "  evaluated_rounds: "
        f"{metrics.evaluation_count}"
    )
    print(
        "  skipped_rounds: "
        f"{skipped_round_count}"
    )
    print(
        "  finalized_outcomes_available: "
        f"{readiness.finalized_outcome_count}"
    )
    print("Results")
    print(
        "  evaluations: "
        f"{metrics.evaluation_count}"
    )
    print(f"  hits: {metrics.hit_count}")
    print(f"  misses: {metrics.miss_count}")
    print(
        "  hit_rate: "
        f"{_format_rate(metrics.hit_rate)}"
    )
    print(
        "  runtime_seconds: "
        f"{runtime_seconds:.6f}"
    )
    print(
        "  experiment_uuid: "
        f"{execution.record.experiment_identifier}"
    )
    if args.output is not None:
        print(
            "  output: "
            f"{args.output}"
        )


def _run_experiment(
    *,
    runner: ExperimentRunner,
    strategy: Strategy,
    deployment_model: DeploymentModel,
    registry_path: Path,
    configuration_identifier: str,
    experiment_identifier: str,
):
    experiment = ExecutableExperiment(
        runner=runner,
        deployment_model=deployment_model,
        registry=ExperimentRegistry(
            registry_path
        ),
        configuration_identifier=(
            configuration_identifier
        ),
        implementation_identifier=(
            IMPLEMENTATION_IDENTIFIER
        ),
    )
    return experiment.execute(
        strategy,
        experiment_identifier=(
            experiment_identifier
        ),
    )


def _configuration_identifier(
    **values: object,
) -> str:
    canonical = json.dumps(
        values,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return (
        "rfc010-configuration-sha256:"
        + hashlib.sha256(canonical).hexdigest()
    )


def _format_rate(
    value: float | None,
) -> str:
    return (
        "n/a"
        if value is None
        else f"{value:.6f}"
    )


def _print_registry(
    name: str,
    registry: dict[str, object],
) -> None:
    print(f"{name}:")
    for item in sorted(registry):
        print(f"  {item}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Execute a deterministic RFC-010 "
            "Strategy Lab experiment."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        help=(
            "Managed replay dataset JSONL. "
            "Metadata is read from the matching "
            ".metadata.json path."
        ),
    )
    parser.add_argument(
        "--strategy",
        choices=tuple(sorted(STRATEGIES)),
    )
    parser.add_argument(
        "--deployment",
        choices=tuple(sorted(DEPLOYMENTS)),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Optional append-only ExperimentRecord "
            "JSONL path."
        ),
    )
    parser.add_argument(
        "--list-strategies",
        action="store_true",
    )
    parser.add_argument(
        "--list-deployments",
        action="store_true",
    )
    parser.add_argument(
        "--slots-remaining",
        type=int,
        default=5,
        help="Replay decision boundary. Default: 5.",
    )
    parser.add_argument(
        "--max-slot-distance",
        type=int,
        default=3,
        help="Maximum replay selection distance. Default: 3.",
    )
    return parser


if __name__ == "__main__":
    main()


__all__ = (
    "DEPLOYMENTS",
    "STRATEGIES",
    "main",
    "parse_args",
)
