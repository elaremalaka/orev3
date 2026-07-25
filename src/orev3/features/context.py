from __future__ import annotations

from dataclasses import dataclass

from orev3.features.types import BoardSnapshot, SquareSnapshot


@dataclass(frozen=True, slots=True)
class FeatureContext:
    board: BoardSnapshot
    square_index: int
    square_history: tuple[SquareSnapshot, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.square_index < 25:
            raise ValueError(
                f"square_index must be in [0, 24], got {self.square_index}"
            )

        if self.square_history:
            current = self.square_history[-1]

            if current is not self.square:
                raise ValueError(
                    "square_history must end with the current square snapshot"
                )

    @property
    def square(self) -> SquareSnapshot:
        return self.board.squares[self.square_index]

    @property
    def previous_square(self) -> SquareSnapshot | None:
        if len(self.square_history) < 2:
            return None

        return self.square_history[-2]

    @property
    def round_progress(self) -> float:
        if self.board.observation_count <= 1:
            return 0.0

        return self.board.observation_index / (
            self.board.observation_count - 1
        )
