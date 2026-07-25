from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from orev3.collection.schemas import SourceCursor
from orev3.ledger.storage import LedgerStore


class CollectionStore:
    def __init__(
        self,
        path: str | Path,
        *,
        busy_timeout_ms: int = 5000,
        read_only: bool = False,
    ) -> None:
        self.ledger = LedgerStore(path, read_only=read_only)
        self.path = self.ledger.path
        self.connection = self.ledger.connection
        if not read_only:
            self.connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.execute("PRAGMA synchronous = NORMAL")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        self.ledger.close()

    def initialize(self) -> None:
        self.ledger.initialize()
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS collection_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_cursors (
                    source_id TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL UNIQUE,
                    source_inode INTEGER NOT NULL,
                    byte_offset INTEGER NOT NULL,
                    line_number INTEGER NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ingested_source_records (
                    record_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_line_number INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    UNIQUE(source_id, content_sha256)
                );
                CREATE TABLE IF NOT EXISTS paper_decisions (
                    decision_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL UNIQUE,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS final_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    round_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    record_json TEXT NOT NULL,
                    UNIQUE(round_id, version)
                );
                CREATE TABLE IF NOT EXISTS paper_accounting (
                    accounting_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL UNIQUE,
                    decision_id TEXT NOT NULL,
                    outcome_id TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS partial_opportunities (
                    partial_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    round_id INTEGER,
                    expired INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_reconciliation (
                    opportunity_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS collection_counters (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                """
            )
            self.connection.execute(
                """
                INSERT OR IGNORE INTO collection_metadata(key, value)
                VALUES ('schema_version', '1')
                """
            )

    @staticmethod
    def _json(record) -> str:
        value = (
            record.model_dump(mode="json")
            if hasattr(record, "model_dump")
            else record
        )
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def load_cursor(self, source_path: str | Path) -> SourceCursor | None:
        row = self.connection.execute(
            "SELECT record_json FROM source_cursors WHERE source_path = ?",
            (str(source_path),),
        ).fetchone()
        return SourceCursor.model_validate_json(row[0]) if row else None

    def save_cursor(self, cursor: SourceCursor) -> None:
        self.connection.execute(
            """
            INSERT INTO source_cursors
            (source_id, source_path, source_inode, byte_offset, line_number, record_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                source_path=excluded.source_path,
                source_inode=excluded.source_inode,
                byte_offset=excluded.byte_offset,
                line_number=excluded.line_number,
                record_json=excluded.record_json
            """,
            (
                cursor.source_id,
                cursor.source_path,
                cursor.source_inode,
                cursor.byte_offset,
                cursor.line_number,
                self._json(cursor),
            ),
        )

    def mark_source_record(
        self,
        *,
        record_id: str,
        source_id: str,
        source_line_number: int,
        content_sha256: str,
    ) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO ingested_source_records
            (record_id, source_id, source_line_number, content_sha256)
            VALUES (?, ?, ?, ?)
            """,
            (record_id, source_id, source_line_number, content_sha256),
        )
        return cursor.rowcount == 1

    def content_hashes(self, source_id: str) -> set[str]:
        return {
            str(row[0])
            for row in self.connection.execute(
                """
                SELECT content_sha256 FROM ingested_source_records
                WHERE source_id = ?
                """,
                (source_id,),
            )
        }

    def next_observation_index(self, round_id: int) -> int:
        row = self.connection.execute(
            """
            SELECT COALESCE(MAX(observation_index), -1) + 1
            FROM opportunities WHERE round_id = ?
            """,
            (round_id,),
        ).fetchone()
        return int(row[0])

    def insert_json_record(
        self,
        table: str,
        key_column: str,
        key: str,
        record,
        *,
        extra: dict[str, object] | None = None,
    ) -> bool:
        allowed = {
            "paper_decisions",
            "final_outcomes",
            "paper_accounting",
            "partial_opportunities",
            "paper_reconciliation",
        }
        if table not in allowed:
            raise ValueError(f"Unsupported collection table: {table}")
        fields = {key_column: key, "record_json": self._json(record)}
        fields.update(extra or {})
        columns = list(fields)
        values = [fields[column] for column in columns]
        cursor = self.connection.execute(
            f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})",
            values,
        )
        return cursor.rowcount == 1

    def upsert_json_record(
        self,
        table: str,
        key_column: str,
        key: str,
        record,
        *,
        extra: dict[str, object] | None = None,
    ) -> None:
        allowed = {"paper_reconciliation"}
        if table not in allowed:
            raise ValueError(f"Unsupported upsert table: {table}")
        fields = {key_column: key, "record_json": self._json(record)}
        fields.update(extra or {})
        columns = list(fields)
        updates = [
            f"{column}=excluded.{column}"
            for column in columns
            if column != key_column
        ]
        self.connection.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)}) "
            f"ON CONFLICT({key_column}) DO UPDATE SET {', '.join(updates)}",
            [fields[column] for column in columns],
        )

    def json_records(self, table: str, order_by: str) -> list[dict]:
        allowed = {
            "paper_decisions",
            "final_outcomes",
            "paper_accounting",
            "partial_opportunities",
            "paper_reconciliation",
        }
        if table not in allowed:
            raise ValueError(f"Unsupported collection table: {table}")
        return [
            json.loads(row[0])
            for row in self.connection.execute(
                f"SELECT record_json FROM {table} ORDER BY {order_by}"
            )
        ]

    def increment(self, key: str, amount: int = 1) -> None:
        self.connection.execute(
            """
            INSERT INTO collection_counters(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = value + excluded.value
            """,
            (key, amount),
        )

    def set_metadata(self, key: str, value: str) -> None:
        self.connection.execute(
            """
            INSERT INTO collection_metadata(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )

    def metadata(self) -> dict[str, str]:
        return {
            str(row[0]): str(row[1])
            for row in self.connection.execute(
                "SELECT key, value FROM collection_metadata ORDER BY key"
            )
        }

    def counters(self) -> dict[str, int]:
        return {
            str(row[0]): int(row[1])
            for row in self.connection.execute(
                "SELECT key, value FROM collection_counters ORDER BY key"
            )
        }

    def integrity_check(self) -> str:
        return str(self.connection.execute("PRAGMA integrity_check").fetchone()[0])

    def rows_by_table(self) -> dict[str, int]:
        names = [
            row[0]
            for row in self.connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        return {
            name: int(
                self.connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            )
            for name in names
        }
