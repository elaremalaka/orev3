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

import orev3.experiments.rq003_experiment3 as experiment3_module
from orev3.experiments.rq003_experiment3 import (
    EXPERIMENT3_ARTIFACT_NAMES,
    EXPERIMENT3_PROTOCOL_DOCUMENT_SHA256,
    Experiment3Configuration,
    _average_ranks,
    _load_ranking_artifact,
    _seeded_random_ranks,
    execute_experiment3,
    validate_experiment3_artifacts,
)
from orev3.experiments.rq003_execution_specification import (
    SourceCommitProvenance,
    SourceScopeBinding,
)
from orev3.historical.models import (
    FinalizedRoundOutcome,
    ObservationReference,
    RoundLifecycleIndexRecord,
    RoundQualityMetadata,
)


def test_average_rank_ties_and_predeclared_directions() -> None:
    values = [0] * 25
    values[0] = 10
    values[1] = 10
    values[2] = 5

    descending = _average_ranks(values, descending=True)
    ascending = _average_ranks(values, descending=False)

    assert descending[0] == descending[1] == 1.5
    assert descending[2] == 3.0
    assert all(rank == 14.5 for rank in descending[3:])
    assert ascending[0] == ascending[1] == 24.5
    assert ascending[2] == 23.0
    assert all(rank == 11.5 for rank in ascending[3:])
    assert _average_ranks([0] * 25, descending=True) == (13.0,) * 25


def test_seeded_random_baseline_is_strict_and_deterministic() -> None:
    first = _seeded_random_ranks("a" * 64)
    second = _seeded_random_ranks("a" * 64)
    changed = _seeded_random_ranks("b" * 64)

    assert first == second
    assert tuple(sorted(first)) == tuple(range(1, 26))
    assert first != changed


def test_configuration_is_immutable_and_protocol_fixed(tmp_path: Path) -> None:
    configuration = Experiment3Configuration(
        replay_dataset_path=tmp_path / "source.jsonl",
        output_directory=tmp_path / "output",
        expected_dataset_sha256="a" * 64,
    )

    with pytest.raises(FrozenInstanceError):
        configuration.requested_slots_remaining = 6  # type: ignore[misc]
    with pytest.raises(ValueError, match="requires"):
        Experiment3Configuration(
            replay_dataset_path=tmp_path / "source.jsonl",
            output_directory=tmp_path / "output",
            expected_dataset_sha256="a" * 64,
            requested_slots_remaining=6,
        )
    with pytest.raises(ValueError, match="does not permit"):
        Experiment3Configuration(
            replay_dataset_path=tmp_path / "source.jsonl",
            output_directory=tmp_path / "output",
            expected_dataset_sha256="a" * 64,
            max_slot_distance=3,
        )


def test_protocol_document_identity_is_current() -> None:
    root = Path(__file__).resolve().parents[2]
    protocol = root / (
        "docs/research/experiments/"
        "rq003-experiment-003-miner-count-predictive-evaluation.md"
    )
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == (
        EXPERIMENT3_PROTOCOL_DOCUMENT_SHA256
    )


def test_end_to_end_freezes_rankings_before_outcome_join(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _write_dataset(tmp_path)
    output = tmp_path / "artifacts"
    monkeypatch.setattr(experiment3_module, "EXPERIMENT3_BOOTSTRAP_REPLICATES", 20)
    _bind_frozen_test_source(monkeypatch)

    result = execute_experiment3(_configuration(dataset, output))

    assert result.replay_rounds == 6
    assert result.ranked_decisions == 6
    assert result.primary_evaluations == 3
    assert result.lifecycle_sensitivity_evaluations == 1
    assert result.missing_outcomes == 2
    assert result.source_commit_sha == "a" * 40
    assert len(result.replay_identity) == 64
    assert len(result.audit_manifest_identity) == 64
    assert tuple(sorted(path.name for path in output.iterdir())) == tuple(
        sorted(EXPERIMENT3_ARTIFACT_NAMES)
    )

    ranking_records = _load_ranking_artifact(output / "ranking_artifact.jsonl")
    ranking_text = (output / "ranking_artifact.jsonl").read_text(encoding="utf-8")
    assert len(ranking_records) == 6
    assert all(len(record["candidates"]) == 25 for record in ranking_records)
    assert all(
        tuple(candidate["candidate_square"] for candidate in record["candidates"])
        == tuple(range(25))
        for record in ranking_records
    )
    assert "winning_square" not in ranking_text
    assert "outcome_source" not in ranking_text
    assert "capture_mode" not in ranking_text
    assert "finalized" not in ranking_text
    assert "deployed_lamports" not in ranking_text
    assert all(
        "miner_count" in candidate
        for record in ranking_records
        for candidate in record["candidates"]
    )
    round_11 = next(record for record in ranking_records if record["round_id"] == 11)
    assert round_11["candidates"][23]["primary_average_rank"] == 1.5
    assert round_11["candidates"][24]["primary_average_rank"] == 1.5
    assert round_11["candidates"][23]["primary_tie_group_size"] == 2
    assert round_11["candidates"][24]["primary_tie_group_size"] == 2

    evaluations = _load_jsonl(output / "evaluation_artifact.jsonl")
    assert len(evaluations) == 4
    assert {record["population"] for record in evaluations} == {
        "primary",
        "lifecycle_sensitivity",
    }
    assert all("winning_square" in record for record in evaluations)
    metrics = _load_json(output / "metrics.json")
    assert metrics["primary_metrics"]["evaluation_count"] == 3
    assert set(metrics["primary_metrics"]["procedures"]) == {
        "primary",
        "deterministic_baseline",
        "seeded_random_baseline",
        "ascending_sensitivity",
    }
    assert _load_json(output / "chronological_folds.json")["fold_count"] == 5
    assert set(_load_json(output / "cadence.json")["groups"]) == {
        "0",
        "1",
        "2",
        "3+",
    }
    assert set(_load_json(output / "provenance.json")["groups"]) == {
        "current_round",
        "post_transition_predecessor",
        "enriched",
        "observed_legacy_unspecified",
    }
    observation_counts = _load_json(output / "observation_counts.json")
    assert observation_counts["replay_bound"] == {"2": 6}
    assert observation_counts["outcome_blind_eligible"] == {"2": 6}
    assert observation_counts["primary_labeled_evaluation"] == {"2": 3}
    assert observation_counts["eligible_missing_outcome"] == {"2": 2}
    provenance = _load_json(output / "outcome_blind_provenance.json")
    manifest = _load_json(output / "experiment_audit_manifest.json")
    assert provenance["replay"]["replay_identity"] == result.replay_identity
    assert manifest["audit_manifest_identity"] == result.audit_manifest_identity
    assert manifest["outcome_blind_provenance"] == provenance
    assert provenance["experiment"]["protocol_revision"] == "1"
    assert (
        provenance["experiment"]["specification"]["revision"]
        == "rq003-research-execution-specification-v2"
    )
    assert (
        provenance["execution_profile"]["execution_profile"]
        == "outcome_aware_v1"
    )
    assert manifest["terminal"]["terminal_kind"] == "outcome_aware"
    assert (
        manifest["terminal"]["outcome_access"]
        == "authorized_after_primary_validation"
    )
    conformance = _load_json(output / "conformance.json")
    assert conformance["feature_set_ordered_fields"] == ["miner_count"]
    assert conformance["outcome_blind_ranking_freeze"] == "validated"
    assert conformance["status"] == "passed"


def test_final_validation_accepts_external_source_bytes_and_keeps_generated_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _write_dataset(tmp_path)
    dataset_records = _load_jsonl(dataset)
    dataset.write_text(
        "".join(
            json.dumps(
                dict(reversed(tuple(record.items()))),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
            for record in dataset_records
        ),
        encoding="utf-8",
    )
    assert dataset.read_text(encoding="utf-8").splitlines()[0] != json.dumps(
        dataset_records[0],
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    output = tmp_path / "artifacts"
    monkeypatch.setattr(experiment3_module, "EXPERIMENT3_BOOTSTRAP_REPLICATES", 20)
    _bind_frozen_test_source(monkeypatch)

    result = execute_experiment3(_configuration(dataset, output))
    assert validate_experiment3_artifacts(
        output,
        replay_dataset_path=dataset,
    ) == result.artifacts

    metrics_path = output / "metrics.json"
    metrics = _load_json(metrics_path)
    metrics_path.write_text(
        json.dumps(
            dict(reversed(tuple(metrics.items()))),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="metrics.json is not canonical"):
        validate_experiment3_artifacts(
            output,
            replay_dataset_path=dataset,
        )


def test_regeneration_is_byte_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _write_dataset(tmp_path)
    monkeypatch.setattr(experiment3_module, "EXPERIMENT3_BOOTSTRAP_REPLICATES", 20)
    _bind_frozen_test_source(monkeypatch)

    first = execute_experiment3(_configuration(dataset, tmp_path / "first"))
    second = execute_experiment3(_configuration(dataset, tmp_path / "second"))

    assert tuple((name, digest) for name, _, digest in first.artifacts) == tuple(
        (name, digest) for name, _, digest in second.artifacts
    )
    for name in EXPERIMENT3_ARTIFACT_NAMES:
        assert (tmp_path / "first" / name).read_bytes() == (
            tmp_path / "second" / name
        ).read_bytes()


def test_execution_is_hash_seed_deterministic(tmp_path: Path) -> None:
    dataset = _write_dataset(tmp_path)
    repository_root = Path(__file__).resolve().parents[2]
    expected = hashlib.sha256(dataset.read_bytes()).hexdigest()
    script = """
import sys
from pathlib import Path
import orev3.experiments.rq003_experiment3 as experiment3_module
from orev3.experiments.rq003_execution_specification import (
    SourceCommitProvenance,
    SourceScopeBinding,
)
from orev3.experiments.rq003_experiment3 import (
    Experiment3Configuration,
    execute_experiment3,
)
experiment3_module._bind_execution_source = lambda configuration: (
    SourceCommitProvenance(
        "a" * 40,
        (SourceScopeBinding("src/orev3", "b" * 40),),
    )
)
result = execute_experiment3(
    Experiment3Configuration(
        replay_dataset_path=Path(sys.argv[1]),
        output_directory=Path(sys.argv[2]),
        expected_dataset_sha256=sys.argv[3],
    )
)
print("|".join(digest for _, _, digest in result.artifacts))
"""
    digests: list[str] = []
    outputs: list[Path] = []
    for seed in ("1", "8675309"):
        output = tmp_path / f"seed-{seed}"
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
                    expected,
                ],
                cwd=repository_root,
                env=environment,
                text=True,
            ).strip()
        )
        outputs.append(output)

    assert digests[0] == digests[1]
    for name in EXPERIMENT3_ARTIFACT_NAMES:
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()


def test_ranking_loader_rejects_outcome_fields(tmp_path: Path) -> None:
    path = tmp_path / "ranking.jsonl"
    path.write_text(
        json.dumps(
            {
                "ranking_record_identity": "a" * 64,
                "winning_square": 1,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="identity does not reconstruct"):
        _load_ranking_artifact(path)


def test_dataset_identity_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _write_dataset(tmp_path)
    output = tmp_path / "output"
    _bind_frozen_test_source(monkeypatch)

    with pytest.raises(ValueError, match="SHA-256"):
        execute_experiment3(
            Experiment3Configuration(
                replay_dataset_path=dataset,
                output_directory=output,
                expected_dataset_sha256="0" * 64,
            )
        )
    assert not output.exists()


def test_artifact_validator_rejects_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _write_dataset(tmp_path)
    output = tmp_path / "output"
    monkeypatch.setattr(experiment3_module, "EXPERIMENT3_BOOTSTRAP_REPLICATES", 20)
    _bind_frozen_test_source(monkeypatch)
    execute_experiment3(_configuration(dataset, output))
    ranking = output / "ranking_artifact.jsonl"
    ranking.write_bytes(ranking.read_bytes() + b"{}\n")

    with pytest.raises(ValueError):
        validate_experiment3_artifacts(
            output,
            replay_dataset_path=dataset,
        )


def test_phase_scope_has_no_strategy_model_or_economics_dependency() -> None:
    tree = ast.parse(inspect.getsource(experiment3_module))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert not any("strategies" in module for module in imported_modules)
    assert not any("economics" in module for module in imported_modules)
    assert not any("modeling" in module for module in imported_modules)


def _configuration(dataset: Path, output: Path) -> Experiment3Configuration:
    return Experiment3Configuration(
        replay_dataset_path=dataset,
        output_directory=output,
        expected_dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
    )


def _bind_frozen_test_source(monkeypatch: pytest.MonkeyPatch) -> None:
    provenance = SourceCommitProvenance(
        "a" * 40,
        (SourceScopeBinding("src/orev3", "b" * 40),),
    )
    monkeypatch.setattr(
        experiment3_module,
        "_bind_execution_source",
        lambda configuration: provenance,
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_dataset(tmp_path: Path) -> Path:
    raw_path = tmp_path / "observer.jsonl"
    index_path = tmp_path / "replay.jsonl"
    raw_records: list[dict[str, Any]] = []
    lifecycles: list[RoundLifecycleIndexRecord] = []
    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    line_number = 0
    settings = (
        (11, "complete", "observed", "current_round", 0),
        (12, "complete", "observed", "post_transition_predecessor", 1),
        (13, "complete", "enriched", None, 2),
        (14, "partial_start", "observed", "current_round", 3),
        (15, "complete", None, None, None),
        (16, "partial_end", None, None, None),
    )
    for round_id, coverage, source, capture_mode, winner in settings:
        start_slot = round_id * 100
        end_slot = start_slot + 20
        references: list[ObservationReference] = []
        for observation_index, slots_remaining in enumerate((10, 5)):
            line_number += 1
            observed_at = base_time + timedelta(
                seconds=round_id * 10 + observation_index
            )
            rpc_slot = end_slot - slots_remaining
            miner = [square for square in range(25)]
            if round_id == 11:
                miner[23] = miner[24]
            raw_records.append(
                {
                    "board": {
                        "end_slot": end_slot,
                        "production_cost_ema": 1_000 + round_id,
                        "round_id": round_id,
                        "start_slot": start_slot,
                    },
                    "collector_session_id": f"session-{round_id}",
                    "observed_at_utc": observed_at.isoformat(),
                    "round": {
                        "deployed_lamports": [100 + square for square in range(25)],
                        "entropy": None,
                        "expires_at": end_slot,
                        "mass": [0] * 25,
                        "miner_counts": miner,
                        "motherlode": 0,
                        "rewards": [0] * 25,
                        "round_id": round_id,
                        "slot_hash_hex": "00" * 32,
                        "top_miner": "11111111111111111111111111111111",
                        "total_miners": 25,
                        "total_vaulted": 0,
                        "total_winnings": 0,
                    },
                    "rpc_slot": rpc_slot,
                    "schema_version": 2,
                    "treasury": {"motherlode": 2_000 + round_id},
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
        outcome = None
        if winner is not None:
            outcome = FinalizedRoundOutcome(
                observed_at_utc=base_time + timedelta(seconds=round_id * 10 + 5),
                rpc_slot=end_slot + 1,
                entropy=round_id,
                winning_square=winner,
                deployed_lamports=[0] * 25,
                miner_counts=[0] * 25,
                reward_buckets=[0] * 25,
                total_vaulted=0,
                total_winnings=0,
                total_miners=0,
                round_motherlode=0,
                top_miner="finalized",
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
                finalized_outcome_source=source,
                finalized_outcome_capture_mode=capture_mode,
                finalized_outcome_evidence_identities=(
                    ("e" * 64,)
                    if capture_mode == "post_transition_predecessor"
                    else ()
                ),
                quality=RoundQualityMetadata(
                    coverage_status=coverage,
                    initialization_state_observed=coverage == "complete",
                    rpc_slot_regression_count=0,
                    largest_rpc_slot_regression=0,
                    duplicate_rpc_slot_count=0,
                    max_observation_gap_seconds=1.0,
                    significant_gap_count=0,
                    significant_gap_threshold_seconds=5.0,
                    collector_session_count=1,
                    finalized_state_observed=source == "observed",
                ),
            )
        )
    raw_path.write_text(
        "".join(
            json.dumps(record, sort_keys=True) + "\n" for record in raw_records
        ),
        encoding="utf-8",
    )
    index_path.write_text(
        "".join(
            json.dumps(
                record.model_dump(mode="json"),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
            for record in lifecycles
        ),
        encoding="utf-8",
    )
    return index_path
