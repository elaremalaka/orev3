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
READINESS_TEST_POLICY_V2_PATH = (
    "config/research/readiness/readiness-test-policy-v2.json"
)
READINESS_SPECIFICATION_PATH = (
    "docs/research/specifications/experiment-execution-readiness-v1.md"
)
READINESS_SPECIFICATION_V1_1_PATH = (
    "docs/research/specifications/experiment-execution-readiness-v1.1.md"
)
READINESS_SPECIFICATION_V1_1_REVISION = "experiment-execution-readiness-v1.1"
READINESS_SPECIFICATION_V1_1_SHA256 = (
    "e938499cc254ce2d65fce925fb6e33c5d8b9dcea73a91a2c01e1017e8fb17da9"
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
        "1aac9f934c4d58274578519098d1b1762637a3e77902d0b43dd2fef4866f8886",
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
PHASE3A_SCHEMA_REGISTRY_IDENTIFIER = "readiness-phase3a-schema-registry-v1"
PHASE3A_SCHEMA_POLICY = {
    **PHASE2_SCHEMA_POLICY,
    "adapter-declaration": (
        "adapter-declaration-v1",
        "src/orev3/execution/schemas/v1/adapter-declaration.schema.json",
    ),
    "adapter-registry": (
        "adapter-registry-v1",
        "src/orev3/execution/schemas/v1/adapter-registry.schema.json",
    ),
    "offline-artifact-manifest": (
        "offline-artifact-manifest-v1",
        "src/orev3/execution/schemas/v1/offline-artifact-manifest.schema.json",
    ),
    "runtime-contract": (
        "runtime-contract-v1",
        "src/orev3/execution/schemas/v1/runtime-contract.schema.json",
    ),
}
PHASE3A_SCHEMA_DOCUMENT_POLICY = {
    **PHASE2_SCHEMA_DOCUMENT_POLICY,
    "adapter-declaration": (
        "orev3://schemas/execution-readiness/v1/adapter-declaration",
        "55fccfb6984b2a565f2d02abc913f76306f774f4e7445ff31c1cb74ffb418cc4",
    ),
    "adapter-registry": (
        "orev3://schemas/execution-readiness/v1/adapter-registry",
        "012b5f0f874a350987e21f53937d5994d52a7c213456c6ce3818f526884d318a",
    ),
    "offline-artifact-manifest": (
        "orev3://schemas/execution-readiness/v1/offline-artifact-manifest",
        "cfa3606e0c5737fe0679f1152b7c5fbde123fb9ccb834d57d80b18a15416fd53",
    ),
    "runtime-contract": (
        "orev3://schemas/execution-readiness/v1/runtime-contract",
        "d67aa372c7913051051b09cf35138a7c17d34e6f06f13c16c4ca522e376bb00e",
    ),
}
PHASE3B_SCHEMA_REGISTRY_IDENTIFIER = "readiness-phase3b-schema-registry-v1"
PHASE3B_SCHEMA_POLICY = {
    **PHASE3A_SCHEMA_POLICY,
    "artifact-declaration-evidence": (
        "artifact-declaration-evidence-v1",
        "src/orev3/execution/schemas/v1/artifact-declaration-evidence.schema.json",
    ),
    "dataset-validation-evidence": (
        "dataset-validation-evidence-v1",
        "src/orev3/execution/schemas/v1/dataset-validation-evidence.schema.json",
    ),
    "evidence-preparation-policy": (
        "evidence-preparation-policy-v1",
        "src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json",
    ),
    "evidence-preparation": (
        "evidence-preparation-v1",
        "src/orev3/execution/schemas/v1/evidence-preparation.schema.json",
    ),
    "immutable-input-snapshot": (
        "immutable-input-snapshot-v1",
        "src/orev3/execution/schemas/v1/immutable-input-snapshot.schema.json",
    ),
    "outcome-blind-projection-evidence": (
        "outcome-blind-projection-evidence-v1",
        "src/orev3/execution/schemas/v1/outcome-blind-projection-evidence.schema.json",
    ),
    "population-accounting-evidence": (
        "population-accounting-evidence-v1",
        "src/orev3/execution/schemas/v1/population-accounting-evidence.schema.json",
    ),
    "profile-conformance-evidence": (
        "profile-conformance-evidence-v1",
        "src/orev3/execution/schemas/v1/profile-conformance-evidence.schema.json",
    ),
    "readiness-test-evidence": (
        "readiness-test-evidence-v1",
        "src/orev3/execution/schemas/v1/readiness-test-evidence.schema.json",
    ),
    "replay-evidence": (
        "replay-evidence-v1",
        "src/orev3/execution/schemas/v1/replay-evidence.schema.json",
    ),
}
PHASE3B_SCHEMA_DOCUMENT_POLICY = {
    **PHASE3A_SCHEMA_DOCUMENT_POLICY,
    "artifact-declaration-evidence": ("orev3://schemas/execution-readiness/v1/artifact-declaration-evidence", "8e003c64196398d9880a68c77d228dd6cb4938edab2a2971ad3354c7c4127c4d"),
    "dataset-validation-evidence": ("orev3://schemas/execution-readiness/v1/dataset-validation-evidence", "a79ebbdeb2f3822354b910808bde88e56ff55b39cce476ab540695c48d03d7a8"),
    "evidence-preparation-policy": ("orev3://schemas/execution-readiness/v1/evidence-preparation-policy", "315cdf396c03098678235b558b8e5569973e1221b2dc878b52d8bab3ebc98b81"),
    "evidence-preparation": ("orev3://schemas/execution-readiness/v1/evidence-preparation", "15538013df0b35a9514756963cb591b875101169cd98b04cf37b53290fc14731"),
    "immutable-input-snapshot": ("orev3://schemas/execution-readiness/v1/immutable-input-snapshot", "173e943980c87d27a4e27acdefc915fd5b5cd43a121b0058388f3072c6b81ce9"),
    "outcome-blind-projection-evidence": ("orev3://schemas/execution-readiness/v1/outcome-blind-projection-evidence", "44725f9357d2361ca1185eac74468e1cfe382cf418145198f88d342a753bfb75"),
    "population-accounting-evidence": ("orev3://schemas/execution-readiness/v1/population-accounting-evidence", "115edbf8775f334cb7d60f2174e72a043ac05112d5b53ebaf3cfeacfd1257384"),
    "profile-conformance-evidence": ("orev3://schemas/execution-readiness/v1/profile-conformance-evidence", "7778a2d0cab2ca491452e89162ddb99da952a9f34cbf1192f4356ee0590684bc"),
    "readiness-test-evidence": ("orev3://schemas/execution-readiness/v1/readiness-test-evidence", "58b73eeade341e47d812f855b73958bd3d469c3dab47c1f942d7de829dd2b01f"),
    "replay-evidence": ("orev3://schemas/execution-readiness/v1/replay-evidence", "a2666f32cc87d824c9e357cbb03534bfeaf5ac6c9f7ebd16e38ee38621b6d4d0"),
}
PROSPECTIVE_PHASE2_SCHEMA_POLICY = {
    **PHASE2_SCHEMA_POLICY,
    "readiness-record": (
        "readiness-record-v2",
        "src/orev3/execution/schemas/v1/readiness-record-v2.schema.json",
    ),
    "readiness-test-policy": (
        "readiness-test-policy-v2",
        "src/orev3/execution/schemas/v1/readiness-test-policy-v2.schema.json",
    ),
}
PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY = {
    **PHASE2_SCHEMA_DOCUMENT_POLICY,
    "readiness-record": (
        "orev3://schemas/execution-readiness/v1/readiness-record-v2",
        "2436da1b932237a005cb703d210a6baee8e56b466bd54de0ac6a58d2d227e068",
    ),
    "readiness-test-policy": (
        "orev3://schemas/execution-readiness/v1/readiness-test-policy-v2",
        "2c09e2088c116b4fd2b2ee2cb60f193d5923c01a9c21e38766f3a3326d17b11b",
    ),
}
PROSPECTIVE_PHASE3A_SCHEMA_POLICY = {
    **PHASE3A_SCHEMA_POLICY,
    "readiness-record": PROSPECTIVE_PHASE2_SCHEMA_POLICY["readiness-record"],
    "adapter-declaration": (
        "adapter-declaration-v3",
        "src/orev3/execution/schemas/v1/adapter-declaration-v3.schema.json",
    ),
    "readiness-test-policy": PROSPECTIVE_PHASE2_SCHEMA_POLICY[
        "readiness-test-policy"
    ],
}
PROSPECTIVE_PHASE3A_SCHEMA_DOCUMENT_POLICY = {
    **PHASE3A_SCHEMA_DOCUMENT_POLICY,
    "readiness-record": PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY[
        "readiness-record"
    ],
    "adapter-declaration": (
        "orev3://schemas/execution-readiness/v1/adapter-declaration-v3",
        "e6b9294498f7b51d34c7e8c03bf18516dfd0a840ba340fddfb9ba919a8fe4d72",
    ),
    "readiness-test-policy": PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY[
        "readiness-test-policy"
    ],
}
PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_POLICY = {
    **PROSPECTIVE_PHASE3A_SCHEMA_POLICY,
    "adapter-declaration": (
        "adapter-declaration-v4",
        "src/orev3/execution/schemas/v1/adapter-declaration-v4.schema.json",
    ),
}
PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_DOCUMENT_POLICY = {
    **PROSPECTIVE_PHASE3A_SCHEMA_DOCUMENT_POLICY,
    "adapter-declaration": (
        "orev3://schemas/execution-readiness/v1/adapter-declaration-v4",
        "985fd13cff1ca5d399a1f254879c397167d75c0355c0d066a22441d7e2d3ab70",
    ),
}
PROSPECTIVE_PHASE3B_SCHEMA_POLICY = {
    **PHASE3B_SCHEMA_POLICY,
    "readiness-record": PROSPECTIVE_PHASE2_SCHEMA_POLICY["readiness-record"],
    "adapter-declaration": PROSPECTIVE_PHASE3A_SCHEMA_POLICY[
        "adapter-declaration"
    ],
    "readiness-test-policy": PROSPECTIVE_PHASE2_SCHEMA_POLICY[
        "readiness-test-policy"
    ],
    "profile-conformance-evidence": (
        "profile-conformance-evidence-v2",
        "src/orev3/execution/schemas/v1/profile-conformance-evidence-v2.schema.json",
    ),
    "replay-evidence": (
        "replay-evidence-v2",
        "src/orev3/execution/schemas/v1/replay-evidence-v2.schema.json",
    ),
    "population-accounting-evidence": (
        "population-accounting-evidence-v2",
        "src/orev3/execution/schemas/v1/population-accounting-evidence-v2.schema.json",
    ),
    "evidence-preparation": (
        "evidence-preparation-v2",
        "src/orev3/execution/schemas/v1/evidence-preparation-v2.schema.json",
    ),
}
PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY = {
    **PHASE3B_SCHEMA_DOCUMENT_POLICY,
    "readiness-record": PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY[
        "readiness-record"
    ],
    "adapter-declaration": PROSPECTIVE_PHASE3A_SCHEMA_DOCUMENT_POLICY[
        "adapter-declaration"
    ],
    "readiness-test-policy": PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY[
        "readiness-test-policy"
    ],
    "profile-conformance-evidence": (
        "orev3://schemas/execution-readiness/v1/profile-conformance-evidence-v2",
        "c8f31746b8252988583bf2df83855536baf40ef3dfe2dc869e27ee5479ec21cb",
    ),
    "replay-evidence": (
        "orev3://schemas/execution-readiness/v1/replay-evidence-v2",
        "124b27cd9458697e3fff9e9f52305b2a416718abcbd08bcfe62692ca14912b0e",
    ),
    "population-accounting-evidence": (
        "orev3://schemas/execution-readiness/v1/population-accounting-evidence-v2",
        "5f311c04486fb2f71634a4b165004d6088b18699562500d8a6b1a5f2a4745991",
    ),
    "evidence-preparation": (
        "orev3://schemas/execution-readiness/v1/evidence-preparation-v2",
        "44cf31c797e777dc17ed33d8e04597dd45c5f7d49e98adf4f67c66f34aa190b5",
    ),
}
PROSPECTIVE_ADAPTER_V4_PHASE3B_SCHEMA_POLICY = {
    **PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
    "adapter-declaration": PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_POLICY[
        "adapter-declaration"
    ],
}
PROSPECTIVE_ADAPTER_V4_PHASE3B_SCHEMA_DOCUMENT_POLICY = {
    **PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY,
    "adapter-declaration": PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_DOCUMENT_POLICY[
        "adapter-declaration"
    ],
}
READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER = "readiness-v1-schema-registry-v1"
READINESS_V1_1_SCHEMA_POLICY = dict(
    sorted(
        {
            **PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
            "attempt-allocation": (
                "attempt-allocation-v1",
                "src/orev3/execution/schemas/v1/attempt-allocation.schema.json",
            ),
            "attempt-authority-contract": (
                "attempt-authority-contract-v1",
                "src/orev3/execution/schemas/v1/attempt-authority-contract.schema.json",
            ),
            "attempt-control-record": (
                "attempt-control-record-v1",
                "src/orev3/execution/schemas/v1/attempt-control-record.schema.json",
            ),
            "attempt-identity-material": (
                "attempt-identity-material-v1",
                "src/orev3/execution/schemas/v1/attempt-identity-material.schema.json",
            ),
            "execution-control-manifest": (
                "execution-control-manifest-v1",
                "src/orev3/execution/schemas/v1/execution-control-manifest.schema.json",
            ),
            "outcome-authorization": (
                "outcome-authorization-v1",
                "src/orev3/execution/schemas/v1/outcome-authorization.schema.json",
            ),
            "output-namespace-identity-material": (
                "output-namespace-identity-material-v1",
                "src/orev3/execution/schemas/v1/output-namespace-identity-material.schema.json",
            ),
            "profile-contract": (
                "profile-contract-v1",
                "src/orev3/execution/schemas/v1/profile-contract.schema.json",
            ),
            "readiness-failure-receipt": (
                "readiness-failure-receipt-v1",
                "src/orev3/execution/schemas/v1/readiness-failure-receipt.schema.json",
            ),
        }.items()
    )
)
READINESS_V1_1_SCHEMA_DOCUMENT_POLICY = dict(
    sorted(
        {
            **PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY,
            "attempt-allocation": (
                "orev3://schemas/execution-readiness/v1/attempt-allocation",
                "57d38f63b0fd8196d8d5cef207cf7481d164421ba59496f0e38149b46881ffaf",
            ),
            "attempt-authority-contract": (
                "orev3://schemas/execution-readiness/v1/attempt-authority-contract",
                "81b6baff7d3776d3891134bd3e26a3c791f4eadd14ab534bbd797752786ab677",
            ),
            "attempt-control-record": (
                "orev3://schemas/execution-readiness/v1/attempt-control-record",
                "76b48b204325589cc3014f0f8335311fab09ee8fdf95913127a5f990848c2310",
            ),
            "attempt-identity-material": (
                "orev3://schemas/execution-readiness/v1/attempt-identity-material",
                "ce2b69e1b0466318c54350f2237d52529f1b43ac14820138e05a2a3db63e71fa",
            ),
            "execution-control-manifest": (
                "orev3://schemas/execution-readiness/v1/execution-control-manifest",
                "9464054245b0d85bb39fd2c8cb3549ef346bfc68612a5b709b4ee7b32bfa018f",
            ),
            "outcome-authorization": (
                "orev3://schemas/execution-readiness/v1/outcome-authorization",
                "a5b6dd23c5f82d9fc2c3690935809479f07d764725fbdc058ba2ae4cafc7e426",
            ),
            "output-namespace-identity-material": (
                "orev3://schemas/execution-readiness/v1/output-namespace-identity-material",
                "deb02a2375d3479b0bb2129bda15e3aa9992713a22d944f4e78fa4b7a5b283c3",
            ),
            "profile-contract": (
                "orev3://schemas/execution-readiness/v1/profile-contract",
                "117e0d32b9afcf4b76763842a3b9b9d7ed36d5a21c8f5b90d227f57338ae9298",
            ),
            "readiness-failure-receipt": (
                "orev3://schemas/execution-readiness/v1/readiness-failure-receipt",
                "00e5d18b39e2a7f0e42536647c39b2478e946caca51773258feb337b2e5a54ad",
            ),
        }.items()
    )
)
READINESS_V1_1_SCHEMA_KIND_ORDER = (
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
READINESS_V1_1_SCHEMA_POLICY = {
    kind: READINESS_V1_1_SCHEMA_POLICY[kind]
    for kind in READINESS_V1_1_SCHEMA_KIND_ORDER
}
READINESS_V1_1_SCHEMA_DOCUMENT_POLICY = {
    kind: READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind]
    for kind in READINESS_V1_1_SCHEMA_KIND_ORDER
}
PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_POLICY = {
    **READINESS_V1_1_SCHEMA_POLICY,
    "adapter-declaration": PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_POLICY[
        "adapter-declaration"
    ],
}
PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_DOCUMENT_POLICY = {
    **READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
    "adapter-declaration": PROSPECTIVE_ADAPTER_V4_PHASE3A_SCHEMA_DOCUMENT_POLICY[
        "adapter-declaration"
    ],
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
class ReadinessRecordV2:
    """Prospective v1.1 candidate material without lifecycle authority."""

    material: Mapping[str, Any]
    readiness_identity: str
    experiment_identifier: str
    source_commit: str
    canonical_record_path: str
    repository_authority_identifier: str
    approved_branch_ref: str
    source_scopes: tuple[SourceScopeDeclarationV1, ...]

    @classmethod
    def from_mapping(cls, material: Mapping[str, Any]) -> "ReadinessRecordV2":
        validate_readiness_record_v2(material)
        expected = reconstruct_readiness_identity(material)
        if material["readiness_identity"] != expected:
            raise CanonicalControlError("readiness-v2 identity does not reconstruct")
        return cls(
            material=dict(material),
            readiness_identity=expected,
            experiment_identifier=material["experiment"]["experiment_identifier"],
            source_commit=material["git_authority"]["source_commit"],
            canonical_record_path=material["experiment"]["canonical_record_path"],
            repository_authority_identifier=material["git_authority"][
                "repository_authority_identifier"
            ],
            approved_branch_ref=material["git_authority"]["approved_branch_ref"],
            source_scopes=tuple(
                SourceScopeDeclarationV1.from_mapping(item)
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


def build_readiness_record_v2(material: Mapping[str, Any]) -> ReadinessRecordV2:
    """Normalize already-reconstructed authority into a candidate data object.

    This function is deliberately pure: it writes nothing and mints no
    lifecycle state.  The caller supplies the governed 18 sections; this
    function supplies only the canonical aggregate identity.
    """

    if "readiness_identity" in material:
        raise CanonicalControlError("readiness identity is derived, not caller-selected")
    complete = dict(material)
    complete["readiness_identity"] = domain_identity(
        READINESS_RECORD_DOMAIN, dict(material)
    )
    return ReadinessRecordV2.from_mapping(complete)


def load_readiness_record_v2_bytes(raw: bytes) -> ReadinessRecordV2:
    material = parse_canonical_bytes(
        raw, validator=validate_readiness_record_v2, max_bytes=MAX_READINESS_RECORD_BYTES
    )
    return ReadinessRecordV2.from_mapping(material)


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


def validate_readiness_record_v2(material: Mapping[str, Any]) -> None:
    """Validate prospective readiness-record-v2 canonical semantics.

    Git bytes are independently checked by ``validate_record_v2_git_bindings``;
    this layer closes the data model and all cross-field relationships.
    """

    top = {
        "artifacts", "attempt_policy", "configuration", "control_plane",
        "execution_profile", "execution_specification", "experiment",
        "external_inputs", "git_authority", "implementation", "outcome_policy",
        "protocol", "readiness_identity", "readiness_specification", "replay",
        "runtime", "schema", "source_scopes", "validation",
    }
    validate_exact_fields(material, top, label="readiness-record-v2")
    require_sha256("readiness_identity", material["readiness_identity"])
    authority = _mapping(material, "git_authority")
    object_format = _object_format_from_identity(authority.get("source_commit"))
    _validate_git_authority_binding(authority, object_format=object_format)
    _validate_schema_section_v2(_mapping(material, "schema"), object_format=object_format)
    _validate_experiment(_mapping(material, "experiment"))
    for section_name, identity_field in (
        ("readiness_specification", "specification_identity"),
        ("protocol", "protocol_identity"),
        ("execution_specification", "specification_identity"),
    ):
        binding = _mapping(material, section_name)
        _validate_document_binding(
            binding, label=section_name, identity_field=identity_field,
            includes_identifier=section_name == "protocol", object_format=object_format,
        )
        if reconstruct_document_binding_identity(binding, identity_field=identity_field) != binding[identity_field]:
            raise CanonicalControlError(f"{section_name} identity does not reconstruct")
    readiness_spec = material["readiness_specification"]
    if (
        readiness_spec["path"] != READINESS_SPECIFICATION_V1_1_PATH
        or readiness_spec["revision"] != READINESS_SPECIFICATION_V1_1_REVISION
        or readiness_spec["sha256"] != READINESS_SPECIFICATION_V1_1_SHA256
    ):
        raise CanonicalControlError("readiness-v1.1 specification binding is unsupported")
    implementation = _mapping(material, "implementation")
    _validate_implementation_v2(implementation, object_format=object_format)
    _validate_control_plane_v2(
        _mapping(material, "control_plane"), implementation=implementation,
        object_format=object_format,
    )
    _validate_source_scopes_v2(material["source_scopes"], object_format=object_format)
    _validate_profile(_mapping(material, "execution_profile"))
    _validate_runtime_v2(_mapping(material, "runtime"), object_format=object_format)
    _validate_configuration_v2(_mapping(material, "configuration"))
    _validate_external_inputs_v2(_mapping(material, "external_inputs"))
    _validate_replay_v2(_mapping(material, "replay"))
    _validate_artifacts_v2(
        _mapping(material, "artifacts"),
        profile_name=material["execution_profile"]["profile_name"],
    )
    _validate_outcome_policy_v2(
        _mapping(material, "outcome_policy"), _mapping(material, "execution_profile")
    )
    _validate_validation_v2(_mapping(material, "validation"))
    _validate_attempt_policy_v2(_mapping(material, "attempt_policy"))
    experiment = material["experiment"]
    if experiment["canonical_record_path"] != str(
        canonical_readiness_record_path(experiment["experiment_identifier"])
    ):
        raise CanonicalControlError("canonical record path does not reconstruct")
    if experiment["experiment_configuration_identity"] != material["configuration"]["experiment_configuration_identity"]:
        raise CanonicalControlError("experiment configuration identity is inconsistent")
    if material["configuration"]["decision_selection_identity"] != material["replay"]["decision_selection_identity"]:
        raise CanonicalControlError("decision-selection identity is inconsistent")
    if material["execution_profile"]["profile_identity"] != material["outcome_policy"]["profile_identity"]:
        raise CanonicalControlError("profile identity is inconsistent")
    if material["artifacts"]["output_policy_identity"] != material["attempt_policy"]["output_policy_identity"]:
        raise CanonicalControlError("output-policy identity is inconsistent")
    control_by_role = {
        item["role"]: item for item in material["control_plane"]["components"]
    }
    if control_by_role["allocator_client"]["component_identity"] != material["attempt_policy"]["allocator_client_component_identity"]:
        raise CanonicalControlError("allocator-client component identity is inconsistent")
    if control_by_role["allocator_contract"]["component_identity"] != material["attempt_policy"]["allocator_contract_identity"]:
        raise CanonicalControlError("allocator-contract component identity is inconsistent")
    if reconstruct_readiness_identity(material) != material["readiness_identity"]:
        raise CanonicalControlError("readiness identity does not reconstruct")


def _validate_schema_section_v2(value: Mapping[str, Any], *, object_format: str) -> None:
    validate_exact_fields(value, {"canonical_encoding_revision", "declarations", "schema_registry_identifier"}, label="prospective schema section")
    if value["canonical_encoding_revision"] != CANONICAL_ENCODING_REVISION or value["schema_registry_identifier"] != READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER:
        raise CanonicalControlError("prospective schema registry selection is unsupported")
    declarations = require_sorted_unique(
        "prospective schema declarations", value["declarations"],
        key=lambda item: item.get("object_kind", "") if isinstance(item, dict) else "",
        uniqueness=lambda item: item.get("object_kind", "") if isinstance(item, dict) else "",
    )
    if tuple(item.get("object_kind") for item in declarations) != READINESS_V1_1_SCHEMA_KIND_ORDER:
        raise CanonicalControlError("prospective 29-kind schema registry is incomplete")
    adapter_declaration = next(
        item for item in declarations if item.get("object_kind") == "adapter-declaration"
    )
    adapter_coordinates = (
        adapter_declaration.get("registry_identifier"),
        adapter_declaration.get("path"),
        adapter_declaration.get("schema_id"),
        adapter_declaration.get("sha256"),
    )
    legacy_coordinates = (
        *READINESS_V1_1_SCHEMA_POLICY["adapter-declaration"],
        *READINESS_V1_1_SCHEMA_DOCUMENT_POLICY["adapter-declaration"],
    )
    v4_coordinates = (
        *PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_POLICY["adapter-declaration"],
        *PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_DOCUMENT_POLICY[
            "adapter-declaration"
        ],
    )
    if adapter_coordinates == legacy_coordinates:
        selected_policy = READINESS_V1_1_SCHEMA_POLICY
        selected_documents = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY
    elif adapter_coordinates == v4_coordinates:
        selected_policy = PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_POLICY
        selected_documents = PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_DOCUMENT_POLICY
    else:
        raise CanonicalControlError("prospective adapter schema generation is unsupported")
    seen_registry: set[str] = set(); seen_ids: set[str] = set(); seen_paths: set[str] = set()
    for declaration in declarations:
        validate_exact_fields(declaration, {"byte_count", "git_blob_identity", "object_kind", "path", "registry_identifier", "schema_id", "sha256"}, label="prospective schema declaration")
        kind = declaration["object_kind"]
        require_integer("byte_count", declaration["byte_count"])
        require_git_object("git_blob_identity", declaration["git_blob_identity"], object_format)
        require_sha256("sha256", declaration["sha256"])
        expected_registry, expected_path = selected_policy[kind]
        expected_id, expected_digest = selected_documents[kind]
        if (declaration["registry_identifier"], declaration["path"], declaration["schema_id"], declaration["sha256"]) != (expected_registry, expected_path, expected_id, expected_digest):
            raise CanonicalControlError("prospective schema declaration conflicts with policy")
        if declaration["registry_identifier"] in seen_registry or declaration["schema_id"] in seen_ids or declaration["path"] in seen_paths:
            raise CanonicalControlError("prospective schema authority is duplicated")
        seen_registry.add(declaration["registry_identifier"]); seen_ids.add(declaration["schema_id"]); seen_paths.add(declaration["path"])


_FIXED_CONTROL_COMPONENTS = {
    "adapter_registry": (
        "experiment-execution-readiness-adapter-registry-v1",
        "src/orev3/execution/registry.py",
    ),
    "canonical_serializer": ("canonical_serializer", "src/orev3/execution/canonical.py"),
    "official_orchestrator": ("official_orchestrator", "src/orev3/execution/orchestrator.py"),
    "outcome_gate": ("outcome_gate", "src/orev3/execution/outcome_gate.py"),
    "readiness_validator": ("readiness_validator", "src/orev3/execution/readiness.py"),
}


def _validate_control_plane_v2(value: Mapping[str, Any], *, implementation: Mapping[str, Any], object_format: str) -> None:
    validate_exact_fields(value, {"components"}, label="control plane")
    components = require_sorted_unique("control components", value["components"], key=lambda item: item.get("component_identifier", "") if isinstance(item, dict) else "")
    by_role: dict[str, Mapping[str, Any]] = {}
    for component in components:
        validate_exact_fields(component, {"component_identifier", "component_identity", "git_object_identity", "path", "role", "sha256"}, label="control component")
        role = component["role"]
        if role not in _CONTROL_ROLES or role in by_role:
            raise CanonicalControlError("control component role is unsupported or duplicated")
        by_role[role] = component
        require_git_object("git_object_identity", component["git_object_identity"], object_format)
        require_sha256("sha256", component["sha256"]); require_sha256("component_identity", component["component_identity"])
        if reconstruct_control_component_identity(component) != component["component_identity"]:
            raise CanonicalControlError("control component identity does not reconstruct")
        fixed = _FIXED_CONTROL_COMPONENTS.get(role)
        if fixed is not None and (component["component_identifier"], component["path"]) != fixed:
            raise CanonicalControlError("control component identifier/path is not governed")
    if set(by_role) != _CONTROL_ROLES:
        raise CanonicalControlError("control component roles are incomplete")
    adapter = by_role["adapter"]
    if adapter["component_identifier"] != implementation["adapter_identifier"] or adapter["path"] != implementation["implementation_path"] or adapter["git_object_identity"] != implementation["implementation_git_blob_identity"] or adapter["sha256"] != implementation["implementation_sha256"]:
        raise CanonicalControlError("adapter control component differs from implementation")


def _validate_source_scopes_v2(value: Any, *, object_format: str) -> None:
    scopes = require_sorted_unique("source scopes", value, key=lambda item: (item.get("repository_path", ""), item.get("role", "")) if isinstance(item, dict) else ("", ""), uniqueness=lambda item: item.get("repository_path", "") if isinstance(item, dict) else "")
    roles: dict[str, int] = {}
    for item in scopes:
        validate_source_scope(item, object_format=object_format)
        roles[item["role"]] = roles.get(item["role"], 0) + 1
    for role in (
        "execution_specification",
        "implementation",
        "protocol",
        "readiness_schema",
        "readiness_specification",
        "readiness_test_policy",
        "repository_authority",
        "source_tree",
    ):
        if roles.get(role) != 1:
            raise CanonicalControlError(f"singleton source-scope role must occur once: {role}")


def _validate_implementation_v2(value: Mapping[str, Any], *, object_format: str) -> None:
    required = {"adapter_identifier", "adapter_identity", "adapter_registry_identity", "entry_point", "implementation_git_blob_identity", "implementation_identity", "implementation_path", "implementation_sha256", "protocol_binding_byte_count", "protocol_binding_git_blob_identity", "protocol_binding_identity", "protocol_binding_path", "protocol_binding_sha256"}
    validate_exact_fields(value, required, label="prospective implementation")
    require_string("adapter_identifier", value["adapter_identifier"], pattern=_SAFE_IDENTIFIER)
    require_string("entry_point", value["entry_point"], pattern=_ENTRY_POINT)
    for field in ("adapter_identity", "adapter_registry_identity", "implementation_identity", "implementation_sha256", "protocol_binding_identity", "protocol_binding_sha256"):
        require_sha256(field, value[field])
    for field in ("implementation_git_blob_identity", "protocol_binding_git_blob_identity"):
        require_git_object(field, value[field], object_format)
    validate_repository_path(value["implementation_path"]); validate_repository_path(value["protocol_binding_path"])
    require_integer("protocol_binding_byte_count", value["protocol_binding_byte_count"])
    if reconstruct_implementation_identity(value) != value["implementation_identity"]:
        raise CanonicalControlError("implementation identity does not reconstruct")


def _validate_runtime_v2(value: Mapping[str, Any], *, object_format: str) -> None:
    required = {"dependency_environment_identity", "dependency_lock_git_blob_identity", "dependency_lock_identity", "dependency_lock_path", "dependency_lock_sha256", "host_system_identity", "offline_artifact_manifest_git_blob_identity", "offline_artifact_manifest_identity", "offline_artifact_manifest_path", "offline_artifact_manifest_sha256", "python_implementation", "python_version", "runtime_bundle_identity", "runtime_contract_byte_count", "runtime_contract_git_blob_identity", "runtime_contract_identity", "runtime_contract_path", "runtime_contract_sha256"}
    validate_exact_fields(value, required, label="runtime")
    for field in required:
        if field.endswith("_path"):
            validate_repository_path(value[field])
        elif field.endswith("git_blob_identity"):
            require_git_object(field, value[field], object_format)
        elif field.endswith("identity") or field.endswith("sha256"):
            require_sha256(field, value[field])
    require_integer("runtime_contract_byte_count", value["runtime_contract_byte_count"])
    require_string("python_implementation", value["python_implementation"]); require_string("python_version", value["python_version"])


def _validate_configuration_v2(value: Mapping[str, Any]) -> None:
    required = {"decision_selection_identity", "evidence_preparation_policy_identity", "experiment_configuration_identity"}
    validate_exact_fields(value, required, label="configuration")
    for field in required: require_sha256(field, value[field])


def _validate_external_inputs_v2(value: Mapping[str, Any]) -> None:
    from orev3.execution.registry import validate_external_input_declaration_v3
    required = {"dataset_validation_evidence_identities", "declarations", "input_snapshot_identities", "projection_evidence_identities"}
    validate_exact_fields(value, required, label="external inputs")
    declarations = value["declarations"]
    expected_order = sorted(declarations, key=lambda item: (item["role"], item["members"][0]["member_path"], item["external_input_identifier"]))
    if declarations != expected_order:
        raise CanonicalControlError("external input declarations are not canonical")
    identifiers: set[str] = set(); roles: set[str] = set(); first_paths: set[str] = set()
    for declaration in declarations:
        validate_external_input_declaration_v3(declaration)
        identifier = declaration["external_input_identifier"]; role = declaration["role"]; path = declaration["members"][0]["member_path"]
        if identifier in identifiers or role in roles or path in first_paths:
            raise CanonicalControlError("external input authority is duplicated")
        identifiers.add(identifier); roles.add(role); first_paths.add(path)
    snapshots = value["input_snapshot_identities"]
    if len(snapshots) != len(declarations):
        raise CanonicalControlError("external input snapshot cardinality differs")
    for field in ("input_snapshot_identities", "dataset_validation_evidence_identities", "projection_evidence_identities"):
        identities = value[field]
        if field != "input_snapshot_identities" and identities != sorted(identities):
            raise CanonicalControlError(f"{field} is not canonical")
        if len(identities) != len(set(identities)):
            raise CanonicalControlError(f"{field} contains duplicates")
        for identity in identities: require_sha256(field, identity)


def _validate_replay_v2(value: Mapping[str, Any]) -> None:
    required = {"candidate_order", "decision_selection_identity", "ordered_decision_identities", "ordered_replay_unit_identities", "ordered_source_unit_identities", "population_accounting", "projection_identity", "replay_evidence_identity", "replay_identity", "replay_preparer_component_identity", "selector_component_identity"}
    validate_exact_fields(value, required, label="replay")
    candidates = value["candidate_order"]
    if not isinstance(candidates, list) or len(candidates) != len(set(candidates)) or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in candidates):
        raise CanonicalControlError("candidate order is invalid")
    for field in required - {"candidate_order", "population_accounting", "ordered_decision_identities", "ordered_replay_unit_identities", "ordered_source_unit_identities"}:
        require_sha256(field, value[field])
    source = value["ordered_source_unit_identities"]; replay = value["ordered_replay_unit_identities"]; decisions = value["ordered_decision_identities"]
    for collection in (source, replay, decisions):
        if len(collection) != len(set(collection)): raise CanonicalControlError("Replay identity collection is duplicated")
        for identity in collection: require_sha256("Replay identity", identity)
    population = _mapping(value, "population_accounting")
    required_population = {"dispositions", "excluded_count", "included_count", "permitted_exclusion_reasons", "population_accounting_evidence_identity", "source_count"}
    validate_exact_fields(population, required_population, label="population accounting")
    reasons = require_sorted_unique("permitted exclusion reasons", population["permitted_exclusion_reasons"], key=lambda item: item)
    dispositions = population["dispositions"]
    if len(dispositions) != len(source): raise CanonicalControlError("population disposition cardinality differs")
    included_replay: list[str] = []; included_decisions: list[str] = []
    for index, disposition in enumerate(dispositions):
        validate_exact_fields(disposition, {"decision_identity", "reason", "replay_unit_identity", "source_unit_identity", "status"}, label="population disposition")
        if disposition["source_unit_identity"] != source[index]: raise CanonicalControlError("population disposition is not source-positional")
        if disposition["status"] == "replay_included":
            if disposition["reason"] != "included_by_governed_selector": raise CanonicalControlError("included disposition reason is invalid")
            require_sha256("replay_unit_identity", disposition["replay_unit_identity"]); require_sha256("decision_identity", disposition["decision_identity"])
            included_replay.append(disposition["replay_unit_identity"]); included_decisions.append(disposition["decision_identity"])
        elif disposition["status"] == "replay_excluded":
            if disposition["replay_unit_identity"] != "not_applicable" or disposition["decision_identity"] != "not_applicable" or disposition["reason"] not in reasons:
                raise CanonicalControlError("excluded disposition is invalid")
        else: raise CanonicalControlError("population disposition status is invalid")
    if included_replay != replay or included_decisions != decisions:
        raise CanonicalControlError("population included identities do not reconcile")
    if population["source_count"] != len(source) or population["included_count"] != len(replay) or population["excluded_count"] != len(source) - len(replay):
        raise CanonicalControlError("population counts do not reconcile")
    require_sha256("population_accounting_evidence_identity", population["population_accounting_evidence_identity"])


def canonical_artifact_dependency_order(declarations: Any) -> list[str]:
    import unicodedata
    by_id: dict[str, Mapping[str, Any]] = {}; identities: set[str] = set(); paths: set[str] = set()
    for declaration in declarations:
        identifier = unicodedata.normalize("NFC", declaration["artifact_identifier"])
        if identifier != declaration["artifact_identifier"] or identifier in by_id or declaration["declaration_identity"] in identities or declaration["relative_path"].casefold() in paths:
            raise CanonicalControlError("artifact authority is duplicated or noncanonical")
        by_id[identifier] = declaration; identities.add(declaration["declaration_identity"]); paths.add(declaration["relative_path"].casefold())
    active: set[str] = set(); visited: set[str] = set(); order: list[str] = []
    def visit(identifier: str) -> None:
        if identifier in active: raise CanonicalControlError("artifact dependency cycle")
        if identifier in visited: return
        active.add(identifier)
        dependencies = by_id[identifier]["dependencies"]
        if dependencies != sorted(dependencies) or len(dependencies) != len(set(dependencies)): raise CanonicalControlError("artifact dependencies are not canonical")
        for dependency in dependencies:
            if dependency not in by_id: raise CanonicalControlError("artifact dependency is missing")
            visit(dependency)
        active.remove(identifier); visited.add(identifier); order.append(identifier)
    for identifier in sorted(by_id): visit(identifier)
    return order


def _validate_artifacts_v2(value: Mapping[str, Any], *, profile_name: str) -> None:
    required = {"artifact_declaration_evidence_identity", "declarations", "dependency_order", "output_policy_identity"}
    validate_exact_fields(value, required, label="artifacts")
    declarations = value["declarations"]
    if declarations != sorted(declarations, key=lambda item: item["artifact_identifier"]): raise CanonicalControlError("artifact declarations are not canonical")
    if value["dependency_order"] != canonical_artifact_dependency_order(declarations): raise CanonicalControlError("artifact dependency order does not reconstruct")
    require_sha256("artifact_declaration_evidence_identity", value["artifact_declaration_evidence_identity"]); require_sha256("output_policy_identity", value["output_policy_identity"])
    from orev3.execution.contract_validation import validate_artifact_declarations
    evidence = validate_artifact_declarations(declarations, profile_name=profile_name)
    if (
        value["artifact_declaration_evidence_identity"]
        != evidence["artifact_declaration_evidence_identity"]
        or value["dependency_order"] != evidence["dependency_order"]
        or value["output_policy_identity"] != evidence["output_policy_identity"]
    ):
        raise CanonicalControlError("artifact evidence authority does not reconstruct")


def _validate_outcome_policy_v2(value: Mapping[str, Any], profile: Mapping[str, Any]) -> None:
    common = {"outcome_capability", "profile_conformance_evidence_identity", "profile_contract_identities", "profile_identity", "profile_name"}
    characterization = value.get("profile_name") == "outcome_blind_characterization_v1"
    validate_exact_fields(value, common if characterization else common | {"authorization_contract_identity"}, label="outcome policy")
    if value["profile_name"] != profile["profile_name"] or value["profile_identity"] != profile["profile_identity"]: raise CanonicalControlError("outcome policy profile differs")
    require_sha256("profile_conformance_evidence_identity", value["profile_conformance_evidence_identity"])
    contracts = value["profile_contract_identities"]
    if characterization:
        if value["outcome_capability"] != "prohibited_and_not_performed" or contracts != []: raise CanonicalControlError("characterization exposes outcome authority")
    else:
        if value["profile_name"] != "outcome_aware_v1" or value["outcome_capability"] != "outcome_aware_authorized_only" or contracts != sorted(contracts) or len(contracts) != 6 or len(set(contracts)) != 6 or value["authorization_contract_identity"] not in contracts:
            raise CanonicalControlError("outcome-aware contract authority is invalid")
        require_sha256("authorization_contract_identity", value["authorization_contract_identity"])


def _validate_validation_v2(value: Mapping[str, Any]) -> None:
    required = {"additional_test_selectors", "collected_node_ids", "compile_passed", "evidence_preparation_identity", "import_passed", "launch_smoke_selectors", "mandatory_test_selectors", "readiness_test_evidence_identity", "reconstruction_passed", "test_policy_identity", "test_results"}
    validate_exact_fields(value, required, label="validation")
    for field in ("compile_passed", "import_passed", "reconstruction_passed"):
        if value[field] is not True: raise CanonicalControlError(f"{field} must be true")
    for field in ("evidence_preparation_identity", "readiness_test_evidence_identity", "test_policy_identity"): require_sha256(field, value[field])
    for field in ("additional_test_selectors", "collected_node_ids", "launch_smoke_selectors", "mandatory_test_selectors"):
        require_sorted_unique(field, value[field], key=lambda item: item)
    results = require_sorted_unique("test results", value["test_results"], key=lambda item: item.get("node_id", "") if isinstance(item, dict) else "")
    for result in results:
        validate_exact_fields(result, {"node_id", "status"}, label="test result")
        if result["status"] != "passed": raise CanonicalControlError("readiness test did not pass")


def _validate_attempt_policy_v2(value: Mapping[str, Any]) -> None:
    required = {"allocation_authority_identity", "allocator_client_component_identity", "allocator_contract_identity", "attempt_authority_contract_byte_count", "attempt_authority_contract_git_blob_identity", "attempt_authority_contract_path", "attempt_authority_contract_sha256", "attempt_identity_domain", "attempt_identity_schema_identifier", "attempt_output_declaration_identity", "collision_policy", "control_storage_component_identity", "control_storage_contract_identity", "output_namespace_identity_policy", "output_policy_identity", "output_policy_revision", "supported_attempt_kinds"}
    validate_exact_fields(value, required, label="attempt policy")
    for field in (
        "allocation_authority_identity", "allocator_client_component_identity",
        "allocator_contract_identity", "attempt_output_declaration_identity",
        "control_storage_component_identity", "control_storage_contract_identity",
        "output_policy_identity",
    ):
        require_sha256(field, value[field])
    require_integer("attempt_authority_contract_byte_count", value["attempt_authority_contract_byte_count"])
    require_git_object("attempt_authority_contract_git_blob_identity", value["attempt_authority_contract_git_blob_identity"], _object_format_from_identity(value["attempt_authority_contract_git_blob_identity"]))
    validate_repository_path(value["attempt_authority_contract_path"])
    require_sha256("attempt_authority_contract_sha256", value["attempt_authority_contract_sha256"])
    if value["attempt_authority_contract_path"] != "config/research/readiness/attempt-authority-contract-v1.json" or value["collision_policy"] != "reject_any_existing_path" or value["output_namespace_identity_policy"] != "output-namespace-identity-material-v1" or value["output_policy_revision"] != "readiness-v1-output-policy": raise CanonicalControlError("attempt policy token is unsupported")
    kinds = require_sorted_unique("supported attempt kinds", value["supported_attempt_kinds"], key=lambda item: item)
    if not set(kinds) <= {"official", "reproduction"} or "official" not in kinds: raise CanonicalControlError("official attempt authority is not supported")


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
            "collection_policy",
            "collection_affecting_paths",
            "expected_mandatory_collection_identity",
            "expected_mandatory_node_count",
            "policy_identifier",
            "policy_identity",
            "required_selectors",
            "result_policy",
            "schema_version",
            "warning_policy",
        },
        label="readiness test policy",
    )
    if material["schema_version"] != 1:
        raise CanonicalControlError("readiness test policy version is unsupported")
    if material["collection_policy"] != "double_fresh_collection_exact_match" or material["result_policy"] != "all_collected_nodes_pass" or material["warning_policy"] != "reject_any_warning":
        raise CanonicalControlError("readiness test policy semantics are unsupported")
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
    require_sha256("expected mandatory collection identity", material["expected_mandatory_collection_identity"])
    count = require_integer("expected mandatory node count", material["expected_mandatory_node_count"])
    if count < 1 or count > 16384:
        raise CanonicalControlError("readiness test policy expected node count is invalid")
    paths = require_sorted_unique("collection affecting paths", material["collection_affecting_paths"], key=lambda item: item)
    for path in paths:
        validate_repository_path(path)
    require_sha256("policy_identity", material["policy_identity"])
    identity_material = dict(material)
    stored = identity_material.pop("policy_identity")
    if domain_identity(TEST_POLICY_DOMAIN, identity_material) != stored:
        raise CanonicalControlError("readiness test policy identity does not reconstruct")


def validate_readiness_test_policy_v2(material: Mapping[str, Any]) -> None:
    validate_exact_fields(
        material,
        {
            "collection_policy",
            "collection_affecting_paths",
            "expected_mandatory_collection_identity",
            "expected_mandatory_node_count",
            "launch_smoke_selectors",
            "policy_identifier",
            "policy_identity",
            "required_selectors",
            "result_policy",
            "schema_version",
            "warning_policy",
        },
        label="readiness test policy v2",
    )
    if material["schema_version"] != 2:
        raise CanonicalControlError("readiness test policy v2 version is unsupported")
    if (
        material["collection_policy"] != "double_fresh_collection_exact_match"
        or material["result_policy"] != "all_collected_nodes_pass"
        or material["warning_policy"] != "reject_any_warning"
    ):
        raise CanonicalControlError("readiness test policy v2 semantics are unsupported")
    policy_identifier = require_string(
        "policy_identifier", material["policy_identifier"], pattern=_SAFE_IDENTIFIER
    )
    if len(policy_identifier) > MAX_READINESS_TEST_POLICY_IDENTIFIER_CODEPOINTS:
        raise CanonicalControlError(
            "readiness test policy v2 identifier exceeds the schema maximum"
        )
    selectors = require_sorted_unique(
        "required selectors", material["required_selectors"], key=lambda item: item
    )
    if not selectors or any(not isinstance(item, str) or not item for item in selectors):
        raise CanonicalControlError("readiness test policy v2 selectors are invalid")
    launch_selectors = require_sorted_unique(
        "launch smoke selectors",
        material["launch_smoke_selectors"],
        key=lambda item: item,
    )
    if not set(launch_selectors).issubset(selectors):
        raise CanonicalControlError(
            "readiness test policy v2 launch selectors are not a mandatory subset"
        )
    for label, selected in (
        ("required", selectors),
        ("launch smoke", launch_selectors),
    ):
        if len(selected) > MAX_READINESS_TEST_SELECTORS:
            raise CanonicalControlError(
                f"readiness test policy v2 {label} selector count exceeds the schema maximum"
            )
        if any(
            not isinstance(selector, str)
            or not selector
            or len(selector) > MAX_READINESS_TEST_SELECTOR_CODEPOINTS
            for selector in selected
        ):
            raise CanonicalControlError(
                f"readiness test policy v2 {label} selector is invalid"
            )
    for selector in launch_selectors:
        if selector.startswith("-") or "\\" in selector or "\x00" in selector:
            raise CanonicalControlError("readiness test policy v2 launch selector is unsafe")
        selector_path = selector.split("::", 1)[0]
        validate_repository_path(selector_path)
        if not selector_path.startswith("tests/"):
            raise CanonicalControlError(
                "readiness test policy v2 launch selector escapes governed tests"
            )
    require_sha256(
        "expected mandatory collection identity",
        material["expected_mandatory_collection_identity"],
    )
    count = require_integer(
        "expected mandatory node count", material["expected_mandatory_node_count"]
    )
    if count < 1 or count > 16384:
        raise CanonicalControlError(
            "readiness test policy v2 expected node count is invalid"
        )
    paths = require_sorted_unique(
        "collection affecting paths",
        material["collection_affecting_paths"],
        key=lambda item: item,
    )
    for path in paths:
        validate_repository_path(path)
    require_sha256("policy_identity", material["policy_identity"])
    identity_material = dict(material)
    stored = identity_material.pop("policy_identity")
    if domain_identity(TEST_POLICY_DOMAIN, identity_material) != stored:
        raise CanonicalControlError(
            "readiness test policy v2 identity does not reconstruct"
        )


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
    "READINESS_SPECIFICATION_V1_1_PATH",
    "READINESS_SPECIFICATION_V1_1_REVISION",
    "READINESS_SPECIFICATION_V1_1_SHA256",
    "READINESS_TEST_POLICY_PATH",
    "READINESS_TEST_POLICY_V2_PATH",
    "READINESS_V1_1_SCHEMA_DOCUMENT_POLICY",
    "READINESS_V1_1_SCHEMA_KIND_ORDER",
    "READINESS_V1_1_SCHEMA_POLICY",
    "READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER",
    "REPOSITORY_AUTHORITY_PATH",
    "PHASE2_SCHEMA_POLICY",
    "PHASE2_SCHEMA_DOCUMENT_POLICY",
    "PHASE2_SCHEMA_REGISTRY_IDENTIFIER",
    "PHASE3A_SCHEMA_POLICY",
    "PHASE3A_SCHEMA_DOCUMENT_POLICY",
    "PHASE3A_SCHEMA_REGISTRY_IDENTIFIER",
    "PHASE3B_SCHEMA_POLICY",
    "PHASE3B_SCHEMA_DOCUMENT_POLICY",
    "PHASE3B_SCHEMA_REGISTRY_IDENTIFIER",
    "PROSPECTIVE_PHASE2_SCHEMA_DOCUMENT_POLICY",
    "PROSPECTIVE_PHASE2_SCHEMA_POLICY",
    "PROSPECTIVE_PHASE3A_SCHEMA_DOCUMENT_POLICY",
    "PROSPECTIVE_PHASE3A_SCHEMA_POLICY",
    "PROSPECTIVE_PHASE3B_SCHEMA_DOCUMENT_POLICY",
    "PROSPECTIVE_PHASE3B_SCHEMA_POLICY",
    "PROTOCOL_BINDING_DOMAIN",
    "ReadinessRecordV1",
    "ReadinessRecordV2",
    "RepositoryAuthorityV1",
    "SourceScopeDeclarationV1",
    "build_launch_authority_snapshot",
    "build_readiness_record_v2",
    "canonical_artifact_dependency_order",
    "canonical_readiness_record_path",
    "load_readiness_record_bytes",
    "load_readiness_record_v2_bytes",
    "load_repository_authority_bytes",
    "reconstruct_readiness_identity",
    "reconstruct_control_component_identity",
    "reconstruct_document_binding_identity",
    "reconstruct_implementation_identity",
    "reconstruct_protocol_binding_identity",
    "validate_implementation_binding",
    "validate_launch_authority_snapshot",
    "validate_readiness_record",
    "validate_readiness_record_v2",
    "validate_repository_authority",
    "validate_readiness_test_policy",
    "validate_readiness_test_policy_v2",
    "validate_source_scope",
]
