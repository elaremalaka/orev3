from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from orev3.historical.assembler import (
    assemble_rounds,
)
from orev3.historical.reader import (
    read_observer_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble and inspect ORE round "
            "lifecycles from Observer JSONL."
        )
    )

    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "Observer JSONL files to read."
        ),
    )

    parser.add_argument(
        "--round-id",
        type=int,
        default=None,
        help=(
            "Print detailed information "
            "for one round."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = read_observer_files(
        [
            Path(path)
            for path in args.paths
        ]
    )

    assembled = assemble_rounds(
        result.snapshots
    )

    coverage_counts = Counter(
        lifecycle.quality.coverage_status
        for lifecycle in assembled.rounds
    )

    regression_rounds = [
        lifecycle
        for lifecycle in assembled.rounds
        if (
            lifecycle.quality
            .rpc_slot_regression_count
            > 0
        )
    ]

    gap_rounds = [
        lifecycle
        for lifecycle in assembled.rounds
        if (
            lifecycle.quality
            .significant_gap_count
            > 0
        )
    ]

    initialization_rounds = [
        lifecycle
        for lifecycle in assembled.rounds
        if (
            lifecycle.quality
            .initialization_state_observed
        )
    ]

    finalized_rounds = [
        lifecycle
        for lifecycle in assembled.rounds
        if (
            lifecycle.quality
            .finalized_state_observed
        )
    ]

    print()
    print(
        "ORE Miner V3 — Round Lifecycle Assembler"
    )
    print(
        "======================================="
    )

    print(
        f"Normalized snapshots: "
        f"{assembled.total_snapshots}"
    )

    print(
        f"Assembled rounds: "
        f"{assembled.total_rounds}"
    )

    print(
        f"Malformed source records: "
        f"{len(result.malformed_records)}"
    )

    print()
    print("Coverage")
    print("--------")

    for status, count in sorted(
        coverage_counts.items()
    ):
        print(
            f"{status}: {count}"
        )

    print()
    print("Quality Flags")
    print("-------------")

    print(
        "Rounds with RPC slot regressions: "
        f"{len(regression_rounds)}"
    )

    print(
        "Rounds with significant gaps: "
        f"{len(gap_rounds)}"
    )

    print(
        "Rounds with initialization state: "
        f"{len(initialization_rounds)}"
    )

    print(
        "Rounds with observed finalized state: "
        f"{len(finalized_rounds)}"
    )

    if args.round_id is not None:
        matches = [
            lifecycle
            for lifecycle
            in assembled.rounds
            if (
                lifecycle.round_id
                == args.round_id
            )
        ]

        print()
        print(
            f"Round {args.round_id}"
        )
        print(
            "-" * (
                6
                + len(
                    str(args.round_id)
                )
            )
        )

        if not matches:
            print(
                "Round not found."
            )
            return

        lifecycle = matches[0]

        print(
            f"Observations: "
            f"{lifecycle.observation_count}"
        )

        print(
            f"Start slot: "
            f"{lifecycle.start_slot}"
        )

        print(
            f"End slot: "
            f"{lifecycle.end_slot}"
        )

        print(
            "First observed RPC slot: "
            f"{lifecycle.first_observed_rpc_slot}"
        )

        print(
            "Last observed RPC slot: "
            f"{lifecycle.last_observed_rpc_slot}"
        )

        print(
            "Coverage status: "
            f"{lifecycle.quality.coverage_status}"
        )

        print(
            "Collector sessions: "
            f"{lifecycle.collector_session_ids}"
        )

        print(
            "RPC slot regressions: "
            f"{lifecycle.quality.rpc_slot_regression_count}"
        )

        print(
            "Largest RPC slot regression: "
            f"{lifecycle.quality.largest_rpc_slot_regression}"
        )

        print(
            "Duplicate RPC slots: "
            f"{lifecycle.quality.duplicate_rpc_slot_count}"
        )

        print(
            "Maximum observation gap: "
            f"{lifecycle.quality.max_observation_gap_seconds:.3f}s"
        )

        print(
            "Significant gaps: "
            f"{lifecycle.quality.significant_gap_count}"
        )

        print(
            "Initialization observed: "
            f"{lifecycle.quality.initialization_state_observed}"
        )

        print(
            "Finalized state observed: "
            f"{lifecycle.quality.finalized_state_observed}"
        )

        if (
            lifecycle.finalized_outcome
            is not None
        ):
            print(
                "Winning square: "
                f"{lifecycle.finalized_outcome.winning_square}"
            )

            print(
                "Round Motherlode raw: "
                f"{lifecycle.finalized_outcome.round_motherlode}"
            )


if __name__ == "__main__":
    main()
