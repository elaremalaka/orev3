from __future__ import annotations

import glob
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

from orev3.collection.config import CollectionConfig
from orev3.collection.cursor_store import CollectionStore
from orev3.collection.opportunity_builder import (
    IncompleteOpportunityError,
    build_opportunity,
    partial_record,
)
from orev3.collection.outcome_linker import (
    corrected_outcome,
    load_outcomes,
    outcome_from_observer_record,
)
from orev3.collection.paper_accounting import account_paper_decision
from orev3.collection.paper_strategy import create_paper_decision
from orev3.collection.schemas import (
    FinalOutcome,
    PaperDecision,
    PaperReconciliation,
)
from orev3.collection.tailer import SourceChangedError, read_complete_lines
from orev3.ledger.event_types import EventType
from orev3.ledger.identifiers import (
    deterministic_id,
    event_id,
    opportunity_id,
)
from orev3.ledger.schemas import (
    DeploymentRecord,
    LedgerEvent,
    OpportunityRecord,
    StrategyDecisionRecord,
)


class PaperCollector:
    def __init__(
        self,
        *,
        store: CollectionStore,
        config: CollectionConfig,
        mode: str,
    ) -> None:
        self.store = store
        self.config = config
        self.mode = mode
        self.stop_requested = Event()
        self.started_monotonic = time.monotonic()
        self.outcomes, self.outcome_metrics = load_outcomes(
            config.outcome_source
        )
        self.initial_sources: set[str] = set()

    def request_stop(self, *_args) -> None:
        self.stop_requested.set()

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self.request_stop)
        signal.signal(signal.SIGTERM, self.request_stop)

    def _save_partial(
        self,
        record,
        error: IncompleteOpportunityError,
    ) -> None:
        expired = error.reason == "incomplete_25_square_board"
        value = partial_record(record, error, expired=expired)
        self.store.insert_json_record(
            "partial_opportunities",
            "partial_id",
            str(value["partial_id"]),
            value,
            extra={
                "source_id": value["source_id"],
                "round_id": value["round_id"],
                "expired": int(expired),
                "reason": value["reason"],
            },
        )
        self.store.increment(
            "opportunities_expired" if expired else "opportunities_partial"
        )

    def _save_complete(self, record, opportunity) -> bool:
        oid = opportunity_id(
            opportunity.round_id, opportunity.observation_index
        )
        ledger_opportunity = OpportunityRecord(
            opportunity_id=oid,
            round_id=opportunity.round_id,
            observation_index=opportunity.observation_index,
            observed_at=opportunity.observed_at,
            seconds_remaining=(
                opportunity.slots_remaining * 0.4
                if opportunity.slots_remaining is not None
                else None
            ),
            board_snapshot_reference=opportunity.source_reference,
            round_state_reference=opportunity.source_reference,
            data_coverage="complete_25_square_board",
            outcome_source=None,
        )
        if not self.store.ledger.upsert_record(
            "opportunities", ledger_opportunity
        ):
            self.store.increment("duplicate_opportunities")
            return False
        decision_time = (
            opportunity.observed_at
            if self.mode == "historical_replay_burn_in"
            else datetime.now(timezone.utc)
        )
        decision = create_paper_decision(
            opportunity, self.config, decision_time=decision_time
        )
        inserted_decision = self.store.insert_json_record(
            "paper_decisions",
            "decision_id",
            decision.decision_id,
            decision,
            extra={"opportunity_id": oid},
        )
        if not inserted_decision:
            self.store.increment("duplicate_decisions")
            return False
        ledger_decision = StrategyDecisionRecord(
            decision_id=decision.decision_id,
            opportunity_id=oid,
            strategy_id=decision.strategy_id,
            strategy_version=decision.strategy_version,
            mode="paper",
            selected_squares=decision.selected_squares,
            ranking_scores=decision.ranking_scores,
            deployment_total_lamports=decision.deployment_total_lamports,
            allocation_by_square=decision.allocation_by_square,
            decision_time=decision.decision_time,
            decision_latency_ms=decision.decision_latency_ms,
            participated=decision.participated,
            no_deploy_reason=decision.no_deploy_reason,
        )
        self.store.ledger.upsert_record("decisions", ledger_decision)
        deployment_id = deterministic_id(
            "rfc007-paper-deployment-intent", decision.decision_id
        )
        deployment = DeploymentRecord(
            deployment_intent_id=deployment_id,
            decision_id=decision.decision_id,
            wallet_public_key=None,
            intended_lamports=decision.deployment_total_lamports,
            submitted_lamports=None,
            landed_lamports=None,
            selected_squares=decision.selected_squares,
            transaction_signature=None,
            submission_time=None,
            confirmation_time=None,
            status="paper_intent_only_never_submitted",
            failure_reason=None,
        )
        self.store.ledger.upsert_record("deployments", deployment)
        event = LedgerEvent(
            event_id=event_id(
                EventType.PAPER_DECISION_CREATED.value,
                record.source_path,
                record.record_id,
            ),
            event_type=EventType.PAPER_DECISION_CREATED,
            event_time=decision.decision_time,
            observed_at=decision.decision_time,
            source=record.source_path,
            source_record_id=record.record_id,
            run_id=deterministic_id(
                "rfc007-run", self.config.configuration_hash
            ),
            session_id=self.mode,
            round_id=opportunity.round_id,
            observation_index=opportunity.observation_index,
            payload={
                "decision_id": decision.decision_id,
                "configuration_hash": self.config.configuration_hash,
                "paper_only": True,
                "transaction_built": False,
                "transaction_submitted": False,
            },
        )
        self.store.ledger.insert_event(event)
        self.store.increment("opportunities_completed")
        self.store.increment("paper_decisions_created")
        outcome = self.outcomes.get(opportunity.round_id)
        if outcome is None:
            self.store.increment("outcomes_missing")
            reconciliation = PaperReconciliation(
                opportunity_id=oid,
                decision_linked=True,
                outcome_linked=False,
                accounting_linked=False,
                provenance_complete=False,
                state="partial_missing_outcome",
                blocking_gaps=["missing_final_outcome"],
                classification="paper_not_wallet_realized",
            )
            self.store.increment("reconciliations_partial")
        else:
            self.store.insert_json_record(
                "final_outcomes",
                "outcome_id",
                outcome.outcome_id,
                outcome,
                extra={
                    "round_id": outcome.round_id,
                    "version": outcome.version,
                },
            )
            accounting = account_paper_decision(
                decision, outcome, self.config
            )
            self.store.insert_json_record(
                "paper_accounting",
                "accounting_id",
                accounting.accounting_id,
                accounting,
                extra={
                    "opportunity_id": oid,
                    "decision_id": decision.decision_id,
                    "outcome_id": outcome.outcome_id,
                },
            )
            provenance_complete = set(accounting.provenance.values()) <= {
                "reconstructed",
                "configured_assumption",
                "unavailable",
            }
            reconciliation = PaperReconciliation(
                opportunity_id=oid,
                decision_linked=True,
                outcome_linked=True,
                accounting_linked=True,
                provenance_complete=provenance_complete,
                state=(
                    "complete_paper_reconstructed"
                    if provenance_complete
                    else "failed_provenance"
                ),
                blocking_gaps=[] if provenance_complete else ["invalid_provenance"],
                classification="paper_not_wallet_realized",
            )
            self.store.increment("outcomes_linked")
            self.store.increment(
                "reconciliations_complete"
                if provenance_complete
                else "reconciliations_partial"
            )
        self.store.insert_json_record(
            "paper_reconciliation",
            "opportunity_id",
            oid,
            reconciliation,
            extra={"state": reconciliation.state},
        )
        return True

    def _persist_outcome(self, outcome: FinalOutcome) -> FinalOutcome:
        existing = self.outcomes.get(outcome.round_id)
        selected = outcome
        if existing is not None:
            selected = corrected_outcome(existing, outcome)
            if selected is existing:
                return existing
        self.outcomes[outcome.round_id] = selected
        self.store.insert_json_record(
            "final_outcomes",
            "outcome_id",
            selected.outcome_id,
            selected,
            extra={
                "round_id": selected.round_id,
                "version": selected.version,
            },
        )
        return selected

    def _link_late_outcome(self, outcome: FinalOutcome) -> int:
        selected = self._persist_outcome(outcome)
        rows = self.store.connection.execute(
            """
            SELECT p.record_json
            FROM paper_decisions p
            JOIN opportunities o ON o.opportunity_id = p.opportunity_id
            WHERE o.round_id = ?
            ORDER BY p.opportunity_id
            """,
            (selected.round_id,),
        ).fetchall()
        linked = 0
        for row in rows:
            decision = PaperDecision.model_validate_json(row[0])
            exists = self.store.connection.execute(
                """
                SELECT 1 FROM paper_accounting
                WHERE opportunity_id = ?
                """,
                (decision.opportunity_id,),
            ).fetchone()
            if exists:
                continue
            accounting = account_paper_decision(
                decision, selected, self.config
            )
            self.store.insert_json_record(
                "paper_accounting",
                "accounting_id",
                accounting.accounting_id,
                accounting,
                extra={
                    "opportunity_id": decision.opportunity_id,
                    "decision_id": decision.decision_id,
                    "outcome_id": selected.outcome_id,
                },
            )
            reconciliation = PaperReconciliation(
                opportunity_id=decision.opportunity_id,
                decision_linked=True,
                outcome_linked=True,
                accounting_linked=True,
                provenance_complete=True,
                state="complete_paper_reconstructed",
                blocking_gaps=[],
                classification="paper_not_wallet_realized",
            )
            self.store.upsert_json_record(
                "paper_reconciliation",
                "opportunity_id",
                decision.opportunity_id,
                reconciliation,
                extra={"state": reconciliation.state},
            )
            self.store.increment("outcomes_linked")
            self.store.increment("reconciliations_complete")
            linked += 1
        return linked

    def process_file(
        self,
        source: str | Path,
        *,
        max_records: int,
        start_at_end: bool = False,
    ) -> dict[str, int | bool]:
        path = Path(source)
        cursor = self.store.load_cursor(path)
        seen = (
            self.store.content_hashes(cursor.source_id)
            if cursor is not None
            else set()
        )
        try:
            batch = read_complete_lines(
                path,
                cursor,
                max_records=max_records,
                seen_content_hashes=seen,
                start_at_end=start_at_end and cursor is None,
            )
        except SourceChangedError:
            with self.store.connection:
                self.store.increment("source_corruption")
            raise
        imported = 0
        with self.store.connection:
            self.store.increment(
                "source_records_seen",
                len(batch.records)
                + batch.malformed_records
                + batch.duplicate_records,
            )
            self.store.increment(
                "source_records_malformed", batch.malformed_records
            )
            self.store.increment(
                "source_records_duplicate", batch.duplicate_records
            )
            for record in batch.records:
                if not self.store.mark_source_record(
                    record_id=record.record_id,
                    source_id=record.source_id,
                    source_line_number=record.source_line_number,
                    content_sha256=record.content_sha256,
                ):
                    self.store.increment("source_records_duplicate")
                    continue
                self.store.increment("source_records_imported")
                finalized, observed_outcome = outcome_from_observer_record(
                    record
                )
                if finalized:
                    if observed_outcome is None:
                        self.store.increment("outcomes_missing_winner")
                    else:
                        self._link_late_outcome(observed_outcome)
                    continue
                round_raw = record.raw.get("board", {}).get("round_id")
                index = (
                    self.store.next_observation_index(int(round_raw))
                    if round_raw is not None
                    else 0
                )
                try:
                    opportunity = build_opportunity(
                        record, observation_index=index
                    )
                except IncompleteOpportunityError as exc:
                    self._save_partial(record, exc)
                    continue
                self.store.increment("opportunities_started")
                if self._save_complete(record, opportunity):
                    imported += 1
            cursor_to_save = batch.cursor
            if (
                self.mode == "historical_replay_burn_in"
                and batch.cursor.last_observed_timestamp is not None
            ):
                cursor_to_save = batch.cursor.model_copy(
                    update={
                        "last_ingested_at": (
                            batch.cursor.last_observed_timestamp
                        )
                    }
                )
            self.store.save_cursor(cursor_to_save)
        return {
            "records_read": len(batch.records),
            "opportunities_imported": imported,
            "malformed_records": batch.malformed_records,
            "duplicate_records": batch.duplicate_records,
            "partial_final_line": batch.partial_final_line,
        }

    def replay(
        self,
        source: str | Path,
        *,
        max_opportunities: int,
    ) -> int:
        while (
            self.store.ledger.count("opportunities") < max_opportunities
            and not self.stop_requested.is_set()
        ):
            remaining = (
                max_opportunities
                - self.store.ledger.count("opportunities")
            )
            result = self.process_file(
                source,
                max_records=min(self.config.batch_size, remaining),
            )
            if result["records_read"] == 0:
                break
        return self.store.ledger.count("opportunities")

    def run_forever(self) -> None:
        self.install_signal_handlers()
        self.initial_sources = set(glob.glob(self.config.source_glob))
        while not self.stop_requested.is_set():
            paths = sorted(glob.glob(self.config.source_glob))
            for path in paths:
                if self.stop_requested.is_set():
                    break
                self.process_file(
                    path,
                    max_records=self.config.batch_size,
                    start_at_end=(
                        self.config.live_start_mode == "end"
                        and path in self.initial_sources
                    ),
                )
            self.stop_requested.wait(self.config.poll_interval_seconds)
