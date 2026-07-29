from __future__ import annotations

import glob
import os
import signal
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

from orev3.collection.opportunity_builder import (
    IncompleteOpportunityError,
    build_opportunity,
)
from orev3.collection.schemas import SourceCursor, TailRecord
from orev3.collection.tailer import (
    SourceChangedError,
    new_cursor,
    read_complete_lines,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.authorization import CollectionAuthorizationStore
from orev3.rfc008.decisions import (
    SnapshotUnavailable,
    build_decisions,
    snapshot_from_opportunity,
)
from orev3.rfc008.marker import verify_marker
from orev3.rfc008.outcomes import enqueue_pending
from orev3.rfc008.resolver import FinalizedOutcomeResolver
from orev3.rfc008.storage import (
    CollectionTargetReached,
    RFC008Store,
    strict_json,
)
from orev3.ledger.identifiers import deterministic_id


class RFC008Collector:
    def __init__(
        self,
        *,
        store: RFC008Store,
        config: RFC008Config,
        marker_path: str | Path,
        expected_marker_sha256: str,
        resolver: FinalizedOutcomeResolver | None = None,
        authorization_store: CollectionAuthorizationStore | None = None,
        recovery: bool = False,
        session_identifier: str | None = None,
        startup_acknowledgement: Callable[[str, Event], bool] | None = None,
    ) -> None:
        self.store = store
        self.config = config
        self.marker = verify_marker(
            marker_path, config, expected_sha256=expected_marker_sha256
        )
        self.stop_requested = Event()
        self.run_id: str | None = None
        self.resolver = resolver
        self.authorization_store = authorization_store
        self.recovery = recovery
        self.session_identifier = session_identifier
        self.startup_acknowledgement = startup_acknowledgement
        contract = self.store.validate_collection_contract(config=config)
        if authorization_store is not None:
            authorization = authorization_store.status().record
            self.store.validate_collection_contract(
                config=config,
                authorization=authorization,
            )
            if authorization.marker_sha256 != expected_marker_sha256:
                raise ValueError("Authorization marker binding mismatch")
        if contract.completed:
            self.stop_requested.set()
        if (
            resolver is not None
            and self.marker.resolver_configuration_sha256
            != resolver.config.fingerprint
        ):
            raise ValueError("Marker and resolver configuration mismatch")

    def request_stop(self, *_args) -> None:
        self.stop_requested.set()

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self.request_stop)
        signal.signal(signal.SIGTERM, self.request_stop)

    def begin_run(self) -> str:
        if self.store.validate_collection_contract().completed:
            raise CollectionTargetReached(
                "RFC-008 collection already completed"
            )
        run_id = self.session_identifier or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        authorization_consumed = False
        if self.authorization_store is not None:
            self.authorization_store.consume_launch(
                run_id,
                recovery=self.recovery,
            )
            authorization_consumed = True
        try:
            self.store.begin_collection_session(
                run_id,
                recovery=self.recovery,
            )
            if self.recovery:
                self.store.connection.execute(
                    """
                    UPDATE collector_runs
                    SET ended_at=COALESCE(ended_at,?)
                    WHERE ended_at IS NULL AND run_id<>?
                    """,
                    (now.isoformat(), run_id),
                )
            contract = self.store.validate_collection_contract()
            self.store.connection.execute(
                """
                INSERT INTO collector_runs
                (run_id,started_at,process_id,configuration_fingerprint,record_json)
                VALUES (?,?,?,?,?)
                """,
                (
                    run_id,
                    now.isoformat(),
                    os.getpid(),
                    self.config.configuration_fingerprint,
                    strict_json(
                        {
                            "run_id": run_id,
                            "started_at": now.isoformat(),
                            "process_id": os.getpid(),
                            "paper_only": True,
                            "configuration_fingerprint": self.config.configuration_fingerprint,
                            "authorization_identifier": (
                                contract.authorization_identifier
                            ),
                            "authorization_digest": contract.authorization_digest,
                            "ledger_instance_identifier": (
                                contract.ledger_instance_identifier
                            ),
                            "collection_target": contract.collection_target,
                            "collection_mode": contract.collection_mode,
                            "recovery": self.recovery,
                        }
                    ),
                ),
            )
            # Supervision reads the ledger through a separate connection.
            # Publish the complete startup handshake before the first poll can
            # perform a potentially long batch inside its own transaction.
            self.store.connection.commit()
        except Exception:
            self.store.connection.rollback()
            if authorization_consumed and self.authorization_store is not None:
                self.authorization_store.fail(run_id)
            raise
        self.run_id = run_id
        return run_id

    def finish_run(self) -> None:
        if self.run_id:
            contract = self.store.validate_collection_contract()
            self.store.connection.execute(
                "UPDATE collector_runs SET ended_at=? WHERE run_id=?",
                (datetime.now(timezone.utc).isoformat(), self.run_id),
            )
            self.store.end_collection_session(self.run_id)
            if (
                contract.completed
                and self.authorization_store is not None
                and self.authorization_store.status().lifecycle_state
                == "active"
            ):
                self.authorization_store.complete(self.run_id)

    def _transition(self, prior_round: int, at: datetime) -> None:
        self.store.transition_round(prior_round, at)
        enqueue_pending(self.store, prior_round, at=at)
        if not self.store.has_snapshot(prior_round):
            self.store.exclude_round(prior_round, "no_timely_complete_snapshot")

    def process_record(self, record: TailRecord) -> None:
        if self.store.validate_collection_contract().completed:
            self.stop_requested.set()
            return
        if not self.store.mark_source_record(
            record.record_id,
            record.source_id,
            record.source_line_number,
            record.content_sha256,
        ):
            return
        self.store.increment("source_records")
        try:
            board_round = int(record.raw["board"]["round_id"])
        except (KeyError, TypeError, ValueError):
            self.store.increment("malformed_records")
            return
        if board_round <= self.marker.latest_preholdout_round_id:
            self.store.increment("preboundary_records_ignored")
            return
        last_raw = self.store.metadata("last_round_id")
        last_round = int(last_raw) if last_raw else None
        if last_round is not None and board_round != last_round:
            if board_round < last_round:
                self.store.increment("out_of_order_round_records")
                return
            self._transition(last_round, record.observed_at)
        self.store.set_metadata("last_round_id", str(board_round))
        self.store.start_round(board_round, record.observed_at)
        if str(record.raw.get("commitment", "")).lower() == "finalized":
            # Observer records never bypass the validated provider resolver.
            self.store.increment("unvalidated_finalized_source_records")
            self.store.exclude_round(
                board_round, "unvalidated_finalized_observer_record"
            )
            return
        if self.store.has_snapshot(board_round):
            return
        try:
            opportunity = build_opportunity(
                record,
                observation_index=self.store.next_observation_index(board_round),
            )
            snapshot = snapshot_from_opportunity(
                opportunity,
                self.config,
                source_content_sha256=record.content_sha256,
            )
        except SnapshotUnavailable:
            return
        except IncompleteOpportunityError:
            self.store.increment("incomplete_opportunities")
            return
        decisions = build_decisions(snapshot, self.config)
        inserted = self.store.insert_snapshot_and_decisions(snapshot, decisions)
        if inserted and self.store.validate_collection_contract().completed:
            self.stop_requested.set()

    def poll_once(self) -> int:
        processed = 0
        for name in sorted(glob.glob(self.config.source_glob)):
            path = Path(name)
            cursor = self.store.load_cursor(path)
            if cursor is None:
                resolved = str(path.resolve())
                matches = [
                    value
                    for value in self.marker.source_identities
                    if value.split("|", 1)[0] == resolved
                ]
                stat = path.stat()
                if len(matches) == 1:
                    _, inode, offset, line = matches[0].split("|")
                    if stat.st_ino != int(inode) or stat.st_size < int(offset):
                        self.store.increment("source_corruption")
                        raise SourceChangedError(
                            "Frozen marker cursor no longer matches source"
                        )
                    cursor = SourceCursor(
                        source_id=deterministic_id("collection-source", resolved),
                        source_path=str(path),
                        byte_offset=int(offset),
                        line_number=int(line),
                        source_size=stat.st_size,
                        source_inode=stat.st_ino,
                    )
                elif not matches:
                    created = getattr(stat, "st_birthtime", stat.st_ctime)
                    if created < self.marker.created_at.timestamp():
                        raise ValueError(
                            f"Pre-marker source lacks a frozen cursor: {resolved}"
                        )
                    cursor = new_cursor(path, start_at_end=False)
                    self.store.audit(
                        "post_marker_source_discovered",
                        {
                            "source_path": resolved,
                            "source_inode": stat.st_ino,
                            "paper_only": True,
                        },
                    )
                else:
                    raise ValueError(
                        f"Marker has duplicate frozen cursors for {resolved}"
                    )
            try:
                batch = read_complete_lines(
                    path,
                    cursor,
                    max_records=self.config.batch_size,
                    seen_content_hashes=(
                        self.store.source_hashes(cursor.source_id)
                        if cursor is not None
                        else set()
                    ),
                    start_at_end=False,
                )
            except SourceChangedError:
                self.store.increment("source_corruption")
                raise
            self.store.increment("malformed_records", batch.malformed_records)
            self.store.increment("duplicate_source_records", batch.duplicate_records)
            for record in batch.records:
                try:
                    self.process_record(record)
                except CollectionTargetReached:
                    self.stop_requested.set()
                    break
                processed += 1
                if self.stop_requested.is_set():
                    cursor = batch.cursor.model_copy(
                        update={
                            "byte_offset": record.end_offset,
                            "line_number": record.source_line_number,
                        }
                    )
                    break
            self.store.save_cursor(
                cursor if self.stop_requested.is_set() else batch.cursor
            )
            if self.stop_requested.is_set():
                break
        if self.resolver is not None and not self.stop_requested.is_set():
            self.resolver.process_due()
        return processed

    def run(self) -> None:
        if self.store.validate_collection_contract().completed:
            return
        self.install_signal_handlers()
        self.begin_run()
        try:
            if (
                self.startup_acknowledgement is not None
                and not self.startup_acknowledgement(
                    str(self.run_id), self.stop_requested
                )
            ):
                return
            while not self.stop_requested.is_set():
                with self.store.connection:
                    processed = self.poll_once()
                    if self.store.validate_collection_contract().completed:
                        self.stop_requested.set()
                if not processed:
                    self.stop_requested.wait(self.config.poll_interval_seconds)
        finally:
            with self.store.connection:
                self.finish_run()
