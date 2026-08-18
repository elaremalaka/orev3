from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from orev3.execution.evidence_preparation import reconstruct_projection_twice, reconstruct_replay_twice
from orev3.execution.canonical import parse_canonical_bytes
from orev3.execution.runtime import MACOS_SANDBOX_EXEC, render_phase3b_sandbox_profile, run_phase3b_worker, sanitized_worker_environment
from orev3.execution.test_policy import run_readiness_tests
from orev3.execution.test_policy import READINESS_TEST_COLLECTION_DOMAIN
from orev3.execution.canonical import canonical_bytes, domain_identity


def _schemas(source: Path) -> tuple[Path, Path]:
    projection_properties = {"candidates": {"items": {"type": "integer"}, "minItems": 1, "type": "array", "uniqueItems": True}, "eligible": {"type": "boolean"}, "exclusion_reason": {"enum": ["missing_observation", "not_applicable"], "type": "string"}, "observation_index": {"minimum": 0, "type": "integer"}, "source_unit_key": {"pattern": "^[a-z0-9-]+$", "type": "string"}}
    projection = {"additionalProperties": False, "properties": projection_properties, "required": sorted(projection_properties), "type": "object"}
    raw_properties = {**projection_properties, "outcome": {"type": "string"}}
    raw = {"additionalProperties": False, "properties": raw_properties, "required": sorted(raw_properties), "type": "object"}
    raw_path = source / "raw-schema.json"; raw_path.write_bytes(canonical_bytes(raw))
    projection_path = source / "projection-schema.json"; projection_path.write_bytes(canonical_bytes(projection))
    return raw_path, projection_path


def _synthetic_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree("src", root / "src")
    (root / "tests").mkdir()
    subprocess.run(("git", "init", "-q", str(root)), check=True)
    subprocess.run(("git", "-C", str(root), "config", "user.email", "test@example.invalid"), check=True)
    subprocess.run(("git", "-C", str(root), "config", "user.name", "Test"), check=True)
    return root


def _commit(source: Path) -> str:
    subprocess.run(("git", "-C", str(source), "add", "."), check=True)
    subprocess.run(("git", "-C", str(source), "commit", "-qm", "fixture"), check=True)
    return subprocess.run(("git", "-C", str(source), "rev-parse", "HEAD"), check=True, stdout=subprocess.PIPE, text=True).stdout.strip()


def _policy() -> dict[str, object]:
    return parse_canonical_bytes(Path("config/research/readiness/evidence-preparation-policy-v1.json").read_bytes())


def _worker_args(source: Path, source_commit: str) -> dict[str, object]:
    return {
        "dependency_root": _dependencies(),
        "runtime_contract_identity": "1" * 64,
        "dependency_environment_identity": "2" * 64,
        "capability_policy": _policy(),
    }


def _dependencies() -> Path:
    return Path(pytest.__file__).resolve().parent.parent


def test_readiness_worker_has_real_network_denial_and_no_ambient_plugins(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_network.py").write_text(
        "import errno, socket\n"
        "def test_denied():\n"
        "    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):\n"
        "        try:\n"
        "            candidate = socket.socket(socket.AF_INET, kind)\n"
        "            candidate.connect(('127.0.0.1', 9))\n"
        "        except PermissionError as exc:\n"
        "            assert exc.errno == errno.EPERM\n"
        "        else:\n"
        "            raise AssertionError('network was not structurally denied')\n",
        encoding="utf-8",
    )
    source_commit = _commit(source)
    result = run_phase3b_worker(source, source_commit, "READINESS_TEST", "readiness_test_worker.py", {"command": "run_exact", "selectors": ["tests/test_network.py"]}, timeout_seconds=30, **_worker_args(source, source_commit)).result
    assert result["exit_code"] == 0
    assert result["results"] == [{"node_id": "tests/test_network.py::test_denied", "status": "passed"}]


def test_projection_worker_is_deterministic_and_replay_worker_cannot_read_raw_store(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    raw_store = tmp_path / "raw"; raw_store.mkdir()
    raw = raw_store / "input"; raw.write_text('{"candidates":[1,2],"eligible":true,"exclusion_reason":"not_applicable","observation_index":0,"outcome":"secret","source_unit_key":"unit-a"}\n', encoding="utf-8")
    raw_schema, projection_schema = _schemas(source)
    source_commit = _commit(source)
    projection, projector_ids, _ = reconstruct_projection_twice(source_root=source, dependency_root=_dependencies(), raw_snapshot=raw, raw_schema_path=raw_schema, projection_schema_path=projection_schema, expected_raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), expected_raw_size=raw.stat().st_size, max_raw_bytes=10000, max_projection_bytes=10000, max_records=10, source_commit=source_commit, runtime_contract_identity="1" * 64, dependency_environment_identity="2" * 64, capability_policy=_policy(), raw_snapshot_identity="3" * 64)
    assert b"secret" not in projection
    assert len(projector_ids) == 2
    projection_path = tmp_path / "projection"; projection_path.write_bytes(projection)
    replay, replay_ids = reconstruct_replay_twice(source_root=source, dependency_root=_dependencies(), projection_path=projection_path, projection_schema_path=projection_schema, raw_store_root=raw_store, request_material={"allowed_exclusion_reasons": [], "candidate_order": [1, 2], "configuration_identity": "1" * 64, "dataset_identity": "2" * 64, "expected_projection_sha256": hashlib.sha256(projection).hexdigest(), "expected_projection_size": len(projection), "max_projection_bytes": 10000, "max_units": 10, "projection_identity": "3" * 64, "projection_schema_path": str(projection_schema), "selector_identifier": "latest-eligible-observation-selector-v1", "selector_component_identity": "4" * 64, "replay_preparer_component_identity": "5" * 64}, source_commit=source_commit, runtime_contract_identity="1" * 64, dependency_environment_identity="2" * 64, capability_policy=_policy(), projection_identity="3" * 64)
    assert b"replay_evidence_identity" in replay
    assert len(replay_ids) == 2


def test_projector_rejection_does_not_propagate_outcome_sentinel(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    raw_schema, projection_schema = _schemas(source)
    raw = tmp_path / "malformed-raw"
    raw.write_text(
        '{"candidates":[1,2],"eligible":true,"exclusion_reason":"not_applicable",'
        '"observation_index":0,"outcome":"OUTCOME-LEAK-SENTINEL",'
        '"source_unit_key":"unit-a","unexpected":"OUTCOME-LEAK-SENTINEL"}\n',
        encoding="utf-8",
    )
    source_commit = _commit(source)
    output = tmp_path / "projection-output"
    request = {
        "command": "project_canonical_jsonl",
        "expected_raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "expected_raw_size": raw.stat().st_size,
        "max_projection_bytes": 10_000,
        "max_raw_bytes": 10_000,
        "max_records": 10,
        "private_output": str(output),
        "projection_schema_path": str(projection_schema),
        "raw_schema_path": str(raw_schema),
        "raw_snapshot": str(raw),
    }
    with pytest.raises(Exception, match="PROJECTION_INVALID") as failure:
        run_phase3b_worker(
            source,
            source_commit,
            "INPUT_PROJECTOR",
            "input_projection_worker.py",
            request,
            read_files=(raw, raw_schema, projection_schema),
            write_roots=(tmp_path,),
            **_worker_args(source, source_commit),
        )
    assert "OUTCOME-LEAK-SENTINEL" not in str(failure.value)
    assert not output.exists()


def test_worker_names_and_pytest_arguments_are_not_caller_extensible(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    source_commit = _commit(source)
    with pytest.raises(Exception, match="not permitted"):
        run_phase3b_worker(source, source_commit, "ARBITRARY", "arbitrary.py", {}, **_worker_args(source, source_commit))
    with pytest.raises(Exception, match="requires exact readiness-test files"):
        run_phase3b_worker(source, source_commit, "READINESS_TEST", "readiness_test_worker.py", {"command": "run_exact", "selectors": ["--pyargs"]}, **_worker_args(source, source_commit))


@pytest.mark.parametrize(
    ("worker_kind", "worker_name", "forbidden_module", "request_material"),
    (
        ("READINESS_TEST", "readiness_test_worker.py", "orev3.execution.projection", {"command": "collect", "selectors": ["tests/test_dummy.py"]}),
        ("INPUT_PROJECTOR", "input_projection_worker.py", "orev3.execution.replay_preparation", {"command": "project_canonical_jsonl"}),
        ("REPLAY_PREPARATION", "replay_preparation_worker.py", "orev3.execution.projection", {"command": "reconstruct_replay"}),
    ),
)
def test_semantic_worker_code_projection_denies_cross_capability_import(
    tmp_path: Path, worker_kind: str, worker_name: str, forbidden_module: str, request_material: dict[str, str]
) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_dummy.py").write_text("def test_dummy(): assert True\n", encoding="utf-8")
    path = source / "src/orev3/execution" / worker_name
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("COMMANDS =", f"import {forbidden_module}\nCOMMANDS =", 1), encoding="utf-8")
    source_commit = _commit(source)
    with pytest.raises(Exception, match="READINESS_TEST_FAILED|PROJECTION_INVALID|REPLAY_IDENTITY_MISMATCH"):
        run_phase3b_worker(source, source_commit, worker_kind, worker_name, request_material, **_worker_args(source, source_commit))


def test_exact_readiness_test_policy_passes_only_all_passed_nodes(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_ready.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    source_commit = _commit(source)
    nodes = ["tests/test_ready.py::test_ok"]
    collection_identity = domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": nodes})
    evidence, worker_ids = run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_ready.py"], additional_selectors=[], expected_mandatory_collection_identity=collection_identity, expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(), timeout_seconds=30, max_output_bytes=65536)
    assert evidence["results"] == [{"node_id": "tests/test_ready.py::test_ok", "status": "passed"}]
    assert len(worker_ids) == 3
    (source / "tests/test_ready.py").write_text("import pytest\n@pytest.mark.skip(reason='no')\ndef test_skip(): pass\n", encoding="utf-8")
    source_commit = _commit(source)
    with pytest.raises(Exception, match="TEST_COLLECTION_MISMATCH"):
        run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_ready.py"], additional_selectors=[], expected_mandatory_collection_identity=collection_identity, expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(), timeout_seconds=30, max_output_bytes=65536)


def test_malicious_conftest_cannot_consistently_hide_mandatory_test(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_mandatory.py").write_text("def test_mandatory_failure(): assert False\n", encoding="utf-8")
    (source / "tests/conftest.py").write_text("def pytest_collection_modifyitems(items): items[:] = []\n", encoding="utf-8")
    source_commit = _commit(source)
    expected = ["tests/test_mandatory.py::test_mandatory_failure"]
    with pytest.raises(Exception, match="TEST_COLLECTION_MISMATCH"):
        run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_mandatory.py"], additional_selectors=[], expected_mandatory_collection_identity=domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": expected}), expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(), timeout_seconds=30, max_output_bytes=65536)


def test_readiness_worker_cannot_open_known_scientific_locator(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    secret = tmp_path / "scientific-input"; secret.write_text("outcome", encoding="utf-8")
    (source / "tests/test_capability.py").write_text(
        "import errno\nfrom pathlib import Path\n"
        f"def test_denied():\n    try: Path({str(secret)!r}).read_bytes()\n    except PermissionError as exc: assert exc.errno == errno.EPERM\n    else: raise AssertionError('scientific locator was readable')\n",
        encoding="utf-8",
    )
    source_commit = _commit(source)
    expected = ["tests/test_capability.py::test_denied"]
    evidence, _ = run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_capability.py"], additional_selectors=[], expected_mandatory_collection_identity=domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": expected}), expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(secret,), timeout_seconds=30, max_output_bytes=65536)
    assert evidence["results"][0]["status"] == "passed"


@pytest.mark.parametrize(
    ("worker_kind", "worker_name", "command"),
    (
        ("READINESS_TEST", "readiness_test_worker.py", "collect"),
        ("INPUT_PROJECTOR", "input_projection_worker.py", "project_canonical_jsonl"),
        ("REPLAY_PREPARATION", "replay_preparation_worker.py", "reconstruct_replay"),
    ),
)
def test_real_sibling_profiles_deny_network_and_cross_capability_reads(
    tmp_path: Path, worker_kind: str, worker_name: str, command: str
) -> None:
    source = _synthetic_source(tmp_path)
    dependency = _dependencies()
    capability = tmp_path / "allowed-object"
    capability.write_text("allowed", encoding="utf-8")
    denied = tmp_path / "other-capability"
    denied.write_text("denied", encoding="utf-8")
    private = tmp_path / "sandbox-private"
    (private / "home").mkdir(parents=True)
    (private / "tmp").mkdir()
    request = private / "request.json"
    request.write_text("{}", encoding="utf-8")
    profile, _ = render_phase3b_sandbox_profile(
        policy=_policy(),
        worker_kind=worker_kind,
        worker_name=worker_name,
        command=command,
        source_root=source,
        dependency_root=dependency,
        request_path=request,
        temporary_root=private,
        read_files=(capability,),
    )
    probe = (
        "import errno,socket;from pathlib import Path;"
        f"assert Path({str(capability)!r}).read_text()=='allowed';"
        "\ntry:\n Path(" + repr(str(source / "src/orev3/execution" / worker_name)) + ").write_text('changed');raise AssertionError('worker code writable')"
        "\nexcept PermissionError as exc:\n assert exc.errno==errno.EPERM"
        "\ntry:\n Path(" + repr(str(denied)) + ").read_bytes();raise AssertionError('cross capability readable')"
        "\nexcept PermissionError as exc:\n assert exc.errno==errno.EPERM"
        "\nfor kind in (socket.SOCK_STREAM,socket.SOCK_DGRAM):"
        "\n try:\n  s=socket.socket(socket.AF_INET,kind);s.connect(('127.0.0.1',9));raise AssertionError('network available')"
        "\n except PermissionError as exc:\n  assert exc.errno==errno.EPERM\n"
    )
    completed = subprocess.run(
        (str(MACOS_SANDBOX_EXEC), "-p", profile, str(Path(sys.executable).resolve()), "-I", "-S", "-c", probe),
        cwd=source,
        env=sanitized_worker_environment(private),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
