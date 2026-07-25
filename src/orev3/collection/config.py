from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orev3.ledger.identifiers import canonical_json
from orev3.ledger.validation import assert_observational_only


class ChronologicalBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block_id: str
    start_index: int = Field(ge=0)
    end_index: int = Field(ge=0)
    target_opportunities: int = Field(gt=0)
    report_only: bool = False

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_index < self.start_index:
            raise ValueError("Block end must not precede block start")
        if self.end_index - self.start_index + 1 != self.target_opportunities:
            raise ValueError("Block range must equal target opportunity count")
        return self


class CollectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    collector_version: str
    source_glob: str
    outcome_source: str
    poll_interval_seconds: float = Field(gt=0)
    batch_size: int = Field(gt=0)
    strategy_id: Literal[
        "least_miner_count",
        "least_deployed",
        "lowest_miner_share",
        "existing_least_crowded",
        "deterministic_seeded_random",
        "rfc004_model",
    ]
    strategy_version: str
    square_count: int = Field(ge=1, le=25)
    allocation_rule: Literal["equal", "rank_decay"]
    deployment_total_lamports: int = Field(ge=0)
    random_seed: int
    assumed_deploy_fee_lamports: int = Field(ge=0)
    assumed_claim_fee_lamports: int = Field(ge=0)
    retain_verbose_payloads: bool
    busy_timeout_ms: int = Field(ge=1)
    checkpoint_every_records: int = Field(ge=1)
    live_start_mode: Literal["beginning", "end"]
    chronological_blocks: list[ChronologicalBlock]
    allow_transaction_building: bool = False
    allow_transaction_submission: bool = False
    allow_signing: bool = False
    allow_claims: bool = False

    @model_validator(mode="after")
    def safe_and_frozen(self):
        assert_observational_only(
            build_transaction=self.allow_transaction_building,
            submit=self.allow_transaction_submission,
            sign=self.allow_signing,
            claim=self.allow_claims,
        )
        if len(self.chronological_blocks) != 4:
            raise ValueError("Exactly four chronological blocks are required")
        ordered = sorted(
            self.chronological_blocks, key=lambda block: block.start_index
        )
        for first, second in zip(ordered, ordered[1:]):
            if first.end_index + 1 != second.start_index:
                raise ValueError("Chronological blocks must be contiguous")
        if sum(block.report_only for block in ordered) != 1 or not ordered[-1].report_only:
            raise ValueError("Only the final chronological block is report-only")
        return self

    @classmethod
    def from_path(cls, path: str | Path) -> "CollectionConfig":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    @property
    def configuration_hash(self) -> str:
        return hashlib.sha256(
            canonical_json(self.model_dump(mode="json")).encode("utf-8")
        ).hexdigest()
