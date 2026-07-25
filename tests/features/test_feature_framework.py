from __future__ import annotations

import pytest

from orev3.features import create_default_pipeline
from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.registry import FeatureRegistry
from orev3.features.relative import (
    average_descending_rank,
)
from orev3.features.types import (
    BoardSnapshot,
    FeatureValues,
    SquareSnapshot,
)


def make_square(
    observation_index: int,
    miner_count: int,
    deployed_lamports: int,
    reward_raw: int = 0,
) -> SquareSnapshot:
    return SquareSnapshot(
        observation_index=observation_index,
        miner_count=miner_count,
        deployed_lamports=deployed_lamports,
        reward_raw=reward_raw,
        mass=0,
    )


def make_board(
    observation_index: int,
    squares: tuple[SquareSnapshot, ...],
) -> BoardSnapshot:
    return BoardSnapshot(
        round_id=100,
        observation_index=observation_index,
        observation_count=2,
        slots_remaining=10,
        squares=squares,
    )


def test_average_rank_handles_complete_tie() -> None:
    values = [0] * 25

    assert average_descending_rank(
        values,
        7,
    ) == 13.0


def test_average_rank_handles_partial_tie() -> None:
    values = [10, 8, 8, 5]

    assert average_descending_rank(
        values,
        0,
    ) == 1.0
    assert average_descending_rank(
        values,
        1,
    ) == 2.5
    assert average_descending_rank(
        values,
        2,
    ) == 2.5
    assert average_descending_rank(
        values,
        3,
    ) == 4.0


def test_pipeline_computes_raw_relative_and_delta() -> None:
    previous_squares = tuple(
        make_square(
            observation_index=0,
            miner_count=index + 1,
            deployed_lamports=(index + 1) * 100,
        )
        for index in range(25)
    )
    current_squares = tuple(
        make_square(
            observation_index=1,
            miner_count=index + 2,
            deployed_lamports=(index + 1) * 150,
        )
        for index in range(25)
    )

    board = make_board(
        observation_index=1,
        squares=current_squares,
    )

    context = FeatureContext(
        board=board,
        square_index=0,
        square_history=(
            previous_squares[0],
            current_squares[0],
        ),
    )

    output = create_default_pipeline().compute(
        context
    )

    assert output["miner_count"] == 2
    assert output["deployed_lamports"] == 150
    assert output["miner_delta_1"] == 1
    assert output["deployed_delta_1"] == 50
    assert output["has_previous_observation"] is True
    assert output["miner_share"] == pytest.approx(
        2 / sum(range(2, 27))
    )
    assert output["miner_average_rank"] == 25.0


def test_first_observation_has_zero_deltas() -> None:
    squares = tuple(
        make_square(
            observation_index=0,
            miner_count=1,
            deployed_lamports=100,
        )
        for _ in range(25)
    )
    board = make_board(
        observation_index=0,
        squares=squares,
    )
    context = FeatureContext(
        board=board,
        square_index=5,
        square_history=(squares[5],),
    )

    output = create_default_pipeline().compute(
        context
    )

    assert output["miner_delta_1"] == 0
    assert output["deployed_delta_1"] == 0
    assert output["has_previous_observation"] is False
    assert output["miner_average_rank"] == 13.0


class DuplicateFeatureOne(Feature):
    name = "duplicate_one"
    family = "test"
    output_columns = ("duplicate_column",)

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        del context
        return {"duplicate_column": 1}


class DuplicateFeatureTwo(Feature):
    name = "duplicate_two"
    family = "test"
    output_columns = ("duplicate_column",)

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        del context
        return {"duplicate_column": 2}


def test_registry_rejects_duplicate_columns() -> None:
    registry = FeatureRegistry(
        [DuplicateFeatureOne()]
    )

    with pytest.raises(
        ValueError,
        match="Duplicate feature output columns",
    ):
        registry.register(DuplicateFeatureTwo())
