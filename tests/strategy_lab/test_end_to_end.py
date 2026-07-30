from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

from orev3.historical.models import (
    FinalizedRoundOutcome,
    ObservationReference,
    RoundLifecycleIndexRecord,
    RoundQualityMetadata,
)
from orev3.strategy_lab import (
    DecisionContext,
    EqualDistributionStrategy,
    EqualWeightDeploymentModel,
    EvaluationResult,
    ExecutableExperiment,
    ExperimentConfiguration,
    ExperimentRegistry,
    ExperimentRunner,
    LeastCrowdedStrategy,
    RankedCandidateSet,
    Strategy,
    TopRankedDeploymentModel,
)


class ContextBoundaryStrategy(Strategy):
    def __init__(self) -> None:
        self.delegate = LeastCrowdedStrategy()
        self.contexts: list[DecisionContext] = []
        self.results: list[EvaluationResult] = []

    def initialize(self) -> None:
        self.delegate.initialize()

    def choose(self, context: DecisionContext) -> RankedCandidateSet:
        self.contexts.append(context)
        return self.delegate.choose(context)

    def update(self, result: object) -> None:
        assert isinstance(result, EvaluationResult)
        self.results.append(result)
        self.delegate.update(result)

    def finalize(self) -> None:
        self.delegate.finalize()


def test_complete_pipeline_is_deterministic_from_replay_through_registry(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(3, 1, 2))
    first = _execute(
        dataset=dataset,
        registry_path=tmp_path / "first.jsonl",
        strategy=LeastCrowdedStrategy(),
        deployment_model=TopRankedDeploymentModel(),
    )
    second = _execute(
        dataset=dataset,
        registry_path=tmp_path / "second.jsonl",
        strategy=LeastCrowdedStrategy(),
        deployment_model=TopRankedDeploymentModel(),
    )

    assert first == second
    assert first.metrics.evaluation_count == 3
    assert len(first.ranked_candidate_sets) == 3
    assert len(first.deployment_decisions) == 3
    assert len(first.evaluation_results) == 3
    assert first.record.metrics is first.metrics
    assert (tmp_path / "first.jsonl").read_bytes() == (
        tmp_path / "second.jsonl"
    ).read_bytes()
    assert ExperimentRegistry(tmp_path / "first.jsonl").records() == (
        first.record,
    )


def test_changing_strategy_changes_only_strategy_originated_behavior(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(8, 9))
    least_crowded = _execute(
        dataset=dataset,
        registry_path=tmp_path / "least.jsonl",
        strategy=LeastCrowdedStrategy(),
        deployment_model=TopRankedDeploymentModel(),
        experiment_identifier="00000000-0000-4000-8000-000000000011",
    )
    equal = _execute(
        dataset=dataset,
        registry_path=tmp_path / "equal.jsonl",
        strategy=EqualDistributionStrategy(),
        deployment_model=TopRankedDeploymentModel(),
        experiment_identifier="00000000-0000-4000-8000-000000000012",
    )

    assert least_crowded.ranked_candidate_sets != equal.ranked_candidate_sets
    assert all(
        decision[0].metadata["deployment_model"] == "top_ranked"
        for decision in (
            *least_crowded.deployment_decisions,
            *equal.deployment_decisions,
        )
    )
    assert (
        least_crowded.record.configuration_identifier
        == equal.record.configuration_identifier
    )
    assert (
        least_crowded.record.implementation_identifier
        == equal.record.implementation_identifier
    )


def test_changing_deployment_changes_only_deployment_originated_behavior(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(14, 15))
    top_ranked = _execute(
        dataset=dataset,
        registry_path=tmp_path / "top.jsonl",
        strategy=LeastCrowdedStrategy(),
        deployment_model=TopRankedDeploymentModel(),
        experiment_identifier="00000000-0000-4000-8000-000000000013",
    )
    equal_weight = _execute(
        dataset=dataset,
        registry_path=tmp_path / "weighted.jsonl",
        strategy=LeastCrowdedStrategy(),
        deployment_model=EqualWeightDeploymentModel(),
        experiment_identifier="00000000-0000-4000-8000-000000000014",
    )

    assert top_ranked.ranked_candidate_sets == equal_weight.ranked_candidate_sets
    assert top_ranked.deployment_decisions != equal_weight.deployment_decisions
    assert all(len(decision) == 1 for decision in top_ranked.deployment_decisions)
    assert all(
        len(decision) == 25 for decision in equal_weight.deployment_decisions
    )


def test_pipeline_never_exposes_future_information_to_strategy(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(20, 21))
    strategy = ContextBoundaryStrategy()

    execution = _execute(
        dataset=dataset,
        registry_path=tmp_path / "boundary.jsonl",
        strategy=strategy,
        deployment_model=TopRankedDeploymentModel(),
        experiment_identifier="00000000-0000-4000-8000-000000000015",
    )

    assert len(strategy.contexts) == 2
    assert tuple(strategy.results) == execution.evaluation_results
    for context in strategy.contexts:
        assert {
            "winning_square",
            "finalized_outcome",
            "entropy",
            "slot_hash_hex",
        }.isdisjoint(context.information)
        round_information = context.information["round"]
        assert isinstance(round_information, Mapping)
        assert {
            "winning_square",
            "entropy",
            "slot_hash_hex",
            "mass",
        }.isdisjoint(round_information)


def _execute(
    *,
    dataset: Path,
    registry_path: Path,
    strategy: Strategy,
    deployment_model,
    experiment_identifier: str = "00000000-0000-4000-8000-000000000010",
):
    experiment = ExecutableExperiment(
        runner=ExperimentRunner(
            ExperimentConfiguration(
                dataset_path=dataset,
                requested_slots_remaining=5,
                max_slot_distance=0,
            )
        ),
        deployment_model=deployment_model,
        registry=ExperimentRegistry(registry_path),
        configuration_identifier="rfc010-e2e-configuration-v1",
        implementation_identifier="rfc010-phase6-reference-v1",
    )
    return experiment.execute(
        strategy,
        experiment_identifier=experiment_identifier,
    )


def _write_dataset(tmp_path: Path, *, round_ids: tuple[int, ...]) -> Path:
    raw_path = tmp_path / "observer.jsonl"
    index_path = tmp_path / "rounds.jsonl"
    raw_records: list[dict[str, object]] = []
    lifecycles: list[RoundLifecycleIndexRecord] = []
    base_time = datetime(2026, 1, 1, tzinfo=UTC)

    for line_number, round_id in enumerate(round_ids, start=1):
        start_slot = round_id * 100
        end_slot = start_slot + 20
        rpc_slot = end_slot - 5
        observed_at = base_time + timedelta(seconds=round_id)
        miner_counts = tuple((square + round_id) % 25 for square in range(25))
        raw_records.append(
            {
                "schema_version": 2,
                "observed_at_utc": observed_at.isoformat(),
                "rpc_slot": rpc_slot,
                "collector_session_id": f"session-{round_id}",
                "board": {
                    "round_id": round_id,
                    "start_slot": start_slot,
                    "end_slot": end_slot,
                    "production_cost_ema": 123,
                },
                "treasury": {"motherlode": 456},
                "round": {
                    "round_id": round_id,
                    "deployed_lamports": [round_id] * 25,
                    "mass": [0] * 25,
                    "miner_counts": miner_counts,
                    "slot_hash_hex": f"replay-only-{round_id}",
                    "expires_at": end_slot,
                    "motherlode": 456,
                    "rewards": [2] * 25,
                    "total_vaulted": 1000,
                    "total_winnings": 200,
                    "total_miners": 25,
                    "top_miner": "miner",
                    "entropy": 999,
                },
            }
        )
        outcome = FinalizedRoundOutcome(
            observed_at_utc=observed_at + timedelta(seconds=30),
            rpc_slot=end_slot + 1,
            entropy=42,
            winning_square=round_id % 25,
            deployed_lamports=[round_id] * 25,
            miner_counts=miner_counts,
            reward_buckets=[3] * 25,
            total_vaulted=1000,
            total_winnings=300,
            total_miners=25,
            round_motherlode=456,
            top_miner="winner",
        )
        lifecycles.append(
            RoundLifecycleIndexRecord(
                round_id=round_id,
                start_slot=start_slot,
                end_slot=end_slot,
                first_observed_at_utc=observed_at,
                last_observed_at_utc=observed_at,
                first_observed_rpc_slot=rpc_slot,
                last_observed_rpc_slot=rpc_slot,
                observation_count=1,
                collector_session_ids=[f"session-{round_id}"],
                source_schema_versions=[2],
                source_files=[str(raw_path)],
                observation_references=[
                    ObservationReference(
                        source_file=str(raw_path),
                        source_line_number=line_number,
                        observed_at_utc=observed_at,
                        rpc_slot=rpc_slot,
                    )
                ],
                finalized_outcome=outcome,
                finalized_outcome_source="observed",
                quality=RoundQualityMetadata(
                    coverage_status="complete",
                    initialization_state_observed=True,
                    rpc_slot_regression_count=0,
                    largest_rpc_slot_regression=0,
                    duplicate_rpc_slot_count=0,
                    max_observation_gap_seconds=0.0,
                    significant_gap_count=0,
                    significant_gap_threshold_seconds=10.0,
                    collector_session_count=1,
                    finalized_state_observed=True,
                ),
            )
        )

    raw_path.write_text(
        "".join(
            json.dumps(record, sort_keys=True) + "\n"
            for record in raw_records
        ),
        encoding="utf-8",
    )
    index_path.write_text(
        "".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True) + "\n"
            for record in lifecycles
        ),
        encoding="utf-8",
    )
    return index_path
