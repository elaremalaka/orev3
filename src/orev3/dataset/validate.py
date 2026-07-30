"""CLI for fail-closed replay dataset validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from orev3.dataset.management import DEFAULT_DATASET_PATH
from orev3.dataset.validation import validate_replay_dataset


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a historical replay dataset and its observations."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = validate_replay_dataset(args.dataset, fail_closed=False)
    print("ORE Miner V3 — Replay Dataset Validation")
    print(f"dataset: {result.dataset_path}")
    print(f"replay_rounds: {result.replay_round_count}")
    print(f"snapshots: {result.snapshot_count}")
    print(f"complete_rounds: {result.complete_round_count}")
    print(f"incomplete_rounds: {result.incomplete_round_count}")
    print(f"missing_outcomes: {result.missing_outcome_count}")
    print(f"validation_issues: {len(result.issues)}")
    print(f"ready_for_replay: {str(result.ready_for_replay).lower()}")
    for issue in result.issues:
        location = (
            f" line={issue.line_number}" if issue.line_number is not None else ""
        )
        round_identifier = (
            f" round={issue.round_identifier}"
            if issue.round_identifier is not None
            else ""
        )
        print(f"issue: {issue.code}{location}{round_identifier}: {issue.message}")
    if not result.valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
