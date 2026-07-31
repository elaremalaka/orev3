from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
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
from orev3.strategy_lab.run import main


def test_cli_lists_registered_components(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(
        [
            "--list-strategies",
            "--list-deployments",
        ]
    )

    assert capsys.readouterr().out == (
        "strategies:\n"
        "  equal-distribution\n"
        "  least-crowded\n"
        "  random\n"
        "deployments:\n"
        "  equal-weight\n"
        "  top-ranked\n"
    )


def test_cli_executes_complete_pipeline_and_serializes_record(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = _write_managed_dataset(
        tmp_path
    )
    output = tmp_path / "experiment.jsonl"

    main(
        [
            "--dataset",
            str(dataset),
            "--strategy",
            "least-crowded",
            "--deployment",
            "top-ranked",
            "--output",
            str(output),
            "--max-slot-distance",
            "0",
        ]
    )

    report = capsys.readouterr().out
    record = json.loads(
        output.read_text(encoding="utf-8")
    )
    assert "dataset_version: cli-fixture-v1" in report
    assert "replay_rounds: 2" in report
    assert "strategy: least-crowded" in report
    assert "deployment_model: top-ranked" in report
    assert "evaluations: 2" in report
    assert "hits: 2" in report
    assert "misses: 0" in report
    assert "hit_rate: 1.000000" in report
    assert (
        f"experiment_uuid: "
        f"{record['experiment_identifier']}"
        in report
    )
    assert record["metrics"]["evaluation_count"] == 2


def test_repeated_cli_execution_has_deterministic_metrics_and_registry_record(
    tmp_path: Path,
) -> None:
    dataset = _write_managed_dataset(
        tmp_path
    )
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    arguments = [
        "--dataset",
        str(dataset),
        "--strategy",
        "random",
        "--deployment",
        "equal-weight",
        "--max-slot-distance",
        "0",
    ]

    main([*arguments, "--output", str(first)])
    main([*arguments, "--output", str(second)])

    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize(
    ("option", "value"),
    (
        ("--strategy", "unknown"),
        ("--deployment", "unknown"),
    ),
)
def test_cli_rejects_unknown_registered_component(
    option: str,
    value: str,
) -> None:
    with pytest.raises(SystemExit) as raised:
        main([option, value])

    assert raised.value.code == 2


def test_cli_fails_closed_on_invalid_dataset(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = tmp_path / "invalid.jsonl"
    dataset.write_text(
        '{"not":"a replay dataset"}\n',
        encoding="utf-8",
    )
    metadata = dataset.with_suffix(
        ".metadata.json"
    )
    metadata.write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "--dataset",
                str(dataset),
                "--strategy",
                "least-crowded",
                "--deployment",
                "top-ranked",
            ]
        )

    assert raised.value.code == 2
    assert "error:" in capsys.readouterr().err


def _write_managed_dataset(
    root: Path,
) -> Path:
    raw_path = root / "observer.jsonl"
    dataset_path = root / "replay.jsonl"
    base_time = datetime(
        2026,
        1,
        1,
        tzinfo=UTC,
    )
    raw_records: list[dict[str, object]] = []
    lifecycles: list[
        RoundLifecycleIndexRecord
    ] = []

    for line_number, round_id in enumerate(
        (1, 2),
        start=1,
    ):
        observed_at = (
            base_time
            + timedelta(seconds=round_id)
        )
        start_slot = round_id * 100
        end_slot = start_slot + 20
        rpc_slot = end_slot - 5
        miner_counts = tuple(
            range(25)
        )
        raw_records.append(
            {
                "schema_version": 2,
                "collector_session_id": (
                    f"session-{round_id}"
                ),
                "observed_at_utc": (
                    observed_at.isoformat()
                ),
                "rpc_slot": rpc_slot,
                "board": {
                    "round_id": round_id,
                    "start_slot": start_slot,
                    "end_slot": end_slot,
                    "production_cost_ema": 1,
                },
                "treasury": {
                    "motherlode": 2,
                },
                "round": {
                    "round_id": round_id,
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
        lifecycles.append(
            RoundLifecycleIndexRecord(
                round_id=round_id,
                start_slot=start_slot,
                end_slot=end_slot,
                first_observed_at_utc=(
                    observed_at
                ),
                last_observed_at_utc=(
                    observed_at
                ),
                first_observed_rpc_slot=(
                    rpc_slot
                ),
                last_observed_rpc_slot=(
                    rpc_slot
                ),
                observation_count=1,
                collector_session_ids=[
                    f"session-{round_id}"
                ],
                source_schema_versions=[2],
                source_files=[
                    str(raw_path)
                ],
                observation_references=[
                    ObservationReference(
                        source_file=(
                            str(raw_path)
                        ),
                        source_line_number=(
                            line_number
                        ),
                        observed_at_utc=(
                            observed_at
                        ),
                        rpc_slot=rpc_slot,
                    )
                ],
                finalized_outcome=(
                    FinalizedRoundOutcome(
                        observed_at_utc=(
                            observed_at
                            + timedelta(seconds=1)
                        ),
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
                ),
                finalized_outcome_source=(
                    "observed"
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
            json.dumps(
                record,
                sort_keys=True,
            )
            + "\n"
            for record in raw_records
        ),
        encoding="utf-8",
    )
    dataset_path.write_text(
        "".join(
            record.model_dump_json()
            + "\n"
            for record in lifecycles
        ),
        encoding="utf-8",
    )
    write_metadata(
        DatasetMetadata(
            dataset_version="cli-fixture-v1",
            created_at_utc=base_time,
            source_collection=(
                str(raw_path),
            ),
            malformed_source_record_count=0,
            replay_round_count=2,
            snapshot_count=2,
            complete_round_count=2,
            incomplete_round_count=0,
            missing_outcome_count=0,
            integrity_status="valid",
            ready_for_replay=True,
            dataset_sha256=dataset_sha256(
                dataset_path
            ),
        ),
        dataset_path.with_suffix(
            ".metadata.json"
        ),
    )
    return dataset_path
