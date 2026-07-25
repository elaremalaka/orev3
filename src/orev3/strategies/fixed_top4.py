from __future__ import annotations

from orev3.replay.models import ReplayPoint
from orev3.strategies.base import Strategy
from orev3.strategies.models import (
    SquareAllocation,
    StrategyDecision,
)


class FixedTop4Strategy(Strategy):
    """
    Deterministic control strategy.

    Always selects squares 0, 1, 2, and 3.
    """

    name = "fixed_top4"
    version = "1.0.0"

    def evaluate(
        self,
        replay_point: ReplayPoint,
    ) -> StrategyDecision:
        selected = [0, 1, 2, 3]

        return StrategyDecision(
            strategy_name=self.name,
            strategy_version=self.version,
            action="participate",
            allocations=[
                SquareAllocation(
                    square=square,
                    weight=0.25,
                )
                for square in selected
            ],
            confidence=None,
            reason=(
                "Deterministic control selecting "
                "fixed squares 0, 1, 2, and 3."
            ),
            metadata={},
        )
