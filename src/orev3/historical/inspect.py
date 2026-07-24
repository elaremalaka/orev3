from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from orev3.historical.reader import (
    read_observer_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect raw ORE Observer JSONL files "
            "through the Historical Dataset reader."
        )
    )

    parser.add_argument(
        "paths",
        nargs="+",
        help=(
            "Observer JSONL files to read."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    paths = [
        Path(path)
        for path in args.paths
    ]

    result = read_observer_files(
        paths
    )

    schema_counts = Counter(
        snapshot.source_schema_version
        for snapshot in result.snapshots
    )

    session_counts = Counter(
        snapshot.collector_session_id
        or "schema-v1-no-session"
        for snapshot in result.snapshots
    )

    round_ids = {
        snapshot.board.round_id
        for snapshot in result.snapshots
    }

    print()
    print(
        "ORE Miner V3 — Historical Reader"
    )
    print(
        "================================"
    )

    print(
        f"Files read: {result.files_read}"
    )

    print(
        f"Lines read: {result.lines_read}"
    )

    print(
        "Valid normalized snapshots: "
        f"{len(result.snapshots)}"
    )

    print(
        "Malformed/unsupported records: "
        f"{len(result.malformed_records)}"
    )

    print()
    print("Schema Versions")
    print("---------------")

    for schema, count in sorted(
        schema_counts.items()
    ):
        print(
            f"Schema {schema}: {count}"
        )

    print()
    print("Rounds")
    print("------")

    print(
        f"Distinct rounds: {len(round_ids)}"
    )

    if round_ids:
        print(
            f"First round ID: {min(round_ids)}"
        )

        print(
            f"Last round ID: {max(round_ids)}"
        )

    print()
    print("Collector Sessions")
    print("------------------")

    print(
        f"Distinct sessions: "
        f"{len(session_counts)}"
    )

    for session_id, count in (
        session_counts.most_common()
    ):
        print(
            f"{session_id}: {count}"
        )

    if result.malformed_records:
        print()
        print("Malformed Records")
        print("-----------------")

        for record in (
            result.malformed_records[:20]
        ):
            print(
                f"{record.source_file}:"
                f"{record.source_line_number} "
                f"{record.error_type}: "
                f"{record.error_message}"
            )


if __name__ == "__main__":
    main()
