from __future__ import annotations

import argparse
import time
from pathlib import Path

from orev3.datasets.observation_dataset import (
    DATASET_VERSION,
    build_observation_rows,
    write_manifest,
    write_observation_csv,
)
from orev3.replay.loader import load_round_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the canonical RFC-003A observation "
            "dataset with one row per round, observation, "
            "and square."
        )
    )

    parser.add_argument(
        "--dataset",
        default=(
            "data/derived/"
            "round_lifecycles_v1.jsonl"
        ),
        help=(
            "Historical round lifecycle index JSONL."
        ),
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output CSV path. Defaults to "
            "data/research/"
            "observation_dataset_v1.csv"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output = Path(
        args.output
        or (
            "data/research/"
            f"{DATASET_VERSION}.csv"
        )
    )

    started = time.perf_counter()

    index = load_round_index(
        args.dataset
    )

    lifecycles = [
        index[round_id]
        for round_id in sorted(index)
    ]

    loaded = time.perf_counter()

    rows, summary = (
        build_observation_rows(
            lifecycles
        )
    )

    built = time.perf_counter()

    csv_path = write_observation_csv(
        rows,
        output,
    )

    manifest_path = write_manifest(
        output_csv=csv_path,
        summary=summary,
    )

    finished = time.perf_counter()

    expected_rows = (
        summary.source_observations
        * 25
    )

    print()
    print(
        "ORE Miner V3 — "
        "Canonical Observation Dataset"
    )
    print(
        "=========================================="
    )
    print(
        f"Dataset version: {DATASET_VERSION}"
    )
    print(
        f"Source rounds: "
        f"{summary.source_rounds}"
    )
    print(
        f"Source observations: "
        f"{summary.source_observations}"
    )
    print(
        f"Rows written: "
        f"{summary.rows_written}"
    )
    print(
        f"Expected rows: "
        f"{expected_rows}"
    )
    print(
        f"Rounds with outcomes: "
        f"{summary.rounds_with_outcomes}"
    )
    print(
        f"Rounds without outcomes: "
        f"{summary.rounds_without_outcomes}"
    )
    print(
        f"Observed outcomes: "
        f"{summary.observed_outcomes}"
    )
    print(
        f"Enriched outcomes: "
        f"{summary.enriched_outcomes}"
    )
    print(
        f"Complete rounds: "
        f"{summary.complete_rounds}"
    )
    print(
        f"Partial rounds: "
        f"{summary.partial_rounds}"
    )
    print(
        f"Unknown coverage rounds: "
        f"{summary.unknown_coverage_rounds}"
    )
    print(
        f"CSV: {csv_path}"
    )
    print(
        f"Manifest: {manifest_path}"
    )
    print()
    print(
        f"Index loading seconds: "
        f"{loaded - started:.3f}"
    )
    print(
        f"Observation construction seconds: "
        f"{built - loaded:.3f}"
    )
    print(
        f"Writing seconds: "
        f"{finished - built:.3f}"
    )
    print(
        f"Total seconds: "
        f"{finished - started:.3f}"
    )

    if summary.rows_written != expected_rows:
        raise RuntimeError(
            "Observation row count mismatch: "
            f"wrote {summary.rows_written}, "
            f"expected {expected_rows}."
        )


if __name__ == "__main__":
    main()
