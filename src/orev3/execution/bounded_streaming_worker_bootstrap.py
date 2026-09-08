"""Shared fixed-FD bootstrap for bounded-streaming measurement workers."""

import os
import sys
import fcntl
import stat
import hashlib
import json
import unicodedata

MAX_BOUNDED_STREAMING_BOOTSTRAP_REQUEST_BYTES = 4_194_304
BOOTSTRAP_REQUEST_DOMAIN = "orev3:bounded-streaming-worker-bootstrap-request:v1\n"
BOUNDED_GENERATION = "prospective-v1.1-adapter-v4-experiment5-bounded-streaming"
INTEGRITY_FAILURE = "BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY"
TERMINAL_INTEGRITY_EXIT_STATUS = 70
FIXED_FDS = {"start_gate": 3, "reservation_socket": 4, "operation_lease": 5, "request": 6}
SYNTHETIC_PACKAGES = (
    "orev3", "orev3.datasets", "orev3.execution", "orev3.experiments",
    "orev3.features", "orev3.historical", "orev3.replay", "orev3.strategy_lab",
)
BOUNDED_STREAMING_WORKER_DISPATCH = {
    "phase3b-controller-v1": ("phase3b_controller", "orev3.execution.evidence_preparation_worker", "main", "bounded-phase3b-controller-import-closure-v1", "MODEL_A"),
    "phase3a-validator-v1": ("phase3a_validator", "orev3.execution.preparation_worker", "main", "bounded-phase3a-validator-import-closure-v1", "MODEL_A"),
    "input-projector-v1": ("input_projector", "orev3.execution.input_projection_worker", "main", "bounded-input-projector-import-closure-v1", "MODEL_B"),
    "readiness-test-v1": ("readiness_test", "orev3.execution.readiness_test_worker", "main", "bounded-readiness-test-import-closure-v1", "MODEL_A"),
    "replay-preparation-v1": ("replay_preparation", "orev3.execution.replay_preparation_worker", "main", "bounded-replay-preparation-import-closure-v1", "MODEL_A"),
}
_OUTER_FIELDS = frozenset((
    "schema_version", "request_kind", "operation_id", "authority_generation",
    "execution_profile_identity", "runtime_contract_identity", "source_root_authority",
    "dependency_root_authority", "runtime_bundle_authority", "worker_entrypoint_identifier",
    "worker_code_closure_identity", "worker_request_byte_count", "worker_request_sha256",
    "worker_request_canonical_json", "bootstrap_request_identity",
))
_SOURCE_FIELDS = frozenset((
    "absolute_root", "source_commit", "root_tree_git_object_identity",
    "source_code_closure_manifest",
))
_RUNTIME_FIELDS = frozenset((
    "runtime_bundle_identity", "python_executable_path", "stdlib_roots",
    "dynamic_library_roots", "runtime_bundle_material",
))
_MANIFEST_FIELDS = frozenset((
    "schema_version", "source_closure_identifier", "source_commit",
    "root_tree_git_object_identity", "git_object_format", "members",
    "source_code_closure_manifest_identity",
))
_MANIFEST_MEMBER_FIELDS = frozenset((
    "path", "mode", "file_kind", "git_object_identity", "byte_count", "sha256",
))
MODEL_B_MODULE_PATHS = (
    ("orev3.datasets.rq003_experiment0", "src/orev3/datasets/rq003_experiment0.py"),
    ("orev3.execution.canonical", "src/orev3/execution/canonical.py"),
    ("orev3.execution.dataset_validation", "src/orev3/execution/dataset_validation.py"),
    ("orev3.execution.filesystem_capability", "src/orev3/execution/filesystem_capability.py"),
    ("orev3.execution.input_projection_worker", "src/orev3/execution/input_projection_worker.py"),
    ("orev3.execution.projection", "src/orev3/execution/projection.py"),
    ("orev3.execution.replay_preparation", "src/orev3/execution/replay_preparation.py"),
    ("orev3.experiments.rq003_execution_specification", "src/orev3/experiments/rq003_execution_specification.py"),
    ("orev3.experiments.rq003_execution_specification_v2", "src/orev3/experiments/rq003_execution_specification_v2.py"),
    ("orev3.experiments.rq003_experiment2a", "src/orev3/experiments/rq003_experiment2a.py"),
    ("orev3.experiments.rq003_experiment5", "src/orev3/experiments/rq003_experiment5.py"),
    ("orev3.experiments.rq003_experiment5_ranking", "src/orev3/experiments/rq003_experiment5_ranking.py"),
    ("orev3.experiments.rq003_experiment5_source_measurements", "src/orev3/experiments/rq003_experiment5_source_measurements.py"),
    ("orev3.experiments.rq003_experiment5_source_processing", "src/orev3/experiments/rq003_experiment5_source_processing.py"),
    ("orev3.features.base", "src/orev3/features/base.py"),
    ("orev3.features.context", "src/orev3/features/context.py"),
    ("orev3.features.rq003_active_round_motherlode", "src/orev3/features/rq003_active_round_motherlode.py"),
    ("orev3.features.rq003_contracts", "src/orev3/features/rq003_contracts.py"),
    ("orev3.features.rq003_deployed_lamports", "src/orev3/features/rq003_deployed_lamports.py"),
    ("orev3.features.rq003_execution", "src/orev3/features/rq003_execution.py"),
    ("orev3.features.rq003_measurement_support", "src/orev3/features/rq003_measurement_support.py"),
    ("orev3.features.rq003_miner_count", "src/orev3/features/rq003_miner_count.py"),
    ("orev3.features.rq003_production_cost_ema", "src/orev3/features/rq003_production_cost_ema.py"),
    ("orev3.features.rq003_registry", "src/orev3/features/rq003_registry.py"),
    ("orev3.features.rq003_total_miners", "src/orev3/features/rq003_total_miners.py"),
    ("orev3.features.rq003_total_vaulted", "src/orev3/features/rq003_total_vaulted.py"),
    ("orev3.features.rq003_total_winnings", "src/orev3/features/rq003_total_winnings.py"),
    ("orev3.features.rq003_treasury_motherlode", "src/orev3/features/rq003_treasury_motherlode.py"),
    ("orev3.features.types", "src/orev3/features/types.py"),
    ("orev3.historical.models", "src/orev3/historical/models.py"),
    ("orev3.historical.reader", "src/orev3/historical/reader.py"),
    ("orev3.replay.engine", "src/orev3/replay/engine.py"),
    ("orev3.replay.loader", "src/orev3/replay/loader.py"),
    ("orev3.replay.models", "src/orev3/replay/models.py"),
    ("orev3.strategy_lab.interfaces", "src/orev3/strategy_lab/interfaces.py"),
    ("orev3.strategy_lab.runner", "src/orev3/strategy_lab/runner.py"),
)
MODEL_A_CLOSURE_PATHS = {
    "bounded-phase3b-controller-import-closure-v1": (
        "src/orev3/__init__.py", "src/orev3/execution/__init__.py",
        "src/orev3/execution/canonical.py", "src/orev3/execution/contract_validation.py",
        "src/orev3/execution/dataset_validation.py", "src/orev3/execution/evidence_preparation.py",
        "src/orev3/execution/evidence_preparation_worker.py", "src/orev3/execution/external_inputs.py",
        "src/orev3/execution/filesystem_capability.py", "src/orev3/execution/git_state.py",
        "src/orev3/execution/phase3b_components.py", "src/orev3/execution/preparation.py",
        "src/orev3/execution/readiness.py", "src/orev3/execution/readiness_candidate.py",
        "src/orev3/execution/readiness_record.py", "src/orev3/execution/registry.py",
        "src/orev3/execution/replay_preparation.py", "src/orev3/execution/runtime.py",
        "src/orev3/execution/test_policy.py", "src/orev3/execution/zero_input_phase3b.py",
    ),
    "bounded-phase3a-validator-import-closure-v1": (
        "src/orev3/__init__.py", "src/orev3/execution/__init__.py",
        "src/orev3/execution/canonical.py", "src/orev3/execution/contract_validation.py",
        "src/orev3/execution/dataset_validation.py", "src/orev3/execution/evidence_preparation.py",
        "src/orev3/execution/external_inputs.py", "src/orev3/execution/filesystem_capability.py",
        "src/orev3/execution/git_state.py", "src/orev3/execution/phase3b_components.py",
        "src/orev3/execution/preparation.py", "src/orev3/execution/preparation_worker.py",
        "src/orev3/execution/readiness.py", "src/orev3/execution/readiness_candidate.py",
        "src/orev3/execution/readiness_record.py", "src/orev3/execution/registry.py",
        "src/orev3/execution/replay_preparation.py", "src/orev3/execution/runtime.py",
        "src/orev3/execution/test_policy.py", "src/orev3/execution/zero_input_phase3b.py",
    ),
    "bounded-readiness-test-import-closure-v1": (
        "config/research/readiness/adapter-registry-v1.json",
        "config/research/readiness/attempt-authority-contract-v1.json", "pyproject.toml",
        "src/orev3/__init__.py", "src/orev3/execution/__init__.py",
        "src/orev3/execution/attempts.py", "src/orev3/execution/canonical.py",
        "src/orev3/execution/contract_validation.py", "src/orev3/execution/control_storage.py",
        "src/orev3/execution/dataset_validation.py", "src/orev3/execution/evidence_preparation.py",
        "src/orev3/execution/external_inputs.py", "src/orev3/execution/filesystem_capability.py",
        "src/orev3/execution/git_state.py", "src/orev3/execution/orchestrator.py",
        "src/orev3/execution/outcome_gate.py", "src/orev3/execution/phase3b_components.py",
        "src/orev3/execution/preparation.py", "src/orev3/execution/readiness.py",
        "src/orev3/execution/readiness_candidate.py", "src/orev3/execution/readiness_record.py",
        "src/orev3/execution/readiness_test_worker.py", "src/orev3/execution/registry.py",
        "src/orev3/execution/replay_preparation.py", "src/orev3/execution/runtime.py",
        "src/orev3/execution/test_policy.py", "src/orev3/execution/zero_input_phase3b.py",
        "src/orev3/execution/schemas/v1/adapter-declaration-v3.schema.json",
        "src/orev3/execution/schemas/v1/adapter-registry.schema.json",
        "src/orev3/execution/schemas/v1/artifact-declaration-evidence.schema.json",
        "src/orev3/execution/schemas/v1/attempt-allocation.schema.json",
        "src/orev3/execution/schemas/v1/attempt-authority-contract.schema.json",
        "src/orev3/execution/schemas/v1/attempt-control-record.schema.json",
        "src/orev3/execution/schemas/v1/attempt-identity-material.schema.json",
        "src/orev3/execution/schemas/v1/dataset-validation-evidence.schema.json",
        "src/orev3/execution/schemas/v1/evidence-preparation-policy.schema.json",
        "src/orev3/execution/schemas/v1/evidence-preparation-v2.schema.json",
        "src/orev3/execution/schemas/v1/execution-control-manifest.schema.json",
        "src/orev3/execution/schemas/v1/immutable-input-snapshot.schema.json",
        "src/orev3/execution/schemas/v1/implementation-binding.schema.json",
        "src/orev3/execution/schemas/v1/launch-authority-snapshot.schema.json",
        "src/orev3/execution/schemas/v1/offline-artifact-manifest.schema.json",
        "src/orev3/execution/schemas/v1/outcome-authorization.schema.json",
        "src/orev3/execution/schemas/v1/outcome-blind-projection-evidence.schema.json",
        "src/orev3/execution/schemas/v1/output-namespace-identity-material.schema.json",
        "src/orev3/execution/schemas/v1/population-accounting-evidence-v2.schema.json",
        "src/orev3/execution/schemas/v1/profile-conformance-evidence-v2.schema.json",
        "src/orev3/execution/schemas/v1/profile-contract.schema.json",
        "src/orev3/execution/schemas/v1/readiness-failure-receipt.schema.json",
        "src/orev3/execution/schemas/v1/readiness-record-v2.schema.json",
        "src/orev3/execution/schemas/v1/readiness-test-evidence.schema.json",
        "src/orev3/execution/schemas/v1/readiness-test-policy-v2.schema.json",
        "src/orev3/execution/schemas/v1/replay-evidence-v2.schema.json",
        "src/orev3/execution/schemas/v1/repository-authority.schema.json",
        "src/orev3/execution/schemas/v1/runtime-contract.schema.json",
        "src/orev3/execution/schemas/v1/source-scope.schema.json",
        "tests/execution/test_attempts.py", "tests/execution/test_control_storage.py",
        "tests/execution/test_orchestrator.py", "tests/execution/test_outcome_gate.py",
        "tests/execution/test_phase3c_schema_registry.py",
        "tests/execution/test_readiness_mandatory_v1.py",
    ),
    "bounded-replay-preparation-import-closure-v1": (
        "src/orev3/__init__.py", "src/orev3/execution/__init__.py",
        "src/orev3/execution/canonical.py", "src/orev3/execution/filesystem_capability.py",
        "src/orev3/execution/replay_preparation.py",
        "src/orev3/execution/replay_preparation_worker.py",
    ),
}
_IDENTITY_FIELDS = (
    "execution_profile_identity", "runtime_contract_identity",
    "worker_code_closure_identity", "worker_request_sha256",
    "bootstrap_request_identity",
)


class BoundedBootstrapError(Exception):
    pass


class BoundedProjectImportError(ImportError):
    pass


def _reject(_detail=""):
    raise BoundedBootstrapError("BOUNDED_STREAMING_BOOTSTRAP_REJECTED")


def _open_relative_regular(root, relative):
    if not isinstance(relative, str) or relative.startswith("/") or "\\" in relative or "\x00" in relative or unicodedata.normalize("NFC", relative) != relative:
        _reject()
    parts = relative.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        _reject()
    current = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
            os.close(current)
            current = child
        return os.open(parts[-1], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
    finally:
        os.close(current)


def _read_authenticated_source_member(root, material):
    descriptor = _open_relative_regular(root, material["path"])
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or stat.S_IMODE(opened.st_mode) != 0o644 or material["mode"] != "100644" or opened.st_size != material["byte_count"]:
            _reject()
        digest = hashlib.sha256()
        payload = bytearray()
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            payload.extend(chunk)
        closed = os.fstat(descriptor)
        before = (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        after = (closed.st_dev, closed.st_ino, closed.st_mode, closed.st_size, closed.st_mtime_ns, closed.st_ctime_ns)
        raw = bytes(payload)
        git_object = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        if before != after or digest.hexdigest() != material["sha256"] or git_object != material["git_object_identity"]:
            _reject()
        return raw
    finally:
        os.close(descriptor)


def authenticate_source_code_closure(root, manifest, *, model_b=False, closure_identifier=None):
    members = manifest["members"]
    paths = [member["path"] for member in members]
    if len(paths) != len(set(paths)):
        _reject()
    if model_b and paths != [path for _name, path in MODEL_B_MODULE_PATHS]:
        _reject()
    if not model_b:
        expected = MODEL_A_CLOSURE_PATHS.get(closure_identifier)
        if expected is None or tuple(paths) != expected:
            _reject()
    by_path = {}
    for member in members:
        path = member["path"]
        expected_kind = (
            "python_source" if path.startswith("src/") and path.endswith(".py")
            else "test_source" if path.startswith("tests/") and path.endswith(".py")
            else "test_configuration"
        )
        if (
            member["file_kind"] != expected_kind or member["mode"] != "100644"
            or type(member["byte_count"]) is not int or member["byte_count"] < 0
            or not _is_hex(member["sha256"], 64)
            or not _is_hex(member["git_object_identity"], 40)
        ):
            _reject()
        _read_authenticated_source_member(root, member)
        by_path[member["path"]] = member
    return by_path


def assert_model_a_import_origins(root, authenticated_paths):
    permitted = frozenset(authenticated_paths)
    for name, module in tuple(sys.modules.items()):
        if name != "orev3" and not name.startswith("orev3."):
            continue
        origin = getattr(module, "__file__", None)
        if not isinstance(origin, str):
            _reject()
        try:
            relative = os.path.relpath(origin, root)
        except (OSError, ValueError):
            _reject()
        if relative.startswith("../") or relative not in permitted:
            _reject()


def bootstrap_validate_value(value):
    if value is None or isinstance(value, float):
        _reject()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if "\x00" in value or unicodedata.normalize("NFC", value) != value:
            _reject()
        try:
            value.encode("utf-8", "strict")
        except UnicodeEncodeError:
            _reject()
        return value
    if isinstance(value, list):
        for item in value:
            bootstrap_validate_value(item)
        return value
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _reject()
            bootstrap_validate_value(key)
            bootstrap_validate_value(item)
        return value
    _reject()


def bootstrap_canonical_bytes(value):
    bootstrap_validate_value(value)
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", "strict") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError):
        _reject()
    return encoded


def bootstrap_domain_identity(domain, material):
    if (
        not isinstance(domain, str) or not domain.endswith("\n")
        or domain.endswith("\n\n") or unicodedata.normalize("NFC", domain) != domain
    ):
        _reject()
    return hashlib.sha256(domain.encode("utf-8") + bootstrap_canonical_bytes(material)).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject()
        result[key] = value
    return result


def _no_float(_value):
    _reject()


def _no_constant(_value):
    _reject()


def _is_hex(value, length):
    return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)


def _require_exact_fields(value, fields):
    if not isinstance(value, dict) or frozenset(value) != fields:
        _reject()


def bootstrap_parse_request_bytes(raw):
    if (
        not isinstance(raw, bytes) or not raw
        or len(raw) > MAX_BOUNDED_STREAMING_BOOTSTRAP_REQUEST_BYTES
        or raw.startswith(b"\xef\xbb\xbf") or raw.endswith((b"\n", b"\r"))
    ):
        _reject()
    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(
            text, object_pairs_hook=_pairs, parse_float=_no_float,
            parse_constant=_no_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, BoundedBootstrapError):
        _reject()
    bootstrap_validate_value(value)
    _require_exact_fields(value, _OUTER_FIELDS)
    if value["schema_version"] != 1 or type(value["schema_version"]) is not int:
        _reject()
    if value["authority_generation"] != BOUNDED_GENERATION:
        _reject()
    operation_id = value["operation_id"]
    if not isinstance(operation_id, str) or len(operation_id) != 35 or not operation_id.startswith("op-") or not _is_hex(operation_id[3:], 32):
        _reject()
    for name in _IDENTITY_FIELDS:
        if not _is_hex(value[name], 64):
            _reject()
    _require_exact_fields(value["source_root_authority"], _SOURCE_FIELDS)
    entry = BOUNDED_STREAMING_WORKER_DISPATCH.get(value["worker_entrypoint_identifier"])
    manifest = value["source_root_authority"]["source_code_closure_manifest"]
    _require_exact_fields(manifest, _MANIFEST_FIELDS)
    if (
        manifest["schema_version"] != 1 or type(manifest["schema_version"]) is not int
        or manifest["git_object_format"] != "sha1"
        or manifest["source_commit"] != value["source_root_authority"]["source_commit"]
        or manifest["root_tree_git_object_identity"] != value["source_root_authority"]["root_tree_git_object_identity"]
        or not _is_hex(manifest["source_commit"], 40)
        or not _is_hex(manifest["root_tree_git_object_identity"], 40)
    ):
        _reject()
    members = manifest["members"]
    if not isinstance(members, list) or any(not isinstance(member, dict) or frozenset(member) != _MANIFEST_MEMBER_FIELDS for member in members):
        _reject()
    if (
        entry is None
        or value["request_kind"] != entry[0]
        or manifest["source_closure_identifier"] != entry[3]
        or value["worker_code_closure_identity"] != manifest["source_code_closure_manifest_identity"]
    ):
        _reject()
    manifest_material = dict(manifest)
    claimed_manifest = manifest_material.pop("source_code_closure_manifest_identity")
    if bootstrap_domain_identity("orev3:bounded-streaming-source-code-closure-manifest:v1\n", manifest_material) != claimed_manifest:
        _reject()
    source_root = value["source_root_authority"]["absolute_root"]
    if not isinstance(source_root, str) or not source_root.startswith("/"):
        _reject()
    dependency = value["dependency_root_authority"]
    if dependency == {"present": False}:
        pass
    else:
        _require_exact_fields(dependency, frozenset(("present", "absolute_root", "closed_dependency_root_identity", "closed_dependency_root_material")))
        if dependency["present"] is not True or not _is_hex(dependency["closed_dependency_root_identity"], 64):
            _reject()
    _require_exact_fields(value["runtime_bundle_authority"], _RUNTIME_FIELDS)
    count = value["worker_request_byte_count"]
    payload = value["worker_request_canonical_json"]
    if type(count) is not int or not 1 <= count <= 1_048_576 or not isinstance(payload, str):
        _reject()
    payload_bytes = payload.encode("utf-8", "strict")
    if len(payload_bytes) != count or hashlib.sha256(payload_bytes).hexdigest() != value["worker_request_sha256"]:
        _reject()
    material = dict(value)
    claimed = material.pop("bootstrap_request_identity")
    if bootstrap_domain_identity(BOOTSTRAP_REQUEST_DOMAIN, material) != claimed:
        _reject()
    if bootstrap_canonical_bytes(value)[:-1] != raw:
        _reject()
    return value


def consume_start_gate(descriptor=3):
    try:
        first = os.read(descriptor, 1)
        trailing = os.read(descriptor, 1)
    except OSError:
        _reject()
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
    if first != b"\xa5" or trailing != b"":
        _reject()


def read_authenticated_request_fd(descriptor=6):
    try:
        opened = os.fstat(descriptor)
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or (flags & os.O_ACCMODE) != os.O_RDONLY or os.lseek(descriptor, 0, os.SEEK_CUR) != 0 or opened.st_size < 1 or opened.st_size > MAX_BOUNDED_STREAMING_BOOTSTRAP_REQUEST_BYTES:
            _reject()
        chunks = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                _reject()
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1) or os.lseek(descriptor, 0, os.SEEK_CUR) != opened.st_size:
            _reject()
        closed = os.fstat(descriptor)
        before = (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_uid, opened.st_gid, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        after = (closed.st_dev, closed.st_ino, closed.st_mode, closed.st_uid, closed.st_gid, closed.st_size, closed.st_mtime_ns, closed.st_ctime_ns)
        if before != after:
            _reject()
        return b"".join(chunks)
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def assert_bounded_project_import_session_single_threaded():
    import threading
    import types
    frames = sys._current_frames()
    current = threading.get_ident()
    if not isinstance(frames, dict) or set(frames) != {current} or any(type(key) is not int or not isinstance(frame, types.FrameType) for key, frame in frames.items()):
        raise BoundedProjectImportError(INTEGRITY_FAILURE)


class AuthenticatedBoundedProjectSourceLoader:
    def __init__(self, fullname, source_root, material, session_objects):
        self.fullname = fullname
        self.source_root = source_root
        self.material = material
        self.session_objects = session_objects

    def create_module(self, _spec):
        return None

    def exec_module(self, module):
        relative = self.material["path"]
        try:
            raw = _read_authenticated_source_member(self.source_root, self.material)
        except BoundedBootstrapError as exc:
            raise BoundedProjectImportError(INTEGRITY_FAILURE) from exc
        module.__file__ = os.path.join(self.source_root, relative)
        module.__loader__ = self
        existing = self.session_objects.get(self.fullname)
        if existing is not None and existing is not module:
            raise BoundedProjectImportError(INTEGRITY_FAILURE)
        self.session_objects[self.fullname] = module
        exec(compile(raw, module.__file__, "exec", dont_inherit=True), module.__dict__)


class BoundedProjectMetaPathFinder:
    def __init__(self, source_root, module_map, shells, session_objects):
        self.source_root = source_root
        self.module_map = module_map
        self.shells = shells
        self.session_objects = session_objects

    def find_spec(self, fullname, _path=None, _target=None):
        if fullname in self.shells:
            return None
        if fullname in self.module_map:
            import importlib.util
            loader = AuthenticatedBoundedProjectSourceLoader(fullname, self.source_root, self.module_map[fullname], self.session_objects)
            return importlib.util.spec_from_loader(fullname, loader, origin=self.module_map[fullname]["path"])
        if fullname == "orev3" or fullname.startswith("orev3."):
            raise BoundedProjectImportError(INTEGRITY_FAILURE)
        return None


class BoundedProjectImportSession:
    PRE_MUTATION = "PRE_MUTATION"
    MUTATED = "GLOBAL_INTERPRETER_STATE_MUTATED"

    def __init__(self, source_root, module_map, *, hook_assignment=None):
        self.source_root = source_root
        self.module_map = dict(module_map)
        self.state = self.PRE_MUTATION
        self.hook_assignment = hook_assignment or setattr

    def _terminal(self):
        os._exit(TERMINAL_INTEGRITY_EXIT_STATUS)

    def __enter__(self):
        import _thread
        import threading
        import types
        try:
            assert_bounded_project_import_session_single_threaded()
        except BaseException:
            self._terminal()
        hooks = (
            (threading.Thread, "start"), (threading, "_start_joinable_thread"),
            (_thread, "start_new_thread"), (_thread, "start_new"),
            (_thread, "start_joinable_thread"),
        )
        self.hooks = hooks
        self.original_hooks = tuple(getattr(owner, name) for owner, name in hooks)
        self.denials = []
        for owner, name in hooks:
            def denial(*_args, **_kwargs):
                raise BoundedProjectImportError(INTEGRITY_FAILURE)
            try:
                self.hook_assignment(owner, name, denial)
            except BaseException:
                self._terminal()
            self.state = self.MUTATED
            self.denials.append(denial)
        if any(getattr(owner, name) is not denial for (owner, name), denial in zip(hooks, self.denials)):
            self._terminal()
        try:
            assert_bounded_project_import_session_single_threaded()
        except BaseException:
            self._terminal()
        self.cache = {name: value for name, value in sys.modules.items() if name == "orev3" or name.startswith("orev3.")}
        for name in tuple(self.cache):
            del sys.modules[name]
        self.meta_path = tuple(sys.meta_path)
        self.shell_objects = {}
        for name in SYNTHETIC_PACKAGES:
            shell = types.ModuleType(name)
            shell.__package__ = name
            shell.__path__ = []
            shell.__loader__ = self
            shell.__spec__ = None
            self.shell_objects[name] = shell
            sys.modules[name] = shell
        self.session_objects = dict(self.shell_objects)
        self.finder = BoundedProjectMetaPathFinder(self.source_root, self.module_map, frozenset(SYNTHETIC_PACKAGES), self.session_objects)
        sys.meta_path.insert(0, self.finder)
        return self

    def check(self):
        try:
            assert_bounded_project_import_session_single_threaded()
            if any(getattr(owner, name) is not denial for (owner, name), denial in zip(self.hooks, self.denials)):
                self._terminal()
        except BaseException:
            self._terminal()
        if tuple(sys.meta_path) != (self.finder,) + self.meta_path:
            raise BoundedProjectImportError(INTEGRITY_FAILURE)
        try:
            permitted = set(SYNTHETIC_PACKAGES) | set(self.module_map)
            current = {
                name: value for name, value in sys.modules.items()
                if name == "orev3" or name.startswith("orev3.")
            }
            if any(name not in permitted for name in current):
                raise BoundedProjectImportError(INTEGRITY_FAILURE)
            for name, shell in self.shell_objects.items():
                if current.get(name) is not shell:
                    raise BoundedProjectImportError(INTEGRITY_FAILURE)
            for name, module in current.items():
                if name in self.module_map:
                    known = self.session_objects.get(name)
                    if known is None or known is not module:
                        raise BoundedProjectImportError(INTEGRITY_FAILURE)
        except BoundedProjectImportError:
            raise
        except BaseException as exc:
            raise BoundedProjectImportError(INTEGRITY_FAILURE) from exc

    def __exit__(self, kind, value, traceback):
        integrity_error = None
        try:
            self.check()
        except BoundedProjectImportError as exc:
            integrity_error = exc
        sys.meta_path[:] = self.meta_path
        for name in tuple(sys.modules):
            if name == "orev3" or name.startswith("orev3."):
                del sys.modules[name]
        sys.modules.update(self.cache)
        self.check_after_import_restore()
        for (owner, name), original in zip(self.hooks, self.original_hooks):
            setattr(owner, name, original)
        assert_bounded_project_import_session_single_threaded()
        if integrity_error is not None:
            raise integrity_error
        return False

    def check_after_import_restore(self):
        try:
            assert_bounded_project_import_session_single_threaded()
            if tuple(sys.meta_path) != self.meta_path:
                self._terminal()
            if any(getattr(owner, name) is not denial for (owner, name), denial in zip(self.hooks, self.denials)):
                self._terminal()
            current = {
                name: value for name, value in sys.modules.items()
                if name == "orev3" or name.startswith("orev3.")
            }
            if set(current) != set(self.cache) or any(current[name] is not value for name, value in self.cache.items()):
                self._terminal()
        except BaseException:
            self._terminal()


MAX_RESERVATION_FRAME_BYTES = 294
RESERVATION_UINT64_MAX = 18446744073709551615
RESERVATION_KINDS = (
    "snapshot_growth", "controller_temporary_growth", "worker_output_growth",
    "projection_publication", "reconstruction_growth",
)
RESERVATION_FAILURE_CODES = (
    "RESOURCE_LIMIT_EXCEEDED", "DISK_RESERVATION_PROTOCOL_REJECTED",
    "DISK_RESERVATION_STATE_MISMATCH",
)
_RESERVATION_COMMON = frozenset((
    "schema_version", "message_type", "operation_id", "sequence_number",
))
_RESERVATION_FIELDS = {
    "reserve_growth": _RESERVATION_COMMON | {
        "reservation_kind", "current_logical_bytes", "requested_growth_bytes",
    },
    "reservation_acknowledged": _RESERVATION_COMMON | {
        "accepted_growth_bytes", "resulting_reserved_bytes", "resulting_charged_bytes",
    },
    "reservation_rejected": _RESERVATION_COMMON | {"failure_code"},
}


class ReservationProtocolError(ValueError):
    """Closed diagnostics only; never include received material."""

    def __init__(self, code="DISK_RESERVATION_PROTOCOL_REJECTED"):
        if code not in RESERVATION_FAILURE_CODES:
            code = "DISK_RESERVATION_PROTOCOL_REJECTED"
        self.code = code
        super().__init__(code)


def reservation_uint64(value, *, positive=False):
    if type(value) is not int or not int(positive) <= value <= RESERVATION_UINT64_MAX:
        raise ReservationProtocolError()
    return value


def reservation_operation_id(value):
    if (
        type(value) is not str or len(value) != 35 or not value.startswith("op-")
        or any(character not in "0123456789abcdef" for character in value[3:])
    ):
        raise ReservationProtocolError()
    return value


def _reservation_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReservationProtocolError()
        result[key] = value
    return result


def _reservation_no_number(_value):
    raise ReservationProtocolError()


def reservation_payload(message):
    """Section 9.1 canonical JSON, deliberately WITHOUT the readiness LF."""
    if type(message) is not dict or type(message.get("message_type")) is not str:
        raise ReservationProtocolError()
    kind = message["message_type"]
    if kind not in _RESERVATION_FIELDS or set(message) != _RESERVATION_FIELDS[kind]:
        raise ReservationProtocolError()
    if type(message["schema_version"]) is not int or message["schema_version"] != 1:
        raise ReservationProtocolError()
    reservation_operation_id(message["operation_id"])
    reservation_uint64(message["sequence_number"])
    if kind == "reserve_growth":
        if type(message["reservation_kind"]) is not str or message["reservation_kind"] not in RESERVATION_KINDS:
            raise ReservationProtocolError()
        reservation_uint64(message["current_logical_bytes"])
        reservation_uint64(message["requested_growth_bytes"], positive=True)
    elif kind == "reservation_acknowledged":
        reservation_uint64(message["accepted_growth_bytes"], positive=True)
        reservation_uint64(message["resulting_reserved_bytes"])
        reservation_uint64(message["resulting_charged_bytes"])
    elif type(message["failure_code"]) is not str or message["failure_code"] not in RESERVATION_FAILURE_CODES:
        raise ReservationProtocolError()
    # Every accepted field is now an ASCII enum/identifier or a bounded integer.
    raw = json.dumps(message, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if not 1 <= len(raw) <= MAX_RESERVATION_FRAME_BYTES:
        raise ReservationProtocolError()
    return raw


def parse_reservation_payload(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_RESERVATION_FRAME_BYTES:
        raise ReservationProtocolError()
    try:
        message = json.loads(
            raw.decode("utf-8", "strict"), object_pairs_hook=_reservation_pairs,
            parse_float=_reservation_no_number, parse_constant=_reservation_no_number,
        )
        if reservation_payload(message) != raw:
            raise ReservationProtocolError()
        return message
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise ReservationProtocolError() from None


def reservation_frame(message):
    raw = reservation_payload(message)
    return len(raw).to_bytes(4, "big") + raw


def read_reservation_frame(read, *, allow_orderly_eof=False):
    """Read one bounded frame; the session alone decides if boundary EOF is legal.

    ``read(n)`` must obey socket recv semantics. No socket/FD is opened here.
    A following frame is left for the next session transition, never discarded.
    """
    def exact(size, boundary=False):
        result = bytearray()
        while len(result) < size:
            try:
                chunk = read(size - len(result))
            except InterruptedError:
                continue
            except OSError:
                raise ReservationProtocolError() from None
            if type(chunk) is not bytes or len(chunk) > size - len(result):
                raise ReservationProtocolError()
            if not chunk:
                if boundary and not result and allow_orderly_eof:
                    return None
                raise ReservationProtocolError()
            result.extend(chunk)
        return bytes(result)

    prefix = exact(4, boundary=True)
    if prefix is None:
        return None
    size = int.from_bytes(prefix, "big")
    if not 1 <= size <= MAX_RESERVATION_FRAME_BYTES:
        raise ReservationProtocolError()
    return exact(size)


def parse_reservation_frame(frame):
    """Single-message interface: concatenated frames/trailing bytes reject."""
    if type(frame) is not bytes or len(frame) < 4:
        raise ReservationProtocolError()
    size = int.from_bytes(frame[:4], "big")
    if not 1 <= size <= MAX_RESERVATION_FRAME_BYTES or len(frame) != 4 + size:
        raise ReservationProtocolError()
    return parse_reservation_payload(frame[4:])


class ReservationAllowance:
    """Worker-side matching/single-use core; grants no filesystem authority.

    No writes, observation inputs, ledger setters, or reconnection are provided.
    A consumed allowance describes ONE bounded write, including its short-write
    outcome. Only the controller may reconcile its unused part.
    """

    def __init__(self, operation_id):
        self._operation_id = reservation_operation_id(operation_id)
        self._sequence = 0
        self._request = None
        self._acknowledged = False
        self._terminal = False

    @property
    def terminal(self):
        return self._terminal

    def _reject(self, code="DISK_RESERVATION_PROTOCOL_REJECTED"):
        self._terminal = True
        raise ReservationProtocolError(code)

    def request(self, reservation_kind, current_logical_bytes, requested_growth_bytes):
        if self._terminal or self._request is not None or self._sequence is None:
            self._reject()
        message = {
            "schema_version": 1, "message_type": "reserve_growth",
            "operation_id": self._operation_id, "sequence_number": self._sequence,
            "reservation_kind": reservation_kind,
            "current_logical_bytes": current_logical_bytes,
            "requested_growth_bytes": requested_growth_bytes,
        }
        try:
            payload = reservation_payload(message)
        except ReservationProtocolError:
            self._reject()
        self._request = message
        return payload

    def accept_response(self, payload):
        if self._terminal or self._request is None or self._acknowledged:
            self._reject()
        try:
            response = parse_reservation_payload(payload)
        except ReservationProtocolError:
            self._reject()
        request = self._request
        if any(response[key] != request[key] for key in ("operation_id", "sequence_number")):
            self._reject()
        if response["message_type"] == "reservation_rejected":
            self._reject(response["failure_code"])
        if (
            response["message_type"] != "reservation_acknowledged"
            or response["accepted_growth_bytes"] != request["requested_growth_bytes"]
            or response["resulting_charged_bytes"] < request["current_logical_bytes"]
            or response["resulting_reserved_bytes"] < response["resulting_charged_bytes"]
            or response["resulting_reserved_bytes"] - response["resulting_charged_bytes"] < request["requested_growth_bytes"]
        ):
            self._reject()
        self._acknowledged = True
        self._sequence = None if self._sequence == RESERVATION_UINT64_MAX else self._sequence + 1

    def consume(self, *, operation_id, sequence_number, reservation_kind, growth_bytes):
        if self._terminal or not self._acknowledged or self._request is None:
            self._reject()
        request = self._request
        try:
            reservation_uint64(sequence_number)
            reservation_uint64(growth_bytes, positive=True)
        except ReservationProtocolError:
            self._reject()
        if (
            operation_id != request["operation_id"]
            or sequence_number != request["sequence_number"]
            or reservation_kind != request["reservation_kind"]
            or growth_bytes > request["requested_growth_bytes"]
        ):
            self._reject()
        self._request = None
        self._acknowledged = False
        return growth_bytes

    def controller_eof(self):
        # Even after an ACK, EOF revokes permission for the next write.
        self._reject()


def main():
    if sys.argv != [sys.argv[0], "--governed-fixed-fds-v1"]:
        return 2
    consume_start_gate(3)
    envelope = bootstrap_parse_request_bytes(read_authenticated_request_fd(6))
    entry = BOUNDED_STREAMING_WORKER_DISPATCH[envelope["worker_entrypoint_identifier"]]
    source_root = envelope["source_root_authority"]["absolute_root"]
    sys.path[:] = [os.path.join(source_root, "src")]
    manifest = envelope["source_root_authority"]["source_code_closure_manifest"]
    if entry[4] == "MODEL_B":
        by_path = authenticate_source_code_closure(source_root, manifest, model_b=True)
        module_map = {
            name: by_path[path] for name, path in MODEL_B_MODULE_PATHS
        }
        with BoundedProjectImportSession(source_root, module_map) as session:
            session.check()
            module = __import__(entry[1], fromlist=(entry[2],))
            session.check()
            callable_value = getattr(module, entry[2], None)
            if not callable(callable_value) or getattr(callable_value, "__module__", None) != entry[1]:
                _reject()
            return callable_value()
    by_path = authenticate_source_code_closure(source_root, manifest, closure_identifier=entry[3])
    if entry[0] == "readiness_test" and os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1":
        _reject()
    module = __import__(entry[1], fromlist=(entry[2],))
    assert_model_a_import_origins(source_root, by_path)
    callable_value = getattr(module, entry[2], None)
    if not callable(callable_value) or getattr(callable_value, "__module__", None) != entry[1]:
        _reject()
    return callable_value()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        raise SystemExit(10)
