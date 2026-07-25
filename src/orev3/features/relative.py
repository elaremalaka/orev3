from __future__ import annotations

from collections.abc import Sequence

from orev3.features.base import Feature
from orev3.features.board_summary import (
    average_descending_ranks,
    summarize_board,
)
from orev3.features.context import FeatureContext
from orev3.features.types import FeatureValues


def safe_share(
    value: int,
    total: int,
) -> float:
    if total <= 0:
        return 0.0

    return value / total


def safe_ratio(value: int, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0

    return value / denominator


def safe_z_score(
    value: int,
    mean: float,
    standard_deviation: float,
) -> float:
    if standard_deviation <= 0:
        return 0.0

    return (value - mean) / standard_deviation


def average_descending_rank(
    values: Sequence[int],
    square_index: int,
) -> float:
    """Preserve the original single-square ranking helper interface."""
    return average_descending_ranks(values)[square_index]


class BoardRelativeFeature(Feature):
    name = "board_relative"
    family = "relative"
    output_columns = (
        "miner_share",
        "deployed_share",
        "miner_average_rank",
        "deployed_average_rank",
        "miner_ratio_to_leader",
        "deployed_ratio_to_leader",
        "miner_ratio_to_mean",
        "deployed_ratio_to_mean",
        "miner_difference_from_mean",
        "deployed_difference_from_mean",
        "miner_z_score",
        "deployed_z_score",
    )

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        miner_values = [
            square.miner_count
            for square in context.board.squares
        ]
        deployed_values = [
            square.deployed_lamports
            for square in context.board.squares
        ]

        square = context.square

        miner_summary = summarize_board(miner_values)
        deployed_summary = summarize_board(deployed_values)

        return {
            "miner_share": safe_share(
                square.miner_count,
                miner_summary.total,
            ),
            "deployed_share": safe_share(
                square.deployed_lamports,
                deployed_summary.total,
            ),
            "miner_average_rank": (
                miner_summary.average_ranks[
                    context.square_index
                ]
            ),
            "deployed_average_rank": (
                deployed_summary.average_ranks[
                    context.square_index
                ]
            ),
            "miner_ratio_to_leader": (
                safe_ratio(
                    square.miner_count,
                    miner_summary.leader,
                )
            ),
            "deployed_ratio_to_leader": (
                safe_ratio(
                    square.deployed_lamports,
                    deployed_summary.leader,
                )
            ),
            "miner_ratio_to_mean": safe_ratio(
                square.miner_count,
                miner_summary.mean,
            ),
            "deployed_ratio_to_mean": safe_ratio(
                square.deployed_lamports,
                deployed_summary.mean,
            ),
            "miner_difference_from_mean": (
                square.miner_count - miner_summary.mean
            ),
            "deployed_difference_from_mean": (
                square.deployed_lamports
                - deployed_summary.mean
            ),
            "miner_z_score": safe_z_score(
                square.miner_count,
                miner_summary.mean,
                miner_summary.standard_deviation,
            ),
            "deployed_z_score": safe_z_score(
                square.deployed_lamports,
                deployed_summary.mean,
                deployed_summary.standard_deviation,
            ),
        }
