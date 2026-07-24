from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from orev3.historical.assembler import (
    assemble_rounds,
)
from orev3.historical.enricher import (
    enrich_rounds,
)
from orev3.historical.models import (
    HistoricalDatasetManifest,
)
from orev3.historical.persistence import (
    lifecycle_to_index_record,
    write_manifest,
    write_round_index,
)
from orev3.historical.reader import (
    read_observer_files,
)
from orev3.observer.rpc import (
    SolanaRpcClient,
)


DEFAULT_OUTPUT = (
    "data/derived/"
    "round_lifecycles_v1.jsonl"
)

DEFAULT_MANIFEST = (
    "data/derived/"
    "round_lifecycles_v1.manifest.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the persistent ORE Miner V3 "
            "historical round lifecycle dataset."
        )
    )

    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "Raw Observer JSONL files."
        ),
    )

    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help=(
            "Delay between historical round "
            "enrichment attempts. Default: 0.25s"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_paths = [
        Path(path)
        for path in args.paths
    ]

    print()
    print(
        "ORE Miner V3 — "
        "Historical Dataset Builder"
    )
    print(
        "======================================"
    )

    print(
        "Reading raw snapshots..."
    )

    read_result = (
        read_observer_files(
            input_paths
        )
    )

    print(
        f"Normalized snapshots: "
        f"{len(read_result.snapshots)}"
    )

    print(
        f"Malformed source records: "
        f"{len(read_result.malformed_records)}"
    )

    print(
        "Assembling round lifecycles..."
    )

    assembled = assemble_rounds(
        read_result.snapshots
    )

    before = Counter(
        lifecycle
        .finalized_outcome_source
        or "missing"
        for lifecycle
        in assembled.rounds
    )

    print(
        f"Assembled rounds: "
        f"{assembled.total_rounds}"
    )

    print(
        f"Observed outcomes: "
        f"{before['observed']}"
    )

    print(
        f"Missing outcomes before enrichment: "
        f"{before['missing']}"
    )

    rpc = SolanaRpcClient()

    try:
        print(
            "Enriching missing finalized outcomes..."
        )

        (
            enriched_rounds,
            stats,
        ) = enrich_rounds(
            rpc=rpc,
            lifecycles=(
                assembled.rounds
            ),
            limit=None,
            delay_seconds=(
                args.delay
            ),
        )

    finally:
        rpc.close()

    after = Counter(
        lifecycle
        .finalized_outcome_source
        or "missing"
        for lifecycle
        in enriched_rounds
    )

    print(
        f"Newly enriched outcomes: "
        f"{stats.enriched}"
    )

    print(
        f"Unavailable/not finalized: "
        f"{stats.unavailable}"
    )

    print(
        f"Failed enrichment attempts: "
        f"{stats.failed}"
    )

    print(
        f"Missing outcomes after enrichment: "
        f"{after['missing']}"
    )

    records = [
        lifecycle_to_index_record(
            lifecycle
        )
        for lifecycle
        in enriched_rounds
    ]

    output_path = write_round_index(
        records=records,
        output_path=args.output,
    )

    manifest = HistoricalDatasetManifest(
        generated_at_utc=datetime.now(
            timezone.utc
        ),
        input_files=[
            str(path)
            for path in input_paths
        ],
        lines_read=(
            read_result.lines_read
        ),
        normalized_snapshots=len(
            read_result.snapshots
        ),
        malformed_source_records=len(
            read_result.malformed_records
        ),
        total_rounds=len(
            records
        ),
        observed_outcomes=(
            after["observed"]
        ),
        enriched_outcomes=(
            after["enriched"]
        ),
        missing_outcomes=(
            after["missing"]
        ),
        enrichment_unavailable=(
            stats.unavailable
        ),
        enrichment_failed=(
            stats.failed
        ),
    )

    manifest_path = write_manifest(
        manifest=manifest,
        output_path=args.manifest,
    )

    print()
    print("Historical Dataset Built")
    print("------------------------")

    print(
        f"Round records: "
        f"{len(records)}"
    )

    print(
        f"Observed outcomes: "
        f"{after['observed']}"
    )

    print(
        f"Enriched outcomes: "
        f"{after['enriched']}"
    )

    print(
        f"Missing outcomes: "
        f"{after['missing']}"
    )

    print(
        f"Dataset: {output_path}"
    )

    print(
        f"Manifest: {manifest_path}"
    )


if __name__ == "__main__":
    main()
