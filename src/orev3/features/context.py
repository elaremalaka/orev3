from __future__ import annotations

from dataclasses import dataclass

from orev3.features.types import BoardSnapshot, SquareSnapshot


@dataclass(frozen=True, slots=True)
class FeatureContext:
    board: BoardSnapshot
    square_index: int
    square_history: tuple[SquareSnapshot, ...]
    board_history: tuple[BoardSnapshot, ...] = ()

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

            observation_indices = [
                square.observation_index
                for square in self.square_history
            ]

            if observation_indices != sorted(observation_indices):
                raise ValueError(
                    "square_history must be ordered by observation_index"
                )

            if len(observation_indices) != len(set(observation_indices)):
                raise ValueError(
                    "square_history cannot contain duplicate observation indices"
                )

            if observation_indices[-1] > self.board.observation_index:
                raise ValueError(
                    "square_history cannot contain future observations"
                )

        if self.board_history:
            if self.board_history[-1] is not self.board:
                raise ValueError(
                    "board_history must end with the current board snapshot"
                )

            if any(
                board.round_id != self.board.round_id
                for board in self.board_history
            ):
                raise ValueError(
                    "board_history cannot cross round boundaries"
                )

            observation_indices = [
                board.observation_index
                for board in self.board_history
            ]

            if observation_indices != sorted(observation_indices):
                raise ValueError(
                    "board_history must be ordered by observation_index"
                )

            if len(observation_indices) != len(set(observation_indices)):
                raise ValueError(
                    "board_history cannot contain duplicate observation indices"
                )

            if observation_indices[-1] > self.board.observation_index:
                raise ValueError(
                    "board_history cannot contain future observations"
                )

    @property
    def square(self) -> SquareSnapshot:
        return self.board.squares[self.square_index]

    @property
    def previous_square(self) -> SquareSnapshot | None:
        return self.square_at_lag(1)

    def square_at_lag(
        self,
        lag: int,
    ) -> SquareSnapshot | None:
        if lag < 0:
            raise ValueError("lag cannot be negative")

        target_index = self.board.observation_index - lag

        return next(
            (
                square
                for square in reversed(self.square_history)
                if square.observation_index == target_index
            ),
            None,
        )

    def board_at_lag(
        self,
        lag: int,
    ) -> BoardSnapshot | None:
        if lag < 0:
            raise ValueError("lag cannot be negative")

        if lag == 0 and not self.board_history:
            return self.board

        target_index = self.board.observation_index - lag

        return next(
            (
                board
                for board in reversed(self.board_history)
                if board.observation_index == target_index
            ),
            None,
        )

    @property
    def round_progress(self) -> float:
        if self.board.observation_count <= 1:
            return 0.0

        return self.board.observation_index / (
            self.board.observation_count - 1
        )
