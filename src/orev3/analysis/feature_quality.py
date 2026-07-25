from __future__ import annotations

import hashlib
import math
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
import pandas as pd


NEAR_CONSTANT_DOMINANCE_THRESHOLD = 0.995
HIGH_CORRELATION_THRESHOLD = 0.98
PERFECT_CORRELATION_TOLERANCE = 1e-12
ORDERING_EQUIVALENCE_THRESHOLD = 0.999

PROGRESS_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("early", 0.0, 0.2),
    ("early-middle", 0.2, 0.4),
    ("middle", 0.4, 0.6),
    ("late-middle", 0.6, 0.8),
    ("late", 0.8, 1.0),
)

TEMPORAL_TOKENS = (
    "delta",
    "rolling",
    "momentum",
    "acceleration",
    "influx",
    "outflow",
    "volatility",
    "observations_since",
    "persistence",
)


def progress_bucket(value: float) -> str:
    if not math.isfinite(value) or value < 0 or value > 1:
        raise ValueError(f"round progress must be in [0, 1], got {value}")

    for name, lower, upper in PROGRESS_BUCKETS:
        if lower <= value < upper or (
            name == "late" and value == upper
        ):
            return name

    raise AssertionError("progress bucket boundaries are incomplete")


def parse_numeric_feature(
    series: pd.Series,
) -> tuple[pd.Series, int, int]:
    missing = series.isna() | series.astype("string").str.strip().eq("")
    normalized = series.astype("string").str.strip().str.lower().replace(
        {"true": "1", "false": "0"}
    )
    numeric = pd.to_numeric(normalized, errors="coerce").astype(float)
    non_finite = (~missing) & (
        numeric.isna() | ~np.isfinite(numeric.to_numpy())
    )
    numeric[~np.isfinite(numeric.to_numpy())] = np.nan
    return numeric, int(missing.sum()), int(non_finite.sum())


def semantic_dtype(
    original: pd.Series,
    numeric: pd.Series,
) -> str:
    finite = numeric.dropna()

    if finite.empty:
        return "unknown"

    unique = set(finite.unique().tolist())

    if unique <= {0.0, 1.0}:
        return "boolean"

    if np.equal(finite.to_numpy(), np.floor(finite.to_numpy())).all():
        return "integer"

    return "float"


def _basic_stats(
    values: np.ndarray,
    weights: np.ndarray | None = None,
) -> dict[str, float | int | None]:
    finite_mask = np.isfinite(values)
    finite = values[finite_mask]

    if finite.size == 0:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "population_std": None,
            "zero_percentage": None,
        }

    if weights is None:
        mean = float(np.mean(finite))
        variance = float(np.mean((finite - mean) ** 2))
        zero_percentage = float(np.mean(finite == 0) * 100)
    else:
        finite_weights = weights[finite_mask]
        total_weight = float(finite_weights.sum())

        if total_weight <= 0:
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "population_std": None,
                "zero_percentage": None,
            }

        normalized = finite_weights / total_weight
        mean = float(np.sum(normalized * finite))
        variance = float(np.sum(normalized * (finite - mean) ** 2))
        zero_percentage = float(
            np.sum(normalized * (finite == 0)) * 100
        )

    return {
        "count": int(finite.size),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": mean,
        "population_std": math.sqrt(max(variance, 0.0)),
        "zero_percentage": zero_percentage,
    }


def observation_balanced_weights(
    values: pd.Series,
    observation_keys: pd.Series,
) -> np.ndarray:
    finite = values.notna()
    finite_counts = finite.groupby(observation_keys).transform("sum")
    weights = np.zeros(len(values), dtype=float)
    usable = finite & finite_counts.gt(0)
    weights[usable.to_numpy()] = (
        1.0 / finite_counts[usable].to_numpy(dtype=float)
    )
    return weights


def summarize_feature(
    name: str,
    original: pd.Series,
    numeric: pd.Series,
    observation_keys: pd.Series,
    missing_count: int,
    non_finite_count: int,
) -> dict[str, Any]:
    finite = numeric.dropna()
    row_stats = _basic_stats(numeric.to_numpy(dtype=float))
    weights = observation_balanced_weights(numeric, observation_keys)
    balanced = _basic_stats(
        numeric.to_numpy(dtype=float),
        weights,
    )
    value_counts = finite.value_counts(dropna=True)
    unique_count = int(len(value_counts))
    dominant_percentage = (
        float(value_counts.iloc[0] / len(finite) * 100)
        if len(finite)
        else None
    )
    constant = unique_count == 1
    near_constant = bool(
        not constant
        and dominant_percentage is not None
        and dominant_percentage
        >= NEAR_CONSTANT_DOMINANCE_THRESHOLD * 100
    )
    boolean_like = bool(
        unique_count > 0
        and set(finite.unique().tolist()) <= {0.0, 1.0}
    )

    return {
        "feature": name,
        "dtype": semantic_dtype(original, numeric),
        "row_count": int(len(original)),
        "missing_count": missing_count,
        "non_finite_count": non_finite_count,
        **row_stats,
        "unique_value_count": unique_count,
        "dominant_value_percentage": dominant_percentage,
        "constant": constant,
        "near_constant": near_constant,
        "boolean_like": boolean_like,
        "availability_flag": bool(
            boolean_like
            and (
                name.startswith("has_")
                or "availability" in name
                or "available" in name
            )
        ),
        "observation_balanced": balanced,
    }


def standardized_mean_difference(
    winners: Sequence[float],
    losers: Sequence[float],
) -> float | None:
    winner_values = np.asarray(winners, dtype=float)
    loser_values = np.asarray(losers, dtype=float)
    winner_values = winner_values[np.isfinite(winner_values)]
    loser_values = loser_values[np.isfinite(loser_values)]

    if not len(winner_values) or not len(loser_values):
        return None

    difference = float(
        np.mean(winner_values) - np.mean(loser_values)
    )
    pooled_variance = float(
        (
            np.var(winner_values, ddof=0)
            + np.var(loser_values, ddof=0)
        )
        / 2
    )

    if pooled_variance <= 0:
        return 0.0 if difference == 0 else None

    return difference / math.sqrt(pooled_variance)


def _series_digest(series: pd.Series) -> str:
    hashed = pd.util.hash_pandas_object(
        series,
        index=False,
        categorize=True,
    ).to_numpy()
    return hashlib.sha256(hashed.tobytes()).hexdigest()


def _redundancy_record(
    first: str,
    second: str,
    relationship: str,
    strength: float,
    affected_rows: int,
    priority: str,
) -> dict[str, Any]:
    return {
        "features": [first, second],
        "relationship_type": relationship,
        "strength": float(strength),
        "affected_row_count": int(affected_rows),
        "suggested_review_priority": priority,
    }


def find_redundancies(
    frame: pd.DataFrame,
    summaries: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    columns = list(frame.columns)
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    exact_pairs: set[tuple[str, str]] = set()
    digest_groups: dict[str, list[str]] = {}

    for column in columns:
        digest_groups.setdefault(
            _series_digest(frame[column]),
            [],
        ).append(column)

    for candidates in digest_groups.values():
        if len(candidates) < 2:
            continue

        for first_index, first in enumerate(candidates):
            for second in candidates[first_index + 1 :]:
                if not frame[first].equals(frame[second]):
                    continue

                relationship = (
                    "availability_flags_identical"
                    if summaries[first]["availability_flag"]
                    and summaries[second]["availability_flag"]
                    else "exact_duplicate"
                )
                findings.append(
                    _redundancy_record(
                        first,
                        second,
                        relationship,
                        1.0,
                        int(frame[[first, second]].notna().all(axis=1).sum()),
                        "high",
                    )
                )
                seen.add((first, second, relationship))
                exact_pairs.add((first, second))

    varying = [
        column
        for column in columns
        if not summaries[column]["constant"]
    ]
    correlations = frame[varying].corr(method="pearson")

    for first_index, first in enumerate(varying):
        for second in varying[first_index + 1 :]:
            if (first, second) in exact_pairs:
                continue

            correlation = correlations.at[first, second]

            if not np.isfinite(correlation):
                continue

            affected = int(
                frame[[first, second]].notna().all(axis=1).sum()
            )

            if abs(abs(correlation) - 1.0) <= (
                PERFECT_CORRELATION_TOLERANCE
            ):
                relationship = (
                    "perfect_positive_affine"
                    if correlation > 0
                    else "perfect_negative_affine"
                )
                priority = "high"
            elif abs(correlation) >= HIGH_CORRELATION_THRESHOLD:
                relationship = "high_correlation"
                priority = "medium"
            else:
                continue

            key = (first, second, relationship)

            if key not in seen:
                findings.append(
                    _redundancy_record(
                        first,
                        second,
                        relationship,
                        correlation,
                        affected,
                        priority,
                    )
                )
                seen.add(key)

    boolean_columns = [
        column
        for column in columns
        if summaries[column]["boolean_like"]
        and not summaries[column]["constant"]
    ]

    for first_index, first in enumerate(boolean_columns):
        for second in boolean_columns[first_index + 1 :]:
            pair = frame[[first, second]].dropna()

            if pair.empty:
                continue

            first_values = pair[first].to_numpy()
            second_values = pair[second].to_numpy()

            if np.all(first_values + second_values == 1):
                relationship = "boolean_complement"
                priority = "high"
            elif (
                np.all((first_values * second_values) == 0)
                and np.any(first_values == 1)
                and np.any(second_values == 1)
            ):
                relationship = "boolean_mutually_exclusive"
                priority = "medium"
            else:
                continue

            key = (first, second, relationship)

            if key not in seen:
                findings.append(
                    _redundancy_record(
                        first,
                        second,
                        relationship,
                        1.0,
                        len(pair),
                        priority,
                    )
                )
                seen.add(key)

    ordering_candidates = [
        column
        for column in varying
        if any(token in column for token in ("rank", "share", "ratio"))
    ]

    for first_index, first in enumerate(ordering_candidates):
        first_metric = first.split("_", 1)[0]

        for second in ordering_candidates[first_index + 1 :]:
            if second.split("_", 1)[0] != first_metric:
                continue

            pair = frame[[first, second]].dropna()

            if len(pair) < 2:
                continue

            correlation = pair.corr(method="spearman").iloc[0, 1]

            if (
                np.isfinite(correlation)
                and abs(correlation)
                >= ORDERING_EQUIVALENCE_THRESHOLD
            ):
                key = (first, second, "ordering_equivalent")

                if key not in seen:
                    findings.append(
                        _redundancy_record(
                            first,
                            second,
                            "ordering_equivalent",
                            correlation,
                            len(pair),
                            "medium",
                        )
                    )
                    seen.add(key)

    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        findings,
        key=lambda item: (
            priority_order[item["suggested_review_priority"]],
            item["relationship_type"],
            item["features"],
        ),
    )


def temporal_availability_flag(feature: str) -> str | None:
    if feature.startswith("has_"):
        return feature
    if "_delta_3" in feature:
        return "has_history_3"
    if "_delta_2" in feature:
        return "has_history_2"
    if "_delta_1" in feature:
        return (
            "has_previous_board_observation"
            if feature.startswith("board_total_")
            else "has_previous_observation"
        )
    if "rolling_std_3" in feature or "rolling_mean_3" in feature:
        return "has_rolling_window_3"
    if "rolling_mean_2" in feature:
        return "has_previous_observation"
    if "momentum_1" in feature or "acceleration_1" in feature:
        return "has_momentum_1"
    if "momentum_3" in feature:
        return "has_previous_observation"
    if "influx_rate_1" in feature or "outflow_rate_1" in feature:
        return "has_previous_observation"
    if "board_change_volatility" in feature:
        return "has_previous_board_observation"
    if "observations_since_became_leader" in feature:
        metric = feature.split("_", 1)[0]
        return f"has_{metric}_ever_led"
    return None


def ambiguous_zero_fallbacks(
    temporal_features: Iterable[str],
    available_columns: Iterable[str],
) -> list[dict[str, str]]:
    columns = set(available_columns)
    findings: list[dict[str, str]] = []

    for feature in sorted(temporal_features):
        if feature.startswith("has_"):
            continue
        if (
            "leader_persistence" in feature
            or "observations_since_leader_change" in feature
        ):
            continue
        if not any(token in feature for token in TEMPORAL_TOKENS):
            continue

        flag = temporal_availability_flag(feature)

        if flag is None or flag not in columns:
            findings.append(
                {
                    "feature": feature,
                    "expected_availability_flag": flag or "none mapped",
                    "reason": (
                        "history-dependent feature can use deterministic "
                        "zero without a matching availability indicator"
                    ),
                }
            )

    return findings


def progress_statistics(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
) -> list[dict[str, Any]]:
    bucket_order = [name for name, _, _ in PROGRESS_BUCKETS]
    records: list[dict[str, Any]] = []

    for feature in feature_columns:
        for bucket in bucket_order:
            values = frame.loc[
                frame["progress_bucket"].eq(bucket),
                feature,
            ].dropna()
            stats = _basic_stats(values.to_numpy(dtype=float))
            records.append(
                {
                    "feature": feature,
                    "progress_bucket": bucket,
                    **stats,
                }
            )

    return records


def label_diagnostics(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    square_count: int,
) -> list[dict[str, Any]]:
    required = {
        "round_id",
        "observation_index",
        "square_index",
        "won",
        "outcome_source",
    }

    if not required <= set(frame.columns) or frame.empty:
        return []

    records: list[dict[str, Any]] = []

    for source in sorted(frame["outcome_source"].dropna().unique()):
        if not str(source).strip():
            continue

        source_frame = frame.loc[
            frame["outcome_source"].eq(source)
        ].sort_values(
            ["round_id", "observation_index", "square_index"]
        )

        if source_frame.empty or not source_frame["won"].eq(1).any():
            continue

        group_sizes = source_frame.groupby(
            ["round_id", "observation_index"],
            sort=False,
        ).size()

        if not group_sizes.eq(square_count).all():
            continue

        observation_count = len(group_sizes)
        won_matrix = (
            pd.to_numeric(source_frame["won"], errors="coerce")
            .fillna(0)
            .to_numpy(dtype=int)
            .reshape(observation_count, square_count)
            .astype(bool)
        )
        valid_winner_rows = won_matrix.sum(axis=1) == 1
        winner_indices = np.argmax(won_matrix, axis=1)
        round_ids = (
            source_frame["round_id"]
            .to_numpy()
            .reshape(observation_count, square_count)[:, 0]
        )

        for feature in feature_columns:
            values = source_frame[feature].to_numpy(
                dtype=float
            ).reshape(observation_count, square_count)
            row_indices = np.arange(observation_count)
            winner_values = values[row_indices, winner_indices]
            winner_valid = (
                valid_winner_rows & np.isfinite(winner_values)
            )
            loser_mask = (
                ~won_matrix & np.isfinite(values)
            )
            loser_values = values[loser_mask]
            winner_values = winner_values[winner_valid]

            if not len(winner_values) or not len(loser_values):
                continue

            all_winners = values[row_indices, winner_indices]
            percentiles = (
                np.sum(values < all_winners[:, None], axis=1)
                + 0.5
                * np.sum(values == all_winners[:, None], axis=1)
            ) / square_count
            loser_counts = loser_mask.sum(axis=1)
            loser_sums = np.where(loser_mask, values, 0.0).sum(axis=1)
            loser_means = np.divide(
                loser_sums,
                loser_counts,
                out=np.full(observation_count, np.nan),
                where=loser_counts > 0,
            )
            diagnostic_valid = (
                winner_valid & np.isfinite(loser_means)
            )
            observation_differences = (
                all_winners[diagnostic_valid]
                - loser_means[diagnostic_valid]
            )
            difference_rounds = round_ids[diagnostic_valid]
            winner_mean = float(np.mean(winner_values))
            loser_mean = float(np.mean(loser_values))
            mean_difference = winner_mean - loser_mean
            round_differences: list[float] = []

            if len(observation_differences):
                differences = pd.DataFrame(
                    {
                        "round_id": difference_rounds,
                        "difference": observation_differences,
                    }
                )
                round_differences = (
                    differences.groupby("round_id")["difference"]
                    .mean()
                    .tolist()
                )

            nonzero_rounds = [
                value
                for value in round_differences
                if value != 0
            ]
            expected_sign = np.sign(mean_difference)
            direction_consistency = (
                float(
                    np.mean(
                        np.sign(nonzero_rounds) == expected_sign
                    )
                )
                if nonzero_rounds and expected_sign != 0
                else None
            )
            records.append(
                {
                    "outcome_source": str(source),
                    "feature": feature,
                    "winner_count": int(len(winner_values)),
                    "loser_count": int(len(loser_values)),
                    "winner_mean": winner_mean,
                    "loser_mean": loser_mean,
                    "mean_difference": mean_difference,
                    "standardized_mean_difference": (
                        standardized_mean_difference(
                            winner_values,
                            loser_values,
                        )
                    ),
                    "winner_median": float(np.median(winner_values)),
                    "loser_median": float(np.median(loser_values)),
                    "winner_percentile_rank_mean": (
                        float(np.mean(percentiles[winner_valid]))
                        if winner_valid.any()
                        else None
                    ),
                    "direction_consistency_across_rounds": (
                        direction_consistency
                    ),
                    "round_count": len(round_differences),
                }
            )

    return sorted(
        records,
        key=lambda item: (
            item["outcome_source"],
            item["feature"],
        ),
    )


def flatten_feature_summary(
    summary: dict[str, Any],
) -> dict[str, Any]:
    flattened = {
        key: value
        for key, value in summary.items()
        if key != "observation_balanced"
    }
    flattened.update(
        {
            f"observation_balanced_{key}": value
            for key, value in summary["observation_balanced"].items()
        }
    )
    return flattened
