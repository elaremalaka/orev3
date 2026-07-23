from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


SquareValues = Annotated[
    list[int],
    Field(min_length=25, max_length=25),
]


class BoardState(BaseModel):
    """Decoded global ORE board state."""

    model_config = ConfigDict(frozen=True)

    round_id: int
    start_slot: int
    end_slot: int
    production_cost_ema: int | None = None


class TreasuryState(BaseModel):
    """Decoded global ORE Treasury state."""

    model_config = ConfigDict(frozen=True)

    motherlode: int


class RoundState(BaseModel):
    """Decoded state for one ORE mining round."""

    model_config = ConfigDict(frozen=True)

    round_id: int

    deployed_lamports: SquareValues
    mass: SquareValues
    miner_counts: SquareValues

    slot_hash_hex: str
    expires_at: int

    motherlode: int

    rewards: SquareValues

    total_vaulted: int
    total_winnings: int
    total_miners: int

    top_miner: str

    entropy: int | None = None


class ObserverSnapshot(BaseModel):
    """
    Immutable point-in-time observation.

    Raw observations should be preserved exactly as seen by the Observer.
    Derived metrics belong in the feature layer.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: int = 1

    observed_at_utc: datetime
    rpc_slot: int

    board: BoardState
    treasury: TreasuryState
    round: RoundState
