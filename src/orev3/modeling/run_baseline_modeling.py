from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn

from orev3.analysis.feature_quality import progress_bucket
from orev3.modeling.baselines import baseline_names, baseline_scores
from orev3.modeling.data import (
    OBSERVATION_KEY,
    ModelingDataset,
    load_modeling_dataset,
    observation_weights,
)
from orev3.modeling.feature_sets import conservative_feature_set
from orev3.modeling.metrics import (
    aggregate_metrics,
    rank_predictions,
    round_bootstrap_interval,
)
from orev3.modeling.models import (
    RANDOM_SEED,
    model_specs,
    native_importance,
    positive_probability,
)
from orev3.modeling.splits import ChronologicalFold, expanding_round_folds


DEFAULT_DATASET = Path("data/research/square_feature_dataset_v1.csv")
DEFAULT_MANIFEST = Path(
    "data/research/square_feature_dataset_v1.manifest.json"
)
DEFAULT_AUDIT = Path("data/research/feature_audit_v1.json")
DEFAULT_RESULTS = Path("data/research/baseline_model_results_v1.json")
DEFAULT_FOLDS = Path("data/research/baseline_fold_metrics_v1.csv")
DEFAULT_PREDICTIONS = Path("data/research/baseline_predictions_v1.csv")
DEFAULT_FEATURE_SETS = Path(
    "data/research/baseline_feature_sets_v1.json"
)
DEFAULT_IMPORTANCE = Path(
    "data/research/baseline_feature_importance_v1.csv"
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _coverage_by_round(dataset: ModelingDataset) -> dict[int, str]:
    path = Path(str(dataset.manifest.get("input_path", "")))
    if not path.exists():
        return {}
    frame = pd.read_csv(path, usecols=["round_id", "coverage_status"])
    unique = frame.drop_duplicates()
    result: dict[int, str] = {}
    for round_id, group in unique.groupby("round_id"):
        values = sorted(group["coverage_status"].dropna().astype(str).unique())
        result[int(round_id)] = values[0] if len(values) == 1 else "mixed"
    return result


def _family_map(manifest: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for registration in manifest.get("feature_registry", ()):
        for feature in registration.get("output_columns", ()):
            result[str(feature)] = str(registration.get("family", "unknown"))
    return result


def _congestion(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
) -> dict[tuple[int, int], str]:
    train_totals = (
        train.groupby(OBSERVATION_KEY, sort=False)["miner_count"].sum()
    )
    evaluation_totals = (
        evaluation.groupby(OBSERVATION_KEY, sort=False)["miner_count"].sum()
    )
    edges = np.quantile(train_totals.to_numpy(dtype=float), [0.25, 0.5, 0.75])
    labels = ("q1_low", "q2", "q3", "q4_high")
    bucket_indices = np.searchsorted(edges, evaluation_totals, side="right")
    return {
        (int(round_id), int(observation_index)): labels[int(index)]
        for (round_id, observation_index), index in zip(
            evaluation_totals.index, bucket_indices, strict=True
        )
    }


def _decorate_observations(
    observations: pd.DataFrame,
    *,
    fold: ChronologicalFold,
    strategy: str,
    feature_set: str,
    coverage: dict[int, str],
    congestion: dict[tuple[int, int], str],
) -> pd.DataFrame:
    result = observations.copy()
    result.insert(0, "feature_set", feature_set)
    result.insert(0, "strategy", strategy)
    result.insert(0, "split_kind", fold.kind)
    result.insert(0, "fold", fold.name)
    result["coverage_status"] = result["round_id"].map(coverage).fillna("unknown")
    result["progress_bucket"] = result["round_progress"].map(progress_bucket)
    result["congestion_bucket"] = [
        congestion[(int(round_id), int(observation_index))]
        for round_id, observation_index in result[OBSERVATION_KEY].itertuples(
            index=False, name=None
        )
    ]
    return result


def _fold_metric_rows(
    observations: pd.DataFrame,
    ranked_rows: pd.DataFrame,
    *,
    fold: ChronologicalFold,
    strategy: str,
    feature_set: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    calibrations: dict[str, Any] = {}
    overall = aggregate_metrics(observations, ranked_rows)
    overall["top_1_round_bootstrap_95"] = round_bootstrap_interval(
        observations, "top_1_hit", seed=RANDOM_SEED
    )
    overall["mrr_round_bootstrap_95"] = round_bootstrap_interval(
        observations, "reciprocal_rank", seed=RANDOM_SEED + 1
    )

    def add_row(segment: str, value: str, metrics: dict[str, Any]) -> None:
        flat = {
            key: metric
            for key, metric in metrics.items()
            if not isinstance(metric, (dict, list))
        }
        rows.append(
            {
                "fold": fold.name,
                "split_kind": fold.kind,
                "feature_set": feature_set,
                "strategy": strategy,
                "segment": segment,
                "segment_value": value,
                **flat,
            }
        )

    add_row("all", "all", overall)
    if "calibration" in overall:
        calibrations["all"] = overall["calibration"]
    for source, subset in observations.groupby("outcome_source", sort=True):
        indices = set(
            subset[OBSERVATION_KEY].itertuples(index=False, name=None)
        )
        row_subset = ranked_rows.loc[
            [
                (round_id, observation_index) in indices
                for round_id, observation_index in ranked_rows[
                    OBSERVATION_KEY
                ].itertuples(index=False, name=None)
            ]
        ]
        source_metrics = aggregate_metrics(subset, row_subset)
        add_row(
            "outcome_source",
            str(source),
            source_metrics,
        )
        if "calibration" in source_metrics:
            calibrations[f"outcome_source:{source}"] = source_metrics[
                "calibration"
            ]
    for segment in ("progress_bucket", "congestion_bucket", "coverage_status"):
        for value, subset in observations.groupby(segment, sort=True):
            add_row(segment, str(value), aggregate_metrics(subset, pd.DataFrame()))
    return rows, overall, calibrations


def _aggregate_uncertainty(
    predictions: pd.DataFrame,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (feature_set, strategy), group in predictions.groupby(
        ["feature_set", "strategy"], sort=True
    ):
        records.append(
            {
                "feature_set": feature_set,
                "strategy": strategy,
                "observation_count": len(group),
                "round_count": int(group["round_id"].nunique()),
                "resampling_unit": "round",
                "bootstrap_samples": 500,
                "top_1_accuracy_95": round_bootstrap_interval(
                    group, "top_1_hit", seed=RANDOM_SEED
                ),
                "mean_reciprocal_rank_95": round_bootstrap_interval(
                    group, "reciprocal_rank", seed=RANDOM_SEED + 1
                ),
            }
        )
    return records


def _aggregate_fold_results(
    fold_metrics: pd.DataFrame,
) -> list[dict[str, Any]]:
    overall = fold_metrics.loc[
        fold_metrics["segment"].eq("all")
        & fold_metrics["split_kind"].eq("validation")
    ]
    identifiers = ["feature_set", "strategy"]
    metric_columns = [
        "top_1_accuracy",
        "top_2_hit_rate",
        "top_3_hit_rate",
        "top_5_hit_rate",
        "mean_reciprocal_rank",
        "mean_winner_rank",
        "mean_ndcg",
        "mean_winner_percentile",
        "log_loss",
        "brier_score",
        "mean_winner_probability",
    ]
    records: list[dict[str, Any]] = []
    for keys, group in overall.groupby(identifiers, dropna=False, sort=True):
        record: dict[str, Any] = dict(zip(identifiers, keys, strict=True))
        record["fold_count"] = len(group)
        record["observation_count"] = int(group["observation_count"].sum())
        record["round_count"] = int(group["round_count"].sum())
        for metric in metric_columns:
            if metric not in group or group[metric].isna().all():
                continue
            values = group[metric].dropna().to_numpy(dtype=float)
            record[f"{metric}_mean"] = float(values.mean())
            record[f"{metric}_std"] = float(values.std(ddof=0))
        records.append(record)
    return records


def _strategy_relative_diagnostics(
    predictions: pd.DataFrame,
) -> list[dict[str, Any]]:
    models = predictions.loc[
        predictions["strategy"].isin(
            [spec.name for spec in model_specs()]
        )
    ]
    baselines = predictions.loc[
        predictions["feature_set"].eq("not_applicable")
    ]
    keys = ["fold", "round_id", "observation_index"]
    records: list[dict[str, Any]] = []
    for (feature_set, strategy), model_group in models.groupby(
        ["feature_set", "strategy"], sort=True
    ):
        for baseline_name, baseline_group in baselines.groupby(
            "strategy", sort=True
        ):
            merged = model_group.merge(
                baseline_group[
                    keys
                    + [
                        "selected_square",
                        "winner_rank",
                        "top_1_hit",
                    ]
                ],
                on=keys,
                suffixes=("_model", "_baseline"),
                validate="one_to_one",
            )
            for segment, segment_value, subset in [
                ("all", "all", merged),
                *[
                    (segment, str(value), group)
                    for segment in (
                        "progress_bucket",
                        "congestion_bucket",
                        "coverage_status",
                    )
                    for value, group in merged.groupby(segment, sort=True)
                ],
            ]:
                records.append({
                    "feature_set": feature_set,
                    "model": strategy,
                    "baseline": baseline_name,
                    "segment": segment,
                    "segment_value": segment_value,
                    "observations": len(subset),
                    "agreement_rate": float(
                        subset["selected_square_model"]
                        .eq(subset["selected_square_baseline"])
                        .mean()
                    ),
                    "incremental_top_1_hits": int(
                        (
                            subset["top_1_hit_model"].eq(1)
                            & subset["top_1_hit_baseline"].eq(0)
                        ).sum()
                    ),
                    "lost_hits": int(
                        (
                            subset["top_1_hit_model"].eq(0)
                            & subset["top_1_hit_baseline"].eq(1)
                        ).sum()
                    ),
                    "mean_winner_rank_improvement": float(
                        (
                            subset["winner_rank_baseline"]
                            - subset["winner_rank_model"]
                        ).mean()
                    ),
                })
    return records


def run_experiment(
    *,
    dataset_path: Path,
    manifest_path: Path,
    audit_path: Path,
    results_path: Path,
    fold_metrics_path: Path,
    predictions_path: Path,
    feature_sets_path: Path,
    importance_path: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    dataset = load_modeling_dataset(dataset_path, manifest_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    folds = expanding_round_folds(
        dataset.frame["round_id"].drop_duplicates().tolist()
    )
    initial_training_frame = dataset.frame.loc[
        dataset.frame["round_id"].isin(folds[0].train_rounds)
    ]
    conservative, exclusions = conservative_feature_set(
        dataset.manifest, audit, initial_training_frame
    )
    feature_sets = {
        "all_72": dataset.feature_columns,
        "conservative_deduplicated": conservative,
    }
    coverage = _coverage_by_round(dataset)
    family = _family_map(dataset.manifest)
    prediction_frames: list[pd.DataFrame] = []
    fold_rows: list[dict[str, Any]] = []
    fold_details: list[dict[str, Any]] = []
    importance_rows: list[dict[str, Any]] = []
    calibration: dict[str, Any] = {}

    for fold in folds:
        train = dataset.frame.loc[
            dataset.frame["round_id"].isin(fold.train_rounds)
        ].reset_index(drop=True)
        evaluation = dataset.frame.loc[
            dataset.frame["round_id"].isin(fold.evaluation_rounds)
        ].reset_index(drop=True)
        congestion = _congestion(train, evaluation)
        detail = fold.summary()
        detail.update(
            {
                "training_rows": len(train),
                "training_observations": train.groupby(OBSERVATION_KEY).ngroups,
                "evaluation_rows": len(evaluation),
                "evaluation_observations": evaluation.groupby(
                    OBSERVATION_KEY
                ).ngroups,
            }
        )
        fold_details.append(detail)

        for baseline in baseline_names():
            scores, probabilities = baseline_scores(
                evaluation, baseline, seed=RANDOM_SEED
            )
            ranked, observations = rank_predictions(
                evaluation, scores, probabilities
            )
            decorated = _decorate_observations(
                observations,
                fold=fold,
                strategy=baseline,
                feature_set="not_applicable",
                coverage=coverage,
                congestion=congestion,
            )
            prediction_frames.append(decorated)
            rows, metrics, fold_calibrations = _fold_metric_rows(
                decorated,
                ranked,
                fold=fold,
                strategy=baseline,
                feature_set="not_applicable",
            )
            fold_rows.extend(rows)
            for segment, summary in fold_calibrations.items():
                calibration[
                    f"{fold.name}:not_applicable:{baseline}:{segment}"
                ] = summary

        y_train = train["won"].to_numpy(dtype=int)
        sample_weight = observation_weights(train)
        for feature_set_name, features in feature_sets.items():
            x_train = train.loc[:, features].to_numpy(dtype=np.float32)
            x_evaluation = evaluation.loc[:, features].to_numpy(dtype=np.float32)
            for spec in model_specs():
                model = spec.build()
                fit_started = time.perf_counter()
                fit_parameters = (
                    {"model__sample_weight": sample_weight}
                    if spec.name == "logistic_regression"
                    else {"sample_weight": sample_weight}
                )
                model.fit(x_train, y_train, **fit_parameters)
                fit_seconds = time.perf_counter() - fit_started
                raw_probability = positive_probability(model, x_evaluation)
                ranked, observations = rank_predictions(
                    evaluation, raw_probability, raw_probability
                )
                decorated = _decorate_observations(
                    observations,
                    fold=fold,
                    strategy=spec.name,
                    feature_set=feature_set_name,
                    coverage=coverage,
                    congestion=congestion,
                )
                prediction_frames.append(decorated)
                rows, metrics, fold_calibrations = _fold_metric_rows(
                    decorated,
                    ranked,
                    fold=fold,
                    strategy=spec.name,
                    feature_set=feature_set_name,
                )
                for row in rows:
                    row["fit_seconds"] = fit_seconds
                fold_rows.extend(rows)
                for segment, summary in fold_calibrations.items():
                    calibration[
                        f"{fold.name}:{feature_set_name}:{spec.name}:{segment}"
                    ] = summary
                for record in native_importance(model, features):
                    importance_rows.append(
                        {
                            "fold": fold.name,
                            "split_kind": fold.kind,
                            "feature_set": feature_set_name,
                            "model": spec.name,
                            "feature_family": family.get(
                                record["feature"], "unknown"
                            ),
                            **record,
                        }
                    )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    fold_metrics = pd.DataFrame(fold_rows)
    importance = pd.DataFrame(importance_rows)
    feature_set_output = {
        "schema_version": 1,
        "all_72": {
            "feature_count": len(dataset.feature_columns),
            "features": list(dataset.feature_columns),
            "exclusions": [],
        },
        "conservative_deduplicated": {
            "feature_count": len(conservative),
            "features": list(conservative),
            "exclusions": list(exclusions),
            "policy": (
                "Using only the initial 263 training rounds, exclude constants "
                "and later manifest-order members of exact, "
                "identical-availability, or perfectly affine equivalence "
                "groups under the RFC-003B.3 audit policy; freeze thereafter."
            ),
        },
    }
    result = {
        "schema_version": 1,
        "experiment": "RFC-004 baseline chronological ranking",
        "dataset": {
            "path": str(dataset_path),
            "sha256": dataset.dataset_sha256,
            "manifest_path": str(manifest_path),
            "manifest_sha256": dataset.manifest_sha256,
            "features": len(dataset.feature_columns),
            "rounds": dataset.frame["round_id"].nunique(),
            "observations": dataset.frame.groupby(OBSERVATION_KEY).ngroups,
            "rows": len(dataset.frame),
            "squares_per_observation": 25,
        },
        "label": {
            "column": "won",
            "rules": (
                "Keep only 25-row observations with exactly one won=1, a "
                "non-empty outcome_source, and winning_square matching won."
            ),
            "outcome_sources": dataset.frame.groupby("outcome_source")[
                "round_id"
            ].nunique().to_dict(),
        },
        "chronology": "ascending numeric round_id",
        "folds": fold_details,
        "sample_weight": {
            "observation_total": 1.0,
            "winner": 0.5,
            "each_loser": 0.5 / 24,
            "round_policy": (
                "Every observation has equal total weight; rounds with more "
                "observations contribute proportionally more observed states."
            ),
        },
        "random_seed": RANDOM_SEED,
        "models": [
            {"name": spec.name, "configuration": spec.configuration}
            for spec in model_specs()
        ],
        "aggregate_validation_metrics": _aggregate_fold_results(fold_metrics),
        "final_holdout_metrics": fold_metrics.loc[
            fold_metrics["split_kind"].eq("holdout")
            & fold_metrics["segment"].eq("all")
        ].to_dict(orient="records"),
        "strategy_relative_diagnostics": _strategy_relative_diagnostics(
            predictions
        ),
        "round_bootstrap_uncertainty": _aggregate_uncertainty(predictions),
        "calibration": calibration,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "platform": platform.platform(),
        },
        "runtime_seconds": time.perf_counter() - started,
    }

    result = _json_safe(result)
    for path in (
        results_path,
        fold_metrics_path,
        predictions_path,
        feature_sets_path,
        importance_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    feature_sets_path.write_text(
        json.dumps(feature_set_output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fold_metrics.to_csv(fold_metrics_path, index=False)
    predictions.to_csv(predictions_path, index=False)
    importance.to_csv(importance_path, index=False)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--fold-metrics", type=Path, default=DEFAULT_FOLDS)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument(
        "--feature-sets", type=Path, default=DEFAULT_FEATURE_SETS
    )
    parser.add_argument("--importance", type=Path, default=DEFAULT_IMPORTANCE)
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    result = run_experiment(
        dataset_path=arguments.dataset,
        manifest_path=arguments.manifest,
        audit_path=arguments.audit,
        results_path=arguments.results,
        fold_metrics_path=arguments.fold_metrics,
        predictions_path=arguments.predictions,
        feature_sets_path=arguments.feature_sets,
        importance_path=arguments.importance,
    )
    print(json.dumps(result["dataset"], sort_keys=True))
    print(f"runtime_seconds={result['runtime_seconds']:.3f}")


if __name__ == "__main__":
    main()
