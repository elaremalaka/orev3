from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orev3.ledger.identifiers import canonical_json, deterministic_id


AUTHORIZATION_APPLICATION_ID = 0x4F523841
AUTHORIZATION_SCHEMA_VERSION = 1
RFC_IDENTIFIER = "RFC-008"
COLLECTION_MODE = "paper"
COLLECTION_TARGET = 600


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_path(path: str | Path) -> str:
    return str(Path(path).resolve())


def path_identity(path: str | Path) -> str:
    return hashlib.sha256(canonical_path(path).encode("utf-8")).hexdigest()


def experiment_identity_sha256(experiment_id: str, protocol_version: str) -> str:
    value = canonical_json(
        {
            "experiment_id": experiment_id,
            "protocol_version": protocol_version,
        }
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _strict_object(raw: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("Authorization JSON must be an object")
    return value


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CollectionAuthorizationRecord(StrictFrozenModel):
    authorization_schema_version: Literal[1] = 1
    rfc_identifier: Literal["RFC-008"] = "RFC-008"
    authorization_identifier: str = Field(min_length=36, max_length=64)
    authorization_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_storage_path: str
    authorization_storage_path_identity: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    nonce: str
    created_at: str
    expires_at: str | None = None
    branch: str
    repository_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    active_approval_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    immediate_predecessor_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_chain_anchor: str = Field(pattern=r"^[0-9a-f]{64}$")
    marker_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    marker_sidecar_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    experiment_id: str
    experiment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolver_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    migration_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cli_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runbook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    burn_in_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    burn_in_ledger_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    external_rpc_burn_in_performed: Literal[True] = True
    ledger_family_identifier: Literal["orev3-rfc008"] = "orev3-rfc008"
    ledger_instance_identifier: str = Field(min_length=36, max_length=64)
    canonical_ledger_path: str
    canonical_ledger_path_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    collection_mode: Literal["paper"] = "paper"
    collection_target: Literal[600] = 600
    production_ledger_initialization_authorized: Literal[True] = True
    collector_launch_authorized: Literal[True] = True
    collection_start_authorized: Literal[True] = True
    analysis_authorized: Literal[False] = False
    freeze_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    wallet_authorized: Literal[False] = False
    transaction_authorized: Literal[False] = False
    live_mining_authorized: Literal[False] = False
    initial_lifecycle_state: Literal["issued"] = "issued"

    @model_validator(mode="after")
    def validate_identities(self):
        if self.authorization_storage_path != canonical_path(
            self.authorization_storage_path
        ):
            raise ValueError("Authorization storage path must be canonical")
        if self.authorization_storage_path_identity != path_identity(
            self.authorization_storage_path
        ):
            raise ValueError("Authorization storage path identity mismatch")
        if self.canonical_ledger_path != canonical_path(
            self.canonical_ledger_path
        ):
            raise ValueError("Ledger path must be canonical")
        if self.canonical_ledger_path_identity != path_identity(
            self.canonical_ledger_path
        ):
            raise ValueError("Ledger path identity mismatch")
        expected_id = deterministic_id(
            "rfc008-collection-authorization",
            self.nonce,
            self.active_approval_sha256,
            self.marker_sha256,
            self.canonical_ledger_path_identity,
            str(self.collection_target),
        )
        if self.authorization_identifier != expected_id:
            raise ValueError("Authorization identifier mismatch")
        expected_ledger = deterministic_id(
            "rfc008-ledger-instance",
            self.authorization_identifier,
            self.canonical_ledger_path_identity,
        )
        if self.ledger_instance_identifier != expected_ledger:
            raise ValueError("Ledger instance identifier mismatch")
        payload = self.model_dump(
            mode="json", exclude={"authorization_digest"}
        )
        digest = hashlib.sha256(
            canonical_json(payload).encode("utf-8")
        ).hexdigest()
        if self.authorization_digest != digest:
            raise ValueError("Authorization digest mismatch")
        return self


class AuthorizationStatus(StrictFrozenModel):
    record: CollectionAuthorizationRecord
    lifecycle_state: Literal[
        "issued",
        "initialization_consumed",
        "initialized",
        "active",
        "completed",
        "failed",
    ]
    updated_at: str
    initialization_consumed_at: str | None
    initialized_at: str | None
    launch_consumed_at: str | None
    completed_at: str | None
    failed_at: str | None
    consuming_ledger_identity: str | None
    consuming_session_identity: str | None
    recovery_count: int = Field(ge=0)


def build_authorization_record(
    *,
    authorization_path: str | Path,
    ledger_path: str | Path,
    branch: str,
    repository_head: str,
    implementation_commit: str,
    active_approval_sha256: str,
    immediate_predecessor_sha256: str,
    approval_chain_anchor: str,
    marker_sha256: str,
    marker_sidecar_sha256: str,
    candidate_sha256: str,
    experiment_id: str,
    protocol_version: str,
    configuration_fingerprint: str,
    resolver_fingerprint: str,
    migration_set_sha256: str,
    cli_sha256: str,
    runbook_sha256: str,
    burn_in_evidence_sha256: str,
    burn_in_ledger_sha256: str,
    approval_manifest_sha256: str,
    external_rpc_burn_in_performed: bool,
    nonce: str | None = None,
    created_at: str | None = None,
) -> CollectionAuthorizationRecord:
    if external_rpc_burn_in_performed is not True:
        raise ValueError("Operational RPC burn-in evidence is required")
    authorization_storage_path = canonical_path(authorization_path)
    canonical_ledger_path = canonical_path(ledger_path)
    if authorization_storage_path == canonical_ledger_path:
        raise ValueError(
            "Authorization and ledger paths must be separate"
        )
    if not authorization_storage_path.endswith(".sqlite"):
        raise ValueError("Authorization storage must use a SQLite path")
    unique = nonce or str(uuid.uuid4())
    authorization_identifier = deterministic_id(
        "rfc008-collection-authorization",
        unique,
        active_approval_sha256,
        marker_sha256,
        path_identity(canonical_ledger_path),
        str(COLLECTION_TARGET),
    )
    payload: dict[str, Any] = {
        "authorization_schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "rfc_identifier": RFC_IDENTIFIER,
        "authorization_identifier": authorization_identifier,
        "authorization_storage_path": authorization_storage_path,
        "authorization_storage_path_identity": path_identity(
            authorization_storage_path
        ),
        "nonce": unique,
        "created_at": created_at or utc_now(),
        "expires_at": None,
        "branch": branch,
        "repository_head": repository_head,
        "implementation_commit": implementation_commit,
        "active_approval_sha256": active_approval_sha256,
        "immediate_predecessor_sha256": immediate_predecessor_sha256,
        "approval_chain_anchor": approval_chain_anchor,
        "marker_sha256": marker_sha256,
        "marker_sidecar_sha256": marker_sidecar_sha256,
        "candidate_sha256": candidate_sha256,
        "experiment_id": experiment_id,
        "experiment_sha256": experiment_identity_sha256(
            experiment_id, protocol_version
        ),
        "configuration_fingerprint": configuration_fingerprint,
        "resolver_fingerprint": resolver_fingerprint,
        "migration_set_sha256": migration_set_sha256,
        "cli_sha256": cli_sha256,
        "runbook_sha256": runbook_sha256,
        "burn_in_evidence_sha256": burn_in_evidence_sha256,
        "burn_in_ledger_sha256": burn_in_ledger_sha256,
        "approval_manifest_sha256": approval_manifest_sha256,
        "external_rpc_burn_in_performed": True,
        "ledger_family_identifier": "orev3-rfc008",
        "ledger_instance_identifier": deterministic_id(
            "rfc008-ledger-instance",
            authorization_identifier,
            path_identity(canonical_ledger_path),
        ),
        "canonical_ledger_path": canonical_ledger_path,
        "canonical_ledger_path_identity": path_identity(canonical_ledger_path),
        "collection_mode": COLLECTION_MODE,
        "collection_target": COLLECTION_TARGET,
        "production_ledger_initialization_authorized": True,
        "collector_launch_authorized": True,
        "collection_start_authorized": True,
        "analysis_authorized": False,
        "freeze_authorized": False,
        "deployment_authorized": False,
        "wallet_authorized": False,
        "transaction_authorized": False,
        "live_mining_authorized": False,
        "initial_lifecycle_state": "issued",
    }
    payload["authorization_digest"] = hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return CollectionAuthorizationRecord.model_validate(payload)


class CollectionAuthorizationStore:
    def __init__(
        self,
        path: str | Path,
        *,
        read_only: bool = False,
        identity_path: str | Path | None = None,
    ) -> None:
        self.path = Path(path)
        self.identity_path = Path(identity_path or path)
        mode = "ro" if read_only else "rw"
        uri = f"file:{self.path.resolve()}?mode={mode}"
        self.connection = sqlite3.connect(
            uri,
            uri=True,
            isolation_level=None,
            timeout=5.0,
        )
        self.connection.row_factory = sqlite3.Row
        if not read_only:
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("PRAGMA busy_timeout=5000")
        application_id = int(
            self.connection.execute("PRAGMA application_id").fetchone()[0]
        )
        if application_id != AUTHORIZATION_APPLICATION_ID:
            raise ValueError("Not an RFC-008 collection authorization database")
        self.status()

    @classmethod
    def issue(
        cls,
        path: str | Path,
        record: CollectionAuthorizationRecord,
        *,
        identity_path: str | Path | None = None,
    ) -> None:
        target = Path(path)
        identity = Path(identity_path or target)
        if target.exists():
            raise FileExistsError(
                f"RFC-008 collection authorization already exists: {target}"
            )
        if record.authorization_storage_path != canonical_path(identity):
            raise ValueError("Authorization record is bound to another path")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(
            f".{target.name}.{uuid.uuid4().hex}.tmp"
        )
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(temporary)
            connection.execute(
                f"PRAGMA application_id={AUTHORIZATION_APPLICATION_ID}"
            )
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(
                """
                CREATE TABLE authorization (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    authorization_identifier TEXT NOT NULL UNIQUE,
                    authorization_digest TEXT NOT NULL UNIQUE,
                    immutable_json TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL CHECK(
                      lifecycle_state IN (
                        'issued','initialization_consumed','initialized',
                        'active','completed','failed'
                      )
                    ),
                    updated_at TEXT NOT NULL,
                    initialization_consumed_at TEXT,
                    initialized_at TEXT,
                    launch_consumed_at TEXT,
                    completed_at TEXT,
                    failed_at TEXT,
                    consuming_ledger_identity TEXT,
                    consuming_session_identity TEXT,
                    recovery_count INTEGER NOT NULL DEFAULT 0
                      CHECK(recovery_count >= 0)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE authorization_events (
                    event_index INTEGER PRIMARY KEY,
                    action TEXT NOT NULL,
                    prior_state TEXT,
                    new_state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    ledger_identity TEXT,
                    session_identity TEXT,
                    previous_event_digest TEXT,
                    event_digest TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                INSERT INTO authorization(
                  singleton,authorization_identifier,authorization_digest,
                  immutable_json,lifecycle_state,updated_at
                ) VALUES (1,?,?,?,?,?)
                """,
                (
                    record.authorization_identifier,
                    record.authorization_digest,
                    canonical_json(record.model_dump(mode="json")),
                    "issued",
                    record.created_at,
                ),
            )
            issued_event = {
                "event_index": 0,
                "action": "issued",
                "prior_state": None,
                "new_state": "issued",
                "occurred_at": record.created_at,
                "ledger_identity": None,
                "session_identity": None,
                "previous_event_digest": None,
            }
            issued_digest = hashlib.sha256(
                canonical_json(issued_event).encode("utf-8")
            ).hexdigest()
            connection.execute(
                """
                INSERT INTO authorization_events(
                  event_index,action,prior_state,new_state,occurred_at,
                  ledger_identity,session_identity,previous_event_digest,
                  event_digest
                ) VALUES (0,?,?,?,?,?,?,?,?)
                """,
                (
                    "issued",
                    None,
                    "issued",
                    record.created_at,
                    None,
                    None,
                    None,
                    issued_digest,
                ),
            )
            connection.commit()
            connection.close()
            connection = None
            descriptor = os.open(temporary, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.link(temporary, target)
            os.chmod(target, 0o600)
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if connection is not None:
                connection.close()
            temporary.unlink(missing_ok=True)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def status(self) -> AuthorizationStatus:
        owns_transaction = not self.connection.in_transaction
        if owns_transaction:
            self.connection.execute("BEGIN")
        try:
            row = self.connection.execute(
                "SELECT * FROM authorization WHERE singleton=1"
            ).fetchone()
            if row is None:
                raise ValueError("RFC-008 authorization record is missing")
            record = CollectionAuthorizationRecord.model_validate(
                _strict_object(str(row["immutable_json"]))
            )
            if (
                record.authorization_identifier
                != row["authorization_identifier"]
            ):
                raise ValueError("Authorization identifier column mismatch")
            if record.authorization_digest != row["authorization_digest"]:
                raise ValueError("Authorization digest column mismatch")
            if record.authorization_storage_path != canonical_path(
                self.identity_path
            ):
                raise ValueError("Copied RFC-008 authorization is rejected")
            status = AuthorizationStatus(
                record=record,
                lifecycle_state=str(row["lifecycle_state"]),
                updated_at=str(row["updated_at"]),
                initialization_consumed_at=row[
                    "initialization_consumed_at"
                ],
                initialized_at=row["initialized_at"],
                launch_consumed_at=row["launch_consumed_at"],
                completed_at=row["completed_at"],
                failed_at=row["failed_at"],
                consuming_ledger_identity=row["consuming_ledger_identity"],
                consuming_session_identity=row["consuming_session_identity"],
                recovery_count=int(row["recovery_count"]),
            )
            self._verify_history(status)
            if owns_transaction:
                self.connection.commit()
            return status
        except Exception:
            if owns_transaction:
                self.connection.rollback()
            raise

    def _verify_history(self, status: AuthorizationStatus) -> None:
        rows = self.connection.execute(
            "SELECT * FROM authorization_events ORDER BY event_index"
        ).fetchall()
        if not rows:
            raise ValueError("Authorization transition history is missing")
        prior_state: str | None = None
        previous_digest: str | None = None
        action_times: dict[str, str] = {}
        recovery_count = 0
        for expected_index, row in enumerate(rows):
            if int(row["event_index"]) != expected_index:
                raise ValueError("Authorization event sequence is invalid")
            value = {
                "event_index": expected_index,
                "action": str(row["action"]),
                "prior_state": row["prior_state"],
                "new_state": str(row["new_state"]),
                "occurred_at": str(row["occurred_at"]),
                "ledger_identity": row["ledger_identity"],
                "session_identity": row["session_identity"],
                "previous_event_digest": row["previous_event_digest"],
            }
            digest = hashlib.sha256(
                canonical_json(value).encode("utf-8")
            ).hexdigest()
            if digest != row["event_digest"]:
                raise ValueError("Authorization event digest mismatch")
            if row["prior_state"] != prior_state:
                raise ValueError("Authorization event state chain mismatch")
            if row["previous_event_digest"] != previous_digest:
                raise ValueError("Authorization event digest chain mismatch")
            prior_state = str(row["new_state"])
            previous_digest = digest
            action_times[str(row["action"])] = str(row["occurred_at"])
            if row["action"] == "recovery":
                recovery_count += 1
        if prior_state != status.lifecycle_state:
            raise ValueError("Authorization state differs from event history")
        expected_times = {
            "initialization_consumed": status.initialization_consumed_at,
            "initialized": status.initialized_at,
            "launch_consumed": status.launch_consumed_at,
            "completed": status.completed_at,
            "failed": status.failed_at,
        }
        for action, timestamp in expected_times.items():
            if action_times.get(action) != timestamp:
                raise ValueError(
                    f"Authorization {action} timestamp was tampered"
                )
        if recovery_count != status.recovery_count:
            raise ValueError("Authorization recovery count was tampered")

    def _append_event(
        self,
        *,
        action: str,
        prior_state: str,
        new_state: str,
        occurred_at: str,
        ledger_identity: str | None,
        session_identity: str | None,
    ) -> None:
        previous = self.connection.execute(
            """
            SELECT event_index,event_digest FROM authorization_events
            ORDER BY event_index DESC LIMIT 1
            """
        ).fetchone()
        if previous is None:
            raise ValueError("Authorization transition history is missing")
        event_index = int(previous["event_index"]) + 1
        previous_digest = str(previous["event_digest"])
        value = {
            "event_index": event_index,
            "action": action,
            "prior_state": prior_state,
            "new_state": new_state,
            "occurred_at": occurred_at,
            "ledger_identity": ledger_identity,
            "session_identity": session_identity,
            "previous_event_digest": previous_digest,
        }
        digest = hashlib.sha256(
            canonical_json(value).encode("utf-8")
        ).hexdigest()
        self.connection.execute(
            """
            INSERT INTO authorization_events(
              event_index,action,prior_state,new_state,occurred_at,
              ledger_identity,session_identity,previous_event_digest,
              event_digest
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                event_index,
                action,
                prior_state,
                new_state,
                occurred_at,
                ledger_identity,
                session_identity,
                previous_digest,
                digest,
            ),
        )

    def _transition(
        self,
        *,
        expected_state: str,
        next_state: str,
        assignments: dict[str, object],
        action: str | None = None,
    ) -> AuthorizationStatus:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            current = self.status()
            if current.lifecycle_state != expected_state:
                raise PermissionError(
                    "RFC-008 authorization state rejected transition: "
                    f"{current.lifecycle_state} != {expected_state}"
                )
            timestamp_values = [
                str(value)
                for key, value in assignments.items()
                if key.endswith("_at") and value is not None
            ]
            now = timestamp_values[0] if timestamp_values else utc_now()
            values = {"lifecycle_state": next_state, "updated_at": now}
            values.update(assignments)
            if (
                values.get("consuming_ledger_identity")
                == "__record_ledger_identity__"
            ):
                values["consuming_ledger_identity"] = (
                    current.record.ledger_instance_identifier
                )
            clause = ",".join(f"{key}=?" for key in values)
            cursor = self.connection.execute(
                f"""
                UPDATE authorization SET {clause}
                WHERE singleton=1 AND lifecycle_state=?
                """,
                (*values.values(), expected_state),
            )
            if cursor.rowcount != 1:
                raise PermissionError(
                    "Concurrent RFC-008 authorization consumption rejected"
                )
            self._append_event(
                action=action or next_state,
                prior_state=expected_state,
                new_state=next_state,
                occurred_at=now,
                ledger_identity=(
                    str(values.get("consuming_ledger_identity"))
                    if values.get("consuming_ledger_identity") is not None
                    else current.consuming_ledger_identity
                ),
                session_identity=(
                    str(values.get("consuming_session_identity"))
                    if values.get("consuming_session_identity") is not None
                    else current.consuming_session_identity
                ),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.status()

    def consume_initialization(self) -> AuthorizationStatus:
        now = utc_now()
        return self._transition(
            expected_state="issued",
            next_state="initialization_consumed",
            assignments={
                "initialization_consumed_at": now,
                "consuming_ledger_identity": "__record_ledger_identity__",
            },
            action="initialization_consumed",
        )

    def mark_initialized(self) -> AuthorizationStatus:
        return self._transition(
            expected_state="initialization_consumed",
            next_state="initialized",
            assignments={"initialized_at": utc_now()},
            action="initialized",
        )

    def consume_launch(
        self,
        session_identifier: str,
        *,
        recovery: bool = False,
    ) -> AuthorizationStatus:
        if recovery:
            current = self.status()
            if current.lifecycle_state != "active":
                raise PermissionError(
                    "RFC-008 recovery requires an active consumed authorization"
                )
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                refreshed = self.status()
                if refreshed.lifecycle_state != "active":
                    raise PermissionError(
                        "Concurrent RFC-008 recovery transition rejected"
                    )
                now = utc_now()
                self.connection.execute(
                    """
                    UPDATE authorization
                    SET updated_at=?,consuming_session_identity=?,
                        recovery_count=recovery_count+1
                    WHERE singleton=1 AND lifecycle_state='active'
                    """,
                    (now, session_identifier),
                )
                self._append_event(
                    action="recovery",
                    prior_state="active",
                    new_state="active",
                    occurred_at=now,
                    ledger_identity=current.consuming_ledger_identity,
                    session_identity=session_identifier,
                )
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
            return self.status()
        return self._transition(
            expected_state="initialized",
            next_state="active",
            assignments={
                "launch_consumed_at": utc_now(),
                "consuming_session_identity": session_identifier,
            },
            action="launch_consumed",
        )

    def complete(self, session_identifier: str) -> AuthorizationStatus:
        current = self.status()
        if current.consuming_session_identity != session_identifier:
            raise PermissionError(
                "RFC-008 completion session identity mismatch"
            )
        return self._transition(
            expected_state="active",
            next_state="completed",
            assignments={"completed_at": utc_now()},
            action="completed",
        )

    def reconcile_completed_ledger(
        self,
        ledger_instance_identifier: str,
    ) -> AuthorizationStatus:
        current = self.status()
        if (
            current.record.ledger_instance_identifier
            != ledger_instance_identifier
            or current.consuming_ledger_identity
            != ledger_instance_identifier
        ):
            raise PermissionError(
                "RFC-008 completed-ledger reconciliation identity mismatch"
            )
        if current.lifecycle_state == "completed":
            return current
        return self._transition(
            expected_state="active",
            next_state="completed",
            assignments={"completed_at": utc_now()},
            action="completed",
        )

    def fail(self, session_identifier: str | None = None) -> AuthorizationStatus:
        current = self.status()
        if (
            session_identifier is not None
            and current.consuming_session_identity != session_identifier
        ):
            raise PermissionError("RFC-008 failed session identity mismatch")
        return self._transition(
            expected_state=current.lifecycle_state,
            next_state="failed",
            assignments={"failed_at": utc_now()},
            action="failed",
        )
