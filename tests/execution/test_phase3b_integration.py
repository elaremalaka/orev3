from __future__ import annotations

import hashlib
import json
import inspect
import shutil
import threading
import time
from pathlib import Path

import pytest

from orev3.execution.canonical import canonical_bytes, domain_identity, parse_canonical_bytes
import orev3.execution.evidence_preparation as evidence_module
from orev3.execution.evidence_preparation import EvidenceAuthorityGeneration, EvidencePreparationDisposition, _collect_evidence_preparation_evidence, validate_evidence_preparation
from orev3.execution.phase3b_components import PROJECTION_SCHEMA_CONTRACT_DOMAIN, RAW_SCHEMA_CONTRACT_DOMAIN, resolve_component
from orev3.execution.contract_validation import reconstruct_profile_binding_identity
from orev3.execution.git_state import GitRepository
from orev3.execution.readiness_record import PROTOCOL_BINDING_DOMAIN, TEST_POLICY_DOMAIN, RepositoryAuthorityV1, RepositoryEndpoint
from orev3.execution.readiness import load_repository_authority
from orev3.execution.registry import ADAPTER_DOMAIN, ADAPTER_REGISTRY_DOMAIN, ARTIFACT_DECLARATION_DOMAIN, EXTERNAL_INPUT_DECLARATION_DOMAIN, EXTERNAL_INPUT_MANIFEST_DOMAIN, EXTERNAL_INPUT_MEMBER_DOMAIN
from orev3.execution.test_policy import READINESS_TEST_COLLECTION_DOMAIN

from test_phase3a_preparation import ARTIFACT_STORE, git, synthetic_repository, write
from test_phase3c_readiness_contracts import (
    _seal_synthetic_authority_context,
    _write_adapter_and_registry,
    prospective_repository,
)

ZERO = "0" * 64


def _file_remote_authority(repository: GitRepository) -> RepositoryAuthorityV1:
    committed = load_repository_authority(
        repository.root / "config/research/readiness/repository-authority-v1.json"
    )
    return RepositoryAuthorityV1(
        committed.schema_version,
        committed.repository_authority_identifier,
        committed.git_object_format,
        committed.approved_branch_ref,
        (
            RepositoryEndpoint(
                "file", repository.text("remote", "get-url", "origin")
            ),
        ),
    )


def test_prospective_detached_worker_accepts_exact_zero_input(
    tmp_path: Path,
) -> None:
    repository, _, _ = prospective_repository(tmp_path, zero_input=True)
    git(repository.root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    evidence = _collect_evidence_preparation_evidence(
        repository,
        "synthetic-prospective",
        operational_input_locators={},
        authority=_file_remote_authority(repository),
        allow_test_file_remote=True,
        artifact_store_root=ARTIFACT_STORE,
        generation=EvidenceAuthorityGeneration.PROSPECTIVE_V1_1,
    )
    material = evidence.aggregate_material
    assert material["schema_version"] == 2
    assert material["input_snapshot_identities"] == []
    assert material["dataset_evidence_identities"] == []
    assert material["projection_evidence_identities"] == []
    assert len(material["semantic_component_identities"]) == 4
    assert len(material["worker_evidence_identities"]) == 4


def test_prospective_detached_worker_accepts_adapter_v4_configuration_resource(
    tmp_path: Path,
) -> None:
    repository, _, _ = prospective_repository(
        tmp_path,
        zero_input=True,
        adapter_v4_configuration_resource=True,
    )
    git(repository.root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    evidence = _collect_evidence_preparation_evidence(
        repository,
        "synthetic-prospective",
        operational_input_locators={},
        authority=_file_remote_authority(repository),
        allow_test_file_remote=True,
        artifact_store_root=ARTIFACT_STORE,
        generation=EvidenceAuthorityGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE,
    )
    material = evidence.aggregate_material
    assert material["schema_version"] == 2
    assert material["input_snapshot_identities"] == []
    assert material["dataset_evidence_identities"] == []
    assert material["projection_evidence_identities"] == []
    assert len(material["semantic_component_identities"]) == 4
    assert len(material["worker_evidence_identities"]) == 4


def test_prospective_detached_worker_accepts_ordered_collection(
    tmp_path: Path,
) -> None:
    repository, _, _ = prospective_repository(tmp_path)
    root = repository.root
    descriptor_path = "config/research/readiness/experiments/synthetic-adapter-v1.json"
    descriptor = parse_canonical_bytes((root / descriptor_path).read_bytes())
    first = (
        b'{"candidates":[1,2],"eligible":true,'
        b'"exclusion_reason":"not_applicable","observation_index":0,'
        b'"outcome":"hidden-a","source_unit_key":"unit-a"}\n'
    )
    second = (
        b'{"candidates":[1,2],"eligible":false,'
        b'"exclusion_reason":"missing_observation","observation_index":0,'
        b'"outcome":"hidden-b","source_unit_key":"unit-b"}\n'
    )
    input_paths = (tmp_path / "ordered-a.jsonl", tmp_path / "ordered-b.jsonl")
    for path, payload in zip(input_paths, (first, second), strict=True):
        path.write_bytes(payload)
    declaration = descriptor["external_inputs"]["declarations"][0]
    declaration["input_kind"] = "ordered_file_collection"
    declaration["members"] = []
    for index, (logical, locator, payload) in enumerate(
        zip(("first", "second"), ("synthetic-input-a", "synthetic-input-b"), (first, second), strict=True)
    ):
        member = {
            "byte_count": len(payload),
            "logical_identifier": logical,
            "member_identity": ZERO,
            "member_order": index,
            "member_path": locator,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        member["member_identity"] = domain_identity(
            EXTERNAL_INPUT_MEMBER_DOMAIN,
            {key: value for key, value in member.items() if key != "member_identity"},
        )
        declaration["members"].append(member)
    declaration["aggregate_byte_count"] = len(first) + len(second)
    declaration["manifest_revision"] = "external-input-ordered-file-manifest-v1"
    declaration["manifest_identity"] = domain_identity(
        EXTERNAL_INPUT_MANIFEST_DOMAIN,
        {
            "external_input_identifier": declaration["external_input_identifier"],
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
    descriptor["evidence_preparation"]["decision_selection"][
        "permitted_exclusion_reasons"
    ] = ["missing_observation"]
    _write_adapter_and_registry(root, descriptor)
    _seal_synthetic_authority_context(root, input_mode="declared_input")
    git(root, "add", ".")
    git(root, "commit", "-qm", "prospective ordered Phase-3B input")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    authority = _file_remote_authority(repository)
    evidence = _collect_evidence_preparation_evidence(
        repository,
        "synthetic-prospective",
        operational_input_locators={
            "synthetic-input-a": input_paths[0].resolve(),
            "synthetic-input-b": input_paths[1].resolve(),
        },
        authority=authority,
        allow_test_file_remote=True,
        artifact_store_root=ARTIFACT_STORE,
        generation=EvidenceAuthorityGeneration.PROSPECTIVE_V1_1,
    )
    assert len(evidence.aggregate_material["input_snapshot_identities"]) == 1
    assert len(evidence.aggregate_material["dataset_evidence_identities"]) == 1
    assert len(evidence.aggregate_material["projection_evidence_identities"]) == 1
    assert evidence.aggregate_material["adapter_identity"] == descriptor["adapter_identity"]


def test_complete_synthetic_pre_outcome_evidence_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository, authority, descriptor_path, _ = synthetic_repository(tmp_path)
    root = repository.root
    evidence_policy = Path("config/research/readiness/evidence-preparation-policy-v1.json").read_bytes()
    write(root, "config/research/readiness/evidence-preparation-policy-v1.json", evidence_policy)
    write(root, "tests/execution/test_mandatory.py", b"def test_mandatory():\n    assert True\n")
    mandatory_nodes = ["tests/execution/test_mandatory.py::test_mandatory"]
    test_policy = {"collection_affecting_paths": [], "collection_policy": "double_fresh_collection_exact_match", "expected_mandatory_collection_identity": domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": mandatory_nodes}), "expected_mandatory_node_count": 1, "policy_identifier": "synthetic-phase3b-tests-v1", "policy_identity": ZERO, "required_selectors": ["tests/execution/test_mandatory.py"], "result_policy": "all_collected_nodes_pass", "schema_version": 1, "warning_policy": "reject_any_warning"}
    test_policy["policy_identity"] = domain_identity(TEST_POLICY_DOMAIN, {key: value for key, value in test_policy.items() if key != "policy_identity"})
    write(root, "config/research/readiness/readiness-test-policy-v1.json", canonical_bytes(test_policy))

    race_source = tmp_path / "race-source"
    race_replacement = tmp_path / "race-replacement"
    race_source.mkdir(); race_replacement.mkdir()
    raw = race_source / "synthetic-combined.jsonl"
    raw.write_text(
        '{"candidates":[1,2],"eligible":true,"exclusion_reason":"not_applicable","observation_index":0,"outcome":"synthetic-label-SENTINEL","source_unit_key":"unit-a"}\n'
        '{"candidates":[1,2],"eligible":true,"exclusion_reason":"not_applicable","observation_index":1,"outcome":"another-label-SENTINEL","source_unit_key":"unit-a"}\n'
        '{"candidates":[1,2],"eligible":false,"exclusion_reason":"missing_observation","observation_index":0,"outcome":"third-label-SENTINEL","source_unit_key":"unit-b"}\n',
        encoding="utf-8",
    )
    (race_replacement / raw.name).write_text(
        '{"candidates":[1,2],"eligible":true,"exclusion_reason":"not_applicable","observation_index":0,"outcome":"replacement-that-must-not-be-consumed","source_unit_key":"unit-z"}\n',
        encoding="utf-8",
    )
    raw_schema_path = "config/research/readiness/experiments/synthetic-raw-v1.json"
    projection_schema_path = "config/research/readiness/experiments/synthetic-projection-v1.json"
    common_properties = {"candidates": {"items": {"type": "integer"}, "minItems": 1, "type": "array", "uniqueItems": True}, "eligible": {"type": "boolean"}, "exclusion_reason": {"enum": ["missing_observation", "not_applicable"], "type": "string"}, "observation_index": {"minimum": 0, "type": "integer"}, "source_unit_key": {"pattern": "^[a-z0-9-]+$", "type": "string"}}
    projection_schema = {"$id": "orev3-test://synthetic/outcome-blind-projection-v1", "additionalProperties": False, "properties": common_properties, "required": sorted(common_properties), "type": "object"}
    raw_properties = {**common_properties, "outcome": {"type": "string"}}
    raw_schema = {"$id": "orev3-test://synthetic/raw-combined-v1", "additionalProperties": False, "properties": raw_properties, "required": sorted(raw_properties), "type": "object"}
    raw_schema_raw = canonical_bytes(raw_schema)
    projection_schema_raw = canonical_bytes(projection_schema)
    write(root, raw_schema_path, raw_schema_raw)
    write(root, projection_schema_path, projection_schema_raw)
    component_repository = GitRepository(root)
    component_source = component_repository.resolve_commit("HEAD")
    parser = resolve_component(component_repository, component_source, "canonical-jsonl-raw-parser-v1")
    declaration = {"external_input_identifier": "synthetic-combined", "external_input_identity": ZERO, "input_kind": "regular_file", "members": [{"byte_count": raw.stat().st_size, "logical_identifier": "combined", "member_path": "synthetic-input", "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}], "parser_identity": parser.component_identity, "role": "dataset", "schema_identity": domain_identity(RAW_SCHEMA_CONTRACT_DOMAIN, raw_schema)}
    declaration["external_input_identity"] = domain_identity(EXTERNAL_INPUT_DECLARATION_DOMAIN, {key: value for key, value in declaration.items() if key != "external_input_identity"})
    descriptor = parse_canonical_bytes((root / descriptor_path).read_bytes())
    descriptor["external_inputs"] = {"declarations": [declaration]}
    descriptor["governed_scope_paths"] = sorted(set(descriptor["governed_scope_paths"]) | {raw_schema_path, projection_schema_path})
    descriptor["artifacts"] = {"declarations": [{"artifact_identifier": "characterization-report", "artifact_kind": "characterization_report", "container": "json", "declaration_identity": ZERO, "dependencies": [], "dependency_roles": [], "execution_phase": "characterization", "profile_applicability": "outcome_blind_characterization_v1", "relative_path": "artifacts/characterization.json", "schema_identity": "7" * 64}]}
    artifact = descriptor["artifacts"]["declarations"][0]
    artifact["declaration_identity"] = domain_identity(ARTIFACT_DECLARATION_DOMAIN, {key: value for key, value in artifact.items() if key != "declaration_identity"})
    descriptor["evidence_preparation"] = {
        "dataset_contracts": [{"candidate_order": [1, 2], "container": "canonical_jsonl", "dataset_validator_identifier": "canonical-jsonl-dataset-validator-v1", "dataset_version": "synthetic-v1", "external_input_identifier": "synthetic-combined", "projection_contract_identifier": "synthetic-outcome-blind-v1", "projection_required": True, "projection_schema_identifier": "synthetic-projection-schema-v1", "projection_schema_identity": domain_identity(PROJECTION_SCHEMA_CONTRACT_DOMAIN, projection_schema), "projection_schema_path": projection_schema_path, "projection_schema_sha256": hashlib.sha256(projection_schema_raw).hexdigest(), "projector_identifier": "canonical-jsonl-outcome-blind-projector-v1", "protocol_revision": "1", "raw_parser_identifier": "canonical-jsonl-raw-parser-v1", "raw_schema_identifier": "synthetic-raw-schema-v1", "raw_schema_path": raw_schema_path, "raw_schema_sha256": hashlib.sha256(raw_schema_raw).hexdigest(), "record_ordering": "source_order", "source_class": "combined_outcome_bearing"}],
        "decision_selection": {"configuration_identity": descriptor["configuration"]["decision_selection_identity"], "permitted_exclusion_reasons": ["missing_observation"], "replay_preparer_identifier": "canonical-replay-preparer-v1", "selector_identifier": "latest-eligible-observation-selector-v1", "selector_revision": "1", "target_observation_rule": "latest-eligible-observation", "tie_behavior": "reject-duplicate-observation-index", "tolerance_contract": "exact"},
        "profile_contract_declarations": [],
        "resource_policy_identity": json.loads(evidence_policy)["policy_identity"],
    }
    descriptor["execution_profile"]["profile_identity"] = reconstruct_profile_binding_identity(
        profile_name="outcome_blind_characterization_v1",
        outcome_policy="prohibited_and_not_performed",
        declarations={},
    )
    binding_path = root / descriptor["implementation_binding_path"]
    binding = parse_canonical_bytes(binding_path.read_bytes())
    binding["profile_identity"] = descriptor["execution_profile"]["profile_identity"]
    binding["protocol_binding_identity"] = domain_identity(PROTOCOL_BINDING_DOMAIN, {key: value for key, value in binding.items() if key != "protocol_binding_identity"})
    binding_path.write_bytes(canonical_bytes(binding))
    replay_component = resolve_component(component_repository, component_source, "canonical-replay-preparer-v1")
    descriptor["replay_preparation_contract_identity"] = replay_component.component_identity
    descriptor["replay_preparation_entry_point"] = "orev3.execution.replay_preparation:build_replay_evidence"
    descriptor["adapter_readiness_test_nodes"] = ["tests/execution/test_synthetic_adapter.py::test_synthetic_adapter"]
    descriptor["adapter_identity"] = domain_identity(ADAPTER_DOMAIN, {key: value for key, value in descriptor.items() if key != "adapter_identity"})
    descriptor_raw = canonical_bytes(descriptor)
    write(root, descriptor_path, descriptor_raw)
    registry_path = root / "config/research/readiness/adapter-registry-v1.json"
    registry = parse_canonical_bytes(registry_path.read_bytes())
    registry["descriptors"][0]["descriptor_identity"] = descriptor["adapter_identity"]
    registry["descriptors"][0]["descriptor_sha256"] = hashlib.sha256(descriptor_raw).hexdigest()
    registry["projection_contracts"] = [{
        "dataset_validator_identifier": "canonical-jsonl-dataset-validator-v1",
        "output_container": "canonical_jsonl",
        "projection_contract_identifier": "synthetic-outcome-blind-v1",
        "projection_schema_identifier": "synthetic-projection-schema-v1",
        "projection_schema_identity": domain_identity(PROJECTION_SCHEMA_CONTRACT_DOMAIN, projection_schema),
        "projection_schema_path": projection_schema_path,
        "projection_schema_sha256": hashlib.sha256(projection_schema_raw).hexdigest(),
        "projector_identifier": "canonical-jsonl-outcome-blind-projector-v1",
        "raw_parser_identifier": "canonical-jsonl-raw-parser-v1",
        "raw_schema_identifier": "synthetic-raw-schema-v1",
        "raw_schema_identity": domain_identity(RAW_SCHEMA_CONTRACT_DOMAIN, raw_schema),
        "raw_schema_path": raw_schema_path,
        "raw_schema_sha256": hashlib.sha256(raw_schema_raw).hexdigest(),
    }]
    registry["adapter_registry_identity"] = domain_identity(ADAPTER_REGISTRY_DOMAIN, {key: value for key, value in registry.items() if key != "adapter_registry_identity"})
    registry_path.write_bytes(canonical_bytes(registry))
    # Test-only synchronization inside committed synthetic S.  The production
    # traversal has no timing hook: this fixture pauses after the race-source
    # directory descriptor is open so the pathname can be retargeted.
    race_opened = tmp_path / "race-opened"
    race_release = tmp_path / "race-release"
    filesystem_path = root / "src/orev3/execution/filesystem_capability.py"
    filesystem_source = filesystem_path.read_text(encoding="utf-8")
    hook = (
        "            opened = os.fstat(child)\n"
        f"            if component == 'race-source':\n"
        f"                Path({str(race_opened)!r}).write_text('opened', encoding='utf-8')\n"
        f"                import time\n"
        f"                deadline = time.monotonic() + 10\n"
        f"                while not Path({str(race_release)!r}).exists():\n"
        f"                    if time.monotonic() >= deadline: raise RuntimeError('test race release timed out')\n"
        f"                    time.sleep(0.01)\n"
    )
    assert "            opened = os.fstat(child)\n" in filesystem_source
    filesystem_path.write_text(filesystem_source.replace("            opened = os.fstat(child)\n", hook, 1), encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic Phase 3B evidence source")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")

    dirty_marker = b"raise RuntimeError('dirty developer Phase-3B source was executed')\n"
    dirty_control_paths = (
        "src/orev3/execution/evidence_preparation.py",
        "src/orev3/execution/evidence_preparation_worker.py",
        "src/orev3/execution/runtime.py",
        "src/orev3/execution/input_projection_worker.py",
        "src/orev3/execution/replay_preparation_worker.py",
        "src/orev3/execution/readiness_test_worker.py",
        "src/orev3/execution/projection.py",
        "src/orev3/execution/phase3b_components.py",
    )
    dirty_developer_root = tmp_path / "dirty-developer-source"
    # Use a complete developer-source tree, not a set of ambient shadow
    # modules, then visibly corrupt every trust-bearing Phase-3B route below.
    shutil.copytree(Path("src"), dirty_developer_root / "src")
    for dirty_path in dirty_control_paths:
        write(dirty_developer_root, dirty_path, dirty_marker)
    monkeypatch.setenv("PYTHONPATH", str(dirty_developer_root / "src"))

    race_failure: list[BaseException] = []
    def retarget_after_descriptor_open() -> None:
        try:
            # Phase-3A reconstructs the closed dependency root before the
            # detached controller reaches input traversal.
            deadline = time.monotonic() + 600
            while not race_opened.exists():
                if time.monotonic() >= deadline:
                    raise RuntimeError("descriptor race did not reach synchronization point")
                time.sleep(0.01)
            race_source.rename(tmp_path / "pinned-race-source")
            race_source.symlink_to(race_replacement, target_is_directory=True)
            race_release.write_text("release", encoding="utf-8")
        except BaseException as exc:
            race_failure.append(exc)
            race_release.write_text("release", encoding="utf-8")

    racer = threading.Thread(target=retarget_after_descriptor_open, daemon=True)
    racer.start()
    evidence = _collect_evidence_preparation_evidence(repository, "synthetic-prospective", operational_input_locators={"synthetic-input": raw}, authority=authority, allow_test_file_remote=True, artifact_store_root=ARTIFACT_STORE)
    racer.join(timeout=5)
    assert not racer.is_alive() and not race_failure
    assert race_source.is_symlink()
    assert evidence.aggregate_material["source_commit"] == git(root, "rev-parse", "HEAD")
    assert "readiness_identity" not in evidence.aggregate_material
    assert "outcome" not in json.dumps(evidence.aggregate_material)
    assert "SENTINEL" not in json.dumps(evidence.aggregate_material)
    assert len(evidence.aggregate_material["worker_evidence_identities"]) == 8
    projection_store = root / "data/research/readiness/projections/sha256"
    assert all(b"SENTINEL" not in path.read_bytes() for path in projection_store.iterdir() if path.is_file())
    monkeypatch.setattr(evidence_module, "load_repository_authority", lambda path: authority)
    monkeypatch.setattr(evidence_module, "_collect_evidence_preparation_evidence", lambda *args, **kwargs: evidence)
    authoritative = validate_evidence_preparation(repository, "synthetic-prospective", operational_input_locators={"synthetic-input": raw})
    assert authoritative.disposition == EvidencePreparationDisposition.EVIDENCE_PREPARATION_VALIDATED
    assert authoritative.evidence == evidence.aggregate_material
    assert "authority" not in inspect.signature(validate_evidence_preparation).parameters
    lexical_alias = tmp_path / "lexical-input-alias"; lexical_alias.symlink_to(tmp_path / "pinned-race-source", target_is_directory=True)
    def collect_symlink(*args: object, **kwargs: object):
        return _collect_evidence_preparation_evidence(repository, "synthetic-prospective", operational_input_locators={"synthetic-input": lexical_alias / raw.name}, authority=authority, allow_test_file_remote=True, artifact_store_root=ARTIFACT_STORE)
    monkeypatch.setattr(evidence_module, "_collect_evidence_preparation_evidence", collect_symlink)
    rejected = validate_evidence_preparation(repository, "synthetic-prospective", operational_input_locators={"synthetic-input": lexical_alias / raw.name})
    assert rejected.disposition == EvidencePreparationDisposition.EVIDENCE_PREPARATION_REJECTED
    for dirty_path in dirty_control_paths:
        assert (dirty_developer_root / dirty_path).read_bytes() == dirty_marker
