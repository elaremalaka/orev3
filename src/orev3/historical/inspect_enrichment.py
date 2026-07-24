from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from orev3.historical.assembler import (
    assemble_rounds,
)
from orev3.historical.enricher import (
    enrich_rounds,
)
from orev3.historical.reader import (
    read_observer_files,
)
from orev3.observer.rpc import (
    SolanaRpcClient,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test finalized outcome enrichment "
            "for historical ORE rounds."
        )
    )

    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "Observer JSONL files."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help=(
            "Maximum number of missing outcomes "
            "to fetch. Default: 10."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    read_result = (
        read_observer_files(
            [
                Path(path)
                for path
                in args.paths
            ]
        )
    )

    assembled = assemble_rounds(
        read_result.snapshots
    )

    before_sources = Counter(
        lifecycle
        .finalized_outcome_source
        or "missing"
        for lifecycle
        in assembled.rounds
    )

    rpc = SolanaRpcClient()

    try:
        (
            enriched_rounds,
            stats,
        ) = enrich_rounds(
            rpc=rpc,
            lifecycles=(
                assembled.rounds
            ),
            limit=args.limit,
        )

    finally:
        rpc.close()

    after_sources = Counter(
        lifecycle
        .finalized_outcome_source
        or "missing"
        for lifecycle
        in enriched_rounds
    )

    print()
    print(
        "ORE Miner V3 — "
        "Finalized Outcome Enricher"
    )
    print(
        "===================================="
    )

    print(
        f"Total rounds: "
        f"{stats.total_rounds}"
    )

    print(
        f"Already finalized: "
        f"{stats.already_finalized}"
    )

    print(
        f"Newly enriched: "
        f"{stats.enriched}"
    )

    print(
        f"Unavailable/not finalized: "
        f"{stats.unavailable}"
    )

    print(
        f"Failed: "
        f"{stats.failed}"
    )

    print()
    print("Outcome Sources Before")
    print("----------------------")

    for source, count in sorted(
        before_sources.items()
    ):
        print(
            f"{source}: {count}"
        )

    print()
    print("Outcome Sources After")
    print("---------------------")

    for source, count in sorted(
        after_sources.items()
    ):
        print(
            f"{source}: {count}"
        )

    newly_enriched = [
        lifecycle
        for lifecycle
        in enriched_rounds
        if (
            lifecycle
            .finalized_outcome_source
            == "enriched"
        )
    ]

    if newly_enriched:
        print()
        print("Newly Enriched Rounds")
        print("---------------------")

        for lifecycle in (
            newly_enriched[:20]
        ):
            outcome = (
                lifecycle
                .finalized_outcome
            )

            print(
                f"round="
                f"{lifecycle.round_id} "
                f"winner="
                f"{outcome.winning_square} "
                f"motherlode_raw="
                f"{outcome.round_motherlode} "
                f"top_miner="
                f"{outcome.top_miner}"
            )


if __name__ == "__main__":
    main()
