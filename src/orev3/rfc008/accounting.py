from __future__ import annotations

from orev3.ledger.identifiers import deterministic_id
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.schemas import ArmDecision, OutcomeEvidence, RoundAccounting


def account_round(
    decision: ArmDecision,
    outcome: OutcomeEvidence,
    config: RFC008Config,
) -> RoundAccounting:
    allocation = decision.allocation_by_square.get(outcome.winner_square, 0)
    denominator = outcome.final_square_deployments[outcome.winner_square]
    if allocation and denominator <= 0:
        raise ValueError("Winning-square final deployment must be positive")
    gross = (
        allocation * outcome.total_winnings_lamports // denominator
        if allocation
        else 0
    )
    motherlode = (
        allocation * int(outcome.motherlode_raw) // denominator
        if allocation and outcome.motherlode_raw is not None
        else 0
    )
    deploy_fee = config.fees.deploy_fee_lamports if decision.participated else 0
    claim_fee = (
        config.fees.claim_fee_lamports
        if gross > 0 or motherlode > 0
        else 0
    )
    before = gross - decision.deployment_lamports
    after = before - deploy_fee - claim_fee
    deployed = decision.deployment_lamports
    return RoundAccounting(
        accounting_id=deterministic_id(
            "rfc008-round-accounting",
            config.configuration_fingerprint,
            decision.decision_id,
            outcome.outcome_id,
        ),
        experiment_id=config.experiment_id,
        round_id=decision.round_id,
        arm_id=decision.arm_id,
        decision_id=decision.decision_id,
        outcome_id=outcome.outcome_id,
        winner_selected=allocation > 0,
        deployed_lamports=deployed,
        gross_sol_return_lamports=gross,
        net_sol_before_fees_lamports=before,
        assumed_deploy_fee_lamports=deploy_fee,
        assumed_claim_fee_lamports=claim_fee,
        net_sol_after_fees_lamports=after,
        roi_before_fees=before / deployed if deployed else None,
        roi_after_fees=after / deployed if deployed else None,
        motherlode_ore_raw=motherlode if outcome.motherlode_raw is not None else None,
        base_ore_raw=None,
        total_ore_raw=None,
        accounting_mode=config.fees.accounting_mode,
    )
