from __future__ import annotations

from datetime import datetime

from orev3.ledger.schemas import Provenance, RewardRecord


def observe_total_only_ore(
    *,
    opportunity_id: str,
    round_id: int,
    wallet_public_key: str | None,
    total_ore_raw: int,
    reward_time: datetime,
    provenance: Provenance,
) -> RewardRecord:
    """Keep unavailable base/Motherlode decomposition explicitly null."""
    return RewardRecord(
        opportunity_id=opportunity_id,
        round_id=round_id,
        wallet_public_key=wallet_public_key,
        total_ore_raw=total_ore_raw,
        base_ore_raw=None,
        motherlode_ore_raw=None,
        reward_time=reward_time,
        provenance=provenance,
    )
