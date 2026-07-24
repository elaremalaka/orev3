from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from orev3.historical.models import (
    NormalizedBoardState,
    NormalizedRoundState,
    NormalizedTreasuryState,
)


class ReplayPoint(BaseModel):
    """
    One strategy-visible point in historical time.

    This contains only information available from the
    selected historical snapshot.
    """

    model_config = ConfigDict(frozen=True)

    round_id: int

    observed_at_utc: datetime
    rpc_slot: int

    start_slot: int
    end_slot: int | None

    slots_elapsed: int | None
    slots_remaining: int | None

    collector_session_id: str | None

    board: NormalizedBoardState
    treasury: NormalizedTreasuryState
    round: NormalizedRoundState

    source_file: str
    source_line_number: int


class ReplaySelection(BaseModel):
    """
    Result of selecting a point from a historical round.
    """

    model_config = ConfigDict(frozen=True)

    requested_slots_remaining: int | None

    replay_point: ReplayPoint

    exact_slot_match: bool

    slot_distance: int | None

    max_slot_distance: int | None

    within_tolerance: bool


class ReplayRoundSummary(BaseModel):
    """
    Strategy-safe summary of one replayable round.

    Finalized outcome is deliberately excluded.
    """

    model_config = ConfigDict(frozen=True)

    round_id: int

    start_slot: int
    end_slot: int | None

    observation_count: int

    first_rpc_slot: int
    last_rpc_slot: int

    first_observed_at_utc: datetime
    last_observed_at_utc: datetime

    coverage_status: str
