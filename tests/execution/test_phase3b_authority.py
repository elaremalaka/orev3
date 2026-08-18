from __future__ import annotations

import inspect
import json
import ast
import copy
from pathlib import Path

import pytest

from orev3.execution.canonical import domain_identity, parse_json, validate_json_schema_instance
from orev3.execution.evidence_preparation import EVIDENCE_POLICY_DOMAIN, EVIDENCE_PREPARATION_DOMAIN, PHASE3B_REMAINING_PREDICATES, EvidencePreparationDisposition, aggregate_evidence, load_evidence_policy, require_phase3b_governance_closure
from orev3.execution.readiness_record import PHASE3B_SCHEMA_POLICY
from orev3.execution.readiness_record import SourceScopeDeclarationV1
from orev3.execution.runtime import PHASE3B_CONTROLLER, SAFE_PHASE3B_WORKERS
from orev3.execution.runtime import _enforce_temporary_disk_limit


def test_schema_policy_is_exactly_twenty() -> None:
    assert len(PHASE3B_SCHEMA_POLICY) == 20
    assert set(PHASE3B_SCHEMA_POLICY) >= {"evidence-preparation-policy", "readiness-test-evidence", "immutable-input-snapshot", "dataset-validation-evidence", "outcome-blind-projection-evidence", "replay-evidence", "population-accounting-evidence", "profile-conformance-evidence", "artifact-declaration-evidence", "evidence-preparation"}
    schema = parse_json(Path("src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json").read_bytes())
    policy = load_evidence_policy(Path("config/research/readiness/evidence-preparation-policy-v1.json").read_bytes(), schema=schema)
    assert policy["limits"]["max_file_bytes"] == 67_108_864


def test_aggregate_is_deterministic_and_not_readiness_identity() -> None:
    h = "1" * 64
    worker_ids = [f"{value:064x}" for value in range(1, 5)]
    component_ids = [f"{value:064x}" for value in range(10, 17)]
    first = aggregate_evidence(source_commit="a" * 40, runtime_contract_identity=h, dependency_environment_identity=h, adapter_identity=h, readiness_test_identity=h, input_snapshot_identities=[h], dataset_identities=[h], projection_identities=[h], replay_identity=h, population_identity=h, profile_identity=h, artifact_identity=h, capability_policy_identity=h, worker_evidence_identities=worker_ids, semantic_component_identities=component_ids)
    second = aggregate_evidence(source_commit="a" * 40, runtime_contract_identity=h, dependency_environment_identity=h, adapter_identity=h, readiness_test_identity=h, input_snapshot_identities=[h], dataset_identities=[h], projection_identities=[h], replay_identity=h, population_identity=h, profile_identity=h, artifact_identity=h, capability_policy_identity=h, worker_evidence_identities=worker_ids, semantic_component_identities=component_ids)
    assert first.aggregate_material == second.aggregate_material
    assert "readiness_identity" not in first.aggregate_material
    assert "outcome" not in json.dumps(first.aggregate_material)
    schema = parse_json(Path("src/orev3/execution/schemas/v1/evidence-preparation.schema.json").read_bytes())
    validate_json_schema_instance(first.aggregate_material, schema, schema_registry={})
    changed_components = list(component_ids); changed_components[-1] = "f" * 64
    changed = aggregate_evidence(source_commit="a" * 40, runtime_contract_identity=h, dependency_environment_identity=h, adapter_identity=h, readiness_test_identity=h, input_snapshot_identities=[h], dataset_identities=[h], projection_identities=[h], replay_identity=h, population_identity=h, profile_identity=h, artifact_identity=h, capability_policy_identity=h, worker_evidence_identities=worker_ids, semantic_component_identities=changed_components)
    assert changed.aggregate_material["evidence_preparation_identity"] != first.aggregate_material["evidence_preparation_identity"]


def test_phase3b_has_fixed_workers_and_no_execution_authority() -> None:
    assert SAFE_PHASE3B_WORKERS == {"input_projection_worker.py", "readiness_test_worker.py", "replay_preparation_worker.py"}
    assert PHASE3B_CONTROLLER == "evidence_preparation_worker.py"
    assert "READINESS_VALIDATED" not in EvidencePreparationDisposition.__members__
    assert "EXECUTION_READY" not in EvidencePreparationDisposition.__members__
    assert {"readiness_identity", "seal_commit_R", "attempt_allocation_and_control_storage"}.issubset(PHASE3B_REMAINING_PREDICATES)
    import orev3.execution.evidence_preparation as module
    source = inspect.getsource(module)
    for forbidden in ("allocate_attempt", "open_outcome", "execute_experiment", "write_readiness_record"):
        assert forbidden not in source
    production = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/orev3/execution").glob("*.py"))
    # Two occurrences declare the enum member/name; the third is the sole mint.
    assert production.count("EVIDENCE_PREPARATION_VALIDATED") == 3
    assert source.count("EvidencePreparationDisposition.EVIDENCE_PREPARATION_VALIDATED") == 1


def test_detached_controller_has_no_scientific_semantic_import_or_nested_sandbox_path() -> None:
    controller = Path("src/orev3/execution/evidence_preparation_worker.py").read_text(encoding="utf-8")
    tree = ast.parse(controller)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "orev3.execution.projection" not in imported
    assert "orev3.execution.replay_preparation" not in imported
    for forbidden in ("sandbox-exec", "rank", "evaluate", "authorize_outcome", "execute_experiment"):
        assert forbidden not in controller
    for worker in SAFE_PHASE3B_WORKERS:
        worker_source = Path("src/orev3/execution", worker).read_text(encoding="utf-8")
        assert "sandbox-exec" not in worker_source
        assert "run_phase3b_worker" not in worker_source


@pytest.mark.parametrize(
    "mutation",
    (
        lambda policy: policy["worker_profiles"][0].__setitem__("module", "src/orev3/execution/readiness_test_worker.py"),
        lambda policy: policy["worker_profiles"][0].__setitem__("network_policy", "permitted"),
        lambda policy: policy["worker_profiles"].pop(),
        lambda policy: policy.__setitem__("profile_renderer_identity", "0" * 64),
        lambda policy: policy["worker_profiles"][0].__setitem__("sandbox_template_identity", "0" * 64),
    ),
)
def test_capability_policy_drift_fails_closed(mutation: object) -> None:
    schema = parse_json(Path("src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json").read_bytes())
    policy = parse_json(Path("config/research/readiness/evidence-preparation-policy-v1.json").read_bytes())
    mutation(policy)
    material = copy.deepcopy(policy)
    material.pop("policy_identity", None)
    policy["policy_identity"] = domain_identity(EVIDENCE_POLICY_DOMAIN, material)
    with pytest.raises(Exception):
        load_evidence_policy(json.dumps(policy, separators=(",", ":"), sort_keys=True).encode() + b"\n", schema=schema)


def test_phase3b_governance_cannot_omit_policy_or_tests() -> None:
    tree = SourceScopeDeclarationV1("src/orev3/execution", "control_plane", "top_level", "a" * 40, "040000")
    schemas = SourceScopeDeclarationV1("src/orev3/execution/schemas/v1", "readiness_schema", "top_level", "b" * 40, "040000")
    policy = SourceScopeDeclarationV1("config/research/readiness/evidence-preparation-policy-v1.json", "configuration", "top_level", "c" * 40, "100644")
    tests = SourceScopeDeclarationV1("tests/execution", "readiness_tests", "top_level", "d" * 40, "040000")
    require_phase3b_governance_closure((tree, schemas, policy, tests), mandatory_test_paths=["tests/execution"], adapter_test_paths=[])
    import pytest
    with pytest.raises(Exception, match="governed-scope closure"):
        require_phase3b_governance_closure((tree, schemas, tests), mandatory_test_paths=["tests/execution"], adapter_test_paths=[])


def test_temporary_disk_policy_is_enforced_during_worker_polling(tmp_path: Path) -> None:
    root = tmp_path / "worker"; root.mkdir(); (root / "large").write_bytes(b"x" * 1025)
    with pytest.raises(Exception, match="RESOURCE_LIMIT_EXCEEDED"):
        _enforce_temporary_disk_limit((root,), 1024)


def test_expected_validation_failures_are_sanitized(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import orev3.execution.evidence_preparation as module
    monkeypatch.setattr(module, "load_repository_authority", lambda path: object())
    monkeypatch.setattr(module, "_collect_evidence_preparation_evidence", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("OUTCOME-SENTINEL")))
    from orev3.execution.git_state import GitRepository
    result = module.validate_evidence_preparation(GitRepository(Path.cwd()), "synthetic", operational_input_locators={})
    assert result.disposition.value == "EVIDENCE_PREPARATION_REJECTED"
    assert result.diagnostics == ("EVIDENCE_PREPARATION_INTERNAL_REJECTED",)
    assert "OUTCOME-SENTINEL" not in repr(result)
