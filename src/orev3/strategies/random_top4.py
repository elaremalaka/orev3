from __future__ import annotations

import random

from orev3.replay.models import ReplayPoint
from orev3.strategies.base import Strategy
from orev3.strategies.models import (
    SquareAllocation,
    StrategyDecision,
)


class SeededRandomTop4Strategy(Strategy):
    """
    Reproducible random 4-of-25 control.

    The round ID is combined with a fixed base seed so
    the same historical round always produces the same
    selection.
    """

    name = "random_top4_seeded"
    version = "1.0.0"

    def __init__(
        self,
        base_seed: int = 42,
    ) -> None:
        self.base_seed = base_seed

    def evaluate(
        self,
        replay_point: ReplayPoint,
    ) -> StrategyDecision:
        rng = random.Random(
            self.base_seed
            + replay_point.round_id
        )

        selected = sorted(
            rng.sample(
                range(25),
                4,
            )
        )

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
                "Reproducible seeded random "
                "4-of-25 control selection."
            ),
            metadata={
                "base_seed":
                    self.base_seed,
            },
        )
