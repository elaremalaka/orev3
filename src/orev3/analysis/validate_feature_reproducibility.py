from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from orev3.datasets.build_square_feature_dataset import (
    IDENTITY_COLUMNS,
    LABEL_COLUMNS,
    build_observations,
    read_round_groups,
)
from orev3.features import (
    create_default_pipeline,
    create_default_registry,
)
from orev3.features.context import FeatureContext


FORBIDDEN_PREDICTIVE_COLUMNS = frozenset(
    {
        "won",
        "winning_square",
        "outcome_source",
        "mass",
        "finalized_outcome_source",
    }
)

NONDETERMINISTIC_MANIFEST_FIELDS = frozenset(
    {
        "output_path",
        "runtime_seconds",
        "performance_profile",
    }
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def normalized_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in NONDETERMINISTIC_MANIFEST_FIELDS
    }


def _numeric_feature_frame(
    frame: pd.DataFrame,
    feature_columns: tuple[str, ...],
) -> pd.DataFrame:
    numeric = pd.DataFrame(index=frame.index)

    for column in feature_columns:
        normalized = (
            frame[column]
            .astype("string")
            .str.strip()
            .str.lower()
            .replace({"true": "1", "false": "0"})
        )
        numeric[column] = pd.to_numeric(
            normalized,
            errors="coerce",
        )

    return numeric


def validate_feature_dataset(
    dataset_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registry_columns = create_default_registry().output_columns
    feature_columns = tuple(manifest["feature_columns"])
    expected_columns = (
        *IDENTITY_COLUMNS,
        *registry_columns,
        *LABEL_COLUMNS,
    )
    frame = pd.read_csv(dataset_path, low_memory=False)
    actual_columns = tuple(frame.columns)
    keys = ["round_id", "observation_index", "square_index"]
    duplicate_key_count = int(frame.duplicated(keys).sum())
    observation_groups = frame.groupby(
        ["round_id", "observation_index"],
        sort=False,
    )
    observation_sizes = observation_groups.size()
    square_sets = observation_groups["square_index"].agg(
        lambda values: frozenset(values)
    )
    expected_square_set = frozenset(range(manifest["square_count"]))
    invalid_observations = int(
        (
            observation_sizes.ne(manifest["square_count"])
            | square_sets.ne(expected_square_set)
        ).sum()
    )
    numeric = _numeric_feature_frame(frame, feature_columns)
    missing_feature_values = {
        column: int(frame[column].isna().sum())
        for column in feature_columns
        if frame[column].isna().any()
    }
    non_finite_values = {
        column: int(
            (
                numeric[column].isna()
                | ~numeric[column].map(math.isfinite)
            ).sum()
        )
        for column in feature_columns
        if (
            numeric[column].isna()
            | ~numeric[column].map(math.isfinite)
        ).any()
    }
    forbidden = sorted(
        set(feature_columns) & FORBIDDEN_PREDICTIVE_COLUMNS
    )
    unexpected_columns = sorted(set(actual_columns) - set(expected_columns))
    missing_columns = sorted(set(expected_columns) - set(actual_columns))
    errors = {
        "duplicate_key_count": duplicate_key_count,
        "invalid_observation_count": invalid_observations,
        "column_order_mismatch": actual_columns != expected_columns,
        "registry_manifest_feature_mismatch": (
            feature_columns != registry_columns
        ),
        "unexpected_columns": unexpected_columns,
        "missing_columns": missing_columns,
        "missing_feature_values": missing_feature_values,
        "non_finite_feature_values": non_finite_values,
        "forbidden_predictive_columns": forbidden,
        "manifest_row_count_mismatch": len(frame) != manifest["row_count"],
        "manifest_observation_count_mismatch": (
            len(observation_sizes) != manifest["observation_count"]
        ),
        "manifest_round_count_mismatch": (
            frame["round_id"].nunique() != manifest["round_count"]
        ),
        "manifest_hash_mismatch": (
            sha256_file(dataset_path) != manifest["output_sha256"]
        ),
    }

    return {
        "passed": not any(errors.values()),
        "dataset": str(dataset_path),
        "manifest": str(manifest_path),
        "row_count": len(frame),
        "column_count": len(actual_columns),
        "round_count": int(frame["round_id"].nunique()),
        "observation_count": len(observation_sizes),
        "feature_count": len(feature_columns),
        "key_order_is_sorted": bool(
            frame[keys].equals(
                frame[keys].sort_values(keys).reset_index(drop=True)
            )
        ),
        "identifiers": list(IDENTITY_COLUMNS),
        "predictive_features": list(feature_columns),
        "labels": list(LABEL_COLUMNS),
        "errors": errors,
    }


def compare_feature_builds(
    first_dataset: Path,
    first_manifest: Path,
    second_dataset: Path,
    second_manifest: Path,
) -> dict[str, Any]:
    first_hash = sha256_file(first_dataset)
    second_hash = sha256_file(second_dataset)
    byte_identical = first_hash == second_hash
    first_metadata = json.loads(first_manifest.read_text(encoding="utf-8"))
    second_metadata = json.loads(second_manifest.read_text(encoding="utf-8"))
    first_header = tuple(pd.read_csv(first_dataset, nrows=0).columns)
    second_header = tuple(pd.read_csv(second_dataset, nrows=0).columns)
    row_counts = (
        int(first_metadata["row_count"]),
        int(second_metadata["row_count"]),
    )
    value_equal = byte_identical
    key_equal = byte_identical

    if not byte_identical:
        value_equal = True
        key_equal = True

        for first_chunk, second_chunk in zip(
            pd.read_csv(first_dataset, chunksize=50_000),
            pd.read_csv(second_dataset, chunksize=50_000),
            strict=True,
        ):
            if not first_chunk.equals(second_chunk):
                value_equal = False

            keys = ["round_id", "observation_index", "square_index"]

            if not first_chunk[keys].equals(second_chunk[keys]):
                key_equal = False

    substantive_manifest_equal = (
        normalized_manifest(first_metadata)
        == normalized_manifest(second_metadata)
    )

    return {
        "passed": all(
            (
                row_counts[0] == row_counts[1],
                first_header == second_header,
                key_equal,
                value_equal,
                substantive_manifest_equal,
            )
        ),
        "row_counts": list(row_counts),
        "column_counts": [len(first_header), len(second_header)],
        "column_order_equal": first_header == second_header,
        "key_order_equal": key_equal,
        "file_hashes": [first_hash, second_hash],
        "file_hashes_equal": byte_identical,
        "value_by_value_equal": value_equal,
        "value_equality_method": (
            "byte-identical CSV"
            if byte_identical
            else "chunked pandas equality"
        ),
        "substantive_manifest_equal": substantive_manifest_equal,
        "ignored_manifest_fields": sorted(
            NONDETERMINISTIC_MANIFEST_FIELDS
        ),
    }


def _parse_batch_value(
    raw: str,
    direct: int | float | bool | None,
) -> int | float | bool | None:
    if direct is None:
        return None if raw == "" else raw
    if isinstance(direct, bool):
        return raw.strip().lower() == "true"
    if isinstance(direct, int):
        return int(raw)
    return float(raw)


def validate_batch_direct_parity(
    observation_dataset: Path,
    feature_dataset: Path,
) -> dict[str, Any]:
    selected_observations: list[tuple[Any, dict[str, Any]]] | None = None

    with observation_dataset.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        reader = csv.DictReader(handle)

        for round_rows in read_round_groups(reader):
            observations = build_observations(round_rows)

            if len(observations) >= 4:
                selected_observations = observations
                break

    if selected_observations is None:
        raise ValueError("No round has sufficient observations for parity")

    boards = [board for board, _ in selected_observations]
    selected_indices = sorted(
        {
            0,
            1,
            3,
            len(selected_observations) - 1,
        }
    )
    round_id = boards[0].round_id
    batch_rows: dict[tuple[int, int], dict[str, str]] = {}

    with feature_dataset.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            if int(row["round_id"]) != round_id:
                continue

            observation_index = int(row["observation_index"])

            if observation_index in selected_indices:
                batch_rows[
                    (observation_index, int(row["square_index"]))
                ] = row

    pipeline = create_default_pipeline()
    feature_columns = pipeline.registry.output_columns
    mismatch_count = 0
    compared_values = 0
    maximum_float_difference = 0.0

    for observation_index in selected_indices:
        board_history = tuple(boards[: observation_index + 1])

        for square_index in range(25):
            context = FeatureContext(
                board=boards[observation_index],
                square_index=square_index,
                square_history=tuple(
                    board.squares[square_index]
                    for board in board_history
                ),
                board_history=board_history,
            )
            direct = pipeline.compute(context)
            batch = batch_rows[(observation_index, square_index)]

            for column in feature_columns:
                batch_value = _parse_batch_value(
                    batch[column],
                    direct[column],
                )
                direct_value = direct[column]
                compared_values += 1

                if isinstance(direct_value, float):
                    difference = abs(
                        float(batch_value) - direct_value
                    )
                    maximum_float_difference = max(
                        maximum_float_difference,
                        difference,
                    )

                    if not math.isclose(
                        float(batch_value),
                        direct_value,
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    ):
                        mismatch_count += 1
                elif batch_value != direct_value:
                    mismatch_count += 1

    return {
        "passed": mismatch_count == 0,
        "round_id": round_id,
        "selected_observation_indices": selected_indices,
        "representative_cases": {
            "first_observation": 0,
            "one_prior_observation": 1,
            "sufficient_rolling_history": 3,
            "late_round_observation": len(selected_observations) - 1,
            "missing_index_gap_present_in_canonical_round": False,
        },
        "square_rows_compared": len(selected_indices) * 25,
        "feature_values_compared": compared_values,
        "mismatch_count": mismatch_count,
        "maximum_float_difference": maximum_float_difference,
        "floating_point_tolerance": {
            "relative": 1e-12,
            "absolute": 1e-12,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate RFC-003B feature build reproducibility."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--compare-dataset", type=Path)
    parser.add_argument("--compare-manifest", type=Path)
    parser.add_argument("--observation-dataset", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report: dict[str, Any] = {
        "integrity": validate_feature_dataset(
            args.dataset,
            args.manifest,
        )
    }

    if args.compare_dataset and args.compare_manifest:
        report["reproducibility"] = compare_feature_builds(
            args.dataset,
            args.manifest,
            args.compare_dataset,
            args.compare_manifest,
        )

    if args.observation_dataset:
        report["batch_direct_parity"] = validate_batch_direct_parity(
            args.observation_dataset,
            args.dataset,
        )

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")

    if not all(section["passed"] for section in report.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
