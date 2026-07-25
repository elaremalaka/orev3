from __future__ import annotations

from datetime import datetime

from orev3.ledger.schemas import ClaimRecord


def attribute_claim(
    *,
    claim_signature: str,
    wallet_public_key: str,
    claim_time: datetime,
    claimed_ore_raw: int,
    claim_fee_lamports: int,
    pending_rewards: list[tuple[str, int]],
    method: str,
    direct_opportunity_ids: list[str] | None = None,
) -> ClaimRecord:
    rewards = [(key, amount) for key, amount in pending_rewards if amount > 0]
    amounts: dict[str, int] = {}
    confidence = "low"
    ambiguity = None
    if method == "direct":
        wanted = set(direct_opportunity_ids or [])
        eligible = [(key, amount) for key, amount in rewards if key in wanted]
        remaining = claimed_ore_raw
        for key, amount in eligible:
            used = min(amount, remaining)
            amounts[key] = used
            remaining -= used
        confidence = "high" if remaining == 0 else "medium"
        ambiguity = None if remaining == 0 else "direct references do not cover claim"
    elif method in {"balance_difference", "fifo"}:
        remaining = claimed_ore_raw
        for key, amount in rewards:
            if remaining <= 0:
                break
            used = min(amount, remaining)
            amounts[key] = used
            remaining -= used
        confidence = "medium" if method == "balance_difference" else "low"
        ambiguity = None if remaining == 0 else "pending rewards do not cover claim"
    elif method == "proportional":
        total = sum(amount for _, amount in rewards)
        remaining = claimed_ore_raw
        if total:
            for index, (key, amount) in enumerate(rewards):
                used = (
                    remaining
                    if index == len(rewards) - 1
                    else min((claimed_ore_raw * amount) // total, remaining)
                )
                amounts[key] = used
                remaining -= used
        ambiguity = "multiple rewards could not be directly separated"
    elif method == "unattributed":
        remaining = claimed_ore_raw
        confidence = "unavailable"
        ambiguity = "no supported opportunity attribution"
    else:
        raise ValueError(f"Unsupported claim attribution method: {method}")
    return ClaimRecord(
        claim_signature=claim_signature,
        wallet_public_key=wallet_public_key,
        claim_time=claim_time,
        claimed_ore_raw=claimed_ore_raw,
        claim_fee_lamports=claim_fee_lamports,
        attributed_opportunity_ids=list(amounts),
        attributed_amounts_raw=amounts,
        unattributed_ore_raw=remaining,
        attribution_method=method,
        attribution_confidence=confidence,
        ambiguity_reason=ambiguity,
    )
