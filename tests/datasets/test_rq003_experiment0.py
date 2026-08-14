from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import orev3.datasets.rq003_experiment0 as experiment0_module
from orev3.datasets.rq003_experiment0 import (
    RQ003_EXPERIMENT0_OUTPUT_NAMES,
    RQ003Experiment0Configuration,
    RQ003Experiment0Record,
    build_fundamental_measurement_pipeline,
    generate_rq003_experiment0_dataset,
    load_rq003_experiment0_dataset,
)
from orev3.historical.models import (
    FinalizedRoundOutcome,
    ObservationReference,
    RoundLifecycleIndexRecord,
    RoundQualityMetadata,
)


def test_configuration_is_immutable_and_identity_bound(tmp_path: Path) -> None:
    first = _configuration(tmp_path / "source.jsonl", tmp_path / "one.jsonl")
    same = _configuration(tmp_path / "other.jsonl", tmp_path / "two.jsonl")
    changed = RQ003Experiment0Configuration(
        replay_dataset_path=tmp_path / "source.jsonl",
        output_path=tmp_path / "three.jsonl",
        requested_slots_remaining=6,
        max_slot_distance=0,
    )

    assert (
        first.decision_point_configuration_identity
        == same.decision_point_configuration_identity
    )
    assert (
        first.decision_point_configuration_identity
        != changed.decision_point_configuration_identity
    )
    with pytest.raises(FrozenInstanceError):
        first.requested_slots_remaining = 7  # type: ignore[misc]
    with pytest.raises(ValueError, match="must not replace"):
        _configuration(tmp_path / "same.jsonl", tmp_path / "same.jsonl")
    with pytest.raises(ValueError, match="nonnegative integer"):
        RQ003Experiment0Configuration(
            tmp_path / "source.jsonl", tmp_path / "out.jsonl", -1
        )


def test_complete_fundamental_library_has_one_canonical_order() -> None:
    pipeline = build_fundamental_measurement_pipeline()

    assert RQ003_EXPERIMENT0_OUTPUT_NAMES == (
        "deployed_lamports",
        "miner_count",
        "total_miners",
        "board_production_cost_ema",
        "active_round_motherlode",
        "treasury_motherlode",
        "pre_finalization_total_vaulted",
        "pre_finalization_total_winnings",
    )
    assert len(pipeline.pipeline_implementation_identity) == 64


def test_end_to_end_generation_executes_every_candidate_in_replay_order(
    tmp_path: Path,
) -> None:
    dataset = _write_replay_dataset(tmp_path, "source", outcome_offset=0)
    output = tmp_path / "experiment0.jsonl"

    result = generate_rq003_experiment0_dataset(
        _configuration(dataset, output)
    )
    records = load_rq003_experiment0_dataset(output)

    assert result.decision_count == 2
    assert result.record_count == 50
    assert result.output_sha256 == hashlib.sha256(output.read_bytes()).hexdigest()
    assert len(records) == 50
    assert tuple(record.candidate_square for record in records[:25]) == tuple(
        range(25)
    )
    assert tuple(record.candidate_square for record in records[25:]) == tuple(
        range(25)
    )
    assert len({record.decision_identity for record in records[:25]}) == 1
    assert len({record.decision_identity for record in records[25:]}) == 1
    assert records[0].decision_identity != records[25].decision_identity
    assert len({record.measurement_vector_identity for record in records}) == 50
    assert records[0].ordered_fundamental_measurement_values == (
        11_100,
        10,
        512,
        1_012,
        0,
        2_012,
        0,
        0,
    )
    assert records[24].ordered_fundamental_measurement_values[:2] == (
        11_124,
        34,
    )


def test_regeneration_is_byte_and_identity_deterministic(
    tmp_path: Path,
) -> None:
    first_dataset = _write_replay_dataset(
        tmp_path, "first-source", outcome_offset=0
    )
    second_dataset = _write_replay_dataset(
        tmp_path, "second-source", outcome_offset=9
    )
    first_output = tmp_path / "first-output.jsonl"
    second_output = tmp_path / "second-output.jsonl"

    first_result = generate_rq003_experiment0_dataset(
        _configuration(first_dataset, first_output)
    )
    second_result = generate_rq003_experiment0_dataset(
        _configuration(second_dataset, second_output)
    )

    assert first_output.read_bytes() == second_output.read_bytes()
    assert first_result.output_sha256 == second_result.output_sha256
    first_records = load_rq003_experiment0_dataset(first_output)
    second_records = load_rq003_experiment0_dataset(second_output)
    assert first_records == second_records
    assert tuple(
        record.measurement_vector_identity for record in first_records
    ) == tuple(
        record.measurement_vector_identity for record in second_records
    )


def test_end_to_end_generation_is_hash_seed_deterministic(
    tmp_path: Path,
) -> None:
    dataset = _write_replay_dataset(tmp_path, "source", outcome_offset=0)
    repository_root = Path(__file__).resolve().parents[2]
    script = """
import sys
from pathlib import Path
from orev3.datasets.rq003_experiment0 import (
    RQ003Experiment0Configuration,
    generate_rq003_experiment0_dataset,
)
result = generate_rq003_experiment0_dataset(
    RQ003Experiment0Configuration(
        replay_dataset_path=Path(sys.argv[1]),
        output_path=Path(sys.argv[2]),
        requested_slots_remaining=5,
        max_slot_distance=0,
    )
)
print(result.output_sha256)
"""
    outputs: list[Path] = []
    digests: list[str] = []
    for seed in ("1", "8675309"):
        output = tmp_path / f"seed-{seed}.jsonl"
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(repository_root / "src")
        digests.append(
            subprocess.check_output(
                [
                    sys.executable,
                    "-c",
                    script,
                    str(dataset),
                    str(output),
                ],
                cwd=repository_root,
                env=environment,
                text=True,
            ).strip()
        )
        outputs.append(output)

    assert digests[0] == digests[1]
    assert outputs[0].read_bytes() == outputs[1].read_bytes()


def test_persisted_rows_contain_only_authorized_fields(tmp_path: Path) -> None:
    dataset = _write_replay_dataset(tmp_path, "source", outcome_offset=0)
    output = tmp_path / "experiment0.jsonl"
    generate_rq003_experiment0_dataset(_configuration(dataset, output))

    expected = {
        "candidate_square",
        "decision_identity",
        "measurement_vector_identity",
        "ordered_fundamental_measurement_values",
    }
    lines = output.read_text(encoding="utf-8").splitlines()
    for line in lines:
        material = json.loads(line)
        assert set(material) == expected
        assert {
            "winning_square",
            "won",
            "outcome",
            "rank",
            "score",
            "strategy",
            "evaluation",
        }.isdisjoint(material)


def test_canonical_loader_rejects_labels_and_noncanonical_encoding(
    tmp_path: Path,
) -> None:
    valid = RQ003Experiment0Record(
        decision_identity="a" * 64,
        candidate_square=0,
        measurement_vector_identity="b" * 64,
        ordered_fundamental_measurement_values=(0,) * 8,
    )
    labeled = json.loads(valid.to_canonical_json())
    labeled["winning_square"] = 1
    labeled_path = tmp_path / "labeled.jsonl"
    labeled_path.write_text(
        json.dumps(labeled, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="fields are invalid"):
        load_rq003_experiment0_dataset(labeled_path)

    noncanonical_path = tmp_path / "noncanonical.jsonl"
    noncanonical_path.write_text(
        json.dumps(json.loads(valid.to_canonical_json()), indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ValueError,
        match="invalid JSON|fields are invalid|not canonical",
    ):
        load_rq003_experiment0_dataset(noncanonical_path)


def test_generation_never_reads_lifecycle_outcomes() -> None:
    source = inspect.getsource(
        experiment0_module.generate_rq003_experiment0_dataset
    )

    assert "finalized_outcome" not in source
    assert "winning_square" not in source
    assert "outcome_source" not in source


def test_execution_imports_no_strategy_evaluation_or_ranking_component() -> None:
    tree = ast.parse(inspect.getsource(experiment0_module))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }

    assert not any("strategies" in module for module in imported_modules)
    assert not any("evaluation" in module for module in imported_modules)
    assert not any("deployment" in module for module in imported_modules)
    assert {"Strategy", "Evaluator", "RankedCandidateSet"}.isdisjoint(
        imported_names
    )


def test_generation_is_atomic_when_measurement_context_fails(
    tmp_path: Path,
) -> None:
    dataset = _write_replay_dataset(
        tmp_path,
        "invalid-source",
        outcome_offset=0,
        active_round_motherlode=1,
    )
    output = tmp_path / "existing.jsonl"
    output.write_text("existing\n", encoding="utf-8")

    with pytest.raises(ValueError, match="pre-finalization"):
        generate_rq003_experiment0_dataset(_configuration(dataset, output))

    assert output.read_text(encoding="utf-8") == "existing\n"
    assert not tuple(tmp_path.glob("existing.jsonl.*.tmp"))


def test_empty_replay_and_output_datasets_fail_closed(tmp_path: Path) -> None:
    empty_replay = tmp_path / "empty-replay.jsonl"
    empty_replay.write_text("", encoding="utf-8")
    output = tmp_path / "output.jsonl"

    with pytest.raises(ValueError, match="contains no decisions"):
        generate_rq003_experiment0_dataset(
            _configuration(empty_replay, output)
        )
    assert not output.exists()

    empty_output = tmp_path / "empty-output.jsonl"
    empty_output.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="contains no records"):
        load_rq003_experiment0_dataset(empty_output)


def test_protocol_revision_dependencies_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        experiment0_module,
        "_PROTOCOL_SOURCE_REVISIONS",
        ("0" * 40,),
    )

    with pytest.raises(ValueError, match="supported revision"):
        build_fundamental_measurement_pipeline()


def test_record_is_immutable_and_rejects_invalid_values() -> None:
    record = RQ003Experiment0Record(
        decision_identity="a" * 64,
        candidate_square=24,
        measurement_vector_identity="b" * 64,
        ordered_fundamental_measurement_values=(0,) * 8,
    )

    with pytest.raises(FrozenInstanceError):
        record.candidate_square = 1  # type: ignore[misc]
    with pytest.raises(ValueError, match="between 0 and 24"):
        RQ003Experiment0Record(
            "a" * 64, 25, "b" * 64, (0,) * 8
        )
    with pytest.raises(ValueError, match="count is invalid"):
        RQ003Experiment0Record(
            "a" * 64, 0, "b" * 64, (0,) * 7
        )


def test_phase_scope_introduces_no_later_research_responsibility() -> None:
    public_names = set(experiment0_module.__all__)
    prohibited = (
        "derived",
        "feature_set",
        "baseline",
        "ranking",
        "strategy",
        "evaluation",
    )

    assert not any(
        fragment in name.lower()
        for fragment in prohibited
        for name in public_names
    )


def _configuration(
    dataset: Path,
    output: Path,
) -> RQ003Experiment0Configuration:
    return RQ003Experiment0Configuration(
        replay_dataset_path=dataset,
        output_path=output,
        requested_slots_remaining=5,
        max_slot_distance=0,
    )


def _write_replay_dataset(
    tmp_path: Path,
    name: str,
    *,
    outcome_offset: int,
    active_round_motherlode: int = 0,
) -> Path:
    raw_path = tmp_path / f"{name}.observer.jsonl"
    index_path = tmp_path / f"{name}.replay.jsonl"
    raw_records: list[dict[str, Any]] = []
    lifecycles: list[RoundLifecycleIndexRecord] = []
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    line_number = 0

    for round_id in (12, 11):
        start_slot = round_id * 100
        end_slot = start_slot + 20
        references: list[ObservationReference] = []
        for observation_index, slots_remaining in enumerate((10, 5)):
            line_number += 1
            observed_at = base_time + timedelta(
                seconds=round_id * 10 + observation_index
            )
            rpc_slot = end_slot - slots_remaining
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
                        "production_cost_ema": (
                            1_000 + round_id + observation_index
                        ),
                    },
                    "treasury": {
                        "motherlode": 2_000 + round_id + observation_index
                    },
                    "round": {
                        "round_id": round_id,
                        "deployed_lamports": [
                            round_id * 1_000 + observation_index * 100 + square
                            for square in range(25)
                        ],
                        "mass": [0] * 25,
                        "miner_counts": [
                            observation_index * 10 + square
                            for square in range(25)
                        ],
                        "slot_hash_hex": "00" * 32,
                        "expires_at": end_slot,
                        "motherlode": active_round_motherlode,
                        "rewards": [0] * 25,
                        "total_vaulted": 0,
                        "total_winnings": 0,
                        "total_miners": (
                            500 + round_id + observation_index
                        ),
                        "top_miner": "11111111111111111111111111111111",
                        "entropy": None,
                    },
                }
            )
            references.append(
                ObservationReference(
                    source_file=str(raw_path),
                    source_line_number=line_number,
                    observed_at_utc=observed_at,
                    rpc_slot=rpc_slot,
                )
            )
        outcome = FinalizedRoundOutcome(
            observed_at_utc=base_time + timedelta(seconds=round_id * 10 + 30),
            rpc_slot=end_slot + 1,
            entropy=round_id + outcome_offset,
            winning_square=(round_id + outcome_offset) % 25,
            deployed_lamports=[9_999 + outcome_offset] * 25,
            miner_counts=[99 + outcome_offset] * 25,
            reward_buckets=[77 + outcome_offset] * 25,
            total_vaulted=8_888 + outcome_offset,
            total_winnings=7_777 + outcome_offset,
            total_miners=66 + outcome_offset,
            round_motherlode=5_555 + outcome_offset,
            top_miner=f"outcome-{outcome_offset}",
        )
        lifecycles.append(
            RoundLifecycleIndexRecord(
                round_id=round_id,
                start_slot=start_slot,
                end_slot=end_slot,
                first_observed_at_utc=references[0].observed_at_utc,
                last_observed_at_utc=references[-1].observed_at_utc,
                first_observed_rpc_slot=references[0].rpc_slot,
                last_observed_rpc_slot=references[-1].rpc_slot,
                observation_count=2,
                collector_session_ids=[f"session-{round_id}"],
                source_schema_versions=[2],
                source_files=[str(raw_path)],
                observation_references=references,
                finalized_outcome=outcome,
                finalized_outcome_source="observed",
                quality=RoundQualityMetadata(
                    coverage_status="complete",
                    initialization_state_observed=True,
                    rpc_slot_regression_count=0,
                    largest_rpc_slot_regression=0,
                    duplicate_rpc_slot_count=0,
                    max_observation_gap_seconds=1.0,
                    significant_gap_count=0,
                    significant_gap_threshold_seconds=5.0,
                    collector_session_count=1,
                    finalized_state_observed=False,
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
