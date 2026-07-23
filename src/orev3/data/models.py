from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


SquareValues = Annotated[list[int], Field(min_length=25, max_length=25)]


class BoardState(BaseModel):
    """Decoded global ORE board state."""

    model_config = ConfigDict(frozen=True)

    round_id: int
    start_slot: int
    end_slot: int
    production_cost_ema: int | None = None


class RoundState(BaseModel):
    """Decoded state for one ORE mining round."""

    model_config = ConfigDict(frozen=True)

    round_id: int

    deployed_lamports: SquareValues
    mass: SquareValues
    miner_counts: SquareValues

    motherlode: int | None = None
    total_miners: int | None = None
    total_vaulted: int | None = None
    total_winnings: int | None = None

    entropy: int | None = None


class ObserverSnapshot(BaseModel):
    """
    Immutable point-in-time observation.

    Raw observations should be preserved exactly as seen by the Observer.
    Derived metrics belong in the feature layer, not here.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: int = 1

    observed_at_utc: datetime
    rpc_slot: int

    board: BoardState
    round: RoundState
