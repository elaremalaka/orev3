from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from orev3.ledger.event_types import EventType
from orev3.ledger.validation import (
    reject_non_finite,
    reject_secret_fields,
    validate_selected_squares,
    validate_transaction_signature,
    validate_wallet_public_key,
)


class LedgerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_safe_json(self):
        raw = self.model_dump(mode="python")
        reject_non_finite(raw)
        reject_secret_fields(raw)
        return self


class Provenance(StrEnum):
    DIRECT_WALLET_OBSERVATION = "direct_wallet_observation"
    DIRECT_RPC_OBSERVATION = "direct_rpc_observation"
    DIRECT_PROGRAM_EVENT = "direct_program_event"
    DIRECT_LOCAL_LOG = "direct_local_log"
    RECONSTRUCTED = "reconstructed"
    INFERRED = "inferred"
    CONFIGURED_ASSUMPTION = "configured_assumption"
    UNAVAILABLE = "unavailable"


class ProvenancedValue(LedgerModel):
    value: int | float | str | bool | None
    provenance: Provenance
    source_identifier: str | None = None
    observed_at: datetime | None = None
    confidence: Literal["high", "medium", "low", "unavailable"] = "unavailable"
    final: bool = False


class LedgerEvent(LedgerModel):
    schema_version: int = 1
    event_id: str
    event_type: EventType
    event_time: datetime
    observed_at: datetime
    source: str
    source_record_id: str
    run_id: str
    session_id: str
    round_id: int | None = Field(default=None, ge=0)
    observation_index: int | None = Field(default=None, ge=0)
    wallet_public_key: str | None = None
    transaction_signature: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("wallet_public_key")
    @classmethod
    def wallet_is_valid(cls, value: str | None) -> str | None:
        return validate_wallet_public_key(value) if value else None

    @field_validator("transaction_signature")
    @classmethod
    def signature_is_valid(cls, value: str | None) -> str | None:
        return validate_transaction_signature(value) if value else None

    @model_validator(mode="after")
    def has_identifier(self):
        if (
            self.round_id is None
            and self.wallet_public_key is None
            and self.transaction_signature is None
        ):
            raise ValueError(
                "Event requires a round, wallet, or transaction identifier"
            )
        return self


class OpportunityRecord(LedgerModel):
    schema_version: int = 1
    opportunity_id: str
    round_id: int = Field(ge=0)
    observation_index: int = Field(ge=0)
    observed_at: datetime
    seconds_remaining: float | None = Field(default=None, ge=0)
    board_snapshot_reference: str
    round_state_reference: str
    data_coverage: str
    outcome_source: str | None = None


class StrategyDecisionRecord(LedgerModel):
    schema_version: int = 1
    decision_id: str
    opportunity_id: str
    strategy_id: str
    strategy_version: str
    mode: Literal["passive", "paper", "historical_live"]
    selected_squares: list[int] = Field(default_factory=list)
    ranking_scores: list[float] | None = None
    deployment_total_lamports: int = Field(ge=0)
    allocation_by_square: dict[int, int] = Field(default_factory=dict)
    decision_time: datetime
    decision_latency_ms: float = Field(ge=0)
    participated: bool
    no_deploy_reason: str | None = None

    @field_validator("selected_squares")
    @classmethod
    def squares_are_valid(cls, values: list[int]) -> list[int]:
        return validate_selected_squares(values)

    @model_validator(mode="after")
    def allocation_is_valid(self):
        if any(square < 0 or square > 24 for square in self.allocation_by_square):
            raise ValueError("Allocation contains an invalid square")
        if any(value < 0 for value in self.allocation_by_square.values()):
            raise ValueError("Allocation cannot be negative")
        if sum(self.allocation_by_square.values()) != self.deployment_total_lamports:
            raise ValueError("Allocation must equal total deployment")
        if self.participated and not self.selected_squares:
            raise ValueError("Participating decision requires selected squares")
        if not self.participated and self.deployment_total_lamports != 0:
            raise ValueError("No-deploy decision must have zero deployment")
        return self


class DeploymentRecord(LedgerModel):
    schema_version: int = 1
    deployment_intent_id: str
    decision_id: str
    wallet_public_key: str | None = None
    intended_lamports: int = Field(ge=0)
    submitted_lamports: int | None = Field(default=None, ge=0)
    landed_lamports: int | None = Field(default=None, ge=0)
    selected_squares: list[int]
    transaction_signature: str | None = None
    submission_time: datetime | None = None
    confirmation_time: datetime | None = None
    status: str
    failure_reason: str | None = None

    @field_validator("selected_squares")
    @classmethod
    def squares_are_valid(cls, values: list[int]) -> list[int]:
        return validate_selected_squares(values)

    @field_validator("wallet_public_key")
    @classmethod
    def wallet_is_valid(cls, value: str | None) -> str | None:
        return validate_wallet_public_key(value) if value else None

    @field_validator("transaction_signature")
    @classmethod
    def signature_is_valid(cls, value: str | None) -> str | None:
        return validate_transaction_signature(value) if value else None


class TransactionCostRecord(LedgerModel):
    schema_version: int = 1
    transaction_signature: str
    base_fee_lamports: int = Field(ge=0)
    priority_fee_lamports: int | None = Field(default=None, ge=0)
    other_fee_lamports: int = Field(default=0, ge=0)
    total_fee_lamports: int = Field(ge=0)
    fee_payer: str | None = None
    provenance: Provenance

    @field_validator("transaction_signature")
    @classmethod
    def signature_is_valid(cls, value: str) -> str:
        return validate_transaction_signature(value)

    @model_validator(mode="after")
    def fee_components_are_consistent(self):
        known = (
            self.base_fee_lamports
            + (self.priority_fee_lamports or 0)
            + self.other_fee_lamports
        )
        if self.priority_fee_lamports is not None and known != self.total_fee_lamports:
            raise ValueError("Known fee components must equal total fee")
        return self


class RewardRecord(LedgerModel):
    schema_version: int = 1
    opportunity_id: str
    round_id: int = Field(ge=0)
    wallet_public_key: str | None = None
    gross_sol_return_lamports: int | None = Field(default=None, ge=0)
    net_sol_return_before_fees_lamports: int | None = None
    base_ore_raw: int | None = Field(default=None, ge=0)
    motherlode_ore_raw: int | None = Field(default=None, ge=0)
    total_ore_raw: int | None = Field(default=None, ge=0)
    reward_time: datetime | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def ore_total_is_consistent(self):
        if (
            self.base_ore_raw is not None
            and self.motherlode_ore_raw is not None
            and self.total_ore_raw != self.base_ore_raw + self.motherlode_ore_raw
        ):
            raise ValueError("ORE components must equal total ORE")
        return self


class ClaimRecord(LedgerModel):
    schema_version: int = 1
    claim_signature: str
    wallet_public_key: str
    claim_time: datetime
    claimed_ore_raw: int = Field(ge=0)
    claim_fee_lamports: int = Field(ge=0)
    attributed_opportunity_ids: list[str] = Field(default_factory=list)
    attributed_amounts_raw: dict[str, int] = Field(default_factory=dict)
    unattributed_ore_raw: int = Field(default=0, ge=0)
    attribution_method: Literal["direct", "balance_difference", "fifo", "proportional", "unattributed"]
    attribution_confidence: Literal["high", "medium", "low", "unavailable"]
    ambiguity_reason: str | None = None

    @field_validator("claim_signature")
    @classmethod
    def signature_is_valid(cls, value: str) -> str:
        return validate_transaction_signature(value)

    @field_validator("wallet_public_key")
    @classmethod
    def wallet_is_valid(cls, value: str) -> str:
        return validate_wallet_public_key(value)

    @model_validator(mode="after")
    def attribution_balances(self):
        if any(value < 0 for value in self.attributed_amounts_raw.values()):
            raise ValueError("Attributed claim amount cannot be negative")
        if sum(self.attributed_amounts_raw.values()) + self.unattributed_ore_raw != self.claimed_ore_raw:
            raise ValueError("Attributed and unattributed claim must equal total")
        return self


class WalletSnapshot(LedgerModel):
    schema_version: int = 1
    wallet_public_key: str
    snapshot_time: datetime
    sol_balance_lamports: int = Field(ge=0)
    ore_token_balance_raw: int | None = Field(default=None, ge=0)
    source: str
    commitment: str

    @field_validator("wallet_public_key")
    @classmethod
    def wallet_is_valid(cls, value: str) -> str:
        return validate_wallet_public_key(value)


class RpcTransactionObservation(LedgerModel):
    schema_version: int = 1
    transaction_signature: str
    slot: int | None = Field(default=None, ge=0)
    block_time: int | None = None
    confirmation_status: str | None = None
    transaction_error: Any | None = None
    protocol_status: Literal[
        "confirmed_success",
        "confirmed_protocol_failure",
        "failed",
        "missing",
        "unknown",
    ]
    fee_payer: str | None = None
    total_fee_lamports: int | None = Field(default=None, ge=0)
    priority_fee_lamports: int | None = Field(default=None, ge=0)
    pre_sol_balances: list[int] = Field(default_factory=list)
    post_sol_balances: list[int] = Field(default_factory=list)
    pre_token_balances: list[dict[str, Any]] = Field(default_factory=list)
    post_token_balances: list[dict[str, Any]] = Field(default_factory=list)
    program_ids: list[str] = Field(default_factory=list)
    instruction_types: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    account_keys: list[str] = Field(default_factory=list)
    provenance: Provenance = Provenance.DIRECT_RPC_OBSERVATION

    @field_validator("transaction_signature")
    @classmethod
    def signature_is_valid(cls, value: str) -> str:
        return validate_transaction_signature(value)


class WalletDeltaRecord(LedgerModel):
    schema_version: int = 1
    wallet_public_key: str
    before_time: datetime
    after_time: datetime
    raw_sol_delta_lamports: int
    raw_ore_delta: int | None = None
    mining_attributed_sol_delta_lamports: int | None = None
    classification: Literal[
        "deployment",
        "reward",
        "fee",
        "external_funding",
        "withdrawal",
        "claim",
        "unrelated_transfer",
        "ambiguous",
        "no_change",
    ]
    evidence: str
    related_transaction_signature: str | None = None
    manual_review: bool = False

    @field_validator("wallet_public_key")
    @classmethod
    def wallet_is_valid(cls, value: str) -> str:
        return validate_wallet_public_key(value)


class ReconciliationResult(LedgerModel):
    schema_version: int = 1
    opportunity_id: str
    decision_status: str
    transaction_status: str
    reward_status: str
    claim_status: str
    wallet_delta_status: str
    state: str
    component_scores: dict[str, float]
    completeness_score: float = Field(ge=0, le=1)
    blocking_gaps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
