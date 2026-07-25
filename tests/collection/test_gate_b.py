from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orev3.collection.collector import PaperCollector
from orev3.collection.cursor_store import CollectionStore
from orev3.collection.gate_b import (
    GATE_B_TARGET,
    freeze_gate_b_marker,
    gate_b_status,
    load_gate_b_marker,
)
from orev3.ledger.reporting import write_strict_json

from .conftest import snapshot


FROZEN_AT = datetime(2026, 7, 25, 13, 0, tzinfo=timezone.utc)


def append_snapshots(path: Path, indices: range | list[int]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for index in indices:
            handle.write(json.dumps(snapshot(observed_index=index)) + "\n")


def gate_a_store(
    tmp_path: Path,
    config,
) -> tuple[CollectionStore, PaperCollector, Path]:
    source = tmp_path / "observer.jsonl"
    source.write_text("", encoding="utf-8")
    append_snapshots(source, range(100))
    ledger = tmp_path / "ledger.sqlite"
    store = CollectionStore(ledger)
    store.initialize()
    with store.connection:
        store.set_metadata("configuration_hash", config.configuration_hash)
        store.set_metadata("collector_version", config.collector_version)
        store.set_metadata("observer_modified", "0")
    PaperCollector(
        store=store,
        config=config,
        mode="historical_replay_burn_in",
    ).process_file(source, max_records=100)
    collector = PaperCollector(
        store=store,
        config=config,
        mode="real_time_burn_in",
    )
    collector.begin_real_time_run(
        run_id="gate-b-proof-run",
        started_at=FROZEN_AT,
        process_id=123,
        lease_exclusive=True,
    )
    append_snapshots(source, [100])
    collector.process_file(source, max_records=10)
    return store, collector, source


def marker(store: CollectionStore, config):
    return freeze_gate_b_marker(
        store,
        repository_commit="f" * 40,
        branch="research/rfc-007-paper-collection-burn-in",
        configuration_hash=config.configuration_hash,
        created_at=FROZEN_AT,
    )


def persist_marker(
    path: Path,
    value,
) -> str:
    write_strict_json(path, value.model_dump(mode="json"), force=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_marker_is_deterministic_strict_and_post_marker_only(
    tmp_path: Path, config
) -> None:
    store, collector, source = gate_a_store(tmp_path, config)
    with store:
        first = marker(store, config)
        second = marker(store, config)
        assert first == second
        assert first.target_sample_size == GATE_B_TARGET
        assert first.completed_opportunity_count == 101
        assert first.paper_decision_count == 101
        assert first.gate_a_evaluation["passed"]
        assert all(value == 0 for value in first.safety_counters.values())

        marker_path = tmp_path / "gate_b_marker.json"
        marker_hash = persist_marker(marker_path, first)
        assert load_gate_b_marker(
            marker_path, expected_sha256=marker_hash
        ) == first

        append_snapshots(source, [101, 102, 103])
        collector.process_file(source, max_records=10)
        status = gate_b_status(
            store,
            marker_path,
            expected_marker_sha256=marker_hash,
        )
        assert status["sample_count"] == 3
        assert status["remaining_to_collection_complete"] == 997
        assert status["first_included_opportunity"]["rowid"] == (
            first.latest_eligible_opportunity.rowid + 1
        )
        assert status["no_pre_marker_opportunity_included"]
        assert status["opportunity_to_decision_linkage"] == 1
        assert status["duplicate_sample_opportunities"] == 0
        assert status["duplicate_sample_decisions"] == 0
        assert status["cursors_monotonic"]
        assert status["no_records_skipped"]
        assert status["marker_boundary_intact"]
        assert not status["collection_complete"]
        assert not status["reconciliation_complete"]
    with CollectionStore(
        tmp_path / "ledger.sqlite", read_only=True
    ) as reopened:
        resumed_status = gate_b_status(
            reopened,
            marker_path,
            expected_marker_sha256=marker_hash,
        )
        assert resumed_status["sample_count"] == 3
        assert resumed_status["first_included_opportunity"] == (
            status["first_included_opportunity"]
        )


def test_first_thousand_are_frozen_and_late_rows_are_excluded(
    tmp_path: Path, config
) -> None:
    empty_outcomes = tmp_path / "empty_outcomes.jsonl"
    empty_outcomes.write_text("", encoding="utf-8")
    configured = config.model_copy(
        update={"outcome_source": str(empty_outcomes)}
    )
    store, collector, source = gate_a_store(tmp_path, configured)
    with store:
        frozen = marker(store, configured)
        marker_path = tmp_path / "gate_b_marker.json"
        marker_hash = persist_marker(marker_path, frozen)
        append_snapshots(source, range(101, 1102))
        collector.process_file(source, max_records=2_000)
        status = gate_b_status(
            store,
            marker_path,
            expected_marker_sha256=marker_hash,
        )
        assert status["post_marker_eligible_count"] == 1_001
        assert status["sample_count"] == 1_000
        assert status["remaining_to_collection_complete"] == 0
        assert status["collection_complete"]
        assert status["complete_reconciliation_count"] == 0
        assert not status["reconciliation_complete"]
        assert not status["analysis_ready"]
        assert status["last_current_sample_opportunity"]["rowid"] == (
            frozen.latest_eligible_opportunity.rowid + 1_000
        )
        finalized = snapshot(observed_index=1102)
        finalized["round"].update(
            {
                "entropy": 0,
                "slot_hash_hex": "01" + ("00" * 31),
                "deployed_lamports": [100_000] * 25,
                "total_vaulted": 1_000_000,
                "total_winnings": 2_000_000,
            }
        )
        with source.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(finalized) + "\n")
        collector.process_file(source, max_records=10)
        reconciled = gate_b_status(
            store,
            marker_path,
            expected_marker_sha256=marker_hash,
        )
        assert reconciled["sample_count"] == 1_000
        assert reconciled["post_marker_eligible_count"] == 1_001
        assert reconciled["complete_reconciliation_count"] == 1_000
        assert reconciled["reconciliation_complete"]
        assert reconciled["analysis_ready"]


def test_marker_rejects_nonzero_safety_counter(
    tmp_path: Path, config
) -> None:
    store, _collector, _source = gate_a_store(tmp_path, config)
    with store:
        with store.connection:
            store.increment("live_actions")
        with pytest.raises(
            ValueError, match="Gate B safety counters are nonzero"
        ):
            marker(store, config)


def test_status_rejects_marker_hash_mismatch(
    tmp_path: Path, config
) -> None:
    store, _collector, _source = gate_a_store(tmp_path, config)
    with store:
        frozen = marker(store, config)
        marker_path = tmp_path / "gate_b_marker.json"
        persist_marker(marker_path, frozen)
        with pytest.raises(ValueError, match="SHA-256 mismatch"):
            gate_b_status(
                store,
                marker_path,
                expected_marker_sha256="0" * 64,
            )


def test_status_rejects_ledger_and_configuration_identity_changes(
    tmp_path: Path, config
) -> None:
    store, _collector, _source = gate_a_store(tmp_path, config)
    with store:
        frozen = marker(store, config)
        wrong_inode = frozen.model_copy(
            update={"ledger_inode": frozen.ledger_inode + 1}
        )
        inode_path = tmp_path / "wrong_inode.json"
        inode_hash = persist_marker(inode_path, wrong_inode)
        with pytest.raises(ValueError, match="ledger inode"):
            gate_b_status(
                store,
                inode_path,
                expected_marker_sha256=inode_hash,
            )

        marker_path = tmp_path / "gate_b_marker.json"
        marker_hash = persist_marker(marker_path, frozen)
        with store.connection:
            store.set_metadata("configuration_hash", "changed")
        with pytest.raises(ValueError, match="collector configuration"):
            gate_b_status(
                store,
                marker_path,
                expected_marker_sha256=marker_hash,
            )


def test_status_rejects_changed_sample_identity(
    tmp_path: Path, config
) -> None:
    store, _collector, _source = gate_a_store(tmp_path, config)
    with store:
        frozen = marker(store, config)
        changed = frozen.model_copy(update={"sample_id": "changed"})
        marker_path = tmp_path / "changed_sample.json"
        marker_hash = persist_marker(marker_path, changed)
        with pytest.raises(ValueError, match="sample identity"):
            gate_b_status(
                store,
                marker_path,
                expected_marker_sha256=marker_hash,
            )


def test_status_rejects_changed_observer_source_identity(
    tmp_path: Path, config
) -> None:
    store, _collector, _source = gate_a_store(tmp_path, config)
    with store:
        frozen = marker(store, config)
        changed_cursor = frozen.source_cursors[0].model_copy(
            update={"source_inode": frozen.source_cursors[0].source_inode + 1}
        )
        changed = frozen.model_copy(
            update={
                "source_cursors": [
                    changed_cursor,
                    *frozen.source_cursors[1:],
                ]
            }
        )
        marker_path = tmp_path / "changed_source.json"
        marker_hash = persist_marker(marker_path, changed)
        with pytest.raises(ValueError, match="observer source inode"):
            gate_b_status(
                store,
                marker_path,
                expected_marker_sha256=marker_hash,
            )


def test_gate_b_contains_no_profitability_or_live_action_logic() -> None:
    source = Path("src/orev3/collection/gate_b.py").read_text(
        encoding="utf-8"
    ).lower()
    assert "profit" not in source
    assert "send_transaction" not in source
    assert "sign_transaction" not in source
    assert "claim_transaction" not in source
