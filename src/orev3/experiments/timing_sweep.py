from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TimingResult:
    slots_remaining: int
    accepted_rounds: int
    least_crowded_hits: int
    least_crowded_hit_rate: float
    random_mean_hit_rate: float
    random_median_hit_rate: float
    random_minimum_hit_rate: float
    random_maximum_hit_rate: float
    least_crowded_percentile: float
    preparation_seconds: float
    evaluation_seconds: float
    total_seconds: float


def extract_int(
    pattern: str,
    output: str,
) -> int:
    match = re.search(
        pattern,
        output,
    )

    if match is None:
        raise ValueError(
            f"Could not parse pattern: {pattern}"
        )

    return int(
        match.group(1)
    )


def extract_float(
    pattern: str,
    output: str,
) -> float:
    match = re.search(
        pattern,
        output,
    )

    if match is None:
        raise ValueError(
            f"Could not parse pattern: {pattern}"
        )

    return float(
        match.group(1)
    )


def evaluate_timing(
    slots_remaining: int,
    max_slot_distance: int,
    seeds: int,
) -> TimingResult:
    command = [
        sys.executable,
        "-m",
        (
            "orev3.experiments."
            "random_baseline_distribution"
        ),
        "--slots-remaining",
        str(
            slots_remaining
        ),
        "--max-slot-distance",
        str(
            max_slot_distance
        ),
        "--seeds",
        str(
            seeds
        ),
    ]

    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )

    output = completed.stdout

    return TimingResult(
        slots_remaining=slots_remaining,
        accepted_rounds=extract_int(
            r"Accepted rounds:\s+(\d+)",
            output,
        ),
        least_crowded_hits=extract_int(
            r"Winning-square hits:\s+(\d+)",
            output,
        ),
        least_crowded_hit_rate=extract_float(
            r"Winning-square hit rate:\s+"
            r"([0-9.]+)%",
            output,
        ),
        random_mean_hit_rate=extract_float(
            r"Mean hit rate:\s+([0-9.]+)%",
            output,
        ),
        random_median_hit_rate=extract_float(
            r"Median hit rate:\s+([0-9.]+)%",
            output,
        ),
        random_minimum_hit_rate=extract_float(
            r"Minimum hit rate:\s+([0-9.]+)%",
            output,
        ),
        random_maximum_hit_rate=extract_float(
            r"Maximum hit rate:\s+([0-9.]+)%",
            output,
        ),
        least_crowded_percentile=extract_float(
            r"Least-crowded percentile "
            r"among random controls:\s+"
            r"([0-9.]+)%",
            output,
        ),
        preparation_seconds=extract_float(
            r"Replay preparation seconds:\s+"
            r"([0-9.]+)",
            output,
        ),
        evaluation_seconds=extract_float(
            r"Random evaluation seconds:\s+"
            r"([0-9.]+)",
            output,
        ),
        total_seconds=extract_float(
            r"Total runtime seconds:\s+"
            r"([0-9.]+)",
            output,
        ),
    )


def write_csv(
    path: Path,
    results: list[TimingResult],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(
            handle
        )

        writer.writerow(
            [
                "slots_remaining",
                "accepted_rounds",
                "least_crowded_hits",
                "least_crowded_hit_rate_pct",
                "random_mean_hit_rate_pct",
                "random_median_hit_rate_pct",
                "random_minimum_hit_rate_pct",
                "random_maximum_hit_rate_pct",
                "least_crowded_percentile_pct",
                "preparation_seconds",
                "evaluation_seconds",
                "total_seconds",
            ]
        )

        for result in results:
            writer.writerow(
                [
                    result.slots_remaining,
                    result.accepted_rounds,
                    result.least_crowded_hits,
                    result.least_crowded_hit_rate,
                    result.random_mean_hit_rate,
                    result.random_median_hit_rate,
                    result.random_minimum_hit_rate,
                    result.random_maximum_hit_rate,
                    result.least_crowded_percentile,
                    result.preparation_seconds,
                    result.evaluation_seconds,
                    result.total_seconds,
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare least-crowded performance "
            "against random controls at multiple "
            "decision timings."
        )
    )

    parser.add_argument(
        "--slots",
        nargs="+",
        type=int,
        default=[
            5,
            10,
            15,
            20,
            25,
            30,
            35,
            40,
        ],
    )

    parser.add_argument(
        "--max-slot-distance",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--seeds",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "timing_sweep_results.csv"
        ),
    )

    args = parser.parse_args()

    results: list[
        TimingResult
    ] = []

    print(
        "ORE Miner V3 — Decision Timing Sweep"
    )
    print(
        "=" * 80
    )
    print(
        f"Slots tested: {args.slots}"
    )
    print(
        f"Maximum slot distance: "
        f"{args.max_slot_distance}"
    )
    print(
        f"Random seeds per timing: "
        f"{args.seeds}"
    )
    print()

    for slots_remaining in args.slots:
        print(
            f"Evaluating "
            f"{slots_remaining:>2} "
            "slots remaining...",
            flush=True,
        )

        result = evaluate_timing(
            slots_remaining=(
                slots_remaining
            ),
            max_slot_distance=(
                args.max_slot_distance
            ),
            seeds=args.seeds,
        )

        results.append(
            result
        )

    print()
    print(
        f"{'Slots':>5} "
        f"{'Rounds':>7} "
        f"{'LC Hits':>7} "
        f"{'LC Rate':>8} "
        f"{'Rnd Mean':>8} "
        f"{'Delta':>8} "
        f"{'Pctile':>7}"
    )
    print(
        "-" * 65
    )

    for result in results:
        delta = (
            result.least_crowded_hit_rate
            - result.random_mean_hit_rate
        )

        print(
            f"{result.slots_remaining:>5} "
            f"{result.accepted_rounds:>7} "
            f"{result.least_crowded_hits:>7} "
            f"{result.least_crowded_hit_rate:>7.2f}% "
            f"{result.random_mean_hit_rate:>7.2f}% "
            f"{delta:>+7.2f}% "
            f"{result.least_crowded_percentile:>6.2f}%"
        )

    write_csv(
        path=args.output,
        results=results,
    )

    print()
    print(
        f"CSV written to: "
        f"{args.output.resolve()}"
    )


if __name__ == "__main__":
    main()
