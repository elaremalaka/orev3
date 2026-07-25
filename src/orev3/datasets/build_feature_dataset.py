from __future__ import annotations

import argparse
import time
from pathlib import Path

from orev3.datasets.square_features import (
    DATASET_VERSION,
    build_square_feature_rows,
    write_manifest,
    write_square_feature_csv,
)
from orev3.experiments.runner import prepare_replay_batch
from orev3.replay.loader import load_round_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build one square-level research row per accepted historical "
            "round and board square."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/derived/round_lifecycles_v1.jsonl",
        help="Historical round-index JSONL used by existing experiments.",
    )
    parser.add_argument(
        "--slots-remaining",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--max-slot-distance",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output CSV path. Defaults to "
            "data/research/<dataset_version>_slots_<N>.csv"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(
        args.output
        or (
            "data/research/"
            f"{DATASET_VERSION}_slots_{args.slots_remaining}.csv"
        )
    )

    started = time.perf_counter()
    index = load_round_index(args.dataset)
    lifecycles = [index[round_id] for round_id in sorted(index)]
    loaded = time.perf_counter()

    batch = prepare_replay_batch(
        lifecycles=lifecycles,
        requested_slots_remaining=args.slots_remaining,
        max_slot_distance=args.max_slot_distance,
    )
    prepared = time.perf_counter()

    rows = build_square_feature_rows(batch)
    built = time.perf_counter()

    csv_path = write_square_feature_csv(rows, output)
    manifest_path = write_manifest(
        output_csv=csv_path,
        batch=batch,
        row_count=len(rows),
    )
    finished = time.perf_counter()

    print()
    print("ORE Miner V3 — Square Feature Dataset")
    print("=====================================")
    print(f"Dataset version: {DATASET_VERSION}")
    print(f"Source rounds: {batch.total_rounds}")
    print(f"Accepted rounds: {len(batch.accepted)}")
    print(f"Rejected rounds: {len(batch.rejected)}")
    print(f"Rows written: {len(rows)}")
    print(f"Expected rows: {len(batch.accepted) * 25}")
    print(f"CSV: {csv_path}")
    print(f"Manifest: {manifest_path}")
    print()
    print(f"Index loading seconds: {loaded - started:.3f}")
    print(f"Replay preparation seconds: {prepared - loaded:.3f}")
    print(f"Feature construction seconds: {built - prepared:.3f}")
    print(f"Writing seconds: {finished - built:.3f}")
    print(f"Total seconds: {finished - started:.3f}")


if __name__ == "__main__":
    main()
