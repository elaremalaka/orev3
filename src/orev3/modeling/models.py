from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


RANDOM_SEED = 20_260_725


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    configuration: dict[str, Any]

    def build(self) -> Any:
        if self.name == "logistic_regression":
            return Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            C=1.0,
                            solver="lbfgs",
                            max_iter=100,
                            tol=1e-4,
                            random_state=RANDOM_SEED,
                        ),
                    ),
                ]
            )
        if self.name == "random_forest":
            return RandomForestClassifier(
                n_estimators=40,
                max_depth=10,
                min_samples_leaf=20,
                max_features="sqrt",
                n_jobs=-1,
                random_state=RANDOM_SEED,
            )
        if self.name == "hist_gradient_boosting":
            return HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=50,
                max_leaf_nodes=31,
                min_samples_leaf=50,
                l2_regularization=1.0,
                random_state=RANDOM_SEED,
            )
        raise ValueError(f"Unknown model: {self.name}")


def model_specs() -> tuple[ModelSpec, ...]:
    return (
        ModelSpec(
            "logistic_regression",
            {
                "preprocessing": "StandardScaler fit on training rows only",
                "C": 1.0,
                "solver": "lbfgs",
                "max_iter": 100,
            },
        ),
        ModelSpec(
            "random_forest",
            {
                "n_estimators": 40,
                "max_depth": 10,
                "min_samples_leaf": 20,
                "max_features": "sqrt",
            },
        ),
        ModelSpec(
            "hist_gradient_boosting",
            {
                "learning_rate": 0.05,
                "max_iter": 50,
                "max_leaf_nodes": 31,
                "min_samples_leaf": 50,
                "l2_regularization": 1.0,
            },
        ),
    )


def positive_probability(model: Any, values: np.ndarray) -> np.ndarray:
    probabilities = model.predict_proba(values)
    classes = np.asarray(model.classes_)
    if hasattr(model, "named_steps"):
        classes = np.asarray(model.named_steps["model"].classes_)
    match = np.flatnonzero(classes == 1)
    if len(match) != 1:
        raise ValueError("Fitted model does not expose positive class 1")
    result = probabilities[:, int(match[0])]
    if not np.isfinite(result).all():
        raise ValueError("Model emitted non-finite probabilities")
    return result


def native_importance(
    model: Any,
    features: tuple[str, ...],
) -> list[dict[str, Any]]:
    if hasattr(model, "named_steps"):
        fitted = model.named_steps["model"]
        values = fitted.coef_[0]
        kind = "standardized_coefficient"
    elif hasattr(model, "feature_importances_"):
        values = model.feature_importances_
        kind = "impurity_importance"
    else:
        return []
    return [
        {
            "feature": feature,
            "importance": float(abs(value)),
            "signed_value": float(value),
            "importance_type": kind,
        }
        for feature, value in zip(features, values, strict=True)
    ]
