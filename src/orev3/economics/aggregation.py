from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def longest_losing_streak(values: np.ndarray) -> int:
    longest = current = 0
    for value in values:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def maximum_drawdown(values: np.ndarray) -> int:
    cumulative = np.cumsum(values, dtype=np.int64)
    path = np.r_[0, cumulative]
    peaks = np.maximum.accumulate(path)
    return int(np.max(peaks - path))


def _trimmed_mean(values: np.ndarray, fraction: float = 0.05) -> float:
    if not len(values):
        return 0.0
    ordered = np.sort(values)
    trim = int(len(ordered) * fraction)
    if trim == 0 or trim * 2 >= len(ordered):
        return float(ordered.mean())
    return float(ordered[trim:-trim].mean())


def _ore_concentration(frame: pd.DataFrame, fraction: float) -> float | None:
    by_round = (
        frame.groupby("round_id", sort=False)["ore_earned"].sum().sort_values(
            ascending=False
        )
    )
    total = float(by_round.sum())
    if total <= 0:
        return None
    count = max(1, int(np.ceil(len(by_round) * fraction)))
    return float(by_round.iloc[:count].sum() / total)


def economic_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "opportunities_evaluated": 0,
            "rounds_evaluated": 0,
        }
    deployed = frame["deployment_lamports"].to_numpy(dtype=np.int64)
    gross = frame["gross_sol_return_lamports"].to_numpy(dtype=np.int64)
    net_before = frame["net_sol_before_fees_lamports"].to_numpy(dtype=np.int64)
    net_after = frame["net_sol_after_fees_lamports"].to_numpy(dtype=np.int64)
    fees = frame["transaction_cost_lamports"].to_numpy(dtype=np.int64)
    ore = frame["ore_earned"].to_numpy(dtype=float)
    total_deployed = int(deployed.sum())
    total_ore = float(ore.sum())
    mother_ore = float(frame.loc[frame["motherlode"], "ore_earned"].sum())
    return {
        "opportunities_evaluated": len(frame),
        "rounds_evaluated": int(frame["round_id"].nunique()),
        "participation_rate": float(frame["participated"].mean()),
        "selected_squares_per_opportunity": int(frame["square_count"].iloc[0]),
        "winner_hit_rate": float(frame["winner_hit"].mean()),
        "total_sol_deployed_lamports": total_deployed,
        "gross_sol_return_lamports": int(gross.sum()),
        "net_sol_before_fees_lamports": int(net_before.sum()),
        "transaction_cost_lamports": int(fees.sum()),
        "net_sol_after_fees_lamports": int(net_after.sum()),
        "roi_before_fees": (
            float(net_before.sum() / total_deployed) if total_deployed else None
        ),
        "roi_after_fees": (
            float(net_after.sum() / total_deployed) if total_deployed else None
        ),
        "average_net_sol_lamports_per_opportunity": float(net_after.mean()),
        "median_net_sol_lamports_per_opportunity": float(np.median(net_after)),
        "trimmed_mean_net_sol_lamports_per_opportunity": _trimmed_mean(net_after),
        "profitable_opportunity_rate": float(np.mean(net_after > 0)),
        "maximum_drawdown_lamports": maximum_drawdown(net_after),
        "longest_losing_streak": longest_losing_streak(net_after),
        "total_ore_earned": total_ore,
        "ore_per_sol_deployed": (
            total_ore / (total_deployed / 1_000_000_000)
            if total_deployed
            else None
        ),
        "ore_per_opportunity": float(ore.mean()),
        "median_ore_per_opportunity": float(np.median(ore)),
        "motherlode_ore_share": (
            mother_ore / total_ore if total_ore > 0 else None
        ),
        "ore_concentration_top_1_percent_rounds": _ore_concentration(frame, 0.01),
        "ore_concentration_top_5_percent_rounds": _ore_concentration(frame, 0.05),
        "ore_concentration_top_10_percent_rounds": _ore_concentration(frame, 0.10),
    }


def segment_frames(frame: pd.DataFrame) -> list[tuple[str, str, pd.DataFrame]]:
    records: list[tuple[str, str, pd.DataFrame]] = [
        ("full_oos", "all", frame),
        (
            "validation_aggregate",
            "validation",
            frame.loc[frame["split_kind"].eq("validation")],
        ),
        (
            "final_holdout",
            "holdout",
            frame.loc[frame["split_kind"].eq("holdout")],
        ),
        (
            "exclude_motherlode",
            "true",
            frame.loc[~frame["motherlode"]],
        ),
    ]
    for fold, group in frame.groupby("fold", sort=True):
        records.append(("fold", str(fold), group))
    for source, group in frame.groupby("outcome_source", sort=True):
        records.append(("outcome_source", str(source), group))
    return records
