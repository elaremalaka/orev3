from __future__ import annotations

import numpy as np
import pandas as pd

from orev3.economics.aggregation import (
    economic_metrics,
    longest_losing_streak,
    maximum_drawdown,
    segment_frames,
)
from orev3.economics.bootstrap import (
    paired_round_bootstrap,
    round_bootstrap_interval,
)
from orev3.economics.schemas import EconomicAssumptions
from orev3.economics.simulator import simulate_bankroll


def test_roi_ore_efficiency_and_concentration(
    simulated_frame: pd.DataFrame,
) -> None:
    metrics = economic_metrics(simulated_frame)
    assert metrics["opportunities_evaluated"] == 4
    assert metrics["total_sol_deployed_lamports"] == 4000
    assert metrics["net_sol_before_fees_lamports"] == 0
    assert metrics["net_sol_after_fees_lamports"] == -20
    assert metrics["roi_after_fees"] == -0.005
    assert metrics["total_ore_earned"] == 1.0
    assert metrics["ore_per_sol_deployed"] == 250_000.0
    assert metrics["motherlode_ore_share"] == 1.0


def test_drawdown_and_losing_streak() -> None:
    values = np.array([-10, -5, 20, -4, -3, -2, 10])
    assert maximum_drawdown(values) == 15
    assert longest_losing_streak(values) == 3


def test_segment_aggregation_separates_sources(
    simulated_frame: pd.DataFrame,
) -> None:
    segments = {
        (name, value): len(frame)
        for name, value, frame in segment_frames(simulated_frame)
    }
    assert segments[("outcome_source", "observed")] == 2
    assert segments[("outcome_source", "enriched")] == 2
    assert segments[("final_holdout", "holdout")] == 0


def test_bootstrap_reproducibility(
    simulated_frame: pd.DataFrame,
) -> None:
    first = round_bootstrap_interval(
        simulated_frame,
        value_column="net_sol_after_fees_lamports",
        seed=7,
        samples=100,
    )
    second = round_bootstrap_interval(
        simulated_frame,
        value_column="net_sol_after_fees_lamports",
        seed=7,
        samples=100,
    )
    assert first == second


def test_paired_difference(
    simulated_frame: pd.DataFrame,
) -> None:
    baseline = simulated_frame.copy()
    baseline["net_sol_after_fees_lamports"] -= 10
    result = paired_round_bootstrap(
        simulated_frame, baseline, seed=4, samples=50
    )
    assert result["estimate"] == 10.0
    assert result["low"] == 10.0
    assert result["high"] == 10.0


def test_insufficient_bankroll_skips_without_negative_balance(
    simulated_frame: pd.DataFrame,
    assumptions: EconomicAssumptions,
) -> None:
    frame = simulated_frame.copy()
    frame["strategy"] = "test"
    frame["deployment_lamports"] = 1_000_000
    frame["deploy_cost_lamports"] = 5_000
    frame["net_sol_after_fees_lamports"] = -1_005_000
    path = simulate_bankroll(
        frame,
        starting_bankroll_lamports=100,
        assumptions=assumptions,
    )
    assert not path["participated"].any()
    assert path["bankroll_after_lamports"].eq(100).all()


def test_sequential_bankroll_is_chronological(
    simulated_frame: pd.DataFrame,
    assumptions: EconomicAssumptions,
) -> None:
    frame = simulated_frame.sample(frac=1, random_state=2)
    frame["deployment_lamports"] = 1
    frame["deploy_cost_lamports"] = 0
    frame["net_sol_after_fees_lamports"] = 0
    path = simulate_bankroll(
        frame,
        starting_bankroll_lamports=100_000,
        assumptions=assumptions,
    )
    keys = list(
        path[["round_id", "observation_index"]].itertuples(index=False, name=None)
    )
    assert keys == sorted(keys)
