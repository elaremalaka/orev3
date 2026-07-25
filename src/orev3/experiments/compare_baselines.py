from __future__ import annotations

import argparse

from orev3.experiments.runner import (
    prepare_replay_batch,
    run_prepared_experiment,
)
from orev3.replay.loader import (
    load_round_index,
)
from orev3.strategies.fixed_top4 import (
    FixedTop4Strategy,
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
            "Compare baseline ORE Miner V3 "
            "strategies on the same historical dataset."
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
        "--random-seed",
        type=int,
        default=42,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    index = load_round_index(
        args.dataset
    )

    lifecycles = [
        index[round_id]
        for round_id
        in sorted(index)
    ]

    strategies = [
        LeastCrowdedTop4Strategy(),
        FixedTop4Strategy(),
        SeededRandomTop4Strategy(
            base_seed=args.random_seed
        ),
    ]

    print()
    print(
        "ORE Miner V3 — Baseline Comparison"
    )
    print(
        "=================================="
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
        f"Random seed: "
        f"{args.random_seed}"
    )

    print()

    batch = prepare_replay_batch(
        lifecycles=lifecycles,
        requested_slots_remaining=(
            args.slots_remaining
        ),
        max_slot_distance=(
            args.max_slot_distance
        ),
    )

    results = [
        run_prepared_experiment(
            strategy=strategy,
            batch=batch,
        )
        for strategy in strategies
    ]

    print(
        "Strategy                         "
        "Accepted   Hits   Hit Rate   "
        "Motherlode Hits"
    )

    print(
        "------------------------------------------------"
        "----------------"
    )

    for result in results:
        hit_rate = (
            f"{result.winning_square_hit_rate:.2%}"
            if (
                result.winning_square_hit_rate
                is not None
            )
            else "N/A"
        )

        print(
            f"{result.strategy_name:<32}"
            f"{result.accepted_rounds:<11}"
            f"{result.winning_square_hits:<7}"
            f"{hit_rate:<11}"
            f"{result.motherlode_selection_hits}"
        )

    print()
    print(
        "Theoretical random 4-of-25 "
        "coverage rate: 16.00%"
    )


if __name__ == "__main__":
    main()
