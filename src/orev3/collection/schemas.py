from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orev3.ledger.validation import reject_non_finite, reject_secret_fields


class CollectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def strict_safe_values(self):
        value = self.model_dump(mode="python")
        reject_non_finite(value)
        reject_secret_fields(value)
        return self


class SourceCursor(CollectionModel):
    schema_version: int = 1
    source_id: str
    source_path: str
    source_type: str = "observer_jsonl"
    cursor_type: str = "byte_offset_and_line"
    byte_offset: int = Field(ge=0)
    line_number: int = Field(ge=0)
    last_record_id: str | None = None
    last_observed_timestamp: datetime | None = None
    last_ingested_at: datetime | None = None
    source_size: int = Field(ge=0)
    source_inode: int = Field(ge=0)


class TailRecord(CollectionModel):
    source_id: str
    source_path: str
    source_line_number: int = Field(gt=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    record_id: str
    content_sha256: str
    observed_at: datetime
    raw: dict[str, Any]
    out_of_order: bool = False


class TailBatch(CollectionModel):
    records: list[TailRecord]
    cursor: SourceCursor
    malformed_records: int = 0
    duplicate_records: int = 0
    partial_final_line: bool = False


class CompleteOpportunity(CollectionModel):
    round_id: int = Field(ge=0)
    observation_index: int = Field(ge=0)
    observed_at: datetime
    rpc_slot: int = Field(ge=0)
    start_slot: int = Field(ge=0)
    end_slot: int | None = Field(default=None, ge=0)
    slots_remaining: int | None = Field(default=None, ge=0)
    miner_counts: list[int]
    deployed_lamports: list[int]
    reward_raw: list[int]
    treasury_motherlode_raw: int = Field(ge=0)
    source_reference: str

    @model_validator(mode="after")
    def complete_board(self):
        for name in ("miner_counts", "deployed_lamports", "reward_raw"):
            values = getattr(self, name)
            if len(values) != 25:
                raise ValueError(f"{name} must contain exactly 25 squares")
            if any(value < 0 for value in values):
                raise ValueError(f"{name} cannot contain negative values")
        return self


class PaperDecision(CollectionModel):
    decision_id: str
    opportunity_id: str
    strategy_id: str
    strategy_version: str
    mode: Literal["paper"] = "paper"
    decision_time: datetime
    source_observed_time: datetime
    decision_latency_ms: float = Field(ge=0)
    selected_squares: list[int]
    ranking_scores: list[float] | None
    ranking_order: list[int]
    square_count: int = Field(ge=0, le=25)
    allocation_rule: str
    deployment_total_lamports: int = Field(ge=0)
    allocation_by_square: dict[int, int]
    participated: bool
    no_deploy_reason: str | None
    configuration_hash: str
    collector_version: str

    @model_validator(mode="after")
    def valid_decision(self):
        if sorted(self.ranking_order) != list(range(25)):
            raise ValueError("Ranking order must contain each square exactly once")
        if len(self.selected_squares) != len(set(self.selected_squares)):
            raise ValueError("Selected squares must be unique")
        if any(square < 0 or square > 24 for square in self.selected_squares):
            raise ValueError("Selected square is invalid")
        if sum(self.allocation_by_square.values()) != self.deployment_total_lamports:
            raise ValueError("Allocation must equal intended deployment")
        return self


class FinalOutcome(CollectionModel):
    outcome_id: str
    round_id: int = Field(ge=0)
    winner_square: int = Field(ge=0, le=24)
    finalized_at: datetime
    outcome_source: Literal["observed", "enriched"]
    final_square_deployments: list[int]
    total_winnings: int = Field(ge=0)
    motherlode_raw: int | None = Field(default=None, ge=0)
    base_ore_raw: int | None = Field(default=None, ge=0)
    source_reference: str
    version: int = Field(ge=1)
    correction_of: str | None = None

    @model_validator(mode="after")
    def board_is_complete(self):
        if len(self.final_square_deployments) != 25:
            raise ValueError("Final outcome requires 25 square deployments")
        return self


class PaperAccounting(CollectionModel):
    accounting_id: str
    opportunity_id: str
    decision_id: str
    outcome_id: str
    winner_selected: bool
    paper_deployed_lamports: int = Field(ge=0)
    paper_gross_sol_return_lamports: int = Field(ge=0)
    paper_net_sol_before_fees: int
    paper_assumed_deploy_fee: int = Field(ge=0)
    paper_assumed_claim_fee: int = Field(ge=0)
    paper_net_sol_after_assumed_fees: int
    paper_base_ore_raw: int | None = Field(default=None, ge=0)
    paper_motherlode_ore_raw: int | None = Field(default=None, ge=0)
    paper_total_ore_raw: int | None = Field(default=None, ge=0)
    provenance: dict[str, str]
    classification: Literal["reconstructed_paper_not_wallet_realized"]


class PaperReconciliation(CollectionModel):
    schema_version: int = 1
    opportunity_id: str
    decision_linked: bool
    outcome_linked: bool
    accounting_linked: bool
    provenance_complete: bool
    state: Literal[
        "complete_paper_reconstructed",
        "partial_missing_decision",
        "partial_missing_outcome",
        "partial_missing_accounting",
        "failed_provenance",
    ]
    blocking_gaps: list[str]
    classification: Literal["paper_not_wallet_realized"]


class HealthSnapshot(CollectionModel):
    schema_version: int = 1
    mode: Literal["historical_replay_burn_in", "real_time_burn_in"]
    collector_uptime_seconds: float = Field(ge=0)
    source_records_seen: int = Field(ge=0)
    source_records_imported: int = Field(ge=0)
    source_records_duplicate: int = Field(ge=0)
    source_records_malformed: int = Field(ge=0)
    cursor_lag_records: int = Field(ge=0)
    cursor_lag_seconds: float | None = Field(default=None, ge=0)
    opportunities_started: int = Field(ge=0)
    opportunities_completed: int = Field(ge=0)
    opportunities_expired: int = Field(ge=0)
    paper_decisions_created: int = Field(ge=0)
    paper_decisions_skipped: int = Field(ge=0)
    outcomes_linked: int = Field(ge=0)
    outcomes_missing: int = Field(ge=0)
    reconciliations_complete: int = Field(ge=0)
    reconciliations_partial: int = Field(ge=0)
    database_size_bytes: int = Field(ge=0)
    memory_usage_bytes: int | None = Field(default=None, ge=0)
    processing_latency_ms: float = Field(ge=0)
    last_successful_ingestion: datetime | None = None
    last_successful_decision: datetime | None = None
    last_successful_outcome_link: datetime | None = None


class BurnInEvaluation(CollectionModel):
    schema_version: int = 1
    mode: Literal["historical_replay_burn_in", "real_time_burn_in"]
    start_opportunity_id: str | None
    evaluated_opportunities: int = Field(ge=0)
    consecutive_eligible_opportunities: int = Field(ge=0)
    opportunity_to_decision_linkage: float = Field(ge=0, le=1)
    outcome_linkage: float = Field(ge=0, le=1)
    duplicate_opportunities: int = Field(ge=0)
    duplicate_decisions: int = Field(ge=0)
    malformed_records: int = Field(ge=0)
    source_corruption: int = Field(ge=0)
    database_lock_failures: int = Field(ge=0)
    provenance_complete: bool
    restart_resume_proven: bool
    observer_modified: bool
    live_actions: int = Field(ge=0)
    passed: bool
    failed_criteria: list[str]
