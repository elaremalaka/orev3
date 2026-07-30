from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from orev3.dataset import (
    DatasetBuildConfiguration,
    DatasetMetadata,
    DatasetValidationError,
    build_replay_dataset,
    discover_observer_data,
    inspect_replay_dataset,
    load_metadata,
    validate_replay_dataset,
)
from orev3.dataset.build import main as build_main
from orev3.dataset.metadata import dataset_sha256
from orev3.dataset.stats import main as stats_main
from orev3.dataset.validate import main as validate_main


CREATED_AT = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
U64_MAX = (2**64) - 1


def test_builder_discovers_sources_and_writes_deterministic_dataset(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "raw"
    first_source = _write_observer_file(source_root, "observer-b.jsonl", (2,))
    second_source = _write_observer_file(source_root, "observer-a.jsonl", (1,))
    first_source.write_text(
        first_source.read_text(encoding="utf-8") + "{malformed}\n",
        encoding="utf-8",
    )
    first_output = tmp_path / "first.jsonl"
    first_metadata = tmp_path / "first.metadata.json"
    second_output = tmp_path / "second.jsonl"
    second_metadata = tmp_path / "second.metadata.json"

    discovered = discover_observer_data(source_root)
    assert discovered == tuple(sorted((first_source, second_source)))

    first = build_replay_dataset(
        _configuration(
            source_root,
            first_output,
            first_metadata,
        )
    )
    second = build_replay_dataset(
        _configuration(
            source_root,
            second_output,
            second_metadata,
        )
    )

    assert first_output.read_bytes() == second_output.read_bytes()
    assert first_metadata.read_bytes() == second_metadata.read_bytes()
    assert first.metadata == second.metadata
    assert first.metadata.dataset_version == "fixture-replay-v1"
    assert first.metadata.metadata_schema_version == 2
    assert first.metadata.created_at_utc == CREATED_AT
    assert first.metadata.source_collection == tuple(
        str(path) for path in discovered
    )
    assert first.metadata.malformed_source_record_count == 1
    assert first.metadata.replay_round_count == 2
    assert first.metadata.snapshot_count == 4
    assert first.metadata.complete_round_count == 2
    assert first.metadata.incomplete_round_count == 0
    assert first.metadata.missing_outcome_count == 0
    assert first.metadata.integrity_status == "valid"
    assert first.metadata.ready_for_replay
    assert first.metadata.dataset_sha256 == dataset_sha256(first_output)
    assert first.source_file_count == 2
    assert first.source_line_count == 5
    assert first.malformed_source_record_count == 1
    assert first.observed_outcome_count == 2
    assert first.enriched_outcome_count == 0


def test_builder_uses_explicit_sources_and_orders_rounds_chronologically(
    tmp_path: Path,
) -> None:
    source = _write_observer_file(
        tmp_path,
        "collection.jsonl",
        (3, 1, 2),
    )
    output = tmp_path / "dataset.jsonl"

    build_replay_dataset(
        DatasetBuildConfiguration(
            output_path=output,
            metadata_path=tmp_path / "metadata.json",
            dataset_version="explicit-v1",
            observer_paths=(source,),
            enrich_missing_outcomes=False,
            created_at_utc=CREATED_AT,
        )
    )

    records = [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["round_id"] for record in records] == [1, 2, 3]


def test_builder_publishes_integral_dataset_that_is_not_replay_ready(
    tmp_path: Path,
) -> None:
    source = _write_observer_file(tmp_path, "observer-missing.jsonl", (1,))
    records = _read_raw_records(source)
    records[-1]["round"]["slot_hash_hex"] = "00" * 32
    records[-1]["round"]["entropy"] = None
    records[-1]["round"]["total_vaulted"] = 0
    records[-1]["round"]["total_winnings"] = 0
    _write_raw_records(source, records)
    output = tmp_path / "not-ready.jsonl"
    metadata_path = tmp_path / "not-ready.metadata.json"

    result = build_replay_dataset(
        DatasetBuildConfiguration(
            output_path=output,
            metadata_path=metadata_path,
            dataset_version="not-ready-v1",
            observer_paths=(source,),
            enrich_missing_outcomes=False,
            created_at_utc=CREATED_AT,
        )
    )
    validation = validate_replay_dataset(output, fail_closed=False)

    assert validation.integrity_valid
    assert not validation.valid
    assert not validation.ready_for_replay
    assert result.metadata.integrity_status == "valid"
    assert result.metadata.missing_outcome_count == 1
    assert not result.metadata.ready_for_replay


def test_builder_uses_initialized_start_slot_and_preserves_provisional_snapshot(
    tmp_path: Path,
) -> None:
    source = _write_observer_file(tmp_path, "observer-start.jsonl", (1,))
    records = _read_raw_records(source)
    records[0]["board"]["start_slot"] = 97
    _write_raw_records(source, records)
    output = tmp_path / "dataset.jsonl"

    build_replay_dataset(
        DatasetBuildConfiguration(
            output_path=output,
            metadata_path=tmp_path / "metadata.json",
            dataset_version="provisional-start-v1",
            observer_paths=(source,),
            enrich_missing_outcomes=False,
            created_at_utc=CREATED_AT,
        )
    )

    record = _read_raw_records(output)[0]
    validation = validate_replay_dataset(output, fail_closed=False)
    assert record["start_slot"] == 100
    assert record["observation_count"] == 2
    assert validation.integrity_valid
    assert "round_start_mismatch" not in _issue_codes(validation)


def test_validator_rejects_initialized_start_slot_mismatch(
    tmp_path: Path,
) -> None:
    source_root, output, _ = _built_fixture(tmp_path)
    source = next(source_root.glob("observer*.jsonl"))
    records = _read_raw_records(source)
    records[1]["board"]["start_slot"] += 1
    _write_raw_records(source, records)

    validation = validate_replay_dataset(output, fail_closed=False)

    assert not validation.integrity_valid
    assert "round_start_mismatch" in _issue_codes(validation)


def test_builder_fails_closed_without_sources_or_on_corrupted_source(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="no observer data"):
        build_replay_dataset(
            _configuration(
                tmp_path / "missing",
                tmp_path / "dataset.jsonl",
                tmp_path / "metadata.json",
            )
        )

    source_root = tmp_path / "raw"
    source_root.mkdir()
    (source_root / "observer-invalid.jsonl").write_text(
        "{not-json}\n",
        encoding="utf-8",
    )
    output = tmp_path / "preserved.jsonl"
    output.write_text("preserved\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="empty_dataset"):
        build_replay_dataset(
            _configuration(
                source_root,
                output,
                tmp_path / "invalid.metadata.json",
            )
        )
    assert output.read_text(encoding="utf-8") == "preserved\n"


def test_validator_accepts_complete_replay_and_reports_statistics(
    tmp_path: Path,
) -> None:
    source_root, output, metadata = _built_fixture(tmp_path)

    result = validate_replay_dataset(output)
    inspection = inspect_replay_dataset(output, metadata)

    assert source_root.exists()
    assert result.valid
    assert result.ready_for_replay
    assert result.replay_round_count == 2
    assert result.snapshot_count == 4
    assert result.first_round_identifier == 1
    assert result.last_round_identifier == 2
    assert result.first_observed_at_utc is not None
    assert result.last_observed_at_utc is not None
    assert inspection.metadata_issues == ()
    assert inspection.ready_for_replay


def test_validator_rejects_duplicate_and_out_of_order_rounds(
    tmp_path: Path,
) -> None:
    _, output, _ = _built_fixture(tmp_path)
    original_lines = output.read_text(encoding="utf-8").splitlines()

    output.write_text(
        "\n".join((original_lines[0], original_lines[1], original_lines[0]))
        + "\n",
        encoding="utf-8",
    )
    duplicate = validate_replay_dataset(output, fail_closed=False)
    assert "duplicate_round" in _issue_codes(duplicate)
    with pytest.raises(DatasetValidationError):
        validate_replay_dataset(output)

    output.write_text(
        "\n".join(reversed(original_lines)) + "\n",
        encoding="utf-8",
    )
    out_of_order = validate_replay_dataset(output, fail_closed=False)
    assert "chronological_order" in _issue_codes(out_of_order)


def test_validator_rejects_corrupted_observations_and_records(
    tmp_path: Path,
) -> None:
    source_root, output, _ = _built_fixture(tmp_path)
    source = next(source_root.glob("observer*.jsonl"))
    lines = source.read_text(encoding="utf-8").splitlines()
    lines[0] = "{corrupted}"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")

    corrupted_observation = validate_replay_dataset(output, fail_closed=False)
    assert "corrupted_observation" in _issue_codes(corrupted_observation)

    output.write_text("{corrupted}\n", encoding="utf-8")
    corrupted_record = validate_replay_dataset(output, fail_closed=False)
    assert "corrupted_record" in _issue_codes(corrupted_record)


def test_validator_rejects_missing_outcomes_and_replay_inconsistencies(
    tmp_path: Path,
) -> None:
    _, output, _ = _built_fixture(tmp_path)
    records = _read_raw_records(output)
    records[0]["finalized_outcome"] = None
    records[0]["finalized_outcome_source"] = None
    records[1]["observation_count"] = 3
    records[1]["finalized_outcome"]["winning_square"] = 24
    _write_raw_records(output, records)

    result = validate_replay_dataset(output, fail_closed=False)

    assert {
        "missing_finalized_outcome",
        "snapshot_count_mismatch",
        "finalized_outcome_mismatch",
    }.issubset(_issue_codes(result))
    assert not result.ready_for_replay


def test_validator_rejects_incomplete_round_and_reference_mismatch(
    tmp_path: Path,
) -> None:
    _, output, _ = _built_fixture(tmp_path)
    records = _read_raw_records(output)
    records[0]["quality"]["coverage_status"] = "partial_end"
    records[1]["observation_references"][0]["rpc_slot"] += 1
    _write_raw_records(output, records)

    result = validate_replay_dataset(output, fail_closed=False)

    assert "incomplete_round" in _issue_codes(result)
    assert "observation_reference_mismatch" in _issue_codes(result)
    assert result.incomplete_round_count == 1


def test_validator_rejects_duplicate_and_misordered_observation_references(
    tmp_path: Path,
) -> None:
    _, output, _ = _built_fixture(tmp_path)
    records = _read_raw_records(output)
    references = records[0]["observation_references"]
    references[1] = references[0]
    records[1]["source_files"] = ["wrong-source.jsonl"]
    records[1]["observation_references"].reverse()
    _write_raw_records(output, records)

    result = validate_replay_dataset(output, fail_closed=False)

    assert {
        "duplicate_observation_reference",
        "observation_order",
        "source_collection_mismatch",
    }.issubset(_issue_codes(result))


def test_metadata_is_immutable_canonical_and_tampering_is_detected(
    tmp_path: Path,
) -> None:
    _, output, metadata_path = _built_fixture(tmp_path)
    metadata = load_metadata(metadata_path)

    with pytest.raises(FrozenInstanceError):
        metadata.dataset_version = "changed"  # type: ignore[misc]
    assert json.loads(metadata_path.read_text(encoding="utf-8"))[
        "dataset_sha256"
    ] == dataset_sha256(output)

    records = _read_raw_records(output)
    output.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records)
        + "\n",
        encoding="utf-8",
    )
    inspection = inspect_replay_dataset(output, metadata_path)
    assert inspection.validation.valid
    assert inspection.metadata_issues == (
        "dataset SHA-256 does not match metadata",
    )
    assert not inspection.ready_for_replay


def test_metadata_rejects_inconsistent_readiness() -> None:
    with pytest.raises(ValueError, match="ready_for_replay"):
        DatasetMetadata(
            dataset_version="fixture-v1",
            created_at_utc=CREATED_AT,
            source_collection=("observer.jsonl",),
            malformed_source_record_count=0,
            replay_round_count=1,
            snapshot_count=2,
            complete_round_count=0,
            incomplete_round_count=1,
            missing_outcome_count=0,
            integrity_status="valid",
            ready_for_replay=True,
            dataset_sha256="0" * 64,
        )


def test_public_build_and_stats_commands_report_ready_dataset(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_root = tmp_path / "raw"
    _write_observer_file(source_root, "observer-cli.jsonl", (1, 2))
    output = tmp_path / "cli.jsonl"
    metadata = tmp_path / "cli.metadata.json"

    build_main(
        [
            "--source-root",
            str(source_root),
            "--output",
            str(output),
            "--metadata",
            str(metadata),
            "--dataset-version",
            "cli-fixture-v1",
            "--skip-enrichment",
        ]
    )
    build_output = capsys.readouterr().out
    assert "dataset_version: cli-fixture-v1" in build_output
    assert "replay_rounds: 2" in build_output
    assert "ready_for_replay: true" in build_output

    stats_main(["--dataset", str(output), "--metadata", str(metadata)])
    stats_output = capsys.readouterr().out
    assert "first_round: 1" in stats_output
    assert "last_round: 2" in stats_output
    assert "missing_outcomes: 0" in stats_output
    assert "ready_for_replay: true" in stats_output

    validate_main(["--dataset", str(output)])
    validate_output = capsys.readouterr().out
    assert "validation_issues: 0" in validate_output
    assert "ready_for_replay: true" in validate_output


def test_stats_command_fails_closed_when_dataset_digest_changes(
    tmp_path: Path,
) -> None:
    _, output, metadata = _built_fixture(tmp_path)
    records = _read_raw_records(output)
    output.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records)
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        stats_main(["--dataset", str(output), "--metadata", str(metadata)])
    assert exc.value.code == 1


def test_validation_command_fails_closed_and_reports_issue(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, output, _ = _built_fixture(tmp_path)
    records = _read_raw_records(output)
    records[0]["finalized_outcome"] = None
    records[0]["finalized_outcome_source"] = None
    _write_raw_records(output, records)

    with pytest.raises(SystemExit) as exc:
        validate_main(["--dataset", str(output)])

    assert exc.value.code == 1
    captured = capsys.readouterr().out
    assert "issue: missing_finalized_outcome" in captured
    assert "ready_for_replay: false" in captured


def _built_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    source_root = tmp_path / "raw"
    _write_observer_file(source_root, "observer-fixture.jsonl", (2, 1))
    output = tmp_path / "dataset.jsonl"
    metadata = tmp_path / "metadata.json"
    build_replay_dataset(_configuration(source_root, output, metadata))
    return source_root, output, metadata


def _configuration(
    source_root: Path,
    output: Path,
    metadata: Path,
) -> DatasetBuildConfiguration:
    return DatasetBuildConfiguration(
        output_path=output,
        metadata_path=metadata,
        dataset_version="fixture-replay-v1",
        observer_root=source_root,
        enrich_missing_outcomes=False,
        created_at_utc=CREATED_AT,
    )


def _write_observer_file(
    directory: Path,
    name: str,
    round_ids: tuple[int, ...],
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    records: list[dict[str, object]] = []
    for round_id in round_ids:
        records.extend(
            (
                _snapshot(round_id, finalized=False),
                _snapshot(round_id, finalized=True),
            )
        )
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def _snapshot(round_id: int, *, finalized: bool) -> dict[str, object]:
    start_slot = round_id * 100
    end_slot = start_slot + 20
    observed_at = datetime(2026, 1, 1, tzinfo=UTC).replace(
        minute=round_id,
        second=20 if finalized else 0,
    )
    return {
        "schema_version": 2,
        "observed_at_utc": observed_at.isoformat(),
        "rpc_slot": end_slot if finalized else start_slot,
        "collector_session_id": "fixture-session",
        "board": {
            "round_id": round_id,
            "start_slot": start_slot,
            "end_slot": end_slot if finalized else U64_MAX,
            "production_cost_ema": 1,
        },
        "treasury": {"motherlode": 100},
        "round": {
            "round_id": round_id,
            "deployed_lamports": [round_id] * 25,
            "mass": [0] * 25,
            "miner_counts": list(range(25)),
            "slot_hash_hex": ("01" * 32) if finalized else ("00" * 32),
            "expires_at": end_slot,
            "motherlode": 100,
            "rewards": [2] * 25,
            "total_vaulted": 1000 if finalized else 0,
            "total_winnings": 100 if finalized else 0,
            "total_miners": 25,
            "top_miner": "fixture",
            "entropy": round_id if finalized else None,
        },
    }


def _read_raw_records(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]


def _write_raw_records(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _issue_codes(result) -> set[str]:
    return {issue.code for issue in result.issues}
