from __future__ import annotations

import copy
import importlib.util
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
)
from orev3.execution.runtime import PHASE3B_WORKER_EVIDENCE_DOMAIN
from orev3.execution.readiness_candidate import (
    CANONICAL_RECEIPT_UNAVAILABLE,
    FAILURE_RECEIPT_DOMAIN,
    INVARIANT_SERIALIZATION_ORDER,
    PHASE3C_EVALUATION_ORDER,
    Phase3CDisposition,
    Phase3CEvaluationInput,
    ReceiptValidationContext,
    ReadinessRejected,
    ReadinessValidated,
    _TestMachineryFailurePlan,
    _evaluate_readiness_candidate_for_test,
    evaluate_readiness_candidate,
    load_readiness_failure_receipt_bytes,
    reconstruct_failure_receipt_identity,
    validate_readiness_failure_receipt,
)
_SLICE3_TEST_PATH = Path(__file__).with_name("test_phase3c_readiness_record_v2.py")
_SLICE3_SPEC = importlib.util.spec_from_file_location(
    "_orev3_slice3_test_fixture", _SLICE3_TEST_PATH
)
assert _SLICE3_SPEC is not None and _SLICE3_SPEC.loader is not None
_SLICE3_MODULE = importlib.util.module_from_spec(_SLICE3_SPEC)
_SLICE3_SPEC.loader.exec_module(_SLICE3_MODULE)
_prospective_git_candidate = _SLICE3_MODULE._prospective_git_candidate
_reconstruct_evidence_identity = _SLICE3_MODULE._reconstruct_evidence_identity


def _build_evaluation(tmp_path: Path) -> Phase3CEvaluationInput:
    repository, record, prerequisites, evidence = _prospective_git_candidate(tmp_path)
    material = dict(record.material)
    del material["readiness_identity"]
    authority = record.material["git_authority"]
    return Phase3CEvaluationInput(
        repository=repository,
        experiment_identifier=record.experiment_identifier,
        repository_authority_identifier=authority["repository_authority_identifier"],
        approved_branch_ref=authority["approved_branch_ref"],
        readiness_material=material,
        prerequisites=prerequisites,
        phase3b_evidence=evidence,
    )


@pytest.fixture(scope="module")
def evaluation(tmp_path_factory: pytest.TempPathFactory) -> Phase3CEvaluationInput:
    return _build_evaluation(tmp_path_factory.mktemp("phase3c-candidate"))


@pytest.fixture(scope="module")
def zero_evaluation(
    tmp_path_factory: pytest.TempPathFactory,
) -> Phase3CEvaluationInput:
    repository, record, prerequisites, evidence = _prospective_git_candidate(
        tmp_path_factory.mktemp("phase3c-zero-candidate"), zero_input=True
    )
    material = dict(record.material)
    material.pop("readiness_identity")
    authority = record.material["git_authority"]
    return Phase3CEvaluationInput(
        repository=repository,
        experiment_identifier=record.experiment_identifier,
        repository_authority_identifier=authority[
            "repository_authority_identifier"
        ],
        approved_branch_ref=authority["approved_branch_ref"],
        readiness_material=material,
        prerequisites=prerequisites,
        phase3b_evidence=evidence,
    )


def _receipt_context(
    evaluation: Phase3CEvaluationInput, result: ReadinessRejected
) -> ReceiptValidationContext:
    receipt = result.receipt
    source = receipt["candidate_source_commit"].get("value")
    readiness = receipt["readiness_identity"].get("value")
    return ReceiptValidationContext(
        experiment_identifier=evaluation.experiment_identifier,
        repository_authority_identifier=evaluation.repository_authority_identifier,
        approved_branch_ref=evaluation.approved_branch_ref,
        failed_invariant_identifier=receipt["failed_invariant_identifier"],
        candidate_source_commit=source,
        readiness_identity=readiness,
    )


def _rehash_receipt(receipt: dict) -> None:
    material = {key: value for key, value in receipt.items() if key != "failure_receipt_identity"}
    receipt["failure_receipt_identity"] = domain_identity(
        FAILURE_RECEIPT_DOMAIN, material
    )


def _mutated_evaluation(
    evaluation: Phase3CEvaluationInput, invariant: str
) -> Phase3CEvaluationInput:
    material = copy.deepcopy(evaluation.readiness_material)
    if invariant == "git_authority":
        substituted = "substituted-repository-authority"
        material["git_authority"]["repository_authority_identifier"] = substituted
        return replace(
            evaluation,
            repository_authority_identifier=substituted,
            readiness_material=material,
        )
    mutations = {
        "readiness_specification": lambda: material["readiness_specification"].__setitem__("specification_identity", "1" * 64),
        "schema_registry": lambda: material["schema"].__setitem__("schema_registry_identifier", "substituted-registry"),
        "experiment": lambda: material["experiment"].__setitem__("experiment_configuration_identity", "2" * 64),
        "control_plane": lambda: material["control_plane"]["components"][0].__setitem__("component_identifier", "substituted-component"),
        "source_scopes": lambda: material.__setitem__("source_scopes", material["source_scopes"][:-1]),
        "protocol": lambda: material["protocol"].__setitem__("protocol_identity", "3" * 64),
        "implementation": lambda: material["implementation"].__setitem__("adapter_identifier", "substituted-adapter"),
        "execution_specification": lambda: material["execution_specification"].__setitem__("specification_identity", "4" * 64),
        "execution_profile": lambda: material["execution_profile"].__setitem__("profile_identity", "5" * 64),
        "runtime": lambda: material["runtime"].__setitem__("runtime_bundle_identity", "6" * 64),
        "configuration": lambda: material["configuration"].__setitem__("decision_selection_identity", "7" * 64),
        "external_inputs": lambda: material["external_inputs"].__setitem__("declarations", []),
        "replay": lambda: material["replay"].__setitem__("replay_identity", "8" * 64),
        "artifacts": lambda: material["artifacts"].__setitem__("output_policy_identity", "9" * 64),
        "outcome_policy": lambda: material["outcome_policy"].__setitem__("profile_identity", "a" * 64),
        "validation": lambda: material["validation"].__setitem__("test_policy_identity", "b" * 64),
        "attempt_policy": lambda: material["attempt_policy"].__setitem__("allocation_authority_identity", "c" * 64),
        "canonical_readiness_record": lambda: material.__setitem__("unexpected_top_level", "closed-shape-violation"),
    }
    mutations[invariant]()
    return replace(evaluation, readiness_material=material)


def _rehash_worker(worker: dict) -> None:
    material = dict(worker)
    material.pop("worker_evidence_identity")
    worker["worker_evidence_identity"] = domain_identity(
        PHASE3B_WORKER_EVIDENCE_DOMAIN, material
    )


def _rebind_worker_aggregate(
    evaluation: Phase3CEvaluationInput, evidence: dict
) -> Phase3CEvaluationInput:
    evidence["workers"].sort(
        key=lambda item: item["material"]["worker_evidence_identity"]
    )
    evidence["aggregate"]["worker_evidence_identities"] = [
        item["material"]["worker_evidence_identity"]
        for item in evidence["workers"]
    ]
    _reconstruct_evidence_identity(
        evidence["aggregate"],
        "orev3:experiment-evidence-preparation:v1\n",
        "evidence_preparation_identity",
    )
    material = copy.deepcopy(evaluation.readiness_material)
    material["validation"]["evidence_preparation_identity"] = evidence[
        "aggregate"
    ]["evidence_preparation_identity"]
    return replace(
        evaluation, readiness_material=material, phase3b_evidence=evidence
    )


def _rebind_subordinate_aggregate(
    evaluation: Phase3CEvaluationInput, evidence: dict
) -> Phase3CEvaluationInput:
    aggregate = evidence["aggregate"]
    aggregate["input_snapshot_identities"] = sorted(
        item["input_snapshot_identity"] for item in evidence["snapshots"]
    )
    aggregate["dataset_evidence_identities"] = sorted(
        item["dataset_validation_evidence_identity"]
        for item in evidence["datasets"]
    )
    aggregate["projection_evidence_identities"] = sorted(
        item["projection_evidence_identity"] for item in evidence["projections"]
    )
    aggregate["replay_evidence_identity"] = evidence["replay"][
        "replay_evidence_identity"
    ]
    aggregate["population_evidence_identity"] = evidence["population"][
        "population_accounting_evidence_identity"
    ]
    aggregate["profile_evidence_identity"] = evidence["profile"][
        "profile_conformance_evidence_identity"
    ]
    aggregate["artifact_evidence_identity"] = evidence["artifacts"][
        "artifact_declaration_evidence_identity"
    ]
    _reconstruct_evidence_identity(
        aggregate,
        "orev3:experiment-evidence-preparation:v1\n",
        "evidence_preparation_identity",
    )
    material = copy.deepcopy(evaluation.readiness_material)
    material["external_inputs"]["input_snapshot_identities"] = list(
        aggregate["input_snapshot_identities"]
    )
    material["external_inputs"]["dataset_validation_evidence_identities"] = list(
        aggregate["dataset_evidence_identities"]
    )
    material["external_inputs"]["projection_evidence_identities"] = list(
        aggregate["projection_evidence_identities"]
    )
    material["validation"]["evidence_preparation_identity"] = aggregate[
        "evidence_preparation_identity"
    ]
    return replace(
        evaluation, readiness_material=material, phase3b_evidence=evidence
    )


def test_success_returns_exact_canonical_candidate_deterministically(
    evaluation: Phase3CEvaluationInput,
) -> None:
    first = evaluate_readiness_candidate(evaluation)
    second = evaluate_readiness_candidate(evaluation)
    assert isinstance(first, ReadinessValidated)
    assert isinstance(second, ReadinessValidated)
    assert first.disposition is Phase3CDisposition.READINESS_VALIDATED
    assert first.candidate_bytes == canonical_bytes(first.record.material)
    assert first.candidate_bytes == second.candidate_bytes
    assert first.readiness_identity == second.readiness_identity
    assert first.candidate_bytes.endswith(b"\n")


def test_complete_zero_input_candidate_is_validated_without_shortcut(
    zero_evaluation: Phase3CEvaluationInput,
) -> None:
    first = evaluate_readiness_candidate(zero_evaluation)
    second = evaluate_readiness_candidate(zero_evaluation)
    assert isinstance(first, ReadinessValidated)
    assert isinstance(second, ReadinessValidated)
    assert first.candidate_bytes == second.candidate_bytes
    assert first.readiness_identity == second.readiness_identity
    assert first.record.material["external_inputs"] == {
        "dataset_validation_evidence_identities": [],
        "declarations": [],
        "input_snapshot_identities": [],
        "projection_evidence_identities": [],
    }
    assert first.record.material["replay"]["candidate_order"] == []
    assert first.record.material["replay"]["population_accounting"][
        "source_count"
    ] == 0


def test_rehashed_zero_projection_authority_fails_replay(
    zero_evaluation: Phase3CEvaluationInput,
) -> None:
    evidence = copy.deepcopy(zero_evaluation.phase3b_evidence)
    replay = evidence["replay"]
    replay["projection_identity"] = "4" * 64
    replay_core = {
        key: value
        for key, value in replay.items()
        if key not in {"replay_evidence_identity", "replay_identity", "schema_version"}
    }
    replay["replay_identity"] = domain_identity(
        "orev3:experiment-replay-evidence:v1\n", replay_core
    )
    _reconstruct_evidence_identity(
        replay,
        "orev3:experiment-replay-evidence:v1\n",
        "replay_evidence_identity",
    )
    altered = _rebind_subordinate_aggregate(zero_evaluation, evidence)
    material = copy.deepcopy(altered.readiness_material)
    material["replay"] = {
        **{key: value for key, value in replay.items() if key != "schema_version"},
        "population_accounting": {
            key: value
            for key, value in evidence["population"].items()
            if key != "schema_version"
        },
    }
    altered = replace(altered, readiness_material=material)
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "replay"


def test_rehashed_normalized_phase3a_output_fails_validation(
    evaluation: Phase3CEvaluationInput,
) -> None:
    evidence = copy.deepcopy(evaluation.phase3b_evidence)
    bundle = next(
        item
        for item in evidence["workers"]
        if item["material"]["worker_kind"] == "PHASE3A_VALIDATOR"
    )
    bundle["result"]["adapter_identity"] = "5" * 64
    bundle["material"]["output_identity"] = domain_identity(
        PHASE3B_WORKER_EVIDENCE_DOMAIN, bundle["result"]
    )
    _rehash_worker(bundle["material"])
    altered = _rebind_worker_aggregate(evaluation, evidence)
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "validation"


def test_normalized_phase3a_worker_is_root_relocation_invariant(
    evaluation: Phase3CEvaluationInput,
) -> None:
    from orev3.execution.evidence_preparation import (
        PHASE3A_NORMALIZED_CODE_PATHS,
        reconstruct_prospective_phase3a_worker,
    )

    existing = next(
        item
        for item in evaluation.phase3b_evidence["workers"]
        if item["material"]["worker_kind"] == "PHASE3A_VALIDATOR"
    )
    normalized = existing["result"]
    raw = {
        "adapter_identity": normalized["adapter_identity"],
        "adapter_registry_identity": normalized["adapter_registry_identity"],
        "closed_dependency_environment_identity": normalized[
            "closed_dependency_environment_identity"
        ],
        "closed_dependency_root_path": "/temporary/a",
        "command": "validate_runtime",
        "dependency_import_origins": normalized["dependency_import_origins"],
        "evidence_disposition": normalized["evidence_disposition"],
        "network_denial_verified": True,
        "project_control_plane_origins": list(PHASE3A_NORMALIZED_CODE_PATHS),
        "remaining_predicates": normalized["remaining_predicates"],
        "runtime_contract_identity": normalized["runtime_contract_identity"],
        "source_commit": normalized["source_commit"],
        "status": "evidence_passed",
    }
    arguments = {
        "repository": evaluation.repository,
        "source_commit": evaluation.prerequisites.source_commit,
        "approved_branch_ref": evaluation.approved_branch_ref,
        "repository_authority_identifier": evaluation.repository_authority_identifier,
        "source_scopes": evaluation.readiness_material["source_scopes"],
        "capability_policy_identity": evaluation.phase3b_evidence["aggregate"][
            "capability_policy_identity"
        ],
        "sandbox_template_identity": existing["material"][
            "sandbox_template_identity"
        ],
    }
    first = reconstruct_prospective_phase3a_worker(
        phase3a_result=raw, **arguments
    )
    raw["closed_dependency_root_path"] = "/different/controller/root"
    second = reconstruct_prospective_phase3a_worker(
        phase3a_result=raw, **arguments
    )
    assert first.evidence_identity == second.evidence_identity
    assert first.result == second.result
    assert "closed_dependency_root_path" not in first.result


def test_complete_outcome_aware_candidate_remains_outcome_value_free(
    tmp_path: Path,
) -> None:
    repository, record, prerequisites, evidence = _prospective_git_candidate(
        tmp_path, outcome_aware=True
    )
    material = dict(record.material)
    material.pop("readiness_identity")
    evaluation = Phase3CEvaluationInput(
        repository=repository,
        experiment_identifier=record.experiment_identifier,
        repository_authority_identifier=record.material["git_authority"][
            "repository_authority_identifier"
        ],
        approved_branch_ref=record.material["git_authority"][
            "approved_branch_ref"
        ],
        readiness_material=material,
        prerequisites=prerequisites,
        phase3b_evidence=evidence,
    )
    result = evaluate_readiness_candidate(evaluation)
    assert isinstance(result, ReadinessValidated)
    assert result.record.material["outcome_policy"]["profile_name"] == "outcome_aware_v1"
    assert len(
        result.record.material["outcome_policy"]["profile_contract_identities"]
    ) == 6
    encoded = result.candidate_bytes.lower()
    assert b'"outcome":' not in encoded
    assert b'"winner"' not in encoded
    assert b'"label"' not in encoded


@pytest.mark.parametrize("failed", PHASE3C_EVALUATION_ORDER)
def test_every_phase3c_first_failure_has_exact_receipt_vector(
    evaluation: Phase3CEvaluationInput, failed: str
) -> None:
    altered = _mutated_evaluation(evaluation, failed)
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.disposition is Phase3CDisposition.READINESS_REJECTED
    receipt = result.receipt
    assert receipt["failed_invariant_identifier"] == failed
    assert reconstruct_failure_receipt_identity(receipt) == result.failure_receipt_identity
    assert load_readiness_failure_receipt_bytes(
        result.receipt_bytes, context=_receipt_context(altered, result)
    ) == receipt
    statuses = receipt["check_statuses"]
    assert [item["check_identifier"] for item in statuses] == list(
        INVARIANT_SERIALIZATION_ORDER
    )
    assert sum(item["status"] == "failed" for item in statuses) == 1
    assert all(item["status"] == "not_applicable" for item in statuses[19:])
    failure_index = PHASE3C_EVALUATION_ORDER.index(failed)
    expected_passed = set(PHASE3C_EVALUATION_ORDER[:failure_index])
    for item in statuses[:19]:
        expected = (
            "failed"
            if item["check_identifier"] == failed
            else "passed"
            if item["check_identifier"] in expected_passed
            else "not_evaluated"
        )
        assert item["status"] == expected
    source_status = receipt["candidate_source_commit"]["status"]
    assert source_status == ("absent" if failed == "git_authority" else "known")
    assert receipt["readiness_identity"] == {"status": "absent"}
    assert receipt["launch_authority_snapshot_identity"] == {"status": "absent"}
    assert b"Traceback" not in result.receipt_bytes


def test_final_result_construction_failure_keeps_known_readiness_identity(
    evaluation: Phase3CEvaluationInput,
) -> None:
    result = _evaluate_readiness_candidate_for_test(
        evaluation,
        _TestMachineryFailurePlan(fail_result_construction=True),
    )
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "canonical_readiness_record"
    assert result.receipt["readiness_identity"]["status"] == "known"
    assert b"test final-result" not in result.receipt_bytes


@pytest.mark.parametrize(
    "mutation",
    (
        "failed_invariant",
        "status",
        "reorder",
        "missing",
        "authority",
        "readiness",
        "identity",
        "unknown",
        "diagnostic",
        "outcome",
    ),
)
def test_receipt_tampering_rejects(
    evaluation: Phase3CEvaluationInput, mutation: str
) -> None:
    altered = _mutated_evaluation(evaluation, "runtime")
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    receipt = copy.deepcopy(result.receipt)
    if mutation == "failed_invariant":
        receipt["failed_invariant_identifier"] = "configuration"
    elif mutation == "status":
        receipt["check_statuses"][0]["status"] = "failed"
    elif mutation == "reorder":
        receipt["check_statuses"][0], receipt["check_statuses"][1] = (
            receipt["check_statuses"][1], receipt["check_statuses"][0]
        )
    elif mutation == "missing":
        receipt["check_statuses"].pop()
    elif mutation == "authority":
        receipt["candidate_source_commit"] = {"status": "absent"}
    elif mutation == "readiness":
        receipt["readiness_identity"] = {"status": "known", "value": "1" * 64}
    elif mutation == "identity":
        receipt["failure_receipt_identity"] = "1" * 64
    elif mutation == "unknown":
        receipt["extension"] = "x"
    elif mutation == "diagnostic":
        receipt["diagnostic"] = "exception"
    else:
        receipt["scientific_outcome_evidence"] = "winner"
    with pytest.raises(CanonicalControlError):
        validate_readiness_failure_receipt(
            receipt, context=_receipt_context(altered, result)
        )


def test_pre_entry_and_receipt_serialization_failures_are_payload_free(
    evaluation: Phase3CEvaluationInput,
) -> None:
    malformed = copy.copy(evaluation)
    object.__setattr__(malformed, "experiment_identifier", "INVALID")
    assert evaluate_readiness_candidate(malformed) is CANONICAL_RECEIPT_UNAVAILABLE
    assert (
        _evaluate_readiness_candidate_for_test(
            evaluation,
            _TestMachineryFailurePlan(fail_entry=True),
        )
        is CANONICAL_RECEIPT_UNAVAILABLE
    )
    assert (
        _evaluate_readiness_candidate_for_test(
            evaluation,
            _TestMachineryFailurePlan(
                fail_active_invariant="runtime",
                fail_receipt_serialization=True,
            ),
        )
        is CANONICAL_RECEIPT_UNAVAILABLE
    )
    ordinary = _evaluate_readiness_candidate_for_test(
        evaluation,
        _TestMachineryFailurePlan(fail_active_invariant="runtime"),
    )
    assert isinstance(ordinary, ReadinessRejected)


@pytest.mark.parametrize(
    ("earlier", "later"),
    (
        ("git_authority", "experiment"),
        ("readiness_specification", "experiment"),
        ("schema_registry", "experiment"),
        ("control_plane", "source_scopes"),
        ("external_inputs", "replay"),
        ("replay", "artifacts"),
        ("validation", "attempt_policy"),
        ("attempt_policy", "canonical_readiness_record"),
    ),
)
def test_real_multi_defect_precedence(
    evaluation: Phase3CEvaluationInput, earlier: str, later: str
) -> None:
    first = _mutated_evaluation(evaluation, earlier)
    second = _mutated_evaluation(first, later)
    result = evaluate_readiness_candidate(second)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == earlier
    assert result.receipt["candidate_source_commit"]["status"] == (
        "absent" if earlier == "git_authority" else "known"
    )


def test_rehashed_snapshot_member_authority_fails_external_inputs(
    evaluation: Phase3CEvaluationInput,
) -> None:
    evidence = copy.deepcopy(evaluation.phase3b_evidence)
    snapshot = evidence["snapshots"][0]
    snapshot["members"][0]["sha256"] = "1" * 64
    _reconstruct_evidence_identity(
        snapshot,
        "orev3:experiment-input-snapshot:v1\n",
        "input_snapshot_identity",
    )
    altered = _rebind_subordinate_aggregate(evaluation, evidence)
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "external_inputs"


@pytest.mark.parametrize(
    ("worker_kind", "expected_owner"),
    (
        ("INPUT_PROJECTOR", "external_inputs"),
        ("REPLAY_PREPARATION", "replay"),
        ("READINESS_TEST", "validation"),
    ),
)
def test_rehashed_worker_command_authority_fails_at_owner(
    evaluation: Phase3CEvaluationInput,
    worker_kind: str,
    expected_owner: str,
) -> None:
    evidence = copy.deepcopy(evaluation.phase3b_evidence)
    worker = next(
        item["material"]
        for item in evidence["workers"]
        if item["material"]["worker_kind"] == worker_kind
    )
    worker["command_identity"] = "2" * 64
    _rehash_worker(worker)
    altered = _rebind_worker_aggregate(evaluation, evidence)
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == expected_owner


@pytest.mark.parametrize(
    ("worker_kind", "attack", "expected_owner"),
    (
        ("INPUT_PROJECTOR", "replacement", "external_inputs"),
        ("INPUT_PROJECTOR", "missing", "external_inputs"),
        ("INPUT_PROJECTOR", "extra", "external_inputs"),
        ("REPLAY_PREPARATION", "replacement", "replay"),
        ("READINESS_TEST", "extra", "validation"),
    ),
)
def test_rehashed_worker_capability_fails_at_owner(
    evaluation: Phase3CEvaluationInput,
    worker_kind: str,
    attack: str,
    expected_owner: str,
) -> None:
    evidence = copy.deepcopy(evaluation.phase3b_evidence)
    worker = next(
        item["material"]
        for item in evidence["workers"]
        if item["material"]["worker_kind"] == worker_kind
    )
    original = list(worker["input_capability_identities"])
    if attack == "replacement":
        worker["input_capability_identities"] = ["3" * 64]
    elif attack == "missing":
        worker["input_capability_identities"] = []
    else:
        worker["input_capability_identities"] = sorted([*original, "3" * 64])
    _rehash_worker(worker)
    altered = _rebind_worker_aggregate(evaluation, evidence)
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == expected_owner


def test_rehashed_artifact_evidence_fails_artifacts(
    evaluation: Phase3CEvaluationInput,
) -> None:
    evidence = copy.deepcopy(evaluation.phase3b_evidence)
    artifact = evidence["artifacts"]
    artifact["output_policy_identity"] = "5" * 64
    _reconstruct_evidence_identity(
        artifact,
        "orev3:experiment-artifact-declaration-evidence:v1\n",
        "artifact_declaration_evidence_identity",
    )
    altered = _rebind_subordinate_aggregate(evaluation, evidence)
    altered.readiness_material["artifacts"]["output_policy_identity"] = "5" * 64
    altered.readiness_material["artifacts"][
        "artifact_declaration_evidence_identity"
    ] = artifact["artifact_declaration_evidence_identity"]
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "artifacts"


def test_rehashed_profile_evidence_fails_outcome_policy(
    evaluation: Phase3CEvaluationInput,
) -> None:
    evidence = copy.deepcopy(evaluation.phase3b_evidence)
    profile = evidence["profile"]
    profile["reconciled_artifact_declaration_identities"] = ["6" * 64]
    _reconstruct_evidence_identity(
        profile,
        "orev3:experiment-profile-conformance-evidence:v1\n",
        "profile_conformance_evidence_identity",
    )
    altered = _rebind_subordinate_aggregate(evaluation, evidence)
    altered.readiness_material["outcome_policy"][
        "profile_conformance_evidence_identity"
    ] = profile["profile_conformance_evidence_identity"]
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "outcome_policy"


def test_rehashed_attempt_authority_claim_fails_attempt_policy(
    evaluation: Phase3CEvaluationInput,
) -> None:
    material = copy.deepcopy(evaluation.readiness_material)
    material["attempt_policy"]["allocation_authority_identity"] = "7" * 64
    result = evaluate_readiness_candidate(
        replace(evaluation, readiness_material=material)
    )
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "attempt_policy"


def test_transition_failure_is_owned_by_new_active_invariant(
    evaluation: Phase3CEvaluationInput,
) -> None:
    result = _evaluate_readiness_candidate_for_test(
        evaluation,
        _TestMachineryFailurePlan(fail_transition_to="runtime"),
    )
    assert isinstance(result, ReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "runtime"


@pytest.mark.parametrize(
    "attack",
    (
        "git_known_source",
        "runtime_known_readiness",
        "experiment",
        "repository",
        "failed_invariant",
        "impossible_availability",
    ),
)
def test_fully_rehashed_receipt_semantic_attacks_reject(
    evaluation: Phase3CEvaluationInput, attack: str
) -> None:
    failed = "git_authority" if attack == "git_known_source" else "runtime"
    altered = _mutated_evaluation(evaluation, failed)
    result = evaluate_readiness_candidate(altered)
    assert isinstance(result, ReadinessRejected)
    receipt = copy.deepcopy(result.receipt)
    context = _receipt_context(altered, result)
    if attack == "git_known_source":
        receipt["candidate_source_commit"] = {"status": "known", "value": "1" * 40}
    elif attack in {"runtime_known_readiness", "impossible_availability"}:
        receipt["readiness_identity"] = {"status": "known", "value": "2" * 64}
    elif attack == "experiment":
        receipt["experiment_identifier"] = "different-experiment"
    elif attack == "repository":
        receipt["repository_authority_identifier"] = "different-repository"
    else:
        receipt["failed_invariant_identifier"] = "configuration"
        failure_index = PHASE3C_EVALUATION_ORDER.index("configuration")
        passed = set(PHASE3C_EVALUATION_ORDER[:failure_index])
        for item in receipt["check_statuses"]:
            identifier = item["check_identifier"]
            item["status"] = (
                "not_applicable"
                if identifier not in PHASE3C_EVALUATION_ORDER
                else "failed"
                if identifier == "configuration"
                else "passed"
                if identifier in passed
                else "not_evaluated"
            )
    _rehash_receipt(receipt)
    with pytest.raises(CanonicalControlError):
        validate_readiness_failure_receipt(receipt, context=context)


def test_production_api_has_no_executable_authority_hooks() -> None:
    signature = inspect.signature(evaluate_readiness_candidate)
    assert tuple(signature.parameters) == ("evaluation",)
    assert all(
        "Callable" not in str(field.type)
        for field in Phase3CEvaluationInput.__dataclass_fields__.values()
    )


def test_representative_semantic_rejection_is_deterministic(
    evaluation: Phase3CEvaluationInput,
) -> None:
    altered = _mutated_evaluation(evaluation, "runtime")
    first = evaluate_readiness_candidate(altered)
    second = evaluate_readiness_candidate(altered)
    assert isinstance(first, ReadinessRejected)
    assert isinstance(second, ReadinessRejected)
    assert first.receipt_bytes == second.receipt_bytes
    assert first.failure_receipt_identity == second.failure_receipt_identity


def test_success_path_performs_no_filesystem_writes(
    evaluation: Phase3CEvaluationInput, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("Slice 4 attempted a filesystem write")

    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    assert isinstance(evaluate_readiness_candidate(evaluation), ReadinessValidated)


def test_evaluator_has_no_lifecycle_or_scientific_payload_surface() -> None:
    import orev3.execution.readiness_candidate as candidate

    source = Path(candidate.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "DecisionContext",
        "FeatureContext",
        "build_attempt_allocation",
        "derive_readiness_seal",
        "run_launch_smoke",
        "build_output_namespace",
        "ranking_callback",
        "evaluation_callback",
    ):
        assert forbidden not in source
