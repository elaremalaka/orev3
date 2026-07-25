from __future__ import annotations

from orev3.collection.config import CollectionConfig
from orev3.collection.schemas import (
    FinalOutcome,
    PaperAccounting,
    PaperDecision,
)
from orev3.ledger.identifiers import deterministic_id


def account_paper_decision(
    decision: PaperDecision,
    outcome: FinalOutcome,
    config: CollectionConfig,
) -> PaperAccounting:
    allocation = decision.allocation_by_square.get(outcome.winner_square, 0)
    denominator = outcome.final_square_deployments[outcome.winner_square]
    if allocation and denominator <= 0:
        raise ValueError("Winning-square final deployment is unavailable")
    gross = allocation * outcome.total_winnings // denominator if allocation else 0
    motherlode = (
        allocation * int(outcome.motherlode_raw or 0) // denominator
        if allocation and outcome.motherlode_raw
        else 0
    )
    deploy_fee = (
        config.assumed_deploy_fee_lamports if decision.participated else 0
    )
    claim_fee = (
        config.assumed_claim_fee_lamports
        if gross > 0 or motherlode > 0
        else 0
    )
    before_fees = gross - decision.deployment_total_lamports
    return PaperAccounting(
        accounting_id=deterministic_id(
            "rfc007-paper-accounting",
            decision.decision_id,
            outcome.outcome_id,
            config.configuration_hash,
        ),
        opportunity_id=decision.opportunity_id,
        decision_id=decision.decision_id,
        outcome_id=outcome.outcome_id,
        winner_selected=allocation > 0,
        paper_deployed_lamports=decision.deployment_total_lamports,
        paper_gross_sol_return_lamports=gross,
        paper_net_sol_before_fees=before_fees,
        paper_assumed_deploy_fee=deploy_fee,
        paper_assumed_claim_fee=claim_fee,
        paper_net_sol_after_assumed_fees=before_fees - deploy_fee - claim_fee,
        paper_base_ore_raw=None,
        paper_motherlode_ore_raw=motherlode,
        paper_total_ore_raw=None,
        provenance={
            "paper_gross_sol_return_lamports": "reconstructed",
            "paper_net_sol_before_fees": "reconstructed",
            "paper_assumed_deploy_fee": "configured_assumption",
            "paper_assumed_claim_fee": "configured_assumption",
            "paper_net_sol_after_assumed_fees": "reconstructed",
            "paper_base_ore_raw": "unavailable",
            "paper_motherlode_ore_raw": "reconstructed",
            "paper_total_ore_raw": "unavailable",
        },
        classification="reconstructed_paper_not_wallet_realized",
    )
