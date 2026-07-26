from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from orev3.ledger.identifiers import canonical_json, deterministic_id
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.marker import sha256_file, verify_marker
from orev3.rfc008.schemas import FinalFreezeManifest
from orev3.rfc008.storage import RFC008Store, strict_json


FINAL_FREEZE_AUTHORIZATION = "RFC008_FINAL_FREEZE_AUTHORIZED"
SAFETY_COUNTER_NAMES = (
    "database_lock_failures",
    "skipped_records",
    "live_actions",
    "source_corruption",
)


def writer_lease_active(ledger_path: str | Path) -> bool:
    lock_path = Path(str(ledger_path) + ".writer.lock")
    if not lock_path.exists():
        return False
    descriptor = os.open(lock_path, os.O_RDWR)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        os.close(descriptor)
    return False


def logical_ledger_hash(store: RFC008Store) -> str:
    tables = (
        "metadata",
        "source_cursors",
        "source_records",
        "experiment_rounds",
        "decision_snapshots",
        "arm_decisions",
        "outcome_queue",
        "outcome_attempts",
        "finalized_outcomes",
        "outcome_conflicts",
        "round_accounting",
        "safety_audit",
        "counters",
        "collector_runs",
        "schema_migrations",
        "resolver_metadata",
    )
    values: dict[str, object] = {}
    for table in tables:
        rows = [
            tuple(row)
            for row in store.connection.execute(
                f"SELECT * FROM {table} ORDER BY rowid"
            )
        ]
        if table == "metadata":
            rows = [row for row in rows if row[0] != "ledger_state"]
        values[table] = rows
    return hashlib.sha256(canonical_json(values).encode()).hexdigest()


def _round_summary(
    store: RFC008Store,
    config: RFC008Config,
    marker_created_at: datetime,
    now: datetime,
) -> dict[str, object]:
    started = store.count("experiment_rounds")
    primary = store.count("experiment_rounds", "state='finalized_primary'")
    sensitivity = store.count(
        "experiment_rounds", "state='finalized_sensitivity'"
    )
    excluded = store.count("experiment_rounds", "state='excluded'")
    pending = store.count("outcome_queue", "state IN ('pending','resolving')")
    failed = store.count("outcome_queue", "state='failed'")
    conflicted = store.count("outcome_queue", "state='conflicted'")
    quarantined = store.count("outcome_queue", "state='quarantined'")
    unusable = excluded + failed + conflicted + quarantined + sensitivity
    counters = store.counters()
    incomplete_accounting = int(
        store.connection.execute(
            """
            SELECT COUNT(*)
            FROM experiment_rounds r
            WHERE r.state IN ('finalized_primary','finalized_sensitivity')
              AND (
                SELECT COUNT(*) FROM round_accounting a
                WHERE a.round_id=r.round_id
              ) != 5
            """
        ).fetchone()[0]
    )
    elapsed_days = (now - marker_created_at).total_seconds() / 86400
    return {
        "total_started_rounds": started,
        "eligible_rounds": max(started - excluded, 0),
        "primary_analyzable_rounds": primary,
        "pending_rounds": pending,
        "failed_rounds": failed,
        "conflicted_rounds": conflicted,
        "quarantined_rounds": quarantined,
        "excluded_rounds": excluded,
        "recovered_sensitivity_rounds": sensitivity,
        "unusable_numerator": unusable,
        "unusable_denominator": started,
        "unusable_rate": unusable / started if started else 0.0,
        "safety_counters": {
            key: counters.get(key, 0) for key in SAFETY_COUNTER_NAMES
        },
        "configuration_mismatch_count": counters.get(
            "configuration_mismatches", 0
        ),
        "marker_mismatch_count": counters.get("marker_mismatches", 0),
        "duplicate_counters": {
            "source_records": counters.get("duplicate_source_records", 0),
            "decisions": counters.get("duplicate_decisions", 0),
            "outcomes": counters.get("duplicate_outcomes", 0),
        },
        "writer_lease_violations": counters.get("writer_lease_violations", 0),
        "outcome_provenance_counts": {
            "direct_observed": store.count(
                "finalized_outcomes", "provenance='direct_observed'"
            ),
            "recovered": store.count(
                "finalized_outcomes", "provenance='recovered'"
            ),
        },
        "started_round_cap_reached": started
        >= config.criteria.maximum_started_rounds,
        "calendar_cap_reached": elapsed_days
        >= config.criteria.maximum_calendar_days,
        "incomplete_accounting_rounds": incomplete_accounting,
        "accounting_complete": incomplete_accounting == 0,
    }


def _write_manifest_pair(
    manifest: FinalFreezeManifest, path: Path
) -> str:
    sidecar = Path(str(path) + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError("Freeze manifest destination exists")
    payload = (strict_json(manifest) + "\n").encode()
    digest = hashlib.sha256(payload).hexdigest()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    sidecar_temporary = sidecar.with_name(f".{sidecar.name}.{os.getpid()}.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        for target, content in (
            (temporary, payload),
            (sidecar_temporary, f"{digest}  {path.name}\n".encode()),
        ):
            with target.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        os.link(sidecar_temporary, sidecar)
        try:
            os.link(temporary, path)
        except Exception:
            sidecar.unlink(missing_ok=True)
            raise
    finally:
        temporary.unlink(missing_ok=True)
        sidecar_temporary.unlink(missing_ok=True)
    return digest


def freeze_experiment(
    *,
    ledger_path: str | Path,
    config_path: str | Path,
    marker_path: str | Path,
    expected_marker_sha256: str,
    output_path: str | Path,
    collection_stop_reason: str,
    authorization_token: str,
    now: datetime | None = None,
) -> dict[str, object]:
    if authorization_token != FINAL_FREEZE_AUTHORIZATION:
        raise PermissionError("Explicit RFC-008 final-freeze authorization required")
    output = Path(output_path)
    if output.exists():
        config = RFC008Config.from_path(config_path)
        verify_marker(
            marker_path, config, expected_sha256=expected_marker_sha256
        )
        sidecar = Path(str(output) + ".sha256")
        if (
            not sidecar.exists()
            or sidecar.read_text(encoding="utf-8").split()[0]
            != sha256_file(output)
        ):
            raise ValueError("Existing final-freeze checksum mismatch")
        existing = verify_freeze(
            freeze_path=output,
            expected_freeze_sha256=sha256_file(output),
            ledger_path=ledger_path,
            config=config,
            marker_sha256=expected_marker_sha256,
        )
        return {
            "idempotent": True,
            "freeze_id": existing.freeze_id,
            "manifest_sha256": sha256_file(output),
        }
    if writer_lease_active(ledger_path):
        raise ValueError("Active RFC-008 writer lease blocks final freeze")
    config = RFC008Config.from_path(config_path)
    marker = verify_marker(
        marker_path, config, expected_sha256=expected_marker_sha256
    )
    current = now or datetime.now(timezone.utc)
    with RFC008Store(ledger_path, config=config) as store:
        if store.integrity() != "ok":
            raise ValueError("SQLite integrity check failed")
        if store.metadata("ledger_state") != "collecting":
            raise ValueError("Ledger is not in collecting state")
        summary = _round_summary(store, config, marker.created_at, current)
        if summary["pending_rounds"]:
            raise ValueError("Pending or resolving outcomes block final freeze")
        logical_hash = logical_ledger_hash(store)
        freeze_id = deterministic_id(
            "rfc008-final-freeze-v1",
            config.experiment_id,
            expected_marker_sha256,
            logical_hash,
            collection_stop_reason,
        )
        record = {
            "schema_version": 1,
            "freeze_id": freeze_id,
            "created_at": current.isoformat(),
            "authorization": FINAL_FREEZE_AUTHORIZATION,
            "experiment_id": config.experiment_id,
            "configuration_fingerprint": config.configuration_fingerprint,
            "marker_sha256": expected_marker_sha256,
            "ledger_sha256": logical_hash,
            "ledger_data_version": store.data_version(),
            "terminal_source_cursors": store.source_cursor_records(),
            **summary,
            "collection_stop_reason": collection_stop_reason,
            "final_freeze_authorized": True,
            "sqlite_integrity": "ok",
        }
        manifest = FinalFreezeManifest.model_validate(record)
        with store.connection:
            store.freeze(freeze_id, manifest.model_dump(mode="json"))
    digest = _write_manifest_pair(manifest, output)
    return {
        "idempotent": False,
        "freeze_id": manifest.freeze_id,
        "manifest_path": str(output),
        "manifest_sha256": digest,
        "ledger_frozen": True,
    }


def verify_freeze(
    *,
    freeze_path: str | Path,
    expected_freeze_sha256: str,
    ledger_path: str | Path,
    config: RFC008Config,
    marker_sha256: str,
) -> FinalFreezeManifest:
    path = Path(freeze_path)
    if sha256_file(path) != expected_freeze_sha256:
        raise ValueError("Final-freeze manifest SHA-256 mismatch")
    manifest = FinalFreezeManifest.model_validate_json(path.read_text())
    if manifest.configuration_fingerprint != config.configuration_fingerprint:
        raise ValueError("Final-freeze configuration mismatch")
    if manifest.marker_sha256 != marker_sha256:
        raise ValueError("Final-freeze marker mismatch")
    with RFC008Store(ledger_path, config=config, read_only=True) as store:
        if store.metadata("ledger_state") != "frozen":
            raise ValueError("RFC-008 ledger is not frozen")
        row = store.connection.execute(
            "SELECT record_json FROM final_freezes WHERE freeze_id=?",
            (manifest.freeze_id,),
        ).fetchone()
        if row is None or json.loads(row[0]) != manifest.model_dump(mode="json"):
            raise ValueError("Ledger freeze evidence mismatch")
        if logical_ledger_hash(store) != manifest.ledger_sha256:
            raise ValueError("RFC-008 ledger changed after final freeze")
    return manifest
