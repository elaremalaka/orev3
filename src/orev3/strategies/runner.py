from __future__ import annotations

from orev3.historical.models import (
    RoundLifecycleIndexRecord,
)
from orev3.replay.engine import (
    select_by_slots_remaining,
)
from orev3.strategies.base import (
    Strategy,
)
from orev3.strategies.models import (
    StrategyEvaluation,
)


def evaluate_strategy(
    strategy: Strategy,
    lifecycle: RoundLifecycleIndexRecord,
    requested_slots_remaining: int,
    max_slot_distance: int | None = 3,
) -> StrategyEvaluation:
    """
    Evaluate one strategy at one historical replay point.

    Finalized outcomes are not passed to the strategy.
    """

    selection = (
        select_by_slots_remaining(
            lifecycle=lifecycle,
            requested_slots_remaining=(
                requested_slots_remaining
            ),
            max_slot_distance=(
                max_slot_distance
            ),
        )
    )

    decision = strategy.evaluate(
        selection.replay_point
    )

    return StrategyEvaluation(
        round_id=(
            lifecycle.round_id
        ),
        requested_slots_remaining=(
            requested_slots_remaining
        ),
        actual_slots_remaining=(
            selection
            .replay_point
            .slots_remaining
        ),
        replay_slot_distance=(
            selection.slot_distance
        ),
        replay_within_tolerance=(
            selection.within_tolerance
        ),
        decision=decision,
    )
