"""CLI for deterministic Research Domain replay dataset rebuilding."""

from __future__ import annotations

import argparse
from pathlib import Path

from orev3.dataset.management import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DATASET_VERSION,
    DEFAULT_METADATA_PATH,
    DEFAULT_OBSERVER_PATTERN,
    DEFAULT_OBSERVER_ROOT,
    DatasetBuildConfiguration,
    build_replay_dataset,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild the managed historical replay dataset."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Observer JSONL files. When omitted, files are discovered.",
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_OBSERVER_ROOT)
    parser.add_argument("--pattern", default=DEFAULT_OBSERVER_PATTERN)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--dataset-version", default=DEFAULT_DATASET_VERSION)
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Do not fetch missing finalized outcomes.",
    )
    parser.add_argument("--enrichment-delay", type=float, default=0.25)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = build_replay_dataset(
        DatasetBuildConfiguration(
            output_path=args.output,
            metadata_path=args.metadata,
            dataset_version=args.dataset_version,
            observer_paths=tuple(args.paths),
            observer_root=args.source_root,
            observer_pattern=args.pattern,
            enrich_missing_outcomes=not args.skip_enrichment,
            enrichment_delay_seconds=args.enrichment_delay,
        )
    )
    metadata = result.metadata
    print("ORE Miner V3 — Replay Dataset Build")
    print(f"dataset_version: {metadata.dataset_version}")
    print(f"source_files: {result.source_file_count}")
    print(f"source_lines: {result.source_line_count}")
    print(
        "malformed_source_records: "
        f"{result.malformed_source_record_count}"
    )
    print(f"replay_rounds: {metadata.replay_round_count}")
    print(f"snapshots: {metadata.snapshot_count}")
    print(f"complete_rounds: {metadata.complete_round_count}")
    print(f"incomplete_rounds: {metadata.incomplete_round_count}")
    print(f"missing_outcomes: {metadata.missing_outcome_count}")
    print(f"observed_outcomes: {result.observed_outcome_count}")
    print(f"enriched_outcomes: {result.enriched_outcome_count}")
    print(f"integrity_status: {metadata.integrity_status}")
    print(f"ready_for_replay: {str(metadata.ready_for_replay).lower()}")
    print(f"dataset: {result.dataset_path}")
    print(f"metadata: {result.metadata_path}")


if __name__ == "__main__":
    main()
