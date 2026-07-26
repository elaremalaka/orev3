from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.marker import verify_marker
from orev3.rfc008.storage import RFC008Store
from orev3.rfc008.storage import SCHEMA_VERSION


def status_report(
    *,
    ledger_path: str | Path,
    config_path: str | Path,
    marker_path: str | Path,
    expected_marker_sha256: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    config = RFC008Config.from_path(config_path)
    marker = verify_marker(
        marker_path, config, expected_sha256=expected_marker_sha256
    )
    with RFC008Store(ledger_path, config=config, read_only=True) as store:
        started = store.count("experiment_rounds")
        primary = store.count(
            "experiment_rounds", "state='finalized_primary'"
        )
        sensitivity = store.count(
            "experiment_rounds", "state='finalized_sensitivity'"
        )
        excluded = store.count("experiment_rounds", "state='excluded'")
        pending = store.count(
            "outcome_queue", "state IN ('pending','resolving')"
        )
        conflicted = store.count("outcome_queue", "state='conflicted'")
        quarantined = store.count("outcome_queue", "state='quarantined'")
        failed = store.count("outcome_queue", "state='failed'")
        unusable = excluded + conflicted + quarantined + failed + sensitivity
        unusable_rate = unusable / started if started else 0.0
        counters = store.counters()
        integrity = store.integrity()
        elapsed_days = (
            (now or datetime.now(timezone.utc)) - marker.created_at
        ).total_seconds() / 86400
        cap_reached = (
            started >= config.criteria.maximum_started_rounds
            or elapsed_days >= config.criteria.maximum_calendar_days
        )
        safety_failures = {
            "database_lock_failures": counters.get("database_lock_failures", 0),
            "skipped_records": counters.get("skipped_records", 0),
            "live_actions": counters.get("live_actions", 0),
            "source_corruption": counters.get("source_corruption", 0),
        }
        no_safety_failure = not any(safety_failures.values())
        ready = (
            integrity == "ok"
            and no_safety_failure
            and unusable_rate <= config.criteria.maximum_unusable_rate
            and not cap_reached
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": config.experiment_id,
            "configuration_fingerprint": config.configuration_fingerprint,
            "marker_verified": True,
            "marker_sha256_verified": expected_marker_sha256 is not None,
            "sqlite_integrity": integrity,
            "started_rounds": started,
            "primary_analyzable_rounds": primary,
            "sensitivity_rounds": sensitivity,
            "excluded_rounds": excluded,
            "pending_outcomes": pending,
            "conflicted_outcomes": conflicted,
            "quarantined_outcomes": quarantined,
            "failed_outcomes": failed,
            "unusable_rounds": unusable,
            "unusable_rate": unusable_rate,
            "duplicate_source_records": counters.get(
                "duplicate_source_records", 0
            ),
            "duplicate_decisions": counters.get("duplicate_decisions", 0),
            "safety": safety_failures,
            "minimum_target_reached": primary
            >= config.criteria.minimum_analyzable_rounds,
            "started_round_cap_reached": started
            >= config.criteria.maximum_started_rounds,
            "calendar_cap_reached": elapsed_days
            >= config.criteria.maximum_calendar_days,
            "collection_complete": primary
            >= config.criteria.minimum_analyzable_rounds,
            "collection_ready": ready,
            "collection_authorized": False,
            "paper_only": True,
        }
