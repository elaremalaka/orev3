from __future__ import annotations

import argparse
from collections import Counter

from orev3.experiments.runner import (
    run_experiment,
)
from orev3.replay.loader import (
    load_round_index,
)
from orev3.strategies.least_crowded import (
    LeastCrowdedTop4Strategy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the least-crowded baseline "
            "across the historical dataset."
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

    strategy = (
        LeastCrowdedTop4Strategy()
    )

    result = run_experiment(
        strategy=strategy,
        lifecycles=lifecycles,
        requested_slots_remaining=(
            args.slots_remaining
        ),
        max_slot_distance=(
            args.max_slot_distance
        ),
    )

    print()
    print(
        "ORE Miner V3 — "
        "Strategy Experiment"
    )
    print(
        "==============================="
    )

    print(
        f"Strategy: "
        f"{result.strategy_name}"
    )

    print(
        f"Version: "
        f"{result.strategy_version}"
    )

    print(
        "Requested slots remaining: "
        f"{result.requested_slots_remaining}"
    )

    print(
        f"Maximum slot distance: "
        f"{result.max_slot_distance}"
    )

    print()
    print("Coverage")
    print("--------")

    print(
        f"Total rounds: "
        f"{result.total_rounds}"
    )

    print(
        f"Accepted/scored rounds: "
        f"{result.accepted_rounds}"
    )

    print(
        f"Rejected rounds: "
        f"{result.rejected_rounds}"
    )

    print()
    print("Strategy Activity")
    print("-----------------")

    print(
        f"Participate rounds: "
        f"{result.participate_rounds}"
    )

    print(
        f"Skip rounds: "
        f"{result.skip_rounds}"
    )

    print()
    print("Selection Performance")
    print("---------------------")

    print(
        f"Scored participations: "
        f"{result.scored_participations}"
    )

    print(
        f"Winning-square hits: "
        f"{result.winning_square_hits}"
    )

    if (
        result.winning_square_hit_rate
        is not None
    ):
        print(
            "Winning-square hit rate: "
            f"{result.winning_square_hit_rate:.2%}"
        )

    print()
    print("Motherlode")
    print("----------")

    print(
        f"Motherlode rounds: "
        f"{result.motherlode_rounds}"
    )

    print(
        "Motherlode winning-square "
        "selections: "
        f"{result.motherlode_selection_hits}"
    )

    reasons = Counter(
        rejected.reason
        for rejected
        in result.rejected
    )

    if reasons:
        print()
        print("Rejection Reasons")
        print("-----------------")

        for reason, count in (
            reasons.most_common()
        ):
            print(
                f"{count}: {reason}"
            )


if __name__ == "__main__":
    main()
