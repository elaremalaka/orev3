from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SquareAllocation(BaseModel):
    """
    One proposed square allocation.

    Allocation values are strategy intent only.
    They do not trigger transactions.
    """

    model_config = ConfigDict(frozen=True)

    square: int = Field(
        ge=0,
        le=24,
    )

    weight: float = Field(
        gt=0,
    )


class StrategyDecision(BaseModel):
    """
    Structured output from a strategy.

    A strategy can either participate or skip.
    """

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    strategy_version: str

    action: Literal[
        "participate",
        "skip",
    ]

    allocations: list[
        SquareAllocation
    ] = []

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    reason: str

    metadata: dict[
        str,
        int
        | float
        | str
        | bool
        | None,
    ] = {}


class StrategyEvaluation(BaseModel):
    """
    One strategy decision at one historical replay point.

    This contains no finalized outcome.
    """

    model_config = ConfigDict(frozen=True)

    round_id: int

    requested_slots_remaining: int

    actual_slots_remaining: int | None

    replay_slot_distance: int | None

    replay_within_tolerance: bool

    decision: StrategyDecision
