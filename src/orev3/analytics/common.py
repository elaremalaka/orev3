from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

EXPECTED_SQUARES = 25
REQUIRED_COLUMNS = {
    "schema_version",
    "feature_version",
    "dataset_version",
    "round_id",
    "square_index",
    "board_row",
    "board_column",
    "is_corner",
    "is_edge",
    "is_center",
    "distance_from_center",
    "miner_count",
    "total_board_miners",
    "miner_share",
    "miner_rank_ascending",
    "miner_rank_descending",
    "is_empty",
    "is_bottom4_miners",
    "is_top4_miners",
    "orthogonal_neighbor_count",
    "orthogonal_neighbor_miners",
    "orthogonal_neighbor_mean_miners",
    "winning_square",
    "won",
}


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    path: Path
    sha256: str
    rows: int
    rounds: int
    columns: int
    schema_versions: tuple[str, ...]
    feature_versions: tuple[str, ...]
    dataset_versions: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_square_dataset(path: str | Path) -> pd.DataFrame:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset does not exist: {dataset_path}")

    frame = pd.read_csv(dataset_path)
    validate_square_dataset(frame)
    return frame


def validate_square_dataset(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    if frame.empty:
        raise ValueError("Dataset contains no rows.")

    duplicate_keys = frame.duplicated(["round_id", "square_index"])
    if duplicate_keys.any():
        count = int(duplicate_keys.sum())
        raise ValueError(
            "Dataset contains duplicate (round_id, square_index) rows: "
            f"{count}"
        )

    square_counts = frame.groupby("round_id")["square_index"].nunique()
    invalid_square_counts = square_counts[square_counts != EXPECTED_SQUARES]
    if not invalid_square_counts.empty:
        examples = invalid_square_counts.head().to_dict()
        raise ValueError(
            "Every round must contain exactly 25 unique squares. "
            f"Invalid examples: {examples}"
        )

    expected_squares = set(range(EXPECTED_SQUARES))
    invalid_rounds: list[int] = []
    for round_id, group in frame.groupby("round_id", sort=False):
        if set(group["square_index"].astype(int)) != expected_squares:
            invalid_rounds.append(int(round_id))
            if len(invalid_rounds) >= 5:
                break
    if invalid_rounds:
        raise ValueError(
            "Rounds do not contain square indexes 0 through 24: "
            f"{invalid_rounds}"
        )

    win_counts = frame.groupby("round_id")["won"].sum()
    invalid_win_counts = win_counts[win_counts != 1]
    if not invalid_win_counts.empty:
        examples = invalid_win_counts.head().to_dict()
        raise ValueError(
            "Every round must contain exactly one winning row. "
            f"Invalid examples: {examples}"
        )

    winner_consistency = frame.loc[frame["won"], ["square_index", "winning_square"]]
    if not (
        winner_consistency["square_index"].astype(int)
        == winner_consistency["winning_square"].astype(int)
    ).all():
        raise ValueError(
            "At least one row marked won=True does not match winning_square."
        )

    invalid_square_indexes = ~frame["square_index"].between(0, 24)
    if invalid_square_indexes.any():
        values = sorted(frame.loc[invalid_square_indexes, "square_index"].unique())
        raise ValueError(f"Invalid square indexes: {values}")


def dataset_metadata(
    frame: pd.DataFrame,
    path: str | Path,
) -> DatasetMetadata:
    dataset_path = Path(path)
    return DatasetMetadata(
        path=dataset_path,
        sha256=sha256_file(dataset_path),
        rows=len(frame),
        rounds=int(frame["round_id"].nunique()),
        columns=len(frame.columns),
        schema_versions=tuple(
            sorted(frame["schema_version"].dropna().astype(str).unique())
        ),
        feature_versions=tuple(
            sorted(frame["feature_version"].dropna().astype(str).unique())
        ),
        dataset_versions=tuple(
            sorted(frame["dataset_version"].dropna().astype(str).unique())
        ),
    )


def ensure_directories(*paths: str | Path) -> tuple[Path, ...]:
    resolved: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        path.mkdir(parents=True, exist_ok=True)
        resolved.append(path)
    return tuple(resolved)


def write_csv(frame: pd.DataFrame, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return output


def write_text(content: str, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content.rstrip() + "\n", encoding="utf-8")
    return output


def json_value(value: object) -> str:
    return json.dumps(value, sort_keys=True, default=str)
