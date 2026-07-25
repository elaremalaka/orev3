from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Any

from orev3.collection.cursor_store import CollectionStore
from orev3.collection.health import (
    deterministic_health,
    disk_forecast,
    health_snapshot,
)
from orev3.collection.metrics import evaluate_burn_in
from orev3.ledger.reporting import strict_json_text, write_strict_json


COLLECTION_EXPORTS = {
    "paper_decisions": ("opportunity_id", "rfc007_paper_decisions_v1.csv"),
    "final_outcomes": ("round_id, version", "rfc007_paper_outcomes_v1.csv"),
    "paper_accounting": ("opportunity_id", "rfc007_paper_economics_v1.csv"),
    "paper_reconciliation": ("opportunity_id", "rfc007_reconciliation_v1.csv"),
}


def collection_report(
    store: CollectionStore,
    *,
    mode: str,
) -> dict[str, Any]:
    health = health_snapshot(store, mode=mode)
    evaluation = evaluate_burn_in(store, mode=mode)
    return {
        "schema_version": 1,
        "mode": mode,
        "configuration_hash": store.metadata().get("configuration_hash"),
        "collector_version": store.metadata().get("collector_version"),
        "rows_by_table": store.rows_by_table(),
        "health": deterministic_health(health),
        "burn_in": evaluation.model_dump(mode="json"),
        "disk_forecast": disk_forecast(store),
        "database_integrity": store.integrity_check(),
        "paper_economics_classification": (
            "reconstructed_paper_not_wallet_realized"
        ),
        "model_strategy": {
            "available": False,
            "reason": (
                "missing serialized RFC-004 inference pipeline and complete "
                "live-compatible ranking vectors"
            ),
        },
    }


def _write_csv(path: Path, records: list[dict], *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {path}; use --force")
    columns = sorted({key for record in records for key in record})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: (
                        json.dumps(
                            record.get(key),
                            allow_nan=False,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                        if isinstance(record.get(key), (dict, list))
                        else record.get(key)
                    )
                    for key in columns
                }
            )


def export_collection(
    store: CollectionStore,
    output_dir: str | Path,
    *,
    mode: str,
    force: bool = False,
) -> list[Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    all_records: list[dict[str, Any]] = []
    opportunities = store.ledger.records("opportunities")
    opportunity_path = directory / "rfc007_opportunities_v1.csv"
    _write_csv(opportunity_path, opportunities, force=force)
    outputs.append(opportunity_path)
    all_records.extend(
        {"table": "opportunities", "record": item} for item in opportunities
    )
    for table, (order, filename) in COLLECTION_EXPORTS.items():
        records = store.json_records(table, order)
        path = directory / filename
        _write_csv(path, records, force=force)
        outputs.append(path)
        all_records.extend(
            {"table": table, "record": item} for item in records
        )
    report_path = directory / "rfc007_burn_in_report_v1.json"
    write_strict_json(
        report_path, collection_report(store, mode=mode), force=force
    )
    outputs.append(report_path)
    health_path = directory / "rfc007_health_v1.json"
    write_strict_json(
        health_path,
        deterministic_health(health_snapshot(store, mode=mode)),
        force=force,
    )
    outputs.append(health_path)
    forecast_path = directory / "rfc007_disk_forecast_v1.json"
    write_strict_json(
        forecast_path, disk_forecast(store), force=force
    )
    outputs.append(forecast_path)
    cursor_path = directory / "rfc007_cursor_state_v1.json"
    cursor_rows = [
        json.loads(row[0])
        for row in store.connection.execute(
            "SELECT record_json FROM source_cursors ORDER BY source_id"
        )
    ]
    for row in cursor_rows:
        row["last_ingested_at"] = None
    write_strict_json(cursor_path, cursor_rows, force=force)
    outputs.append(cursor_path)
    compressed = directory / "rfc007_deterministic_export_v1.jsonl.gz"
    if compressed.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {compressed}; use --force"
        )
    all_records.sort(
        key=lambda item: (
            item["table"],
            json.dumps(item["record"], sort_keys=True),
        )
    )
    with compressed.open("wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0
        ) as handle:
            for item in all_records:
                handle.write(
                    (
                        json.dumps(
                            item,
                            allow_nan=False,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                        + "\n"
                    ).encode("utf-8")
                )
    outputs.append(compressed)
    return outputs
