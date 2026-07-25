from __future__ import annotations

from typing import Any

from orev3.collection.schemas import CompleteOpportunity, TailRecord
from orev3.ledger.identifiers import deterministic_id


class IncompleteOpportunityError(ValueError):
    def __init__(self, reason: str, *, round_id: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.round_id = round_id


def build_opportunity(
    record: TailRecord,
    *,
    observation_index: int,
) -> CompleteOpportunity:
    raw: dict[str, Any] = record.raw
    try:
        board = raw["board"]
        round_state = raw["round"]
        round_id = int(board["round_id"])
        if int(round_state["round_id"]) != round_id:
            raise IncompleteOpportunityError(
                "board_round_conflict", round_id=round_id
            )
        miners = [int(value) for value in round_state["miner_counts"]]
        deployed = [int(value) for value in round_state["deployed_lamports"]]
        rewards = [int(value) for value in round_state["rewards"]]
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, IncompleteOpportunityError):
            raise
        raise IncompleteOpportunityError("missing_or_invalid_board_fields") from exc
    if any(len(values) != 25 for values in (miners, deployed, rewards)):
        raise IncompleteOpportunityError(
            "incomplete_25_square_board", round_id=round_id
        )
    rpc_slot = int(raw["rpc_slot"])
    end_raw = board.get("end_slot")
    end_slot = (
        None if end_raw is None or int(end_raw) == 2**64 - 1 else int(end_raw)
    )
    return CompleteOpportunity(
        round_id=round_id,
        observation_index=observation_index,
        observed_at=record.observed_at,
        rpc_slot=rpc_slot,
        start_slot=int(board["start_slot"]),
        end_slot=end_slot,
        slots_remaining=(
            max(end_slot - rpc_slot, 0) if end_slot is not None else None
        ),
        miner_counts=miners,
        deployed_lamports=deployed,
        reward_raw=rewards,
        treasury_motherlode_raw=int(raw.get("treasury", {}).get("motherlode", 0)),
        source_reference=f"{record.source_path}:{record.source_line_number}",
    )


def partial_record(
    record: TailRecord,
    error: IncompleteOpportunityError,
    *,
    expired: bool,
) -> dict[str, object]:
    return {
        "partial_id": deterministic_id("partial-opportunity", record.record_id),
        "source_id": record.source_id,
        "round_id": error.round_id,
        "expired": expired,
        "reason": error.reason,
        "source_reference": f"{record.source_path}:{record.source_line_number}",
        "observed_at": record.observed_at.isoformat(),
    }
