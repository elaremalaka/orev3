from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SquareSnapshot:
    observation_index: int
    miner_count: int
    deployed_lamports: int
    reward_raw: int
    mass: int


@dataclass(frozen=True, slots=True)
class BoardSnapshot:
    round_id: int
    observation_index: int
    observation_count: int
    slots_remaining: int | None
    squares: tuple[SquareSnapshot, ...]

    def __post_init__(self) -> None:
        if len(self.squares) != 25:
            raise ValueError(
                "BoardSnapshot must contain exactly 25 squares; "
                f"received {len(self.squares)}"
            )


FeatureValues = Mapping[str, int | float | bool | None]
