"""Governed, non-operational prerequisite contracts for readiness v1.1.

This module reconstructs committed declarations at one source commit ``S``.
It cannot assemble a readiness record, execute smoke, allocate an attempt, or
create any lifecycle authority.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import (
    CanonicalControlError,
    domain_identity,
    parse_canonical_bytes,
    parse_json,
    validate_json_schema_instance,
    validate_repository_path,
)
from orev3.execution.contract_validation import (
    PROFILE_CONTRACT_DOMAIN,
    validate_artifact_declarations,
    validate_profile_contract,
)
from orev3.execution.git_state import GitRepository
from orev3.execution.readiness_record import (
    PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY,
    PROSPECTIVE_PHASE2_SCHEMA_POLICY,
    PROSPECTIVE_PHASE3A_SCHEMA_DOCUMENT_POLICY,
    PROSPECTIVE_PHASE3A_SCHEMA_POLICY,
    PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY,
    PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
    READINESS_TEST_POLICY_V2_PATH,
    READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
    READINESS_V1_1_SCHEMA_POLICY,
    REPOSITORY_AUTHORITY_PATH,
    SourceScopeDeclarationV1,
    load_repository_authority_bytes,
    reconstruct_control_component_identity,
    validate_implementation_binding,
    validate_readiness_test_policy_v2,
)
from orev3.execution.registry import (
    AdapterDeclarationV1,
    AdapterRegistryV1,
    load_adapter_declaration_bytes,
    load_adapter_registry_bytes,
)


ALLOCATION_AUTHORITY_IDENTITY_DOMAIN = (
    "orev3:experiment-attempt-allocation-authority:v1\n"
)
CONTROL_STORAGE_CONTRACT_IDENTITY_DOMAIN = (
    "orev3:experiment-control-storage-contract:v1\n"
)
ATTEMPT_OUTPUT_DECLARATION_IDENTITY_DOMAIN = (
    "orev3:experiment-attempt-output-declaration:v1\n"
)
ADAPTER_REGISTRY_PATH = "config/research/readiness/adapter-registry-v1.json"
ATTEMPT_AUTHORITY_CONTRACT_PATH = (
    "config/research/readiness/attempt-authority-contract-v1.json"
)
PROSPECTIVE_POLICY_IDENTIFIER = "experiment-execution-readiness-v1.1-tests-v1"
ALLOCATOR_IMPLEMENTATION_PATH = "src/orev3/execution/attempts.py"
ORCHESTRATOR_IMPLEMENTATION_PATH = "src/orev3/execution/orchestrator.py"
OUTCOME_GATE_IMPLEMENTATION_PATH = "src/orev3/execution/outcome_gate.py"
SOURCE_TREE_PATH = "src/orev3"
MAX_PREREQUISITE_BYTES = 1_048_576
_SINGLETON_PREREQUISITE_ROLES = frozenset(
    {
        "execution_specification",
        "implementation",
        "protocol",
        "readiness_schema",
        "readiness_specification",
        "readiness_test_policy",
        "repository_authority",
        "source_tree",
    }
)


class ProspectiveRegistryGeneration(str, Enum):
    PHASE2 = "prospective-v1.1-phase2"
    PHASE3A = "prospective-v1.1-phase3a"
    PHASE3B = "prospective-v1.1-phase3b"
    READINESS_V1_1 = "prospective-v1.1-final"


_PROSPECTIVE_POLICIES = {
    ProspectiveRegistryGeneration.PHASE2: (
        PROSPECTIVE_PHASE2_SCHEMA_POLICY,
        PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY,
        6,
    ),
    ProspectiveRegistryGeneration.PHASE3A: (
        PROSPECTIVE_PHASE3A_SCHEMA_POLICY,
        PROSPECTIVE_PHASE3A_SCHEMA_DOCUMENT_POLICY,
        10,
    ),
    ProspectiveRegistryGeneration.PHASE3B: (
        PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
        PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY,
        20,
    ),
    ProspectiveRegistryGeneration.READINESS_V1_1: (
        READINESS_V1_1_SCHEMA_POLICY,
        READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
        29,
    ),
}


@dataclass(frozen=True, slots=True)
class BoundReadinessTestPolicyV2:
    material: Mapping[str, Any]
    repository_path: str
    git_object_identity: str
    sha256: str


@dataclass(frozen=True, slots=True)
class BoundAttemptAuthorityContract:
    material: Mapping[str, Any]
    repository_path: str
    git_object_identity: str
    sha256: str
    allocation_authority_identity: str
    allocator_contract_identity: str
    allocator_client_component_identity: str
    control_storage_component_identity: str
    control_storage_contract_identity: str


@dataclass(frozen=True, slots=True)
class BoundProfileContracts:
    declarations: Mapping[str, Mapping[str, Any]]
    profile_evidence: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ReadinessPrerequisiteContracts:
    source_commit: str
    schemas: Mapping[str, Mapping[str, Any]]
    readiness_test_policy: BoundReadinessTestPolicyV2
    adapter_registry: AdapterRegistryV1
    adapter: AdapterDeclarationV1
    attempt_authority: BoundAttemptAuthorityContract
    profile_contracts: BoundProfileContracts
    implementation_binding: Mapping[str, Any]
    source_scopes: tuple[SourceScopeDeclarationV1, ...]


def _committed_blob(
    repository: GitRepository, source_commit: str, repository_path: str
) -> tuple[bytes, str]:
    path = validate_repository_path(repository_path)
    entry = repository.tree_entry(source_commit, path)
    if entry.object_type != "blob" or entry.mode != "100644":
        raise CanonicalControlError(
            f"governed prerequisite is not a safe regular Git blob: {path}"
        )
    return (
        repository.object_bytes(entry.object_identity, max_bytes=MAX_PREREQUISITE_BYTES),
        entry.object_identity,
    )


def prospective_schema_policy(
    generation: ProspectiveRegistryGeneration,
) -> tuple[Mapping[str, tuple[str, str]], Mapping[str, tuple[str, str]], int]:
    if not isinstance(generation, ProspectiveRegistryGeneration):
        raise CanonicalControlError("prospective schema generation is not governed")
    return _PROSPECTIVE_POLICIES[generation]


def load_prospective_schemas(
    repository: GitRepository,
    source_commit: str,
    generation: ProspectiveRegistryGeneration,
) -> Mapping[str, Mapping[str, Any]]:
    source = repository.resolve_commit(source_commit)
    policy, documents, expected_count = prospective_schema_policy(generation)
    if set(policy) != set(documents) or len(policy) != expected_count:
        raise CanonicalControlError("prospective schema overlay is inconsistent")
    schemas: dict[str, Mapping[str, Any]] = {}
    for kind in policy:
        _, path = policy[kind]
        expected_id, expected_sha256 = documents[kind]
        raw, _ = _committed_blob(repository, source, path)
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise CanonicalControlError(
                f"prospective schema digest differs from governed overlay: {kind}"
            )
        schema = parse_json(raw)
        if schema.get("$id") != expected_id:
            raise CanonicalControlError(
                f"prospective schema identifier differs from governed overlay: {kind}"
            )
        schemas[kind] = schema
    if tuple(schemas) != tuple(policy):
        raise CanonicalControlError("prospective schema order is inconsistent")
    return schemas


def _require_selected_schema(
    repository: GitRepository,
    source_commit: str,
    schemas: Mapping[str, Mapping[str, Any]],
    kind: str,
) -> Mapping[str, Any]:
    try:
        supplied = schemas[kind]
        _, path = READINESS_V1_1_SCHEMA_POLICY[kind]
        expected_id, expected_sha256 = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind]
    except KeyError as exc:
        raise CanonicalControlError(f"governed prerequisite schema is absent: {kind}") from exc
    raw, _ = _committed_blob(repository, source_commit, path)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CanonicalControlError(f"governed prerequisite schema digest differs: {kind}")
    committed = parse_json(raw)
    if committed.get("$id") != expected_id or supplied != committed:
        raise CanonicalControlError(f"governed prerequisite schema was substituted: {kind}")
    return supplied


def load_readiness_test_policy_v2(
    repository: GitRepository,
    source_commit: str,
    *,
    schemas: Mapping[str, Mapping[str, Any]],
) -> BoundReadinessTestPolicyV2:
    raw, git_identity = _committed_blob(
        repository, source_commit, READINESS_TEST_POLICY_V2_PATH
    )
    material = parse_canonical_bytes(raw)
    validate_json_schema_instance(
        material,
        _require_selected_schema(
            repository, source_commit, schemas, "readiness-test-policy"
        ),
        schema_registry={},
    )
    validate_readiness_test_policy_v2(material)
    if material["policy_identifier"] != PROSPECTIVE_POLICY_IDENTIFIER:
        raise CanonicalControlError("prospective readiness-test policy identifier differs")
    for selector in (
        *material["required_selectors"],
        *material["launch_smoke_selectors"],
    ):
        selector_path = selector.split("::", 1)[0]
        _committed_blob(repository, source_commit, selector_path)
    for path in material["collection_affecting_paths"]:
        _committed_blob(repository, source_commit, path)
    return BoundReadinessTestPolicyV2(
        material,
        READINESS_TEST_POLICY_V2_PATH,
        git_identity,
        hashlib.sha256(raw).hexdigest(),
    )


def _control_component_identity(
    repository: GitRepository,
    source_commit: str,
    *,
    identifier: str,
    role: str,
    path: str,
) -> str:
    raw, git_identity = _committed_blob(repository, source_commit, path)
    component = {
        "component_identifier": identifier,
        "component_identity": "0" * 64,
        "git_object_identity": git_identity,
        "path": path,
        "role": role,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return reconstruct_control_component_identity(component)


def _reconstruct_committed_control_component(
    repository: GitRepository,
    source_commit: str,
    component: Mapping[str, Any],
) -> str:
    raw, git_identity = _committed_blob(
        repository, source_commit, component["path"]
    )
    if (
        component["git_object_identity"] != git_identity
        or component["sha256"] != hashlib.sha256(raw).hexdigest()
    ):
        raise CanonicalControlError(
            "control-storage component bytes differ from committed authority"
        )
    reconstructed = reconstruct_control_component_identity(component)
    if reconstructed != component["component_identity"]:
        raise CanonicalControlError(
            "control-storage component identity does not reconstruct"
        )
    return reconstructed


def _reconstruct_control_storage_contract_identity(
    repository: GitRepository,
    source_commit: str,
    material: Mapping[str, Any],
) -> tuple[str, str]:
    component_identity = _reconstruct_committed_control_component(
        repository, source_commit, material["control_storage_component"]
    )
    identity_material = material["control_storage_contract_identity_material"]
    if identity_material["control_storage_component_identity"] != component_identity:
        raise CanonicalControlError(
            "control-storage contract binds another committed component"
        )
    contract_identity = domain_identity(
        CONTROL_STORAGE_CONTRACT_IDENTITY_DOMAIN, identity_material
    )
    if contract_identity != material["control_storage_contract_identity"]:
        raise CanonicalControlError(
            "control-storage contract identity does not reconstruct"
        )
    return component_identity, contract_identity


def load_attempt_authority_contract(
    repository: GitRepository,
    source_commit: str,
    *,
    schemas: Mapping[str, Mapping[str, Any]],
    requested_attempt_kind: str,
) -> BoundAttemptAuthorityContract:
    if requested_attempt_kind not in {"official", "reproduction"}:
        raise CanonicalControlError("requested attempt kind is unsupported")
    raw, git_identity = _committed_blob(
        repository, source_commit, ATTEMPT_AUTHORITY_CONTRACT_PATH
    )
    material = parse_canonical_bytes(raw)
    validate_json_schema_instance(
        material,
        _require_selected_schema(
            repository, source_commit, schemas, "attempt-authority-contract"
        ),
        schema_registry={},
    )
    reconstructed = domain_identity(
        ALLOCATION_AUTHORITY_IDENTITY_DOMAIN,
        material["allocation_authority_identity_material"],
    )
    if reconstructed != material["allocation_authority_identity"]:
        raise CanonicalControlError("allocation-authority identity does not reconstruct")
    authority_raw, _ = _committed_blob(
        repository, source_commit, REPOSITORY_AUTHORITY_PATH
    )
    repository_authority = load_repository_authority_bytes(authority_raw)
    if (
        material["allocation_authority_identity_material"][
            "repository_authority_identifier"
        ]
        != repository_authority.repository_authority_identifier
    ):
        raise CanonicalControlError(
            "allocation authority is bound to another repository authority"
        )
    if requested_attempt_kind not in material["supported_attempt_kinds"]:
        raise CanonicalControlError(
            f"attempt authority does not support {requested_attempt_kind}"
        )
    allocator_contract_identity = _control_component_identity(
        repository,
        source_commit,
        identifier=material["allocator_implementation_identifier"],
        role="allocator_contract",
        path=ALLOCATOR_IMPLEMENTATION_PATH,
    )
    if allocator_contract_identity != material["allocator_contract_identity"]:
        raise CanonicalControlError("allocator-contract identity does not reconstruct")
    allocator_client_identity = _control_component_identity(
        repository,
        source_commit,
        identifier=material["allocator_client_identifier"],
        role="allocator_client",
        path=ALLOCATOR_IMPLEMENTATION_PATH,
    )
    (
        control_storage_component_identity,
        control_storage_contract_identity,
    ) = _reconstruct_control_storage_contract_identity(
        repository, source_commit, material
    )
    return BoundAttemptAuthorityContract(
        material,
        ATTEMPT_AUTHORITY_CONTRACT_PATH,
        git_identity,
        hashlib.sha256(raw).hexdigest(),
        reconstructed,
        allocator_contract_identity,
        allocator_client_identity,
        control_storage_component_identity,
        control_storage_contract_identity,
    )


def _load_adapter(
    repository: GitRepository,
    source_commit: str,
    *,
    schemas: Mapping[str, Mapping[str, Any]],
    experiment_identifier: str,
) -> tuple[AdapterRegistryV1, AdapterDeclarationV1, Mapping[str, Any]]:
    registry_raw, _ = _committed_blob(repository, source_commit, ADAPTER_REGISTRY_PATH)
    registry = load_adapter_registry_bytes(
        registry_raw,
        schema=_require_selected_schema(
            repository, source_commit, schemas, "adapter-registry"
        ),
    )
    reference = registry.descriptor_reference(experiment_identifier)
    descriptor_raw, _ = _committed_blob(
        repository, source_commit, reference["descriptor_path"]
    )
    if hashlib.sha256(descriptor_raw).hexdigest() != reference["descriptor_sha256"]:
        raise CanonicalControlError("adapter descriptor digest differs from registry")
    adapter = load_adapter_declaration_bytes(
        descriptor_raw,
        schema=_require_selected_schema(
            repository, source_commit, schemas, "adapter-declaration"
        ),
    )
    if (
        adapter.experiment_identifier != reference["experiment_identifier"]
        or adapter.adapter_identifier != reference["adapter_identifier"]
        or adapter.adapter_identity != reference["descriptor_identity"]
    ):
        raise CanonicalControlError("adapter descriptor differs from registry reference")
    binding_raw, _ = _committed_blob(
        repository, source_commit, adapter.material["implementation_binding_path"]
    )
    binding = parse_canonical_bytes(binding_raw)
    validate_json_schema_instance(
        binding,
        _require_selected_schema(
            repository, source_commit, schemas, "implementation-binding"
        ),
        schema_registry={},
    )
    validate_implementation_binding(binding, object_format=repository.object_format())
    expected = {
        "adapter_identifier": adapter.adapter_identifier,
        "entry_point": adapter.material["implementation_entry_point"],
        "execution_specification_identity": adapter.material[
            "execution_specification"
        ]["specification_identity"],
        "experiment_configuration_identity": adapter.material["configuration"][
            "experiment_configuration_identity"
        ],
        "experiment_identifier": adapter.experiment_identifier,
        "profile_identity": adapter.material["execution_profile"]["profile_identity"],
    }
    for field, value in expected.items():
        if binding[field] != value:
            raise CanonicalControlError(
                f"adapter implementation binding differs: {field}"
            )
    implementation_raw, implementation_git_identity = _committed_blob(
        repository, source_commit, binding["implementation"]["path"]
    )
    if (
        hashlib.sha256(implementation_raw).hexdigest()
        != binding["implementation"]["sha256"]
        or implementation_git_identity != binding["implementation"]["git_blob_identity"]
    ):
        raise CanonicalControlError("adapter implementation bytes differ from binding")
    return registry, adapter, binding


def load_profile_contracts(
    repository: GitRepository,
    source_commit: str,
    *,
    schemas: Mapping[str, Mapping[str, Any]],
    adapter: AdapterDeclarationV1,
) -> BoundProfileContracts:
    declarations: dict[str, Mapping[str, Any]] = {}
    for reference in adapter.material["evidence_preparation"][
        "profile_contract_declarations"
    ]:
        raw, _ = _committed_blob(repository, source_commit, reference["path"])
        if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
            raise CanonicalControlError("profile contract digest differs from adapter")
        contract = parse_canonical_bytes(raw)
        validate_json_schema_instance(
            contract,
            _require_selected_schema(
                repository, source_commit, schemas, "profile-contract"
            ),
            schema_registry={},
        )
        identifier = contract["contract_identifier"]
        if identifier != reference["contract_identifier"]:
            raise CanonicalControlError("profile contract identifier differs from adapter")
        if identifier in declarations:
            raise CanonicalControlError("duplicate profile contract declaration")
        identity_material = dict(contract)
        claimed = identity_material.pop("contract_identity")
        if (
            claimed != reference["identity"]
            or claimed != domain_identity(PROFILE_CONTRACT_DOMAIN, identity_material)
        ):
            raise CanonicalControlError("profile contract identity does not reconstruct")
        declarations[identifier] = contract
    profile = {
        **adapter.material["execution_profile"],
        "declarations": declarations,
        "outcome_policy": adapter.material["outcome_policy"],
    }
    evidence = validate_profile_contract(
        profile, artifact_declarations=adapter.material["artifacts"]["declarations"]
    )
    return BoundProfileContracts(declarations, evidence)


def validate_attempt_output_declaration(
    adapter: AdapterDeclarationV1,
    attempt_authority: BoundAttemptAuthorityContract,
) -> str:
    artifact_evidence = validate_artifact_declarations(
        adapter.material["artifacts"]["declarations"],
        profile_name=adapter.material["execution_profile"]["profile_name"],
    )
    ordered_artifacts = sorted(
        adapter.material["artifacts"]["declarations"],
        key=lambda item: item["artifact_identifier"],
    )
    expected_material = {
        "adapter_identifier": adapter.adapter_identifier,
        "allocation_authority_identity": (
            attempt_authority.allocation_authority_identity
        ),
        "allocator_contract_identity": attempt_authority.allocator_contract_identity,
        "artifact_declaration_identities": [
            item["declaration_identity"] for item in ordered_artifacts
        ],
        "attempt_output_declaration_schema_revision": (
            "attempt-output-declaration-identity-material-v1"
        ),
        "control_storage_contract_identity": (
            attempt_authority.control_storage_contract_identity
        ),
        "experiment_identifier": adapter.experiment_identifier,
        "output_namespace_identity_policy": attempt_authority.material[
            "output_namespace_identity_policy"
        ],
        "output_policy_identity": artifact_evidence["output_policy_identity"],
        "output_policy_revision": "readiness-v1-output-policy",
    }
    supplied = adapter.material["attempt_output_declaration_identity_material"]
    if supplied != expected_material:
        raise CanonicalControlError(
            "attempt-output declaration differs from reconstructed authority"
        )
    reconstructed = domain_identity(
        ATTEMPT_OUTPUT_DECLARATION_IDENTITY_DOMAIN, expected_material
    )
    if reconstructed != adapter.material["attempt_output_declaration_identity"]:
        raise CanonicalControlError(
            "attempt-output declaration identity does not reconstruct"
        )
    return reconstructed


def validate_prerequisite_source_scopes(
    repository: GitRepository,
    source_commit: str,
    raw_scopes: Sequence[Mapping[str, Any]],
    *,
    required_roles: Mapping[str, str],
    required_nesting: Mapping[str, tuple[str, str]] | None = None,
) -> tuple[SourceScopeDeclarationV1, ...]:
    scopes = tuple(
        SourceScopeDeclarationV1.from_mapping(
            item, object_format=repository.object_format()
        )
        for item in raw_scopes
    )
    paths = [scope.repository_path for scope in scopes]
    if not paths or paths != sorted(paths) or len(paths) != len(set(paths)):
        raise CanonicalControlError(
            "prerequisite source scopes are duplicated or noncanonical"
        )
    by_path = {scope.repository_path: scope for scope in scopes}
    for scope in scopes:
        entry = repository.tree_entry(source_commit, scope.repository_path)
        permitted = (
            entry.object_type == "blob" and entry.mode == "100644"
        ) or (entry.object_type == "tree" and entry.mode == "040000")
        if not permitted:
            raise CanonicalControlError("prerequisite source scope is unsafe")
        if (
            entry.mode != scope.git_mode
            or entry.object_identity != scope.git_object_identity
        ):
            raise CanonicalControlError(
                "prerequisite source scope identity differs from S"
            )
        if scope.nesting == "nested":
            parent = by_path.get(scope.parent_path)
            if (
                parent is None
                or parent.nesting != "contains_declared_children"
                or not scope.repository_path.startswith(scope.parent_path + "/")
            ):
                raise CanonicalControlError(
                    "nested prerequisite source scope has no governed parent"
                )
        for candidate in scopes:
            if scope.repository_path == candidate.repository_path:
                continue
            if scope.repository_path.startswith(candidate.repository_path + "/"):
                if scope.nesting != "nested":
                    raise CanonicalControlError(
                        "overlapping prerequisite source scope is ambiguous"
                    )
    for path, role in required_roles.items():
        scope = by_path.get(path)
        if scope is None or scope.role != role:
            raise CanonicalControlError(
                f"required prerequisite source scope is absent: {role}:{path}"
            )
    for path, (nesting, parent_path) in (required_nesting or {}).items():
        scope = by_path.get(path)
        if scope is None or scope.nesting != nesting or scope.parent_path != parent_path:
            raise CanonicalControlError(
                f"required prerequisite source scope nesting differs: {path}"
            )
    role_counts: dict[str, int] = {}
    for scope in scopes:
        role_counts[scope.role] = role_counts.get(scope.role, 0) + 1
    for role in _SINGLETON_PREREQUISITE_ROLES:
        if role_counts.get(role, 0) > 1:
            raise CanonicalControlError(
                f"singleton prerequisite source-scope role is duplicated: {role}"
            )
    return scopes


def load_readiness_prerequisite_contracts(
    repository: GitRepository,
    source_commit: str,
    *,
    experiment_identifier: str,
    requested_attempt_kind: str,
    source_scopes: Sequence[Mapping[str, Any]],
) -> ReadinessPrerequisiteContracts:
    """Load one complete prospective declaration set without performing it."""

    source = repository.resolve_commit(source_commit)
    schemas = load_prospective_schemas(
        repository, source, ProspectiveRegistryGeneration.READINESS_V1_1
    )
    policy = load_readiness_test_policy_v2(repository, source, schemas=schemas)
    registry, adapter, binding = _load_adapter(
        repository,
        source,
        schemas=schemas,
        experiment_identifier=experiment_identifier,
    )
    attempt_authority = load_attempt_authority_contract(
        repository,
        source,
        schemas=schemas,
        requested_attempt_kind=requested_attempt_kind,
    )
    profiles = load_profile_contracts(
        repository, source, schemas=schemas, adapter=adapter
    )
    validate_attempt_output_declaration(adapter, attempt_authority)
    control_storage_path = attempt_authority.material[
        "control_storage_component"
    ]["path"]
    required_control_paths = {
        ALLOCATOR_IMPLEMENTATION_PATH,
        control_storage_path,
        ORCHESTRATOR_IMPLEMENTATION_PATH,
        OUTCOME_GATE_IMPLEMENTATION_PATH,
    }
    governed_paths = set(adapter.material["governed_scope_paths"])
    required_adapter_paths = {
        ATTEMPT_AUTHORITY_CONTRACT_PATH,
        SOURCE_TREE_PATH,
        binding["implementation"]["path"],
        *(reference["path"] for reference in adapter.material["evidence_preparation"]["profile_contract_declarations"]),
        *required_control_paths,
    }
    if not required_adapter_paths.issubset(governed_paths):
        raise CanonicalControlError(
            "adapter does not govern every prerequisite authority path"
        )
    for path in (ORCHESTRATOR_IMPLEMENTATION_PATH, OUTCOME_GATE_IMPLEMENTATION_PATH):
        _committed_blob(repository, source, path)
    required_roles = {
        READINESS_TEST_POLICY_V2_PATH: "readiness_test_policy",
        ATTEMPT_AUTHORITY_CONTRACT_PATH: "configuration",
        ADAPTER_REGISTRY_PATH: "configuration",
        REPOSITORY_AUTHORITY_PATH: "repository_authority",
        binding["implementation"]["path"]: "implementation",
        ALLOCATOR_IMPLEMENTATION_PATH: "control_plane",
        control_storage_path: "control_plane",
        ORCHESTRATOR_IMPLEMENTATION_PATH: "control_plane",
        OUTCOME_GATE_IMPLEMENTATION_PATH: "control_plane",
        READINESS_V1_1_SCHEMA_POLICY["readiness-test-policy"][1]: "readiness_schema",
        SOURCE_TREE_PATH: "source_tree",
    }
    for selector in (
        *policy.material["required_selectors"],
        *policy.material["launch_smoke_selectors"],
    ):
        required_roles[selector.split("::", 1)[0]] = "readiness_tests"
    for path in policy.material["collection_affecting_paths"]:
        required_roles[path] = "dependency_manifest"
    descriptor_reference = registry.descriptor_reference(experiment_identifier)
    required_roles[descriptor_reference["descriptor_path"]] = "configuration"
    required_roles[adapter.material["implementation_binding_path"]] = "configuration"
    for reference in adapter.material["evidence_preparation"][
        "profile_contract_declarations"
    ]:
        required_roles[reference["path"]] = "configuration"
    nested_under_source = {
        path: ("nested", SOURCE_TREE_PATH)
        for path in required_roles
        if path.startswith(SOURCE_TREE_PATH + "/")
    }
    nested_under_source[SOURCE_TREE_PATH] = ("contains_declared_children", "")
    scopes = validate_prerequisite_source_scopes(
        repository,
        source,
        source_scopes,
        required_roles=required_roles,
        required_nesting=nested_under_source,
    )
    return ReadinessPrerequisiteContracts(
        source,
        schemas,
        policy,
        registry,
        adapter,
        attempt_authority,
        profiles,
        binding,
        scopes,
    )


__all__ = [
    "ADAPTER_REGISTRY_PATH",
    "ALLOCATION_AUTHORITY_IDENTITY_DOMAIN",
    "ATTEMPT_OUTPUT_DECLARATION_IDENTITY_DOMAIN",
    "ALLOCATOR_IMPLEMENTATION_PATH",
    "ATTEMPT_AUTHORITY_CONTRACT_PATH",
    "BoundAttemptAuthorityContract",
    "BoundProfileContracts",
    "BoundReadinessTestPolicyV2",
    "CONTROL_STORAGE_CONTRACT_IDENTITY_DOMAIN",
    "ORCHESTRATOR_IMPLEMENTATION_PATH",
    "OUTCOME_GATE_IMPLEMENTATION_PATH",
    "PROSPECTIVE_POLICY_IDENTIFIER",
    "SOURCE_TREE_PATH",
    "ProspectiveRegistryGeneration",
    "ReadinessPrerequisiteContracts",
    "load_attempt_authority_contract",
    "load_profile_contracts",
    "load_prospective_schemas",
    "load_readiness_prerequisite_contracts",
    "load_readiness_test_policy_v2",
    "prospective_schema_policy",
    "validate_attempt_output_declaration",
    "validate_prerequisite_source_scopes",
]
