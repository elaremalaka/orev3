from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_DATASET = Path("data/research/observation_dataset_v1.csv")
DEFAULT_OUTPUT = Path(
    "data/research/winner_metric_dynamics_summary.json"
)

SQUARE_COUNT = 25
PROGRESS_BUCKET_COUNT = 20
METRICS = (
    "mass",
    "deployed_lamports",
    "miner_count",
)


def percentile(
    values: list[float],
    probability: float,
) -> float | None:
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
        + (
            ordered[upper_index] - ordered[lower_index]
        )
        * fraction
    )


def summarize(
    values: list[float],
) -> dict[str, float | None]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
        }

    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p25": percentile(values, 0.25),
        "p75": percentile(values, 0.75),
    }


def rank_descending(
    values: list[int],
    square_index: int,
) -> int:
    target = values[square_index]

    return 1 + sum(
        value > target
        for value in values
    )


def rank_percentile(rank: int) -> float:
    if SQUARE_COUNT <= 1:
        return 1.0

    return (
        SQUARE_COUNT - rank
    ) / (
        SQUARE_COUNT - 1
    )


def normalized_progress(
    observation_index: int,
    observation_count: int,
) -> float:
    if observation_count <= 1:
        return 0.0

    return observation_index / (
        observation_count - 1
    )


def progress_bucket(progress: float) -> int:
    return min(
        PROGRESS_BUCKET_COUNT - 1,
        int(progress * PROGRESS_BUCKET_COUNT),
    )


def load_observations(
    dataset_path: Path,
) -> dict[int, list[dict[str, Any]]]:
    observations: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}

    required_columns = {
        "round_id",
        "observation_index",
        "round_observation_count",
        "square_index",
        "mass",
        "deployed_lamports",
        "miner_count",
        "winning_square",
    }

    with dataset_path.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        reader = csv.DictReader(handle)

        missing_columns = sorted(
            required_columns
            - set(reader.fieldnames or [])
        )

        if missing_columns:
            raise ValueError(
                "Dataset is missing required columns: "
                + ", ".join(missing_columns)
            )

        for row in reader:
            round_id = int(row["round_id"])
            observation_index = int(
                row["observation_index"]
            )
            observation_count = int(
                row["round_observation_count"]
            )
            square_index = int(row["square_index"])

            key = (round_id, observation_index)

            observation = observations.setdefault(
                key,
                {
                    "round_id": round_id,
                    "observation_index": (
                        observation_index
                    ),
                    "observation_count": (
                        observation_count
                    ),
                    "winning_square": int(
                        row["winning_square"]
                    ),
                    "mass": [0] * SQUARE_COUNT,
                    "deployed_lamports": (
                        [0] * SQUARE_COUNT
                    ),
                    "miner_count": (
                        [0] * SQUARE_COUNT
                    ),
                },
            )

            observation["mass"][square_index] = int(
                row["mass"]
            )
            observation[
                "deployed_lamports"
            ][square_index] = int(
                row["deployed_lamports"]
            )
            observation[
                "miner_count"
            ][square_index] = int(
                row["miner_count"]
            )

    rounds: dict[
        int,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for observation in observations.values():
        rounds[observation["round_id"]].append(
            observation
        )

    for round_observations in rounds.values():
        round_observations.sort(
            key=lambda item: item[
                "observation_index"
            ]
        )

    return dict(rounds)


def analyze(
    dataset_path: Path,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    rounds = load_observations(dataset_path)

    by_progress: dict[
        str,
        dict[
            int,
            dict[str, list[float]],
        ],
    ] = {
        metric: defaultdict(
            lambda: defaultdict(list)
        )
        for metric in METRICS
    }

    round_level: dict[
        str,
        dict[str, list[float]],
    ] = {
        metric: defaultdict(list)
        for metric in METRICS
    }

    for round_id, observations in rounds.items():
        del round_id

        metric_rank_series: dict[
            str,
            list[int],
        ] = {
            metric: []
            for metric in METRICS
        }

        metric_progress_series: dict[
            str,
            list[float],
        ] = {
            metric: []
            for metric in METRICS
        }

        for observation in observations:
            winning_square = observation[
                "winning_square"
            ]

            progress = normalized_progress(
                observation["observation_index"],
                observation["observation_count"],
            )
            bucket = progress_bucket(progress)

            for metric in METRICS:
                values = observation[metric]
                rank = rank_descending(
                    values,
                    winning_square,
                )
                winner_value = values[
                    winning_square
                ]

                bucket_metrics = by_progress[
                    metric
                ][bucket]

                bucket_metrics[
                    "winner_rank"
                ].append(float(rank))
                bucket_metrics[
                    "winner_rank_percentile"
                ].append(
                    rank_percentile(rank)
                )
                bucket_metrics[
                    "winner_value"
                ].append(float(winner_value))
                bucket_metrics[
                    "winner_top_1"
                ].append(float(rank <= 1))
                bucket_metrics[
                    "winner_top_3"
                ].append(float(rank <= 3))
                bucket_metrics[
                    "winner_top_5"
                ].append(float(rank <= 5))
                bucket_metrics[
                    "winner_top_10"
                ].append(float(rank <= 10))

                metric_rank_series[
                    metric
                ].append(rank)
                metric_progress_series[
                    metric
                ].append(progress)

        for metric in METRICS:
            ranks = metric_rank_series[metric]
            progresses = metric_progress_series[
                metric
            ]

            if not ranks:
                continue

            rank_changes = [
                abs(current - previous)
                for previous, current in zip(
                    ranks,
                    ranks[1:],
                )
            ]

            round_level[metric][
                "final_rank"
            ].append(float(ranks[-1]))

            round_level[metric][
                "best_rank"
            ].append(float(min(ranks)))

            round_level[metric][
                "worst_rank"
            ].append(float(max(ranks)))

            round_level[metric][
                "mean_absolute_rank_change"
            ].append(
                statistics.fmean(rank_changes)
                if rank_changes
                else 0.0
            )

            for top_k in (1, 3, 5, 10):
                qualifying_indices = [
                    index
                    for index, rank in enumerate(
                        ranks
                    )
                    if rank <= top_k
                ]

                round_level[metric][
                    f"ever_top_{top_k}"
                ].append(
                    float(bool(qualifying_indices))
                )

                round_level[metric][
                    f"top_{top_k}_observation_share"
                ].append(
                    sum(
                        rank <= top_k
                        for rank in ranks
                    )
                    / len(ranks)
                )

                if qualifying_indices:
                    first_index = (
                        qualifying_indices[0]
                    )
                    last_index = (
                        qualifying_indices[-1]
                    )

                    round_level[metric][
                        f"first_top_{top_k}_progress"
                    ].append(
                        progresses[first_index]
                    )
                    round_level[metric][
                        f"last_top_{top_k}_progress"
                    ].append(
                        progresses[last_index]
                    )

    progress_output: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for metric in METRICS:
        metric_output = []

        for bucket in range(
            PROGRESS_BUCKET_COUNT
        ):
            bucket_values = by_progress[
                metric
            ].get(bucket)

            if not bucket_values:
                continue

            metric_output.append(
                {
                    "bucket": bucket,
                    "progress_start": (
                        bucket
                        / PROGRESS_BUCKET_COUNT
                    ),
                    "progress_end": (
                        (bucket + 1)
                        / PROGRESS_BUCKET_COUNT
                    ),
                    "observation_count": len(
                        bucket_values[
                            "winner_rank"
                        ]
                    ),
                    "metrics": {
                        name: summarize(values)
                        for name, values
                        in sorted(
                            bucket_values.items()
                        )
                    },
                }
            )

        progress_output[metric] = (
            metric_output
        )

    round_output = {
        metric: {
            name: summarize(values)
            for name, values
            in sorted(
                round_level[metric].items()
            )
        }
        for metric in METRICS
    }

    return {
        "dataset": str(dataset_path),
        "round_count": len(rounds),
        "progress_bucket_count": (
            PROGRESS_BUCKET_COUNT
        ),
        "metrics": list(METRICS),
        "by_progress": progress_output,
        "round_level": round_output,
        "runtime_seconds": (
            time.perf_counter() - started_at
        ),
    }


def format_number(
    value: float | None,
    digits: int = 2,
) -> str:
    if value is None:
        return "n/a"

    return f"{value:.{digits}f}"


def print_progress_comparison(
    summary: dict[str, Any],
) -> None:
    selected_buckets = {
        0,
        4,
        9,
        14,
        19,
    }

    print("Winner rank by progress")
    print("-----------------------")

    for metric in METRICS:
        print()
        print(metric)
        print("~" * len(metric))

        for item in summary[
            "by_progress"
        ][metric]:
            if item["bucket"] not in (
                selected_buckets
            ):
                continue

            metrics = item["metrics"]

            print(
                f"Bucket {item['bucket']:>2} "
                f"({item['progress_start']:.0%}–"
                f"{item['progress_end']:.0%})"
            )
            print(
                "  winner rank median: "
                f"{format_number(
                    metrics[
                        'winner_rank'
                    ]['median']
                )}"
            )
            print(
                "  winner rank mean: "
                f"{format_number(
                    metrics[
                        'winner_rank'
                    ]['mean']
                )}"
            )
            print(
                "  winner percentile mean: "
                f"{format_number(
                    metrics[
                        'winner_rank_percentile'
                    ]['mean']
                    * 100
                )}%"
            )
            print(
                "  winner top 1: "
                f"{format_number(
                    metrics[
                        'winner_top_1'
                    ]['mean']
                    * 100
                )}%"
            )
            print(
                "  winner top 3: "
                f"{format_number(
                    metrics[
                        'winner_top_3'
                    ]['mean']
                    * 100
                )}%"
            )
            print(
                "  winner top 5: "
                f"{format_number(
                    metrics[
                        'winner_top_5'
                    ]['mean']
                    * 100
                )}%"
            )


def print_round_comparison(
    summary: dict[str, Any],
) -> None:
    print()
    print("Round-level winner behavior")
    print("---------------------------")

    for metric in METRICS:
        values = summary[
            "round_level"
        ][metric]

        print()
        print(metric)
        print("~" * len(metric))
        print(
            "  final rank median: "
            f"{format_number(
                values[
                    'final_rank'
                ]['median']
            )}"
        )
        print(
            "  best rank median: "
            f"{format_number(
                values[
                    'best_rank'
                ]['median']
            )}"
        )
        print(
            "  ever top 1: "
            f"{format_number(
                values[
                    'ever_top_1'
                ]['mean']
                * 100
            )}%"
        )
        print(
            "  ever top 3: "
            f"{format_number(
                values[
                    'ever_top_3'
                ]['mean']
                * 100
            )}%"
        )
        print(
            "  ever top 5: "
            f"{format_number(
                values[
                    'ever_top_5'
                ]['mean']
                * 100
            )}%"
        )
        print(
            "  top-5 observation share: "
            f"{format_number(
                values[
                    'top_5_observation_share'
                ]['mean']
                * 100
            )}%"
        )
        print(
            "  first top-5 progress median: "
            f"{format_number(
                values.get(
                    'first_top_5_progress',
                    {},
                ).get('median')
                * 100
                if values.get(
                    'first_top_5_progress',
                    {},
                ).get('median')
                is not None
                else None
            )}%"
        )
        print(
            "  mean absolute rank change: "
            f"{format_number(
                values[
                    'mean_absolute_rank_change'
                ]['mean']
            )}"
        )


def print_summary(
    summary: dict[str, Any],
) -> None:
    print()
    print(
        "ORE Miner V3 — Winner Metric Dynamics"
    )
    print(
        "====================================="
    )
    print(f"Dataset: {summary['dataset']}")
    print(
        f"Rounds: {summary['round_count']:,}"
    )
    print()

    print_progress_comparison(summary)
    print_round_comparison(summary)

    print()
    print(
        "Analysis completed in "
        f"{summary['runtime_seconds']:.3f} "
        "seconds"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare winning-square mass, "
            "deployment, and miner-count "
            "dynamics."
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

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.output.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print_summary(summary)
    print(f"Summary JSON: {args.output}")


if __name__ == "__main__":
    main()
