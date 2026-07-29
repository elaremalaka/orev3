from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import orev3
import orev3.rfc008.cli as cli
import orev3.rfc008.supervision as supervision
from orev3.rfc008.status import active_identity_agrees
from orev3.rfc008.supervision import (
    INTERNAL_CHILD_COMMAND,
    SanitizingTextIO,
    SupervisionError,
    approved_python_command,
    atomic_write_metadata,
    consume_child_authority,
    controlled_environment,
    create_child_authority,
    read_metadata,
    safe_open_log,
    supervision_paths,
    validate_import_identity,
    writer_lease_status,
)

from .test_supervision import metadata_for


def test_public_run_command_is_removed_and_programmatic_run_is_guarded() -> None:
    with pytest.raises(SystemExit):
        cli.parser().parse_args(["run"])
    with pytest.raises(SupervisionError, match="supervised"):
        cli.command_run(SimpleNamespace())


def test_internal_child_requires_inherited_single_use_authority() -> None:
    with pytest.raises(SystemExit):
        cli.parser().parse_args([INTERNAL_CHILD_COMMAND])
    descriptor, digest = create_child_authority()
    consume_child_authority(descriptor, expected_sha256=digest)
    replay_read, replay_write = os.pipe()
    os.close(replay_write)
    with pytest.raises(SupervisionError, match="authority"):
        consume_child_authority(replay_read, expected_sha256=digest)


def test_child_environment_replaces_python_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/hostile/package")
    monkeypatch.setenv("PYTHONHOME", "/hostile/runtime")
    monkeypatch.setenv("UNRELATED_SECRET", "recognizable-secret")
    value = controlled_environment(Path.cwd())
    assert value["PYTHONPATH"] == str(Path.cwd() / "src")
    assert "PYTHONHOME" not in value
    assert "UNRELATED_SECRET" not in value


def test_approved_interpreter_and_import_origin() -> None:
    assert approved_python_command(Path.cwd()) == str(
        (Path.cwd() / ".venv/bin/python").absolute()
    )
    digest = hashlib.sha256(
        (Path.cwd() / "src/orev3/rfc008/cli.py").read_bytes()
    ).hexdigest()
    validate_import_identity(Path.cwd(), expected_cli_sha256=digest)


@pytest.mark.parametrize("kind", ("alternate", "outside_prefix"))
def test_alternate_interpreter_is_rejected(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    if kind == "alternate":
        monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    else:
        monkeypatch.setattr(sys, "prefix", "/tmp/not-approved")
    with pytest.raises(SupervisionError):
        approved_python_command(Path.cwd())


def test_package_origin_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(orev3, "__file__", "/tmp/fake/orev3/__init__.py")
    with pytest.raises(SupervisionError, match="origin"):
        validate_import_identity(Path.cwd(), expected_cli_sha256="0" * 64)


@pytest.mark.parametrize(
    "target_name",
    (
        "unrelated.txt",
        "source.py",
        "approval.json",
        "marker.json",
        "ledger.sqlite",
    ),
)
def test_log_symlink_targets_are_rejected_without_modification(
    tmp_path: Path, target_name: str
) -> None:
    target = tmp_path / target_name
    target.write_bytes(b"protected")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    link = tmp_path / "collector.log"
    link.symlink_to(target)
    with pytest.raises(SupervisionError):
        safe_open_log(link)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest


def test_runtime_directory_symlink_and_non_regular_log_are_rejected(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(SupervisionError, match="directory"):
        safe_open_log(linked / "collector.log")
    fifo = tmp_path / "collector.fifo"
    os.mkfifo(fifo)
    with pytest.raises(SupervisionError):
        safe_open_log(fifo)


def test_sanitized_log_removes_urls_credentials_and_known_secrets(
    tmp_path: Path,
) -> None:
    path = tmp_path / "collector.log"
    descriptor, _ = safe_open_log(path)
    secret = "RECOGNIZABLE_FAKE_SECRET"
    stream = SanitizingTextIO(descriptor, known_secrets=(secret,))
    stream.write(
        "provider error https://user:pass@example.invalid/rpc?api-key="
        f"{secret} Authorization: Bearer token-{secret}\n"
    )
    stream.flush()
    os.close(descriptor)
    value = path.read_text()
    assert secret not in value
    assert "user:pass" not in value
    assert "api-key=" not in value
    assert "Bearer token" not in value
    assert "<redacted-url>" in value


def test_passive_writer_status_never_takes_a_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "ledger.sqlite"
    Path(str(ledger) + ".writer.lock").write_text("999999\n")
    monkeypatch.setattr(
        supervision.fcntl,
        "flock",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("status attempted a lock")
        ),
    )
    assert writer_lease_status(ledger)["observation"] == "inactive_stale"


def _agreement_fixture(tmp_path: Path):
    process = {"pid": 42, "start_identity": "a" * 64, "alive": True}
    lease = {
        "recorded_process_id": 42,
        "recorded_process_start_identity": "a" * 64,
    }
    record = SimpleNamespace(
        authorization_identifier="authorization",
        authorization_digest="b" * 64,
        repository_branch="branch",
        repository_head="c" * 40,
    )
    authorization = SimpleNamespace(record=record)
    contract = SimpleNamespace(
        ledger_instance_identifier="ledger",
        active_session_identity="session",
        collection_target=600,
    )
    metadata = {
        "collector_pid": 42,
        "collector_process_start_identity": "a" * 64,
        "authorization_identifier": "authorization",
        "authorization_digest": "b" * 64,
        "ledger_instance_identifier": "ledger",
        "session_identity": "session",
        "branch": "branch",
        "head": "c" * 40,
        "target_count": 600,
        "log_path": str(tmp_path / "ledger.collector.log"),
    }
    run = {"run_id": "session", "process_id": 42}
    return metadata, process, lease, run, authorization, contract


def test_status_exact_identity_agreement(tmp_path: Path) -> None:
    values = _agreement_fixture(tmp_path)
    assert active_identity_agrees(
        supervision=values[0],
        process=values[1],
        lease=values[2],
        open_run=values[3],
        authorization=values[4],
        contract=values[5],
        runtime_log_path=tmp_path / "ledger.collector.log",
    )


@pytest.mark.parametrize(
    ("source", "field", "value"),
    (
        ("metadata", "collector_pid", 41),
        ("metadata", "collector_process_start_identity", "d" * 64),
        ("metadata", "authorization_identifier", "wrong"),
        ("metadata", "authorization_digest", "d" * 64),
        ("metadata", "ledger_instance_identifier", "wrong"),
        ("metadata", "session_identity", "wrong"),
        ("metadata", "branch", "wrong"),
        ("metadata", "head", "d" * 40),
        ("metadata", "target_count", 599),
        ("metadata", "log_path", "/tmp/wrong.log"),
        ("run", "run_id", "wrong"),
        ("run", "process_id", 41),
        ("lease", "recorded_process_id", 41),
        ("lease", "recorded_process_start_identity", "d" * 64),
    ),
)
def test_status_rejects_each_cross_source_disagreement(
    tmp_path: Path, source: str, field: str, value: object
) -> None:
    metadata, process, lease, run, authorization, contract = (
        _agreement_fixture(tmp_path)
    )
    {"metadata": metadata, "run": run, "lease": lease}[source][field] = value
    assert not active_identity_agrees(
        supervision=metadata,
        process=process,
        lease=lease,
        open_run=run,
        authorization=authorization,
        contract=contract,
        runtime_log_path=tmp_path / "ledger.collector.log",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("schema_version", True),
        ("launch_identifier", "not-a-uuid"),
        ("launch_authority_sha256", "A" * 64),
        ("launcher_pid", True),
        ("collector_pid", 0),
        ("collector_start_timestamp", "not-time"),
        ("collector_process_start_identity", "short"),
        ("head", "g" * 40),
        ("cli_sha256", "short"),
        ("target_count", True),
        ("last_observed_status_timestamp", "not-time"),
        ("exit_code", False),
        ("failure_reason", 1),
    ),
)
def test_metadata_rejects_malformed_authoritative_fields(
    tmp_path: Path, field: str, value: object
) -> None:
    metadata = metadata_for(tmp_path)
    metadata[field] = value
    atomic_write_metadata(metadata["metadata_path"], metadata)
    with pytest.raises(SupervisionError):
        read_metadata(metadata["metadata_path"])


def test_metadata_rejects_duplicate_truncated_unknown_and_symlink(
    tmp_path: Path,
) -> None:
    metadata = metadata_for(tmp_path)
    path = Path(metadata["metadata_path"])
    raw = json.dumps(metadata)
    path.write_text(raw.replace('"target_count": 600', '"target_count": 601, "target_count": 600'))
    with pytest.raises(SupervisionError, match="Duplicate"):
        read_metadata(path)
    path.write_text(raw[:-10])
    with pytest.raises(SupervisionError, match="Malformed"):
        read_metadata(path)
    metadata["unknown"] = True
    atomic_write_metadata(path, metadata)
    with pytest.raises(SupervisionError, match="contract"):
        read_metadata(path)
    path.unlink()
    target = tmp_path / "target.json"
    target.write_text(raw)
    path.symlink_to(target)
    with pytest.raises(SupervisionError):
        read_metadata(path)


def test_child_cleanup_runs_when_identity_discovery_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from .test_supervision import (
        initialized_start_state,
        mock_start_preflight,
        start_args,
    )

    mock_start_preflight(monkeypatch)
    monkeypatch.setattr(
        cli, "_startup_authoritative_state", lambda *a, **k: initialized_start_state()
    )
    monkeypatch.setattr(cli, "writer_lease_status", lambda *_: {"active": False})
    child = SimpleNamespace(pid=4321, poll=lambda: None)
    cleaned: list[tuple[object, object]] = []
    monkeypatch.setattr(cli, "spawn_detached", lambda *a, **k: child)
    monkeypatch.setattr(
        cli,
        "wait_for_process_identity",
        lambda *_: (_ for _ in ()).throw(SupervisionError("identity failed")),
    )
    monkeypatch.setattr(
        cli,
        "terminate_unestablished_child",
        lambda item, identity: cleaned.append((item, identity)),
    )
    with pytest.raises(SupervisionError, match="identity"):
        cli.command_start(start_args(tmp_path))
    assert cleaned == [(child, None)]
    assert read_metadata(supervision_paths(tmp_path / "ledger.sqlite")["metadata"])[
        "supervision_state"
    ] == "failed"


def test_final_liveness_race_cannot_report_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from .test_supervision import mock_start_preflight, start_args

    mock_start_preflight(monkeypatch)
    record = SimpleNamespace(
        authorization_identifier="authorization",
        authorization_digest="a" * 64,
    )
    initialized = {
        "authorization": SimpleNamespace(
            lifecycle_state="initialized",
            consuming_session_identity=None,
            record=record,
        ),
        "contract": SimpleNamespace(
            completed=False,
            active_session_identity=None,
            ledger_instance_identifier="ledger",
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
            completed=False,
            active_session_identity="session",
            ledger_instance_identifier="ledger",
            collection_target=600,
        ),
        "open_runs": [{"run_id": "session", "process_id": 4321}],
        "matching_run": {"run_id": "session", "process_id": 4321},
    }
    states = iter((initialized, active))
    monkeypatch.setattr(
        cli, "_startup_authoritative_state", lambda *a, **k: next(states)
    )
    lease_calls = {"count": 0}

    def lease_status(*_args):
        lease_calls["count"] += 1
        return {
            "active": lease_calls["count"] > 1,
            "recorded_process_id": (
                4321 if lease_calls["count"] > 1 else None
            ),
        }

    monkeypatch.setattr(cli, "writer_lease_status", lease_status)
    args = start_args(tmp_path)

    class Child:
        pid = 4321

        def poll(self):
            return None

    def spawn(*_args, **_kwargs):
        cli.update_metadata(
            supervision_paths(args.ledger)["metadata"],
            collector_pid=4321,
            collector_start_timestamp="2026-07-29T00:00:00+00:00",
            collector_process_start_identity="f" * 64,
            launch_authority_consumed_at="2026-07-29T00:00:00+00:00",
        )
        return Child()

    monkeypatch.setattr(cli, "spawn_detached", spawn)
    alive = {
        "pid": 4321,
        "alive": True,
        "start_identity": "f" * 64,
        "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
    }
    dead = {
        "pid": 4321,
        "alive": False,
        "start_identity": None,
        "command": None,
    }
    snapshots = iter((alive, alive, dead))
    monkeypatch.setattr(cli, "wait_for_process_identity", lambda *_: alive)
    monkeypatch.setattr(cli, "process_snapshot", lambda *_: next(snapshots))
    monkeypatch.setattr(cli.time, "sleep", lambda *_: None)
    monkeypatch.setattr(cli, "terminate_unestablished_child", lambda *a: None)
    with pytest.raises(SupervisionError, match="final startup"):
        cli.command_start(args)
    assert "supervised_launch" not in capsys.readouterr().out


def test_supervised_completed_recovery_exits_reconciled_without_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from .test_supervision import mock_start_preflight, start_args

    mock_start_preflight(monkeypatch)
    args = start_args(tmp_path)
    args.recovery = True
    record = SimpleNamespace(
        authorization_identifier="authorization",
        authorization_digest="a" * 64,
    )
    crashed = {
        "authorization": SimpleNamespace(
            lifecycle_state="active",
            consuming_session_identity="old-session",
            record=record,
        ),
        "contract": SimpleNamespace(
            completed=True,
            active_session_identity="old-session",
            ledger_instance_identifier="ledger",
            collection_target=600,
        ),
        "open_runs": [{"run_id": "old-session", "process_id": 1}],
        "matching_run": None,
    }
    completed = {
        "authorization": SimpleNamespace(
            lifecycle_state="completed",
            consuming_session_identity="old-session",
            record=record,
        ),
        "contract": SimpleNamespace(
            completed=True,
            active_session_identity=None,
            ledger_instance_identifier="ledger",
            collection_target=600,
        ),
        "open_runs": [],
        "matching_run": None,
    }
    states = iter((crashed, completed))
    monkeypatch.setattr(
        cli, "_startup_authoritative_state", lambda *a, **k: next(states)
    )
    monkeypatch.setattr(
        cli,
        "writer_lease_status",
        lambda *_: {
            "active": False,
            "recorded_process_id": None,
        },
    )

    class Child:
        pid = 4321

        def poll(self):
            return 0

    def spawn(*_args, **_kwargs):
        cli.update_metadata(
            supervision_paths(args.ledger)["metadata"],
            collector_pid=4321,
            collector_start_timestamp="2026-07-29T00:00:00+00:00",
            collector_process_start_identity="f" * 64,
            launch_authority_consumed_at="2026-07-29T00:00:00+00:00",
            supervision_state="completed",
            exit_code=0,
        )
        return Child()

    monkeypatch.setattr(cli, "spawn_detached", spawn)
    alive = {
        "pid": 4321,
        "alive": True,
        "start_identity": "f" * 64,
        "command": f"python -m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}",
    }
    dead = {
        "pid": 4321,
        "alive": False,
        "start_identity": None,
        "command": None,
    }
    monkeypatch.setattr(cli, "wait_for_process_identity", lambda *_: alive)
    monkeypatch.setattr(cli, "process_snapshot", lambda *_: dead)
    cli.command_start(args)
    report = json.loads(capsys.readouterr().out)
    assert report["supervised_launch"] == "completed_reconciliation"
    assert report["session_identity"] is None
