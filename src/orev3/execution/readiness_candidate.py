"""Pure Phase-3C terminal readiness evaluation.

This module turns already-governed prospective authority and detached evidence
into exactly one bounded result.  It deliberately has no persistence, seal,
current-readiness, launch, allocation, control-storage, or scientific-execution
capability.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    normalize_experiment_identifier,
    parse_canonical_bytes,
    parse_json,
    require_sha256,
    require_string,
    validate_exact_fields,
    validate_json_schema_instance,
    validate_repository_path,
)
from orev3.execution.git_state import (
    GitAuthorityError,
    GitDiagnosticCode,
    GitRepository,
    validate_record_v2_git_bindings,
)
from orev3.execution.readiness_record import (
    CANONICAL_ENCODING_REVISION,
    READINESS_SPECIFICATION_V1_1_PATH,
    READINESS_SPECIFICATION_V1_1_REVISION,
    READINESS_SPECIFICATION_V1_1_SHA256,
    READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
    READINESS_V1_1_SCHEMA_KIND_ORDER,
    READINESS_V1_1_SCHEMA_POLICY,
    READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER,
    REPOSITORY_AUTHORITY_PATH,
    ReadinessRecordV2,
    build_readiness_record_v2,
    canonical_readiness_record_path,
    load_repository_authority_bytes,
    load_readiness_record_v2_bytes,
    reconstruct_control_component_identity,
    reconstruct_document_binding_identity,
    reconstruct_implementation_identity,
    reconstruct_protocol_binding_identity,
)


FAILURE_RECEIPT_DOMAIN = "orev3:experiment-readiness-failure-receipt:v1\n"
FAILURE_RECEIPT_SCHEMA_PATH = (
    Path(__file__).parent / "schemas/v1/readiness-failure-receipt.schema.json"
)

INVARIANT_SERIALIZATION_ORDER = (
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

PHASE3C_EVALUATION_ORDER = (
    "git_authority",
    "readiness_specification",
    "schema_registry",
    "experiment",
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
)

CURRENT_READINESS_EVALUATION_ORDER = (
    "git_authority",
    "canonical_readiness_record",
    "schema_registry",
    "experiment",
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
    "readiness_seal_and_ancestry",
    "current_external_inputs",
)

_PHASE3C_APPLICABLE = frozenset(PHASE3C_EVALUATION_ORDER)
_STATUS_VALUES = frozenset(
    {"passed", "failed", "not_evaluated", "not_applicable"}
)


class Phase3CDisposition(str, Enum):
    READINESS_VALIDATED = "READINESS_VALIDATED"
    READINESS_REJECTED = "READINESS_REJECTED"


@dataclass(frozen=True, slots=True)
class ReadinessValidated:
    disposition: Phase3CDisposition
    candidate_bytes: bytes
    readiness_identity: str
    record: ReadinessRecordV2


@dataclass(frozen=True, slots=True)
class ReadinessRejected:
    disposition: Phase3CDisposition
    receipt_bytes: bytes
    failure_receipt_identity: str
    receipt: Mapping[str, Any]


class _CanonicalReceiptUnavailable(Enum):
    CANONICAL_RECEIPT_UNAVAILABLE = "CANONICAL_RECEIPT_UNAVAILABLE"


CANONICAL_RECEIPT_UNAVAILABLE = (
    _CanonicalReceiptUnavailable.CANONICAL_RECEIPT_UNAVAILABLE
)

Phase3CResult = (
    ReadinessValidated | ReadinessRejected | _CanonicalReceiptUnavailable
)


class InvariantFailure(RuntimeError):
    """Outcome-free signal that one governed invariant did not validate."""

    def __init__(self, invariant_identifier: str) -> None:
        if invariant_identifier not in _PHASE3C_APPLICABLE:
            raise ValueError("invalid Phase-3C invariant")
        super().__init__(invariant_identifier)
        self.invariant_identifier = invariant_identifier


@dataclass(frozen=True, slots=True)
class Phase3CEvaluationInput:
    repository: GitRepository
    experiment_identifier: str
    repository_authority_identifier: str
    approved_branch_ref: str
    readiness_material: Mapping[str, Any]
    prerequisites: Any
    phase3b_evidence: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ReceiptValidationContext:
    experiment_identifier: str
    repository_authority_identifier: str
    approved_branch_ref: str
    failed_invariant_identifier: str
    candidate_source_commit: str | None
    readiness_identity: str | None
    receipt_class: str = "READINESS_REJECTED"
    current_readiness_disposition: str = "not_applicable"


@dataclass(frozen=True, slots=True)
class _TestMachineryFailurePlan:
    """Closed test-only machinery failures; never accepted by the public API."""

    fail_entry: bool = False
    fail_active_invariant: str | None = None
    fail_transition_to: str | None = None
    fail_result_construction: bool = False
    fail_receipt_serialization: bool = False


@dataclass(slots=True)
class _EvaluationState:
    active: str = "git_authority"
    passed: tuple[str, ...] = ()
    candidate_source_commit: str | None = None
    readiness_identity: str | None = None

    def transition(self, next_invariant: str) -> None:
        previous = self.active
        self.active = next_invariant
        self.passed = (*self.passed, previous)


def reconstruct_failure_receipt_identity(material: Mapping[str, Any]) -> str:
    identity_material = dict(material)
    require_sha256(
        "failure_receipt_identity",
        identity_material.pop("failure_receipt_identity", None),
    )
    return domain_identity(FAILURE_RECEIPT_DOMAIN, identity_material)


def validate_readiness_failure_receipt(
    material: Mapping[str, Any], *, context: ReceiptValidationContext,
    schema: Mapping[str, Any] | None = None,
) -> None:
    fields = {
        "approved_branch_ref",
        "candidate_source_commit",
        "check_statuses",
        "current_readiness_disposition",
        "experiment_identifier",
        "failed_invariant_identifier",
        "failure_receipt_identity",
        "launch_authority_snapshot_identity",
        "readiness_identity",
        "receipt_class",
        "repository_authority_identifier",
        "schema_version",
        "scientific_execution_started",
        "scientific_outcome_evidence",
    }
    validate_exact_fields(material, fields, label="readiness-failure-receipt")
    if material["schema_version"] != 1:
        raise CanonicalControlError("failure receipt schema revision is unsupported")
    if context.receipt_class not in {"READINESS_REJECTED", "CURRENT_READINESS"}:
        raise CanonicalControlError("receipt validation context is unsupported")
    if material["receipt_class"] != context.receipt_class:
        raise CanonicalControlError("failure receipt class differs from context")
    if material["current_readiness_disposition"] != context.current_readiness_disposition:
        raise CanonicalControlError("failure receipt disposition differs from context")
    if context.receipt_class == "READINESS_REJECTED":
        evaluation_order = PHASE3C_EVALUATION_ORDER
    else:
        evaluation_order = CURRENT_READINESS_EVALUATION_ORDER
    normalize_experiment_identifier(material["experiment_identifier"])
    require_string("repository_authority_identifier", material["repository_authority_identifier"])
    branch = require_string("approved_branch_ref", material["approved_branch_ref"])
    if not branch.startswith("refs/heads/"):
        raise CanonicalControlError("approved branch ref must be a full branch ref")
    _validate_availability(material["candidate_source_commit"], git=True)
    _validate_availability(material["readiness_identity"], git=False)
    if material["launch_authority_snapshot_identity"] != {"status": "absent"}:
        raise CanonicalControlError("pre-launch receipt snapshot authority must be absent")
    if material["scientific_execution_started"] is not False:
        raise CanonicalControlError("scientific execution cannot start in a receipt")
    if material["scientific_outcome_evidence"] != "absent":
        raise CanonicalControlError("scientific outcome evidence must be absent")
    failed = material["failed_invariant_identifier"]
    applicable = frozenset(evaluation_order)
    if failed not in applicable:
        raise CanonicalControlError("failure receipt invariant is not stage-applicable")
    statuses = material["check_statuses"]
    if not isinstance(statuses, list) or len(statuses) != 27:
        raise CanonicalControlError("failure receipt must contain 27 statuses")
    if [item.get("check_identifier") for item in statuses if isinstance(item, Mapping)] != list(INVARIANT_SERIALIZATION_ORDER):
        raise CanonicalControlError("failure receipt status order is invalid")
    passed = set(evaluation_order[: evaluation_order.index(failed)])
    for item in statuses:
        validate_exact_fields(item, {"check_identifier", "status"}, label="failure check status")
        identifier = item["check_identifier"]
        status = item["status"]
        if status not in _STATUS_VALUES:
            raise CanonicalControlError("failure receipt status is invalid")
        expected = (
            "not_applicable"
            if identifier not in applicable
            else "failed"
            if identifier == failed
            else "passed"
            if identifier in passed
            else "not_evaluated"
        )
        if status != expected:
            raise CanonicalControlError("failure receipt status progression is invalid")
    expected_experiment = normalize_experiment_identifier(
        context.experiment_identifier
    )
    if (
        material["experiment_identifier"] != expected_experiment
        or material["repository_authority_identifier"]
        != context.repository_authority_identifier
        or material["approved_branch_ref"] != context.approved_branch_ref
        or failed != context.failed_invariant_identifier
    ):
        raise CanonicalControlError("failure receipt context does not reconstruct")
    expected_source = _availability(context.candidate_source_commit)
    expected_readiness = _availability(context.readiness_identity)
    if context.receipt_class == "READINESS_REJECTED":
        if failed == "git_authority":
            expected_source = {"status": "absent"}
        elif context.candidate_source_commit is None:
            raise CanonicalControlError("post-Git failure requires known source authority")
        if context.readiness_identity is not None and failed != "canonical_readiness_record":
            raise CanonicalControlError("known readiness identity is outside its authority point")
    if (
        material["candidate_source_commit"] != expected_source
        or material["readiness_identity"] != expected_readiness
    ):
        raise CanonicalControlError("failure receipt availability does not reconstruct")
    if reconstruct_failure_receipt_identity(material) != material["failure_receipt_identity"]:
        raise CanonicalControlError("failure receipt identity does not reconstruct")
    if schema is not None:
        validate_json_schema_instance(material, schema, schema_registry={})


def load_readiness_failure_receipt_bytes(
    raw: bytes, *, context: ReceiptValidationContext,
    schema: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    return parse_canonical_bytes(
        raw,
        validator=lambda value: validate_readiness_failure_receipt(
            value, context=context, schema=schema
        ),
    )


def build_readiness_failure_receipt(
    *,
    experiment_identifier: str,
    repository_authority_identifier: str,
    approved_branch_ref: str,
    failed_invariant_identifier: str,
    candidate_source_commit: str | None,
    readiness_identity: str | None,
    schema: Mapping[str, Any],
    receipt_class: str = "READINESS_REJECTED",
    current_readiness_disposition: str = "not_applicable",
) -> Mapping[str, Any]:
    evaluation_order = (
        PHASE3C_EVALUATION_ORDER
        if receipt_class == "READINESS_REJECTED"
        else CURRENT_READINESS_EVALUATION_ORDER
        if receipt_class == "CURRENT_READINESS"
        else ()
    )
    applicable = frozenset(evaluation_order)
    if failed_invariant_identifier not in applicable:
        raise CanonicalControlError("invalid stage failed invariant")
    passed = set(
        evaluation_order[
            : evaluation_order.index(failed_invariant_identifier)
        ]
    )
    statuses = []
    for identifier in INVARIANT_SERIALIZATION_ORDER:
        status = (
            "not_applicable"
            if identifier not in applicable
            else "failed"
            if identifier == failed_invariant_identifier
            else "passed"
            if identifier in passed
            else "not_evaluated"
        )
        statuses.append({"check_identifier": identifier, "status": status})
    receipt = {
        "approved_branch_ref": approved_branch_ref,
        "candidate_source_commit": _availability(candidate_source_commit),
        "check_statuses": statuses,
        "current_readiness_disposition": current_readiness_disposition,
        "experiment_identifier": normalize_experiment_identifier(experiment_identifier),
        "failed_invariant_identifier": failed_invariant_identifier,
        "launch_authority_snapshot_identity": {"status": "absent"},
        "readiness_identity": _availability(readiness_identity),
        "receipt_class": receipt_class,
        "repository_authority_identifier": repository_authority_identifier,
        "schema_version": 1,
        "scientific_execution_started": False,
        "scientific_outcome_evidence": "absent",
    }
    receipt["failure_receipt_identity"] = domain_identity(
        FAILURE_RECEIPT_DOMAIN, receipt
    )
    validate_readiness_failure_receipt(
        receipt,
        context=ReceiptValidationContext(
            experiment_identifier=experiment_identifier,
            repository_authority_identifier=repository_authority_identifier,
            approved_branch_ref=approved_branch_ref,
            failed_invariant_identifier=failed_invariant_identifier,
            candidate_source_commit=candidate_source_commit,
            readiness_identity=readiness_identity,
            receipt_class=receipt_class,
            current_readiness_disposition=current_readiness_disposition,
        ),
        schema=schema,
    )
    return receipt


def evaluate_readiness_candidate(
    evaluation: Phase3CEvaluationInput,
) -> Phase3CResult:
    """Return the bounded terminal Phase-3C result without writing anything."""

    return _evaluate_readiness_candidate(evaluation, machinery=None)


def validate_phase3c_invariant_bindings(
    evaluation: Phase3CEvaluationInput, invariant_identifier: str
) -> None:
    """Run the shared governed reconstruction for one Phase-3C owner."""

    if invariant_identifier not in PHASE3C_EVALUATION_ORDER[:-1]:
        raise ValueError("invariant has no incremental Git-binding owner")
    if invariant_identifier == "git_authority":
        _check_git_authority(evaluation)
    else:
        _check_semantic_invariant(evaluation, invariant_identifier)


def _evaluate_readiness_candidate_for_test(
    evaluation: Phase3CEvaluationInput,
    machinery: _TestMachineryFailurePlan,
) -> Phase3CResult:
    return _evaluate_readiness_candidate(evaluation, machinery=machinery)


def _evaluate_readiness_candidate(
    evaluation: Phase3CEvaluationInput,
    *,
    machinery: _TestMachineryFailurePlan | None,
) -> Phase3CResult:
    """Internal state machine with a closed, non-callable test failure plan."""

    try:
        if machinery is not None and machinery.fail_entry:
            raise CanonicalControlError("test entry failure")
        experiment_identifier = normalize_experiment_identifier(
            evaluation.experiment_identifier
        )
        require_string(
            "repository_authority_identifier",
            evaluation.repository_authority_identifier,
        )
        if not evaluation.approved_branch_ref.startswith("refs/heads/"):
            raise CanonicalControlError("approved branch ref must be complete")
        receipt_schema = _load_governed_receipt_schema()
        expected_receipt_id, _ = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[
            "readiness-failure-receipt"
        ]
        if (
            receipt_schema.get("$id") != expected_receipt_id
            or receipt_schema.get("title") != "ReadinessFailureReceiptV1"
            or receipt_schema.get("additionalProperties") is not False
        ):
            raise CanonicalControlError("failure receipt schema is unavailable")
        _serializer_self_check()
    except Exception:
        return CANONICAL_RECEIPT_UNAVAILABLE

    state = _EvaluationState()
    try:
        for index, invariant in enumerate(PHASE3C_EVALUATION_ORDER):
            state.active = invariant
            if (
                machinery is not None
                and machinery.fail_active_invariant == invariant
            ):
                raise RuntimeError("test active-invariant machinery failure")
            if invariant == "git_authority":
                _check_git_authority(evaluation)
                state.candidate_source_commit = str(
                    evaluation.readiness_material["git_authority"]["source_commit"]
                )
            elif invariant != "canonical_readiness_record":
                _check_semantic_invariant(evaluation, invariant)
            if invariant == "canonical_readiness_record":
                record = build_readiness_record_v2(evaluation.readiness_material)
                candidate_bytes = canonical_bytes(record.material)
                reparsed = load_readiness_record_v2_bytes(candidate_bytes)
                validate_record_v2_git_bindings(
                    evaluation.repository,
                    reparsed,
                    prerequisites=evaluation.prerequisites,
                    phase3b_evidence=evaluation.phase3b_evidence,
                )
                state.readiness_identity = reparsed.readiness_identity
                if machinery is not None and machinery.fail_result_construction:
                    raise RuntimeError("test final-result machinery failure")
                # The final invariant becomes passed only with the constructed result.
                return ReadinessValidated(
                    Phase3CDisposition.READINESS_VALIDATED,
                    candidate_bytes,
                    reparsed.readiness_identity,
                    reparsed,
                )
            if index + 1 < len(PHASE3C_EVALUATION_ORDER):
                state.transition(PHASE3C_EVALUATION_ORDER[index + 1])
                if (
                    machinery is not None
                    and machinery.fail_transition_to == state.active
                ):
                    raise RuntimeError("test transition machinery failure")
        raise AssertionError("Phase-3C evaluation did not terminate")
    except InvariantFailure as exc:
        failed = exc.invariant_identifier
    except Exception:
        failed = state.active

    try:
        receipt = build_readiness_failure_receipt(
            experiment_identifier=experiment_identifier,
            repository_authority_identifier=evaluation.repository_authority_identifier,
            approved_branch_ref=evaluation.approved_branch_ref,
            failed_invariant_identifier=failed,
            candidate_source_commit=state.candidate_source_commit,
            readiness_identity=state.readiness_identity,
            schema=receipt_schema,
        )
        if machinery is not None and machinery.fail_receipt_serialization:
            raise RuntimeError("test receipt serialization failure")
        receipt_bytes = canonical_bytes(receipt)
        context = ReceiptValidationContext(
            experiment_identifier=experiment_identifier,
            repository_authority_identifier=evaluation.repository_authority_identifier,
            approved_branch_ref=evaluation.approved_branch_ref,
            failed_invariant_identifier=failed,
            candidate_source_commit=state.candidate_source_commit,
            readiness_identity=state.readiness_identity,
        )
        loaded = load_readiness_failure_receipt_bytes(
            receipt_bytes, context=context, schema=receipt_schema
        )
        return ReadinessRejected(
            Phase3CDisposition.READINESS_REJECTED,
            receipt_bytes,
            loaded["failure_receipt_identity"],
            loaded,
        )
    except Exception:
        return CANONICAL_RECEIPT_UNAVAILABLE


def _load_governed_receipt_schema() -> Mapping[str, Any]:
    raw = FAILURE_RECEIPT_SCHEMA_PATH.read_bytes()
    expected_id, expected_sha256 = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[
        "readiness-failure-receipt"
    ]
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CanonicalControlError("failure receipt schema digest differs")
    schema = parse_json(raw)
    if schema.get("$id") != expected_id:
        raise CanonicalControlError("failure receipt schema identity differs")
    return schema


def _serializer_self_check() -> None:
    if canonical_bytes({"a": [True, 1, "x"]}) != b'{"a":[true,1,"x"]}\n':
        raise CanonicalControlError("canonical serializer self-check failed")


def _availability(value: str | None) -> Mapping[str, str]:
    if value is None:
        return {"status": "absent"}
    return {"status": "known", "value": value}


def _validate_availability(value: Any, *, git: bool) -> None:
    if value == {"status": "absent"}:
        return
    if not isinstance(value, Mapping) or set(value) != {"status", "value"} or value.get("status") != "known":
        raise CanonicalControlError("authority availability branch is invalid")
    text = value["value"]
    if git:
        if not isinstance(text, str) or len(text) not in {40, 64} or any(char not in "0123456789abcdef" for char in text):
            raise CanonicalControlError("known Git authority is invalid")
    else:
        require_sha256("known identity", text)


def _check_git_authority(evaluation: Phase3CEvaluationInput) -> None:
    authority = evaluation.readiness_material.get("git_authority")
    if not isinstance(authority, Mapping):
        raise InvariantFailure("git_authority")
    if (
        authority.get("repository_authority_identifier")
        != evaluation.repository_authority_identifier
        or authority.get("approved_branch_ref") != evaluation.approved_branch_ref
    ):
        raise InvariantFailure("git_authority")
    try:
        source = evaluation.repository.resolve_commit(
            str(authority.get("source_commit", ""))
        )
        if source != evaluation.prerequisites.source_commit:
            raise InvariantFailure("git_authority")
        entry = evaluation.repository.tree_entry(source, REPOSITORY_AUTHORITY_PATH)
        if entry.object_type != "blob" or entry.mode != "100644":
            raise InvariantFailure("git_authority")
        committed = load_repository_authority_bytes(
            evaluation.repository.object_bytes(
                entry.object_identity, max_bytes=1_048_576
            )
        )
        if (
            committed.repository_authority_identifier
            != evaluation.repository_authority_identifier
            or committed.approved_branch_ref != evaluation.approved_branch_ref
            or committed.git_object_format != evaluation.repository.object_format()
            or evaluation.phase3b_evidence["aggregate"]["source_commit"] != source
            or any(
                item["material"]["source_commit"] != source
                for item in evaluation.phase3b_evidence["workers"]
            )
        ):
            raise InvariantFailure("git_authority")
    except InvariantFailure:
        raise
    except Exception as exc:
        raise InvariantFailure("git_authority") from exc


def _check_semantic_invariant(
    evaluation: Phase3CEvaluationInput, invariant: str
) -> None:
    """Perform dependency-ordered semantic checks before final validation.

    Each section is established at its frozen owner before evaluation may
    advance.  The complete independent Git/evidence validator still runs last
    as defense in depth; it never guesses an earlier owner from diagnostics.
    """

    material = evaluation.readiness_material
    prerequisites = evaluation.prerequisites
    evidence = evaluation.phase3b_evidence
    try:
        adapter = prerequisites.adapter.material
        attempt_authority = prerequisites.attempt_authority
        if invariant == "readiness_specification":
            specification = material["readiness_specification"]
            _check_committed_binding(
                evaluation.repository,
                material["git_authority"]["source_commit"],
                specification,
            )
            if (
                specification["path"] != READINESS_SPECIFICATION_V1_1_PATH
                or specification["revision"]
                != READINESS_SPECIFICATION_V1_1_REVISION
                or specification["sha256"] != READINESS_SPECIFICATION_V1_1_SHA256
                or reconstruct_document_binding_identity(
                    specification, identity_field="specification_identity"
                )
                != specification["specification_identity"]
            ):
                raise InvariantFailure(invariant)
        elif invariant == "schema_registry":
            section = material["schema"]
            declarations = section["declarations"]
            if (
                section["canonical_encoding_revision"]
                != CANONICAL_ENCODING_REVISION
                or section["schema_registry_identifier"]
                != READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER
                or len(declarations) != 29
                or tuple(item["object_kind"] for item in declarations)
                != READINESS_V1_1_SCHEMA_KIND_ORDER
            ):
                raise InvariantFailure(invariant)
            expected = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY
            for declaration in declarations:
                kind = declaration["object_kind"]
                expected_registry, expected_path = READINESS_V1_1_SCHEMA_POLICY[kind]
                if (
                    kind not in expected
                    or declaration["registry_identifier"] != expected_registry
                    or declaration["path"] != expected_path
                    or declaration["schema_id"] != expected[kind][0]
                    or declaration["sha256"] != expected[kind][1]
                ):
                    raise InvariantFailure(invariant)
                _check_committed_binding(
                    evaluation.repository,
                    material["git_authority"]["source_commit"],
                    declaration,
                )
                raw = evaluation.repository.object_bytes(
                    declaration["git_blob_identity"], max_bytes=1_048_576
                )
                schema = parse_json(raw)
                if schema.get("$id") != declaration["schema_id"]:
                    raise InvariantFailure(invariant)
        elif invariant == "experiment":
            experiment = material["experiment"]
            if (
                experiment["experiment_identifier"]
                != evaluation.experiment_identifier
                or experiment["experiment_configuration_identity"]
                != adapter["configuration"]["experiment_configuration_identity"]
                or experiment["canonical_record_path"]
                != str(canonical_readiness_record_path(evaluation.experiment_identifier))
            ):
                raise InvariantFailure(invariant)
        elif invariant == "control_plane":
            components = material["control_plane"]["components"]
            if len(components) != 8:
                raise InvariantFailure(invariant)
            expected_components = _expected_control_components(evaluation)
            if components != expected_components:
                raise InvariantFailure(invariant)
        elif invariant == "source_scopes":
            expected_scopes = []
            for scope in prerequisites.source_scopes:
                item = {
                    "git_mode": scope.git_mode,
                    "git_object_identity": scope.git_object_identity,
                    "nesting": scope.nesting,
                    "repository_path": scope.repository_path,
                    "role": scope.role,
                }
                if scope.nesting == "nested":
                    item["parent_path"] = scope.parent_path
                expected_scopes.append(item)
            expected_scopes.sort(key=lambda item: (item["repository_path"], item["role"]))
            if material["source_scopes"] != expected_scopes:
                raise InvariantFailure(invariant)
        elif invariant in {"protocol", "execution_specification"}:
            section = material[invariant]
            _check_committed_binding(
                evaluation.repository,
                material["git_authority"]["source_commit"],
                section,
            )
            adapter_section = adapter[
                "protocol" if invariant == "protocol" else "execution_specification"
            ]
            if any(
                section[key] != adapter_section[key]
                for key in ("path", "revision", "sha256")
            ) or reconstruct_document_binding_identity(
                section,
                identity_field=(
                    "protocol_identity"
                    if invariant == "protocol"
                    else "specification_identity"
                ),
            ) != section[
                "protocol_identity"
                if invariant == "protocol"
                else "specification_identity"
            ]:
                raise InvariantFailure(invariant)
        elif invariant == "implementation":
            implementation = material["implementation"]
            if implementation != _expected_implementation(evaluation):
                raise InvariantFailure(invariant)
        elif invariant == "execution_profile":
            profile = material["execution_profile"]
            profile_evidence = evidence["profile"]
            if (
                profile != adapter["execution_profile"]
                or set(profile) != {"profile_identity", "profile_name"}
                or profile["profile_identity"] != profile_evidence["profile_identity"]
                or profile["profile_name"] != profile_evidence["profile_name"]
            ):
                raise InvariantFailure(invariant)
        elif invariant == "runtime":
            runtime = material["runtime"]
            if runtime != _expected_runtime(evaluation):
                raise InvariantFailure(invariant)
        elif invariant == "configuration":
            configuration = material["configuration"]
            expected_configuration = {
                "decision_selection_identity": adapter["configuration"][
                    "decision_selection_identity"
                ],
                "evidence_preparation_policy_identity": adapter[
                    "evidence_preparation"
                ]["resource_policy_identity"],
                "experiment_configuration_identity": adapter["configuration"][
                    "experiment_configuration_identity"
                ],
            }
            if configuration != expected_configuration or configuration[
                "evidence_preparation_policy_identity"
            ] != evidence["aggregate"]["capability_policy_identity"]:
                raise InvariantFailure(invariant)
        elif invariant == "external_inputs":
            direct = material["external_inputs"]
            _validate_external_evidence(evaluation)
            expected_external = {
                "declarations": adapter["external_inputs"]["declarations"],
                "input_snapshot_identities": [
                    item["input_snapshot_identity"] for item in evidence["snapshots"]
                ],
                "dataset_validation_evidence_identities": sorted(
                    item["dataset_validation_evidence_identity"]
                    for item in evidence["datasets"]
                ),
                "projection_evidence_identities": sorted(
                    item["projection_evidence_identity"]
                    for item in evidence["projections"]
                ),
            }
            if direct != expected_external:
                raise InvariantFailure(invariant)
        elif invariant == "replay":
            replay = material["replay"]
            replay_evidence = evidence["replay"]
            population = evidence["population"]
            _validate_replay_evidence(evaluation)
            expected_replay = {
                **{
                    key: value
                    for key, value in replay_evidence.items()
                    if key != "schema_version"
                },
                "population_accounting": {
                    key: value
                    for key, value in population.items()
                    if key != "schema_version"
                },
            }
            if replay != expected_replay:
                raise InvariantFailure(invariant)
        elif invariant == "artifacts":
            artifacts = material["artifacts"]
            artifact_evidence = evidence["artifacts"]
            _validate_evidence_object(
                evaluation,
                artifact_evidence,
                schema_kind="artifact-declaration-evidence",
                identity_field="artifact_declaration_evidence_identity",
                domain="orev3:experiment-artifact-declaration-evidence:v1\n",
            )
            from orev3.execution.contract_validation import (
                validate_artifact_declarations,
            )

            reconstructed_artifact_evidence = validate_artifact_declarations(
                adapter["artifacts"]["declarations"],
                profile_name=adapter["execution_profile"]["profile_name"],
            )
            if artifact_evidence != reconstructed_artifact_evidence:
                raise InvariantFailure(invariant)
            expected_artifacts = {
                "artifact_declaration_evidence_identity": artifact_evidence[
                    "artifact_declaration_evidence_identity"
                ],
                "declarations": adapter["artifacts"]["declarations"],
                "dependency_order": artifact_evidence["dependency_order"],
                "output_policy_identity": artifact_evidence["output_policy_identity"],
            }
            if artifacts != expected_artifacts:
                raise InvariantFailure(invariant)
        elif invariant == "outcome_policy":
            outcome = material["outcome_policy"]
            profile_evidence = evidence["profile"]
            _validate_evidence_object(
                evaluation,
                profile_evidence,
                schema_kind="profile-conformance-evidence",
                identity_field="profile_conformance_evidence_identity",
                domain="orev3:experiment-profile-conformance-evidence:v1\n",
            )
            if profile_evidence != prerequisites.profile_contracts.profile_evidence:
                raise InvariantFailure(invariant)
            expected_outcome = {
                key: value
                for key, value in profile_evidence.items()
                if key
                in {
                    "authorization_contract_identity",
                    "outcome_capability",
                    "profile_conformance_evidence_identity",
                    "profile_contract_identities",
                    "profile_identity",
                    "profile_name",
                }
            }
            if outcome != expected_outcome:
                raise InvariantFailure(invariant)
        elif invariant == "validation":
            validation = material["validation"]
            readiness_test = evidence["readiness_test"]
            policy = prerequisites.readiness_test_policy.material
            _validate_validation_evidence(evaluation)
            expected_validation = {
                "additional_test_selectors": readiness_test["additional_selectors"],
                "collected_node_ids": readiness_test["collected_node_ids"],
                "compile_passed": True,
                "evidence_preparation_identity": evidence["aggregate"][
                    "evidence_preparation_identity"
                ],
                "import_passed": True,
                "launch_smoke_selectors": policy["launch_smoke_selectors"],
                "mandatory_test_selectors": readiness_test["mandatory_selectors"],
                "readiness_test_evidence_identity": readiness_test[
                    "readiness_test_evidence_identity"
                ],
                "reconstruction_passed": True,
                "test_policy_identity": policy["policy_identity"],
                "test_results": readiness_test["results"],
            }
            if validation != expected_validation:
                raise InvariantFailure(invariant)
        elif invariant == "attempt_policy":
            attempt = material["attempt_policy"]
            if attempt != _expected_attempt_policy(evaluation):
                raise InvariantFailure(invariant)
    except InvariantFailure:
        raise
    except (KeyError, TypeError, AttributeError) as exc:
        raise InvariantFailure(invariant) from exc
    except (CanonicalControlError, GitAuthorityError) as exc:
        raise InvariantFailure(invariant) from exc


def _check_committed_binding(
    repository: GitRepository, source: str, binding: Mapping[str, Any]
) -> None:
    _check_path_digest(
        repository,
        source,
        binding["path"],
        binding["git_blob_identity"],
        binding["sha256"],
    )
    if "byte_count" in binding:
        entry = repository.tree_entry(source, binding["path"])
        raw = repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
        if binding["byte_count"] != len(raw):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "governed byte count differs",
                repository_path=binding["path"],
            )


def _expected_control_components(
    evaluation: Phase3CEvaluationInput,
) -> list[Mapping[str, Any]]:
    source = evaluation.prerequisites.source_commit
    adapter = evaluation.prerequisites.adapter.material
    authority = evaluation.prerequisites.attempt_authority.material
    binding = evaluation.prerequisites.implementation_binding
    specifications = (
        (
            adapter["adapter_identifier"],
            "adapter",
            binding["implementation"]["path"],
        ),
        (
            evaluation.prerequisites.adapter_registry.material["registry_identifier"],
            "adapter_registry",
            "src/orev3/execution/registry.py",
        ),
        (
            authority["allocator_client_identifier"],
            "allocator_client",
            "src/orev3/execution/attempts.py",
        ),
        (
            authority["allocator_implementation_identifier"],
            "allocator_contract",
            "src/orev3/execution/attempts.py",
        ),
        (
            "canonical_serializer",
            "canonical_serializer",
            "src/orev3/execution/canonical.py",
        ),
        (
            "official_orchestrator",
            "official_orchestrator",
            "src/orev3/execution/orchestrator.py",
        ),
        ("outcome_gate", "outcome_gate", "src/orev3/execution/outcome_gate.py"),
        (
            "readiness_validator",
            "readiness_validator",
            "src/orev3/execution/readiness.py",
        ),
    )
    components: list[Mapping[str, Any]] = []
    for identifier, role, path in specifications:
        entry = evaluation.repository.tree_entry(source, path)
        raw = evaluation.repository.object_bytes(
            entry.object_identity, max_bytes=8 * 1024 * 1024
        )
        if entry.object_type != "blob" or entry.mode != "100644":
            raise InvariantFailure("control_plane")
        component = {
            "component_identifier": identifier,
            "component_identity": "0" * 64,
            "git_object_identity": entry.object_identity,
            "path": path,
            "role": role,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        component["component_identity"] = reconstruct_control_component_identity(
            component
        )
        components.append(component)
    return sorted(components, key=lambda item: item["component_identifier"])


def _expected_implementation(
    evaluation: Phase3CEvaluationInput,
) -> Mapping[str, Any]:
    source = evaluation.prerequisites.source_commit
    adapter = evaluation.prerequisites.adapter.material
    binding = evaluation.prerequisites.implementation_binding
    if reconstruct_protocol_binding_identity(binding) != binding[
        "protocol_binding_identity"
    ]:
        raise InvariantFailure("implementation")
    implementation_path = binding["implementation"]["path"]
    implementation_entry = evaluation.repository.tree_entry(
        source, implementation_path
    )
    implementation_raw = evaluation.repository.object_bytes(
        implementation_entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    binding_path = adapter["implementation_binding_path"]
    binding_entry = evaluation.repository.tree_entry(source, binding_path)
    binding_raw = evaluation.repository.object_bytes(
        binding_entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    expected = {
        "adapter_identifier": adapter["adapter_identifier"],
        "adapter_identity": adapter["adapter_identity"],
        "adapter_registry_identity": evaluation.prerequisites.adapter_registry.material[
            "adapter_registry_identity"
        ],
        "entry_point": binding["entry_point"],
        "implementation_git_blob_identity": implementation_entry.object_identity,
        "implementation_identity": "0" * 64,
        "implementation_path": implementation_path,
        "implementation_sha256": hashlib.sha256(implementation_raw).hexdigest(),
        "protocol_binding_byte_count": len(binding_raw),
        "protocol_binding_git_blob_identity": binding_entry.object_identity,
        "protocol_binding_identity": binding["protocol_binding_identity"],
        "protocol_binding_path": binding_path,
        "protocol_binding_sha256": hashlib.sha256(binding_raw).hexdigest(),
    }
    expected["implementation_identity"] = reconstruct_implementation_identity(
        expected
    )
    return expected


def _expected_runtime(evaluation: Phase3CEvaluationInput) -> Mapping[str, Any]:
    from orev3.execution.runtime import (
        load_offline_artifact_manifest_bytes,
        load_runtime_contract_bytes,
        validate_dependency_lock,
    )

    source = evaluation.prerequisites.source_commit
    runtime_path = "config/research/readiness/runtime-contract-v1.json"
    runtime_entry = evaluation.repository.tree_entry(source, runtime_path)
    runtime_raw = evaluation.repository.object_bytes(
        runtime_entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    runtime_contract = load_runtime_contract_bytes(
        runtime_raw,
        schema=evaluation.prerequisites.schemas["runtime-contract"],
    )
    lock_entry = evaluation.repository.tree_entry(
        source, runtime_contract.dependency_lock_path
    )
    lock_raw = evaluation.repository.object_bytes(
        lock_entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    dependency_lock = validate_dependency_lock(
        lock_raw, expected_sha256=runtime_contract.dependency_lock_sha256
    )
    manifest_entry = evaluation.repository.tree_entry(
        source, runtime_contract.artifact_manifest_path
    )
    manifest_raw = evaluation.repository.object_bytes(
        manifest_entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    manifest = load_offline_artifact_manifest_bytes(
        manifest_raw,
        schema=evaluation.prerequisites.schemas["offline-artifact-manifest"],
        expected_sha256=runtime_contract.artifact_manifest_sha256,
        dependency_lock_sha256=runtime_contract.dependency_lock_sha256,
        dependency_lock=dependency_lock,
    )
    runtime_material = runtime_contract.material
    return {
        "dependency_environment_identity": runtime_material["dependency_lock"][
            "closed_environment_identity"
        ],
        "dependency_lock_git_blob_identity": lock_entry.object_identity,
        "dependency_lock_identity": runtime_material["dependency_lock"][
            "lock_identity"
        ],
        "dependency_lock_path": runtime_contract.dependency_lock_path,
        "dependency_lock_sha256": runtime_contract.dependency_lock_sha256,
        "host_system_identity": runtime_material["host_system"][
            "host_system_identity"
        ],
        "offline_artifact_manifest_git_blob_identity": manifest_entry.object_identity,
        "offline_artifact_manifest_identity": manifest.manifest_identity,
        "offline_artifact_manifest_path": runtime_contract.artifact_manifest_path,
        "offline_artifact_manifest_sha256": runtime_contract.artifact_manifest_sha256,
        "python_implementation": runtime_material["python"]["implementation"],
        "python_version": runtime_material["python"]["version"],
        "runtime_bundle_identity": runtime_material["python"][
            "runtime_bundle_identity"
        ],
        "runtime_contract_byte_count": len(runtime_raw),
        "runtime_contract_git_blob_identity": runtime_entry.object_identity,
        "runtime_contract_identity": runtime_contract.runtime_contract_identity,
        "runtime_contract_path": runtime_path,
        "runtime_contract_sha256": hashlib.sha256(runtime_raw).hexdigest(),
    }


def _validate_evidence_object(
    evaluation: Phase3CEvaluationInput,
    value: Mapping[str, Any],
    *,
    schema_kind: str,
    identity_field: str,
    domain: str,
) -> None:
    validate_json_schema_instance(
        value,
        evaluation.prerequisites.schemas[schema_kind],
        schema_registry={},
    )
    identity_material = dict(value)
    claimed = identity_material.pop(identity_field)
    if domain_identity(domain, identity_material) != claimed:
        raise CanonicalControlError("detached evidence identity does not reconstruct")


def _validate_external_evidence(evaluation: Phase3CEvaluationInput) -> None:
    from orev3.execution.dataset_validation import (
        DATASET_EVIDENCE_DOMAIN,
        PROJECTION_EVIDENCE_DOMAIN,
        dataset_evidence,
    )
    from orev3.execution.external_inputs import INPUT_SNAPSHOT_DOMAIN
    from orev3.execution.phase3b_components import resolve_component

    evidence = evaluation.phase3b_evidence
    for value in evidence["snapshots"]:
        _validate_evidence_object(
            evaluation,
            value,
            schema_kind="immutable-input-snapshot",
            identity_field="input_snapshot_identity",
            domain=INPUT_SNAPSHOT_DOMAIN,
        )
    for value in evidence["datasets"]:
        _validate_evidence_object(
            evaluation,
            value,
            schema_kind="dataset-validation-evidence",
            identity_field="dataset_validation_evidence_identity",
            domain=DATASET_EVIDENCE_DOMAIN,
        )
    for value in evidence["projections"]:
        _validate_evidence_object(
            evaluation,
            value,
            schema_kind="outcome-blind-projection-evidence",
            identity_field="projection_evidence_identity",
            domain=PROJECTION_EVIDENCE_DOMAIN,
        )

    declarations = evaluation.prerequisites.adapter.material["external_inputs"][
        "declarations"
    ]
    snapshots = evidence["snapshots"]
    if len(snapshots) != len(declarations):
        raise CanonicalControlError("snapshot/declaration cardinality differs")
    contracts = {
        item["external_input_identifier"]: item
        for item in evaluation.prerequisites.adapter.material[
            "evidence_preparation"
        ]["dataset_contracts"]
    }
    datasets_by_snapshot = {
        item["input_snapshot_identity"]: item for item in evidence["datasets"]
    }
    projections_by_dataset = {
        item["dataset_identity"]: item for item in evidence["projections"]
    }
    if (
        len(datasets_by_snapshot) != len(evidence["datasets"])
        or len(projections_by_dataset) != len(evidence["projections"])
    ):
        raise CanonicalControlError("external-input evidence bindings are duplicated")

    projection_worker_expected: list[tuple[str, str, tuple[str, ...]]] = []
    for declaration, snapshot in zip(declarations, snapshots, strict=True):
        expected_members = [
            {
                "byte_count": member["byte_count"],
                "logical_member_identifier": member["logical_identifier"],
                "member_order": index,
                "sha256": member["sha256"],
            }
            for index, member in enumerate(declaration["members"])
        ]
        if (
            snapshot["external_input_identifier"]
            != declaration["external_input_identifier"]
            or snapshot["input_kind"] != declaration["input_kind"]
            or snapshot["members"] != expected_members
        ):
            raise CanonicalControlError(
                "immutable snapshot differs from adapter-v3 declaration"
            )
        try:
            dataset = datasets_by_snapshot[snapshot["input_snapshot_identity"]]
            contract = contracts[declaration["external_input_identifier"]]
        except KeyError as exc:
            raise CanonicalControlError(
                "dataset evidence is absent for governed snapshot"
            ) from exc
        parser = resolve_component(
            evaluation.repository,
            evaluation.prerequisites.source_commit,
            declaration["parser_configuration"]["parser_identifier"],
        )
        validator = resolve_component(
            evaluation.repository,
            evaluation.prerequisites.source_commit,
            contract["dataset_validator_identifier"],
        )
        expected_dataset = dataset_evidence(
            external_input_identity=declaration["external_input_identity"],
            snapshot_identity=snapshot["input_snapshot_identity"],
            source_class=contract["source_class"],
            dataset_version=contract["dataset_version"],
            container=contract["container"],
            parser_component_identity=parser.component_identity,
            validator_component_identity=validator.component_identity,
            schema_identity=declaration["schema_identity"],
            protocol_revision=contract["protocol_revision"],
            record_count=dataset["ordered_record_count"],
            record_ordering=contract["record_ordering"],
            candidate_order=contract["candidate_order"],
            projection_required=contract["projection_required"],
            dataset_content_identity=dataset["dataset_content_identity"],
        )
        if dataset != expected_dataset:
            raise CanonicalControlError(
                "dataset evidence first-order authority does not reconstruct"
            )
        projection = projections_by_dataset.get(dataset["dataset_identity"])
        if contract["projection_required"] and projection is None:
            raise CanonicalControlError("required projection evidence is absent")
        if projection is not None:
            projector = resolve_component(
                evaluation.repository,
                evaluation.prerequisites.source_commit,
                contract["projector_identifier"],
            )
            schema_entry = evaluation.repository.tree_entry(
                evaluation.prerequisites.source_commit,
                contract["projection_schema_path"],
            )
            projection_schema = parse_canonical_bytes(
                evaluation.repository.object_bytes(
                    schema_entry.object_identity, max_bytes=1_048_576
                )
            )
            expected_projection_identity = domain_identity(
                PROJECTION_EVIDENCE_DOMAIN,
                {
                    "byte_count": projection["byte_count"],
                    "ordered_record_count": projection["ordered_record_count"],
                    "parser_component_identity": parser.component_identity,
                    "projection_schema_identity": contract[
                        "projection_schema_identity"
                    ],
                    "projector_component_identity": projector.component_identity,
                    "sha256": projection["sha256"],
                },
            )
            if (
                projection["projection_identity"]
                != expected_projection_identity
                or projection["raw_input_snapshot_identity"]
                != snapshot["input_snapshot_identity"]
                or projection["parser_component_identity"]
                != parser.component_identity
                or projection["projector_component_identity"]
                != projector.component_identity
                or projection["projection_schema_identity"]
                != contract["projection_schema_identity"]
                or projection["allowed_fields"]
                != sorted(projection_schema["properties"])
            ):
                raise CanonicalControlError(
                    "projection evidence first-order authority does not reconstruct"
                )
        for invocation in ("projection-1", "projection-2"):
            projection_worker_expected.append(
                (
                    "INPUT_PROJECTOR",
                    invocation,
                    (snapshot["input_snapshot_identity"],),
                )
            )

    if set(datasets_by_snapshot) != {
        item["input_snapshot_identity"] for item in snapshots
    }:
        raise CanonicalControlError(
            "dataset evidence contains an ungoverned snapshot binding"
        )
    required_projection_datasets = {
        dataset["dataset_identity"]
        for dataset in evidence["datasets"]
        if contracts[
            next(
                declaration["external_input_identifier"]
                for declaration, snapshot in zip(
                    declarations, snapshots, strict=True
                )
                if snapshot["input_snapshot_identity"]
                == dataset["input_snapshot_identity"]
            )
        ]["projection_required"]
    }
    if set(projections_by_dataset) != required_projection_datasets:
        raise CanonicalControlError(
            "projection evidence membership differs from governed contracts"
        )
    _validate_worker_authorities(
        evaluation,
        worker_kind="INPUT_PROJECTOR",
        expected_invocations=[
            ("project_canonical_jsonl", invocation, capabilities)
            for _, invocation, capabilities in projection_worker_expected
        ],
    )

    results = _worker_results(evaluation, "INPUT_PROJECTOR")
    for dataset in evidence["datasets"]:
        projection = projections_by_dataset.get(dataset["dataset_identity"])
        matching = [
            result
            for result in results
            if result.get("status") == "evidence_passed"
            and result.get("dataset_content_identity")
            == dataset["dataset_content_identity"]
            and result.get("record_count") == dataset["ordered_record_count"]
            and projection is not None
            and result.get("byte_count") == projection["byte_count"]
            and result.get("sha256") == projection["sha256"]
        ]
        if len(matching) < 2:
            raise CanonicalControlError(
                "dataset/projection authority lacks detached worker reconstruction"
            )


def _validate_replay_evidence(evaluation: Phase3CEvaluationInput) -> None:
    from orev3.execution.replay_preparation import (
        POPULATION_EVIDENCE_DOMAIN,
        REPLAY_EVIDENCE_DOMAIN,
    )
    from orev3.execution.zero_input_phase3b import build_zero_input_replay_evidence

    _validate_evidence_object(
        evaluation,
        evaluation.phase3b_evidence["replay"],
        schema_kind="replay-evidence",
        identity_field="replay_evidence_identity",
        domain=REPLAY_EVIDENCE_DOMAIN,
    )
    _validate_evidence_object(
        evaluation,
        evaluation.phase3b_evidence["population"],
        schema_kind="population-accounting-evidence",
        identity_field="population_accounting_evidence_identity",
        domain=POPULATION_EVIDENCE_DOMAIN,
    )
    decision = evaluation.prerequisites.adapter.material[
        "evidence_preparation"
    ]["decision_selection"]
    replay = evaluation.phase3b_evidence["replay"]
    population = evaluation.phase3b_evidence["population"]
    if (
        population["permitted_exclusion_reasons"]
        != decision["permitted_exclusion_reasons"]
        or replay["decision_selection_identity"]
        != decision["configuration_identity"]
    ):
        raise CanonicalControlError(
            "population/decision-selection authority differs from adapter-v3"
        )
    declarations = evaluation.prerequisites.adapter.material["external_inputs"][
        "declarations"
    ]
    if declarations == []:
        adapter = evaluation.prerequisites.adapter.material
        selector = _resolve_component_identity(
            evaluation, decision["selector_identifier"]
        )
        preparer = _resolve_component_identity(
            evaluation, decision["replay_preparer_identifier"]
        )
        expected_replay, expected_population = build_zero_input_replay_evidence(
            adapter_identity=adapter["adapter_identity"],
            experiment_identifier=evaluation.experiment_identifier,
            profile_identity=adapter["execution_profile"]["profile_identity"],
            source_commit=evaluation.prerequisites.source_commit,
            decision_selection_identity=decision["configuration_identity"],
            selector_component_identity=selector,
            replay_preparer_component_identity=preparer,
            permitted_exclusion_reasons=decision["permitted_exclusion_reasons"],
        )
        if replay != expected_replay or population != expected_population:
            raise CanonicalControlError(
                "zero-input Replay/population authority does not reconstruct"
            )
        _validate_worker_authorities(
            evaluation,
            worker_kind="REPLAY_PREPARATION",
            expected_invocations=[],
        )
        return
    expected = [
        (
            "REPLAY_PREPARATION",
            invocation,
            (replay["projection_identity"],),
        )
        for invocation in ("replay-1", "replay-2")
    ]
    _validate_worker_authorities(
        evaluation,
        worker_kind="REPLAY_PREPARATION",
        expected_invocations=[
            ("reconstruct_replay", invocation, capabilities)
            for _, invocation, capabilities in expected
        ],
    )
    matching = sum(
        result.get("status") == "evidence_passed"
        and result.get("replay_identity") == replay["replay_evidence_identity"]
        and result.get("population_identity")
        == population["population_accounting_evidence_identity"]
        for result in _worker_results(evaluation, "REPLAY_PREPARATION")
    )
    if matching < 2:
        raise CanonicalControlError(
            "Replay/population authority lacks detached worker reconstruction"
        )


def _evidence_policy_authority(
    evaluation: Phase3CEvaluationInput,
) -> Mapping[str, Any]:
    from orev3.execution.evidence_preparation import (
        EVIDENCE_POLICY_PATH,
        load_evidence_policy,
    )

    entry = evaluation.repository.tree_entry(
        evaluation.prerequisites.source_commit, EVIDENCE_POLICY_PATH
    )
    raw = evaluation.repository.object_bytes(
        entry.object_identity, max_bytes=1_048_576
    )
    return load_evidence_policy(
        raw,
        schema=evaluation.prerequisites.schemas["evidence-preparation-policy"],
    )


def _worker_results(
    evaluation: Phase3CEvaluationInput, worker_kind: str
) -> list[Mapping[str, Any]]:
    return [
        bundle["result"]
        for bundle in evaluation.phase3b_evidence["workers"]
        if bundle["material"].get("worker_kind") == worker_kind
    ]


def _resolve_component_identity(
    evaluation: Phase3CEvaluationInput, identifier: str
) -> str:
    from orev3.execution.phase3b_components import resolve_component

    return resolve_component(
        evaluation.repository,
        evaluation.prerequisites.source_commit,
        identifier,
    ).component_identity


def _expected_source_scope_material(
    evaluation: Phase3CEvaluationInput,
) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for scope in evaluation.prerequisites.source_scopes:
        item: dict[str, Any] = {
            "git_mode": scope.git_mode,
            "git_object_identity": scope.git_object_identity,
            "nesting": scope.nesting,
            "repository_path": scope.repository_path,
            "role": scope.role,
        }
        if scope.nesting == "nested":
            item["parent_path"] = scope.parent_path
        result.append(item)
    return sorted(result, key=lambda item: (item["repository_path"], item["role"]))


def _validate_normalized_phase3a_worker(
    evaluation: Phase3CEvaluationInput,
) -> None:
    from orev3.execution.evidence_preparation import (
        PHASE3A_NORMALIZED_CODE_PATHS,
        PHASE3A_NORMALIZED_INVOCATION,
        PHASE3A_NORMALIZED_OUTPUT_REVISION,
        PHASE3A_NORMALIZED_WORKER_REVISION,
    )
    from orev3.execution.preparation import PHASE3A_REMAINING_PREDICATES
    from orev3.execution.runtime import PHASE3B_WORKER_EVIDENCE_DOMAIN

    bundles = [
        bundle
        for bundle in evaluation.phase3b_evidence["workers"]
        if bundle["material"].get("worker_kind") == "PHASE3A_VALIDATOR"
    ]
    if len(bundles) != 1:
        raise CanonicalControlError(
            "prospective Phase-3A worker membership differs"
        )
    bundle = bundles[0]
    worker = bundle["material"]
    result = bundle["result"]
    source = evaluation.prerequisites.source_commit
    runtime = _expected_runtime(evaluation)
    policy = _evidence_policy_authority(evaluation)
    profile = next(
        item
        for item in policy["worker_profiles"]
        if item["worker_kind"] == "PHASE3A_VALIDATOR"
    )
    code_ids = sorted(
        {
            evaluation.repository.tree_entry(source, path).object_identity
            for path in PHASE3A_NORMALIZED_CODE_PATHS
        }
    )
    origins = result.get("dependency_import_origins")
    if not isinstance(origins, list):
        raise CanonicalControlError("normalized dependency origins are malformed")
    runtime_entry = evaluation.repository.tree_entry(
        source, "config/research/readiness/runtime-contract-v1.json"
    )
    runtime_contract = parse_canonical_bytes(
        evaluation.repository.object_bytes(
            runtime_entry.object_identity, max_bytes=8 * 1024 * 1024
        )
    )
    probes = runtime_contract["import_policy"]["dependency_import_probes"]
    if len(origins) != len(probes):
        raise CanonicalControlError("normalized dependency origins differ")
    for origin, probe in zip(origins, probes, strict=True):
        validate_repository_path(origin)
        module_path = probe["module"].replace(".", "/")
        if not (
            origin == module_path + ".py"
            or origin.startswith(module_path + "/")
            or origin.startswith(module_path + ".")
        ):
            raise CanonicalControlError(
                "normalized dependency origin differs from probe order"
            )
    adapter = evaluation.prerequisites.adapter.material
    expected_result = {
        "adapter_identity": adapter["adapter_identity"],
        "adapter_registry_identity": evaluation.prerequisites.adapter_registry.material[
            "adapter_registry_identity"
        ],
        "approved_branch_ref": evaluation.approved_branch_ref,
        "authority_generation": "prospective-v1.1-phase3a",
        "closed_dependency_environment_identity": runtime[
            "dependency_environment_identity"
        ],
        "command": "validate_runtime",
        "dependency_import_origins": origins,
        "evidence_disposition": "PREPARATION_ENVIRONMENT_EVIDENCE_PASSED",
        "network_denial_verified": True,
        "normalized_output_revision": PHASE3A_NORMALIZED_OUTPUT_REVISION,
        "remaining_predicates": list(PHASE3A_REMAINING_PREDICATES),
        "repository_authority_identifier": evaluation.repository_authority_identifier,
        "runtime_contract_identity": runtime["runtime_contract_identity"],
        "source_commit": source,
        "source_scopes": _expected_source_scope_material(evaluation),
        "status": "evidence_passed",
        "worker_code_git_identities": code_ids,
    }
    if result != expected_result:
        raise CanonicalControlError(
            "normalized Phase-3A output authority differs"
        )
    output_identity = domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, expected_result)
    command_identity = domain_identity(
        PHASE3B_WORKER_EVIDENCE_DOMAIN,
        {
            "authority_generation": "prospective-v1.1-phase3a",
            "command": "validate_runtime",
            "invocation_identifier": PHASE3A_NORMALIZED_INVOCATION,
            "worker_kind": "PHASE3A_VALIDATOR",
            "worker_revision": PHASE3A_NORMALIZED_WORKER_REVISION,
        },
    )
    expected_worker = {
        "capability_policy_identity": policy["policy_identity"],
        "closed_dependency_identity": runtime["dependency_environment_identity"],
        "code_capability_git_identities": code_ids,
        "command_identity": command_identity,
        "input_capability_identities": [],
        "invocation_identifier": PHASE3A_NORMALIZED_INVOCATION,
        "output_identity": output_identity,
        "runtime_contract_identity": runtime["runtime_contract_identity"],
        "sandbox_template_identity": profile["sandbox_template_identity"],
        "source_commit": source,
        "successful_worker_disposition": "evidence_passed",
        "worker_kind": "PHASE3A_VALIDATOR",
        "worker_module_git_identity": evaluation.repository.tree_entry(
            source, "src/orev3/execution/preparation_worker.py"
        ).object_identity,
        "worker_revision": PHASE3A_NORMALIZED_WORKER_REVISION,
    }
    expected_identity = domain_identity(
        PHASE3B_WORKER_EVIDENCE_DOMAIN, expected_worker
    )
    if worker != {**expected_worker, "worker_evidence_identity": expected_identity}:
        raise CanonicalControlError(
            "normalized Phase-3A worker authority differs"
        )


def _validate_worker_authorities(
    evaluation: Phase3CEvaluationInput,
    *,
    worker_kind: str,
    expected_invocations: list[tuple[str, str, tuple[str, ...]]],
) -> None:
    from orev3.execution.phase3b_components import WORKER_CODE_CLOSURES
    from orev3.execution.runtime import PHASE3B_WORKER_EVIDENCE_DOMAIN

    policy = _evidence_policy_authority(evaluation)
    profile = next(
        (
            item
            for item in policy["worker_profiles"]
            if item["worker_kind"] == worker_kind
        ),
        None,
    )
    if profile is None:
        raise CanonicalControlError("governed worker profile is absent")
    source = evaluation.prerequisites.source_commit
    module_path = profile["module"]
    module_identity = evaluation.repository.tree_entry(
        source, module_path
    ).object_identity
    expected_code_ids = {
        evaluation.repository.tree_entry(source, path).object_identity
        for path in WORKER_CODE_CLOSURES[worker_kind]
    }
    runtime = _expected_runtime(evaluation)
    expected = Counter()
    for command, invocation, capabilities in expected_invocations:
        command_identity = domain_identity(
            PHASE3B_WORKER_EVIDENCE_DOMAIN,
            {
                "command": command,
                "invocation_identifier": invocation,
                "worker_kind": worker_kind,
            },
        )
        expected[(command_identity, tuple(sorted(capabilities)))] += 1

    actual = Counter()
    expected_fields = {
        "capability_policy_identity",
        "closed_dependency_identity",
        "code_capability_git_identities",
        "command_identity",
        "input_capability_identities",
        "output_identity",
        "runtime_contract_identity",
        "sandbox_template_identity",
        "source_commit",
        "successful_worker_disposition",
        "worker_evidence_identity",
        "worker_kind",
        "worker_module_git_identity",
    }
    for bundle in evaluation.phase3b_evidence["workers"]:
        worker = bundle["material"]
        if worker.get("worker_kind") != worker_kind:
            continue
        result = bundle["result"]
        identity_material = dict(worker)
        claimed = identity_material.pop("worker_evidence_identity")
        if (
            set(bundle) != {"material", "result"}
            or set(worker) != expected_fields
            or domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, identity_material)
            != claimed
            or domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, result)
            != worker["output_identity"]
            or worker["capability_policy_identity"] != policy["policy_identity"]
            or worker["closed_dependency_identity"]
            != runtime["dependency_environment_identity"]
            or worker["runtime_contract_identity"]
            != runtime["runtime_contract_identity"]
            or worker["sandbox_template_identity"]
            != profile["sandbox_template_identity"]
            or worker["source_commit"] != source
            or worker["successful_worker_disposition"] != "evidence_passed"
            or worker["worker_module_git_identity"] != module_identity
        ):
            raise CanonicalControlError(
                "worker authority differs from governed policy"
            )
        code_ids = worker["code_capability_git_identities"]
        capabilities = worker["input_capability_identities"]
        if (
            code_ids != sorted(set(code_ids))
            or not expected_code_ids.issubset(set(code_ids))
            or capabilities != sorted(set(capabilities))
        ):
            raise CanonicalControlError("worker authority is not canonical")
        actual[(worker["command_identity"], tuple(capabilities))] += 1
    if actual != expected:
        raise CanonicalControlError(
            "worker command/input authority differs from governed invocation"
        )


def _validate_validation_evidence(evaluation: Phase3CEvaluationInput) -> None:
    from orev3.execution.evidence_preparation import EVIDENCE_PREPARATION_DOMAIN
    from orev3.execution.phase3b_components import resolve_component
    from orev3.execution.runtime import PHASE3B_WORKER_EVIDENCE_DOMAIN
    from orev3.execution.test_policy import READINESS_TEST_EVIDENCE_DOMAIN

    evidence = evaluation.phase3b_evidence
    _validate_evidence_object(
        evaluation,
        evidence["readiness_test"],
        schema_kind="readiness-test-evidence",
        identity_field="readiness_test_evidence_identity",
        domain=READINESS_TEST_EVIDENCE_DOMAIN,
    )
    _validate_evidence_object(
        evaluation,
        evidence["aggregate"],
        schema_kind="evidence-preparation",
        identity_field="evidence_preparation_identity",
        domain=EVIDENCE_PREPARATION_DOMAIN,
    )
    worker_ids = []
    for bundle in evidence["workers"]:
        if set(bundle) != {"material", "result"}:
            raise CanonicalControlError("worker bundle is not closed")
        worker = bundle["material"]
        identity_material = dict(worker)
        claimed = identity_material.pop("worker_evidence_identity")
        if domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, identity_material) != claimed:
            raise CanonicalControlError("worker evidence identity does not reconstruct")
        worker_ids.append(claimed)
    if worker_ids != sorted(set(worker_ids)) or evidence["aggregate"][
        "worker_evidence_identities"
    ] != worker_ids:
        raise CanonicalControlError("worker evidence collection is not canonical")

    readiness = evidence["readiness_test"]
    policy = evaluation.prerequisites.readiness_test_policy.material
    if (
        readiness["policy_identity"] != policy["policy_identity"]
        or readiness["mandatory_selectors"] != policy["required_selectors"]
        or readiness["additional_selectors"]
        != evaluation.prerequisites.adapter.material["adapter_readiness_tests"]
        or readiness["source_commit"]
        != evaluation.prerequisites.source_commit
        or readiness["environment_identity"]
        != evaluation.readiness_material["runtime"][
            "dependency_environment_identity"
        ]
    ):
        raise CanonicalControlError(
            "readiness-test evidence authority does not reconstruct"
        )
    _validate_worker_authorities(
        evaluation,
        worker_kind="READINESS_TEST",
        expected_invocations=[
            ("collect", "collection-a", ()),
            ("collect", "collection-b", ()),
            ("run_exact", "execution", ()),
        ],
    )
    _validate_normalized_phase3a_worker(evaluation)
    if not any(
        result.get("status") == "evidence_passed"
        and result.get("exit_code") == 0
        and result.get("warning_count") == 0
        and result.get("collected_node_ids") == readiness["collected_node_ids"]
        and result.get("results") == readiness["results"]
        for result in _worker_results(evaluation, "READINESS_TEST")
    ):
        raise CanonicalControlError(
            "readiness-test evidence lacks detached execution authority"
        )

    adapter = evaluation.prerequisites.adapter.material
    source = evaluation.prerequisites.source_commit
    semantic_component_ids: set[str] = set()
    contracts = {
        item["external_input_identifier"]: item
        for item in adapter["evidence_preparation"]["dataset_contracts"]
    }
    for declaration in adapter["external_inputs"]["declarations"]:
        contract = contracts[declaration["external_input_identifier"]]
        for identifier in (
            declaration["parser_configuration"]["parser_identifier"],
            contract["dataset_validator_identifier"],
            contract["projector_identifier"],
        ):
            semantic_component_ids.add(
                resolve_component(
                    evaluation.repository, source, identifier
                ).component_identity
            )
    decision = adapter["evidence_preparation"]["decision_selection"]
    for identifier in (
        decision["selector_identifier"],
        decision["replay_preparer_identifier"],
        "static-profile-validator-v1",
        "static-artifact-validator-v1",
    ):
        semantic_component_ids.add(
            resolve_component(
                evaluation.repository, source, identifier
            ).component_identity
        )
    evidence_policy = _evidence_policy_authority(evaluation)
    aggregate = evidence["aggregate"]
    expected_aggregate = {
        "adapter_identity": adapter["adapter_identity"],
        "artifact_evidence_identity": evidence["artifacts"][
            "artifact_declaration_evidence_identity"
        ],
        "dataset_evidence_identities": sorted(
            item["dataset_validation_evidence_identity"]
            for item in evidence["datasets"]
        ),
        "evidence_preparation_identity": evaluation.readiness_material[
            "validation"
        ]["evidence_preparation_identity"],
        "input_snapshot_identities": sorted(
            item["input_snapshot_identity"] for item in evidence["snapshots"]
        ),
        "population_evidence_identity": evidence["population"][
            "population_accounting_evidence_identity"
        ],
        "profile_evidence_identity": evidence["profile"][
            "profile_conformance_evidence_identity"
        ],
        "projection_evidence_identities": sorted(
            item["projection_evidence_identity"]
            for item in evidence["projections"]
        ),
        "readiness_test_evidence_identity": readiness[
            "readiness_test_evidence_identity"
        ],
        "replay_evidence_identity": evidence["replay"][
            "replay_evidence_identity"
        ],
        "source_commit": source,
        "runtime_contract_identity": evaluation.readiness_material["runtime"][
            "runtime_contract_identity"
        ],
        "dependency_environment_identity": evaluation.readiness_material[
            "runtime"
        ]["dependency_environment_identity"],
        "capability_policy_identity": evidence_policy["policy_identity"],
        "semantic_component_identities": sorted(semantic_component_ids),
        "worker_evidence_identities": worker_ids,
    }
    if any(
        aggregate[key] != expected
        for key, expected in expected_aggregate.items()
    ):
        raise CanonicalControlError(
            "Phase-3B aggregate cross-binding differs from record"
        )


def _expected_attempt_policy(
    evaluation: Phase3CEvaluationInput,
) -> Mapping[str, Any]:
    authority = evaluation.prerequisites.attempt_authority
    material = authority.material
    adapter = evaluation.prerequisites.adapter.material
    artifact_evidence = evaluation.phase3b_evidence["artifacts"]
    entry = evaluation.repository.tree_entry(
        evaluation.prerequisites.source_commit,
        authority.repository_path,
    )
    raw = evaluation.repository.object_bytes(
        entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    return {
        "allocation_authority_identity": authority.allocation_authority_identity,
        "allocator_client_component_identity": authority.allocator_client_component_identity,
        "allocator_contract_identity": authority.allocator_contract_identity,
        "attempt_authority_contract_byte_count": len(raw),
        "attempt_authority_contract_git_blob_identity": entry.object_identity,
        "attempt_authority_contract_path": authority.repository_path,
        "attempt_authority_contract_sha256": authority.sha256,
        "attempt_identity_domain": "orev3:experiment-attempt:v1\n",
        "attempt_identity_schema_identifier": "attempt-identity-material-v1",
        "attempt_output_declaration_identity": adapter[
            "attempt_output_declaration_identity"
        ],
        "collision_policy": material["collision_policy"],
        "control_storage_component_identity": authority.control_storage_component_identity,
        "control_storage_contract_identity": authority.control_storage_contract_identity,
        "output_namespace_identity_policy": material[
            "output_namespace_identity_policy"
        ],
        "output_policy_identity": artifact_evidence["output_policy_identity"],
        "output_policy_revision": "readiness-v1-output-policy",
        "supported_attempt_kinds": material["supported_attempt_kinds"],
    }


def _check_path_digest(
    repository: GitRepository,
    source: str,
    path: str,
    claimed_git_object: str,
    claimed_sha256: str,
) -> None:
    entry = repository.tree_entry(source, path)
    raw = repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
    if (
        entry.object_type != "blob"
        or entry.object_identity != claimed_git_object
        or hashlib.sha256(raw).hexdigest() != claimed_sha256
    ):
        raise GitAuthorityError(
            # The caller's active invariant owns this deterministic mismatch.
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "governed path/digest binding differs",
            repository_path=path,
        )


__all__ = [
    "CANONICAL_RECEIPT_UNAVAILABLE",
    "FAILURE_RECEIPT_DOMAIN",
    "INVARIANT_SERIALIZATION_ORDER",
    "PHASE3C_EVALUATION_ORDER",
    "InvariantFailure",
    "Phase3CDisposition",
    "Phase3CEvaluationInput",
    "Phase3CResult",
    "ReadinessRejected",
    "ReadinessValidated",
    "build_readiness_failure_receipt",
    "evaluate_readiness_candidate",
    "load_readiness_failure_receipt_bytes",
    "reconstruct_failure_receipt_identity",
    "validate_readiness_failure_receipt",
]
