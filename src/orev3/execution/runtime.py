"""Detached, sanitized, non-scientific preparation runtime foundation."""

from __future__ import annotations

import csv
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import platform
import re
import shutil
import stat
import sys
import sysconfig
import tempfile
import tomllib
import zipfile
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import urlsplit

from orev3.execution.canonical import (
    CanonicalControlError,
    domain_identity,
    parse_canonical_bytes,
    require_sha256,
    validate_json_schema_instance,
    validate_repository_path,
)
from orev3.execution.git_state import GitAuthorityError, GitDiagnosticCode, GitRepository, _run_bounded_process

RUNTIME_CONTRACT_DOMAIN = "orev3:readiness-runtime-contract:v1\n"
RUNTIME_BUNDLE_DOMAIN = "orev3:readiness-python-runtime-bundle:v1\n"
DEPENDENCY_ENVIRONMENT_DOMAIN = "orev3:readiness-closed-dependency-root:v1\n"
DEPENDENCY_LOCK_DOMAIN = "orev3:readiness-dependency-lock:v1\n"
OFFLINE_ARTIFACT_MANIFEST_DOMAIN = "orev3:readiness-offline-artifact-manifest:v1\n"
HOST_SYSTEM_DOMAIN = "orev3:readiness-host-system:v1\n"
NETWORK_SANDBOX_DOMAIN = "orev3:readiness-network-sandbox:v1\n"
PHASE3B_PROFILE_RENDERER_DOMAIN = "orev3:phase3b-seatbelt-profile-renderer:v1\n"
PHASE3B_WORKER_EVIDENCE_DOMAIN = "orev3:phase3b-worker-evidence:v1\n"
MAX_RUNTIME_CONTRACT_BYTES = 262_144
MAX_ARTIFACT_MANIFEST_BYTES = 1_048_576
MAX_DEPENDENCY_LOCK_BYTES = 8 * 1024 * 1024
MAX_WORKER_OUTPUT_BYTES = 1_048_576
WORKER_TIMEOUT_SECONDS = 180
SAFE_WORKER_COMMANDS = frozenset({"validate_imports", "validate_runtime"})
SAFE_PHASE3B_WORKERS = frozenset({
    "input_projection_worker.py",
    "readiness_test_worker.py",
    "replay_preparation_worker.py",
})
PHASE3B_CONTROLLER = "evidence_preparation_worker.py"
MACOS_SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")
OTOOL = Path("/usr/bin/otool")
SW_VERS = Path("/usr/bin/sw_vers")
NETWORK_SANDBOX_PROFILE = "(version 1)\n(allow default)\n(deny network*)\n"
PHASE3B_PROFILE_RENDERER_IDENTITY = domain_identity(
    PHASE3B_PROFILE_RENDERER_DOMAIN,
    {
        "filesystem_policy": "default_deny_named_capability_roots",
        "network_policy": "deny_network_star",
        "renderer_revision": "macos-seatbelt-capability-renderer-v4",
        "python_framework_app_runtime": "allowed_if_present_beneath_bound_base_prefix",
        "system_base_profile": "system.sb",
    },
)
PHASE3A_SANDBOX_TEMPLATE_IDENTITY = "e55dba9a5ec1fb87d8237cd95c8a29dd49c0919fc7380c38678ee6669a3ed7bc"
_NORMALIZED_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LOCK_FILENAME = re.compile(r"^pylock(?:\.[a-z0-9][a-z0-9.-]*)?\.toml$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class LockedWheel:
    package_name: str
    version: str
    filename: str
    url: str
    sha256: str


@dataclass(frozen=True, slots=True)
class DependencyLockV1:
    wheels: tuple[LockedWheel, ...]

    @property
    def packages(self) -> tuple[tuple[str, str], ...]:
        return tuple((item.package_name, item.version) for item in self.wheels)


@dataclass(frozen=True, slots=True)
class OfflineArtifactManifestV1:
    material: Mapping[str, Any]
    manifest_identity: str
    artifacts_by_digest: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ClosedDependencyRoot:
    path: Path
    identity: str
    distributions: tuple[tuple[str, str], ...]
    file_count: int


@dataclass(frozen=True, slots=True)
class RuntimeContractV1:
    material: Mapping[str, Any]
    runtime_contract_identity: str
    dependency_lock_path: str
    dependency_lock_sha256: str
    artifact_manifest_path: str
    artifact_manifest_sha256: str


@dataclass(frozen=True, slots=True)
class PreparationWorkerEvidence:
    command: str
    material: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Phase3BWorkerEvidence:
    worker_kind: str
    evidence_identity: str
    material: Mapping[str, Any]
    result: Mapping[str, Any]


def _normalized_distribution_name(value: str) -> str:
    normalized = re.sub(r"[-_.]+", "-", value).lower()
    if not _NORMALIZED_NAME.fullmatch(normalized):
        raise CanonicalControlError("dependency distribution name is invalid")
    return normalized


def reconstruct_runtime_contract_identity(material: Mapping[str, Any]) -> str:
    require_sha256("runtime_contract_identity", material.get("runtime_contract_identity"))
    identity_material = dict(material)
    del identity_material["runtime_contract_identity"]
    return domain_identity(RUNTIME_CONTRACT_DOMAIN, identity_material)


def reconstruct_offline_artifact_manifest_identity(material: Mapping[str, Any]) -> str:
    require_sha256("artifact_manifest_identity", material.get("artifact_manifest_identity"))
    identity_material = dict(material)
    del identity_material["artifact_manifest_identity"]
    return domain_identity(OFFLINE_ARTIFACT_MANIFEST_DOMAIN, identity_material)


def load_runtime_contract_bytes(raw: bytes, *, schema: Mapping[str, Any]) -> RuntimeContractV1:
    material = parse_canonical_bytes(raw, max_bytes=MAX_RUNTIME_CONTRACT_BYTES)
    validate_json_schema_instance(material, schema, schema_registry={})
    if reconstruct_runtime_contract_identity(material) != material["runtime_contract_identity"]:
        raise CanonicalControlError("runtime contract identity does not reconstruct")
    lock = material["dependency_lock"]
    validate_repository_path(lock["path"])
    if not _LOCK_FILENAME.fullmatch(PurePosixPath(lock["path"]).name):
        raise CanonicalControlError("dependency lock filename is not PEP 751 conformant")
    lock_identity_material = {
        "format": lock["format"],
        "git_blob_binding": lock["git_blob_binding"],
        "path": lock["path"],
        "sha256": lock["sha256"],
    }
    if domain_identity(DEPENDENCY_LOCK_DOMAIN, lock_identity_material) != lock["lock_identity"]:
        raise CanonicalControlError("dependency lock identity does not reconstruct")
    artifact_manifest = lock["offline_artifact_manifest"]
    validate_repository_path(artifact_manifest["path"])
    profile = material["network_isolation"]
    if domain_identity(
        NETWORK_SANDBOX_DOMAIN,
        {"mechanism": profile["mechanism"], "profile": NETWORK_SANDBOX_PROFILE},
    ) != profile["profile_identity"]:
        raise CanonicalControlError("network-isolation profile identity differs")
    return RuntimeContractV1(
        material,
        material["runtime_contract_identity"],
        lock["path"],
        lock["sha256"],
        artifact_manifest["path"],
        artifact_manifest["sha256"],
    )


def validate_dependency_lock(raw: bytes, *, expected_sha256: str) -> DependencyLockV1:
    if len(raw) > MAX_DEPENDENCY_LOCK_BYTES:
        raise CanonicalControlError("dependency lock exceeds the byte limit")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CanonicalControlError("dependency lock digest differs from runtime contract")
    try:
        material = tomllib.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CanonicalControlError("dependency lock is not strict UTF-8 PEP 751 TOML") from exc
    if set(material) != {"lock-version", "created-by", "packages"}:
        raise CanonicalControlError("dependency lock contains unsupported top-level fields")
    if material["lock-version"] != "1.0" or not isinstance(material["created-by"], str):
        raise CanonicalControlError("dependency lock is not the supported PEP 751 form")
    packages = material["packages"]
    if not isinstance(packages, list) or not packages:
        raise CanonicalControlError("dependency lock package set is empty")
    wheels: list[LockedWheel] = []
    names: list[str] = []
    for package in packages:
        if not isinstance(package, dict) or set(package) != {"name", "version", "wheels"}:
            raise CanonicalControlError("dependency lock package is malformed")
        name = _normalized_distribution_name(package["name"])
        version = package["version"]
        package_wheels = package["wheels"]
        if not isinstance(version, str) or not version or not isinstance(package_wheels, list):
            raise CanonicalControlError("dependency lock package is incomplete")
        if name in names:
            raise CanonicalControlError("dependency lock package is duplicated")
        names.append(name)
        if len(package_wheels) != 1:
            raise CanonicalControlError("v1 requires exactly one selected wheel per package")
        wheel = package_wheels[0]
        if not isinstance(wheel, dict) or set(wheel) != {"name", "url", "hashes"}:
            raise CanonicalControlError("dependency wheel declaration is malformed")
        hashes = wheel["hashes"]
        if not isinstance(hashes, dict) or set(hashes) != {"sha256"}:
            raise CanonicalControlError("dependency wheel hashes are malformed")
        digest = hashes["sha256"]
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise CanonicalControlError("dependency wheel lacks a normalized SHA-256")
        filename, url = wheel["name"], wheel["url"]
        if not isinstance(filename, str) or not filename.endswith(".whl"):
            raise CanonicalControlError("dependency artifact is not a wheel")
        if not isinstance(url, str):
            raise CanonicalControlError("dependency wheel URL is invalid")
        split = urlsplit(url)
        if split.scheme != "https" or not split.hostname or split.username or split.password or split.query or split.fragment:
            raise CanonicalControlError("dependency wheel URL is not credential-free HTTPS")
        if PurePosixPath(split.path).name != filename:
            raise CanonicalControlError("dependency wheel filename and URL disagree")
        wheels.append(LockedWheel(name, version, filename, url, digest))
    if names != sorted(names):
        raise CanonicalControlError("dependency lock packages are not canonically ordered")
    return DependencyLockV1(tuple(wheels))


def load_offline_artifact_manifest_bytes(
    raw: bytes,
    *,
    schema: Mapping[str, Any],
    expected_sha256: str,
    dependency_lock_sha256: str,
    dependency_lock: DependencyLockV1,
) -> OfflineArtifactManifestV1:
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CanonicalControlError("offline artifact manifest digest differs")
    material = parse_canonical_bytes(raw, max_bytes=MAX_ARTIFACT_MANIFEST_BYTES)
    validate_json_schema_instance(material, schema, schema_registry={})
    if reconstruct_offline_artifact_manifest_identity(material) != material["artifact_manifest_identity"]:
        raise CanonicalControlError("offline artifact manifest identity does not reconstruct")
    if material["dependency_lock_sha256"] != dependency_lock_sha256:
        raise CanonicalControlError("offline artifact manifest binds another lock")
    expected = [
        {
            "filename": item.filename,
            "package_name": item.package_name,
            "relative_store_path": f"sha256/{item.sha256}.whl",
            "sha256": item.sha256,
            "version": item.version,
        }
        for item in dependency_lock.wheels
    ]
    if material["artifacts"] != expected:
        raise CanonicalControlError("offline artifact manifest differs from the dependency lock")
    return OfflineArtifactManifestV1(
        material,
        material["artifact_manifest_identity"],
        {item["sha256"]: item for item in material["artifacts"]},
    )


def _safe_wheel_member_path(value: str) -> PurePosixPath:
    if not value or "\\" in value or "\x00" in value:
        raise CanonicalControlError("wheel member path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CanonicalControlError("wheel member path escapes the dependency root")
    return path


def _wheel_target_path(path: PurePosixPath) -> PurePosixPath | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if part.endswith(".data"):
            if index + 2 > len(parts):
                raise CanonicalControlError("wheel .data member is malformed")
            scheme = parts[index + 1]
            if scheme not in {"purelib", "platlib"}:
                raise CanonicalControlError("wheel contains a non-import dependency payload")
            remainder = parts[index + 2 :]
            return PurePosixPath(*remainder) if remainder else None
    return path


def _validate_wheel_record(archive: zipfile.ZipFile, names: set[str]) -> None:
    records = [name for name in names if name.endswith(".dist-info/RECORD")]
    if len(records) != 1:
        raise CanonicalControlError("wheel must contain exactly one RECORD")
    try:
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode("utf-8", errors="strict"))))
    except (UnicodeDecodeError, csv.Error, KeyError) as exc:
        raise CanonicalControlError("wheel RECORD is malformed") from exc
    declared: set[str] = set()
    for row in rows:
        if len(row) != 3 or not row[0]:
            raise CanonicalControlError("wheel RECORD row is malformed")
        member = _safe_wheel_member_path(row[0]).as_posix()
        if member in declared:
            raise CanonicalControlError("wheel RECORD path is duplicated")
        declared.add(member)
        if member == records[0]:
            if row[1] or row[2]:
                raise CanonicalControlError("wheel RECORD self-entry must be unhashed")
            continue
        if not row[1].startswith("sha256=") or not row[2].isdigit():
            raise CanonicalControlError("wheel RECORD entry lacks a deterministic identity")
        raw = archive.read(member)
        import base64

        encoded = row[1][7:]
        expected = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        if hashlib.sha256(raw).digest() != expected or len(raw) != int(row[2]):
            raise CanonicalControlError("wheel RECORD identity differs from member bytes")
    file_names = {name for name in names if not name.endswith("/")}
    if declared != file_names:
        raise CanonicalControlError("wheel contains an unrecorded file")


def construct_closed_dependency_root(
    dependency_lock: DependencyLockV1,
    manifest: OfflineArtifactManifestV1,
    artifact_store_root: Path,
    destination: Path,
) -> ClosedDependencyRoot:
    store = artifact_store_root.resolve()
    if artifact_store_root.is_symlink() or not store.is_dir():
        raise CanonicalControlError("offline artifact store is unavailable or is a symlink")
    if destination.exists() and any(destination.iterdir()):
        raise CanonicalControlError("closed dependency root is not empty")
    destination.mkdir(parents=True, exist_ok=True)
    owners: dict[str, str] = {}
    written: set[str] = set()
    artifact_material: list[dict[str, object]] = []
    for wheel in dependency_lock.wheels:
        declaration = manifest.artifacts_by_digest.get(wheel.sha256)
        if declaration is None:
            raise CanonicalControlError("required offline dependency artifact is undeclared")
        candidate = store / declaration["relative_store_path"]
        if candidate.is_symlink() or not candidate.is_file():
            raise CanonicalControlError(f"offline dependency artifact is unavailable: {wheel.package_name}")
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != wheel.sha256:
            raise CanonicalControlError(f"offline dependency artifact digest differs: {wheel.package_name}")
        top_levels: set[str] = set()
        try:
            with zipfile.ZipFile(candidate) as archive:
                infos = archive.infolist()
                names = {info.filename for info in infos}
                if len(names) != len(infos):
                    raise CanonicalControlError("wheel archive member path is duplicated")
                _validate_wheel_record(archive, names)
                for info in sorted(infos, key=lambda item: item.filename):
                    source_path = _safe_wheel_member_path(info.filename)
                    mode = (info.external_attr >> 16) & 0o170000
                    if mode not in {0, stat.S_IFREG, stat.S_IFDIR}:
                        raise CanonicalControlError("wheel contains a non-regular member")
                    target_path = _wheel_target_path(source_path)
                    if target_path is None or info.is_dir():
                        continue
                    normalized = target_path.as_posix()
                    if normalized in written:
                        raise CanonicalControlError("locked wheels contain a path collision")
                    written.add(normalized)
                    first = target_path.parts[0]
                    if not first.endswith((".dist-info", ".data")):
                        top_levels.add(first.removesuffix(".py"))
                    target = destination.joinpath(*target_path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(info.filename))
        except zipfile.BadZipFile as exc:
            raise CanonicalControlError("offline dependency artifact is not a valid wheel") from exc
        for top_level in sorted(top_levels):
            previous = owners.setdefault(top_level, wheel.package_name)
            if previous != wheel.package_name:
                raise CanonicalControlError("locked wheels contain a top-level package collision")
        artifact_material.append(
            {
                "filename": wheel.filename,
                "package_name": wheel.package_name,
                "sha256": wheel.sha256,
                "top_level_names": sorted(top_levels),
                "version": wheel.version,
            }
        )
    files: list[dict[str, object]] = []
    for path in sorted(destination.rglob("*")):
        if path.is_symlink():
            raise CanonicalControlError("closed dependency root contains a symlink")
        if path.is_file():
            relative = path.relative_to(destination).as_posix()
            raw = path.read_bytes()
            files.append({"byte_count": len(raw), "path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
    distributions: dict[str, str] = {}
    for distribution in importlib.metadata.distributions(path=[str(destination)]):
        name_value = distribution.metadata.get("Name")
        if not name_value:
            raise CanonicalControlError("closed dependency distribution lacks a name")
        name = _normalized_distribution_name(name_value)
        if name in distributions:
            raise CanonicalControlError("closed dependency distribution is duplicated")
        if distribution.read_text("direct_url.json") is not None:
            raise CanonicalControlError("direct/editable dependency installation is prohibited")
        distributions[name] = distribution.version
    if tuple(sorted(distributions.items())) != dependency_lock.packages:
        raise CanonicalControlError("closed dependency root distribution set differs from lock")
    material = {
        "artifacts": artifact_material,
        "distributions": [{"name": name, "version": version} for name, version in sorted(distributions.items())],
        "files": files,
        "root_format": "wheel-projection-v1",
    }
    return ClosedDependencyRoot(destination, domain_identity(DEPENDENCY_ENVIRONMENT_DOMAIN, material), tuple(sorted(distributions.items())), len(files))


def reconstruct_runtime_bundle_identity(*, interpreter: Path | None = None) -> str:
    executable = (interpreter or Path(sys.executable)).resolve()
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    files: list[dict[str, object]] = []
    for path in sorted(stdlib.rglob("*")):
        relative = path.relative_to(stdlib)
        if "site-packages" in relative.parts or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            resolved = path.resolve()
            if not resolved.is_file():
                raise CanonicalControlError("runtime bundle symlink target is unavailable")
            files.append({"byte_count": resolved.stat().st_size, "path": relative.as_posix(), "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(), "symlink_target": path.readlink().as_posix()})
        elif path.is_file():
            files.append({"byte_count": path.stat().st_size, "path": relative.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return domain_identity(
        RUNTIME_BUNDLE_DOMAIN,
        {
            "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "files": files,
            "python": {"abi_tag": sysconfig.get_config_var("SOABI"), "cache_tag": sys.implementation.cache_tag, "implementation": platform.python_implementation(), "platform_tag": sysconfig.get_platform(), "version": platform.python_version()},
        },
    )


def _bounded_tool(path: Path, *arguments: str) -> str:
    result = _run_bounded_process((str(path), *arguments), cwd=Path("/"), environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}, timeout_seconds=30, max_output_bytes=4 * 1024 * 1024)
    if result.returncode != 0:
        raise CanonicalControlError(f"runtime identity tool failed: {path.name}")
    return result.stdout.decode("utf-8", errors="strict")


def _normalize_install_name(value: str) -> tuple[str, str]:
    if "Python.framework/Versions/" in value and value.endswith("/Python"):
        resolved = Path(value)
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest() if resolved.is_file() else ""
        return "python-framework/Python", digest
    return value, ""


def reconstruct_host_system_material(dependency_root: Path, *, interpreter: Path | None = None) -> Mapping[str, Any]:
    executable = (interpreter or Path(sys.executable)).resolve()
    consumers: list[tuple[str, Path]] = [("python", executable)]
    for path in sorted(dependency_root.rglob("*")):
        if path.is_file() and path.suffix in {".so", ".dylib"}:
            consumers.append((f"dependency/{path.relative_to(dependency_root).as_posix()}", path))
    links: list[dict[str, str]] = []
    pattern = re.compile(r"^\s+(.+?) \(compatibility version ([^,]+), current version ([^)]+)\)$")
    for consumer, path in consumers:
        output = _bounded_tool(OTOOL, "-L", str(path))
        for line in output.splitlines()[1:]:
            match = pattern.match(line)
            if match:
                install_name, digest = _normalize_install_name(match.group(1))
                links.append({"compatibility_version": match.group(2), "consumer": consumer, "current_version": match.group(3), "install_name": install_name, "resolved_sha256": digest})
    unique_links = {
        (
            item["consumer"],
            item["install_name"],
            item["compatibility_version"],
            item["current_version"],
            item["resolved_sha256"],
        ): item
        for item in links
    }
    material: dict[str, Any] = {
        "architecture": platform.machine(),
        "darwin_release": platform.release(),
        "dynamic_links": sorted(unique_links.values(), key=lambda item: (item["consumer"], item["install_name"])),
        "macos_build": _bounded_tool(SW_VERS, "-buildVersion").strip(),
        "macos_version": platform.mac_ver()[0],
        "operating_system": "macOS",
    }
    material["host_system_identity"] = domain_identity(HOST_SYSTEM_DOMAIN, material)
    return material


def validate_host_runtime(contract: RuntimeContractV1, dependency_root: ClosedDependencyRoot, *, interpreter: Path | None = None) -> None:
    material = contract.material
    actual = {
        "abi_tag": sysconfig.get_config_var("SOABI"),
        "cache_tag": sys.implementation.cache_tag,
        "implementation": platform.python_implementation(),
        "platform_tag": sysconfig.get_platform(),
        "runtime_bundle_identity": reconstruct_runtime_bundle_identity(interpreter=interpreter),
        "version": platform.python_version(),
    }
    if actual != material["python"]:
        raise CanonicalControlError("host Python/runtime differs from runtime contract")
    executable_paths = {"otool": OTOOL, "python": (interpreter or Path(sys.executable)).resolve(), "sandbox-exec": MACOS_SANDBOX_EXEC, "sw-vers": SW_VERS}
    expected = {item["executable_identifier"]: item["sha256"] for item in material["allowed_executables"]}
    actual_executables = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in executable_paths.items() if path.is_file()}
    if actual_executables != expected:
        raise CanonicalControlError("allowed executable bytes differ from runtime contract")
    if dependency_root.identity != material["dependency_lock"]["closed_environment_identity"]:
        raise CanonicalControlError("closed dependency environment identity differs")
    if reconstruct_host_system_material(dependency_root.path, interpreter=interpreter) != material["host_system"]:
        raise CanonicalControlError("host/system runtime differs from runtime contract")


def validate_closed_dependency_imports(contract: RuntimeContractV1, dependency_root: ClosedDependencyRoot, source_root: Path) -> tuple[str, ...]:
    source_package_root = (source_root / "src").resolve()
    root = dependency_root.path.resolve()
    if str(root) not in sys.path:
        sys.path.append(str(root))
    origins: list[str] = []
    for probe in contract.material["import_policy"]["dependency_import_probes"]:
        module = importlib.import_module(probe["module"])
        origin = getattr(module, "__file__", "")
        if not origin:
            raise CanonicalControlError("dependency import probe lacks a file origin")
        try:
            relative = Path(origin).resolve().relative_to(root)
        except ValueError as exc:
            raise CanonicalControlError("dependency module escaped the closed root") from exc
        origins.append(relative.as_posix())
    try:
        importlib.import_module("pip")
    except ModuleNotFoundError:
        pass
    else:
        raise CanonicalControlError("undeclared ambient distribution is importable")
    for name, module in tuple(sys.modules.items()):
        if not name.startswith("orev3.execution"):
            continue
        origin = getattr(module, "__file__", "")
        if not origin:
            continue
        try:
            Path(origin).resolve().relative_to(source_package_root)
        except ValueError as exc:
            raise CanonicalControlError("project control-plane module escaped detached S") from exc
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    runtime_lib = stdlib.parent
    for entry in sys.path:
        if not entry:
            continue
        resolved = Path(entry).resolve()
        if resolved in {source_package_root, root}:
            continue
        try:
            resolved.relative_to(runtime_lib)
        except ValueError as exc:
            raise CanonicalControlError("module search path contains an unbound root") from exc
    return tuple(origins)


def sanitized_worker_environment(temp_root: Path) -> dict[str, str]:
    return {"HOME": str(temp_root / "home"), "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "TMPDIR": str(temp_root / "tmp"), "TZ": "UTC"}


def _seatbelt_path(path: Path) -> tuple[Path, str]:
    resolved = path.resolve(strict=True)
    value = str(resolved)
    if any(character in value for character in ('"', "\\", "\n", "\r", "\x00")):
        raise CanonicalControlError("sandbox capability path cannot be represented safely")
    return resolved, f'"{value}"'


def render_phase3b_sandbox_profile(
    *,
    policy: Mapping[str, Any],
    worker_kind: str,
    worker_name: str,
    command: str,
    source_root: Path,
    dependency_root: Path,
    request_path: Path,
    temporary_root: Path,
    read_files: tuple[Path, ...] = (),
    read_roots: tuple[Path, ...] = (),
    write_roots: tuple[Path, ...] = (),
    interpreter: Path | None = None,
) -> tuple[str, Mapping[str, Any]]:
    """Render one default-deny profile from a governed worker-kind policy."""

    if policy.get("profile_renderer_identity") != PHASE3B_PROFILE_RENDERER_IDENTITY:
        raise CanonicalControlError("Phase-3B profile renderer identity differs")
    workers = policy.get("worker_profiles")
    if not isinstance(workers, list):
        raise CanonicalControlError("Phase-3B worker profile policy is absent")
    matches = [item for item in workers if item.get("worker_kind") == worker_kind]
    if len(matches) != 1:
        raise CanonicalControlError("Phase-3B worker kind is missing or duplicated")
    declaration = matches[0]
    expected_module = f"src/orev3/execution/{worker_name}"
    if declaration.get("module") != expected_module or command not in declaration.get("commands", ()):
        raise CanonicalControlError("Phase-3B worker mapping or command differs from policy")
    if declaration.get("network_policy") != "prohibited" or declaration.get("sandbox_template_revision") != "macos-seatbelt-capability-v4":
        raise CanonicalControlError("Phase-3B sandbox policy is weakened")
    template_material = {
        "allowed_read_roles": declaration.get("allowed_read_roles"),
        "allowed_write_roles": declaration.get("allowed_write_roles"),
        "commands": declaration.get("commands"),
        "denied_roles": declaration.get("denied_roles"),
        "module": declaration.get("module"),
        "network_policy": declaration.get("network_policy"),
        "sandbox_template_revision": declaration.get("sandbox_template_revision"),
        "worker_kind": declaration.get("worker_kind"),
    }
    if domain_identity(PHASE3B_PROFILE_RENDERER_DOMAIN, template_material) != declaration.get("sandbox_template_identity"):
        raise CanonicalControlError("Phase-3B sandbox template identity differs")

    interpreter_path = (interpreter or Path(sys.executable)).resolve(strict=True)
    base_prefix = Path(sys.base_prefix).resolve(strict=True)
    fixed_read_roots = tuple(path for path in (
        source_root,
        dependency_root,
        temporary_root,
        base_prefix,
        Path("/System"),
        Path("/usr/lib"),
        Path("/private/var/db/dyld"),
        Path("/private/etc"),
        Path("/dev"),
    ) if path.exists())
    normalized_read_roots = sorted({_seatbelt_path(path)[0] for path in (*fixed_read_roots, *read_roots)}, key=str)
    normalized_write_roots = sorted({
        _seatbelt_path(path)[0]
        for path in (temporary_root / "home", temporary_root / "tmp", *write_roots)
    }, key=str)
    exact_read_paths: set[Path] = set()
    for path in (request_path, *read_files):
        resolved = _seatbelt_path(path)[0]
        exact_read_paths.add(resolved)
        # Descriptor-relative no-follow traversal needs directory descriptors
        # for the lexical ancestor chain.  Literal directory capabilities do
        # not grant access to sibling children (unlike a Seatbelt subpath).
        exact_read_paths.update(resolved.parents)
    normalized_read_files = sorted(exact_read_paths, key=str)
    _, interpreter_literal = _seatbelt_path(interpreter_path)
    process_executables = [interpreter_literal]
    app_runtime = base_prefix / "Resources/Python.app/Contents/MacOS/Python"
    if app_runtime.exists():
        process_executables.append(_seatbelt_path(app_runtime)[1])
    lines = [
        "(version 1)",
        "(deny default)",
        '(import "system.sb")',
        "(allow process-exec " + " ".join(f"(literal {value})" for value in process_executables) + ")",
        "(allow process-info*)",
        "(allow sysctl-read)",
        "(allow mach-lookup)",
        "(allow ipc-posix*)",
        "(allow file-read-metadata)",
    ]
    for root in normalized_read_roots:
        lines.append(f'(allow file-read* (subpath "{root}"))')
    for path in normalized_read_files:
        lines.append(f'(allow file-read* (literal "{path}"))')
    for root in normalized_write_roots:
        lines.append(f'(allow file-write* (subpath "{root}"))')
    lines.append("(deny network*)")
    profile = "\n".join(lines) + "\n"
    rendered = {
        "sandbox_template_identity": declaration["sandbox_template_identity"],
        "worker_kind": worker_kind,
    }
    return profile, rendered


def _enforce_temporary_disk_limit(roots: tuple[Path, ...], limit: int) -> None:
    total = 0
    entries = 0
    pending = list(roots)
    seen: set[tuple[int, int]] = set()
    while pending:
        root = pending.pop()
        try:
            opened = os.lstat(root)
        except FileNotFoundError:
            continue
        identity = (opened.st_dev, opened.st_ino)
        if identity in seen:
            continue
        seen.add(identity); entries += 1
        if entries > 100_000:
            raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
        if stat.S_ISREG(opened.st_mode):
            total += opened.st_size
        elif stat.S_ISDIR(opened.st_mode):
            with os.scandir(root) as directory:
                pending.extend(Path(item.path) for item in directory)
        if total > limit:
            raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")


def _readiness_test_code_paths(
    repository: GitRepository, source_commit: str, selectors: object
) -> tuple[str, ...]:
    """Return the exact committed code/configuration capability for pytest.

    Phase-3B v1 intentionally supports exact test-file selectors only.  This
    makes collection authority finite and prevents pytest from discovering or
    importing unrelated experiment, parser, Replay, or outcome-capable code.
    """

    if not isinstance(selectors, list) or not selectors:
        raise CanonicalControlError("readiness-test selectors are absent")
    selected: set[str] = set()
    for selector in selectors:
        if not isinstance(selector, str):
            raise CanonicalControlError("readiness-test selector is invalid")
        path = validate_repository_path(selector.split("::", 1)[0])
        if not path.startswith("tests/") or not path.endswith(".py"):
            raise CanonicalControlError("Phase-3B v1 requires exact readiness-test files")
        entry = repository.tree_entry(source_commit, path)
        if entry.object_type != "blob" or entry.mode not in {"100644", "100755"}:
            raise CanonicalControlError("readiness-test selector is not an ordinary committed file")
        selected.add(path)

        parts = path.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            parent = "/".join(parts[:index])
            for candidate in (f"{parent}/conftest.py", f"{parent}/__init__.py"):
                if repository.optional_tree_entry(source_commit, candidate) is not None:
                    selected.add(candidate)

    for candidate in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
        if repository.optional_tree_entry(source_commit, candidate) is not None:
            selected.add(candidate)
    return tuple(sorted(selected))


def run_phase3b_worker(
    source_root: Path,
    source_commit: str,
    worker_kind: str,
    worker_name: str,
    request_material: Mapping[str, Any],
    *,
    dependency_root: Path,
    runtime_contract_identity: str,
    dependency_environment_identity: str,
    capability_policy: Mapping[str, Any],
    invocation_identifier: str = "single",
    input_capability_identities: tuple[str, ...] = (),
    read_files: tuple[Path, ...] = (),
    read_roots: tuple[Path, ...] = (),
    write_roots: tuple[Path, ...] = (),
    timeout_seconds: int = WORKER_TIMEOUT_SECONDS,
    max_output_bytes: int = MAX_WORKER_OUTPUT_BYTES,
    interpreter: Path | None = None,
) -> Phase3BWorkerEvidence:
    """Run one fixed Phase-3B worker; returned material is evidence, not authority."""

    if worker_name not in SAFE_PHASE3B_WORKERS:
        raise CanonicalControlError("Phase-3B worker is not permitted")
    if not invocation_identifier or len(invocation_identifier) > 64 or not all(
        character.islower() or character.isdigit() or character in "-_" for character in invocation_identifier
    ):
        raise CanonicalControlError("Phase-3B worker invocation identifier is invalid")
    temporary_root = Path(tempfile.mkdtemp(prefix="orev3-evidence-worker-"))
    try:
        (temporary_root / "home").mkdir()
        (temporary_root / "tmp").mkdir()
        repository = GitRepository(source_root)
        module_path = f"src/orev3/execution/{worker_name}"
        module_identity = repository.tree_entry(source_commit, module_path).object_identity
        execution_source = source_root
        code_closure_identities: list[str] = []
        if worker_kind in {"READINESS_TEST", "INPUT_PROJECTOR", "REPLAY_PREPARATION"}:
            from orev3.execution.phase3b_components import WORKER_CODE_CLOSURES
            try:
                code_paths = list(WORKER_CODE_CLOSURES[worker_kind])
            except KeyError as exc:
                raise CanonicalControlError("Phase-3B code capability is absent") from exc
            if worker_kind == "READINESS_TEST":
                code_paths.extend(
                    _readiness_test_code_paths(
                        repository, source_commit, request_material.get("selectors")
                    )
                )
            execution_source = temporary_root / "code-capability"
            for relative in sorted(set(code_paths)):
                entry = repository.tree_entry(source_commit, relative)
                raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
                target = execution_source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                code_closure_identities.append(entry.object_identity)
        request = dict(request_material)
        limits = capability_policy.get("limits", {})
        request["resource_limits"] = {
            "max_open_files": limits.get("max_open_files", 256),
            "max_processes": limits.get("max_processes", 16),
            "max_temporary_disk_bytes": limits.get("max_temporary_disk_bytes", 1_073_741_824),
        }
        request["source_root"] = str(execution_source.resolve())
        request["dependency_root"] = str(dependency_root.resolve())
        request_path = temporary_root / "request.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        worker = execution_source / "src/orev3/execution" / worker_name
        profile, profile_material = render_phase3b_sandbox_profile(
            policy=capability_policy,
            worker_kind=worker_kind,
            worker_name=worker_name,
            command=str(request_material.get("command", "")),
            source_root=execution_source,
            dependency_root=dependency_root,
            request_path=request_path,
            temporary_root=temporary_root,
            read_files=read_files,
            read_roots=read_roots,
            write_roots=write_roots,
            interpreter=interpreter,
        )
        try:
            completed = _run_bounded_process(
                (str(MACOS_SANDBOX_EXEC), "-p", profile, str((interpreter or Path(sys.executable)).resolve()), "-I", "-S", str(worker), str(request_path)),
                cwd=execution_source,
                environment=sanitized_worker_environment(temporary_root),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
                periodic_guard=lambda: _enforce_temporary_disk_limit(
                    (temporary_root, *write_roots),
                    int(limits.get("max_temporary_disk_bytes", 1_073_741_824)),
                ),
            )
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.GIT_COMMAND_TIMEOUT:
                raise CanonicalControlError("WORKER_TIMEOUT") from exc
            if exc.code == GitDiagnosticCode.GIT_OUTPUT_LIMIT_EXCEEDED:
                raise CanonicalControlError("WORKER_OUTPUT_LIMIT_EXCEEDED") from exc
            raise
        if completed.returncode != 0:
            default_code = {
                "INPUT_PROJECTOR": "PROJECTION_INVALID",
                "READINESS_TEST": "READINESS_TEST_FAILED",
                "REPLAY_PREPARATION": "REPLAY_IDENTITY_MISMATCH",
            }.get(worker_kind, "EVIDENCE_PREPARATION_INTERNAL_REJECTED")
            stable_code = default_code
            try:
                rejection = json.loads(completed.stdout.decode("utf-8", errors="strict"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                rejection = None
            permitted_failure_codes = {
                "INPUT_MISMATCH",
                "INPUT_MUTATED",
                "INPUT_SCHEMA_MISMATCH",
                "OUTCOME_ISOLATION_VIOLATION",
                "POPULATION_MISMATCH",
                "PROJECTION_INVALID",
                "READINESS_TEST_FAILED",
                "REPLAY_IDENTITY_MISMATCH",
                "RESOURCE_LIMIT_EXCEEDED",
            }
            if (
                isinstance(rejection, dict)
                and rejection.get("status") == "evidence_rejected"
                and rejection.get("failure_code") in permitted_failure_codes
                and set(rejection) == {"failure_code", "status"}
            ):
                stable_code = rejection["failure_code"]
            raise CanonicalControlError(stable_code)
        try:
            result = json.loads(completed.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalControlError("Phase-3B worker result is malformed") from exc
        if not isinstance(result, dict) or result.get("status") != "evidence_passed":
            raise CanonicalControlError("Phase-3B worker did not return evidence")
        result_identity = domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, result)
        material = {
            "capability_policy_identity": capability_policy["policy_identity"],
            "closed_dependency_identity": dependency_environment_identity,
            "command_identity": domain_identity(
                PHASE3B_WORKER_EVIDENCE_DOMAIN,
                {
                    "command": request_material["command"],
                    "invocation_identifier": invocation_identifier,
                    "worker_kind": worker_kind,
                },
            ),
            "code_capability_git_identities": sorted(code_closure_identities),
            "input_capability_identities": list(sorted(input_capability_identities)),
            "output_identity": result_identity,
            "runtime_contract_identity": runtime_contract_identity,
            "sandbox_template_identity": profile_material["sandbox_template_identity"],
            "source_commit": source_commit,
            "successful_worker_disposition": "evidence_passed",
            "worker_kind": worker_kind,
            "worker_module_git_identity": module_identity,
        }
        evidence_identity = domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, material)
        return Phase3BWorkerEvidence(worker_kind, evidence_identity, {**material, "worker_evidence_identity": evidence_identity}, result)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def run_phase3b_controller(
    source_root: Path,
    request_material: Mapping[str, Any],
    *,
    timeout_seconds: int,
    max_output_bytes: int,
    interpreter: Path | None = None,
) -> Mapping[str, Any]:
    """Launch the fixed detached-S controller without Seatbelt so it can create sibling sandboxes."""

    temporary_root = Path(tempfile.mkdtemp(prefix="orev3-evidence-controller-"))
    try:
        (temporary_root / "home").mkdir()
        (temporary_root / "tmp").mkdir()
        request = dict(request_material)
        request["source_root"] = str(source_root.resolve())
        request_path = temporary_root / "request.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        controller = source_root / "src/orev3/execution" / PHASE3B_CONTROLLER
        try:
            completed = _run_bounded_process(
                (str((interpreter or Path(sys.executable)).resolve()), "-I", "-S", str(controller), str(request_path)),
                cwd=source_root,
                environment=sanitized_worker_environment(temporary_root),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            )
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.GIT_COMMAND_TIMEOUT:
                raise CanonicalControlError("WORKER_TIMEOUT") from exc
            if exc.code == GitDiagnosticCode.GIT_OUTPUT_LIMIT_EXCEEDED:
                raise CanonicalControlError("WORKER_OUTPUT_LIMIT_EXCEEDED") from exc
            raise
        if completed.returncode != 0:
            raise CanonicalControlError(
                f"detached Phase-3B controller rejected evidence (code {completed.returncode})"
            )
        try:
            result = json.loads(completed.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalControlError("detached Phase-3B controller result is malformed") from exc
        if not isinstance(result, dict) or result.get("status") != "controller_evidence_passed":
            raise CanonicalControlError("detached Phase-3B controller did not return evidence")
        return result
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


class DetachedSource(AbstractContextManager[Path]):
    """Temporary detached Git worktree at an exact committed S."""

    def __init__(self, repository: GitRepository, source_commit: str) -> None:
        self.repository = repository
        self.source_commit = repository.resolve_commit(source_commit)
        self._root = Path(tempfile.mkdtemp(prefix="orev3-readiness-source-"))
        self.path = self._root / "source"
        self._registered = False

    def __enter__(self) -> Path:
        try:
            self.repository.run("worktree", "add", "--detach", "--no-checkout", str(self.path), self.source_commit)
            self._registered = True
            self.repository.run("-C", str(self.path), "checkout", "--detach", self.source_commit)
            return self.path
        except (GitAuthorityError, OSError):
            self._cleanup()
            raise

    def _cleanup(self) -> None:
        try:
            if self._registered:
                self.repository.run("worktree", "remove", "--force", str(self.path), check=False)
        except (GitAuthorityError, OSError):
            # Cleanup is best effort and must not mask the trust-bearing failure.
            pass
        finally:
            shutil.rmtree(self._root, ignore_errors=True)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._cleanup()


def _run_preparation_worker(source_root: Path, command: str, request_material: Mapping[str, Any], *, interpreter: Path | None = None) -> PreparationWorkerEvidence:
    """Return detached predicate evidence; this function cannot mint authority."""

    if command not in SAFE_WORKER_COMMANDS:
        raise CanonicalControlError("preparation worker command is not permitted")
    interpreter_path = (interpreter or Path(sys.executable)).resolve()
    temp_root = Path(tempfile.mkdtemp(prefix="orev3-readiness-worker-"))
    try:
        (temp_root / "home").mkdir()
        (temp_root / "tmp").mkdir()
        request = dict(request_material)
        request["command"] = command
        request["source_root"] = str(source_root.resolve())
        request_path = temp_root / "request.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        worker = source_root / "src/orev3/execution/preparation_worker.py"
        completed = _run_bounded_process(
            (str(MACOS_SANDBOX_EXEC), "-p", NETWORK_SANDBOX_PROFILE, str(interpreter_path), "-I", "-S", str(worker), str(request_path)),
            cwd=source_root,
            environment=sanitized_worker_environment(temp_root),
            timeout_seconds=WORKER_TIMEOUT_SECONDS,
            max_output_bytes=MAX_WORKER_OUTPUT_BYTES,
        )
        if completed.returncode != 0:
            raise CanonicalControlError(f"detached preparation worker rejected the environment (code {completed.returncode})")
        try:
            result = json.loads(completed.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalControlError("preparation worker result is malformed") from exc
        if not isinstance(result, dict) or result.get("command") != command or result.get("status") != "evidence_passed":
            raise CanonicalControlError("preparation worker did not produce predicate evidence")
        return PreparationWorkerEvidence(command, result)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


__all__ = [
    "ClosedDependencyRoot", "DependencyLockV1", "DetachedSource", "LockedWheel", "NETWORK_SANDBOX_PROFILE", "OfflineArtifactManifestV1", "PHASE3A_SANDBOX_TEMPLATE_IDENTITY", "PHASE3B_CONTROLLER", "PHASE3B_PROFILE_RENDERER_IDENTITY", "PHASE3B_WORKER_EVIDENCE_DOMAIN", "Phase3BWorkerEvidence", "PreparationWorkerEvidence", "RuntimeContractV1", "SAFE_PHASE3B_WORKERS", "SAFE_WORKER_COMMANDS", "construct_closed_dependency_root", "load_offline_artifact_manifest_bytes", "load_runtime_contract_bytes", "reconstruct_host_system_material", "reconstruct_offline_artifact_manifest_identity", "reconstruct_runtime_bundle_identity", "reconstruct_runtime_contract_identity", "render_phase3b_sandbox_profile", "run_phase3b_controller", "run_phase3b_worker", "sanitized_worker_environment", "validate_closed_dependency_imports", "validate_dependency_lock", "validate_host_runtime",
]
