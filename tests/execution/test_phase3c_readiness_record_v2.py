from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from orev3.execution.canonical import CanonicalControlError, domain_identity, parse_json, validate_json_schema_instance
from orev3.execution.readiness_record import (
    CANONICAL_ENCODING_REVISION,
    CONTROL_COMPONENT_DOMAIN,
    DOCUMENT_BINDING_DOMAIN,
    IMPLEMENTATION_IDENTITY_DOMAIN,
    PHASE2_SCHEMA_POLICY,
    PHASE3A_SCHEMA_POLICY,
    PHASE3B_SCHEMA_POLICY,
    PROSPECTIVE_PHASE2_SCHEMA_POLICY,
    PROSPECTIVE_PHASE3A_SCHEMA_POLICY,
    PROSPECTIVE_PHASE3B_SCHEMA_POLICY,
    READINESS_RECORD_DOMAIN,
    READINESS_SPECIFICATION_V1_1_PATH,
    READINESS_SPECIFICATION_V1_1_REVISION,
    READINESS_SPECIFICATION_V1_1_SHA256,
    READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
    READINESS_V1_1_SCHEMA_KIND_ORDER,
    READINESS_V1_1_SCHEMA_POLICY,
    READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER,
    build_readiness_record_v2,
    canonical_artifact_dependency_order,
    reconstruct_control_component_identity,
    reconstruct_document_binding_identity,
    reconstruct_implementation_identity,
    validate_readiness_record_v2,
)
from orev3.execution.registry import (
    EXTERNAL_INPUT_DECLARATION_DOMAIN,
    EXTERNAL_INPUT_MANIFEST_DOMAIN,
    EXTERNAL_INPUT_MEMBER_DOMAIN,
    PARSER_CONFIGURATION_DOMAIN,
    validate_external_input_declaration_v3,
)
from orev3.execution.external_inputs import ResourceLimits, snapshot_declared_input
from orev3.execution.contract_validation import validate_artifact_declarations
from orev3.execution.dataset_validation import (
    DATASET_CONTENT_DOMAIN,
    dataset_evidence,
    projection_evidence,
)
from orev3.execution.evidence_preparation import (
    EVIDENCE_POLICY_PATH,
    aggregate_evidence,
    load_evidence_policy,
    reconstruct_prospective_phase3a_worker,
)
from orev3.execution.preparation import PHASE3A_REMAINING_PREDICATES
from orev3.execution.external_inputs import INPUT_SNAPSHOT_DOMAIN
from orev3.execution.git_state import GitAuthorityError, validate_record_v2_git_bindings
from orev3.execution.phase3b_components import WORKER_CODE_CLOSURES, resolve_component
from orev3.execution.replay_preparation import (
    build_replay_evidence,
)
from orev3.execution.zero_input_phase3b import build_zero_input_replay_evidence
from orev3.execution.runtime import (
    PHASE3B_WORKER_EVIDENCE_DOMAIN,
    load_offline_artifact_manifest_bytes,
    load_runtime_contract_bytes,
    validate_dependency_lock,
)
from orev3.execution.test_policy import READINESS_TEST_EVIDENCE_DOMAIN
from test_phase3c_readiness_contracts import prospective_repository


SHA = "1" * 64
GIT = "a" * 40


def _document(path: str, revision: str, sha256: str, *, protocol: bool = False) -> dict[str, object]:
    value: dict[str, object] = {
        "byte_count": 1,
        "git_blob_identity": GIT,
        "path": path,
        "revision": revision,
        "sha256": sha256,
    }
    identity_field = "protocol_identity" if protocol else "specification_identity"
    if protocol:
        value["identifier"] = "protocol-v1"
    value[identity_field] = "0" * 64
    value[identity_field] = reconstruct_document_binding_identity(value, identity_field=identity_field)
    return value


def _component(identifier: str, role: str, path: str) -> dict[str, str]:
    value = {
        "component_identifier": identifier,
        "component_identity": "0" * 64,
        "git_object_identity": GIT,
        "path": path,
        "role": role,
        "sha256": SHA,
    }
    value["component_identity"] = reconstruct_control_component_identity(value)
    return value


def _scope(path: str, role: str, *, nesting: str = "top_level", parent: str = "") -> dict[str, str]:
    value = {"git_mode": "100644", "git_object_identity": GIT, "nesting": nesting, "repository_path": path, "role": role}
    if nesting == "nested":
        value["parent_path"] = parent
    return value


def _material() -> dict[str, object]:
    implementation = {
        "adapter_identifier": "synthetic-adapter",
        "adapter_identity": SHA,
        "adapter_registry_identity": SHA,
        "entry_point": "orev3.synthetic:run",
        "implementation_git_blob_identity": GIT,
        "implementation_identity": "0" * 64,
        "implementation_path": "src/orev3/synthetic.py",
        "implementation_sha256": SHA,
        "protocol_binding_byte_count": 1,
        "protocol_binding_git_blob_identity": GIT,
        "protocol_binding_identity": SHA,
        "protocol_binding_path": "config/research/synthetic-binding.json",
        "protocol_binding_sha256": SHA,
    }
    implementation["implementation_identity"] = domain_identity(IMPLEMENTATION_IDENTITY_DOMAIN, {
        key: implementation[key] for key in ("adapter_identifier", "entry_point", "implementation_git_blob_identity", "implementation_path", "implementation_sha256")
    })
    components = [
        _component("synthetic-adapter", "adapter", "src/orev3/synthetic.py"),
        _component(
            "experiment-execution-readiness-adapter-registry-v1",
            "adapter_registry",
            "src/orev3/execution/registry.py",
        ),
        _component("shared-allocator-client-v1", "allocator_client", "src/orev3/execution/attempts.py"),
        _component("shared-allocator-v1", "allocator_contract", "src/orev3/execution/attempts.py"),
        _component("canonical_serializer", "canonical_serializer", "src/orev3/execution/canonical.py"),
        _component("official_orchestrator", "official_orchestrator", "src/orev3/execution/orchestrator.py"),
        _component("outcome_gate", "outcome_gate", "src/orev3/execution/outcome_gate.py"),
        _component("readiness_validator", "readiness_validator", "src/orev3/execution/readiness.py"),
    ]
    components.sort(key=lambda item: item["component_identifier"])
    scopes = [
        _scope("config/research/dependencies.lock", "dependency_manifest"),
        _scope("docs/research/execution.md", "execution_specification"),
        _scope("docs/research/protocol.md", "protocol"),
        _scope(READINESS_SPECIFICATION_V1_1_PATH, "readiness_specification"),
        _scope("config/research/readiness/repository-authority-v1.json", "repository_authority"),
        _scope("config/research/readiness/readiness-test-policy-v2.json", "readiness_test_policy"),
        _scope("src/orev3", "source_tree", nesting="contains_declared_children"),
        _scope("src/orev3/execution", "control_plane", nesting="nested", parent="src/orev3"),
        _scope("src/orev3/execution/schemas/v1", "readiness_schema", nesting="nested", parent="src/orev3"),
        _scope("src/orev3/synthetic.py", "implementation", nesting="nested", parent="src/orev3"),
    ]
    scopes.sort(key=lambda item: (item["repository_path"], item["role"]))
    declarations = [
        {
            "byte_count": 1,
            "git_blob_identity": GIT,
            "object_kind": kind,
            "path": READINESS_V1_1_SCHEMA_POLICY[kind][1],
            "registry_identifier": READINESS_V1_1_SCHEMA_POLICY[kind][0],
            "schema_id": READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind][0],
            "sha256": READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind][1],
        }
        for kind in READINESS_V1_1_SCHEMA_KIND_ORDER
    ]
    profile_identity = "2" * 64
    artifact_material = {
        "artifact_identifier": "characterization-report",
        "artifact_kind": "characterization_report",
        "container": "json",
        "dependencies": [],
        "dependency_roles": [],
        "execution_phase": "characterization",
        "profile_applicability": "outcome_blind_characterization_v1",
        "relative_path": "outputs/characterization.json",
        "schema_identity": SHA,
    }
    artifact = {
        **artifact_material,
        "declaration_identity": domain_identity(
            "orev3:readiness-adapter-artifact:v1\n", artifact_material
        ),
    }
    artifact_evidence = validate_artifact_declarations(
        [artifact], profile_name="outcome_blind_characterization_v1"
    )
    return {
        "schema": {"canonical_encoding_revision": CANONICAL_ENCODING_REVISION, "declarations": declarations, "schema_registry_identifier": READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER},
        "experiment": {"canonical_record_path": "docs/research/readiness/synthetic-experiment.json", "experiment_configuration_identity": SHA, "experiment_identifier": "synthetic-experiment"},
        "git_authority": {"approved_branch_ref": "refs/heads/research/post-v1", "repository_authority_identifier": "research-post-v1", "source_commit": GIT},
        "readiness_specification": _document(READINESS_SPECIFICATION_V1_1_PATH, READINESS_SPECIFICATION_V1_1_REVISION, READINESS_SPECIFICATION_V1_1_SHA256),
        "control_plane": {"components": components},
        "source_scopes": scopes,
        "protocol": _document("docs/research/protocol.md", "1", SHA, protocol=True),
        "implementation": implementation,
        "execution_specification": _document("docs/research/execution.md", "1", SHA),
        "execution_profile": {"profile_identity": profile_identity, "profile_name": "outcome_blind_characterization_v1"},
        "runtime": {
            "dependency_environment_identity": SHA, "dependency_lock_git_blob_identity": GIT, "dependency_lock_identity": SHA, "dependency_lock_path": "config/research/dependencies.lock", "dependency_lock_sha256": SHA,
            "host_system_identity": SHA, "offline_artifact_manifest_git_blob_identity": GIT, "offline_artifact_manifest_identity": SHA, "offline_artifact_manifest_path": "config/research/offline.json", "offline_artifact_manifest_sha256": SHA,
            "python_implementation": "CPython", "python_version": "3.12.0", "runtime_bundle_identity": SHA, "runtime_contract_byte_count": 1, "runtime_contract_git_blob_identity": GIT, "runtime_contract_identity": SHA, "runtime_contract_path": "config/research/runtime.json", "runtime_contract_sha256": SHA,
        },
        "configuration": {"decision_selection_identity": SHA, "evidence_preparation_policy_identity": SHA, "experiment_configuration_identity": SHA},
        "external_inputs": {"dataset_validation_evidence_identities": [], "declarations": [], "input_snapshot_identities": [], "projection_evidence_identities": []},
        "replay": {"candidate_order": [0], "decision_selection_identity": SHA, "ordered_decision_identities": ["6" * 64], "ordered_replay_unit_identities": ["5" * 64], "ordered_source_unit_identities": ["4" * 64], "population_accounting": {"dispositions": [{"decision_identity": "6" * 64, "reason": "included_by_governed_selector", "replay_unit_identity": "5" * 64, "source_unit_identity": "4" * 64, "status": "replay_included"}], "excluded_count": 0, "included_count": 1, "permitted_exclusion_reasons": [], "population_accounting_evidence_identity": SHA, "source_count": 1}, "projection_identity": SHA, "replay_evidence_identity": SHA, "replay_identity": "3" * 64, "replay_preparer_component_identity": SHA, "selector_component_identity": SHA},
        "artifacts": {"artifact_declaration_evidence_identity": artifact_evidence["artifact_declaration_evidence_identity"], "declarations": [artifact], "dependency_order": artifact_evidence["dependency_order"], "output_policy_identity": artifact_evidence["output_policy_identity"]},
        "outcome_policy": {"outcome_capability": "prohibited_and_not_performed", "profile_conformance_evidence_identity": SHA, "profile_contract_identities": [], "profile_identity": profile_identity, "profile_name": "outcome_blind_characterization_v1"},
        "validation": {"additional_test_selectors": [], "collected_node_ids": [], "compile_passed": True, "evidence_preparation_identity": SHA, "import_passed": True, "launch_smoke_selectors": [], "mandatory_test_selectors": ["tests/execution"], "readiness_test_evidence_identity": SHA, "reconstruction_passed": True, "test_policy_identity": SHA, "test_results": []},
        "attempt_policy": {"allocation_authority_identity": SHA, "allocator_client_component_identity": next(item["component_identity"] for item in components if item["role"] == "allocator_client"), "allocator_contract_identity": next(item["component_identity"] for item in components if item["role"] == "allocator_contract"), "attempt_authority_contract_byte_count": 1, "attempt_authority_contract_git_blob_identity": GIT, "attempt_authority_contract_path": "config/research/readiness/attempt-authority-contract-v1.json", "attempt_authority_contract_sha256": SHA, "attempt_identity_domain": "orev3:experiment-attempt:v1\n", "attempt_identity_schema_identifier": "attempt-identity-material-v1", "attempt_output_declaration_identity": SHA, "collision_policy": "reject_any_existing_path", "control_storage_component_identity": SHA, "control_storage_contract_identity": SHA, "output_namespace_identity_policy": "output-namespace-identity-material-v1", "output_policy_identity": artifact_evidence["output_policy_identity"], "output_policy_revision": "readiness-v1-output-policy", "supported_attempt_kinds": ["official", "reproduction"]},
    }


def _external(kind: str = "regular_file") -> dict[str, object]:
    members = []
    for index, name in enumerate(("first",) if kind == "regular_file" else ("first", "second")):
        member = {"byte_count": index + 1, "logical_identifier": name, "member_identity": "0" * 64, "member_order": index, "member_path": f"data/{name}.jsonl", "sha256": str(index + 4) * 64}
        member["member_identity"] = domain_identity(EXTERNAL_INPUT_MEMBER_DOMAIN, {key: value for key, value in member.items() if key != "member_identity"})
        members.append(member)
    parser = {"container": "canonical_jsonl", "decoder": {"decoder_kind": "not_required"}, "parser_identifier": "canonical-jsonl-raw-parser-v1", "parser_revision": "1", "record_ordering": "source_order", "schema_identity": SHA}
    value: dict[str, object] = {"aggregate_byte_count": sum(item["byte_count"] for item in members), "external_input_identifier": "input", "external_input_identity": "0" * 64, "input_kind": kind, "input_version": "v1", "members": members, "parser_configuration": parser, "parser_configuration_identity": domain_identity(PARSER_CONFIGURATION_DOMAIN, parser), "parser_identity": SHA, "role": "input", "schema_identity": SHA}
    if kind == "ordered_file_collection":
        value["manifest_revision"] = "external-input-ordered-file-manifest-v1"
        value["manifest_identity"] = domain_identity(EXTERNAL_INPUT_MANIFEST_DOMAIN, {"external_input_identifier": "input", "input_version": "v1", "manifest_revision": value["manifest_revision"], "members": members})
    value["external_input_identity"] = domain_identity(EXTERNAL_INPUT_DECLARATION_DOMAIN, {key: item for key, item in value.items() if key != "external_input_identity"})
    return value


def _git_blob(repository, source: str, path: str) -> tuple[bytes, str]:
    entry = repository.tree_entry(source, path)
    return repository.object_bytes(entry.object_identity, max_bytes=8_388_608), entry.object_identity


def _committed_document(
    repository,
    source: str,
    *,
    path: str,
    revision: str,
    identity_field: str,
    identifier: str | None = None,
) -> dict[str, object]:
    raw, git_blob = _git_blob(repository, source, path)
    material: dict[str, object] = {
        "byte_count": len(raw),
        "git_blob_identity": git_blob,
        identity_field: SHA,
        "path": path,
        "revision": revision,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if identifier is not None:
        material["identifier"] = identifier
    material[identity_field] = reconstruct_document_binding_identity(
        material, identity_field=identity_field
    )
    return material


def _committed_component(
    repository, source: str, *, identifier: str, role: str, path: str
) -> dict[str, str]:
    raw, git_blob = _git_blob(repository, source, path)
    material = {
        "component_identifier": identifier,
        "component_identity": SHA,
        "git_object_identity": git_blob,
        "path": path,
        "role": role,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    material["component_identity"] = reconstruct_control_component_identity(material)
    return material


def _prospective_git_candidate(
    tmp_path: Path,
    *,
    zero_input: bool = False,
    outcome_aware: bool = False,
    ordered_input: bool = False,
):
    from orev3.execution.readiness_contracts import load_readiness_prerequisite_contracts

    repository, source, scopes = prospective_repository(
        tmp_path,
        zero_input=zero_input,
        outcome_aware=outcome_aware,
        ordered_input=ordered_input,
    )
    prerequisites = load_readiness_prerequisite_contracts(
        repository,
        source,
        experiment_identifier="synthetic-prospective",
        requested_attempt_kind="official",
        source_scopes=scopes,
    )
    adapter = prerequisites.adapter.material
    binding = prerequisites.implementation_binding
    authority = prerequisites.attempt_authority

    declarations = []
    for kind in READINESS_V1_1_SCHEMA_KIND_ORDER:
        registry_identifier, path = READINESS_V1_1_SCHEMA_POLICY[kind]
        raw, git_blob = _git_blob(repository, source, path)
        declarations.append(
            {
                "byte_count": len(raw),
                "git_blob_identity": git_blob,
                "object_kind": kind,
                "path": path,
                "registry_identifier": registry_identifier,
                "schema_id": READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind][0],
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )

    implementation_raw, implementation_blob = _git_blob(
        repository, source, binding["implementation"]["path"]
    )
    implementation = {
        "adapter_identifier": adapter["adapter_identifier"],
        "adapter_identity": adapter["adapter_identity"],
        "adapter_registry_identity": prerequisites.adapter_registry.material[
            "adapter_registry_identity"
        ],
        "entry_point": binding["entry_point"],
        "implementation_git_blob_identity": implementation_blob,
        "implementation_identity": SHA,
        "implementation_path": binding["implementation"]["path"],
        "implementation_sha256": hashlib.sha256(implementation_raw).hexdigest(),
        "protocol_binding_byte_count": 0,
        "protocol_binding_git_blob_identity": "",
        "protocol_binding_identity": binding["protocol_binding_identity"],
        "protocol_binding_path": adapter["implementation_binding_path"],
        "protocol_binding_sha256": "",
    }
    binding_raw, binding_blob = _git_blob(
        repository, source, adapter["implementation_binding_path"]
    )
    implementation.update(
        {
            "protocol_binding_byte_count": len(binding_raw),
            "protocol_binding_git_blob_identity": binding_blob,
            "protocol_binding_sha256": hashlib.sha256(binding_raw).hexdigest(),
        }
    )
    implementation["implementation_identity"] = reconstruct_implementation_identity(
        implementation
    )

    component_specs = (
        (adapter["adapter_identifier"], "adapter", binding["implementation"]["path"]),
        (
            prerequisites.adapter_registry.material["registry_identifier"],
            "adapter_registry",
            "src/orev3/execution/registry.py",
        ),
        (
            authority.material["allocator_client_identifier"],
            "allocator_client",
            "src/orev3/execution/attempts.py",
        ),
        (
            authority.material["allocator_implementation_identifier"],
            "allocator_contract",
            "src/orev3/execution/attempts.py",
        ),
        ("canonical_serializer", "canonical_serializer", "src/orev3/execution/canonical.py"),
        ("official_orchestrator", "official_orchestrator", "src/orev3/execution/orchestrator.py"),
        ("outcome_gate", "outcome_gate", "src/orev3/execution/outcome_gate.py"),
        ("readiness_validator", "readiness_validator", "src/orev3/execution/readiness.py"),
    )
    components = sorted(
        (
            _committed_component(
                repository, source, identifier=identifier, role=role, path=path
            )
            for identifier, role, path in component_specs
        ),
        key=lambda item: item["component_identifier"],
    )

    runtime_path = "config/research/readiness/runtime-contract-v1.json"
    runtime_raw, runtime_blob = _git_blob(repository, source, runtime_path)
    runtime_contract = load_runtime_contract_bytes(
        runtime_raw, schema=prerequisites.schemas["runtime-contract"]
    )
    runtime_material = runtime_contract.material
    lock_raw, lock_blob = _git_blob(
        repository, source, runtime_contract.dependency_lock_path
    )
    dependency_lock = validate_dependency_lock(
        lock_raw, expected_sha256=runtime_contract.dependency_lock_sha256
    )
    manifest_raw, manifest_blob = _git_blob(
        repository, source, runtime_contract.artifact_manifest_path
    )
    manifest = load_offline_artifact_manifest_bytes(
        manifest_raw,
        schema=prerequisites.schemas["offline-artifact-manifest"],
        expected_sha256=runtime_contract.artifact_manifest_sha256,
        dependency_lock_sha256=runtime_contract.dependency_lock_sha256,
        dependency_lock=dependency_lock,
    )
    runtime = {
        "dependency_environment_identity": runtime_material["dependency_lock"]["closed_environment_identity"],
        "dependency_lock_git_blob_identity": lock_blob,
        "dependency_lock_identity": runtime_material["dependency_lock"]["lock_identity"],
        "dependency_lock_path": runtime_contract.dependency_lock_path,
        "dependency_lock_sha256": runtime_contract.dependency_lock_sha256,
        "host_system_identity": runtime_material["host_system"]["host_system_identity"],
        "offline_artifact_manifest_git_blob_identity": manifest_blob,
        "offline_artifact_manifest_identity": manifest.manifest_identity,
        "offline_artifact_manifest_path": runtime_contract.artifact_manifest_path,
        "offline_artifact_manifest_sha256": runtime_contract.artifact_manifest_sha256,
        "python_implementation": runtime_material["python"]["implementation"],
        "python_version": runtime_material["python"]["version"],
        "runtime_bundle_identity": runtime_material["python"]["runtime_bundle_identity"],
        "runtime_contract_byte_count": len(runtime_raw),
        "runtime_contract_git_blob_identity": runtime_blob,
        "runtime_contract_identity": runtime_contract.runtime_contract_identity,
        "runtime_contract_path": runtime_path,
        "runtime_contract_sha256": hashlib.sha256(runtime_raw).hexdigest(),
    }

    input_declarations = adapter["external_inputs"]["declarations"]
    snapshots = []
    datasets = []
    projections = []
    contracts = {
        item["external_input_identifier"]: item
        for item in adapter["evidence_preparation"]["dataset_contracts"]
    }
    semantic_components: set[str] = set()
    for declaration in input_declarations:
        snapshot_material = {
            "external_input_identifier": declaration["external_input_identifier"],
            "input_kind": declaration["input_kind"],
            "members": [
                {
                    "byte_count": member["byte_count"],
                    "logical_member_identifier": member["logical_identifier"],
                    "member_order": member["member_order"],
                    "sha256": member["sha256"],
                }
                for member in declaration["members"]
            ],
            "schema_version": 1,
        }
        snapshot = {
            **snapshot_material,
            "input_snapshot_identity": domain_identity(
                INPUT_SNAPSHOT_DOMAIN, snapshot_material
            ),
        }
        snapshots.append(snapshot)
        contract = contracts[declaration["external_input_identifier"]]
        parser = resolve_component(
            repository, source, contract["raw_parser_identifier"]
        )
        validator = resolve_component(
            repository, source, contract["dataset_validator_identifier"]
        )
        projector = resolve_component(
            repository, source, contract["projector_identifier"]
        )
        semantic_components.update(
            (parser.component_identity, validator.component_identity, projector.component_identity)
        )
        dataset = dataset_evidence(
            external_input_identity=declaration["external_input_identity"],
            snapshot_identity=snapshot["input_snapshot_identity"],
            source_class=contract["source_class"],
            dataset_version=contract["dataset_version"],
            container=contract["container"],
            parser_component_identity=parser.component_identity,
            validator_component_identity=validator.component_identity,
            schema_identity=declaration["schema_identity"],
            protocol_revision=contract["protocol_revision"],
            record_count=1,
            record_ordering=contract["record_ordering"],
            candidate_order=contract["candidate_order"],
            projection_required=contract["projection_required"],
            dataset_content_identity=domain_identity(
                DATASET_CONTENT_DOMAIN,
                {"ordered_record_sha256s": [SHA], "record_count": 1},
            ),
        )
        datasets.append(dataset)
        projection_schema = parse_json(
            repository.object_bytes(
                repository.tree_entry(source, contract["projection_schema_path"]).object_identity,
                max_bytes=1_048_576,
            )
        )
        projection = projection_evidence(
            raw_snapshot_identity=snapshot["input_snapshot_identity"],
            raw_dataset_identity=dataset["dataset_identity"],
            parser_component_identity=parser.component_identity,
            projector_component_identity=projector.component_identity,
            projection_schema_identity=contract["projection_schema_identity"],
            allowed_fields=sorted(projection_schema["properties"]),
            projection_bytes=b"{}\n",
            record_count=1,
        )
        projections.append(projection)

    decision = adapter["evidence_preparation"]["decision_selection"]
    selector = resolve_component(repository, source, decision["selector_identifier"])
    replay_preparer = resolve_component(
        repository, source, decision["replay_preparer_identifier"]
    )
    semantic_components.update((selector.component_identity, replay_preparer.component_identity))
    if zero_input:
        replay, population = build_zero_input_replay_evidence(
            adapter_identity=adapter["adapter_identity"],
            experiment_identifier=adapter["experiment_identifier"],
            profile_identity=adapter["execution_profile"]["profile_identity"],
            source_commit=source,
            decision_selection_identity=decision["configuration_identity"],
            selector_component_identity=selector.component_identity,
            replay_preparer_component_identity=replay_preparer.component_identity,
            permitted_exclusion_reasons=decision["permitted_exclusion_reasons"],
        )
    else:
        replay, population = build_replay_evidence(
            [
                {
                    "candidates": contracts[input_declarations[0]["external_input_identifier"]]["candidate_order"],
                    "eligible": True,
                    "exclusion_reason": "not_applicable",
                    "observation_index": 0,
                    "source_unit_key": "unit-a",
                }
            ],
            dataset_identity=datasets[0]["dataset_identity"],
            projection_identity=projections[0]["projection_identity"],
            selector_identifier=selector.identifier,
            selector_component_identity=selector.component_identity,
            replay_preparer_component_identity=replay_preparer.component_identity,
            configuration_identity=decision["configuration_identity"],
            candidate_order=contracts[input_declarations[0]["external_input_identifier"]]["candidate_order"],
            allowed_exclusion_reasons=decision["permitted_exclusion_reasons"],
            max_units=10,
            decision_selection_identity=decision["configuration_identity"],
            schema_version=2,
        )
    artifact_evidence = validate_artifact_declarations(
        adapter["artifacts"]["declarations"],
        profile_name=adapter["execution_profile"]["profile_name"],
    )
    profile = dict(prerequisites.profile_contracts.profile_evidence)
    semantic_components.update(
        resolve_component(repository, source, identifier).component_identity
        for identifier in ("static-profile-validator-v1", "static-artifact-validator-v1")
    )

    policy = prerequisites.readiness_test_policy.material
    collected = ["tests/execution/test_readiness_mandatory_v1.py::test_policy_shape"]
    readiness_material = {
        "additional_selectors": adapter["adapter_readiness_tests"],
        "collected_node_ids": collected,
        "environment_identity": runtime["dependency_environment_identity"],
        "mandatory_selectors": policy["required_selectors"],
        "policy_identity": policy["policy_identity"],
        "results": [{"node_id": collected[0], "status": "passed"}],
        "schema_version": 1,
        "source_commit": source,
    }
    readiness_test = {
        **readiness_material,
        "readiness_test_evidence_identity": domain_identity(
            READINESS_TEST_EVIDENCE_DOMAIN, readiness_material
        ),
    }
    evidence_policy_raw, _ = _git_blob(repository, source, EVIDENCE_POLICY_PATH)
    evidence_policy = load_evidence_policy(
        evidence_policy_raw,
        schema=prerequisites.schemas["evidence-preparation-policy"],
    )
    source_scope_material = []
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
        source_scope_material.append(item)
    source_scope_material.sort(
        key=lambda item: (item["repository_path"], item["role"])
    )
    workers = []
    repository_authority = parse_json(
        repository.object_bytes(
            repository.tree_entry(
                source, "config/research/readiness/repository-authority-v1.json"
            ).object_identity,
            max_bytes=1_048_576,
        )
    )
    normalized_phase3a = reconstruct_prospective_phase3a_worker(
        repository=repository,
        source_commit=source,
        phase3a_result={
            "adapter_identity": adapter["adapter_identity"],
            "adapter_registry_identity": prerequisites.adapter_registry.material[
                "adapter_registry_identity"
            ],
            "closed_dependency_environment_identity": runtime[
                "dependency_environment_identity"
            ],
            "closed_dependency_root_path": "/operational/root-not-authority",
            "command": "validate_runtime",
            "dependency_import_origins": [
                probe["module"].replace(".", "/") + "/__init__.py"
                for probe in runtime_contract.material["import_policy"][
                    "dependency_import_probes"
                ]
            ],
            "evidence_disposition": "PREPARATION_ENVIRONMENT_EVIDENCE_PASSED",
            "network_denial_verified": True,
            "project_control_plane_origins": [
                "src/orev3/execution/canonical.py",
                "src/orev3/execution/git_state.py",
                "src/orev3/execution/preparation.py",
                "src/orev3/execution/preparation_worker.py",
                "src/orev3/execution/readiness_record.py",
                "src/orev3/execution/registry.py",
                "src/orev3/execution/runtime.py",
            ],
            "remaining_predicates": list(PHASE3A_REMAINING_PREDICATES),
            "runtime_contract_identity": runtime_contract.runtime_contract_identity,
            "source_commit": source,
            "status": "evidence_passed",
        },
        approved_branch_ref=repository_authority["approved_branch_ref"],
        repository_authority_identifier=repository_authority[
            "repository_authority_identifier"
        ],
        source_scopes=source_scope_material,
        capability_policy_identity=evidence_policy["policy_identity"],
        sandbox_template_identity=next(
            item["sandbox_template_identity"]
            for item in evidence_policy["worker_profiles"]
            if item["worker_kind"] == "PHASE3A_VALIDATOR"
        ),
    )
    workers.append(
        {
            "material": dict(normalized_phase3a.material),
            "result": dict(normalized_phase3a.result),
        }
    )
    worker_occurrences: dict[str, int] = {}
    worker_kinds = (
        ("READINESS_TEST", "READINESS_TEST", "READINESS_TEST")
        if zero_input
        else (
            "INPUT_PROJECTOR",
            "INPUT_PROJECTOR",
            "READINESS_TEST",
            "READINESS_TEST",
            "READINESS_TEST",
            "REPLAY_PREPARATION",
            "REPLAY_PREPARATION",
        )
    )
    for kind in worker_kinds:
        occurrence = worker_occurrences.get(kind, 0) + 1
        worker_occurrences[kind] = occurrence
        profile_policy = next(
            item for item in evidence_policy["worker_profiles"] if item["worker_kind"] == kind
        )
        code_ids = sorted(
            {
                repository.tree_entry(source, path).object_identity
                for path in WORKER_CODE_CLOSURES[kind]
            }
        )
        worker_module = profile_policy["module"]
        if kind == "INPUT_PROJECTOR":
            result = {
                "byte_count": projections[0]["byte_count"],
                "dataset_content_identity": datasets[0]["dataset_content_identity"],
                "record_count": datasets[0]["ordered_record_count"],
                "sha256": projections[0]["sha256"],
                "status": "evidence_passed",
            }
        elif kind == "READINESS_TEST":
            result = {
                "collected_node_ids": readiness_test["collected_node_ids"],
                "exit_code": 0,
                "results": readiness_test["results"],
                "status": "evidence_passed",
                "warning_count": 0,
            }
        else:
            result = {
                "byte_count": 1,
                "population_identity": population[
                    "population_accounting_evidence_identity"
                ],
                "replay_identity": replay["replay_evidence_identity"],
                "sha256": SHA,
                "status": "evidence_passed",
            }
        if kind == "INPUT_PROJECTOR":
            command = "project_canonical_jsonl"
            invocation_identifier = f"projection-{occurrence}"
            input_capability_identities = [snapshots[0]["input_snapshot_identity"]]
        elif kind == "READINESS_TEST":
            command = "collect" if occurrence < 3 else "run_exact"
            invocation_identifier = (
                f"collection-{'a' if occurrence == 1 else 'b'}"
                if occurrence < 3
                else "execution"
            )
            input_capability_identities = []
        else:
            command = "reconstruct_replay"
            invocation_identifier = f"replay-{occurrence}"
            input_capability_identities = [replay["projection_identity"]]
        worker_material = {
            "capability_policy_identity": evidence_policy["policy_identity"],
            "closed_dependency_identity": runtime["dependency_environment_identity"],
            "code_capability_git_identities": code_ids,
            "command_identity": domain_identity(
                PHASE3B_WORKER_EVIDENCE_DOMAIN,
                {
                    "command": command,
                    "invocation_identifier": invocation_identifier,
                    "worker_kind": kind,
                },
            ),
            "input_capability_identities": input_capability_identities,
            "output_identity": domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, result),
            "runtime_contract_identity": runtime_contract.runtime_contract_identity,
            "sandbox_template_identity": profile_policy["sandbox_template_identity"],
            "source_commit": source,
            "successful_worker_disposition": "evidence_passed",
            "worker_kind": kind,
            "worker_module_git_identity": repository.tree_entry(source, worker_module).object_identity,
        }
        worker = {
            **worker_material,
            "worker_evidence_identity": domain_identity(
                PHASE3B_WORKER_EVIDENCE_DOMAIN, worker_material
            ),
        }
        workers.append({"material": worker, "result": result})
    workers.sort(key=lambda item: item["material"]["worker_evidence_identity"])
    aggregate = aggregate_evidence(
        source_commit=source,
        runtime_contract_identity=runtime_contract.runtime_contract_identity,
        dependency_environment_identity=runtime["dependency_environment_identity"],
        adapter_identity=adapter["adapter_identity"],
        readiness_test_identity=readiness_test["readiness_test_evidence_identity"],
        input_snapshot_identities=sorted(item["input_snapshot_identity"] for item in snapshots),
        dataset_identities=sorted(item["dataset_validation_evidence_identity"] for item in datasets),
        projection_identities=sorted(item["projection_evidence_identity"] for item in projections),
        replay_identity=replay["replay_evidence_identity"],
        population_identity=population["population_accounting_evidence_identity"],
        profile_identity=profile["profile_conformance_evidence_identity"],
        artifact_identity=artifact_evidence["artifact_declaration_evidence_identity"],
        capability_policy_identity=evidence_policy["policy_identity"],
        worker_evidence_identities=[
            item["material"]["worker_evidence_identity"] for item in workers
        ],
        semantic_component_identities=sorted(semantic_components),
        schema_version=2,
    ).aggregate_material

    readiness_specification = _committed_document(
        repository,
        source,
        path=READINESS_SPECIFICATION_V1_1_PATH,
        revision=READINESS_SPECIFICATION_V1_1_REVISION,
        identity_field="specification_identity",
    )
    protocol = _committed_document(
        repository,
        source,
        path=adapter["protocol"]["path"],
        revision=adapter["protocol"]["revision"],
        identity_field="protocol_identity",
        identifier=binding["protocol"]["identifier"],
    )
    execution_specification = _committed_document(
        repository,
        source,
        path=adapter["execution_specification"]["path"],
        revision=adapter["execution_specification"]["revision"],
        identity_field="specification_identity",
    )
    attempt_raw, attempt_blob = _git_blob(
        repository, source, authority.repository_path
    )
    outcome_policy = {
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
    material = {
        "schema": {
            "canonical_encoding_revision": CANONICAL_ENCODING_REVISION,
            "declarations": declarations,
            "schema_registry_identifier": READINESS_V1_1_SCHEMA_REGISTRY_IDENTIFIER,
        },
        "experiment": {
            "canonical_record_path": "docs/research/readiness/synthetic-prospective.json",
            "experiment_configuration_identity": adapter["configuration"]["experiment_configuration_identity"],
            "experiment_identifier": adapter["experiment_identifier"],
        },
        "git_authority": {
            "approved_branch_ref": repository_authority["approved_branch_ref"],
            "repository_authority_identifier": repository_authority["repository_authority_identifier"],
            "source_commit": source,
        },
        "readiness_specification": readiness_specification,
        "control_plane": {"components": components},
        "source_scopes": source_scope_material,
        "protocol": protocol,
        "implementation": implementation,
        "execution_specification": execution_specification,
        "execution_profile": dict(adapter["execution_profile"]),
        "runtime": runtime,
        "configuration": {
            "decision_selection_identity": adapter["configuration"]["decision_selection_identity"],
            "evidence_preparation_policy_identity": evidence_policy["policy_identity"],
            "experiment_configuration_identity": adapter["configuration"]["experiment_configuration_identity"],
        },
        "external_inputs": {
            "declarations": input_declarations,
            "input_snapshot_identities": [item["input_snapshot_identity"] for item in snapshots],
            "dataset_validation_evidence_identities": sorted(item["dataset_validation_evidence_identity"] for item in datasets),
            "projection_evidence_identities": sorted(item["projection_evidence_identity"] for item in projections),
        },
        "replay": {
            **{key: value for key, value in replay.items() if key != "schema_version"},
            "population_accounting": {key: value for key, value in population.items() if key != "schema_version"},
        },
        "artifacts": {
            "artifact_declaration_evidence_identity": artifact_evidence["artifact_declaration_evidence_identity"],
            "declarations": adapter["artifacts"]["declarations"],
            "dependency_order": artifact_evidence["dependency_order"],
            "output_policy_identity": artifact_evidence["output_policy_identity"],
        },
        "outcome_policy": outcome_policy,
        "validation": {
            "additional_test_selectors": readiness_test["additional_selectors"],
            "collected_node_ids": readiness_test["collected_node_ids"],
            "compile_passed": True,
            "evidence_preparation_identity": aggregate["evidence_preparation_identity"],
            "import_passed": True,
            "launch_smoke_selectors": policy["launch_smoke_selectors"],
            "mandatory_test_selectors": readiness_test["mandatory_selectors"],
            "readiness_test_evidence_identity": readiness_test["readiness_test_evidence_identity"],
            "reconstruction_passed": True,
            "test_policy_identity": policy["policy_identity"],
            "test_results": readiness_test["results"],
        },
        "attempt_policy": {
            "allocation_authority_identity": authority.allocation_authority_identity,
            "allocator_client_component_identity": authority.allocator_client_component_identity,
            "allocator_contract_identity": authority.allocator_contract_identity,
            "attempt_authority_contract_byte_count": len(attempt_raw),
            "attempt_authority_contract_git_blob_identity": attempt_blob,
            "attempt_authority_contract_path": authority.repository_path,
            "attempt_authority_contract_sha256": authority.sha256,
            "attempt_identity_domain": "orev3:experiment-attempt:v1\n",
            "attempt_identity_schema_identifier": "attempt-identity-material-v1",
            "attempt_output_declaration_identity": adapter["attempt_output_declaration_identity"],
            "collision_policy": authority.material["collision_policy"],
            "control_storage_component_identity": authority.control_storage_component_identity,
            "control_storage_contract_identity": authority.control_storage_contract_identity,
            "output_namespace_identity_policy": authority.material["output_namespace_identity_policy"],
            "output_policy_identity": artifact_evidence["output_policy_identity"],
            "output_policy_revision": "readiness-v1-output-policy",
            "supported_attempt_kinds": authority.material["supported_attempt_kinds"],
        },
    }
    record = build_readiness_record_v2(material)
    evidence = {
        "aggregate": aggregate,
        "artifacts": artifact_evidence,
        "datasets": datasets,
        "population": population,
        "profile": profile,
        "projections": projections,
        "readiness_test": readiness_test,
        "replay": replay,
        "snapshots": snapshots,
        "workers": workers,
    }
    return repository, record, prerequisites, evidence


def _with_reconstructed_readiness_claim(record, material):
    claimed = copy.deepcopy(material)
    identity_material = dict(claimed)
    identity_material.pop("readiness_identity", None)
    identity = domain_identity(READINESS_RECORD_DOMAIN, identity_material)
    claimed["readiness_identity"] = identity
    return replace(record, material=claimed, readiness_identity=identity)


def _reconstruct_evidence_identity(
    evidence: dict[str, object], domain: str, identity_field: str
) -> None:
    material = dict(evidence)
    material.pop(identity_field, None)
    evidence[identity_field] = domain_identity(domain, material)


def _rebind_aggregate(record, evidence):
    aggregate = evidence["aggregate"]
    aggregate["input_snapshot_identities"] = sorted(
        item["input_snapshot_identity"] for item in evidence["snapshots"]
    )
    aggregate["dataset_evidence_identities"] = sorted(
        item["dataset_validation_evidence_identity"] for item in evidence["datasets"]
    )
    aggregate["projection_evidence_identities"] = sorted(
        item["projection_evidence_identity"] for item in evidence["projections"]
    )
    aggregate["profile_evidence_identity"] = evidence["profile"][
        "profile_conformance_evidence_identity"
    ]
    aggregate["population_evidence_identity"] = evidence["population"][
        "population_accounting_evidence_identity"
    ]
    aggregate["replay_evidence_identity"] = evidence["replay"][
        "replay_evidence_identity"
    ]
    _reconstruct_evidence_identity(
        aggregate,
        "orev3:experiment-evidence-preparation:v1\n",
        "evidence_preparation_identity",
    )
    material = copy.deepcopy(record.material)
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
    return material


def test_prospective_overlays_substitute_v2_v3_without_count_change() -> None:
    assert [len(PHASE2_SCHEMA_POLICY), len(PHASE3A_SCHEMA_POLICY), len(PHASE3B_SCHEMA_POLICY)] == [6, 10, 20]
    assert [len(PROSPECTIVE_PHASE2_SCHEMA_POLICY), len(PROSPECTIVE_PHASE3A_SCHEMA_POLICY), len(PROSPECTIVE_PHASE3B_SCHEMA_POLICY), len(READINESS_V1_1_SCHEMA_POLICY)] == [6, 10, 20, 29]
    assert PROSPECTIVE_PHASE2_SCHEMA_POLICY["readiness-record"][0] == "readiness-record-v2"
    assert PROSPECTIVE_PHASE3A_SCHEMA_POLICY["adapter-declaration"][0] == "adapter-declaration-v3"
    assert PROSPECTIVE_PHASE3B_SCHEMA_POLICY["profile-conformance-evidence"][0] == "profile-conformance-evidence-v2"
    assert PHASE3A_SCHEMA_POLICY["adapter-declaration"][0] == "adapter-declaration-v1"


def test_readiness_record_v2_positive_and_identity_substitution_rejects() -> None:
    record = build_readiness_record_v2(_material())
    validate_readiness_record_v2(record.material)
    assert record.readiness_identity == domain_identity(READINESS_RECORD_DOMAIN, _material())
    changed = copy.deepcopy(record.material)
    changed["readiness_identity"] = SHA
    with pytest.raises(CanonicalControlError, match="identity"):
        from orev3.execution.readiness_record import ReadinessRecordV2
        ReadinessRecordV2.from_mapping(changed)


def test_readiness_record_v2_schema_validates_positive_material() -> None:
    record = build_readiness_record_v2(_material())
    schemas = {kind: parse_json(Path(path).read_bytes()) for kind, (_, path) in READINESS_V1_1_SCHEMA_POLICY.items()}
    registry = {path.rsplit("/", 1)[-1]: schemas[kind] for kind, (_, path) in READINESS_V1_1_SCHEMA_POLICY.items()}
    validate_json_schema_instance(record.material, schemas["readiness-record"], schema_registry=registry)


@pytest.mark.parametrize("kind", ["regular_file", "ordered_file_collection"])
def test_external_input_v3_branches_reconstruct(kind: str) -> None:
    validate_external_input_declaration_v3(_external(kind))


def test_ordered_manifest_reordering_and_duplicate_paths_reject() -> None:
    declaration = _external("ordered_file_collection")
    changed = copy.deepcopy(declaration); changed["members"].reverse()
    with pytest.raises(CanonicalControlError): validate_external_input_declaration_v3(changed)


def test_ordered_manifest_snapshot_preserves_semantic_member_order(tmp_path: Path) -> None:
    declaration = _external("ordered_file_collection")
    locators = {}
    for member, payload in zip(declaration["members"], (b"a", b"bb"), strict=True):
        path = tmp_path / member["logical_identifier"]
        path.write_bytes(payload)
        member["byte_count"] = len(payload)
        import hashlib
        member["sha256"] = hashlib.sha256(payload).hexdigest()
        member["member_identity"] = domain_identity(EXTERNAL_INPUT_MEMBER_DOMAIN, {key: value for key, value in member.items() if key != "member_identity"})
        locators[member["member_path"]] = path
    declaration["aggregate_byte_count"] = 3
    declaration["manifest_identity"] = domain_identity(EXTERNAL_INPUT_MANIFEST_DOMAIN, {"external_input_identifier": "input", "input_version": "v1", "manifest_revision": declaration["manifest_revision"], "members": declaration["members"]})
    declaration["external_input_identity"] = domain_identity(EXTERNAL_INPUT_DECLARATION_DOMAIN, {key: value for key, value in declaration.items() if key != "external_input_identity"})
    limits = ResourceLimits(10, 10, 20, 20, 20, 10, 1000, 1000, 1000)
    snapshot = snapshot_declared_input(declaration, locator_paths=locators, object_store=tmp_path / "objects", limits=limits)
    assert [item["logical_member_identifier"] for item in snapshot.material["members"]] == ["first", "second"]
    changed = copy.deepcopy(declaration); changed["members"][1]["member_path"] = changed["members"][0]["member_path"]
    with pytest.raises(CanonicalControlError): validate_external_input_declaration_v3(changed)


def test_population_branches_and_positional_reconciliation() -> None:
    material = _material(); source = "4" * 64; replay = "5" * 64; decision = "6" * 64
    material["replay"].update({"ordered_source_unit_identities": [source], "ordered_replay_unit_identities": [replay], "ordered_decision_identities": [decision]})
    material["replay"]["population_accounting"].update({"dispositions": [{"decision_identity": decision, "reason": "included_by_governed_selector", "replay_unit_identity": replay, "source_unit_identity": source, "status": "replay_included"}], "source_count": 1, "included_count": 1, "excluded_count": 0})
    validate_readiness_record_v2(build_readiness_record_v2(material).material)
    material["replay"]["population_accounting"]["dispositions"][0]["decision_identity"] = "not_applicable"
    with pytest.raises(CanonicalControlError): build_readiness_record_v2(material)


def test_artifact_dependency_order_is_canonical_and_cycles_reject() -> None:
    declarations = [{"artifact_identifier": name, "declaration_identity": char * 64, "dependencies": deps, "relative_path": f"out/{name}.json"} for name, char, deps in (("b", "2", []), ("a", "3", []), ("c", "4", ["a", "b"]))]
    assert canonical_artifact_dependency_order(declarations) == ["a", "b", "c"]
    declarations[0]["dependencies"] = ["c"]
    with pytest.raises(CanonicalControlError, match="cycle"): canonical_artifact_dependency_order(declarations)


def test_git_validator_reconstructs_complete_prospective_candidate(
    tmp_path: Path,
) -> None:
    repository, record, prerequisites, evidence = _prospective_git_candidate(tmp_path)
    registry = validate_record_v2_git_bindings(
        repository,
        record,
        prerequisites=prerequisites,
        phase3b_evidence=evidence,
    )
    assert len(registry.schemas_by_object_kind) == 29


@pytest.mark.parametrize(
    "attack",
    (
        "schema",
        "component_identifier",
        "adapter_registry",
        "runtime",
        "configuration",
        "source_scope",
        "attempt_policy",
        "readiness_identity",
    ),
)
def test_git_validator_rejects_direct_authority_substitution(
    tmp_path: Path, attack: str
) -> None:
    repository, record, prerequisites, evidence = _prospective_git_candidate(tmp_path)
    material = copy.deepcopy(record.material)
    if attack == "schema":
        material["schema"]["declarations"][0]["sha256"] = SHA
    elif attack == "component_identifier":
        component = next(
            item
            for item in material["control_plane"]["components"]
            if item["role"] == "readiness_validator"
        )
        component["component_identifier"] = "caller-readiness-validator"
        component["component_identity"] = reconstruct_control_component_identity(component)
        material["control_plane"]["components"].sort(
            key=lambda item: item["component_identifier"]
        )
    elif attack == "adapter_registry":
        material["implementation"]["adapter_registry_identity"] = SHA
    elif attack == "runtime":
        material["runtime"]["dependency_environment_identity"] = SHA
    elif attack == "configuration":
        material["configuration"]["evidence_preparation_policy_identity"] = SHA
    elif attack == "source_scope":
        material["source_scopes"] = [
            item
            for item in material["source_scopes"]
            if item["repository_path"] != "src/orev3/execution/canonical.py"
        ]
    elif attack == "attempt_policy":
        material["attempt_policy"]["allocation_authority_identity"] = SHA
    else:
        material["readiness_identity"] = SHA
        tampered = replace(record, material=material, readiness_identity=SHA)
        with pytest.raises(GitAuthorityError):
            validate_record_v2_git_bindings(
                repository,
                tampered,
                prerequisites=prerequisites,
                phase3b_evidence=evidence,
            )
        return
    tampered = _with_reconstructed_readiness_claim(record, material)
    with pytest.raises(GitAuthorityError):
        validate_record_v2_git_bindings(
            repository,
            tampered,
            prerequisites=prerequisites,
            phase3b_evidence=evidence,
        )


@pytest.mark.parametrize(
    "attack", ("snapshot", "dataset", "projection", "profile", "population")
)
def test_git_validator_rejects_rehashed_detached_evidence_substitution(
    tmp_path: Path, attack: str
) -> None:
    repository, record, prerequisites, original = _prospective_git_candidate(tmp_path)
    evidence = copy.deepcopy(original)
    if attack == "snapshot":
        snapshot = evidence["snapshots"][0]
        snapshot["members"][0]["sha256"] = SHA
        _reconstruct_evidence_identity(
            snapshot,
            "orev3:experiment-immutable-input-snapshot:v1\n",
            "input_snapshot_identity",
        )
    elif attack == "dataset":
        declaration = prerequisites.adapter.material["external_inputs"]["declarations"][0]
        contract = prerequisites.adapter.material["evidence_preparation"]["dataset_contracts"][0]
        old = evidence["datasets"][0]
        changed = dataset_evidence(
            external_input_identity=declaration["external_input_identity"],
            snapshot_identity=old["input_snapshot_identity"],
            source_class=contract["source_class"],
            dataset_version=contract["dataset_version"],
            container=contract["container"],
            parser_component_identity=old["parser_component_identity"],
            validator_component_identity=old["validator_component_identity"],
            schema_identity=old["schema_identity"],
            protocol_revision=contract["protocol_revision"],
            record_count=old["ordered_record_count"],
            record_ordering=contract["record_ordering"],
            candidate_order=contract["candidate_order"],
            projection_required=contract["projection_required"],
            dataset_content_identity=SHA,
        )
        evidence["datasets"][0] = changed
        projection = evidence["projections"][0]
        projection["dataset_identity"] = changed["dataset_identity"]
        _reconstruct_evidence_identity(
            projection,
            "orev3:experiment-outcome-blind-projection:v1\n",
            "projection_evidence_identity",
        )
    elif attack == "projection":
        projection = evidence["projections"][0]
        projection["sha256"] = SHA
        projection["projection_identity"] = domain_identity(
            "orev3:experiment-outcome-blind-projection:v1\n",
            {
                "byte_count": projection["byte_count"],
                "ordered_record_count": projection["ordered_record_count"],
                "parser_component_identity": projection["parser_component_identity"],
                "projection_schema_identity": projection["projection_schema_identity"],
                "projector_component_identity": projection["projector_component_identity"],
                "sha256": projection["sha256"],
            },
        )
        _reconstruct_evidence_identity(
            projection,
            "orev3:experiment-outcome-blind-projection:v1\n",
            "projection_evidence_identity",
        )
        evidence["replay"]["projection_identity"] = projection["projection_identity"]
        replay_core = {
            key: evidence["replay"][key]
            for key in (
                "candidate_order",
                "decision_selection_identity",
                "ordered_decision_identities",
                "ordered_replay_unit_identities",
                "ordered_source_unit_identities",
                "projection_identity",
                "replay_preparer_component_identity",
                "selector_component_identity",
            )
        }
        evidence["replay"]["replay_identity"] = domain_identity(
            "orev3:experiment-replay-evidence:v1\n", replay_core
        )
        _reconstruct_evidence_identity(
            evidence["replay"],
            "orev3:experiment-replay-evidence:v1\n",
            "replay_evidence_identity",
        )
    elif attack == "profile":
        profile = evidence["profile"]
        profile["reconciled_artifact_declaration_identities"] = [SHA]
        _reconstruct_evidence_identity(
            profile,
            "orev3:experiment-profile-conformance-evidence:v1\n",
            "profile_conformance_evidence_identity",
        )
    else:
        population = evidence["population"]
        population["permitted_exclusion_reasons"] = ["caller-selected-reason"]
        _reconstruct_evidence_identity(
            population,
            "orev3:experiment-population-accounting-evidence:v1\n",
            "population_accounting_evidence_identity",
        )
    material = _rebind_aggregate(record, evidence)
    if attack == "projection":
        material["replay"] = {
            **{
                key: value
                for key, value in evidence["replay"].items()
                if key != "schema_version"
            },
            "population_accounting": material["replay"]["population_accounting"],
        }
    elif attack == "profile":
        material["outcome_policy"]["profile_conformance_evidence_identity"] = evidence[
            "profile"
        ]["profile_conformance_evidence_identity"]
    elif attack == "population":
        material["replay"]["population_accounting"] = {
            key: value
            for key, value in evidence["population"].items()
            if key != "schema_version"
        }
    tampered = _with_reconstructed_readiness_claim(record, material)
    with pytest.raises(GitAuthorityError):
        validate_record_v2_git_bindings(
            repository,
            tampered,
            prerequisites=prerequisites,
            phase3b_evidence=evidence,
        )


@pytest.mark.parametrize(
    "attack",
    (
        "command",
        "capability_replacement",
        "capability_missing",
        "capability_extra",
        "capability_duplicate",
        "capability_cross_context",
    ),
)
def test_git_validator_rejects_rehashed_worker_authority_substitution(
    tmp_path: Path, attack: str
) -> None:
    repository, record, prerequisites, evidence = _prospective_git_candidate(tmp_path)
    worker = next(
        item["material"]
        for item in evidence["workers"]
        if item["material"]["worker_kind"] == "INPUT_PROJECTOR"
    )
    original_capability = worker["input_capability_identities"][0]
    if attack == "command":
        worker["command_identity"] = SHA
    elif attack == "capability_replacement":
        worker["input_capability_identities"] = [SHA]
    elif attack == "capability_missing":
        worker["input_capability_identities"] = []
    elif attack == "capability_extra":
        worker["input_capability_identities"] = sorted(
            [original_capability, SHA]
        )
    elif attack == "capability_duplicate":
        worker["input_capability_identities"] = [
            original_capability,
            original_capability,
        ]
    else:
        worker["input_capability_identities"] = [
            evidence["replay"]["projection_identity"]
        ]

    worker_material = dict(worker)
    worker_material.pop("worker_evidence_identity")
    worker["worker_evidence_identity"] = domain_identity(
        PHASE3B_WORKER_EVIDENCE_DOMAIN, worker_material
    )
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
    material = copy.deepcopy(record.material)
    material["validation"]["evidence_preparation_identity"] = evidence[
        "aggregate"
    ]["evidence_preparation_identity"]
    tampered = _with_reconstructed_readiness_claim(record, material)
    with pytest.raises(GitAuthorityError, match="worker"):
        validate_record_v2_git_bindings(
            repository,
            tampered,
            prerequisites=prerequisites,
            phase3b_evidence=evidence,
        )


def test_control_component_identifier_substitution_rejects() -> None:
    material = _material()
    component = next(item for item in material["control_plane"]["components"] if item["role"] == "readiness_validator")
    component["component_identifier"] = "other-validator"
    component["component_identity"] = domain_identity(CONTROL_COMPONENT_DOMAIN, {key: value for key, value in component.items() if key != "component_identity"})
    material["control_plane"]["components"].sort(key=lambda item: item["component_identifier"])
    with pytest.raises(CanonicalControlError, match="governed"):
        build_readiness_record_v2(material)


def test_characterization_authorization_route_rejects() -> None:
    material = _material(); material["outcome_policy"]["authorization_contract_identity"] = SHA
    with pytest.raises(CanonicalControlError): build_readiness_record_v2(material)


def test_profile_conformance_v2_closed_branches() -> None:
    schema = parse_json(Path("src/orev3/execution/schemas/v1/profile-conformance-evidence-v2.schema.json").read_bytes())
    characterization = {"outcome_capability": "prohibited_and_not_performed", "profile_conformance_evidence_identity": SHA, "profile_contract_identities": [], "profile_identity": SHA, "profile_name": "outcome_blind_characterization_v1", "reconciled_artifact_declaration_identities": [SHA], "schema_version": 2, "validated_artifact_identifiers": ["report"]}
    validate_json_schema_instance(characterization, schema, schema_registry={})
    characterization["authorization_contract_identity"] = SHA
    with pytest.raises(CanonicalControlError): validate_json_schema_instance(characterization, schema, schema_registry={})
    contracts = [f"{index:x}" * 64 for index in range(1, 7)]
    outcome = {"authorization_contract_identity": contracts[0], "outcome_capability": "outcome_aware_authorized_only", "profile_conformance_evidence_identity": SHA, "profile_contract_identities": contracts, "profile_identity": SHA, "profile_name": "outcome_aware_v1", "reconciled_artifact_declaration_identities": [SHA], "schema_version": 2, "validated_artifact_identifiers": ["ranking"]}
    validate_json_schema_instance(outcome, schema, schema_registry={})
