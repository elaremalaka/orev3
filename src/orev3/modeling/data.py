from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_SHA256 = (
    "9047141c99e2eb067bc0ca0bc5ee082ed141f91f16e25c23e125b062bf97983d"
)
EXPECTED_FEATURES = 72
EXPECTED_ROUNDS = 439
EXPECTED_OBSERVATIONS = 33_956
EXPECTED_ROWS = 848_900
EXPECTED_SQUARES = 25

IDENTIFIER_COLUMNS = frozenset(
    {
        "round_id",
        "observation_index",
        "round_observation_count",
        "round_progress",
        "slots_remaining",
        "square_index",
    }
)
LABEL_COLUMNS = frozenset({"won", "winning_square", "outcome_source"})
FORBIDDEN_PREDICTORS = IDENTIFIER_COLUMNS | LABEL_COLUMNS | frozenset(
    {
        "coverage_status",
        "mass",
        "final_board_state",
        "finalized_outcome_source",
    }
)
OBSERVATION_KEY = ["round_id", "observation_index"]
ROW_KEY = [*OBSERVATION_KEY, "square_index"]


@dataclass(frozen=True, slots=True)
class ModelingDataset:
    frame: pd.DataFrame
    manifest: dict[str, Any]
    feature_columns: tuple[str, ...]
    dataset_sha256: str
    manifest_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_feature_manifest(
    manifest: dict[str, Any],
) -> tuple[str, ...]:
    features = tuple(manifest.get("feature_columns", ()))
    if len(features) != len(set(features)):
        raise ValueError("Manifest feature names are not unique")
    forbidden = sorted(set(features) & FORBIDDEN_PREDICTORS)
    if forbidden:
        raise ValueError(
            "Manifest contains forbidden predictors: " + ", ".join(forbidden)
        )
    if not features:
        raise ValueError("Manifest has no predictive features")
    return features


def validate_labels(frame: pd.DataFrame) -> pd.Series:
    required = set(ROW_KEY) | {"won", "winning_square", "outcome_source"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("Missing label/identity columns: " + ", ".join(missing))

    won = pd.to_numeric(frame["won"], errors="coerce")
    source_usable = frame["outcome_source"].fillna("").astype(str).str.strip().ne("")
    square = pd.to_numeric(frame["square_index"], errors="coerce")
    winner = pd.to_numeric(frame["winning_square"], errors="coerce")
    candidate = won.isin([0, 1]) & source_usable & square.notna() & winner.notna()
    usable_groups = candidate.groupby(
        [frame[column] for column in OBSERVATION_KEY], sort=False
    ).transform("all")
    positives = won.eq(1).groupby(
        [frame[column] for column in OBSERVATION_KEY], sort=False
    ).transform("sum")
    sizes = won.groupby(
        [frame[column] for column in OBSERVATION_KEY], sort=False
    ).transform("size")
    winner_matches = square.eq(winner)
    consistent = winner_matches.eq(won.eq(1)).groupby(
        [frame[column] for column in OBSERVATION_KEY], sort=False
    ).transform("all")
    return usable_groups & positives.eq(1) & sizes.eq(EXPECTED_SQUARES) & consistent


def observation_weights(frame: pd.DataFrame) -> np.ndarray:
    usable = validate_labels(frame)
    if not usable.all():
        raise ValueError("Training data includes unusable observations")
    won = frame["won"].to_numpy(dtype=int)
    weights = np.where(won == 1, 0.5, 0.5 / (EXPECTED_SQUARES - 1))
    totals = (
        pd.Series(weights, index=frame.index)
        .groupby([frame[column] for column in OBSERVATION_KEY], sort=False)
        .sum()
    )
    if not np.allclose(totals.to_numpy(), 1.0):
        raise ValueError("Observation weights do not sum to one")
    return weights


def load_modeling_dataset(
    dataset_path: Path,
    manifest_path: Path,
    *,
    enforce_canonical: bool = True,
) -> ModelingDataset:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    features = validate_feature_manifest(manifest)
    digest = sha256_file(dataset_path)
    if enforce_canonical and digest != EXPECTED_SHA256:
        raise ValueError(f"Dataset SHA-256 mismatch: {digest}")
    frame = pd.read_csv(dataset_path, low_memory=False)
    missing = sorted((set(features) | set(ROW_KEY) | LABEL_COLUMNS) - set(frame))
    if missing:
        raise ValueError("Dataset columns missing: " + ", ".join(missing))
    if frame.duplicated(ROW_KEY).any():
        raise ValueError("Dataset contains duplicate square keys")
    numeric = frame.loc[:, features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Predictive input contains missing or non-finite values")
    frame.loc[:, features] = numeric
    group_sizes = frame.groupby(OBSERVATION_KEY, sort=False).size()
    if not group_sizes.eq(EXPECTED_SQUARES).all():
        raise ValueError("Dataset does not contain 25 rows per observation")
    usable = validate_labels(frame)
    frame = frame.loc[usable].copy()
    frame.sort_values(ROW_KEY, kind="stable", inplace=True)
    frame.reset_index(drop=True, inplace=True)

    if enforce_canonical:
        actual = {
            "features": len(features),
            "rounds": frame["round_id"].nunique(),
            "observations": frame.groupby(OBSERVATION_KEY).ngroups,
            "rows": len(frame),
        }
        expected = {
            "features": EXPECTED_FEATURES,
            "rounds": EXPECTED_ROUNDS,
            "observations": EXPECTED_OBSERVATIONS,
            "rows": EXPECTED_ROWS,
        }
        if actual != expected:
            raise ValueError(
                f"Canonical dataset invariant mismatch: {actual} != {expected}"
            )
    return ModelingDataset(
        frame=frame,
        manifest=manifest,
        feature_columns=features,
        dataset_sha256=digest,
        manifest_sha256=_sha256_json(manifest_path),
    )
