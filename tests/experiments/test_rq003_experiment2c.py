from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import orev3.experiments.rq003_experiment2c as experiment2c_module
from orev3.experiments.rq003_execution_specification import (
    SourceCommitProvenance,
    SourceScopeBinding,
)
from orev3.experiments.rq003_experiment2a import (
    IDENTICAL_RANK_VECTORS,
    STRICT_ORDERING_CHANGE,
    TIE_ONLY_CHANGE,
    CanonicalRational,
    OutcomeBlindReplayPopulation,
)
from orev3.experiments.rq003_experiment2c import (
    CHARACTERIZATION_ARTIFACT_NAME,
    EXPERIMENT2C_ARTIFACT_NAMES,
    MINER_VS_DEPLOYMENT,
    MINER_VS_DEPLOYMENT_PER_MINER,
    ORDERING_DISTRIBUTIONS_ARTIFACT_NAME,
    Experiment2CConfiguration,
    characterize_miner_count_ordering,
    execute_experiment2c,
    validate_experiment2c_artifacts,
)
from orev3.historical.models import (
    ObservationReference,
    RoundLifecycleIndexRecord,
    RoundQualityMetadata,
)


def test_miner_count_comparisons_cover_all_ordering_classes_exactly() -> None:
    identical_and_tie = characterize_miner_count_ordering(
        [100, 80] + [0] * 23,
        [10, 8] + [0] * 23,
    )
    tie_and_strict = characterize_miner_count_ordering(
        [100, 100] + [0] * 23,
        [1, 2] + [0] * 23,
    )
    strict_both = characterize_miner_count_ordering(
        [100, 90] + [0] * 23,
        [1, 10] + [0] * 23,
    )

    assert identical_and_tie["comparisons"][MINER_VS_DEPLOYMENT][
        "classification"
    ] == IDENTICAL_RANK_VECTORS
    assert identical_and_tie["comparisons"][MINER_VS_DEPLOYMENT_PER_MINER][
        "classification"
    ] == TIE_ONLY_CHANGE
    assert tie_and_strict["comparisons"][MINER_VS_DEPLOYMENT][
        "classification"
    ] == TIE_ONLY_CHANGE
    assert tie_and_strict["comparisons"][MINER_VS_DEPLOYMENT_PER_MINER][
        "classification"
    ] == STRICT_ORDERING_CHANGE
    assert strict_both["comparisons"][MINER_VS_DEPLOYMENT][
        "classification"
    ] == STRICT_ORDERING_CHANGE
    assert strict_both["comparisons"][MINER_VS_DEPLOYMENT_PER_MINER][
        "classification"
    ] == STRICT_ORDERING_CHANGE

    comparison = strict_both["comparisons"][MINER_VS_DEPLOYMENT]
    assert comparison["strict_reversals"] == 1
    assert comparison["unordered_candidate_pair_count"] == 300
    assert len(comparison["absolute_rank_displacements"]) == 25
    assert CanonicalRational.from_dict(comparison["total_rank_displacement"]) > (
        CanonicalRational.make(0)
    )


def test_top_k_and_tie_statistics_are_exact_and_tie_preserving() -> None:
    characterization = characterize_miner_count_ordering(
        [100, 100, 50] + [0] * 22,
        [10, 5, 5] + [0] * 22,
    )

    miner_ties = characterization["tie_statistics"]["miner_count"]
    assert miner_ties["non_singleton_group_sizes"] == (2, 22)
    assert miner_ties["candidate_tie_count"] == 24
    comparison = characterization["comparisons"][MINER_VS_DEPLOYMENT]
    assert comparison["top_k_membership_changes"]["1"] == {
        "changed": True,
        "primary_only_count": 1,
        "reference_only_count": 0,
    }
    assert all(
        CanonicalRational.from_dict(value).denominator in {1, 2}
        for value in characterization["miner_count_average_ranks"]
    )


def test_end_to_end_synthetic_execution_is_outcome_blind_and_v2_conformant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    output = tmp_path / "artifacts"
    _bind_frozen_test_source(monkeypatch)

    result = execute_experiment2c(_configuration(dataset, population, output))

    assert result.replay_rounds == 4
    assert result.eligible_decisions == 3
    assert result.excluded_decisions == 1
    assert tuple(sorted(path.name for path in output.iterdir())) == tuple(
        sorted(EXPERIMENT2C_ARTIFACT_NAMES)
    )
    records = _load_jsonl(output / CHARACTERIZATION_ARTIFACT_NAME)
    assert len(records) == 3
    assert all(tuple(record["comparisons"]) == tuple(sorted((
        MINER_VS_DEPLOYMENT,
        MINER_VS_DEPLOYMENT_PER_MINER,
    ))) for record in records)
    manifest = _load_json(output / "experiment_audit_manifest.json")
    assert manifest["execution_profile"]["execution_profile"] == (
        "outcome_blind_characterization_v1"
    )
    assert manifest["terminal"]["outcome_access"] == (
        "prohibited_and_not_performed"
    )
    assert manifest["terminal"]["outcome_aware_extension"] == "absent"
    artifact_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output.iterdir()
        if path.suffix in {".json", ".jsonl"}
    )
    for prohibited in (
        '"winning_square"',
        '"label"',
        '"outcome"',
        '"outcome_source"',
        '"evaluation"',
        '"baseline"',
    ):
        assert prohibited not in artifact_text
    assert validate_experiment2c_artifacts(
        output, replay_dataset_path=dataset
    ) == result.artifacts


def test_exact_empirical_distributions_cover_both_comparisons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    output = tmp_path / "artifacts"
    _bind_frozen_test_source(monkeypatch)
    execute_experiment2c(_configuration(dataset, population, output))

    report = _load_json(output / ORDERING_DISTRIBUTIONS_ARTIFACT_NAME)
    for comparison_name in (MINER_VS_DEPLOYMENT, MINER_VS_DEPLOYMENT_PER_MINER):
        comparison = report["comparisons"][comparison_name]
        assert sum(entry["count"] for entry in comparison["class_counts"]) == 3
        assert sum(
            entry["count"]
            for entry in comparison["distributions"][
                "candidate_absolute_rank_displacement"
            ]
        ) == 75
        assert sum(
            entry["count"]
            for entry in comparison["distributions"]["top_3_changed"]
        ) == 3


def test_synthetic_regeneration_is_byte_identical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    _bind_frozen_test_source(monkeypatch)

    first = execute_experiment2c(
        _configuration(dataset, population, tmp_path / "first")
    )
    second = execute_experiment2c(
        _configuration(dataset, population, tmp_path / "second")
    )

    assert first.replay_identity == second.replay_identity
    assert first.audit_manifest_identity == second.audit_manifest_identity
    for name in EXPERIMENT2C_ARTIFACT_NAMES:
        assert (tmp_path / "first" / name).read_bytes() == (
            tmp_path / "second" / name
        ).read_bytes()


def test_zero_miner_inconsistency_fails_closed_without_partial_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(
        tmp_path,
        override_first=([1] + [0] * 24, [0] * 25),
    )
    output = tmp_path / "artifacts"
    _bind_frozen_test_source(monkeypatch)

    with pytest.raises(ValueError, match="positive deployment with zero miners"):
        execute_experiment2c(_configuration(dataset, population, output))
    assert not output.exists()


def test_validator_rejects_generated_artifact_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    output = tmp_path / "artifacts"
    _bind_frozen_test_source(monkeypatch)
    execute_experiment2c(_configuration(dataset, population, output))
    path = output / CHARACTERIZATION_ARTIFACT_NAME
    path.write_bytes(path.read_bytes() + b"{}\n")

    with pytest.raises(ValueError):
        validate_experiment2c_artifacts(output, replay_dataset_path=dataset)


def test_configuration_is_immutable_and_module_has_no_outcome_capability(
    tmp_path: Path,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    configuration = Experiment2CConfiguration(
        replay_dataset_path=dataset,
        replay_population=population,
        output_directory=tmp_path / "output",
        expected_dataset_sha256="a" * 64,
    )
    with pytest.raises(FrozenInstanceError):
        configuration.requested_slots_remaining = 6  # type: ignore[misc]

    tree = ast.parse(inspect.getsource(experiment2c_module))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "OutcomeJoinAuthorization" not in imported_names
    assert "authorize_profiled_outcome_join" not in imported_names
    assert "open_profiled_outcome_source" not in imported_names
    assert not any("economics" in module for module in imported_modules)
    assert not any("strategies" in module for module in imported_modules)


def _configuration(
    dataset: Path,
    population: OutcomeBlindReplayPopulation,
    output: Path,
) -> Experiment2CConfiguration:
    return Experiment2CConfiguration(
        replay_dataset_path=dataset,
        replay_population=population,
        output_directory=output,
        expected_dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),
    )


def _bind_frozen_test_source(monkeypatch: pytest.MonkeyPatch) -> None:
    provenance = SourceCommitProvenance(
        "a" * 40,
        (SourceScopeBinding("src/orev3", "b" * 40),),
    )
    monkeypatch.setattr(
        experiment2c_module,
        "_bind_execution_source",
        lambda configuration: provenance,
    )


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_synthetic_dataset(
    tmp_path: Path,
    *,
    override_first: tuple[list[int], list[int]] | None = None,
) -> tuple[Path, OutcomeBlindReplayPopulation]:
    raw_path = tmp_path / "observer.jsonl"
    replay_path = tmp_path / "replay.jsonl"
    patterns = [
        ([100, 80] + [0] * 23, [10, 8] + [0] * 23, "complete"),
        ([100, 100] + [0] * 23, [1, 2] + [0] * 23, "complete"),
        ([100, 90] + [0] * 23, [1, 10] + [0] * 23, "complete"),
        ([50, 25] + [0] * 23, [1, 1] + [0] * 23, "partial_start"),
    ]
    if override_first is not None:
        patterns[0] = (override_first[0], override_first[1], "complete")
    raw_records: list[dict[str, object]] = []
    lifecycles: list[RoundLifecycleIndexRecord] = []
    base_time = datetime(2026, 8, 15, tzinfo=UTC)
    for offset, (deployed, miners, coverage) in enumerate(patterns):
        round_id = 200 + offset
        start_slot = round_id * 100
        end_slot = start_slot + 20
        rpc_slot = end_slot - 5
        observed_at = base_time + timedelta(seconds=offset)
        raw_records.append(
            {
                "board": {
                    "end_slot": end_slot,
                    "production_cost_ema": 1_000,
                    "round_id": round_id,
                    "start_slot": start_slot,
                },
                "collector_session_id": "synthetic-session",
                "observed_at_utc": observed_at.isoformat(),
                "round": {
                    "deployed_lamports": deployed,
                    "entropy": None,
                    "expires_at": end_slot,
                    "mass": [0] * 25,
                    "miner_counts": miners,
                    "motherlode": 0,
                    "rewards": [0] * 25,
                    "round_id": round_id,
                    "slot_hash_hex": "00" * 32,
                    "top_miner": "11111111111111111111111111111111",
                    "total_miners": sum(miners),
                    "total_vaulted": 0,
                    "total_winnings": 0,
                },
                "rpc_slot": rpc_slot,
                "schema_version": 2,
                "treasury": {"motherlode": 2_000},
            }
        )
        reference = ObservationReference(
            source_file=str(raw_path),
            source_line_number=offset + 1,
            observed_at_utc=observed_at,
            rpc_slot=rpc_slot,
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
                collector_session_ids=["synthetic-session"],
                source_schema_versions=[2],
                source_files=[str(raw_path)],
                observation_references=[reference],
                finalized_outcome=None,
                finalized_outcome_source=None,
                finalized_outcome_capture_mode=None,
                finalized_outcome_evidence_identities=(),
                quality=RoundQualityMetadata(
                    coverage_status=coverage,
                    initialization_state_observed=coverage == "complete",
                    rpc_slot_regression_count=0,
                    largest_rpc_slot_regression=0,
                    duplicate_rpc_slot_count=0,
                    max_observation_gap_seconds=0.0,
                    significant_gap_count=0,
                    significant_gap_threshold_seconds=5.0,
                    collector_session_count=1,
                    finalized_state_observed=False,
                ),
            )
        )
    raw_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in raw_records),
        encoding="utf-8",
    )
    replay_path.write_text(
        "".join(
            json.dumps(
                lifecycle.model_dump(mode="json"),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
            for lifecycle in lifecycles
        ),
        encoding="utf-8",
    )
    return replay_path, OutcomeBlindReplayPopulation(tuple(lifecycles))
