from __future__ import annotations

from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.types import FeatureValues


class RawSquareFeature(Feature):
    name = "raw_square"
    family = "raw"
    output_columns = (
        "miner_count",
        "deployed_lamports",
        "reward_raw",
    )

    def compute(
        self,
        context: FeatureContext,
    ) -> FeatureValues:
        square = context.square

        return {
            "miner_count": square.miner_count,
            "deployed_lamports": (
                square.deployed_lamports
            ),
            "reward_raw": square.reward_raw,
        }
