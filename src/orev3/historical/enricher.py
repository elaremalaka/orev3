from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time

from orev3.historical.models import (
    FinalizedRoundOutcome,
    RoundLifecycle,
)
from orev3.observer.accounts import (
    decode_round,
    derive_round_address,
)
from orev3.observer.rpc import (
    SolanaRpcClient,
)


@dataclass(frozen=True)
class EnrichmentStats:
    """
    Summary of one outcome-enrichment operation.
    """

    total_rounds: int
    already_finalized: int
    enriched: int
    unavailable: int
    failed: int


def round_state_to_outcome(
    lifecycle: RoundLifecycle,
    round_state,
    rpc_slot: int,
) -> FinalizedRoundOutcome:
    """
    Convert a finalized decoded Round account into
    historical outcome data.

    This information is for outcome scoring only and
    is not inserted into observation_history.
    """

    entropy = round_state.entropy

    winning_square = (
        entropy % 25
        if entropy is not None
        else None
    )

    return FinalizedRoundOutcome(
        # For enriched outcomes this is the time the
        # finalized account was fetched, not the time a
        # strategy could have known the outcome.
        observed_at_utc=datetime.now(
            timezone.utc
        ),
        rpc_slot=rpc_slot,
        entropy=entropy,
        winning_square=winning_square,
        deployed_lamports=(
            round_state.deployed_lamports
        ),
        miner_counts=(
            round_state.miner_counts
        ),
        reward_buckets=(
            round_state.rewards
        ),
        total_vaulted=(
            round_state.total_vaulted
        ),
        total_winnings=(
            round_state.total_winnings
        ),
        total_miners=(
            round_state.total_miners
        ),
        round_motherlode=(
            round_state.motherlode
        ),
        top_miner=(
            round_state.top_miner
        ),
    )


def is_finalized_round_state(
    round_state,
) -> bool:
    """
    Require explicit finalized protocol indicators.

    Do not infer finalization merely because a round
    is old.
    """

    slot_hash_nonzero = (
        round_state.slot_hash_hex
        != ("00" * 32)
    )

    return any(
        [
            slot_hash_nonzero,
            round_state.entropy
            is not None,
            round_state.total_vaulted
            > 0,
            round_state.total_winnings
            > 0,
        ]
    )


def enrich_round(
    rpc: SolanaRpcClient,
    lifecycle: RoundLifecycle,
) -> tuple[
    RoundLifecycle,
    str,
]:
    """
    Enrich one RoundLifecycle.

    Returns:
        (lifecycle, status)

    Status values:
        already_finalized
        enriched
        unavailable
        not_finalized
        failed
    """

    if (
        lifecycle.finalized_outcome
        is not None
    ):
        return (
            lifecycle,
            "already_finalized",
        )

    try:
        round_address = (
            derive_round_address(
                lifecycle.round_id
            )
        )

        account = (
            rpc.get_account_info(
                str(round_address)
            )
        )

        if account is None:
            return (
                lifecycle,
                "unavailable",
            )

        round_state = decode_round(
            account
        )

        if not is_finalized_round_state(
            round_state
        ):
            return (
                lifecycle,
                "not_finalized",
            )

        rpc_slot = rpc.get_slot()

        outcome = (
            round_state_to_outcome(
                lifecycle=lifecycle,
                round_state=round_state,
                rpc_slot=rpc_slot,
            )
        )

        enriched = lifecycle.model_copy(
            update={
                "finalized_outcome":
                    outcome,
                "finalized_outcome_source":
                    "enriched",
            }
        )

        return (
            enriched,
            "enriched",
        )

    except Exception:
        return (
            lifecycle,
            "failed",
        )


def enrich_rounds(
    rpc: SolanaRpcClient,
    lifecycles: list[
        RoundLifecycle
    ],
    limit: int | None = None,
    delay_seconds: float = 0.25,
) -> tuple[
    list[RoundLifecycle],
    EnrichmentStats,
]:
    """
    Enrich missing finalized outcomes.

    Existing observed outcomes are preserved.

    `limit` limits the number of previously-unenriched
    rounds for controlled testing.
    """

    enriched_rounds: list[
        RoundLifecycle
    ] = []

    already_finalized = 0
    enriched_count = 0
    unavailable = 0
    failed = 0

    attempted = 0

    for lifecycle in lifecycles:
        if (
            lifecycle.finalized_outcome
            is not None
        ):
            already_finalized += 1

            enriched_rounds.append(
                lifecycle
            )

            continue

        if (
            limit is not None
            and attempted >= limit
        ):
            enriched_rounds.append(
                lifecycle
            )

            continue

        attempted += 1

        updated, status = enrich_round(
            rpc=rpc,
            lifecycle=lifecycle,
        )

        if delay_seconds > 0:
            time.sleep(
                delay_seconds
            )

        enriched_rounds.append(
            updated
        )

        if status == "enriched":
            enriched_count += 1

        elif status in (
            "unavailable",
            "not_finalized",
        ):
            unavailable += 1

        elif status == "failed":
            failed += 1

    stats = EnrichmentStats(
        total_rounds=len(
            lifecycles
        ),
        already_finalized=(
            already_finalized
        ),
        enriched=enriched_count,
        unavailable=unavailable,
        failed=failed,
    )

    return (
        enriched_rounds,
        stats,
    )
