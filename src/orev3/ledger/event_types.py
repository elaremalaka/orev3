from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    OBSERVATION_STARTED = "observation_started"
    BOARD_SNAPSHOT_OBSERVED = "board_snapshot_observed"
    ROUND_STATE_OBSERVED = "round_state_observed"
    OPPORTUNITY_CLOSED = "opportunity_closed"

    STRATEGY_EVALUATED = "strategy_evaluated"
    PAPER_DECISION_CREATED = "paper_decision_created"
    DEPLOYMENT_INTENT_CREATED = "deployment_intent_created"
    NO_DEPLOY_DECISION = "no_deploy_decision"

    DEPLOY_TRANSACTION_BUILT = "deploy_transaction_built"
    DEPLOY_TRANSACTION_SUBMITTED = "deploy_transaction_submitted"
    DEPLOY_TRANSACTION_CONFIRMED = "deploy_transaction_confirmed"
    DEPLOY_TRANSACTION_FAILED = "deploy_transaction_failed"
    DEPLOY_TRANSACTION_EXPIRED = "deploy_transaction_expired"

    WALLET_SNAPSHOT_BEFORE = "wallet_snapshot_before"
    WALLET_SNAPSHOT_AFTER = "wallet_snapshot_after"
    WALLET_SOL_DELTA_OBSERVED = "wallet_sol_delta_observed"
    WALLET_ORE_DELTA_OBSERVED = "wallet_ore_delta_observed"

    ROUND_REWARD_OBSERVED = "round_reward_observed"
    BASE_ORE_OBSERVED = "base_ore_observed"
    MOTHERLODE_ORE_OBSERVED = "motherlode_ore_observed"
    CLAIM_DETECTED = "claim_detected"
    CLAIM_ATTRIBUTED = "claim_attributed"
    CLAIM_UNATTRIBUTED = "claim_unattributed"

    RECONCILIATION_COMPLETE = "reconciliation_complete"
    RECONCILIATION_PARTIAL = "reconciliation_partial"
    RECONCILIATION_FAILED = "reconciliation_failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


TRANSACTION_HISTORY_EVENTS = frozenset(
    {
        EventType.DEPLOY_TRANSACTION_BUILT,
        EventType.DEPLOY_TRANSACTION_SUBMITTED,
        EventType.DEPLOY_TRANSACTION_CONFIRMED,
        EventType.DEPLOY_TRANSACTION_FAILED,
        EventType.DEPLOY_TRANSACTION_EXPIRED,
    }
)
