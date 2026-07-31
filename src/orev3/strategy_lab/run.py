"""Command-line execution for deterministic RFC-010/RFC-011 experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
import sys
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from orev3.dataset.management import inspect_replay_dataset
from orev3.strategy_lab.deployment import (
    DeploymentModel,
    EqualWeightDeploymentModel,
    TopRankedDeploymentModel,
)
from orev3.strategy_lab.experiment import ExecutableExperiment
from orev3.strategy_lab.economic_cli import (
    dataset_and_replay_identities,
    execute_economic_simulation,
    load_economic_scenario,
    write_economic_simulation_record,
)
from orev3.strategy_lab.economic_record import EconomicSimulationRecord
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

IMPLEMENTATION_IDENTIFIER = "rfc010-strategy-lab-cli-v3"


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
    if args.economic_scenario is None and (
        args.deployment_budget_lamports is not None
        or args.protocol_revision is not None
    ):
        parser.error(
            "--deployment-budget-lamports and --protocol-revision require "
            "--economic-scenario"
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
    runner_configuration = ExperimentConfiguration(
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
    runner = ExperimentRunner(runner_configuration)
    economic_scenario = None
    if args.economic_scenario is not None:
        dataset_identity, replay_identity = dataset_and_replay_identities(
            dataset_sha256=inspection.metadata.dataset_sha256,
            configuration_identifier=configuration_identifier,
        )
        economic_scenario = load_economic_scenario(
            args.economic_scenario.resolve(),
            dataset_identity=dataset_identity,
            replay_identity=replay_identity,
            deployment_budget_lamports=args.deployment_budget_lamports,
            protocol_revision=args.protocol_revision,
        )

    started_at = time.perf_counter()

    if args.output is None or economic_scenario is not None:
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

    economic_record: EconomicSimulationRecord | None = None
    if economic_scenario is not None:
        economic_record = execute_economic_simulation(
            experiment=execution,
            configuration=runner_configuration,
            scenario=economic_scenario,
        )
        if args.output is not None:
            write_economic_simulation_record(economic_record, args.output)

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
    print(
        "  date_range: "
        f"{validation.first_observed_at_utc} .. "
        f"{validation.last_observed_at_utc}"
    )
    print("Decision")
    print(f"  strategy: {args.strategy}")
    print(
        "  deployment_model: "
        f"{args.deployment}"
    )
    if economic_scenario is not None:
        print(
            "  economic_scenario: "
            f"{args.economic_scenario}"
        )
        print(
            "  economic_scenario_identity: "
            f"{economic_scenario.scenario_identity}"
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
    if economic_record is not None:
        _print_economic_summary(economic_record)
    if args.output is not None:
        print(
            "  output: "
            f"{args.output}"
        )


def _print_economic_summary(record: EconomicSimulationRecord) -> None:
    metrics = record.economic_experiment_metrics
    terminal = record.terminal_participant_state
    total_fees = (
        metrics.total_protocol_fees_lamports
        + metrics.total_transaction_fees_lamports
        + metrics.total_priority_fees_lamports
        + metrics.total_checkpoint_costs_lamports
    )

    print("Economics")
    print(f"  settled_rounds: {metrics.settled_round_count}")
    print(f"  rejected_rounds: {metrics.rejected_round_count}")
    print(f"  unincluded_rounds: {metrics.unincluded_round_count}")
    print(
        "  missing_outcome_rounds: "
        f"{metrics.missing_outcome_round_count}"
    )
    print(
        "  deployed_sol_lamports: "
        f"{metrics.total_deployed_lamports}"
    )
    print(
        "  returned_sol_lamports: "
        f"{metrics.total_returned_sol_lamports}"
    )
    print(
        "  net_sol_change_lamports: "
        f"{metrics.net_sol_change_lamports}"
    )
    print(f"  ore_earned_raw: {metrics.total_ore_earned_raw}")
    print(f"  total_fees_lamports: {total_fees}")
    print(
        "  capture_efficiency: "
        f"{_format_fraction(metrics.capture_efficiency)}"
    )
    print(
        "  economic_completeness: "
        f"{_format_fraction(metrics.completeness_percentage)}%"
    )
    print("Simulation")
    print(
        "  participant_ending_sol_lamports: "
        f"{terminal.available_sol_lamports + terminal.accrued_sol_lamports}"
    )
    print(f"  participant_ending_ore_raw: {terminal.accrued_ore}")
    print(
        "  economic_simulation_record_identity: "
        f"{record.record_identity}"
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


def _format_fraction(value: Fraction | None) -> str:
    if value is None:
        return "n/a"
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


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
            "Execute a deterministic RFC-010 Strategy Lab experiment, with "
            "optional RFC-011 economic simulation."
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
            "Optional output path. Writes append-only RFC-010 metadata for "
            "a decision-only run, or one immutable RFC-011 simulation record "
            "when --economic-scenario is selected."
        ),
    )
    parser.add_argument(
        "--economic-scenario",
        type=Path,
        help="Immutable RFC-011 Economic Scenario template JSON.",
    )
    parser.add_argument(
        "--deployment-budget-lamports",
        type=int,
        help=(
            "Optional immutable per-round deployment-budget override in "
            "lamports. Requires --economic-scenario."
        ),
    )
    parser.add_argument(
        "--protocol-revision",
        help=(
            "Optional immutable protocol-revision override. Requires "
            "--economic-scenario."
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
