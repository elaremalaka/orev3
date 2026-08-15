from __future__ import annotations

import json
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from orev3.experiments.rq003_execution_specification import (
    AUDIT_MANIFEST_NAME,
    EXECUTION_SPECIFICATION_REVISION,
    EXECUTION_SPECIFICATION_SHA256,
    OUTCOME_BLIND_PROVENANCE_NAME,
    ArtifactDeclaration,
    EvaluationDisposition,
    ExecutionSpecificationBinding,
    ExperimentAuditManifest,
    ExperimentProtocolBinding,
    OutcomeBlindProvenanceBlock,
    PopulationDisposition,
    ReplayDatasetBinding,
    ReplayIdentity,
    SourceCommitProvenance,
    SourceScopeBinding,
    authorize_outcome_join,
    bind_source_commit,
    canonical_json,
    construct_artifact_contract,
    freeze_outcome_blind_provenance,
    identity,
    open_canonical_outcome_source,
    seal_audit_manifest,
    validate_audit_manifest,
    validate_population_accounting,
    write_canonical_json_once,
    write_canonical_jsonl_once,
)


def test_contracts_are_immutable_and_reconstruct_deterministically() -> None:
    first = _bindings()
    second = _bindings()

    assert first == second
    assert first[0].specification_identity == second[0].specification_identity
    assert first[1].experiment_binding_identity == second[1].experiment_binding_identity
    assert first[2].source_commit_provenance_identity == (
        second[2].source_commit_provenance_identity
    )
    assert canonical_json(first[1].to_dict()) == canonical_json(second[1].to_dict())
    with pytest.raises(FrozenInstanceError):
        first[0].revision = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="unsupported"):
        ExecutionSpecificationBinding(
            "future-revision",
            EXECUTION_SPECIFICATION_SHA256,
        )


def test_experiment_protocol_revision_is_distinct_identity_authority() -> None:
    specification, first, _ = _bindings()
    second = ExperimentProtocolBinding(
        experiment_identifier=first.experiment_identifier,
        protocol_revision="2",
        protocol_document_sha256=first.protocol_document_sha256,
        specification=specification,
        experiment_configuration_identity=first.experiment_configuration_identity,
    )

    assert first.protocol_revision == "1"
    assert second.protocol_revision == "2"
    assert first.experiment_binding_identity != second.experiment_binding_identity


def test_source_commit_binding_requires_one_clean_frozen_tree(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "rq003@example.invalid")
    _git(repository, "config", "user.name", "RQ003 Test")
    source = repository / "implementation.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repository, "add", "implementation.py")
    _git(repository, "commit", "-qm", "freeze source")
    commit = _git(repository, "rev-parse", "HEAD").strip()

    provenance = bind_source_commit(repository, commit, ("implementation.py",))

    assert provenance.commit_sha == commit
    assert provenance.scopes[0].repository_path == "implementation.py"
    source.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from commit"):
        bind_source_commit(repository, commit, ("implementation.py",))


def test_population_accounting_is_exact_ordered_and_fail_closed() -> None:
    replay, dispositions = _replay_and_dispositions()

    validate_population_accounting(replay, dispositions)
    with pytest.raises(ValueError, match="Replay order"):
        validate_population_accounting(replay, tuple(reversed(dispositions)))
    with pytest.raises(ValueError, match="Replay order"):
        validate_population_accounting(replay, dispositions[:1])


def test_complete_manifest_lifecycle_reconstructs_and_seals(tmp_path: Path) -> None:
    manifest = _execute_generic_lifecycle(tmp_path)
    manifest_path = tmp_path / AUDIT_MANIFEST_NAME

    material = validate_audit_manifest(manifest_path, expected=manifest)

    assert material["audit_manifest_identity"] == manifest.audit_manifest_identity
    assert material["outcome_blind_provenance"]["replay"]["replay_identity"] == (
        manifest.outcome_blind_provenance.replay.replay_identity
    )
    with pytest.raises(FileExistsError):
        seal_audit_manifest(manifest_path, manifest)


def test_manifest_rejects_unknown_fields_and_broken_identities(tmp_path: Path) -> None:
    _execute_generic_lifecycle(tmp_path)
    material = json.loads((tmp_path / AUDIT_MANIFEST_NAME).read_text(encoding="utf-8"))
    material["unexpected"] = True
    damaged = tmp_path / "damaged.json"
    damaged.write_text(canonical_json(material) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="schema is invalid"):
        validate_audit_manifest(damaged)


def test_ranking_contract_rejects_outcome_information(tmp_path: Path) -> None:
    declaration = ArtifactDeclaration(
        "ranking", 1, "jsonl", "replay_order"
    )
    record = {"decision_identity": "a" * 64, "winning_square": 3}
    path = tmp_path / "ranking.jsonl"
    write_canonical_jsonl_once(path, (record,))

    with pytest.raises(ValueError, match="outcome information"):
        construct_artifact_contract(path, declaration, (record,), ("b" * 64,))


def test_outcome_source_requires_frozen_ranking_authorization(tmp_path: Path) -> None:
    source = tmp_path / "outcomes.jsonl"
    write_canonical_jsonl_once(source, ({"round": 1, "outcome": 2},))

    with pytest.raises(TypeError, match="OutcomeJoinAuthorization"):
        open_canonical_outcome_source(source, object())  # type: ignore[arg-type]


def test_generic_lifecycle_regenerates_byte_identically(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    first_manifest = _execute_generic_lifecycle(first)
    second_manifest = _execute_generic_lifecycle(second)

    assert first_manifest == second_manifest
    for name in (
        OUTCOME_BLIND_PROVENANCE_NAME,
        "ranking.jsonl",
        "outcomes.jsonl",
        "evaluation.jsonl",
        AUDIT_MANIFEST_NAME,
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def _bindings() -> tuple[
    ExecutionSpecificationBinding,
    ExperimentProtocolBinding,
    SourceCommitProvenance,
]:
    specification = ExecutionSpecificationBinding(
        EXECUTION_SPECIFICATION_REVISION,
        EXECUTION_SPECIFICATION_SHA256,
    )
    experiment = ExperimentProtocolBinding(
        experiment_identifier="rq003-test-experiment",
        protocol_revision="1",
        protocol_document_sha256="1" * 64,
        specification=specification,
        experiment_configuration_identity="2" * 64,
    )
    source = SourceCommitProvenance(
        "3" * 40,
        (SourceScopeBinding("src/orev3", "4" * 40),),
    )
    return specification, experiment, source


def _replay_and_dispositions() -> tuple[
    ReplayIdentity, tuple[PopulationDisposition, ...]
]:
    specification, experiment, source = _bindings()
    dataset = ReplayDatasetBinding(
        dataset_version="test-v1",
        schema_identity="5" * 64,
        byte_count=12,
        sha256="6" * 64,
    )
    round_identities = ("7" * 64, "8" * 64)
    replay = ReplayIdentity(
        specification_identity=specification.specification_identity,
        experiment_binding_identity=experiment.experiment_binding_identity,
        experiment_configuration_identity="2" * 64,
        source_commit_provenance_identity=(
            source.source_commit_provenance_identity
        ),
        dataset=dataset,
        protocol_revision_identity="9" * 64,
        decision_selection_configuration_identity="a" * 64,
        ordered_replay_round_identities=round_identities,
        canonical_candidate_order=tuple(range(25)),
    )
    dispositions = (
        PopulationDisposition(
            round_identity=round_identities[0],
            round_reference="1",
            status="eligible",
            reason=None,
            decision_identity="b" * 64,
        ),
        PopulationDisposition(
            round_identity=round_identities[1],
            round_reference="2",
            status="excluded",
            reason="no_decision",
            decision_identity=None,
        ),
    )
    return replay, dispositions


def _execute_generic_lifecycle(root: Path) -> ExperimentAuditManifest:
    root.mkdir(parents=True, exist_ok=True)
    specification, experiment, source = _bindings()
    replay, dispositions = _replay_and_dispositions()
    declarations = {
        "audit": ArtifactDeclaration(
            "experiment_audit_manifest", 1, "json", "single_record"
        ),
        "evaluation": ArtifactDeclaration(
            "evaluation", 1, "jsonl", "replay_order"
        ),
        "outcomes": ArtifactDeclaration(
            "outcome_source", 1, "jsonl", "replay_order"
        ),
        "ranking": ArtifactDeclaration(
            "ranking", 1, "jsonl", "replay_order"
        ),
    }
    block = OutcomeBlindProvenanceBlock(
        specification=specification,
        experiment=experiment,
        source_commit=source,
        replay=replay,
        component_identities=(("ranking_component", "c" * 64),),
        population_dispositions=dispositions,
        upstream_artifact_contracts=(),
        downstream_artifact_declarations=tuple(sorted(declarations.items())),
    )
    provenance_contract = freeze_outcome_blind_provenance(
        root / OUTCOME_BLIND_PROVENANCE_NAME,
        block,
    )
    rankings = ({"decision_identity": "b" * 64, "round_reference": "1"},)
    ranking_path = root / "ranking.jsonl"
    write_canonical_jsonl_once(ranking_path, rankings)
    ranking_contract = construct_artifact_contract(
        ranking_path,
        declarations["ranking"],
        rankings,
        (block.provenance_block_identity,),
    )
    authorization = authorize_outcome_join(block, ranking_contract)
    outcome_records = ({"outcome": 3, "round_reference": "1"},)
    outcome_path = root / "outcomes.jsonl"
    write_canonical_jsonl_once(outcome_path, outcome_records)
    opened_outcomes = open_canonical_outcome_source(outcome_path, authorization)
    outcome_contract = construct_artifact_contract(
        outcome_path,
        declarations["outcomes"],
        opened_outcomes,
        (replay.dataset.dataset_identity,),
    )
    evaluations = ({"rank": 1.0, "round_reference": "1"},)
    evaluation_path = root / "evaluation.jsonl"
    write_canonical_jsonl_once(evaluation_path, evaluations)
    evaluation_contract = construct_artifact_contract(
        evaluation_path,
        declarations["evaluation"],
        evaluations,
        (
            ranking_contract.artifact_contract_identity,
            outcome_contract.artifact_contract_identity,
        ),
    )
    evaluation_dispositions = (
        EvaluationDisposition(
            round_identity="7" * 64,
            round_reference="1",
            status="evaluated",
            reason="primary",
            outcome_source_identity=identity(
                "rq003-test-outcome-v1", outcome_records[0]
            ),
        ),
    )
    manifest = ExperimentAuditManifest(
        outcome_blind_provenance=block,
        artifact_contracts=tuple(
            sorted(
                {
                    "evaluation": evaluation_contract,
                    "outcomes": outcome_contract,
                    "provenance": provenance_contract,
                    "ranking": ranking_contract,
                }.items()
            )
        ),
        evaluation_dispositions=evaluation_dispositions,
        execution_conformance_result="passed",
    )
    seal_audit_manifest(root / AUDIT_MANIFEST_NAME, manifest)
    return manifest


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ("git", *arguments),
        cwd=repository,
        text=True,
    )
