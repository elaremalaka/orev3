from __future__ import annotations

from orev3.replay.models import (
    ReplayPoint,
)
from orev3.strategies.base import (
    Strategy,
)
from orev3.strategies.models import (
    SquareAllocation,
    StrategyDecision,
)


class LeastCrowdedTop4Strategy(
    Strategy
):
    """
    Baseline strategy:

    Select the four squares with the fewest miners.

    Ties are resolved by square index.

    Allocation weights are equal.
    """

    name = "least_crowded_top4_equal"
    version = "1.0.0"

    def evaluate(
        self,
        replay_point: ReplayPoint,
    ) -> StrategyDecision:
        ranked = sorted(
            range(25),
            key=lambda square: (
                replay_point
                .round
                .miner_counts[
                    square
                ],
                square,
            ),
        )

        selected = ranked[:4]

        allocations = [
            SquareAllocation(
                square=square,
                weight=0.25,
            )
            for square
            in selected
        ]

        counts = [
            replay_point
            .round
            .miner_counts[
                square
            ]
            for square
            in selected
        ]

        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=(
                self.version
            ),
            action="participate",
            allocations=allocations,
            confidence=None,
            reason=(
                "Selected the four "
                "least-crowded squares "
                "by observed miner count."
            ),
            metadata={
                "min_selected_miners":
                    min(counts),
                "max_selected_miners":
                    max(counts),
            },
        )
