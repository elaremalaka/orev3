from __future__ import annotations

from abc import ABC, abstractmethod

from orev3.replay.models import (
    ReplayPoint,
)
from orev3.strategies.models import (
    StrategyDecision,
)


class Strategy(ABC):
    """
    Base interface for all ORE Miner V3 strategies.

    Strategies receive only ReplayPoint data.

    They must not receive finalized outcome data.
    """

    name: str
    version: str

    @abstractmethod
    def evaluate(
        self,
        replay_point: ReplayPoint,
    ) -> StrategyDecision:
        """
        Evaluate one point-in-time replay state.
        """
        raise NotImplementedError
