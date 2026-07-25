from __future__ import annotations

import hashlib
from datetime import timedelta
from pathlib import Path

import pytest

from orev3.ledger.decision_capture import (
    capture_paper_decision,
    capture_passive_decision,
)
from orev3.ledger.historical_import import import_history
from orev3.ledger.identifiers import source_record_id
from orev3.ledger.observation_capture import capture_observation
from orev3.ledger.storage import LedgerStore

from .conftest import NOW


def test_passive_and_paper_capture(snapshot: dict) -> None:
    sid = source_record_id("fixture", 1, snapshot)
    opportunity, event = capture_observation(
        snapshot,
        observation_index=0,
        source="fixture",
        source_record_id=sid,
        run_id="run",
        session_id="session",
    )
    passive = capture_passive_decision(
        opportunity_id=opportunity.opportunity_id,
        decision_time=NOW,
    )
    paper = capture_paper_decision(
        opportunity_id=opportunity.opportunity_id,
        strategy_id="fixture",
        strategy_version="1",
        selected_squares=[1, 2, 3],
        ranking_scores=[float(index) for index in range(25)],
        deployment_total_lamports=10,
        decision_time=NOW,
        decision_latency_ms=2.5,
    )
    assert event.payload["capture_mode"] == "passive"
    assert not passive.participated
    assert paper.participated
    assert sum(paper.allocation_by_square.values()) == 10
    assert paper.allocation_by_square == {1: 4, 2: 3, 3: 3}


def test_no_deploy_and_invalid_decision() -> None:
    no_deploy = capture_paper_decision(
        opportunity_id="opportunity",
        strategy_id="fixture",
        strategy_version="1",
        selected_squares=[1],
        ranking_scores=None,
        deployment_total_lamports=10,
        decision_time=NOW,
        decision_latency_ms=0,
        participate=False,
    )
    assert no_deploy.deployment_total_lamports == 0
    with pytest.raises(ValueError, match="25"):
        capture_paper_decision(
            opportunity_id="opportunity",
            strategy_id="fixture",
            strategy_version="1",
            selected_squares=[1],
            ranking_scores=[1.0],
            deployment_total_lamports=1,
            decision_time=NOW,
            decision_latency_ms=0,
        )


def test_import_is_idempotent_and_source_unchanged(
    tmp_path: Path, snapshot_file: Path
) -> None:
    before = hashlib.sha256(snapshot_file.read_bytes()).hexdigest()
    ledger = tmp_path / "ledger.sqlite"
    with LedgerStore(ledger) as store:
        store.initialize()
        first = import_history(snapshot_file, store)
        second = import_history(snapshot_file, store)
        assert store.count("opportunities") == 1
        assert store.count("events") == 1
    assert first["imported_records"] == 1
    assert second["duplicate_records"] == 1
    assert hashlib.sha256(snapshot_file.read_bytes()).hexdigest() == before


def test_dry_run_does_not_create_ledger(
    tmp_path: Path, snapshot_file: Path
) -> None:
    ledger = tmp_path / "ledger.sqlite"
    result = import_history(snapshot_file, None, dry_run=True)
    assert result["imported_records"] == 1
    assert not ledger.exists()


def test_malformed_partial_and_unknown_schema_counts(
    tmp_path: Path, snapshot: dict
) -> None:
    path = tmp_path / "mixed.jsonl"
    unknown = {**snapshot, "schema_version": 999}
    path.write_text(
        "{bad json}\n"
        + '{"event":"session_start"}\n'
        + __import__("json").dumps(unknown)
        + "\n",
        encoding="utf-8",
    )
    result = import_history(path, None, dry_run=True)
    assert result["malformed_records"] == 1
    assert result["partial_records"] == 1
    assert result["failed_records"] == 1
