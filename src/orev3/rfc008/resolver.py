from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from orev3.ledger.identifiers import canonical_json, deterministic_id
from orev3.observer.accounts import (
    decode_account_data,
    decode_round,
    derive_round_address,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.outcomes import (
    accept_outcome,
    begin_resolution,
    mark_attempt,
    quarantine_expired,
    record_provider_conflict,
)
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import OutcomeEvidence
from orev3.rfc008.storage import RFC008Store


class OutcomeProvider(Protocol):
    provider_id: str

    def get_genesis_hash(self) -> str: ...

    def get_account_info_with_context(
        self, address: str, *, commitment: str
    ) -> dict[str, Any]: ...

    def close(self) -> None: ...


def derive_round_pda(round_id: int, expected_program_owner: str) -> str:
    address = str(derive_round_address(round_id))
    # derive_round_address is frozen to the ORE program. Keep the explicit
    # owner argument so configuration drift cannot be hidden.
    from orev3.observer.accounts import ORE_PROGRAM_ID

    if expected_program_owner != str(ORE_PROGRAM_ID):
        raise ValueError("Configured owner cannot derive the canonical ORE PDA")
    return address


def _nonnegative(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _decode_response(
    response: dict[str, Any],
    *,
    round_id: int,
    round_pda: str,
    provider_id: str,
    requested_at: datetime,
    resolver_config: ResolverConfig,
) -> dict[str, object]:
    context = response.get("context")
    account = response.get("value")
    if not isinstance(context, dict) or not isinstance(account, dict):
        raise ValueError("Finalized account is unavailable")
    owner = str(account.get("owner", ""))
    if owner != resolver_config.expected_program_owner:
        raise ValueError("Finalized account owner mismatch")
    raw = decode_account_data(account)
    decoded = decode_round(account)
    if decoded.round_id != round_id:
        raise ValueError("Decoded round identity mismatch")
    if decoded.entropy is None or decoded.slot_hash_hex in {"00" * 32, "ff" * 32}:
        raise ValueError("Round account is not finalized")
    deployments = tuple(
        _nonnegative(value, f"deployed_lamports[{index}]")
        for index, value in enumerate(decoded.deployed_lamports)
    )
    if len(deployments) != 25:
        raise ValueError("Final deployment vector must contain 25 values")
    canonical = {
        "round_id": round_id,
        "round_pda": round_pda,
        "owner": owner,
        "slot_hash_hex": decoded.slot_hash_hex,
        "entropy": _nonnegative(decoded.entropy, "entropy"),
        "winner_square": decoded.entropy % 25,
        "final_square_deployments": deployments,
        "total_vaulted": _nonnegative(decoded.total_vaulted, "total_vaulted"),
        "total_winnings": _nonnegative(decoded.total_winnings, "total_winnings"),
        "motherlode_raw": _nonnegative(decoded.motherlode, "motherlode"),
    }
    return {
        "provider_id": provider_id,
        "requested_at": requested_at.isoformat(),
        "context_slot": _nonnegative(context.get("slot"), "context slot"),
        "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_response_sha256": hashlib.sha256(
            canonical_json(canonical).encode()
        ).hexdigest(),
        "canonical": canonical,
        "commitment": "finalized",
        "decoder_version": resolver_config.decoder_version,
    }


class FinalizedOutcomeResolver:
    def __init__(
        self,
        *,
        store: RFC008Store,
        experiment_config: RFC008Config,
        resolver_config: ResolverConfig,
        providers: tuple[OutcomeProvider, ...],
    ) -> None:
        if len(providers) != resolver_config.minimum_provider_count:
            raise ValueError("Resolver requires the frozen provider count")
        identities = tuple(provider.provider_id for provider in providers)
        if identities != resolver_config.provider_ids:
            raise ValueError("Provider identities do not match resolver configuration")
        self.store = store
        self.experiment_config = experiment_config
        self.config = resolver_config
        self.providers = providers

    def validate_provider_networks(self) -> None:
        hashes = tuple(provider.get_genesis_hash() for provider in self.providers)
        if len(set(hashes)) != 1 or hashes[0] != self.config.expected_genesis_hash:
            raise ValueError("Outcome providers do not agree on the frozen network")

    def resolve_round(
        self, round_id: int, *, now: datetime | None = None
    ) -> str:
        requested_at = now or datetime.now(timezone.utc)
        queue = self.store.queue(round_id)
        if queue is None:
            raise ValueError("Round must be enqueued before resolution")
        if queue.state == "finalized":
            return "duplicate"
        begin_resolution(self.store, round_id, at=requested_at)
        round_pda = derive_round_pda(
            round_id, self.config.expected_program_owner
        )
        if queue.round_pda != round_pda:
            record_provider_conflict(
                self.store,
                round_id,
                provider_evidence={
                    "reason": "persisted_round_pda_mismatch",
                    "persisted": queue.round_pda,
                    "derived": round_pda,
                },
                at=requested_at,
            )
            return "conflict"
        evidence: list[dict[str, object]] = []
        try:
            for provider in self.providers:
                response = provider.get_account_info_with_context(
                    round_pda, commitment=self.config.commitment
                )
                evidence.append(
                    _decode_response(
                        response,
                        round_id=round_id,
                        round_pda=round_pda,
                        provider_id=provider.provider_id,
                        requested_at=requested_at,
                        resolver_config=self.config,
                    )
                )
        except Exception as exc:
            mark_attempt(
                self.store,
                round_id,
                source_type="finalized_round_account",
                status="retry",
                error=f"{type(exc).__name__}:{exc}",
                at=requested_at,
                base_retry_seconds=self.config.base_retry_seconds,
                maximum_retry_seconds=self.config.maximum_retry_seconds,
                jitter_modulus_seconds=self.config.jitter_modulus_seconds,
            )
            self.store.increment("resolver_retryable_failures")
            return "retry"
        canonical_hashes = {
            str(value["canonical_response_sha256"]) for value in evidence
        }
        if len(canonical_hashes) != 1:
            combined = {
                str(value["provider_id"]): {
                    "canonical_response_sha256": value[
                        "canonical_response_sha256"
                    ],
                    "context_slot": value["context_slot"],
                }
                for value in evidence
            }
            mark_attempt(
                self.store,
                round_id,
                source_type="finalized_round_account",
                status="conflict",
                response_sha256=hashlib.sha256(
                    canonical_json(combined).encode()
                ).hexdigest(),
                error="provider_disagreement",
                at=requested_at,
                base_retry_seconds=self.config.base_retry_seconds,
                maximum_retry_seconds=self.config.maximum_retry_seconds,
                jitter_modulus_seconds=self.config.jitter_modulus_seconds,
            )
            record_provider_conflict(
                self.store,
                round_id,
                provider_evidence=combined,
                at=requested_at,
            )
            return "conflict"
        canonical = evidence[0]["canonical"]
        assert isinstance(canonical, dict)
        combined_hash = hashlib.sha256(canonical_json(evidence).encode()).hexdigest()
        mark_attempt(
            self.store,
            round_id,
            source_type="finalized_round_account",
            status="accepted",
            response_sha256=combined_hash,
            at=requested_at,
            base_retry_seconds=self.config.base_retry_seconds,
            maximum_retry_seconds=self.config.maximum_retry_seconds,
            jitter_modulus_seconds=self.config.jitter_modulus_seconds,
        )
        outcome = OutcomeEvidence(
            outcome_id=deterministic_id(
                "rfc008-direct-finalized-outcome-v1",
                self.experiment_config.configuration_fingerprint,
                round_id,
                combined_hash,
            ),
            round_id=round_id,
            winner_square=int(canonical["winner_square"]),
            finalized_at=requested_at,
            provenance="direct_observed",
            commitment="finalized",
            final_square_deployments=tuple(
                int(value) for value in canonical["final_square_deployments"]
            ),
            total_winnings_lamports=int(canonical["total_winnings"]),
            motherlode_raw=int(canonical["motherlode_raw"]),
            base_ore_raw=None,
            source_reference=f"finalized-account:{round_pda}",
            source_content_sha256=combined_hash,
            round_pda=round_pda,
            program_owner=self.config.expected_program_owner,
            provider_ids=tuple(
                str(value["provider_id"]) for value in evidence
            ),
            provider_response_sha256=tuple(
                str(value["raw_response_sha256"]) for value in evidence
            ),
            provider_context_slots=tuple(
                int(value["context_slot"]) for value in evidence
            ),
            requested_at=requested_at,
            decoder_version=self.config.decoder_version,
            resolver_version=self.config.resolver_version,
            configuration_fingerprint=(
                self.experiment_config.configuration_fingerprint
            ),
        )
        return str(
            accept_outcome(
                self.store,
                outcome,
                self.experiment_config,
                at=requested_at,
            )
        )

    def process_due(self, *, now: datetime | None = None) -> dict[str, int]:
        current = now or datetime.now(timezone.utc)
        quarantined = quarantine_expired(
            self.store,
            now=current,
            age=timedelta(seconds=self.config.quarantine_after_seconds),
        )
        counts = {
            "accepted": 0,
            "duplicate": 0,
            "retry": 0,
            "conflict": 0,
            "quarantined": quarantined,
        }
        for queue in self.store.unresolved_queue():
            if queue.next_retry_at is not None and queue.next_retry_at > current:
                continue
            result = self.resolve_round(queue.round_id, now=current)
            counts[result] = counts.get(result, 0) + 1
        return counts
