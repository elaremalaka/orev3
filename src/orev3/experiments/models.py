from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScoredStrategyDecision(BaseModel):
    """
    Result of scoring one frozen historical strategy
    decision against the finalized round outcome.
    """

    model_config = ConfigDict(frozen=True)

    round_id: int

    strategy_name: str
    strategy_version: str

    requested_slots_remaining: int
    actual_slots_remaining: int | None

    replay_slot_distance: int | None
    replay_within_tolerance: bool

    action: str

    selected_squares: list[int]
    allocation_weights: dict[int, float]

    winning_square: int | None

    selected_winning_square: bool | None
    winning_square_weight: float

    round_motherlode_raw: int

    selected_motherlode_winner: bool | None

    outcome_source: str | None


class RejectedReplay(BaseModel):
    """
    Historical round excluded before strategy scoring
    because its replay point failed experiment quality
    requirements.
    """

    model_config = ConfigDict(frozen=True)

    round_id: int

    requested_slots_remaining: int

    actual_slots_remaining: int | None

    replay_slot_distance: int | None

    reason: str


class StrategyExperimentResult(BaseModel):
    """
    Aggregate results for one historical strategy
    experiment.
    """

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    strategy_version: str

    requested_slots_remaining: int
    max_slot_distance: int

    total_rounds: int

    accepted_rounds: int
    rejected_rounds: int

    participate_rounds: int
    skip_rounds: int

    scored_participations: int

    winning_square_hits: int
    winning_square_hit_rate: float | None

    motherlode_rounds: int
    motherlode_selection_hits: int

    decisions: list[
        ScoredStrategyDecision
    ]

    rejected: list[
        RejectedReplay
    ]
