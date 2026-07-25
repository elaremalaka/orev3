from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    square_statistics: pd.DataFrame
    square_heatmap: pd.DataFrame
    geometry_statistics: pd.DataFrame
    feature_correlations: pd.DataFrame
    missingness: pd.DataFrame


def _safe_lift(win_rate: pd.Series, baseline: float) -> pd.Series:
    if baseline == 0:
        return pd.Series(np.nan, index=win_rate.index, dtype=float)
    return win_rate / baseline


def compute_square_statistics(frame: pd.DataFrame) -> pd.DataFrame:
    rounds = int(frame["round_id"].nunique())
    baseline_win_rate = 1.0 / 25.0

    grouped = frame.groupby("square_index", sort=True)
    result = grouped.agg(
        board_row=("board_row", "first"),
        board_column=("board_column", "first"),
        rounds_observed=("round_id", "nunique"),
        wins=("won", "sum"),
        win_rate=("won", "mean"),
        mean_miners=("miner_count", "mean"),
        median_miners=("miner_count", "median"),
        min_miners=("miner_count", "min"),
        max_miners=("miner_count", "max"),
        mean_miner_share=("miner_share", "mean"),
        mean_rank_ascending=("miner_rank_ascending", "mean"),
        bottom4_rate=("is_bottom4_miners", "mean"),
        top4_rate=("is_top4_miners", "mean"),
        empty_rate=("is_empty", "mean"),
        mean_neighbor_miners=("orthogonal_neighbor_mean_miners", "mean"),
        mean_distance_from_center=("distance_from_center", "mean"),
        is_corner=("is_corner", "first"),
        is_edge=("is_edge", "first"),
        is_center=("is_center", "first"),
    ).reset_index()

    result["expected_wins_uniform"] = rounds * baseline_win_rate
    result["win_rate_lift_vs_uniform"] = _safe_lift(
        result["win_rate"],
        baseline_win_rate,
    )
    result["wins_minus_uniform"] = (
        result["wins"] - result["expected_wins_uniform"]
    )
    return result


def compute_square_heatmap(
    square_statistics: pd.DataFrame,
) -> pd.DataFrame:
    heatmap = square_statistics[
        [
            "square_index",
            "board_row",
            "board_column",
            "wins",
            "win_rate",
            "win_rate_lift_vs_uniform",
            "mean_miners",
            "mean_miner_share",
        ]
    ].copy()
    return heatmap.sort_values(["board_row", "board_column"]).reset_index(
        drop=True
    )


def _geometry_label(frame: pd.DataFrame) -> pd.Series:
    labels = np.full(len(frame), "interior", dtype=object)
    labels[frame["is_corner"].to_numpy(dtype=bool)] = "corner"
    labels[frame["is_edge"].to_numpy(dtype=bool)] = "edge"
    labels[frame["is_center"].to_numpy(dtype=bool)] = "center"
    return pd.Series(labels, index=frame.index, name="geometry")


def compute_geometry_statistics(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["geometry"] = _geometry_label(working)

    grouped = working.groupby("geometry", sort=False)
    result = grouped.agg(
        rows=("square_index", "size"),
        unique_squares=("square_index", "nunique"),
        rounds=("round_id", "nunique"),
        wins=("won", "sum"),
        row_win_rate=("won", "mean"),
        mean_miners=("miner_count", "mean"),
        median_miners=("miner_count", "median"),
        mean_miner_share=("miner_share", "mean"),
        mean_rank_ascending=("miner_rank_ascending", "mean"),
        bottom4_rate=("is_bottom4_miners", "mean"),
        top4_rate=("is_top4_miners", "mean"),
        empty_rate=("is_empty", "mean"),
        mean_neighbor_miners=("orthogonal_neighbor_mean_miners", "mean"),
        mean_distance_from_center=("distance_from_center", "mean"),
    ).reset_index()

    total_squares = 25
    result["uniform_win_share"] = result["unique_squares"] / total_squares
    total_wins = result["wins"].sum()
    result["observed_win_share"] = (
        result["wins"] / total_wins if total_wins else np.nan
    )
    result["win_share_lift_vs_uniform"] = (
        result["observed_win_share"] / result["uniform_win_share"]
    )

    order = {"corner": 0, "edge": 1, "interior": 2, "center": 3}
    result["_order"] = result["geometry"].map(order)
    return result.sort_values("_order").drop(columns="_order").reset_index(
        drop=True
    )


def compute_feature_correlations(frame: pd.DataFrame) -> pd.DataFrame:
    candidate_columns = [
        "won",
        "square_index",
        "board_row",
        "board_column",
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
        "round_motherlode_raw",
        "actual_slots_remaining",
        "replay_slot_distance",
        "exact_slot_match",
    ]
    available = [column for column in candidate_columns if column in frame.columns]
    numeric = frame[available].copy()

    for column in numeric.select_dtypes(include=["bool"]).columns:
        numeric[column] = numeric[column].astype(int)

    correlations = numeric.corr(method="pearson", min_periods=2)
    if "won" not in correlations:
        return pd.DataFrame(
            columns=[
                "feature",
                "correlation_with_won",
                "absolute_correlation",
                "non_null_rows",
            ]
        )

    result = (
        correlations["won"]
        .drop(labels=["won"], errors="ignore")
        .rename("correlation_with_won")
        .reset_index()
        .rename(columns={"index": "feature"})
    )
    result["absolute_correlation"] = result[
        "correlation_with_won"
    ].abs()
    result["non_null_rows"] = result["feature"].map(
        lambda column: int(frame[column].notna().sum())
    )
    return result.sort_values(
        ["absolute_correlation", "feature"],
        ascending=[False, True],
    ).reset_index(drop=True)


def compute_missingness(frame: pd.DataFrame) -> pd.DataFrame:
    rows = len(frame)
    result = pd.DataFrame(
        {
            "column": frame.columns,
            "missing_rows": [int(frame[column].isna().sum()) for column in frame],
        }
    )
    result["total_rows"] = rows
    result["missing_rate"] = (
        result["missing_rows"] / rows if rows else np.nan
    )
    return result.sort_values(
        ["missing_rate", "column"],
        ascending=[False, True],
    ).reset_index(drop=True)


def analyze_square_dataset(frame: pd.DataFrame) -> AnalysisResult:
    square_statistics = compute_square_statistics(frame)
    return AnalysisResult(
        square_statistics=square_statistics,
        square_heatmap=compute_square_heatmap(square_statistics),
        geometry_statistics=compute_geometry_statistics(frame),
        feature_correlations=compute_feature_correlations(frame),
        missingness=compute_missingness(frame),
    )
