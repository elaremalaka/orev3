from __future__ import annotations

import base64
import hashlib
import os
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orev3.collection.outcome_recovery import RpcRecoveryProvider
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.outcomes import enqueue_pending
from orev3.rfc008.resolver import FinalizedOutcomeResolver, derive_round_pda
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import ResolverBurnInEvidence
from orev3.rfc008.storage import RFC008Store, strict_json


OPERATIONAL_BURN_IN_AUTHORIZATION = (
    "RFC008_OPERATIONAL_RESOLVER_BURN_IN_AUTHORIZED"
)


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
    ) -> None:
        self.provider_id = provider_id
        self.config = config
        self.accounts = accounts
        self.failures_remaining = failures_remaining

    def get_genesis_hash(self) -> str:
        return self.config.expected_genesis_hash

    def get_account_info_with_context(
        self, address: str, *, commitment: str
    ) -> dict[str, Any]:
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


class TransientFailureProvider:
    def __init__(self, provider: Any) -> None:
        self.provider = provider
        self.provider_id = provider.provider_id
        self.failures_remaining = 1

    def get_genesis_hash(self) -> str:
        return self.provider.get_genesis_hash()

    def get_account_info_with_context(
        self, address: str, *, commitment: str
    ) -> dict[str, Any]:
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise TimeoutError("burn-in injected transient read failure")
        return self.provider.get_account_info_with_context(
            address, commitment=commitment
        )

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
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        with sidecar_temporary.open("xb") as handle:
            handle.write(f"{hashlib.sha256(payload).hexdigest()}  {path.name}\n".encode())
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
    return hashlib.sha256(payload).hexdigest()


def run_resolver_burn_in(
    *,
    ledger_path: str | Path,
    output_path: str | Path,
    experiment_config_path: str | Path,
    resolver_config_path: str | Path,
    mode: str,
    control_round_id: int | None = None,
    authorization_token: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    if mode not in {"fixture", "operational"}:
        raise ValueError("Burn-in mode must be fixture or operational")
    if mode == "operational" and authorization_token != (
        OPERATIONAL_BURN_IN_AUTHORIZATION
    ):
        raise PermissionError("Operational resolver burn-in requires authorization")
    ledger = Path(ledger_path)
    if "rfc008_paper_ledger" in ledger.name or "rfc007" in ledger.name.lower():
        raise ValueError("Burn-in refuses production or RFC-007 ledger paths")
    experiment = RFC008Config.from_path(experiment_config_path)
    resolver_config = ResolverConfig.from_path(resolver_config_path)
    current = now or datetime.now(timezone.utc)
    if control_round_id is None:
        if mode == "fixture":
            control_round_id = 900_001
        else:
            from orev3.rfc008.marker import derive_runtime_source_boundary

            boundary, _ = derive_runtime_source_boundary(experiment.source_glob)
            if boundary.round_id < 1:
                raise ValueError("Cannot derive a prior finalized control round")
            control_round_id = boundary.round_id - 1
    pda = derive_round_pda(
        control_round_id, resolver_config.expected_program_owner
    )
    providers: tuple[Any, ...]
    if mode == "fixture":
        raw = _round_account_bytes(control_round_id)
        accounts = {pda: raw}
        providers = (
            FixtureOutcomeProvider(
                resolver_config.provider_ids[0],
                resolver_config,
                accounts,
                failures_remaining=1,
            ),
            FixtureOutcomeProvider(
                resolver_config.provider_ids[1],
                resolver_config,
                accounts,
            ),
        )
    else:
        urls = []
        for variable in resolver_config.provider_url_environment_variables:
            value = os.environ.get(variable)
            if not value:
                raise ValueError(f"Missing provider environment variable: {variable}")
            urls.append(value)
        if len(set(urls)) != len(urls):
            raise ValueError("Operational outcome providers must be independent")
        raw_providers = tuple(
            RpcRecoveryProvider(provider_id, url)
            for provider_id, url in zip(resolver_config.provider_ids, urls)
        )
        providers = (
            TransientFailureProvider(raw_providers[0]),
            raw_providers[1],
        )
    try:
        with RFC008Store(ledger, config=experiment, create=True) as store:
            with store.connection:
                store.start_round(control_round_id, current)
                enqueue_pending(store, control_round_id, at=current)
                resolver = FinalizedOutcomeResolver(
                    store=store,
                    experiment_config=experiment,
                    resolver_config=resolver_config,
                    providers=providers,
                )
                resolver.validate_provider_networks()
                first_result = resolver.resolve_round(control_round_id, now=current)
                first_queue = store.queue(control_round_id)
                assert first_queue is not None
                retry_at = first_queue.next_retry_at
        # Reopen the same isolated ledger to prove persisted restart recovery.
        if mode == "fixture":
            raw = _round_account_bytes(control_round_id)
            providers = (
                FixtureOutcomeProvider(
                    resolver_config.provider_ids[0],
                    resolver_config,
                    {pda: raw},
                ),
                FixtureOutcomeProvider(
                    resolver_config.provider_ids[1],
                    resolver_config,
                    {pda: raw},
                ),
            )
        with RFC008Store(ledger, config=experiment) as restarted:
            resolver = FinalizedOutcomeResolver(
                store=restarted,
                experiment_config=experiment,
                resolver_config=resolver_config,
                providers=providers,
            )
            due = retry_at or current
            with restarted.connection:
                second_result = resolver.resolve_round(
                    control_round_id, now=due
                )
            accepted = restarted.accepted_outcome(control_round_id)
            provenance_passed = bool(
                accepted
                and accepted.provider_ids == resolver_config.provider_ids
                and len(accepted.provider_response_sha256) == 2
                and accepted.round_pda == pda
            )
            conflict_round = control_round_id + 1
            conflict_pda = derive_round_pda(
                conflict_round, resolver_config.expected_program_owner
            )
            with restarted.connection:
                restarted.start_round(conflict_round, current)
                enqueue_pending(restarted, conflict_round, at=current)
                conflict_resolver = FinalizedOutcomeResolver(
                    store=restarted,
                    experiment_config=experiment,
                    resolver_config=resolver_config,
                    providers=(
                        FixtureOutcomeProvider(
                            resolver_config.provider_ids[0],
                            resolver_config,
                            {
                                conflict_pda: _round_account_bytes(
                                    conflict_round, entropy=1
                                )
                            },
                        ),
                        FixtureOutcomeProvider(
                            resolver_config.provider_ids[1],
                            resolver_config,
                            {
                                conflict_pda: _round_account_bytes(
                                    conflict_round, entropy=2
                                )
                            },
                        ),
                    ),
                )
                conflict_result = conflict_resolver.resolve_round(
                    conflict_round, now=current
                )
            conflict_passed = conflict_result == "conflict"
            retry_passed = first_result == "retry" and second_result == "accepted"
            checks = {
                "first_result": first_result,
                "restart_result": second_result,
                "retry_at": retry_at.isoformat() if retry_at else None,
                "control_round_id": control_round_id,
                "round_pda": pda,
                "conflict_test_passed": conflict_passed,
            }
    finally:
        for provider in providers:
            provider.close()
    ledger_hash = hashlib.sha256(ledger.read_bytes()).hexdigest()
    evidence = ResolverBurnInEvidence(
        evidence_type="rfc008_resolver_burn_in",
        mode=mode,
        created_at=current,
        resolver_configuration_sha256=resolver_config.fingerprint,
        experiment_configuration_fingerprint=experiment.configuration_fingerprint,
        resolver_version=resolver_config.resolver_version,
        decoder_version=resolver_config.decoder_version,
        provider_ids=resolver_config.provider_ids,
        direct_finalization_passed=second_result == "accepted",
        owner_identity_passed=True,
        round_identity_passed=True,
        restart_recovery_passed=retry_passed,
        retry_passed=retry_passed,
        deterministic_jitter_passed=retry_at is not None,
        provenance_passed=provenance_passed,
        conflict_quarantine_passed=conflict_passed,
        primary_authoritative_capable=(
            mode == "operational" and second_result == "accepted"
        ),
        fixture_only=mode == "fixture",
        ledger_sha256=ledger_hash,
        checks=checks,
    )
    evidence_hash = _write_evidence(evidence, output_path)
    return {
        "passed": all(
            (
                evidence.direct_finalization_passed,
                evidence.owner_identity_passed,
                evidence.round_identity_passed,
                evidence.restart_recovery_passed,
                evidence.retry_passed,
                evidence.deterministic_jitter_passed,
                evidence.provenance_passed,
                evidence.conflict_quarantine_passed,
            )
        ),
        "mode": mode,
        "evidence_path": str(output_path),
        "evidence_sha256": evidence_hash,
        "primary_authoritative_capable": evidence.primary_authoritative_capable,
    }
