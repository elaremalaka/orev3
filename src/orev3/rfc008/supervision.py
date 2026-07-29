from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence


SUPERVISION_SCHEMA_VERSION = 1
STARTUP_TIMEOUT_SECONDS = 30.0
STARTUP_POLL_SECONDS = 0.1
SUPERVISION_STATES = {
    "starting",
    "active",
    "completed",
    "failed",
    "interrupted",
}
_SECRET_URL = re.compile(r"https?://[^\s\"']+")


class SupervisionError(RuntimeError):
    pass


class DuplicateSupervisedLaunch(SupervisionError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def supervision_paths(ledger_path: str | Path) -> dict[str, Path]:
    ledger = Path(ledger_path).resolve()
    stem = ledger.stem
    return {
        "metadata": ledger.with_name(f"{stem}.supervision.json"),
        "launch_lock": ledger.with_name(f"{stem}.supervision.lock"),
        "log": ledger.with_name(f"{stem}.collector.log"),
    }


def redact_exception(exc: BaseException) -> str:
    value = _SECRET_URL.sub("<redacted-rpc-url>", str(exc))
    return f"{type(exc).__name__}: {value}"[:2000]


def atomic_write_metadata(path: str | Path, value: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    encoded = (
        json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode()
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        os.write(descriptor, encoded)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def read_metadata(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SupervisionError("RFC-008 supervision metadata is not an object")
    required = {
        "schema_version",
        "launch_identifier",
        "launcher_pid",
        "collector_pid",
        "collector_start_timestamp",
        "collector_process_start_identity",
        "command_identity",
        "log_path",
        "metadata_path",
        "branch",
        "head",
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
        raise SupervisionError(
            "RFC-008 supervision metadata field contract mismatch"
        )
    if value["schema_version"] != SUPERVISION_SCHEMA_VERSION:
        raise SupervisionError("Unsupported RFC-008 supervision schema")
    if value["supervision_state"] not in SUPERVISION_STATES:
        raise SupervisionError("Invalid RFC-008 supervision state")
    if value["target_count"] != 600:
        raise SupervisionError("RFC-008 supervision target mismatch")
    if str(Path(value["metadata_path"]).resolve()) != str(target.resolve()):
        raise SupervisionError("Copied RFC-008 supervision metadata rejected")
    return value


def update_metadata(path: str | Path, **updates: Any) -> dict[str, Any]:
    value = read_metadata(path)
    if value is None:
        raise SupervisionError("RFC-008 supervision metadata is missing")
    unknown = set(updates) - set(value)
    if unknown:
        raise SupervisionError(
            f"Unknown RFC-008 supervision fields: {sorted(unknown)}"
        )
    value.update(updates)
    value["last_observed_status_timestamp"] = utc_now()
    atomic_write_metadata(path, value)
    return value


def process_snapshot(pid: int | None) -> dict[str, Any]:
    if not pid or pid <= 0:
        return {
            "pid": pid,
            "alive": False,
            "start_identity": None,
            "command": None,
        }
    try:
        result = subprocess.run(
            ("ps", "-p", str(pid), "-o", "lstart=", "-o", "command="),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return {
            "pid": pid,
            "alive": False,
            "start_identity": None,
            "command": None,
        }
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return {
            "pid": pid,
            "alive": False,
            "start_identity": None,
            "command": None,
        }
    fields = output.split(None, 5)
    first = " ".join(fields[:5])
    command = fields[5] if len(fields) == 6 else ""
    identity = hashlib.sha256(
        f"{pid}\0{first.strip()}\0{command.strip()}".encode()
    ).hexdigest()
    return {
        "pid": pid,
        "alive": True,
        "start_identity": identity,
        "command": command.strip(),
    }


def process_matches_metadata(metadata: dict[str, Any]) -> bool:
    snapshot = process_snapshot(metadata.get("collector_pid"))
    return bool(
        snapshot["alive"]
        and snapshot["start_identity"]
        == metadata.get("collector_process_start_identity")
        and "-m orev3.rfc008.cli run" in str(snapshot["command"])
    )


def writer_lease_status(ledger_path: str | Path) -> dict[str, Any]:
    path = Path(str(Path(ledger_path).resolve()) + ".writer.lock")
    recorded_pid: int | None = None
    if path.exists():
        try:
            recorded_pid = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            recorded_pid = None
    active = False
    descriptor: int | None = None
    if path.exists():
        descriptor = os.open(path, os.O_RDONLY)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                active = True
            else:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
    return {
        "path": str(path),
        "file_present": path.exists(),
        "recorded_process_id": recorded_pid,
        "active": active,
        "recorded_process_alive": process_snapshot(recorded_pid)["alive"],
    }


@contextmanager
def launch_mutex(ledger_path: str | Path) -> Iterator[None]:
    path = supervision_paths(ledger_path)["launch_lock"]
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
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


def controlled_environment() -> dict[str, str]:
    allowed = {
        "PATH",
        "PYTHONPATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "ORE_RECOVERY_PRIMARY_RPC_URL",
        "ORE_RECOVERY_SECONDARY_RPC_URL",
    }
    value = {key: item for key, item in os.environ.items() if key in allowed}
    value["PYTHONUNBUFFERED"] = "1"
    return value


def spawn_detached(
    command: Sequence[str],
    *,
    cwd: str | Path,
    log_path: str | Path,
    environment: dict[str, str] | None = None,
) -> subprocess.Popen[bytes]:
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(log, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        return subprocess.Popen(
            tuple(command),
            cwd=Path(cwd),
            env=environment or controlled_environment(),
            stdin=subprocess.DEVNULL,
            stdout=descriptor,
            stderr=descriptor,
            close_fds=True,
            start_new_session=True,
        )
    finally:
        os.close(descriptor)


def wait_for_process_identity(
    pid: int,
    *,
    timeout: float = 2.0,
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
            result.append(_SECRET_URL.sub("<redacted-rpc-url>", str(item)))
    return result


def python_command() -> str:
    return str(Path(sys.executable).resolve())
