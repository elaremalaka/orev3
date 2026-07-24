from __future__ import annotations

from orev3.historical.models import (
    NormalizedSnapshot,
    RoundLifecycleIndexRecord,
)
from orev3.replay.loader import (
    load_round_observations,
)
from orev3.replay.models import (
    ReplayPoint,
    ReplayRoundSummary,
    ReplaySelection,
)


U64_MAX = (2 ** 64) - 1


def snapshot_to_replay_point(
    snapshot: NormalizedSnapshot,
) -> ReplayPoint:
    """
    Convert one normalized historical observation into
    a strategy-visible ReplayPoint.

    Finalized outcome metadata is intentionally absent.
    """

    start_slot = (
        snapshot.board.start_slot
    )

    raw_end_slot = (
        snapshot.board.end_slot
    )

    if raw_end_slot == U64_MAX:
        end_slot = None
        slots_remaining = None
    else:
        end_slot = raw_end_slot

        slots_remaining = max(
            end_slot
            - snapshot.rpc_slot,
            0,
        )

    slots_elapsed = max(
        snapshot.rpc_slot
        - start_slot,
        0,
    )

    return ReplayPoint(
        round_id=(
            snapshot.board.round_id
        ),
        observed_at_utc=(
            snapshot.observed_at_utc
        ),
        rpc_slot=(
            snapshot.rpc_slot
        ),
        start_slot=start_slot,
        end_slot=end_slot,
        slots_elapsed=(
            slots_elapsed
        ),
        slots_remaining=(
            slots_remaining
        ),
        collector_session_id=(
            snapshot.collector_session_id
        ),
        board=(
            snapshot.board
        ),
        treasury=(
            snapshot.treasury
        ),
        round=(
            snapshot.round
        ),
        source_file=(
            snapshot.source_file
        ),
        source_line_number=(
            snapshot.source_line_number
        ),
    )


def summarize_round(
    lifecycle: RoundLifecycleIndexRecord,
) -> ReplayRoundSummary:
    """
    Produce a strategy-safe summary.

    Final outcome fields are deliberately excluded.
    """

    return ReplayRoundSummary(
        round_id=(
            lifecycle.round_id
        ),
        start_slot=(
            lifecycle.start_slot
        ),
        end_slot=(
            lifecycle.end_slot
        ),
        observation_count=(
            lifecycle.observation_count
        ),
        first_rpc_slot=(
            lifecycle.first_observed_rpc_slot
        ),
        last_rpc_slot=(
            lifecycle.last_observed_rpc_slot
        ),
        first_observed_at_utc=(
            lifecycle.first_observed_at_utc
        ),
        last_observed_at_utc=(
            lifecycle.last_observed_at_utc
        ),
        coverage_status=(
            lifecycle
            .quality
            .coverage_status
        ),
    )


def select_at_or_before_slot(
    lifecycle: RoundLifecycleIndexRecord,
    target_rpc_slot: int,
) -> ReplayPoint:
    """
    Select the latest observation whose rpc_slot is less
    than or equal to the requested slot.

    This prevents using a future observation.

    Because raw RPC slots can regress, chronological
    observation order is preserved and eligible snapshots
    are filtered by their observed rpc_slot.
    """

    snapshots = load_round_observations(
        lifecycle
    )

    eligible = [
        snapshot
        for snapshot in snapshots
        if (
            snapshot.rpc_slot
            <= target_rpc_slot
        )
    ]

    if not eligible:
        raise ValueError(
            f"No observation for round "
            f"{lifecycle.round_id} "
            f"at or before RPC slot "
            f"{target_rpc_slot}"
        )

    # Select the closest observed RPC slot that does
    # not exceed the target.
    #
    # RPC observations may temporarily regress, so simply
    # choosing the latest snapshot chronologically could
    # select an older slot farther from the requested
    # decision point.
    best_rpc_slot = max(
        snapshot.rpc_slot
        for snapshot in eligible
    )

    closest = [
        snapshot
        for snapshot in eligible
        if snapshot.rpc_slot
        == best_rpc_slot
    ]

    # If the same slot was observed multiple times,
    # prefer the latest observation of that exact slot.
    selected = closest[-1]

    return snapshot_to_replay_point(
        selected
    )


def select_by_slots_remaining(
    lifecycle: RoundLifecycleIndexRecord,
    requested_slots_remaining: int,
    max_slot_distance: int | None = None,
) -> ReplaySelection:
    """
    Select the closest historical observation available
    at or before the requested decision boundary.

    No observation after the target slot may be used.

    max_slot_distance optionally defines the maximum
    acceptable difference between the requested and
    actual replay point.
    """

    if requested_slots_remaining < 0:
        raise ValueError(
            "requested_slots_remaining "
            "must be >= 0"
        )

    if (
        max_slot_distance is not None
        and max_slot_distance < 0
    ):
        raise ValueError(
            "max_slot_distance "
            "must be >= 0"
        )

    if lifecycle.end_slot is None:
        raise ValueError(
            f"Round {lifecycle.round_id} "
            "has no usable end_slot."
        )

    target_rpc_slot = (
        lifecycle.end_slot
        - requested_slots_remaining
    )

    point = select_at_or_before_slot(
        lifecycle=lifecycle,
        target_rpc_slot=target_rpc_slot,
    )

    actual_slots_remaining = (
        point.slots_remaining
    )

    exact_match = (
        actual_slots_remaining
        == requested_slots_remaining
    )

    slot_distance = (
        abs(
            actual_slots_remaining
            - requested_slots_remaining
        )
        if (
            actual_slots_remaining
            is not None
        )
        else None
    )

    within_tolerance = (
        True
        if max_slot_distance is None
        else (
            slot_distance is not None
            and slot_distance
            <= max_slot_distance
        )
    )

    return ReplaySelection(
        requested_slots_remaining=(
            requested_slots_remaining
        ),
        replay_point=point,
        exact_slot_match=exact_match,
        slot_distance=slot_distance,
        max_slot_distance=(
            max_slot_distance
        ),
        within_tolerance=(
            within_tolerance
        ),
    )

