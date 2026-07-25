from __future__ import annotations

import numpy as np
import pandas as pd

from orev3.modeling.baselines import baseline_scores
from orev3.modeling.metrics import (
    aggregate_metrics,
    calibration_summary,
    normalize_observation_probabilities,
    rank_predictions,
)


def _one_observation(winner: int = 4) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "round_id": [1] * 25,
            "observation_index": [0] * 25,
            "square_index": range(25),
            "winning_square": [winner] * 25,
            "outcome_source": ["observed"] * 25,
            "won": [int(index == winner) for index in range(25)],
            "round_progress": [0.5] * 25,
            "miner_count": range(25),
            "deployed_lamports": np.arange(25) * 10,
            "miner_share": np.arange(25) / 300,
            "reward_raw": np.arange(25),
        }
    )


def test_deterministic_tie_breaking_and_metric_correctness() -> None:
    frame = _one_observation(winner=4)
    ranked, observations = rank_predictions(frame, np.zeros(25))
    assert observations.loc[0, "selected_square"] == 0
    assert observations.loc[0, "winner_rank"] == 5
    assert observations.loc[0, "reciprocal_rank"] == 0.2
    metrics = aggregate_metrics(observations, ranked)
    assert metrics["top_1_accuracy"] == 0.0
    assert metrics["top_5_hit_rate"] == 1.0
    assert metrics["mean_winner_rank"] == 5.0


def test_top_k_and_mrr_for_perfect_ranking() -> None:
    frame = _one_observation(winner=24)
    scores = np.arange(25, dtype=float)
    ranked, observations = rank_predictions(frame, scores)
    metrics = aggregate_metrics(observations, ranked)
    assert metrics["top_1_accuracy"] == 1.0
    assert metrics["mean_reciprocal_rank"] == 1.0
    assert metrics["mean_ndcg"] == 1.0
    assert metrics["mean_winner_percentile"] == 1.0


def test_probability_normalization_with_zero_fallback() -> None:
    frame = pd.concat([_one_observation(), _one_observation()], ignore_index=True)
    frame.loc[25:, "observation_index"] = 1
    raw = np.r_[np.arange(25, dtype=float), np.zeros(25)]
    normalized = normalize_observation_probabilities(raw, frame)
    totals = pd.Series(normalized).groupby(frame["observation_index"]).sum()
    assert np.allclose(totals, 1.0)
    assert np.allclose(normalized[25:], 1 / 25)


def test_baseline_directions_and_uniform_probability() -> None:
    frame = _one_observation()
    least, _ = baseline_scores(frame, "least_miner_count")
    deployed, _ = baseline_scores(frame, "least_deployed")
    reward, _ = baseline_scores(frame, "highest_reward")
    uniform, probability = baseline_scores(frame, "uniform")
    assert np.argmax(least) == 0
    assert np.argmax(deployed) == 0
    assert np.argmax(reward) == 24
    assert np.all(uniform == 0)
    assert np.allclose(probability, 1 / 25)


def test_seeded_random_baseline_is_reproducible() -> None:
    frame = _one_observation()
    first, _ = baseline_scores(frame, "random", seed=7)
    second, _ = baseline_scores(frame, "random", seed=7)
    third, _ = baseline_scores(frame, "random", seed=8)
    assert np.array_equal(first, second)
    assert not np.array_equal(first, third)


def test_prediction_schema() -> None:
    frame = _one_observation()
    ranked, observations = rank_predictions(frame, np.arange(25))
    assert {
        "round_id",
        "observation_index",
        "winning_square",
        "selected_square",
        "winner_rank",
        "winner_probability",
        "outcome_source",
    } <= set(observations)
    assert {"score", "predicted_rank", "probability", "won"} <= set(ranked)


def test_calibration_uses_probability_quantiles() -> None:
    rows = pd.DataFrame(
        {
            "probability": np.linspace(0.01, 0.08, 100),
            "won": np.tile([0, 0, 0, 0, 1], 20),
        }
    )
    summary = calibration_summary(rows, bins=5)
    assert summary is not None
    assert len(summary["bins"]) == 5
    assert np.isfinite(summary["expected_calibration_error"])
