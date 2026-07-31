from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from itertools import cycle
from pathlib import Path

import pytest

from orev3.dataset.metadata import (
    DatasetMetadata,
    dataset_sha256,
    write_metadata,
)
from orev3.historical.models import (
    FinalizedRoundOutcome,
    ObservationReference,
    RoundLifecycleIndexRecord,
    RoundQualityMetadata,
)
from orev3.strategy_lab import baselines


def test_baseline_cli_executes_every_supported_combination(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = _write_managed_dataset(tmp_path)

    baselines.main(["--dataset", str(dataset)])

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "dataset_version: baseline-fixture-v1" in captured.out
    assert "replay_readiness: COMPLETE" in captured.out
    assert "dataset_completeness: 100.000000%" in captured.out
    assert "evaluated_rounds: 2" in captured.out
    assert captured.out.count("    strategy: ") == 6
    assert captured.out.count("    deployment: ") == 6
    assert captured.out.count("    evaluations: 2") == 6
    assert captured.out.count("    experiment_uuid: ") == 6

    for strategy_name in (
        "equal-distribution",
        "least-crowded",
        "random",
    ):
        for deployment_name in (
            "equal-weight",
            "top-ranked",
        ):
            assert (
                f"  {strategy_name} | {deployment_name} | "
                in captured.out
            )

    assert "recommend" not in captured.out.lower()
    assert "ranking" not in captured.out.lower()


def test_baseline_cli_is_deterministic_except_measured_runtime(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    clock = cycle((10.0, 10.25))
    monkeypatch.setattr(
        baselines.time,
        "perf_counter",
        lambda: next(clock),
    )

    baselines.main(["--dataset", str(dataset)])
    first = capsys.readouterr()
    baselines.main(["--dataset", str(dataset)])
    second = capsys.readouterr()

    assert first == second
    assert first.out.count("runtime_seconds: 0.250000") == 6
    assert first.out.count("| 0.250000 |") == 6


def test_baseline_cli_executes_partial_replay_deterministically(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = _write_managed_dataset(
        tmp_path,
        missing_round_ids=(2,),
    )

    baselines.main(["--dataset", str(dataset)])

    captured = capsys.readouterr()
    assert "WARNING: partial replay" in captured.err
    assert "replay_readiness: PARTIAL" in captured.out
    assert "dataset_completeness: 50.000000%" in captured.out
    assert "evaluated_rounds: 1" in captured.out
    assert captured.out.count("    evaluations: 1") == 6


def test_baseline_cli_fails_closed_on_invalid_dataset(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = tmp_path / "invalid.jsonl"
    dataset.write_text('{"not":"a replay dataset"}\n', encoding="utf-8")
    dataset.with_suffix(".metadata.json").write_text(
        "{}\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as raised:
        baselines.main(["--dataset", str(dataset)])

    assert raised.value.code == 2
    assert "error:" in capsys.readouterr().err


def _write_managed_dataset(
    root: Path,
    *,
    missing_round_ids: tuple[int, ...] = (),
) -> Path:
    raw_path = root / "observer.jsonl"
    dataset_path = root / "replay.jsonl"
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    raw_records: list[dict[str, object]] = []
    lifecycles: list[RoundLifecycleIndexRecord] = []

    for line_number, round_identifier in enumerate((1, 2), start=1):
        observed_at = base_time + timedelta(seconds=round_identifier)
        start_slot = round_identifier * 100
        end_slot = start_slot + 20
        rpc_slot = end_slot - 5
        miner_counts = tuple(range(25))
        raw_records.append(
            {
                "schema_version": 2,
                "collector_session_id": f"session-{round_identifier}",
                "observed_at_utc": observed_at.isoformat(),
                "rpc_slot": rpc_slot,
                "board": {
                    "round_id": round_identifier,
                    "start_slot": start_slot,
                    "end_slot": end_slot,
                    "production_cost_ema": 1,
                },
                "treasury": {"motherlode": 2},
                "round": {
                    "round_id": round_identifier,
                    "deployed_lamports": [1] * 25,
                    "mass": [0] * 25,
                    "miner_counts": miner_counts,
                    "slot_hash_hex": "00" * 32,
                    "expires_at": end_slot,
                    "motherlode": 2,
                    "rewards": [0] * 25,
                    "total_vaulted": 0,
                    "total_winnings": 0,
                    "total_miners": 25,
                    "top_miner": "miner",
                    "entropy": None,
                },
            }
        )
        outcome = (
            None
            if round_identifier in missing_round_ids
            else FinalizedRoundOutcome(
                observed_at_utc=observed_at + timedelta(seconds=1),
                rpc_slot=end_slot + 1,
                entropy=0,
                winning_square=0,
                deployed_lamports=[1] * 25,
                miner_counts=miner_counts,
                reward_buckets=[0] * 25,
                total_vaulted=1,
                total_winnings=1,
                total_miners=25,
                round_motherlode=2,
                top_miner="winner",
            )
        )
        lifecycles.append(
            RoundLifecycleIndexRecord(
                round_id=round_identifier,
                start_slot=start_slot,
                end_slot=end_slot,
                first_observed_at_utc=observed_at,
                last_observed_at_utc=observed_at,
                first_observed_rpc_slot=rpc_slot,
                last_observed_rpc_slot=rpc_slot,
                observation_count=1,
                collector_session_ids=[f"session-{round_identifier}"],
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
    dataset_path.write_text(
        "".join(record.model_dump_json() + "\n" for record in lifecycles),
        encoding="utf-8",
    )
    write_metadata(
        DatasetMetadata(
            dataset_version="baseline-fixture-v1",
            created_at_utc=base_time,
            source_collection=(str(raw_path),),
            malformed_source_record_count=0,
            replay_round_count=2,
            snapshot_count=2,
            complete_round_count=2,
            incomplete_round_count=0,
            missing_outcome_count=len(missing_round_ids),
            integrity_status="valid",
            ready_for_replay=not missing_round_ids,
            dataset_sha256=dataset_sha256(dataset_path),
        ),
        dataset_path.with_suffix(".metadata.json"),
    )
    return dataset_path
