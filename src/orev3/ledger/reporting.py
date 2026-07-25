from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from orev3.ledger.completeness import completeness_report
from orev3.ledger.storage import LedgerStore, RECORD_TABLES


EXPORT_NAMES = {
    "opportunities": "participant_opportunities_v1.csv",
    "decisions": "participant_decisions_v1.csv",
    "transactions": "participant_transactions_v1.csv",
    "rewards": "participant_rewards_v1.csv",
    "claims": "participant_claims_v1.csv",
    "reconciliation": "participant_reconciliation_v1.csv",
}


def strict_json_text(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_strict_json(path: Path, value: Any, *, force: bool = False) -> Path:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {path}; use --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(strict_json_text(value), encoding="utf-8")
    return path


def ledger_report(store: LedgerStore) -> dict[str, Any]:
    events = store.connection.execute(
        "SELECT source, event_type, record_json FROM events ORDER BY event_id"
    ).fetchall()
    source_counts = Counter(row["source"] for row in events)
    event_counts = Counter(row["event_type"] for row in events)
    event_records = [json.loads(row["record_json"]) for row in events]
    run_counts = Counter(record["run_id"] for record in event_records)
    session_counts = Counter(record["session_id"] for record in event_records)
    wallet_counts = Counter(
        record["wallet_public_key"]
        for record in event_records
        if record.get("wallet_public_key")
    )
    opportunities = store.records("opportunities")
    observed_times = [item["observed_at"] for item in opportunities]
    return {
        "schema_version": 1,
        "storage": "sqlite",
        "counts": {
            table: store.count(table)
            for table in (
                "source_records",
                "events",
                *RECORD_TABLES.keys(),
            )
        },
        "event_type_counts": dict(sorted(event_counts.items())),
        "coverage_by_source": dict(sorted(source_counts.items())),
        "coverage_by_run": dict(sorted(run_counts.items())),
        "coverage_by_session": dict(sorted(session_counts.items())),
        "coverage_by_wallet": dict(sorted(wallet_counts.items())),
        "earliest_timestamp": min(observed_times) if observed_times else None,
        "latest_timestamp": max(observed_times) if observed_times else None,
        "completeness": completeness_report(store),
        "authority": {
            "observer_snapshots": "direct_local_log",
            "board_round_treasury_fields": "direct_rpc_observation_at_capture",
            "participant_wallet_fields": "unavailable",
            "transaction_fees": "unavailable",
            "participant_sol_returns": "unavailable",
            "base_ore": "unavailable",
            "motherlode_ore_participant_share": "unavailable",
            "historical_final_outcomes": "not_imported_as_participant_economics",
        },
    }


def _pseudonym(value: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()
    return f"wallet_{digest[:16]}"


def _transform_wallets(value: Any, salt: str) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                _pseudonym(child, salt)
                if key in {"wallet_public_key", "fee_payer"} and child
                else _transform_wallets(child, salt)
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_transform_wallets(child, salt) for child in value]
    return value


def export_tables(
    store: LedgerStore,
    output_dir: str | Path,
    *,
    pseudonymize_wallets: bool = False,
    pseudonym_salt: str = "rfc006-export-v1",
    force: bool = False,
) -> list[Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for table, filename in EXPORT_NAMES.items():
        records = store.records(table)
        if pseudonymize_wallets:
            records = [
                _transform_wallets(record, pseudonym_salt) for record in records
            ]
        path = directory / filename
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
        outputs.append(path)
    completeness_path = directory / "participant_completeness_v1.json"
    write_strict_json(
        completeness_path, completeness_report(store), force=force
    )
    outputs.append(completeness_path)
    return outputs
