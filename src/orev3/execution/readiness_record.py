"""Readiness-v1 control models, schemas, paths, and identity reconstruction.

The objects in this module are declarative only.  They cannot execute an
experiment, allocate an attempt, or establish the complete EXECUTION_READY
invariant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from orev3.execution.canonical import (
    CanonicalControlError,
    domain_identity,
    normalize_experiment_identifier,
    parse_canonical_bytes,
    require_boolean,
    require_git_object,
    require_integer,
    require_sha256,
    require_sorted_unique,
    require_string,
    validate_exact_fields,
    validate_repository_path,
)


READINESS_RECORD_DOMAIN = "orev3:experiment-execution-readiness:v1\n"
LAUNCH_AUTHORITY_DOMAIN = "orev3:experiment-launch-authority-snapshot:v1\n"
DOCUMENT_BINDING_DOMAIN = "orev3:readiness-document-binding:v1\n"
IMPLEMENTATION_IDENTITY_DOMAIN = "orev3:readiness-implementation:v1\n"
PROTOCOL_BINDING_DOMAIN = "orev3:experiment-protocol-binding:v1\n"
CONTROL_COMPONENT_DOMAIN = "orev3:readiness-control-component:v1\n"
TEST_POLICY_DOMAIN = "orev3:readiness-test-policy:v1\n"
READINESS_SPECIFICATION_REVISION = "experiment-execution-readiness-v1"
READINESS_SPECIFICATION_SHA256 = (
    "6aea25aac1b701619bde4db309fdeb341a4fc3fd790e6ee9fcfa4414e9a9db6b"
)
READINESS_RECORD_SCHEMA_VERSION = 1
LAUNCH_AUTHORITY_SCHEMA_VERSION = 1
CANONICAL_ENCODING_REVISION = "readiness-v1-canonical-json"
MAX_READINESS_RECORD_BYTES = 1_048_576
MAX_PROTOCOL_BINDING_BYTES = 1_048_576
MAX_READINESS_TEST_POLICY_IDENTIFIER_CODEPOINTS = 128
MAX_READINESS_TEST_SELECTORS = 1_024
MAX_READINESS_TEST_SELECTOR_CODEPOINTS = 512

REPOSITORY_AUTHORITY_PATH = (
    "config/research/readiness/repository-authority-v1.json"
)
READINESS_TEST_POLICY_PATH = (
    "config/research/readiness/readiness-test-policy-v1.json"
)
READINESS_SPECIFICATION_PATH = (
    "docs/research/specifications/experiment-execution-readiness-v1.md"
)
PHASE2_SCHEMA_REGISTRY_IDENTIFIER = "readiness-phase2-schema-registry-v1"
PHASE2_SCHEMA_POLICY = {
    "implementation-binding": (
        "implementation-binding-v1",
        "src/orev3/execution/schemas/v1/implementation-binding.schema.json",
    ),
    "launch-authority-snapshot": (
        "launch-authority-snapshot-v1",
        "src/orev3/execution/schemas/v1/launch-authority-snapshot.schema.json",
    ),
    "readiness-record": (
        "readiness-record-v1",
        "src/orev3/execution/schemas/v1/readiness-record.schema.json",
    ),
    "readiness-test-policy": (
        "readiness-test-policy-v1",
        "src/orev3/execution/schemas/v1/readiness-test-policy.schema.json",
    ),
    "repository-authority": (
        "repository-authority-v1",
        "src/orev3/execution/schemas/v1/repository-authority.schema.json",
    ),
    "source-scope": (
        "source-scope-v1",
        "src/orev3/execution/schemas/v1/source-scope.schema.json",
    ),
}
PHASE2_SCHEMA_DOCUMENT_POLICY = {
    "implementation-binding": (
        "orev3://schemas/execution-readiness/v1/implementation-binding",
        "e477b1301340b216b9a9310eb96750ab7881d85e7fbece9652c4e89490812acb",
    ),
    "launch-authority-snapshot": (
        "orev3://schemas/execution-readiness/v1/launch-authority-snapshot",
        "da5a5ed23f4095fe812c6a84e6798bfd7ec707f0db0ba3a1ba22776b9ccafb9e",
    ),
    "readiness-record": (
        "orev3://schemas/execution-readiness/v1/readiness-record",
        "c354fa32d8882b8fd8231fa4fed0d943b6cac28dec43fe879d5df525f9d163b7",
    ),
    "readiness-test-policy": (
        "orev3://schemas/execution-readiness/v1/readiness-test-policy",
        "ff76640e1e460f9b5d63d9c8f455ba6955a0b25642d92f0c5c07a312066d1410",
    ),
    "repository-authority": (
        "orev3://schemas/execution-readiness/v1/repository-authority",
        "05bea86ebbcc9631da12b929c6b96f0b2111dee245ed198c894f75396d466029",
    ),
    "source-scope": (
        "orev3://schemas/execution-readiness/v1/source-scope",
        "921938ec88ede21282bdbff191ab361751f127c27649d51d0eae28fc76c5ceb5",
    ),
}

_SAFE_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]*")
_FULL_REF = re.compile(r"refs/heads/[A-Za-z0-9._/-]+")
_ENTRY_POINT = re.compile(
    r"[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_.]*"
)

_SOURCE_ROLES = frozenset(
    {
        "configuration",
        "control_plane",
        "dependency_manifest",
        "execution_specification",
        "implementation",
        "protocol",
        "readiness_schema",
        "readiness_specification",
        "readiness_test_policy",
        "readiness_tests",
        "repository_authority",
        "runtime_manifest",
        "source_tree",
    }
)
_NESTING = frozenset({"top_level", "contains_declared_children", "nested"})
_CONTROL_ROLES = frozenset(
    {
        "adapter",
        "adapter_registry",
        "allocator_client",
        "allocator_contract",
        "canonical_serializer",
        "official_orchestrator",
        "outcome_gate",
        "readiness_validator",
    }
)
_OUTCOME_CAPABILITIES = frozenset(
    {"outcome_aware_authorized_only", "prohibited_and_not_performed"}
)
_COLLISION_POLICIES = frozenset({"reject_any_existing_path"})


@dataclass(frozen=True, slots=True)
class RepositoryEndpoint:
    transport: str
    canonical_endpoint: str


@dataclass(frozen=True, slots=True)
class RepositoryAuthorityV1:
    schema_version: int
    repository_authority_identifier: str
    git_object_format: str
    approved_branch_ref: str
    canonical_fetch_endpoints: tuple[RepositoryEndpoint, ...]

    @classmethod
    def from_mapping(cls, material: Mapping[str, Any]) -> "RepositoryAuthorityV1":
        validate_repository_authority(material)
        return cls(
            schema_version=material["schema_version"],
            repository_authority_identifier=material[
                "repository_authority_identifier"
            ],
            git_object_format=material["git_object_format"],
            approved_branch_ref=material["approved_branch_ref"],
            canonical_fetch_endpoints=tuple(
                RepositoryEndpoint(item["transport"], item["canonical_endpoint"])
                for item in material["canonical_fetch_endpoints"]
            ),
        )


@dataclass(frozen=True, slots=True)
class SourceScopeDeclarationV1:
    repository_path: str
    role: str
    nesting: str
    git_object_identity: str
    git_mode: str
    parent_path: str = ""

    @classmethod
    def from_mapping(
        cls, material: Mapping[str, Any], *, object_format: str = "sha1"
    ) -> "SourceScopeDeclarationV1":
        validate_source_scope(material, object_format=object_format)
        return cls(
            repository_path=material["repository_path"],
            role=material["role"],
            nesting=material["nesting"],
            git_object_identity=material["git_object_identity"],
            git_mode=material["git_mode"],
            parent_path=material.get("parent_path", ""),
        )


@dataclass(frozen=True, slots=True)
class ReadinessRecordV1:
    material: Mapping[str, Any]
    readiness_identity: str
    experiment_identifier: str
    canonical_record_path: str
    repository_authority_identifier: str
    approved_branch_ref: str
    source_commit: str
    source_scopes: tuple[SourceScopeDeclarationV1, ...]

    @classmethod
    def from_mapping(cls, material: Mapping[str, Any]) -> "ReadinessRecordV1":
        validate_readiness_record(material)
        reconstructed = reconstruct_readiness_identity(material)
        if reconstructed != material["readiness_identity"]:
            raise CanonicalControlError("readiness identity does not reconstruct")
        authority = material["git_authority"]
        experiment = material["experiment"]
        object_format = _object_format_from_identity(authority["source_commit"])
        return cls(
            material=dict(material),
            readiness_identity=material["readiness_identity"],
            experiment_identifier=experiment["experiment_identifier"],
            canonical_record_path=experiment["canonical_record_path"],
            repository_authority_identifier=authority[
                "repository_authority_identifier"
            ],
            approved_branch_ref=authority["approved_branch_ref"],
            source_commit=authority["source_commit"],
            source_scopes=tuple(
                SourceScopeDeclarationV1.from_mapping(
                    item, object_format=object_format
                )
                for item in material["source_scopes"]
            ),
        )


@dataclass(frozen=True, slots=True)
class LaunchAuthoritySnapshotV1:
    schema_version: int
    repository_authority_identifier: str
    approved_branch_ref: str
    remote_head_commit: str
    canonical_readiness_record_path: str
    readiness_record_blob_identity: str
    readiness_seal_commit: str
    readiness_identity: str
    source_commit: str
    launch_authority_snapshot_identity: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "approved_branch_ref": self.approved_branch_ref,
            "canonical_readiness_record_path": self.canonical_readiness_record_path,
            "launch_authority_snapshot_identity": (
                self.launch_authority_snapshot_identity
            ),
            "readiness_identity": self.readiness_identity,
            "readiness_record_blob_identity": self.readiness_record_blob_identity,
            "readiness_seal_commit": self.readiness_seal_commit,
            "remote_head_commit": self.remote_head_commit,
            "repository_authority_identifier": self.repository_authority_identifier,
            "schema_version": self.schema_version,
            "source_commit": self.source_commit,
        }


def canonical_readiness_record_path(experiment_identifier: str) -> PurePosixPath:
    identifier = normalize_experiment_identifier(experiment_identifier)
    return PurePosixPath(f"docs/research/readiness/{identifier}.json")


def load_repository_authority_bytes(raw: bytes) -> RepositoryAuthorityV1:
    return RepositoryAuthorityV1.from_mapping(
        parse_canonical_bytes(raw, validator=validate_repository_authority)
    )


def load_readiness_record_bytes(
    raw: bytes, *, expected_experiment_identifier: str
) -> ReadinessRecordV1:
    material = parse_canonical_bytes(
        raw,
        validator=validate_readiness_record,
        max_bytes=MAX_READINESS_RECORD_BYTES,
    )
    record = ReadinessRecordV1.from_mapping(material)
    identifier = normalize_experiment_identifier(expected_experiment_identifier)
    expected_path = str(canonical_readiness_record_path(identifier))
    if record.experiment_identifier != identifier:
        raise CanonicalControlError("record experiment identifier is not requested identifier")
    if record.canonical_record_path != expected_path:
        raise CanonicalControlError("record canonical path does not reconstruct")
    return record


def reconstruct_readiness_identity(material: Mapping[str, Any]) -> str:
    require_sha256("readiness_identity", material.get("readiness_identity"))
    identity_material = dict(material)
    del identity_material["readiness_identity"]
    return domain_identity(READINESS_RECORD_DOMAIN, identity_material)


def reconstruct_document_binding_identity(
    binding: Mapping[str, Any], *, identity_field: str
) -> str:
    material = dict(binding)
    require_sha256(identity_field, material.pop(identity_field, None))
    return domain_identity(DOCUMENT_BINDING_DOMAIN, material)


def reconstruct_control_component_identity(component: Mapping[str, Any]) -> str:
    material = dict(component)
    require_sha256("component_identity", material.pop("component_identity", None))
    return domain_identity(CONTROL_COMPONENT_DOMAIN, material)


def reconstruct_implementation_identity(implementation: Mapping[str, Any]) -> str:
    fields = {
        "adapter_identifier": implementation["adapter_identifier"],
        "entry_point": implementation["entry_point"],
        "implementation_git_blob_identity": implementation[
            "implementation_git_blob_identity"
        ],
        "implementation_path": implementation["implementation_path"],
        "implementation_sha256": implementation["implementation_sha256"],
    }
    return domain_identity(IMPLEMENTATION_IDENTITY_DOMAIN, fields)


def reconstruct_protocol_binding_identity(binding: Mapping[str, Any]) -> str:
    material = dict(binding)
    require_sha256(
        "protocol_binding_identity", material.pop("protocol_binding_identity", None)
    )
    return domain_identity(PROTOCOL_BINDING_DOMAIN, material)


def build_launch_authority_snapshot(
    *,
    repository_authority_identifier: str,
    approved_branch_ref: str,
    remote_head_commit: str,
    canonical_record_path: str,
    readiness_record_blob_identity: str,
    readiness_seal_commit: str,
    readiness_identity: str,
    source_commit: str,
    object_format: str = "sha1",
) -> LaunchAuthoritySnapshotV1:
    material = {
        "approved_branch_ref": approved_branch_ref,
        "canonical_readiness_record_path": canonical_record_path,
        "readiness_identity": readiness_identity,
        "readiness_record_blob_identity": readiness_record_blob_identity,
        "readiness_seal_commit": readiness_seal_commit,
        "remote_head_commit": remote_head_commit,
        "repository_authority_identifier": repository_authority_identifier,
        "schema_version": LAUNCH_AUTHORITY_SCHEMA_VERSION,
        "source_commit": source_commit,
    }
    identity = domain_identity(LAUNCH_AUTHORITY_DOMAIN, material)
    complete = {**material, "launch_authority_snapshot_identity": identity}
    validate_launch_authority_snapshot(complete, object_format=object_format)
    return LaunchAuthoritySnapshotV1(**complete)


def validate_repository_authority(material: Mapping[str, Any]) -> None:
    required = {
        "approved_branch_ref",
        "canonical_fetch_endpoints",
        "git_object_format",
        "repository_authority_identifier",
        "schema_version",
    }
    validate_exact_fields(material, required, label="repository authority")
    if require_integer("schema_version", material["schema_version"], minimum=1) != 1:
        raise CanonicalControlError("repository authority schema version is unsupported")
    require_string(
        "repository_authority_identifier",
        material["repository_authority_identifier"],
        pattern=_SAFE_IDENTIFIER,
    )
    if material["git_object_format"] not in {"sha1", "sha256"}:
        raise CanonicalControlError("Git object format is unsupported")
    _require_full_branch_ref(material["approved_branch_ref"])
    endpoints = require_sorted_unique(
        "canonical_fetch_endpoints",
        material["canonical_fetch_endpoints"],
        key=lambda item: item.get("canonical_endpoint", "") if isinstance(item, dict) else "",
        uniqueness=lambda item: item.get("canonical_endpoint", "") if isinstance(item, dict) else "",
    )
    if not endpoints:
        raise CanonicalControlError("canonical fetch endpoint allowlist cannot be empty")
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            raise CanonicalControlError("endpoint declaration must be an object")
        validate_exact_fields(
            endpoint, {"canonical_endpoint", "transport"}, label="endpoint"
        )
        if endpoint["transport"] not in {"https", "ssh"}:
            raise CanonicalControlError("production endpoint transport is unsupported")
        canonical = require_string("canonical_endpoint", endpoint["canonical_endpoint"])
        if "@" in canonical.split("://", 1)[-1].split("/", 1)[0] and not canonical.startswith("ssh://git@"):
            raise CanonicalControlError("credential-bearing endpoint is prohibited")
        if "?" in canonical or "#" in canonical or canonical.startswith("file:"):
            raise CanonicalControlError("endpoint contains prohibited locator material")


def validate_source_scope(
    material: Mapping[str, Any], *, object_format: str = "sha1"
) -> None:
    nesting = material.get("nesting")
    required = {
        "git_mode",
        "git_object_identity",
        "nesting",
        "repository_path",
        "role",
    }
    if nesting == "nested":
        required.add("parent_path")
    validate_exact_fields(material, required, label="source scope")
    path = validate_repository_path(material["repository_path"])
    if material["role"] not in _SOURCE_ROLES:
        raise CanonicalControlError("source scope role is unsupported")
    if nesting not in _NESTING:
        raise CanonicalControlError("source scope nesting is unsupported")
    require_git_object("git_object_identity", material["git_object_identity"], object_format)
    require_string("git_mode", material["git_mode"], pattern=re.compile(r"[0-7]{6}"))
    if nesting == "nested":
        parent = validate_repository_path(material["parent_path"], label="parent_path")
        if not path.startswith(parent + "/"):
            raise CanonicalControlError("nested source scope is outside its parent")


def validate_readiness_record(material: Mapping[str, Any]) -> None:
    top = {
        "artifacts",
        "attempt_policy",
        "configuration",
        "control_plane",
        "execution_profile",
        "execution_specification",
        "experiment",
        "external_inputs",
        "git_authority",
        "implementation",
        "outcome_policy",
        "protocol",
        "readiness_identity",
        "readiness_specification",
        "replay",
        "runtime",
        "schema",
        "source_scopes",
        "validation",
    }
    validate_exact_fields(material, top, label="readiness record")
    require_sha256("readiness_identity", material["readiness_identity"])
    authority = _mapping(material, "git_authority")
    object_format = _object_format_from_identity(authority.get("source_commit"))
    _validate_schema_section(_mapping(material, "schema"), object_format=object_format)
    _validate_experiment(_mapping(material, "experiment"))
    _validate_git_authority_binding(authority, object_format=object_format)
    _validate_document_binding(
        _mapping(material, "readiness_specification"),
        label="readiness specification",
        identity_field="specification_identity",
        object_format=object_format,
    )
    readiness_spec = material["readiness_specification"]
    if readiness_spec["revision"] != READINESS_SPECIFICATION_REVISION:
        raise CanonicalControlError("readiness specification revision is unsupported")
    if readiness_spec["sha256"] != READINESS_SPECIFICATION_SHA256:
        raise CanonicalControlError("readiness specification digest is unsupported")
    if readiness_spec["path"] != READINESS_SPECIFICATION_PATH:
        raise CanonicalControlError("readiness specification path is unsupported")
    if reconstruct_document_binding_identity(
        readiness_spec, identity_field="specification_identity"
    ) != readiness_spec["specification_identity"]:
        raise CanonicalControlError("readiness specification identity does not reconstruct")
    _validate_control_plane(
        _mapping(material, "control_plane"),
        implementation_path=_mapping(material, "implementation")["implementation_path"],
        object_format=object_format,
    )
    _validate_source_scopes(
        material["source_scopes"], material=material, object_format=object_format
    )
    _validate_document_binding(
        _mapping(material, "protocol"),
        label="protocol",
        identity_field="protocol_identity",
        includes_identifier=True,
        object_format=object_format,
    )
    if reconstruct_document_binding_identity(
        material["protocol"], identity_field="protocol_identity"
    ) != material["protocol"]["protocol_identity"]:
        raise CanonicalControlError("protocol identity does not reconstruct")
    _validate_implementation(
        _mapping(material, "implementation"), object_format=object_format
    )
    _validate_document_binding(
        _mapping(material, "execution_specification"),
        label="execution specification",
        identity_field="specification_identity",
        object_format=object_format,
    )
    if reconstruct_document_binding_identity(
        material["execution_specification"], identity_field="specification_identity"
    ) != material["execution_specification"]["specification_identity"]:
        raise CanonicalControlError("execution specification identity does not reconstruct")
    _validate_profile(_mapping(material, "execution_profile"))
    _validate_runtime(_mapping(material, "runtime"), object_format=object_format)
    _validate_configuration(_mapping(material, "configuration"))
    _validate_external_inputs(_mapping(material, "external_inputs"))
    _validate_replay(_mapping(material, "replay"))
    _validate_artifacts(_mapping(material, "artifacts"))
    _validate_outcome_policy(_mapping(material, "outcome_policy"))
    _validate_validation(_mapping(material, "validation"))
    _validate_attempt_policy(_mapping(material, "attempt_policy"))
    experiment = material["experiment"]
    authority = material["git_authority"]
    expected_path = str(
        canonical_readiness_record_path(experiment["experiment_identifier"])
    )
    if experiment["canonical_record_path"] != expected_path:
        raise CanonicalControlError("canonical record path is identity-inconsistent")
    if experiment["experiment_configuration_identity"] != material["configuration"]["experiment_configuration_identity"]:
        raise CanonicalControlError("experiment configuration identity is inconsistent")
    if material["execution_profile"]["profile_name"] != material["outcome_policy"]["profile_name"]:
        raise CanonicalControlError("profile and outcome policy disagree")
    require_git_object("source_commit", authority["source_commit"], object_format)


def validate_launch_authority_snapshot(
    material: Mapping[str, Any], *, object_format: str = "sha1"
) -> None:
    required = {
        "approved_branch_ref",
        "canonical_readiness_record_path",
        "launch_authority_snapshot_identity",
        "readiness_identity",
        "readiness_record_blob_identity",
        "readiness_seal_commit",
        "remote_head_commit",
        "repository_authority_identifier",
        "schema_version",
        "source_commit",
    }
    validate_exact_fields(material, required, label="launch authority snapshot")
    if require_integer("schema_version", material["schema_version"], minimum=1) != 1:
        raise CanonicalControlError("launch authority schema version is unsupported")
    require_string("repository_authority_identifier", material["repository_authority_identifier"], pattern=_SAFE_IDENTIFIER)
    _require_full_branch_ref(material["approved_branch_ref"])
    validate_repository_path(material["canonical_readiness_record_path"])
    for field in (
        "remote_head_commit",
        "readiness_record_blob_identity",
        "readiness_seal_commit",
        "source_commit",
    ):
        require_git_object(field, material[field], object_format)
    require_sha256("readiness_identity", material["readiness_identity"])
    require_sha256(
        "launch_authority_snapshot_identity",
        material["launch_authority_snapshot_identity"],
    )
    identity_material = dict(material)
    stored = identity_material.pop("launch_authority_snapshot_identity")
    if domain_identity(LAUNCH_AUTHORITY_DOMAIN, identity_material) != stored:
        raise CanonicalControlError("launch authority snapshot identity does not reconstruct")


def _mapping(parent: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    value = parent[field]
    if not isinstance(value, dict):
        raise CanonicalControlError(f"{field} must be an object")
    return value


def _object_format_from_identity(value: Any) -> str:
    if isinstance(value, str) and len(value) == 40:
        require_git_object("Git identity", value, "sha1")
        return "sha1"
    if isinstance(value, str) and len(value) == 64:
        require_git_object("Git identity", value, "sha256")
        return "sha256"
    raise CanonicalControlError("source commit does not identify a supported Git object format")


def _require_full_branch_ref(value: Any) -> str:
    ref = require_string("approved_branch_ref", value, pattern=_FULL_REF)
    if ".." in ref or "@{" in ref or ref.endswith((".", "/")) or "//" in ref:
        raise CanonicalControlError("approved branch ref is invalid")
    return ref


def _validate_schema_section(
    value: Mapping[str, Any], *, object_format: str
) -> None:
    validate_exact_fields(
        value,
        {"canonical_encoding_revision", "declarations", "schema_registry_identifier"},
        label="schema section",
    )
    require_string("schema_registry_identifier", value["schema_registry_identifier"], pattern=_SAFE_IDENTIFIER)
    if value["schema_registry_identifier"] != PHASE2_SCHEMA_REGISTRY_IDENTIFIER:
        raise CanonicalControlError("schema registry identifier is unsupported")
    if value["canonical_encoding_revision"] != CANONICAL_ENCODING_REVISION:
        raise CanonicalControlError("canonical encoding revision is unsupported")
    declarations = require_sorted_unique(
        "schema declarations",
        value["declarations"],
        key=lambda item: item.get("object_kind", "") if isinstance(item, dict) else "",
        uniqueness=lambda item: item.get("object_kind", "") if isinstance(item, dict) else "",
    )
    expected_kinds = tuple(sorted(PHASE2_SCHEMA_POLICY))
    actual_kinds = tuple(item.get("object_kind", "") for item in declarations)
    if actual_kinds != expected_kinds:
        raise CanonicalControlError("Phase-2 schema registry is incomplete or unexpected")
    for item in declarations:
        if not isinstance(item, dict):
            raise CanonicalControlError("schema declaration must be an object")
        validate_exact_fields(
            item,
            {"byte_count", "git_blob_identity", "object_kind", "path", "schema_identifier", "sha256"},
            label="schema declaration",
        )
        require_string("object_kind", item["object_kind"], pattern=_SAFE_IDENTIFIER)
        require_string("schema_identifier", item["schema_identifier"], pattern=_SAFE_IDENTIFIER)
        validate_repository_path(item["path"])
        require_integer("byte_count", item["byte_count"])
        require_sha256("sha256", item["sha256"])
        require_git_object("git_blob_identity", item["git_blob_identity"], object_format)
        expected_identifier, expected_path = PHASE2_SCHEMA_POLICY[item["object_kind"]]
        if item["schema_identifier"] != expected_identifier or item["path"] != expected_path:
            raise CanonicalControlError("schema declaration conflicts with repository policy")
        expected_digest = PHASE2_SCHEMA_DOCUMENT_POLICY[item["object_kind"]][1]
        if item["sha256"] != expected_digest:
            raise CanonicalControlError("schema declaration digest conflicts with repository policy")


def _validate_experiment(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"canonical_record_path", "experiment_configuration_identity", "experiment_identifier"}, label="experiment")
    normalize_experiment_identifier(value["experiment_identifier"])
    validate_repository_path(value["canonical_record_path"])
    require_sha256("experiment_configuration_identity", value["experiment_configuration_identity"])


def _validate_git_authority_binding(
    value: Mapping[str, Any], *, object_format: str
) -> None:
    validate_exact_fields(value, {"approved_branch_ref", "repository_authority_identifier", "source_commit"}, label="Git authority binding")
    require_string("repository_authority_identifier", value["repository_authority_identifier"], pattern=_SAFE_IDENTIFIER)
    _require_full_branch_ref(value["approved_branch_ref"])
    require_git_object("source_commit", value["source_commit"], object_format)


def _validate_document_binding(
    value: Mapping[str, Any],
    *,
    label: str,
    identity_field: str,
    includes_identifier: bool = False,
    object_format: str,
) -> None:
    required = {"byte_count", "git_blob_identity", identity_field, "path", "revision", "sha256"}
    if includes_identifier:
        required.add("identifier")
    validate_exact_fields(value, required, label=label)
    validate_repository_path(value["path"])
    require_string("revision", value["revision"])
    if includes_identifier:
        require_string("identifier", value["identifier"], pattern=_SAFE_IDENTIFIER)
    require_integer("byte_count", value["byte_count"])
    require_sha256("sha256", value["sha256"])
    require_git_object("git_blob_identity", value["git_blob_identity"], object_format)
    require_sha256(identity_field, value[identity_field])


def _validate_control_plane(
    value: Mapping[str, Any], *, implementation_path: str, object_format: str
) -> None:
    validate_exact_fields(value, {"components"}, label="control plane")
    components = require_sorted_unique("control-plane components", value["components"], key=lambda item: item.get("component_identifier", "") if isinstance(item, dict) else "")
    roles: set[str] = set()
    role_paths = {
        "adapter": implementation_path,
        "adapter_registry": "src/orev3/execution/registry.py",
        "allocator_client": "src/orev3/execution/attempts.py",
        "allocator_contract": "src/orev3/execution/attempts.py",
        "canonical_serializer": "src/orev3/execution/canonical.py",
        "official_orchestrator": "src/orev3/execution/orchestrator.py",
        "outcome_gate": "src/orev3/execution/outcome_gate.py",
        "readiness_validator": "src/orev3/execution/readiness.py",
    }
    for item in components:
        if not isinstance(item, dict):
            raise CanonicalControlError("control-plane component must be an object")
        validate_exact_fields(item, {"component_identifier", "component_identity", "git_object_identity", "path", "role", "sha256"}, label="control-plane component")
        require_string("component_identifier", item["component_identifier"], pattern=_SAFE_IDENTIFIER)
        if item["role"] not in _CONTROL_ROLES:
            raise CanonicalControlError("control-plane component role is unsupported")
        if item["role"] in roles:
            raise CanonicalControlError("control-plane component role is duplicated")
        roles.add(item["role"])
        validate_repository_path(item["path"])
        if item["path"] != role_paths[item["role"]]:
            raise CanonicalControlError(
                "control-plane component path conflicts with repository policy"
            )
        require_git_object("git_object_identity", item["git_object_identity"], object_format)
        require_sha256("sha256", item["sha256"])
        require_sha256("component_identity", item["component_identity"])
        if reconstruct_control_component_identity(item) != item["component_identity"]:
            raise CanonicalControlError("control-plane component identity does not reconstruct")
    if roles != _CONTROL_ROLES:
        raise CanonicalControlError("control-plane component roles are incomplete")


def _validate_source_scopes(
    value: Any, *, material: Mapping[str, Any], object_format: str
) -> None:
    scopes = require_sorted_unique("source scopes", value, key=lambda item: (item.get("repository_path", ""), item.get("role", "")) if isinstance(item, dict) else ("", ""), uniqueness=lambda item: item.get("repository_path", "") if isinstance(item, dict) else "")
    if not scopes:
        raise CanonicalControlError("source scopes cannot be empty")
    parsed = [
        SourceScopeDeclarationV1.from_mapping(item, object_format=object_format)
        for item in scopes
    ]
    paths = {item.repository_path: item for item in parsed}
    if "src/orev3" not in paths or paths["src/orev3"].role != "source_tree":
        raise CanonicalControlError("complete src/orev3 source scope is required")
    implementation = material["implementation"]
    required: dict[str, tuple[str, str, str]] = {
        "src/orev3": ("source_tree", "contains_declared_children", ""),
        "src/orev3/execution": (
            "control_plane",
            "nested",
            "src/orev3",
        ),
        "src/orev3/execution/schemas/v1": (
            "readiness_schema",
            "nested",
            "src/orev3",
        ),
        material["protocol"]["path"]: ("protocol", "top_level", ""),
        material["execution_specification"]["path"]: (
            "execution_specification",
            "top_level",
            "",
        ),
        READINESS_SPECIFICATION_PATH: ("readiness_specification", "top_level", ""),
        REPOSITORY_AUTHORITY_PATH: ("repository_authority", "top_level", ""),
        READINESS_TEST_POLICY_PATH: ("readiness_test_policy", "top_level", ""),
        "tests/execution": ("readiness_tests", "top_level", ""),
        material["runtime"]["dependency_manifest_path"]: (
            "dependency_manifest",
            "top_level",
            "",
        ),
        implementation["implementation_path"]: (
            "implementation",
            "nested",
            "src/orev3",
        ),
        implementation["protocol_binding_path"]: (
            "configuration",
            "top_level",
            "",
        ),
    }
    for path, (role, nesting, parent_path) in required.items():
        scope = paths.get(path)
        if scope is None or scope.role != role or scope.nesting != nesting:
            raise CanonicalControlError(
                f"mandatory governed scope is missing or misclassified: {path}"
            )
        if nesting == "nested" and scope.parent_path != parent_path:
            raise CanonicalControlError(
                f"mandatory governed scope has the wrong parent: {path}"
            )
    role_counts: dict[str, int] = {}
    for scope in parsed:
        role_counts[scope.role] = role_counts.get(scope.role, 0) + 1
    for singleton in (
        "configuration",
        "control_plane",
        "dependency_manifest",
        "execution_specification",
        "implementation",
        "protocol",
        "readiness_schema",
        "readiness_specification",
        "readiness_test_policy",
        "readiness_tests",
        "repository_authority",
        "source_tree",
    ):
        if role_counts.get(singleton) != 1:
            raise CanonicalControlError(
                f"mandatory governed scope role must occur exactly once: {singleton}"
            )
    for scope in parsed:
        if scope.nesting == "nested":
            parent = paths.get(scope.parent_path)
            if parent is None or parent.nesting != "contains_declared_children":
                raise CanonicalControlError("nested source scope has no declared containing scope")
        for other in parsed:
            if scope.repository_path == other.repository_path:
                continue
            if scope.repository_path.startswith(other.repository_path + "/"):
                if scope.nesting != "nested":
                    raise CanonicalControlError("source scope overlap is not explicit")
                ancestors: set[str] = set()
                cursor = scope
                while cursor.nesting == "nested":
                    ancestors.add(cursor.parent_path)
                    cursor = paths[cursor.parent_path]
                shared_explicit_parent = (
                    other.nesting == "nested"
                    and other.parent_path == scope.parent_path
                )
                if other.repository_path not in ancestors and not shared_explicit_parent:
                    raise CanonicalControlError("source scope nesting is ambiguous")


def _validate_implementation(
    value: Mapping[str, Any], *, object_format: str
) -> None:
    validate_exact_fields(
        value,
        {
            "adapter_identifier",
            "entry_point",
            "implementation_git_blob_identity",
            "implementation_identity",
            "implementation_path",
            "implementation_sha256",
            "protocol_binding_byte_count",
            "protocol_binding_git_blob_identity",
            "protocol_binding_identity",
            "protocol_binding_path",
            "protocol_binding_sha256",
        },
        label="implementation",
    )
    require_string("adapter_identifier", value["adapter_identifier"], pattern=_SAFE_IDENTIFIER)
    require_string("entry_point", value["entry_point"], pattern=_ENTRY_POINT)
    validate_repository_path(value["implementation_path"])
    require_git_object(
        "implementation_git_blob_identity",
        value["implementation_git_blob_identity"],
        object_format,
    )
    require_sha256("implementation_sha256", value["implementation_sha256"])
    require_sha256("implementation_identity", value["implementation_identity"])
    validate_repository_path(value["protocol_binding_path"])
    protocol_binding_byte_count = require_integer(
        "protocol_binding_byte_count", value["protocol_binding_byte_count"]
    )
    if protocol_binding_byte_count > MAX_PROTOCOL_BINDING_BYTES:
        raise CanonicalControlError(
            "protocol_binding_byte_count exceeds the readiness-v1 schema maximum"
        )
    require_git_object(
        "protocol_binding_git_blob_identity",
        value["protocol_binding_git_blob_identity"],
        object_format,
    )
    require_sha256("protocol_binding_sha256", value["protocol_binding_sha256"])
    require_sha256("protocol_binding_identity", value["protocol_binding_identity"])
    if reconstruct_implementation_identity(value) != value["implementation_identity"]:
        raise CanonicalControlError("implementation identity does not reconstruct")


def _validate_profile(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"profile_identity", "profile_name"}, label="execution profile")
    require_string("profile_name", value["profile_name"], pattern=_SAFE_IDENTIFIER)
    require_sha256("profile_identity", value["profile_identity"])


def _validate_runtime(value: Mapping[str, Any], *, object_format: str) -> None:
    required = {"dependency_manifest_git_blob_identity", "dependency_manifest_path", "dependency_manifest_sha256", "environment_contract_identity", "python_implementation", "python_version", "runtime_identity"}
    validate_exact_fields(value, required, label="runtime")
    require_string("python_implementation", value["python_implementation"])
    require_string("python_version", value["python_version"])
    require_sha256("runtime_identity", value["runtime_identity"])
    validate_repository_path(value["dependency_manifest_path"])
    require_sha256("dependency_manifest_sha256", value["dependency_manifest_sha256"])
    require_git_object(
        "dependency_manifest_git_blob_identity",
        value["dependency_manifest_git_blob_identity"],
        object_format,
    )
    require_sha256("environment_contract_identity", value["environment_contract_identity"])


def _validate_configuration(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"decision_selection_identity", "experiment_configuration_identity"}, label="configuration")
    require_sha256("experiment_configuration_identity", value["experiment_configuration_identity"])
    require_sha256("decision_selection_identity", value["decision_selection_identity"])


def _validate_external_inputs(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"declarations"}, label="external inputs")
    declarations = require_sorted_unique(
        "external input declarations",
        value["declarations"],
        key=lambda item: (
            item.get("role", ""),
            tuple(
                member.get("member_path", "")
                for member in item.get("members", [])
                if isinstance(member, dict)
            ),
            item.get("external_input_identifier", ""),
        )
        if isinstance(item, dict)
        else ("", (), ""),
        uniqueness=lambda item: item.get("external_input_identifier", "")
        if isinstance(item, dict)
        else "",
    )
    for item in declarations:
        if not isinstance(item, dict):
            raise CanonicalControlError("external input declaration must be an object")
        validate_exact_fields(item, {"external_input_identifier", "external_input_identity", "input_kind", "members", "parser_identity", "role", "schema_identity"}, label="external input declaration")
        require_string("external_input_identifier", item["external_input_identifier"], pattern=_SAFE_IDENTIFIER)
        require_string("role", item["role"], pattern=_SAFE_IDENTIFIER)
        if item["input_kind"] not in {"regular_file", "ordered_file_collection"}:
            raise CanonicalControlError("external input kind is unsupported")
        require_sha256("external_input_identity", item["external_input_identity"])
        require_sha256("parser_identity", item["parser_identity"])
        require_sha256("schema_identity", item["schema_identity"])
        members = item["members"]
        if not isinstance(members, list) or not members:
            raise CanonicalControlError("external input members must be a nonempty ordered array")
        paths: set[str] = set()
        for member in members:
            if not isinstance(member, dict):
                raise CanonicalControlError("external input member must be an object")
            validate_exact_fields(member, {"byte_count", "member_path", "sha256"}, label="external input member")
            path = validate_repository_path(member["member_path"], label="member_path")
            if path in paths:
                raise CanonicalControlError("external input member path is duplicated")
            paths.add(path)
            require_integer("byte_count", member["byte_count"])
            require_sha256("sha256", member["sha256"])
        if item["input_kind"] == "regular_file" and len(members) != 1:
            raise CanonicalControlError("regular-file input requires exactly one member")


def _validate_replay(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"candidate_order", "construction_identity", "decision_selection_order", "population_accounting_identity", "replay_identity"}, label="replay")
    for field in ("construction_identity", "population_accounting_identity", "replay_identity"):
        require_sha256(field, value[field])
    candidates = value["candidate_order"]
    if not isinstance(candidates, list) or not candidates or any(isinstance(item, bool) or not isinstance(item, int) for item in candidates) or len(candidates) != len(set(candidates)):
        raise CanonicalControlError("candidate order must be a nonempty unique integer array")
    order = value["decision_selection_order"]
    if not isinstance(order, list) or not order or any(not isinstance(item, str) or not item for item in order) or len(order) != len(set(order)):
        raise CanonicalControlError("decision selection order must be a nonempty unique string array")


def _validate_artifacts(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"declarations"}, label="artifacts")
    declarations = require_sorted_unique("artifact declarations", value["declarations"], key=lambda item: item.get("artifact_identifier", "") if isinstance(item, dict) else "")
    for item in declarations:
        if not isinstance(item, dict):
            raise CanonicalControlError("artifact declaration must be an object")
        validate_exact_fields(item, {"artifact_identifier", "artifact_kind", "declaration_identity", "dependency_roles", "relative_path"}, label="artifact declaration")
        require_string("artifact_identifier", item["artifact_identifier"], pattern=_SAFE_IDENTIFIER)
        require_string("artifact_kind", item["artifact_kind"], pattern=_SAFE_IDENTIFIER)
        validate_repository_path(item["relative_path"], label="artifact relative_path")
        require_sha256("declaration_identity", item["declaration_identity"])
        roles = item["dependency_roles"]
        if not isinstance(roles, list) or roles != sorted(roles) or len(roles) != len(set(roles)) or any(not isinstance(role, str) or not role for role in roles):
            raise CanonicalControlError("artifact dependency roles must be sorted and unique")


def _validate_outcome_policy(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"authorization_contract_identity", "outcome_capability", "policy_identity", "profile_name"}, label="outcome policy")
    require_string("profile_name", value["profile_name"], pattern=_SAFE_IDENTIFIER)
    if value["outcome_capability"] not in _OUTCOME_CAPABILITIES:
        raise CanonicalControlError("outcome capability is unsupported")
    require_sha256("authorization_contract_identity", value["authorization_contract_identity"])
    require_sha256("policy_identity", value["policy_identity"])


def _validate_validation(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"compile_passed", "import_passed", "reconstruction_passed", "test_policy_identity", "test_results_identity", "test_selectors"}, label="validation")
    for field in ("compile_passed", "import_passed", "reconstruction_passed"):
        require_boolean(field, value[field])
    require_sha256("test_policy_identity", value["test_policy_identity"])
    require_sha256("test_results_identity", value["test_results_identity"])
    selectors = require_sorted_unique("test selectors", value["test_selectors"], key=lambda item: item)
    if not selectors or any(not isinstance(item, str) or not item for item in selectors):
        raise CanonicalControlError("test selectors must be nonempty canonical strings")


def _validate_attempt_policy(value: Mapping[str, Any]) -> None:
    validate_exact_fields(value, {"allocator_contract_identity", "attempt_identity_domain", "collision_policy", "output_policy_identity"}, label="attempt policy")
    require_sha256("allocator_contract_identity", value["allocator_contract_identity"])
    require_string("attempt_identity_domain", value["attempt_identity_domain"])
    require_sha256("output_policy_identity", value["output_policy_identity"])
    if value["collision_policy"] not in _COLLISION_POLICIES:
        raise CanonicalControlError("collision policy is unsupported")


def validate_implementation_binding(
    material: Mapping[str, Any], *, object_format: str = "sha1"
) -> None:
    validate_exact_fields(
        material,
        {
            "adapter_identifier",
            "entry_point",
            "execution_specification_identity",
            "experiment_configuration_identity",
            "experiment_identifier",
            "implementation",
            "profile_identity",
            "protocol",
            "protocol_binding_identity",
            "schema_version",
        },
        label="implementation protocol binding",
    )
    if material["schema_version"] != 1:
        raise CanonicalControlError("implementation binding schema version is unsupported")
    normalize_experiment_identifier(material["experiment_identifier"])
    require_string("adapter_identifier", material["adapter_identifier"], pattern=_SAFE_IDENTIFIER)
    require_string("entry_point", material["entry_point"], pattern=_ENTRY_POINT)
    require_sha256(
        "execution_specification_identity",
        material["execution_specification_identity"],
    )
    require_sha256(
        "experiment_configuration_identity",
        material["experiment_configuration_identity"],
    )
    require_sha256("profile_identity", material["profile_identity"])
    implementation = _mapping(material, "implementation")
    validate_exact_fields(
        implementation,
        {"git_blob_identity", "path", "sha256"},
        label="bound implementation",
    )
    validate_repository_path(implementation["path"])
    require_git_object(
        "implementation git_blob_identity",
        implementation["git_blob_identity"],
        object_format,
    )
    require_sha256("implementation sha256", implementation["sha256"])
    protocol = _mapping(material, "protocol")
    validate_exact_fields(
        protocol,
        {"identifier", "revision", "sha256"},
        label="bound protocol",
    )
    require_string("protocol identifier", protocol["identifier"], pattern=_SAFE_IDENTIFIER)
    require_string("protocol revision", protocol["revision"])
    require_sha256("protocol sha256", protocol["sha256"])
    require_sha256("protocol_binding_identity", material["protocol_binding_identity"])
    if reconstruct_protocol_binding_identity(material) != material["protocol_binding_identity"]:
        raise CanonicalControlError("protocol binding identity does not reconstruct")


def validate_readiness_test_policy(material: Mapping[str, Any]) -> None:
    validate_exact_fields(
        material,
        {
            "policy_identifier",
            "policy_identity",
            "required_selectors",
            "schema_version",
        },
        label="readiness test policy",
    )
    if material["schema_version"] != 1:
        raise CanonicalControlError("readiness test policy version is unsupported")
    policy_identifier = require_string(
        "policy_identifier", material["policy_identifier"], pattern=_SAFE_IDENTIFIER
    )
    if len(policy_identifier) > MAX_READINESS_TEST_POLICY_IDENTIFIER_CODEPOINTS:
        raise CanonicalControlError(
            "readiness test policy identifier exceeds the schema maximum"
        )
    selectors = require_sorted_unique(
        "required selectors", material["required_selectors"], key=lambda item: item
    )
    if not selectors or any(not isinstance(item, str) or not item for item in selectors):
        raise CanonicalControlError("readiness test policy selectors are invalid")
    if len(selectors) > MAX_READINESS_TEST_SELECTORS:
        raise CanonicalControlError(
            "readiness test policy selector count exceeds the schema maximum"
        )
    if any(
        len(selector) > MAX_READINESS_TEST_SELECTOR_CODEPOINTS
        for selector in selectors
    ):
        raise CanonicalControlError(
            "readiness test policy selector length exceeds the schema maximum"
        )
    require_sha256("policy_identity", material["policy_identity"])
    identity_material = dict(material)
    stored = identity_material.pop("policy_identity")
    if domain_identity(TEST_POLICY_DOMAIN, identity_material) != stored:
        raise CanonicalControlError("readiness test policy identity does not reconstruct")


__all__ = [
    "CANONICAL_ENCODING_REVISION",
    "CONTROL_COMPONENT_DOMAIN",
    "DOCUMENT_BINDING_DOMAIN",
    "IMPLEMENTATION_IDENTITY_DOMAIN",
    "LAUNCH_AUTHORITY_DOMAIN",
    "LaunchAuthoritySnapshotV1",
    "READINESS_RECORD_DOMAIN",
    "READINESS_SPECIFICATION_PATH",
    "READINESS_SPECIFICATION_REVISION",
    "READINESS_SPECIFICATION_SHA256",
    "READINESS_TEST_POLICY_PATH",
    "REPOSITORY_AUTHORITY_PATH",
    "PHASE2_SCHEMA_POLICY",
    "PHASE2_SCHEMA_DOCUMENT_POLICY",
    "PHASE2_SCHEMA_REGISTRY_IDENTIFIER",
    "PROTOCOL_BINDING_DOMAIN",
    "ReadinessRecordV1",
    "RepositoryAuthorityV1",
    "SourceScopeDeclarationV1",
    "build_launch_authority_snapshot",
    "canonical_readiness_record_path",
    "load_readiness_record_bytes",
    "load_repository_authority_bytes",
    "reconstruct_readiness_identity",
    "reconstruct_control_component_identity",
    "reconstruct_document_binding_identity",
    "reconstruct_implementation_identity",
    "reconstruct_protocol_binding_identity",
    "validate_implementation_binding",
    "validate_launch_authority_snapshot",
    "validate_readiness_record",
    "validate_repository_authority",
    "validate_readiness_test_policy",
    "validate_source_scope",
]
