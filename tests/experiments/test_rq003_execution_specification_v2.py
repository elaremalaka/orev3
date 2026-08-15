from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from orev3.experiments.rq003_execution_specification import (
    EXECUTION_SPECIFICATION_REVISION,
    EXECUTION_SPECIFICATION_SHA256,
    ArtifactDeclaration,
    EvaluationDisposition,
    ExecutionSpecificationBinding,
    PopulationDisposition,
    ReplayDatasetBinding,
    SourceCommitProvenance,
    SourceScopeBinding,
    canonical_json,
    construct_artifact_contract,
    write_canonical_json_once,
    write_canonical_jsonl_once,
)
from orev3.experiments.rq003_execution_specification_v2 import (
    EXECUTION_SPECIFICATION_V2_REVISION,
    EXECUTION_SPECIFICATION_V2_SHA256,
    OUTCOME_AWARE_PROFILE,
    OUTCOME_BLIND_CHARACTERIZATION_PROFILE,
    ExecutionProfileBinding,
    ExecutionSpecificationV2Binding,
    ExperimentProtocolV2Binding,
    OutcomeAwareTerminal,
    OutcomeBlindCharacterizationTerminal,
    ProfiledExperimentAuditManifest,
    ProfiledExperimentConfiguration,
    ProfiledArtifactDeclaration,
    ProfiledOutcomeBlindProvenanceBlock,
    ProfiledReplayIdentity,
    authorize_profiled_outcome_join,
    construct_profile_artifact_contract,
    freeze_profiled_outcome_blind_provenance,
    seal_profiled_audit_manifest,
    validate_profiled_audit_manifest,
)


def test_v1_binding_and_identity_remain_unchanged() -> None:
    binding = ExecutionSpecificationBinding(
        EXECUTION_SPECIFICATION_REVISION,
        EXECUTION_SPECIFICATION_SHA256,
    )

    assert EXECUTION_SPECIFICATION_REVISION == "rq003-research-execution-specification-v1"
    assert EXECUTION_SPECIFICATION_SHA256 == "3f7da6977f3a4f7c31766c856fc9cc000ed6a6a0d4dffcbf6e5cd0193d948eb2"
    assert binding.specification_identity == "00917dff4dbd72bc7f18183ab913b9bb394f26dc37cf97b1f3825fd199a4afdc"


def test_v2_contracts_are_immutable_and_profile_bound() -> None:
    aware = _bindings(OUTCOME_AWARE_PROFILE)
    blind = _bindings(OUTCOME_BLIND_CHARACTERIZATION_PROFILE)

    assert aware[0].revision == EXECUTION_SPECIFICATION_V2_REVISION
    assert aware[0].document_sha256 == EXECUTION_SPECIFICATION_V2_SHA256
    assert aware[1].profile_identity != blind[1].profile_identity
    assert aware[2].experiment_configuration_identity != blind[2].experiment_configuration_identity
    assert aware[2].experiment_binding_identity != blind[2].experiment_binding_identity
    assert aware[3].replay_identity != blind[3].replay_identity
    with pytest.raises(FrozenInstanceError):
        aware[1].profile = OUTCOME_BLIND_CHARACTERIZATION_PROFILE  # type: ignore[misc]
    with pytest.raises(ValueError, match="unsupported"):
        ExecutionProfileBinding("unknown_profile")


def test_v2_document_binding_and_experiment_2a_consumer_are_frozen() -> None:
    root = Path(__file__).resolve().parents[2]
    specification_path = root / "docs/research/specifications/rq003-research-execution-specification-v2.md"
    experiment_path = root / "docs/research/experiments/rq003-experiment-002a-deployment-per-miner-characterization.md"

    assert hashlib.sha256(specification_path.read_bytes()).hexdigest() == (
        EXECUTION_SPECIFICATION_V2_SHA256
    )
    experiment_text = experiment_path.read_text(encoding="utf-8")
    assert "rq003-research-execution-specification-v2.md" in experiment_text
    assert EXECUTION_SPECIFICATION_V2_SHA256 in experiment_text
    assert f"`{OUTCOME_BLIND_CHARACTERIZATION_PROFILE}`" in experiment_text


def test_outcome_blind_profile_lifecycle_seals_and_reconstructs(tmp_path: Path) -> None:
    manifest = _execute_blind_lifecycle(tmp_path)
    manifest_path = tmp_path / "experiment_audit_manifest.json"

    material = validate_profiled_audit_manifest(manifest_path, expected=manifest)

    assert material["execution_profile"]["execution_profile"] == OUTCOME_BLIND_CHARACTERIZATION_PROFILE
    assert material["terminal"]["outcome_access"] == "prohibited_and_not_performed"
    assert material["terminal"]["outcome_aware_extension"] == "absent"
    assert {entry["contract"]["declaration"]["artifact_kind"] for entry in material["artifact_contracts"]} == {
        "characterization",
        "conformance",
        "descriptive_report",
        "outcome_blind_provenance",
    }


def test_outcome_aware_profile_lifecycle_seals_and_reconstructs(tmp_path: Path) -> None:
    manifest = _execute_aware_lifecycle(tmp_path)

    material = validate_profiled_audit_manifest(
        tmp_path / "experiment_audit_manifest.json", expected=manifest
    )

    assert material["execution_profile"]["execution_profile"] == OUTCOME_AWARE_PROFILE
    assert material["terminal"]["terminal_kind"] == "outcome_aware"
    assert len(material["terminal"]["evaluation_dispositions"]) == 1


def test_profiles_reject_wrong_terminal_and_artifact_graph(tmp_path: Path) -> None:
    block, contracts = _blind_artifacts(tmp_path)
    # The terminal type mismatch is rejected before its authorization could be
    # used; the immutable object still requires a structurally valid identity.
    aware_block = _provenance(
        OUTCOME_AWARE_PROFILE,
        (("ranking", ArtifactDeclaration("ranking", 1, "jsonl", "replay_order")),),
    )
    ranking_path = tmp_path / "wrong-profile-ranking.jsonl"
    ranking_records = ({"decision_identity": "3" * 64, "ranking": list(range(25))},)
    write_canonical_jsonl_once(ranking_path, ranking_records)
    ranking = construct_profile_artifact_contract(
        ranking_path,
        aware_block.downstream_artifact_declarations[0][1].declaration,
        ranking_records,
        (aware_block.provenance_block_identity,),
        aware_block.profile,
    )
    aware_terminal = OutcomeAwareTerminal(
        authorize_profiled_outcome_join(aware_block, ranking),
        (
            EvaluationDisposition(
                round_identity="1" * 64,
                round_reference="round-1",
                status="excluded",
                reason="missing_outcome",
                outcome_source_identity=None,
            ),
        )
    )
    with pytest.raises(ValueError, match="requires OutcomeBlindCharacterizationTerminal"):
        ProfiledExperimentAuditManifest(block, contracts, aware_terminal, "passed")

    outcome_path = tmp_path / "outcome.jsonl"
    outcome_path.write_bytes(b'{"winning_square":3}\n')
    declaration = ArtifactDeclaration("outcome_source", 1, "jsonl", "replay_order")
    with pytest.raises(ValueError, match="prohibited"):
        construct_profile_artifact_contract(
            outcome_path,
            declaration,
            ({"winning_square": 3},),
            (block.provenance_block_identity,),
            block.profile,
        )


def test_outcome_blind_profile_cannot_create_outcome_authorization(tmp_path: Path) -> None:
    block, contracts = _blind_artifacts(tmp_path)
    characterization = dict(contracts)["characterization"]

    with pytest.raises(ValueError, match="prohibits outcome authorization"):
        authorize_profiled_outcome_join(block, characterization)  # type: ignore[arg-type]


def test_characterization_rejects_outcome_fields_and_noncanonical_bytes(tmp_path: Path) -> None:
    profile = ExecutionProfileBinding(OUTCOME_BLIND_CHARACTERIZATION_PROFILE)
    declaration = ArtifactDeclaration("characterization", 1, "jsonl", "replay_order")
    path = tmp_path / "characterization.jsonl"
    write_canonical_jsonl_once(path, ({"winning_square": 2},))
    with pytest.raises(ValueError, match="outcome information"):
        construct_profile_artifact_contract(path, declaration, ({"winning_square": 2},), ("a" * 64,), profile)

    noncanonical = tmp_path / "noncanonical.jsonl"
    noncanonical.write_bytes(b'{"z":1,"a":2}\n')
    with pytest.raises(ValueError, match="not canonical"):
        construct_profile_artifact_contract(noncanonical, declaration, ({"a": 2, "z": 1},), ("a" * 64,), profile)


def test_manifest_identity_and_bytes_regenerate_deterministically(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    first_manifest = _execute_blind_lifecycle(first)
    second_manifest = _execute_blind_lifecycle(second)

    assert first_manifest == second_manifest
    for name in (
        "outcome_blind_provenance.json",
        "characterization.jsonl",
        "descriptive_report.json",
        "conformance.json",
        "experiment_audit_manifest.json",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_manifest_reconstruction_fails_closed_on_profile_tampering(tmp_path: Path) -> None:
    _execute_blind_lifecycle(tmp_path)
    path = tmp_path / "experiment_audit_manifest.json"
    material = json.loads(path.read_text(encoding="utf-8"))
    material["execution_profile"]["execution_profile"] = OUTCOME_AWARE_PROFILE
    damaged = tmp_path / "damaged.json"
    damaged.write_text(canonical_json(material) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="profile_identity does not reconstruct"):
        validate_profiled_audit_manifest(damaged)


def test_experiment_2a_profile_binding_is_outcome_blind() -> None:
    _, profile, experiment, replay, _, _ = _bindings(
        OUTCOME_BLIND_CHARACTERIZATION_PROFILE,
        experiment_identifier="rq003_experiment_002a",
    )

    assert profile.profile == OUTCOME_BLIND_CHARACTERIZATION_PROFILE
    assert experiment.profile == profile
    assert replay.profile_identity == profile.profile_identity


def _bindings(
    profile_name: str,
    *,
    experiment_identifier: str = "rq003_profile_test",
) -> tuple[
    ExecutionSpecificationV2Binding,
    ExecutionProfileBinding,
    ExperimentProtocolV2Binding,
    ProfiledReplayIdentity,
    SourceCommitProvenance,
    tuple[PopulationDisposition, ...],
]:
    specification = ExecutionSpecificationV2Binding()
    profile = ExecutionProfileBinding(profile_name)
    configuration = ProfiledExperimentConfiguration(profile, "b" * 64)
    experiment = ExperimentProtocolV2Binding(
        experiment_identifier=experiment_identifier,
        protocol_revision="1",
        protocol_document_sha256="a" * 64,
        specification=specification,
        profile=profile,
        configuration=configuration,
    )
    source = SourceCommitProvenance(
        "c" * 40,
        (SourceScopeBinding("src/experiment.py", "d" * 40),),
    )
    dataset = ReplayDatasetBinding("replay-dataset-v1", "e" * 64, 100, "f" * 64)
    replay = ProfiledReplayIdentity(
        specification_identity=specification.specification_identity,
        profile_identity=profile.profile_identity,
        experiment_binding_identity=experiment.experiment_binding_identity,
        experiment_configuration_identity=experiment.experiment_configuration_identity,
        source_commit_provenance_identity=source.source_commit_provenance_identity,
        dataset=dataset,
        protocol_revision_identity="0" * 64,
        decision_selection_configuration_identity="1" * 64,
        ordered_replay_round_identities=("1" * 64, "2" * 64),
        canonical_candidate_order=tuple(range(25)),
    )
    dispositions = (
        PopulationDisposition("1" * 64, "round-1", "eligible", None, "3" * 64),
        PopulationDisposition("2" * 64, "round-2", "excluded", "no_decision", None),
    )
    return specification, profile, experiment, replay, source, dispositions


def _provenance(
    profile_name: str,
    declarations: tuple[tuple[str, ArtifactDeclaration], ...],
) -> ProfiledOutcomeBlindProvenanceBlock:
    specification, profile, experiment, replay, source, dispositions = _bindings(profile_name)
    profiled_declarations = tuple(
        (name, ProfiledArtifactDeclaration(profile.profile_identity, declaration))
        for name, declaration in declarations
    )
    return ProfiledOutcomeBlindProvenanceBlock(
        specification=specification,
        profile=profile,
        experiment=experiment,
        source_commit=source,
        replay=replay,
        component_identities=(("measurement_pipeline", "4" * 64),),
        population_dispositions=dispositions,
        upstream_artifact_contracts=(),
        downstream_artifact_declarations=profiled_declarations,
    )


def _blind_artifacts(
    root: Path,
) -> tuple[ProfiledOutcomeBlindProvenanceBlock, tuple[tuple[str, object], ...]]:
    characterization_declaration = ArtifactDeclaration("characterization", 1, "jsonl", "replay_order")
    conformance_declaration = ArtifactDeclaration("conformance", 1, "json", "single_canonical_record")
    report_declaration = ArtifactDeclaration("descriptive_report", 1, "json", "single_canonical_record")
    declarations = (
        ("characterization", characterization_declaration),
        ("conformance", conformance_declaration),
        ("descriptive_report", report_declaration),
    )
    block = _provenance(OUTCOME_BLIND_CHARACTERIZATION_PROFILE, declarations)
    provenance_contract = freeze_profiled_outcome_blind_provenance(root / "outcome_blind_provenance.json", block)
    characterization_records = ({"decision_identity": "3" * 64, "ordering_class": "identical"},)
    write_canonical_jsonl_once(root / "characterization.jsonl", characterization_records)
    characterization = construct_profile_artifact_contract(
        root / "characterization.jsonl",
        characterization_declaration,
        characterization_records,
        (block.provenance_block_identity,),
        block.profile,
    )
    report_record = {"characterization_contract_identity": characterization.artifact_contract_identity, "decisions": 1}
    write_canonical_json_once(root / "descriptive_report.json", report_record)
    report = construct_profile_artifact_contract(
        root / "descriptive_report.json",
        report_declaration,
        (report_record,),
        (characterization.artifact_contract_identity,),
        block.profile,
    )
    conformance_record = {"characterization_contract_identity": characterization.artifact_contract_identity, "status": "passed"}
    write_canonical_json_once(root / "conformance.json", conformance_record)
    conformance = construct_profile_artifact_contract(
        root / "conformance.json",
        conformance_declaration,
        (conformance_record,),
        (characterization.artifact_contract_identity,),
        block.profile,
    )
    contracts = (
        ("characterization", characterization),
        ("conformance", conformance),
        ("descriptive_report", report),
        ("outcome_blind_provenance", provenance_contract),
    )
    return block, contracts  # type: ignore[return-value]


def _execute_blind_lifecycle(root: Path) -> ProfiledExperimentAuditManifest:
    block, contracts = _blind_artifacts(root)
    terminal = OutcomeBlindCharacterizationTerminal(block.population_dispositions)
    manifest = ProfiledExperimentAuditManifest(block, contracts, terminal, "passed")  # type: ignore[arg-type]
    seal_profiled_audit_manifest(root / "experiment_audit_manifest.json", manifest)
    return manifest


def _execute_aware_lifecycle(root: Path) -> ProfiledExperimentAuditManifest:
    ranking_declaration = ArtifactDeclaration("ranking", 1, "jsonl", "replay_order")
    outcome_declaration = ArtifactDeclaration("outcome_source", 1, "jsonl", "replay_order")
    evaluation_declaration = ArtifactDeclaration("evaluation", 1, "jsonl", "replay_order")
    declarations = (
        ("evaluation", evaluation_declaration),
        ("outcome_source", outcome_declaration),
        ("ranking", ranking_declaration),
    )
    block = _provenance(OUTCOME_AWARE_PROFILE, declarations)
    provenance = freeze_profiled_outcome_blind_provenance(root / "outcome_blind_provenance.json", block)
    ranking_records = ({"decision_identity": "3" * 64, "ranking": list(range(25))},)
    write_canonical_jsonl_once(root / "ranking.jsonl", ranking_records)
    ranking = construct_profile_artifact_contract(root / "ranking.jsonl", ranking_declaration, ranking_records, (block.provenance_block_identity,), block.profile)
    outcome_records = ({"round_reference": "round-1", "winning_square": 2},)
    # External sources preserve deterministic persisted bytes without requiring sorted keys.
    (root / "outcomes.jsonl").write_bytes(b'{"winning_square":2,"round_reference":"round-1"}\n')
    outcome = construct_artifact_contract(root / "outcomes.jsonl", outcome_declaration, outcome_records, (ranking.artifact_contract_identity,))
    evaluation_records = ({"round_reference": "round-1", "winner_rank": 3},)
    write_canonical_jsonl_once(root / "evaluation.jsonl", evaluation_records)
    evaluation = construct_profile_artifact_contract(
        root / "evaluation.jsonl",
        evaluation_declaration,
        evaluation_records,
        (ranking.artifact_contract_identity, outcome.artifact_contract_identity),
        block.profile,
    )
    authorization = authorize_profiled_outcome_join(block, ranking)
    terminal = OutcomeAwareTerminal(
        authorization,
        (EvaluationDisposition("1" * 64, "round-1", "evaluated", "outcome_available", outcome.artifact_contract_identity),),
    )
    contracts = (
        ("evaluation", evaluation),
        ("outcome_blind_provenance", provenance),
        ("outcome_source", outcome),
        ("ranking", ranking),
    )
    manifest = ProfiledExperimentAuditManifest(block, contracts, terminal, "passed")
    seal_profiled_audit_manifest(root / "experiment_audit_manifest.json", manifest)
    return manifest
