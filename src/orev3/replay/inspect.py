from __future__ import annotations

import argparse

from orev3.replay.engine import (
    select_by_slots_remaining,
    summarize_round,
)
from orev3.replay.loader import (
    load_round_index,
)


LAMPORTS_PER_SOL = 1_000_000_000
RAW_UNITS_PER_ORE = 100_000_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a point-in-time historical "
            "ORE replay state."
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
        help=(
            "Maximum acceptable replay distance "
            "in slots. Default: 3."
        ),
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

    summary = summarize_round(
        lifecycle
    )

    selection = (
        select_by_slots_remaining(
            lifecycle=lifecycle,
            requested_slots_remaining=(
                args.slots_remaining
            ),
            max_slot_distance=(
                args.max_slot_distance
            ),
        )
    )

    point = selection.replay_point

    print()
    print(
        "ORE Miner V3 — Replay Inspector"
    )
    print(
        "==============================="
    )

    print(
        f"Round ID: {summary.round_id}"
    )

    print(
        f"Coverage: "
        f"{summary.coverage_status}"
    )

    print(
        f"Round observations: "
        f"{summary.observation_count}"
    )

    print()
    print("Requested Replay Point")
    print("----------------------")

    print(
        "Requested slots remaining: "
        f"{selection.requested_slots_remaining}"
    )

    print(
        f"Selected RPC slot: "
        f"{point.rpc_slot}"
    )

    print(
        f"Actual slots remaining: "
        f"{point.slots_remaining}"
    )

    print(
        f"Exact match: "
        f"{selection.exact_slot_match}"
    )

    print(
        f"Slot distance: "
        f"{selection.slot_distance}"
    )

    print(
        f"Maximum allowed distance: "
        f"{selection.max_slot_distance}"
    )

    print(
        f"Within tolerance: "
        f"{selection.within_tolerance}"
    )

    print(
        f"Observed at UTC: "
        f"{point.observed_at_utc}"
    )

    print()
    print("Strategy-Visible State")
    print("----------------------")

    motherlode_ore = (
        point.treasury.motherlode
        / RAW_UNITS_PER_ORE
    )

    print(
        f"Motherlode: "
        f"{motherlode_ore:.6f} ORE"
    )

    print()
    print("Squares")
    print("-------")

    for square in range(25):
        deployed_sol = (
            point.round
            .deployed_lamports[
                square
            ]
            / LAMPORTS_PER_SOL
        )

        miners = (
            point.round
            .miner_counts[
                square
            ]
        )

        print(
            f"{square:02d}: "
            f"{deployed_sol:.9f} SOL | "
            f"{miners:>4} miners"
        )

    print()
    print(
        "Finalized outcome intentionally "
        "hidden from Replay state."
    )


if __name__ == "__main__":
    main()
