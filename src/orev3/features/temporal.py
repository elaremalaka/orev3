from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache

from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.types import (
    BoardSnapshot,
    FeatureValues,
    SquareSnapshot,
)


Metric = Callable[[SquareSnapshot], int]


def _miner(square: SquareSnapshot) -> int:
    return square.miner_count


def _deployed(square: SquareSnapshot) -> int:
    return square.deployed_lamports


def _reward(square: SquareSnapshot) -> int:
    return square.reward_raw


METRICS: tuple[tuple[str, Metric], ...] = (
    ("miner", _miner),
    ("deployed", _deployed),
    ("reward", _reward),
)


@dataclass(frozen=True, slots=True)
class TemporalBoardSummary:
    miner_total: int
    deployed_total: int
    leader_sets: tuple[
        tuple[str, frozenset[int]],
        ...,
    ]

    def leaders_for(
        self,
        metric_name: str,
    ) -> frozenset[int]:
        return dict(self.leader_sets)[metric_name]


@lru_cache(maxsize=4096)
def summarize_temporal_board(
    board: BoardSnapshot,
) -> TemporalBoardSummary:
    leader_sets: list[tuple[str, frozenset[int]]] = []

    for name, metric in METRICS:
        values = [metric(square) for square in board.squares]
        leader = max(values)
        leader_sets.append(
            (
                name,
                frozenset(
                    index
                    for index, value in enumerate(values)
                    if value == leader
                ),
            )
        )

    return TemporalBoardSummary(
        miner_total=sum(square.miner_count for square in board.squares),
        deployed_total=sum(
            square.deployed_lamports
            for square in board.squares
        ),
        leader_sets=tuple(leader_sets),
    )


def contiguous_square_history(
    context: FeatureContext,
    limit: int | None = None,
) -> tuple[SquareSnapshot, ...]:
    snapshots: list[SquareSnapshot] = []
    lag = 0

    while limit is None or lag < limit:
        square = context.square_at_lag(lag)

        if square is None:
            break

        snapshots.append(square)
        lag += 1

    snapshots.reverse()
    return tuple(snapshots)


def trailing_mean(
    history: Sequence[SquareSnapshot],
    metric: Metric,
    window: int,
) -> float:
    values = [metric(square) for square in history[-window:]]

    if not values:
        return 0.0

    return statistics.fmean(values)


def exponential_moving_average(
    history: Sequence[SquareSnapshot],
    metric: Metric,
    alpha: float = 0.5,
) -> float:
    if not history:
        return 0.0

    result = float(metric(history[0]))

    for square in history[1:]:
        result = alpha * metric(square) + (1 - alpha) * result

    return result


def mean_delta(
    history: Sequence[SquareSnapshot],
    metric: Metric,
    transitions: int,
) -> float:
    available = min(transitions, len(history) - 1)

    if available <= 0:
        return 0.0

    return (
        metric(history[-1])
        - metric(history[-available - 1])
    ) / available


def second_difference(
    history: Sequence[SquareSnapshot],
    metric: Metric,
) -> int:
    if len(history) < 3:
        return 0

    return (
        metric(history[-1])
        - 2 * metric(history[-2])
        + metric(history[-3])
    )


@lru_cache(maxsize=None)
def leader_set(
    board: BoardSnapshot,
    metric: Metric,
) -> frozenset[int]:
    metric_name = next(
        name
        for name, candidate in METRICS
        if candidate is metric
    )
    return summarize_temporal_board(board).leaders_for(metric_name)


@lru_cache(maxsize=4096)
def square_leader_dynamics(
    boards: tuple[BoardSnapshot, ...],
    metric_name: str,
) -> tuple[
    tuple[int, ...],
    tuple[int, ...],
    tuple[bool, ...],
]:
    current = boards[-1]
    current_leaders = summarize_temporal_board(
        current
    ).leaders_for(metric_name)

    if len(boards) == 1:
        observations_since = tuple(0 for _ in range(25))
        consecutive = tuple(
            1 if index in current_leaders else 0
            for index in range(25)
        )
        ever_led = tuple(
            index in current_leaders
            for index in range(25)
        )
        return observations_since, consecutive, ever_led

    previous = boards[-2]
    (
        previous_since,
        previous_consecutive,
        previous_ever,
    ) = square_leader_dynamics(boards[:-1], metric_name)
    gap = current.observation_index - previous.observation_index
    contiguous = gap == 1
    observations_since_values: list[int] = []
    consecutive_values: list[int] = []
    ever_led_values: list[bool] = []

    for square_index in range(25):
        is_leader = square_index in current_leaders
        was_leader = (
            contiguous
            and previous_consecutive[square_index] > 0
        )

        if is_leader:
            observations_since_values.append(
                previous_since[square_index] + 1
                if was_leader
                else 0
            )
            consecutive_values.append(
                previous_consecutive[square_index] + 1
                if was_leader
                else 1
            )
        else:
            observations_since_values.append(
                previous_since[square_index] + gap
                if previous_ever[square_index]
                else 0
            )
            consecutive_values.append(0)

        ever_led_values.append(
            previous_ever[square_index] or is_leader
        )

    return (
        tuple(observations_since_values),
        tuple(consecutive_values),
        tuple(ever_led_values),
    )


@lru_cache(maxsize=4096)
def cached_leader_set_age(
    boards: tuple[BoardSnapshot, ...],
    metric_name: str,
) -> int:
    return leader_set_age(boards, dict(METRICS)[metric_name])


def leader_set_age(
    boards: Sequence[BoardSnapshot],
    metric: Metric,
) -> int:
    if not boards:
        return 0

    current_leaders = leader_set(boards[-1], metric)
    age = 0

    later_index = boards[-1].observation_index

    for board in reversed(boards[:-1]):
        if board.observation_index != later_index - 1:
            break

        if leader_set(board, metric) != current_leaders:
            break

        age += 1
        later_index = board.observation_index

    return age


def leader_persistence(
    boards: Sequence[BoardSnapshot],
    square_index: int,
    metric: Metric,
) -> int:
    persistence = 0

    later_index = boards[-1].observation_index if boards else None

    for board in reversed(boards):
        if (
            later_index is not None
            and board is not boards[-1]
            and board.observation_index != later_index - 1
        ):
            break

        if square_index not in leader_set(board, metric):
            break

        persistence += 1
        later_index = board.observation_index

    return persistence


def board_change_volatility(
    boards: Sequence[BoardSnapshot],
    metric: Metric,
) -> float:
    if len(boards) < 2:
        return 0.0

    return cached_board_change_volatility(
        boards[-2],
        boards[-1],
        metric,
    )


@lru_cache(maxsize=4096)
def cached_board_change_volatility(
    previous: BoardSnapshot,
    current: BoardSnapshot,
    metric: Metric,
) -> float:
    deltas = [
        metric(current_square) - metric(previous_square)
        for previous_square, current_square in zip(
            previous.squares,
            current.squares,
            strict=True,
        )
    ]

    return statistics.pstdev(deltas)


def exact_board_change_volatility(
    context: FeatureContext,
    metric: Metric,
) -> float:
    previous = context.board_at_lag(1)

    if previous is None:
        return 0.0

    return board_change_volatility(
        (previous, context.board),
        metric,
    )


class OneStepDeltaFeature(Feature):
    name = "one_step_delta"
    family = "temporal"
    output_columns = (
        "miner_delta_1",
        "deployed_delta_1",
        "reward_delta_1",
        "has_previous_observation",
    )

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        current = context.square
        previous = context.previous_square

        if previous is None:
            return {
                "miner_delta_1": 0,
                "deployed_delta_1": 0,
                "reward_delta_1": 0,
                "has_previous_observation": False,
            }

        return {
            "miner_delta_1": (
                current.miner_count
                - previous.miner_count
            ),
            "deployed_delta_1": (
                current.deployed_lamports
                - previous.deployed_lamports
            ),
            "reward_delta_1": (
                current.reward_raw
                - previous.reward_raw
            ),
            "has_previous_observation": True,
        }


class LagDeltaFeature(Feature):
    name = "lag_delta"
    family = "temporal"
    output_columns = (
        "miner_delta_2",
        "deployed_delta_2",
        "reward_delta_2",
        "has_history_2",
        "miner_delta_3",
        "deployed_delta_3",
        "reward_delta_3",
        "has_history_3",
    )

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        output: dict[str, int | bool] = {}

        for lag in (2, 3):
            lagged = context.square_at_lag(lag)
            has_history = lagged is not None

            for name, metric in METRICS:
                output[f"{name}_delta_{lag}"] = (
                    metric(context.square) - metric(lagged)
                    if has_history
                    else 0
                )

            output[f"has_history_{lag}"] = has_history

        return {
            column: output[column]
            for column in self.output_columns
        }


class RollingDynamicsFeature(Feature):
    name = "rolling_dynamics"
    family = "temporal"
    output_columns = (
        "miner_rolling_mean_2",
        "deployed_rolling_mean_2",
        "reward_rolling_mean_2",
        "miner_rolling_mean_3",
        "deployed_rolling_mean_3",
        "reward_rolling_mean_3",
        "miner_ema_0_5",
        "deployed_ema_0_5",
        "reward_ema_0_5",
        "miner_momentum_3",
        "deployed_momentum_3",
        "reward_momentum_3",
        "miner_acceleration_1",
        "deployed_acceleration_1",
        "reward_acceleration_1",
        "miner_influx_rate_1",
        "miner_outflow_rate_1",
        "deployed_influx_rate_1",
        "deployed_outflow_rate_1",
    )

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        history = contiguous_square_history(context)
        output: dict[str, int | float] = {}

        for window in (2, 3):
            for name, metric in METRICS:
                output[f"{name}_rolling_mean_{window}"] = (
                    trailing_mean(history, metric, window)
                )

        for name, metric in METRICS:
            output[f"{name}_ema_0_5"] = exponential_moving_average(
                history,
                metric,
            )
            output[f"{name}_momentum_3"] = mean_delta(
                history,
                metric,
                transitions=3,
            )
            output[f"{name}_acceleration_1"] = second_difference(
                history,
                metric,
            )

        miner_delta = (
            _miner(history[-1]) - _miner(history[-2])
            if len(history) >= 2
            else 0
        )
        deployed_delta = (
            _deployed(history[-1]) - _deployed(history[-2])
            if len(history) >= 2
            else 0
        )
        output["miner_influx_rate_1"] = max(miner_delta, 0)
        output["miner_outflow_rate_1"] = max(-miner_delta, 0)
        output["deployed_influx_rate_1"] = max(deployed_delta, 0)
        output["deployed_outflow_rate_1"] = max(-deployed_delta, 0)

        return {
            column: output[column]
            for column in self.output_columns
        }


class LeaderDynamicsFeature(Feature):
    name = "leader_dynamics"
    family = "temporal"
    output_columns = (
        "miner_observations_since_leader_change",
        "deployed_observations_since_leader_change",
        "miner_leader_persistence",
        "deployed_leader_persistence",
    )

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        boards = context.board_history or (context.board,)
        board_tuple = tuple(boards)
        miner_dynamics = square_leader_dynamics(
            board_tuple,
            "miner",
        )
        deployed_dynamics = square_leader_dynamics(
            board_tuple,
            "deployed",
        )

        return {
            "miner_observations_since_leader_change": (
                cached_leader_set_age(
                    board_tuple,
                    "miner",
                )
            ),
            "deployed_observations_since_leader_change": (
                cached_leader_set_age(
                    board_tuple,
                    "deployed",
                )
            ),
            "miner_leader_persistence": miner_dynamics[1][
                context.square_index
            ],
            "deployed_leader_persistence": deployed_dynamics[1][
                context.square_index
            ],
        }


class BoardVolatilityFeature(Feature):
    name = "board_volatility"
    family = "temporal"
    output_columns = (
        "miner_board_change_volatility",
        "deployed_board_change_volatility",
    )

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        return {
            "miner_board_change_volatility": (
                exact_board_change_volatility(
                    context,
                    _miner,
                )
            ),
            "deployed_board_change_volatility": (
                exact_board_change_volatility(
                    context,
                    _deployed,
                )
            ),
        }


class TemporalExpansionFeature(Feature):
    name = "temporal_expansion"
    family = "temporal"
    output_columns = (
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

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        history = contiguous_square_history(context, limit=3)
        has_three = len(history) == 3
        output: dict[str, int | float | bool] = {
            "has_rolling_window_3": has_three,
            "has_momentum_1": has_three,
        }

        for name, metric in METRICS:
            values = [metric(square) for square in history]
            output[f"{name}_rolling_std_3"] = (
                statistics.pstdev(values)
                if len(values) >= 2
                else 0.0
            )
            output[f"{name}_momentum_1"] = (
                metric(history[-1])
                - 2 * metric(history[-2])
                + metric(history[-3])
                if has_three
                else 0
            )

        boards = context.board_history or (context.board,)

        for name, _metric in METRICS:
            (
                observations_since,
                consecutive,
                ever_led,
            ) = square_leader_dynamics(tuple(boards), name)
            square_index = context.square_index
            output[
                f"{name}_observations_since_became_leader"
            ] = observations_since[square_index]
            output[
                f"{name}_consecutive_leader_observations"
            ] = consecutive[square_index]
            output[f"has_{name}_ever_led"] = ever_led[square_index]

        current_summary = summarize_temporal_board(context.board)
        previous_board = context.board_at_lag(1)
        has_previous_board = previous_board is not None
        output["has_previous_board_observation"] = has_previous_board

        if previous_board is None:
            output["board_total_miner_delta_1"] = 0
            output["board_total_deployed_delta_1"] = 0
        else:
            previous_summary = summarize_temporal_board(previous_board)
            output["board_total_miner_delta_1"] = (
                current_summary.miner_total
                - previous_summary.miner_total
            )
            output["board_total_deployed_delta_1"] = (
                current_summary.deployed_total
                - previous_summary.deployed_total
            )

        return {
            column: output[column]
            for column in self.output_columns
        }
