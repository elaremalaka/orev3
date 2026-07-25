from __future__ import annotations

import os
import resource
from datetime import datetime, timezone

from orev3.collection.cursor_store import CollectionStore
from orev3.collection.schemas import HealthSnapshot


def database_size(path) -> int:
    return sum(
        candidate.stat().st_size
        for candidate in (
            path,
            path.with_name(path.name + "-wal"),
            path.with_name(path.name + "-shm"),
        )
        if candidate.exists()
    )


def health_snapshot(
    store: CollectionStore,
    *,
    mode: str,
    uptime_seconds: float = 0,
    processing_latency_ms: float = 0,
) -> HealthSnapshot:
    counters = store.counters()
    reconciliations = store.json_records(
        "paper_reconciliation", "opportunity_id"
    )
    linked_reconciliations = sum(
        item["outcome_linked"] for item in reconciliations
    )
    cursors = store.connection.execute(
        "SELECT record_json FROM source_cursors ORDER BY source_id"
    ).fetchall()
    last_ingestion = None
    last_observed = None
    for row in cursors:
        import json

        value = json.loads(row[0])
        if value.get("last_ingested_at"):
            last_ingestion = max(
                last_ingestion, value["last_ingested_at"]
            ) if last_ingestion else value["last_ingested_at"]
        if value.get("last_observed_timestamp"):
            last_observed = max(
                last_observed, value["last_observed_timestamp"]
            ) if last_observed else value["last_observed_timestamp"]
    lag = None
    if mode == "real_time_burn_in" and last_observed:
        observed = datetime.fromisoformat(last_observed.replace("Z", "+00:00"))
        lag = max((datetime.now(timezone.utc) - observed).total_seconds(), 0)
    memory = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return HealthSnapshot(
        mode=mode,
        collector_uptime_seconds=uptime_seconds,
        source_records_seen=counters.get("source_records_seen", 0),
        source_records_imported=counters.get("source_records_imported", 0),
        source_records_duplicate=counters.get("source_records_duplicate", 0),
        source_records_malformed=counters.get("source_records_malformed", 0),
        cursor_lag_records=0,
        cursor_lag_seconds=lag,
        opportunities_started=counters.get("opportunities_started", 0),
        opportunities_completed=counters.get("opportunities_completed", 0),
        opportunities_expired=counters.get("opportunities_expired", 0),
        paper_decisions_created=counters.get("paper_decisions_created", 0),
        paper_decisions_skipped=counters.get("paper_decisions_skipped", 0),
        outcomes_linked=linked_reconciliations,
        outcomes_missing=len(reconciliations) - linked_reconciliations,
        reconciliations_complete=sum(
            item["state"] == "complete_paper_reconstructed"
            for item in reconciliations
        ),
        reconciliations_partial=sum(
            item["state"] != "complete_paper_reconstructed"
            for item in reconciliations
        ),
        database_size_bytes=database_size(store.path),
        memory_usage_bytes=memory,
        processing_latency_ms=processing_latency_ms,
        last_successful_ingestion=last_ingestion,
        last_successful_decision=(
            last_ingestion
            if counters.get("paper_decisions_created", 0)
            else None
        ),
        last_successful_outcome_link=(
            last_ingestion if counters.get("outcomes_linked", 0) else None
        ),
    )


def disk_forecast(store: CollectionStore) -> dict[str, object]:
    opportunities = store.ledger.count("opportunities")
    size = database_size(store.path)
    per = size / opportunities if opportunities else None
    return {
        "schema_version": 1,
        "database_size_bytes": size,
        "opportunities": opportunities,
        "bytes_per_opportunity": per,
        "estimated_bytes": {
            str(target): int(per * target) if per is not None else None
            for target in (1000, 10000, 100000)
        },
        "retention": "no automatic deletion; verbose payload retention configurable",
        "compaction": "manual archive then VACUUM only while collector is stopped",
    }


def deterministic_health(snapshot: HealthSnapshot) -> dict[str, object]:
    value = snapshot.model_dump(mode="json")
    for key, replacement in {
        "collector_uptime_seconds": 0.0,
        "memory_usage_bytes": None,
        "processing_latency_ms": 0.0,
        "cursor_lag_seconds": None,
        "last_successful_ingestion": None,
        "last_successful_decision": None,
        "last_successful_outcome_link": None,
    }.items():
        value[key] = replacement
    return value
