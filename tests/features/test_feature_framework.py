from __future__ import annotations

import math

import pytest

from orev3.features import (
    create_default_pipeline,
    create_default_registry,
)
from orev3.features.base import Feature
from orev3.features.board_summary import summarize_board
from orev3.features.context import FeatureContext
from orev3.features.pipeline import FeaturePipeline
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


def test_board_summary_calculates_reusable_values() -> None:
    summary = summarize_board([10, 8, 8, 4])

    assert summary.total == 30
    assert summary.mean == 7.5
    assert summary.standard_deviation == pytest.approx(
        math.sqrt(4.75)
    )
    assert summary.leader == 10
    assert summary.average_ranks == (1.0, 2.5, 2.5, 4.0)


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


def test_relative_features_handle_zero_total_and_zero_variance() -> None:
    squares = tuple(
        make_square(
            observation_index=0,
            miner_count=0,
            deployed_lamports=0,
        )
        for _ in range(25)
    )
    context = FeatureContext(
        board=make_board(0, squares),
        square_index=7,
        square_history=(squares[7],),
    )

    output = create_default_pipeline().compute(context)

    for column in (
        "miner_share",
        "deployed_share",
        "miner_ratio_to_leader",
        "deployed_ratio_to_leader",
        "miner_ratio_to_mean",
        "deployed_ratio_to_mean",
        "miner_z_score",
        "deployed_z_score",
    ):
        assert output[column] == 0.0

    assert output["miner_average_rank"] == 13.0
    assert output["deployed_average_rank"] == 13.0


def test_relative_features_handle_leaders_and_partial_ties() -> None:
    miner_values = [10, 8, 8, 4] + [0] * 21
    deployed_values = [100, 50, 50, 25] + [0] * 21
    squares = tuple(
        make_square(0, miners, deployed)
        for miners, deployed in zip(
            miner_values,
            deployed_values,
            strict=True,
        )
    )

    leader = FeatureContext(
        board=make_board(0, squares),
        square_index=0,
        square_history=(squares[0],),
    )
    tied = FeatureContext(
        board=make_board(0, squares),
        square_index=1,
        square_history=(squares[1],),
    )

    leader_output = create_default_pipeline().compute(leader)
    tied_output = create_default_pipeline().compute(tied)

    assert leader_output["miner_ratio_to_leader"] == 1.0
    assert leader_output["deployed_ratio_to_leader"] == 1.0
    assert tied_output["miner_ratio_to_leader"] == pytest.approx(0.8)
    assert tied_output["deployed_ratio_to_leader"] == pytest.approx(0.5)
    assert tied_output["miner_average_rank"] == 2.5
    assert tied_output["deployed_average_rank"] == 2.5


def test_default_feature_columns_are_unique() -> None:
    columns = create_default_registry().output_columns

    assert len(columns) == len(set(columns))


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


class DuplicateWithinFeature(Feature):
    name = "duplicate_within"
    family = "test"
    output_columns = ("repeated", "repeated")

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        del context
        return {"repeated": 1}


def test_registry_rejects_duplicate_columns_within_feature() -> None:
    with pytest.raises(
        ValueError,
        match="Feature contains duplicate output columns",
    ):
        FeatureRegistry([DuplicateWithinFeature()])


class NonFiniteFeature(Feature):
    name = "non_finite"
    family = "test"
    output_columns = ("bad_value",)

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        del context
        return {"bad_value": float("nan")}


def test_pipeline_rejects_non_finite_output() -> None:
    squares = tuple(make_square(0, 0, 0) for _ in range(25))
    context = FeatureContext(
        board=make_board(0, squares),
        square_index=0,
        square_history=(squares[0],),
    )
    pipeline = FeaturePipeline(FeatureRegistry([NonFiniteFeature()]))

    with pytest.raises(ValueError, match="non-finite"):
        pipeline.compute(context)
