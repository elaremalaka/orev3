from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

from orev3.ledger.decision_capture import (
    capture_paper_decision,
    capture_passive_decision,
)
from orev3.ledger.identifiers import deterministic_id, source_record_id
from orev3.ledger.observation_capture import capture_observation
from orev3.ledger.reconciliation import reconcile
from orev3.ledger.reporting import export_tables, ledger_report, strict_json_text
from orev3.ledger.schemas import (
    DeploymentRecord,
    Provenance,
    RewardRecord,
    RpcTransactionObservation,
    WalletSnapshot,
)
from orev3.ledger.storage import LedgerStore

from .conftest import NOW, SIGNATURE, WALLET


def insert_opportunity(store: LedgerStore, snapshot: dict):
    sid = source_record_id("fixture", 1, snapshot)
    opportunity, event = capture_observation(
        snapshot,
        observation_index=0,
        source="fixture",
        source_record_id=sid,
        run_id="run",
        session_id="session",
    )
    with store.connection:
        store.upsert_record("opportunities", opportunity)
        store.insert_event(event)
    return opportunity


def test_no_participation_is_complete(tmp_path: Path, snapshot: dict) -> None:
    with LedgerStore(tmp_path / "ledger.sqlite") as store:
        store.initialize()
        opportunity = insert_opportunity(store, snapshot)
        decision = capture_passive_decision(
            opportunity_id=opportunity.opportunity_id, decision_time=NOW
        )
        with store.connection:
            store.upsert_record("decisions", decision)
        result = reconcile(store)[0]
    assert result.state == "complete_no_participation"
    assert result.completeness_score == 1


def test_full_and_partial_reconciliation(tmp_path: Path, snapshot: dict) -> None:
    with LedgerStore(tmp_path / "ledger.sqlite") as store:
        store.initialize()
        opportunity = insert_opportunity(store, snapshot)
        partial = reconcile(store)[0]
        assert partial.state == "partial_missing_transaction"
        assert "missing_decision" in partial.blocking_gaps

        decision = capture_paper_decision(
            opportunity_id=opportunity.opportunity_id,
            strategy_id="fixture",
            strategy_version="1",
            selected_squares=[1],
            ranking_scores=None,
            deployment_total_lamports=100,
            decision_time=NOW,
            decision_latency_ms=1,
        )
        deployment = DeploymentRecord(
            deployment_intent_id=deterministic_id("deployment", decision.decision_id),
            decision_id=decision.decision_id,
            wallet_public_key=WALLET,
            intended_lamports=100,
            submitted_lamports=100,
            landed_lamports=100,
            selected_squares=[1],
            transaction_signature=SIGNATURE,
            submission_time=NOW,
            confirmation_time=NOW + timedelta(seconds=1),
            status="landed",
        )
        transaction = RpcTransactionObservation(
            transaction_signature=SIGNATURE,
            protocol_status="confirmed_success",
            total_fee_lamports=5,
        )
        reward = RewardRecord(
            opportunity_id=opportunity.opportunity_id,
            round_id=opportunity.round_id,
            wallet_public_key=WALLET,
            gross_sol_return_lamports=110,
            net_sol_return_before_fees_lamports=10,
            base_ore_raw=0,
            motherlode_ore_raw=0,
            total_ore_raw=0,
            reward_time=NOW,
            provenance=Provenance.DIRECT_WALLET_OBSERVATION,
        )
        before = WalletSnapshot(
            wallet_public_key=WALLET,
            snapshot_time=NOW,
            sol_balance_lamports=1000,
            ore_token_balance_raw=0,
            source="fixture",
            commitment="confirmed",
        )
        after = before.model_copy(
            update={
                "snapshot_time": NOW + timedelta(seconds=2),
                "sol_balance_lamports": 1005,
            }
        )
        with store.connection:
            store.upsert_record("decisions", decision)
            store.upsert_record("deployments", deployment)
            store.upsert_record("transactions", transaction)
            store.upsert_record("rewards", reward)
            store.upsert_record("wallet_snapshots", before)
            store.upsert_record("wallet_snapshots", after)
        complete = reconcile(store)[0]
    assert complete.state == "complete"
    assert complete.completeness_score == 1


def test_reports_and_pseudonymized_exports_are_deterministic(
    tmp_path: Path, snapshot: dict
) -> None:
    with LedgerStore(tmp_path / "ledger.sqlite") as store:
        store.initialize()
        opportunity = insert_opportunity(store, snapshot)
        decision = capture_passive_decision(
            opportunity_id=opportunity.opportunity_id, decision_time=NOW
        )
        with store.connection:
            store.upsert_record("decisions", decision)
        reconcile(store)
        report = ledger_report(store)
        first_dir = tmp_path / "first"
        second_dir = tmp_path / "second"
        first = export_tables(
            store, first_dir, pseudonymize_wallets=True
        )
        second = export_tables(
            store, second_dir, pseudonymize_wallets=True
        )
    assert json.loads(strict_json_text(report))["storage"] == "sqlite"
    first_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in first
    }
    second_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in second
    }
    assert first_hashes == second_hashes
    assert WALLET not in "\n".join(
        path.read_text(encoding="utf-8") for path in first
    )
