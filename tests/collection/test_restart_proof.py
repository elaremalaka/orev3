from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orev3.collection.collector import PaperCollector
from orev3.collection.cursor_store import CollectionStore
from orev3.collection.metrics import evaluate_burn_in

from .conftest import snapshot


START = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def initialized(path: Path, config) -> CollectionStore:
    store = CollectionStore(path, busy_timeout_ms=config.busy_timeout_ms)
    store.initialize()
    return store


def write_snapshots(path: Path, indices: list[int]) -> None:
    path.write_text(
        "".join(
            json.dumps(snapshot(observed_index=index)) + "\n"
            for index in indices
        ),
        encoding="utf-8",
    )


def append_snapshots(path: Path, indices: list[int]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for index in indices:
            handle.write(json.dumps(snapshot(observed_index=index)) + "\n")


def begin(
    store: CollectionStore,
    config,
    *,
    run_id: str,
    minute: int,
    process_id: int,
) -> PaperCollector:
    collector = PaperCollector(
        store=store,
        config=config,
        mode="real_time_burn_in",
    )
    collector.begin_real_time_run(
        run_id=run_id,
        started_at=START + timedelta(minutes=minute),
        process_id=process_id,
        lease_exclusive=True,
    )
    return collector


def first_completed_run(
    store: CollectionStore,
    config,
    source: Path,
) -> PaperCollector:
    first = begin(
        store,
        config,
        run_id="run-one",
        minute=0,
        process_id=101,
    )
    first.process_file(source, max_records=10)
    first.finish_real_time_run(ended_at=START + timedelta(seconds=30))
    return first


def test_first_run_and_empty_restart_do_not_prove_resume(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first = first_completed_run(store, config, source)
        first_evidence = store.load_collector_run(first.run_id or "")
        assert first_evidence is not None
        assert first_evidence.failure_reason == "no_prior_run_exists"

        second = begin(
            store,
            config,
            run_id="run-two",
            minute=1,
            process_id=202,
        )
        evidence = store.load_collector_run(second.run_id or "")
        assert evidence is not None
        assert evidence.resumed_from_checkpoint
        assert evidence.validation_status == "pending"
        assert evidence.failure_reason == "no_post_resume_record_imported"


def test_prior_run_without_cursor_cannot_prove_resume(
    tmp_path: Path, config
) -> None:
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first = begin(
            store,
            config,
            run_id="empty-run",
            minute=0,
            process_id=101,
        )
        first.finish_real_time_run(ended_at=START + timedelta(seconds=30))
        second = begin(
            store,
            config,
            run_id="run-two",
            minute=1,
            process_id=202,
        )
        evidence = store.load_collector_run(second.run_id or "")
        assert evidence is not None
        assert evidence.failure_reason == "prior_run_had_no_durable_cursor"


@pytest.mark.parametrize("new_indices", [[1], [1, 2, 3]])
def test_restart_with_new_records_proves_and_survives_reopen(
    tmp_path: Path, config, new_indices: list[int]
) -> None:
    source = tmp_path / "observer.jsonl"
    ledger = tmp_path / "ledger.sqlite"
    write_snapshots(source, [0])
    with initialized(ledger, config) as store:
        first_completed_run(store, config, source)
    append_snapshots(source, new_indices)
    with initialized(ledger, config) as store:
        second = begin(
            store,
            config,
            run_id="run-two",
            minute=1,
            process_id=202,
        )
        second.process_file(source, max_records=10)
        evidence = store.load_collector_run(second.run_id or "")
        assert evidence is not None
        assert evidence.validation_status == "proven"
        assert evidence.failure_reason is None
        assert evidence.first_post_resume_line_number == 2
        assert evidence.latest_source_records == 1 + len(new_indices)
    with CollectionStore(ledger, read_only=True) as reopened:
        persisted = reopened.latest_collector_run(include_legacy=False)
        assert persisted is not None
        assert persisted.validation_status == "proven"


def test_new_process_and_crash_like_prior_run_can_prove_resume(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    ledger = tmp_path / "ledger.sqlite"
    write_snapshots(source, [0])
    with initialized(ledger, config) as store:
        first = begin(
            store,
            config,
            run_id="crashed-run",
            minute=0,
            process_id=101,
        )
        first.process_file(source, max_records=10)
        assert store.load_collector_run("crashed-run").ended_at is None
    append_snapshots(source, [1])
    with initialized(ledger, config) as store:
        resumed = begin(
            store,
            config,
            run_id="new-process-run",
            minute=1,
            process_id=999,
        )
        before = store.load_collector_run("new-process-run")
        assert before is not None
        assert before.failure_reason == "no_post_resume_record_imported"
        resumed.process_file(source, max_records=10)
        after = store.load_collector_run("new-process-run")
        assert after is not None
        assert after.validation_status == "proven"
        assert after.process_id == 999


def test_cursor_regression_prevents_proof(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first_completed_run(store, config, source)
        second = begin(
            store,
            config,
            run_id="run-two",
            minute=1,
            process_id=202,
        )
        cursor = store.load_cursor(source)
        assert cursor is not None
        with store.connection:
            store.save_cursor(
                cursor.model_copy(
                    update={
                        "byte_offset": cursor.byte_offset - 1,
                        "line_number": cursor.line_number - 1,
                    }
                )
            )
            evidence = second.refresh_run_evidence()
        assert evidence is not None
        assert evidence.validation_status == "failed"
        assert evidence.failure_reason == "cursor_regression_detected"


def test_skipped_first_post_resume_record_prevents_proof(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first_completed_run(store, config, source)
        append_snapshots(source, [1])
        second = begin(
            store,
            config,
            run_id="run-two",
            minute=1,
            process_id=202,
        )
        second.process_file(source, max_records=10)
        evidence = store.load_collector_run(second.run_id or "")
        assert evidence is not None
        with store.connection:
            store.save_collector_run(
                evidence.model_copy(
                    update={
                        "first_post_resume_line_number": (
                            evidence.first_post_resume_line_number + 1
                        )
                    }
                )
            )
            failed = second.refresh_run_evidence()
        assert failed is not None
        assert failed.validation_status == "failed"
        assert failed.failure_reason == "skipped_record_detected"


@pytest.mark.parametrize(
    ("counter", "reason"),
    [
        ("source_records_duplicate", "duplicate_source_records_detected"),
        ("duplicate_opportunities", "duplicate_opportunities_detected"),
        ("duplicate_decisions", "duplicate_decisions_detected"),
    ],
)
def test_duplicate_attempts_prevent_proof(
    tmp_path: Path, config, counter: str, reason: str
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first_completed_run(store, config, source)
        append_snapshots(source, [1])
        second = begin(
            store,
            config,
            run_id="run-two",
            minute=1,
            process_id=202,
        )
        second.process_file(source, max_records=10)
        with store.connection:
            store.increment(counter)
            evidence = second.refresh_run_evidence()
        assert evidence is not None
        assert evidence.validation_status == "failed"
        assert evidence.failure_reason == reason


def test_reused_run_identity_is_rejected(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first_completed_run(store, config, source)
        with pytest.raises(ValueError, match="identity was reused"):
            begin(
                store,
                config,
                run_id="run-one",
                minute=1,
                process_id=202,
            )


def test_configuration_change_prevents_resume_proof(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first_completed_run(store, config, source)
        changed = config.model_copy(update={"strategy_version": "changed"})
        second = begin(
            store,
            changed,
            run_id="changed-config-run",
            minute=1,
            process_id=202,
        )
        evidence = store.load_collector_run(second.run_id or "")
        assert evidence is not None
        assert (
            evidence.failure_reason
            == "configuration_changed_since_prior_run"
        )


def test_graceful_shutdown_persists_end_and_final_cursor(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        collector = begin(
            store,
            config,
            run_id="graceful-run",
            minute=0,
            process_id=101,
        )
        collector.process_file(source, max_records=10)
        ended = START + timedelta(minutes=1)
        result = collector.finish_real_time_run(ended_at=ended)
        assert result is not None
        assert result.ended_at == ended
        assert result.latest_cursors == store.cursor_checkpoints()


def test_existing_v1_ledger_migrates_without_record_loss(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    ledger = tmp_path / "ledger.sqlite"
    write_snapshots(source, [0])
    with initialized(ledger, config) as store:
        PaperCollector(
            store=store,
            config=config,
            mode="historical_replay_burn_in",
        ).process_file(source, max_records=10)
        with store.connection:
            store.connection.execute("DROP TABLE collector_runs")
            store.connection.execute(
                "DELETE FROM collection_metadata "
                "WHERE key='collection_schema_version'"
            )
        before = store.rows_by_table()
    with initialized(ledger, config) as migrated:
        assert migrated.metadata()["collection_schema_version"] == "2"
        assert migrated.ledger.count("opportunities") == 1
        assert migrated.connection.execute(
            "SELECT count(*) FROM collector_runs"
        ).fetchone()[0] == 0
        after = migrated.rows_by_table()
        assert after["opportunities"] == before["opportunities"]
        current = begin(
            migrated,
            config,
            run_id="first-instrumented-run",
            minute=1,
            process_id=202,
        )
        evidence = migrated.load_collector_run(current.run_id or "")
        assert evidence is not None
        assert evidence.prior_run_id is not None
        assert evidence.failure_reason == "no_post_resume_record_imported"
        append_snapshots(source, [1])
        current.process_file(source, max_records=10)
        proven = migrated.load_collector_run(current.run_id or "")
        assert proven is not None
        assert proven.validation_status == "proven"


def test_future_collection_schema_is_rejected(
    tmp_path: Path, config
) -> None:
    ledger = tmp_path / "ledger.sqlite"
    with initialized(ledger, config) as store:
        with store.connection:
            store.set_metadata("collection_schema_version", "999")
    with pytest.raises(
        ValueError, match="Unsupported collection schema version"
    ):
        initialized(ledger, config)


def test_gate_a_uses_persisted_real_time_proof(
    tmp_path: Path, config
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, list(range(100)))
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first = begin(
            store,
            config,
            run_id="run-one",
            minute=0,
            process_id=101,
        )
        first.process_file(source, max_records=100)
        first.finish_real_time_run(ended_at=START + timedelta(minutes=1))
        append_snapshots(source, [100])
        second = begin(
            store,
            config,
            run_id="run-two",
            minute=2,
            process_id=202,
        )
        second.process_file(source, max_records=10)
        result = evaluate_burn_in(store, mode="real_time_burn_in")
        assert result.passed
        assert result.restart_resume_proven
        assert result.restart_resume_status == "proven"
        assert result.restart_resume_failure_reason is None
        assert result.restart_resume_run_id == "run-two"


@pytest.mark.parametrize(
    ("lease_exclusive", "add_live_action", "reason"),
    [
        (False, False, "writer_lease_not_exclusive"),
        (True, True, "live_action_detected"),
    ],
)
def test_nonexclusive_lease_and_live_action_prevent_proof(
    tmp_path: Path,
    config,
    lease_exclusive: bool,
    add_live_action: bool,
    reason: str,
) -> None:
    source = tmp_path / "observer.jsonl"
    write_snapshots(source, [0])
    with initialized(tmp_path / "ledger.sqlite", config) as store:
        first_completed_run(store, config, source)
        append_snapshots(source, [1])
        collector = PaperCollector(
            store=store,
            config=config,
            mode="real_time_burn_in",
        )
        evidence = collector.begin_real_time_run(
            run_id="unsafe-run",
            started_at=START + timedelta(minutes=1),
            process_id=202,
            lease_exclusive=lease_exclusive,
        )
        if add_live_action:
            with store.connection:
                store.increment("live_actions")
                evidence = collector.refresh_run_evidence()
        assert evidence is not None
        assert evidence.failure_reason == reason
