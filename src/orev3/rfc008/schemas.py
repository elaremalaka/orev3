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


class ResolverBurnInEvidence(StrictModel):
    schema_version: Literal[1] = 1
    evidence_type: Literal["rfc008_resolver_burn_in"]
    mode: Literal["fixture", "operational"]
    created_at: datetime
    resolver_configuration_sha256: str
    experiment_configuration_fingerprint: str
    resolver_version: str
    decoder_version: str
    provider_ids: tuple[str, ...]
    finalized_commitment: Literal[True] = True
    direct_finalization_passed: bool
    owner_identity_passed: bool
    round_identity_passed: bool
    restart_recovery_passed: bool
    retry_passed: bool
    deterministic_jitter_passed: bool
    provenance_passed: bool
    conflict_quarantine_passed: bool
    primary_authoritative_capable: bool
    fixture_only: bool
    ledger_sha256: str
    checks: dict[str, object]


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
