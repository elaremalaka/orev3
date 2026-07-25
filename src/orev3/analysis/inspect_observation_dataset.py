from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DATASET = Path("data/research/observation_dataset_v1.csv")
DEFAULT_OUTPUT = Path("data/research/observation_dataset_summary.json")
EXPECTED_SQUARES_PER_OBSERVATION = 25


def percentile(values: Iterable[int], probability: float) -> float | None:
    ordered = sorted(values)

    if not ordered:
        return None

    if len(ordered) == 1:
        return float(ordered[0])

    position = (len(ordered) - 1) * probability
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index

    return (
        ordered[lower_index]
        + (ordered[upper_index] - ordered[lower_index]) * fraction
    )


def summarize_distribution(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "p95": None,
        }

    return {
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p95": percentile(values, 0.95),
    }


def inspect_dataset(dataset_path: Path) -> dict[str, Any]:
    started_at = time.perf_counter()

    row_count = 0

    round_observation_indices: dict[int, set[int]] = defaultdict(set)
    round_sessions: dict[int, set[str]] = defaultdict(set)
    round_coverage: dict[int, set[str]] = defaultdict(set)
    round_outcome_sources: dict[int, set[str]] = defaultdict(set)

    observation_row_counts: Counter[tuple[int, int]] = Counter()
    observation_square_indices: dict[tuple[int, int], set[int]] = defaultdict(set)

    global_sessions: set[str] = set()

    slots_remaining_min: int | None = None
    slots_remaining_max: int | None = None
    slots_remaining_missing_rows = 0

    with dataset_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)

        required_columns = {
            "round_id",
            "observation_index",
            "collector_session_id",
            "coverage_status",
            "finalized_outcome_source",
            "slots_remaining",
            "square_index",
        }

        fieldnames = set(reader.fieldnames or [])
        missing_columns = sorted(required_columns - fieldnames)

        if missing_columns:
            raise ValueError(
                "Dataset is missing required columns: "
                + ", ".join(missing_columns)
            )

        for row in reader:
            row_count += 1

            round_id = int(row["round_id"])
            observation_index = int(row["observation_index"])
            square_index = int(row["square_index"])

            slots_remaining_raw = row["slots_remaining"].strip()
            slots_remaining = (
                int(slots_remaining_raw)
                if slots_remaining_raw
                else None
            )

            observation_key = (round_id, observation_index)

            round_observation_indices[round_id].add(observation_index)
            observation_row_counts[observation_key] += 1
            observation_square_indices[observation_key].add(square_index)

            collector_session_id = row["collector_session_id"].strip()
            if collector_session_id:
                global_sessions.add(collector_session_id)
                round_sessions[round_id].add(collector_session_id)

            coverage_status = row["coverage_status"].strip() or "unknown"
            round_coverage[round_id].add(coverage_status)

            outcome_source = (
                row["finalized_outcome_source"].strip() or "unknown"
            )
            round_outcome_sources[round_id].add(outcome_source)

            if slots_remaining is None:
                slots_remaining_missing_rows += 1
            elif slots_remaining_min is None:
                slots_remaining_min = slots_remaining
                slots_remaining_max = slots_remaining
            else:
                slots_remaining_min = min(
                    slots_remaining_min,
                    slots_remaining,
                )
                slots_remaining_max = max(
                    slots_remaining_max,
                    slots_remaining,
                )

    round_ids = sorted(round_observation_indices)
    observation_counts = [
        len(round_observation_indices[round_id])
        for round_id in round_ids
    ]
    sessions_per_round = [
        len(round_sessions[round_id])
        for round_id in round_ids
    ]

    non_contiguous_rounds: list[dict[str, Any]] = []

    for round_id in round_ids:
        indices = sorted(round_observation_indices[round_id])

        if not indices:
            continue

        expected = list(range(indices[0], indices[-1] + 1))

        if indices != expected:
            missing = sorted(set(expected) - set(indices))
            non_contiguous_rounds.append(
                {
                    "round_id": round_id,
                    "first_index": indices[0],
                    "last_index": indices[-1],
                    "missing_indices": missing,
                }
            )

    invalid_row_count_observations = [
        {
            "round_id": round_id,
            "observation_index": observation_index,
            "rows": count,
        }
        for (round_id, observation_index), count
        in sorted(observation_row_counts.items())
        if count != EXPECTED_SQUARES_PER_OBSERVATION
    ]

    invalid_square_sets = []

    expected_square_indices = set(
        range(EXPECTED_SQUARES_PER_OBSERVATION)
    )

    for observation_key, square_indices in sorted(
        observation_square_indices.items()
    ):
        if square_indices != expected_square_indices:
            round_id, observation_index = observation_key

            invalid_square_sets.append(
                {
                    "round_id": round_id,
                    "observation_index": observation_index,
                    "missing_square_indices": sorted(
                        expected_square_indices - square_indices
                    ),
                    "unexpected_square_indices": sorted(
                        square_indices - expected_square_indices
                    ),
                }
            )

    coverage_counts: Counter[str] = Counter()
    mixed_coverage_rounds: list[dict[str, Any]] = []

    for round_id in round_ids:
        statuses = sorted(round_coverage[round_id])

        if len(statuses) == 1:
            coverage_counts[statuses[0]] += 1
        else:
            coverage_counts["mixed"] += 1
            mixed_coverage_rounds.append(
                {
                    "round_id": round_id,
                    "statuses": statuses,
                }
            )

    outcome_source_counts: Counter[str] = Counter()
    mixed_outcome_source_rounds: list[dict[str, Any]] = []

    for round_id in round_ids:
        sources = sorted(round_outcome_sources[round_id])

        if len(sources) == 1:
            outcome_source_counts[sources[0]] += 1
        else:
            outcome_source_counts["mixed"] += 1
            mixed_outcome_source_rounds.append(
                {
                    "round_id": round_id,
                    "sources": sources,
                }
            )

    observation_count = len(observation_row_counts)
    expected_row_count = (
        observation_count * EXPECTED_SQUARES_PER_OBSERVATION
    )

    summary: dict[str, Any] = {
        "dataset": str(dataset_path),
        "expected_squares_per_observation": (
            EXPECTED_SQUARES_PER_OBSERVATION
        ),
        "rows": {
            "actual": row_count,
            "expected_from_observations": expected_row_count,
            "matches_expected": row_count == expected_row_count,
        },
        "rounds": {
            "count": len(round_ids),
        },
        "observations": {
            "count": observation_count,
            "per_round": summarize_distribution(
                observation_counts
            ),
        },
        "coverage": {
            "round_counts": dict(sorted(coverage_counts.items())),
            "mixed_rounds": mixed_coverage_rounds,
        },
        "outcome_sources": {
            "round_counts": dict(
                sorted(outcome_source_counts.items())
            ),
            "mixed_rounds": mixed_outcome_source_rounds,
        },
        "collector_sessions": {
            "unique": len(global_sessions),
            "per_round": summarize_distribution(
                sessions_per_round
            ),
        },
        "slots_remaining": {
            "min": slots_remaining_min,
            "max": slots_remaining_max,
            "missing_rows": slots_remaining_missing_rows,
        },
        "observation_indices": {
            "all_rounds_contiguous": not non_contiguous_rounds,
            "non_contiguous_round_count": len(
                non_contiguous_rounds
            ),
            "non_contiguous_rounds": non_contiguous_rounds,
        },
        "square_row_invariants": {
            "all_observations_have_25_rows": (
                not invalid_row_count_observations
            ),
            "invalid_row_count_observation_count": len(
                invalid_row_count_observations
            ),
            "invalid_row_count_observations": (
                invalid_row_count_observations
            ),
            "all_observations_have_square_indices_0_through_24": (
                not invalid_square_sets
            ),
            "invalid_square_set_observation_count": len(
                invalid_square_sets
            ),
            "invalid_square_sets": invalid_square_sets,
        },
        "runtime_seconds": time.perf_counter() - started_at,
    }

    return summary


def print_summary(summary: dict[str, Any]) -> None:
    observations = summary["observations"]
    observation_distribution = observations["per_round"]
    sessions = summary["collector_sessions"]
    rows = summary["rows"]
    indices = summary["observation_indices"]
    invariants = summary["square_row_invariants"]

    print()
    print("ORE Miner V3 — Observation Dataset Inspection")
    print("=============================================")
    print(f"Dataset: {summary['dataset']}")
    print(f"Rows: {rows['actual']:,}")
    print(f"Rounds: {summary['rounds']['count']:,}")
    print(f"Observations: {observations['count']:,}")
    print()

    print("Observations per round")
    print("----------------------")
    print(f"Min: {observation_distribution['min']}")
    print(f"Max: {observation_distribution['max']}")
    print(f"Mean: {observation_distribution['mean']:.2f}")
    print(f"Median: {observation_distribution['median']}")
    print(f"P95: {observation_distribution['p95']:.2f}")
    print()

    print("Coverage")
    print("--------")
    for status, count in summary["coverage"]["round_counts"].items():
        print(f"{status}: {count}")
    print()

    print("Outcome sources")
    print("---------------")
    for source, count in summary["outcome_sources"][
        "round_counts"
    ].items():
        print(f"{source}: {count}")
    print()

    print("Collector sessions")
    print("------------------")
    print(f"Unique sessions: {sessions['unique']}")
    print(
        "Sessions per round: "
        f"min={sessions['per_round']['min']}, "
        f"median={sessions['per_round']['median']}, "
        f"max={sessions['per_round']['max']}"
    )
    print()

    print("Slots remaining")
    print("---------------")
    print(f"Min: {summary['slots_remaining']['min']}")
    print(f"Max: {summary['slots_remaining']['max']}")
    print(
        "Missing rows: "
        f"{summary['slots_remaining']['missing_rows']:,}"
    )
    print()

    print("Dataset invariants")
    print("------------------")
    print(
        "Rows equal observations × 25: "
        f"{rows['matches_expected']}"
    )
    print(
        "Observation indices contiguous: "
        f"{indices['all_rounds_contiguous']}"
    )
    print(
        "Every observation has 25 rows: "
        f"{invariants['all_observations_have_25_rows']}"
    )
    print(
        "Every observation has squares 0–24: "
        f"{invariants['all_observations_have_square_indices_0_through_24']}"
    )
    print()
    print(
        f"Inspection completed in "
        f"{summary['runtime_seconds']:.3f} seconds"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the canonical ORE V3 observation dataset."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Input CSV. Default: {DEFAULT_DATASET}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Summary JSON. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.dataset.exists():
        raise FileNotFoundError(
            f"Observation dataset not found: {args.dataset}"
        )

    summary = inspect_dataset(args.dataset)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print_summary(summary)
    print(f"Summary JSON: {args.output}")


if __name__ == "__main__":
    main()
