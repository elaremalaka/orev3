from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from orev3.ledger import SCHEMA_VERSION
from orev3.ledger.schemas import LedgerEvent


RECORD_TABLES = {
    "opportunities": ("opportunity_id",),
    "decisions": ("decision_id",),
    "deployments": ("deployment_intent_id",),
    "transactions": ("transaction_signature",),
    "wallet_snapshots": ("wallet_public_key", "snapshot_time"),
    "rewards": ("opportunity_id",),
    "claims": ("claim_signature",),
    "reconciliation": ("opportunity_id",),
}


class LedgerStore:
    def __init__(self, path: str | Path, *, read_only: bool = False) -> None:
        self.path = Path(path)
        if read_only:
            uri = f"file:{self.path.resolve()}?mode=ro"
            self.connection = sqlite3.connect(uri, uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def initialize(self) -> None:
        existing = self.connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'metadata'
            """
        ).fetchone()
        if existing is not None:
            row = self.connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is not None and int(row[0]) != SCHEMA_VERSION:
                raise ValueError(
                    "Unsupported ledger schema version: "
                    f"{row[0]} (expected {SCHEMA_VERSION})"
                )
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_records (
                    source_record_id TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    source_line_number INTEGER NOT NULL,
                    record_sha256 TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    round_id INTEGER,
                    observation_index INTEGER,
                    wallet_public_key TEXT,
                    transaction_signature TEXT,
                    record_json TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS events_source_event
                ON events(source_record_id, event_type);
                CREATE TABLE IF NOT EXISTS opportunities (
                    opportunity_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL,
                    observation_index INTEGER NOT NULL,
                    observed_at TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    UNIQUE(round_id, observation_index)
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id)
                );
                CREATE TABLE IF NOT EXISTS deployments (
                    deployment_intent_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    transaction_signature TEXT,
                    record_json TEXT NOT NULL,
                    FOREIGN KEY(decision_id) REFERENCES decisions(decision_id)
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_signature TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS wallet_snapshots (
                    wallet_public_key TEXT NOT NULL,
                    snapshot_time TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    PRIMARY KEY(wallet_public_key, snapshot_time)
                );
                CREATE TABLE IF NOT EXISTS rewards (
                    opportunity_id TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id)
                );
                CREATE TABLE IF NOT EXISTS claims (
                    claim_signature TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reconciliation (
                    opportunity_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    completeness_score REAL NOT NULL,
                    record_json TEXT NOT NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(opportunity_id)
                );
                """
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )

    @staticmethod
    def _json(record: BaseModel) -> str:
        return json.dumps(
            record.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def insert_source_record(
        self,
        source_record_id: str,
        source_name: str,
        source_line_number: int,
        record_sha256: str,
    ) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO source_records
            (source_record_id, source_name, source_line_number, record_sha256)
            VALUES (?, ?, ?, ?)
            """,
            (source_record_id, source_name, source_line_number, record_sha256),
        )
        return cursor.rowcount == 1

    def insert_event(self, event: LedgerEvent) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO events
            (event_id, event_type, event_time, observed_at, source,
             source_record_id, round_id, observation_index,
             wallet_public_key, transaction_signature, record_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_type.value,
                event.event_time.isoformat(),
                event.observed_at.isoformat(),
                event.source,
                event.source_record_id,
                event.round_id,
                event.observation_index,
                event.wallet_public_key,
                event.transaction_signature,
                self._json(event),
            ),
        )
        return cursor.rowcount == 1

    def upsert_record(self, table: str, record: BaseModel) -> bool:
        if table not in RECORD_TABLES:
            raise ValueError(f"Unknown ledger table: {table}")
        data = record.model_dump(mode="json")
        keys = RECORD_TABLES[table]
        columns = list(keys)
        values = [data[key] for key in keys]
        if table == "opportunities":
            columns += ["round_id", "observation_index", "observed_at"]
            values += [data["round_id"], data["observation_index"], data["observed_at"]]
        elif table == "decisions":
            columns.append("opportunity_id")
            values.append(data["opportunity_id"])
        elif table == "deployments":
            columns += ["decision_id", "transaction_signature"]
            values += [data["decision_id"], data["transaction_signature"]]
        elif table == "reconciliation":
            columns += ["state", "completeness_score"]
            values += [data["state"], data["completeness_score"]]
        columns.append("record_json")
        values.append(self._json(record))
        placeholders = ", ".join("?" for _ in columns)
        sql = (
            f"INSERT OR IGNORE INTO {table} "
            f"({', '.join(columns)}) VALUES ({placeholders})"
        )
        cursor = self.connection.execute(sql, values)
        return cursor.rowcount == 1

    def records(self, table: str) -> list[dict]:
        if table not in RECORD_TABLES:
            raise ValueError(f"Unknown ledger table: {table}")
        rows = self.connection.execute(
            f"SELECT record_json FROM {table} ORDER BY {', '.join(RECORD_TABLES[table])}"
        )
        return [json.loads(row["record_json"]) for row in rows]

    def count(self, table: str) -> int:
        allowed = set(RECORD_TABLES) | {"events", "source_records"}
        if table not in allowed:
            raise ValueError(f"Unknown ledger table: {table}")
        return int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def replace_reconciliation(self, records: Iterable[BaseModel]) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM reconciliation")
            for record in records:
                self.upsert_record("reconciliation", record)
