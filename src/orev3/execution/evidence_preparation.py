"""Non-executing Phase-3B evidence aggregation and bounded result types."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import CanonicalControlError, domain_identity, parse_canonical_bytes, parse_json, validate_json_schema_instance, validate_repository_path
from orev3.execution.git_state import GitAuthorityError, GitRepository, RequiredCommittedObject, SourceCandidateRequirements, fetch_remote_head, resolve_source_candidate
from orev3.execution.preparation import DEFAULT_ARTIFACT_STORE, PHASE3A_REMAINING_PREDICATES, REPOSITORY_AUTHORITY_PATH, PreparationAuthorityGeneration, _collect_preparation_environment_evidence, _discover_requirements, _scope_mapping
from orev3.execution.readiness import load_repository_authority
from orev3.execution.readiness_record import (
    PHASE3B_SCHEMA_DOCUMENT_POLICY,
    PHASE3B_SCHEMA_POLICY,
    PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY,
    PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
)
from orev3.execution.readiness_record import SourceScopeDeclarationV1
from orev3.execution.runtime import PHASE3A_SANDBOX_TEMPLATE_IDENTITY, PHASE3B_PROFILE_RENDERER_DOMAIN, PHASE3B_PROFILE_RENDERER_IDENTITY, PHASE3B_WORKER_EVIDENCE_DOMAIN, DetachedSource, Phase3BWorkerEvidence, run_phase3b_controller, run_phase3b_worker

EVIDENCE_PREPARATION_DOMAIN = "orev3:experiment-evidence-preparation:v1\n"
EVIDENCE_POLICY_DOMAIN = "orev3:readiness-evidence-preparation-policy:v1\n"
EVIDENCE_POLICY_PATH = "config/research/readiness/evidence-preparation-policy-v1.json"
PHASE3A_NORMALIZED_OUTPUT_REVISION = "phase3a-normalized-output-v1"
PHASE3A_NORMALIZED_WORKER_REVISION = "phase3a-normalized-worker-v1"
PHASE3A_NORMALIZED_INVOCATION = "phase3a-validate-runtime"
PHASE3A_NORMALIZED_CODE_PATHS = (
    "src/orev3/execution/canonical.py",
    "src/orev3/execution/git_state.py",
    "src/orev3/execution/preparation.py",
    "src/orev3/execution/preparation_worker.py",
    "src/orev3/execution/readiness_record.py",
    "src/orev3/execution/registry.py",
    "src/orev3/execution/runtime.py",
)
PHASE3B_REMAINING_PREDICATES = (
    "attempt_allocation_and_control_storage",
    "candidate_readiness_record_generation",
    "canonical_readiness_path_materialization",
    "current_remote_backed_readiness",
    "launch_smoke_tests",
    "launch_time_input_snapshots",
    "ranking_freeze_authorization_and_evaluation",
    "readiness_identity",
    "readiness_validated",
    "scientific_and_control_manifests",
    "seal_commit_R",
)
PHASE3B_CONTROL_PATHS = (
    "src/orev3/execution/contract_validation.py",
    "src/orev3/execution/dataset_validation.py",
    "src/orev3/execution/evidence_preparation.py",
    "src/orev3/execution/evidence_preparation_worker.py",
    "src/orev3/execution/external_inputs.py",
    "src/orev3/execution/filesystem_capability.py",
    "src/orev3/execution/input_projection_worker.py",
    "src/orev3/execution/phase3b_components.py",
    "src/orev3/execution/projection.py",
    "src/orev3/execution/readiness_test_worker.py",
    "src/orev3/execution/replay_preparation.py",
    "src/orev3/execution/replay_preparation_worker.py",
    "src/orev3/execution/test_policy.py",
    "src/orev3/execution/zero_input_phase3b.py",
)


class EvidencePreparationDisposition(str, Enum):
    EVIDENCE_PREPARATION_VALIDATED = "EVIDENCE_PREPARATION_VALIDATED"
    EVIDENCE_PREPARATION_REJECTED = "EVIDENCE_PREPARATION_REJECTED"


class EvidenceAuthorityGeneration(str, Enum):
    HISTORICAL = "historical-phase3b-v1"
    PROSPECTIVE_V1_1 = "prospective-v1.1-phase3b"


class EvidencePreparationFailureCode(str, Enum):
    ARTIFACT_CONTRACT_INVALID = "ARTIFACT_CONTRACT_INVALID"
    INPUT_MISMATCH = "INPUT_MISMATCH"
    INPUT_MUTATED = "INPUT_MUTATED"
    INPUT_SCHEMA_MISMATCH = "INPUT_SCHEMA_MISMATCH"
    INPUT_UNAVAILABLE = "INPUT_UNAVAILABLE"
    INPUT_UNSAFE_TYPE = "INPUT_UNSAFE_TYPE"
    OUTCOME_ISOLATION_VIOLATION = "OUTCOME_ISOLATION_VIOLATION"
    POPULATION_MISMATCH = "POPULATION_MISMATCH"
    PROFILE_POLICY_MISMATCH = "PROFILE_POLICY_MISMATCH"
    PROJECTION_INVALID = "PROJECTION_INVALID"
    READINESS_TEST_FAILED = "READINESS_TEST_FAILED"
    REPLAY_IDENTITY_MISMATCH = "REPLAY_IDENTITY_MISMATCH"
    REPLAY_NONDETERMINISTIC = "REPLAY_NONDETERMINISTIC"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    TEST_COLLECTION_MISMATCH = "TEST_COLLECTION_MISMATCH"
    WORKER_OUTPUT_LIMIT_EXCEEDED = "WORKER_OUTPUT_LIMIT_EXCEEDED"
    WORKER_TIMEOUT = "WORKER_TIMEOUT"
    EVIDENCE_PREPARATION_INTERNAL_REJECTED = "EVIDENCE_PREPARATION_INTERNAL_REJECTED"


@dataclass(frozen=True, slots=True)
class EvidencePreparationWorkerEvidence:
    component_identities: Mapping[str, Any]
    aggregate_material: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class EvidencePreparationAssessment:
    disposition: EvidencePreparationDisposition
    remaining_predicates: tuple[str, ...]
    diagnostics: tuple[str, ...]
    evidence_preparation_identity: str = ""
    evidence: Mapping[str, Any] | None = None


def reconstruct_prospective_phase3a_worker(
    *,
    repository: GitRepository,
    source_commit: str,
    phase3a_result: Mapping[str, Any],
    approved_branch_ref: str,
    repository_authority_identifier: str,
    source_scopes: Sequence[Mapping[str, Any]],
    capability_policy_identity: str,
    sandbox_template_identity: str,
) -> Phase3BWorkerEvidence:
    """Normalize prospective Phase-3A worker authority without physical paths."""

    allowed_result_fields = {
        "adapter_identity",
        "adapter_registry_identity",
        "closed_dependency_environment_identity",
        "closed_dependency_root_path",
        "command",
        "dependency_import_origins",
        "evidence_disposition",
        "network_denial_verified",
        "project_control_plane_origins",
        "remaining_predicates",
        "runtime_contract_identity",
        "source_commit",
        "status",
    }
    if set(phase3a_result) != allowed_result_fields:
        raise CanonicalControlError("prospective Phase-3A result shape differs")
    if (
        phase3a_result["source_commit"] != source_commit
        or phase3a_result["command"] != "validate_runtime"
        or phase3a_result["evidence_disposition"]
        != "PREPARATION_ENVIRONMENT_EVIDENCE_PASSED"
        or phase3a_result["network_denial_verified"] is not True
        or phase3a_result["status"] != "evidence_passed"
    ):
        raise CanonicalControlError("prospective Phase-3A result did not pass")
    expected_predicates = list(PHASE3A_REMAINING_PREDICATES)
    if phase3a_result["remaining_predicates"] != expected_predicates:
        raise CanonicalControlError("prospective Phase-3A predicates differ")
    import_origins = phase3a_result["dependency_import_origins"]
    if not isinstance(import_origins, list):
        raise CanonicalControlError("dependency import origins are malformed")
    for origin in import_origins:
        validate_repository_path(origin)
    scopes = [dict(item) for item in source_scopes]
    if scopes != sorted(scopes, key=lambda item: (item["repository_path"], item["role"])):
        raise CanonicalControlError("prospective Phase-3A scopes are not canonical")
    scope_paths = [item["repository_path"] for item in scopes]
    if len(scope_paths) != len(set(scope_paths)):
        raise CanonicalControlError("prospective Phase-3A scope path is duplicated")
    required_origins = set(PHASE3A_NORMALIZED_CODE_PATHS)
    if not required_origins.issubset(
        set(phase3a_result["project_control_plane_origins"])
    ):
        raise CanonicalControlError("prospective Phase-3A worker origins are incomplete")
    code_ids = sorted(
        {
            repository.tree_entry(source_commit, path).object_identity
            for path in PHASE3A_NORMALIZED_CODE_PATHS
        }
    )
    output_material = {
        "adapter_identity": phase3a_result["adapter_identity"],
        "adapter_registry_identity": phase3a_result["adapter_registry_identity"],
        "approved_branch_ref": approved_branch_ref,
        "authority_generation": PreparationAuthorityGeneration.PROSPECTIVE_V1_1.value,
        "closed_dependency_environment_identity": phase3a_result[
            "closed_dependency_environment_identity"
        ],
        "command": "validate_runtime",
        "dependency_import_origins": list(import_origins),
        "evidence_disposition": "PREPARATION_ENVIRONMENT_EVIDENCE_PASSED",
        "network_denial_verified": True,
        "normalized_output_revision": PHASE3A_NORMALIZED_OUTPUT_REVISION,
        "remaining_predicates": expected_predicates,
        "repository_authority_identifier": repository_authority_identifier,
        "runtime_contract_identity": phase3a_result["runtime_contract_identity"],
        "source_commit": source_commit,
        "source_scopes": scopes,
        "status": "evidence_passed",
        "worker_code_git_identities": code_ids,
    }
    output_identity = domain_identity(
        PHASE3B_WORKER_EVIDENCE_DOMAIN, output_material
    )
    command_material = {
        "authority_generation": PreparationAuthorityGeneration.PROSPECTIVE_V1_1.value,
        "command": "validate_runtime",
        "invocation_identifier": PHASE3A_NORMALIZED_INVOCATION,
        "worker_kind": "PHASE3A_VALIDATOR",
        "worker_revision": PHASE3A_NORMALIZED_WORKER_REVISION,
    }
    worker_material = {
        "capability_policy_identity": capability_policy_identity,
        "closed_dependency_identity": phase3a_result[
            "closed_dependency_environment_identity"
        ],
        "code_capability_git_identities": code_ids,
        "command_identity": domain_identity(
            PHASE3B_WORKER_EVIDENCE_DOMAIN, command_material
        ),
        "input_capability_identities": [],
        "invocation_identifier": PHASE3A_NORMALIZED_INVOCATION,
        "output_identity": output_identity,
        "runtime_contract_identity": phase3a_result["runtime_contract_identity"],
        "sandbox_template_identity": sandbox_template_identity,
        "source_commit": source_commit,
        "successful_worker_disposition": "evidence_passed",
        "worker_kind": "PHASE3A_VALIDATOR",
        "worker_module_git_identity": repository.tree_entry(
            source_commit, "src/orev3/execution/preparation_worker.py"
        ).object_identity,
        "worker_revision": PHASE3A_NORMALIZED_WORKER_REVISION,
    }
    identity = domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, worker_material)
    return Phase3BWorkerEvidence(
        "PHASE3A_VALIDATOR",
        identity,
        {**worker_material, "worker_evidence_identity": identity},
        output_material,
    )


def _read_verified_worker_object(path: Path, *, expected_size: int, expected_sha256: str, limit: int) -> bytes:
    if expected_size < 0 or expected_size > limit:
        raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CanonicalControlError("WORKER_OUTPUT_INVALID") from exc
    chunks: list[bytes] = []
    total = 0
    digest = hashlib.sha256()
    with os.fdopen(descriptor, "rb", buffering=0) as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != expected_size:
            raise CanonicalControlError("WORKER_OUTPUT_INVALID")
        while chunk := stream.read(min(1024 * 1024, limit + 1 - total)):
            total += len(chunk)
            if total > limit:
                raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
            digest.update(chunk); chunks.append(chunk)
        closed = os.fstat(stream.fileno())
    if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (closed.st_dev, closed.st_ino, closed.st_size, closed.st_mtime_ns, closed.st_ctime_ns):
        raise CanonicalControlError("WORKER_OUTPUT_INVALID")
    if total != expected_size or digest.hexdigest() != expected_sha256:
        raise CanonicalControlError("WORKER_OUTPUT_INVALID")
    return b"".join(chunks)


def load_phase3b_schemas(repository: GitRepository, source_commit: str) -> Mapping[str, Mapping[str, Any]]:
    schemas: dict[str, Mapping[str, Any]] = {}
    for kind, (_, path) in PHASE3B_SCHEMA_POLICY.items():
        entry = repository.tree_entry(source_commit, path)
        raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
        expected_id, expected_digest = PHASE3B_SCHEMA_DOCUMENT_POLICY[kind]
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            raise CanonicalControlError(f"bound Phase-3B schema digest differs: {kind}")
        schema = parse_json(raw)
        if schema.get("$id") != expected_id:
            raise CanonicalControlError(f"bound Phase-3B schema identifier differs: {kind}")
        schemas[kind] = schema
    if set(schemas) != set(PHASE3B_SCHEMA_POLICY) or len(schemas) != 20:
        raise CanonicalControlError("Phase-3B schema registry is not exactly complete")
    return schemas


def load_prospective_phase3b_schemas(
    repository: GitRepository, source_commit: str
) -> Mapping[str, Mapping[str, Any]]:
    """Load the explicit complete-v1.1 overlay; never infer a latest revision."""

    schemas: dict[str, Mapping[str, Any]] = {}
    for kind, (_, path) in PROSPECTIVE_PHASE3B_SCHEMA_POLICY.items():
        entry = repository.tree_entry(source_commit, path)
        raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
        expected_id, expected_digest = PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY[kind]
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            raise CanonicalControlError(
                f"prospective Phase-3B schema digest differs: {kind}"
            )
        schema = parse_json(raw)
        if schema.get("$id") != expected_id:
            raise CanonicalControlError(
                f"prospective Phase-3B schema identifier differs: {kind}"
            )
        schemas[kind] = schema
    if tuple(schemas) != tuple(PROSPECTIVE_PHASE3B_SCHEMA_POLICY) or len(schemas) != 20:
        raise CanonicalControlError(
            "prospective Phase-3B schema registry is not exactly complete"
        )
    return schemas


def load_evidence_policy(raw: bytes, *, schema: Mapping[str, Any]) -> Mapping[str, Any]:
    material = parse_canonical_bytes(raw)
    validate_json_schema_instance(material, schema, schema_registry={})
    identity_material = dict(material); identity_material.pop("policy_identity")
    if domain_identity(EVIDENCE_POLICY_DOMAIN, identity_material) != material["policy_identity"]:
        raise CanonicalControlError("evidence-preparation policy identity differs")
    if material["profile_renderer_identity"] != PHASE3B_PROFILE_RENDERER_IDENTITY:
        raise CanonicalControlError("Phase-3B profile renderer identity differs")
    expected = {
        "INPUT_PROJECTOR": ("src/orev3/execution/input_projection_worker.py", ("project_canonical_jsonl",)),
        "PHASE3A_VALIDATOR": ("src/orev3/execution/preparation_worker.py", ("validate_imports", "validate_runtime")),
        "READINESS_TEST": ("src/orev3/execution/readiness_test_worker.py", ("collect", "run_exact")),
        "REPLAY_PREPARATION": ("src/orev3/execution/replay_preparation_worker.py", ("reconstruct_replay",)),
    }
    actual = {
        item["worker_kind"]: (item["module"], tuple(item["commands"]))
        for item in material["worker_profiles"]
    }
    modules = [item["module"] for item in material["worker_profiles"]]
    if actual != expected or len(modules) != len(set(modules)) or any(item["network_policy"] != "prohibited" for item in material["worker_profiles"]):
        raise CanonicalControlError("Phase-3B worker capability policy differs from repository policy")
    for declaration in material["worker_profiles"]:
        if declaration["worker_kind"] == "PHASE3A_VALIDATOR":
            expected_template_identity = PHASE3A_SANDBOX_TEMPLATE_IDENTITY
        else:
            expected_template_identity = domain_identity(
                PHASE3B_PROFILE_RENDERER_DOMAIN,
                {
                    "allowed_read_roles": declaration["allowed_read_roles"],
                    "allowed_write_roles": declaration["allowed_write_roles"],
                    "commands": declaration["commands"],
                    "denied_roles": declaration["denied_roles"],
                    "module": declaration["module"],
                    "network_policy": declaration["network_policy"],
                    "sandbox_template_revision": declaration["sandbox_template_revision"],
                    "worker_kind": declaration["worker_kind"],
                },
            )
        if declaration["sandbox_template_identity"] != expected_template_identity:
            raise CanonicalControlError("Phase-3B sandbox template identity differs")
    return material


def require_phase3b_governance_closure(
    scopes: Sequence[SourceScopeDeclarationV1],
    *, mandatory_test_paths: Sequence[str], adapter_test_paths: Sequence[str],
    collection_affecting_paths: Sequence[str] = (), contract_paths: Sequence[str] = (),
) -> None:
    def covered(path: str, role: str) -> bool:
        return any(scope.role == role and (scope.repository_path == path or (scope.git_mode == "040000" and path.startswith(scope.repository_path + "/"))) for scope in scopes)
    required = [(EVIDENCE_POLICY_PATH, "configuration"), ("src/orev3/execution/schemas/v1", "readiness_schema")]
    required.extend((path, "control_plane") for path in PHASE3B_CONTROL_PATHS)
    required.extend((path, "readiness_tests") for path in (*mandatory_test_paths, *adapter_test_paths))
    missing = [f"{role}:{path}" for path, role in required if not covered(path, role)]
    for path in (*collection_affecting_paths, *contract_paths):
        if not any(scope.repository_path == path or (scope.git_mode == "040000" and path.startswith(scope.repository_path + "/")) for scope in scopes):
            missing.append(f"contract:{path}")
    if missing:
        raise CanonicalControlError("Phase-3B governed-scope closure is incomplete: " + ", ".join(sorted(missing)))


def aggregate_evidence(
    *, source_commit: str, runtime_contract_identity: str, dependency_environment_identity: str,
    adapter_identity: str, readiness_test_identity: str, input_snapshot_identities: Sequence[str],
    dataset_identities: Sequence[str], projection_identities: Sequence[str], replay_identity: str,
    population_identity: str, profile_identity: str, artifact_identity: str,
    capability_policy_identity: str = "0" * 64,
    worker_evidence_identities: Sequence[str] = (),
    semantic_component_identities: Sequence[str] = (),
    schema_version: int = 1,
) -> EvidencePreparationWorkerEvidence:
    if schema_version not in {1, 2}:
        raise CanonicalControlError("unsupported evidence-preparation schema version")
    components = {
        "artifact_evidence_identity": artifact_identity,
        "dataset_evidence_identities": list(dataset_identities),
        "input_snapshot_identities": list(input_snapshot_identities),
        "population_evidence_identity": population_identity,
        "profile_evidence_identity": profile_identity,
        "projection_evidence_identities": list(projection_identities),
        "readiness_test_evidence_identity": readiness_test_identity,
        "replay_evidence_identity": replay_identity,
        "worker_evidence_identities": list(worker_evidence_identities),
        "semantic_component_identities": list(semantic_component_identities),
    }
    material = {
        "adapter_identity": adapter_identity,
        "artifact_evidence_identity": artifact_identity,
        "capability_policy_identity": capability_policy_identity,
        "dataset_evidence_identities": list(dataset_identities),
        "dependency_environment_identity": dependency_environment_identity,
        "input_snapshot_identities": list(input_snapshot_identities),
        "population_evidence_identity": population_identity,
        "profile_evidence_identity": profile_identity,
        "projection_evidence_identities": list(projection_identities),
        "readiness_test_evidence_identity": readiness_test_identity,
        "replay_evidence_identity": replay_identity,
        "runtime_contract_identity": runtime_contract_identity,
        "semantic_component_identities": list(semantic_component_identities),
        "schema_version": schema_version,
        "source_commit": source_commit,
        "worker_evidence_identities": list(worker_evidence_identities),
    }
    identity = domain_identity(EVIDENCE_PREPARATION_DOMAIN, material)
    return EvidencePreparationWorkerEvidence(components, {**material, "evidence_preparation_identity": identity})


def reconstruct_projection_twice(
    *, source_root: Path, dependency_root: Path, raw_snapshot: Path,
    raw_schema_path: Path, projection_schema_path: Path,
    expected_raw_sha256: str, expected_raw_size: int,
    max_raw_bytes: int, max_projection_bytes: int, max_records: int,
    source_commit: str, runtime_contract_identity: str, dependency_environment_identity: str,
    capability_policy: Mapping[str, Any], raw_snapshot_identity: str,
) -> tuple[bytes, tuple[str, ...], Mapping[str, Any]]:
    root = Path(tempfile.mkdtemp(prefix="orev3-projection-reconstruction-"))
    try:
        outputs: list[bytes] = []
        worker_evidence: list[str] = []
        results: list[Mapping[str, Any]] = []
        for index in range(2):
            target = root / f"projection-{index}"
            worker = run_phase3b_worker(source_root, source_commit, "INPUT_PROJECTOR", "input_projection_worker.py", {"command": "project_canonical_jsonl", "expected_raw_sha256": expected_raw_sha256, "expected_raw_size": expected_raw_size, "max_projection_bytes": max_projection_bytes, "max_raw_bytes": max_raw_bytes, "max_records": max_records, "private_output": str(target), "projection_schema_path": str(projection_schema_path), "raw_schema_path": str(raw_schema_path), "raw_snapshot": str(raw_snapshot)}, dependency_root=dependency_root, runtime_contract_identity=runtime_contract_identity, dependency_environment_identity=dependency_environment_identity, capability_policy=capability_policy, invocation_identifier=f"projection-{index + 1}", input_capability_identities=(raw_snapshot_identity,), read_files=(raw_snapshot, raw_schema_path, projection_schema_path), write_roots=(root,), timeout_seconds=180, max_output_bytes=262144)
            result = worker.result
            worker_evidence.append(worker.evidence_identity)
            results.append(result)
            payload = _read_verified_worker_object(target, expected_size=result["byte_count"], expected_sha256=result["sha256"], limit=max_projection_bytes)
            outputs.append(payload)
        if outputs[0] != outputs[1] or results[0] != results[1]:
            raise CanonicalControlError("PROJECTION_INVALID: nondeterministic projection")
        return outputs[0], tuple(worker_evidence), results[0]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def reconstruct_replay_twice(
    *, source_root: Path, dependency_root: Path, projection_path: Path,
    projection_schema_path: Path,
    raw_store_root: Path, request_material: Mapping[str, Any], denied_locator_roots: Sequence[Path] = (),
    source_commit: str, runtime_contract_identity: str, dependency_environment_identity: str,
    capability_policy: Mapping[str, Any], projection_identity: str,
) -> tuple[bytes, tuple[str, ...]]:
    root = Path(tempfile.mkdtemp(prefix="orev3-replay-reconstruction-"))
    try:
        outputs: list[bytes] = []
        worker_evidence: list[str] = []
        for index in range(2):
            target = root / f"replay-{index}"
            request = dict(request_material)
            request.update({"command": "reconstruct_replay", "private_output": str(target), "projection_path": str(projection_path)})
            worker = run_phase3b_worker(source_root, source_commit, "REPLAY_PREPARATION", "replay_preparation_worker.py", request, dependency_root=dependency_root, runtime_contract_identity=runtime_contract_identity, dependency_environment_identity=dependency_environment_identity, capability_policy=capability_policy, invocation_identifier=f"replay-{index + 1}", input_capability_identities=(projection_identity,), read_files=(projection_path, projection_schema_path), write_roots=(root,), timeout_seconds=180, max_output_bytes=262144)
            worker_evidence.append(worker.evidence_identity)
            outputs.append(_read_verified_worker_object(target, expected_size=worker.result["byte_count"], expected_sha256=worker.result["sha256"], limit=int(request_material["max_projection_bytes"])))
        if outputs[0] != outputs[1]:
            raise CanonicalControlError("REPLAY_NONDETERMINISTIC")
        return outputs[0], tuple(worker_evidence)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _collect_evidence_preparation_evidence(
    repository: GitRepository,
    experiment_identifier: str,
    *,
    operational_input_locators: Mapping[str, Path],
    authority: Any,
    allow_test_file_remote: bool = False,
    artifact_store_root: Path | None = None,
    generation: EvidenceAuthorityGeneration = EvidenceAuthorityGeneration.HISTORICAL,
) -> EvidencePreparationWorkerEvidence:
    """Private collector for production and synthetic tests; cannot mint status."""

    phase3a_generation = (
        PreparationAuthorityGeneration.HISTORICAL
        if generation is EvidenceAuthorityGeneration.HISTORICAL
        else PreparationAuthorityGeneration.PROSPECTIVE_V1_1
    )
    environment = _collect_preparation_environment_evidence(
        repository,
        experiment_identifier,
        authority=authority,
        allow_test_file_remote=allow_test_file_remote,
        artifact_store_root=artifact_store_root,
        generation=phase3a_generation,
    )
    if not environment.evidence_passed:
        raise CanonicalControlError("; ".join(environment.diagnostics))
    remote = fetch_remote_head(repository, authority, "origin", allow_test_file=allow_test_file_remote)
    branch = repository.text("symbolic-ref", "--quiet", "HEAD")
    local_head = repository.resolve_commit("HEAD")
    if branch != authority.approved_branch_ref or local_head != remote.remote_head_commit or local_head != environment.source_commit:
        raise CanonicalControlError("Phase-3B authority changed after environment validation")
    requirements = _discover_requirements(
        repository,
        local_head,
        experiment_identifier,
        generation=phase3a_generation,
    )
    from orev3.execution.preparation import (
        _load_adapter_material,
        load_phase3a_schemas,
        load_prospective_phase3a_schemas,
    )
    selected_phase3a_schemas = (
        load_phase3a_schemas(repository, local_head)
        if generation is EvidenceAuthorityGeneration.HISTORICAL
        else load_prospective_phase3a_schemas(repository, local_head)
    )
    _, _, adapter = _load_adapter_material(
        repository, local_head, selected_phase3a_schemas, experiment_identifier
    )
    policy_entry = repository.tree_entry(local_head, EVIDENCE_POLICY_PATH)
    policy_bytes = repository.object_bytes(policy_entry.object_identity, max_bytes=1_048_576)
    extra_objects = [RequiredCommittedObject(EVIDENCE_POLICY_PATH, hashlib.sha256(policy_bytes).hexdigest(), "blob")]
    extra_scopes = [(EVIDENCE_POLICY_PATH, "configuration", "top_level", "")]
    existing_paths = {item[0] for item in requirements.governed_scopes}
    for contract in adapter.material["evidence_preparation"]["dataset_contracts"]:
        for path in (contract["raw_schema_path"], contract["projection_schema_path"]):
            if any(path == parent or path.startswith(parent + "/") for parent in existing_paths):
                continue
            entry = repository.tree_entry(local_head, path)
            raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
            extra_objects.append(RequiredCommittedObject(path, hashlib.sha256(raw).hexdigest(), "blob"))
            extra_scopes.append((path, "configuration", "top_level", ""))
            existing_paths.add(path)
    for declaration in adapter.material["evidence_preparation"]["profile_contract_declarations"]:
        path = declaration["path"]
        if any(path == parent or path.startswith(parent + "/") for parent in existing_paths):
            continue
        entry = repository.tree_entry(local_head, path)
        raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
        extra_objects.append(RequiredCommittedObject(path, hashlib.sha256(raw).hexdigest(), "blob"))
        extra_scopes.append((path, "configuration", "top_level", ""))
        existing_paths.add(path)
    requirements = SourceCandidateRequirements(requirements.experiment_identifier, (*requirements.required_objects, *extra_objects), (*requirements.governed_scopes, *extra_scopes))
    candidate = resolve_source_candidate(repository, authority, "origin", requirements, allow_test_file=allow_test_file_remote)
    request = {
        "approved_branch_ref": candidate.remote_head.approved_branch_ref,
        "artifact_store_root": str((artifact_store_root or (repository.root / DEFAULT_ARTIFACT_STORE)).resolve()),
        "command": "prepare_evidence",
        "evidence_policy_path": EVIDENCE_POLICY_PATH,
        "experiment_identifier": experiment_identifier,
        "input_object_store": os.path.abspath(repository.root / "data/research/readiness/inputs/sha256"),
        # Preserve lexical symlink components for the descriptor-safe no-follow
        # walk in external_inputs.  resolve() here would erase the evidence.
        "operational_input_locators": {key: os.fspath(value) for key, value in operational_input_locators.items()},
        "projection_object_store": os.path.abspath(repository.root / "data/research/readiness/projections/sha256"),
        "repository_authority_identifier": candidate.remote_head.repository_authority_identifier,
        "source_commit": candidate.source_commit,
        "source_scopes": [_scope_mapping(scope) for scope in candidate.source_scopes],
        "authority_generation": generation.value,
    }
    with DetachedSource(repository, candidate.source_commit) as detached:
        controller_entry = repository.tree_entry(candidate.source_commit, "src/orev3/execution/evidence_preparation_worker.py")
        request["controller_module_git_identity"] = controller_entry.object_identity
        evidence = run_phase3b_controller(detached, request, timeout_seconds=3600, max_output_bytes=1_048_576)
    aggregate = evidence["aggregate_evidence"]
    if aggregate.get("source_commit") != candidate.source_commit:
        raise CanonicalControlError("detached controller evidence is bound to another S")
    identity_material = dict(aggregate)
    claimed_identity = identity_material.pop("evidence_preparation_identity", None)
    if claimed_identity != domain_identity(EVIDENCE_PREPARATION_DOMAIN, identity_material):
        raise CanonicalControlError("detached controller aggregate identity does not reconstruct")
    required_origins = {
        "src/orev3/execution/evidence_preparation.py",
        "src/orev3/execution/evidence_preparation_worker.py",
        "src/orev3/execution/runtime.py",
    }
    if not required_origins.issubset(set(evidence.get("controller_module_origins", ()))):
        raise CanonicalControlError("detached controller origins are incomplete")
    return EvidencePreparationWorkerEvidence({"aggregate_evidence_identity": aggregate["evidence_preparation_identity"]}, aggregate)


def validate_evidence_preparation(
    repository: GitRepository,
    experiment_identifier: str,
    *,
    operational_input_locators: Mapping[str, Path],
    generation: EvidenceAuthorityGeneration = EvidenceAuthorityGeneration.HISTORICAL,
) -> EvidencePreparationAssessment:
    """Sole authoritative entry; no caller may supply S, authority, or evidence."""

    try:
        authority = load_repository_authority(repository.root / REPOSITORY_AUTHORITY_PATH)
        evidence = _collect_evidence_preparation_evidence(
            repository,
            experiment_identifier,
            operational_input_locators=operational_input_locators,
            authority=authority,
            generation=generation,
        )
        aggregate = evidence.aggregate_material
        return EvidencePreparationAssessment(EvidencePreparationDisposition.EVIDENCE_PREPARATION_VALIDATED, PHASE3B_REMAINING_PREDICATES, (), aggregate["evidence_preparation_identity"], aggregate)
    except (CanonicalControlError, GitAuthorityError, OSError, KeyError, ValueError, TypeError) as exc:
        message = str(exc)
        code = next(
            (item.value for item in EvidencePreparationFailureCode if item.value in message),
            EvidencePreparationFailureCode.EVIDENCE_PREPARATION_INTERNAL_REJECTED.value,
        )
        return EvidencePreparationAssessment(EvidencePreparationDisposition.EVIDENCE_PREPARATION_REJECTED, PHASE3B_REMAINING_PREDICATES, (code,))
__all__ = ["EVIDENCE_POLICY_DOMAIN", "EVIDENCE_POLICY_PATH", "EVIDENCE_PREPARATION_DOMAIN", "PHASE3A_NORMALIZED_CODE_PATHS", "PHASE3A_NORMALIZED_INVOCATION", "PHASE3A_NORMALIZED_OUTPUT_REVISION", "PHASE3A_NORMALIZED_WORKER_REVISION", "PHASE3B_CONTROL_PATHS", "PHASE3B_REMAINING_PREDICATES", "EvidenceAuthorityGeneration", "EvidencePreparationAssessment", "EvidencePreparationDisposition", "EvidencePreparationFailureCode", "EvidencePreparationWorkerEvidence", "aggregate_evidence", "load_evidence_policy", "load_phase3b_schemas", "load_prospective_phase3b_schemas", "reconstruct_projection_twice", "reconstruct_prospective_phase3a_worker", "reconstruct_replay_twice", "require_phase3b_governance_closure", "validate_evidence_preparation"]
