from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_DATASET = Path("data/research/observation_dataset_v1.csv")
DEFAULT_OUTPUT = Path("data/research/temporal_behavior_summary.json")

PROGRESS_BUCKETS = 20


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * probability
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index

    return (
        ordered[lower_index]
        + (ordered[upper_index] - ordered[lower_index]) * fraction
    )


def summarize(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
        }

    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p25": percentile(values, 0.25),
        "p75": percentile(values, 0.75),
    }


def progress_bucket(
    observation_index: int,
    observation_count: int,
) -> int:
    if observation_count <= 1:
        return 0

    progress = observation_index / (observation_count - 1)

    return min(
        PROGRESS_BUCKETS - 1,
        int(progress * PROGRESS_BUCKETS),
    )


def entropy(values: list[int]) -> float:
    total = sum(values)

    if total <= 0:
        return 0.0

    result = 0.0

    for value in values:
        if value <= 0:
            continue

        probability = value / total
        result -= probability * math.log(probability)

    return result


def analyze(dataset_path: Path) -> dict[str, Any]:
    started_at = time.perf_counter()

    observations: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}

    with dataset_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)

        required_columns = {
            "round_id",
            "observation_index",
            "round_observation_count",
            "slots_remaining",
            "square_index",
            "deployed_lamports",
            "miner_count",
            "winning_square",
        }

        missing = sorted(
            required_columns - set(reader.fieldnames or [])
        )

        if missing:
            raise ValueError(
                "Missing required columns: " + ", ".join(missing)
            )

        for row in reader:
            round_id = int(row["round_id"])
            observation_index = int(row["observation_index"])
            observation_count = int(
                row["round_observation_count"]
            )
            square_index = int(row["square_index"])

            key = (round_id, observation_index)

            observation = observations.setdefault(
                key,
                {
                    "round_id": round_id,
                    "observation_index": observation_index,
                    "observation_count": observation_count,
                    "slots_remaining": (
                        int(row["slots_remaining"])
                        if row["slots_remaining"].strip()
                        else None
                    ),
                    "winning_square": int(row["winning_square"]),
                    "miners": [0] * 25,
                    "deployed": [0] * 25,
                },
            )

            observation["miners"][square_index] = int(
                row["miner_count"]
            )
            observation["deployed"][square_index] = int(
                row["deployed_lamports"]
            )

    by_progress: dict[int, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    by_slots: dict[int, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for observation in observations.values():
        miners = observation["miners"]
        deployed = observation["deployed"]
        winning_square = observation["winning_square"]

        total_miners = sum(miners)
        total_deployed = sum(deployed)

        active_squares = sum(
            1
            for miner_count, lamports in zip(miners, deployed)
            if miner_count > 0 or lamports > 0
        )

        sorted_miners = sorted(miners, reverse=True)

        top_1_miner_share = (
            sorted_miners[0] / total_miners
            if total_miners > 0
            else 0.0
        )
        top_3_miner_share = (
            sum(sorted_miners[:3]) / total_miners
            if total_miners > 0
            else 0.0
        )
        top_5_miner_share = (
            sum(sorted_miners[:5]) / total_miners
            if total_miners > 0
            else 0.0
        )

        winner_miners = miners[winning_square]
        winner_deployed = deployed[winning_square]

        winner_miner_rank = (
            1
            + sum(
                value > winner_miners
                for value in miners
            )
        )
        winner_deployed_rank = (
            1
            + sum(
                value > winner_deployed
                for value in deployed
            )
        )

        metrics = {
            "total_miners": float(total_miners),
            "total_deployed_lamports": float(total_deployed),
            "active_squares": float(active_squares),
            "mean_miners_per_square": (
                total_miners / 25
            ),
            "mean_deployed_lamports_per_square": (
                total_deployed / 25
            ),
            "top_1_miner_share": top_1_miner_share,
            "top_3_miner_share": top_3_miner_share,
            "top_5_miner_share": top_5_miner_share,
            "miner_entropy": entropy(miners),
            "winner_miner_count": float(winner_miners),
            "winner_deployed_lamports": float(
                winner_deployed
            ),
            "winner_miner_rank": float(winner_miner_rank),
            "winner_deployed_rank": float(
                winner_deployed_rank
            ),
            "winner_in_top_1_miners": float(
                winner_miner_rank <= 1
            ),
            "winner_in_top_3_miners": float(
                winner_miner_rank <= 3
            ),
            "winner_in_top_5_miners": float(
                winner_miner_rank <= 5
            ),
        }

        bucket = progress_bucket(
            observation["observation_index"],
            observation["observation_count"],
        )

        for metric_name, value in metrics.items():
            by_progress[bucket][metric_name].append(value)

        slots_remaining = observation["slots_remaining"]

        if slots_remaining is not None:
            for metric_name, value in metrics.items():
                by_slots[slots_remaining][metric_name].append(
                    value
                )

    progress_summary: list[dict[str, Any]] = []

    for bucket in range(PROGRESS_BUCKETS):
        bucket_metrics = by_progress.get(bucket, {})

        if not bucket_metrics:
            continue

        progress_summary.append(
            {
                "bucket": bucket,
                "progress_start": bucket / PROGRESS_BUCKETS,
                "progress_end": (
                    (bucket + 1) / PROGRESS_BUCKETS
                ),
                "observation_count": len(
                    next(iter(bucket_metrics.values()))
                ),
                "metrics": {
                    metric_name: summarize(values)
                    for metric_name, values
                    in sorted(bucket_metrics.items())
                },
            }
        )

    slot_summary: list[dict[str, Any]] = []

    for slots_remaining in sorted(by_slots, reverse=True):
        slot_metrics = by_slots[slots_remaining]

        slot_summary.append(
            {
                "slots_remaining": slots_remaining,
                "observation_count": len(
                    next(iter(slot_metrics.values()))
                ),
                "metrics": {
                    metric_name: summarize(values)
                    for metric_name, values
                    in sorted(slot_metrics.items())
                },
            }
        )

    return {
        "dataset": str(dataset_path),
        "observation_count": len(observations),
        "progress_bucket_count": PROGRESS_BUCKETS,
        "by_progress": progress_summary,
        "by_slots_remaining": slot_summary,
        "runtime_seconds": time.perf_counter() - started_at,
    }


def format_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"

    return f"{value:.{digits}f}"


def print_summary(summary: dict[str, Any]) -> None:
    print()
    print("ORE Miner V3 — Temporal Behavior Analysis")
    print("========================================")
    print(f"Dataset: {summary['dataset']}")
    print(
        f"Observations: {summary['observation_count']:,}"
    )
    print()

    print("Progress buckets")
    print("----------------")

    selected_buckets = {0, 4, 9, 14, 19}

    for item in summary["by_progress"]:
        if item["bucket"] not in selected_buckets:
            continue

        metrics = item["metrics"]

        print(
            f"Bucket {item['bucket']:>2} "
            f"({item['progress_start']:.0%}–"
            f"{item['progress_end']:.0%})"
        )
        print(
            "  observations: "
            f"{item['observation_count']:,}"
        )
        print(
            "  total miners mean: "
            f"{format_number(metrics['total_miners']['mean'])}"
        )
        print(
            "  active squares mean: "
            f"{format_number(metrics['active_squares']['mean'])}"
        )
        print(
            "  total deployed SOL mean: "
            f"{format_number(
                metrics['total_deployed_lamports']['mean']
                / 1_000_000_000,
                6,
            )}"
        )
        print(
            "  top-3 miner share mean: "
            f"{format_number(
                metrics['top_3_miner_share']['mean'] * 100
            )}%"
        )
        print(
            "  winner miner rank median: "
            f"{format_number(
                metrics['winner_miner_rank']['median']
            )}"
        )
        print(
            "  winner in top 5: "
            f"{format_number(
                metrics['winner_in_top_5_miners']['mean']
                * 100
            )}%"
        )
        print()

    print(
        f"Analysis completed in "
        f"{summary['runtime_seconds']:.3f} seconds"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze temporal behavior in the canonical "
            "ORE observation dataset."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.dataset.exists():
        raise FileNotFoundError(
            f"Dataset not found: {args.dataset}"
        )

    summary = analyze(args.dataset)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print_summary(summary)
    print(f"Summary JSON: {args.output}")


if __name__ == "__main__":
    main()
