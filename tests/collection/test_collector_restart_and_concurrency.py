from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from orev3.collection.collector import PaperCollector
from orev3.collection.cursor_store import CollectionStore
from orev3.collection.writer_lock import (
    DuplicateCollectorError,
    WriterLease,
)

from .conftest import lifecycle, snapshot


def initialized(path: Path, config) -> CollectionStore:
    store = CollectionStore(
        path, busy_timeout_ms=config.busy_timeout_ms
    )
    store.initialize()
    return store


def test_restart_resume_is_idempotent(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    source.write_text(
        "\n".join(
            json.dumps(snapshot(observed_index=index))
            for index in range(4)
        )
        + "\n"
    )
    ledger = tmp_path / "ledger.sqlite"
    with initialized(ledger, config) as store:
        collector = PaperCollector(
            store=store,
            config=config,
            mode="historical_replay_burn_in",
        )
        assert collector.replay(source, max_opportunities=2) == 2
        cursor = store.load_cursor(source)
        assert cursor is not None and cursor.line_number == 2
    with initialized(ledger, config) as store:
        collector = PaperCollector(
            store=store,
            config=config,
            mode="historical_replay_burn_in",
        )
        assert collector.replay(source, max_opportunities=4) == 4
        assert store.ledger.count("decisions") == 4
        assert store.counters().get("duplicate_decisions", 0) == 0
        cursor = store.load_cursor(source)
        assert cursor is not None and cursor.line_number == 4
        collector.request_stop()
        assert collector.stop_requested.is_set()


def test_duplicate_writer_fails_safely(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.sqlite"
    with WriterLease(ledger):
        with pytest.raises(DuplicateCollectorError):
            with WriterLease(ledger):
                pass


def test_wal_and_transient_lock_recovery(tmp_path: Path, config) -> None:
    ledger = tmp_path / "ledger.sqlite"
    with initialized(ledger, config) as store:
        assert store.connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        locker = sqlite3.connect(ledger, check_same_thread=False)
        locker.execute("PRAGMA busy_timeout=1000")
        locker.execute("BEGIN IMMEDIATE")

        def release() -> None:
            time.sleep(0.05)
            locker.rollback()
            locker.close()

        thread = threading.Thread(target=release)
        thread.start()
        store.increment("lock_recovered")
        store.connection.commit()
        thread.join()
        assert store.counters()["lock_recovered"] == 1


def test_interrupted_batch_rolls_back_and_integrity_survives(
    tmp_path: Path, config
) -> None:
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        with pytest.raises(RuntimeError):
            with store.connection:
                store.increment("should_rollback")
                raise RuntimeError("simulated interruption")
        assert "should_rollback" not in store.counters()
        assert store.integrity_check() == "ok"


def test_repeated_replay_has_identical_contents(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    source.write_text(
        "\n".join(
            json.dumps(snapshot(observed_index=index))
            for index in range(3)
        )
        + "\n"
    )
    contents = []
    for name in ("first.sqlite", "second.sqlite"):
        with initialized(tmp_path / name, config) as store:
            PaperCollector(
                store=store,
                config=config,
                mode="historical_replay_burn_in",
            ).replay(source, max_opportunities=3)
            contents.append(
                {
                    "opportunities": store.ledger.records("opportunities"),
                    "decisions": store.json_records(
                        "paper_decisions", "opportunity_id"
                    ),
                    "accounting": store.json_records(
                        "paper_accounting", "opportunity_id"
                    ),
                    "cursors": [
                        json.loads(row[0])
                        for row in store.connection.execute(
                            "SELECT record_json FROM source_cursors ORDER BY source_id"
                        )
                    ],
                }
            )
    assert contents[0] == contents[1]


def test_late_observer_outcome_completes_prior_paper_decision(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    active = snapshot()
    finalized = snapshot(observed_index=1)
    finalized["round"].update(
        {
            "entropy": 0,
            "slot_hash_hex": "01" + ("00" * 31),
            "deployed_lamports": [100_000] * 25,
            "total_vaulted": 1_000_000,
            "total_winnings": 2_000_000,
        }
    )
    source.write_text(
        json.dumps(active) + "\n" + json.dumps(finalized) + "\n"
    )
    empty_outcomes = tmp_path / "empty_outcomes.jsonl"
    empty_outcomes.write_text("")
    configured = config.model_copy(
        update={"outcome_source": str(empty_outcomes)}
    )
    with initialized(tmp_path / "ledger.sqlite", configured) as store:
        collector = PaperCollector(
            store=store,
            config=configured,
            mode="real_time_burn_in",
        )
        assert collector.replay(source, max_opportunities=1) == 1
        before = store.json_records(
            "paper_reconciliation", "opportunity_id"
        )[0]
        assert before["state"] == "partial_missing_outcome"
        result = collector.process_file(source, max_records=10)
        assert result["opportunities_imported"] == 0
        assert store.ledger.count("opportunities") == 1
        assert store.ledger.count("decisions") == 1
        assert len(
            store.json_records("paper_accounting", "opportunity_id")
        ) == 1
        after = store.json_records(
            "paper_reconciliation", "opportunity_id"
        )[0]
        assert after["state"] == "complete_paper_reconstructed"
        assert store.counters()["source_records_imported"] == 2
