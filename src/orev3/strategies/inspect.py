from __future__ import annotations

import argparse

from orev3.replay.loader import (
    load_round_index,
)
from orev3.strategies.least_crowded import (
    LeastCrowdedTop4Strategy,
)
from orev3.strategies.runner import (
    evaluate_strategy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect one historical "
            "Strategy Lab evaluation."
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
        "--round-id",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--slots-remaining",
        type=int,
        required=True,
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

    lifecycle = index.get(
        args.round_id
    )

    if lifecycle is None:
        raise SystemExit(
            f"Round {args.round_id} "
            "not found."
        )

    strategy = (
        LeastCrowdedTop4Strategy()
    )

    evaluation = (
        evaluate_strategy(
            strategy=strategy,
            lifecycle=lifecycle,
            requested_slots_remaining=(
                args.slots_remaining
            ),
            max_slot_distance=(
                args.max_slot_distance
            ),
        )
    )

    print()
    print(
        "ORE Miner V3 — Strategy Lab"
    )
    print(
        "==========================="
    )

    print(
        f"Round ID: "
        f"{evaluation.round_id}"
    )

    print(
        "Requested slots remaining: "
        f"{evaluation.requested_slots_remaining}"
    )

    print(
        "Actual slots remaining: "
        f"{evaluation.actual_slots_remaining}"
    )

    print(
        "Replay slot distance: "
        f"{evaluation.replay_slot_distance}"
    )

    print(
        "Replay within tolerance: "
        f"{evaluation.replay_within_tolerance}"
    )

    print()
    print("Strategy")
    print("--------")

    print(
        f"Name: "
        f"{evaluation.decision.strategy_name}"
    )

    print(
        f"Version: "
        f"{evaluation.decision.strategy_version}"
    )

    print(
        f"Action: "
        f"{evaluation.decision.action}"
    )

    print(
        f"Reason: "
        f"{evaluation.decision.reason}"
    )

    print()
    print("Allocations")
    print("-----------")

    for allocation in (
        evaluation
        .decision
        .allocations
    ):
        print(
            f"Square "
            f"{allocation.square:02d}: "
            f"weight="
            f"{allocation.weight:.4f}"
        )

    print()
    print(
        "Finalized outcome was not "
        "provided to the strategy."
    )


if __name__ == "__main__":
    main()
