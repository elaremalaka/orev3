"""CLI for read-only managed replay dataset inspection."""

from __future__ import annotations

import argparse
from pathlib import Path

from orev3.dataset.management import (
    DEFAULT_DATASET_PATH,
    DEFAULT_METADATA_PATH,
    inspect_replay_dataset,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and validate the managed replay dataset."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    inspection = inspect_replay_dataset(args.dataset, args.metadata)
    metadata = inspection.metadata
    validation = inspection.validation
    integrity_status = (
        "valid"
        if validation.valid and not inspection.metadata_issues
        else "invalid"
    )
    print("ORE Miner V3 — Replay Dataset Statistics")
    print(f"dataset_version: {metadata.dataset_version}")
    print(f"created_at_utc: {metadata.created_at_utc.isoformat()}")
    print(f"source_collection: {len(metadata.source_collection)}")
    print(f"replay_rounds: {validation.replay_round_count}")
    print(f"snapshots: {validation.snapshot_count}")
    print(f"first_round: {validation.first_round_identifier}")
    print(f"last_round: {validation.last_round_identifier}")
    print(
        "date_range: "
        f"{validation.first_observed_at_utc} .. "
        f"{validation.last_observed_at_utc}"
    )
    print(f"complete_rounds: {validation.complete_round_count}")
    print(f"incomplete_rounds: {validation.incomplete_round_count}")
    print(f"missing_outcomes: {validation.missing_outcome_count}")
    print(f"integrity_status: {integrity_status}")
    print(f"validation_issues: {len(validation.issues)}")
    print(f"metadata_issues: {len(inspection.metadata_issues)}")
    print(f"ready_for_replay: {str(inspection.ready_for_replay).lower()}")
    if not inspection.ready_for_replay:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
