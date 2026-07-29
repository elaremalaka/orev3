from __future__ import annotations

import json
import os
import subprocess
import traceback
from pathlib import Path
from types import SimpleNamespace

import pytest

import orev3.rfc008.cli as cli
import orev3.rfc008.lifecycle as lifecycle
from orev3.rfc008.authorization import CollectionAuthorizationStore
from orev3.rfc008.status import status_report
from orev3.rfc008.supervision import (
    INTERNAL_CHILD_COMMAND,
    SanitizingTextIO,
    SupervisionError,
    configured_secret_values,
    safe_open_log,
    sanitize_text,
    supervision_paths,
    terminate_unestablished_child,
)

from .test_supervision import mock_start_preflight
from .test_supervision import start_args


PRIMARY_SECRET = "PRIMARY_API_KEY_7f4e91"
SECONDARY_SECRET = "SECONDARY_API_KEY_83c2a7"
USERNAME_SECRET = "RPC_USER_5d71ce"
PASSWORD_SECRET = "RPC_PASSWORD_c9d12b"
ENCODED_SECRET = "encoded secret 71ab"


def _secret_environment() -> dict[str, str]:
    return {
        "ORE_RECOVERY_PRIMARY_RPC_URL": (
            f"https://{USERNAME_SECRET}:"
            f"{PASSWORD_SECRET}@primary.rpc.invalid/v1/{PRIMARY_SECRET}"
            f"?api-key={PRIMARY_SECRET}&encoded=encoded%20secret%2071ab"
        ),
        "ORE_RECOVERY_SECONDARY_RPC_URL": (
            "https://secondary.rpc.invalid/rpc"
            f"?token={SECONDARY_SECRET}"
        ),
        "UNRELATED_SAFE_VALUE": "safe-diagnostic",
    }


@pytest.mark.parametrize(
    "secret",
    (
        PRIMARY_SECRET,
        SECONDARY_SECRET,
        USERNAME_SECRET,
        PASSWORD_SECRET,
        ENCODED_SECRET,
        "encoded%20secret%2071ab",
    ),
)
def test_provider_secret_components_are_redacted(secret: str) -> None:
    known = configured_secret_values(_secret_environment())
    traceback = (
        "ProviderError: HTTP 429 from primary.rpc.invalid\n"
        f"traceback repeated {secret}\ncaused by {secret}"
    )
    sanitized = sanitize_text(traceback, known_secrets=known)
    assert secret not in sanitized
    assert "primary.rpc.invalid" in sanitized
    assert "HTTP 429" in sanitized
    assert "ProviderError" in sanitized


def test_provider_secret_fragment_is_absent_from_durable_log(
    tmp_path: Path,
) -> None:
    descriptor, _ = safe_open_log(tmp_path / "collector.log")
    stream = SanitizingTextIO(
        descriptor,
        known_secrets=configured_secret_values(_secret_environment()),
    )
    stream.write(
        f"ProviderError HTTP 429 at primary.rpc.invalid: {PRIMARY_SECRET}\n"
    )
    stream.flush()
    stream.close()
    os.close(descriptor)
    value = (tmp_path / "collector.log").read_text()
    assert PRIMARY_SECRET not in value
    assert "primary.rpc.invalid" in value
    assert "HTTP 429" in value


@pytest.mark.parametrize(
    ("command", "failure_name", "safe_context"),
    (
        ("status", "validate_active_release", "repository_head"),
        ("start", "validate_collection_preflight", "collection_preflight"),
    ),
)
def test_public_command_exception_never_returns_configured_secret(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    failure_name: str,
    safe_context: str,
) -> None:
    secret = f"{command.upper()}_BOUNDARY_SECRET_7fA91"
    monkeypatch.setenv(
        "ORE_RECOVERY_PRIMARY_RPC_URL",
        f"https://audit.invalid/credential/{secret}?token={secret}",
    )
    monkeypatch.setattr(
        cli,
        failure_name,
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError(f"{safe_context}: HTTP 429: {secret}")
        ),
    )
    if command == "status":
        args = SimpleNamespace(
            repository_root=Path.cwd(),
            config=Path("config.json"),
            resolver_config=Path("resolver.json"),
            burn_in_evidence=Path("burn.json"),
            release_approval=Path("approval.json"),
            approval_manifest=Path("manifest.json"),
            marker=Path("marker.json"),
            authorization=Path("authorization.sqlite"),
            ledger=Path("ledger.sqlite"),
            expected_marker_sha256="e" * 64,
            expected_marker_sha256_file=None,
        )
        invoke = cli.command_status
    else:
        args = SimpleNamespace(
            repository_root=Path.cwd(),
            config=Path("config.json"),
            resolver_config=Path("resolver.json"),
            burn_in_evidence=Path("burn.json"),
            release_approval=Path("approval.json"),
            approval_manifest=Path("manifest.json"),
            marker=Path("marker.json"),
            authorization=Path("authorization.sqlite"),
            ledger=Path("ledger.sqlite"),
            recovery=False,
        )
        invoke = cli.command_start
    with pytest.raises(RuntimeError) as caught:
        invoke(args)
    error = caught.value
    formatted = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    traceback.print_exception(type(error), error, error.__traceback__)
    captured = capsys.readouterr()
    combined = "\n".join(
        (
            str(error),
            repr(error),
            formatted,
            captured.out,
            captured.err,
        )
    )
    assert secret not in combined
    assert safe_context in combined
    assert "RuntimeError" in combined
    assert "HTTP 429" in combined
    assert error.__cause__ is None
    assert error.__context__ is None


def _handshake_state() -> dict[str, object]:
    record = SimpleNamespace(
        authorization_identifier="authorization",
        authorization_digest="a" * 64,
    )
    return {
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


def _mutated_final_state(kind: str) -> dict[str, object]:
    value = _handshake_state()
    if kind == "authorization_consuming_session":
        value["authorization"].consuming_session_identity = "changed"
    elif kind == "ledger_active_session":
        value["contract"].active_session_identity = "changed"
    elif kind == "open_collector_run":
        value["matching_run"] = None
        value["open_runs"] = []
    elif kind == "open_run_pid":
        value["matching_run"]["process_id"] = 9999
    elif kind == "open_run_session":
        value["matching_run"]["run_id"] = "changed"
    elif kind == "authorization_state":
        value["authorization"].lifecycle_state = "completed"
    elif kind == "ledger_state":
        value["contract"].collection_state = "completed"
        value["contract"].completed = True
    elif kind == "target":
        value["contract"].collection_target = 599
    return value


@pytest.mark.parametrize(
    "mutation",
    (
        "authorization_consuming_session",
        "ledger_active_session",
        "open_collector_run",
        "open_run_pid",
        "open_run_session",
        "authorization_state",
        "ledger_state",
        "target",
        "writer_owner",
        "process_identity",
    ),
)
def test_final_authoritative_mutation_never_reports_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mutation: str,
) -> None:
    mock_start_preflight(monkeypatch)
    args = start_args(tmp_path)
    initialized = {
        "authorization": SimpleNamespace(
            lifecycle_state="initialized",
            consuming_session_identity=None,
            record=_handshake_state()["authorization"].record,
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
    active = _handshake_state()
    final = _mutated_final_state(mutation)
    states = iter((initialized, active, final))
    monkeypatch.setattr(
        cli,
        "_startup_authoritative_state",
        lambda *args, **kwargs: next(states),
    )
    lease_calls = {"count": 0}

    def lease_status(*_args):
        lease_calls["count"] += 1
        if lease_calls["count"] == 1:
            return {
                "active": False,
                "recorded_process_id": None,
                "recorded_process_start_identity": None,
            }
        owner = 9999 if mutation == "writer_owner" and lease_calls["count"] == 3 else 4321
        return {
            "active": True,
            "recorded_process_id": owner,
            "recorded_process_start_identity": "f" * 64,
        }

    monkeypatch.setattr(cli, "writer_lease_status", lease_status)

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
    final_process = dict(alive)
    if mutation == "process_identity":
        final_process["start_identity"] = "e" * 64
    snapshots = iter((alive, alive, final_process))
    monkeypatch.setattr(cli, "wait_for_process_identity", lambda *_: alive)
    monkeypatch.setattr(cli, "process_snapshot", lambda *_: next(snapshots))
    monkeypatch.setattr(cli.time, "sleep", lambda *_: None)
    cleaned: list[int] = []
    monkeypatch.setattr(
        cli,
        "terminate_unestablished_child",
        lambda child, identity: cleaned.append(child.pid),
    )
    with pytest.raises(SupervisionError, match="final startup"):
        cli.command_start(args)
    assert cleaned == [4321]
    assert '"supervised_launch": "active"' not in capsys.readouterr().out


class _CleanupChild:
    pid = 4321

    def __init__(
        self,
        *,
        initial_exit: bool = False,
        exit_between: bool = False,
        kill_wait_timeout: bool = False,
    ) -> None:
        self.exited = initial_exit
        self.exit_between = exit_between
        self.kill_wait_timeout = kill_wait_timeout
        self.terminated = 0
        self.killed = 0
        self.reaped = 0
        self.waits = 0

    def poll(self):
        if self.exit_between and self.waits >= 1:
            self.exited = True
        return 0 if self.exited else None

    def terminate(self):
        self.terminated += 1

    def kill(self):
        self.killed += 1
        if not self.kill_wait_timeout:
            self.exited = True

    def wait(self, timeout):
        self.waits += 1
        if self.exited:
            self.reaped += 1
            return 0
        if self.killed and not self.kill_wait_timeout:
            self.exited = True
            self.reaped += 1
            return -9
        if self.killed and self.kill_wait_timeout:
            self.exit_between = True
        raise subprocess.TimeoutExpired("child", timeout)


@pytest.mark.parametrize(
    ("child", "expected_terminate", "expected_kill"),
    (
        (_CleanupChild(), 1, 1),
        (_CleanupChild(exit_between=True), 1, 0),
        (_CleanupChild(kill_wait_timeout=True), 1, 1),
        (_CleanupChild(initial_exit=True), 0, 0),
    ),
)
def test_unestablished_child_cleanup_is_bounded_and_reaped(
    child: _CleanupChild,
    expected_terminate: int,
    expected_kill: int,
) -> None:
    terminate_unestablished_child(child, "unrelated-metadata-identity")
    assert child.terminated == expected_terminate
    assert child.killed == expected_kill
    assert child.poll() == 0
    assert child.reaped >= 1


@pytest.mark.parametrize(
    ("field", "expected_mismatch"),
    (
        (None, None),
        ("repository_head", "repository_head"),
        ("implementation_commit", "implementation_commit"),
        ("active_approval_sha256", "active_approval_sha256"),
        ("immediate_predecessor_sha256", "immediate_predecessor_sha256"),
        ("cli_sha256", "cli_sha256"),
        ("runbook_sha256", "runbook_sha256"),
        ("resolver_fingerprint", "resolver_fingerprint"),
        ("migration_set_sha256", "migration_set_sha256"),
        ("branch", "branch"),
        ("marker_sha256", "marker_sha256"),
    ),
)
def test_active_release_binding_reports_each_mismatch(
    store,
    config,
    monkeypatch: pytest.MonkeyPatch,
    field: str | None,
    expected_mismatch: str | None,
) -> None:
    value, path = store
    authorization_path = path.with_suffix(".authorization.sqlite")
    with CollectionAuthorizationStore(
        authorization_path,
        read_only=True,
    ) as authorization:
        record = authorization.status().record
    approval = {
        "validated_production_marker_sha256": record.marker_sha256,
        "validated_production_marker_sidecar_sha256": (
            record.marker_sidecar_sha256
        ),
        "resolver_configuration_sha256": record.resolver_fingerprint,
        "migration_set_sha256": record.migration_set_sha256,
        "cli_sha256": record.cli_sha256,
        "runbook_sha256": record.runbook_sha256,
        "validated_operational_burn_in_evidence_sha256": (
            record.burn_in_evidence_sha256
        ),
        "validated_operational_burn_in_ledger_sha256": (
            record.burn_in_ledger_sha256
        ),
        "frozen_approval_manifest_sha256": (
            record.approval_manifest_sha256
        ),
        "verification": {"external_rpc_burn_in_performed": True},
    }
    active = SimpleNamespace(
        parsed_active_approval=approval,
        active_approval_sha256=record.active_approval_sha256,
        approval_hashes=(record.approval_chain_anchor,),
    )
    authority = SimpleNamespace(
        branch=record.branch,
        implementation_commit=record.implementation_commit,
        predecessor_approval_sha256=record.immediate_predecessor_sha256,
    )
    monkeypatch.setattr(
        lifecycle,
        "repository_release_authority",
        lambda **kwargs: authority,
    )
    monkeypatch.setattr(
        lifecycle.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout=record.repository_head + "\n"
        ),
    )
    matching_config = SimpleNamespace(
        candidate_configuration_sha256=record.candidate_sha256,
        experiment_id=record.experiment_id,
        configuration_fingerprint=record.configuration_fingerprint,
    )
    mutated = record
    if field is not None:
        replacement = "f" * (
            40
            if field in {"repository_head", "implementation_commit"}
            else 64
        )
        if field == "branch":
            replacement = "wrong-branch"
        mutated = record.model_copy(update={field: replacement})
    mismatches = lifecycle.authorization_release_mismatches(
        repository_root=Path.cwd(),
        release_approval_path=Path("approval.json"),
        ledger_path=path,
        config=matching_config,
        active_release=active,
        authorization=mutated,
    )
    if expected_mismatch is None:
        assert not mismatches
    else:
        assert expected_mismatch in mismatches


def test_status_readiness_fails_closed_on_release_mismatch(
    store,
    marker_file,
) -> None:
    _, path = store
    marker, digest = marker_file
    report = status_report(
        ledger_path=path,
        config_path=Path("config/collection/rfc008_paper_v1.json"),
        marker_path=marker,
        authorization_path=path.with_suffix(".authorization.sqlite"),
        authorization_binding_valid=False,
        authorization_release_mismatches=("repository_head",),
        expected_marker_sha256=digest,
    )
    assert report["sqlite_integrity"] == "ok"
    assert not report["authorization_binding_valid"]
    assert report["authorization_release_mismatches"] == [
        "repository_head"
    ]
    assert not report["active_release_compatible"]
    assert not report["collection_ready"]
