from __future__ import annotations

import copy
import hashlib
import importlib
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from orev3.execution.canonical import CanonicalControlError, canonical_bytes, parse_json
from orev3.execution.runtime import (
    ClosedDependencyRoot,
    MACOS_SANDBOX_EXEC,
    NETWORK_SANDBOX_PROFILE,
    RuntimeContractV1,
    construct_closed_dependency_root,
    load_offline_artifact_manifest_bytes,
    load_runtime_contract_bytes,
    reconstruct_host_system_material,
    validate_closed_dependency_imports,
    validate_dependency_lock,
    validate_host_runtime,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_STORE = ROOT / "data/research/readiness/wheels"
RUNTIME_SCHEMA = parse_json((ROOT / "src/orev3/execution/schemas/v1/runtime-contract.schema.json").read_bytes())
ARTIFACT_SCHEMA = parse_json((ROOT / "src/orev3/execution/schemas/v1/offline-artifact-manifest.schema.json").read_bytes())


def contract() -> RuntimeContractV1:
    return load_runtime_contract_bytes((ROOT / "config/research/readiness/runtime-contract-v1.json").read_bytes(), schema=RUNTIME_SCHEMA)


def lock_and_manifest():
    runtime = contract()
    lock_raw = (ROOT / runtime.dependency_lock_path).read_bytes()
    lock = validate_dependency_lock(lock_raw, expected_sha256=runtime.dependency_lock_sha256)
    manifest_raw = (ROOT / runtime.artifact_manifest_path).read_bytes()
    manifest = load_offline_artifact_manifest_bytes(
        manifest_raw,
        schema=ARTIFACT_SCHEMA,
        expected_sha256=runtime.artifact_manifest_sha256,
        dependency_lock_sha256=runtime.dependency_lock_sha256,
        dependency_lock=lock,
    )
    return lock, manifest


@pytest.fixture(scope="session")
def closed_dependency_root(tmp_path_factory: pytest.TempPathFactory) -> ClosedDependencyRoot:
    lock, manifest = lock_and_manifest()
    return construct_closed_dependency_root(lock, manifest, ARTIFACT_STORE, tmp_path_factory.mktemp("closed-root") / "root")


def test_exact_runtime_lock_artifacts_and_closed_root_are_accepted(closed_dependency_root: ClosedDependencyRoot) -> None:
    value = contract()
    validate_host_runtime(value, closed_dependency_root)
    assert closed_dependency_root.identity == value.material["dependency_lock"]["closed_environment_identity"]
    assert len(closed_dependency_root.distributions) == 27
    assert closed_dependency_root.file_count > 1_000


def test_pep751_lock_filename_and_hex_hash_are_strict() -> None:
    value = contract()
    assert Path(value.dependency_lock_path).name == "pylock.readiness-v1.toml"
    raw = (ROOT / value.dependency_lock_path).read_bytes()
    bad = raw.replace(b"1f02e8b43a8fbbc3f3e0d4f0f4bfc8131bcb4eebe8849b8e5c773f3a1c582a53", b"z" * 64, 1)
    with pytest.raises(CanonicalControlError, match="normalized SHA-256"):
        validate_dependency_lock(bad, expected_sha256=hashlib.sha256(bad).hexdigest())


def test_missing_or_changed_offline_artifact_fails_closed(tmp_path: Path) -> None:
    lock, manifest = lock_and_manifest()
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(CanonicalControlError, match="unavailable"):
        construct_closed_dependency_root(lock, manifest, empty, tmp_path / "root-a")
    store = tmp_path / "store"
    (store / "sha256").mkdir(parents=True)
    first = lock.wheels[0]
    (store / f"sha256/{first.sha256}.whl").write_bytes(b"wrong")
    with pytest.raises(CanonicalControlError, match="digest differs"):
        construct_closed_dependency_root(lock, manifest, store, tmp_path / "root-b")


def test_closed_root_excludes_ambient_editable_project_and_pip(closed_dependency_root: ClosedDependencyRoot) -> None:
    script = "import importlib.util,sys; sys.path.append(sys.argv[1]); assert importlib.util.find_spec('pip') is None; assert importlib.util.find_spec('orev3') is None"
    completed = subprocess.run((sys.executable, "-I", "-S", "-c", script, str(closed_dependency_root.path)), check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_dependency_imports_resolve_only_from_closed_root(closed_dependency_root: ClosedDependencyRoot) -> None:
    script = (
        "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
        "from orev3.execution.canonical import parse_json; "
        "from orev3.execution.runtime import ClosedDependencyRoot,load_runtime_contract_bytes,validate_closed_dependency_imports; "
        "root=Path(sys.argv[2]); source=Path(sys.argv[3]); "
        "contract=load_runtime_contract_bytes((source/'config/research/readiness/runtime-contract-v1.json').read_bytes(),schema=parse_json((source/'src/orev3/execution/schemas/v1/runtime-contract.schema.json').read_bytes())); "
        "closed=ClosedDependencyRoot(root,contract.material['dependency_lock']['closed_environment_identity'],(),0); "
        "print(len(validate_closed_dependency_imports(contract,closed,source)))"
    )
    completed = subprocess.run((sys.executable, "-I", "-S", "-c", script, str(ROOT / "src"), str(closed_dependency_root.path), str(ROOT)), check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "6"


@pytest.mark.parametrize(
    ("section", "field", "value"),
    (
        ("python", "version", "3.14.4"),
        ("python", "implementation", "OtherPython"),
        ("python", "platform_tag", "linux-x86_64"),
        ("host_system", "macos_build", "DIFFERENT"),
        ("host_system", "darwin_release", "0.0.0"),
    ),
)
def test_runtime_and_system_drift_are_rejected(closed_dependency_root: ClosedDependencyRoot, section: str, field: str, value: str) -> None:
    original = contract()
    material = copy.deepcopy(original.material)
    material[section][field] = value
    drifted = RuntimeContractV1(material, original.runtime_contract_identity, original.dependency_lock_path, original.dependency_lock_sha256, original.artifact_manifest_path, original.artifact_manifest_sha256)
    with pytest.raises(CanonicalControlError):
        validate_host_runtime(drifted, closed_dependency_root)


def test_dynamic_system_binding_reconstructs(closed_dependency_root: ClosedDependencyRoot) -> None:
    actual = reconstruct_host_system_material(closed_dependency_root.path)
    assert actual == contract().material["host_system"]
    assert any(item["consumer"] == "python" for item in actual["dynamic_links"])
    assert any(item["consumer"].startswith("dependency/") for item in actual["dynamic_links"])


def test_network_sandbox_denies_real_tcp_connection() -> None:
    script = "import socket; socket.create_connection(('127.0.0.1',9),.2)"
    completed = subprocess.run((str(MACOS_SANDBOX_EXEC), "-p", NETWORK_SANDBOX_PROFILE, sys.executable, "-I", "-S", "-c", script), check=False, capture_output=True, text=True)
    assert completed.returncode != 0
    assert "Operation not permitted" in completed.stderr


def test_runtime_contract_schema_and_identity_reject_mutation() -> None:
    material = copy.deepcopy(contract().material)
    material["network_isolation"]["profile_identity"] = "0" * 64
    material["runtime_contract_identity"] = "0" * 64
    with pytest.raises(CanonicalControlError):
        load_runtime_contract_bytes(canonical_bytes(material), schema=RUNTIME_SCHEMA)
