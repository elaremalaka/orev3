from __future__ import annotations

from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.types import FeatureValues


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
