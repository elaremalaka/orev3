from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from orev3.modeling.data import EXPECTED_SQUARES, OBSERVATION_KEY


def normalize_observation_probabilities(
    values: np.ndarray,
    frame: pd.DataFrame,
) -> np.ndarray:
    probabilities = np.asarray(values, dtype=float).copy()
    if len(probabilities) != len(frame) or not np.isfinite(probabilities).all():
        raise ValueError("Probability input is wrong-sized or non-finite")
    probabilities = np.clip(probabilities, 0.0, None)
    result = np.empty_like(probabilities)
    for indices in frame.groupby(OBSERVATION_KEY, sort=False).indices.values():
        total = probabilities[indices].sum()
        result[indices] = (
            probabilities[indices] / total
            if total > 0
            else 1.0 / len(indices)
        )
    return result


def rank_predictions(
    frame: pd.DataFrame,
    scores: np.ndarray,
    probabilities: np.ndarray | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = frame.reset_index(drop=True)
    scores = np.asarray(scores, dtype=float)
    if len(scores) != len(frame) or not np.isfinite(scores).all():
        raise ValueError("Scores are wrong-sized or non-finite")
    if probabilities is not None:
        probabilities = normalize_observation_probabilities(probabilities, frame)
    row_records: list[pd.DataFrame] = []
    observation_records: list[dict[str, Any]] = []
    columns = [
        "round_id",
        "observation_index",
        "square_index",
        "winning_square",
        "outcome_source",
        "won",
        "round_progress",
    ]
    for _, group in frame.groupby(OBSERVATION_KEY, sort=False):
        if len(group) != EXPECTED_SQUARES or int(group["won"].sum()) != 1:
            raise ValueError("Ranking group must have 25 rows and one winner")
        positions = group.index.to_numpy()
        group_scores = scores[positions]
        square_indices = group["square_index"].to_numpy(dtype=int)
        order = np.lexsort((square_indices, -group_scores))
        ranks = np.empty(len(group), dtype=int)
        ranks[order] = np.arange(1, len(group) + 1)
        winner_position = int(np.flatnonzero(group["won"].to_numpy(dtype=int))[0])
        winner_rank = int(ranks[winner_position])
        selected_position = int(order[0])
        probability = (
            float(probabilities[positions[winner_position]])
            if probabilities is not None
            else None
        )
        ranked = group.loc[:, columns].copy()
        ranked["score"] = group_scores
        ranked["predicted_rank"] = ranks
        ranked["probability"] = (
            probabilities[positions] if probabilities is not None else np.nan
        )
        row_records.append(ranked)
        observation_records.append(
            {
                "round_id": int(group["round_id"].iloc[0]),
                "observation_index": int(group["observation_index"].iloc[0]),
                "outcome_source": str(group["outcome_source"].iloc[0]),
                "round_progress": float(group["round_progress"].iloc[0]),
                "winning_square": int(group["winning_square"].iloc[0]),
                "selected_square": int(square_indices[selected_position]),
                "winner_rank": winner_rank,
                "reciprocal_rank": 1.0 / winner_rank,
                "ndcg": 1.0 / np.log2(winner_rank + 1.0),
                "winner_percentile": (EXPECTED_SQUARES - winner_rank)
                / (EXPECTED_SQUARES - 1),
                "winner_probability": probability,
                "top_1_hit": int(winner_rank <= 1),
                "top_2_hit": int(winner_rank <= 2),
                "top_3_hit": int(winner_rank <= 3),
                "top_5_hit": int(winner_rank <= 5),
            }
        )
    return pd.concat(row_records).sort_index(), pd.DataFrame(observation_records)


def calibration_summary(
    ranked_rows: pd.DataFrame,
    *,
    bins: int = 10,
) -> dict[str, Any] | None:
    if ranked_rows["probability"].isna().all():
        return None
    working = ranked_rows.dropna(subset=["probability"]).copy()
    unique = working["probability"].nunique()
    working["bin"] = (
        0
        if unique <= 1
        else pd.qcut(
            working["probability"],
            q=min(bins, unique),
            labels=False,
            duplicates="drop",
        )
    )
    records = []
    ece = 0.0
    for bin_index, group in working.groupby("bin", observed=True):
        predicted = float(group["probability"].mean())
        observed = float(group["won"].mean())
        fraction = len(group) / len(working)
        ece += fraction * abs(predicted - observed)
        records.append(
            {
                "bin": int(bin_index),
                "rows": len(group),
                "minimum_probability": float(group["probability"].min()),
                "maximum_probability": float(group["probability"].max()),
                "mean_probability": predicted,
                "observed_rate": observed,
            }
        )
    return {"expected_calibration_error": ece, "bins": records}


def aggregate_metrics(
    observations: pd.DataFrame,
    ranked_rows: pd.DataFrame,
) -> dict[str, Any]:
    ranks = observations["winner_rank"].to_numpy(dtype=float)
    result: dict[str, Any] = {
        "observation_count": len(observations),
        "round_count": int(observations["round_id"].nunique()),
        "top_1_accuracy": float(np.mean(ranks <= 1)),
        "top_2_hit_rate": float(np.mean(ranks <= 2)),
        "top_3_hit_rate": float(np.mean(ranks <= 3)),
        "top_5_hit_rate": float(np.mean(ranks <= 5)),
        "mean_reciprocal_rank": float(observations["reciprocal_rank"].mean()),
        "mean_winner_rank": float(np.mean(ranks)),
        "median_winner_rank": float(np.median(ranks)),
        "mean_ndcg": float(observations["ndcg"].mean()),
        "mean_winner_percentile": float(
            observations["winner_percentile"].mean()
        ),
    }
    if (
        not ranked_rows.empty
        and "probability" in ranked_rows
        and not ranked_rows["probability"].isna().all()
    ):
        probabilities = ranked_rows["probability"].to_numpy(dtype=float)
        labels = ranked_rows["won"].to_numpy(dtype=float)
        winner_p = observations["winner_probability"].to_numpy(dtype=float)
        result.update(
            {
                "log_loss": float(-np.log(np.clip(winner_p, 1e-15, 1.0)).mean()),
                "brier_score": float(
                    ((probabilities - labels) ** 2)
                    .reshape(-1, EXPECTED_SQUARES)
                    .sum(axis=1)
                    .mean()
                ),
                "mean_winner_probability": float(winner_p.mean()),
                "calibration": calibration_summary(ranked_rows),
            }
        )
    return result


def round_bootstrap_interval(
    observations: pd.DataFrame,
    column: str,
    *,
    seed: int,
    samples: int = 500,
) -> dict[str, float]:
    by_round = observations.groupby("round_id")[column].mean().to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    estimates = np.empty(samples)
    for index in range(samples):
        estimates[index] = rng.choice(
            by_round, size=len(by_round), replace=True
        ).mean()
    low, high = np.quantile(estimates, [0.025, 0.975])
    return {"low": float(low), "high": float(high)}
