from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


EXPECTED_DATASET_SHA256 = (
    "9047141c99e2eb067bc0ca0bc5ee082ed141f91f16e25c23e125b062bf97983d"
)
EXPECTED_FOLDS = {
    "validation_1": (342395, 342438, 44),
    "validation_2": (342439, 342482, 44),
    "validation_3": (342483, 342526, 44),
    "final_holdout": (342527, 342570, 44),
}
FORBIDDEN_SELECTION_PATTERN = re.compile(
    r"(won|winner|winning|future|final|outcome|realized|pnl|profit|"
    r"reward_received|claimed|post_round)",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_forbidden_selection_fields(fields: Iterable[str]) -> None:
    forbidden = sorted(
        str(field) for field in fields if FORBIDDEN_SELECTION_PATTERN.search(str(field))
    )
    if forbidden:
        raise ValueError(
            "Outcome/future fields are forbidden during selection: "
            + ", ".join(forbidden)
        )


def validate_selected_squares(
    selected_squares: Iterable[int],
    *,
    square_count: int = 25,
) -> tuple[int, ...]:
    selected = tuple(int(value) for value in selected_squares)
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate square selection")
    if any(value < 0 or value >= square_count for value in selected):
        raise ValueError("Selected square does not exist")
    return selected


def validate_canonical_inputs(
    *,
    dataset_path: Path,
    manifest_path: Path,
    feature_sets_path: Path,
    predictions: pd.DataFrame,
) -> dict[str, Any]:
    digest = sha256_file(dataset_path)
    if digest != EXPECTED_DATASET_SHA256:
        raise ValueError(f"Canonical dataset hash mismatch: {digest}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    feature_sets = json.loads(feature_sets_path.read_text(encoding="utf-8"))
    if len(manifest["feature_columns"]) != 72:
        raise ValueError("Expected 72 manifest features")
    if feature_sets["all_72"]["features"] != manifest["feature_columns"]:
        raise ValueError("RFC-004 all-72 feature configuration changed")
    if feature_sets["conservative_deduplicated"]["feature_count"] != 52:
        raise ValueError("RFC-004 frozen conservative feature count changed")
    required = {
        "fold",
        "split_kind",
        "strategy",
        "feature_set",
        "round_id",
        "observation_index",
        "outcome_source",
        "winning_square",
        "selected_square",
        "winner_rank",
    }
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError("Prediction columns missing: " + ", ".join(missing))
    numeric = predictions[
        ["round_id", "observation_index", "winning_square", "selected_square", "winner_rank"]
    ].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Predictions contain non-finite required values")
    if not numeric["winning_square"].between(0, 24).all():
        raise ValueError("Invalid winning square in predictions")
    if not numeric["selected_square"].between(0, 24).all():
        raise ValueError("Invalid selected square in predictions")
    if not numeric["winner_rank"].between(1, 25).all():
        raise ValueError("Invalid winner rank in predictions")
    for fold, (minimum, maximum, count) in EXPECTED_FOLDS.items():
        rounds = sorted(
            predictions.loc[predictions["fold"].eq(fold), "round_id"].unique()
        )
        if (
            len(rounds) != count
            or int(rounds[0]) != minimum
            or int(rounds[-1]) != maximum
        ):
            raise ValueError(f"RFC-004 fold boundary changed: {fold}")
    fold_sets = [
        set(predictions.loc[predictions["fold"].eq(name), "round_id"].unique())
        for name in EXPECTED_FOLDS
    ]
    for index, first in enumerate(fold_sets):
        for second in fold_sets[index + 1 :]:
            if first & second:
                raise ValueError("Out-of-sample fold rounds overlap")
    return {
        "dataset_sha256": digest,
        "feature_count": 72,
        "conservative_feature_count": 52,
        "folds": EXPECTED_FOLDS,
    }
