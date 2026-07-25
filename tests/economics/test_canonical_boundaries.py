from __future__ import annotations

from pathlib import Path

import pandas as pd

from orev3.economics.validation import validate_canonical_inputs


def test_rfc004_artifacts_preserve_oos_folds_and_feature_sets() -> None:
    predictions = pd.read_csv(
        "data/research/baseline_predictions_v1.csv",
        low_memory=False,
    )
    result = validate_canonical_inputs(
        dataset_path=Path("data/research/square_feature_dataset_v1.csv"),
        manifest_path=Path(
            "data/research/square_feature_dataset_v1.manifest.json"
        ),
        feature_sets_path=Path(
            "data/research/baseline_feature_sets_v1.json"
        ),
        predictions=predictions,
    )
    assert result["feature_count"] == 72
    assert result["conservative_feature_count"] == 52
    assert result["folds"]["final_holdout"] == (342527, 342570, 44)
