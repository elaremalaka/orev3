from __future__ import annotations

from collections.abc import Sequence

from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.types import FeatureValues


def safe_share(
    value: int,
    total: int,
) -> float:
    if total <= 0:
        return 0.0

    return value / total


def average_descending_rank(
    values: Sequence[int],
    square_index: int,
) -> float:
    target = values[square_index]

    strictly_greater = sum(
        value > target
        for value in values
    )
    equal = sum(
        value == target
        for value in values
    )

    first_rank = strictly_greater + 1
    last_rank = strictly_greater + equal

    return (first_rank + last_rank) / 2


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

        total_miners = sum(miner_values)
        total_deployed = sum(deployed_values)

        miner_leader = max(miner_values)
        deployed_leader = max(deployed_values)

        return {
            "miner_share": safe_share(
                square.miner_count,
                total_miners,
            ),
            "deployed_share": safe_share(
                square.deployed_lamports,
                total_deployed,
            ),
            "miner_average_rank": (
                average_descending_rank(
                    miner_values,
                    context.square_index,
                )
            ),
            "deployed_average_rank": (
                average_descending_rank(
                    deployed_values,
                    context.square_index,
                )
            ),
            "miner_ratio_to_leader": (
                square.miner_count / miner_leader
                if miner_leader > 0
                else 0.0
            ),
            "deployed_ratio_to_leader": (
                square.deployed_lamports
                / deployed_leader
                if deployed_leader > 0
                else 0.0
            ),
        }
