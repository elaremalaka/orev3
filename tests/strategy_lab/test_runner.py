from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from orev3.historical.models import (
    FinalizedRoundOutcome,
    ObservationReference,
    RoundLifecycleIndexRecord,
    RoundQualityMetadata,
)
from orev3.strategy_lab import (
    DecisionContext,
    ExperimentConfiguration,
    ExperimentRunner,
    RankedCandidate,
    RankedCandidateSet,
    Strategy,
)


class RecordingStrategy(Strategy):
    def __init__(self) -> None:
        self.events: list[str] = []
        self.contexts: list[DecisionContext] = []
        self.outcomes: list[object] = []

    def initialize(self) -> None:
        self.events.append("initialize")

    def choose(self, context: DecisionContext) -> RankedCandidateSet:
        assert not self.outcomes or len(self.outcomes) < len(self.contexts) + 1
        self.events.append(f"choose:{context.information['round_id']}")
        self.contexts.append(context)
        return RankedCandidateSet(
            [
                RankedCandidate(
                    square_identifier=int(context.information["round_id"]) % 25,
                    preference_score=float(len(self.outcomes)),
                )
            ]
        )

    def update(self, result: object) -> None:
        assert isinstance(result, Mapping)
        self.events.append(f"update:{result['winning_square']}")
        self.outcomes.append(result)

    def finalize(self) -> None:
        self.events.append("finalize")


def test_experiment_configuration_is_immutable_and_validated(
    tmp_path: Path,
) -> None:
    configuration = ExperimentConfiguration(
        dataset_path=tmp_path / "rounds.jsonl",
        requested_slots_remaining=5,
        max_slot_distance=2,
    )

    assert configuration.dataset_path == tmp_path / "rounds.jsonl"
    with pytest.raises(FrozenInstanceError):
        configuration.requested_slots_remaining = 6  # type: ignore[misc]
    with pytest.raises(ValueError):
        ExperimentConfiguration(tmp_path, -1)
    with pytest.raises(ValueError):
        ExperimentConfiguration(tmp_path, True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ExperimentConfiguration(tmp_path, 1, -1)
    with pytest.raises(TypeError):
        ExperimentConfiguration(
            tmp_path,
            1,
            skip_missing_outcomes=1,  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError):
        ExperimentConfiguration(
            tmp_path,
            1,
            skip_unavailable_replay_points=1,  # type: ignore[arg-type]
        )


def test_runner_orchestrates_lifecycle_in_chronological_order(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(12, 11))
    strategy = RecordingStrategy()

    decisions = _runner(dataset).run(strategy)

    assert strategy.events == [
        "initialize",
        "choose:11",
        "update:11",
        "choose:12",
        "update:12",
        "finalize",
    ]
    assert tuple(
        decision[0].square_identifier for decision in decisions
    ) == (11, 12)


def test_decision_context_excludes_outcomes_and_replay_internals(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(7,))
    strategy = RecordingStrategy()

    _runner(dataset).run(strategy)

    information = strategy.contexts[0].information
    assert set(information) == {
        "round_id",
        "observed_at_utc",
        "rpc_slot",
        "start_slot",
        "end_slot",
        "slots_elapsed",
        "slots_remaining",
        "board",
        "treasury",
        "round",
    }
    assert {
        "collector_session_id",
        "source_file",
        "source_line_number",
        "winning_square",
        "finalized_outcome",
    }.isdisjoint(information)
    round_information = information["round"]
    assert isinstance(round_information, Mapping)
    assert {"entropy", "slot_hash_hex", "mass", "winning_square"}.isdisjoint(
        round_information
    )
    with pytest.raises(TypeError):
        round_information["round_id"] = 999  # type: ignore[index]


def test_outcome_is_revealed_only_after_choice_and_is_immutable(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(9,))
    strategy = RecordingStrategy()

    _runner(dataset).run(strategy)

    assert strategy.events == [
        "initialize",
        "choose:9",
        "update:9",
        "finalize",
    ]
    outcome = strategy.outcomes[0]
    assert isinstance(outcome, Mapping)
    assert outcome["winning_square"] == 9
    with pytest.raises(TypeError):
        outcome["winning_square"] = 10  # type: ignore[index]


def test_repeated_experiments_are_deterministic(tmp_path: Path) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(2, 1, 3))

    first_strategy = RecordingStrategy()
    second_strategy = RecordingStrategy()
    first = _runner(dataset).run(first_strategy)
    second = _runner(dataset).run(second_strategy)

    assert first == second
    assert first_strategy.events == second_strategy.events
    assert [
        dict(context.information) for context in first_strategy.contexts
    ] == [
        dict(context.information) for context in second_strategy.contexts
    ]
    assert [
        dict(outcome)  # type: ignore[arg-type]
        for outcome in first_strategy.outcomes
    ] == [
        dict(outcome)  # type: ignore[arg-type]
        for outcome in second_strategy.outcomes
    ]


def test_out_of_tolerance_selection_fails_closed_and_finalizes(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(
        tmp_path,
        round_ids=(4,),
        actual_slots_remaining=8,
    )
    strategy = RecordingStrategy()

    with pytest.raises(ValueError, match="outside the configured slot tolerance"):
        _runner(dataset, max_slot_distance=1).run(strategy)

    assert strategy.events == ["initialize", "finalize"]


def test_missing_outcome_fails_after_decision_and_finalizes(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(5,), include_outcome=False)
    strategy = RecordingStrategy()

    with pytest.raises(ValueError, match="finalized historical outcome"):
        _runner(dataset).run(strategy)

    assert strategy.events == ["initialize", "choose:5", "finalize"]
    assert strategy.outcomes == []


def test_partial_mode_skips_missing_outcome_before_strategy_decision(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(
        tmp_path,
        round_ids=(5,),
        include_outcome=False,
    )
    strategy = RecordingStrategy()

    decisions = _runner(
        dataset,
        skip_missing_outcomes=True,
    ).run(strategy)

    assert decisions == ()
    assert strategy.events == [
        "initialize",
        "finalize",
    ]


def test_partial_mode_skips_unavailable_replay_point_deterministically(
    tmp_path: Path,
) -> None:
    dataset = _write_dataset(
        tmp_path,
        round_ids=(4,),
        actual_slots_remaining=8,
    )
    strategy = RecordingStrategy()

    decisions = _runner(
        dataset,
        max_slot_distance=1,
        skip_unavailable_replay_points=True,
    ).run(strategy)

    assert decisions == ()
    assert strategy.events == [
        "initialize",
        "finalize",
    ]


def test_invalid_strategy_decision_fails_closed_and_finalizes(
    tmp_path: Path,
) -> None:
    class InvalidStrategy(RecordingStrategy):
        def choose(self, context: DecisionContext) -> RankedCandidateSet:
            self.events.append("choose")
            return object()  # type: ignore[return-value]

    dataset = _write_dataset(tmp_path, round_ids=(6,))
    strategy = InvalidStrategy()

    with pytest.raises(TypeError, match="must return RankedCandidateSet"):
        _runner(dataset).run(strategy)

    assert strategy.events == ["initialize", "choose", "finalize"]


def test_runner_rejects_objects_outside_strategy_interface(tmp_path: Path) -> None:
    dataset = _write_dataset(tmp_path, round_ids=(1,))

    with pytest.raises(TypeError, match="Strategy interface"):
        _runner(dataset).run(object())  # type: ignore[arg-type]


def _runner(
    dataset: Path,
    *,
    max_slot_distance: int | None = 0,
    skip_missing_outcomes: bool = False,
    skip_unavailable_replay_points: bool = False,
) -> ExperimentRunner:
    return ExperimentRunner(
        ExperimentConfiguration(
            dataset_path=dataset,
            requested_slots_remaining=5,
            max_slot_distance=max_slot_distance,
            skip_missing_outcomes=(
                skip_missing_outcomes
            ),
            skip_unavailable_replay_points=(
                skip_unavailable_replay_points
            ),
        )
    )


def _write_dataset(
    tmp_path: Path,
    *,
    round_ids: tuple[int, ...],
    actual_slots_remaining: int = 5,
    include_outcome: bool = True,
) -> Path:
    raw_path = tmp_path / "observer.jsonl"
    index_path = tmp_path / "rounds.jsonl"
    raw_records: list[dict[str, Any]] = []
    lifecycle_records: list[RoundLifecycleIndexRecord] = []
    base_time = datetime(2026, 1, 1, tzinfo=UTC)

    for line_number, round_id in enumerate(round_ids, start=1):
        start_slot = round_id * 100
        end_slot = start_slot + 20
        rpc_slot = end_slot - actual_slots_remaining
        observed_at = base_time + timedelta(seconds=round_id)
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
                    "miner_counts": list(range(25)),
                    "slot_hash_hex": f"private-replay-hash-{round_id}",
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
        outcome = (
            FinalizedRoundOutcome(
                observed_at_utc=observed_at + timedelta(seconds=30),
                rpc_slot=end_slot + 1,
                entropy=42,
                winning_square=round_id % 25,
                deployed_lamports=[round_id] * 25,
                miner_counts=list(range(25)),
                reward_buckets=[3] * 25,
                total_vaulted=1000,
                total_winnings=300,
                total_miners=25,
                round_motherlode=456,
                top_miner="winner",
            )
            if include_outcome
            else None
        )
        lifecycle_records.append(
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
                finalized_outcome_source=(
                    "observed" if outcome is not None else None
                ),
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
                    finalized_state_observed=outcome is not None,
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
            for record in lifecycle_records
        ),
        encoding="utf-8",
    )
    return index_path
