from __future__ import annotations

from dataclasses import replace

import pytest

from orev3.economics.reward_accounting import account_price_taking
from orev3.economics.schemas import EconomicAssumptions, FinalRoundEconomics
from orev3.economics.sizing import allocate_lamports


def test_equal_allocation_and_residual() -> None:
    allocation = allocate_lamports(10, 3, "equal")
    assert allocation == (4, 3, 3)
    assert sum(allocation) == 10


def test_rank_decay_allocation_and_residual() -> None:
    allocation = allocate_lamports(101, 3, "rank_decay")
    assert sum(allocation) == 101
    assert allocation[0] > allocation[1] > allocation[2]


def test_negative_deployment_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        allocate_lamports(-1, 1, "equal")


def test_winning_square_proportional_return_and_fees(
    assumptions: EconomicAssumptions,
    outcome: FinalRoundEconomics,
) -> None:
    result = account_price_taking(
        outcome=outcome,
        winner_rank=1,
        square_count=1,
        allocation_rule="equal",
        deployment_lamports=1_000_000,
        assumptions=assumptions,
    )
    assert result.gross_sol_return_lamports == 10_000_000
    assert result.net_sol_before_fees_lamports == 9_000_000
    assert result.deploy_cost_lamports == 5_000
    assert result.claim_cost_lamports == 5_000
    assert result.net_sol_after_fees_lamports == 8_990_000
    assert result.ore_earned == 1.0


def test_losing_square_and_zero_reward(
    assumptions: EconomicAssumptions,
    outcome: FinalRoundEconomics,
) -> None:
    result = account_price_taking(
        outcome=outcome,
        winner_rank=2,
        square_count=1,
        allocation_rule="equal",
        deployment_lamports=1_000_000,
        assumptions=assumptions,
    )
    assert not result.winner_hit
    assert result.gross_sol_return_lamports == 0
    assert result.claim_cost_lamports == 0
    assert result.ore_earned == 0
    assert result.net_sol_after_fees_lamports == -1_005_000


def test_multi_square_rank_decay_reward_share(
    assumptions: EconomicAssumptions,
    outcome: FinalRoundEconomics,
) -> None:
    allocation = allocate_lamports(1_000_000, 3, "rank_decay")
    result = account_price_taking(
        outcome=outcome,
        winner_rank=2,
        square_count=3,
        allocation_rule="rank_decay",
        deployment_lamports=1_000_000,
        assumptions=assumptions,
    )
    assert result.winner_hit
    assert result.gross_sol_return_lamports == (
        allocation[1] * 1_000_000_000 // 100_000_000
    )


def test_zero_deployment_has_no_transaction(
    assumptions: EconomicAssumptions,
    outcome: FinalRoundEconomics,
) -> None:
    result = account_price_taking(
        outcome=outcome,
        winner_rank=1,
        square_count=1,
        allocation_rule="equal",
        deployment_lamports=0,
        assumptions=assumptions,
    )
    assert result.transaction_cost_lamports == 0
    assert result.net_sol_after_fees_lamports == 0


def test_missing_denominator_rejected(
    assumptions: EconomicAssumptions,
) -> None:
    outcome = FinalRoundEconomics(
        round_id=1,
        outcome_source="observed",
        winning_square=0,
        winning_square_deployed_lamports=0,
        total_winnings_lamports=1,
        total_vaulted_lamports=0,
        total_deployed_lamports=1,
        round_motherlode_raw=0,
    )
    with pytest.raises(ValueError, match="denominator"):
        account_price_taking(
            outcome=outcome,
            winner_rank=1,
            square_count=1,
            allocation_rule="equal",
            deployment_lamports=1,
            assumptions=assumptions,
        )


def test_non_finite_price_assumption_rejected(
    assumptions: EconomicAssumptions,
) -> None:
    invalid = replace(
        assumptions,
        ore_price_usd_scenarios=(float("nan"),),
    )
    with pytest.raises(ValueError, match="finite"):
        invalid.validate()
