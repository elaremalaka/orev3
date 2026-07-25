from __future__ import annotations

from orev3.historical.models import (
    RoundLifecycleIndexRecord,
)
from orev3.strategies.models import (
    StrategyEvaluation,
)
from orev3.experiments.models import (
    ScoredStrategyDecision,
)


def score_evaluation(
    evaluation: StrategyEvaluation,
    lifecycle: RoundLifecycleIndexRecord,
) -> ScoredStrategyDecision:
    """
    Score a completed strategy evaluation against the
    finalized outcome.

    The strategy decision has already been produced before
    this function is called.

    Finalized outcome information is therefore used only
    for scoring.
    """

    outcome = (
        lifecycle.finalized_outcome
    )

    if outcome is None:
        raise ValueError(
            f"Round {lifecycle.round_id} "
            "has no finalized outcome."
        )

    decision = evaluation.decision

    selected_squares = [
        allocation.square
        for allocation
        in decision.allocations
    ]

    allocation_weights = {
        allocation.square:
            allocation.weight
        for allocation
        in decision.allocations
    }

    winning_square = (
        outcome.winning_square
    )

    if (
        decision.action
        == "participate"
        and winning_square
        is not None
    ):
        selected_winning_square = (
            winning_square
            in selected_squares
        )

        winning_square_weight = (
            allocation_weights.get(
                winning_square,
                0.0,
            )
        )

    else:
        selected_winning_square = None
        winning_square_weight = 0.0

    motherlode_raw = (
        outcome.round_motherlode
    )

    if (
        motherlode_raw > 0
        and winning_square
        is not None
        and decision.action
        == "participate"
    ):
        selected_motherlode_winner = (
            winning_square
            in selected_squares
        )
    else:
        selected_motherlode_winner = None

    return ScoredStrategyDecision(
        round_id=(
            lifecycle.round_id
        ),
        strategy_name=(
            decision.strategy_name
        ),
        strategy_version=(
            decision.strategy_version
        ),
        requested_slots_remaining=(
            evaluation
            .requested_slots_remaining
        ),
        actual_slots_remaining=(
            evaluation
            .actual_slots_remaining
        ),
        replay_slot_distance=(
            evaluation
            .replay_slot_distance
        ),
        replay_within_tolerance=(
            evaluation
            .replay_within_tolerance
        ),
        action=decision.action,
        selected_squares=(
            selected_squares
        ),
        allocation_weights=(
            allocation_weights
        ),
        winning_square=(
            winning_square
        ),
        selected_winning_square=(
            selected_winning_square
        ),
        winning_square_weight=(
            winning_square_weight
        ),
        round_motherlode_raw=(
            motherlode_raw
        ),
        selected_motherlode_winner=(
            selected_motherlode_winner
        ),
        outcome_source=(
            lifecycle
            .finalized_outcome_source
        ),
    )
