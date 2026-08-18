"""Non-authoritative Phase-3A preparation-environment composition."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from orev3.execution.canonical import CanonicalControlError, normalize_experiment_identifier, parse_canonical_bytes, parse_json, validate_json_schema_instance
from orev3.execution.git_state import (
    GitAuthorityError,
    GitDiagnosticCode,
    GitRepository,
    RequiredCommittedObject,
    SourceCandidate,
    SourceCandidateRequirements,
    _validate_safe_governed_entry,
    fetch_remote_head,
    resolve_source_candidate,
)
from orev3.execution.readiness import load_repository_authority
from orev3.execution.readiness_record import (
    PHASE3A_SCHEMA_DOCUMENT_POLICY,
    PHASE3A_SCHEMA_POLICY,
    RepositoryAuthorityV1,
    SourceScopeDeclarationV1,
    load_repository_authority_bytes,
    reconstruct_document_binding_identity,
    validate_implementation_binding,
    validate_readiness_test_policy,
)
from orev3.execution.registry import load_adapter_declaration_bytes, load_adapter_registry_bytes
from orev3.execution.runtime import (
    DetachedSource,
    construct_closed_dependency_root,
    load_offline_artifact_manifest_bytes,
    load_runtime_contract_bytes,
    _run_preparation_worker,
    validate_closed_dependency_imports,
    validate_dependency_lock,
    validate_host_runtime,
)

RUNTIME_CONTRACT_PATH = "config/research/readiness/runtime-contract-v1.json"
ADAPTER_REGISTRY_PATH = "config/research/readiness/adapter-registry-v1.json"
READINESS_TEST_POLICY_PATH = "config/research/readiness/readiness-test-policy-v1.json"
READINESS_SPECIFICATION_PATH = "docs/research/specifications/experiment-execution-readiness-v1.md"
REPOSITORY_AUTHORITY_PATH = "config/research/readiness/repository-authority-v1.json"
DEFAULT_ARTIFACT_STORE = "data/research/readiness/wheels"
PHASE3A_REMAINING_PREDICATES = (
    "artifact_declaration_validation",
    "candidate_readiness_record_generation",
    "external_input_snapshot_validation",
    "mandatory_readiness_test_execution",
    "population_accounting",
    "profile_operational_validation",
    "readiness_seal_and_current_status",
    "replay_reconstruction",
)


class PreparationEnvironmentDisposition(str, Enum):
    PREPARATION_ENVIRONMENT_VALIDATED = "PREPARATION_ENVIRONMENT_VALIDATED"
    PREPARATION_ENVIRONMENT_REJECTED = "PREPARATION_ENVIRONMENT_REJECTED"


class PreparationEvidenceDisposition(str, Enum):
    EVIDENCE_PASSED = "PREPARATION_ENVIRONMENT_EVIDENCE_PASSED"
    EVIDENCE_REJECTED = "PREPARATION_ENVIRONMENT_EVIDENCE_REJECTED"


@dataclass(frozen=True, slots=True)
class PreparationEnvironmentAssessment:
    disposition: PreparationEnvironmentDisposition
    remaining_predicates: tuple[str, ...]
    diagnostics: tuple[str, ...]
    source_commit: str = ""
    runtime_contract_identity: str = ""
    adapter_registry_identity: str = ""
    adapter_identity: str = ""
    closed_dependency_environment_identity: str = ""

    @property
    def environment_validated(self) -> bool:
        return self.disposition == PreparationEnvironmentDisposition.PREPARATION_ENVIRONMENT_VALIDATED


@dataclass(frozen=True, slots=True)
class PreparationEnvironmentEvidence:
    disposition: PreparationEvidenceDisposition
    remaining_predicates: tuple[str, ...]
    diagnostics: tuple[str, ...]
    source_commit: str = ""
    runtime_contract_identity: str = ""
    adapter_registry_identity: str = ""
    adapter_identity: str = ""
    closed_dependency_environment_identity: str = ""

    @property
    def evidence_passed(self) -> bool:
        return self.disposition == PreparationEvidenceDisposition.EVIDENCE_PASSED


def _blob(repository: GitRepository, commit: str, path: str, *, limit: int = 1_048_576) -> bytes:
    entry = repository.tree_entry(commit, path)
    if entry.object_type != "blob" or entry.mode not in {"100644", "100755"}:
        raise CanonicalControlError(f"Phase-3A governed object is not a regular file: {path}")
    return repository.object_bytes(entry.object_identity, max_bytes=limit)


def load_phase3a_schemas(repository: GitRepository, source_commit: str) -> Mapping[str, Mapping[str, object]]:
    schemas: dict[str, Mapping[str, object]] = {}
    for kind, (_, path) in PHASE3A_SCHEMA_POLICY.items():
        raw = _blob(repository, source_commit, path)
        expected_identifier, expected_digest = PHASE3A_SCHEMA_DOCUMENT_POLICY[kind]
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            raise CanonicalControlError(f"bound Phase-3A schema digest differs: {kind}")
        schema = parse_json(raw)
        if schema.get("$id") != expected_identifier:
            raise CanonicalControlError(f"bound Phase-3A schema identifier differs: {kind}")
        schemas[kind] = schema
    return schemas


def _scope_mapping(scope: SourceScopeDeclarationV1) -> dict[str, str]:
    material = {
        "git_mode": scope.git_mode,
        "git_object_identity": scope.git_object_identity,
        "nesting": scope.nesting,
        "repository_path": scope.repository_path,
        "role": scope.role,
    }
    if scope.nesting == "nested":
        material["parent_path"] = scope.parent_path
    return material


def _scope_has_role(scopes: tuple[SourceScopeDeclarationV1, ...], path: str, role: str) -> bool:
    for scope in scopes:
        if scope.role != role:
            continue
        if scope.repository_path == path:
            return True
        if scope.git_mode == "040000" and path.startswith(scope.repository_path + "/"):
            return True
    return False


def _require_phase3a_scope_closure(
    scopes: tuple[SourceScopeDeclarationV1, ...],
    descriptor: Mapping[str, Any],
    descriptor_path: str,
    implementation_path: str,
    dependency_lock_path: str,
    artifact_manifest_path: str,
    mandatory_test_paths: tuple[str, ...],
) -> None:
    required: dict[str, str] = {
        RUNTIME_CONTRACT_PATH: "runtime_manifest",
        ADAPTER_REGISTRY_PATH: "configuration",
        descriptor_path: "configuration",
        artifact_manifest_path: "configuration",
        READINESS_TEST_POLICY_PATH: "readiness_test_policy",
        READINESS_SPECIFICATION_PATH: "readiness_specification",
        REPOSITORY_AUTHORITY_PATH: "repository_authority",
        "src/orev3": "source_tree",
        "src/orev3/execution": "control_plane",
        "src/orev3/execution/schemas/v1": "readiness_schema",
        descriptor["implementation_binding_path"]: "configuration",
        descriptor["protocol"]["path"]: "protocol",
        descriptor["execution_specification"]["path"]: "execution_specification",
        implementation_path: "implementation",
        dependency_lock_path: "dependency_manifest",
    }
    for path in mandatory_test_paths:
        required[path] = "readiness_tests"
    for path in descriptor["adapter_readiness_tests"]:
        required[path] = "readiness_tests"
    missing = [f"{role}:{path}" for path, role in sorted(required.items()) if not _scope_has_role(scopes, path, role)]
    if missing:
        raise CanonicalControlError("Phase-3A governed-scope closure is incomplete: " + ", ".join(missing))


def _validate_scope_objects(repository: GitRepository, source: str, raw_scopes: Any) -> tuple[SourceScopeDeclarationV1, ...]:
    if not isinstance(raw_scopes, list) or not raw_scopes:
        raise CanonicalControlError("resolved Phase-3A source scopes are absent")
    scopes = tuple(SourceScopeDeclarationV1.from_mapping(item, object_format=repository.object_format()) for item in raw_scopes)
    paths: set[str] = set()
    for scope in scopes:
        if scope.repository_path in paths:
            raise CanonicalControlError("resolved Phase-3A source scope is duplicated")
        paths.add(scope.repository_path)
        actual = repository.tree_entry(source, scope.repository_path)
        _validate_safe_governed_entry(repository, source, actual)
        if actual.mode != scope.git_mode or actual.object_identity != scope.git_object_identity:
            raise CanonicalControlError("resolved Phase-3A source scope identity differs from S")
    return scopes


def _load_adapter_material(repository: GitRepository, source: str, schemas: Mapping[str, Mapping[str, object]], experiment_identifier: str):
    registry = load_adapter_registry_bytes(_blob(repository, source, ADAPTER_REGISTRY_PATH), schema=schemas["adapter-registry"])
    reference = registry.descriptor_reference(experiment_identifier)
    descriptor_raw = _blob(repository, source, reference["descriptor_path"])
    if hashlib.sha256(descriptor_raw).hexdigest() != reference["descriptor_sha256"]:
        raise CanonicalControlError("adapter descriptor digest differs from registry")
    adapter = load_adapter_declaration_bytes(descriptor_raw, schema=schemas["adapter-declaration"])
    if adapter.experiment_identifier != reference["experiment_identifier"] or adapter.adapter_identifier != reference["adapter_identifier"] or adapter.adapter_identity != reference["descriptor_identity"]:
        raise CanonicalControlError("adapter descriptor differs from registry reference")
    return registry, reference, adapter


def _validate_detached_preparation_environment(request: Mapping[str, Any]) -> Mapping[str, Any]:
    """Trust-bearing validation executed only from the committed detached S worker."""

    source_root = Path(request["source_root"]).resolve()
    repository = GitRepository(source_root)
    source = repository.resolve_commit("HEAD")
    if request.get("source_commit") != source:
        raise CanonicalControlError("detached source HEAD differs from resolved S")
    identifier = normalize_experiment_identifier(request["experiment_identifier"])
    committed_authority = load_repository_authority_bytes(
        _blob(repository, source, REPOSITORY_AUTHORITY_PATH)
    )
    if (
        committed_authority.repository_authority_identifier
        != request["repository_authority_identifier"]
        or committed_authority.approved_branch_ref != request["approved_branch_ref"]
        or committed_authority.git_object_format != repository.object_format()
    ):
        raise CanonicalControlError("detached repository authority differs from resolved Phase-2 authority")
    scopes = _validate_scope_objects(repository, source, request["source_scopes"])
    schemas = load_phase3a_schemas(repository, source)
    policy = parse_canonical_bytes(_blob(repository, source, READINESS_TEST_POLICY_PATH))
    validate_json_schema_instance(policy, schemas["readiness-test-policy"], schema_registry={})
    validate_readiness_test_policy(policy)
    mandatory_test_paths = tuple(policy["required_selectors"])
    runtime = load_runtime_contract_bytes(_blob(repository, source, RUNTIME_CONTRACT_PATH), schema=schemas["runtime-contract"])
    lock_raw = _blob(repository, source, runtime.dependency_lock_path, limit=8 * 1024 * 1024)
    dependency_lock = validate_dependency_lock(lock_raw, expected_sha256=runtime.dependency_lock_sha256)
    artifact_manifest_raw = _blob(repository, source, runtime.artifact_manifest_path)
    artifact_manifest = load_offline_artifact_manifest_bytes(
        artifact_manifest_raw,
        schema=schemas["offline-artifact-manifest"],
        expected_sha256=runtime.artifact_manifest_sha256,
        dependency_lock_sha256=runtime.dependency_lock_sha256,
        dependency_lock=dependency_lock,
    )
    expected_artifact_identity = runtime.material["dependency_lock"]["offline_artifact_manifest"]["identity"]
    if artifact_manifest.manifest_identity != expected_artifact_identity:
        raise CanonicalControlError("offline artifact manifest identity differs from runtime contract")
    registry, reference, adapter = _load_adapter_material(repository, source, schemas, identifier)
    descriptor = adapter.material
    protocol_raw = _blob(repository, source, descriptor["protocol"]["path"])
    if hashlib.sha256(protocol_raw).hexdigest() != descriptor["protocol"]["sha256"]:
        raise CanonicalControlError("adapter protocol digest differs from committed bytes")
    specification = descriptor["execution_specification"]
    specification_raw = _blob(repository, source, specification["path"])
    if hashlib.sha256(specification_raw).hexdigest() != specification["sha256"]:
        raise CanonicalControlError("adapter execution specification digest differs")
    specification_binding = {
        "byte_count": len(specification_raw),
        "git_blob_identity": repository.tree_entry(source, specification["path"]).object_identity,
        "path": specification["path"],
        "revision": specification["revision"],
        "sha256": specification["sha256"],
        "specification_identity": specification["specification_identity"],
    }
    if reconstruct_document_binding_identity(specification_binding, identity_field="specification_identity") != specification["specification_identity"]:
        raise CanonicalControlError("execution specification identity does not reconstruct")
    binding = parse_canonical_bytes(_blob(repository, source, descriptor["implementation_binding_path"]))
    validate_json_schema_instance(binding, schemas["implementation-binding"], schema_registry={})
    validate_implementation_binding(binding, object_format=repository.object_format())
    expected_pairs = (
        (binding["adapter_identifier"], descriptor["adapter_identifier"], "adapter identifier"),
        (binding["entry_point"], descriptor["implementation_entry_point"], "implementation entry point"),
        (binding["experiment_identifier"], descriptor["experiment_identifier"], "experiment identifier"),
        (binding["execution_specification_identity"], specification["specification_identity"], "execution specification"),
        (binding["experiment_configuration_identity"], descriptor["configuration"]["experiment_configuration_identity"], "configuration"),
        (binding["profile_identity"], descriptor["execution_profile"]["profile_identity"], "profile"),
        (binding["protocol"]["revision"], descriptor["protocol"]["revision"], "protocol revision"),
        (binding["protocol"]["sha256"], descriptor["protocol"]["sha256"], "protocol digest"),
    )
    for actual, expected, label in expected_pairs:
        if actual != expected:
            raise CanonicalControlError(f"adapter {label} differs from implementation binding")
    implementation_path = binding["implementation"]["path"]
    implementation_raw = _blob(repository, source, implementation_path)
    if hashlib.sha256(implementation_raw).hexdigest() != binding["implementation"]["sha256"]:
        raise CanonicalControlError("implementation digest differs from binding")
    required_descriptor_paths = {reference["descriptor_path"], descriptor["protocol"]["path"], descriptor["implementation_binding_path"], specification["path"], implementation_path}
    if not required_descriptor_paths.issubset(set(descriptor["governed_scope_paths"])):
        raise CanonicalControlError("adapter governed scopes omit a bound authority object")
    _require_phase3a_scope_closure(scopes, descriptor, reference["descriptor_path"], implementation_path, runtime.dependency_lock_path, runtime.artifact_manifest_path, mandatory_test_paths)
    if request.get("phase3b_controller") is True:
        dependency_root_path = Path(request["closed_dependency_root_path"]).resolve()
        temporary_root = Path(request["controller_temporary_root"]).resolve()
        try:
            dependency_root_path.parent.relative_to(temporary_root)
        except ValueError as exc:
            raise CanonicalControlError("Phase-3B dependency root escapes the controller temporary root") from exc
        dependency_root_path.mkdir(mode=0o700)
    else:
        dependency_root_path = Path(tempfile.mkdtemp(prefix="closed-dependencies-", dir=os.environ["TMPDIR"]))
    dependency_root = construct_closed_dependency_root(dependency_lock, artifact_manifest, Path(request["artifact_store_root"]), dependency_root_path)
    validate_host_runtime(runtime, dependency_root)
    if dict(dependency_root.distributions).get(runtime.material["test_runner"]["distribution"]) != runtime.material["test_runner"]["version"]:
        raise CanonicalControlError("test-runner version differs from closed dependency root")
    import_origins = validate_closed_dependency_imports(runtime, dependency_root, source_root)
    module_origins: list[str] = ["src/orev3/execution/preparation_worker.py"]
    for name, module in sorted(sys.modules.items()):
        if not name.startswith("orev3.execution") or not getattr(module, "__file__", ""):
            continue
        origin = Path(module.__file__).resolve()
        try:
            module_origins.append(origin.relative_to(source_root).as_posix())
        except ValueError as exc:
            raise CanonicalControlError("trust-bearing project module escaped detached S") from exc
    result = {
        "adapter_identity": adapter.adapter_identity,
        "adapter_registry_identity": registry.registry_identity,
        "closed_dependency_environment_identity": dependency_root.identity,
        "dependency_import_origins": list(import_origins),
        "evidence_disposition": PreparationEvidenceDisposition.EVIDENCE_PASSED.value,
        "project_control_plane_origins": module_origins,
        "remaining_predicates": list(PHASE3A_REMAINING_PREDICATES),
        "runtime_contract_identity": runtime.runtime_contract_identity,
        "source_commit": source,
    }
    if request.get("phase3b_controller") is True:
        result["closed_dependency_root_path"] = str(dependency_root.path)
    return result


def _discover_requirements(repository: GitRepository, source: str, experiment_identifier: str) -> SourceCandidateRequirements:
    schemas = load_phase3a_schemas(repository, source)
    policy = parse_canonical_bytes(_blob(repository, source, READINESS_TEST_POLICY_PATH))
    validate_readiness_test_policy(policy)
    runtime = load_runtime_contract_bytes(_blob(repository, source, RUNTIME_CONTRACT_PATH), schema=schemas["runtime-contract"])
    registry, reference, adapter = _load_adapter_material(repository, source, schemas, experiment_identifier)
    del registry
    descriptor = adapter.material
    binding = parse_canonical_bytes(_blob(repository, source, descriptor["implementation_binding_path"]))
    implementation_path = binding["implementation"]["path"]
    scopes: dict[str, tuple[str, str, str]] = {
        "src/orev3": ("source_tree", "contains_declared_children", ""),
        "src/orev3/execution": ("control_plane", "nested", "src/orev3"),
        "src/orev3/execution/schemas/v1": ("readiness_schema", "nested", "src/orev3"),
        implementation_path: ("implementation", "nested", "src/orev3"),
        RUNTIME_CONTRACT_PATH: ("runtime_manifest", "top_level", ""),
        ADAPTER_REGISTRY_PATH: ("configuration", "top_level", ""),
        reference["descriptor_path"]: ("configuration", "top_level", ""),
        runtime.artifact_manifest_path: ("configuration", "top_level", ""),
        READINESS_TEST_POLICY_PATH: ("readiness_test_policy", "top_level", ""),
        READINESS_SPECIFICATION_PATH: ("readiness_specification", "top_level", ""),
        REPOSITORY_AUTHORITY_PATH: ("repository_authority", "top_level", ""),
        descriptor["implementation_binding_path"]: ("configuration", "top_level", ""),
        descriptor["protocol"]["path"]: ("protocol", "top_level", ""),
        descriptor["execution_specification"]["path"]: ("execution_specification", "top_level", ""),
        runtime.dependency_lock_path: ("dependency_manifest", "top_level", ""),
    }
    for path in policy["required_selectors"]:
        scopes[path] = ("readiness_tests", "top_level", "")
    for path in descriptor["adapter_readiness_tests"]:
        if not any(path == parent or path.startswith(parent + "/") for parent in policy["required_selectors"]):
            scopes[path] = ("readiness_tests", "top_level", "")
    for path in _collection_affecting_paths(repository, source, (*policy["required_selectors"], *descriptor["adapter_readiness_tests"])):
        scopes[path] = ("readiness_tests", "top_level", "")
    required_objects: list[RequiredCommittedObject] = []
    for path in sorted(scopes):
        entry = repository.tree_entry(source, path)
        expected_sha = hashlib.sha256(_blob(repository, source, path, limit=8 * 1024 * 1024)).hexdigest() if entry.object_type == "blob" else ""
        required_objects.append(RequiredCommittedObject(path, expected_sha, entry.object_type))
    governed = tuple((path, role, nesting, parent) for path, (role, nesting, parent) in sorted(scopes.items()))
    return SourceCandidateRequirements(experiment_identifier, tuple(required_objects), governed)


def _collection_affecting_paths(repository: GitRepository, source: str, selectors: tuple[str, ...]) -> tuple[str, ...]:
    candidates = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"}
    for selector in selectors:
        base = selector.split("::", 1)[0]
        parts = base.split("/")
        if parts and "." in parts[-1]:
            parts = parts[:-1]
        for index in range(1, len(parts) + 1):
            parent = "/".join(parts[:index])
            candidates.add(f"{parent}/conftest.py")
            candidates.add(f"{parent}/__init__.py")
    existing: list[str] = []
    for path in sorted(candidates):
        try:
            repository.tree_entry(source, path)
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.OBJECT_NOT_FOUND:
                continue
            raise
        existing.append(path)
    return tuple(existing)


def _collect_preparation_environment_evidence(
    repository: GitRepository,
    experiment_identifier: str,
    *,
    authority: RepositoryAuthorityV1,
    remote_alias: str = "origin",
    artifact_store_root: Path | None = None,
    allow_test_file_remote: bool = False,
    interpreter: Path | None = None,
) -> PreparationEnvironmentEvidence:
    """Private evidence collector; it cannot return authoritative Phase-3A state."""

    try:
        identifier = normalize_experiment_identifier(experiment_identifier)
        first_remote = fetch_remote_head(repository, authority, remote_alias, allow_test_file=allow_test_file_remote)
        branch = repository.text("symbolic-ref", "--quiet", "HEAD")
        local_head = repository.resolve_commit("HEAD")
        if branch != authority.approved_branch_ref or local_head != first_remote.remote_head_commit:
            raise GitAuthorityError(GitDiagnosticCode.LOCAL_REMOTE_DIVERGENCE, "preparation requires synchronized approved local and remote heads")
        requirements = _discover_requirements(repository, local_head, identifier)
        candidate = resolve_source_candidate(repository, authority, remote_alias, requirements, allow_test_file=allow_test_file_remote)
        store = (artifact_store_root or (repository.root / DEFAULT_ARTIFACT_STORE)).resolve()
        request = {
            "approved_branch_ref": candidate.remote_head.approved_branch_ref,
            "artifact_store_root": str(store),
            "experiment_identifier": identifier,
            "repository_authority_identifier": candidate.remote_head.repository_authority_identifier,
            "source_commit": candidate.source_commit,
            "source_scopes": [_scope_mapping(scope) for scope in candidate.source_scopes],
        }
        with DetachedSource(repository, candidate.source_commit) as detached:
            worker = _run_preparation_worker(detached, "validate_runtime", request, interpreter=interpreter)
        material = worker.material
        if material.get("evidence_disposition") != PreparationEvidenceDisposition.EVIDENCE_PASSED.value or tuple(material.get("remaining_predicates", ())) != PHASE3A_REMAINING_PREDICATES:
            raise CanonicalControlError("detached worker did not establish the bounded Phase-3A evidence set")
        required_worker_origins = {
            "src/orev3/execution/canonical.py",
            "src/orev3/execution/git_state.py",
            "src/orev3/execution/preparation.py",
            "src/orev3/execution/preparation_worker.py",
            "src/orev3/execution/readiness_record.py",
            "src/orev3/execution/registry.py",
            "src/orev3/execution/runtime.py",
        }
        if not required_worker_origins.issubset(set(material.get("project_control_plane_origins", ()))):
            raise CanonicalControlError("detached worker did not prove every trust-bearing project module origin")
        return PreparationEnvironmentEvidence(
            PreparationEvidenceDisposition.EVIDENCE_PASSED,
            PHASE3A_REMAINING_PREDICATES,
            (),
            material["source_commit"],
            material["runtime_contract_identity"],
            material["adapter_registry_identity"],
            material["adapter_identity"],
            material["closed_dependency_environment_identity"],
        )
    except (CanonicalControlError, GitAuthorityError, OSError) as exc:
        code = exc.code.value if isinstance(exc, GitAuthorityError) else type(exc).__name__
        return PreparationEnvironmentEvidence(PreparationEvidenceDisposition.EVIDENCE_REJECTED, PHASE3A_REMAINING_PREDICATES, (f"{code}: {exc}",))


def validate_preparation_environment(
    repository: GitRepository,
    experiment_identifier: str,
    *,
    remote_alias: str = "origin",
    artifact_store_root: Path | None = None,
    interpreter: Path | None = None,
) -> PreparationEnvironmentAssessment:
    """Use only repository-owned production authority to mint Phase-3A success."""

    try:
        authority = load_repository_authority(repository.root / REPOSITORY_AUTHORITY_PATH)
    except (CanonicalControlError, GitAuthorityError, OSError) as exc:
        code = exc.code.value if isinstance(exc, GitAuthorityError) else type(exc).__name__
        return PreparationEnvironmentAssessment(
            PreparationEnvironmentDisposition.PREPARATION_ENVIRONMENT_REJECTED,
            PHASE3A_REMAINING_PREDICATES,
            (f"{code}: {exc}",),
        )
    evidence = _collect_preparation_environment_evidence(
        repository,
        experiment_identifier,
        authority=authority,
        remote_alias=remote_alias,
        artifact_store_root=artifact_store_root,
        allow_test_file_remote=False,
        interpreter=interpreter,
    )
    if not evidence.evidence_passed:
        return PreparationEnvironmentAssessment(
            PreparationEnvironmentDisposition.PREPARATION_ENVIRONMENT_REJECTED,
            evidence.remaining_predicates,
            evidence.diagnostics,
        )
    return PreparationEnvironmentAssessment(
        PreparationEnvironmentDisposition.PREPARATION_ENVIRONMENT_VALIDATED,
        evidence.remaining_predicates,
        (),
        evidence.source_commit,
        evidence.runtime_contract_identity,
        evidence.adapter_registry_identity,
        evidence.adapter_identity,
        evidence.closed_dependency_environment_identity,
    )


__all__ = [
    "ADAPTER_REGISTRY_PATH",
    "DEFAULT_ARTIFACT_STORE",
    "PHASE3A_REMAINING_PREDICATES",
    "READINESS_SPECIFICATION_PATH",
    "READINESS_TEST_POLICY_PATH",
    "REPOSITORY_AUTHORITY_PATH",
    "RUNTIME_CONTRACT_PATH",
    "PreparationEnvironmentAssessment",
    "PreparationEnvironmentDisposition",
    "load_phase3a_schemas",
    "validate_preparation_environment",
]
