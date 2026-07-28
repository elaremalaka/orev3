from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


APPLICATION_ID = 0x4F523038
DATABASE_FAMILY = "orev3-rfc008"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        material = "\n".join((str(self.version), self.name, *self.statements))
        return hashlib.sha256(material.encode()).hexdigest()


MIGRATIONS = (
    Migration(
        1,
        "initial_rfc008_schema",
        (
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
            "CREATE TABLE source_cursors (source_id TEXT PRIMARY KEY, source_path TEXT NOT NULL UNIQUE, record_json TEXT NOT NULL)",
            "CREATE TABLE source_records (record_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, line_number INTEGER NOT NULL, content_sha256 TEXT NOT NULL, UNIQUE(source_id,line_number), UNIQUE(source_id,content_sha256))",
            "CREATE TABLE experiment_rounds (round_id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, transition_at TEXT, state TEXT NOT NULL, exclusion_reason TEXT, record_json TEXT NOT NULL)",
            "CREATE TABLE decision_snapshots (snapshot_id TEXT PRIMARY KEY, round_id INTEGER NOT NULL UNIQUE, source_content_sha256 TEXT NOT NULL, record_json TEXT NOT NULL)",
            "CREATE TABLE arm_decisions (decision_id TEXT PRIMARY KEY, round_id INTEGER NOT NULL, arm_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, record_json TEXT NOT NULL, UNIQUE(round_id,arm_id))",
            "CREATE TABLE outcome_queue (round_id INTEGER PRIMARY KEY, state TEXT NOT NULL, next_retry_at TEXT, record_json TEXT NOT NULL)",
            "CREATE TABLE outcome_attempts (attempt_id TEXT PRIMARY KEY, round_id INTEGER NOT NULL, attempted_at TEXT NOT NULL, source_type TEXT NOT NULL, status TEXT NOT NULL, response_sha256 TEXT, record_json TEXT NOT NULL)",
            "CREATE TABLE finalized_outcomes (outcome_id TEXT PRIMARY KEY, round_id INTEGER NOT NULL, provenance TEXT NOT NULL, source_content_sha256 TEXT NOT NULL, record_json TEXT NOT NULL, UNIQUE(round_id,provenance))",
            "CREATE TABLE outcome_conflicts (conflict_id TEXT PRIMARY KEY, round_id INTEGER NOT NULL, created_at TEXT NOT NULL, record_json TEXT NOT NULL)",
            "CREATE TABLE round_accounting (accounting_id TEXT PRIMARY KEY, round_id INTEGER NOT NULL, arm_id TEXT NOT NULL, decision_id TEXT NOT NULL, outcome_id TEXT NOT NULL, record_json TEXT NOT NULL, UNIQUE(round_id,arm_id))",
            "CREATE TABLE safety_audit (audit_id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, event_type TEXT NOT NULL, record_json TEXT NOT NULL)",
            "CREATE TABLE counters (key TEXT PRIMARY KEY, value INTEGER NOT NULL)",
            "CREATE TABLE collector_runs (run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT, process_id INTEGER NOT NULL, configuration_fingerprint TEXT NOT NULL, record_json TEXT NOT NULL)",
        ),
    ),
    Migration(
        2,
        "freeze_and_resolution_identity",
        (
            "CREATE TABLE final_freezes (freeze_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, ledger_data_version INTEGER NOT NULL, record_json TEXT NOT NULL)",
            "CREATE TABLE resolver_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        ),
    ),
    Migration(
        3,
        "frozen_ledger_write_guards",
        tuple(
            statement
            for table in (
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
                "resolver_metadata",
            )
            for statement in (
                f"""CREATE TRIGGER freeze_{table}_insert
                BEFORE INSERT ON {table}
                WHEN (SELECT value FROM metadata WHERE key='ledger_state')='frozen'
                BEGIN SELECT RAISE(ABORT,'RFC-008 ledger is frozen'); END""",
                f"""CREATE TRIGGER freeze_{table}_update
                BEFORE UPDATE ON {table}
                WHEN (SELECT value FROM metadata WHERE key='ledger_state')='frozen'
                BEGIN SELECT RAISE(ABORT,'RFC-008 ledger is frozen'); END""",
                f"""CREATE TRIGGER freeze_{table}_delete
                BEFORE DELETE ON {table}
                WHEN (SELECT value FROM metadata WHERE key='ledger_state')='frozen'
                BEGIN SELECT RAISE(ABORT,'RFC-008 ledger is frozen'); END""",
            )
        ),
    ),
    Migration(
        4,
        "paper_holdout_collection_contract",
        (
            """
            CREATE TABLE collection_contract (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                ledger_schema_version INTEGER NOT NULL CHECK(
                  typeof(ledger_schema_version)='integer'
                  AND ledger_schema_version=1
                ),
                evidence_schema_version INTEGER NOT NULL CHECK(
                  typeof(evidence_schema_version)='integer'
                ),
                rfc_identifier TEXT NOT NULL CHECK(rfc_identifier='RFC-008'),
                ledger_family_identifier TEXT NOT NULL CHECK(
                  ledger_family_identifier='orev3-rfc008'
                ),
                ledger_instance_identifier TEXT NOT NULL UNIQUE,
                canonical_ledger_path TEXT NOT NULL,
                canonical_ledger_path_identity TEXT NOT NULL UNIQUE,
                authorization_identifier TEXT NOT NULL UNIQUE,
                authorization_digest TEXT NOT NULL UNIQUE,
                collection_mode TEXT NOT NULL CHECK(collection_mode='paper'),
                collection_target INTEGER NOT NULL CHECK(
                  typeof(collection_target)='integer'
                  AND collection_target=600
                ),
                committed_opportunity_count INTEGER NOT NULL DEFAULT 0 CHECK(
                  typeof(committed_opportunity_count)='integer'
                  AND committed_opportunity_count BETWEEN 0 AND collection_target
                ),
                collection_state TEXT NOT NULL CHECK(
                  collection_state IN ('initialized','active','completed','failed')
                ),
                created_at TEXT NOT NULL,
                completion_timestamp TEXT,
                active_session_identity TEXT,
                last_committed_opportunity_identity TEXT,
                collection_seed_cursor_json TEXT NOT NULL,
                publication_cursor_json TEXT NOT NULL,
                last_observed_cursor_json TEXT,
                immutable_release_json TEXT NOT NULL
            )
            """,
            "UPDATE metadata SET value='4' WHERE key='schema_version'",
            """
            CREATE TRIGGER immutable_ledger_metadata_update
            BEFORE UPDATE ON metadata
            WHEN OLD.key IN (
              'schema_version','database_family','experiment_id',
              'configuration_fingerprint','candidate_configuration_sha256',
              'approval_manifest_sha256'
            )
            BEGIN
              SELECT RAISE(ABORT,'RFC-008 immutable ledger metadata');
            END
            """,
            """
            CREATE TRIGGER immutable_ledger_metadata_delete
            BEFORE DELETE ON metadata
            WHEN OLD.key IN (
              'schema_version','database_family','experiment_id',
              'configuration_fingerprint','candidate_configuration_sha256',
              'approval_manifest_sha256'
            )
            BEGIN
              SELECT RAISE(ABORT,'RFC-008 immutable ledger metadata');
            END
            """,
            """
            CREATE TRIGGER collection_contract_immutable_update
            BEFORE UPDATE ON collection_contract
            WHEN
              OLD.ledger_schema_version != NEW.ledger_schema_version
              OR OLD.evidence_schema_version != NEW.evidence_schema_version
              OR OLD.rfc_identifier != NEW.rfc_identifier
              OR OLD.ledger_family_identifier != NEW.ledger_family_identifier
              OR OLD.ledger_instance_identifier != NEW.ledger_instance_identifier
              OR OLD.canonical_ledger_path != NEW.canonical_ledger_path
              OR OLD.canonical_ledger_path_identity != NEW.canonical_ledger_path_identity
              OR OLD.authorization_identifier != NEW.authorization_identifier
              OR OLD.authorization_digest != NEW.authorization_digest
              OR OLD.collection_mode != NEW.collection_mode
              OR OLD.collection_target != NEW.collection_target
              OR OLD.created_at != NEW.created_at
              OR OLD.collection_seed_cursor_json != NEW.collection_seed_cursor_json
              OR OLD.publication_cursor_json != NEW.publication_cursor_json
              OR OLD.immutable_release_json != NEW.immutable_release_json
            BEGIN
              SELECT RAISE(ABORT,'RFC-008 immutable collection contract');
            END
            """,
            """
            CREATE TRIGGER collection_contract_no_delete
            BEFORE DELETE ON collection_contract
            BEGIN
              SELECT RAISE(ABORT,'RFC-008 collection contract cannot be deleted');
            END
            """,
            """
            CREATE TRIGGER decision_snapshot_target_guard
            BEFORE INSERT ON decision_snapshots
            WHEN
              (SELECT COUNT(*) FROM collection_contract WHERE singleton=1) != 1
              OR (SELECT collection_state FROM collection_contract WHERE singleton=1)
                   NOT IN ('initialized','active')
              OR (SELECT committed_opportunity_count
                  FROM collection_contract WHERE singleton=1)
                   >= (SELECT collection_target
                       FROM collection_contract WHERE singleton=1)
            BEGIN
              SELECT RAISE(ABORT,'RFC-008 collection target reached');
            END
            """,
            """
            CREATE TRIGGER decision_snapshot_count_after_insert
            AFTER INSERT ON decision_snapshots
            BEGIN
              UPDATE collection_contract
              SET committed_opportunity_count=committed_opportunity_count+1,
                  last_committed_opportunity_identity=NEW.snapshot_id,
                  collection_state=CASE
                    WHEN committed_opportunity_count+1=collection_target
                    THEN 'completed' ELSE collection_state END,
                  completion_timestamp=CASE
                    WHEN committed_opportunity_count+1=collection_target
                    THEN strftime('%Y-%m-%dT%H:%M:%fZ','now')
                    ELSE completion_timestamp END
              WHERE singleton=1;
            END
            """,
            """
            CREATE TRIGGER decision_snapshot_no_update
            BEFORE UPDATE ON decision_snapshots
            BEGIN
              SELECT RAISE(ABORT,'RFC-008 canonical opportunity is immutable');
            END
            """,
            """
            CREATE TRIGGER decision_snapshot_no_delete
            BEFORE DELETE ON decision_snapshots
            BEGIN
              SELECT RAISE(ABORT,'RFC-008 canonical opportunity cannot be deleted');
            END
            """,
        ),
    ),
)


def migration_set_hash(
    migrations: Iterable[Migration] = MIGRATIONS,
) -> str:
    material = "\n".join(migration.checksum for migration in migrations)
    return hashlib.sha256(material.encode()).hexdigest()


def _validate_sequence(migrations: tuple[Migration, ...]) -> None:
    versions = tuple(migration.version for migration in migrations)
    if versions != tuple(range(1, len(migrations) + 1)):
        raise ValueError("RFC-008 migrations must be contiguous and ordered")


def apply_migrations(
    connection: sqlite3.Connection,
    migrations: tuple[Migration, ...] = MIGRATIONS,
) -> None:
    _validate_sequence(migrations)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        int(row[0]): (str(row[1]), str(row[2]))
        for row in connection.execute(
            "SELECT version,name,checksum FROM schema_migrations"
        )
    }
    if applied and set(applied) != set(range(1, max(applied) + 1)):
        raise ValueError("RFC-008 migration history has skipped versions")
    for migration in migrations:
        existing = applied.get(migration.version)
        if existing is not None:
            if existing != (migration.name, migration.checksum):
                raise ValueError(
                    f"RFC-008 migration {migration.version} checksum mismatch"
                )
            continue
        if migration.version != len(applied) + 1:
            raise ValueError("RFC-008 migrations cannot be applied out of order")
        try:
            connection.execute("BEGIN")
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                """
                INSERT INTO schema_migrations(version,name,checksum,applied_at)
                VALUES (?,?,?,?)
                """,
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
            applied[migration.version] = (
                migration.name,
                migration.checksum,
            )
        except Exception:
            connection.rollback()
            raise
