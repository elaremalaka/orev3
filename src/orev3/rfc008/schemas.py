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

    @model_validator(mode="after")
    def complete(self):
        if len(self.final_square_deployments) != 25:
            raise ValueError("Outcome requires 25 final deployments")
        return self


class OutcomeQueueRecord(StrictModel):
    round_id: int = Field(ge=0)
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
    start_conditions: dict[str, object]
    collection_authorized: Literal[False] = False
