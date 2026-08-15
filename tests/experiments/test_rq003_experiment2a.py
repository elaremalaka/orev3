from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import orev3.experiments.rq003_experiment2a as experiment2a_module
from orev3.experiments.rq003_execution_specification import (
    SourceCommitProvenance,
    SourceScopeBinding,
)
from orev3.experiments.rq003_experiment2a import (
    CHARACTERIZATION_ARTIFACT_NAME,
    EXPERIMENT2A_ARTIFACT_NAMES,
    FINDING_002_ARTIFACT_NAME,
    GOVERNANCE_DISPOSITION_ARTIFACT_NAME,
    IDENTICAL_RANK_VECTORS,
    ORDERING_DISTRIBUTIONS_ARTIFACT_NAME,
    OutcomeBlindReplayPopulation,
    STRICT_ORDERING_CHANGE,
    THEORETICAL_BOUND_ARTIFACT_NAME,
    TIE_ONLY_CHANGE,
    CanonicalRational,
    Experiment2AConfiguration,
    characterize_orderings,
    deployment_per_miner,
    exact_average_ranks,
    execute_experiment2a,
    validate_experiment2a_artifacts,
)
from orev3.historical.models import (
    ObservationReference,
    RoundLifecycleIndexRecord,
    RoundQualityMetadata,
)


def test_canonical_rational_reduces_reconstructs_and_compares_exactly() -> None:
    value = CanonicalRational.make(100, 10)
    reconstructed = CanonicalRational.from_dict(value.to_dict())

    assert value == CanonicalRational(10, 1)
    assert reconstructed == value
    assert CanonicalRational.make(1, 3) < CanonicalRational.make(2, 5)
    assert CanonicalRational.make(2, 5).absolute_difference(
        CanonicalRational.make(1, 3)
    ) == CanonicalRational.make(1, 15)
    with pytest.raises(ValueError, match="canonically reduced"):
        CanonicalRational(2, 2)
    with pytest.raises(ValueError, match="identity does not reconstruct"):
        CanonicalRational.from_dict(
            {"denominator": 1, "numerator": 10, "rational_identity": "0" * 64}
        )


def test_deployment_per_miner_zero_rules_are_exhaustive() -> None:
    ordinary, empty = deployment_per_miner(90, 6)
    zero, zero_empty = deployment_per_miner(0, 0)

    assert ordinary == CanonicalRational.make(15)
    assert empty is False
    assert zero == CanonicalRational.make(0, 1)
    assert zero_empty is True
    with pytest.raises(ValueError, match="positive deployment with zero miners"):
        deployment_per_miner(1, 0)


def test_exact_average_rank_vectors_preserve_ties_without_floats() -> None:
    values = [0] * 25
    values[0] = 10
    values[1] = 10
    values[2] = 5

    ranks = exact_average_ranks(values)

    assert ranks[0] == ranks[1] == CanonicalRational.make(3, 2)
    assert ranks[2] == CanonicalRational.make(3)
    assert all(rank == CanonicalRational.make(29, 2) for rank in ranks[3:])
    assert exact_average_ranks([0] * 25) == (CanonicalRational.make(13),) * 25


def test_ordering_classes_and_exact_upper_bounds() -> None:
    identical = characterize_orderings([0] * 25, [0] * 25)
    tie_only = characterize_orderings(
        [100, 100] + [0] * 23,
        [1, 2] + [0] * 23,
    )
    strict = characterize_orderings(
        [100, 90] + [0] * 23,
        [10, 1] + [0] * 23,
    )

    assert identical["classification"] == IDENTICAL_RANK_VECTORS
    assert identical["empty_square_extension_count"] == 25
    assert CanonicalRational.from_dict(
        identical["theoretical_mrr_improvement_upper_bound"]
    ) == CanonicalRational.make(0)
    assert tie_only["classification"] == TIE_ONLY_CHANGE
    assert tie_only["strict_reversals"] == 0
    assert tie_only["tie_to_strict_changes"] == 1
    assert CanonicalRational.from_dict(
        tie_only["theoretical_mrr_improvement_upper_bound"]
    ) == CanonicalRational.make(1, 3)
    assert strict["classification"] == STRICT_ORDERING_CHANGE
    assert strict["strict_reversals"] == 1
    assert strict["unordered_candidate_pair_count"] == 300
    assert len(strict["absolute_rank_displacements"]) == 25
    assert CanonicalRational.from_dict(
        strict["theoretical_mrr_improvement_upper_bound"]
    ) == CanonicalRational.make(1, 2)


def test_end_to_end_synthetic_execution_is_outcome_blind_and_v2_conformant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    output = tmp_path / "artifacts"
    _bind_frozen_test_source(monkeypatch)

    result = execute_experiment2a(_configuration(dataset, population, output))

    assert result.replay_rounds == 4
    assert result.eligible_decisions == 3
    assert result.excluded_decisions == 1
    assert tuple(sorted(path.name for path in output.iterdir())) == tuple(
        sorted(EXPERIMENT2A_ARTIFACT_NAMES)
    )
    records = _load_jsonl(output / CHARACTERIZATION_ARTIFACT_NAME)
    assert [record["classification"] for record in records] == [
        IDENTICAL_RANK_VECTORS,
        TIE_ONLY_CHANGE,
        STRICT_ORDERING_CHANGE,
    ]
    manifest = _load_json(output / "experiment_audit_manifest.json")
    assert manifest["execution_profile"]["execution_profile"] == (
        "outcome_blind_characterization_v1"
    )
    assert manifest["terminal"]["outcome_access"] == (
        "prohibited_and_not_performed"
    )
    assert manifest["terminal"]["outcome_aware_extension"] == "absent"
    governance = _load_json(output / GOVERNANCE_DISPOSITION_ARTIFACT_NAME)
    assert governance["continuation_disposition"] == (
        "research_governance_decision_required"
    )
    assert governance["experiment_2b_authorized"] is False
    bound = _load_json(output / THEORETICAL_BOUND_ARTIFACT_NAME)
    assert CanonicalRational.from_dict(bound["population_upper_bound"]) == (
        CanonicalRational.make(5, 18)
    )
    finding = _load_json(output / FINDING_002_ARTIFACT_NAME)
    assert finding["characterization_validity"] == "valid"
    assert finding["delta_min_governance_status"] == "not_established"

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
    assert validate_experiment2a_artifacts(
        output,
        replay_dataset_path=dataset,
    ) == result.artifacts


def test_exact_empirical_distributions_are_canonical_and_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    output = tmp_path / "artifacts"
    _bind_frozen_test_source(monkeypatch)
    execute_experiment2a(_configuration(dataset, population, output))

    report = _load_json(output / ORDERING_DISTRIBUTIONS_ARTIFACT_NAME)
    assert [entry["classification"] for entry in report["class_counts"]] == [
        IDENTICAL_RANK_VECTORS,
        TIE_ONLY_CHANGE,
        STRICT_ORDERING_CHANGE,
    ]
    assert [entry["count"] for entry in report["class_counts"]] == [1, 1, 1]
    pairwise = report["distributions"]["pairwise_sign_disagreements"]
    assert [CanonicalRational.from_dict(entry["value"]) for entry in pairwise] == [
        CanonicalRational.make(0),
        CanonicalRational.make(1),
    ]
    assert sum(entry["count"] for entry in pairwise) == 3
    assert sum(
        entry["count"]
        for entry in report["distributions"]["candidate_absolute_rank_displacement"]
    ) == 75
    assert report["empty_square_extension"]["candidate_instances"] == 69


def test_synthetic_regeneration_is_byte_identical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    _bind_frozen_test_source(monkeypatch)

    first = execute_experiment2a(
        _configuration(dataset, population, tmp_path / "first")
    )
    second = execute_experiment2a(
        _configuration(dataset, population, tmp_path / "second")
    )

    assert first.replay_identity == second.replay_identity
    assert first.audit_manifest_identity == second.audit_manifest_identity
    for name in EXPERIMENT2A_ARTIFACT_NAMES:
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
        execute_experiment2a(_configuration(dataset, population, output))
    assert not output.exists()


def test_validator_rejects_artifact_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    output = tmp_path / "artifacts"
    _bind_frozen_test_source(monkeypatch)
    execute_experiment2a(_configuration(dataset, population, output))
    path = output / CHARACTERIZATION_ARTIFACT_NAME
    path.write_bytes(path.read_bytes() + b"{}\n")

    with pytest.raises(ValueError):
        validate_experiment2a_artifacts(output, replay_dataset_path=dataset)


def test_configuration_is_immutable_and_scope_has_no_outcome_capability(
    tmp_path: Path,
) -> None:
    dataset, population = _write_synthetic_dataset(tmp_path)
    configuration = Experiment2AConfiguration(
        replay_dataset_path=dataset,
        replay_population=population,
        output_directory=tmp_path / "output",
        expected_dataset_sha256="a" * 64,
    )
    with pytest.raises(FrozenInstanceError):
        configuration.requested_slots_remaining = 6  # type: ignore[misc]

    tree = ast.parse(inspect.getsource(experiment2a_module))
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


def test_outcome_blind_population_rejects_outcome_state(tmp_path: Path) -> None:
    _, population = _write_synthetic_dataset(tmp_path)
    lifecycle = population.lifecycles[0]
    quality = lifecycle.quality.model_copy(update={"finalized_state_observed": True})
    contaminated = lifecycle.model_copy(update={"quality": quality})

    with pytest.raises(ValueError, match="exposes outcome state"):
        OutcomeBlindReplayPopulation((contaminated,))


def _configuration(
    dataset: Path,
    population: OutcomeBlindReplayPopulation,
    output: Path,
) -> Experiment2AConfiguration:
    return Experiment2AConfiguration(
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
        experiment2a_module,
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
        ([100, 80] + [0] * 23, [1, 1] + [0] * 23, "complete"),
        ([100, 100] + [0] * 23, [1, 2] + [0] * 23, "complete"),
        ([100, 90] + [0] * 23, [10, 1] + [0] * 23, "complete"),
        ([50, 25] + [0] * 23, [1, 1] + [0] * 23, "partial_start"),
    ]
    if override_first is not None:
        patterns[0] = (override_first[0], override_first[1], "complete")
    raw_records: list[dict[str, object]] = []
    lifecycles: list[RoundLifecycleIndexRecord] = []
    base_time = datetime(2026, 8, 15, tzinfo=UTC)
    for offset, (deployed, miners, coverage) in enumerate(patterns):
        round_id = 100 + offset
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
