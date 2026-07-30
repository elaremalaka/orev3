from __future__ import annotations

import ctypes
import ctypes.util
import fcntl
import hashlib
import io
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Iterator
from typing import Sequence
from urllib.parse import parse_qsl
from urllib.parse import quote
from urllib.parse import quote_plus
from urllib.parse import unquote
from urllib.parse import urlsplit


SUPERVISION_SCHEMA_VERSION = 2
STARTUP_TIMEOUT_SECONDS = 30.0
STARTUP_POLL_SECONDS = 0.1
SUPERVISION_STATES = {
    "starting",
    "active",
    "completed",
    "failed",
    "interrupted",
}
INTERNAL_CHILD_COMMAND = "_supervised-child"
_HEX_40 = re.compile(r"^[0-9a-f]{40}$")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_URL = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_CREDENTIAL = re.compile(
    r"(?i)\b(api[-_]?key|token|secret|password|authorization)"
    r"\s*[:=]\s*[^\s,;]+"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ENVIRONMENT_NAME = re.compile(
    r"(?i)(?:api[-_]?key|token|secret|password|authorization|rpc[-_]?url)"
)
_CREDENTIAL_PATH_HINT = re.compile(
    r"(?i)(?:api[-_]?key|token|secret|password|credential|auth)"
)
_API_KEY_SHAPE = re.compile(r"^[A-Za-z0-9._~+/=-]{12,}$")
_MINIMUM_SECRET_LENGTH = 6


class SupervisionError(RuntimeError):
    pass


class DuplicateSupervisedLaunch(SupervisionError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strict_json(raw: str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise SupervisionError(
                    f"Duplicate RFC-008 supervision field: {key}"
                )
            value[key] = item
        return value

    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SupervisionError("Malformed RFC-008 supervision metadata") from exc


def _is_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _is_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _safe_parent(path: Path) -> Path:
    parent = path.parent
    try:
        parent_stat = os.lstat(parent)
    except OSError as exc:
        raise SupervisionError(
            "RFC-008 runtime directory is unavailable"
        ) from exc
    if stat.S_ISLNK(parent_stat.st_mode) or not stat.S_ISDIR(
        parent_stat.st_mode
    ):
        raise SupervisionError("Unsafe RFC-008 runtime directory")
    if parent.resolve() != parent.absolute():
        raise SupervisionError("Symlinked RFC-008 runtime directory rejected")
    return parent


def _validate_existing_regular(path: Path) -> None:
    try:
        value = os.lstat(path)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(value.st_mode) or not stat.S_ISREG(value.st_mode):
        raise SupervisionError(f"Unsafe RFC-008 runtime object: {path.name}")
    if value.st_nlink != 1:
        raise SupervisionError(f"Hard-linked RFC-008 runtime file rejected: {path.name}")


def supervision_paths(ledger_path: str | Path) -> dict[str, Path]:
    ledger_input = Path(ledger_path)
    ledger = ledger_input.resolve()
    if ledger_input.exists() and ledger_input.absolute() != ledger:
        raise SupervisionError("Symlinked RFC-008 ledger path rejected")
    stem = ledger.stem
    return {
        "metadata": ledger.with_name(f"{stem}.supervision.json"),
        "launch_lock": ledger.with_name(f"{stem}.supervision.lock"),
        "log": ledger.with_name(f"{stem}.collector.log"),
    }


def _usable_secret(value: str, *, credential_context: bool = False) -> bool:
    if len(value) < _MINIMUM_SECRET_LENGTH or value.isdigit():
        return False
    if credential_context:
        return True
    return bool(
        _CREDENTIAL_PATH_HINT.search(value)
        or (
            _API_KEY_SHAPE.fullmatch(value)
            and any(character.isalpha() for character in value)
            and any(
                not character.isalpha()
                for character in value
            )
        )
    )


def _secret_forms(value: str) -> set[str]:
    decoded = unquote(value)
    candidates = {
        value,
        decoded,
        quote(decoded, safe=""),
        quote_plus(decoded, safe=""),
    }
    return {
        item
        for item in candidates
        if _usable_secret(item, credential_context=True)
    }


def provider_secret_values(
    provider_urls: Sequence[str],
    *,
    secret_environment: dict[str, str] | None = None,
) -> tuple[str, ...]:
    """Derive redaction-only values without retaining provider URLs."""
    secrets: set[str] = set()
    for raw_url in provider_urls:
        if not raw_url:
            continue
        secrets.update(_secret_forms(raw_url))
        try:
            parsed = urlsplit(raw_url)
        except ValueError:
            continue
        for value in (parsed.username, parsed.password):
            if value:
                secrets.update(_secret_forms(value))
        for _, value in parse_qsl(parsed.query, keep_blank_values=True):
            if _usable_secret(value, credential_context=True):
                secrets.update(_secret_forms(value))
        for component in parsed.path.split("/"):
            decoded = unquote(component)
            if _usable_secret(decoded):
                secrets.update(_secret_forms(component))
                secrets.update(_secret_forms(decoded))
    for name, value in (secret_environment or {}).items():
        if value and _SECRET_ENVIRONMENT_NAME.search(name):
            secrets.update(_secret_forms(value))
    return tuple(sorted(secrets, key=lambda item: (-len(item), item)))


def configured_secret_values(
    environment: dict[str, str] | None = None,
) -> tuple[str, ...]:
    values = environment if environment is not None else dict(os.environ)
    provider_urls = tuple(
        values.get(name, "")
        for name in (
            "ORE_RECOVERY_PRIMARY_RPC_URL",
            "ORE_RECOVERY_SECONDARY_RPC_URL",
        )
    )
    secret_environment = {
        name: value
        for name, value in values.items()
        if _SECRET_ENVIRONMENT_NAME.search(name)
    }
    return provider_secret_values(
        provider_urls,
        secret_environment=secret_environment,
    )


def sanitize_text(value: object, *, known_secrets: Sequence[str] = ()) -> str:
    result = str(value)
    for secret in sorted(
        (item for item in known_secrets if item), key=len, reverse=True
    ):
        result = result.replace(secret, "<redacted-secret>")
    result = _URL.sub("<redacted-url>", result)
    result = _BEARER.sub("Bearer <redacted>", result)
    result = _CREDENTIAL.sub(lambda match: f"{match.group(1)}=<redacted>", result)
    return result


def redact_exception(
    exc: BaseException, *, known_secrets: Sequence[str] = ()
) -> str:
    return sanitize_text(
        f"{type(exc).__name__}: {exc}", known_secrets=known_secrets
    )[:2000]


class SanitizingTextIO(io.TextIOBase):
    def __init__(self, descriptor: int, *, known_secrets: Sequence[str] = ()):
        self._stream = os.fdopen(
            os.dup(descriptor),
            "w",
            buffering=1,
            encoding="utf-8",
            errors="replace",
        )
        self._known_secrets = tuple(known_secrets)

    @property
    def encoding(self) -> str:
        return "utf-8"

    def writable(self) -> bool:
        return True

    def write(self, value: str) -> int:
        safe = sanitize_text(value, known_secrets=self._known_secrets)
        self._stream.write(safe)
        self._stream.flush()
        return len(value)

    def flush(self) -> None:
        self._stream.flush()


def install_sanitized_streams(
    descriptor: int, *, known_secrets: Sequence[str] = ()
) -> None:
    sys.stdout = SanitizingTextIO(descriptor, known_secrets=known_secrets)
    sys.stderr = SanitizingTextIO(descriptor, known_secrets=known_secrets)


def safe_open_log(path: str | Path) -> tuple[int, os.stat_result]:
    target = Path(path).absolute()
    _safe_parent(target)
    _validate_existing_regular(target)
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags, 0o600)
    except OSError as exc:
        raise SupervisionError("RFC-008 collector log open rejected") from exc
    try:
        value = os.fstat(descriptor)
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            raise SupervisionError("RFC-008 collector log is not a safe file")
        os.fchmod(descriptor, 0o600)
        if os.lstat(target).st_ino != value.st_ino:
            raise SupervisionError("RFC-008 collector log replacement detected")
        return descriptor, value
    except Exception:
        os.close(descriptor)
        raise


def atomic_write_metadata(path: str | Path, value: dict[str, Any]) -> None:
    target = Path(path).absolute()
    parent = _safe_parent(target)
    _validate_existing_regular(target)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    encoded = (
        json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode()
    descriptor: int | None = None
    try:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600)
        os.write(descriptor, encoded)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, target)
        directory = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _validate_metadata(value: dict[str, Any], target: Path) -> None:
    required = {
        "schema_version",
        "launch_identifier",
        "launch_authority_sha256",
        "launch_authority_consumed_at",
        "launcher_pid",
        "collector_pid",
        "collector_start_timestamp",
        "collector_process_start_identity",
        "command_identity",
        "log_path",
        "log_device",
        "log_inode",
        "metadata_path",
        "branch",
        "head",
        "cli_sha256",
        "authorization_identifier",
        "authorization_digest",
        "ledger_instance_identifier",
        "ledger_path",
        "session_identity",
        "target_count",
        "supervision_state",
        "last_observed_status_timestamp",
        "exit_code",
        "failure_reason",
        "stale_recovery",
    }
    if set(value) != required:
        raise SupervisionError("RFC-008 supervision metadata field contract mismatch")
    if type(value["schema_version"]) is not int or value[
        "schema_version"
    ] != SUPERVISION_SCHEMA_VERSION:
        raise SupervisionError("Unsupported RFC-008 supervision schema")
    if not _is_uuid(value["launch_identifier"]):
        raise SupervisionError("Invalid RFC-008 launch identifier")
    for name in ("launch_authority_sha256", "head", "cli_sha256", "authorization_digest"):
        pattern = _HEX_40 if name == "head" else _HEX_64
        if not isinstance(value[name], str) or not pattern.fullmatch(value[name]):
            raise SupervisionError(f"Invalid RFC-008 supervision {name}")
    if value["launch_authority_consumed_at"] is not None and not _is_timestamp(
        value["launch_authority_consumed_at"]
    ):
        raise SupervisionError("Invalid launch-authority timestamp")
    for name in ("launcher_pid",):
        if type(value[name]) is not int or value[name] <= 0:
            raise SupervisionError(f"Invalid RFC-008 supervision {name}")
    if value["collector_pid"] is not None and (
        type(value["collector_pid"]) is not int or value["collector_pid"] <= 0
    ):
        raise SupervisionError("Invalid RFC-008 collector PID")
    if value["collector_start_timestamp"] is not None and not _is_timestamp(
        value["collector_start_timestamp"]
    ):
        raise SupervisionError("Invalid collector-start timestamp")
    if value["collector_process_start_identity"] is not None and (
        not isinstance(value["collector_process_start_identity"], str)
        or not _HEX_64.fullmatch(value["collector_process_start_identity"])
    ):
        raise SupervisionError("Invalid collector process-start identity")
    if (
        not isinstance(value["command_identity"], list)
        or not value["command_identity"]
        or any(not isinstance(item, str) for item in value["command_identity"])
        or INTERNAL_CHILD_COMMAND not in value["command_identity"]
    ):
        raise SupervisionError("Invalid RFC-008 child command identity")
    if type(value["target_count"]) is not int or value["target_count"] != 600:
        raise SupervisionError("RFC-008 supervision target mismatch")
    if value["supervision_state"] not in SUPERVISION_STATES:
        raise SupervisionError("Invalid RFC-008 supervision state")
    if not _is_timestamp(value["last_observed_status_timestamp"]):
        raise SupervisionError("Invalid supervision status timestamp")
    for name in ("log_device", "log_inode"):
        if type(value[name]) is not int or value[name] <= 0:
            raise SupervisionError(f"Invalid RFC-008 supervision {name}")
    if value["exit_code"] is not None and type(value["exit_code"]) is not int:
        raise SupervisionError("Invalid RFC-008 supervision exit code")
    if value["failure_reason"] is not None and not isinstance(
        value["failure_reason"], str
    ):
        raise SupervisionError("Invalid RFC-008 supervision failure reason")
    if value["stale_recovery"] is not None and not isinstance(
        value["stale_recovery"], dict
    ):
        raise SupervisionError("Invalid RFC-008 stale-recovery value")
    for name in ("branch", "authorization_identifier", "ledger_instance_identifier"):
        if not isinstance(value[name], str) or not value[name]:
            raise SupervisionError(f"Invalid RFC-008 supervision {name}")
    if value["session_identity"] is not None and not isinstance(
        value["session_identity"], str
    ):
        raise SupervisionError("Invalid RFC-008 session identity")
    ledger = Path(value["ledger_path"]).absolute()
    expected = supervision_paths(ledger)
    if Path(value["metadata_path"]).absolute() != target:
        raise SupervisionError("Copied RFC-008 supervision metadata rejected")
    if Path(value["log_path"]).absolute() != expected["log"]:
        raise SupervisionError("RFC-008 supervision log path mismatch")
    if target != expected["metadata"]:
        raise SupervisionError("RFC-008 supervision metadata path mismatch")


def read_metadata(path: str | Path) -> dict[str, Any] | None:
    target = Path(path).absolute()
    if not target.exists():
        return None
    _safe_parent(target)
    _validate_existing_regular(target)
    try:
        raw = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SupervisionError("RFC-008 supervision metadata is unreadable") from exc
    value = _strict_json(raw)
    if not isinstance(value, dict):
        raise SupervisionError("RFC-008 supervision metadata is not an object")
    _validate_metadata(value, target)
    return value


_TRANSITIONS = {
    "starting": {"starting", "active", "completed", "failed", "interrupted"},
    "active": {"active", "completed", "failed", "interrupted"},
    "completed": {"completed"},
    "failed": {"failed"},
    "interrupted": {"interrupted", "starting"},
}


def update_metadata(path: str | Path, **updates: Any) -> dict[str, Any]:
    value = read_metadata(path)
    if value is None:
        raise SupervisionError("RFC-008 supervision metadata is missing")
    unknown = set(updates) - set(value)
    if unknown:
        raise SupervisionError(f"Unknown RFC-008 supervision fields: {sorted(unknown)}")
    prior_state = value["supervision_state"]
    next_state = updates.get("supervision_state", prior_state)
    if next_state not in _TRANSITIONS[prior_state]:
        raise SupervisionError(
            f"Invalid RFC-008 supervision transition: {prior_state}->{next_state}"
        )
    value.update(updates)
    value["last_observed_status_timestamp"] = utc_now()
    _validate_metadata(value, Path(path).absolute())
    atomic_write_metadata(path, value)
    return value


class _DarwinProcessInfo(ctypes.Structure):
    _fields_ = [
        ("pbi_flags", ctypes.c_uint32),
        ("pbi_status", ctypes.c_uint32),
        ("pbi_xstatus", ctypes.c_uint32),
        ("pbi_pid", ctypes.c_uint32),
        ("pbi_ppid", ctypes.c_uint32),
        ("pbi_uid", ctypes.c_uint32),
        ("pbi_gid", ctypes.c_uint32),
        ("pbi_ruid", ctypes.c_uint32),
        ("pbi_rgid", ctypes.c_uint32),
        ("pbi_svuid", ctypes.c_uint32),
        ("pbi_svgid", ctypes.c_uint32),
        ("pbi_rfu_1", ctypes.c_uint32),
        ("pbi_comm", ctypes.c_char * 16),
        ("pbi_name", ctypes.c_char * 32),
        ("pbi_nfiles", ctypes.c_uint32),
        ("pbi_pgid", ctypes.c_uint32),
        ("pbi_pjobc", ctypes.c_uint32),
        ("e_tdev", ctypes.c_uint32),
        ("e_tpgid", ctypes.c_uint32),
        ("pbi_nice", ctypes.c_int32),
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    ]


_PROC_PIDTBSDINFO = 3
_CTL_KERN = 1
_KERN_PROCARGS2 = 49


def _darwin_process_details(pid: int) -> tuple[str, tuple[str, ...]] | None:
    library_name = ctypes.util.find_library("proc")
    if library_name is None:
        return None
    library = ctypes.CDLL(library_name, use_errno=True)
    library.proc_pidinfo.argtypes = (
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    )
    library.proc_pidinfo.restype = ctypes.c_int
    info = _DarwinProcessInfo()
    if library.proc_pidinfo(
        pid,
        _PROC_PIDTBSDINFO,
        0,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ) != ctypes.sizeof(info):
        return None

    libc = ctypes.CDLL(None, use_errno=True)
    libc.sysctl.argtypes = (
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_void_p,
        ctypes.c_size_t,
    )
    libc.sysctl.restype = ctypes.c_int
    mib = (ctypes.c_int * 3)(_CTL_KERN, _KERN_PROCARGS2, pid)
    size = ctypes.c_size_t()
    if libc.sysctl(mib, 3, None, ctypes.byref(size), None, 0) != 0:
        return None
    arguments_buffer = ctypes.create_string_buffer(size.value)
    if (
        libc.sysctl(
            mib,
            3,
            arguments_buffer,
            ctypes.byref(size),
            None,
            0,
        )
        != 0
    ):
        return None
    raw = arguments_buffer.raw[: size.value]
    integer_size = ctypes.sizeof(ctypes.c_int)
    if len(raw) < integer_size:
        return None
    argument_count = int.from_bytes(
        raw[:integer_size], byteorder=sys.byteorder, signed=True
    )
    if argument_count <= 0:
        return None
    offset = integer_size
    executable_end = raw.find(b"\0", offset)
    if executable_end < 0:
        return None
    offset = executable_end
    while offset < len(raw) and raw[offset] == 0:
        offset += 1
    arguments: list[str] = []
    for _ in range(argument_count):
        end = raw.find(b"\0", offset)
        if end < 0:
            return None
        arguments.append(os.fsdecode(raw[offset:end]))
        offset = end + 1
    start = f"{info.pbi_start_tvsec}:{info.pbi_start_tvusec}"
    return start, tuple(arguments)


def _linux_process_details(pid: int) -> tuple[str, tuple[str, ...]] | None:
    process = Path("/proc") / str(pid)
    stat_value = (process / "stat").read_text(encoding="utf-8")
    command_end = stat_value.rfind(")")
    if command_end < 0:
        return None
    fields = stat_value[command_end + 2 :].split()
    if len(fields) <= 19:
        return None
    start = fields[19]
    raw_arguments = (process / "cmdline").read_bytes().rstrip(b"\0")
    arguments = tuple(
        os.fsdecode(value)
        for value in raw_arguments.split(b"\0")
        if value
    )
    if not arguments:
        return None
    return start, arguments


def _native_process_details(
    pid: int,
) -> tuple[str, tuple[str, ...]] | None:
    try:
        if sys.platform == "darwin":
            return _darwin_process_details(pid)
        if sys.platform.startswith("linux"):
            return _linux_process_details(pid)
    except (OSError, UnicodeError, ValueError):
        return None
    return None


def process_snapshot(pid: int | None) -> dict[str, Any]:
    if not pid or pid <= 0:
        return {"pid": pid, "alive": False, "start_identity": None, "command": None}
    details = _native_process_details(pid)
    if details is None:
        return {"pid": pid, "alive": False, "start_identity": None, "command": None}
    start, arguments = details
    identity = hashlib.sha256(f"{pid}\0{start}".encode()).hexdigest()
    return {
        "pid": pid,
        "alive": True,
        "start_identity": identity,
        "command": shlex.join(arguments[1:]),
    }


def process_matches_metadata(metadata: dict[str, Any]) -> bool:
    snapshot = process_snapshot(metadata.get("collector_pid"))
    return bool(
        snapshot["alive"]
        and snapshot["start_identity"]
        == metadata.get("collector_process_start_identity")
        and f"-m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}"
        in str(snapshot["command"])
    )


def writer_lease_status(ledger_path: str | Path) -> dict[str, Any]:
    """Passively inspect the recorded owner; never acquire the advisory lock."""
    path = Path(str(Path(ledger_path).resolve()) + ".writer.lock")
    recorded_pid: int | None = None
    observation = "absent"
    if path.exists():
        observation = "unknown"
        try:
            value = os.lstat(path)
            if stat.S_ISREG(value.st_mode) and value.st_nlink == 1:
                raw = path.read_text(encoding="utf-8").strip()
                recorded_pid = int(raw)
        except (OSError, ValueError):
            recorded_pid = None
    process = process_snapshot(recorded_pid)
    if recorded_pid is not None:
        observation = "active_recorded_owner" if process["alive"] else "inactive_stale"
    return {
        "path": str(path),
        "file_present": path.exists(),
        "recorded_process_id": recorded_pid,
        "active": bool(process["alive"]),
        "observation": observation,
        "recorded_process_alive": process["alive"],
        "recorded_process_start_identity": process["start_identity"],
    }


@contextmanager
def launch_mutex(ledger_path: str | Path) -> Iterator[None]:
    path = supervision_paths(ledger_path)["launch_lock"]
    _safe_parent(path)
    _validate_existing_regular(path)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        value = os.fstat(descriptor)
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            raise SupervisionError("Unsafe RFC-008 launch mutex")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DuplicateSupervisedLaunch(
                "Another RFC-008 supervised launch is in progress"
            ) from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def controlled_environment(repository_root: str | Path) -> dict[str, str]:
    root = Path(repository_root).resolve()
    allowed = {
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "ORE_RECOVERY_PRIMARY_RPC_URL",
        "ORE_RECOVERY_SECONDARY_RPC_URL",
    }
    value = {key: item for key, item in os.environ.items() if key in allowed}
    value["PYTHONPATH"] = str(root / "src")
    value["PYTHONUNBUFFERED"] = "1"
    value.pop("PYTHONHOME", None)
    return value


def approved_python_command(repository_root: str | Path) -> str:
    root = Path(repository_root).resolve()
    expected = root / ".venv/bin/python"
    if not expected.exists() or not os.access(expected, os.X_OK):
        raise SupervisionError("Approved RFC-008 Python interpreter is unavailable")
    if Path(sys.prefix).resolve() != (root / ".venv").resolve():
        raise SupervisionError(
            "RFC-008 start must run under the repository-approved virtual environment"
        )
    if Path(sys.executable).absolute() != expected.absolute():
        raise SupervisionError("Alternate RFC-008 Python interpreter rejected")
    return str(expected.absolute())


def validate_import_identity(
    repository_root: str | Path, *, expected_cli_sha256: str
) -> None:
    import orev3
    import orev3.rfc008.cli

    root = Path(repository_root).resolve()
    package = Path(orev3.__file__).resolve()
    cli = Path(orev3.rfc008.cli.__file__).resolve()
    if package != root / "src/orev3/__init__.py":
        raise SupervisionError("RFC-008 package origin mismatch")
    if cli != root / "src/orev3/rfc008/cli.py":
        raise SupervisionError("RFC-008 CLI origin mismatch")
    if hashlib.sha256(cli.read_bytes()).hexdigest() != expected_cli_sha256:
        raise SupervisionError("RFC-008 CLI hash mismatch")


def create_child_authority() -> tuple[int, str]:
    read_fd, write_fd = os.pipe()
    token = os.urandom(32)
    os.write(write_fd, token)
    os.close(write_fd)
    return read_fd, hashlib.sha256(token).hexdigest()


def consume_child_authority(
    descriptor: int, *, expected_sha256: str
) -> None:
    try:
        token = os.read(descriptor, 33)
    finally:
        os.close(descriptor)
    if len(token) != 32 or hashlib.sha256(token).hexdigest() != expected_sha256:
        raise SupervisionError("RFC-008 internal child authority rejected")


def spawn_detached(
    command: Sequence[str],
    *,
    cwd: str | Path,
    log_descriptor: int,
    authority_descriptor: int,
    environment: dict[str, str],
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        tuple(command),
        cwd=Path(cwd),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        pass_fds=(log_descriptor, authority_descriptor),
        start_new_session=True,
    )


def terminate_unestablished_child(
    child: subprocess.Popen[bytes],
    expected_identity: str | None,
) -> None:
    del expected_identity
    if child.poll() is not None:
        child.wait(timeout=1)
        return
    # An unreaped Popen with poll() == None still identifies the exact child;
    # POSIX cannot reuse that PID before the child exits and is reaped.
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if child.poll() is None:
            child.kill()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            if child.poll() is not None:
                child.wait(timeout=1)
                return
            raise SupervisionError(
                "RFC-008 unestablished child could not be reaped"
            ) from exc


def wait_for_process_identity(
    pid: int, *, timeout: float = 2.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = process_snapshot(pid)
        if snapshot["alive"] and snapshot["start_identity"]:
            return snapshot
        time.sleep(0.02)
    raise SupervisionError("RFC-008 child process identity was not observable")


def command_identity(command: Sequence[str]) -> list[str]:
    result: list[str] = []
    hide_next = False
    for item in command:
        if hide_next:
            result.append("<redacted>")
            hide_next = False
            continue
        if item in {
            "--rpc-url",
            "--primary-rpc-url",
            "--secondary-rpc-url",
        }:
            result.append(item)
            hide_next = True
        else:
            result.append(sanitize_text(item))
    return result
