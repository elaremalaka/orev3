from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib

from orev3.ledger.identifiers import deterministic_id
from orev3.observer.accounts import derive_round_address
from orev3.rfc008.accounting import account_round
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.schemas import OutcomeEvidence, OutcomeQueueRecord
from orev3.rfc008.storage import RFC008Store, strict_json


def enqueue_pending(
    store: RFC008Store,
    round_id: int,
    *,
    at: datetime | None = None,
) -> OutcomeQueueRecord:
    now = at or datetime.now(timezone.utc)
    queue = OutcomeQueueRecord(
        round_id=round_id,
        round_pda=str(derive_round_address(round_id)),
        state="pending",
        enqueued_at=now,
        updated_at=now,
        retry_count=0,
        next_retry_at=now,
    )
    store.enqueue_outcome(queue)
    return store.queue(round_id) or queue


def mark_attempt(
    store: RFC008Store,
    round_id: int,
    *,
    source_type: str,
    status: str,
    response_sha256: str | None = None,
    error: str | None = None,
    at: datetime | None = None,
    base_retry_seconds: int = 2,
    maximum_retry_seconds: int = 300,
    jitter_modulus_seconds: int = 7,
) -> OutcomeQueueRecord:
    now = at or datetime.now(timezone.utc)
    queue = store.queue(round_id)
    if queue is None:
        raise ValueError("Round must be durably enqueued before resolution")
    attempt_id = deterministic_id(
        "rfc008-outcome-attempt", round_id, queue.retry_count, now.isoformat()
    )
    store.connection.execute(
        """
        INSERT INTO outcome_attempts
        (attempt_id,round_id,attempted_at,source_type,status,response_sha256,record_json)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            attempt_id,
            round_id,
            now.isoformat(),
            source_type,
            status,
            response_sha256,
            strict_json(
                {
                    "attempt_id": attempt_id,
                    "round_id": round_id,
                    "source_type": source_type,
                    "status": status,
                    "response_sha256": response_sha256,
                    "error": error,
                }
            ),
        ),
    )
    retry = queue.retry_count + 1
    exponential = base_retry_seconds * (2 ** max(retry - 1, 0))
    jitter_material = f"rfc008-retry-jitter-v1:{round_id}:{retry}".encode()
    jitter = (
        int.from_bytes(hashlib.sha256(jitter_material).digest()[:8], "big")
        % jitter_modulus_seconds
    )
    delay = min(exponential + jitter, maximum_retry_seconds)
    updated = queue.model_copy(
        update={
            "state": "pending" if status != "conflict" else "conflicted",
            "updated_at": now,
            "retry_count": retry,
            "next_retry_at": now + timedelta(seconds=delay),
            "last_error": error,
        }
    )
    store.save_queue(updated)
    return updated


def record_provider_conflict(
    store: RFC008Store,
    round_id: int,
    *,
    provider_evidence: dict[str, object],
    at: datetime | None = None,
) -> None:
    now = at or datetime.now(timezone.utc)
    queue = store.queue(round_id)
    if queue is None:
        raise ValueError("Conflict requires a durable pending round")
    conflict_id = deterministic_id(
        "rfc008-provider-conflict",
        round_id,
        provider_evidence,
    )
    store.connection.execute(
        """
        INSERT OR IGNORE INTO outcome_conflicts
        (conflict_id,round_id,created_at,record_json) VALUES (?,?,?,?)
        """,
        (
            conflict_id,
            round_id,
            now.isoformat(),
            strict_json(
                {
                    "conflict_id": conflict_id,
                    "round_id": round_id,
                    "provider_evidence": provider_evidence,
                    "conflict_status": "conflicted",
                }
            ),
        ),
    )
    store.save_queue(
        queue.model_copy(
            update={
                "state": "conflicted",
                "updated_at": now,
                "next_retry_at": None,
                "last_error": "authoritative_provider_disagreement",
            }
        )
    )
    store.connection.execute(
        "UPDATE experiment_rounds SET state='conflicted' WHERE round_id=?",
        (round_id,),
    )
    store.increment("outcome_conflicts")


def begin_resolution(
    store: RFC008Store,
    round_id: int,
    *,
    at: datetime | None = None,
) -> OutcomeQueueRecord:
    now = at or datetime.now(timezone.utc)
    queue = store.queue(round_id)
    if queue is None:
        raise ValueError("Round must be durably enqueued before resolution")
    if queue.state not in {"pending", "resolving"}:
        raise ValueError(f"Outcome is not resolvable from state {queue.state}")
    updated = queue.model_copy(
        update={"state": "resolving", "updated_at": now}
    )
    store.save_queue(updated)
    return updated


def accept_outcome(
    store: RFC008Store,
    outcome: OutcomeEvidence,
    config: RFC008Config,
    *,
    at: datetime | None = None,
) -> LiteralResult:
    now = at or datetime.now(timezone.utc)
    queue = store.queue(outcome.round_id)
    if queue is None:
        raise ValueError("Outcome arrived before durable pending-round enqueue")
    existing = store.accepted_outcome(outcome.round_id)
    if existing is not None:
        comparable = {
            "winner_square": existing.winner_square == outcome.winner_square,
            "deployments": existing.final_square_deployments
            == outcome.final_square_deployments,
            "winnings": existing.total_winnings_lamports
            == outcome.total_winnings_lamports,
        }
        if all(comparable.values()):
            store.increment("duplicate_outcomes")
            return LiteralResult("duplicate")
        conflict_id = deterministic_id(
            "rfc008-outcome-conflict", existing.outcome_id, outcome.outcome_id
        )
        store.connection.execute(
            """
            INSERT OR IGNORE INTO outcome_conflicts
            (conflict_id,round_id,created_at,record_json) VALUES (?,?,?,?)
            """,
            (
                conflict_id,
                outcome.round_id,
                now.isoformat(),
                strict_json(
                    {
                        "conflict_id": conflict_id,
                        "round_id": outcome.round_id,
                        "existing_outcome_id": existing.outcome_id,
                        "incoming_outcome_id": outcome.outcome_id,
                        "checks": comparable,
                    }
                ),
            ),
        )
        store.save_queue(
            queue.model_copy(
                update={
                    "state": "conflicted",
                    "updated_at": now,
                    "last_error": "authoritative_outcome_disagreement",
                }
            )
        )
        store.connection.execute(
            "UPDATE experiment_rounds SET state='conflicted' WHERE round_id=?",
            (outcome.round_id,),
        )
        store.increment("outcome_conflicts")
        return LiteralResult("conflict")
    store.insert_outcome(outcome)
    updated = queue.model_copy(
        update={
            "state": "finalized",
            "updated_at": now,
            "next_retry_at": None,
            "accepted_outcome_id": outcome.outcome_id,
            "last_error": None,
        }
    )
    store.save_queue(updated)
    decisions = store.decisions(outcome.round_id)
    for decision in decisions:
        store.insert_accounting(account_round(decision, outcome, config))
    prior = store.connection.execute(
        "SELECT state FROM experiment_rounds WHERE round_id=?",
        (outcome.round_id,),
    ).fetchone()
    if len(decisions) == 5 and prior is not None and prior[0] != "excluded":
        store.connection.execute(
            """
            UPDATE experiment_rounds SET state=? WHERE round_id=?
            """,
            (
                "finalized_primary"
                if outcome.provenance == "direct_observed"
                else "finalized_sensitivity",
                outcome.round_id,
            ),
        )
        store.increment(
            "primary_outcomes"
            if outcome.provenance == "direct_observed"
            else "recovered_outcomes"
        )
    else:
        store.increment("outcomes_for_unanalyzable_rounds")
    return LiteralResult("accepted")


class LiteralResult(str):
    """Stable string result with an explicit small result vocabulary."""


def quarantine_expired(
    store: RFC008Store,
    *,
    now: datetime | None = None,
    age: timedelta = timedelta(hours=24),
) -> int:
    current = now or datetime.now(timezone.utc)
    changed = 0
    for queue in store.unresolved_queue():
        if current - queue.enqueued_at >= age:
            store.save_queue(
                queue.model_copy(
                    update={
                        "state": "quarantined",
                        "updated_at": current,
                        "next_retry_at": None,
                        "last_error": "unresolved_after_24_hours",
                    }
                )
            )
            changed += 1
    if changed:
        store.increment("quarantined_outcomes", changed)
    return changed
