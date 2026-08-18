from __future__ import annotations

import json
from pathlib import Path

import pytest

from orev3.execution.canonical import CanonicalControlError, domain_identity, parse_json, validate_json_schema_instance
from orev3.execution.contract_validation import PROFILE_CONTRACT_DOMAIN, reconstruct_profile_binding_identity, validate_artifact_declarations, validate_profile_contract
from orev3.execution.dataset_validation import dataset_evidence, projection_evidence
from orev3.execution.projection import canonical_jsonl, project_jsonl
from orev3.execution.replay_preparation import build_replay_evidence, load_verified_projection, require_deterministic_reconstruction
from orev3.execution.phase3b_components import require_projection_contract_binding
from orev3.execution.registry import ARTIFACT_DECLARATION_DOMAIN

H = "1" * 64


def bound_artifact(**material: object) -> dict[str, object]:
    result = dict(material)
    result["declaration_identity"] = domain_identity(ARTIFACT_DECLARATION_DOMAIN, result)
    return result


def bound_profile(
    profile_name: str, outcome_policy: str, declarations: dict[str, dict[str, object]]
) -> dict[str, object]:
    return {
        "declarations": declarations,
        "outcome_policy": outcome_policy,
        "profile_identity": reconstruct_profile_binding_identity(
            profile_name=profile_name,
            outcome_policy=outcome_policy,
            declarations=declarations,
        ),
        "profile_name": profile_name,
    }


def bound_contract(identifier: str, **material: object) -> dict[str, object]:
    result = {"contract_identifier": identifier, **material}
    result["contract_identity"] = domain_identity(PROFILE_CONTRACT_DOMAIN, result)
    return result


def projection_schema() -> dict[str, object]:
    properties = {"candidates": {"items": {"type": "integer"}, "minItems": 1, "type": "array", "uniqueItems": True}, "eligible": {"type": "boolean"}, "exclusion_reason": {"enum": ["missing_observation", "not_applicable"], "type": "string"}, "observation_index": {"minimum": 0, "type": "integer"}, "source_unit_key": {"pattern": "^[a-z0-9-]+$", "type": "string"}}
    return {"additionalProperties": False, "properties": properties, "required": sorted(properties), "type": "object"}


def raw_schema() -> dict[str, object]:
    result = projection_schema(); result["properties"] = {**result["properties"], "outcome": {"type": "string"}}  # type: ignore[dict-item]
    result["required"] = sorted(result["properties"])  # type: ignore[arg-type]
    return result


def projected_records() -> list[dict[str, object]]:
    return [
        {"candidates": [1, 2], "eligible": True, "exclusion_reason": "not_applicable", "observation_index": 0, "source_unit_key": "unit-a"},
        {"candidates": [1, 2], "eligible": True, "exclusion_reason": "not_applicable", "observation_index": 1, "source_unit_key": "unit-a"},
        {"candidates": [1, 2], "eligible": False, "exclusion_reason": "missing_observation", "observation_index": 0, "source_unit_key": "unit-b"},
    ]


def test_projection_is_exact_allowlist_and_deterministic(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    payload = {**projected_records()[0], "outcome": "secret"}
    raw.write_bytes(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode() + b"\n")
    digest = __import__("hashlib").sha256(raw.read_bytes()).hexdigest()
    first, count, _ = project_jsonl(raw, raw_schema=raw_schema(), projection_schema=projection_schema(), expected_raw_sha256=digest, expected_raw_size=raw.stat().st_size, max_raw_bytes=10000, max_projection_bytes=10000, max_records=10)
    second, _, _ = project_jsonl(raw, raw_schema=raw_schema(), projection_schema=projection_schema(), expected_raw_sha256=digest, expected_raw_size=raw.stat().st_size, max_raw_bytes=10000, max_projection_bytes=10000, max_records=10)
    assert first == second and count == 1 and b"outcome" not in first and b"secret" not in first
    with pytest.raises(CanonicalControlError, match="unknown fields"):
        canonical_jsonl([{**projected_records()[0], "outcome": "x"}], projection_schema=projection_schema())


@pytest.mark.parametrize(
    "leak",
    (
        {"outcome": "OUTCOME-SENTINEL"}, {"winner": "OUTCOME-SENTINEL"},
        {"label": "OUTCOME-SENTINEL"}, {"metadata": {"value": "OUTCOME-SENTINEL"}},
        {"provenance": {"value": "OUTCOME-SENTINEL"}}, {"result": "OUTCOME-SENTINEL"},
        {"extension": {"value": "OUTCOME-SENTINEL"}}, {"blob": "T1VUQ09NRS1TRU5USU5FTA=="},
        {"unknown": "OUTCOME-SENTINEL"}, {"auxiliary": ["OUTCOME-SENTINEL"]},
    ),
)
def test_projection_contract_rejects_every_undeclared_outcome_channel(leak: dict[str, object]) -> None:
    with pytest.raises(CanonicalControlError) as caught:
        canonical_jsonl([{**projected_records()[0], **leak}], projection_schema=projection_schema())
    assert "OUTCOME-SENTINEL" not in str(caught.value)


@pytest.mark.parametrize("keyword", ("patternProperties", "unevaluatedProperties", "$ref"))
def test_projection_schema_cannot_add_extension_channels(keyword: str) -> None:
    schema = projection_schema()
    schema[keyword] = {} if keyword != "$ref" else "synthetic://broad-schema"
    with pytest.raises(CanonicalControlError, match="PROJECTION_SCHEMA_INVALID"):
        canonical_jsonl(projected_records(), projection_schema=schema)


def test_nested_projection_structure_and_replay_revalidation_reject(tmp_path: Path) -> None:
    malformed = {**projected_records()[0], "candidates": [1, {"value": "OUTCOME-SENTINEL"}]}
    raw = json.dumps(malformed, separators=(",", ":"), sort_keys=True).encode() + b"\n"
    path = tmp_path / "projection"; path.write_bytes(raw)
    with pytest.raises(CanonicalControlError) as caught:
        load_verified_projection(path, expected_sha256=__import__("hashlib").sha256(raw).hexdigest(), expected_size=len(raw), projection_schema=projection_schema(), max_bytes=10000, max_units=10)
    assert "OUTCOME-SENTINEL" not in str(caught.value)


def test_adapter_cannot_broaden_repository_projection_contract() -> None:
    governed = {
        "dataset_validator_identifier": "canonical-jsonl-dataset-validator-v1", "output_container": "canonical_jsonl",
        "projection_contract_identifier": "synthetic-v1", "projection_schema_identifier": "closed-v1",
        "projection_schema_identity": "1" * 64, "projection_schema_path": "tests/fixtures/closed.json",
        "projection_schema_sha256": "2" * 64, "projector_identifier": "canonical-jsonl-outcome-blind-projector-v1",
        "raw_parser_identifier": "canonical-jsonl-raw-parser-v1", "raw_schema_identifier": "raw-v1",
        "raw_schema_identity": "3" * 64, "raw_schema_path": "tests/fixtures/raw.json", "raw_schema_sha256": "4" * 64,
    }
    descriptor = dict(governed)
    descriptor["container"] = descriptor.pop("output_container")
    del descriptor["raw_schema_identity"]
    require_projection_contract_binding(governed, descriptor, "3" * 64)
    descriptor["projection_schema_path"] = "tests/fixtures/adapter-broadened.json"
    with pytest.raises(CanonicalControlError, match="repository authority"):
        require_projection_contract_binding(governed, descriptor, "3" * 64)


def test_replay_population_is_complete_and_double_reconstruction_matches() -> None:
    args = dict(dataset_identity=H, projection_identity="2" * 64, selector_identifier="latest-eligible-observation-selector-v1", selector_component_identity="3" * 64, replay_preparer_component_identity="4" * 64, configuration_identity="5" * 64, candidate_order=[1, 2], allowed_exclusion_reasons=["missing_observation"], max_units=10)
    first = build_replay_evidence(projected_records(), **args)
    second = build_replay_evidence(projected_records(), **args)
    require_deterministic_reconstruction(first, second)
    assert first[1]["source_count"] == first[1]["included_count"] + first[1]["excluded_count"]
    changed = projected_records()[::-1]
    with pytest.raises(CanonicalControlError, match="REPLAY_NONDETERMINISTIC"):
        require_deterministic_reconstruction(first, build_replay_evidence(changed, **args))
    earlier = projected_records(); earlier[1]["eligible"] = False; earlier[1]["exclusion_reason"] = "missing_observation"
    reconstructed = build_replay_evidence(earlier, **args)
    assert reconstructed[0]["ordered_decision_identities"] != first[0]["ordered_decision_identities"]
    assert reconstructed[0]["replay_identity"] != first[0]["replay_identity"]


def test_population_rejects_duplicate_and_ungoverned_exclusion() -> None:
    duplicate = projected_records(); duplicate[1]["observation_index"] = duplicate[0]["observation_index"]
    with pytest.raises(CanonicalControlError, match="POPULATION_MISMATCH"):
        build_replay_evidence(duplicate, dataset_identity=H, projection_identity=H, selector_identifier="latest-eligible-observation-selector-v1", selector_component_identity=H, replay_preparer_component_identity=H, configuration_identity=H, candidate_order=[1, 2], allowed_exclusion_reasons=["missing_observation"], max_units=10)


def test_profile_and_artifact_contracts_are_static_and_fail_closed() -> None:
    declaration = bound_artifact(artifact_identifier="report", artifact_kind="characterization_report", container="json", dependencies=[], dependency_roles=[], execution_phase="characterization", profile_applicability="outcome_blind_characterization_v1", relative_path="artifacts/report.json", schema_identity="3" * 64)
    profile = validate_profile_contract(bound_profile("outcome_blind_characterization_v1", "prohibited_and_not_performed", {}), artifact_declarations=[declaration])
    assert profile["outcome_capability"] == "prohibited_and_not_performed"
    evidence = validate_artifact_declarations([declaration], profile_name="outcome_blind_characterization_v1")
    assert evidence["declaration_identities"] == [declaration["declaration_identity"]]
    cycle = [bound_artifact(**{key: value for key, value in declaration.items() if key != "declaration_identity"} | {"dependencies": ["report"]})]
    with pytest.raises(CanonicalControlError, match="cycle"):
        validate_artifact_declarations(cycle, profile_name="outcome_blind_characterization_v1")


def test_profile_and_artifact_semantic_contradictions_reject() -> None:
    ranking = bound_artifact(artifact_identifier="ranking", artifact_kind="ranking_artifact", container="json", dependencies=[], dependency_roles=["replay"], execution_phase="ranking", profile_applicability="outcome_aware_v1", relative_path="artifacts/ranking.json", schema_identity="2" * 64)
    evaluation = bound_artifact(artifact_identifier="evaluation", artifact_kind="evaluation_report", container="json", dependencies=["ranking"], dependency_roles=["authorization", "outcome", "ranking"], execution_phase="evaluation", profile_applicability="outcome_aware_v1", relative_path="artifacts/evaluation.json", schema_identity="4" * 64)
    contracts = {
        "authorization_contract_identity": bound_contract("authorization_contract_identity", contract_kind="outcome-authorization", evaluation_artifact_identifier="evaluation", outcome_access="authorization_required"),
        "evaluation_dependency_graph_identity": bound_contract("evaluation_dependency_graph_identity", contract_kind="evaluation-dependency-graph", edges=[["authorization", "evaluation"], ["outcome_source", "evaluation"], ["ranking", "evaluation"]], evaluation_artifact_identifier="evaluation", ranking_artifact_identifier="ranking"),
        "freeze_contract_identity": bound_contract("freeze_contract_identity", contract_kind="ranking-freeze", ranking_artifact_identifier="ranking", ranking_frozen_before_outcome=True),
        "outcome_blind_ranking_source_identity": bound_contract("outcome_blind_ranking_source_identity", contract_kind="outcome-blind-ranking-source", outcome_blind=True, ranking_artifact_identifier="ranking"),
        "outcome_source_identity": bound_contract("outcome_source_identity", contract_kind="outcome-source", external_input_identifier="synthetic-outcome", outcome_source_role="declared_external_input"),
        "ranking_artifact_identifier": bound_contract("ranking_artifact_identifier", artifact_identifier="ranking", contract_kind="ranking-artifact-reference"),
    }
    profile = bound_profile("outcome_aware_v1", "outcome_aware_authorized_only", contracts)
    validate_artifact_declarations([ranking, evaluation], profile_name="outcome_aware_v1")
    validate_profile_contract(profile, artifact_declarations=[ranking, evaluation])
    for missing in ("ranking_artifact_identifier", "freeze_contract_identity", "authorization_contract_identity"):
        broken = dict(contracts); del broken[missing]
        with pytest.raises(CanonicalControlError, match="PROFILE_POLICY_MISMATCH"):
            validate_profile_contract({**profile, "declarations": broken}, artifact_declarations=[ranking, evaluation])
    broken_graph = dict(contracts); broken_graph["evaluation_dependency_graph_identity"] = {**contracts["evaluation_dependency_graph_identity"], "edges": [["ranking", "evaluation"]]}
    with pytest.raises(CanonicalControlError, match="PROFILE_POLICY_MISMATCH"):
        validate_profile_contract({**profile, "declarations": broken_graph}, artifact_declarations=[ranking, evaluation])
    with pytest.raises(CanonicalControlError, match="profile|artifact kind"):
        validate_artifact_declarations([evaluation], profile_name="outcome_blind_characterization_v1")
    impossible_evaluation = bound_artifact(**{key: value for key, value in evaluation.items() if key != "declaration_identity"} | {"execution_phase": "ranking"})
    impossible = [ranking, impossible_evaluation]
    with pytest.raises(CanonicalControlError, match="phase"):
        validate_artifact_declarations(impossible, profile_name="outcome_aware_v1")


def test_profile_contracts_reject_unknown_fields_after_identity_reconstruction() -> None:
    authorization = bound_contract(
        "authorization_contract_identity",
        contract_kind="outcome-authorization",
        evaluation_artifact_identifier="evaluation",
        outcome_access="authorization_required",
    )
    material = dict(authorization)
    material.pop("contract_identity")
    material["authorization_bypass"] = True
    material["contract_identity"] = domain_identity(
        PROFILE_CONTRACT_DOMAIN,
        {key: value for key, value in material.items() if key != "contract_identity"},
    )
    with pytest.raises(CanonicalControlError, match="contract fields"):
        validate_profile_contract(
            bound_profile(
                "outcome_aware_v1",
                "outcome_aware_authorized_only",
                {
                    "authorization_contract_identity": material,
                    "evaluation_dependency_graph_identity": bound_contract("evaluation_dependency_graph_identity", contract_kind="evaluation-dependency-graph", edges=[["authorization", "evaluation"], ["outcome_source", "evaluation"], ["ranking", "evaluation"]], evaluation_artifact_identifier="evaluation", ranking_artifact_identifier="ranking"),
                    "freeze_contract_identity": bound_contract("freeze_contract_identity", contract_kind="ranking-freeze", ranking_artifact_identifier="ranking", ranking_frozen_before_outcome=True),
                    "outcome_blind_ranking_source_identity": bound_contract("outcome_blind_ranking_source_identity", contract_kind="outcome-blind-ranking-source", outcome_blind=True, ranking_artifact_identifier="ranking"),
                    "outcome_source_identity": bound_contract("outcome_source_identity", contract_kind="outcome-source", external_input_identifier="synthetic-outcome", outcome_source_role="declared_external_input"),
                    "ranking_artifact_identifier": bound_contract("ranking_artifact_identifier", artifact_identifier="ranking", contract_kind="ranking-artifact-reference"),
                },
            ),
            artifact_declarations=[],
        )


@pytest.mark.parametrize(
    ("contract_name", "field", "value"),
    (
        ("authorization_contract_identity", "outcome_access", None),
        ("authorization_contract_identity", "outcome_access", 1),
        ("authorization_contract_identity", "outcome_access", "bypass_allowed"),
        ("freeze_contract_identity", "ranking_frozen_before_outcome", 1),
        ("outcome_blind_ranking_source_identity", "outcome_blind", "true"),
        ("outcome_source_identity", "outcome_source_role", "ambient_locator"),
        ("ranking_artifact_identifier", "artifact_identifier", "Not Stable"),
    ),
)
def test_profile_contracts_reject_null_wrong_type_and_invalid_enums(
    contract_name: str, field: str, value: object
) -> None:
    contracts = {
        "authorization_contract_identity": bound_contract("authorization_contract_identity", contract_kind="outcome-authorization", evaluation_artifact_identifier="evaluation", outcome_access="authorization_required"),
        "evaluation_dependency_graph_identity": bound_contract("evaluation_dependency_graph_identity", contract_kind="evaluation-dependency-graph", edges=[["authorization", "evaluation"], ["outcome_source", "evaluation"], ["ranking", "evaluation"]], evaluation_artifact_identifier="evaluation", ranking_artifact_identifier="ranking"),
        "freeze_contract_identity": bound_contract("freeze_contract_identity", contract_kind="ranking-freeze", ranking_artifact_identifier="ranking", ranking_frozen_before_outcome=True),
        "outcome_blind_ranking_source_identity": bound_contract("outcome_blind_ranking_source_identity", contract_kind="outcome-blind-ranking-source", outcome_blind=True, ranking_artifact_identifier="ranking"),
        "outcome_source_identity": bound_contract("outcome_source_identity", contract_kind="outcome-source", external_input_identifier="synthetic-outcome", outcome_source_role="declared_external_input"),
        "ranking_artifact_identifier": bound_contract("ranking_artifact_identifier", artifact_identifier="ranking", contract_kind="ranking-artifact-reference"),
    }
    changed = dict(contracts[contract_name])
    changed[field] = value
    if value is not None:
        material = {key: item for key, item in changed.items() if key != "contract_identity"}
        changed["contract_identity"] = domain_identity(PROFILE_CONTRACT_DOMAIN, material)
    contracts[contract_name] = changed
    with pytest.raises(CanonicalControlError, match="PROFILE_POLICY_MISMATCH"):
        validate_profile_contract(
            bound_profile("outcome_aware_v1", "outcome_aware_authorized_only", contracts),
            artifact_declarations=[],
        )


def test_profile_graph_must_equal_actual_artifact_dag() -> None:
    ranking = bound_artifact(artifact_identifier="ranking", artifact_kind="ranking_artifact", container="json", dependencies=[], dependency_roles=["replay"], execution_phase="ranking", profile_applicability="outcome_aware_v1", relative_path="artifacts/ranking.json", schema_identity="2" * 64)
    replay = bound_artifact(artifact_identifier="replay", artifact_kind="replay_manifest", container="json", dependencies=[], dependency_roles=[], execution_phase="ranking", profile_applicability="outcome_aware_v1", relative_path="artifacts/replay.json", schema_identity="3" * 64)
    evaluation = bound_artifact(artifact_identifier="evaluation", artifact_kind="evaluation_report", container="json", dependencies=["replay"], dependency_roles=["authorization", "outcome", "ranking"], execution_phase="evaluation", profile_applicability="outcome_aware_v1", relative_path="artifacts/evaluation.json", schema_identity="4" * 64)
    contracts = {
        "authorization_contract_identity": bound_contract("authorization_contract_identity", contract_kind="outcome-authorization", evaluation_artifact_identifier="evaluation", outcome_access="authorization_required"),
        "evaluation_dependency_graph_identity": bound_contract("evaluation_dependency_graph_identity", contract_kind="evaluation-dependency-graph", edges=[["authorization", "evaluation"], ["outcome_source", "evaluation"], ["ranking", "evaluation"]], evaluation_artifact_identifier="evaluation", ranking_artifact_identifier="ranking"),
        "freeze_contract_identity": bound_contract("freeze_contract_identity", contract_kind="ranking-freeze", ranking_artifact_identifier="ranking", ranking_frozen_before_outcome=True),
        "outcome_blind_ranking_source_identity": bound_contract("outcome_blind_ranking_source_identity", contract_kind="outcome-blind-ranking-source", outcome_blind=True, ranking_artifact_identifier="ranking"),
        "outcome_source_identity": bound_contract("outcome_source_identity", contract_kind="outcome-source", external_input_identifier="synthetic-outcome", outcome_source_role="declared_external_input"),
        "ranking_artifact_identifier": bound_contract("ranking_artifact_identifier", artifact_identifier="ranking", contract_kind="ranking-artifact-reference"),
    }
    validate_artifact_declarations([ranking, replay, evaluation], profile_name="outcome_aware_v1")
    with pytest.raises(CanonicalControlError, match="artifact dependency graph"):
        validate_profile_contract(bound_profile("outcome_aware_v1", "outcome_aware_authorized_only", contracts), artifact_declarations=[ranking, replay, evaluation])


@pytest.mark.parametrize(
    "case",
    (
        "profile-ranking-differs",
        "missing-ranking-dependency",
        "missing-authorization-role",
        "missing-evaluation-artifact",
        "nonexistent-profile-artifact",
        "duplicate-ranking-role",
        "contradictory-phase",
    ),
)
def test_outcome_aware_profile_and_artifact_graph_are_one_structure(case: str) -> None:
    ranking_identifier = "ranking"
    evaluation_identifier = "evaluation"
    ranking = bound_artifact(artifact_identifier="ranking", artifact_kind="ranking_artifact", container="json", dependencies=[], dependency_roles=["replay"], execution_phase="ranking", profile_applicability="outcome_aware_v1", relative_path="artifacts/ranking.json", schema_identity="2" * 64)
    evaluation = bound_artifact(artifact_identifier="evaluation", artifact_kind="evaluation_report", container="json", dependencies=["ranking"], dependency_roles=["authorization", "outcome", "ranking"], execution_phase="evaluation", profile_applicability="outcome_aware_v1", relative_path="artifacts/evaluation.json", schema_identity="4" * 64)
    declarations = [ranking, evaluation]
    if case == "profile-ranking-differs":
        ranking_identifier = "ranking-a"
    elif case == "missing-ranking-dependency":
        evaluation = bound_artifact(**{key: value for key, value in evaluation.items() if key != "declaration_identity"} | {"dependencies": []})
        declarations = [ranking, evaluation]
    elif case == "missing-authorization-role":
        evaluation = bound_artifact(**{key: value for key, value in evaluation.items() if key != "declaration_identity"} | {"dependency_roles": ["outcome", "ranking"]})
        declarations = [ranking, evaluation]
    elif case == "missing-evaluation-artifact":
        declarations = [ranking]
    elif case == "nonexistent-profile-artifact":
        evaluation_identifier = "missing-evaluation"
    elif case == "duplicate-ranking-role":
        second = bound_artifact(artifact_identifier="ranking-b", artifact_kind="ranking_artifact", container="json", dependencies=[], dependency_roles=["replay"], execution_phase="ranking", profile_applicability="outcome_aware_v1", relative_path="artifacts/ranking-b.json", schema_identity="5" * 64)
        declarations = [ranking, second, evaluation]
    elif case == "contradictory-phase":
        evaluation = bound_artifact(**{key: value for key, value in evaluation.items() if key != "declaration_identity"} | {"execution_phase": "ranking"})
        declarations = [ranking, evaluation]
    contracts = {
        "authorization_contract_identity": bound_contract("authorization_contract_identity", contract_kind="outcome-authorization", evaluation_artifact_identifier=evaluation_identifier, outcome_access="authorization_required"),
        "evaluation_dependency_graph_identity": bound_contract("evaluation_dependency_graph_identity", contract_kind="evaluation-dependency-graph", edges=[["authorization", "evaluation"], ["outcome_source", "evaluation"], ["ranking", "evaluation"]], evaluation_artifact_identifier=evaluation_identifier, ranking_artifact_identifier=ranking_identifier),
        "freeze_contract_identity": bound_contract("freeze_contract_identity", contract_kind="ranking-freeze", ranking_artifact_identifier=ranking_identifier, ranking_frozen_before_outcome=True),
        "outcome_blind_ranking_source_identity": bound_contract("outcome_blind_ranking_source_identity", contract_kind="outcome-blind-ranking-source", outcome_blind=True, ranking_artifact_identifier=ranking_identifier),
        "outcome_source_identity": bound_contract("outcome_source_identity", contract_kind="outcome-source", external_input_identifier="synthetic-outcome", outcome_source_role="declared_external_input"),
        "ranking_artifact_identifier": bound_contract("ranking_artifact_identifier", artifact_identifier=ranking_identifier, contract_kind="ranking-artifact-reference"),
    }
    with pytest.raises(CanonicalControlError):
        validate_artifact_declarations(declarations, profile_name="outcome_aware_v1")
        validate_profile_contract(
            bound_profile("outcome_aware_v1", "outcome_aware_authorized_only", contracts),
            artifact_declarations=declarations,
        )


def test_characterization_profile_rejects_contracts_and_outcome_dependencies() -> None:
    authorization = bound_contract(
        "authorization_contract_identity",
        contract_kind="outcome-authorization",
        evaluation_artifact_identifier="evaluation",
        outcome_access="authorization_required",
    )
    with pytest.raises(CanonicalControlError, match="PROFILE_POLICY_MISMATCH"):
        validate_profile_contract(
            bound_profile(
                "outcome_blind_characterization_v1",
                "prohibited_and_not_performed",
                {"authorization_contract_identity": authorization},
            ),
            artifact_declarations=[],
        )
    report = bound_artifact(artifact_identifier="report", artifact_kind="characterization_report", container="json", dependencies=[], dependency_roles=["outcome"], execution_phase="characterization", profile_applicability="outcome_blind_characterization_v1", relative_path="artifacts/report.json", schema_identity="3" * 64)
    with pytest.raises(CanonicalControlError, match="outcome dependency"):
        validate_artifact_declarations([report], profile_name="outcome_blind_characterization_v1")


def test_profile_evidence_binds_closed_contracts_and_artifact_dag() -> None:
    declaration = bound_artifact(artifact_identifier="report", artifact_kind="characterization_report", container="json", dependencies=[], dependency_roles=[], execution_phase="characterization", profile_applicability="outcome_blind_characterization_v1", relative_path="artifacts/report.json", schema_identity="3" * 64)
    first = validate_profile_contract(bound_profile("outcome_blind_characterization_v1", "prohibited_and_not_performed", {}), artifact_declarations=[declaration])
    changed = bound_artifact(**{key: value for key, value in declaration.items() if key != "declaration_identity"} | {"schema_identity": "4" * 64})
    second = validate_profile_contract(bound_profile("outcome_blind_characterization_v1", "prohibited_and_not_performed", {}), artifact_declarations=[changed])
    assert first["profile_conformance_evidence_identity"] != second["profile_conformance_evidence_identity"]
    assert first["reconciled_artifact_declaration_identities"] == [declaration["declaration_identity"]]


def test_generated_replay_population_profile_and_artifact_objects_match_exact_schemas() -> None:
    root = Path("src/orev3/execution/schemas/v1")
    args = dict(dataset_identity=H, projection_identity="2" * 64, selector_identifier="latest-eligible-observation-selector-v1", selector_component_identity="3" * 64, replay_preparer_component_identity="4" * 64, configuration_identity="5" * 64, candidate_order=[1, 2], allowed_exclusion_reasons=["missing_observation"], max_units=10)
    replay, population = build_replay_evidence(projected_records(), **args)
    declaration = bound_artifact(artifact_identifier="report", artifact_kind="characterization_report", container="json", dependencies=[], dependency_roles=[], execution_phase="characterization", profile_applicability="outcome_blind_characterization_v1", relative_path="artifacts/report.json", schema_identity="3" * 64)
    profile = validate_profile_contract(bound_profile("outcome_blind_characterization_v1", "prohibited_and_not_performed", {}), artifact_declarations=[declaration])
    artifact = validate_artifact_declarations([declaration], profile_name="outcome_blind_characterization_v1")
    for name, material in (("replay-evidence", replay), ("population-accounting-evidence", population), ("profile-conformance-evidence", profile), ("artifact-declaration-evidence", artifact)):
        schema = parse_json((root / f"{name}.schema.json").read_bytes())
        validate_json_schema_instance(material, schema, schema_registry={})


def test_generated_dataset_and_projection_objects_match_exact_schemas() -> None:
    dataset = dataset_evidence(external_input_identity=H, snapshot_identity="2" * 64, source_class="combined_outcome_bearing", dataset_version="synthetic-v1", container="canonical_jsonl", parser_component_identity="3" * 64, validator_component_identity="4" * 64, schema_identity="5" * 64, protocol_revision="v1", record_count=1, record_ordering="source_order", candidate_order=["1"], projection_required=True, dataset_content_identity="6" * 64)
    projection_bytes = canonical_jsonl([projected_records()[0]], projection_schema=projection_schema())
    projection = projection_evidence(raw_snapshot_identity="2" * 64, raw_dataset_identity=dataset["dataset_identity"], parser_component_identity="3" * 64, projector_component_identity="5" * 64, projection_schema_identity="6" * 64, allowed_fields=sorted(projection_schema()["properties"]), projection_bytes=projection_bytes, record_count=1)
    root = Path("src/orev3/execution/schemas/v1")
    for name, material in (("dataset-validation-evidence", dataset), ("outcome-blind-projection-evidence", projection)):
        validate_json_schema_instance(material, parse_json((root / f"{name}.schema.json").read_bytes()), schema_registry={})


def test_dataset_identity_binds_parser_schema_content_and_order() -> None:
    base = dict(external_input_identity=H, snapshot_identity="2" * 64, source_class="combined_outcome_bearing", dataset_version="synthetic-v1", container="canonical_jsonl", parser_component_identity="3" * 64, validator_component_identity="4" * 64, schema_identity="5" * 64, protocol_revision="v1", record_count=2, record_ordering="source_order", candidate_order=["1", "2"], projection_required=True, dataset_content_identity="6" * 64)
    original = dataset_evidence(**base)
    for field, value in (("parser_component_identity", "7" * 64), ("schema_identity", "8" * 64), ("dataset_content_identity", "9" * 64), ("record_ordering", "reverse_source_order")):
        changed = dict(base); changed[field] = value
        assert dataset_evidence(**changed)["dataset_identity"] != original["dataset_identity"]
