from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orev3.collection.schemas import SourceCursor
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.schemas import (
    ArmDecision,
    DecisionSnapshot,
    OutcomeEvidence,
    OutcomeQueueRecord,
    RoundAccounting,
)


SCHEMA_VERSION = 1
PROTECTED_LEDGER_NAMES = {
    "rfc007_live_ledger_v1.sqlite",
    "participant_ledger_v1.sqlite",
}


def strict_json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def assert_safe_new_ledger_path(path: str | Path) -> Path:
    target = Path(path)
    if target.name in PROTECTED_LEDGER_NAMES or "rfc007" in target.name.lower():
        raise ValueError("RFC-008 refuses protected or RFC-007 ledger paths")
    if target.exists():
        raise FileExistsError(f"RFC-008 ledger already exists: {target}")
    return target


class RFC008Store:
    def __init__(
        self,
        path: str | Path,
        *,
        config: RFC008Config | None = None,
        create: bool = False,
        read_only: bool = False,
    ) -> None:
        self.path = Path(path)
        if create:
            assert_safe_new_ledger_path(self.path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
        if read_only:
            uri = f"file:{self.path.resolve()}?mode=ro"
            self.connection = sqlite3.connect(uri, uri=True)
        else:
            if not create and not self.path.exists():
                raise FileNotFoundError(self.path)
            self.connection = sqlite3.connect(self.path)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute(
                f"PRAGMA busy_timeout={int(config.busy_timeout_ms if config else 5000)}"
            )
        self.connection.row_factory = sqlite3.Row
        if create:
            if config is None:
                raise ValueError("Creating a ledger requires RFC-008 configuration")
            self.initialize(config)
        self.verify_identity(config)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def initialize(self, config: RFC008Config) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE source_cursors (
                    source_id TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL UNIQUE,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE source_records (
                    record_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    UNIQUE(source_id, line_number),
                    UNIQUE(source_id, content_sha256)
                );
                CREATE TABLE experiment_rounds (
                    round_id INTEGER PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    transition_at TEXT,
                    state TEXT NOT NULL,
                    exclusion_reason TEXT,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE decision_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL UNIQUE,
                    source_content_sha256 TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE arm_decisions (
                    decision_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL,
                    arm_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    UNIQUE(round_id, arm_id)
                );
                CREATE TABLE outcome_queue (
                    round_id INTEGER PRIMARY KEY,
                    state TEXT NOT NULL,
                    next_retry_at TEXT,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE outcome_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL,
                    attempted_at TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_sha256 TEXT,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE finalized_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL,
                    provenance TEXT NOT NULL,
                    source_content_sha256 TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    UNIQUE(round_id, provenance)
                );
                CREATE TABLE outcome_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE round_accounting (
                    accounting_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL,
                    arm_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    outcome_id TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    UNIQUE(round_id, arm_id)
                );
                CREATE TABLE safety_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE counters (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                CREATE TABLE collector_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    process_id INTEGER NOT NULL,
                    configuration_fingerprint TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                """
            )
            values = {
                "schema_version": str(SCHEMA_VERSION),
                "experiment_id": config.experiment_id,
                "configuration_fingerprint": config.configuration_fingerprint,
                "candidate_configuration_sha256": config.candidate_configuration_sha256,
                "approval_manifest_sha256": config.approval_manifest_sha256,
                "last_round_id": "",
            }
            self.connection.executemany(
                "INSERT INTO metadata(key,value) VALUES (?,?)", values.items()
            )
            self.audit(
                "ledger_initialized",
                {
                    "schema_version": SCHEMA_VERSION,
                    "paper_only": True,
                    "live_actions": 0,
                },
            )

    def verify_identity(self, config: RFC008Config | None) -> None:
        try:
            values = dict(self.connection.execute("SELECT key,value FROM metadata"))
        except sqlite3.OperationalError as exc:
            raise ValueError("Not an initialized RFC-008 ledger") from exc
        if int(values.get("schema_version", -1)) != SCHEMA_VERSION:
            raise ValueError("Unsupported RFC-008 schema version")
        if config is not None:
            if values.get("experiment_id") != config.experiment_id:
                raise ValueError("RFC-008 experiment identity mismatch")
            if values.get("configuration_fingerprint") != config.configuration_fingerprint:
                raise ValueError("RFC-008 configuration fingerprint mismatch")

    def metadata(self, key: str) -> str:
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key=?", (key,)
        ).fetchone()
        if row is None:
            raise KeyError(key)
        return str(row[0])

    def set_metadata(self, key: str, value: str) -> None:
        self.connection.execute(
            "UPDATE metadata SET value=? WHERE key=?", (value, key)
        )

    def audit(self, event_type: str, record: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO safety_audit(created_at,event_type,record_json) VALUES (?,?,?)",
            (datetime.now(timezone.utc).isoformat(), event_type, strict_json(record)),
        )

    def increment(self, key: str, amount: int = 1) -> None:
        self.connection.execute(
            """
            INSERT INTO counters(key,value) VALUES (?,?)
            ON CONFLICT(key) DO UPDATE SET value=value+excluded.value
            """,
            (key, amount),
        )

    def counters(self) -> dict[str, int]:
        return {str(r[0]): int(r[1]) for r in self.connection.execute("SELECT key,value FROM counters")}

    def save_cursor(self, cursor: SourceCursor) -> None:
        self.connection.execute(
            """
            INSERT INTO source_cursors(source_id,source_path,record_json)
            VALUES (?,?,?)
            ON CONFLICT(source_id) DO UPDATE SET
              source_path=excluded.source_path,record_json=excluded.record_json
            """,
            (cursor.source_id, cursor.source_path, strict_json(cursor)),
        )

    def load_cursor(self, source_path: str | Path) -> SourceCursor | None:
        row = self.connection.execute(
            "SELECT record_json FROM source_cursors WHERE source_path=?",
            (str(source_path),),
        ).fetchone()
        return SourceCursor.model_validate_json(row[0]) if row else None

    def mark_source_record(
        self, record_id: str, source_id: str, line_number: int, content_sha256: str
    ) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO source_records
            (record_id,source_id,line_number,content_sha256) VALUES (?,?,?,?)
            """,
            (record_id, source_id, line_number, content_sha256),
        )
        if not cursor.rowcount:
            self.increment("duplicate_source_records")
        return cursor.rowcount == 1

    def source_hashes(self, source_id: str) -> set[str]:
        return {str(r[0]) for r in self.connection.execute(
            "SELECT content_sha256 FROM source_records WHERE source_id=?", (source_id,)
        )}

    def next_observation_index(self, round_id: int) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) FROM source_records sr
            WHERE EXISTS (
              SELECT 1 FROM experiment_rounds er
              WHERE er.round_id=? AND sr.rowid>=1
            )
            """,
            (round_id,),
        ).fetchone()
        # The collector keeps a per-round counter in metadata for exact restart.
        key = f"observation_index:{round_id}"
        try:
            value = int(self.metadata(key))
        except KeyError:
            value = 0
            self.connection.execute(
                "INSERT INTO metadata(key,value) VALUES (?,?)", (key, "1")
            )
            return value
        self.set_metadata(key, str(value + 1))
        return value

    def start_round(self, round_id: int, started_at: datetime) -> bool:
        record = {
            "round_id": round_id,
            "started_at": started_at.isoformat(),
            "state": "started",
            "paper_only": True,
        }
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO experiment_rounds
            (round_id,started_at,state,record_json) VALUES (?,?,?,?)
            """,
            (round_id, started_at.isoformat(), "started", strict_json(record)),
        )
        if cursor.rowcount:
            self.increment("started_rounds")
        return cursor.rowcount == 1

    def transition_round(self, round_id: int, at: datetime) -> None:
        self.connection.execute(
            "UPDATE experiment_rounds SET transition_at=? WHERE round_id=?",
            (at.isoformat(), round_id),
        )

    def exclude_round(self, round_id: int, reason: str) -> None:
        self.connection.execute(
            """
            UPDATE experiment_rounds SET state='excluded',exclusion_reason=?
            WHERE round_id=? AND state!='finalized'
            """,
            (reason, round_id),
        )
        self.increment("excluded_rounds")

    def has_snapshot(self, round_id: int) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM decision_snapshots WHERE round_id=?", (round_id,)
        ).fetchone() is not None

    def insert_snapshot_and_decisions(
        self, snapshot: DecisionSnapshot, decisions: tuple[ArmDecision, ...]
    ) -> bool:
        try:
            self.connection.execute(
                """
                INSERT INTO decision_snapshots
                (snapshot_id,round_id,source_content_sha256,record_json)
                VALUES (?,?,?,?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.round_id,
                    snapshot.source_content_sha256,
                    strict_json(snapshot),
                ),
            )
            for decision in decisions:
                self.connection.execute(
                    """
                    INSERT INTO arm_decisions
                    (decision_id,round_id,arm_id,snapshot_id,record_json)
                    VALUES (?,?,?,?,?)
                    """,
                    (
                        decision.decision_id,
                        decision.round_id,
                        decision.arm_id,
                        decision.snapshot_id,
                        strict_json(decision),
                    ),
                )
        except sqlite3.IntegrityError:
            self.increment("duplicate_decisions")
            return False
        self.increment("decision_snapshots")
        self.increment("arm_decisions", len(decisions))
        return True

    def decisions(self, round_id: int) -> list[ArmDecision]:
        return [
            ArmDecision.model_validate_json(row[0])
            for row in self.connection.execute(
                "SELECT record_json FROM arm_decisions WHERE round_id=? ORDER BY arm_id",
                (round_id,),
            )
        ]

    def enqueue_outcome(self, queue: OutcomeQueueRecord) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO outcome_queue
            (round_id,state,next_retry_at,record_json) VALUES (?,?,?,?)
            """,
            (
                queue.round_id,
                queue.state,
                queue.next_retry_at.isoformat() if queue.next_retry_at else None,
                strict_json(queue),
            ),
        )
        if cursor.rowcount:
            self.increment("outcomes_pending")
        return cursor.rowcount == 1

    def save_queue(self, queue: OutcomeQueueRecord) -> None:
        self.connection.execute(
            """
            UPDATE outcome_queue SET state=?,next_retry_at=?,record_json=?
            WHERE round_id=?
            """,
            (
                queue.state,
                queue.next_retry_at.isoformat() if queue.next_retry_at else None,
                strict_json(queue),
                queue.round_id,
            ),
        )

    def queue(self, round_id: int) -> OutcomeQueueRecord | None:
        row = self.connection.execute(
            "SELECT record_json FROM outcome_queue WHERE round_id=?", (round_id,)
        ).fetchone()
        return OutcomeQueueRecord.model_validate_json(row[0]) if row else None

    def unresolved_queue(self) -> list[OutcomeQueueRecord]:
        return [
            OutcomeQueueRecord.model_validate_json(row[0])
            for row in self.connection.execute(
                """
                SELECT record_json FROM outcome_queue
                WHERE state IN ('pending','resolving')
                ORDER BY round_id
                """
            )
        ]

    def accepted_outcome(self, round_id: int) -> OutcomeEvidence | None:
        row = self.connection.execute(
            """
            SELECT record_json FROM finalized_outcomes WHERE round_id=?
            ORDER BY CASE provenance WHEN 'direct_observed' THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (round_id,),
        ).fetchone()
        return OutcomeEvidence.model_validate_json(row[0]) if row else None

    def insert_outcome(self, outcome: OutcomeEvidence) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO finalized_outcomes
            (outcome_id,round_id,provenance,source_content_sha256,record_json)
            VALUES (?,?,?,?,?)
            """,
            (
                outcome.outcome_id,
                outcome.round_id,
                outcome.provenance,
                outcome.source_content_sha256,
                strict_json(outcome),
            ),
        )
        return cursor.rowcount == 1

    def insert_accounting(self, value: RoundAccounting) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO round_accounting
            (accounting_id,round_id,arm_id,decision_id,outcome_id,record_json)
            VALUES (?,?,?,?,?,?)
            """,
            (
                value.accounting_id,
                value.round_id,
                value.arm_id,
                value.decision_id,
                value.outcome_id,
                strict_json(value),
            ),
        )
        return cursor.rowcount == 1

    def integrity(self) -> str:
        return str(self.connection.execute("PRAGMA integrity_check").fetchone()[0])

    def count(self, table: str, where: str = "", params: tuple = ()) -> int:
        allowed = {
            "experiment_rounds", "decision_snapshots", "arm_decisions",
            "outcome_queue", "finalized_outcomes", "outcome_conflicts",
            "round_accounting", "source_records", "safety_audit",
        }
        if table not in allowed:
            raise ValueError("Unsupported table")
        query = f"SELECT COUNT(*) FROM {table}"
        if where:
            query += " WHERE " + where
        return int(self.connection.execute(query, params).fetchone()[0])
