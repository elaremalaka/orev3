from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import orev3.rfc008.cli as cli
from orev3.rfc008.cli import parser
from orev3.rfc008.supervision import (
    INTERNAL_CHILD_COMMAND,
    DuplicateSupervisedLaunch,
    SupervisionError,
    atomic_write_metadata,
    command_identity,
    controlled_environment,
    launch_mutex,
    process_matches_metadata,
    read_metadata,
    redact_exception,
    safe_open_log,
    spawn_detached,
    supervision_paths,
    update_metadata,
    writer_lease_status,
)
from orev3.rfc008.writer import RFC008WriterLease


def metadata_for(tmp_path: Path) -> dict[str, object]:
    path = supervision_paths(tmp_path / "ledger.sqlite")["metadata"]
    log = supervision_paths(tmp_path / "ledger.sqlite")["log"]
    log.touch(mode=0o600)
    log_stat = log.stat()
    return {
        "schema_version": 2,
        "launch_identifier": "10000000-0000-4000-8000-000000000001",
        "launch_authority_sha256": "c" * 64,
        "launch_authority_consumed_at": None,
        "launcher_pid": 1,
        "collector_pid": None,
        "collector_start_timestamp": None,
        "collector_process_start_identity": None,
        "command_identity": [
            "python",
            "-m",
            "orev3.rfc008.cli",
            INTERNAL_CHILD_COMMAND,
        ],
        "log_path": str(log),
        "log_device": log_stat.st_dev,
        "log_inode": log_stat.st_ino,
        "metadata_path": str(path),
        "branch": "research/rfc-007-paper-collection-burn-in",
        "head": "a" * 40,
        "cli_sha256": "d" * 64,
        "authorization_identifier": "authorization-id",
        "authorization_digest": "b" * 64,
        "ledger_instance_identifier": "ledger-id",
        "ledger_path": str((tmp_path / "ledger.sqlite").resolve()),
        "session_identity": None,
        "target_count": 600,
        "supervision_state": "starting",
        "last_observed_status_timestamp": "2026-07-29T00:00:00+00:00",
        "exit_code": None,
        "failure_reason": None,
        "stale_recovery": None,
    }


def start_args(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        repository_root=tmp_path,
        config="config",
        resolver_config="resolver",
        burn_in_evidence="burn",
        release_approval="release",
        approval_manifest="approval",
        marker="marker",
        authorization="authorization",
        ledger=tmp_path / "ledger.sqlite",
        recovery=False,
        expected_marker_sha256="b" * 64,
        expected_marker_sha256_file=None,
        startup_timeout_seconds=0.02,
    )


def initialized_start_state() -> dict[str, object]:
    return {
        "authorization": SimpleNamespace(
            lifecycle_state="initialized",
            consuming_session_identity=None,
            record=SimpleNamespace(
                authorization_identifier="authorization",
                authorization_digest="a" * 64,
            ),
        ),
        "contract": SimpleNamespace(
            collection_state="initialized",
            completed=False,
            active_session_identity=None,
            ledger_instance_identifier="ledger-instance",
            collection_target=600,
        ),
        "open_runs": [],
        "matching_run": None,
    }


def mock_start_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "validate_collection_preflight",
        lambda **kwargs: SimpleNamespace(
            ready=True,
            gate_reasons=[],
            active_release_validation=SimpleNamespace(
                parsed_active_approval={"cli_sha256": "d" * 64}
            ),
        ),
    )
    monkeypatch.setattr(
        cli,
        "_git_branch_and_head",
        lambda root: ("research/rfc-007-paper-collection-burn-in", "a" * 40),
    )
    monkeypatch.setattr(cli, "validate_import_identity", lambda *a, **k: None)
    monkeypatch.setattr(cli, "approved_python_command", lambda root: sys.executable)
    monkeypatch.setattr(
        cli,
        "validate_active_release",
        lambda **kwargs: SimpleNamespace(valid=True),
    )
    monkeypatch.setattr(
        cli,
        "_active_authorization_release_mismatches",
        lambda *args, **kwargs: (),
    )


def test_supervision_paths_are_deterministic_and_ledger_local(
    tmp_path: Path,
) -> None:
    paths = supervision_paths(tmp_path / "paper.sqlite")
    assert paths["metadata"].name == "paper.supervision.json"
    assert paths["launch_lock"].name == "paper.supervision.lock"
    assert paths["log"].name == "paper.collector.log"
    assert len({path.parent for path in paths.values()}) == 1


def test_metadata_is_atomic_strict_and_copy_rejected(tmp_path: Path) -> None:
    value = metadata_for(tmp_path)
    path = Path(value["metadata_path"])
    atomic_write_metadata(path, value)
    assert read_metadata(path) == value
    updated = update_metadata(
        path,
        supervision_state="active",
        collector_pid=123,
        session_identity="session",
    )
    assert updated["supervision_state"] == "active"
    assert updated["collector_pid"] == 123
    copied = tmp_path / "copied.supervision.json"
    copied.write_bytes(path.read_bytes())
    with pytest.raises(SupervisionError, match="Copied"):
        read_metadata(copied)
    raw = json.loads(path.read_text())
    raw["unknown"] = True
    path.write_text(json.dumps(raw))
    with pytest.raises(SupervisionError, match="field contract"):
        read_metadata(path)


def test_metadata_rejects_invalid_state_and_target(tmp_path: Path) -> None:
    value = metadata_for(tmp_path)
    path = Path(value["metadata_path"])
    value["supervision_state"] = "restarting"
    atomic_write_metadata(path, value)
    with pytest.raises(SupervisionError, match="state"):
        read_metadata(path)
    value["supervision_state"] = "starting"
    value["target_count"] = 601
    atomic_write_metadata(path, value)
    with pytest.raises(SupervisionError, match="target"):
        read_metadata(path)


def test_secret_values_are_not_serialized_in_identity_or_errors() -> None:
    secret = "https://provider.example/rpc?api-key=do-not-print"
    identity = command_identity(["python", "--rpc-url", secret])
    assert secret not in json.dumps(identity)
    assert identity[-1] == "<redacted>"
    message = redact_exception(RuntimeError(f"request failed at {secret}"))
    assert secret not in message
    assert "<redacted-url>" in message


def test_controlled_environment_is_an_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNRELATED_SECRET", "do-not-inherit")
    monkeypatch.setenv("ORE_RECOVERY_PRIMARY_RPC_URL", "primary-secret")
    value = controlled_environment(Path.cwd())
    assert "UNRELATED_SECRET" not in value
    assert value["ORE_RECOVERY_PRIMARY_RPC_URL"] == "primary-secret"
    assert value["PYTHONUNBUFFERED"] == "1"
    assert value["PYTHONPATH"] == str(Path.cwd() / "src")
    assert "PYTHONHOME" not in value


def test_detached_child_survives_spawn_return_and_logs(tmp_path: Path) -> None:
    ready = tmp_path / "ready"
    log_descriptor, _ = safe_open_log(tmp_path / "child.log")
    authority_read, authority_write = os.pipe()
    os.write(authority_write, b"x")
    os.close(authority_write)
    child = spawn_detached(
        (
            sys.executable,
            "-c",
            f"import pathlib,time; pathlib.Path({str(ready)!r}).touch(); time.sleep(5)",
        ),
        cwd=tmp_path,
        log_descriptor=log_descriptor,
        authority_descriptor=authority_read,
        environment=dict(os.environ),
    )
    os.close(log_descriptor)
    os.close(authority_read)
    try:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not ready.exists():
            time.sleep(0.02)
        assert child.poll() is None
        assert ready.exists()
    finally:
        child.terminate()
        child.wait(timeout=5)


def test_writer_lease_status_distinguishes_stale_and_active(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger.sqlite"
    stale = Path(str(ledger) + ".writer.lock")
    stale.write_text("999999\n")
    assert not writer_lease_status(ledger)["active"]
    with RFC008WriterLease(ledger):
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "orev3.rfc008.supervision.process_snapshot",
                lambda pid: {
                    "pid": pid,
                    "alive": pid == os.getpid(),
                    "start_identity": "a" * 64,
                    "command": "pytest",
                },
            )
            state = writer_lease_status(ledger)
            assert state["active"]
            assert state["recorded_process_id"] == os.getpid()
    assert not writer_lease_status(ledger)["active"]


def test_launch_mutex_rejects_concurrent_launcher(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.sqlite"
    with launch_mutex(ledger):
        with pytest.raises(DuplicateSupervisedLaunch):
            with launch_mutex(ledger):
                pass


def test_process_identity_rejects_pid_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = metadata_for(tmp_path)
    value["collector_pid"] = 123
    value["collector_process_start_identity"] = "original"
    monkeypatch.setattr(
        "orev3.rfc008.supervision.process_snapshot",
        lambda pid: {
            "pid": pid,
            "alive": True,
            "start_identity": "reused",
            "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
        },
    )
    assert not process_matches_metadata(value)


def test_cli_exposes_start_and_hides_internal_supervision_arguments() -> None:
    commands = parser()
    args = commands.parse_args(
        [
            "start",
            "--config",
            "config.json",
            "--marker",
            "marker.json",
            "--expected-marker-sha256",
            "a" * 64,
            "--ledger",
            "ledger.sqlite",
            "--authorization",
            "authorization.sqlite",
        ]
    )
    assert args.command == "start"
    assert not args.recovery
    assert args.startup_timeout_seconds == 30.0
    help_text = commands.format_help()
    assert "--supervision-metadata" not in help_text


def test_supervised_child_command_contains_no_rpc_values(
    tmp_path: Path,
) -> None:
    args = SimpleNamespace(
        config="config.json",
        resolver_config="resolver.json",
        marker="marker.json",
        ledger="ledger.sqlite",
        authorization="authorization.sqlite",
        repository_root=".",
        burn_in_evidence="burn.json",
        release_approval="release.json",
        approval_manifest="approval.json",
        expected_marker_sha256="a" * 64,
        expected_marker_sha256_file=None,
        recovery=False,
    )
    command = cli._supervised_child_command(
        args,
        metadata_path=tmp_path / "metadata.json",
        launch_identifier="10000000-0000-4000-8000-000000000001",
        authority_descriptor=7,
        log_descriptor=8,
    )
    text = " ".join(command)
    assert "ORE_RECOVERY_PRIMARY_RPC_URL" not in text
    assert "ORE_RECOVERY_SECONDARY_RPC_URL" not in text
    assert "--supervision-metadata" in command
    assert "--startup-timeout-seconds" in command
    assert INTERNAL_CHILD_COMMAND in command


def test_supervisor_acknowledgement_requires_exact_session(
    tmp_path: Path,
) -> None:
    value = metadata_for(tmp_path)
    value.update(
        {
            "collector_pid": 4321,
            "collector_start_timestamp": "2026-07-29T00:00:00+00:00",
            "collector_process_start_identity": "f" * 64,
            "launch_authority_consumed_at": "2026-07-29T00:00:00+00:00",
            "session_identity": "another-session",
            "supervision_state": "active",
        }
    )
    path = Path(value["metadata_path"])
    atomic_write_metadata(path, value)
    with pytest.raises(SupervisionError, match="another session"):
        cli._await_supervisor_acknowledgement(
            metadata_path=path,
            launch_identifier=str(value["launch_identifier"]),
            session_identifier="expected-session",
            collector_pid=4321,
            stop_requested=SimpleNamespace(is_set=lambda: False),
            timeout_seconds=1.0,
        )


def test_supervisor_acknowledgement_accepts_exact_active_session(
    tmp_path: Path,
) -> None:
    value = metadata_for(tmp_path)
    value.update(
        {
            "collector_pid": 4321,
            "collector_start_timestamp": "2026-07-29T00:00:00+00:00",
            "collector_process_start_identity": "f" * 64,
            "launch_authority_consumed_at": "2026-07-29T00:00:00+00:00",
            "session_identity": "expected-session",
            "supervision_state": "active",
        }
    )
    path = Path(value["metadata_path"])
    atomic_write_metadata(path, value)
    assert cli._await_supervisor_acknowledgement(
        metadata_path=path,
        launch_identifier=str(value["launch_identifier"]),
        session_identifier="expected-session",
        collector_pid=4321,
        stop_requested=SimpleNamespace(is_set=lambda: False),
        timeout_seconds=1.0,
    )


@pytest.mark.parametrize(
    ("gate_reasons", "expected_ready"),
    (
        (("active_session_present",), True),
        (("active_session_present", "ledger_completed"), False),
    ),
)
def test_continuation_runtime_preflight_allows_only_expected_active_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gate_reasons: tuple[str, ...],
    expected_ready: bool,
) -> None:
    monkeypatch.setattr(
        cli,
        "preflight_continuation",
        lambda **kwargs: SimpleNamespace(
            ready=False,
            gate_reasons=gate_reasons,
        ),
    )
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40 + "\n"),
    )
    release = SimpleNamespace(
        valid=True,
        parsed_active_approval={"cli_sha256": "d" * 64},
    )
    monkeypatch.setattr(cli, "validate_active_release", lambda **kwargs: release)
    args = SimpleNamespace(
        continuation_approval=tmp_path / "continuation.json",
        recovery=True,
        repository_root=tmp_path,
        config="config",
        resolver_config="resolver",
        burn_in_evidence="burn",
        release_approval="release",
        approval_manifest="manifest",
        marker="marker",
        authorization="authorization",
        ledger="ledger",
    )
    before_session = cli._runtime_preflight(args)
    runtime = cli._runtime_preflight(
        args,
        expected_active_session="expected-session",
    )
    assert not before_session.ready
    assert runtime.ready is expected_ready


def test_supervised_run_rejects_wrong_launch_binding(
    tmp_path: Path,
) -> None:
    value = metadata_for(tmp_path)
    path = Path(value["metadata_path"])
    atomic_write_metadata(path, value)
    args = SimpleNamespace(
        supervision_metadata=str(path),
        supervision_launch_identifier="wrong",
        supervision_authority_fd=0,
        supervision_log_fd=0,
        ledger=value["ledger_path"],
    )
    with pytest.raises(SupervisionError, match="binding"):
        cli.command_run(args)


def test_supervised_run_records_redacted_early_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = metadata_for(tmp_path)
    value["collector_pid"] = os.getpid()
    value["collector_process_start_identity"] = "e" * 64
    path = Path(value["metadata_path"])
    atomic_write_metadata(path, value)
    monkeypatch.setattr(
        cli,
        "process_snapshot",
        lambda pid: {
            "pid": pid,
            "alive": True,
            "start_identity": "e" * 64,
            "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
        },
    )
    secret = "https://provider.invalid/?token=secret"
    monkeypatch.setattr(
        cli,
        "_command_run",
        lambda args: (_ for _ in ()).throw(RuntimeError(secret)),
    )
    monkeypatch.setattr(cli, "_supervision_exit_state", lambda args: "failed")
    monkeypatch.setattr(cli, "consume_child_authority", lambda *a, **k: None)
    monkeypatch.setattr(cli, "validate_import_identity", lambda *a, **k: None)
    monkeypatch.setattr(cli, "install_sanitized_streams", lambda *a, **k: None)
    args = SimpleNamespace(
        supervision_metadata=str(path),
        supervision_launch_identifier=value["launch_identifier"],
        supervision_authority_fd=0,
        supervision_log_fd=0,
        ledger=value["ledger_path"],
        repository_root=tmp_path,
    )
    with pytest.raises(RuntimeError):
        cli.command_run(args)
    result = read_metadata(path)
    assert result["supervision_state"] == "failed"
    assert secret not in result["failure_reason"]
    assert result["exit_code"] == 1


def test_start_rejects_active_authoritative_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "validate_collection_preflight",
        lambda **kwargs: SimpleNamespace(
            ready=True,
            gate_reasons=[],
            active_release_validation=SimpleNamespace(
                parsed_active_approval={"cli_sha256": "d" * 64}
            ),
        ),
    )
    monkeypatch.setattr(
        cli,
        "_git_branch_and_head",
        lambda root: ("research/rfc-007-paper-collection-burn-in", "a" * 40),
    )
    monkeypatch.setattr(cli, "validate_import_identity", lambda *a, **k: None)
    monkeypatch.setattr(cli, "approved_python_command", lambda root: sys.executable)
    authorization = SimpleNamespace(
        lifecycle_state="active",
        consuming_session_identity="session",
        record=SimpleNamespace(
            authorization_identifier="authorization",
            authorization_digest="a" * 64,
        ),
    )
    contract = SimpleNamespace(
        completed=False,
        active_session_identity="session",
        ledger_instance_identifier="ledger",
        collection_target=600,
    )
    monkeypatch.setattr(
        cli,
        "_startup_authoritative_state",
        lambda args, process_id=None: {
            "authorization": authorization,
            "contract": contract,
            "open_runs": [object()],
        },
    )
    args = SimpleNamespace(
        repository_root=tmp_path,
        config="config",
        resolver_config="resolver",
        burn_in_evidence="burn",
        release_approval="release",
        approval_manifest="approval",
        marker="marker",
        authorization="authorization",
        ledger=tmp_path / "ledger.sqlite",
        recovery=False,
    )
    with pytest.raises(PermissionError, match="session"):
        cli.command_start(args)


def test_start_rejects_live_stale_metadata_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_start_preflight(monkeypatch)
    monkeypatch.setattr(
        cli,
        "_startup_authoritative_state",
        lambda args, process_id=None: initialized_start_state(),
    )
    monkeypatch.setattr(
        cli,
        "writer_lease_status",
        lambda ledger: {"active": False},
    )
    value = metadata_for(tmp_path)
    value["collector_pid"] = 123
    value["collector_process_start_identity"] = "e" * 64
    atomic_write_metadata(value["metadata_path"], value)
    monkeypatch.setattr(cli, "process_matches_metadata", lambda value: True)
    monkeypatch.setattr(
        cli,
        "spawn_detached",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("must not spawn")
        ),
    )
    with pytest.raises(PermissionError, match="already active"):
        cli.command_start(start_args(tmp_path))


def test_start_reports_child_exit_before_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_start_preflight(monkeypatch)
    monkeypatch.setattr(
        cli,
        "_startup_authoritative_state",
        lambda args, process_id=None: initialized_start_state(),
    )
    monkeypatch.setattr(
        cli,
        "writer_lease_status",
        lambda ledger: {"active": False},
    )

    class Child:
        pid = 4321

        def poll(self):
            return 1

        def wait(self, timeout):
            return 1

    monkeypatch.setattr(cli, "spawn_detached", lambda *a, **k: Child())
    monkeypatch.setattr(
        cli,
        "wait_for_process_identity",
        lambda pid: {
            "pid": pid,
            "alive": True,
            "start_identity": "e" * 64,
            "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
        },
    )
    monkeypatch.setattr(
        cli,
        "process_snapshot",
        lambda pid: {
            "pid": pid,
            "alive": False,
            "start_identity": None,
            "command": None,
        },
    )
    with pytest.raises(SupervisionError, match="exited before startup"):
        cli.command_start(start_args(tmp_path))
    assert (
        read_metadata(supervision_paths(tmp_path / "ledger.sqlite")["metadata"])[
            "supervision_state"
        ]
        == "failed"
    )


def test_start_timeout_terminates_unestablished_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_start_preflight(monkeypatch)
    monkeypatch.setattr(
        cli,
        "_startup_authoritative_state",
        lambda args, process_id=None: initialized_start_state(),
    )
    monkeypatch.setattr(
        cli,
        "writer_lease_status",
        lambda ledger: {"active": False, "recorded_process_id": None},
    )

    class Child:
        pid = 4321
        returncode = None
        terminated = False

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout):
            return self.returncode

        def kill(self):
            self.returncode = -9

        def poll(self):
            return self.returncode

    child = Child()
    monkeypatch.setattr(cli, "spawn_detached", lambda *a, **k: child)
    snapshot = {
        "pid": 4321,
        "alive": True,
        "start_identity": "e" * 64,
        "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
    }
    monkeypatch.setattr(cli, "wait_for_process_identity", lambda pid: snapshot)
    monkeypatch.setattr(cli, "process_snapshot", lambda pid: snapshot)
    monkeypatch.setattr(
        "orev3.rfc008.supervision.process_snapshot", lambda pid: snapshot
    )
    with pytest.raises(SupervisionError, match="timed out"):
        cli.command_start(start_args(tmp_path))
    assert child.terminated
    metadata = read_metadata(
        supervision_paths(tmp_path / "ledger.sqlite")["metadata"]
    )
    assert metadata["supervision_state"] == "failed"
    assert metadata["exit_code"] == -15


def test_start_reports_success_only_after_authoritative_handshake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "validate_collection_preflight",
        lambda **kwargs: SimpleNamespace(
            ready=True,
            gate_reasons=[],
            active_release_validation=SimpleNamespace(
                parsed_active_approval={"cli_sha256": "d" * 64}
            ),
        ),
    )
    monkeypatch.setattr(
        cli,
        "_git_branch_and_head",
        lambda root: ("research/rfc-007-paper-collection-burn-in", "a" * 40),
    )
    monkeypatch.setattr(cli, "validate_import_identity", lambda *a, **k: None)
    monkeypatch.setattr(cli, "approved_python_command", lambda root: sys.executable)
    monkeypatch.setattr(
        cli,
        "validate_active_release",
        lambda **kwargs: SimpleNamespace(valid=True),
    )
    monkeypatch.setattr(
        cli,
        "_active_authorization_release_mismatches",
        lambda *args, **kwargs: (),
    )
    record = SimpleNamespace(
        authorization_identifier="authorization",
        authorization_digest="a" * 64,
    )
    initialized_authorization = SimpleNamespace(
        lifecycle_state="initialized",
        consuming_session_identity=None,
        record=record,
    )
    active_authorization = SimpleNamespace(
        lifecycle_state="active",
        consuming_session_identity="session",
        record=record,
    )
    initialized_contract = SimpleNamespace(
        collection_state="initialized",
        completed=False,
        active_session_identity=None,
        ledger_instance_identifier="ledger-instance",
        collection_target=600,
    )
    active_contract = SimpleNamespace(
        collection_state="active",
        completed=False,
        active_session_identity="session",
        ledger_instance_identifier="ledger-instance",
        collection_target=600,
    )
    calls = 0

    def authoritative(args, process_id=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "authorization": initialized_authorization,
                "contract": initialized_contract,
                "open_runs": [],
            }
        return {
            "authorization": active_authorization,
            "contract": active_contract,
            "open_runs": [
                {"run_id": "session", "process_id": 4321}
            ],
            "matching_run": {
                "run_id": "session",
                "process_id": 4321,
            },
        }

    monkeypatch.setattr(cli, "_startup_authoritative_state", authoritative)
    monkeypatch.setattr(
        cli,
        "writer_lease_status",
        lambda ledger: {
            "active": calls > 1,
            "recorded_process_id": 4321 if calls > 1 else None,
            "recorded_process_start_identity": (
                "f" * 64 if calls > 1 else None
            ),
        },
    )

    class Child:
        pid = 4321

        def terminate(self):
            raise AssertionError("successful child must not be terminated")

        def poll(self):
            return None

    def spawn(*_args, **_kwargs):
        update_metadata(
            supervision_paths(args.ledger)["metadata"],
            collector_pid=4321,
            collector_start_timestamp="2026-07-29T00:00:00+00:00",
            collector_process_start_identity="f" * 64,
            launch_authority_consumed_at="2026-07-29T00:00:00+00:00",
        )
        return Child()

    monkeypatch.setattr(cli, "spawn_detached", spawn)
    snapshot = {
        "pid": 4321,
        "alive": True,
        "start_identity": "f" * 64,
        "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
    }
    monkeypatch.setattr(cli, "wait_for_process_identity", lambda pid: snapshot)
    monkeypatch.setattr(cli, "process_snapshot", lambda pid: snapshot)
    args = SimpleNamespace(
        repository_root=tmp_path,
        config="config",
        resolver_config="resolver",
        burn_in_evidence="burn",
        release_approval="release",
        approval_manifest="approval",
        marker="marker",
        authorization="authorization",
        ledger=tmp_path / "ledger.sqlite",
        recovery=False,
        expected_marker_sha256="b" * 64,
        expected_marker_sha256_file=None,
        startup_timeout_seconds=1.0,
    )
    cli.command_start(args)
    result = json.loads(capsys.readouterr().out)
    assert result["supervised_launch"] == "active"
    assert result["collector_pid"] == 4321
    assert result["session_identity"] == "session"
    metadata = read_metadata(
        supervision_paths(args.ledger)["metadata"]
    )
    assert metadata["supervision_state"] == "active"
    assert metadata["session_identity"] == "session"


def test_continuation_recovery_uses_runtime_session_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    preflight_sessions: list[str | None] = []
    release = SimpleNamespace(
        parsed_active_approval={"cli_sha256": "d" * 64}
    )

    def runtime_preflight(args, *, expected_active_session=None):
        preflight_sessions.append(expected_active_session)
        return SimpleNamespace(
            ready=True,
            gate_reasons=(),
            active_release_validation=release,
        )

    monkeypatch.setattr(cli, "_runtime_preflight", runtime_preflight)
    monkeypatch.setattr(
        cli,
        "_git_branch_and_head",
        lambda root: ("research/rfc-007-paper-collection-burn-in", "a" * 40),
    )
    monkeypatch.setattr(cli, "validate_import_identity", lambda *a, **k: None)
    monkeypatch.setattr(cli, "approved_python_command", lambda root: sys.executable)
    record = SimpleNamespace(
        authorization_identifier="authorization",
        authorization_digest="a" * 64,
    )
    before = {
        "authorization": SimpleNamespace(
            lifecycle_state="active",
            consuming_session_identity=None,
            record=record,
        ),
        "contract": SimpleNamespace(
            collection_state="active",
            completed=False,
            active_session_identity=None,
            ledger_instance_identifier="ledger-instance",
            collection_target=600,
        ),
        "open_runs": [],
        "matching_run": None,
    }
    active = {
        "authorization": SimpleNamespace(
            lifecycle_state="active",
            consuming_session_identity="session",
            record=record,
        ),
        "contract": SimpleNamespace(
            collection_state="active",
            completed=False,
            active_session_identity="session",
            ledger_instance_identifier="ledger-instance",
            collection_target=600,
        ),
        "open_runs": [{"run_id": "session", "process_id": 4321}],
        "matching_run": {"run_id": "session", "process_id": 4321},
    }
    states = iter((before, active, active))
    monkeypatch.setattr(
        cli,
        "_startup_authoritative_state",
        lambda *args, **kwargs: next(states),
    )
    lease_calls = 0

    def lease_status(_ledger):
        nonlocal lease_calls
        lease_calls += 1
        return {
            "active": lease_calls > 1,
            "recorded_process_id": 4321 if lease_calls > 1 else None,
            "recorded_process_start_identity": (
                "f" * 64 if lease_calls > 1 else None
            ),
        }

    monkeypatch.setattr(cli, "writer_lease_status", lease_status)

    class Child:
        pid = 4321

        def poll(self):
            return None

    def spawn(*_args, **_kwargs):
        update_metadata(
            supervision_paths(args.ledger)["metadata"],
            collector_pid=4321,
            collector_start_timestamp="2026-07-29T00:00:00+00:00",
            collector_process_start_identity="f" * 64,
            launch_authority_consumed_at="2026-07-29T00:00:00+00:00",
        )
        return Child()

    monkeypatch.setattr(cli, "spawn_detached", spawn)
    snapshot = {
        "pid": 4321,
        "alive": True,
        "start_identity": "f" * 64,
        "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
    }
    monkeypatch.setattr(cli, "wait_for_process_identity", lambda pid: snapshot)
    monkeypatch.setattr(cli, "process_snapshot", lambda pid: snapshot)
    args = start_args(tmp_path)
    args.recovery = True
    args.continuation_approval = "continuation.json"
    cli.command_start(args)
    result = json.loads(capsys.readouterr().out)
    assert result["supervised_launch"] == "active"
    assert result["session_identity"] == "session"
    assert preflight_sessions == [None, "session"]


def test_process_fixture_uses_no_shell_or_ad_hoc_backgrounding() -> None:
    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "nohup" not in source
    assert "disown" not in source
    assert "screen " not in source
    assert "tmux" not in source
