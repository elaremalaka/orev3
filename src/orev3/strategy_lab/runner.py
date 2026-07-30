"""Deterministic historical orchestration for the RFC-010 Strategy Laboratory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orev3.historical.models import RoundLifecycleIndexRecord
from orev3.replay.engine import select_by_slots_remaining
from orev3.replay.loader import load_round_index
from orev3.replay.models import ReplayPoint

from orev3.strategy_lab.interfaces import (
    DecisionContext,
    RankedCandidateSet,
    Strategy,
    _freeze_mapping,
)


@dataclass(frozen=True, slots=True)
class ExperimentConfiguration:
    """Immutable configuration for one deterministic replay experiment."""

    dataset_path: Path
    requested_slots_remaining: int
    max_slot_distance: int | None = 3

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_path", Path(self.dataset_path))
        _validate_nonnegative_integer(
            "requested_slots_remaining",
            self.requested_slots_remaining,
        )
        if self.max_slot_distance is not None:
            _validate_nonnegative_integer(
                "max_slot_distance",
                self.max_slot_distance,
            )


@dataclass(frozen=True, slots=True)
class ExperimentRunner:
    """Orchestrate a strategy over historical rounds in deterministic order."""

    configuration: ExperimentConfiguration

    def run(self, strategy: Strategy) -> tuple[RankedCandidateSet, ...]:
        """Execute one strategy sequentially over the configured replay dataset."""

        if not isinstance(strategy, Strategy):
            raise TypeError("strategy must implement the Strategy interface")

        lifecycles = _load_chronological_lifecycles(
            self.configuration.dataset_path
        )
        decisions: list[RankedCandidateSet] = []

        strategy.initialize()
        try:
            for lifecycle in lifecycles:
                selection = select_by_slots_remaining(
                    lifecycle,
                    requested_slots_remaining=(
                        self.configuration.requested_slots_remaining
                    ),
                    max_slot_distance=self.configuration.max_slot_distance,
                )
                if not selection.within_tolerance:
                    raise ValueError(
                        "replay selection is outside the configured slot "
                        f"tolerance for round {lifecycle.round_id}"
                    )

                context = _decision_context_from_replay_point(
                    selection.replay_point
                )
                decision = strategy.choose(context)
                if not isinstance(decision, RankedCandidateSet):
                    raise TypeError(
                        "Strategy.choose() must return RankedCandidateSet"
                    )
                decisions.append(decision)

                outcome = lifecycle.finalized_outcome
                if outcome is None:
                    raise ValueError(
                        "finalized historical outcome is required after the "
                        f"decision for round {lifecycle.round_id}"
                    )
                strategy.update(
                    _freeze_mapping(outcome.model_dump(mode="json"))
                )
        finally:
            strategy.finalize()

        return tuple(decisions)


def _load_chronological_lifecycles(
    dataset_path: Path,
) -> tuple[RoundLifecycleIndexRecord, ...]:
    index = load_round_index(dataset_path)
    return tuple(
        sorted(
            index.values(),
            key=lambda lifecycle: (
                lifecycle.start_slot,
                lifecycle.round_id,
            ),
        )
    )


def _decision_context_from_replay_point(point: ReplayPoint) -> DecisionContext:
    """Project a replay point onto the live-available Strategy Lab boundary."""

    board = point.board
    treasury = point.treasury
    round_state = point.round
    information: dict[str, Any] = {
        "round_id": point.round_id,
        "observed_at_utc": point.observed_at_utc.isoformat(),
        "rpc_slot": point.rpc_slot,
        "start_slot": point.start_slot,
        "end_slot": point.end_slot,
        "slots_elapsed": point.slots_elapsed,
        "slots_remaining": point.slots_remaining,
        "board": {
            "round_id": board.round_id,
            "start_slot": board.start_slot,
            "end_slot": board.end_slot,
            "production_cost_ema": board.production_cost_ema,
        },
        "treasury": {
            "motherlode": treasury.motherlode,
        },
        "round": {
            "round_id": round_state.round_id,
            "deployed_lamports": round_state.deployed_lamports,
            "miner_counts": round_state.miner_counts,
            "rewards": round_state.rewards,
            "expires_at": round_state.expires_at,
            "motherlode": round_state.motherlode,
            "total_vaulted": round_state.total_vaulted,
            "total_winnings": round_state.total_winnings,
            "total_miners": round_state.total_miners,
            "top_miner": round_state.top_miner,
        },
    }
    return DecisionContext(information)


def _validate_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


__all__ = ["ExperimentConfiguration", "ExperimentRunner"]
