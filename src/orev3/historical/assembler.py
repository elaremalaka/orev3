from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from orev3.historical.models import (
    FinalizedRoundOutcome,
    LifecycleAssemblyResult,
    NormalizedSnapshot,
    RoundLifecycle,
    RoundQualityMetadata,
)


U64_MAX = (2 ** 64) - 1

DEFAULT_SIGNIFICANT_GAP_SECONDS = 5.0


def _is_finalized(
    snapshot: NormalizedSnapshot,
) -> bool:
    """
    Determine whether finalized protocol state was
    actually observed.

    We intentionally require explicit finalized-state
    indicators rather than inferring finalization from
    time or round transitions alone.
    """

    round_state = snapshot.round

    slot_hash_nonzero = (
        round_state.slot_hash_hex
        != ("00" * 32)
    )

    return any(
        [
            slot_hash_nonzero,
            round_state.entropy is not None,
            round_state.total_vaulted > 0,
            round_state.total_winnings > 0,
        ]
    )


def _build_finalized_outcome(
    snapshots: list[NormalizedSnapshot],
) -> FinalizedRoundOutcome | None:
    """
    Use the latest snapshot that explicitly contains
    finalized protocol state.
    """

    finalized = [
        snapshot
        for snapshot in snapshots
        if _is_finalized(snapshot)
    ]

    if not finalized:
        return None

    snapshot = finalized[-1]

    entropy = snapshot.round.entropy

    winning_square = (
        entropy % 25
        if entropy is not None
        else None
    )

    return FinalizedRoundOutcome(
        observed_at_utc=(
            snapshot.observed_at_utc
        ),
        rpc_slot=snapshot.rpc_slot,
        entropy=entropy,
        winning_square=winning_square,
        deployed_lamports=(
            snapshot.round.deployed_lamports
        ),
        miner_counts=(
            snapshot.round.miner_counts
        ),
        reward_buckets=(
            snapshot.round.rewards
        ),
        total_vaulted=(
            snapshot.round.total_vaulted
        ),
        total_winnings=(
            snapshot.round.total_winnings
        ),
        total_miners=(
            snapshot.round.total_miners
        ),
        round_motherlode=(
            snapshot.round.motherlode
        ),
        top_miner=(
            snapshot.round.top_miner
        ),
    )


def _coverage_status(
    snapshots: list[NormalizedSnapshot],
    start_slot: int,
    end_slot: int | None,
) -> str:
    """
    Classify observational coverage conservatively.

    This is a quality classification, not a claim that
    every individual Solana slot was observed.
    """

    if not snapshots:
        return "unknown"

    rpc_slots = [
        snapshot.rpc_slot
        for snapshot in snapshots
    ]

    first_slot = min(
        rpc_slots
    )

    last_slot = max(
        rpc_slots
    )

    # Allow a small observation margin because the
    # collector polls by wall-clock time rather than
    # synchronizing exactly to every Solana slot.
    start_seen = (
        first_slot
        <= start_slot + 5
    )

    if end_slot is None:
        return (
            "partial_end"
            if start_seen
            else "partial_both"
        )

    end_seen = (
        last_slot
        >= end_slot - 5
    )

    if start_seen and end_seen:
        return "complete"

    if not start_seen and end_seen:
        return "partial_start"

    if start_seen and not end_seen:
        return "partial_end"

    return "partial_both"


def _build_quality(
    snapshots: list[NormalizedSnapshot],
    start_slot: int,
    end_slot: int | None,
    significant_gap_threshold_seconds: float,
) -> RoundQualityMetadata:
    rpc_regressions: list[int] = []

    duplicate_rpc_slot_count = 0

    observation_gaps: list[
        float
    ] = []

    for previous, current in zip(
        snapshots,
        snapshots[1:],
    ):
        slot_delta = (
            current.rpc_slot
            - previous.rpc_slot
        )

        if slot_delta < 0:
            rpc_regressions.append(
                abs(slot_delta)
            )

        if slot_delta == 0:
            duplicate_rpc_slot_count += 1

        gap_seconds = (
            current.observed_at_utc
            - previous.observed_at_utc
        ).total_seconds()

        observation_gaps.append(
            gap_seconds
        )

    significant_gap_count = sum(
        1
        for gap in observation_gaps
        if gap
        > significant_gap_threshold_seconds
    )

    session_ids = {
        snapshot.collector_session_id
        for snapshot in snapshots
        if snapshot.collector_session_id
        is not None
    }

    initialization_state_observed = any(
        snapshot.board.end_slot
        == U64_MAX
        for snapshot in snapshots
    )

    finalized_state_observed = any(
        _is_finalized(snapshot)
        for snapshot in snapshots
    )

    return RoundQualityMetadata(
        coverage_status=_coverage_status(
            snapshots=snapshots,
            start_slot=start_slot,
            end_slot=end_slot,
        ),
        initialization_state_observed=(
            initialization_state_observed
        ),
        rpc_slot_regression_count=len(
            rpc_regressions
        ),
        largest_rpc_slot_regression=(
            max(rpc_regressions)
            if rpc_regressions
            else 0
        ),
        duplicate_rpc_slot_count=(
            duplicate_rpc_slot_count
        ),
        max_observation_gap_seconds=(
            max(observation_gaps)
            if observation_gaps
            else 0.0
        ),
        significant_gap_count=(
            significant_gap_count
        ),
        significant_gap_threshold_seconds=(
            significant_gap_threshold_seconds
        ),
        collector_session_count=(
            len(session_ids)
        ),
        finalized_state_observed=(
            finalized_state_observed
        ),
    )


def assemble_rounds(
    snapshots: list[NormalizedSnapshot],
    significant_gap_threshold_seconds: float = (
        DEFAULT_SIGNIFICANT_GAP_SECONDS
    ),
) -> LifecycleAssemblyResult:
    """
    Assemble normalized raw observations into
    reproducible per-round lifecycle records.

    Raw snapshots are preserved in observation_history.
    """

    grouped: dict[
        int,
        list[NormalizedSnapshot],
    ] = defaultdict(list)

    for snapshot in snapshots:
        grouped[
            snapshot.board.round_id
        ].append(
            snapshot
        )

    lifecycles: list[
        RoundLifecycle
    ] = []

    for round_id in sorted(
        grouped
    ):
        round_snapshots = sorted(
            grouped[round_id],
            key=lambda snapshot: (
                snapshot.observed_at_utc,
                snapshot.source_file,
                snapshot.source_line_number,
            ),
        )

        first = round_snapshots[0]
        last = round_snapshots[-1]

        valid_end_slots = [
            snapshot.board.end_slot
            for snapshot in round_snapshots
            if snapshot.board.end_slot
            != U64_MAX
        ]

        initialized_snapshots = [
            snapshot
            for snapshot in round_snapshots
            if snapshot.board.end_slot
            != U64_MAX
        ]

        # Board start_slot is provisional while end_slot still carries the
        # protocol's uninitialized sentinel.  Use the first initialized board
        # state as the canonical lifecycle boundary while retaining every
        # earlier observation in the replay history.
        start_slot = (
            initialized_snapshots[0].board.start_slot
            if initialized_snapshots
            else first.board.start_slot
        )

        end_slot = (
            valid_end_slots[-1]
            if valid_end_slots
            else None
        )

        collector_session_ids = sorted(
            {
                snapshot.collector_session_id
                for snapshot in round_snapshots
                if (
                    snapshot.collector_session_id
                    is not None
                )
            }
        )

        source_schema_versions = sorted(
            {
                snapshot.source_schema_version
                for snapshot in round_snapshots
            }
        )

        source_files = sorted(
            {
                snapshot.source_file
                for snapshot in round_snapshots
            }
        )

        quality = _build_quality(
            snapshots=round_snapshots,
            start_slot=start_slot,
            end_slot=end_slot,
            significant_gap_threshold_seconds=(
                significant_gap_threshold_seconds
            ),
        )

        finalized_outcome = (
            _build_finalized_outcome(
                round_snapshots
            )
        )

        lifecycles.append(
            RoundLifecycle(
                round_id=round_id,
                start_slot=start_slot,
                end_slot=end_slot,
                first_observed_at_utc=(
                    first.observed_at_utc
                ),
                last_observed_at_utc=(
                    last.observed_at_utc
                ),
                first_observed_rpc_slot=(
                    first.rpc_slot
                ),
                last_observed_rpc_slot=(
                    last.rpc_slot
                ),
                observation_count=len(
                    round_snapshots
                ),
                collector_session_ids=(
                    collector_session_ids
                ),
                source_schema_versions=(
                    source_schema_versions
                ),
                source_files=(
                    source_files
                ),
                first_observation=first,
                last_observation=last,
                observation_history=(
                    round_snapshots
                ),
                finalized_outcome=(
                    finalized_outcome
                ),
                finalized_outcome_source=(
                    "observed"
                    if finalized_outcome
                    is not None
                    else None
                ),
                finalized_outcome_capture_mode=(
                    "current_round"
                    if finalized_outcome
                    is not None
                    else None
                ),
                quality=quality,
            )
        )

    return LifecycleAssemblyResult(
        rounds=lifecycles,
        total_snapshots=len(
            snapshots
        ),
        total_rounds=len(
            lifecycles
        ),
    )
