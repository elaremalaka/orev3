from __future__ import annotations

import json
from pathlib import Path

import pytest

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    parse_json,
    validate_json_schema_instance,
)
from orev3.execution.readiness_record import (
    PHASE2_SCHEMA_DOCUMENT_POLICY,
    PHASE2_SCHEMA_POLICY,
    PHASE3B_SCHEMA_POLICY,
    READINESS_V1_1_SCHEMA_POLICY,
    READINESS_SPECIFICATION_SHA256,
    TEST_POLICY_DOMAIN,
    build_launch_authority_snapshot,
    canonical_readiness_record_path,
    load_readiness_record_bytes,
    reconstruct_control_component_identity,
    reconstruct_document_binding_identity,
    reconstruct_implementation_identity,
    reconstruct_readiness_identity,
    validate_readiness_record,
    validate_readiness_test_policy,
    validate_launch_authority_snapshot,
)
from orev3.execution.readiness import load_repository_authority


ZERO_SHA = "0" * 64
ONE_SHA = "1" * 64
ZERO_GIT = "0" * 40
ONE_GIT = "1" * 40


def readiness_record_material(
    *, source_commit: str = ZERO_GIT, experiment_identifier: str = "rq999-experiment-001"
) -> dict[str, object]:
    record_path = str(canonical_readiness_record_path(experiment_identifier))
    component_roles = (
        "adapter",
        "adapter_registry",
        "allocator_client",
        "allocator_contract",
        "canonical_serializer",
        "official_orchestrator",
        "outcome_gate",
        "readiness_validator",
    )
    component_paths = {
        "adapter": "src/orev3/experiments/synthetic.py",
        "adapter_registry": "src/orev3/execution/registry.py",
        "allocator_client": "src/orev3/execution/attempts.py",
        "allocator_contract": "src/orev3/execution/attempts.py",
        "canonical_serializer": "src/orev3/execution/canonical.py",
        "official_orchestrator": "src/orev3/execution/orchestrator.py",
        "outcome_gate": "src/orev3/execution/outcome_gate.py",
        "readiness_validator": "src/orev3/execution/readiness.py",
    }
    material: dict[str, object] = {
        "artifacts": {"declarations": []},
        "attempt_policy": {
            "allocator_contract_identity": ZERO_SHA,
            "attempt_identity_domain": "orev3:experiment-attempt:v1",
            "collision_policy": "reject_any_existing_path",
            "output_policy_identity": ONE_SHA,
        },
        "configuration": {
            "decision_selection_identity": ZERO_SHA,
            "experiment_configuration_identity": ONE_SHA,
        },
        "control_plane": {
            "components": [
                {
                    "component_identifier": role,
                    "component_identity": ZERO_SHA,
                    "git_object_identity": ZERO_GIT,
                    "path": component_paths[role],
                    "role": role,
                    "sha256": ZERO_SHA,
                }
                for role in component_roles
            ]
        },
        "execution_profile": {
            "profile_identity": ZERO_SHA,
            "profile_name": "outcome_blind_characterization_v1",
        },
        "execution_specification": {
            "byte_count": 1,
            "git_blob_identity": ZERO_GIT,
            "path": "docs/research/specifications/execution-v2.md",
            "revision": "execution-v2",
            "sha256": ZERO_SHA,
            "specification_identity": ZERO_SHA,
        },
        "experiment": {
            "canonical_record_path": record_path,
            "experiment_configuration_identity": ONE_SHA,
            "experiment_identifier": experiment_identifier,
        },
        "external_inputs": {"declarations": []},
        "git_authority": {
            "approved_branch_ref": "refs/heads/research/post-v1",
            "repository_authority_identifier": "orev3-primary-repository-v1",
            "source_commit": source_commit,
        },
        "implementation": {
            "adapter_identifier": "synthetic-adapter",
            "entry_point": "orev3.synthetic:run",
            "implementation_git_blob_identity": ZERO_GIT,
            "implementation_identity": ZERO_SHA,
            "implementation_path": "src/orev3/experiments/synthetic.py",
            "implementation_sha256": ZERO_SHA,
            "protocol_binding_byte_count": 1,
            "protocol_binding_git_blob_identity": ZERO_GIT,
            "protocol_binding_identity": ONE_SHA,
            "protocol_binding_path": "config/research/readiness/experiments/synthetic-experiment-binding.json",
            "protocol_binding_sha256": ZERO_SHA,
        },
        "outcome_policy": {
            "authorization_contract_identity": ZERO_SHA,
            "outcome_capability": "prohibited_and_not_performed",
            "policy_identity": ONE_SHA,
            "profile_name": "outcome_blind_characterization_v1",
        },
        "protocol": {
            "byte_count": 1,
            "git_blob_identity": ZERO_GIT,
            "identifier": "synthetic-protocol",
            "path": "docs/research/experiments/synthetic.md",
            "protocol_identity": ZERO_SHA,
            "revision": "1",
            "sha256": ZERO_SHA,
        },
        "readiness_identity": ZERO_SHA,
        "readiness_specification": {
            "byte_count": 1,
            "git_blob_identity": ZERO_GIT,
            "path": "docs/research/specifications/experiment-execution-readiness-v1.md",
            "revision": "experiment-execution-readiness-v1",
            "sha256": READINESS_SPECIFICATION_SHA256,
            "specification_identity": ZERO_SHA,
        },
        "replay": {
            "candidate_order": [0, 1],
            "construction_identity": ZERO_SHA,
            "decision_selection_order": ["round", "observation"],
            "population_accounting_identity": ONE_SHA,
            "replay_identity": ZERO_SHA,
        },
        "runtime": {
            "dependency_manifest_git_blob_identity": ZERO_GIT,
            "dependency_manifest_path": "requirements/readiness-v1.lock",
            "dependency_manifest_sha256": ZERO_SHA,
            "environment_contract_identity": ONE_SHA,
            "python_implementation": "CPython",
            "python_version": "3.12.0",
            "runtime_identity": ZERO_SHA,
        },
        "schema": {
            "canonical_encoding_revision": "readiness-v1-canonical-json",
            "declarations": [
                {
                    "byte_count": 1,
                    "git_blob_identity": ZERO_GIT,
                    "object_kind": object_kind,
                    "path": path,
                    "schema_identifier": schema_identifier,
                    "sha256": PHASE2_SCHEMA_DOCUMENT_POLICY[object_kind][1],
                }
                for object_kind, (schema_identifier, path) in sorted(
                    PHASE2_SCHEMA_POLICY.items()
                )
            ],
            "schema_registry_identifier": "readiness-phase2-schema-registry-v1",
        },
        "source_scopes": [
            {
                "git_mode": "040000",
                "git_object_identity": ZERO_GIT,
                "nesting": "contains_declared_children",
                "repository_path": "src/orev3",
                "role": "source_tree",
            },
            {"git_mode": "040000", "git_object_identity": ZERO_GIT, "nesting": "nested", "parent_path": "src/orev3", "repository_path": "src/orev3/execution", "role": "control_plane"},
            {"git_mode": "040000", "git_object_identity": ZERO_GIT, "nesting": "nested", "parent_path": "src/orev3", "repository_path": "src/orev3/execution/schemas/v1", "role": "readiness_schema"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "config/research/readiness/experiments/synthetic-experiment-binding.json", "role": "configuration"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "config/research/readiness/readiness-test-policy-v1.json", "role": "readiness_test_policy"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "config/research/readiness/repository-authority-v1.json", "role": "repository_authority"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "docs/research/experiments/synthetic.md", "role": "protocol"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "docs/research/specifications/execution-v2.md", "role": "execution_specification"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "docs/research/specifications/experiment-execution-readiness-v1.md", "role": "readiness_specification"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "requirements/readiness-v1.lock", "role": "dependency_manifest"},
            {"git_mode": "100644", "git_object_identity": ZERO_GIT, "nesting": "nested", "parent_path": "src/orev3", "repository_path": "src/orev3/experiments/synthetic.py", "role": "implementation"},
            {"git_mode": "040000", "git_object_identity": ZERO_GIT, "nesting": "top_level", "repository_path": "tests/execution", "role": "readiness_tests"}
        ],
        "validation": {
            "compile_passed": True,
            "import_passed": True,
            "reconstruction_passed": True,
            "test_policy_identity": "e2eff3859d6400ca7b4dde0528900055b377cc40c4561fece8ec259af7d34720",
            "test_results_identity": ONE_SHA,
            "test_selectors": ["tests/execution/test_readiness_mandatory_v1.py"],
        },
    }
    for component in material["control_plane"]["components"]:  # type: ignore[index]
        component["component_identity"] = reconstruct_control_component_identity(component)
    material["source_scopes"] = sorted(  # type: ignore[index]
        material["source_scopes"],  # type: ignore[arg-type]
        key=lambda item: (item["repository_path"], item["role"]),
    )
    for section, identity_field in (
        ("readiness_specification", "specification_identity"),
        ("protocol", "protocol_identity"),
        ("execution_specification", "specification_identity"),
    ):
        binding = material[section]  # type: ignore[index]
        binding[identity_field] = reconstruct_document_binding_identity(
            binding, identity_field=identity_field
        )
    material["implementation"]["implementation_identity"] = reconstruct_implementation_identity(  # type: ignore[index]
        material["implementation"]  # type: ignore[arg-type]
    )
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    return material


def test_record_round_trip_and_identity() -> None:
    material = readiness_record_material()
    raw = canonical_bytes(material)
    record = load_readiness_record_bytes(
        raw, expected_experiment_identifier="rq999-experiment-001"
    )

    assert record.readiness_identity == reconstruct_readiness_identity(material)
    assert record.source_commit == ZERO_GIT
    assert record.canonical_record_path == (
        "docs/research/readiness/rq999-experiment-001.json"
    )


def test_record_rejects_reconstructable_but_wrong_readiness_identity() -> None:
    material = readiness_record_material()
    material["readiness_identity"] = ZERO_SHA
    with pytest.raises(CanonicalControlError, match="does not reconstruct"):
        load_readiness_record_bytes(
            canonical_bytes(material),
            expected_experiment_identifier="rq999-experiment-001",
        )


@pytest.mark.parametrize("mutation", ("unknown", "null", "unordered"))
def test_record_rejects_schema_and_canonical_violations(mutation: str) -> None:
    material = readiness_record_material()
    if mutation == "unknown":
        material["unexpected"] = True
    elif mutation == "null":
        material["runtime"]["python_version"] = None  # type: ignore[index]
    else:
        material["validation"]["test_selectors"] = ["z", "a"]  # type: ignore[index]
    with pytest.raises(CanonicalControlError):
        load_readiness_record_bytes(
            canonical_bytes(material),
            expected_experiment_identifier="rq999-experiment-001",
        )


def test_launch_snapshot_reconstructs_and_has_no_execution_state() -> None:
    snapshot = build_launch_authority_snapshot(
        repository_authority_identifier="orev3-primary-repository-v1",
        approved_branch_ref="refs/heads/research/post-v1",
        remote_head_commit=ONE_GIT,
        canonical_record_path="docs/research/readiness/rq999-experiment-001.json",
        readiness_record_blob_identity=ZERO_GIT,
        readiness_seal_commit=ONE_GIT,
        readiness_identity=ZERO_SHA,
        source_commit=ZERO_GIT,
    )
    validate_launch_authority_snapshot(snapshot.to_mapping())

    assert "state" not in snapshot.to_mapping()
    assert "EXECUTION_READY" not in repr(snapshot)


def test_machine_schemas_are_strict_null_free_documents() -> None:
    schema_root = Path("src/orev3/execution/schemas/v1")
    expected = {Path(path).name for _, path in READINESS_V1_1_SCHEMA_POLICY.values()}
    assert {path.name for path in schema_root.glob("*.json")} == expected
    for path in schema_root.glob("*.json"):
        material = json.loads(path.read_text(encoding="utf-8"))
        assert material["$schema"].endswith("2020-12/schema")
        assert "null" not in path.read_text(encoding="utf-8")


def test_schema_registry_cannot_be_incomplete_or_use_fake_digest() -> None:
    material = readiness_record_material()
    material["schema"]["declarations"].pop()  # type: ignore[index]
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    with pytest.raises(CanonicalControlError, match="registry is incomplete"):
        load_readiness_record_bytes(
            canonical_bytes(material),
            expected_experiment_identifier="rq999-experiment-001",
        )


def test_mandatory_protocol_scope_cannot_be_omitted() -> None:
    material = readiness_record_material()
    material["source_scopes"] = [  # type: ignore[index]
        scope
        for scope in material["source_scopes"]  # type: ignore[index]
        if scope["role"] != "protocol"
    ]
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    with pytest.raises(CanonicalControlError, match="mandatory governed scope"):
        load_readiness_record_bytes(
            canonical_bytes(material),
            expected_experiment_identifier="rq999-experiment-001",
        )

    material = readiness_record_material()
    material["schema"]["declarations"][0]["sha256"] = "f" * 64  # type: ignore[index]
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    with pytest.raises(CanonicalControlError, match="digest conflicts"):
        load_readiness_record_bytes(
            canonical_bytes(material),
            expected_experiment_identifier="rq999-experiment-001",
        )


def test_schema_and_python_enforce_external_input_cardinality_and_order() -> None:
    schema = parse_json(
        Path(
            "src/orev3/execution/schemas/v1/readiness-record.schema.json"
        ).read_bytes()
    )
    registry = {
        path.rsplit("/", 1)[-1]: parse_json(Path(path).read_bytes())
        for _, path in PHASE2_SCHEMA_POLICY.values()
    }
    material = readiness_record_material()
    regular = {
        "external_input_identifier": "regular-b",
        "external_input_identity": ZERO_SHA,
        "input_kind": "regular_file",
        "members": [
            {"byte_count": 1, "member_path": "data/a", "sha256": ZERO_SHA},
            {"byte_count": 1, "member_path": "data/b", "sha256": ONE_SHA},
        ],
        "parser_identity": ZERO_SHA,
        "role": "dataset",
        "schema_identity": ONE_SHA,
    }
    material["external_inputs"]["declarations"] = [regular]  # type: ignore[index]
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    with pytest.raises(CanonicalControlError, match="exactly one member"):
        load_readiness_record_bytes(
            canonical_bytes(material),
            expected_experiment_identifier="rq999-experiment-001",
        )
    with pytest.raises(CanonicalControlError, match="exactly one member"):
        validate_json_schema_instance(material, schema, schema_registry=registry)

    material = readiness_record_material()
    first = {**regular, "members": [regular["members"][0]]}
    second = {
        **first,
        "external_input_identifier": "regular-a",
        "external_input_identity": ONE_SHA,
        "members": [
            {"byte_count": 1, "member_path": "data/z", "sha256": ZERO_SHA}
        ],
    }
    material["external_inputs"]["declarations"] = [second, first]  # type: ignore[index]
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    with pytest.raises(CanonicalControlError, match="not canonically ordered"):
        load_readiness_record_bytes(
            canonical_bytes(material),
            expected_experiment_identifier="rq999-experiment-001",
        )
    with pytest.raises(CanonicalControlError, match="not canonically ordered"):
        validate_json_schema_instance(material, schema, schema_registry=registry)


def _schema_registry() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    schemas = {
        object_kind: parse_json(Path(path).read_bytes())
        for object_kind, (_, path) in PHASE2_SCHEMA_POLICY.items()
    }
    registry = {
        path.rsplit("/", 1)[-1]: schemas[object_kind]
        for object_kind, (_, path) in PHASE2_SCHEMA_POLICY.items()
    }
    return schemas, registry


def _assert_python_schema_parity(
    material: dict[str, object],
    *,
    python_validator: object,
    schema_kind: str,
    expected: bool,
) -> None:
    schemas, registry = _schema_registry()
    results: list[bool] = []
    for validator in (
        python_validator,
        lambda value: validate_json_schema_instance(
            value, schemas[schema_kind], schema_registry=registry
        ),
    ):
        try:
            validator(material)  # type: ignore[operator]
        except CanonicalControlError:
            results.append(False)
        else:
            results.append(True)
    assert results == [expected, expected]


@pytest.mark.parametrize(
    ("byte_count", "expected"),
    ((0, True), (1, True), (1_048_576, True), (1_048_577, False)),
)
def test_implementation_protocol_binding_byte_count_parity(
    byte_count: int, expected: bool
) -> None:
    material = readiness_record_material()
    material["implementation"]["protocol_binding_byte_count"] = byte_count  # type: ignore[index]
    _assert_python_schema_parity(
        material,
        python_validator=validate_readiness_record,
        schema_kind="readiness-record",
        expected=expected,
    )


def _readiness_test_policy_material(
    *, policy_identifier: str = "policy", selectors: list[str] | None = None
) -> dict[str, object]:
    material: dict[str, object] = {
        "collection_affecting_paths": [],
        "collection_policy": "double_fresh_collection_exact_match",
        "expected_mandatory_collection_identity": "1" * 64,
        "expected_mandatory_node_count": 1,
        "policy_identifier": policy_identifier,
        "policy_identity": ZERO_SHA,
        "required_selectors": selectors or ["tests/execution"],
        "result_policy": "all_collected_nodes_pass",
        "schema_version": 1,
        "warning_policy": "reject_any_warning",
    }
    identity_material = dict(material)
    del identity_material["policy_identity"]
    material["policy_identity"] = domain_identity(
        TEST_POLICY_DOMAIN, identity_material
    )
    return material


@pytest.mark.parametrize(
    ("length", "expected"), ((127, True), (128, True), (129, False))
)
def test_readiness_test_policy_identifier_length_parity(
    length: int, expected: bool
) -> None:
    material = _readiness_test_policy_material(policy_identifier="p" * length)
    _assert_python_schema_parity(
        material,
        python_validator=validate_readiness_test_policy,
        schema_kind="readiness-test-policy",
        expected=expected,
    )


@pytest.mark.parametrize(
    ("count", "expected"),
    ((0, False), (1_023, True), (1_024, True), (1_025, False)),
)
def test_readiness_test_policy_selector_count_parity(
    count: int, expected: bool
) -> None:
    selectors = [f"tests/selector-{index:04d}" for index in range(count)]
    material = _readiness_test_policy_material(selectors=selectors)
    if count == 0:
        material["required_selectors"] = []
        identity_material = dict(material)
        del identity_material["policy_identity"]
        material["policy_identity"] = domain_identity(
            TEST_POLICY_DOMAIN, identity_material
        )
    _assert_python_schema_parity(
        material,
        python_validator=validate_readiness_test_policy,
        schema_kind="readiness-test-policy",
        expected=expected,
    )


@pytest.mark.parametrize(
    ("length", "expected"), ((511, True), (512, True), (513, False))
)
def test_readiness_test_policy_selector_length_parity(
    length: int, expected: bool
) -> None:
    material = _readiness_test_policy_material(selectors=["s" * length])
    _assert_python_schema_parity(
        material,
        python_validator=validate_readiness_test_policy,
        schema_kind="readiness-test-policy",
        expected=expected,
    )


@pytest.mark.parametrize("case", ("duplicate", "unknown", "null"))
def test_readiness_test_policy_structural_parity(case: str) -> None:
    material = _readiness_test_policy_material()
    if case == "duplicate":
        material["required_selectors"] = ["tests/same", "tests/same"]
    elif case == "unknown":
        material["unexpected"] = True
    else:
        material["required_selectors"] = None
    _assert_python_schema_parity(
        material,
        python_validator=validate_readiness_test_policy,
        schema_kind="readiness-test-policy",
        expected=False,
    )


def test_production_repository_authority_is_canonical_and_credential_free(
    tmp_path: Path,
) -> None:
    path = Path("config/research/readiness/repository-authority-v1.json")
    authority = load_repository_authority(path)
    assert authority.repository_authority_identifier == "orev3-primary-repository-v1"
    assert authority.approved_branch_ref == "refs/heads/research/post-v1"
    assert authority.canonical_fetch_endpoints[0].canonical_endpoint == (
        "https://github.com/elaremalaka/orev3.git"
    )
    linked = tmp_path / "authority.json"
    linked.symlink_to(path.resolve())
    with pytest.raises(CanonicalControlError, match="symlink"):
        load_repository_authority(linked)
