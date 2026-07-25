from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

from orev3.features import create_default_pipeline
from orev3.features.context import FeatureContext
from orev3.features.types import (
    BoardSnapshot,
    SquareSnapshot,
)


DEFAULT_INPUT = Path(
    "data/research/observation_dataset_v1.csv"
)
DEFAULT_OUTPUT = Path(
    "data/research/square_feature_dataset_v1.csv"
)
DEFAULT_MANIFEST = Path(
    "data/research/square_feature_dataset_v1.manifest.json"
)

SQUARE_COUNT = 25

IDENTITY_COLUMNS = (
    "round_id",
    "observation_index",
    "round_observation_count",
    "round_progress",
    "slots_remaining",
    "square_index",
)

LABEL_COLUMNS = (
    "won",
    "winning_square",
    "outcome_source",
)


def parse_optional_int(value: str) -> int | None:
    value = value.strip()

    if not value:
        return None

    return int(value)


def require_column(
    row: dict[str, str],
    name: str,
) -> str:
    if name not in row:
        raise ValueError(
            f"Required dataset column is missing: {name}"
        )

    return row[name]


def read_round_groups(
    reader: csv.DictReader,
) -> Iterator[list[dict[str, str]]]:
    current_round_id: int | None = None
    current_rows: list[dict[str, str]] = []
    completed_round_ids: set[int] = set()

    for row in reader:
        round_id = int(
            require_column(row, "round_id")
        )

        if current_round_id is None:
            current_round_id = round_id

        if round_id != current_round_id:
            completed_round_ids.add(current_round_id)

            if round_id in completed_round_ids:
                raise ValueError(
                    "Input dataset is not grouped by round_id; "
                    f"round {round_id} appeared more than once"
                )

            yield current_rows
            current_rows = []
            current_round_id = round_id

        current_rows.append(row)

    if current_rows:
        yield current_rows


def build_observations(
    round_rows: list[dict[str, str]],
) -> list[tuple[BoardSnapshot, dict[str, Any]]]:
    grouped: dict[
        int,
        list[dict[str, str]],
    ] = {}

    for row in round_rows:
        observation_index = int(
            row["observation_index"]
        )
        grouped.setdefault(
            observation_index,
            [],
        ).append(row)

    observations: list[
        tuple[BoardSnapshot, dict[str, Any]]
    ] = []

    expected_indices = list(range(len(grouped)))
    actual_indices = sorted(grouped)

    if actual_indices != expected_indices:
        raise ValueError(
            "Observation indices are not contiguous: "
            f"expected={expected_indices}, "
            f"actual={actual_indices}"
        )

    for observation_index in actual_indices:
        rows = grouped[observation_index]

        if len(rows) != SQUARE_COUNT:
            raise ValueError(
                "Expected 25 rows per observation; "
                f"round={rows[0]['round_id']} "
                f"observation={observation_index} "
                f"rows={len(rows)}"
            )

        rows.sort(
            key=lambda row: int(row["square_index"])
        )

        square_indices = [
            int(row["square_index"])
            for row in rows
        ]

        if square_indices != list(range(SQUARE_COUNT)):
            raise ValueError(
                "Invalid square indices; "
                f"round={rows[0]['round_id']} "
                f"observation={observation_index}"
            )

        squares = tuple(
            SquareSnapshot(
                observation_index=observation_index,
                miner_count=int(row["miner_count"]),
                deployed_lamports=int(
                    row["deployed_lamports"]
                ),
                reward_raw=int(row["reward_raw"]),
                mass=int(row["mass"]),
            )
            for row in rows
        )

        first = rows[0]

        board = BoardSnapshot(
            round_id=int(first["round_id"]),
            observation_index=observation_index,
            observation_count=int(
                first["round_observation_count"]
            ),
            slots_remaining=parse_optional_int(
                first["slots_remaining"]
            ),
            squares=squares,
        )

        metadata = {
            "winning_square": int(
                first["winning_square"]
            ),
            "outcome_source": first[
                "finalized_outcome_source"
            ],
        }

        observations.append((board, metadata))

    return observations


def serialize_value(
    value: object,
) -> object:
    if value is None:
        return ""

    return value


def write_round_features(
    writer: csv.DictWriter,
    observations: list[
        tuple[BoardSnapshot, dict[str, Any]]
    ],
    pipeline: Any,
) -> int:
    square_histories: list[
        list[SquareSnapshot]
    ] = [
        []
        for _ in range(SQUARE_COUNT)
    ]

    rows_written = 0

    for board, metadata in observations:
        for square_index in range(SQUARE_COUNT):
            current_square = board.squares[
                square_index
            ]
            square_histories[
                square_index
            ].append(current_square)

            context = FeatureContext(
                board=board,
                square_index=square_index,
                square_history=tuple(
                    square_histories[square_index]
                ),
            )

            feature_values = pipeline.compute(context)

            output_row = {
                "round_id": board.round_id,
                "observation_index": (
                    board.observation_index
                ),
                "round_observation_count": (
                    board.observation_count
                ),
                "round_progress": (
                    context.round_progress
                ),
                "slots_remaining": (
                    board.slots_remaining
                ),
                "square_index": square_index,
                **feature_values,
                "won": int(
                    square_index
                    == metadata["winning_square"]
                ),
                "winning_square": metadata[
                    "winning_square"
                ],
                "outcome_source": metadata[
                    "outcome_source"
                ],
            }

            writer.writerow(
                {
                    key: serialize_value(value)
                    for key, value
                    in output_row.items()
                }
            )
            rows_written += 1

    return rows_written


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def build_dataset(
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    pipeline = create_default_pipeline()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    manifest_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_columns = (
        pipeline.registry.output_columns
    )
    fieldnames = (
        *IDENTITY_COLUMNS,
        *feature_columns,
        *LABEL_COLUMNS,
    )

    round_count = 0
    observation_count = 0
    row_count = 0

    with input_path.open(
        newline="",
        encoding="utf-8",
    ) as input_handle, output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output_handle:
        reader = csv.DictReader(input_handle)
        writer = csv.DictWriter(
            output_handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for round_rows in read_round_groups(reader):
            observations = build_observations(
                round_rows
            )

            row_count += write_round_features(
                writer,
                observations,
                pipeline,
            )
            round_count += 1
            observation_count += len(observations)

            if round_count % 50 == 0:
                print(
                    f"Processed {round_count:,} rounds, "
                    f"{observation_count:,} observations, "
                    f"{row_count:,} rows"
                )

    expected_rows = (
        observation_count * SQUARE_COUNT
    )

    if row_count != expected_rows:
        raise ValueError(
            "Feature row invariant failed: "
            f"rows={row_count}, "
            f"expected={expected_rows}"
        )

    runtime_seconds = (
        time.perf_counter() - started_at
    )

    manifest = {
        "schema_version": 1,
        "dataset_type": (
            "square_temporal_feature_dataset"
        ),
        "input_path": str(input_path),
        "output_path": str(output_path),
        "round_count": round_count,
        "observation_count": observation_count,
        "row_count": row_count,
        "square_count": SQUARE_COUNT,
        "identity_columns": list(
            IDENTITY_COLUMNS
        ),
        "feature_columns": list(
            feature_columns
        ),
        "label_columns": list(LABEL_COLUMNS),
        "feature_registry": (
            pipeline.registry.manifest()
        ),
        "output_sha256": sha256_file(
            output_path
        ),
        "runtime_seconds": runtime_seconds,
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the RFC-003B square-level "
            "temporal feature dataset."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {args.input}"
        )

    manifest = build_dataset(
        input_path=args.input,
        output_path=args.output,
        manifest_path=args.manifest,
    )

    print()
    print("ORE Miner V3 — Square Feature Dataset")
    print("=====================================")
    print(
        f"Rounds: {manifest['round_count']:,}"
    )
    print(
        "Observations: "
        f"{manifest['observation_count']:,}"
    )
    print(f"Rows: {manifest['row_count']:,}")
    print(
        "Features: "
        f"{len(manifest['feature_columns']):,}"
    )
    print(
        "Runtime: "
        f"{manifest['runtime_seconds']:.3f} seconds"
    )
    print(f"Dataset: {args.output}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()
