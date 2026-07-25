from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from orev3.analysis.audit_feature_dataset import audit_feature_dataset
from orev3.analysis.feature_quality import (
    ambiguous_zero_fallbacks,
    find_redundancies,
    label_diagnostics,
    observation_balanced_weights,
    parse_numeric_feature,
    progress_bucket,
    standardized_mean_difference,
    summarize_feature,
)


def summary_for(
    name: str,
    values: list[float],
    observations: list[str] | None = None,
) -> dict[str, object]:
    original = pd.Series(values)
    numeric, missing, non_finite = parse_numeric_feature(original)
    keys = pd.Series(
        observations
        if observations is not None
        else [str(index) for index in range(len(values))]
    )
    return summarize_feature(
        name,
        original,
        numeric,
        keys,
        missing,
        non_finite,
    )


def test_constant_and_near_constant_detection() -> None:
    constant = summary_for("constant", [4.0] * 1000)
    near = summary_for("near", [0.0] * 995 + [1.0] * 5)
    below = summary_for("below", [0.0] * 994 + [1.0] * 6)

    assert constant["constant"] is True
    assert constant["near_constant"] is False
    assert near["constant"] is False
    assert near["near_constant"] is True
    assert below["near_constant"] is False


def test_observation_balanced_weighting() -> None:
    values = pd.Series([0.0, 0.0, 10.0])
    observations = pd.Series(["a", "a", "b"])
    weights = observation_balanced_weights(values, observations)
    summary = summary_for(
        "weighted",
        values.tolist(),
        observations.tolist(),
    )

    assert weights.tolist() == [0.5, 0.5, 1.0]
    assert summary["mean"] == pytest.approx(10 / 3)
    assert summary["observation_balanced"]["mean"] == 5.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "early"),
        (0.199999, "early"),
        (0.2, "early-middle"),
        (0.4, "middle"),
        (0.6, "late-middle"),
        (0.8, "late"),
        (1.0, "late"),
    ],
)
def test_progress_bucket_boundaries(
    value: float,
    expected: str,
) -> None:
    assert progress_bucket(value) == expected


def test_zero_variance_standardized_difference_is_safe() -> None:
    assert standardized_mean_difference([1, 1], [1, 1]) == 0.0
    assert standardized_mean_difference([2, 2], [1, 1]) is None


def test_redundancy_relationships_and_threshold() -> None:
    x = np.arange(100, dtype=float)
    high = x + np.sin(x) * 4
    below = x + np.sin(x) * 40
    frame = pd.DataFrame(
        {
            "x": x,
            "duplicate": x,
            "positive_affine": x * 2 + 3,
            "negative_affine": -x,
            "high": high,
            "below": below,
        }
    )
    summaries = {
        column: summary_for(column, frame[column].tolist())
        for column in frame
    }

    findings = find_redundancies(frame, summaries)
    relationships = {
        (tuple(item["features"]), item["relationship_type"])
        for item in findings
    }

    assert (("x", "duplicate"), "exact_duplicate") in relationships
    assert (
        ("x", "positive_affine"),
        "perfect_positive_affine",
    ) in relationships
    assert (
        ("x", "negative_affine"),
        "perfect_negative_affine",
    ) in relationships
    assert (("x", "high"), "high_correlation") in relationships
    assert not any(
        item["features"] == ["x", "below"]
        and item["relationship_type"] == "high_correlation"
        for item in findings
    )
    assert findings == find_redundancies(frame, summaries)


def test_boolean_redundancy_relationships() -> None:
    frame = pd.DataFrame(
        {
            "has_a": [0.0, 1.0, 0.0, 1.0],
            "has_a_copy": [0.0, 1.0, 0.0, 1.0],
            "not_a": [1.0, 0.0, 1.0, 0.0],
            "exclusive": [0.0, 0.0, 1.0, 0.0],
        }
    )
    summaries = {
        column: summary_for(column, frame[column].tolist())
        for column in frame
    }
    findings = find_redundancies(frame, summaries)
    relationships = {
        item["relationship_type"]
        for item in findings
    }

    assert "availability_flags_identical" in relationships
    assert "boolean_complement" in relationships
    assert "boolean_mutually_exclusive" in relationships


def test_ambiguous_zero_fallback_detection() -> None:
    findings = ambiguous_zero_fallbacks(
        ["miner_delta_1", "custom_momentum"],
        ["miner_delta_1"],
    )

    assert [item["feature"] for item in findings] == [
        "custom_momentum",
        "miner_delta_1",
    ]


def test_label_diagnostics_separate_outcome_sources() -> None:
    frame = pd.DataFrame(
        {
            "round_id": [1, 1, 2, 2],
            "observation_index": [0, 0, 0, 0],
            "square_index": [0, 1, 0, 1],
            "won": [1, 0, 1, 0],
            "outcome_source": [
                "observed",
                "observed",
                "enriched",
                "enriched",
            ],
            "feature": [3.0, 1.0, 2.0, 4.0],
        }
    )

    records = label_diagnostics(frame, ["feature"], square_count=2)

    assert [record["outcome_source"] for record in records] == [
        "enriched",
        "observed",
    ]
    assert records[0]["mean_difference"] == -2.0
    assert records[1]["mean_difference"] == 2.0
    assert label_diagnostics(frame.iloc[0:0], ["feature"], 2) == []


def test_temporal_coverage_and_partial_labels(tmp_path: Path) -> None:
    dataset = tmp_path / "features.csv"
    manifest = tmp_path / "manifest.json"
    frame = pd.DataFrame(
        {
            "round_id": [1, 1, 1, 1],
            "observation_index": [0, 0, 1, 1],
            "round_progress": [0.0, 0.0, 1.0, 1.0],
            "square_index": [0, 1, 0, 1],
            "miner_delta_1": [0, 0, 2, 3],
            "has_previous_observation": [False, False, True, True],
            "won": [1, 0, 1, 0],
            "outcome_source": ["observed", "observed", "", ""],
        }
    )
    frame.to_csv(dataset, index=False)
    manifest.write_text(
        json.dumps(
            {
                "feature_columns": [
                    "miner_delta_1",
                    "has_previous_observation",
                ],
                "feature_registry": [
                    {
                        "name": "one_step_delta",
                        "family": "temporal",
                        "output_columns": [
                            "miner_delta_1",
                            "has_previous_observation",
                        ],
                    }
                ],
                "square_count": 2,
                "row_count": 4,
            }
        ),
        encoding="utf-8",
    )

    report = audit_feature_dataset(dataset, manifest)
    coverage = {
        item["feature"]: item
        for item in report["temporal_coverage"]
    }

    assert coverage["miner_delta_1"]["percentage_available"] == 50.0
    assert (
        coverage["miner_delta_1"][
            "first_available_observation_index"
        ]
        == 1
    )
    assert coverage["miner_delta_1"][
        "zero_fallback_distinguishable"
    ] is True
    assert {
        item["outcome_source"]
        for item in report["label_diagnostics"]
    } == {"observed"}
