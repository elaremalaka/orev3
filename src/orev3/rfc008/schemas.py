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
    marker_schema_version: Literal[1] = 1
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
    source_identities: tuple[str, ...]
    runtime_source_path: str
    runtime_source_inode: int = Field(ge=0)
    runtime_source_byte_offset: int = Field(ge=0)
    runtime_source_line_number: int = Field(ge=1)
    runtime_source_record_sha256: str
    runtime_source_observed_at: datetime
    resolver_configuration_sha256: str
    resolver_burn_in_evidence_sha256: str
    release_approval_sha256: str
    start_conditions: dict[str, object]
    collection_authorized: Literal[False] = False


class RpcRequestCounts(StrictModel):
    total: int = Field(ge=0)
    by_provider: dict[str, int]
    by_method: dict[str, int]
    by_provider_and_method: dict[str, dict[str, int]]
    successful_responses: int = Field(ge=0)
    unavailable_responses: int = Field(ge=0)
    malformed_responses: int = Field(ge=0)
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
        return self


class ProviderRoundEvidence(StrictModel):
    provider_id: str
    request_method: Literal["get_account_info_with_context"]
    requested_at: datetime
    commitment: Literal["finalized"]
    genesis_hash: str
    response_context_slot: int = Field(ge=1)
    raw_response_sha256: str
    canonical_response_sha256: str
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
    restart_test_passed: bool
    retry_test_passed: bool
    deterministic_jitter_test_passed: bool


class ConflictTestEvidence(StrictModel):
    test_type: Literal["controlled_conflict"]
    evidence_mode: Literal["fixture"]
    round_id: int = Field(ge=0)
    injected_non_authoritative_disagreement: Literal[True] = True
    conflict_state: str
    provenance_retained: bool
    overwrite_refused: bool
    primary_analysis_ineligible: bool
    conflict_test_passed: bool


class QuarantineTestEvidence(StrictModel):
    test_type: Literal["controlled_quarantine"]
    evidence_mode: Literal["fixture"]
    quarantine_round_id: int = Field(ge=0)
    configured_expiration_seconds: int = Field(ge=1)
    quarantine_initial_state: str
    quarantine_final_state: str
    quarantine_restart_persistence: bool
    quarantine_overwrite_refused: bool
    primary_analysis_ineligible: bool
    quarantine_test_passed: bool


class ResolverBurnInEvidence(StrictModel):
    schema_version: Literal[2] = 2
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
    operational: OperationalBurnInSummary
    real_rpc_request_counts: RpcRequestCounts
    controlled_fixture_call_counts: dict[str, int]
    restart_retry: RestartRetryEvidence
    conflict: ConflictTestEvidence
    quarantine: QuarantineTestEvidence
    sqlite_integrity: Literal["ok"]
    safety_inspection_passed: bool
    production_artifacts_absent: bool
    running_processes_preserved: bool
    primary_authoritative_capable: bool
    fixture_only: bool
    ledger_sha256: str
    limitations: tuple[str, ...]

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
                counts_complete,
                self.restart_retry.restart_test_passed,
                self.restart_retry.retry_test_passed,
                self.restart_retry.deterministic_jitter_test_passed,
                self.conflict.conflict_test_passed,
                self.quarantine.quarantine_test_passed,
                self.sqlite_integrity == "ok",
                self.safety_inspection_passed,
                self.production_artifacts_absent,
                self.running_processes_preserved,
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
