from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orev3.ledger.event_types import EventType
from orev3.ledger.identifiers import event_id, opportunity_id
from orev3.ledger.schemas import LedgerEvent, OpportunityRecord


def capture_observation(
    snapshot: dict[str, Any],
    *,
    observation_index: int,
    source: str,
    source_record_id: str,
    run_id: str,
    session_id: str,
) -> tuple[OpportunityRecord, LedgerEvent]:
    board = snapshot["board"]
    round_state = snapshot["round"]
    round_id = int(board["round_id"])
    if int(round_state["round_id"]) != round_id:
        raise ValueError("Board and round identifiers do not match")
    observed_at = datetime.fromisoformat(
        str(snapshot["observed_at_utc"]).replace("Z", "+00:00")
    )
    rpc_slot = int(snapshot["rpc_slot"])
    end_slot = board.get("end_slot")
    seconds_remaining = None
    if end_slot is not None and int(end_slot) < 2**64 - 1:
        # Approximate wall time is labeled as derived; raw slots remain in payload.
        seconds_remaining = max(int(end_slot) - rpc_slot, 0) * 0.4
    oid = opportunity_id(round_id, observation_index)
    opportunity = OpportunityRecord(
        opportunity_id=oid,
        round_id=round_id,
        observation_index=observation_index,
        observed_at=observed_at,
        seconds_remaining=seconds_remaining,
        board_snapshot_reference=source_record_id,
        round_state_reference=source_record_id,
        data_coverage="board_round_treasury",
        outcome_source=None,
    )
    event = LedgerEvent(
        event_id=event_id(
            EventType.BOARD_SNAPSHOT_OBSERVED.value,
            source,
            source_record_id,
        ),
        event_type=EventType.BOARD_SNAPSHOT_OBSERVED,
        event_time=observed_at,
        # Historical imports use the source observation time so a clean
        # re-import is byte-reproducible. Live capture callers may replace it.
        observed_at=observed_at,
        source=source,
        source_record_id=source_record_id,
        run_id=run_id,
        session_id=session_id,
        round_id=round_id,
        observation_index=observation_index,
        payload={
            "rpc_slot": rpc_slot,
            "board": board,
            "treasury": snapshot.get("treasury"),
            "round": round_state,
            "capture_mode": "passive",
        },
    )
    return opportunity, event
