from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orev3.collection.schemas import SourceCursor
from orev3.rfc008.authorization import (
    CollectionAuthorizationRecord,
    build_authorization_record,
    canonical_path,
    path_identity,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.migrations import (
    APPLICATION_ID,
    DATABASE_FAMILY,
    MIGRATIONS,
    apply_migrations,
)
from orev3.rfc008.schemas import (
    ArmDecision,
    DecisionSnapshot,
    OutcomeEvidence,
    OutcomeQueueRecord,
    RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION,
    RoundAccounting,
)


SCHEMA_VERSION = len(MIGRATIONS)
PROTECTED_LEDGER_NAMES = {
    "rfc007_live_ledger_v1.sqlite",
    "participant_ledger_v1.sqlite",
}
CANONICAL_PRODUCTION_LEDGER_NAME = "rfc008_paper_ledger_v1.sqlite"
LEDGER_SCHEMA_VERSION = 1


class CollectionTargetReached(RuntimeError):
    pass


class CollectionContractError(ValueError):
    pass


@dataclass(frozen=True)
class LedgerInitialization:
    authorization: CollectionAuthorizationRecord
    collection_seed_cursors: tuple[dict[str, object], ...]
    publication_cursors: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class CollectionContractStatus:
    ledger_schema_version: int
    evidence_schema_version: int
    rfc_identifier: str
    ledger_family_identifier: str
    ledger_instance_identifier: str
    canonical_ledger_path: str
    canonical_ledger_path_identity: str
    authorization_identifier: str
    authorization_digest: str
    collection_mode: str
    collection_target: int
    committed_opportunity_count: int
    collection_state: str
    created_at: str
    completion_timestamp: str | None
    active_session_identity: str | None
    last_committed_opportunity_identity: str | None
    collection_seed_cursors: tuple[dict[str, object], ...]
    publication_cursors: tuple[dict[str, object], ...]
    last_observed_cursors: tuple[dict[str, object], ...]
    immutable_release: CollectionAuthorizationRecord

    @property
    def remaining_opportunity_count(self) -> int:
        return self.collection_target - self.committed_opportunity_count

    @property
    def completed(self) -> bool:
        return self.collection_state == "completed"


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
        initialization: LedgerInitialization | None = None,
        identity_path: str | Path | None = None,
    ) -> None:
        self.path = Path(path)
        self.identity_path = Path(identity_path or path)
        if create:
            assert_safe_new_ledger_path(self.path)
            if (
                self.identity_path.name == CANONICAL_PRODUCTION_LEDGER_NAME
                and initialization is None
            ):
                raise PermissionError(
                    "Canonical RFC-008 production ledger requires a persisted "
                    "collection authorization"
                )
            self.path.parent.mkdir(parents=True, exist_ok=True)
        if read_only:
            uri = f"file:{self.path.resolve()}?mode=ro"
            self.connection = sqlite3.connect(uri, uri=True)
        else:
            if not create and not self.path.exists():
                raise FileNotFoundError(self.path)
            self.connection = sqlite3.connect(self.path)
            self.connection.execute(
                f"PRAGMA journal_mode={'DELETE' if create else 'WAL'}"
            )
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute(
                f"PRAGMA busy_timeout={int(config.busy_timeout_ms if config else 5000)}"
            )
        self.connection.row_factory = sqlite3.Row
        if create:
            if config is None:
                raise ValueError("Creating a ledger requires RFC-008 configuration")
            self.connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
            apply_migrations(self.connection)
            self.initialize(
                config,
                initialization
                or self._fixture_initialization(config, self.identity_path),
            )
        elif not read_only:
            self._verify_application_identity()
            if (
                self.identity_path.name == CANONICAL_PRODUCTION_LEDGER_NAME
                and self._applied_schema_version() != SCHEMA_VERSION
            ):
                raise ValueError(
                    "RFC-008 production ledger migration requires explicit "
                    "release authorization"
                )
            apply_migrations(self.connection)
            self.connection.commit()
        self.verify_identity(config)
        if not read_only and self._metadata_or_none("ledger_state") == "frozen":
            self.connection.execute("PRAGMA query_only=ON")

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    @staticmethod
    def _fixture_initialization(
        config: RFC008Config,
        path: str | Path,
    ) -> LedgerInitialization:
        record = build_authorization_record(
            authorization_path=Path(path).with_suffix(".authorization.sqlite"),
            ledger_path=path,
            branch="fixture",
            repository_head="0" * 40,
            implementation_commit="0" * 40,
            active_approval_sha256="0" * 64,
            immediate_predecessor_sha256="0" * 64,
            approval_chain_anchor="0" * 64,
            marker_sha256="0" * 64,
            marker_sidecar_sha256="0" * 64,
            candidate_sha256=config.candidate_configuration_sha256,
            experiment_id=config.experiment_id,
            protocol_version=config.protocol_version,
            configuration_fingerprint=config.configuration_fingerprint,
            resolver_fingerprint="0" * 64,
            migration_set_sha256="0" * 64,
            cli_sha256="0" * 64,
            runbook_sha256="0" * 64,
            burn_in_evidence_sha256="0" * 64,
            burn_in_ledger_sha256="0" * 64,
            approval_manifest_sha256=config.approval_manifest_sha256,
            external_rpc_burn_in_performed=True,
            nonce=f"fixture-{uuid.uuid4()}",
        )
        return LedgerInitialization(
            authorization=record,
            collection_seed_cursors=(),
            publication_cursors=(),
        )

    def initialize(
        self,
        config: RFC008Config,
        initialization: LedgerInitialization,
    ) -> None:
        authorization = initialization.authorization
        if authorization.canonical_ledger_path != canonical_path(
            self.identity_path
        ):
            raise CollectionContractError(
                "Authorization is bound to another ledger path"
            )
        created_at = datetime.now(timezone.utc).isoformat()
        with self.connection:
            values = {
                "schema_version": str(SCHEMA_VERSION),
                "database_family": DATABASE_FAMILY,
                "experiment_id": config.experiment_id,
                "configuration_fingerprint": config.configuration_fingerprint,
                "candidate_configuration_sha256": config.candidate_configuration_sha256,
                "approval_manifest_sha256": config.approval_manifest_sha256,
                "last_round_id": "",
                "ledger_state": "collecting",
            }
            self.connection.executemany(
                "INSERT INTO metadata(key,value) VALUES (?,?)", values.items()
            )
            self.connection.execute(
                """
                INSERT INTO collection_contract(
                  singleton,ledger_schema_version,evidence_schema_version,
                  rfc_identifier,ledger_family_identifier,
                  ledger_instance_identifier,canonical_ledger_path,
                  canonical_ledger_path_identity,authorization_identifier,
                  authorization_digest,collection_mode,collection_target,
                  committed_opportunity_count,collection_state,created_at,
                  completion_timestamp,active_session_identity,
                  last_committed_opportunity_identity,
                  collection_seed_cursor_json,publication_cursor_json,
                  last_observed_cursor_json,immutable_release_json
                ) VALUES (
                  1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
                """,
                (
                    LEDGER_SCHEMA_VERSION,
                    RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION,
                    "RFC-008",
                    DATABASE_FAMILY,
                    authorization.ledger_instance_identifier,
                    authorization.canonical_ledger_path,
                    authorization.canonical_ledger_path_identity,
                    authorization.authorization_identifier,
                    authorization.authorization_digest,
                    authorization.collection_mode,
                    authorization.collection_target,
                    0,
                    "initialized",
                    created_at,
                    None,
                    None,
                    None,
                    strict_json(initialization.collection_seed_cursors),
                    strict_json(initialization.publication_cursors),
                    strict_json(()),
                    strict_json(authorization),
                ),
            )
            self.audit(
                "ledger_initialized",
                {
                    "schema_version": SCHEMA_VERSION,
                    "ledger_schema_version": LEDGER_SCHEMA_VERSION,
                    "authorization_identifier": (
                        authorization.authorization_identifier
                    ),
                    "ledger_instance_identifier": (
                        authorization.ledger_instance_identifier
                    ),
                    "collection_target": authorization.collection_target,
                    "paper_only": True,
                    "live_actions": 0,
                },
            )

    def _applied_schema_version(self) -> int:
        try:
            row = self.connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()
        except sqlite3.OperationalError:
            return 0
        return int(row[0] or 0)

    def _verify_application_identity(self) -> None:
        application_id = int(
            self.connection.execute("PRAGMA application_id").fetchone()[0]
        )
        if application_id != APPLICATION_ID:
            raise ValueError("Not an RFC-008 database application")

    def _metadata_or_none(self, key: str) -> str | None:
        try:
            row = self.connection.execute(
                "SELECT value FROM metadata WHERE key=?", (key,)
            ).fetchone()
        except sqlite3.OperationalError:
            return None
        return str(row[0]) if row is not None else None

    def verify_identity(self, config: RFC008Config | None) -> None:
        self._verify_application_identity()
        try:
            values = dict(self.connection.execute("SELECT key,value FROM metadata"))
        except sqlite3.OperationalError as exc:
            raise ValueError("Not an initialized RFC-008 ledger") from exc
        if int(values.get("schema_version", -1)) != SCHEMA_VERSION:
            raise ValueError("Unsupported RFC-008 schema version")
        if values.get("database_family") != DATABASE_FAMILY:
            raise ValueError("RFC-008 database family sentinel mismatch")
        applied = {
            int(row[0]): str(row[1])
            for row in self.connection.execute(
                "SELECT version,checksum FROM schema_migrations"
            )
        }
        expected = {migration.version: migration.checksum for migration in MIGRATIONS}
        if applied != expected:
            raise ValueError("RFC-008 migration history mismatch")
        if config is not None:
            if values.get("experiment_id") != config.experiment_id:
                raise ValueError("RFC-008 experiment identity mismatch")
            if values.get("configuration_fingerprint") != config.configuration_fingerprint:
                raise ValueError("RFC-008 configuration fingerprint mismatch")
        self.validate_collection_contract(config=config)

    def collection_contract(self) -> CollectionContractStatus:
        row = self.connection.execute(
            "SELECT * FROM collection_contract WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise CollectionContractError(
                "RFC-008 collection contract is missing"
            )
        try:
            release = CollectionAuthorizationRecord.model_validate_json(
                str(row["immutable_release_json"])
            )
            seed = tuple(json.loads(str(row["collection_seed_cursor_json"])))
            publication = tuple(
                json.loads(str(row["publication_cursor_json"]))
            )
            observed_raw = row["last_observed_cursor_json"]
            observed = tuple(json.loads(str(observed_raw))) if observed_raw else ()
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise CollectionContractError(
                f"RFC-008 collection contract JSON is invalid: {exc}"
            ) from exc
        return CollectionContractStatus(
            ledger_schema_version=int(row["ledger_schema_version"]),
            evidence_schema_version=int(row["evidence_schema_version"]),
            rfc_identifier=str(row["rfc_identifier"]),
            ledger_family_identifier=str(row["ledger_family_identifier"]),
            ledger_instance_identifier=str(row["ledger_instance_identifier"]),
            canonical_ledger_path=str(row["canonical_ledger_path"]),
            canonical_ledger_path_identity=str(
                row["canonical_ledger_path_identity"]
            ),
            authorization_identifier=str(row["authorization_identifier"]),
            authorization_digest=str(row["authorization_digest"]),
            collection_mode=str(row["collection_mode"]),
            collection_target=int(row["collection_target"]),
            committed_opportunity_count=int(
                row["committed_opportunity_count"]
            ),
            collection_state=str(row["collection_state"]),
            created_at=str(row["created_at"]),
            completion_timestamp=row["completion_timestamp"],
            active_session_identity=row["active_session_identity"],
            last_committed_opportunity_identity=row[
                "last_committed_opportunity_identity"
            ],
            collection_seed_cursors=seed,
            publication_cursors=publication,
            last_observed_cursors=observed,
            immutable_release=release,
        )

    def validate_collection_contract(
        self,
        *,
        config: RFC008Config | None = None,
        authorization: CollectionAuthorizationRecord | None = None,
    ) -> CollectionContractStatus:
        owns_transaction = not self.connection.in_transaction
        if owns_transaction:
            self.connection.execute("BEGIN")
        try:
            contract = self._validate_collection_contract_snapshot(
                config=config,
                authorization=authorization,
            )
            if owns_transaction:
                self.connection.commit()
            return contract
        except Exception:
            if owns_transaction:
                self.connection.rollback()
            raise

    def _validate_collection_contract_snapshot(
        self,
        *,
        config: RFC008Config | None,
        authorization: CollectionAuthorizationRecord | None,
    ) -> CollectionContractStatus:
        contract = self.collection_contract()
        failures: list[str] = []
        if contract.ledger_schema_version != LEDGER_SCHEMA_VERSION:
            failures.append("ledger schema version")
        if (
            contract.evidence_schema_version
            != RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION
        ):
            failures.append("evidence schema version")
        if contract.rfc_identifier != "RFC-008":
            failures.append("RFC identifier")
        if contract.ledger_family_identifier != DATABASE_FAMILY:
            failures.append("ledger family")
        if contract.canonical_ledger_path != canonical_path(self.identity_path):
            failures.append("canonical ledger path")
        if contract.canonical_ledger_path_identity != path_identity(
            self.identity_path
        ):
            failures.append("ledger path identity")
        release = contract.immutable_release
        column_matches = {
            "ledger instance": (
                contract.ledger_instance_identifier
                == release.ledger_instance_identifier
            ),
            "authorization identifier": (
                contract.authorization_identifier
                == release.authorization_identifier
            ),
            "authorization digest": (
                contract.authorization_digest == release.authorization_digest
            ),
            "mode": contract.collection_mode == release.collection_mode,
            "target": (
                contract.collection_target == release.collection_target == 600
            ),
        }
        failures.extend(
            name for name, matches in column_matches.items() if not matches
        )
        if config is not None:
            if (
                release.configuration_fingerprint
                != config.configuration_fingerprint
            ):
                failures.append("configuration fingerprint")
            if release.experiment_id != config.experiment_id:
                failures.append("experiment identity")
            if (
                release.candidate_sha256
                != config.candidate_configuration_sha256
            ):
                failures.append("candidate identity")
        if authorization is not None and release != authorization:
            failures.append("persisted authorization binding")
        sequence = self.connection.execute(
            """
            SELECT
              COUNT(*) AS row_count,
              MIN(committed_opportunity_sequence) AS first_sequence,
              MAX(committed_opportunity_sequence) AS last_sequence,
              SUM(
                CASE WHEN committed_opportunity_sequence IS NULL
                THEN 1 ELSE 0 END
              ) AS missing_sequence_count
            FROM decision_snapshots
            """
        ).fetchone()
        row_count = int(sequence["row_count"])
        canonical_last = None
        canonical_last_valid = False
        if contract.committed_opportunity_count > 0:
            canonical_last_row = self.connection.execute(
                """
                SELECT snapshot_id
                FROM decision_snapshots
                WHERE committed_opportunity_sequence=?
                """,
                (contract.committed_opportunity_count,),
            ).fetchone()
            if canonical_last_row is not None:
                canonical_last = str(canonical_last_row["snapshot_id"])
                try:
                    canonical_last_valid = (
                        str(uuid.UUID(canonical_last)) == canonical_last
                    )
                except ValueError:
                    canonical_last_valid = False
        sequence_valid = (
            (
                row_count == 0
                and sequence["first_sequence"] is None
                and sequence["last_sequence"] is None
                and int(sequence["missing_sequence_count"] or 0) == 0
            )
            or (
                row_count > 0
                and int(sequence["first_sequence"] or 0) == 1
                and int(sequence["last_sequence"] or 0) == row_count
                and int(sequence["missing_sequence_count"] or 0) == 0
            )
        )
        if row_count != contract.committed_opportunity_count:
            failures.append("canonical opportunity count")
        if not sequence_valid:
            failures.append("committed opportunity sequence")
        if contract.committed_opportunity_count == 0:
            if contract.last_committed_opportunity_identity is not None:
                failures.append("unexpected last opportunity identity")
        elif canonical_last is None:
            failures.append("canonical last opportunity")
        elif not canonical_last_valid:
            failures.append("canonical last opportunity identity")
        elif contract.last_committed_opportunity_identity != canonical_last:
            failures.append("last opportunity identity")
        if contract.committed_opportunity_count > contract.collection_target:
            failures.append("opportunity target exceeded")
        if contract.committed_opportunity_count == contract.collection_target:
            if (
                contract.collection_state != "completed"
                or contract.completion_timestamp is None
                or contract.last_committed_opportunity_identity is None
            ):
                failures.append("completed target state")
        elif contract.collection_state == "completed":
            failures.append("premature completed state")
        if failures:
            raise CollectionContractError(
                "RFC-008 collection contract mismatch: "
                + ", ".join(failures)
            )
        return contract

    def begin_collection_session(
        self,
        session_identifier: str,
        *,
        recovery: bool = False,
    ) -> None:
        contract = self.validate_collection_contract()
        if contract.completed:
            raise CollectionTargetReached(
                "RFC-008 collection already completed at target"
            )
        if (
            not recovery
            and contract.active_session_identity
            not in (None, session_identifier)
        ):
            raise PermissionError("Another RFC-008 collector session is active")
        if recovery and contract.collection_state not in {
            "initialized",
            "active",
        }:
            raise PermissionError(
                "RFC-008 recovery requires an active collection state"
            )
        cursor = self.connection.execute(
            """
            UPDATE collection_contract
            SET collection_state='active',active_session_identity=?
            WHERE singleton=1
              AND collection_state IN ('initialized','active')
              AND committed_opportunity_count < collection_target
              AND (
                ?=1
                OR
                active_session_identity IS NULL
                OR active_session_identity=?
              )
            """,
            (
                session_identifier,
                int(recovery),
                session_identifier,
            ),
        )
        if cursor.rowcount != 1:
            raise PermissionError(
                "RFC-008 collector session activation rejected"
            )

    def end_collection_session(self, session_identifier: str) -> None:
        contract = self.validate_collection_contract()
        if contract.active_session_identity != session_identifier:
            raise PermissionError("RFC-008 collector session identity mismatch")
        self.connection.execute(
            """
            UPDATE collection_contract
            SET active_session_identity=NULL
            WHERE singleton=1 AND active_session_identity=?
            """,
            (session_identifier,),
        )

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

    def data_version(self) -> int:
        return int(self.connection.execute("PRAGMA data_version").fetchone()[0])

    def source_cursor_records(self) -> tuple[dict[str, object], ...]:
        return tuple(
            json.loads(row[0])
            for row in self.connection.execute(
                "SELECT record_json FROM source_cursors ORDER BY source_id"
            )
        )

    def freeze(self, freeze_id: str, record: dict[str, object]) -> None:
        if self.metadata("ledger_state") == "frozen":
            existing = self.connection.execute(
                "SELECT record_json FROM final_freezes WHERE freeze_id=?",
                (freeze_id,),
            ).fetchone()
            if existing is None or json.loads(existing[0]) != record:
                raise ValueError("Ledger is already frozen with different evidence")
            return
        self.connection.execute(
            """
            INSERT INTO final_freezes
            (freeze_id,created_at,ledger_data_version,record_json)
            VALUES (?,?,?,?)
            """,
            (
                freeze_id,
                str(record["created_at"]),
                int(record["ledger_data_version"]),
                strict_json(record),
            ),
        )
        self.set_metadata("ledger_state", "frozen")

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
        observed = tuple(
            json.loads(row[0])
            for row in self.connection.execute(
                "SELECT record_json FROM source_cursors ORDER BY source_id"
            )
        )
        self.connection.execute(
            """
            UPDATE collection_contract
            SET last_observed_cursor_json=?
            WHERE singleton=1
            """,
            (strict_json(observed),),
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
        snapshot = DecisionSnapshot.model_validate(
            snapshot.model_dump(mode="python")
        )
        decisions = tuple(
            ArmDecision.model_validate(
                decision.model_dump(mode="python")
            )
            for decision in decisions
        )
        contract = self.validate_collection_contract()
        committed_sequence = contract.committed_opportunity_count + 1
        self.connection.execute("SAVEPOINT rfc008_opportunity")
        try:
            self.connection.execute(
                """
                INSERT INTO decision_snapshots
                (
                  snapshot_id,round_id,source_content_sha256,record_json,
                  committed_opportunity_sequence
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.round_id,
                    snapshot.source_content_sha256,
                    strict_json(snapshot),
                    committed_sequence,
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
            self.connection.execute("RELEASE SAVEPOINT rfc008_opportunity")
        except sqlite3.IntegrityError as exc:
            self.connection.execute(
                "ROLLBACK TO SAVEPOINT rfc008_opportunity"
            )
            self.connection.execute("RELEASE SAVEPOINT rfc008_opportunity")
            if "collection target reached" in str(exc):
                raise CollectionTargetReached(
                    "RFC-008 collection target reached; opportunity rejected"
                ) from exc
            self.increment("duplicate_decisions")
            return False
        self.increment("decision_snapshots")
        self.increment("arm_decisions", len(decisions))
        self.validate_collection_contract()
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


def create_authorized_ledger(
    path: str | Path,
    *,
    config: RFC008Config,
    initialization: LedgerInitialization,
) -> CollectionContractStatus:
    target = assert_safe_new_ledger_path(path)
    if initialization.authorization.canonical_ledger_path != canonical_path(
        target
    ):
        raise CollectionContractError(
            "Authorization does not bind the requested production ledger"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with RFC008Store(
            temporary,
            config=config,
            create=True,
            initialization=initialization,
            identity_path=target,
        ) as store:
            contract = store.validate_collection_contract(
                config=config,
                authorization=initialization.authorization,
            )
            store.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
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
        with RFC008Store(
            target,
            config=config,
            read_only=True,
        ) as opened:
            return opened.validate_collection_contract(
                config=config,
                authorization=initialization.authorization,
            )
    finally:
        temporary.unlink(missing_ok=True)
