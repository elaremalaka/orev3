from __future__ import annotations

from dataclasses import dataclass

from orev3.experiments.models import (
    RejectedReplay,
    StrategyExperimentResult,
)
from orev3.experiments.scorer import (
    score_evaluation,
)
from orev3.historical.models import (
    RoundLifecycleIndexRecord,
)
from orev3.replay.engine import (
    select_by_slots_remaining,
)
from orev3.replay.models import (
    ReplaySelection,
)
from orev3.strategies.base import (
    Strategy,
)
from orev3.strategies.models import (
    StrategyEvaluation,
)


@dataclass(frozen=True)
class PreparedReplayCase:
    """
    One replay point resolved and validated before
    strategies are evaluated.

    The finalized lifecycle is retained only for scoring.
    It is never passed into Strategy.evaluate().
    """

    lifecycle: RoundLifecycleIndexRecord
    selection: ReplaySelection


@dataclass(frozen=True)
class PreparedReplayBatch:
    """
    Reusable replay batch for one decision boundary.

    Raw snapshot references are resolved only once.
    """

    total_rounds: int
    requested_slots_remaining: int
    max_slot_distance: int

    accepted: list[PreparedReplayCase]
    rejected: list[RejectedReplay]


def prepare_replay_batch(
    lifecycles: list[
        RoundLifecycleIndexRecord
    ],
    requested_slots_remaining: int,
    max_slot_distance: int = 3,
) -> PreparedReplayBatch:
    """
    Resolve and validate replay points once.

    This batch can then be reused across many strategies
    or random seeds without repeatedly reading raw JSONL.
    """

    accepted: list[
        PreparedReplayCase
    ] = []

    rejected: list[
        RejectedReplay
    ] = []

    for lifecycle in lifecycles:
        try:
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

        except ValueError as exc:
            rejected.append(
                RejectedReplay(
                    round_id=(
                        lifecycle.round_id
                    ),
                    requested_slots_remaining=(
                        requested_slots_remaining
                    ),
                    actual_slots_remaining=None,
                    replay_slot_distance=None,
                    reason=str(exc),
                )
            )

            continue

        if not selection.within_tolerance:
            rejected.append(
                RejectedReplay(
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
                    reason=(
                        "Replay point outside "
                        "configured slot tolerance."
                    ),
                )
            )

            continue

        if (
            lifecycle.finalized_outcome
            is None
        ):
            rejected.append(
                RejectedReplay(
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
                    reason=(
                        "Finalized outcome "
                        "unavailable for scoring."
                    ),
                )
            )

            continue

        accepted.append(
            PreparedReplayCase(
                lifecycle=lifecycle,
                selection=selection,
            )
        )

    return PreparedReplayBatch(
        total_rounds=len(
            lifecycles
        ),
        requested_slots_remaining=(
            requested_slots_remaining
        ),
        max_slot_distance=(
            max_slot_distance
        ),
        accepted=accepted,
        rejected=rejected,
    )


def run_prepared_experiment(
    strategy: Strategy,
    batch: PreparedReplayBatch,
) -> StrategyExperimentResult:
    """
    Evaluate and score one strategy using a prepared
    replay batch.

    Strategy decisions are produced before finalized
    outcomes are used for scoring.
    """

    decisions = []

    participate_rounds = 0
    skip_rounds = 0

    for replay_case in batch.accepted:
        lifecycle = (
            replay_case.lifecycle
        )

        selection = (
            replay_case.selection
        )

        # Only the strategy-visible ReplayPoint is passed
        # into the strategy.
        decision = strategy.evaluate(
            selection.replay_point
        )

        evaluation = StrategyEvaluation(
            round_id=(
                lifecycle.round_id
            ),
            requested_slots_remaining=(
                batch
                .requested_slots_remaining
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

        if decision.action == "participate":
            participate_rounds += 1
        else:
            skip_rounds += 1

        # The outcome becomes available only here,
        # after the decision has been frozen.
        scored = score_evaluation(
            evaluation=evaluation,
            lifecycle=lifecycle,
        )

        decisions.append(
            scored
        )

    participations = [
        decision
        for decision in decisions
        if decision.action
        == "participate"
    ]

    hits = sum(
        1
        for decision
        in participations
        if (
            decision
            .selected_winning_square
            is True
        )
    )

    scored_participations = len(
        participations
    )

    hit_rate = (
        hits / scored_participations
        if scored_participations
        else None
    )

    motherlode_rounds = sum(
        1
        for decision in decisions
        if (
            decision
            .round_motherlode_raw
            > 0
        )
    )

    motherlode_hits = sum(
        1
        for decision in decisions
        if (
            decision
            .selected_motherlode_winner
            is True
        )
    )

    return StrategyExperimentResult(
        strategy_name=strategy.name,
        strategy_version=(
            strategy.version
        ),
        requested_slots_remaining=(
            batch
            .requested_slots_remaining
        ),
        max_slot_distance=(
            batch.max_slot_distance
        ),
        total_rounds=(
            batch.total_rounds
        ),
        accepted_rounds=len(
            decisions
        ),
        rejected_rounds=len(
            batch.rejected
        ),
        participate_rounds=(
            participate_rounds
        ),
        skip_rounds=(
            skip_rounds
        ),
        scored_participations=(
            scored_participations
        ),
        winning_square_hits=hits,
        winning_square_hit_rate=(
            hit_rate
        ),
        motherlode_rounds=(
            motherlode_rounds
        ),
        motherlode_selection_hits=(
            motherlode_hits
        ),
        decisions=decisions,
        rejected=batch.rejected,
    )


def run_experiment(
    strategy: Strategy,
    lifecycles: list[
        RoundLifecycleIndexRecord
    ],
    requested_slots_remaining: int,
    max_slot_distance: int = 3,
) -> StrategyExperimentResult:
    """
    Convenience wrapper for a single strategy.

    Multi-strategy experiments should call
    prepare_replay_batch once and reuse the result.
    """

    batch = prepare_replay_batch(
        lifecycles=lifecycles,
        requested_slots_remaining=(
            requested_slots_remaining
        ),
        max_slot_distance=(
            max_slot_distance
        ),
    )

    return run_prepared_experiment(
        strategy=strategy,
        batch=batch,
    )
