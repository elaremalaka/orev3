from __future__ import annotations

import json
import os
import sqlite3
import stat
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from orev3.rfc008.cli import command_rotate_production_artifacts
from orev3.rfc008.authorization import (
    CollectionAuthorizationStore,
    build_authorization_record,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.decisions import build_decisions, snapshot_from_opportunity
from orev3.rfc008.rotation import (
    RotationError,
    evaluate_rotation,
    production_rotation_paths,
    recover_production_artifacts,
    rotate_production_artifacts,
    rotation_status,
)
from orev3.rfc008.storage import (
    LedgerInitialization,
    RFC008Store,
    create_authorized_ledger,
)
from orev3.rfc008.supervision import (
    DuplicateSupervisedLaunch,
    launch_mutex,
)
from orev3.rfc008.writer import DuplicateRFC008Writer, RFC008WriterLease

from .conftest import make_opportunity


ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config/collection/rfc008_paper_v1.json"
CURSORS = (
    {
        "source_path": "/tmp/rfc008-rotation-source.jsonl",
        "source_inode": 100,
        "source_byte_offset": 200,
        "source_line_number": 3,
    },
)


def _file_evidence(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False}
    value = os.lstat(path)
    result: dict[str, object] = {
        "exists": True,
        "size": value.st_size,
        "mtime_ns": value.st_mtime_ns,
        "ctime_ns": value.st_ctime_ns,
        "mode": stat.S_IMODE(value.st_mode),
        "uid": value.st_uid,
        "gid": value.st_gid,
        "inode": value.st_ino,
    }
    if stat.S_ISREG(value.st_mode):
        result["sha256"] = __import__("hashlib").sha256(
            path.read_bytes()
        ).hexdigest()
    return result


def _production_like_evidence(paths: object) -> dict[str, dict[str, object]]:
    monitored = (
        paths.authorization,
        Path(str(paths.authorization) + "-wal"),
        Path(str(paths.authorization) + "-shm"),
        paths.ledger,
        Path(str(paths.ledger) + "-wal"),
        Path(str(paths.ledger) + "-shm"),
        paths.writer_lock,
        paths.rotation_lock,
        paths.launch_lock,
        paths.manifest,
        paths.archive_root,
        paths.supervision_metadata,
        paths.supervision_log,
    )
    return {str(path): _file_evidence(path) for path in monitored}


def _record(
    root: Path,
    config: RFC008Config,
    *,
    release: str,
) -> object:
    paths = production_rotation_paths(root)
    digit = "1" if release == "old" else "2"
    return build_authorization_record(
        authorization_path=paths.authorization,
        ledger_path=paths.ledger,
        branch="research/rfc-007-paper-collection-burn-in",
        repository_head=digit * 40,
        implementation_commit=digit * 40,
        active_approval_sha256=digit * 64,
        immediate_predecessor_sha256=("0" if release == "old" else "1") * 64,
        approval_chain_anchor="a" * 64,
        marker_sha256="b" * 64,
        marker_sidecar_sha256="c" * 64,
        candidate_sha256=config.candidate_configuration_sha256,
        experiment_id=config.experiment_id,
        protocol_version=config.protocol_version,
        configuration_fingerprint=config.configuration_fingerprint,
        resolver_fingerprint="d" * 64,
        migration_set_sha256="e" * 64,
        cli_sha256=digit * 64,
        runbook_sha256=digit * 64,
        burn_in_evidence_sha256="f" * 64,
        burn_in_ledger_sha256="9" * 64,
        approval_manifest_sha256=config.approval_manifest_sha256,
        external_rpc_burn_in_performed=True,
        nonce=f"{release}-rotation-authorization",
        created_at="2026-07-29T00:00:00+00:00",
    )


def _initialized_pair(
    root: Path,
    config: RFC008Config,
    *,
    release: str = "old",
) -> tuple[object, object]:
    paths = production_rotation_paths(root)
    record = _record(root, config, release=release)
    CollectionAuthorizationStore.issue(paths.authorization, record)
    with CollectionAuthorizationStore(paths.authorization) as authorization:
        authorization.consume_initialization()
        create_authorized_ledger(
            paths.ledger,
            config=config,
            initialization=LedgerInitialization(
                authorization=record,
                collection_seed_cursors=CURSORS,
                publication_cursors=CURSORS,
            ),
        )
        authorization.mark_initialized()
    return record, paths


@pytest.fixture
def config() -> RFC008Config:
    return RFC008Config.from_path(CONFIG_PATH)


@pytest.fixture(autouse=True)
def no_live_collector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "orev3.rfc008.rotation._collector_processes", lambda: ()
    )


def _rotate(
    root: Path,
    config: RFC008Config,
    *,
    fault=None,
    release_mismatches: tuple[str, ...] = ("repository_head",),
    transaction_id: str | None = None,
) -> dict[str, object]:
    return rotate_production_artifacts(
        repository_root=root,
        config=config,
        release_mismatches=release_mismatches,
        new_authorization_factory=lambda: _record(
            root, config, release="new"
        ),
        initialization_cursors=CURSORS,
        fault=fault,
        transaction_id=transaction_id,
        created_at="2026-07-29T01:02:03+00:00",
    )


def test_successful_rotation_archives_and_activates_current_pair(
    tmp_path: Path, config: RFC008Config
) -> None:
    old, paths = _initialized_pair(tmp_path, config)
    paths.writer_lock.write_text("999999\n", encoding="utf-8")
    old_authorization_sha = __import__("hashlib").sha256(
        paths.authorization.read_bytes()
    ).hexdigest()
    old_ledger_sha = __import__("hashlib").sha256(
        paths.ledger.read_bytes()
    ).hexdigest()

    result = _rotate(tmp_path, config)

    assert result["result"] == "rotated"
    assert result["old_authorization_identifier"] == old.authorization_identifier
    assert result["new_authorization_identifier"] != old.authorization_identifier
    archive = Path(str(result["archive_directory"]))
    manifest = json.loads(
        (archive / "rotation_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["completion_state"] == "completed"
    assert manifest["old"]["authorization_sha256"] == old_authorization_sha
    assert manifest["old"]["ledger_sha256"] == old_ledger_sha
    assert manifest["old"]["writer_lock_sha256"] is not None
    assert "http://" not in json.dumps(manifest)
    assert "https://" not in json.dumps(manifest)
    assert not paths.manifest.exists()
    assert not paths.writer_lock.exists()
    with (
        CollectionAuthorizationStore(
            paths.authorization, read_only=True
        ) as authorization,
        RFC008Store(paths.ledger, config=config, read_only=True) as ledger,
    ):
        status = authorization.status()
        contract = ledger.validate_collection_contract(
            config=config, authorization=status.record
        )
    assert status.lifecycle_state == "initialized"
    assert status.record.repository_head == "2" * 40
    assert contract.committed_opportunity_count == 0
    archived_authorization = archive / "old" / paths.authorization.name
    with pytest.raises(ValueError, match="Copied RFC-008 authorization"):
        CollectionAuthorizationStore(
            archived_authorization, read_only=True
        )


def test_current_pair_is_a_byte_preserving_no_op(
    tmp_path: Path, config: RFC008Config
) -> None:
    record, paths = _initialized_pair(tmp_path, config, release="new")
    before = (
        paths.authorization.read_bytes(),
        paths.ledger.read_bytes(),
        paths.authorization.stat().st_mtime_ns,
        paths.ledger.stat().st_mtime_ns,
    )
    called = False

    def factory():
        nonlocal called
        called = True
        return _record(tmp_path, config, release="new")

    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=(),
        new_authorization_factory=factory,
        initialization_cursors=CURSORS,
    )
    after = (
        paths.authorization.read_bytes(),
        paths.ledger.read_bytes(),
        paths.authorization.stat().st_mtime_ns,
        paths.ledger.stat().st_mtime_ns,
    )
    assert result["result"] == "no_op"
    assert not called
    assert before == after
    assert record.authorization_identifier == result[
        "old_authorization_identifier"
    ]
    assert not paths.archive_root.exists()


def test_dry_run_is_passive(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    before = (
        paths.authorization.read_bytes(),
        paths.ledger.read_bytes(),
        set(tmp_path.rglob("*")),
    )
    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
        new_authorization_factory=lambda: pytest.fail(
            "dry run must not issue an authorization"
        ),
        initialization_cursors=CURSORS,
        dry_run=True,
    )
    after = (
        paths.authorization.read_bytes(),
        paths.ledger.read_bytes(),
        set(tmp_path.rglob("*")),
    )
    assert result["dry_run"] is True
    assert result["eligible"] is True
    assert result["needed"] is True
    assert before == after


def test_passive_dry_run_preserves_existing_wal_shm_and_all_metadata(
    tmp_path: Path,
    config: RFC008Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    authorization_connection = sqlite3.connect(paths.authorization)
    ledger_connection = sqlite3.connect(paths.ledger)
    for connection in (authorization_connection, ledger_connection):
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
    authorization_connection.execute(
        "CREATE TABLE passive_wal_fixture(value INTEGER)"
    )
    authorization_connection.execute(
        "INSERT INTO passive_wal_fixture VALUES (1)"
    )
    authorization_connection.commit()
    ledger_connection.execute(
        "CREATE TABLE passive_wal_fixture(value INTEGER)"
    )
    ledger_connection.execute(
        "INSERT INTO passive_wal_fixture VALUES (1)"
    )
    ledger_connection.commit()
    assert Path(str(paths.authorization) + "-wal").stat().st_size > 0
    assert Path(str(paths.authorization) + "-shm").exists()
    assert Path(str(paths.ledger) + "-wal").stat().st_size > 0
    assert Path(str(paths.ledger) + "-shm").exists()
    original_temporary_directory = __import__(
        "orev3.rfc008.rotation", fromlist=["tempfile"]
    ).tempfile.TemporaryDirectory
    temporary_paths: list[Path] = []

    def tracked_temporary_directory(*args, **kwargs):
        value = original_temporary_directory(*args, **kwargs)
        temporary_paths.append(Path(value.name))
        return value

    monkeypatch.setattr(
        "orev3.rfc008.rotation.tempfile.TemporaryDirectory",
        tracked_temporary_directory,
    )
    before = _production_like_evidence(paths)
    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
        new_authorization_factory=lambda: pytest.fail(
            "dry run must not issue an authorization"
        ),
        initialization_cursors=CURSORS,
        dry_run=True,
    )
    after = _production_like_evidence(paths)
    authorization_connection.close()
    ledger_connection.close()
    assert result["eligible"] is True
    assert result["needed"] is True
    assert before == after
    assert temporary_paths
    assert all(not path.exists() for path in temporary_paths)


def test_passive_dry_run_reads_committed_wal_state_without_source_changes(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    store = RFC008Store(paths.ledger, config=config)
    store.connection.execute("PRAGMA wal_autocheckpoint=0")
    snapshot = snapshot_from_opportunity(
        make_opportunity(500_002),
        config,
        source_content_sha256="8" * 64,
    )
    assert store.insert_snapshot_and_decisions(
        snapshot, build_decisions(snapshot, config)
    )
    assert Path(str(paths.ledger) + "-wal").stat().st_size > 0
    before = _production_like_evidence(paths)
    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
        new_authorization_factory=lambda: pytest.fail(
            "ineligible dry run must not issue"
        ),
        initialization_cursors=CURSORS,
        dry_run=True,
    )
    after = _production_like_evidence(paths)
    store.close()
    assert result["eligible"] is False
    assert "ledger_stored_opportunities" in result["reasons"]
    assert "ledger_decision_snapshots" in result["reasons"]
    assert "ledger_arm_decisions" in result["reasons"]
    assert before == after


def test_passive_dry_run_preserves_empty_wal_and_existing_shm_timestamp(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    connection = sqlite3.connect(paths.ledger)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("SELECT COUNT(*) FROM collection_contract").fetchone()
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    wal = Path(str(paths.ledger) + "-wal")
    shm = Path(str(paths.ledger) + "-shm")
    assert wal.exists() and wal.stat().st_size == 0
    assert shm.exists()
    before = _production_like_evidence(paths)
    before_shm_mtime = shm.stat().st_mtime_ns
    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
        new_authorization_factory=lambda: pytest.fail("must remain passive"),
        initialization_cursors=CURSORS,
        dry_run=True,
    )
    after = _production_like_evidence(paths)
    after_shm_mtime = shm.stat().st_mtime_ns
    connection.close()
    assert result["eligible"] is True
    assert before == after
    assert before_shm_mtime == after_shm_mtime


def test_passive_dry_run_without_wal_or_shm_creates_no_sidecars(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    for database in (paths.authorization, paths.ledger):
        Path(str(database) + "-wal").unlink(missing_ok=True)
        Path(str(database) + "-shm").unlink(missing_ok=True)
    before = _production_like_evidence(paths)
    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
        new_authorization_factory=lambda: pytest.fail("must remain passive"),
        initialization_cursors=CURSORS,
        dry_run=True,
    )
    assert result["eligible"] is True
    assert before == _production_like_evidence(paths)


def test_repeated_current_release_dry_runs_are_exact_no_ops(
    tmp_path: Path, config: RFC008Config
) -> None:
    _initialized_pair(tmp_path, config, release="new")
    paths = production_rotation_paths(tmp_path)
    before = _production_like_evidence(paths)
    results = [
        rotate_production_artifacts(
            repository_root=tmp_path,
            config=config,
            release_mismatches=(),
            new_authorization_factory=lambda: pytest.fail(
                "no-op dry run must not issue"
            ),
            initialization_cursors=CURSORS,
            dry_run=True,
        )
        for _ in range(3)
    ]
    assert all(result["needed"] is False for result in results)
    assert all(result["reasons"] == ["already_current"] for result in results)
    assert before == _production_like_evidence(paths)


def test_ineligible_dry_run_is_passive(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    with CollectionAuthorizationStore(paths.authorization) as authorization:
        authorization.consume_launch(str(uuid.uuid4()))
    before = _production_like_evidence(paths)
    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
        new_authorization_factory=lambda: pytest.fail("must remain passive"),
        initialization_cursors=CURSORS,
        dry_run=True,
    )
    assert result["eligible"] is False
    assert "authorization_not_initialized" in result["reasons"]
    assert before == _production_like_evidence(paths)


def test_recovery_required_dry_run_does_not_touch_manifest_or_sources(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    paths.manifest.write_text("{}\n", encoding="utf-8")
    before = _production_like_evidence(paths)
    result = rotate_production_artifacts(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
        new_authorization_factory=lambda: pytest.fail("must remain passive"),
        initialization_cursors=CURSORS,
        dry_run=True,
    )
    assert result["recovery_required"] is True
    assert result["reasons"] == ["incomplete_rotation_requires_recovery"]
    assert before == _production_like_evidence(paths)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("authorization_active", "authorization_not_initialized"),
        ("authorization_session", "authorization_not_initialized"),
        ("ledger_active", "ledger_not_initialized"),
        ("collector_run", "ledger_historical_collector_run"),
        ("active_session", "ledger_active_session"),
    ],
)
def test_ineligible_state_fails_closed(
    tmp_path: Path,
    config: RFC008Config,
    mutation: str,
    reason: str,
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    if mutation.startswith("authorization"):
        with CollectionAuthorizationStore(paths.authorization) as store:
            store.consume_launch(str(uuid.uuid4()))
    else:
        connection = sqlite3.connect(paths.ledger)
        if mutation == "ledger_active":
            connection.execute(
                "UPDATE collection_contract SET collection_state='active'"
            )
        elif mutation == "collector_run":
            connection.execute(
                """
                INSERT INTO collector_runs(
                  run_id,started_at,ended_at,process_id,
                  configuration_fingerprint,record_json
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    str(uuid.uuid4()),
                    "2026-07-29T00:00:00+00:00",
                    "2026-07-29T00:01:00+00:00",
                    1,
                    config.configuration_fingerprint,
                    "{}",
                ),
            )
        elif mutation == "active_session":
            connection.execute(
                """
                UPDATE collection_contract
                SET collection_state='active',active_session_identity=?
                """,
                (str(uuid.uuid4()),),
            )
        connection.commit()
        connection.close()
    before = (paths.authorization.read_bytes(), paths.ledger.read_bytes())
    report = evaluate_rotation(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
    )
    assert report["eligible"] is False
    assert reason in report["reasons"]
    assert before == (paths.authorization.read_bytes(), paths.ledger.read_bytes())
    assert not paths.archive_root.exists()


def test_nonempty_ledger_and_decisions_are_refused(
    tmp_path: Path, config: RFC008Config
) -> None:
    record, paths = _initialized_pair(tmp_path, config)
    with RFC008Store(paths.ledger, config=config) as store:
        snapshot = snapshot_from_opportunity(
            make_opportunity(500_001),
            config,
            source_content_sha256="7" * 64,
        )
        assert store.insert_snapshot_and_decisions(
            snapshot, build_decisions(snapshot, config)
        )
    report = evaluate_rotation(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
    )
    assert report["eligible"] is False
    assert "ledger_stored_opportunities" in report["reasons"]
    assert "ledger_decision_snapshots" in report["reasons"]
    assert "ledger_arm_decisions" in report["reasons"]
    with CollectionAuthorizationStore(
        paths.authorization, read_only=True
    ) as authorization:
        assert authorization.status().record == record


@pytest.mark.parametrize(
    "phase,expected",
    [
        ("after_manifest", "recovered_old_pair"),
        ("after_archive", "recovered_old_pair"),
        ("after_staged_authorization", "recovered_old_pair"),
        ("after_staged_ledger", "recovered_old_pair"),
        ("after_staged_validation", "recovered_old_pair"),
        ("before_first_activation", "recovered_new_pair"),
        ("between_replacements", "recovered_new_pair"),
        ("after_activation", "recovered_new_pair"),
    ],
)
def test_every_material_crash_phase_recovers_a_complete_pair(
    tmp_path: Path,
    config: RFC008Config,
    phase: str,
    expected: str,
) -> None:
    old, paths = _initialized_pair(tmp_path, config)

    def inject(current: str) -> None:
        if current == phase:
            raise RuntimeError(f"injected:{phase}")

    with pytest.raises(RuntimeError, match=f"injected:{phase}"):
        _rotate(tmp_path, config, fault=inject)
    status = rotation_status(tmp_path)
    assert status["recovery_required"] is True
    with pytest.raises(DuplicateRFC008Writer):
        RFC008WriterLease(paths.ledger).acquire()

    result = recover_production_artifacts(
        repository_root=tmp_path, config=config
    )

    assert result["result"] == expected
    assert rotation_status(tmp_path)["recovery_required"] is False
    with (
        CollectionAuthorizationStore(
            paths.authorization, read_only=True
        ) as authorization,
        RFC008Store(paths.ledger, config=config, read_only=True) as ledger,
    ):
        authorization_status = authorization.status()
        contract = ledger.validate_collection_contract(
            config=config, authorization=authorization_status.record
        )
    assert contract.committed_opportunity_count == 0
    assert (
        authorization_status.record.authorization_identifier
        == contract.authorization_identifier
    )
    if expected == "recovered_old_pair":
        assert (
            authorization_status.record.authorization_identifier
            == old.authorization_identifier
        )
    else:
        assert (
            authorization_status.record.authorization_identifier
            != old.authorization_identifier
        )


def test_interruption_after_wal_checkpoint_is_safe_to_retry(
    tmp_path: Path, config: RFC008Config
) -> None:
    old, paths = _initialized_pair(tmp_path, config)

    def inject(phase: str) -> None:
        if phase == "after_checkpoint":
            raise RuntimeError("checkpoint interruption")

    with pytest.raises(RuntimeError, match="checkpoint interruption"):
        _rotate(tmp_path, config, fault=inject)
    assert rotation_status(tmp_path)["recovery_required"] is False
    with CollectionAuthorizationStore(
        paths.authorization, read_only=True
    ) as authorization:
        assert (
            authorization.status().record.authorization_identifier
            == old.authorization_identifier
        )
    assert _rotate(tmp_path, config)["result"] == "rotated"


def test_archive_collision_refuses_before_manifest_or_activation(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    tx = "11111111-1111-1111-1111-111111111111"
    archive = (
        paths.archive_root
        / f"2026-07-29T010203_0000_{tx}"
    )
    archive.mkdir(parents=True)
    before = (paths.authorization.read_bytes(), paths.ledger.read_bytes())
    with pytest.raises(RotationError, match="archive destination"):
        _rotate(tmp_path, config, transaction_id=tx)
    assert before == (paths.authorization.read_bytes(), paths.ledger.read_bytes())
    assert not paths.manifest.exists()


def test_symlinked_artifact_is_refused(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    original = paths.authorization.with_name("real.sqlite")
    paths.authorization.rename(original)
    paths.authorization.symlink_to(original)
    with pytest.raises(RotationError, match="Unsafe"):
        evaluate_rotation(
            repository_root=tmp_path,
            config=config,
            release_mismatches=("repository_head",),
        )


def test_archived_hash_corruption_stops_recovery(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)

    def inject(phase: str) -> None:
        if phase == "after_archive":
            raise RuntimeError("stop")

    with pytest.raises(RuntimeError):
        _rotate(tmp_path, config, fault=inject)
    active = json.loads(paths.manifest.read_text(encoding="utf-8"))
    archived_ledger = next(
        Path(item["archive_path"])
        for item in active["archived_artifacts"]
        if item["source_path"] == str(paths.ledger)
    )
    with archived_ledger.open("ab") as output:
        output.write(b"corrupt")
    paths.ledger.unlink()
    with pytest.raises(RotationError, match="hash mismatch"):
        recover_production_artifacts(
            repository_root=tmp_path, config=config
        )
    assert rotation_status(tmp_path)["recovery_required"] is True


def test_two_rotation_attempts_serialize(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    descriptor = os.open(paths.rotation_lock, os.O_CREAT | os.O_RDWR, 0o600)
    import fcntl

    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(RotationError, match="rotation is active"):
            _rotate(tmp_path, config)
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
    assert not paths.manifest.exists()


def test_launch_mutex_is_unavailable_during_rotation(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)

    def inject(phase: str) -> None:
        if phase == "after_manifest":
            with pytest.raises(DuplicateSupervisedLaunch):
                with launch_mutex(paths.ledger):
                    pass
            raise RuntimeError("stop")

    with pytest.raises(RuntimeError, match="stop"):
        _rotate(tmp_path, config, fault=inject)
    assert rotation_status(tmp_path)["recovery_required"] is True
    recover_production_artifacts(repository_root=tmp_path, config=config)


def test_active_writer_and_collector_are_refused(
    tmp_path: Path,
    config: RFC008Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    monkeypatch.setattr(
        "orev3.rfc008.rotation.writer_lease_status",
        lambda *_: {"active": True, "file_present": True},
    )
    report = evaluate_rotation(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
    )
    assert "writer_owner_active" in report["reasons"]
    monkeypatch.setattr(
        "orev3.rfc008.rotation.writer_lease_status",
        lambda *_: {"active": False, "file_present": False},
    )
    monkeypatch.setattr(
        "orev3.rfc008.rotation._collector_processes", lambda: (12345,)
    )
    report = evaluate_rotation(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("repository_head",),
    )
    assert "collector_process_active" in report["reasons"]


def test_non_release_binding_mismatch_is_refused(
    tmp_path: Path, config: RFC008Config
) -> None:
    _initialized_pair(tmp_path, config)
    report = evaluate_rotation(
        repository_root=tmp_path,
        config=config,
        release_mismatches=("canonical_ledger_path",),
    )
    assert report["eligible"] is False
    assert report["reasons"] == [
        "non_release_binding_mismatch:canonical_ledger_path"
    ]


def test_wal_shm_and_stale_runtime_artifacts_are_archived(
    tmp_path: Path, config: RFC008Config
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    connection = sqlite3.connect(paths.ledger)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "UPDATE metadata SET value=value WHERE key='ledger_state'"
    )
    connection.commit()
    assert Path(str(paths.ledger) + "-wal").exists()
    assert Path(str(paths.ledger) + "-shm").exists()
    paths.supervision_log.write_text("inactive log\n", encoding="utf-8")
    try:
        result = _rotate(tmp_path, config)
    finally:
        connection.close()
    manifest = json.loads(
        Path(str(result["manifest_path"])).read_text(encoding="utf-8")
    )
    archived_sources = {
        item["source_path"] for item in manifest["archived_artifacts"]
    }
    assert str(Path(str(paths.ledger) + "-wal")) in archived_sources
    assert str(Path(str(paths.ledger) + "-shm")) in archived_sources
    assert str(paths.supervision_log) in archived_sources


def test_interrupted_first_manifest_publication_leaves_old_pair_active(
    tmp_path: Path,
    config: RFC008Config,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, paths = _initialized_pair(tmp_path, config)
    before = (paths.authorization.read_bytes(), paths.ledger.read_bytes())
    original = __import__(
        "orev3.rfc008.rotation", fromlist=["_atomic_json"]
    )._atomic_json
    attempted = False

    def interrupted(path: Path, value: dict[str, object]) -> None:
        nonlocal attempted
        if path == paths.manifest and not attempted:
            attempted = True
            raise OSError("injected manifest publication interruption")
        original(path, value)

    monkeypatch.setattr("orev3.rfc008.rotation._atomic_json", interrupted)
    with pytest.raises(OSError, match="manifest publication"):
        _rotate(tmp_path, config)
    assert before == (paths.authorization.read_bytes(), paths.ledger.read_bytes())
    assert not paths.manifest.exists()


def test_public_command_refuses_noncanonical_artifact_paths(
    tmp_path: Path,
) -> None:
    args = SimpleNamespace(
        repository_root=str(tmp_path),
        authorization=str(tmp_path / "other-authorization.sqlite"),
        ledger=str(
            tmp_path / "data/ledger/rfc008_paper_ledger_v1.sqlite"
        ),
    )
    with pytest.raises(
        PermissionError, match="official authorization path"
    ):
        command_rotate_production_artifacts(args)
