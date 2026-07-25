from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd

from orev3.economics.schemas import (
    EconomicAssumptions,
    FinalRoundEconomics,
)
from orev3.economics.sizing import allocate_lamports
from orev3.economics.strategy_selection import deterministic_random_ranking


REQUIRED_HEURISTICS = (
    "least_miner_count",
    "least_deployed",
    "lowest_miner_share",
    "highest_reward",
    "existing_least_crowded",
)
MODEL_CONFIGURATIONS = (
    ("logistic_regression", "all_72", "logistic_all_72"),
    (
        "logistic_regression",
        "conservative_deduplicated",
        "logistic_conservative_52",
    ),
    ("random_forest", "all_72", "random_forest_all_72"),
    (
        "random_forest",
        "conservative_deduplicated",
        "random_forest_conservative_52",
    ),
    ("hist_gradient_boosting", "all_72", "hist_gradient_boosting_all_72"),
    (
        "hist_gradient_boosting",
        "conservative_deduplicated",
        "hist_gradient_boosting_conservative_52",
    ),
)


def strategy_definitions() -> list[dict[str, Any]]:
    definitions = [
        {
            "strategy": name,
            "kind": "heuristic",
            "ranking_source": "RFC-004 out-of-sample prediction artifact",
            "available": True,
        }
        for name in REQUIRED_HEURISTICS
    ]
    definitions.extend(
        {
            "strategy": output_name,
            "kind": "model",
            "model": model,
            "feature_set": feature_set,
            "ranking_source": "RFC-004 out-of-sample prediction artifact",
            "probabilities_used": False,
            "available": True,
        }
        for model, feature_set, output_name in MODEL_CONFIGURATIONS
    )
    definitions.append(
        {
            "strategy": "seeded_random_20260725",
            "kind": "random",
            "seed": 20260725,
            "ranking_source": "RFC-004 out-of-sample prediction artifact",
            "available": True,
        }
    )
    definitions.extend(
        [
            {
                "strategy": "average_rank_random_forest_least_miner",
                "kind": "ensemble",
                "available": False,
                "exclusion_reason": "RFC-004 artifact lacks full model rank vectors",
            },
            {
                "strategy": "average_rank_random_forest_least_crowded",
                "kind": "ensemble",
                "available": False,
                "exclusion_reason": "RFC-004 artifact lacks full model rank vectors",
            },
            {
                "strategy": "average_rank_three_models",
                "kind": "ensemble",
                "available": False,
                "exclusion_reason": "RFC-004 artifact lacks full model rank vectors",
            },
        ]
    )
    return definitions


def extract_strategy_rank_summaries(
    predictions: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    for name in REQUIRED_HEURISTICS:
        subset = predictions.loc[
            predictions["strategy"].eq(name)
            & predictions["feature_set"].eq("not_applicable")
        ].copy()
        results[name] = _validate_rank_summary(subset, name)
    for model, feature_set, output_name in MODEL_CONFIGURATIONS:
        subset = predictions.loc[
            predictions["strategy"].eq(model)
            & predictions["feature_set"].eq(feature_set)
        ].copy()
        results[output_name] = _validate_rank_summary(subset, output_name)
    random = predictions.loc[
        predictions["strategy"].eq("random")
        & predictions["feature_set"].eq("not_applicable")
    ].copy()
    results["seeded_random_20260725"] = _validate_rank_summary(
        random, "seeded_random_20260725"
    )
    return results


def _validate_rank_summary(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    keys = ["round_id", "observation_index"]
    if frame.empty:
        raise ValueError(f"Strategy prediction unavailable: {name}")
    if frame.duplicated(keys).any():
        raise ValueError(f"Duplicate prediction opportunity: {name}")
    if frame.groupby(keys).ngroups != 13_652:
        raise ValueError(f"Strategy {name} does not cover 13,652 OOS opportunities")
    return frame.sort_values(keys, kind="stable").reset_index(drop=True)


def random_rank_summary(
    base: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    result = base.copy()
    selected: list[int] = []
    ranks: list[int] = []
    for row in result.itertuples(index=False):
        ranking = deterministic_random_ranking(
            seed=seed,
            round_id=int(row.round_id),
            observation_index=int(row.observation_index),
        )
        selected.append(ranking[0])
        ranks.append(ranking.index(int(row.winning_square)) + 1)
    result["selected_square"] = selected
    result["winner_rank"] = ranks
    return result


def attach_outcomes(
    summary: pd.DataFrame,
    outcomes: dict[int, FinalRoundEconomics],
) -> pd.DataFrame:
    records = pd.DataFrame(
        [
            {
                "round_id": value.round_id,
                "economic_outcome_source": value.outcome_source,
                "winning_square_deployed_lamports": (
                    value.winning_square_deployed_lamports
                ),
                "total_winnings_lamports": value.total_winnings_lamports,
                "total_vaulted_lamports": value.total_vaulted_lamports,
                "total_deployed_lamports": value.total_deployed_lamports,
                "round_motherlode_raw": value.round_motherlode_raw,
            }
            for value in outcomes.values()
        ]
    )
    result = summary.merge(records, on="round_id", how="left", validate="many_to_one")
    required = [
        "winning_square_deployed_lamports",
        "total_winnings_lamports",
        "total_deployed_lamports",
        "round_motherlode_raw",
    ]
    if result[required].isna().any().any():
        raise ValueError("Missing finalized economics are not imputed")
    if not result["economic_outcome_source"].eq(result["outcome_source"]).all():
        raise ValueError("Prediction and economic outcome sources disagree")
    return result


def simulate_scenario(
    frame: pd.DataFrame,
    *,
    strategy: str,
    square_count: int,
    allocation_rule: str,
    deployment_lamports: int,
    assumptions: EconomicAssumptions,
) -> pd.DataFrame:
    result = frame.copy()
    source_models = (
        result["strategy"].copy()
        if "strategy" in result
        else pd.Series(strategy, index=result.index)
    )
    allocations = allocate_lamports(
        deployment_lamports, square_count, allocation_rule
    )
    ranks = result["winner_rank"].to_numpy(dtype=np.int64)
    hit = ranks <= square_count
    winner_allocation = np.zeros(len(result), dtype=np.int64)
    for rank, allocation in enumerate(allocations, 1):
        winner_allocation[ranks == rank] = allocation
    denominator = result["winning_square_deployed_lamports"].to_numpy(
        dtype=np.int64
    )
    winnings = result["total_winnings_lamports"].to_numpy(dtype=np.int64)
    gross = winner_allocation * winnings // denominator
    mother = result["round_motherlode_raw"].to_numpy(dtype=np.int64)
    ore_raw = np.zeros(len(result), dtype=np.int64)
    for index in np.flatnonzero(mother > 0):
        ore_raw[index] = (
            int(winner_allocation[index])
            * int(mother[index])
            // int(denominator[index])
        )
    deploy_cost = (
        assumptions.deploy_fee_lamports
        + assumptions.priority_fee_lamports
        + assumptions.failed_transaction_cost_lamports
        if deployment_lamports > 0
        else 0
    )
    claim_cost = np.where(
        (gross > 0) | (ore_raw > 0), assumptions.claim_fee_lamports, 0
    ).astype(np.int64)
    result["model"] = np.where(
        result["feature_set"].ne("not_applicable"),
        source_models,
        None,
    )
    result["strategy"] = strategy
    result["square_count"] = square_count
    result["allocation_rule"] = allocation_rule
    result["deployment_lamports"] = deployment_lamports
    result["participated"] = True
    result["winner_hit"] = hit
    result["gross_sol_return_lamports"] = gross
    result["net_sol_before_fees_lamports"] = gross - deployment_lamports
    result["deploy_cost_lamports"] = deploy_cost
    result["claim_cost_lamports"] = claim_cost
    result["transaction_cost_lamports"] = deploy_cost + claim_cost
    result["net_sol_after_deploy_lamports"] = (
        result["net_sol_before_fees_lamports"] - deploy_cost
    )
    result["net_sol_after_fees_lamports"] = (
        result["net_sol_before_fees_lamports"]
        - result["transaction_cost_lamports"]
    )
    result["ore_earned_raw"] = ore_raw
    result["ore_earned"] = ore_raw / assumptions.ore_raw_per_ore
    result["motherlode"] = mother > 0
    result["accounting_mode"] = assumptions.accounting_mode
    return result


def reference_opportunity_output(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "round_id",
        "observation_index",
        "fold",
        "split_kind",
        "outcome_source",
        "strategy",
        "model",
        "feature_set",
        "square_count",
        "allocation_rule",
        "deployment_lamports",
        "participated",
        "selected_square",
        "winning_square",
        "winner_hit",
        "gross_sol_return_lamports",
        "net_sol_before_fees_lamports",
        "deploy_cost_lamports",
        "claim_cost_lamports",
        "transaction_cost_lamports",
        "net_sol_after_fees_lamports",
        "ore_earned",
        "motherlode",
        "accounting_mode",
    ]
    result = frame.loc[:, columns].copy()
    result.rename(columns={"winning_square": "winner_square"}, inplace=True)
    result["selected_squares"] = result["selected_square"].map(
        lambda value: json.dumps([int(value)], separators=(",", ":"))
    )
    return result.drop(columns=["selected_square"])


def simulate_bankroll(
    frame: pd.DataFrame,
    *,
    starting_bankroll_lamports: int,
    assumptions: EconomicAssumptions,
) -> pd.DataFrame:
    ordered = frame.sort_values(
        ["round_id", "observation_index"], kind="stable"
    )
    bankroll = int(starting_bankroll_lamports)
    peak = bankroll
    records: list[dict[str, Any]] = []
    for row in ordered.itertuples(index=False):
        required = (
            int(row.deployment_lamports)
            + int(row.deploy_cost_lamports)
            + assumptions.claim_fee_lamports
        )
        participated = bankroll >= required
        start = bankroll
        net = int(row.net_sol_after_fees_lamports) if participated else 0
        bankroll += net
        if bankroll < 0:
            raise ValueError("Sequential bankroll became negative")
        peak = max(peak, bankroll)
        records.append(
            {
                "round_id": int(row.round_id),
                "observation_index": int(row.observation_index),
                "strategy": str(row.strategy),
                "starting_bankroll_lamports": starting_bankroll_lamports,
                "bankroll_before_lamports": start,
                "participated": participated,
                "net_sol_after_fees_lamports": net,
                "bankroll_after_lamports": bankroll,
                "peak_bankroll_lamports": peak,
                "drawdown_lamports": peak - bankroll,
                "ore_earned": float(row.ore_earned) if participated else 0.0,
            }
        )
    return pd.DataFrame(records)
