from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.decisions import build_decisions, snapshot_from_opportunity
from orev3.rfc008.outcomes import (
    accept_outcome,
    begin_resolution,
    enqueue_pending,
    mark_attempt,
    quarantine_expired,
)
from orev3.rfc008.storage import RFC008Store, assert_safe_new_ledger_path

from .conftest import make_opportunity, make_outcome


def populate_round(
    store: RFC008Store,
    config: RFC008Config,
    round_id: int,
    *,
    provenance: str = "direct_observed",
    winner: int = 0,
) -> None:
    at = datetime(2026, 7, 25, tzinfo=timezone.utc)
    store.start_round(round_id, at)
    snapshot = snapshot_from_opportunity(
        make_opportunity(round_id),
        config,
        source_content_sha256=f"{round_id:064x}"[-64:],
    )
    assert store.insert_snapshot_and_decisions(
        snapshot, build_decisions(snapshot, config)
    )
    enqueue_pending(store, round_id, at=at)
    result = accept_outcome(
        store,
        make_outcome(round_id, winner=winner, provenance=provenance),
        config,
        at=at + timedelta(minutes=1),
    )
    assert result == "accepted"


def test_new_schema_is_isolated_and_identity_checked(
    tmp_path: Path, config: RFC008Config
) -> None:
    with pytest.raises(ValueError, match="RFC-007"):
        assert_safe_new_ledger_path(tmp_path / "rfc007_live_ledger_v1.sqlite")
    path = tmp_path / "new.sqlite"
    with RFC008Store(path, config=config, create=True) as store:
        assert store.integrity() == "ok"
        assert store.metadata("schema_version") == "6"
    with pytest.raises(FileExistsError):
        RFC008Store(path, config=config, create=True)
    raw = config.model_dump(mode="json")
    raw["poll_interval_seconds"] = 2
    changed = RFC008Config.model_validate(raw)
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        RFC008Store(path, config=changed)


def test_pending_queue_survives_restart_and_backoff_is_bounded(
    store, config: RFC008Config
) -> None:
    first, path = store
    now = datetime(2026, 7, 25, tzinfo=timezone.utc)
    first.start_round(346000, now)
    enqueue_pending(first, 346000, at=now)
    assert begin_resolution(first, 346000, at=now).state == "resolving"
    updated = mark_attempt(
        first,
        346000,
        source_type="direct_finalized_adapter",
        status="unavailable",
        error="not_finalized",
        at=now,
    )
    assert updated.retry_count == 1
    first.connection.commit()
    with RFC008Store(path, config=config) as reopened:
        pending = reopened.unresolved_queue()
        assert [item.round_id for item in pending] == [346000]
        assert pending[0].last_error == "not_finalized"


def test_direct_and_recovered_provenance_are_separate(store, config) -> None:
    value, _ = store
    populate_round(value, config, 346001)
    assert value.count(
        "experiment_rounds", "state='finalized_primary'"
    ) == 1
    populate_round(value, config, 346002, provenance="recovered")
    assert value.count(
        "experiment_rounds", "state='finalized_sensitivity'"
    ) == 1
    assert value.count("round_accounting") == 10


def test_accounting_fees_no_deploy_and_unavailable_base_ore(store, config) -> None:
    value, _ = store
    populate_round(value, config, 346003, winner=0)
    rows = value.connection.execute(
        "SELECT arm_id,record_json FROM round_accounting WHERE round_id=346003"
    ).fetchall()
    by_arm = {row[0]: row[1] for row in rows}
    import json

    candidate = json.loads(by_arm["highest_reward_top4_v1"])
    control = json.loads(by_arm["no_deploy_v1"])
    assert candidate["assumed_deploy_fee_lamports"] == 5000
    assert candidate["assumed_claim_fee_lamports"] == 5000
    assert candidate["base_ore_raw"] is None
    assert control["deployed_lamports"] == 0
    assert control["net_sol_after_fees_lamports"] == 0
    assert control["roi_after_fees"] is None


def test_duplicate_and_conflicting_outcomes_fail_closed(store, config) -> None:
    value, _ = store
    populate_round(value, config, 346004, winner=0)
    same = make_outcome(346004, winner=0, suffix="duplicate")
    assert accept_outcome(value, same, config) == "duplicate"
    conflict = make_outcome(346004, winner=1, suffix="conflict")
    assert accept_outcome(value, conflict, config) == "conflict"
    assert value.queue(346004).state == "conflicted"
    assert value.count("outcome_conflicts") == 1
    assert value.count("experiment_rounds", "state='conflicted'") == 1


def test_quarantine_keeps_missing_outcome_explicit(store) -> None:
    value, _ = store
    at = datetime(2026, 7, 24, tzinfo=timezone.utc)
    value.start_round(346005, at)
    enqueue_pending(value, 346005, at=at)
    assert quarantine_expired(
        value, now=at + timedelta(hours=24, seconds=1)
    ) == 1
    assert value.queue(346005).state == "quarantined"
