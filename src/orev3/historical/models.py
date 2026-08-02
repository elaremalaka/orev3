from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


SquareValues = Annotated[
    list[int],
    Field(min_length=25, max_length=25),
]


class NormalizedBoardState(BaseModel):
    model_config = ConfigDict(frozen=True)

    round_id: int
    start_slot: int
    end_slot: int
    production_cost_ema: int | None = None


class NormalizedTreasuryState(BaseModel):
    model_config = ConfigDict(frozen=True)

    motherlode: int


class NormalizedRoundState(BaseModel):
    model_config = ConfigDict(frozen=True)

    round_id: int

    deployed_lamports: SquareValues
    mass: SquareValues
    miner_counts: SquareValues

    slot_hash_hex: str
    expires_at: int

    motherlode: int
    rewards: SquareValues

    total_vaulted: int
    total_winnings: int
    total_miners: int

    top_miner: str
    entropy: int | None = None


class NormalizedSnapshot(BaseModel):
    """
    Canonical historical representation of one raw
    Observer snapshot.

    Raw JSONL files remain untouched.
    """

    model_config = ConfigDict(frozen=True)

    source_schema_version: int

    observed_at_utc: datetime
    rpc_slot: int

    collector_session_id: str | None = None

    board: NormalizedBoardState
    treasury: NormalizedTreasuryState
    round: NormalizedRoundState

    source_file: str
    source_line_number: int


class MalformedRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_file: str
    source_line_number: int
    error_type: str
    error_message: str


class SnapshotReadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshots: list[NormalizedSnapshot]
    malformed_records: list[MalformedRecord]

    files_read: int
    lines_read: int


class RoundQualityMetadata(BaseModel):
    """
    Data-quality observations for one assembled round.

    Quality flags never alter or delete raw observations.
    """

    model_config = ConfigDict(frozen=True)

    coverage_status: Literal[
        "complete",
        "partial_start",
        "partial_end",
        "partial_both",
        "unknown",
    ]

    initialization_state_observed: bool

    rpc_slot_regression_count: int
    largest_rpc_slot_regression: int

    duplicate_rpc_slot_count: int

    max_observation_gap_seconds: float

    significant_gap_count: int
    significant_gap_threshold_seconds: float

    collector_session_count: int

    finalized_state_observed: bool


class FinalizedRoundOutcome(BaseModel):
    """
    Finalized protocol state, only when actually observed.

    This must not be inferred from active-round state.
    """

    model_config = ConfigDict(frozen=True)

    observed_at_utc: datetime
    rpc_slot: int

    entropy: int | None
    winning_square: int | None

    deployed_lamports: SquareValues
    miner_counts: SquareValues

    reward_buckets: SquareValues

    total_vaulted: int
    total_winnings: int
    total_miners: int

    round_motherlode: int
    top_miner: str


class RoundLifecycle(BaseModel):
    """
    Derived historical representation of one ORE round.

    The observation_history preserves point-in-time state
    for future replay.
    """

    model_config = ConfigDict(frozen=True)

    lifecycle_schema_version: int = 1

    round_id: int

    start_slot: int
    end_slot: int | None

    first_observed_at_utc: datetime
    last_observed_at_utc: datetime

    first_observed_rpc_slot: int
    last_observed_rpc_slot: int

    observation_count: int

    collector_session_ids: list[str]

    source_schema_versions: list[int]
    source_files: list[str]

    first_observation: NormalizedSnapshot
    last_observation: NormalizedSnapshot

    observation_history: list[NormalizedSnapshot]

    finalized_outcome: FinalizedRoundOutcome | None

    # Distinguishes outcomes captured in the live observation
    # timeline from outcomes fetched later for scoring/backtesting.
    finalized_outcome_source: Literal[
        "observed",
        "enriched",
    ] | None = None

    # RFC-012 capture detail remains outcome-only metadata.  None preserves
    # compatibility with pre-RFC-012 lifecycles and enriched outcomes.
    finalized_outcome_capture_mode: Literal[
        "current_round",
        "post_transition_predecessor",
    ] | None = None

    # Immutable evidence identities supporting the selected local outcome.
    # Current-round outcomes may retain agreeing supplementary RFC-012
    # identities without exposing them through replay snapshots.
    finalized_outcome_evidence_identities: tuple[str, ...] = ()

    quality: RoundQualityMetadata


class LifecycleAssemblyResult(BaseModel):
    """
    Result of assembling normalized snapshots into rounds.
    """

    model_config = ConfigDict(frozen=True)

    rounds: list[RoundLifecycle]

    total_snapshots: int
    total_rounds: int


class ObservationReference(BaseModel):
    """
    Pointer back to one immutable raw snapshot.

    The full observation remains in the raw JSONL file.
    """

    model_config = ConfigDict(frozen=True)

    source_file: str
    source_line_number: int

    observed_at_utc: datetime
    rpc_slot: int


class RoundLifecycleIndexRecord(BaseModel):
    """
    Compact persistent historical record for one round.

    Full observation history is represented by references
    to immutable raw JSONL source records.
    """

    model_config = ConfigDict(frozen=True)

    lifecycle_schema_version: int = 1

    round_id: int

    start_slot: int
    end_slot: int | None

    first_observed_at_utc: datetime
    last_observed_at_utc: datetime

    first_observed_rpc_slot: int
    last_observed_rpc_slot: int

    observation_count: int

    collector_session_ids: list[str]
    source_schema_versions: list[int]
    source_files: list[str]

    observation_references: list[
        ObservationReference
    ]

    finalized_outcome: (
        FinalizedRoundOutcome
        | None
    )

    finalized_outcome_source: Literal[
        "observed",
        "enriched",
    ] | None

    finalized_outcome_capture_mode: Literal[
        "current_round",
        "post_transition_predecessor",
    ] | None = None

    finalized_outcome_evidence_identities: tuple[str, ...] = ()

    quality: RoundQualityMetadata


class HistoricalDatasetManifest(BaseModel):
    """
    Metadata describing one reproducible derived dataset build.
    """

    model_config = ConfigDict(frozen=True)

    dataset_schema_version: int = 1

    generated_at_utc: datetime

    input_files: list[str]

    lines_read: int
    normalized_snapshots: int
    malformed_source_records: int

    total_rounds: int

    observed_outcomes: int
    enriched_outcomes: int
    missing_outcomes: int

    enrichment_unavailable: int
    enrichment_failed: int
