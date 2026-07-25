from __future__ import annotations

from orev3.economics.schemas import (
    AccountingResult,
    EconomicAssumptions,
    FinalRoundEconomics,
)
from orev3.economics.sizing import allocate_lamports


def account_price_taking(
    *,
    outcome: FinalRoundEconomics,
    winner_rank: int,
    square_count: int,
    allocation_rule: str,
    deployment_lamports: int,
    assumptions: EconomicAssumptions,
) -> AccountingResult:
    outcome.validate()
    if not 1 <= winner_rank <= 25:
        raise ValueError("winner_rank must be in 1..25")
    allocations = allocate_lamports(
        deployment_lamports, square_count, allocation_rule
    )
    winner_hit = winner_rank <= square_count
    winning_allocation = allocations[winner_rank - 1] if winner_hit else 0
    denominator = outcome.winning_square_deployed_lamports
    gross_return = (
        winning_allocation * outcome.total_winnings_lamports // denominator
    )
    ore_raw = winning_allocation * outcome.round_motherlode_raw // denominator
    deploy_cost = (
        assumptions.deploy_fee_lamports
        + assumptions.priority_fee_lamports
        + assumptions.failed_transaction_cost_lamports
        if deployment_lamports > 0
        else 0
    )
    claim_cost = (
        assumptions.claim_fee_lamports
        if gross_return > 0 or ore_raw > 0
        else 0
    )
    before_fees = gross_return - deployment_lamports
    transaction_cost = deploy_cost + claim_cost
    return AccountingResult(
        deployment_lamports=deployment_lamports,
        gross_sol_return_lamports=gross_return,
        net_sol_before_fees_lamports=before_fees,
        deploy_cost_lamports=deploy_cost,
        claim_cost_lamports=claim_cost,
        transaction_cost_lamports=transaction_cost,
        net_sol_after_deploy_lamports=before_fees - deploy_cost,
        net_sol_after_fees_lamports=before_fees - transaction_cost,
        ore_earned_raw=ore_raw,
        ore_earned=ore_raw / assumptions.ore_raw_per_ore,
        winner_hit=winner_hit,
        motherlode=outcome.round_motherlode_raw > 0,
    )
