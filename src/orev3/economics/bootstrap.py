from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def round_bootstrap_interval(
    frame: pd.DataFrame,
    *,
    value_column: str,
    seed: int,
    samples: int,
) -> dict[str, float]:
    by_round = frame.groupby("round_id", sort=False)[value_column].mean()
    if by_round.empty:
        raise ValueError("Cannot bootstrap an empty frame")
    values = by_round.to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    estimates = np.empty(samples, dtype=float)
    for index in range(samples):
        estimates[index] = rng.choice(
            values, size=len(values), replace=True
        ).mean()
    low, median, high = np.quantile(estimates, [0.025, 0.5, 0.975])
    return {
        "estimate": float(values.mean()),
        "low": float(low),
        "median": float(median),
        "high": float(high),
    }


def paired_round_bootstrap(
    candidate: pd.DataFrame,
    baseline: pd.DataFrame,
    *,
    seed: int,
    samples: int,
) -> dict[str, Any]:
    keys = ["round_id", "observation_index"]
    merged = candidate[keys + ["net_sol_after_fees_lamports"]].merge(
        baseline[keys + ["net_sol_after_fees_lamports"]],
        on=keys,
        suffixes=("_candidate", "_baseline"),
        validate="one_to_one",
    )
    merged["difference"] = (
        merged["net_sol_after_fees_lamports_candidate"]
        - merged["net_sol_after_fees_lamports_baseline"]
    )
    interval = round_bootstrap_interval(
        merged,
        value_column="difference",
        seed=seed,
        samples=samples,
    )
    return {
        "paired_opportunities": len(merged),
        "paired_rounds": int(merged["round_id"].nunique()),
        **interval,
    }
