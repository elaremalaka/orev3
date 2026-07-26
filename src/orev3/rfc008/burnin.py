from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orev3.collection.outcome_recovery import RpcRecoveryProvider
from orev3.ledger.identifiers import deterministic_id
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.marker import derive_runtime_source_boundary
from orev3.rfc008.lifecycle import (
    capture_marker_pair,
    validate_production_isolation,
)
from orev3.rfc008.outcomes import enqueue_pending, quarantine_expired
from orev3.rfc008.resolver import (
    FinalizedOutcomeResolver,
    _decode_response,
    derive_round_pda,
)
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import (
    ConflictTestEvidence,
    BurnInSourceBoundary,
    JitterTestEvidence,
    OperationalBurnInSummary,
    OperationalAttemptEvidence,
    OperationalRequestEvidence,
    OperationalRoundEvidence,
    ProtectedProcessEvidence,
    ProviderRoundEvidence,
    REQUIRED_PROCESS_COMMAND_IDENTITIES,
    REQUIRED_PROTECTED_PROCESSES,
    QuarantineTestEvidence,
    ResolverBurnInEvidence,
    RestartRetryEvidence,
    RpcRequestCounts,
)
from orev3.rfc008.storage import RFC008Store, strict_json


OPERATIONAL_BURN_IN_AUTHORIZATION = (
    "RFC008_OPERATIONAL_RESOLVER_BURN_IN_AUTHORIZED"
)
MINIMUM_OPERATIONAL_SAMPLE_SIZE = 5
DEFAULT_OPERATIONAL_SAMPLE_SIZE = 5
SELECTION_POLICY = (
    "latest consecutive completed rounds strictly before the durable observer "
    "boundary, selected as boundary-sample_size through boundary-1"
)


def select_operational_rounds(
    boundary_round_id: int, sample_size: int = DEFAULT_OPERATIONAL_SAMPLE_SIZE
) -> tuple[int, ...]:
    if sample_size < MINIMUM_OPERATIONAL_SAMPLE_SIZE:
        raise ValueError("Operational resolver burn-in requires at least 5 rounds")
    if boundary_round_id <= sample_size:
        raise ValueError("Observer boundary cannot supply the bounded sample")
    selected = tuple(range(boundary_round_id - sample_size, boundary_round_id))
    if len(selected) != sample_size or len(set(selected)) != sample_size:
        raise ValueError("Operational burn-in selection must be distinct")
    return selected


def _round_account_bytes(
    round_id: int, *, entropy: int = 26, total_winnings: int = 2_000
) -> bytes:
    body = b"".join(
        (
            struct.pack("<Q", round_id),
            struct.pack("<25Q", *[round_id + index for index in range(25)]),
            struct.pack("<25Q", *([0] * 25)),
            struct.pack("<25Q", *([1] * 25)),
            struct.pack("<QQQQ", entropy, 0, 0, 0),
            struct.pack("<Q", 999),
            struct.pack("<Q", 7),
            bytes(32),
            struct.pack("<25Q", *([2] * 25)),
            struct.pack("<Q", 1_000),
            struct.pack("<Q", total_winnings),
            struct.pack("<Q", 25),
            bytes(32),
        )
    )
    return bytes([109]) + bytes(7) + body


class FixtureOutcomeProvider:
    def __init__(
        self,
        provider_id: str,
        config: ResolverConfig,
        accounts: dict[str, bytes],
        *,
        failures_remaining: int = 0,
        call_counts: Counter[str] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.config = config
        self.accounts = accounts
        self.failures_remaining = failures_remaining
        self.call_counts = call_counts

    def get_genesis_hash(self) -> str:
        if self.call_counts is not None:
            self.call_counts["get_genesis_hash"] += 1
        return self.config.expected_genesis_hash

    def get_account_info_with_context(
        self, address: str, *, commitment: str
    ) -> dict[str, Any]:
        if self.call_counts is not None:
            self.call_counts["get_account_info_with_context"] += 1
        if commitment != "finalized":
            raise ValueError("Fixture provider requires finalized commitment")
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise TimeoutError("fixture retry")
        raw = self.accounts.get(address)
        return {
            "context": {"slot": 500},
            "value": (
                None
                if raw is None
                else {
                    "owner": self.config.expected_program_owner,
                    "data": [base64.b64encode(raw).decode(), "base64"],
                }
            ),
        }

    def close(self) -> None:
        return None


class RpcAccounting:
    def __init__(self, provider_ids: tuple[str, ...]) -> None:
        self.provider_ids = provider_ids
        self.by_provider: Counter[str] = Counter()
        self.by_method: Counter[str] = Counter()
        self.by_provider_and_method: dict[str, Counter[str]] = defaultdict(Counter)
        self.successful_responses = 0
        self.unavailable_responses = 0
        self.malformed_responses = 0
        self.retried_requests = 0
        self._failed_keys: set[tuple[str, str, str]] = set()

    def begin(
        self,
        provider_id: str,
        method: str,
        identity: str = "",
        *,
        retry_request: bool | None = None,
    ) -> bool:
        key = (provider_id, method, identity)
        retried = (
            key in self._failed_keys
            if retry_request is None
            else retry_request
        )
        if retried:
            self.retried_requests += 1
        self.by_provider[provider_id] += 1
        self.by_method[method] += 1
        self.by_provider_and_method[provider_id][method] += 1
        return retried

    def success(self) -> None:
        self.successful_responses += 1

    def unavailable(self, provider_id: str, method: str, identity: str = "") -> None:
        self.unavailable_responses += 1
        self._failed_keys.add((provider_id, method, identity))

    def malformed(self, provider_id: str, method: str, identity: str = "") -> None:
        self.malformed_responses += 1
        self._failed_keys.add((provider_id, method, identity))

    def evidence(self) -> RpcRequestCounts:
        methods = ("get_genesis_hash", "get_account_info_with_context")
        by_provider = {
            provider: self.by_provider[provider] for provider in self.provider_ids
        }
        by_method = {method: self.by_method[method] for method in methods}
        detail = {
            provider: {
                method: self.by_provider_and_method[provider][method]
                for method in methods
            }
            for provider in self.provider_ids
        }
        total = sum(by_provider.values())
        return RpcRequestCounts(
            total=total,
            by_provider=by_provider,
            by_method=by_method,
            by_provider_and_method=detail,
            successful_responses=self.successful_responses,
            unavailable_responses=self.unavailable_responses,
            malformed_responses=self.malformed_responses,
            failed_responses=(
                self.unavailable_responses + self.malformed_responses
            ),
            retried_requests=self.retried_requests,
            finalized_account_reads=by_method["get_account_info_with_context"],
            genesis_hash_reads=by_method["get_genesis_hash"],
        )


class CountingOutcomeProvider:
    def __init__(
        self,
        provider: Any,
        *,
        accounting: RpcAccounting,
        resolver_config: ResolverConfig,
        address_to_round: dict[str, int],
    ) -> None:
        self.provider = provider
        self.provider_id = provider.provider_id
        self.accounting = accounting
        self.resolver_config = resolver_config
        self.address_to_round = address_to_round
        self.genesis_hash: str | None = None
        self.round_traces: dict[int, dict[str, object]] = {}
        self.requests: list[OperationalRequestEvidence] = []
        self.active_attempt_id: str | None = None
        self.active_attempt_number: int | None = None

    def set_attempt(self, attempt_id: str, attempt_number: int) -> None:
        self.active_attempt_id = attempt_id
        self.active_attempt_number = attempt_number

    def _record(
        self,
        *,
        method: str,
        requested_at: datetime,
        classification: str,
        identity: str = "",
        round_id: int | None = None,
        commitment: str | None = None,
        retry_request: bool = False,
    ) -> str:
        request_id = deterministic_id(
            "rfc008-operational-request-v1",
            self.provider_id,
            method,
            identity,
            len(self.requests),
            requested_at.isoformat(),
        )
        self.requests.append(
            OperationalRequestEvidence(
                request_id=request_id,
                attempt_id=(
                    self.active_attempt_id
                    if method == "get_account_info_with_context"
                    else None
                ),
                round_id=round_id,
                round_pda=identity or None,
                provider_id=self.provider_id,
                method=method,
                requested_at=requested_at,
                classification=classification,
                retry_request=retry_request,
                commitment=commitment,
            )
        )
        return request_id

    def get_genesis_hash(self) -> str:
        method = "get_genesis_hash"
        requested_at = datetime.now(timezone.utc)
        retried = self.accounting.begin(self.provider_id, method)
        try:
            value = self.provider.get_genesis_hash()
        except Exception:
            self.accounting.unavailable(self.provider_id, method)
            self._record(
                method=method,
                requested_at=requested_at,
                classification="unavailable",
                retry_request=retried,
            )
            raise
        if not isinstance(value, str) or not value:
            self.accounting.malformed(self.provider_id, method)
            self._record(
                method=method,
                requested_at=requested_at,
                classification="malformed",
                retry_request=retried,
            )
            raise ValueError("Malformed genesis-hash response")
        self.genesis_hash = value
        self.accounting.success()
        self._record(
            method=method,
            requested_at=requested_at,
            classification="successful",
            retry_request=retried,
        )
        return value

    def get_account_info_with_context(
        self, address: str, *, commitment: str
    ) -> dict[str, Any]:
        method = "get_account_info_with_context"
        retried = self.accounting.begin(
            self.provider_id,
            method,
            address,
            retry_request=bool(
                self.active_attempt_number
                and self.active_attempt_number > 1
            ),
        )
        requested_at = datetime.now(timezone.utc)
        round_id = self.address_to_round.get(address)
        try:
            response = self.provider.get_account_info_with_context(
                address, commitment=commitment
            )
        except Exception:
            self.accounting.unavailable(self.provider_id, method, address)
            self._record(
                method=method,
                requested_at=requested_at,
                classification="unavailable",
                identity=address,
                round_id=round_id,
                commitment=commitment,
                retry_request=retried,
            )
            raise
        if round_id is None:
            self.accounting.malformed(self.provider_id, method, address)
            self._record(
                method=method,
                requested_at=requested_at,
                classification="malformed",
                identity=address,
                commitment=commitment,
                retry_request=retried,
            )
            raise ValueError("RPC response does not match a selected round PDA")
        try:
            decoded = _decode_response(
                response,
                round_id=round_id,
                round_pda=address,
                provider_id=self.provider_id,
                requested_at=requested_at,
                resolver_config=self.resolver_config,
            )
        except Exception:
            account = response.get("value") if isinstance(response, dict) else None
            if account is None:
                self.accounting.unavailable(self.provider_id, method, address)
                classification = "unavailable"
            else:
                self.accounting.malformed(self.provider_id, method, address)
                classification = "malformed"
            self._record(
                method=method,
                requested_at=requested_at,
                classification=classification,
                identity=address,
                round_id=round_id,
                commitment=commitment,
                retry_request=retried,
            )
            raise
        request_id = self._record(
            method=method,
            requested_at=requested_at,
            classification="successful",
            identity=address,
            round_id=round_id,
            commitment=commitment,
            retry_request=retried,
        )
        decoded["request_id"] = request_id
        self.round_traces[round_id] = decoded
        self.accounting.success()
        return response

    def close(self) -> None:
        self.provider.close()


def _write_evidence(
    evidence: ResolverBurnInEvidence, output_path: str | Path
) -> str:
    path = Path(output_path)
    sidecar = Path(str(path) + ".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError("Burn-in evidence or checksum exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (strict_json(evidence) + "\n").encode()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    sidecar_temporary = sidecar.with_name(
        f".{sidecar.name}.{os.getpid()}.tmp"
    )
    digest = hashlib.sha256(payload).hexdigest()
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        with sidecar_temporary.open("xb") as handle:
            handle.write(f"{digest}  {path.name}\n".encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.link(sidecar_temporary, sidecar)
        try:
            os.link(temporary, path)
        except Exception:
            sidecar.unlink(missing_ok=True)
            raise
    finally:
        temporary.unlink(missing_ok=True)
        sidecar_temporary.unlink(missing_ok=True)
    return digest


def _attempt_count(store: RFC008Store, round_id: int) -> int:
    return int(
        store.connection.execute(
            "SELECT COUNT(*) FROM outcome_attempts WHERE round_id=?", (round_id,)
        ).fetchone()[0]
    )


def _operational_round_evidence(
    *,
    store: RFC008Store,
    round_id: int,
    selection_order: int,
    result: str,
    providers: tuple[CountingOutcomeProvider, ...],
    resolver_config: ResolverConfig,
) -> OperationalRoundEvidence:
    pda = derive_round_pda(round_id, resolver_config.expected_program_owner)
    traces = [
        provider.round_traces[round_id]
        for provider in providers
        if round_id in provider.round_traces
    ]
    canonical_hashes = {
        str(trace["canonical_response_sha256"]) for trace in traces
    }
    canonical = traces[0]["canonical"] if traces else None
    provider_evidence = tuple(
        ProviderRoundEvidence(
            request_id=str(trace["request_id"]),
            provider_id=str(trace["provider_id"]),
            request_method="get_account_info_with_context",
            requested_at=str(trace["requested_at"]),
            commitment="finalized",
            genesis_hash=str(provider.genesis_hash or ""),
            response_context_slot=int(trace["context_slot"]),
            raw_response_sha256=str(trace["raw_response_sha256"]),
            canonical_response_sha256=str(trace["canonical_response_sha256"]),
            account_owner=str(trace["canonical"]["owner"]),
            returned_account_identity=pda,
            decoded_round_id=int(trace["canonical"]["round_id"]),
        )
        for provider, trace in (
            (provider, provider.round_traces[round_id])
            for provider in providers
            if round_id in provider.round_traces
        )
    )
    provider_ids = tuple(value.provider_id for value in provider_evidence)
    complete = (
        result == "accepted"
        and len(provider_evidence) == len(resolver_config.provider_ids)
        and provider_ids == resolver_config.provider_ids
        and len(canonical_hashes) == 1
    )
    deployments = tuple(canonical["final_square_deployments"]) if canonical else ()
    accounting_values = (
        canonical.get("total_vaulted"),
        canonical.get("total_winnings"),
        canonical.get("motherlode_raw"),
    ) if canonical else ()
    return OperationalRoundEvidence(
        round_id=round_id,
        round_pda=pda,
        selection_order=selection_order,
        provider_ids=provider_ids,
        provider_evidence=provider_evidence,
        entropy=int(canonical["entropy"]) if canonical else None,
        winning_square=int(canonical["winner_square"]) if canonical else None,
        deployment_vector_validated=(
            len(deployments) == 25
            and all(isinstance(value, int) and value >= 0 for value in deployments)
        ),
        accounting_validated=(
            bool(accounting_values)
            and all(isinstance(value, int) and value >= 0 for value in accounting_values)
        ),
        provider_agreement=complete,
        owner_validation_passed=(
            complete
            and all(
                value.account_owner == resolver_config.expected_program_owner
                for value in provider_evidence
            )
        ),
        pda_validation_passed=(
            pda == derive_round_pda(round_id, resolver_config.expected_program_owner)
        ),
        account_identity_passed=(
            complete
            and all(value.returned_account_identity == pda for value in provider_evidence)
        ),
        decoded_round_identity_passed=(
            complete
            and all(value.decoded_round_id == round_id for value in provider_evidence)
        ),
        finalized_validation_passed=(
            complete
            and all(
                value.commitment == "finalized" and value.response_context_slot > 0
                for value in provider_evidence
            )
        ),
        provenance_complete=(
            complete
            and all(
                value.raw_response_sha256
                and value.canonical_response_sha256
                and value.genesis_hash
                and value.requested_at
                for value in provider_evidence
            )
        ),
        final_state=result if result in {"accepted", "retry", "conflict"} else "failed",
        attempt_count=_attempt_count(store, round_id),
        request_timestamps=tuple(value.requested_at for value in provider_evidence),
    )


def _summary(
    *,
    mode: str,
    sample_size: int,
    selected_round_ids: tuple[int, ...],
    selection_source: str,
    selection_boundary_round_id: int | None,
    rounds: tuple[OperationalRoundEvidence, ...],
) -> OperationalBurnInSummary:
    accepted = sum(value.final_state == "accepted" for value in rounds)
    return OperationalBurnInSummary(
        requested_sample_size=sample_size if mode == "operational" else 0,
        selection_policy=SELECTION_POLICY,
        selection_source=selection_source,
        selection_boundary_round_id=selection_boundary_round_id,
        selected_round_ids=selected_round_ids,
        selected_round_count=len(selected_round_ids),
        distinct_round_count=len(set(selected_round_ids)),
        successful_authoritative_count=accepted,
        failed_count=sum(value.final_state == "failed" for value in rounds),
        unresolved_count=sum(value.final_state == "retry" for value in rounds),
        conflicted_count=sum(value.final_state == "conflict" for value in rounds),
        quarantined_count=0,
        provider_agreement_count=sum(value.provider_agreement for value in rounds),
        owner_validation_pass_count=sum(
            value.owner_validation_passed for value in rounds
        ),
        identity_validation_pass_count=sum(
            value.pda_validation_passed
            and value.account_identity_passed
            and value.decoded_round_identity_passed
            for value in rounds
        ),
        finalized_validation_pass_count=sum(
            value.finalized_validation_passed for value in rounds
        ),
        deployment_validation_pass_count=sum(
            value.deployment_vector_validated for value in rounds
        ),
        accounting_validation_pass_count=sum(
            value.accounting_validated for value in rounds
        ),
        complete_provenance_count=sum(
            value.provenance_complete for value in rounds
        ),
        five_round_criterion_passed=(
            mode == "operational"
            and sample_size >= MINIMUM_OPERATIONAL_SAMPLE_SIZE
            and len(rounds) == sample_size
            and len(set(selected_round_ids)) == sample_size
            and accepted == sample_size
            and all(
                value.provider_agreement
                and value.owner_validation_passed
                and value.pda_validation_passed
                and value.account_identity_passed
                and value.decoded_round_identity_passed
                and value.finalized_validation_passed
                and value.provenance_complete
                for value in rounds
            )
        ),
        rounds=rounds,
    )


def _fixture_providers(
    resolver_config: ResolverConfig,
    round_id: int,
    *,
    entropy_primary: int = 26,
    entropy_secondary: int = 26,
    failures_remaining: int = 0,
    calls: Counter[str],
) -> tuple[FixtureOutcomeProvider, ...]:
    pda = derive_round_pda(round_id, resolver_config.expected_program_owner)
    return (
        FixtureOutcomeProvider(
            resolver_config.provider_ids[0],
            resolver_config,
            {pda: _round_account_bytes(round_id, entropy=entropy_primary)},
            failures_remaining=failures_remaining,
            call_counts=calls,
        ),
        FixtureOutcomeProvider(
            resolver_config.provider_ids[1],
            resolver_config,
            {pda: _round_account_bytes(round_id, entropy=entropy_secondary)},
            call_counts=calls,
        ),
    )


def _controlled_exercises(
    *,
    ledger: Path,
    experiment: RFC008Config,
    resolver_config: ResolverConfig,
    base_round_id: int,
    current: datetime,
    fixture_calls: Counter[str],
) -> tuple[
    RestartRetryEvidence,
    JitterTestEvidence,
    ConflictTestEvidence,
    QuarantineTestEvidence,
]:
    retry_round = base_round_id
    retry_pda = derive_round_pda(
        retry_round, resolver_config.expected_program_owner
    )
    with RFC008Store(ledger, config=experiment) as store:
        with store.connection:
            store.start_round(retry_round, current)
            enqueue_pending(store, retry_round, at=current)
            resolver = FinalizedOutcomeResolver(
                store=store,
                experiment_config=experiment,
                resolver_config=resolver_config,
                providers=_fixture_providers(
                    resolver_config,
                    retry_round,
                    failures_remaining=1,
                    calls=fixture_calls,
                ),
            )
            initial_result = resolver.resolve_round(retry_round, now=current)
            persisted = store.queue(retry_round)
            assert persisted is not None and persisted.next_retry_at is not None
            persisted_attempt_count = _attempt_count(store, retry_round)
            retry_at = persisted.next_retry_at
            retry_count = persisted.retry_count
            retry_state = persisted.state
    with RFC008Store(ledger, config=experiment) as restarted:
        persisted_after_restart = restarted.queue(retry_round)
        assert persisted_after_restart is not None
        resolver = FinalizedOutcomeResolver(
            store=restarted,
            experiment_config=experiment,
            resolver_config=resolver_config,
            providers=_fixture_providers(
                resolver_config, retry_round, calls=fixture_calls
            ),
        )
        with restarted.connection:
            final_result = resolver.resolve_round(retry_round, now=retry_at)
        final_queue = restarted.queue(retry_round)
        assert final_queue is not None
        retry_numbers = (1, 2, 3)

        def retry_delay(retry_number: int) -> int:
            exponential = resolver_config.base_retry_seconds * (
                2 ** max(retry_number - 1, 0)
            )
            jitter_value = int.from_bytes(
                hashlib.sha256(
                    (
                        f"rfc008-retry-jitter-v1:{retry_round}:"
                        f"{retry_number}"
                    ).encode()
                ).digest()[:8],
                "big",
            ) % resolver_config.jitter_modulus_seconds
            return min(
                exponential + jitter_value,
                resolver_config.maximum_retry_seconds,
            )

        expected_delays = tuple(retry_delay(value) for value in retry_numbers)
        recomputed_delays = tuple(retry_delay(value) for value in retry_numbers)
        expected_retry_at = current + timedelta(seconds=expected_delays[0])
        restart_retry = RestartRetryEvidence(
            test_type="controlled_restart_retry",
            evidence_mode="fixture",
            round_id=retry_round,
            initial_state=retry_state,
            persisted_retry_count=retry_count,
            persisted_next_retry_time=retry_at,
            persisted_pda=persisted_after_restart.round_pda,
            persisted_attempt_count=persisted_attempt_count,
            restart_state=persisted_after_restart.state,
            final_result=final_result,
            final_state=final_queue.state,
            recomputed_restart_test_passed=(
                persisted_after_restart.retry_count == retry_count
                and persisted_after_restart.next_retry_at == retry_at
                and persisted_after_restart.round_pda == retry_pda
                and persisted_attempt_count == 1
            ),
            recomputed_retry_test_passed=(
                initial_result == "retry"
                and final_result == "accepted"
                and final_queue.state == "finalized"
            ),
            restart_test_passed=(
                persisted_after_restart.retry_count == retry_count
                and persisted_after_restart.next_retry_at == retry_at
                and persisted_after_restart.round_pda == retry_pda
                and persisted_attempt_count == 1
            ),
            retry_test_passed=(
                initial_result == "retry"
                and final_result == "accepted"
                and final_queue.state == "finalized"
            ),
        )
        jitter = JitterTestEvidence(
            test_type="controlled_jitter",
            evidence_mode="fixture",
            round_id=retry_round,
            retry_numbers_tested=retry_numbers,
            expected_delays_seconds=expected_delays,
            recomputed_delays_seconds=recomputed_delays,
            deterministic_match=expected_delays == recomputed_delays,
            bounded_delay_result=all(
                0 < value <= resolver_config.maximum_retry_seconds
                for value in expected_delays
            ),
            persisted_schedule_match=retry_at == expected_retry_at,
            jitter_derivation_version="rfc008-retry-jitter-v1",
            recomputed_jitter_test_passed=(
                expected_delays == recomputed_delays
                and retry_at == expected_retry_at
                and all(
                    0 < value <= resolver_config.maximum_retry_seconds
                    for value in expected_delays
                )
            ),
            jitter_test_passed=(
                expected_delays == recomputed_delays
                and retry_at == expected_retry_at
                and all(
                    0 < value <= resolver_config.maximum_retry_seconds
                    for value in expected_delays
                )
            ),
        )

        conflict_round = base_round_id + 1
        with restarted.connection:
            restarted.start_round(conflict_round, current)
            enqueue_pending(restarted, conflict_round, at=current)
            conflict_resolver = FinalizedOutcomeResolver(
                store=restarted,
                experiment_config=experiment,
                resolver_config=resolver_config,
                providers=_fixture_providers(
                    resolver_config,
                    conflict_round,
                    entropy_primary=1,
                    entropy_secondary=2,
                    calls=fixture_calls,
                ),
            )
            conflict_result = conflict_resolver.resolve_round(
                conflict_round, now=current
            )
        overwrite_refused = False
        try:
            with restarted.connection:
                FinalizedOutcomeResolver(
                    store=restarted,
                    experiment_config=experiment,
                    resolver_config=resolver_config,
                    providers=_fixture_providers(
                        resolver_config, conflict_round, calls=fixture_calls
                    ),
                ).resolve_round(conflict_round, now=current)
        except ValueError:
            overwrite_refused = True
        conflict_queue = restarted.queue(conflict_round)
        conflict_rows = restarted.connection.execute(
            """
            SELECT record_json FROM outcome_conflicts
            WHERE round_id=? ORDER BY created_at, conflict_id
            """,
            (conflict_round,),
        ).fetchall()
        conflict_count = len(conflict_rows)
        conflict_record = (
            json.loads(str(conflict_rows[0][0]))
            if conflict_count == 1
            else {}
        )
        provider_provenance = conflict_record.get("provider_evidence", {})
        provider_hashes = {
            str(value.get("canonical_response_sha256"))
            for value in provider_provenance.values()
            if isinstance(value, dict)
        } if isinstance(provider_provenance, dict) else set()
        provenance_retained = (
            isinstance(provider_provenance, dict)
            and set(provider_provenance) == set(resolver_config.provider_ids)
        )
        disagreement_retained = (
            conflict_record.get("conflict_status") == "conflicted"
            and len(provider_hashes) == len(resolver_config.provider_ids)
        )
        terminal_conflict_persisted = (
            conflict_queue is not None
            and conflict_queue.state == "conflicted"
        )
        primary_ineligible_conflict = (
            restarted.accepted_outcome(conflict_round) is None
        )
        later_conflict_replacement_refused = (
            overwrite_refused
            and terminal_conflict_persisted
            and primary_ineligible_conflict
        )
        conflict_passed = (
            conflict_result == "conflict"
            and provenance_retained
            and disagreement_retained
            and terminal_conflict_persisted
            and overwrite_refused
            and later_conflict_replacement_refused
            and primary_ineligible_conflict
        )
        conflict = ConflictTestEvidence(
            test_type="controlled_conflict",
            evidence_mode="fixture",
            round_id=conflict_round,
            conflict_state=conflict_queue.state if conflict_queue else "missing",
            provider_provenance_count=(
                len(provider_provenance)
                if isinstance(provider_provenance, dict)
                else 0
            ),
            provenance_retained=provenance_retained,
            disagreement_details_retained=disagreement_retained,
            terminal_conflict_persisted=terminal_conflict_persisted,
            overwrite_attempted=True,
            overwrite_refused=overwrite_refused,
            later_success_replacement_refused=(
                later_conflict_replacement_refused
            ),
            primary_analysis_ineligible=primary_ineligible_conflict,
            recomputed_conflict_test_passed=conflict_passed,
            conflict_test_passed=conflict_passed,
        )

        quarantine_round = base_round_id + 2
        with restarted.connection:
            restarted.start_round(quarantine_round, current)
            initial = enqueue_pending(restarted, quarantine_round, at=current)
            changed = quarantine_expired(
                restarted,
                now=current
                + timedelta(
                    seconds=resolver_config.quarantine_after_seconds + 1
                ),
                age=timedelta(
                    seconds=resolver_config.quarantine_after_seconds
                ),
            )
        quarantined = restarted.queue(quarantine_round)
    with RFC008Store(ledger, config=experiment) as quarantine_restart:
        persisted_quarantine = quarantine_restart.queue(quarantine_round)
        quarantine_overwrite_refused = False
        try:
            with quarantine_restart.connection:
                FinalizedOutcomeResolver(
                    store=quarantine_restart,
                    experiment_config=experiment,
                    resolver_config=resolver_config,
                    providers=_fixture_providers(
                        resolver_config, quarantine_round, calls=fixture_calls
                    ),
                ).resolve_round(quarantine_round, now=current)
        except ValueError:
            quarantine_overwrite_refused = True
        primary_ineligible = (
            quarantine_restart.accepted_outcome(quarantine_round) is None
        )
        final_quarantine = quarantine_restart.queue(quarantine_round)
        quarantine_persisted = (
            quarantined is not None
            and persisted_quarantine is not None
            and quarantined.state == "quarantined"
            and persisted_quarantine.state == "quarantined"
        )
        later_quarantine_replacement_refused = (
            quarantine_overwrite_refused
            and final_quarantine is not None
            and final_quarantine.state == "quarantined"
            and primary_ineligible
        )
        quarantine_passed = (
            initial.state == "pending"
            and changed == 1
            and persisted_quarantine is not None
            and persisted_quarantine.state == "quarantined"
            and quarantine_persisted
            and quarantine_overwrite_refused
            and later_quarantine_replacement_refused
            and primary_ineligible
        )
        quarantine = QuarantineTestEvidence(
            test_type="controlled_quarantine",
            evidence_mode="fixture",
            quarantine_round_id=quarantine_round,
            configured_expiration_seconds=(
                resolver_config.quarantine_after_seconds
            ),
            quarantine_initial_state=initial.state,
            expiry_reached=True,
            production_transition_invoked=changed == 1,
            quarantine_final_state=(
                persisted_quarantine.state
                if persisted_quarantine is not None
                else "missing"
            ),
            quarantine_restart_persistence=quarantine_persisted,
            overwrite_attempted=True,
            quarantine_overwrite_refused=quarantine_overwrite_refused,
            later_success_replacement_refused=(
                later_quarantine_replacement_refused
            ),
            primary_analysis_ineligible=primary_ineligible,
            recomputed_quarantine_test_passed=quarantine_passed,
            quarantine_test_passed=quarantine_passed,
        )
    return restart_retry, jitter, conflict, quarantine


def _repository_state(root: Path) -> tuple[str, str]:
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=root, text=True
    ).strip()
    return commit, branch


def _process_snapshot(
    process_ids: tuple[int, ...],
) -> dict[int, tuple[str, str, datetime]]:
    snapshot: dict[int, tuple[str, str, datetime]] = {}
    for process_id in process_ids:
        if process_id <= 0:
            raise ValueError("Preserved process IDs must be positive")
        command = subprocess.check_output(
            ["ps", "-p", str(process_id), "-o", "command="],
            text=True,
        ).strip()
        if not command:
            raise RuntimeError(f"Required process is not running: {process_id}")
        role = REQUIRED_PROTECTED_PROCESSES.get(process_id)
        if role is None:
            raise ValueError(f"Unapproved protected process PID: {process_id}")
        required_fragment = REQUIRED_PROCESS_COMMAND_IDENTITIES[role]
        if required_fragment not in command:
            raise RuntimeError(
                f"Protected process command identity mismatch: {process_id}"
            )
        snapshot[process_id] = (
            hashlib.sha256(command.encode()).hexdigest(),
            required_fragment,
            datetime.now(timezone.utc),
        )
    return snapshot


def _process_evidence(
    *,
    mode: str,
    before: dict[int, tuple[str, str, datetime]],
    after: dict[int, tuple[str, str, datetime]],
    current: datetime,
) -> tuple[ProtectedProcessEvidence, ...]:
    values = []
    for pid, role in REQUIRED_PROTECTED_PROCESSES.items():
        if mode == "fixture":
            command = f"fixture:{role}"
            digest = hashlib.sha256(command.encode()).hexdigest()
            values.append(
                ProtectedProcessEvidence(
                    pid=pid,
                    role=role,
                    sanitized_command_identity=command,
                    observed_before=True,
                    observed_after=True,
                    before_command_sha256=digest,
                    after_command_sha256=digest,
                    before_observed_at=current,
                    after_observed_at=current,
                    unchanged=True,
                    evidence_mode="fixture",
                )
            )
            continue
        before_value = before.get(pid)
        after_value = after.get(pid)
        values.append(
            ProtectedProcessEvidence(
                pid=pid,
                role=role,
                sanitized_command_identity=(
                    before_value[1] if before_value else f"missing:{role}"
                ),
                observed_before=before_value is not None,
                observed_after=after_value is not None,
                before_command_sha256=(
                    before_value[0] if before_value else "0" * 64
                ),
                after_command_sha256=(
                    after_value[0] if after_value else "0" * 64
                ),
                before_observed_at=(
                    before_value[2] if before_value else current
                ),
                after_observed_at=(
                    after_value[2] if after_value else current
                ),
                unchanged=(
                    before_value is not None
                    and after_value is not None
                    and before_value[0] == after_value[0]
                ),
                evidence_mode="operational",
            )
        )
    return tuple(values)


def _safety_inspection(experiment: RFC008Config) -> bool:
    return not any(
        (
            experiment.allow_transaction_building,
            experiment.allow_transaction_submission,
            experiment.allow_signing,
            experiment.allow_claims,
            experiment.allow_wallet_access,
        )
    )


def _safe_burnin_paths(
    ledger_path: str | Path, output_path: str | Path
) -> tuple[Path, Path]:
    ledger = Path(ledger_path)
    output = Path(output_path)
    joined = f"{ledger} {output}".lower()
    if "rfc007" in joined or "rfc008_paper_ledger" in joined or "rfc008_marker" in joined:
        raise ValueError("Burn-in refuses production, marker, or RFC-007 paths")
    if ledger.exists() or output.exists() or Path(str(output) + ".sha256").exists():
        raise FileExistsError("Burn-in outputs must not already exist")
    return ledger, output


def run_resolver_burn_in(
    *,
    ledger_path: str | Path,
    output_path: str | Path,
    experiment_config_path: str | Path,
    resolver_config_path: str | Path,
    mode: str,
    sample_size: int = DEFAULT_OPERATIONAL_SAMPLE_SIZE,
    control_round_id: int | None = None,
    authorization_token: str | None = None,
    release_approval_path: str | Path = (
        "docs/research/rfc008/release_implementation_approval_v1.json"
    ),
    repository_root: str | Path = ".",
    preserve_process_ids: tuple[int, ...] = (),
    now: datetime | None = None,
) -> dict[str, object]:
    if mode not in {"fixture", "operational"}:
        raise ValueError("Burn-in mode must be fixture or operational")
    if mode == "operational":
        if authorization_token != OPERATIONAL_BURN_IN_AUTHORIZATION:
            raise PermissionError("Operational resolver burn-in requires authorization")
        if sample_size < MINIMUM_OPERATIONAL_SAMPLE_SIZE:
            raise ValueError("Operational resolver burn-in requires at least 5 rounds")
        if control_round_id is not None:
            raise ValueError("Operational round selection is automatic and bounded")
        if not preserve_process_ids:
            raise ValueError(
                "Operational burn-in requires preserved-process checks"
            )
        if (
            len(preserve_process_ids) != len(set(preserve_process_ids))
            or set(preserve_process_ids) != set(REQUIRED_PROTECTED_PROCESSES)
        ):
            raise ValueError(
                "Operational burn-in requires exactly the three approved "
                "protected process PIDs"
            )
    ledger, output = _safe_burnin_paths(ledger_path, output_path)
    experiment = RFC008Config.from_path(experiment_config_path)
    resolver_config = ResolverConfig.from_path(resolver_config_path)
    current = now or datetime.now(timezone.utc)
    root = Path(repository_root).resolve()
    production_marker = root / "data/ledger/rfc008_marker_v1.json"
    initial_lifecycle = capture_marker_pair(production_marker)
    approval_path = Path(release_approval_path)
    if not approval_path.is_absolute():
        approval_path = root / approval_path
    release_hash = hashlib.sha256(approval_path.read_bytes()).hexdigest()
    repository_commit, repository_branch = _repository_state(root)
    initial_processes = (
        _process_snapshot(preserve_process_ids)
        if mode == "operational"
        else {}
    )

    selected: tuple[int, ...] = ()
    source = "fixture-only; no operational rounds selected"
    boundary_round_id: int | None = None
    source_boundary: BurnInSourceBoundary
    if mode == "operational":
        boundary, _ = derive_runtime_source_boundary(experiment.source_glob)
        boundary_round_id = boundary.round_id
        source = (
            f"{boundary.source_path}|inode={boundary.source_inode}|"
            f"offset={boundary.source_byte_offset}|line={boundary.source_line_number}|"
            f"record_sha256={boundary.source_record_sha256}"
        )
        selected = select_operational_rounds(boundary.round_id, sample_size)
        source_boundary = BurnInSourceBoundary(
            round_id=boundary.round_id,
            source_path=boundary.source_path,
            inode=boundary.source_inode,
            byte_offset=boundary.source_byte_offset,
            line_number=boundary.source_line_number,
            record_sha256=boundary.source_record_sha256,
            record_timestamp=boundary.source_observed_at,
            observed_at=current,
        )
    elif control_round_id is None:
        control_round_id = 900_001
        fixture_hash = hashlib.sha256(
            f"fixture-boundary:{control_round_id}".encode()
        ).hexdigest()
        source_boundary = BurnInSourceBoundary(
            round_id=control_round_id,
            source_path="fixture://rfc008-resolver-burn-in",
            inode=0,
            byte_offset=0,
            line_number=1,
            record_sha256=fixture_hash,
            record_timestamp=current,
            observed_at=current,
        )
    else:
        fixture_hash = hashlib.sha256(
            f"fixture-boundary:{control_round_id}".encode()
        ).hexdigest()
        source_boundary = BurnInSourceBoundary(
            round_id=control_round_id,
            source_path="fixture://rfc008-resolver-burn-in",
            inode=0,
            byte_offset=0,
            line_number=1,
            record_sha256=fixture_hash,
            record_timestamp=current,
            observed_at=current,
        )

    real_accounting = RpcAccounting(resolver_config.provider_ids)
    provider_genesis_hashes: dict[str, str] = {}
    round_evidence: tuple[OperationalRoundEvidence, ...] = ()
    operational_attempts: tuple[OperationalAttemptEvidence, ...] = ()
    operational_requests: tuple[OperationalRequestEvidence, ...] = ()
    operational_providers: tuple[CountingOutcomeProvider, ...] = ()
    with RFC008Store(ledger, config=experiment, create=True) as store:
        if mode == "operational":
            address_to_round = {
                derive_round_pda(value, resolver_config.expected_program_owner): value
                for value in selected
            }
            urls = []
            for variable in resolver_config.provider_url_environment_variables:
                value = os.environ.get(variable)
                if not value:
                    raise ValueError(f"Missing provider environment variable: {variable}")
                urls.append(value)
            if len(set(urls)) != len(urls):
                raise ValueError("Operational outcome providers must be independent")
            operational_providers = tuple(
                CountingOutcomeProvider(
                    RpcRecoveryProvider(provider_id, url),
                    accounting=real_accounting,
                    resolver_config=resolver_config,
                    address_to_round=address_to_round,
                )
                for provider_id, url in zip(resolver_config.provider_ids, urls)
            )
            resolver = FinalizedOutcomeResolver(
                store=store,
                experiment_config=experiment,
                resolver_config=resolver_config,
                providers=operational_providers,
            )
            try:
                resolver.validate_provider_networks()
                provider_genesis_hashes = {
                    provider.provider_id: str(provider.genesis_hash)
                    for provider in operational_providers
                }
                values = []
                attempt_values = []
                for order, round_id in enumerate(selected, 1):
                    with store.connection:
                        store.start_round(round_id, current)
                        queue = enqueue_pending(store, round_id, at=current)
                        attempt_id = deterministic_id(
                            "rfc008-outcome-attempt",
                            round_id,
                            queue.retry_count,
                            current.isoformat(),
                        )
                        attempt_number = queue.retry_count + 1
                        for provider in operational_providers:
                            provider.set_attempt(attempt_id, attempt_number)
                        result = resolver.resolve_round(round_id, now=current)
                    persisted_attempt = store.connection.execute(
                        """
                        SELECT 1 FROM outcome_attempts
                        WHERE attempt_id=? AND round_id=?
                        """,
                        (attempt_id, round_id),
                    ).fetchone()
                    provider_request_ids = tuple(
                        request.request_id
                        for provider in operational_providers
                        for request in provider.requests
                        if request.attempt_id == attempt_id
                    )
                    attempt_values.append(
                        OperationalAttemptEvidence(
                            attempt_id=attempt_id,
                            round_id=round_id,
                            attempt_number=attempt_number,
                            attempted_at=current,
                            status=(
                                result
                                if result in {"accepted", "retry", "conflict"}
                                else "failed"
                            ),
                            provider_request_ids=provider_request_ids,
                            persisted=persisted_attempt is not None,
                        )
                    )
                    values.append(
                        _operational_round_evidence(
                            store=store,
                            round_id=round_id,
                            selection_order=order,
                            result=result,
                            providers=operational_providers,
                            resolver_config=resolver_config,
                        )
                    )
                round_evidence = tuple(values)
                operational_attempts = tuple(attempt_values)
                operational_requests = tuple(
                    request
                    for provider in operational_providers
                    for request in provider.requests
                )
            finally:
                for provider in operational_providers:
                    provider.close()

    operational = _summary(
        mode=mode,
        sample_size=sample_size,
        selected_round_ids=selected,
        selection_source=source,
        selection_boundary_round_id=boundary_round_id,
        rounds=round_evidence,
    )
    fixture_calls: Counter[str] = Counter()
    controlled_base = (
        (max(selected) + 1_000_000)
        if selected
        else int(control_round_id or 900_001)
    )
    restart_retry, jitter, conflict, quarantine = _controlled_exercises(
        ledger=ledger,
        experiment=experiment,
        resolver_config=resolver_config,
        base_round_id=controlled_base,
        current=current,
        fixture_calls=fixture_calls,
    )
    with RFC008Store(ledger, config=experiment) as store:
        integrity = str(store.connection.execute("PRAGMA integrity_check").fetchone()[0])
        store.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    ledger_hash = hashlib.sha256(ledger.read_bytes()).hexdigest()
    rpc_counts = real_accounting.evidence()
    lifecycle = validate_production_isolation(
        repository_root=root,
        config_path=experiment_config_path,
        expected_snapshot=initial_lifecycle,
    )
    production_absent = bool(lifecycle["ready"])
    final_processes = (
        _process_snapshot(preserve_process_ids)
        if mode == "operational"
        else {}
    )
    process_evidence = _process_evidence(
        mode=mode,
        before=initial_processes,
        after=final_processes,
        current=current,
    )
    processes_preserved = all(
        value.unchanged for value in process_evidence
    )
    safety_passed = _safety_inspection(experiment)
    provider_independence = (
        mode == "operational"
        and len(resolver_config.provider_ids) == 2
        and len(set(resolver_config.provider_ids)) == 2
    )
    genesis_agreement = (
        mode == "operational"
        and len(provider_genesis_hashes) == 2
        and len(set(provider_genesis_hashes.values())) == 1
        and next(iter(provider_genesis_hashes.values()))
        == resolver_config.expected_genesis_hash
    )
    preliminary = ResolverBurnInEvidence.model_construct(
        evidence_type="rfc008_resolver_burn_in",
        mode=mode,
        created_at=current,
        completed_at=datetime.now(timezone.utc) if now is None else current,
        repository_commit=repository_commit,
        repository_branch=repository_branch,
        release_implementation_approval_sha256=release_hash,
        resolver_configuration_sha256=resolver_config.fingerprint,
        experiment_configuration_fingerprint=experiment.configuration_fingerprint,
        resolver_version=resolver_config.resolver_version,
        decoder_version=resolver_config.decoder_version,
        provider_ids=resolver_config.provider_ids,
        provider_independence_passed=provider_independence,
        provider_genesis_hashes=provider_genesis_hashes,
        genesis_agreement_passed=genesis_agreement,
        source_boundary=source_boundary,
        operational=operational,
        operational_attempts=operational_attempts,
        operational_requests=operational_requests,
        real_rpc_request_counts=rpc_counts,
        rpc_attempt_reconciliation_passed=False,
        rpc_attempt_reconciliation_errors=(),
        controlled_fixture_call_counts=dict(sorted(fixture_calls.items())),
        restart_retry=restart_retry,
        jitter=jitter,
        conflict=conflict,
        quarantine=quarantine,
        sqlite_integrity="ok",
        safety_inspection_passed=safety_passed,
        production_artifacts_absent=production_absent,
        running_processes_preserved=processes_preserved,
        protected_processes=process_evidence,
        primary_authoritative_capable=False,
        fixture_only=mode == "fixture",
        ledger_sha256=ledger_hash,
        limitations=(),
    )
    reconciliation_errors = preliminary.reconciliation_errors()
    reconciliation_passed = not reconciliation_errors
    capability = all(
        (
            mode == "operational",
            operational.five_round_criterion_passed,
            provider_independence,
            genesis_agreement,
            set(provider_genesis_hashes)
            == set(resolver_config.provider_ids),
            len(set(provider_genesis_hashes.values())) == 1,
            rpc_counts.finalized_account_reads
            == len(selected) * len(resolver_config.provider_ids),
            rpc_counts.genesis_hash_reads
            == len(resolver_config.provider_ids),
            rpc_counts.total
            == (
                len(selected) * len(resolver_config.provider_ids)
                + len(resolver_config.provider_ids)
            ),
            all(
                rpc_counts.by_provider_and_method.get(provider_id, {}).get(
                    "get_account_info_with_context", 0
                )
                == len(selected)
                for provider_id in resolver_config.provider_ids
            ),
            reconciliation_passed,
            all(
                value.deployment_vector_validated
                and value.accounting_validated
                and value.attempt_count >= 1
                for value in round_evidence
            ),
            restart_retry.recomputed_restart_test_passed,
            restart_retry.recomputed_retry_test_passed,
            jitter.recomputed_jitter_test_passed,
            conflict.recomputed_conflict_test_passed,
            quarantine.recomputed_quarantine_test_passed,
            conflict.round_id != quarantine.quarantine_round_id,
            not (
                {
                    restart_retry.round_id,
                    conflict.round_id,
                    quarantine.quarantine_round_id,
                }
                & set(selected)
            ),
            integrity == "ok",
            production_absent,
            processes_preserved,
            all(
                value.evidence_mode == "operational"
                and value.sanitized_command_identity
                == REQUIRED_PROCESS_COMMAND_IDENTITIES[value.role]
                for value in process_evidence
            ),
            safety_passed,
        )
    )
    evidence = ResolverBurnInEvidence(
        evidence_type="rfc008_resolver_burn_in",
        mode=mode,
        created_at=current,
        completed_at=datetime.now(timezone.utc) if now is None else current,
        repository_commit=repository_commit,
        repository_branch=repository_branch,
        release_implementation_approval_sha256=release_hash,
        resolver_configuration_sha256=resolver_config.fingerprint,
        experiment_configuration_fingerprint=experiment.configuration_fingerprint,
        resolver_version=resolver_config.resolver_version,
        decoder_version=resolver_config.decoder_version,
        provider_ids=resolver_config.provider_ids,
        provider_independence_passed=provider_independence,
        provider_genesis_hashes=provider_genesis_hashes,
        genesis_agreement_passed=genesis_agreement,
        source_boundary=source_boundary,
        operational=operational,
        operational_attempts=operational_attempts,
        operational_requests=operational_requests,
        real_rpc_request_counts=rpc_counts,
        rpc_attempt_reconciliation_passed=reconciliation_passed,
        rpc_attempt_reconciliation_errors=reconciliation_errors,
        controlled_fixture_call_counts=dict(sorted(fixture_calls.items())),
        restart_retry=restart_retry,
        jitter=jitter,
        conflict=conflict,
        quarantine=quarantine,
        sqlite_integrity="ok" if integrity == "ok" else integrity,
        safety_inspection_passed=safety_passed,
        production_artifacts_absent=production_absent,
        running_processes_preserved=processes_preserved,
        protected_processes=process_evidence,
        primary_authoritative_capable=capability,
        fixture_only=mode == "fixture",
        ledger_sha256=ledger_hash,
        limitations=(
            "Burn-in rounds are non-production, non-holdout, and analysis-ineligible.",
            "Controlled retry, conflict, and quarantine checks use fixture providers.",
            "Burn-in grants neither marker nor collection authorization.",
        ),
    )
    evidence_hash = _write_evidence(evidence, output)
    controlled_passed = all(
        (
            restart_retry.recomputed_restart_test_passed,
            restart_retry.recomputed_retry_test_passed,
            jitter.recomputed_jitter_test_passed,
            conflict.recomputed_conflict_test_passed,
            quarantine.recomputed_quarantine_test_passed,
            integrity == "ok",
            production_absent,
        )
    )
    passed = capability if mode == "operational" else controlled_passed
    return {
        "passed": passed,
        "mode": mode,
        "evidence_path": str(output),
        "evidence_sha256": evidence_hash,
        "primary_authoritative_capable": evidence.primary_authoritative_capable,
        "real_round_count": len(selected),
        "real_rpc_request_counts": rpc_counts.model_dump(mode="json"),
        "attempt_reconciliation": {
            "passed": reconciliation_passed,
            "errors": list(reconciliation_errors),
            "operational_attempt_count": len(operational_attempts),
            "operational_request_count": len(operational_requests),
        },
        "operational_summary": operational.model_dump(mode="json"),
        "restart_result": restart_retry.restart_test_passed,
        "retry_result": restart_retry.retry_test_passed,
        "jitter_result": {
            "passed": jitter.jitter_test_passed,
            "tested_round_id": jitter.round_id,
            "retry_numbers_tested": list(jitter.retry_numbers_tested),
            "expected_delays_seconds": list(
                jitter.expected_delays_seconds
            ),
            "recomputed_delays_seconds": list(
                jitter.recomputed_delays_seconds
            ),
            "deterministic_match": jitter.deterministic_match,
            "bounded_delay_result": jitter.bounded_delay_result,
            "persisted_schedule_match": jitter.persisted_schedule_match,
            "jitter_derivation_version": jitter.jitter_derivation_version,
        },
        "conflict_result": conflict.conflict_test_passed,
        "quarantine_result": quarantine.quarantine_test_passed,
        "process_preservation": {
            "passed": processes_preserved,
            "processes": [
                value.model_dump(mode="json") for value in process_evidence
            ],
        },
        "source_boundary": source_boundary.model_dump(mode="json"),
        "recomputed_primary_authoritative_capable": capability,
        "marker_authorized": False,
        "collection_authorized": False,
    }
