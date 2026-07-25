from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from orev3.modeling.data import validate_feature_manifest


def conservative_feature_set(
    manifest: dict[str, Any],
    audit: dict[str, Any],
    training_frame: pd.DataFrame,
) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    features = validate_feature_manifest(manifest)
    missing = sorted(set(features) - set(training_frame.columns))
    if missing:
        raise ValueError(
            "Training frame is missing manifest features: " + ", ".join(missing)
        )
    if not audit.get("passed", False):
        raise ValueError("The RFC-003B.3 audit did not pass")
    position = {feature: index for index, feature in enumerate(features)}
    parent = {feature: feature for feature in features}

    def find(value: str) -> str:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(first: str, second: str) -> None:
        first_root, second_root = find(first), find(second)
        if first_root == second_root:
            return
        if position[first_root] <= position[second_root]:
            parent[second_root] = first_root
        else:
            parent[first_root] = second_root

    numeric = training_frame.loc[:, features]
    reasons: dict[str, str] = {
        feature: "constant_on_initial_training_rounds"
        for feature in features
        if numeric[feature].nunique(dropna=False) <= 1
    }
    correlations = numeric.corr(method="pearson")
    for first_index, first in enumerate(features):
        if first in reasons:
            continue
        for second in features[first_index + 1 :]:
            if second in reasons:
                continue
            if numeric[first].equals(numeric[second]):
                union(first, second)
                continue
            correlation = correlations.at[first, second]
            if np.isfinite(correlation) and abs(abs(correlation) - 1.0) <= 1e-12:
                union(first, second)

    groups: dict[str, list[str]] = {}
    for feature in features:
        groups.setdefault(find(feature), []).append(feature)
    for members in groups.values():
        keeper = min(members, key=position.__getitem__)
        for feature in members:
            if feature != keeper and feature not in reasons:
                reasons[feature] = (
                    "initial_training_exact_or_perfect_affine_redundancy"
                )

    selected = tuple(feature for feature in features if feature not in reasons)
    exclusions = tuple(
        {"feature": feature, "reason": reasons[feature]}
        for feature in features
        if feature in reasons
    )
    return selected, exclusions
