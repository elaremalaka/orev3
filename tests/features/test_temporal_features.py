from __future__ import annotations

import math
import statistics

import pytest

from orev3.features import create_default_pipeline
from orev3.features.context import FeatureContext
from orev3.features.types import BoardSnapshot, SquareSnapshot


def make_board(
    observation_index: int,
    miner_values: list[int],
    deployed_values: list[int] | None = None,
    reward_values: list[int] | None = None,
) -> BoardSnapshot:
    if deployed_values is None:
        deployed_values = [value * 10 for value in miner_values]
    if reward_values is None:
        reward_values = [0] * 25
    squares = tuple(
        SquareSnapshot(
            observation_index=observation_index,
            miner_count=miner,
            deployed_lamports=deployed,
            reward_raw=reward,
            mass=0,
        )
        for miner, deployed, reward in zip(
            miner_values,
            deployed_values,
            reward_values,
            strict=True,
        )
    )

    return BoardSnapshot(
        round_id=100,
        observation_index=observation_index,
        observation_count=4,
        slots_remaining=None,
        squares=squares,
    )


def make_context(
    boards: tuple[BoardSnapshot, ...],
    square_index: int = 0,
) -> FeatureContext:
    return FeatureContext(
        board=boards[-1],
        square_index=square_index,
        square_history=tuple(
            board.squares[square_index]
            for board in boards
        ),
        board_history=boards,
    )


def test_temporal_features_use_only_available_history() -> None:
    board = make_board(0, [5] * 25)

    output = create_default_pipeline().compute(
        make_context((board,))
    )

    assert output["miner_delta_1"] == 0
    assert output["miner_delta_2"] == 0
    assert output["miner_delta_3"] == 0
    assert output["has_previous_observation"] is False
    assert output["has_history_2"] is False
    assert output["has_history_3"] is False
    assert output["miner_rolling_mean_3"] == 5.0
    assert output["miner_ema_0_5"] == 5.0
    assert output["miner_momentum_3"] == 0.0
    assert output["miner_acceleration_1"] == 0
    assert output["miner_influx_rate_1"] == 0
    assert output["miner_outflow_rate_1"] == 0
    assert output["miner_board_change_volatility"] == 0.0
    assert output["miner_rolling_std_3"] == 0.0
    assert output["has_rolling_window_3"] is False
    assert output["miner_momentum_1"] == 0
    assert output["has_momentum_1"] is False
    assert output["board_total_miner_delta_1"] == 0
    assert output["has_previous_board_observation"] is False


def test_one_prior_observation_has_only_one_step_history() -> None:
    previous = make_board(0, [1] * 25)
    current = make_board(1, [3] * 25)

    output = create_default_pipeline().compute(
        make_context((previous, current))
    )

    assert output["miner_delta_1"] == 2
    assert output["has_previous_observation"] is True
    assert output["miner_delta_2"] == 0
    assert output["has_history_2"] is False
    assert output["miner_momentum_1"] == 0
    assert output["has_momentum_1"] is False
    assert output["has_previous_board_observation"] is True


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((1, 3, 8), 3),
        ((1, 5, 7), -2),
    ],
)
def test_momentum_is_current_delta_minus_previous_delta(
    values: tuple[int, int, int],
    expected: int,
) -> None:
    boards = tuple(
        make_board(index, [value] * 25)
        for index, value in enumerate(values)
    )

    output = create_default_pipeline().compute(make_context(boards))

    assert output["miner_momentum_1"] == expected
    assert output["has_momentum_1"] is True


def test_square_temporal_features_apply_to_all_three_metrics() -> None:
    boards = (
        make_board(0, [1] * 25, [10] * 25, [2] * 25),
        make_board(1, [3] * 25, [40] * 25, [5] * 25),
        make_board(2, [8] * 25, [90] * 25, [9] * 25),
    )

    output = create_default_pipeline().compute(make_context(boards))

    assert output["miner_delta_2"] == 7
    assert output["deployed_delta_2"] == 80
    assert output["reward_delta_2"] == 7
    assert output["reward_rolling_mean_3"] == pytest.approx(16 / 3)
    assert output["reward_rolling_std_3"] == pytest.approx(
        statistics.pstdev((2, 5, 9))
    )
    assert output["miner_momentum_1"] == 3
    assert output["deployed_momentum_1"] == 20
    assert output["reward_momentum_1"] == 1


def test_missing_observation_index_is_not_treated_as_one_step() -> None:
    first = make_board(0, [1] * 25)
    current = make_board(2, [5] * 25)

    output = create_default_pipeline().compute(
        make_context((first, current))
    )

    assert output["miner_delta_1"] == 0
    assert output["has_previous_observation"] is False
    assert output["miner_delta_2"] == 4
    assert output["has_history_2"] is True
    assert output["has_rolling_window_3"] is False
    assert output["miner_momentum_1"] == 0
    assert output["has_previous_board_observation"] is False
    assert output["miner_board_change_volatility"] == 0.0


def test_lags_rolling_ema_momentum_and_acceleration() -> None:
    boards = tuple(
        make_board(index, [value] * 25)
        for index, value in enumerate((2, 4, 8, 14))
    )

    output = create_default_pipeline().compute(make_context(boards))

    assert output["miner_delta_1"] == 6
    assert output["miner_delta_2"] == 10
    assert output["miner_delta_3"] == 12
    assert output["has_history_2"] is True
    assert output["has_history_3"] is True
    assert output["miner_rolling_mean_2"] == 11.0
    assert output["miner_rolling_mean_3"] == pytest.approx(26 / 3)
    assert output["miner_ema_0_5"] == 9.75
    assert output["miner_momentum_3"] == 4.0
    assert output["miner_acceleration_1"] == 2
    assert output["miner_influx_rate_1"] == 6
    assert output["miner_outflow_rate_1"] == 0
    assert output["has_rolling_window_3"] is True
    assert output["miner_rolling_std_3"] == pytest.approx(
        math.sqrt(152 / 9)
    )


def test_outflow_rates_are_positive_magnitudes() -> None:
    previous = make_board(0, [10] * 25)
    current = make_board(1, [7] * 25, [60] * 25)

    output = create_default_pipeline().compute(
        make_context((previous, current))
    )

    assert output["miner_influx_rate_1"] == 0
    assert output["miner_outflow_rate_1"] == 3
    assert output["deployed_influx_rate_1"] == 0
    assert output["deployed_outflow_rate_1"] == 40


def test_leader_change_and_persistence_are_tie_aware() -> None:
    first = make_board(0, [10, 10] + [0] * 23)
    second = make_board(1, [12, 12] + [0] * 23)
    changed = make_board(2, [12, 14] + [0] * 23)
    boards = (first, second, changed)

    leader_output = create_default_pipeline().compute(
        make_context(boards, square_index=1)
    )
    former_leader_output = create_default_pipeline().compute(
        make_context(boards, square_index=0)
    )

    assert leader_output["miner_observations_since_leader_change"] == 0
    assert leader_output["miner_leader_persistence"] == 3
    assert former_leader_output["miner_leader_persistence"] == 0
    assert (
        leader_output["miner_observations_since_became_leader"]
        == 2
    )
    assert (
        leader_output["miner_consecutive_leader_observations"]
        == 3
    )
    assert leader_output["has_miner_ever_led"] is True
    assert (
        former_leader_output["miner_observations_since_became_leader"]
        == 2
    )
    assert (
        former_leader_output["miner_consecutive_leader_observations"]
        == 0
    )


def test_complete_tie_leader_set_persists() -> None:
    boards = tuple(
        make_board(index, [value] * 25)
        for index, value in enumerate((0, 1, 2))
    )

    output = create_default_pipeline().compute(
        make_context(boards, square_index=17)
    )

    assert output["miner_observations_since_leader_change"] == 2
    assert output["miner_leader_persistence"] == 3
    assert output["miner_observations_since_became_leader"] == 2
    assert output["miner_consecutive_leader_observations"] == 3


def test_partial_tie_counts_each_tied_square_as_leader() -> None:
    board = make_board(0, [10, 10, 5] + [0] * 22)

    tied = create_default_pipeline().compute(
        make_context((board,), square_index=1)
    )
    non_leader = create_default_pipeline().compute(
        make_context((board,), square_index=2)
    )

    assert tied["miner_consecutive_leader_observations"] == 1
    assert tied["has_miner_ever_led"] is True
    assert non_leader["miner_consecutive_leader_observations"] == 0
    assert non_leader["has_miner_ever_led"] is False


def test_board_volatility_is_dispersion_of_square_changes() -> None:
    previous = make_board(0, [0] * 25, [0] * 25)
    miner_changes = [0, 2] + [1] * 23
    deployed_changes = [0, 20] + [10] * 23
    current = make_board(1, miner_changes, deployed_changes)

    output = create_default_pipeline().compute(
        make_context((previous, current))
    )

    expected = math.sqrt(2 / 25)
    assert output["miner_board_change_volatility"] == pytest.approx(
        expected
    )
    assert output["deployed_board_change_volatility"] == pytest.approx(
        expected * 10
    )
    assert output["board_total_miner_delta_1"] == 25
    assert output["board_total_deployed_delta_1"] == 250


def test_zero_board_has_zero_rolling_variance() -> None:
    boards = tuple(
        make_board(index, [0] * 25, [0] * 25, [0] * 25)
        for index in range(3)
    )

    output = create_default_pipeline().compute(make_context(boards))

    assert output["miner_rolling_std_3"] == 0.0
    assert output["deployed_rolling_std_3"] == 0.0
    assert output["reward_rolling_std_3"] == 0.0
    assert output["miner_momentum_1"] == 0
    assert output["miner_consecutive_leader_observations"] == 3


def test_non_finite_input_is_rejected() -> None:
    values = [0] * 25
    values[0] = float("inf")  # type: ignore[list-item]
    board = make_board(0, values)

    with pytest.raises(ValueError, match="non-finite"):
        create_default_pipeline().compute(make_context((board,)))


def test_temporal_feature_column_order_is_deterministic() -> None:
    first_pipeline = create_default_pipeline()
    first = first_pipeline.registry.output_columns
    second = create_default_pipeline().registry.output_columns
    board = make_board(0, [0] * 25)
    computed = first_pipeline.compute(make_context((board,)))

    assert first == second
    assert len(first) == len(set(first))
    assert tuple(computed) == first
    assert first[-20:] == (
        "miner_rolling_std_3",
        "deployed_rolling_std_3",
        "reward_rolling_std_3",
        "has_rolling_window_3",
        "miner_momentum_1",
        "deployed_momentum_1",
        "reward_momentum_1",
        "has_momentum_1",
        "miner_observations_since_became_leader",
        "miner_consecutive_leader_observations",
        "has_miner_ever_led",
        "deployed_observations_since_became_leader",
        "deployed_consecutive_leader_observations",
        "has_deployed_ever_led",
        "reward_observations_since_became_leader",
        "reward_consecutive_leader_observations",
        "has_reward_ever_led",
        "board_total_miner_delta_1",
        "board_total_deployed_delta_1",
        "has_previous_board_observation",
    )


def test_context_rejects_future_board_history() -> None:
    current = make_board(0, [0] * 25)
    future = make_board(1, [1] * 25)

    with pytest.raises(
        ValueError,
        match="board_history must end with the current board snapshot",
    ):
        FeatureContext(
            board=current,
            square_index=0,
            square_history=(current.squares[0],),
            board_history=(current, future),
        )
