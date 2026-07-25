from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from orev3.modeling.data import (
    load_modeling_dataset,
    observation_weights,
    validate_feature_manifest,
    validate_labels,
)
from orev3.modeling.feature_sets import conservative_feature_set
from orev3.modeling.run_baseline_modeling import _json_safe


def test_manifest_only_selection_rejects_identifiers_and_labels() -> None:
    assert validate_feature_manifest({"feature_columns": ["miner_count"]}) == (
        "miner_count",
    )
    for forbidden in ("round_id", "square_index", "won", "outcome_source"):
        with pytest.raises(ValueError, match="forbidden"):
            validate_feature_manifest({"feature_columns": [forbidden]})


def test_duplicate_manifest_features_are_rejected() -> None:
    with pytest.raises(ValueError, match="not unique"):
        validate_feature_manifest(
            {"feature_columns": ["miner_count", "miner_count"]}
        )


def test_conservative_set_uses_only_documented_exact_relationships() -> None:
    manifest = {
        "feature_columns": ["a", "b", "c", "d", "e"],
    }
    audit = {
        "passed": True,
        "constant_features": ["e"],
        "redundancy_findings": [
            {
                "relationship_type": "exact_duplicate",
                "features": ["a", "b"],
            },
            {
                "relationship_type": "perfect_positive_affine",
                "features": ["b", "c"],
            },
            {
                "relationship_type": "high_correlation",
                "features": ["c", "d"],
            },
        ],
    }
    training = pd.DataFrame(
        {
            "a": [0.0, 1.0, 2.0],
            "b": [0.0, 1.0, 2.0],
            "c": [1.0, 3.0, 5.0],
            "d": [0.0, 1.0, 4.0],
            "e": [0.0, 0.0, 0.0],
        }
    )
    selected, exclusions = conservative_feature_set(manifest, audit, training)
    assert selected == ("a", "d")
    assert [item["feature"] for item in exclusions] == ["b", "c", "e"]


def test_one_positive_validation_and_source_separation(
    observation_frame: pd.DataFrame,
) -> None:
    usable = validate_labels(observation_frame)
    assert usable.all()
    assert set(observation_frame.loc[usable, "outcome_source"]) == {
        "observed",
        "enriched",
    }
    broken = observation_frame.copy()
    broken.loc[
        broken["round_id"].eq(10)
        & broken["observation_index"].eq(0),
        "won",
    ] = 0
    broken.loc[
        broken["round_id"].eq(10)
        & broken["observation_index"].eq(0),
        "winning_square",
    ] = np.nan
    mask = validate_labels(broken)
    assert not mask.loc[
        broken["round_id"].eq(10)
        & broken["observation_index"].eq(0)
    ].any()
    assert mask.loc[broken["round_id"].eq(11)].all()


def test_equal_observation_weighting(observation_frame: pd.DataFrame) -> None:
    weights = observation_weights(observation_frame)
    weighted = observation_frame[["round_id", "observation_index", "won"]].copy()
    weighted["weight"] = weights
    totals = weighted.groupby(["round_id", "observation_index"])["weight"].sum()
    positives = weighted.loc[weighted["won"].eq(1), "weight"]
    negatives = weighted.loc[weighted["won"].eq(0), "weight"]
    assert np.allclose(totals, 1.0)
    assert np.allclose(positives, 0.5)
    assert np.allclose(negatives, 0.5 / 24)


def test_non_finite_predictor_is_rejected(
    tmp_path, observation_frame: pd.DataFrame
) -> None:
    frame = observation_frame.copy()
    frame.loc[0, "miner_count"] = np.inf
    dataset = tmp_path / "dataset.csv"
    manifest = tmp_path / "manifest.json"
    frame.to_csv(dataset, index=False)
    manifest.write_text(
        json.dumps({"feature_columns": ["miner_count"]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="non-finite"):
        load_modeling_dataset(dataset, manifest, enforce_canonical=False)


def test_generated_json_uses_null_for_unavailable_metrics() -> None:
    assert _json_safe({"metric": float("nan")}) == {"metric": None}
