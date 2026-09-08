"""Prospective current-readiness resolution through ``EXECUTION_READY``.

This module performs one fresh approved-ref fetch and reads sealed authority.
It never writes a candidate or seal, creates a launch snapshot, contacts a
control backend, allocates an attempt, or opens scientific outcomes.
"""

from __future__ import annotations

import copy
import hashlib
import os
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    normalize_experiment_identifier,
    domain_identity,
    parse_canonical_bytes,
    parse_json,
    validate_exact_fields,
    validate_json_schema_instance,
)
from orev3.execution.runtime import controller_acquisition_policy
from orev3.execution.filesystem_capability import (
    DescriptorOwner,
    open_pinned_regular,
    verify_opened_regular,
)
from orev3.execution.detached_evidence import (
    DetachedEvidenceError,
    DetachedEvidenceGraph,
    EvidencePublicationHistoryError,
    load_detached_evidence_graph,
    validate_evidence_publication_history,
)
from orev3.execution.git_state import (
    GitAuthorityError,
    GitDiagnosticCode,
    GitRepository,
    ReadinessSealDerivation,
    derive_readiness_seal,
    fetch_remote_head,
)
from orev3.execution.readiness_candidate import (
    CANONICAL_RECEIPT_UNAVAILABLE,
    CURRENT_READINESS_EVALUATION_ORDER,
    INVARIANT_SERIALIZATION_ORDER,
    Phase3CEvaluationInput,
    ReceiptValidationContext,
    _check_semantic_invariant,
    _load_governed_receipt_schema,
    _serializer_self_check,
    build_readiness_failure_receipt,
    load_readiness_failure_receipt_bytes,
)
from orev3.execution.readiness_contracts import (
    READINESS_TEST_POLICY_V2_PATH,
    load_readiness_prerequisite_contracts,
    load_prospective_schemas,
    prospective_schema_policy,
    ProspectiveRegistryGeneration,
)
from orev3.execution.readiness_record import (
    CANONICAL_ENCODING_REVISION,
    READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
    READINESS_V1_1_SCHEMA_POLICY,
    READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER,
    ReadinessRecordV2,
    RepositoryAuthorityV1,
    SourceScopeDeclarationV1,
    canonical_readiness_record_path,
    reconstruct_readiness_identity,
)


PathArgument = str | Path


class CurrentReadinessDisposition(str, Enum):
    EXECUTION_READY = "EXECUTION_READY"
    READINESS_UNRESOLVED_REMOTE = "READINESS_UNRESOLVED_REMOTE"
    READINESS_AMBIGUOUS = "READINESS_AMBIGUOUS"
    READINESS_INVALID_RECORD = "READINESS_INVALID_RECORD"
    READINESS_ORPHANED = "READINESS_ORPHANED"
    SUPERSEDED = "SUPERSEDED"
    READINESS_STALE = "READINESS_STALE"
    READINESS_INPUT_MISMATCH = "READINESS_INPUT_MISMATCH"
    READINESS_BLOCKED_INPUT_UNAVAILABLE = "READINESS_BLOCKED_INPUT_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class CurrentReadinessInput:
    repository: GitRepository
    repository_authority: RepositoryAuthorityV1
    remote_alias: str
    experiment_identifier: str
    current_input_locators: Mapping[str, Sequence[PathArgument]]
    authority_generation: ProspectiveRegistryGeneration = (
        ProspectiveRegistryGeneration.READINESS_V1_1
    )


@dataclass(frozen=True, slots=True)
class ExecutionReady:
    disposition: CurrentReadinessDisposition
    source_commit: str
    readiness_seal_commit: str
    remote_head_commit: str
    readiness_identity: str
    canonical_record_path: str
    readiness_record_blob_identity: str
    record: ReadinessRecordV2


@dataclass(frozen=True, slots=True)
class CurrentReadinessRejected:
    disposition: CurrentReadinessDisposition
    receipt_bytes: bytes
    failure_receipt_identity: str
    receipt: Mapping[str, Any]


CurrentReadinessResult = ExecutionReady | CurrentReadinessRejected | type(
    CANONICAL_RECEIPT_UNAVAILABLE
)


class _InvariantFailure(RuntimeError):
    def __init__(self, invariant: str, disposition: CurrentReadinessDisposition):
        super().__init__(invariant)
        self.invariant = invariant
        self.disposition = disposition


@dataclass(slots=True)
class _State:
    active: str = "git_authority"
    source_commit: str | None = None
    readiness_identity: str | None = None
    remote_head: str | None = None
    record_blob: str | None = None
    record: ReadinessRecordV2 | None = None
    prerequisites: Any | None = None
    seal: ReadinessSealDerivation | None = None
    record_transition_commit: str | None = None
    record_transition_parent: str | None = None
    detached_graph: DetachedEvidenceGraph | None = None
    detached_error: DetachedEvidenceError | None = None
    evidence_publication_orphaned: bool = False
    authority_generation: ProspectiveRegistryGeneration = (
        ProspectiveRegistryGeneration.READINESS_V1_1
    )


def evaluate_current_readiness(
    evaluation: CurrentReadinessInput,
) -> CurrentReadinessResult:
    """Resolve current authority without accepting S, R, H, or record bytes."""

    return _evaluate_current_readiness(evaluation, allow_test_file_remote=False)


def _evaluate_current_readiness_for_test(
    evaluation: CurrentReadinessInput,
) -> CurrentReadinessResult:
    """File-remote seam for committed synthetic repositories only."""

    return _evaluate_current_readiness(evaluation, allow_test_file_remote=True)


def _evaluate_current_readiness(
    evaluation: CurrentReadinessInput, *, allow_test_file_remote: bool
) -> CurrentReadinessResult:
    with controller_acquisition_policy():
        try:
            identifier = normalize_experiment_identifier(evaluation.experiment_identifier)
            if not isinstance(evaluation.repository_authority, RepositoryAuthorityV1):
                raise CanonicalControlError("repository authority is unavailable")
            if not isinstance(evaluation.current_input_locators, Mapping):
                raise CanonicalControlError("current input locator configuration is invalid")
            for values in evaluation.current_input_locators.values():
                if isinstance(values, (str, Path)):
                    values = (values,)
                if not isinstance(values, Sequence) or any(
                    not isinstance(value, (str, Path)) for value in values
                ):
                    raise CanonicalControlError("current input locators must be paths")
            receipt_schema = _load_governed_receipt_schema()
            _serializer_self_check()
        except Exception:
            return CANONICAL_RECEIPT_UNAVAILABLE

        state = _State(authority_generation=evaluation.authority_generation)
        try:
            for invariant in CURRENT_READINESS_EVALUATION_ORDER:
                state.active = invariant
                if invariant == "git_authority":
                    try:
                        if not allow_test_file_remote:
                            _reject_remote_url_rewrite(
                                evaluation.repository, evaluation.remote_alias
                            )
                        remote = fetch_remote_head(
                            evaluation.repository,
                            evaluation.repository_authority,
                            evaluation.remote_alias,
                            allow_test_file=allow_test_file_remote,
                        )
                        state.remote_head = remote.remote_head_commit
                    except GitAuthorityError as exc:
                        disposition = (
                            CurrentReadinessDisposition.READINESS_AMBIGUOUS
                            if exc.code
                            in {
                                GitDiagnosticCode.SEAL_AMBIGUOUS,
                                GitDiagnosticCode.SEAL_COMMIT_SHAPE_INVALID,
                            }
                            else CurrentReadinessDisposition.READINESS_UNRESOLVED_REMOTE
                        )
                        raise _InvariantFailure(invariant, disposition) from exc
                elif invariant == "canonical_readiness_record":
                    _load_current_record(evaluation, identifier, state)
                elif invariant == "schema_registry":
                    _check_schema_registry(evaluation.repository, state)
                elif invariant in CURRENT_READINESS_EVALUATION_ORDER[3:19]:
                    _check_current_semantic(evaluation, identifier, state, invariant)
                elif invariant == "readiness_seal_and_ancestry":
                    assert state.record is not None and state.remote_head is not None
                    try:
                        state.seal = derive_readiness_seal(
                            evaluation.repository,
                            remote_head_commit=state.remote_head,
                            record=state.record,
                            record_blob_identity=str(state.record_blob),
                            validate_governed_source=False,
                        )
                        if state.detached_graph is None:
                            raise GitAuthorityError(
                                GitDiagnosticCode.SEAL_NOT_FOUND,
                                "detached evidence graph is unavailable",
                            )
                        if state.evidence_publication_orphaned:
                            raise EvidencePublicationHistoryError(ambiguous=False)
                        validate_evidence_publication_history(
                            evaluation.repository,
                            graph=state.detached_graph,
                            record=state.record,
                            seal=state.seal,
                            remote_head_commit=state.remote_head,
                        )
                    except EvidencePublicationHistoryError as exc:
                        disposition = (
                            CurrentReadinessDisposition.READINESS_AMBIGUOUS
                            if exc.ambiguous
                            else CurrentReadinessDisposition.READINESS_ORPHANED
                        )
                        raise _InvariantFailure(invariant, disposition) from exc
                    except GitAuthorityError as exc:
                        disposition = _seal_disposition(exc.code)
                        raise _InvariantFailure(invariant, disposition) from exc
                elif invariant == "current_external_inputs":
                    assert state.record is not None
                    _check_current_inputs(
                        state.record.material["external_inputs"]["declarations"],
                        evaluation.current_input_locators,
                    )
            assert state.record is not None
            assert state.seal is not None
            assert state.remote_head is not None
            return ExecutionReady(
                CurrentReadinessDisposition.EXECUTION_READY,
                state.record.source_commit,
                state.seal.readiness_seal_commit,
                state.remote_head,
                state.record.readiness_identity,
                state.record.canonical_record_path,
                str(state.record_blob),
                state.record,
            )
        except _InvariantFailure as failure:
            failed = failure.invariant
            disposition = failure.disposition
        except Exception:
            failed = state.active
            disposition = CurrentReadinessDisposition.READINESS_INVALID_RECORD

        try:
            receipt = build_readiness_failure_receipt(
                experiment_identifier=identifier,
                repository_authority_identifier=(
                    evaluation.repository_authority.repository_authority_identifier
                ),
                approved_branch_ref=evaluation.repository_authority.approved_branch_ref,
                failed_invariant_identifier=failed,
                candidate_source_commit=state.source_commit,
                readiness_identity=state.readiness_identity,
                schema=receipt_schema,
                receipt_class="CURRENT_READINESS",
                current_readiness_disposition=disposition.value,
            )
            receipt_bytes = canonical_bytes(receipt)
            context = ReceiptValidationContext(
                experiment_identifier=identifier,
                repository_authority_identifier=(
                    evaluation.repository_authority.repository_authority_identifier
                ),
                approved_branch_ref=evaluation.repository_authority.approved_branch_ref,
                failed_invariant_identifier=failed,
                candidate_source_commit=state.source_commit,
                readiness_identity=state.readiness_identity,
                receipt_class="CURRENT_READINESS",
                current_readiness_disposition=disposition.value,
            )
            loaded = load_readiness_failure_receipt_bytes(
                receipt_bytes, context=context, schema=receipt_schema
            )
            return CurrentReadinessRejected(
                disposition,
                receipt_bytes,
                loaded["failure_receipt_identity"],
                loaded,
            )
        except Exception:
            return CANONICAL_RECEIPT_UNAVAILABLE


def _load_current_record(
    evaluation: CurrentReadinessInput, identifier: str, state: _State
) -> None:
    assert state.remote_head is not None
    path = str(canonical_readiness_record_path(identifier))
    try:
        entry = evaluation.repository.tree_entry(state.remote_head, path)
        if entry.object_type != "blob" or entry.mode not in {"100644", "100755"}:
            raise CanonicalControlError("canonical readiness path is not a regular blob")
        raw = evaluation.repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
        material = parse_canonical_bytes(raw, max_bytes=8 * 1024 * 1024)
        validate_exact_fields(
            material,
            {
                "readiness_identity", "schema", "experiment", "git_authority",
                "readiness_specification", "control_plane", "source_scopes",
                "protocol", "implementation", "execution_specification",
                "execution_profile", "runtime", "configuration", "external_inputs",
                "replay", "artifacts", "outcome_policy", "validation", "attempt_policy",
            },
            label="sealed readiness record",
        )
        if canonical_bytes(material) != raw:
            raise CanonicalControlError("sealed readiness bytes are noncanonical")
        readiness_identity = reconstruct_readiness_identity(material)
        if material["readiness_identity"] != readiness_identity:
            raise CanonicalControlError("sealed readiness identity differs")
        _validate_record_structure(evaluation.repository, material)
        experiment = material["experiment"]
        authority = material["git_authority"]
        record = ReadinessRecordV2(
            material,
            readiness_identity,
            experiment["experiment_identifier"],
            authority["source_commit"],
            experiment["canonical_record_path"],
            authority["repository_authority_identifier"],
            authority["approved_branch_ref"],
            (),
        )
        if (
            record.experiment_identifier != identifier
            or record.canonical_record_path != path
            or record.repository_authority_identifier
            != evaluation.repository_authority.repository_authority_identifier
            or record.approved_branch_ref
            != evaluation.repository_authority.approved_branch_ref
        ):
            raise CanonicalControlError("sealed readiness authority differs")
    except (CanonicalControlError, GitAuthorityError) as exc:
        raise _InvariantFailure(
            "canonical_readiness_record",
            CurrentReadinessDisposition.READINESS_INVALID_RECORD,
        ) from exc
    state.record = record
    state.record_blob = entry.object_identity
    state.source_commit = record.source_commit
    state.readiness_identity = record.readiness_identity
    try:
        state.prerequisites = load_readiness_prerequisite_contracts(
            evaluation.repository,
            record.source_commit,
            experiment_identifier=identifier,
            requested_attempt_kind="official",
            source_scopes=_normalized_scope_authority(
                evaluation.repository,
                record.source_commit,
                record.material["source_scopes"],
            ),
            generation=evaluation.authority_generation,
        )
    except Exception:
        state.prerequisites = None
    _prepare_detached_evidence(evaluation, state)


def _prepare_detached_evidence(
    evaluation: CurrentReadinessInput, state: _State
) -> None:
    """Discover R's parent and load only fetched Git evidence authority.

    Discovery is deliberately performed before its semantic owners execute;
    it does not mark any invariant passed and stores structured failures for
    the owner selected by the frozen 21-invariant order.
    """

    assert state.remote_head is not None and state.record is not None
    try:
        history = evaluation.repository.first_parent_history(state.remote_head)
        transition: tuple[str, tuple[str, ...]] | None = None
        for commit, parents in history:
            entry = evaluation.repository.optional_tree_entry(
                commit, state.record.canonical_record_path
            )
            if entry is None or entry.object_identity != state.record_blob:
                continue
            parent_entry = (
                evaluation.repository.optional_tree_entry(
                    parents[0], state.record.canonical_record_path
                )
                if parents
                else None
            )
            if parent_entry is None or parent_entry.object_identity != state.record_blob:
                transition = (commit, parents)
                break
        if transition is None:
            return
        state.record_transition_commit = transition[0]
        if transition[1]:
            state.record_transition_parent = transition[1][0]
        if state.record_transition_parent is None:
            return
        try:
            state.detached_graph = load_detached_evidence_graph(
                evaluation.repository, state.record_transition_parent, state.record
            )
        except (DetachedEvidenceError, CanonicalControlError, GitAuthorityError, KeyError, TypeError) as exc:
            governed_error = (
                exc
                if isinstance(exc, DetachedEvidenceError)
                else DetachedEvidenceError(
                    "validation", "DETACHED_EVIDENCE_GRAPH_INVALID"
                )
            )
            # A valid graph introduced only after R is evidence-shaped but not
            # publication authority.  Parse it solely so earlier semantic
            # checks cannot be bypassed; E qualification still fails later.
            try:
                state.detached_graph = load_detached_evidence_graph(
                    evaluation.repository, state.remote_head, state.record
                )
                state.evidence_publication_orphaned = True
            except (DetachedEvidenceError, CanonicalControlError, GitAuthorityError, KeyError, TypeError):
                state.detached_error = governed_error
    except (CanonicalControlError, GitAuthorityError):
        # Strict R/history ownership remains readiness_seal_and_ancestry.
        return


def _normalized_scope_authority(
    repository: GitRepository,
    source_commit: str,
    declarations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Rebuild Git facts without trusting the sealed scope claims.

    This lets earlier owners load their committed prerequisites while the
    ``source_scopes`` invariant remains responsible for comparing the sealed
    vector with independently resolved Git authority.
    """

    normalized: list[dict[str, Any]] = []
    for declaration in declarations:
        item = dict(declaration)
        path = item["repository_path"]
        entry = repository.tree_entry(source_commit, path)
        item["git_mode"] = entry.mode
        item["git_object_identity"] = entry.object_identity
        normalized.append(item)
    return normalized


_STRUCTURAL_SCHEMA_KEYS = {
    "$id",
    "$ref",
    "$schema",
    "additionalProperties",
    "items",
    "maxItems",
    "maximum",
    "minItems",
    "minLength",
    "minimum",
    "pattern",
    "properties",
    "required",
    "type",
    "uniqueItems",
}


def _structural_schema(value: Any) -> Any:
    """Project a governed schema to record-owned shape constraints only."""

    if isinstance(value, list):
        return [_structural_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for key, nested in value.items():
        if key in {"$defs", "properties"}:
            result[key] = {
                name: _structural_schema(item) for name, item in nested.items()
            }
        elif key in _STRUCTURAL_SCHEMA_KEYS:
            result[key] = _structural_schema(nested)
        elif key == "oneOf":
            branches = [_structural_schema(item) for item in nested]
            signatures = [tuple(item.get("required", ())) for item in nested]
            if len(signatures) != len(set(signatures)):
                # Branches with identical shapes need only their exact tag
                # constants retained so JSON Schema can select one branch.
                for original, projected in zip(nested, branches, strict=True):
                    for name, property_schema in original.get("properties", {}).items():
                        if "const" in property_schema:
                            projected.setdefault("properties", {}).setdefault(name, {})[
                                "const"
                            ] = property_schema["const"]
            result["oneOf"] = branches
        elif key in {"anyOf", "allOf"}:
            result[key] = [_structural_schema(item) for item in nested]
    return result


def _validate_record_structure(
    repository: GitRepository, material: Mapping[str, Any]
) -> None:
    source_commit = material["git_authority"]["source_commit"]
    schemas: dict[str, Mapping[str, Any]] = {}
    for kind in ("readiness-record", "source-scope"):
        _, path = READINESS_V1_1_SCHEMA_POLICY[kind]
        expected_id, expected_digest = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind]
        entry = repository.tree_entry(source_commit, path)
        raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            # Actual schema authority is owned by schema_registry.  This
            # projection never turns a missing/substituted schema into record
            # authority; the later owner will reject it deterministically.
            return
        schema = parse_json(raw, max_bytes=1_048_576)
        if schema.get("$id") != expected_id:
            return
        schemas[kind] = _structural_schema(schema)
    validate_json_schema_instance(
        material,
        schemas["readiness-record"],
        schema_registry={
            READINESS_V1_1_SCHEMA_POLICY["source-scope"][1].rsplit("/", 1)[-1]: schemas[
                "source-scope"
            ]
        },
    )


def _reject_remote_url_rewrite(repository: GitRepository, remote_alias: str) -> None:
    """Prevent production authority from being redirected by Git config."""

    remote = repository.run(
        "config", "--get-all", f"remote.{remote_alias}.url", check=False
    )
    if remote.returncode != 0:
        return
    urls = remote.stdout.decode("utf-8", errors="strict").splitlines()
    rewrites = repository.run(
        "config", "--get-regexp", r"^url\..*\.insteadof$", check=False
    )
    if rewrites.returncode not in {0, 1}:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "Git URL rewrite authority cannot be established",
        )
    for line in rewrites.stdout.decode("utf-8", errors="strict").splitlines():
        _, separator, replaced_prefix = line.partition(" ")
        if separator and any(url.startswith(replaced_prefix) for url in urls):
            raise GitAuthorityError(
                GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
                "authorized remote endpoint is subject to a Git URL rewrite",
            )


def _check_schema_registry(repository: GitRepository, state: _State) -> None:
    assert state.record is not None
    try:
        schemas = load_prospective_schemas(
            repository,
            state.record.source_commit,
            state.authority_generation,
        )
        selected_policy, selected_documents, selected_count = prospective_schema_policy(
            state.authority_generation
        )
        declarations = state.record.material["schema"]["declarations"]
        schema_section = state.record.material["schema"]
        if (
            schema_section["canonical_encoding_revision"]
            != CANONICAL_ENCODING_REVISION
            or schema_section["schema_registry_identifier"]
            != READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER
            or len(declarations) != selected_count
        ):
            raise CanonicalControlError("sealed schema registry cardinality differs")
        for declaration in declarations:
            kind = declaration["object_kind"]
            registry_identifier, path = selected_policy[kind]
            expected_id, expected_digest = selected_documents[kind]
            entry = repository.tree_entry(state.record.source_commit, path)
            raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
            if declaration != {
                "byte_count": len(raw),
                "git_blob_identity": entry.object_identity,
                "object_kind": kind,
                "path": path,
                "registry_identifier": registry_identifier,
                "schema_id": expected_id,
                "sha256": expected_digest,
            } or schemas[kind].get("$id") != expected_id:
                raise CanonicalControlError("sealed schema declaration differs")
    except Exception as exc:
        raise _InvariantFailure(
            "schema_registry", CurrentReadinessDisposition.READINESS_INVALID_RECORD
        ) from exc
    _reject_drift(repository, state, "schema_registry", [item["path"] for item in declarations])


def _check_current_semantic(
    evaluation: CurrentReadinessInput,
    identifier: str,
    state: _State,
    invariant: str,
) -> None:
    assert state.record is not None
    if state.prerequisites is None:
        raise _InvariantFailure(invariant, CurrentReadinessDisposition.READINESS_INVALID_RECORD)
    material = copy.deepcopy(state.record.material)
    material.pop("readiness_identity")
    adapter = state.prerequisites.adapter.material
    direct = state.record.material
    evidence_owners = {
        "external_inputs",
        "replay",
        "artifacts",
        "outcome_policy",
        "validation",
    }
    if invariant in evidence_owners:
        if state.detached_error is not None and state.detached_error.owner == invariant:
            raise _InvariantFailure(
                invariant, CurrentReadinessDisposition.READINESS_INVALID_RECORD
            ) from state.detached_error
        if state.detached_graph is not None:
            synthetic = Phase3CEvaluationInput(
                repository=evaluation.repository,
                experiment_identifier=identifier,
                repository_authority_identifier=state.record.repository_authority_identifier,
                approved_branch_ref=state.record.approved_branch_ref,
                readiness_material=material,
                prerequisites=state.prerequisites,
                phase3b_evidence=state.detached_graph.evidence,
            )
            try:
                _check_semantic_invariant(synthetic, invariant)
            except Exception as exc:
                raise _InvariantFailure(
                    invariant, CurrentReadinessDisposition.READINESS_INVALID_RECORD
                ) from exc
            _reject_drift(
                evaluation.repository,
                state,
                invariant,
                _owned_paths(state.record, state.prerequisites, invariant),
            )
            return
    try:
        if invariant == "execution_profile":
            if direct["execution_profile"] != adapter["execution_profile"]:
                raise CanonicalControlError("sealed execution profile differs")
            _reject_drift(evaluation.repository, state, invariant, [])
            return
        if invariant == "configuration":
            expected = {
                "decision_selection_identity": adapter["configuration"]["decision_selection_identity"],
                "evidence_preparation_policy_identity": adapter["evidence_preparation"]["resource_policy_identity"],
                "experiment_configuration_identity": adapter["configuration"]["experiment_configuration_identity"],
            }
            if direct["configuration"] != expected:
                raise CanonicalControlError("sealed configuration differs")
            return
        if invariant == "external_inputs":
            if direct["external_inputs"]["declarations"] != adapter["external_inputs"]["declarations"]:
                raise CanonicalControlError("sealed external-input declarations differ")
            return
        if invariant == "replay":
            from orev3.execution.phase3b_components import resolve_component

            decision = adapter["evidence_preparation"]["decision_selection"]
            selector = resolve_component(
                evaluation.repository, state.record.source_commit, decision["selector_identifier"]
            )
            preparer = resolve_component(
                evaluation.repository, state.record.source_commit, decision["replay_preparer_identifier"]
            )
            replay = direct["replay"]
            if (
                replay["decision_selection_identity"] != decision["configuration_identity"]
                or replay["selector_component_identity"] != selector.component_identity
                or replay["replay_preparer_component_identity"] != preparer.component_identity
            ):
                raise CanonicalControlError("sealed Replay authority differs")
            _reject_drift(
                evaluation.repository, state, invariant, [selector.path, preparer.path]
            )
            return
        if invariant == "artifacts":
            from orev3.execution.contract_validation import validate_artifact_declarations

            evidence = validate_artifact_declarations(
                adapter["artifacts"]["declarations"],
                profile_name=adapter["execution_profile"]["profile_name"],
            )
            expected = {
                "artifact_declaration_evidence_identity": evidence[
                    "artifact_declaration_evidence_identity"
                ],
                "declarations": adapter["artifacts"]["declarations"],
                "dependency_order": evidence["dependency_order"],
                "output_policy_identity": evidence["output_policy_identity"],
            }
            if direct["artifacts"] != expected:
                raise CanonicalControlError("sealed artifact authority differs")
            return
        if invariant == "outcome_policy":
            profile = state.prerequisites.profile_contracts.profile_evidence
            expected = {
                key: value
                for key, value in profile.items()
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
            if direct["outcome_policy"] != expected:
                raise CanonicalControlError("sealed outcome-policy authority differs")
            return
        if invariant == "validation":
            from orev3.execution.test_policy import READINESS_TEST_EVIDENCE_DOMAIN

            policy = state.prerequisites.readiness_test_policy.material
            validation = direct["validation"]
            evidence_material = {
                "additional_selectors": validation["additional_test_selectors"],
                "collected_node_ids": validation["collected_node_ids"],
                "environment_identity": direct["runtime"]["dependency_environment_identity"],
                "mandatory_selectors": validation["mandatory_test_selectors"],
                "policy_identity": validation["test_policy_identity"],
                "results": validation["test_results"],
                "schema_version": 1,
                "source_commit": state.record.source_commit,
            }
            if (
                validation["test_policy_identity"] != policy["policy_identity"]
                or validation["mandatory_test_selectors"] != policy["required_selectors"]
                or validation["launch_smoke_selectors"] != policy["launch_smoke_selectors"]
                or validation["readiness_test_evidence_identity"]
                != domain_identity(READINESS_TEST_EVIDENCE_DOMAIN, evidence_material)
            ):
                raise CanonicalControlError("sealed validation authority differs")
            _reject_drift(
                evaluation.repository,
                state,
                invariant,
                _owned_paths(state.record, state.prerequisites, invariant),
            )
            return
    except (CanonicalControlError, GitAuthorityError, KeyError, TypeError) as exc:
        raise _InvariantFailure(
            invariant, CurrentReadinessDisposition.READINESS_INVALID_RECORD
        ) from exc
    synthetic = Phase3CEvaluationInput(
        repository=evaluation.repository,
        experiment_identifier=identifier,
        repository_authority_identifier=state.record.repository_authority_identifier,
        approved_branch_ref=state.record.approved_branch_ref,
        readiness_material=material,
        prerequisites=state.prerequisites,
        phase3b_evidence=_sealed_evidence_view(state.record, state.prerequisites),
    )
    try:
        _check_semantic_invariant(synthetic, invariant)
    except Exception as exc:
        raise _InvariantFailure(
            invariant, CurrentReadinessDisposition.READINESS_INVALID_RECORD
        ) from exc
    if invariant == "source_scopes":
        try:
            state.record = replace(
                state.record,
                source_scopes=tuple(
                    SourceScopeDeclarationV1.from_mapping(item)
                    for item in state.record.material["source_scopes"]
                ),
            )
        except Exception as exc:
            raise _InvariantFailure(
                invariant, CurrentReadinessDisposition.READINESS_INVALID_RECORD
            ) from exc
    _reject_drift(
        evaluation.repository,
        state,
        invariant,
        _owned_paths(state.record, state.prerequisites, invariant),
    )


def _sealed_evidence_view(record: ReadinessRecordV2, prerequisites: Any) -> Mapping[str, Any]:
    """Reconstruct the non-executing evidence view encoded by the sealed record.

    Current readiness does not rerun Phase 3B.  It rebuilds the exact first-order
    objects that the record retained and uses committed prerequisite authority
    for the independently reconstructable profile/artifact/policy portions.
    """

    direct = record.material
    replay = {
        key: value for key, value in direct["replay"].items() if key != "population_accounting"
    }
    replay["schema_version"] = 2
    population = {**direct["replay"]["population_accounting"], "schema_version": 2}
    outcome = direct["outcome_policy"]
    profile = dict(prerequisites.profile_contracts.profile_evidence)
    artifacts_direct = direct["artifacts"]
    artifacts = {
        "artifact_declaration_evidence_identity": artifacts_direct[
            "artifact_declaration_evidence_identity"
        ],
        "declarations": artifacts_direct["declarations"],
        "dependency_order": artifacts_direct["dependency_order"],
        "output_policy_identity": artifacts_direct["output_policy_identity"],
        "schema_version": 1,
    }
    validation = direct["validation"]
    readiness_test = {
        "additional_selectors": validation["additional_test_selectors"],
        "collected_node_ids": validation["collected_node_ids"],
        "mandatory_selectors": validation["mandatory_test_selectors"],
        "readiness_test_evidence_identity": validation[
            "readiness_test_evidence_identity"
        ],
        "results": validation["test_results"],
        "schema_version": 1,
    }
    aggregate = {
        "capability_policy_identity": direct["configuration"][
            "evidence_preparation_policy_identity"
        ],
        "evidence_preparation_identity": validation["evidence_preparation_identity"],
    }
    # Detached worker and subordinate evidence are intentionally not rerun.
    # Empty vectors make any accidental worker/evidence reconstruction fail
    # closed; current checks below use only sealed direct authority.
    return {
        "aggregate": aggregate,
        "artifacts": artifacts,
        "datasets": [],
        "population": population,
        "profile": profile if profile else outcome,
        "projections": [],
        "readiness_test": readiness_test,
        "replay": replay,
        "snapshots": [],
        "workers": [],
    }


def _owned_paths(record: ReadinessRecordV2, prerequisites: Any, invariant: str) -> list[str]:
    material = record.material
    if invariant == "readiness_specification":
        return [material[invariant]["path"]]
    if invariant == "control_plane":
        return [item["path"] for item in material["control_plane"]["components"]]
    if invariant == "protocol":
        return [material["protocol"]["path"]]
    if invariant == "implementation":
        return [material["implementation"][key] for key in ("implementation_path", "protocol_binding_path")]
    if invariant == "execution_specification":
        return [material[invariant]["path"]]
    if invariant == "runtime":
        return [material["runtime"][key] for key in ("dependency_lock_path", "offline_artifact_manifest_path", "runtime_contract_path")]
    if invariant == "validation":
        policy = prerequisites.readiness_test_policy.material
        return [READINESS_TEST_POLICY_V2_PATH, *(item.split("::", 1)[0] for item in policy["required_selectors"]), *policy["collection_affecting_paths"]]
    if invariant == "attempt_policy":
        return [material["attempt_policy"]["attempt_authority_contract_path"]]
    return []


def _reject_drift(
    repository: GitRepository, state: _State, invariant: str, paths: Sequence[str]
) -> None:
    assert state.record is not None and state.remote_head is not None
    for path in dict.fromkeys(paths):
        try:
            at_source = repository.tree_entry(state.record.source_commit, path)
            at_head = repository.tree_entry(state.remote_head, path)
        except GitAuthorityError as exc:
            raise _InvariantFailure(
                invariant, CurrentReadinessDisposition.READINESS_STALE
            ) from exc
        if (
            at_source.object_identity != at_head.object_identity
            or at_source.mode != at_head.mode
            or at_source.object_type != at_head.object_type
        ):
            raise _InvariantFailure(invariant, CurrentReadinessDisposition.READINESS_STALE)


def _check_current_inputs(
    declarations: Sequence[Mapping[str, Any]],
    locators: Mapping[str, Sequence[PathArgument]],
) -> None:
    with DescriptorOwner("INPUT_UNSAFE_TYPE") as owner:
        expected_identifiers = [item["external_input_identifier"] for item in declarations]
        if set(locators) != set(expected_identifiers):
            missing = set(expected_identifiers) - set(locators)
            disposition = (
                CurrentReadinessDisposition.READINESS_BLOCKED_INPUT_UNAVAILABLE
                if missing
                else CurrentReadinessDisposition.READINESS_INPUT_MISMATCH
            )
            raise _InvariantFailure("current_external_inputs", disposition)
        for declaration in declarations:
            supplied = locators[declaration["external_input_identifier"]]
            if isinstance(supplied, (str, Path)):
                supplied = (supplied,)
            if not isinstance(supplied, Sequence) or len(supplied) != len(declaration["members"]):
                raise _InvariantFailure(
                    "current_external_inputs",
                    CurrentReadinessDisposition.READINESS_INPUT_MISMATCH,
                )
            for member, path in zip(declaration["members"], supplied, strict=True):
                try:
                    descriptor, _ = open_pinned_regular(
                        path, owner=owner,
                        error_code="INPUT_UNSAFE_TYPE",
                        missing_error_code="INPUT_UNAVAILABLE",
                        nonblocking=True,
                    )
                except CanonicalControlError as exc:
                    raise _InvariantFailure(
                        "current_external_inputs",
                        CurrentReadinessDisposition.READINESS_BLOCKED_INPUT_UNAVAILABLE,
                    ) from exc
                try:
                    verify_opened_regular(
                        descriptor,
                        expected_size=member["byte_count"],
                        expected_sha256=member["sha256"],
                        limit=max(member["byte_count"], 1),
                        error_code="INPUT_MISMATCH",
                        mutation_error_code="INPUT_MUTATED",
                    )
                except CanonicalControlError as exc:
                    raise _InvariantFailure(
                        "current_external_inputs",
                        CurrentReadinessDisposition.READINESS_INPUT_MISMATCH,
                    ) from exc
                finally:
                    owner.close_one(descriptor)
                    owner.check()


def _seal_disposition(code: GitDiagnosticCode) -> CurrentReadinessDisposition:
    if code in {GitDiagnosticCode.SEAL_AMBIGUOUS, GitDiagnosticCode.SEAL_COMMIT_SHAPE_INVALID}:
        return CurrentReadinessDisposition.READINESS_AMBIGUOUS
    if code == GitDiagnosticCode.SOURCE_STALE:
        return CurrentReadinessDisposition.READINESS_STALE
    return CurrentReadinessDisposition.READINESS_ORPHANED


def assess_historical_seal(
    result: ExecutionReady, queried_seal_commit: str
) -> CurrentReadinessDisposition:
    """Status-only historical query; never supplies authority to evaluation."""

    if queried_seal_commit != result.readiness_seal_commit:
        return CurrentReadinessDisposition.SUPERSEDED
    return CurrentReadinessDisposition.EXECUTION_READY


def evaluate_historical_readiness_status(
    evaluation: CurrentReadinessInput, queried_seal_commit: str
) -> CurrentReadinessResult:
    """Resolve current authority, then assess a non-authoritative historical query."""

    current = evaluate_current_readiness(evaluation)
    if not isinstance(current, ExecutionReady) or queried_seal_commit == current.readiness_seal_commit:
        return current
    try:
        schema = _load_governed_receipt_schema()
        receipt = build_readiness_failure_receipt(
            experiment_identifier=evaluation.experiment_identifier,
            repository_authority_identifier=evaluation.repository_authority.repository_authority_identifier,
            approved_branch_ref=evaluation.repository_authority.approved_branch_ref,
            failed_invariant_identifier="readiness_seal_and_ancestry",
            candidate_source_commit=current.source_commit,
            readiness_identity=current.readiness_identity,
            schema=schema,
            receipt_class="CURRENT_READINESS",
            current_readiness_disposition=CurrentReadinessDisposition.SUPERSEDED.value,
        )
        raw = canonical_bytes(receipt)
        context = ReceiptValidationContext(
            evaluation.experiment_identifier,
            evaluation.repository_authority.repository_authority_identifier,
            evaluation.repository_authority.approved_branch_ref,
            "readiness_seal_and_ancestry",
            current.source_commit,
            current.readiness_identity,
            "CURRENT_READINESS",
            CurrentReadinessDisposition.SUPERSEDED.value,
        )
        loaded = load_readiness_failure_receipt_bytes(raw, context=context, schema=schema)
        return CurrentReadinessRejected(
            CurrentReadinessDisposition.SUPERSEDED,
            raw,
            loaded["failure_receipt_identity"],
            loaded,
        )
    except Exception:
        return CANONICAL_RECEIPT_UNAVAILABLE


__all__ = [
    "CurrentReadinessDisposition",
    "CurrentReadinessInput",
    "CurrentReadinessRejected",
    "ExecutionReady",
    "assess_historical_seal",
    "evaluate_historical_readiness_status",
    "evaluate_current_readiness",
]
