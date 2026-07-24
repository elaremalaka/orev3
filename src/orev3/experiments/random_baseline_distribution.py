from __future__ import annotations

import argparse
import statistics
import time

from orev3.experiments.runner import (
    prepare_replay_batch,
    run_prepared_experiment,
)
from orev3.replay.loader import (
    load_round_index,
)
from orev3.strategies.least_crowded import (
    LeastCrowdedTop4Strategy,
)
from orev3.strategies.random_top4 import (
    SeededRandomTop4Strategy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare least-crowded performance against "
            "many reproducible random 4-of-25 controls."
        )
    )

    parser.add_argument(
        "--dataset",
        default=(
            "data/derived/"
            "round_lifecycles_v1.jsonl"
        ),
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
        "--seeds",
        type=int,
        default=100,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.seeds <= 0:
        raise SystemExit(
            "--seeds must be greater than 0."
        )

    started_at = time.monotonic()

    index = load_round_index(
        args.dataset
    )

    lifecycles = [
        index[round_id]
        for round_id in sorted(index)
    ]

    print()
    print(
        "Preparing reusable replay batch..."
    )

    batch = prepare_replay_batch(
        lifecycles=lifecycles,
        requested_slots_remaining=(
            args.slots_remaining
        ),
        max_slot_distance=(
            args.max_slot_distance
        ),
    )

    preparation_seconds = (
        time.monotonic()
        - started_at
    )

    print(
        f"Accepted replay points: "
        f"{len(batch.accepted)}"
    )

    print(
        f"Rejected replay points: "
        f"{len(batch.rejected)}"
    )

    print(
        "Replay preparation seconds: "
        f"{preparation_seconds:.3f}"
    )

    least_crowded = (
        run_prepared_experiment(
            strategy=(
                LeastCrowdedTop4Strategy()
            ),
            batch=batch,
        )
    )

    least_rate = (
        least_crowded
        .winning_square_hit_rate
    )

    random_rates: list[
        float
    ] = []

    random_started_at = (
        time.monotonic()
    )

    for seed in range(
        args.seeds
    ):
        result = (
            run_prepared_experiment(
                strategy=(
                    SeededRandomTop4Strategy(
                        base_seed=seed
                    )
                ),
                batch=batch,
            )
        )

        if (
            result
            .winning_square_hit_rate
            is not None
        ):
            random_rates.append(
                result
                .winning_square_hit_rate
            )

    random_seconds = (
        time.monotonic()
        - random_started_at
    )

    if not random_rates:
        raise SystemExit(
            "No random baseline results."
        )

    if least_rate is None:
        raise SystemExit(
            "Least-crowded strategy produced "
            "no scored participation rate."
        )

    mean_rate = statistics.mean(
        random_rates
    )

    median_rate = statistics.median(
        random_rates
    )

    min_rate = min(
        random_rates
    )

    max_rate = max(
        random_rates
    )

    random_at_or_below = sum(
        1
        for rate in random_rates
        if rate <= least_rate
    )

    random_above = sum(
        1
        for rate in random_rates
        if rate > least_rate
    )

    percentile = (
        random_at_or_below
        / len(random_rates)
    )

    total_seconds = (
        time.monotonic()
        - started_at
    )

    print()
    print(
        "ORE Miner V3 — "
        "Random Baseline Distribution"
    )
    print(
        "====================================="
    )

    print(
        "Requested slots remaining: "
        f"{args.slots_remaining}"
    )

    print(
        "Maximum slot distance: "
        f"{args.max_slot_distance}"
    )

    print(
        f"Random seeds tested: "
        f"{len(random_rates)}"
    )

    print(
        f"Accepted rounds: "
        f"{least_crowded.accepted_rounds}"
    )

    print()
    print("Least-Crowded Baseline")
    print("----------------------")

    print(
        "Winning-square hits: "
        f"{least_crowded.winning_square_hits}"
    )

    print(
        "Winning-square hit rate: "
        f"{least_rate:.2%}"
    )

    print()
    print("Random 4-of-25 Distribution")
    print("---------------------------")

    print(
        f"Mean hit rate: "
        f"{mean_rate:.2%}"
    )

    print(
        f"Median hit rate: "
        f"{median_rate:.2%}"
    )

    print(
        f"Minimum hit rate: "
        f"{min_rate:.2%}"
    )

    print(
        f"Maximum hit rate: "
        f"{max_rate:.2%}"
    )

    print()
    print("Least-Crowded vs Random")
    print("-----------------------")

    print(
        "Random seeds at or below "
        "least-crowded: "
        f"{random_at_or_below}"
    )

    print(
        "Random seeds above "
        "least-crowded: "
        f"{random_above}"
    )

    print(
        "Least-crowded percentile "
        "among random controls: "
        f"{percentile:.2%}"
    )

    print()
    print("Performance")
    print("-----------")

    print(
        "Random evaluation seconds: "
        f"{random_seconds:.3f}"
    )

    print(
        f"Total runtime seconds: "
        f"{total_seconds:.3f}"
    )

    print()
    print(
        "Theoretical random 4-of-25 "
        "coverage rate: 16.00%"
    )


if __name__ == "__main__":
    main()
