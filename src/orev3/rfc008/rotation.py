from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from orev3.rfc008.authorization import (
    CollectionAuthorizationRecord,
    CollectionAuthorizationStore,
    canonical_path,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.storage import (
    LedgerInitialization,
    RFC008Store,
    create_authorized_ledger,
)
from orev3.rfc008.supervision import (
    launch_mutex,
    process_matches_metadata,
    read_metadata,
    supervision_paths,
    writer_lease_status,
)


ROTATION_SCHEMA_VERSION = 1
ROTATION_COMMAND = "rotate-production-artifacts"
OFFICIAL_AUTHORIZATION = "data/ledger/rfc008_collection_authorization_v1.sqlite"
OFFICIAL_LEDGER = "data/ledger/rfc008_paper_ledger_v1.sqlite"
ACTIVE_MANIFEST = "data/ledger/rfc008_artifact_rotation_v1.json"
ARCHIVE_ROOT = "data/ledger/archive/rfc008"
RELEASE_BINDING_FIELDS = frozenset(
    {
        "branch",
        "repository_head",
        "implementation_commit",
        "active_approval_sha256",
        "immediate_predecessor_sha256",
        "approval_chain_anchor",
        "marker_sha256",
        "marker_sidecar_sha256",
        "candidate_sha256",
        "experiment_id",
        "configuration_fingerprint",
        "resolver_fingerprint",
        "migration_set_sha256",
        "cli_sha256",
        "runbook_sha256",
        "burn_in_evidence_sha256",
        "burn_in_ledger_sha256",
        "approval_manifest_sha256",
        "external_rpc_burn_in_performed",
    }
)


class RotationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RotationPaths:
    root: Path
    authorization: Path
    ledger: Path
    writer_lock: Path
    supervision_metadata: Path
    supervision_log: Path
    launch_lock: Path
    manifest: Path
    rotation_lock: Path
    archive_root: Path


@dataclass(frozen=True)
class PassiveSQLiteSnapshot:
    authorization: Path
    ledger: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def production_rotation_paths(repository_root: str | Path) -> RotationPaths:
    root = Path(repository_root).resolve()
    authorization = root / OFFICIAL_AUTHORIZATION
    ledger = root / OFFICIAL_LEDGER
    runtime = supervision_paths(ledger)
    return RotationPaths(
        root=root,
        authorization=authorization,
        ledger=ledger,
        writer_lock=Path(str(ledger) + ".writer.lock"),
        supervision_metadata=runtime["metadata"],
        supervision_log=runtime["log"],
        launch_lock=runtime["launch_lock"],
        manifest=root / ACTIVE_MANIFEST,
        rotation_lock=root / "data/ledger/rfc008_artifact_rotation_v1.lock",
        archive_root=root / ARCHIVE_ROOT,
    )


def rotation_status(repository_root: str | Path) -> dict[str, object]:
    paths = production_rotation_paths(repository_root)
    if not paths.manifest.exists():
        return {
            "recovery_required": False,
            "manifest_path": str(paths.manifest),
            "phase": None,
            "rotation_transaction_id": None,
        }
    try:
        value = _read_manifest(paths.manifest)
        return {
            "recovery_required": value.get("completion_state")
            not in {"completed", "rolled_back"},
            "manifest_path": str(paths.manifest),
            "phase": value.get("phase"),
            "rotation_transaction_id": value.get(
                "rotation_transaction_id"
            ),
        }
    except Exception:
        return {
            "recovery_required": True,
            "manifest_path": str(paths.manifest),
            "phase": "malformed",
            "rotation_transaction_id": None,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False}
    _regular(path)
    value = os.lstat(path)
    return {
        "exists": True,
        "device": value.st_dev,
        "inode": value.st_ino,
        "size": value.st_size,
        "mtime_ns": value.st_mtime_ns,
        "ctime_ns": value.st_ctime_ns,
        "mode": stat.S_IMODE(value.st_mode),
        "uid": value.st_uid,
        "gid": value.st_gid,
        "sha256": _sha256(path),
    }


def _regular(path: Path, *, required: bool = True) -> bool:
    if not path.exists():
        if required:
            raise RotationError(f"Required RFC-008 artifact is absent: {path}")
        return False
    value = os.lstat(path)
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise RotationError(f"Unsafe RFC-008 artifact refused: {path}")
    return True


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    encoded = (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
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
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _read_manifest(path: Path) -> dict[str, object]:
    _regular(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RotationError("RFC-008 rotation manifest is not an object")
    if raw.get("manifest_schema_version") != ROTATION_SCHEMA_VERSION:
        raise RotationError("RFC-008 rotation manifest version mismatch")
    transaction_id = raw.get("rotation_transaction_id")
    try:
        if str(uuid.UUID(str(transaction_id))) != transaction_id:
            raise ValueError
    except ValueError as exc:
        raise RotationError("RFC-008 rotation transaction ID is invalid") from exc
    return raw


def _copy_exact(source: Path, target: Path) -> None:
    _regular(source)
    if target.exists():
        raise RotationError(f"RFC-008 archive collision: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    try:
        with source.open("rb") as reader:
            while chunk := reader.read(1024 * 1024):
                os.write(descriptor, chunk)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if _sha256(source) != _sha256(target):
        raise RotationError("RFC-008 archived artifact hash mismatch")
    _fsync_directory(target.parent)


def _sqlite_file_set(path: Path) -> tuple[Path, ...]:
    return (
        path,
        Path(str(path) + "-wal"),
        Path(str(path) + "-shm"),
    )


@contextmanager
def _passive_sqlite_snapshot(
    paths: RotationPaths,
) -> Iterator[PassiveSQLiteSnapshot]:
    sources = (
        *_sqlite_file_set(paths.authorization),
        *_sqlite_file_set(paths.ledger),
    )
    before = {source: _source_fingerprint(source) for source in sources}
    with tempfile.TemporaryDirectory(
        prefix="rfc008-passive-rotation-"
    ) as temporary_raw:
        temporary = Path(temporary_raw)
        snapshot_authorization = temporary / paths.authorization.name
        snapshot_ledger = temporary / paths.ledger.name
        mapping = {
            paths.authorization: snapshot_authorization,
            paths.ledger: snapshot_ledger,
        }
        for source, target in tuple(mapping.items()):
            for suffix in ("", "-wal", "-shm"):
                source_file = Path(str(source) + suffix)
                if before[source_file]["exists"]:
                    target_file = Path(str(target) + suffix)
                    with source_file.open("rb") as reader, target_file.open(
                        "xb"
                    ) as writer:
                        shutil.copyfileobj(reader, writer)
                    os.chmod(target_file, 0o600)
                    if _sha256(target_file) != before[source_file]["sha256"]:
                        raise RotationError(
                            "RFC-008 passive SQLite snapshot hash mismatch"
                        )
        after_copy = {
            source: _source_fingerprint(source) for source in sources
        }
        if after_copy != before:
            raise RotationError(
                "RFC-008 SQLite source changed during passive snapshot"
            )
        yield PassiveSQLiteSnapshot(
            authorization=snapshot_authorization,
            ledger=snapshot_ledger,
        )
    after = {source: _source_fingerprint(source) for source in sources}
    if after != before:
        raise RotationError(
            "RFC-008 SQLite source changed during passive inspection"
        )


def _replace_from_copy(source: Path, target: Path) -> None:
    _regular(source)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.rotate")
    try:
        _copy_exact(source, temporary)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
        _fsync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _rotation_mutex(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        value = os.fstat(descriptor)
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            raise RotationError("Unsafe RFC-008 rotation lock")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RotationError(
                "Another RFC-008 production artifact rotation is active"
            ) from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _collector_processes() -> tuple[int, ...]:
    output = subprocess.run(
        ("ps", "-axo", "pid=,command="),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return tuple(
        int(line.strip().split(None, 1)[0])
        for line in output.splitlines()
        if "orev3.rfc008.cli" in line
        and (
            "__run-supervised" in line
            or " rfc008.cli start " in f" {line} "
        )
        and int(line.strip().split(None, 1)[0]) != os.getpid()
    )


def _checkpoint(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        result = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if result is not None and int(result[0]) != 0:
            raise RotationError("RFC-008 WAL checkpoint remained busy")
    finally:
        connection.close()


def _authorization_eligibility(
    path: Path,
    *,
    identity_path: Path | None = None,
) -> tuple[object, list[str]]:
    failures: list[str] = []
    try:
        with CollectionAuthorizationStore(
            path,
            read_only=True,
            identity_path=identity_path,
        ) as store:
            if store.connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                failures.append("authorization_integrity")
            status = store.status()
            history = tuple(
                str(row[0])
                for row in store.connection.execute(
                    "SELECT action FROM authorization_events ORDER BY event_index"
                )
            )
    except Exception as exc:
        raise RotationError("RFC-008 authorization validation failed") from exc
    if status.lifecycle_state != "initialized":
        failures.append("authorization_not_initialized")
    if status.record.collection_target != 600:
        failures.append("authorization_target")
    if status.launch_consumed_at is not None:
        failures.append("authorization_launch_consumed")
    if status.consuming_session_identity is not None:
        failures.append("authorization_session")
    if status.completed_at is not None or status.failed_at is not None:
        failures.append("authorization_terminal")
    if status.recovery_count != 0:
        failures.append("authorization_recovery_history")
    prohibited = {
        "launch_consumed",
        "recovery",
        "completed",
        "failed",
    }
    if prohibited.intersection(history):
        failures.append("authorization_historical_use")
    return status, failures


def _ledger_eligibility(
    path: Path,
    *,
    config: RFC008Config,
    authorization: CollectionAuthorizationRecord,
    identity_path: Path | None = None,
) -> tuple[object, list[str]]:
    failures: list[str] = []
    try:
        with RFC008Store(
            path,
            config=config,
            read_only=True,
            identity_path=identity_path,
        ) as store:
            if store.integrity() != "ok":
                failures.append("ledger_integrity")
            contract = store.validate_collection_contract(
                config=config, authorization=authorization
            )
            counts = {
                table: store.count(table)
                for table in (
                    "decision_snapshots",
                    "arm_decisions",
                    "experiment_rounds",
                    "outcome_queue",
                    "finalized_outcomes",
                    "outcome_conflicts",
                    "round_accounting",
                    "source_records",
                )
            }
            run_count = int(
                store.connection.execute(
                    "SELECT COUNT(*) FROM collector_runs"
                ).fetchone()[0]
            )
            open_runs = int(
                store.connection.execute(
                    "SELECT COUNT(*) FROM collector_runs WHERE ended_at IS NULL"
                ).fetchone()[0]
            )
    except Exception as exc:
        raise RotationError("RFC-008 ledger validation failed") from exc
    if contract.collection_state != "initialized":
        failures.append("ledger_not_initialized")
    if contract.committed_opportunity_count != 0:
        failures.append("ledger_stored_opportunities")
    if contract.collection_target != 600:
        failures.append("ledger_target")
    if contract.last_committed_opportunity_identity is not None:
        failures.append("ledger_last_identity")
    if contract.active_session_identity is not None:
        failures.append("ledger_active_session")
    failures.extend(f"ledger_{name}" for name, count in counts.items() if count)
    if run_count:
        failures.append("ledger_historical_collector_run")
    if open_runs:
        failures.append("ledger_open_collector_run")
    return contract, failures


def _runtime_eligibility(paths: RotationPaths) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    optional: list[str] = []
    lease = writer_lease_status(paths.ledger)
    if lease["active"]:
        failures.append("writer_owner_active")
    if lease["file_present"]:
        optional.append(str(paths.writer_lock))
    metadata = read_metadata(paths.supervision_metadata)
    if metadata is not None:
        optional.append(str(paths.supervision_metadata))
        if process_matches_metadata(metadata):
            failures.append("supervision_metadata_active")
    if paths.supervision_log.exists():
        _regular(paths.supervision_log)
        optional.append(str(paths.supervision_log))
        if metadata is not None:
            failures.append("collector_log_session_present")
    if _collector_processes():
        failures.append("collector_process_active")
    return failures, optional


def evaluate_rotation(
    *,
    repository_root: str | Path,
    config: RFC008Config,
    release_mismatches: tuple[str, ...],
    passive: bool = False,
) -> dict[str, object]:
    paths = production_rotation_paths(repository_root)
    if rotation_status(repository_root)["recovery_required"]:
        return {
            "eligible": False,
            "needed": False,
            "recovery_required": True,
            "reasons": ["incomplete_rotation_requires_recovery"],
            "release_mismatches": list(release_mismatches),
            "artifacts_to_archive": [],
            "archive_directory_pattern": str(
                paths.archive_root / "<UTC>_<rotation-uuid>"
            ),
        }
    _regular(paths.authorization)
    _regular(paths.ledger)
    runtime_failures, optional = _runtime_eligibility(paths)
    if passive:
        with _passive_sqlite_snapshot(paths) as snapshot:
            authorization, failures = _authorization_eligibility(
                snapshot.authorization,
                identity_path=paths.authorization,
            )
            contract, ledger_failures = _ledger_eligibility(
                snapshot.ledger,
                config=config,
                authorization=authorization.record,
                identity_path=paths.ledger,
            )
    else:
        authorization, failures = _authorization_eligibility(
            paths.authorization
        )
        contract, ledger_failures = _ledger_eligibility(
            paths.ledger,
            config=config,
            authorization=authorization.record,
        )
    failures.extend(ledger_failures)
    failures.extend(runtime_failures)
    if contract.ledger_instance_identifier != (
        authorization.record.ledger_instance_identifier
    ):
        failures.append("authorization_ledger_identity")
    unsupported = sorted(set(release_mismatches) - RELEASE_BINDING_FIELDS)
    if unsupported:
        failures.append("non_release_binding_mismatch:" + ",".join(unsupported))
    needed = bool(release_mismatches)
    artifacts = [str(paths.authorization), str(paths.ledger)]
    for suffix in ("-wal", "-shm"):
        candidate = Path(str(paths.authorization) + suffix)
        if candidate.exists():
            _regular(candidate)
            artifacts.append(str(candidate))
        candidate = Path(str(paths.ledger) + suffix)
        if candidate.exists():
            _regular(candidate)
            artifacts.append(str(candidate))
    artifacts.extend(optional)
    return {
        "eligible": not failures,
        "needed": needed,
        "recovery_required": False,
        "reasons": failures or (["already_current"] if not needed else []),
        "release_mismatches": list(release_mismatches),
        "artifacts_to_archive": artifacts,
        "archive_directory_pattern": str(
            paths.archive_root / "<UTC>_<rotation-uuid>"
        ),
        "old_authorization_identifier": (
            authorization.record.authorization_identifier
        ),
        "old_ledger_identifier": contract.ledger_instance_identifier,
    }


def _update_manifest(
    paths: RotationPaths,
    archive_manifest: Path,
    manifest: dict[str, object],
    *,
    phase: str,
) -> None:
    manifest["phase"] = phase
    _atomic_json(paths.manifest, manifest)
    _atomic_json(archive_manifest, manifest)


def _validate_pair(
    *,
    authorization_path: Path,
    ledger_path: Path,
    identity_authorization_path: Path,
    identity_ledger_path: Path,
    config: RFC008Config,
) -> tuple[object, object]:
    with (
        CollectionAuthorizationStore(
            authorization_path,
            read_only=True,
            identity_path=identity_authorization_path,
        ) as authorization_store,
        RFC008Store(
            ledger_path,
            config=config,
            read_only=True,
            identity_path=identity_ledger_path,
        ) as ledger_store,
    ):
        authorization = authorization_store.status()
        contract = ledger_store.validate_collection_contract(
            config=config, authorization=authorization.record
        )
        if authorization.lifecycle_state != "initialized":
            raise RotationError("Staged authorization is not initialized")
        if contract.collection_state != "initialized":
            raise RotationError("Staged ledger is not initialized")
        if contract.committed_opportunity_count != 0:
            raise RotationError("Staged ledger is not empty")
        if ledger_store.count("decision_snapshots") or ledger_store.count(
            "arm_decisions"
        ):
            raise RotationError("Staged ledger contains decisions")
        if ledger_store.integrity() != "ok":
            raise RotationError("Staged ledger integrity failed")
        return authorization, contract


def _archive_artifacts(
    artifacts: list[str], archive: Path
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for raw in artifacts:
        source = Path(raw)
        if not source.exists():
            continue
        _regular(source)
        target = archive / "old" / source.name
        _copy_exact(source, target)
        result.append(
            {
                "source_path": str(source),
                "archive_path": str(target),
                "sha256": _sha256(target),
                "size": target.stat().st_size,
            }
        )
    return result


def _fault(callback: Callable[[str], None] | None, phase: str) -> None:
    if callback is not None:
        callback(phase)


def rotate_production_artifacts(
    *,
    repository_root: str | Path,
    config: RFC008Config,
    release_mismatches: tuple[str, ...],
    new_authorization_factory: Callable[[], CollectionAuthorizationRecord],
    initialization_cursors: tuple[dict[str, object], ...],
    dry_run: bool = False,
    recover: bool = False,
    fault: Callable[[str], None] | None = None,
    transaction_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, object]:
    paths = production_rotation_paths(repository_root)
    if dry_run:
        return {
            "command": ROTATION_COMMAND,
            "dry_run": True,
            **evaluate_rotation(
                repository_root=repository_root,
                config=config,
                release_mismatches=release_mismatches,
                passive=True,
            ),
        }
    if not recover:
        passive = evaluate_rotation(
            repository_root=repository_root,
            config=config,
            release_mismatches=release_mismatches,
            passive=True,
        )
        if passive["recovery_required"]:
            raise RotationError("Incomplete RFC-008 rotation requires recovery")
        if not passive["eligible"]:
            raise RotationError(
                "RFC-008 production artifact rotation is ineligible: "
                + ",".join(str(value) for value in passive["reasons"])
            )
        if not passive["needed"]:
            return {
                "command": ROTATION_COMMAND,
                "dry_run": False,
                "result": "no_op",
                **passive,
            }
    with _rotation_mutex(paths.rotation_lock), launch_mutex(paths.ledger):
        if recover:
            return recover_production_artifacts(
                repository_root=repository_root,
                config=config,
                _locks_held=True,
            )
        eligibility = evaluate_rotation(
            repository_root=repository_root,
            config=config,
            release_mismatches=release_mismatches,
        )
        if eligibility["recovery_required"] or not eligibility["eligible"]:
            raise RotationError(
                "RFC-008 rotation eligibility changed before maintenance"
            )
        _checkpoint(paths.authorization)
        _checkpoint(paths.ledger)
        _fault(fault, "after_checkpoint")
        refreshed = evaluate_rotation(
            repository_root=repository_root,
            config=config,
            release_mismatches=release_mismatches,
        )
        if not refreshed["eligible"] or not refreshed["needed"]:
            raise RotationError("RFC-008 rotation eligibility changed under lock")
        tx = transaction_id or str(uuid.uuid4())
        if str(uuid.UUID(tx)) != tx:
            raise RotationError("RFC-008 rotation transaction ID is invalid")
        timestamp = created_at or utc_now()
        directory_name = (
            timestamp.replace(":", "").replace("+", "_").replace(".", "_")
            + "_"
            + tx
        )
        archive = paths.archive_root / directory_name
        if archive.exists():
            raise RotationError("RFC-008 archive destination already exists")
        archive.mkdir(parents=True)
        _fsync_directory(archive.parent)
        archive_manifest = archive / "rotation_manifest.json"
        manifest: dict[str, object] = {
            "manifest_schema_version": ROTATION_SCHEMA_VERSION,
            "artifact_type": "rfc008_production_artifact_rotation",
            "command": ROTATION_COMMAND,
            "rotation_transaction_id": tx,
            "created_at": timestamp,
            "completed_at": None,
            "phase": "manifest_created",
            "completion_state": "in_progress",
            "recovery_state": "not_required",
            "repository_root": str(paths.root),
            "target": 600,
            "eligibility": refreshed,
            "old": {},
            "new": {},
            "archived_artifacts": [],
            "staged_validation": {},
            "activation_result": {},
            "final_status": {},
            "archive_directory": str(archive),
        }
        _update_manifest(
            paths, archive_manifest, manifest, phase="manifest_created"
        )
        _fault(fault, "after_manifest")
        archived = _archive_artifacts(
            list(refreshed["artifacts_to_archive"]), archive
        )
        manifest["archived_artifacts"] = archived
        old_auth = next(
            item for item in archived if item["source_path"] == str(paths.authorization)
        )
        old_ledger = next(
            item for item in archived if item["source_path"] == str(paths.ledger)
        )
        with CollectionAuthorizationStore(
            paths.authorization, read_only=True
        ) as old_authorization:
            old_authorization_status = old_authorization.status()
        with RFC008Store(
            paths.ledger, config=config, read_only=True
        ) as old_store:
            old_contract = old_store.validate_collection_contract(
                config=config,
                authorization=old_authorization_status.record,
            )
        manifest["old"] = {
            "branch": old_authorization_status.record.branch,
            "head": old_authorization_status.record.repository_head,
            "implementation_commit": (
                old_authorization_status.record.implementation_commit
            ),
            "active_approval_sha256": (
                old_authorization_status.record.active_approval_sha256
            ),
            "authorization_identifier": (
                old_authorization_status.record.authorization_identifier
            ),
            "authorization_path": str(paths.authorization),
            "authorization_sha256": old_auth["sha256"],
            "ledger_identifier": old_contract.ledger_instance_identifier,
            "ledger_path": str(paths.ledger),
            "ledger_sha256": old_ledger["sha256"],
            "writer_lock_path": str(paths.writer_lock),
            "writer_lock_sha256": next(
                (
                    item["sha256"]
                    for item in archived
                    if item["source_path"] == str(paths.writer_lock)
                ),
                None,
            ),
        }
        _update_manifest(paths, archive_manifest, manifest, phase="archived")
        _fault(fault, "after_archive")
        stage = archive / "staging"
        stage.mkdir()
        stage_authorization = stage / "authorization.sqlite"
        stage_ledger = stage / "ledger.sqlite"
        record = new_authorization_factory()
        if record.authorization_storage_path != canonical_path(
            paths.authorization
        ) or record.canonical_ledger_path != canonical_path(paths.ledger):
            raise RotationError("New authorization is not bound to production")
        CollectionAuthorizationStore.issue(
            stage_authorization,
            record,
            identity_path=paths.authorization,
        )
        with CollectionAuthorizationStore(
            stage_authorization, identity_path=paths.authorization
        ) as authorization:
            authorization.consume_initialization()
        _update_manifest(
            paths, archive_manifest, manifest, phase="staged_authorization"
        )
        _fault(fault, "after_staged_authorization")
        create_authorized_ledger(
            stage_ledger,
            config=config,
            initialization=LedgerInitialization(
                authorization=record,
                collection_seed_cursors=initialization_cursors,
                publication_cursors=initialization_cursors,
            ),
            identity_path=paths.ledger,
        )
        with CollectionAuthorizationStore(
            stage_authorization, identity_path=paths.authorization
        ) as authorization:
            authorization.mark_initialized()
        _update_manifest(paths, archive_manifest, manifest, phase="staged_ledger")
        _fault(fault, "after_staged_ledger")
        staged_authorization, staged_contract = _validate_pair(
            authorization_path=stage_authorization,
            ledger_path=stage_ledger,
            identity_authorization_path=paths.authorization,
            identity_ledger_path=paths.ledger,
            config=config,
        )
        manifest["new"] = {
            "branch": record.branch,
            "head": record.repository_head,
            "implementation_commit": record.implementation_commit,
            "active_approval_sha256": record.active_approval_sha256,
            "authorization_identifier": record.authorization_identifier,
            "authorization_sha256": _sha256(stage_authorization),
            "ledger_identifier": staged_contract.ledger_instance_identifier,
            "ledger_sha256": _sha256(stage_ledger),
            "staged_authorization_path": str(stage_authorization),
            "staged_ledger_path": str(stage_ledger),
        }
        manifest["staged_validation"] = {
            "authorization_state": staged_authorization.lifecycle_state,
            "ledger_state": staged_contract.collection_state,
            "stored_count": staged_contract.committed_opportunity_count,
            "canonical_count": 0,
            "sqlite_integrity": "ok",
            "binding_valid": True,
        }
        _update_manifest(
            paths, archive_manifest, manifest, phase="staged_validated"
        )
        _fault(fault, "after_staged_validation")
        _update_manifest(
            paths, archive_manifest, manifest, phase="activation_started"
        )
        _fault(fault, "before_first_activation")
        _replace_from_copy(stage_authorization, paths.authorization)
        _update_manifest(
            paths, archive_manifest, manifest, phase="authorization_activated"
        )
        _fault(fault, "between_replacements")
        _replace_from_copy(stage_ledger, paths.ledger)
        for sidecar in (
            Path(str(paths.authorization) + "-wal"),
            Path(str(paths.authorization) + "-shm"),
            Path(str(paths.ledger) + "-wal"),
            Path(str(paths.ledger) + "-shm"),
            paths.writer_lock,
            paths.supervision_metadata,
            paths.supervision_log,
        ):
            sidecar.unlink(missing_ok=True)
        _update_manifest(
            paths, archive_manifest, manifest, phase="pair_activated"
        )
        _fault(fault, "after_activation")
        active_authorization, active_contract = _validate_pair(
            authorization_path=paths.authorization,
            ledger_path=paths.ledger,
            identity_authorization_path=paths.authorization,
            identity_ledger_path=paths.ledger,
            config=config,
        )
        if (
            _sha256(paths.authorization)
            != manifest["new"]["authorization_sha256"]
            or _sha256(paths.ledger) != manifest["new"]["ledger_sha256"]
        ):
            raise RotationError("Activated RFC-008 artifact hash mismatch")
        manifest["activation_result"] = {
            "complete_pair": True,
            "authorization_identifier": (
                active_authorization.record.authorization_identifier
            ),
            "ledger_identifier": active_contract.ledger_instance_identifier,
            "mixed_pair_prevented_by_active_manifest": True,
        }
        manifest["final_status"] = {
            "authorization_state": active_authorization.lifecycle_state,
            "ledger_state": active_contract.collection_state,
            "stored_count": active_contract.committed_opportunity_count,
            "canonical_count": 0,
            "ready_for_collection_preflight": True,
        }
        manifest["completion_state"] = "completed"
        manifest["recovery_state"] = "not_required"
        manifest["completed_at"] = utc_now()
        _update_manifest(paths, archive_manifest, manifest, phase="completed")
        paths.manifest.unlink()
        _fsync_directory(paths.manifest.parent)
        return {
            "command": ROTATION_COMMAND,
            "dry_run": False,
            "result": "rotated",
            "rotation_transaction_id": tx,
            "archive_directory": str(archive),
            "manifest_path": str(archive_manifest),
            "old_authorization_identifier": eligibility[
                "old_authorization_identifier"
            ],
            "new_authorization_identifier": record.authorization_identifier,
            "old_ledger_identifier": eligibility["old_ledger_identifier"],
            "new_ledger_identifier": active_contract.ledger_instance_identifier,
            "authorization_sha256": _sha256(paths.authorization),
            "ledger_sha256": _sha256(paths.ledger),
            "recovery_required": False,
        }


def recover_production_artifacts(
    *,
    repository_root: str | Path,
    config: RFC008Config,
    _locks_held: bool = False,
) -> dict[str, object]:
    paths = production_rotation_paths(repository_root)
    if not _locks_held:
        with _rotation_mutex(paths.rotation_lock), launch_mutex(paths.ledger):
            return recover_production_artifacts(
                repository_root=repository_root,
                config=config,
                _locks_held=True,
            )
    manifest = _read_manifest(paths.manifest)
    archive_manifest = (
        Path(str(manifest["archive_directory"])) / "rotation_manifest.json"
    )
    phase = str(manifest["phase"])
    old = dict(manifest.get("old") or {})
    new = dict(manifest.get("new") or {})
    if phase in {
        "manifest_created",
        "archived",
        "staged_authorization",
        "staged_ledger",
        "staged_validated",
    }:
        archived = {
            str(item["source_path"]): item
            for item in manifest.get("archived_artifacts", [])
        }
        for target in (paths.authorization, paths.ledger):
            item = archived.get(str(target))
            if item is None:
                if not target.exists():
                    raise RotationError("Old RFC-008 pair cannot be recovered")
                continue
            source = Path(str(item["archive_path"]))
            if _sha256(source) != item["sha256"]:
                raise RotationError("Archived RFC-008 evidence hash mismatch")
            if not target.exists() or _sha256(target) != item["sha256"]:
                _replace_from_copy(source, target)
        with CollectionAuthorizationStore(
            paths.authorization, read_only=True
        ) as authorization_store:
            authorization = authorization_store.status()
        with RFC008Store(
            paths.ledger, config=config, read_only=True
        ) as ledger_store:
            ledger_store.validate_collection_contract(
                config=config, authorization=authorization.record
            )
        manifest["completion_state"] = "rolled_back"
        manifest["recovery_state"] = "old_pair_restored"
        manifest["completed_at"] = utc_now()
        _update_manifest(
            paths, archive_manifest, manifest, phase="rolled_back"
        )
        paths.manifest.unlink()
        _fsync_directory(paths.manifest.parent)
        return {
            "result": "recovered_old_pair",
            "rotation_transaction_id": manifest["rotation_transaction_id"],
            "recovery_required": False,
        }
    if phase not in {
        "activation_started",
        "authorization_activated",
        "pair_activated",
        "completed",
    }:
        raise RotationError("Unknown RFC-008 rotation recovery phase")
    stage_authorization = Path(str(new["staged_authorization_path"]))
    stage_ledger = Path(str(new["staged_ledger_path"]))
    if (
        _sha256(stage_authorization) != new["authorization_sha256"]
        or _sha256(stage_ledger) != new["ledger_sha256"]
    ):
        raise RotationError("Staged RFC-008 recovery artifact hash mismatch")
    _validate_pair(
        authorization_path=stage_authorization,
        ledger_path=stage_ledger,
        identity_authorization_path=paths.authorization,
        identity_ledger_path=paths.ledger,
        config=config,
    )
    _replace_from_copy(stage_authorization, paths.authorization)
    _replace_from_copy(stage_ledger, paths.ledger)
    for sidecar in (
        Path(str(paths.authorization) + "-wal"),
        Path(str(paths.authorization) + "-shm"),
        Path(str(paths.ledger) + "-wal"),
        Path(str(paths.ledger) + "-shm"),
        paths.writer_lock,
        paths.supervision_metadata,
        paths.supervision_log,
    ):
        sidecar.unlink(missing_ok=True)
    _validate_pair(
        authorization_path=paths.authorization,
        ledger_path=paths.ledger,
        identity_authorization_path=paths.authorization,
        identity_ledger_path=paths.ledger,
        config=config,
    )
    manifest["completion_state"] = "completed"
    manifest["recovery_state"] = "new_pair_activation_completed"
    manifest["completed_at"] = utc_now()
    _update_manifest(paths, archive_manifest, manifest, phase="completed")
    paths.manifest.unlink()
    _fsync_directory(paths.manifest.parent)
    return {
        "result": "recovered_new_pair",
        "rotation_transaction_id": manifest["rotation_transaction_id"],
        "recovery_required": False,
    }
