from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from orev3.ledger.identifiers import (
    canonical_json,
    deterministic_id,
    source_record_id,
)
from orev3.ledger.observation_capture import capture_observation
from orev3.ledger.storage import LedgerStore


def source_files(source: str | Path) -> list[Path]:
    path = Path(source)
    if path.is_dir():
        return sorted(path.glob("*.jsonl"))
    return [path]


def _read_records(paths: list[Path]) -> tuple[list[tuple], Counter]:
    records: list[tuple] = []
    counts: Counter = Counter()
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                counts["total_source_records"] += 1
                try:
                    raw = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    counts["malformed_records"] += 1
                    continue
                if not isinstance(raw, dict):
                    counts["malformed_records"] += 1
                    continue
                if not {"board", "round", "observed_at_utc", "rpc_slot"} <= raw.keys():
                    counts["partial_records"] += 1
                    continue
                if int(raw.get("schema_version", 1)) not in {1, 2}:
                    counts["failed_records"] += 1
                    continue
                records.append(
                    (
                        int(raw["board"]["round_id"]),
                        str(raw["observed_at_utc"]),
                        str(path),
                        line_number,
                        raw,
                    )
                )
    records.sort(key=lambda item: item[:4])
    return records, counts


def import_history(
    source: str | Path,
    store: LedgerStore | None,
    *,
    dry_run: bool = False,
    run_id: str | None = None,
    session_id: str = "historical-import-v1",
) -> dict[str, Any]:
    paths = source_files(source)
    records, counts = _read_records(paths)
    observation_indices: defaultdict[int, int] = defaultdict(int)
    seen_batch: set[str] = set()
    run = run_id or deterministic_id(
        "historical-import-run", *[str(path) for path in paths]
    )
    first = None
    last = None
    sources = Counter()
    rounds: set[int] = set()

    for round_id, timestamp, source_name, line_number, raw in records:
        sid = source_record_id(source_name, line_number, raw)
        if sid in seen_batch:
            counts["duplicate_records"] += 1
            continue
        seen_batch.add(sid)
        index = observation_indices[round_id]
        observation_indices[round_id] += 1
        rounds.add(round_id)
        sources[source_name] += 1
        first = min(first, timestamp) if first else timestamp
        last = max(last, timestamp) if last else timestamp
        opportunity, event = capture_observation(
            raw,
            observation_index=index,
            source=source_name,
            source_record_id=sid,
            run_id=run,
            session_id=session_id,
        )
        if dry_run:
            counts["imported_records"] += 1
            continue
        if store is None:
            raise ValueError("Non-dry-run import requires a ledger store")
        digest = hashlib.sha256(canonical_json(raw).encode()).hexdigest()
        with store.connection:
            inserted_source = store.insert_source_record(
                sid, source_name, line_number, digest
            )
            if not inserted_source:
                counts["duplicate_records"] += 1
                continue
            store.upsert_record("opportunities", opportunity)
            store.insert_event(event)
        counts["imported_records"] += 1

    return {
        "schema_version": 1,
        **{
            key: int(counts[key])
            for key in (
                "total_source_records",
                "imported_records",
                "duplicate_records",
                "partial_records",
                "malformed_records",
                "failed_records",
            )
        },
        "unique_opportunities": len(rounds) and sum(observation_indices.values()),
        "unique_rounds": len(rounds),
        "earliest_timestamp": first,
        "latest_timestamp": last,
        "coverage_by_source": dict(sorted(sources.items())),
        "dry_run": dry_run,
    }
