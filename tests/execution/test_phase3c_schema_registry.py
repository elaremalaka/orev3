from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from orev3.execution.canonical import (
    CanonicalControlError,
    parse_json,
    validate_json_schema_instance,
)
from orev3.execution.readiness_record import (
    PHASE2_SCHEMA_POLICY,
    PHASE3A_SCHEMA_POLICY,
    PHASE3B_SCHEMA_POLICY,
    READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
    READINESS_V1_1_SCHEMA_KIND_ORDER,
    READINESS_V1_1_SCHEMA_POLICY,
)
from orev3.execution.contract_validation import (
    reconstruct_profile_binding_identity,
    validate_profile_contract,
)


SCHEMA_ROOT = Path("src/orev3/execution/schemas/v1")
SHA = "1" * 64
GIT = "a" * 40
NEW_KINDS = {
    "attempt-allocation",
    "attempt-authority-contract",
    "attempt-control-record",
    "attempt-identity-material",
    "execution-control-manifest",
    "outcome-authorization",
    "output-namespace-identity-material",
    "profile-contract",
    "readiness-failure-receipt",
}
FINAL_KINDS = (
    "adapter-declaration",
    "adapter-registry",
    "artifact-declaration-evidence",
    "attempt-allocation",
    "attempt-authority-contract",
    "attempt-control-record",
    "attempt-identity-material",
    "dataset-validation-evidence",
    "evidence-preparation",
    "evidence-preparation-policy",
    "execution-control-manifest",
    "immutable-input-snapshot",
    "implementation-binding",
    "launch-authority-snapshot",
    "offline-artifact-manifest",
    "outcome-authorization",
    "outcome-blind-projection-evidence",
    "output-namespace-identity-material",
    "population-accounting-evidence",
    "profile-conformance-evidence",
    "profile-contract",
    "readiness-failure-receipt",
    "readiness-record",
    "readiness-test-evidence",
    "readiness-test-policy",
    "replay-evidence",
    "repository-authority",
    "runtime-contract",
    "source-scope",
)
INVARIANT_IDENTIFIERS = (
    "schema_registry",
    "experiment",
    "git_authority",
    "readiness_specification",
    "control_plane",
    "source_scopes",
    "protocol",
    "implementation",
    "execution_specification",
    "execution_profile",
    "runtime",
    "configuration",
    "external_inputs",
    "replay",
    "artifacts",
    "outcome_policy",
    "validation",
    "attempt_policy",
    "canonical_readiness_record",
    "readiness_seal_and_ancestry",
    "current_external_inputs",
    "launch_authority_snapshot",
    "launch_input_snapshots",
    "control_storage",
    "output_namespace",
    "launch_smoke",
    "second_fetch",
)
NON_READY_DISPOSITIONS = (
    "READINESS_UNRESOLVED_REMOTE",
    "READINESS_AMBIGUOUS",
    "READINESS_INVALID_RECORD",
    "READINESS_ORPHANED",
    "SUPERSEDED",
    "READINESS_STALE",
    "READINESS_INPUT_MISMATCH",
    "READINESS_BLOCKED_INPUT_UNAVAILABLE",
)


def _check_statuses(
    failed: str = "git_authority", *, receipt_class: str = "READINESS_REJECTED"
) -> list[dict[str, str]]:
    statuses = []
    for index, identifier in enumerate(INVARIANT_IDENTIFIERS):
        if identifier == failed:
            status = "failed"
        elif receipt_class == "READINESS_REJECTED" and index >= 19:
            status = "not_applicable"
        elif receipt_class == "CURRENT_READINESS" and index >= 21:
            status = "not_applicable"
        else:
            status = "not_evaluated"
        statuses.append({"check_identifier": identifier, "status": status})
    return statuses


def _coherent_history() -> dict[str, Any]:
    return {
        "common_prefix_record_identities": [],
        "control_history_kind": "coherent",
        "observed_control_objects": [],
    }


def _failure_evidence(
    failure_class: str = "infrastructure_failure",
    fact: str = "shared_control_storage_failure",
) -> dict[str, Any]:
    return {
        "control_history": _coherent_history(),
        "failure_boundary": "terminalization",
        "failure_class": failure_class,
        "last_durable_control_state": "ALLOCATED",
        "normalized_failure_fact": fact,
        "scientific_invalidity_established": False,
        "scientific_validity_established": False,
    }


def _conflicting_failure_evidence(
    *, slot_fact: str = "malformed_only", validated_records: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    evidence = _failure_evidence(
        "ambiguous_state", "conflicting_authoritative_control_records"
    )
    evidence["control_history"] = {
        "common_prefix_record_identities": [],
        "control_history_kind": "conflicting",
        "observed_control_objects": [
            {
                "authority_sequence": 1,
                "normalized_slot_fact": slot_fact,
                "object_kind": "conflicting_control_slot",
                "validated_records": validated_records or [],
            }
        ],
    }
    return evidence


def _schemas() -> dict[str, dict[str, Any]]:
    return {
        kind: parse_json(Path(path).read_bytes())
        for kind, (_, path) in READINESS_V1_1_SCHEMA_POLICY.items()
        if kind in NEW_KINDS
    }


def _representatives() -> dict[str, dict[str, Any]]:
    common_attempt = {
        "attempt_kind": "official",
        "experiment_identifier": "synthetic-experiment-001",
        "external_input_snapshot_identities": [SHA],
        "launch_authority_snapshot_identity": SHA,
        "ordinal": 1,
        "output_namespace_identity": SHA,
        "readiness_identity": SHA,
        "readiness_seal_commit": GIT,
        "remote_head_commit": GIT,
        "schema_version": 1,
        "source_commit": GIT,
    }
    return {
        "attempt-allocation": {
            **common_attempt,
            "allocation_authority_identity": SHA,
            "allocation_receipt_identity": SHA,
            "allocator_contract_identity": SHA,
            "attempt_identity": SHA,
        },
        "attempt-authority-contract": {
            "allocation_authority_identity": SHA,
            "allocation_authority_identity_material": {
                "allocation_authority_identifier": "shared-attempt-authority-v1",
                "allocation_authority_schema_revision": (
                    "allocation-authority-identity-material-v1"
                ),
                "repository_authority_identifier": "research-post-v1",
            },
            "allocation_receipt_policy": "immutable_write_once",
            "allocator_client_identifier": "shared-allocator-client-v1",
            "allocator_implementation_identifier": "shared-allocator-v1",
            "atomicity_semantics": "atomic_compare_and_create",
            "allocator_contract_identity": SHA,
            "collision_policy": "reject_any_existing_path",
            "contract_revision": "attempt-authority-v1",
            "control_storage_component": {
                "component_identifier": "shared-control-storage-v1",
                "component_identity": SHA,
                "git_object_identity": GIT,
                "path": "src/orev3/execution/control_storage.py",
                "role": "control_storage",
                "sha256": SHA,
            },
            "control_storage_contract_identity": SHA,
            "control_storage_contract_identity_material": {
                "attempt_control_record_schema_identifier": (
                    "attempt-control-record-v1"
                ),
                "control_storage_component_identity": SHA,
                "control_storage_contract_schema_revision": (
                    "control-storage-contract-identity-material-v1"
                ),
                "execution_control_manifest_schema_identifier": (
                    "execution-control-manifest-v1"
                ),
                "persistence_contract_revision": (
                    "shared-append-only-control-history-v1"
                ),
                "recovery_contract_revision": (
                    "atomic-no-live-owner-fence-and-append-failed-v1"
                ),
            },
            "ordinal_consumption_policy": "permanent_once_allocated",
            "ordinal_scope": "experiment_and_attempt_kind",
            "output_namespace_identity_policy": (
                "output-namespace-identity-material-v1"
            ),
            "schema_version": 1,
            "supported_attempt_kinds": ["official", "reproduction"],
        },
        "attempt-control-record": {
            "allocation_receipt_identity": SHA,
            "attempt_control_record_identity": SHA,
            "attempt_identity": SHA,
            "attempt_kind": "official",
            "external_input_snapshot_identities": [SHA],
            "launch_authority_snapshot_identity": SHA,
            "ordinal": 1,
            "predecessor_control_record_identity": {"status": "absent"},
            "profile_identity": SHA,
            "readiness_identity": SHA,
            "readiness_seal_commit": GIT,
            "remote_head_commit": GIT,
            "schema_version": 1,
            "sequence": 1,
            "source_commit": GIT,
            "state": {"control_state": "STARTED"},
        },
        "attempt-identity-material": {
            **common_attempt,
            "allocation_authority_identity": SHA,
            "allocator_contract_identity": SHA,
            "attempt_identity_schema_identifier": "attempt-identity-material-v1",
            "output_policy_revision": "readiness-v1-output-policy",
        },
        "execution-control-manifest": {
            "allocation_receipt_identity": SHA,
            "attempt_identity": SHA,
            "attempt_kind": "official",
            "control_record_identities": [SHA],
            "execution_control_manifest_identity": SHA,
            "external_input_snapshot_identities": [SHA],
            "launch_authority_snapshot_identity": SHA,
            "ordinal": 1,
            "profile_identity": SHA,
            "readiness_identity": SHA,
            "readiness_seal_commit": GIT,
            "remote_head_commit": GIT,
            "schema_version": 1,
            "source_commit": GIT,
            "terminal": {"final_control_disposition": "INCOMPLETE"},
        },
        "outcome-authorization": {
            "attempt_identity": SHA,
            "dataset_identity": SHA,
            "external_input_snapshot_identities": [SHA],
            "frozen_ranking_artifact_identity": SHA,
            "launch_authority_snapshot_identity": SHA,
            "non_replayable": True,
            "outcome_authorization_identity": SHA,
            "outcome_blind_provenance_identity": SHA,
            "outcome_source_identity": SHA,
            "profile_identity": SHA,
            "ranking_contract_identity": SHA,
            "readiness_identity": SHA,
            "readiness_seal_commit": GIT,
            "replay_identity": SHA,
            "schema_version": 1,
            "source_commit": GIT,
        },
        "output-namespace-identity-material": {
            "allocation_authority_identity": SHA,
            "allocator_contract_identity": SHA,
            "attempt_kind": "official",
            "experiment_identifier": "synthetic-experiment-001",
            "output_namespace_schema_revision": (
                "output-namespace-identity-material-v1"
            ),
            "output_policy_revision": "readiness-v1-output-policy",
            "permanent_ordinal": 1,
        },
        "profile-contract": {
            "contract_identifier": "authorization_contract_identity",
            "contract_identity": SHA,
            "contract_kind": "outcome-authorization",
            "evaluation_artifact_identifier": "evaluation-report",
            "outcome_access": "authorization_required",
        },
        "readiness-failure-receipt": {
            "approved_branch_ref": "refs/heads/research/post-v1",
            "candidate_source_commit": {"status": "absent"},
            "check_statuses": _check_statuses(),
            "current_readiness_disposition": "not_applicable",
            "experiment_identifier": "synthetic-experiment-001",
            "failed_invariant_identifier": "git_authority",
            "failure_receipt_identity": SHA,
            "launch_authority_snapshot_identity": {"status": "absent"},
            "readiness_identity": {"status": "absent"},
            "receipt_class": "READINESS_REJECTED",
            "repository_authority_identifier": "research-post-v1",
            "schema_version": 1,
            "scientific_execution_started": False,
            "scientific_outcome_evidence": "absent",
        },
    }


def _validate(kind: str, value: dict[str, Any]) -> None:
    validate_json_schema_instance(value, _schemas()[kind], schema_registry={})


def _walk_schema(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if isinstance(value, dict):
        result.append(value)
        for child in value.values():
            result.extend(_walk_schema(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_walk_schema(child))
    return result


def test_schema_policy_generations_are_exact_and_final_union_is_sorted() -> None:
    assert len(PHASE2_SCHEMA_POLICY) == 6
    assert len(PHASE3A_SCHEMA_POLICY) == 10
    assert len(PHASE3B_SCHEMA_POLICY) == 20
    assert len(READINESS_V1_1_SCHEMA_POLICY) == 29
    assert set(READINESS_V1_1_SCHEMA_POLICY) == set(PHASE3B_SCHEMA_POLICY) | NEW_KINDS
    assert set(PHASE2_SCHEMA_POLICY) < set(PHASE3A_SCHEMA_POLICY)
    assert set(PHASE3A_SCHEMA_POLICY) < set(PHASE3B_SCHEMA_POLICY)
    assert set(PHASE3B_SCHEMA_POLICY) < set(READINESS_V1_1_SCHEMA_POLICY)
    assert set(PHASE3A_SCHEMA_POLICY) - set(PHASE2_SCHEMA_POLICY) == {
        "adapter-declaration",
        "adapter-registry",
        "offline-artifact-manifest",
        "runtime-contract",
    }
    assert set(PHASE3B_SCHEMA_POLICY) - set(PHASE3A_SCHEMA_POLICY) == {
        "artifact-declaration-evidence",
        "dataset-validation-evidence",
        "evidence-preparation",
        "evidence-preparation-policy",
        "immutable-input-snapshot",
        "outcome-blind-projection-evidence",
        "population-accounting-evidence",
        "profile-conformance-evidence",
        "readiness-test-evidence",
        "replay-evidence",
    }
    assert set(READINESS_V1_1_SCHEMA_POLICY) - set(PHASE3B_SCHEMA_POLICY) == NEW_KINDS
    assert READINESS_V1_1_SCHEMA_KIND_ORDER == FINAL_KINDS
    assert tuple(READINESS_V1_1_SCHEMA_POLICY) == FINAL_KINDS
    assert tuple(READINESS_V1_1_SCHEMA_DOCUMENT_POLICY) == FINAL_KINDS


def test_final_schema_paths_identifiers_and_digests_are_exact() -> None:
    assert set(READINESS_V1_1_SCHEMA_DOCUMENT_POLICY) == set(
        READINESS_V1_1_SCHEMA_POLICY
    )
    for kind, (_, path_text) in READINESS_V1_1_SCHEMA_POLICY.items():
        path = Path(path_text)
        assert path.is_file()
        raw = path.read_bytes()
        schema = parse_json(raw)
        expected_id, expected_digest = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind]
        assert schema["$id"] == expected_id
        assert hashlib.sha256(raw).hexdigest() == expected_digest


def test_new_schemas_are_draft_2020_12_closed_and_fully_required() -> None:
    for schema in _schemas().values():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        for node in _walk_schema(schema):
            if node.get("type") == "object" and "properties" in node:
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])


@pytest.mark.parametrize("kind", sorted(NEW_KINDS))
def test_minimal_representative_objects_validate(kind: str) -> None:
    _validate(kind, _representatives()[kind])


def test_all_six_closed_profile_contract_kinds_validate() -> None:
    contracts = [
        _representatives()["profile-contract"],
        {
            "contract_identifier": "evaluation_dependency_graph_identity",
            "contract_identity": SHA,
            "contract_kind": "evaluation-dependency-graph",
            "edges": [
                ["authorization", "evaluation"],
                ["outcome_source", "evaluation"],
                ["ranking", "evaluation"],
            ],
            "evaluation_artifact_identifier": "evaluation-report",
            "ranking_artifact_identifier": "ranking-artifact",
        },
        {
            "contract_identifier": "freeze_contract_identity",
            "contract_identity": SHA,
            "contract_kind": "ranking-freeze",
            "ranking_artifact_identifier": "ranking-artifact",
            "ranking_frozen_before_outcome": True,
        },
        {
            "contract_identifier": "outcome_blind_ranking_source_identity",
            "contract_identity": SHA,
            "contract_kind": "outcome-blind-ranking-source",
            "outcome_blind": True,
            "ranking_artifact_identifier": "ranking-artifact",
        },
        {
            "contract_identifier": "outcome_source_identity",
            "contract_identity": SHA,
            "contract_kind": "outcome-source",
            "external_input_identifier": "combined-dataset",
            "outcome_source_role": "declared_external_input",
        },
        {
            "artifact_identifier": "ranking-artifact",
            "contract_identifier": "ranking_artifact_identifier",
            "contract_identity": SHA,
            "contract_kind": "ranking-artifact-reference",
        },
    ]
    for contract in contracts:
        _validate("profile-contract", contract)


@pytest.mark.parametrize("kind", sorted(NEW_KINDS))
def test_new_schemas_reject_unknown_missing_and_null(kind: str) -> None:
    valid = _representatives()[kind]
    unknown = copy.deepcopy(valid)
    unknown["operator_note"] = "prohibited"
    with pytest.raises(CanonicalControlError):
        _validate(kind, unknown)

    missing = copy.deepcopy(valid)
    missing.pop(next(iter(missing)))
    with pytest.raises(CanonicalControlError):
        _validate(kind, missing)

    null_value = copy.deepcopy(valid)
    null_value[next(iter(null_value))] = None
    with pytest.raises(CanonicalControlError):
        _validate(kind, null_value)

    wrong_type = copy.deepcopy(valid)
    typed_field = "contract_identity" if kind == "profile-contract" else "schema_version"
    wrong_type[typed_field] = 1 if typed_field == "contract_identity" else "1"
    with pytest.raises(CanonicalControlError):
        _validate(kind, wrong_type)


@pytest.mark.parametrize(
    ("kind", "field", "invalid"),
    (
        ("attempt-allocation", "attempt_kind", "development"),
        ("attempt-authority-contract", "atomicity_semantics", "best_effort"),
        ("attempt-control-record", "state", {"control_state": "COMPLETE"}),
        ("attempt-identity-material", "attempt_kind", "legacy_reproduction"),
        (
            "execution-control-manifest",
            "terminal",
            {"final_control_disposition": "COMPLETE"},
        ),
        ("outcome-authorization", "non_replayable", False),
        (
            "output-namespace-identity-material",
            "attempt_kind",
            "development",
        ),
        ("profile-contract", "contract_kind", "authorization-bypass"),
        ("readiness-failure-receipt", "receipt_class", "EXECUTION_READY"),
    ),
)
def test_new_schemas_reject_invalid_enum_or_const(
    kind: str, field: str, invalid: object
) -> None:
    material = copy.deepcopy(_representatives()[kind])
    material[field] = invalid
    with pytest.raises(CanonicalControlError):
        _validate(kind, material)


def test_identity_bearing_arrays_reject_duplicates_or_noncanonical_order() -> None:
    authority = copy.deepcopy(_representatives()["attempt-authority-contract"])
    authority["supported_attempt_kinds"] = ["reproduction", "official"]
    with pytest.raises(CanonicalControlError):
        _validate("attempt-authority-contract", authority)
    authority["supported_attempt_kinds"] = ["official", "official"]
    with pytest.raises(CanonicalControlError):
        _validate("attempt-authority-contract", authority)

    allocation = copy.deepcopy(_representatives()["attempt-allocation"])
    allocation["external_input_snapshot_identities"] = [SHA, SHA]
    with pytest.raises(CanonicalControlError):
        _validate("attempt-allocation", allocation)

    failure = copy.deepcopy(_representatives()["readiness-failure-receipt"])
    failure["check_statuses"] = failure["check_statuses"] * 2
    with pytest.raises(CanonicalControlError):
        _validate("readiness-failure-receipt", failure)


def test_attempt_identity_dependencies_are_cycle_free() -> None:
    schemas = _schemas()
    namespace_properties = set(
        schemas["output-namespace-identity-material"]["properties"]
    )

    dependencies = {
        "output_namespace_identity": {
            "allocation_authority_identity",
            "allocator_contract_identity",
            "experiment_identifier",
            "attempt_kind",
            "output_namespace_schema_revision",
            "output_policy_revision",
            "permanent_ordinal",
        },
        "attempt_identity": {
            "allocation_authority_identity",
            "allocator_contract_identity",
            "attempt_kind",
            "experiment_identifier",
            "external_input_snapshot_identities",
            "launch_authority_snapshot_identity",
            "ordinal",
            "output_namespace_identity",
            "output_policy_revision",
            "readiness_identity",
            "readiness_seal_commit",
            "remote_head_commit",
            "source_commit",
        },
        "allocation_receipt_identity": {
            "allocator_contract_identity",
            "attempt_identity",
            "attempt_kind",
            "experiment_identifier",
            "external_input_snapshot_identities",
            "launch_authority_snapshot_identity",
            "ordinal",
            "output_namespace_identity",
            "readiness_identity",
            "readiness_seal_commit",
            "remote_head_commit",
            "source_commit",
        },
    }
    assert namespace_properties == dependencies["output_namespace_identity"]
    assert "attempt_identity" not in dependencies["output_namespace_identity"]
    order = [
        "output_namespace_identity",
        "attempt_identity",
        "allocation_receipt_identity",
    ]
    positions = {identifier: index for index, identifier in enumerate(order)}
    for identifier, inputs in dependencies.items():
        assert all(
            positions[input_identity] < positions[identifier]
            for input_identity in inputs
            if input_identity in positions
        )


def _control_with_state(state: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(_representatives()["attempt-control-record"])
    value["state"] = state
    return value


def _manifest_with_terminal(terminal: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(_representatives()["execution-control-manifest"])
    value["terminal"] = terminal
    return value


def _failed_state(
    *, recovery: bool = False, evidence: dict[str, Any] | None = None
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "control_state": "FAILED",
        "failure_control_evidence": evidence or _failure_evidence(),
        "no_live_owner_evidence": "absent",
        "recovery_mode": "not_recovery_generated",
    }
    if recovery:
        state["no_live_owner_evidence"] = {
            "allocation_authority_identity": SHA,
            "no_live_owner_established": True,
            "recovery_component_identity": SHA,
            "recovery_operation": "atomic_compare_no_live_owner_and_append_failed",
            "recovery_policy_identity": SHA,
        }
        state["recovery_mode"] = "recovery_no_live_owner_established"
    return state


def _failed_terminal(
    *, recovery: bool = False, evidence: dict[str, Any] | None = None
) -> dict[str, Any]:
    terminal = _failed_state(recovery=recovery, evidence=evidence)
    terminal["final_control_disposition"] = terminal.pop("control_state")
    return terminal


@pytest.mark.parametrize(
    "state",
    (
        {
            "control_state": "VALID",
            "experiment_audit_manifest_identity": SHA,
            "experiment_audit_manifest_sha256": SHA,
        },
        {
            "control_state": "INVALID",
            "governing_invalidity_evidence_identity": SHA,
            "governing_invalidity_evidence_sha256": SHA,
            "required_scientific_manifest_bindings": [],
        },
        _failed_state(),
    ),
)
def test_terminal_control_states_require_distinct_evidence(state: dict[str, Any]) -> None:
    _validate("attempt-control-record", _control_with_state(state))


@pytest.mark.parametrize(
    "state",
    (
        {"control_state": "STARTED", "experiment_audit_manifest_identity": SHA},
        {"control_state": "VALID"},
        {"control_state": "INVALID", "required_scientific_manifest_bindings": []},
        {
            "control_state": "FAILED",
            "experiment_audit_manifest_identity": SHA,
            "experiment_audit_manifest_sha256": SHA,
        },
        {
            "control_state": "VALID",
            "experiment_audit_manifest_identity": SHA,
            "experiment_audit_manifest_sha256": SHA,
            "governing_invalidity_evidence_identity": SHA,
        },
    ),
)
def test_control_states_reject_missing_or_cross_state_evidence(
    state: dict[str, Any],
) -> None:
    with pytest.raises(CanonicalControlError):
        _validate("attempt-control-record", _control_with_state(state))


@pytest.mark.parametrize(
    "terminal",
    (
        {
            "final_control_disposition": "VALID",
            "experiment_audit_manifest_identity": SHA,
            "experiment_audit_manifest_sha256": SHA,
        },
        {
            "final_control_disposition": "INVALID",
            "governing_invalidity_evidence_identity": SHA,
            "governing_invalidity_evidence_sha256": SHA,
            "required_scientific_manifest_bindings": [],
        },
        _failed_terminal(recovery=True),
    ),
)
def test_terminal_manifests_require_distinct_evidence(
    terminal: dict[str, Any],
) -> None:
    _validate("execution-control-manifest", _manifest_with_terminal(terminal))


@pytest.mark.parametrize(
    "terminal",
    (
        {"final_control_disposition": "VALID"},
        {
            "final_control_disposition": "INVALID",
            "required_scientific_manifest_bindings": [],
        },
        {
            "final_control_disposition": "FAILED",
            "governing_invalidity_evidence_identity": SHA,
            "governing_invalidity_evidence_sha256": SHA,
        },
        {
            "final_control_disposition": "INCOMPLETE",
            "failure_control_evidence_identity": SHA,
        },
    ),
)
def test_terminal_manifests_reject_missing_or_cross_state_evidence(
    terminal: dict[str, Any],
) -> None:
    with pytest.raises(CanonicalControlError):
        _validate("execution-control-manifest", _manifest_with_terminal(terminal))


@pytest.mark.parametrize(
    ("failure_class", "fact"),
    (
        ("ambiguous_state", "conflicting_authoritative_control_records"),
        ("ambiguous_state", "indeterminate_authoritative_control_state"),
        ("infrastructure_failure", "shared_control_storage_failure"),
        ("infrastructure_failure", "execution_infrastructure_failure"),
        ("interruption", "governed_owner_terminated"),
        ("interruption", "governed_owner_unavailable"),
        ("validity_not_established", "premature_outcome_access"),
        (
            "validity_not_established",
            "terminal_scientific_authority_not_established",
        ),
    ),
)
def test_failed_classes_accept_exact_class_specific_facts(
    failure_class: str, fact: str
) -> None:
    evidence = _failure_evidence(failure_class, fact)
    recovery = False
    if fact == "conflicting_authoritative_control_records":
        evidence = _conflicting_failure_evidence()
        recovery = True
    _validate(
        "attempt-control-record",
        _control_with_state(_failed_state(recovery=recovery, evidence=evidence)),
    )
    _validate(
        "execution-control-manifest",
        _manifest_with_terminal(
            _failed_terminal(recovery=recovery, evidence=evidence)
        ),
    )


@pytest.mark.parametrize(
    ("failure_class", "fact"),
    (
        ("ambiguous_state", "shared_control_storage_failure"),
        ("infrastructure_failure", "governed_owner_terminated"),
        ("interruption", "premature_outcome_access"),
        ("validity_not_established", "indeterminate_authoritative_control_state"),
    ),
)
def test_failed_classes_reject_cross_class_facts(
    failure_class: str, fact: str
) -> None:
    evidence = _failure_evidence(failure_class, fact)
    with pytest.raises(CanonicalControlError):
        _validate(
            "attempt-control-record",
            _control_with_state(_failed_state(evidence=evidence)),
        )


@pytest.mark.parametrize(
    "boundary",
    (
        "post_allocation_pre_start",
        "post_start_pre_ranking_freeze",
        "post_ranking_freeze_pre_authorization",
        "post_authorization_pre_terminal",
        "terminalization",
    ),
)
def test_failed_evidence_accepts_exact_failure_boundaries(boundary: str) -> None:
    evidence = _failure_evidence()
    evidence["failure_boundary"] = boundary
    _validate("attempt-control-record", _control_with_state(_failed_state(evidence=evidence)))


def test_last_durable_state_domain_is_structural_and_reconstruction_is_later() -> None:
    for state in ("ALLOCATED", "STARTED"):
        evidence = _failure_evidence()
        evidence["last_durable_control_state"] = state
        _validate(
            "attempt-control-record",
            _control_with_state(_failed_state(evidence=evidence)),
        )

    invalid = _failure_evidence()
    invalid["last_durable_control_state"] = "VALID"
    with pytest.raises(CanonicalControlError):
        _validate(
            "attempt-control-record",
            _control_with_state(_failed_state(evidence=invalid)),
        )


@pytest.mark.parametrize(
    "predecessor",
    ({"status": "absent"}, {"identity": SHA, "status": "known"}),
)
def test_predecessor_closed_branches_validate(predecessor: dict[str, str]) -> None:
    record = copy.deepcopy(_representatives()["attempt-control-record"])
    record["predecessor_control_record_identity"] = predecessor
    _validate("attempt-control-record", record)


@pytest.mark.parametrize(
    "predecessor",
    (
        None,
        SHA,
        {},
        {"identity": SHA},
        {"status": "none"},
        {"identity": SHA, "status": "absent"},
        {"status": "absent", "extra": "prohibited"},
        {"identity": SHA, "status": "known", "extra": "prohibited"},
    ),
)
def test_predecessor_alternate_encodings_reject(predecessor: object) -> None:
    record = copy.deepcopy(_representatives()["attempt-control-record"])
    record["predecessor_control_record_identity"] = predecessor
    with pytest.raises(CanonicalControlError):
        _validate("attempt-control-record", record)


@pytest.mark.parametrize(
    ("slot_fact", "validated_records"),
    (
        ("malformed_only", []),
        (
            "duplicate_valid_record",
            [
                {
                    "control_record_identity": SHA,
                    "declared_control_sequence": 1,
                    "predecessor_control_record_identity": {"status": "absent"},
                }
            ],
        ),
        (
            "multiple_valid_records",
            [
                {
                    "control_record_identity": "1" * 64,
                    "declared_control_sequence": 1,
                    "predecessor_control_record_identity": {"status": "absent"},
                },
                {
                    "control_record_identity": "2" * 64,
                    "declared_control_sequence": 1,
                    "predecessor_control_record_identity": {"status": "absent"},
                },
            ],
        ),
        (
            "valid_and_malformed",
            [
                {
                    "control_record_identity": SHA,
                    "declared_control_sequence": 1,
                    "predecessor_control_record_identity": {"status": "absent"},
                }
            ],
        ),
    ),
)
def test_conflicting_history_accepts_exact_finite_slot_facts(
    slot_fact: str, validated_records: list[dict[str, Any]]
) -> None:
    evidence = _conflicting_failure_evidence(
        slot_fact=slot_fact, validated_records=validated_records
    )
    _validate(
        "attempt-control-record",
        _control_with_state(_failed_state(recovery=True, evidence=evidence)),
    )


def test_failed_recovery_modes_are_closed_and_consistent() -> None:
    _validate("attempt-control-record", _control_with_state(_failed_state()))
    _validate("attempt-control-record", _control_with_state(_failed_state(recovery=True)))

    mismatch = _failed_state()
    mismatch["recovery_mode"] = "recovery_no_live_owner_established"
    with pytest.raises(CanonicalControlError):
        _validate("attempt-control-record", _control_with_state(mismatch))


def test_conflicting_history_failed_requires_recovery_in_both_terminal_schemas() -> None:
    evidence = _conflicting_failure_evidence()
    record = _control_with_state(_failed_state(recovery=True, evidence=evidence))
    manifest = _manifest_with_terminal(
        _failed_terminal(recovery=True, evidence=evidence)
    )
    _validate("attempt-control-record", record)
    _validate("execution-control-manifest", manifest)

    non_recovery_record = _control_with_state(_failed_state(evidence=evidence))
    non_recovery_manifest = _manifest_with_terminal(_failed_terminal(evidence=evidence))
    with pytest.raises(CanonicalControlError):
        _validate("attempt-control-record", non_recovery_record)
    with pytest.raises(CanonicalControlError):
        _validate("execution-control-manifest", non_recovery_manifest)


def test_conflicting_history_recovery_requires_evidence_and_absent_predecessor() -> None:
    evidence = _conflicting_failure_evidence()

    record_without_evidence = _control_with_state(
        _failed_state(recovery=True, evidence=evidence)
    )
    record_without_evidence["state"]["no_live_owner_evidence"] = "absent"
    manifest_without_evidence = _manifest_with_terminal(
        _failed_terminal(recovery=True, evidence=evidence)
    )
    manifest_without_evidence["terminal"]["no_live_owner_evidence"] = "absent"
    with pytest.raises(CanonicalControlError):
        _validate("attempt-control-record", record_without_evidence)
    with pytest.raises(CanonicalControlError):
        _validate("execution-control-manifest", manifest_without_evidence)

    known_predecessor = _control_with_state(
        _failed_state(recovery=True, evidence=evidence)
    )
    known_predecessor["predecessor_control_record_identity"] = {
        "identity": SHA,
        "status": "known",
    }
    with pytest.raises(CanonicalControlError):
        _validate("attempt-control-record", known_predecessor)


def test_conflicting_failure_fact_and_history_branch_cannot_be_mixed() -> None:
    conflict_fact_coherent_history = _conflicting_failure_evidence()
    conflict_fact_coherent_history["control_history"] = _coherent_history()
    non_conflict_fact_conflicting_history = _failure_evidence(
        "ambiguous_state", "indeterminate_authoritative_control_state"
    )
    non_conflict_fact_conflicting_history["control_history"] = (
        _conflicting_failure_evidence()["control_history"]
    )

    for evidence, recovery in (
        (conflict_fact_coherent_history, True),
        (non_conflict_fact_conflicting_history, False),
    ):
        with pytest.raises(CanonicalControlError):
            _validate(
                "attempt-control-record",
                _control_with_state(_failed_state(recovery=recovery, evidence=evidence)),
            )
        with pytest.raises(CanonicalControlError):
            _validate(
                "execution-control-manifest",
                _manifest_with_terminal(
                    _failed_terminal(recovery=recovery, evidence=evidence)
                ),
            )


@pytest.mark.parametrize(
    "field",
    (
        "diagnostic",
        "exception",
        "outcome",
        "winner",
        "label",
        "scientific_result",
        "interpretation",
        "local_path",
        "malformed_bytes_sha256",
    ),
)
def test_failed_evidence_rejects_payload_and_outcome_channels(field: str) -> None:
    state = _failed_state()
    state["failure_control_evidence"][field] = "prohibited"
    with pytest.raises(CanonicalControlError):
        _validate("attempt-control-record", _control_with_state(state))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("failed_invariant_identifier", "winner_square_17"),
        ("failed_invariant_identifier", "A" * 4096),
        ("failed_invariant_identifier", "b3V0Y29tZT13aW5uZXI="),
        ("check_statuses", [{"check_identifier": "winner_17", "status": "failed"}]),
        ("check_statuses", [{"check_identifier": "x" * 4096, "status": "failed"}]),
        (
            "check_statuses",
            [{"check_identifier": "b3V0Y29tZV9sYWJlbA", "status": "failed"}],
        ),
    ),
)
def test_failure_receipt_rejects_caller_defined_payload_identifiers(
    field: str,
    value: object,
) -> None:
    receipt = copy.deepcopy(_representatives()["readiness-failure-receipt"])
    receipt[field] = value
    with pytest.raises(CanonicalControlError):
        _validate("readiness-failure-receipt", receipt)


@pytest.mark.parametrize(
    ("receipt_class", "disposition"),
    (
        ("READINESS_REJECTED", "not_applicable"),
        *(("CURRENT_READINESS", value) for value in NON_READY_DISPOSITIONS),
        *(("LAUNCH_REJECTED", value) for value in NON_READY_DISPOSITIONS),
        ("LAUNCH_REJECTED", "EXECUTION_READY"),
    ),
)
def test_failure_receipt_accepts_exact_class_disposition_combinations(
    receipt_class: str, disposition: str
) -> None:
    receipt = copy.deepcopy(_representatives()["readiness-failure-receipt"])
    receipt["receipt_class"] = receipt_class
    receipt["current_readiness_disposition"] = disposition
    receipt["check_statuses"] = _check_statuses(receipt_class=receipt_class)
    _validate("readiness-failure-receipt", receipt)


@pytest.mark.parametrize(
    ("failed_invariant", "smoke_status"),
    (
        pytest.param("git_authority", "not_evaluated", id="early-launch-failure"),
        pytest.param("second_fetch", "not_applicable", id="validated-empty-selectors"),
        pytest.param("output_namespace", "not_evaluated", id="smoke-not-reached"),
        pytest.param("launch_smoke", "failed", id="smoke-first-failure"),
        pytest.param("second_fetch", "passed", id="smoke-passed-later-failure"),
    ),
)
def test_launch_receipt_structurally_supports_progressive_smoke_states(
    failed_invariant: str, smoke_status: str
) -> None:
    receipt = copy.deepcopy(_representatives()["readiness-failure-receipt"])
    receipt["receipt_class"] = "LAUNCH_REJECTED"
    receipt["current_readiness_disposition"] = "EXECUTION_READY"
    receipt["failed_invariant_identifier"] = failed_invariant
    receipt["check_statuses"] = _check_statuses(
        failed_invariant, receipt_class="LAUNCH_REJECTED"
    )
    receipt["check_statuses"][INVARIANT_IDENTIFIERS.index("launch_smoke")][
        "status"
    ] = smoke_status
    _validate("readiness-failure-receipt", receipt)


@pytest.mark.parametrize(
    ("receipt_class", "disposition"),
    (
        ("READINESS_REJECTED", "READINESS_STALE"),
        ("READINESS_REJECTED", "EXECUTION_READY"),
        ("CURRENT_READINESS", "not_applicable"),
        ("CURRENT_READINESS", "EXECUTION_READY"),
        ("LAUNCH_REJECTED", "not_applicable"),
        ("CANONICAL_RECEIPT_UNAVAILABLE", "not_applicable"),
    ),
)
def test_failure_receipt_rejects_cross_class_dispositions(
    receipt_class: str, disposition: str
) -> None:
    receipt = copy.deepcopy(_representatives()["readiness-failure-receipt"])
    receipt["receipt_class"] = receipt_class
    receipt["current_readiness_disposition"] = disposition
    with pytest.raises(CanonicalControlError):
        _validate("readiness-failure-receipt", receipt)


def test_failure_receipt_vector_has_exact_frozen_identifiers_and_order() -> None:
    receipt = copy.deepcopy(_representatives()["readiness-failure-receipt"])
    assert [entry["check_identifier"] for entry in receipt["check_statuses"]] == list(
        INVARIANT_IDENTIFIERS
    )
    _validate("readiness-failure-receipt", receipt)

    for invalid_identifier in (
        "internal_control",
        "caller_check",
        "x" * 4096,
        "b3V0Y29tZT13aW5uZXI=",
        "exception_timeout",
        "winner_square_17",
    ):
        invalid = copy.deepcopy(receipt)
        invalid["check_statuses"][0]["check_identifier"] = invalid_identifier
        with pytest.raises(CanonicalControlError):
            _validate("readiness-failure-receipt", invalid)


def test_failure_receipt_requires_exactly_one_structural_failed_status() -> None:
    receipt = copy.deepcopy(_representatives()["readiness-failure-receipt"])
    no_failure = copy.deepcopy(receipt)
    no_failure["check_statuses"][2]["status"] = "not_evaluated"
    with pytest.raises(CanonicalControlError):
        _validate("readiness-failure-receipt", no_failure)

    two_failures = copy.deepcopy(receipt)
    two_failures["check_statuses"][0]["status"] = "failed"
    with pytest.raises(CanonicalControlError):
        _validate("readiness-failure-receipt", two_failures)

    for status in ("passed", "not_evaluated", "not_applicable"):
        valid = copy.deepcopy(receipt)
        valid["check_statuses"][0]["status"] = status
        _validate("readiness-failure-receipt", valid)


@pytest.mark.parametrize(
    "kind",
    (
        "attempt-allocation",
        "attempt-control-record",
        "attempt-identity-material",
        "execution-control-manifest",
        "outcome-authorization",
    ),
)
def test_zero_external_inputs_are_canonical_and_valid(kind: str) -> None:
    value = copy.deepcopy(_representatives()[kind])
    value["external_input_snapshot_identities"] = []
    _validate(kind, value)


@pytest.mark.parametrize(
    "supported",
    (["official"], ["official", "reproduction"], ["reproduction"]),
)
def test_attempt_authority_accepts_every_reusable_supported_kind_set(
    supported: list[str],
) -> None:
    authority = copy.deepcopy(_representatives()["attempt-authority-contract"])
    authority["supported_attempt_kinds"] = supported
    _validate("attempt-authority-contract", authority)


@pytest.mark.parametrize(
    "supported",
    ([], ["official", "official"], ["unknown"], ["reproduction", "official"],
     ["official", "reproduction", "future"]),
)
def test_attempt_authority_rejects_invalid_supported_kind_sets(
    supported: list[str],
) -> None:
    authority = copy.deepcopy(_representatives()["attempt-authority-contract"])
    authority["supported_attempt_kinds"] = supported
    with pytest.raises(CanonicalControlError):
        _validate("attempt-authority-contract", authority)


def test_allocator_contract_identity_is_distinct_and_required_everywhere() -> None:
    authority = copy.deepcopy(_representatives()["attempt-authority-contract"])
    assert authority["allocator_contract_identity"] == SHA
    assert authority["allocation_authority_identity"] == SHA
    assert "attempt_authority_contract_identity" not in authority
    authority["allocation_authority_identity"] = "2" * 64
    _validate("attempt-authority-contract", authority)

    missing = copy.deepcopy(authority)
    del missing["allocator_contract_identity"]
    with pytest.raises(CanonicalControlError):
        _validate("attempt-authority-contract", missing)

    provisional = copy.deepcopy(authority)
    provisional["attempt_authority_contract_identity"] = provisional.pop(
        "allocator_contract_identity"
    )
    with pytest.raises(CanonicalControlError):
        _validate("attempt-authority-contract", provisional)

    for kind in (
        "attempt-allocation",
        "attempt-authority-contract",
        "attempt-identity-material",
        "output-namespace-identity-material",
    ):
        properties = _schemas()[kind]["properties"]
        assert "allocator_contract_identity" in properties
        assert "allocation_authority_identity" in properties
        assert "attempt_authority_contract_identity" not in properties


@pytest.mark.parametrize(
    "identifier",
    ("a", "authority-1", "authority.v1", "authority_v1", "a1-b2.c3_d4"),
)
def test_allocation_authority_identifier_accepts_canonical_grammar(
    identifier: str,
) -> None:
    authority = copy.deepcopy(_representatives()["attempt-authority-contract"])
    authority["allocation_authority_identity_material"][
        "allocation_authority_identifier"
    ] = identifier
    _validate("attempt-authority-contract", authority)


@pytest.mark.parametrize(
    "identifier",
    (
        "",
        "Authority",
        "authority value",
        "authority/value",
        "authority\\value",
        "-authority",
        "authority-",
        "authority--value",
        "authority%2fvalue",
        "a" * 65,
        "authority@value",
    ),
)
def test_allocation_authority_identifier_rejects_noncanonical_grammar(
    identifier: str,
) -> None:
    authority = copy.deepcopy(_representatives()["attempt-authority-contract"])
    authority["allocation_authority_identity_material"][
        "allocation_authority_identifier"
    ] = identifier
    with pytest.raises(CanonicalControlError):
        _validate("attempt-authority-contract", authority)


def test_characterization_cannot_gain_outcome_authority() -> None:
    declarations = {
        "authorization_contract_identity": {
            "contract_identifier": "authorization_contract_identity",
            "contract_identity": SHA,
            "contract_kind": "outcome-authorization",
            "evaluation_artifact_identifier": "evaluation-report",
            "outcome_access": "authorization_required",
        }
    }
    profile_name = "outcome_blind_characterization_v1"
    outcome_policy = "prohibited_and_not_performed"
    profile = {
        "declarations": declarations,
        "outcome_policy": outcome_policy,
        "profile_identity": reconstruct_profile_binding_identity(
            profile_name=profile_name,
            outcome_policy=outcome_policy,
            declarations=declarations,
        ),
        "profile_name": profile_name,
    }
    with pytest.raises(CanonicalControlError, match="PROFILE_POLICY_MISMATCH"):
        validate_profile_contract(profile)


def test_final_registry_has_unique_kinds_policy_identifiers_ids_and_paths() -> None:
    kinds = list(READINESS_V1_1_SCHEMA_POLICY)
    policy_identifiers = [READINESS_V1_1_SCHEMA_POLICY[kind][0] for kind in kinds]
    identifiers = [
        READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind][0] for kind in kinds
    ]
    paths = [READINESS_V1_1_SCHEMA_POLICY[kind][1] for kind in kinds]
    assert len(kinds) == len(set(kinds))
    assert len(policy_identifiers) == len(set(policy_identifiers))
    assert len(identifiers) == len(set(identifiers))
    assert len(paths) == len(set(paths))


def test_prospective_phase3b_v2_schemas_accept_only_exact_zero_branches() -> None:
    schemas = {
        name: parse_json((SCHEMA_ROOT / f"{name}-v2.schema.json").read_bytes())
        for name in (
            "replay-evidence",
            "population-accounting-evidence",
            "evidence-preparation",
        )
    }
    replay = {
        "candidate_order": [],
        "decision_selection_identity": SHA,
        "ordered_decision_identities": [],
        "ordered_replay_unit_identities": [],
        "ordered_source_unit_identities": [],
        "projection_identity": SHA,
        "replay_evidence_identity": SHA,
        "replay_identity": SHA,
        "replay_preparer_component_identity": SHA,
        "schema_version": 2,
        "selector_component_identity": SHA,
    }
    population = {
        "dispositions": [],
        "excluded_count": 0,
        "included_count": 0,
        "permitted_exclusion_reasons": [],
        "population_accounting_evidence_identity": SHA,
        "schema_version": 2,
        "source_count": 0,
    }
    aggregate = {
        "adapter_identity": SHA,
        "artifact_evidence_identity": SHA,
        "capability_policy_identity": SHA,
        "dataset_evidence_identities": [],
        "dependency_environment_identity": SHA,
        "evidence_preparation_identity": SHA,
        "input_snapshot_identities": [],
        "population_evidence_identity": SHA,
        "profile_evidence_identity": SHA,
        "projection_evidence_identities": [],
        "readiness_test_evidence_identity": SHA,
        "replay_evidence_identity": SHA,
        "runtime_contract_identity": SHA,
        "schema_version": 2,
        "semantic_component_identities": [str(index) * 64 for index in range(1, 5)],
        "source_commit": GIT,
        "worker_evidence_identities": [str(index) * 64 for index in range(5, 9)],
    }
    for schema, value in (
        (schemas["replay-evidence"], replay),
        (schemas["population-accounting-evidence"], population),
        (schemas["evidence-preparation"], aggregate),
    ):
        validate_json_schema_instance(value, schema, schema_registry={})

    invalid_population = copy.deepcopy(population)
    invalid_population["source_count"] = 1
    with pytest.raises(CanonicalControlError):
        validate_json_schema_instance(
            invalid_population,
            schemas["population-accounting-evidence"],
            schema_registry={},
        )
    invalid_aggregate = copy.deepcopy(aggregate)
    invalid_aggregate["worker_evidence_identities"].append("9" * 64)
    with pytest.raises(CanonicalControlError):
        validate_json_schema_instance(
            invalid_aggregate,
            schemas["evidence-preparation"],
            schema_registry={},
        )


def test_shared_semantic_core_introduces_no_operational_authority() -> None:
    production = Path("src/orev3/execution")
    assert (production / "attempts.py").is_file()
    assert (production / "control_storage.py").is_file()
    assert not (production / "orchestrator.py").exists()
    assert not (production / "outcome_gate.py").exists()
    assert not Path(
        "config/research/readiness/attempt-authority-contract-v1.json"
    ).exists()
    for forbidden in (
        "build_attempt_allocation",
        "build_attempt_control_record",
        "build_execution_control_manifest",
        "build_outcome_authorization",
        "build_readiness_failure_receipt",
    ):
        assert not hasattr(__import__("orev3.execution.readiness_record", fromlist=[forbidden]), forbidden)
