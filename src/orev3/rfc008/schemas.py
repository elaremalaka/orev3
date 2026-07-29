from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orev3.ledger.validation import reject_non_finite, reject_secret_fields


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def strict_values(self):
        value = self.model_dump(mode="python")
        reject_non_finite(value)
        reject_secret_fields(value)
        return self


class DecisionSnapshot(StrictModel):
    snapshot_id: str
    experiment_id: str
    round_id: int = Field(ge=0)
    observation_index: int = Field(ge=0)
    observed_at: datetime
    rpc_slot: int = Field(ge=0)
    slots_remaining: int = Field(ge=0, le=75)
    source_reference: str
    source_content_sha256: str
    miner_counts: tuple[int, ...]
    deployed_lamports: tuple[int, ...]
    reward_raw: tuple[int, ...]

    @model_validator(mode="after")
    def complete(self):
        for name in ("miner_counts", "deployed_lamports", "reward_raw"):
            values = getattr(self, name)
            if len(values) != 25 or any(value < 0 for value in values):
                raise ValueError(f"{name} must contain 25 non-negative integers")
        return self


class ArmDecision(StrictModel):
    decision_id: str
    experiment_id: str
    round_id: int
    snapshot_id: str
    arm_id: str
    arm_configuration_hash: str
    ranking: tuple[int, ...]
    selected_squares: tuple[int, ...]
    allocation_by_square: dict[int, int]
    deployment_lamports: int = Field(ge=0)
    participated: bool
    statistical_independent: bool
    paper_only: Literal[True] = True

    @model_validator(mode="after")
    def valid_decision(self):
        if self.participated:
            if tuple(sorted(self.ranking)) != tuple(range(25)):
                raise ValueError("Active arm must rank every square exactly once")
            if len(self.selected_squares) != 4:
                raise ValueError("Active arm must select four squares")
        elif self.ranking or self.selected_squares or self.allocation_by_square:
            raise ValueError("No-deploy decision must be empty")
        if sum(self.allocation_by_square.values()) != self.deployment_lamports:
            raise ValueError("Allocations must sum to deployment")
        return self


class OutcomeEvidence(StrictModel):
    outcome_id: str
    round_id: int = Field(ge=0)
    winner_square: int = Field(ge=0, le=24)
    finalized_at: datetime
    provenance: Literal["direct_observed", "recovered"]
    commitment: Literal["finalized"]
    final_square_deployments: tuple[int, ...]
    total_winnings_lamports: int = Field(ge=0)
    motherlode_raw: int | None = Field(default=None, ge=0)
    base_ore_raw: int | None = Field(default=None, ge=0)
    source_reference: str
    source_content_sha256: str
    round_pda: str
    program_owner: str
    provider_ids: tuple[str, ...]
    provider_response_sha256: tuple[str, ...]
    provider_context_slots: tuple[int, ...]
    requested_at: datetime
    decoder_version: str
    resolver_version: str
    configuration_fingerprint: str
    conflict_status: Literal["accepted"] = "accepted"

    @model_validator(mode="after")
    def complete(self):
        if len(self.final_square_deployments) != 25:
            raise ValueError("Outcome requires 25 final deployments")
        return self


class OutcomeQueueRecord(StrictModel):
    round_id: int = Field(ge=0)
    round_pda: str
    state: Literal["pending", "resolving", "finalized", "conflicted", "quarantined", "failed"]
    enqueued_at: datetime
    updated_at: datetime
    retry_count: int = Field(ge=0)
    next_retry_at: datetime | None = None
    last_error: str | None = None
    accepted_outcome_id: str | None = None


class RoundAccounting(StrictModel):
    accounting_id: str
    experiment_id: str
    round_id: int
    arm_id: str
    decision_id: str
    outcome_id: str
    winner_selected: bool
    deployed_lamports: int = Field(ge=0)
    gross_sol_return_lamports: int = Field(ge=0)
    net_sol_before_fees_lamports: int
    assumed_deploy_fee_lamports: int = Field(ge=0)
    assumed_claim_fee_lamports: int = Field(ge=0)
    net_sol_after_fees_lamports: int
    roi_before_fees: float | None
    roi_after_fees: float | None
    motherlode_ore_raw: int | None = Field(default=None, ge=0)
    base_ore_raw: int | None = Field(default=None, ge=0)
    total_ore_raw: int | None = Field(default=None, ge=0)
    accounting_mode: Literal[
        "historical_price_taking_reconstructed_not_wallet_realized"
    ]


class ExperimentMarker(StrictModel):
    marker_schema_version: Literal[2] = 2
    experiment_id: str
    protocol_version: str
    created_at: datetime
    repository_commit: str
    branch: str
    approval_manifest_path: str
    approval_manifest_sha256: str
    candidate_configuration_sha256: str
    configuration_fingerprint: str
    latest_preholdout_round_id: int
    first_eligible_round_id: int
    # Publication-time cursors seed collection and prevent replay. They may be
    # later than, and must never redefine, the historical eligibility boundary.
    source_identities: tuple[str, ...]
    # Schema-v2 keeps the legacy runtime_source_* names for the immutable
    # historical burn-in eligibility boundary.
    runtime_source_path: str
    runtime_source_inode: int = Field(ge=0)
    runtime_source_byte_offset: int = Field(ge=0)
    runtime_source_line_number: int = Field(ge=1)
    runtime_source_record_sha256: str
    runtime_source_observed_at: datetime
    burn_in_boundary_observed_at: datetime
    resolver_configuration_sha256: str
    resolver_burn_in_evidence_sha256: str
    release_approval_sha256: str
    start_conditions: dict[str, object]
    collection_authorized: Literal[False] = False


SHA256_PATTERN = r"^[0-9a-f]{64}$"
RFC008_CLI_VERSION = "rfc008-cli-v8"
RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION = 4
RFC008_BURN_IN_AUDIT_VERSION = "rfc008-release-preflight-v5"
RFC008_RUNBOOK_VERSION = "rfc008-operator-runbook-v9"
REQUIRED_PROTECTED_PROCESSES = {
    48404: "observer",
    48405: "observer_caffeinate",
    78317: "rfc007_collector",
}
REQUIRED_PROCESS_COMMAND_IDENTITIES = {
    "observer": "-m orev3.observer.collect",
    "observer_caffeinate": "caffeinate -i python -m orev3.observer.collect",
    "rfc007_collector": (
        "-m orev3.collection.cli run --config "
        "config/collection/rfc007_burn_in_v1.json --ledger "
        "data/ledger/rfc007_live_ledger_v1.sqlite"
    ),
}


class RpcRequestCounts(StrictModel):
    total: int = Field(ge=0)
    by_provider: dict[str, int]
    by_method: dict[str, int]
    by_provider_and_method: dict[str, dict[str, int]]
    successful_responses: int = Field(ge=0)
    unavailable_responses: int = Field(ge=0)
    malformed_responses: int = Field(ge=0)
    failed_responses: int = Field(ge=0)
    retried_requests: int = Field(ge=0)
    finalized_account_reads: int = Field(ge=0)
    genesis_hash_reads: int = Field(ge=0)

    @model_validator(mode="after")
    def internally_consistent(self):
        if sum(self.by_provider.values()) != self.total:
            raise ValueError("RPC provider counts do not sum to total")
        if sum(self.by_method.values()) != self.total:
            raise ValueError("RPC method counts do not sum to total")
        if sum(
            count
            for methods in self.by_provider_and_method.values()
            for count in methods.values()
        ) != self.total:
            raise ValueError("RPC provider/method counts do not sum to total")
        for provider, count in self.by_provider.items():
            if sum(self.by_provider_and_method.get(provider, {}).values()) != count:
                raise ValueError("RPC provider detail does not match provider total")
        if self.finalized_account_reads != self.by_method.get(
            "get_account_info_with_context", 0
        ):
            raise ValueError("Finalized-account read count is inconsistent")
        if self.genesis_hash_reads != self.by_method.get("get_genesis_hash", 0):
            raise ValueError("Genesis-hash read count is inconsistent")
        if (
            self.successful_responses
            + self.unavailable_responses
            + self.malformed_responses
            != self.total
        ):
            raise ValueError("RPC response classifications do not sum to total")
        if self.failed_responses != (
            self.unavailable_responses + self.malformed_responses
        ):
            raise ValueError("RPC failed-response count is inconsistent")
        return self


class ProviderRoundEvidence(StrictModel):
    request_id: str
    provider_id: str
    request_method: Literal["get_account_info_with_context"]
    requested_at: datetime
    commitment: Literal["finalized"]
    genesis_hash: str
    response_context_slot: int = Field(ge=1)
    raw_response_sha256: str = Field(pattern=SHA256_PATTERN)
    canonical_response_sha256: str = Field(pattern=SHA256_PATTERN)
    account_owner: str
    returned_account_identity: str
    decoded_round_id: int = Field(ge=0)


class OperationalRoundEvidence(StrictModel):
    round_id: int = Field(ge=0)
    round_pda: str
    selection_order: int = Field(ge=1)
    provider_ids: tuple[str, ...]
    provider_evidence: tuple[ProviderRoundEvidence, ...]
    entropy: int | None = Field(default=None, ge=0)
    winning_square: int | None = Field(default=None, ge=0, le=24)
    deployment_vector_validated: bool
    accounting_validated: bool
    provider_agreement: bool
    owner_validation_passed: bool
    pda_validation_passed: bool
    account_identity_passed: bool
    decoded_round_identity_passed: bool
    finalized_validation_passed: bool
    provenance_complete: bool
    final_state: Literal["accepted", "retry", "conflict", "failed"]
    attempt_count: int = Field(ge=0)
    request_timestamps: tuple[datetime, ...]


class OperationalBurnInSummary(StrictModel):
    requested_sample_size: int = Field(ge=0)
    minimum_required_sample_size: Literal[5] = 5
    selection_policy: str
    selection_source: str
    selection_boundary_round_id: int | None = Field(default=None, ge=0)
    selected_round_ids: tuple[int, ...]
    selected_round_count: int = Field(ge=0)
    distinct_round_count: int = Field(ge=0)
    successful_authoritative_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)
    conflicted_count: int = Field(ge=0)
    quarantined_count: int = Field(ge=0)
    provider_agreement_count: int = Field(ge=0)
    owner_validation_pass_count: int = Field(ge=0)
    identity_validation_pass_count: int = Field(ge=0)
    finalized_validation_pass_count: int = Field(ge=0)
    deployment_validation_pass_count: int = Field(ge=0)
    accounting_validation_pass_count: int = Field(ge=0)
    complete_provenance_count: int = Field(ge=0)
    five_round_criterion_passed: bool
    rounds: tuple[OperationalRoundEvidence, ...]

    @model_validator(mode="after")
    def totals_match(self):
        if self.selected_round_count != len(self.selected_round_ids):
            raise ValueError("Selected-round count is inconsistent")
        if self.distinct_round_count != len(set(self.selected_round_ids)):
            raise ValueError("Distinct-round count is inconsistent")
        if len(self.rounds) != self.selected_round_count:
            raise ValueError("Per-round evidence count is inconsistent")
        if tuple(value.round_id for value in self.rounds) != self.selected_round_ids:
            raise ValueError("Per-round evidence order differs from selection order")
        if tuple(value.selection_order for value in self.rounds) != tuple(
            range(1, self.selected_round_count + 1)
        ):
            raise ValueError("Operational selection order is not deterministic")
        states = [value.final_state for value in self.rounds]
        expected = {
            "successful_authoritative_count": states.count("accepted"),
            "failed_count": states.count("failed"),
            "unresolved_count": states.count("retry"),
            "conflicted_count": states.count("conflict"),
        }
        for name, count in expected.items():
            if getattr(self, name) != count:
                raise ValueError(f"{name} is inconsistent")
        aggregate_checks = {
            "provider_agreement_count": sum(
                value.provider_agreement for value in self.rounds
            ),
            "owner_validation_pass_count": sum(
                value.owner_validation_passed for value in self.rounds
            ),
            "identity_validation_pass_count": sum(
                value.pda_validation_passed
                and value.account_identity_passed
                and value.decoded_round_identity_passed
                for value in self.rounds
            ),
            "finalized_validation_pass_count": sum(
                value.finalized_validation_passed for value in self.rounds
            ),
            "deployment_validation_pass_count": sum(
                value.deployment_vector_validated for value in self.rounds
            ),
            "accounting_validation_pass_count": sum(
                value.accounting_validated for value in self.rounds
            ),
            "complete_provenance_count": sum(
                value.provenance_complete for value in self.rounds
            ),
        }
        for name, count in aggregate_checks.items():
            if getattr(self, name) != count:
                raise ValueError(f"{name} is inconsistent")
        criterion = (
            self.requested_sample_size >= self.minimum_required_sample_size
            and self.selected_round_count >= self.minimum_required_sample_size
            and self.distinct_round_count == self.selected_round_count
            and self.successful_authoritative_count == self.selected_round_count
            and self.provider_agreement_count == self.selected_round_count
            and self.owner_validation_pass_count == self.selected_round_count
            and self.identity_validation_pass_count == self.selected_round_count
            and self.finalized_validation_pass_count == self.selected_round_count
            and self.deployment_validation_pass_count
            == self.selected_round_count
            and self.accounting_validation_pass_count
            == self.selected_round_count
            and self.complete_provenance_count == self.selected_round_count
            and self.failed_count == 0
            and self.unresolved_count == 0
            and self.conflicted_count == 0
            and self.quarantined_count == 0
        )
        if self.five_round_criterion_passed != criterion:
            raise ValueError("Five-round criterion classification is inconsistent")
        return self


class RestartRetryEvidence(StrictModel):
    test_type: Literal["controlled_restart_retry"]
    evidence_mode: Literal["fixture"]
    round_id: int = Field(ge=0)
    initial_state: str
    persisted_retry_count: int = Field(ge=1)
    persisted_next_retry_time: datetime
    persisted_pda: str
    persisted_attempt_count: int = Field(ge=1)
    restart_state: str
    final_result: str
    final_state: str
    recomputed_restart_test_passed: bool
    recomputed_retry_test_passed: bool
    restart_test_passed: bool
    retry_test_passed: bool

    @model_validator(mode="after")
    def valid_restart_retry(self):
        restart = (
            self.initial_state == "pending"
            and self.restart_state == "pending"
            and bool(self.persisted_pda)
            and self.persisted_retry_count >= 1
            and self.persisted_attempt_count >= 1
            and self.persisted_next_retry_time.utcoffset() is not None
        )
        retry = (
            self.initial_state == "pending"
            and self.final_result == "accepted"
            and self.final_state == "finalized"
        )
        if (
            self.recomputed_restart_test_passed != restart
            or self.restart_test_passed != restart
        ):
            raise ValueError("Restart pass classification is invalid")
        if (
            self.recomputed_retry_test_passed != retry
            or self.retry_test_passed != retry
        ):
            raise ValueError("Retry pass classification is invalid")
        return self


class JitterTestEvidence(StrictModel):
    test_type: Literal["controlled_jitter"]
    evidence_mode: Literal["fixture"]
    round_id: int = Field(ge=0)
    retry_numbers_tested: tuple[int, ...]
    expected_delays_seconds: tuple[int, ...]
    recomputed_delays_seconds: tuple[int, ...]
    deterministic_match: bool
    bounded_delay_result: bool
    persisted_schedule_match: bool
    jitter_derivation_version: Literal["rfc008-retry-jitter-v1"]
    recomputed_jitter_test_passed: bool
    jitter_test_passed: bool

    @model_validator(mode="after")
    def valid_jitter(self):
        count = len(self.retry_numbers_tested)
        if (
            self.retry_numbers_tested != (1, 2, 3)
            or len(self.expected_delays_seconds) != count
            or len(self.recomputed_delays_seconds) != count
        ):
            raise ValueError("Jitter evidence vectors are incomplete")
        recomputed = (
            self.expected_delays_seconds == self.recomputed_delays_seconds
        )
        if self.deterministic_match != recomputed:
            raise ValueError("Jitter deterministic-match classification is invalid")
        expected_pass = (
            self.deterministic_match
            and self.bounded_delay_result
            and self.persisted_schedule_match
            and all(value > 0 for value in self.expected_delays_seconds)
        )
        if (
            self.recomputed_jitter_test_passed != expected_pass
            or self.jitter_test_passed != expected_pass
        ):
            raise ValueError("Jitter pass classification is invalid")
        return self


class ConflictTestEvidence(StrictModel):
    test_type: Literal["controlled_conflict"]
    evidence_mode: Literal["fixture"]
    round_id: int = Field(ge=0)
    injected_non_authoritative_disagreement: Literal[True] = True
    conflict_state: str
    provider_provenance_count: int = Field(ge=0)
    provenance_retained: bool
    disagreement_details_retained: bool
    terminal_conflict_persisted: bool
    overwrite_attempted: bool
    overwrite_refused: bool
    later_success_replacement_refused: bool
    primary_analysis_ineligible: bool
    recomputed_conflict_test_passed: bool
    conflict_test_passed: bool

    @model_validator(mode="after")
    def valid_conflict(self):
        recomputed = (
            self.injected_non_authoritative_disagreement
            and self.conflict_state == "conflicted"
            and self.provider_provenance_count == 2
            and self.provenance_retained
            and self.disagreement_details_retained
            and self.terminal_conflict_persisted
            and self.overwrite_attempted
            and self.overwrite_refused
            and self.later_success_replacement_refused
            and self.primary_analysis_ineligible
        )
        if (
            self.recomputed_conflict_test_passed != recomputed
            or self.conflict_test_passed != recomputed
        ):
            raise ValueError("Conflict pass classification is invalid")
        return self


class QuarantineTestEvidence(StrictModel):
    test_type: Literal["controlled_quarantine"]
    evidence_mode: Literal["fixture"]
    quarantine_round_id: int = Field(ge=0)
    configured_expiration_seconds: int = Field(ge=1)
    quarantine_initial_state: str
    expiry_reached: bool
    production_transition_invoked: bool
    quarantine_final_state: str
    quarantine_restart_persistence: bool
    overwrite_attempted: bool
    quarantine_overwrite_refused: bool
    later_success_replacement_refused: bool
    primary_analysis_ineligible: bool
    recomputed_quarantine_test_passed: bool
    quarantine_test_passed: bool

    @model_validator(mode="after")
    def valid_quarantine(self):
        recomputed = (
            self.quarantine_initial_state == "pending"
            and self.expiry_reached
            and self.production_transition_invoked
            and self.quarantine_final_state == "quarantined"
            and self.quarantine_restart_persistence
            and self.overwrite_attempted
            and self.quarantine_overwrite_refused
            and self.later_success_replacement_refused
            and self.primary_analysis_ineligible
        )
        if (
            self.recomputed_quarantine_test_passed != recomputed
            or self.quarantine_test_passed != recomputed
        ):
            raise ValueError("Quarantine pass classification is invalid")
        return self


class BurnInSourceBoundary(StrictModel):
    round_id: int = Field(ge=1)
    source_path: str = Field(min_length=1)
    inode: int = Field(ge=0)
    byte_offset: int = Field(ge=0)
    line_number: int = Field(ge=1)
    record_sha256: str = Field(pattern=SHA256_PATTERN)
    record_timestamp: datetime
    observed_at: datetime

    @model_validator(mode="after")
    def timezone_aware(self):
        if (
            self.record_timestamp.utcoffset() is None
            or self.observed_at.utcoffset() is None
        ):
            raise ValueError("Source-boundary timestamps must include timezone")
        return self


class OperationalRequestEvidence(StrictModel):
    request_id: str = Field(min_length=1)
    attempt_id: str | None = None
    round_id: int | None = Field(default=None, ge=0)
    round_pda: str | None = None
    provider_id: str
    method: Literal["get_genesis_hash", "get_account_info_with_context"]
    requested_at: datetime
    classification: Literal["successful", "unavailable", "malformed"]
    retry_request: bool
    commitment: Literal["finalized"] | None = None
    operational: Literal[True] = True


class OperationalAttemptEvidence(StrictModel):
    attempt_id: str = Field(min_length=1)
    round_id: int = Field(ge=0)
    attempt_number: int = Field(ge=1)
    attempted_at: datetime
    status: Literal["accepted", "retry", "conflict", "failed"]
    provider_request_ids: tuple[str, ...]
    persisted: Literal[True] = True


class ProtectedProcessEvidence(StrictModel):
    pid: int = Field(ge=1)
    role: Literal["observer", "observer_caffeinate", "rfc007_collector"]
    sanitized_command_identity: str = Field(min_length=1)
    observed_before: bool
    observed_after: bool
    before_command_sha256: str = Field(pattern=SHA256_PATTERN)
    after_command_sha256: str = Field(pattern=SHA256_PATTERN)
    before_observed_at: datetime
    after_observed_at: datetime
    unchanged: bool
    evidence_mode: Literal["operational", "fixture"]

    @model_validator(mode="after")
    def valid_process(self):
        if (
            self.before_observed_at.utcoffset() is None
            or self.after_observed_at.utcoffset() is None
        ):
            raise ValueError("Process timestamps must include timezone")
        expected = (
            self.observed_before
            and self.observed_after
            and self.before_command_sha256 == self.after_command_sha256
        )
        if self.unchanged != expected:
            raise ValueError("Protected-process unchanged result is invalid")
        return self


class ResolverBurnInEvidence(StrictModel):
    schema_version: Literal[4] = RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION
    evidence_type: Literal["rfc008_resolver_burn_in"]
    mode: Literal["fixture", "operational"]
    non_production: Literal[True] = True
    holdout_eligible: Literal[False] = False
    created_at: datetime
    completed_at: datetime
    repository_commit: str
    repository_branch: str
    release_implementation_approval_sha256: str
    resolver_configuration_sha256: str
    experiment_configuration_fingerprint: str
    resolver_version: str
    decoder_version: str
    provider_ids: tuple[str, ...]
    provider_independence_passed: bool
    provider_genesis_hashes: dict[str, str]
    genesis_agreement_passed: bool
    finalized_commitment: Literal[True] = True
    source_boundary: BurnInSourceBoundary
    operational: OperationalBurnInSummary
    operational_attempts: tuple[OperationalAttemptEvidence, ...]
    operational_requests: tuple[OperationalRequestEvidence, ...]
    real_rpc_request_counts: RpcRequestCounts
    rpc_attempt_reconciliation_passed: bool
    rpc_attempt_reconciliation_errors: tuple[str, ...]
    controlled_fixture_call_counts: dict[str, int]
    restart_retry: RestartRetryEvidence
    jitter: JitterTestEvidence
    conflict: ConflictTestEvidence
    quarantine: QuarantineTestEvidence
    sqlite_integrity: Literal["ok"]
    safety_inspection_passed: bool
    production_artifacts_absent: bool
    running_processes_preserved: bool
    protected_processes: tuple[ProtectedProcessEvidence, ...]
    primary_authoritative_capable: bool
    fixture_only: bool
    ledger_sha256: str
    limitations: tuple[str, ...]

    def reconciliation_errors(self) -> tuple[str, ...]:
        errors: list[str] = []
        attempts = self.operational_attempts
        requests = self.operational_requests
        attempt_ids = [value.attempt_id for value in attempts]
        request_ids = [value.request_id for value in requests]
        if len(attempt_ids) != len(set(attempt_ids)):
            errors.append("duplicate_attempt_id")
        if len(request_ids) != len(set(request_ids)):
            errors.append("duplicate_request_id")
        attempt_by_id = {value.attempt_id: value for value in attempts}
        request_by_id = {value.request_id: value for value in requests}
        operational_round_ids = {
            value.round_id for value in self.operational.rounds
        }
        requests_by_attempt: dict[str, list[OperationalRequestEvidence]] = {}
        for request in requests:
            if request.method == "get_account_info_with_context":
                if request.attempt_id not in attempt_by_id:
                    errors.append("account_request_without_attempt")
                else:
                    attempt = attempt_by_id[str(request.attempt_id)]
                    if request.round_id != attempt.round_id:
                        errors.append(
                            "request_attempt_round_mismatch:"
                            f"{request.request_id}"
                        )
                    requests_by_attempt.setdefault(
                        str(request.attempt_id), []
                    ).append(request)
            elif request.attempt_id is not None or request.round_id is not None:
                errors.append("genesis_request_bound_to_attempt")
        for attempt in attempts:
            if attempt.round_id not in operational_round_ids:
                errors.append(
                    f"attempt_operational_round_missing:{attempt.attempt_id}"
                )
            linked = requests_by_attempt.get(attempt.attempt_id, [])
            if set(attempt.provider_request_ids) != {
                value.request_id for value in linked
            }:
                errors.append(f"attempt_request_mismatch:{attempt.round_id}")
            expected_retry = attempt.attempt_number > 1
            if any(value.retry_request != expected_retry for value in linked):
                errors.append(f"retry_classification_mismatch:{attempt.round_id}")
        for round_value in self.operational.rounds:
            round_attempts = [
                value for value in attempts if value.round_id == round_value.round_id
            ]
            if round_value.attempt_count != len(round_attempts):
                errors.append(f"attempt_count_mismatch:{round_value.round_id}")
            if round_value.final_state == "accepted" and not round_attempts:
                errors.append(f"attempt_history_missing:{round_value.round_id}")
            if round_attempts and round_attempts[-1].status != round_value.final_state:
                errors.append(f"attempt_state_mismatch:{round_value.round_id}")
            successful_providers = {
                value.provider_id
                for value in requests
                if value.round_id == round_value.round_id
                and value.method == "get_account_info_with_context"
                and value.classification == "successful"
            }
            if (
                round_value.final_state == "accepted"
                and successful_providers != set(self.provider_ids)
            ):
                errors.append(
                    f"provider_request_coverage_incomplete:{round_value.round_id}"
                )
            for provider_value in round_value.provider_evidence:
                request = request_by_id.get(provider_value.request_id)
                if (
                    request is None
                    or request.round_id != round_value.round_id
                    or request.provider_id != provider_value.provider_id
                    or request.method != provider_value.request_method
                    or request.classification != "successful"
                    or request.commitment != provider_value.commitment
                    or request.round_pda
                    != provider_value.returned_account_identity
                ):
                    errors.append(
                        "provider_trace_request_mismatch:"
                        f"{round_value.round_id}:{provider_value.provider_id}"
                    )
        derived_provider = {
            provider_id: sum(
                value.provider_id == provider_id for value in requests
            )
            for provider_id in self.provider_ids
        }
        derived_method = {
            method: sum(value.method == method for value in requests)
            for method in ("get_genesis_hash", "get_account_info_with_context")
        }
        derived_detail = {
            provider_id: {
                method: sum(
                    value.provider_id == provider_id and value.method == method
                    for value in requests
                )
                for method in ("get_genesis_hash", "get_account_info_with_context")
            }
            for provider_id in self.provider_ids
        }
        counts = self.real_rpc_request_counts
        if counts.total != len(requests):
            errors.append("rpc_total_mismatch")
        if counts.by_provider != derived_provider:
            errors.append("rpc_provider_total_mismatch")
        if counts.by_method != derived_method:
            errors.append("rpc_method_total_mismatch")
        if counts.by_provider_and_method != derived_detail:
            errors.append("rpc_provider_method_total_mismatch")
        classifications = {
            name: sum(value.classification == name for value in requests)
            for name in ("successful", "unavailable", "malformed")
        }
        if counts.successful_responses != classifications["successful"]:
            errors.append("rpc_success_total_mismatch")
        if counts.unavailable_responses != classifications["unavailable"]:
            errors.append("rpc_unavailable_total_mismatch")
        if counts.malformed_responses != classifications["malformed"]:
            errors.append("rpc_malformed_total_mismatch")
        if counts.failed_responses != (
            classifications["unavailable"] + classifications["malformed"]
        ):
            errors.append("rpc_failed_total_mismatch")
        if counts.retried_requests != sum(
            value.retry_request for value in requests
        ):
            errors.append("rpc_retry_total_mismatch")
        return tuple(sorted(set(errors)))

    @model_validator(mode="after")
    def capability_is_fail_closed(self):
        if self.fixture_only != (self.mode == "fixture"):
            raise ValueError("Fixture classification does not match burn-in mode")
        real_rounds = self.operational.rounds
        expected_account_reads = len(real_rounds) * len(self.provider_ids)
        counts_complete = (
            self.real_rpc_request_counts.finalized_account_reads
            == expected_account_reads
            and self.real_rpc_request_counts.genesis_hash_reads
            == len(self.provider_ids)
            and self.real_rpc_request_counts.total
            == expected_account_reads + len(self.provider_ids)
            and all(
                self.real_rpc_request_counts.by_provider_and_method.get(
                    provider_id, {}
                ).get("get_account_info_with_context", 0)
                == len(real_rounds)
                for provider_id in self.provider_ids
            )
        )
        provider_identity_complete = (
            set(self.provider_genesis_hashes) == set(self.provider_ids)
            and len(set(self.provider_genesis_hashes.values())) == 1
        )
        reconciliation_errors = self.reconciliation_errors()
        if self.rpc_attempt_reconciliation_errors != reconciliation_errors:
            raise ValueError("RPC/attempt reconciliation errors are inconsistent")
        if self.rpc_attempt_reconciliation_passed != (not reconciliation_errors):
            raise ValueError("RPC/attempt reconciliation result is inconsistent")
        operational_ids = set(self.operational.selected_round_ids)
        controlled_ids = {
            self.restart_retry.round_id,
            self.jitter.round_id,
            self.conflict.round_id,
            self.quarantine.quarantine_round_id,
        }
        controlled_independent = (
            len(controlled_ids) == 3
            and self.restart_retry.round_id == self.jitter.round_id
            and not (controlled_ids & operational_ids)
            and self.conflict.round_id != self.quarantine.quarantine_round_id
        )
        expected_selection = tuple(
            range(
                self.source_boundary.round_id
                - self.operational.requested_sample_size,
                self.source_boundary.round_id,
            )
        )
        boundary_matches = (
            self.mode == "fixture"
            or (
                self.operational.selection_boundary_round_id
                == self.source_boundary.round_id
                and expected_selection == self.operational.selected_round_ids
            )
        )
        process_roles = [value.role for value in self.protected_processes]
        process_pids = [value.pid for value in self.protected_processes]
        process_evidence_complete = (
            len(process_roles) == len(set(process_roles)) == 3
            and len(process_pids) == len(set(process_pids)) == 3
            and all(value.unchanged for value in self.protected_processes)
        )
        if self.mode == "operational":
            process_evidence_complete = (
                process_evidence_complete
                and {
                    value.pid: value.role for value in self.protected_processes
                }
                == REQUIRED_PROTECTED_PROCESSES
                and all(
                    value.evidence_mode == "operational"
                    and value.sanitized_command_identity
                    == REQUIRED_PROCESS_COMMAND_IDENTITIES[value.role]
                    for value in self.protected_processes
                )
            )
        else:
            process_evidence_complete = (
                process_evidence_complete
                and all(
                    value.evidence_mode == "fixture"
                    for value in self.protected_processes
                )
            )
        if self.running_processes_preserved != process_evidence_complete:
            raise ValueError(
                "Protected-process preservation result is inconsistent"
            )
        per_round_complete = all(
            value.deployment_vector_validated
            and value.accounting_validated
            and value.attempt_count >= 1
            for value in real_rounds
        )
        required = all(
            (
                self.mode == "operational",
                not self.fixture_only,
                len(self.provider_ids) == 2,
                len(set(self.provider_ids)) == 2,
                self.provider_independence_passed,
                self.genesis_agreement_passed,
                provider_identity_complete,
                self.operational.five_round_criterion_passed,
                per_round_complete,
                counts_complete,
                self.rpc_attempt_reconciliation_passed,
                self.restart_retry.recomputed_restart_test_passed,
                self.restart_retry.recomputed_retry_test_passed,
                self.jitter.recomputed_jitter_test_passed,
                self.conflict.recomputed_conflict_test_passed,
                self.quarantine.recomputed_quarantine_test_passed,
                controlled_independent,
                boundary_matches,
                self.sqlite_integrity == "ok",
                self.safety_inspection_passed,
                self.production_artifacts_absent,
                self.running_processes_preserved,
                process_evidence_complete,
            )
        )
        if self.primary_authoritative_capable != required:
            raise ValueError("Primary-authoritative capability is inconsistent")
        if self.mode == "fixture":
            if self.primary_authoritative_capable:
                raise ValueError("Fixture evidence cannot be authoritative")
            if self.real_rpc_request_counts.total:
                raise ValueError("Fixture evidence cannot report real RPC requests")
        return self


class RuntimeSourceBoundary(StrictModel):
    source_path: str
    source_inode: int = Field(ge=0)
    source_byte_offset: int = Field(ge=0)
    source_line_number: int = Field(ge=1)
    source_record_sha256: str
    source_observed_at: datetime
    round_id: int = Field(ge=0)


class FinalFreezeManifest(StrictModel):
    schema_version: Literal[1] = 1
    freeze_id: str
    created_at: datetime
    authorization: Literal["RFC008_FINAL_FREEZE_AUTHORIZED"]
    experiment_id: str
    configuration_fingerprint: str
    marker_sha256: str
    ledger_sha256: str
    ledger_data_version: int = Field(ge=0)
    terminal_source_cursors: tuple[dict[str, object], ...]
    total_started_rounds: int = Field(ge=0)
    eligible_rounds: int = Field(ge=0)
    primary_analyzable_rounds: int = Field(ge=0)
    pending_rounds: int = Field(ge=0)
    failed_rounds: int = Field(ge=0)
    conflicted_rounds: int = Field(ge=0)
    quarantined_rounds: int = Field(ge=0)
    excluded_rounds: int = Field(ge=0)
    recovered_sensitivity_rounds: int = Field(ge=0)
    unusable_numerator: int = Field(ge=0)
    unusable_denominator: int = Field(ge=0)
    unusable_rate: float = Field(ge=0)
    safety_counters: dict[str, int]
    configuration_mismatch_count: int = Field(ge=0)
    marker_mismatch_count: int = Field(ge=0)
    duplicate_counters: dict[str, int]
    writer_lease_violations: int = Field(ge=0)
    outcome_provenance_counts: dict[str, int]
    started_round_cap_reached: bool
    calendar_cap_reached: bool
    collection_stop_reason: str
    final_freeze_authorized: Literal[True] = True
    sqlite_integrity: Literal["ok"]
    incomplete_accounting_rounds: int = Field(ge=0)
    accounting_complete: bool
