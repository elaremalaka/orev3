from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    parse_json,
)
from orev3.execution.contract_validation import (
    PROFILE_CONTRACT_DOMAIN,
    reconstruct_profile_binding_identity,
    validate_artifact_declarations,
)
from orev3.execution.git_state import GitAuthorityError
from orev3.execution.evidence_preparation import load_prospective_phase3b_schemas
from orev3.execution.phase3b_components import (
    PROJECTION_SCHEMA_CONTRACT_DOMAIN,
    RAW_SCHEMA_CONTRACT_DOMAIN,
    resolve_component,
)
from orev3.execution.readiness_contracts import (
    ADAPTER_REGISTRY_PATH,
    ALLOCATION_AUTHORITY_IDENTITY_DOMAIN,
    ALLOCATOR_IMPLEMENTATION_PATH,
    ATTEMPT_AUTHORITY_CONTRACT_PATH,
    ATTEMPT_OUTPUT_DECLARATION_IDENTITY_DOMAIN,
    CONTROL_STORAGE_CONTRACT_IDENTITY_DOMAIN,
    ORCHESTRATOR_IMPLEMENTATION_PATH,
    OUTCOME_GATE_IMPLEMENTATION_PATH,
    ProspectiveRegistryGeneration,
    SOURCE_TREE_PATH,
    load_attempt_authority_contract,
    load_prospective_schemas,
    load_readiness_prerequisite_contracts,
    load_readiness_test_policy_v2,
    prospective_schema_policy,
    validate_prerequisite_source_scopes,
)
from orev3.execution.readiness_record import (
    PHASE2_SCHEMA_POLICY,
    PHASE3A_SCHEMA_POLICY,
    PHASE3B_SCHEMA_POLICY,
    PROSPECTIVE_PHASE2_SCHEMA_POLICY,
    PROSPECTIVE_PHASE3A_SCHEMA_POLICY,
    PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
    PROTOCOL_BINDING_DOMAIN,
    READINESS_TEST_POLICY_PATH,
    READINESS_TEST_POLICY_V2_PATH,
    READINESS_V1_1_SCHEMA_POLICY,
    REPOSITORY_AUTHORITY_PATH,
    reconstruct_control_component_identity,
)
from orev3.execution.registry import (
    ADAPTER_DOMAIN,
    ADAPTER_REGISTRY_DOMAIN,
    ARTIFACT_DECLARATION_DOMAIN,
    EXTERNAL_INPUT_DECLARATION_DOMAIN,
    EXTERNAL_INPUT_MANIFEST_DOMAIN,
    EXTERNAL_INPUT_MEMBER_DOMAIN,
    PARSER_CONFIGURATION_DOMAIN,
    AdapterDeclarationV1,
    load_adapter_declaration_bytes,
)
ROOT = Path(__file__).resolve().parents[2]
_PHASE3A_SPEC = importlib.util.spec_from_file_location(
    "_phase3a_test_support", ROOT / "tests/execution/test_phase3a_preparation.py"
)
assert _PHASE3A_SPEC and _PHASE3A_SPEC.loader
_PHASE3A_SUPPORT = importlib.util.module_from_spec(_PHASE3A_SPEC)
_PHASE3A_SPEC.loader.exec_module(_PHASE3A_SUPPORT)
git = _PHASE3A_SUPPORT.git
synthetic_repository = _PHASE3A_SUPPORT.synthetic_repository
write = _PHASE3A_SUPPORT.write


ZERO = "0" * 64
ONE = "1" * 64
CONTROL_STORAGE_IMPLEMENTATION_PATH = "src/orev3/execution/control_storage.py"


def _identity_component(
    root: Path, *, identifier: str, role: str, path: str
) -> str:
    raw = (root / path).read_bytes()
    return reconstruct_control_component_identity(
        {
            "component_identifier": identifier,
            "component_identity": ZERO,
            "git_object_identity": git(root, "hash-object", path),
            "path": path,
            "role": role,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    )


def _rewrite_adapter(
    root: Path,
    *,
    attempt_contract: dict[str, object],
    extra_governed: tuple[str, ...],
    outcome_aware: bool = False,
) -> tuple[str, str, str]:
    descriptor_path = "config/research/readiness/experiments/synthetic-adapter-v1.json"
    binding_path = "config/research/readiness/experiments/synthetic-binding.json"
    descriptor = parse_json((root / descriptor_path).read_bytes())
    binding = parse_json((root / binding_path).read_bytes())
    profile_declarations: dict[str, dict[str, object]] = {}
    profile_references: list[dict[str, object]] = []
    if outcome_aware:
        profile_declarations = {
            "authorization_contract_identity": _bound_contract(
                "authorization_contract_identity",
                contract_kind="outcome-authorization",
                evaluation_artifact_identifier="evaluation",
                outcome_access="authorization_required",
            ),
            "evaluation_dependency_graph_identity": _bound_contract(
                "evaluation_dependency_graph_identity",
                contract_kind="evaluation-dependency-graph",
                edges=[["authorization", "evaluation"], ["outcome_source", "evaluation"], ["ranking", "evaluation"]],
                evaluation_artifact_identifier="evaluation",
                ranking_artifact_identifier="ranking",
            ),
            "freeze_contract_identity": _bound_contract(
                "freeze_contract_identity",
                contract_kind="ranking-freeze",
                ranking_artifact_identifier="ranking",
                ranking_frozen_before_outcome=True,
            ),
            "outcome_blind_ranking_source_identity": _bound_contract(
                "outcome_blind_ranking_source_identity",
                contract_kind="outcome-blind-ranking-source",
                outcome_blind=True,
                ranking_artifact_identifier="ranking",
            ),
            "outcome_source_identity": _bound_contract(
                "outcome_source_identity",
                contract_kind="outcome-source",
                external_input_identifier="synthetic-input",
                outcome_source_role="declared_external_input",
            ),
            "ranking_artifact_identifier": _bound_contract(
                "ranking_artifact_identifier",
                artifact_identifier="ranking",
                contract_kind="ranking-artifact-reference",
            ),
        }
        for identifier in sorted(profile_declarations):
            path = f"config/research/readiness/profiles/{identifier}.json"
            raw = canonical_bytes(profile_declarations[identifier])
            write(root, path, raw)
            profile_references.append(
                {
                    "contract_identifier": identifier,
                    "identity": profile_declarations[identifier]["contract_identity"],
                    "path": path,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
    profile_name = (
        "outcome_aware_v1"
        if outcome_aware
        else "outcome_blind_characterization_v1"
    )
    outcome_policy = (
        "outcome_aware_authorized_only"
        if outcome_aware
        else "prohibited_and_not_performed"
    )
    profile_identity = reconstruct_profile_binding_identity(
        profile_name=profile_name,
        outcome_policy=outcome_policy,
        declarations=profile_declarations,
    )
    descriptor["execution_profile"]["profile_identity"] = profile_identity
    descriptor["evidence_preparation"]["resource_policy_identity"] = parse_json(
        (
            root
            / "config/research/readiness/evidence-preparation-policy-v1.json"
        ).read_bytes()
    )["policy_identity"]
    replay_preparer = resolve_component(
        root_repository(root),
        root_repository(root).resolve_commit("HEAD"),
        "canonical-replay-preparer-v1",
    )
    descriptor["replay_preparation_contract_identity"] = (
        replay_preparer.component_identity
    )
    descriptor["replay_preparation_entry_point"] = (
        "orev3.execution.replay_preparation:build_replay_evidence"
    )
    artifacts = [
        _bound_artifact(
            artifact_identifier="characterization-report",
            artifact_kind="characterization_report",
            container="json",
            dependencies=[],
            dependency_roles=[],
            execution_phase="characterization",
            profile_applicability="outcome_blind_characterization_v1",
            relative_path="artifacts/characterization-report.json",
            schema_identity=ONE,
        ),
        _bound_artifact(
            artifact_identifier="replay-manifest",
            artifact_kind="replay_manifest",
            container="json",
            dependencies=[],
            dependency_roles=[],
            execution_phase="characterization",
            profile_applicability="outcome_blind_characterization_v1",
            relative_path="artifacts/replay-manifest.json",
            schema_identity="2" * 64,
        ),
    ]
    if outcome_aware:
        artifacts = [
            _bound_artifact(
                artifact_identifier="ranking",
                artifact_kind="ranking_artifact",
                container="json",
                dependencies=[],
                dependency_roles=["replay"],
                execution_phase="ranking",
                profile_applicability="outcome_aware_v1",
                relative_path="artifacts/ranking.json",
                schema_identity=ONE,
            ),
            _bound_artifact(
                artifact_identifier="evaluation",
                artifact_kind="evaluation_report",
                container="json",
                dependencies=["ranking"],
                dependency_roles=["authorization", "outcome", "ranking"],
                execution_phase="evaluation",
                profile_applicability="outcome_aware_v1",
                relative_path="artifacts/evaluation.json",
                schema_identity="2" * 64,
            ),
        ]
        artifacts.sort(key=lambda item: item["artifact_identifier"])
    descriptor["artifacts"]["declarations"] = artifacts
    artifact_evidence = validate_artifact_declarations(
        artifacts, profile_name=profile_name
    )
    descriptor["execution_profile"] = {
        "profile_identity": profile_identity,
        "profile_name": profile_name,
    }
    descriptor["outcome_policy"] = outcome_policy
    descriptor["evidence_preparation"][
        "profile_contract_declarations"
    ] = profile_references
    output_material = {
        "adapter_identifier": descriptor["adapter_identifier"],
        "allocation_authority_identity": attempt_contract[
            "allocation_authority_identity"
        ],
        "allocator_contract_identity": attempt_contract[
            "allocator_contract_identity"
        ],
        "artifact_declaration_identities": [
            item["declaration_identity"] for item in artifacts
        ],
        "attempt_output_declaration_schema_revision": (
            "attempt-output-declaration-identity-material-v1"
        ),
        "control_storage_contract_identity": attempt_contract[
            "control_storage_contract_identity"
        ],
        "experiment_identifier": descriptor["experiment_identifier"],
        "output_namespace_identity_policy": attempt_contract[
            "output_namespace_identity_policy"
        ],
        "output_policy_identity": artifact_evidence["output_policy_identity"],
        "output_policy_revision": "readiness-v1-output-policy",
    }
    descriptor["attempt_output_declaration_identity_material"] = output_material
    descriptor["attempt_output_declaration_identity"] = domain_identity(
        ATTEMPT_OUTPUT_DECLARATION_IDENTITY_DOMAIN, output_material
    )
    contracts = {
        item["external_input_identifier"]: item
        for item in descriptor["evidence_preparation"]["dataset_contracts"]
    }
    for declaration in descriptor["external_inputs"]["declarations"]:
        contract = contracts[declaration["external_input_identifier"]]
        declaration["aggregate_byte_count"] = sum(
            item["byte_count"] for item in declaration["members"]
        )
        declaration["input_version"] = contract["dataset_version"]
        for index, member in enumerate(declaration["members"]):
            member["member_order"] = index
            member["member_identity"] = domain_identity(
                EXTERNAL_INPUT_MEMBER_DOMAIN,
                {
                    "byte_count": member["byte_count"],
                    "logical_identifier": member["logical_identifier"],
                    "member_order": index,
                    "member_path": member["member_path"],
                    "sha256": member["sha256"],
                },
            )
        parser_configuration = {
            "container": contract["container"],
            "decoder": {"decoder_kind": "not_required"},
            "parser_identifier": contract["raw_parser_identifier"],
            "parser_revision": "1",
            "record_ordering": contract["record_ordering"],
            "schema_identity": declaration["schema_identity"],
        }
        declaration["parser_configuration"] = parser_configuration
        declaration["parser_configuration_identity"] = domain_identity(
            PARSER_CONFIGURATION_DOMAIN, parser_configuration
        )
        if declaration["input_kind"] == "ordered_file_collection":
            declaration["manifest_revision"] = (
                "external-input-ordered-file-manifest-v1"
            )
            declaration["manifest_identity"] = domain_identity(
                EXTERNAL_INPUT_MANIFEST_DOMAIN,
                {
                    "external_input_identifier": declaration[
                        "external_input_identifier"
                    ],
                    "input_version": declaration["input_version"],
                    "manifest_revision": declaration["manifest_revision"],
                    "members": declaration["members"],
                },
            )
        declaration["external_input_identity"] = domain_identity(
            EXTERNAL_INPUT_DECLARATION_DOMAIN,
            {
                key: value
                for key, value in declaration.items()
                if key != "external_input_identity"
            },
        )
    descriptor["schema_version"] = 3
    descriptor["governed_scope_paths"] = sorted(
        set(descriptor["governed_scope_paths"])
        | set(extra_governed)
        | {item["path"] for item in profile_references}
    )
    descriptor["adapter_identity"] = domain_identity(
        ADAPTER_DOMAIN,
        {key: value for key, value in descriptor.items() if key != "adapter_identity"},
    )
    descriptor_raw = canonical_bytes(descriptor)
    write(root, descriptor_path, descriptor_raw)

    binding["profile_identity"] = profile_identity
    binding["protocol_binding_identity"] = domain_identity(
        PROTOCOL_BINDING_DOMAIN,
        {
            key: value
            for key, value in binding.items()
            if key != "protocol_binding_identity"
        },
    )
    write(root, binding_path, canonical_bytes(binding))

    registry = parse_json((root / ADAPTER_REGISTRY_PATH).read_bytes())
    reference = registry["descriptors"][0]
    reference["descriptor_identity"] = descriptor["adapter_identity"]
    reference["descriptor_sha256"] = hashlib.sha256(descriptor_raw).hexdigest()
    declarations_by_identifier = {
        item["external_input_identifier"]: item
        for item in descriptor["external_inputs"]["declarations"]
    }
    registry["projection_contracts"] = [
        {
            "dataset_validator_identifier": contract[
                "dataset_validator_identifier"
            ],
            "output_container": contract["container"],
            "projection_contract_identifier": contract[
                "projection_contract_identifier"
            ],
            "projection_schema_identifier": contract[
                "projection_schema_identifier"
            ],
            "projection_schema_identity": contract[
                "projection_schema_identity"
            ],
            "projection_schema_path": contract["projection_schema_path"],
            "projection_schema_sha256": contract["projection_schema_sha256"],
            "projector_identifier": contract["projector_identifier"],
            "raw_parser_identifier": contract["raw_parser_identifier"],
            "raw_schema_identifier": contract["raw_schema_identifier"],
            "raw_schema_identity": declarations_by_identifier[
                contract["external_input_identifier"]
            ]["schema_identity"],
            "raw_schema_path": contract["raw_schema_path"],
            "raw_schema_sha256": contract["raw_schema_sha256"],
        }
        for contract in descriptor["evidence_preparation"]["dataset_contracts"]
    ]
    registry["adapter_registry_identity"] = domain_identity(
        ADAPTER_REGISTRY_DOMAIN,
        {
            key: value
            for key, value in registry.items()
            if key != "adapter_registry_identity"
        },
    )
    write(root, ADAPTER_REGISTRY_PATH, canonical_bytes(registry))
    return descriptor_path, binding_path, binding["implementation"]["path"]


def _source_scopes(root: Path, source: str, roles: dict[str, str]) -> list[dict[str, str]]:
    scopes: list[dict[str, str]] = []
    for path in sorted(roles):
        entry = root_repository(root).tree_entry(source, path)
        material = {
            "git_mode": entry.mode,
            "git_object_identity": entry.object_identity,
            "nesting": "top_level",
            "repository_path": path,
            "role": roles[path],
        }
        if path == SOURCE_TREE_PATH:
            material["nesting"] = "contains_declared_children"
        elif path.startswith(SOURCE_TREE_PATH + "/"):
            material["nesting"] = "nested"
            material["parent_path"] = SOURCE_TREE_PATH
        scopes.append(material)
    return scopes


def root_repository(root: Path):
    from orev3.execution.git_state import GitRepository

    return GitRepository(root)


def prospective_repository(
    tmp_path: Path,
    *,
    kinds: tuple[str, ...] = ("official", "reproduction"),
    zero_input: bool = False,
    outcome_aware: bool = False,
    ordered_input: bool = False,
):
    repository, _, _, _ = synthetic_repository(tmp_path)
    root = repository.root
    write(root, READINESS_TEST_POLICY_V2_PATH, (ROOT / READINESS_TEST_POLICY_V2_PATH).read_bytes())
    write(
        root,
        "docs/research/specifications/experiment-execution-readiness-v1.1.md",
        (
            ROOT
            / "docs/research/specifications/experiment-execution-readiness-v1.1.md"
        ).read_bytes(),
    )
    write(
        root,
        "config/research/readiness/evidence-preparation-policy-v1.json",
        (
            ROOT
            / "config/research/readiness/evidence-preparation-policy-v1.json"
        ).read_bytes(),
    )
    write(root, "pyproject.toml", (ROOT / "pyproject.toml").read_bytes())
    raw_schema_path = "config/research/readiness/experiments/synthetic-raw-v1.json"
    projection_schema_path = (
        "config/research/readiness/experiments/synthetic-projection-v1.json"
    )
    common_properties = {
        "candidates": {
            "items": {"type": "integer"},
            "minItems": 1,
            "type": "array",
            "uniqueItems": True,
        },
        "eligible": {"type": "boolean"},
        "exclusion_reason": {
            "enum": ["missing_observation", "not_applicable"],
            "type": "string",
        },
        "observation_index": {"minimum": 0, "type": "integer"},
        "source_unit_key": {"pattern": "^[a-z0-9-]+$", "type": "string"},
    }
    projection_schema = {
        "$id": "orev3-test://synthetic/outcome-blind-projection-v1",
        "additionalProperties": False,
        "properties": common_properties,
        "required": sorted(common_properties),
        "type": "object",
    }
    raw_properties = {**common_properties, "outcome": {"type": "string"}}
    raw_schema = {
        "$id": "orev3-test://synthetic/raw-v1",
        "additionalProperties": False,
        "properties": raw_properties,
        "required": sorted(raw_properties),
        "type": "object",
    }
    raw_schema_raw = canonical_bytes(raw_schema)
    projection_schema_raw = canonical_bytes(projection_schema)
    write(root, raw_schema_path, raw_schema_raw)
    write(root, projection_schema_path, projection_schema_raw)
    input_payload = (
        b'{"candidates":[1,2],"eligible":true,'
        b'"exclusion_reason":"not_applicable","observation_index":0,'
        b'"outcome":"hidden","source_unit_key":"unit-a"}\n'
    )
    descriptor_path = (
        "config/research/readiness/experiments/synthetic-adapter-v1.json"
    )
    descriptor = parse_json((root / descriptor_path).read_bytes())
    parser = resolve_component(
        repository, repository.resolve_commit("HEAD"), "canonical-jsonl-raw-parser-v1"
    )
    member_payloads = (
        (input_payload[:70], input_payload[70:])
        if ordered_input
        else (input_payload,)
    )
    declaration = {
        "external_input_identifier": "synthetic-input",
        "external_input_identity": ZERO,
        "input_kind": (
            "ordered_file_collection" if ordered_input else "regular_file"
        ),
        "members": [
            {
                "byte_count": len(payload),
                "logical_identifier": (
                    ("first", "second")[index]
                    if ordered_input
                    else "combined"
                ),
                "member_path": (
                    f"synthetic-input-{index + 1}"
                    if ordered_input
                    else "synthetic-input"
                ),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for index, payload in enumerate(member_payloads)
        ],
        "parser_identity": parser.component_identity,
        "role": "dataset",
        "schema_identity": domain_identity(RAW_SCHEMA_CONTRACT_DOMAIN, raw_schema),
    }
    declaration["external_input_identity"] = domain_identity(
        EXTERNAL_INPUT_DECLARATION_DOMAIN,
        {key: value for key, value in declaration.items() if key != "external_input_identity"},
    )
    descriptor["external_inputs"] = {"declarations": [declaration]}
    descriptor["evidence_preparation"]["dataset_contracts"] = [
        {
            "candidate_order": [1, 2],
            "container": "canonical_jsonl",
            "dataset_validator_identifier": "canonical-jsonl-dataset-validator-v1",
            "dataset_version": "synthetic-v1",
            "external_input_identifier": "synthetic-input",
            "projection_contract_identifier": "synthetic-outcome-blind-v1",
            "projection_required": True,
            "projection_schema_identifier": "synthetic-projection-schema-v1",
            "projection_schema_identity": domain_identity(
                PROJECTION_SCHEMA_CONTRACT_DOMAIN, projection_schema
            ),
            "projection_schema_path": projection_schema_path,
            "projection_schema_sha256": hashlib.sha256(
                projection_schema_raw
            ).hexdigest(),
            "projector_identifier": "canonical-jsonl-outcome-blind-projector-v1",
            "protocol_revision": "1",
            "raw_parser_identifier": "canonical-jsonl-raw-parser-v1",
            "raw_schema_identifier": "synthetic-raw-schema-v1",
            "raw_schema_path": raw_schema_path,
            "raw_schema_sha256": hashlib.sha256(raw_schema_raw).hexdigest(),
            "record_ordering": "source_order",
            "source_class": "combined_outcome_bearing",
        }
    ]
    if zero_input:
        descriptor["external_inputs"] = {"declarations": []}
        descriptor["evidence_preparation"]["dataset_contracts"] = []
        descriptor["evidence_preparation"]["decision_selection"][
            "permitted_exclusion_reasons"
        ] = []
    write(root, descriptor_path, canonical_bytes(descriptor))
    for path, raw in (
        (ALLOCATOR_IMPLEMENTATION_PATH, b"# governed allocator contract; no allocator implementation\n"),
        (ORCHESTRATOR_IMPLEMENTATION_PATH, b"# governed orchestrator contract; no orchestrator implementation\n"),
        (OUTCOME_GATE_IMPLEMENTATION_PATH, b"# governed outcome gate contract; no outcome opener\n"),
        (
            CONTROL_STORAGE_IMPLEMENTATION_PATH,
            b"# governed control-storage contract implementation; not invoked\n",
        ),
    ):
        write(root, path, raw)

    authority_material = {
        "allocation_authority_identifier": "synthetic-shared-authority",
        "allocation_authority_schema_revision": "allocation-authority-identity-material-v1",
        "repository_authority_identifier": "synthetic-repository-v1",
    }
    control_storage_component = {
        "component_identifier": "synthetic-control-storage-v1",
        "component_identity": ZERO,
        "git_object_identity": git(
            root, "hash-object", CONTROL_STORAGE_IMPLEMENTATION_PATH
        ),
        "path": CONTROL_STORAGE_IMPLEMENTATION_PATH,
        "role": "control_storage",
        "sha256": hashlib.sha256(
            (root / CONTROL_STORAGE_IMPLEMENTATION_PATH).read_bytes()
        ).hexdigest(),
    }
    control_storage_component["component_identity"] = (
        reconstruct_control_component_identity(control_storage_component)
    )
    control_storage_material = {
        "attempt_control_record_schema_identifier": "attempt-control-record-v1",
        "control_storage_component_identity": control_storage_component[
            "component_identity"
        ],
        "control_storage_contract_schema_revision": (
            "control-storage-contract-identity-material-v1"
        ),
        "execution_control_manifest_schema_identifier": (
            "execution-control-manifest-v1"
        ),
        "persistence_contract_revision": "shared-append-only-control-history-v1",
        "recovery_contract_revision": (
            "atomic-no-live-owner-fence-and-append-failed-v1"
        ),
    }
    attempt_contract = {
        "allocation_authority_identity": domain_identity(
            ALLOCATION_AUTHORITY_IDENTITY_DOMAIN, authority_material
        ),
        "allocation_authority_identity_material": authority_material,
        "allocation_receipt_policy": "immutable_write_once",
        "allocator_client_identifier": "synthetic-allocator-client-v1",
        "allocator_implementation_identifier": "synthetic-allocator-v1",
        "atomicity_semantics": "atomic_compare_and_create",
        "allocator_contract_identity": _identity_component(
            root,
            identifier="synthetic-allocator-v1",
            role="allocator_contract",
            path=ALLOCATOR_IMPLEMENTATION_PATH,
        ),
        "collision_policy": "reject_any_existing_path",
        "contract_revision": "attempt-authority-v1",
        "control_storage_component": control_storage_component,
        "control_storage_contract_identity": domain_identity(
            CONTROL_STORAGE_CONTRACT_IDENTITY_DOMAIN, control_storage_material
        ),
        "control_storage_contract_identity_material": control_storage_material,
        "ordinal_consumption_policy": "permanent_once_allocated",
        "ordinal_scope": "experiment_and_attempt_kind",
        "output_namespace_identity_policy": "output-namespace-identity-material-v1",
        "schema_version": 1,
        "supported_attempt_kinds": list(kinds),
    }
    write(root, ATTEMPT_AUTHORITY_CONTRACT_PATH, canonical_bytes(attempt_contract))
    descriptor_path, binding_path, implementation_path = _rewrite_adapter(
        root,
        attempt_contract=attempt_contract,
        extra_governed=(
            ATTEMPT_AUTHORITY_CONTRACT_PATH,
            SOURCE_TREE_PATH,
            ALLOCATOR_IMPLEMENTATION_PATH,
            ORCHESTRATOR_IMPLEMENTATION_PATH,
            OUTCOME_GATE_IMPLEMENTATION_PATH,
            CONTROL_STORAGE_IMPLEMENTATION_PATH,
            raw_schema_path,
            projection_schema_path,
        ),
        outcome_aware=outcome_aware,
    )
    git(root, "add", ".")
    git(root, "commit", "-qm", "prospective v1.1 prerequisite contracts")
    source = git(root, "rev-parse", "HEAD")
    roles = {
        READINESS_TEST_POLICY_V2_PATH: "readiness_test_policy",
        ATTEMPT_AUTHORITY_CONTRACT_PATH: "configuration",
        ADAPTER_REGISTRY_PATH: "configuration",
        REPOSITORY_AUTHORITY_PATH: "repository_authority",
        descriptor_path: "configuration",
        binding_path: "configuration",
        implementation_path: "implementation",
        "docs/research/experiments/synthetic.md": "protocol",
        "docs/research/specifications/execution-v2.md": "execution_specification",
        "docs/research/specifications/experiment-execution-readiness-v1.1.md": "readiness_specification",
        ALLOCATOR_IMPLEMENTATION_PATH: "control_plane",
        ORCHESTRATOR_IMPLEMENTATION_PATH: "control_plane",
        OUTCOME_GATE_IMPLEMENTATION_PATH: "control_plane",
        CONTROL_STORAGE_IMPLEMENTATION_PATH: "control_plane",
        "src/orev3/execution/projection.py": "control_plane",
        "src/orev3/execution/canonical.py": "control_plane",
        "src/orev3/execution/registry.py": "control_plane",
        "src/orev3/execution/readiness.py": "control_plane",
        READINESS_V1_1_SCHEMA_POLICY["readiness-test-policy"][1]: "readiness_schema",
        SOURCE_TREE_PATH: "source_tree",
        "pyproject.toml": "dependency_manifest",
        "requirements/pylock.readiness-v1.toml": "dependency_manifest",
        "config/research/readiness/evidence-preparation-policy-v1.json": "configuration",
        "config/research/readiness/runtime-contract-v1.json": "runtime_manifest",
        "config/research/readiness/offline-artifact-manifest-v1.json": "runtime_manifest",
        raw_schema_path: "configuration",
        projection_schema_path: "configuration",
        "tests/execution/test_readiness_mandatory_v1.py": "readiness_tests",
    }
    if outcome_aware:
        for path in (root / "config/research/readiness/profiles").glob("*.json"):
            roles[path.relative_to(root).as_posix()] = "configuration"
    return repository, source, _source_scopes(root, source, roles)


def _commit_mutation(repository, message: str = "mutate prerequisite") -> str:
    git(repository.root, "add", ".")
    git(repository.root, "commit", "-qm", message)
    return git(repository.root, "rev-parse", "HEAD")


def _write_adapter_and_registry(
    root: Path,
    descriptor: dict[str, object],
    *,
    reconstruct_output_identity: bool = True,
) -> None:
    descriptor_path = "config/research/readiness/experiments/synthetic-adapter-v1.json"
    if reconstruct_output_identity:
        descriptor["attempt_output_declaration_identity"] = domain_identity(
            ATTEMPT_OUTPUT_DECLARATION_IDENTITY_DOMAIN,
            descriptor["attempt_output_declaration_identity_material"],
        )
    descriptor["adapter_identity"] = domain_identity(
        ADAPTER_DOMAIN,
        {key: value for key, value in descriptor.items() if key != "adapter_identity"},
    )
    descriptor_raw = canonical_bytes(descriptor)
    write(root, descriptor_path, descriptor_raw)
    registry = parse_json((root / ADAPTER_REGISTRY_PATH).read_bytes())
    registry["descriptors"][0]["descriptor_identity"] = descriptor[
        "adapter_identity"
    ]
    registry["descriptors"][0]["descriptor_sha256"] = hashlib.sha256(
        descriptor_raw
    ).hexdigest()
    registry["adapter_registry_identity"] = domain_identity(
        ADAPTER_REGISTRY_DOMAIN,
        {
            key: value
            for key, value in registry.items()
            if key != "adapter_registry_identity"
        },
    )
    write(root, ADAPTER_REGISTRY_PATH, canonical_bytes(registry))


def _bound_contract(identifier: str, **values: object) -> dict[str, object]:
    material = {"contract_identifier": identifier, **values}
    material["contract_identity"] = domain_identity(PROFILE_CONTRACT_DOMAIN, material)
    return material


def _bound_artifact(**values: object) -> dict[str, object]:
    material = dict(values)
    material["declaration_identity"] = domain_identity(
        ARTIFACT_DECLARATION_DOMAIN, material
    )
    return material


def test_historical_and_prospective_overlays_are_explicit_and_exact() -> None:
    assert [len(PHASE2_SCHEMA_POLICY), len(PHASE3A_SCHEMA_POLICY), len(PHASE3B_SCHEMA_POLICY)] == [6, 10, 20]
    assert [len(PROSPECTIVE_PHASE2_SCHEMA_POLICY), len(PROSPECTIVE_PHASE3A_SCHEMA_POLICY), len(PROSPECTIVE_PHASE3B_SCHEMA_POLICY), len(READINESS_V1_1_SCHEMA_POLICY)] == [6, 10, 20, 29]
    for historical in (PHASE2_SCHEMA_POLICY, PHASE3A_SCHEMA_POLICY, PHASE3B_SCHEMA_POLICY):
        assert historical["readiness-test-policy"][0] == "readiness-test-policy-v1"
    assert "adapter-declaration" not in PHASE2_SCHEMA_POLICY
    assert PHASE3A_SCHEMA_POLICY["adapter-declaration"][0] == "adapter-declaration-v1"
    assert PHASE3B_SCHEMA_POLICY["adapter-declaration"][0] == "adapter-declaration-v1"
    for prospective in (PROSPECTIVE_PHASE2_SCHEMA_POLICY, PROSPECTIVE_PHASE3A_SCHEMA_POLICY, PROSPECTIVE_PHASE3B_SCHEMA_POLICY, READINESS_V1_1_SCHEMA_POLICY):
        assert prospective["readiness-test-policy"][0] == "readiness-test-policy-v2"
        assert len([kind for kind in prospective if kind == "readiness-test-policy"]) == 1
    assert "adapter-declaration" not in PROSPECTIVE_PHASE2_SCHEMA_POLICY
    for prospective in (
        PROSPECTIVE_PHASE3A_SCHEMA_POLICY,
        PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
        READINESS_V1_1_SCHEMA_POLICY,
    ):
        assert prospective["adapter-declaration"][0] == "adapter-declaration-v3"
        assert len([kind for kind in prospective if kind == "adapter-declaration"]) == 1
    with pytest.raises(CanonicalControlError, match="not governed"):
        prospective_schema_policy("latest")  # type: ignore[arg-type]


def test_all_prospective_overlay_schemas_reconstruct_from_s(tmp_path: Path) -> None:
    repository, source, _ = prospective_repository(tmp_path)
    for generation, count in (
        (ProspectiveRegistryGeneration.PHASE2, 6),
        (ProspectiveRegistryGeneration.PHASE3A, 10),
        (ProspectiveRegistryGeneration.PHASE3B, 20),
        (ProspectiveRegistryGeneration.READINESS_V1_1, 29),
    ):
        schemas = load_prospective_schemas(repository, source, generation)
        assert len(schemas) == count
        assert schemas["readiness-test-policy"]["$id"].endswith("readiness-test-policy-v2")
        if generation is not ProspectiveRegistryGeneration.PHASE2:
            assert schemas["adapter-declaration"]["$id"].endswith(
                "adapter-declaration-v3"
            )
    prospective_phase3b = load_prospective_phase3b_schemas(repository, source)
    assert prospective_phase3b["adapter-declaration"]["$id"].endswith("adapter-declaration-v3")
    assert prospective_phase3b["profile-conformance-evidence"]["$id"].endswith("profile-conformance-evidence-v2")


def test_complete_synthetic_prerequisites_reconstruct_without_side_effects(tmp_path: Path) -> None:
    repository, source, scopes = prospective_repository(tmp_path)
    result = load_readiness_prerequisite_contracts(
        repository,
        source,
        experiment_identifier="synthetic-prospective",
        requested_attempt_kind="official",
        source_scopes=scopes,
    )
    assert len(result.schemas) == 29
    assert result.readiness_test_policy.material["launch_smoke_selectors"] == []
    assert result.attempt_authority.allocation_authority_identity != result.attempt_authority.allocator_contract_identity
    assert result.attempt_authority.control_storage_contract_identity not in {
        result.attempt_authority.allocation_authority_identity,
        result.attempt_authority.allocator_contract_identity,
        result.attempt_authority.control_storage_component_identity,
    }
    assert (
        result.adapter.material["attempt_output_declaration_identity"]
        != result.adapter.material["attempt_output_declaration_identity_material"][
            "output_policy_identity"
        ]
    )
    assert result.profile_contracts.declarations == {}
    assert not hasattr(result, "readiness_identity")
    assert not hasattr(result, "attempt_identity")
    assert not hasattr(result, "allocation_receipt")


@pytest.mark.parametrize("open_field", ("decision_selection", "profile_contracts"))
def test_adapter_v3_rejects_open_nested_authority(
    tmp_path: Path, open_field: str
) -> None:
    repository, _, scopes = prospective_repository(tmp_path)
    descriptor_path = (
        repository.root
        / "config/research/readiness/experiments/synthetic-adapter-v1.json"
    )
    descriptor = parse_json(descriptor_path.read_bytes())
    if open_field == "decision_selection":
        descriptor["evidence_preparation"]["decision_selection"][
            "caller_extension"
        ] = {"authority": ONE}
    else:
        descriptor["evidence_preparation"]["profile_contract_declarations"] = [
            {"caller_extension": ONE}
        ]
    _write_adapter_and_registry(repository.root, descriptor)
    source = _commit_mutation(repository, "open adapter-v3 authority")
    scopes = _source_scopes(
        repository.root,
        source,
        {item["repository_path"]: item["role"] for item in scopes},
    )
    with pytest.raises((CanonicalControlError, GitAuthorityError)):
        load_readiness_prerequisite_contracts(
            repository,
            source,
            experiment_identifier="synthetic-prospective",
            requested_attempt_kind="official",
            source_scopes=scopes,
        )


def test_adapter_v3_rejects_arbitrary_governed_decoder_authority(
    tmp_path: Path,
) -> None:
    repository, _, scopes = prospective_repository(tmp_path)
    descriptor_path = (
        repository.root
        / "config/research/readiness/experiments/synthetic-adapter-v1.json"
    )
    descriptor = parse_json(descriptor_path.read_bytes())
    implementation_path = "src/orev3/execution/projection.py"
    configuration_path = "config/research/readiness/evidence-preparation-policy-v1.json"
    implementation = (repository.root / implementation_path).read_bytes()
    configuration = (repository.root / configuration_path).read_bytes()
    decoder = {
        "configuration_byte_count": len(configuration),
        "configuration_git_blob_identity": git(
            repository.root, "hash-object", configuration_path
        ),
        "configuration_identity": ONE,
        "configuration_path": configuration_path,
        "configuration_sha256": hashlib.sha256(configuration).hexdigest(),
        "decoder_component_identity": ONE,
        "decoder_identifier": "caller-selected-decoder-v1",
        "decoder_kind": "governed_decoder",
        "decoder_revision": "1",
        "implementation_git_blob_identity": git(
            repository.root, "hash-object", implementation_path
        ),
        "implementation_path": implementation_path,
        "implementation_sha256": hashlib.sha256(implementation).hexdigest(),
    }
    declaration = descriptor["external_inputs"]["declarations"][0]
    declaration["parser_configuration"]["decoder"] = decoder
    declaration["parser_configuration_identity"] = domain_identity(
        PARSER_CONFIGURATION_DOMAIN, declaration["parser_configuration"]
    )
    declaration["external_input_identity"] = domain_identity(
        EXTERNAL_INPUT_DECLARATION_DOMAIN,
        {
            key: value
            for key, value in declaration.items()
            if key != "external_input_identity"
        },
    )
    _write_adapter_and_registry(repository.root, descriptor)
    source = _commit_mutation(repository, "arbitrary decoder authority")
    scopes = _source_scopes(
        repository.root,
        source,
        {item["repository_path"]: item["role"] for item in scopes},
    )
    with pytest.raises((CanonicalControlError, GitAuthorityError), match="decoder"):
        load_readiness_prerequisite_contracts(
            repository,
            source,
            experiment_identifier="synthetic-prospective",
            requested_attempt_kind="official",
            source_scopes=scopes,
        )


@pytest.mark.parametrize("defect", ("missing", "malformed", "authority", "allocator"))
def test_attempt_authority_contract_fails_closed(tmp_path: Path, defect: str) -> None:
    repository, source, _ = prospective_repository(tmp_path)
    path = repository.root / ATTEMPT_AUTHORITY_CONTRACT_PATH
    if defect == "missing":
        path.rename(path.with_suffix(".absent"))
    elif defect == "malformed":
        path.write_bytes(b"{}\n")
    else:
        material = parse_json(path.read_bytes())
        material["allocation_authority_identity" if defect == "authority" else "allocator_contract_identity"] = ZERO
        path.write_bytes(canonical_bytes(material))
    source = _commit_mutation(repository)
    schemas = load_prospective_schemas(repository, source, ProspectiveRegistryGeneration.READINESS_V1_1)
    with pytest.raises((CanonicalControlError, GitAuthorityError)):
        load_attempt_authority_contract(repository, source, schemas=schemas, requested_attempt_kind="official")


def test_caller_cannot_substitute_a_prerequisite_schema(tmp_path: Path) -> None:
    repository, source, _ = prospective_repository(tmp_path)
    schemas = dict(
        load_prospective_schemas(
            repository, source, ProspectiveRegistryGeneration.READINESS_V1_1
        )
    )
    schemas["attempt-authority-contract"] = {
        "$id": schemas["attempt-authority-contract"]["$id"],
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
    }
    with pytest.raises(CanonicalControlError, match="substituted"):
        load_attempt_authority_contract(
            repository,
            source,
            schemas=schemas,
            requested_attempt_kind="official",
        )


@pytest.mark.parametrize(
    ("defect", "message"),
    (
        ("identity", "identity does not reconstruct"),
        ("component", "another committed component"),
        ("component-bytes", "component bytes differ"),
        ("revision", "const"),
    ),
)
def test_control_storage_contract_reconstruction_rejects_substitution(
    tmp_path: Path, defect: str, message: str
) -> None:
    repository, source, _ = prospective_repository(tmp_path)
    path = repository.root / ATTEMPT_AUTHORITY_CONTRACT_PATH
    material = parse_json(path.read_bytes())
    if defect == "identity":
        material["control_storage_contract_identity"] = ZERO
    elif defect == "component":
        material["control_storage_contract_identity_material"][
            "control_storage_component_identity"
        ] = ONE
        material["control_storage_contract_identity"] = domain_identity(
            CONTROL_STORAGE_CONTRACT_IDENTITY_DOMAIN,
            material["control_storage_contract_identity_material"],
        )
    elif defect == "component-bytes":
        material["control_storage_component"]["sha256"] = ONE
        material["control_storage_component"]["component_identity"] = domain_identity(
            "orev3:readiness-control-component:v1\n",
            {
                key: value
                for key, value in material["control_storage_component"].items()
                if key != "component_identity"
            },
        )
        material["control_storage_contract_identity_material"][
            "control_storage_component_identity"
        ] = material["control_storage_component"]["component_identity"]
        material["control_storage_contract_identity"] = domain_identity(
            CONTROL_STORAGE_CONTRACT_IDENTITY_DOMAIN,
            material["control_storage_contract_identity_material"],
        )
    else:
        material["control_storage_contract_identity_material"][
            "control_storage_contract_schema_revision"
        ] = "future-revision"
    write(repository.root, ATTEMPT_AUTHORITY_CONTRACT_PATH, canonical_bytes(material))
    changed = _commit_mutation(repository)
    schemas = load_prospective_schemas(
        repository, changed, ProspectiveRegistryGeneration.READINESS_V1_1
    )
    with pytest.raises(CanonicalControlError, match=message):
        load_attempt_authority_contract(
            repository,
            changed,
            schemas=schemas,
            requested_attempt_kind="official",
        )


@pytest.mark.parametrize(
    ("kinds", "requested", "accepted"),
    (
        (("official",), "official", True),
        (("official",), "reproduction", False),
        (("reproduction",), "official", False),
        (("reproduction",), "reproduction", True),
        (("official", "reproduction"), "official", True),
        (("official", "reproduction"), "reproduction", True),
    ),
)
def test_attempt_kind_suitability_is_cross_contract(
    tmp_path: Path, kinds: tuple[str, ...], requested: str, accepted: bool
) -> None:
    repository, source, _ = prospective_repository(tmp_path, kinds=kinds)
    schemas = load_prospective_schemas(repository, source, ProspectiveRegistryGeneration.READINESS_V1_1)
    operation = lambda: load_attempt_authority_contract(repository, source, schemas=schemas, requested_attempt_kind=requested)
    if accepted:
        assert operation().material["supported_attempt_kinds"] == list(kinds)
    else:
        with pytest.raises(CanonicalControlError, match="does not support"):
            operation()


def test_policy_v2_empty_is_valid_but_missing_unsorted_and_mismatch_reject(tmp_path: Path) -> None:
    repository, source, _ = prospective_repository(tmp_path)
    schemas = load_prospective_schemas(repository, source, ProspectiveRegistryGeneration.READINESS_V1_1)
    assert load_readiness_test_policy_v2(repository, source, schemas=schemas).material["launch_smoke_selectors"] == []
    for value in (None, ["tests/z.py", "tests/a.py"], ["tests/a.py", "tests/a.py"]):
        material = parse_json((repository.root / READINESS_TEST_POLICY_V2_PATH).read_bytes())
        if value is None:
            del material["launch_smoke_selectors"]
        else:
            material["launch_smoke_selectors"] = value
        material["policy_identity"] = ZERO
        write(repository.root, READINESS_TEST_POLICY_V2_PATH, canonical_bytes(material))
        changed = _commit_mutation(repository)
        with pytest.raises(CanonicalControlError):
            load_readiness_test_policy_v2(repository, changed, schemas=schemas)


def test_launch_smoke_selectors_are_an_identity_bound_mandatory_subset(
    tmp_path: Path,
) -> None:
    repository, source, _ = prospective_repository(tmp_path)
    schemas = load_prospective_schemas(
        repository, source, ProspectiveRegistryGeneration.READINESS_V1_1
    )
    path = repository.root / READINESS_TEST_POLICY_V2_PATH
    empty = parse_json(path.read_bytes())
    empty_identity = empty["policy_identity"]

    selected = dict(empty)
    selected["launch_smoke_selectors"] = list(selected["required_selectors"])
    selected["policy_identity"] = ZERO
    selected["policy_identity"] = domain_identity(
        "orev3:readiness-test-policy:v1\n",
        {key: value for key, value in selected.items() if key != "policy_identity"},
    )
    assert selected["policy_identity"] != empty_identity
    write(repository.root, READINESS_TEST_POLICY_V2_PATH, canonical_bytes(selected))
    selected_source = _commit_mutation(repository, "bind nonempty smoke subset")
    assert load_readiness_test_policy_v2(
        repository, selected_source, schemas=schemas
    ).material["launch_smoke_selectors"] == selected["required_selectors"]

    invalid = dict(selected)
    invalid["launch_smoke_selectors"] = [
        "tests/execution/test_synthetic_adapter.py"
    ]
    invalid["policy_identity"] = ZERO
    invalid["policy_identity"] = domain_identity(
        "orev3:readiness-test-policy:v1\n",
        {key: value for key, value in invalid.items() if key != "policy_identity"},
    )
    write(repository.root, READINESS_TEST_POLICY_V2_PATH, canonical_bytes(invalid))
    invalid_source = _commit_mutation(repository, "attempt smoke selector substitution")
    with pytest.raises(CanonicalControlError, match="mandatory subset"):
        load_readiness_test_policy_v2(
            repository, invalid_source, schemas=schemas
        )


def test_production_empty_registry_remains_fail_closed(tmp_path: Path) -> None:
    repository, _, scopes = prospective_repository(tmp_path)
    write(repository.root, ADAPTER_REGISTRY_PATH, (ROOT / ADAPTER_REGISTRY_PATH).read_bytes())
    source = _commit_mutation(repository)
    with pytest.raises(CanonicalControlError, match="not registered"):
        load_readiness_prerequisite_contracts(
            repository,
            source,
            experiment_identifier="synthetic-prospective",
            requested_attempt_kind="official",
            source_scopes=scopes,
        )


def test_adapter_binding_override_rejects(tmp_path: Path) -> None:
    repository, _, scopes = prospective_repository(tmp_path)
    binding_path = "config/research/readiness/experiments/synthetic-binding.json"
    binding = parse_json((repository.root / binding_path).read_bytes())
    binding["profile_identity"] = ONE
    binding["protocol_binding_identity"] = domain_identity(
        PROTOCOL_BINDING_DOMAIN,
        {key: value for key, value in binding.items() if key != "protocol_binding_identity"},
    )
    write(repository.root, binding_path, canonical_bytes(binding))
    source = _commit_mutation(repository)
    with pytest.raises(CanonicalControlError, match="profile_identity"):
        load_readiness_prerequisite_contracts(
            repository,
            source,
            experiment_identifier="synthetic-prospective",
            requested_attempt_kind="official",
            source_scopes=scopes,
        )


@pytest.mark.parametrize(
    "defect",
    (
        "adapter",
        "experiment",
        "allocation-authority",
        "allocator-contract",
        "control-storage",
        "output-policy",
        "artifact-substitution",
        "artifact-reordering",
        "artifact-duplication",
        "namespace-policy",
    ),
)
def test_attempt_output_declaration_cross_binding_rejects_substitution(
    tmp_path: Path, defect: str
) -> None:
    repository, _, scopes = prospective_repository(tmp_path)
    descriptor_path = (
        repository.root
        / "config/research/readiness/experiments/synthetic-adapter-v1.json"
    )
    descriptor = parse_json(descriptor_path.read_bytes())
    material = descriptor["attempt_output_declaration_identity_material"]
    field_by_defect = {
        "adapter": "adapter_identifier",
        "experiment": "experiment_identifier",
        "allocation-authority": "allocation_authority_identity",
        "allocator-contract": "allocator_contract_identity",
        "control-storage": "control_storage_contract_identity",
        "output-policy": "output_policy_identity",
        "namespace-policy": "output_namespace_identity_policy",
    }
    if defect in field_by_defect:
        field = field_by_defect[defect]
        material[field] = (
            "substituted-adapter"
            if field == "adapter_identifier"
            else "substituted-experiment"
            if field == "experiment_identifier"
            else "future-namespace-policy"
            if field == "output_namespace_identity_policy"
            else ONE
        )
    elif defect == "artifact-substitution":
        material["artifact_declaration_identities"][0] = ONE
    elif defect == "artifact-reordering":
        material["artifact_declaration_identities"] = list(
            reversed(material["artifact_declaration_identities"])
        )
    else:
        material["artifact_declaration_identities"] = [
            material["artifact_declaration_identities"][0],
            material["artifact_declaration_identities"][0],
        ]
    _write_adapter_and_registry(repository.root, descriptor)
    source = _commit_mutation(repository, f"attempt output substitution: {defect}")
    with pytest.raises(CanonicalControlError):
        load_readiness_prerequisite_contracts(
            repository,
            source,
            experiment_identifier="synthetic-prospective",
            requested_attempt_kind="official",
            source_scopes=scopes,
        )


def test_output_policy_identity_cannot_substitute_for_attempt_output_identity(
    tmp_path: Path,
) -> None:
    repository, _, scopes = prospective_repository(tmp_path)
    descriptor_path = (
        repository.root
        / "config/research/readiness/experiments/synthetic-adapter-v1.json"
    )
    descriptor = parse_json(descriptor_path.read_bytes())
    descriptor["attempt_output_declaration_identity"] = descriptor[
        "attempt_output_declaration_identity_material"
    ]["output_policy_identity"]
    _write_adapter_and_registry(
        repository.root, descriptor, reconstruct_output_identity=False
    )
    source = _commit_mutation(repository, "substitute output policy identity")
    with pytest.raises(CanonicalControlError, match="does not reconstruct"):
        load_readiness_prerequisite_contracts(
            repository,
            source,
            experiment_identifier="synthetic-prospective",
            requested_attempt_kind="official",
            source_scopes=scopes,
        )


def test_adapter_schema_revisions_cannot_cross_historical_overlay(
    tmp_path: Path,
) -> None:
    repository, source, scopes = prospective_repository(tmp_path)
    descriptor_path = (
        repository.root
        / "config/research/readiness/experiments/synthetic-adapter-v1.json"
    )
    descriptor_raw = descriptor_path.read_bytes()
    historical_schema = parse_json(
        (repository.root / "src/orev3/execution/schemas/v1/adapter-declaration.schema.json").read_bytes()
    )
    with pytest.raises(CanonicalControlError):
        load_adapter_declaration_bytes(descriptor_raw, schema=historical_schema)

    descriptor = parse_json(descriptor_raw)
    descriptor.pop("attempt_output_declaration_identity_material")
    descriptor["schema_version"] = 1
    _write_adapter_and_registry(
        repository.root, descriptor, reconstruct_output_identity=False
    )
    changed = _commit_mutation(repository, "substitute historical adapter v1")
    with pytest.raises(CanonicalControlError):
        load_readiness_prerequisite_contracts(
            repository,
            changed,
            experiment_identifier="synthetic-prospective",
            requested_attempt_kind="official",
            source_scopes=scopes,
        )


def test_characterization_cannot_bind_outcome_profile_contract(tmp_path: Path) -> None:
    repository, _, _ = prospective_repository(tmp_path)
    descriptor_path = "config/research/readiness/experiments/synthetic-adapter-v1.json"
    contract_path = "config/research/readiness/profiles/authorization.json"
    contract = {
        "contract_identifier": "authorization_contract_identity",
        "contract_identity": ZERO,
        "contract_kind": "outcome-authorization",
        "evaluation_artifact_identifier": "evaluation",
        "outcome_access": "authorization_required",
    }
    contract["contract_identity"] = domain_identity(
        "orev3:experiment-profile-contract:v1\n",
        {key: value for key, value in contract.items() if key != "contract_identity"},
    )
    raw = canonical_bytes(contract)
    write(repository.root, contract_path, raw)
    descriptor = parse_json((repository.root / descriptor_path).read_bytes())
    descriptor["evidence_preparation"]["profile_contract_declarations"] = [{
        "contract_identifier": "authorization_contract_identity",
        "identity": contract["contract_identity"],
        "path": contract_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }]
    descriptor["governed_scope_paths"] = sorted(set(descriptor["governed_scope_paths"]) | {contract_path})
    descriptor["adapter_identity"] = domain_identity(
        ADAPTER_DOMAIN,
        {key: value for key, value in descriptor.items() if key != "adapter_identity"},
    )
    descriptor_raw = canonical_bytes(descriptor)
    write(repository.root, descriptor_path, descriptor_raw)
    registry = parse_json((repository.root / ADAPTER_REGISTRY_PATH).read_bytes())
    registry["descriptors"][0]["descriptor_identity"] = descriptor["adapter_identity"]
    registry["descriptors"][0]["descriptor_sha256"] = hashlib.sha256(descriptor_raw).hexdigest()
    registry["adapter_registry_identity"] = domain_identity(
        ADAPTER_REGISTRY_DOMAIN,
        {key: value for key, value in registry.items() if key != "adapter_registry_identity"},
    )
    write(repository.root, ADAPTER_REGISTRY_PATH, canonical_bytes(registry))
    source = _commit_mutation(repository)
    schemas = load_prospective_schemas(repository, source, ProspectiveRegistryGeneration.READINESS_V1_1)
    with pytest.raises(
        CanonicalControlError, match="profile contract declarations differ"
    ):
        __import__(
            "orev3.execution.readiness_contracts", fromlist=["_load_adapter"]
        )._load_adapter(
            repository,
            source,
            schemas=schemas,
            experiment_identifier="synthetic-prospective",
        )


def test_outcome_aware_profile_contracts_reconstruct_and_fail_closed(tmp_path: Path) -> None:
    from orev3.execution.readiness_contracts import load_profile_contracts

    repository, _, _ = prospective_repository(tmp_path)
    ranking = _bound_artifact(
        artifact_identifier="ranking",
        artifact_kind="ranking_artifact",
        container="json",
        dependencies=[],
        dependency_roles=["replay"],
        execution_phase="ranking",
        profile_applicability="outcome_aware_v1",
        relative_path="artifacts/ranking.json",
        schema_identity=ONE,
    )
    evaluation = _bound_artifact(
        artifact_identifier="evaluation",
        artifact_kind="evaluation_report",
        container="json",
        dependencies=["ranking"],
        dependency_roles=["authorization", "outcome", "ranking"],
        execution_phase="evaluation",
        profile_applicability="outcome_aware_v1",
        relative_path="artifacts/evaluation.json",
        schema_identity="2" * 64,
    )
    declarations = {
        "authorization_contract_identity": _bound_contract(
            "authorization_contract_identity",
            contract_kind="outcome-authorization",
            evaluation_artifact_identifier="evaluation",
            outcome_access="authorization_required",
        ),
        "evaluation_dependency_graph_identity": _bound_contract(
            "evaluation_dependency_graph_identity",
            contract_kind="evaluation-dependency-graph",
            edges=[["authorization", "evaluation"], ["outcome_source", "evaluation"], ["ranking", "evaluation"]],
            evaluation_artifact_identifier="evaluation",
            ranking_artifact_identifier="ranking",
        ),
        "freeze_contract_identity": _bound_contract(
            "freeze_contract_identity",
            contract_kind="ranking-freeze",
            ranking_artifact_identifier="ranking",
            ranking_frozen_before_outcome=True,
        ),
        "outcome_blind_ranking_source_identity": _bound_contract(
            "outcome_blind_ranking_source_identity",
            contract_kind="outcome-blind-ranking-source",
            outcome_blind=True,
            ranking_artifact_identifier="ranking",
        ),
        "outcome_source_identity": _bound_contract(
            "outcome_source_identity",
            contract_kind="outcome-source",
            external_input_identifier="governed-outcome",
            outcome_source_role="declared_external_input",
        ),
        "ranking_artifact_identifier": _bound_contract(
            "ranking_artifact_identifier",
            artifact_identifier="ranking",
            contract_kind="ranking-artifact-reference",
        ),
    }
    references: list[dict[str, object]] = []
    for identifier in sorted(declarations):
        path = f"config/research/readiness/profiles/{identifier}.json"
        raw = canonical_bytes(declarations[identifier])
        write(repository.root, path, raw)
        references.append(
            {
                "contract_identifier": identifier,
                "identity": declarations[identifier]["contract_identity"],
                "path": path,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    source = _commit_mutation(repository)
    schemas = load_prospective_schemas(
        repository, source, ProspectiveRegistryGeneration.READINESS_V1_1
    )
    profile_identity = reconstruct_profile_binding_identity(
        profile_name="outcome_aware_v1",
        outcome_policy="outcome_aware_authorized_only",
        declarations=declarations,
    )

    def adapter(refs: list[dict[str, object]]) -> AdapterDeclarationV1:
        material = {
            "artifacts": {"declarations": [ranking, evaluation]},
            "evidence_preparation": {"profile_contract_declarations": refs},
            "execution_profile": {
                "profile_identity": profile_identity,
                "profile_name": "outcome_aware_v1",
            },
            "outcome_policy": "outcome_aware_authorized_only",
        }
        return AdapterDeclarationV1(material, "synthetic-prospective", "synthetic", ZERO)

    loaded = load_profile_contracts(
        repository, source, schemas=schemas, adapter=adapter(references)
    )
    assert set(loaded.declarations) == set(declarations)
    with pytest.raises(CanonicalControlError, match="PROFILE_POLICY_MISMATCH"):
        load_profile_contracts(
            repository, source, schemas=schemas, adapter=adapter(references[:-1])
        )
    with pytest.raises(CanonicalControlError, match="duplicate"):
        load_profile_contracts(
            repository,
            source,
            schemas=schemas,
            adapter=adapter(references + [references[0]]),
        )
    mismatched = [dict(item) for item in references]
    mismatched[0]["identity"] = ZERO
    with pytest.raises(CanonicalControlError, match="identity"):
        load_profile_contracts(
            repository, source, schemas=schemas, adapter=adapter(mismatched)
        )


def test_source_scope_multiple_paths_and_substitution_fail_closed(tmp_path: Path) -> None:
    repository, source, scopes = prospective_repository(tmp_path)
    assert sum(item["role"] == "control_plane" for item in scopes) >= 2
    assert sum(item["role"] == "dependency_manifest" for item in scopes) == 2
    required = {item["repository_path"]: item["role"] for item in scopes}
    assert len(validate_prerequisite_source_scopes(repository, source, scopes, required_roles=required)) == len(scopes)
    duplicate = sorted(scopes + [dict(scopes[0])], key=lambda item: item["repository_path"])
    with pytest.raises(CanonicalControlError, match="duplicated"):
        validate_prerequisite_source_scopes(repository, source, duplicate, required_roles=required)
    wrong = [dict(item) for item in scopes]
    wrong[0]["git_object_identity"] = "0" * 40
    with pytest.raises(CanonicalControlError, match="differs from S"):
        validate_prerequisite_source_scopes(repository, source, wrong, required_roles=required)
    missing = scopes[1:]
    with pytest.raises(CanonicalControlError, match="absent"):
        validate_prerequisite_source_scopes(repository, source, missing, required_roles=required)
    unsafe = [dict(item) for item in scopes]
    unsafe[0]["repository_path"] = "../escape"
    with pytest.raises(CanonicalControlError):
        validate_prerequisite_source_scopes(repository, source, unsafe, required_roles=required)

    additional_tests_path = "tests/execution/test_synthetic_adapter.py"
    entry = repository.tree_entry(source, additional_tests_path)
    additional_tests = {
        "git_mode": entry.mode,
        "git_object_identity": entry.object_identity,
        "nesting": "top_level",
        "repository_path": additional_tests_path,
        "role": "readiness_tests",
    }
    multiple_non_singletons = sorted(
        scopes + [additional_tests], key=lambda item: item["repository_path"]
    )
    multiple_required = {
        item["repository_path"]: item["role"] for item in multiple_non_singletons
    }
    assert validate_prerequisite_source_scopes(
        repository,
        source,
        multiple_non_singletons,
        required_roles=multiple_required,
    )

    duplicate_singleton = [dict(item) for item in scopes]
    substituted = next(
        item
        for item in duplicate_singleton
        if item["repository_path"] == ADAPTER_REGISTRY_PATH
    )
    substituted["role"] = "repository_authority"
    duplicate_singleton.sort(key=lambda item: item["repository_path"])
    duplicate_required = {
        item["repository_path"]: item["role"] for item in duplicate_singleton
    }
    with pytest.raises(CanonicalControlError, match="singleton.*duplicated"):
        validate_prerequisite_source_scopes(
            repository,
            source,
            duplicate_singleton,
            required_roles=duplicate_required,
        )


def test_slice2_module_exposes_no_operational_lifecycle_api() -> None:
    import orev3.execution.readiness_contracts as contracts

    prohibited = (
        "allocate",
        "authorize_outcome",
        "construct_candidate",
        "execute",
        "launch",
        "mint_execution_ready",
        "mint_readiness_validated",
        "realize_namespace",
        "run_smoke",
    )
    assert not any(hasattr(contracts, name) for name in prohibited)
    assert parse_json((ROOT / ADAPTER_REGISTRY_PATH).read_bytes())["descriptors"] == []
    assert READINESS_TEST_POLICY_PATH.endswith("readiness-test-policy-v1.json")
