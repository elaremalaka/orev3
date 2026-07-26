from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orev3.ledger.identifiers import canonical_json
from orev3.ledger.validation import assert_observational_only


EXPERIMENT_ID = "rfc008-round-level-paper-v1"
CANDIDATE_HASH = (
    "e60722e845d6364c41d28ebc7d1641f8c8726766f87bdb838f3822decf50a372"
)
APPROVAL_MANIFEST_HASH = (
    "9fe94099ed3d9e15e015eef72db5543f16c756b1c3c5463f014e18467a44d789"
)
RANDOM_PREFIX = "rfc008-random-top4-v1-seed-20260725"


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArmConfig(FrozenModel):
    arm_id: Literal[
        "highest_reward_top4_v1",
        "random_top4_v1",
        "least_crowded_v1",
        "rfc007_frozen_reference_v1",
        "no_deploy_v1",
    ]
    role: Literal["candidate", "baseline", "historical", "economic_control"]
    statistical_independent: bool
    deployment_lamports: int = Field(ge=0)


class FeeConfig(FrozenModel):
    deploy_fee_lamports: Literal[5000] = 5000
    claim_fee_lamports: Literal[5000] = 5000
    priority_fee_lamports: Literal[0] = 0
    failed_transaction_fee_lamports: Literal[0] = 0
    accounting_mode: Literal[
        "historical_price_taking_reconstructed_not_wallet_realized"
    ] = "historical_price_taking_reconstructed_not_wallet_realized"


class DecisionCriteria(FrozenModel):
    alpha_predictive: Literal[0.025] = 0.025
    alpha_economic: Literal[0.025] = 0.025
    minimum_paired_hit_improvement: Literal[0.06] = 0.06
    minimum_analyzable_rounds: Literal[600] = 600
    maximum_started_rounds: Literal[632] = 632
    maximum_calendar_days: Literal[14] = 14
    maximum_unusable_rate: Literal[0.05] = 0.05


class RFC008Config(FrozenModel):
    schema_version: Literal[1] = 1
    protocol_version: Literal["rfc008-v1"] = "rfc008-v1"
    experiment_id: Literal[EXPERIMENT_ID] = EXPERIMENT_ID
    collector_version: str = "rfc008-paper-collector-v1"
    source_glob: str
    candidate_configuration_sha256: Literal[CANDIDATE_HASH] = CANDIDATE_HASH
    approval_manifest_sha256: Literal[APPROVAL_MANIFEST_HASH] = (
        APPROVAL_MANIFEST_HASH
    )
    trigger_seconds_remaining: Literal[30.0] = 30.0
    trigger_slots_remaining: Literal[75] = 75
    slot_duration_seconds: Literal[0.4] = 0.4
    square_count: Literal[4] = 4
    deployment_total_lamports: Literal[50000] = 50000
    allocation_rule: Literal["equal"] = "equal"
    random_algorithm: Literal["sha256_digest_sort"] = "sha256_digest_sort"
    random_seed_prefix: Literal[RANDOM_PREFIX] = RANDOM_PREFIX
    direct_outcomes_only_primary: Literal[True] = True
    arms: tuple[ArmConfig, ...]
    fees: FeeConfig = FeeConfig()
    criteria: DecisionCriteria = DecisionCriteria()
    poll_interval_seconds: float = Field(default=1.0, gt=0)
    batch_size: int = Field(default=100, gt=0)
    busy_timeout_ms: int = Field(default=5000, ge=1)
    allow_transaction_building: Literal[False] = False
    allow_transaction_submission: Literal[False] = False
    allow_signing: Literal[False] = False
    allow_claims: Literal[False] = False
    allow_wallet_access: Literal[False] = False
    allow_rpc_outcome_recovery: Literal[False] = False

    @model_validator(mode="after")
    def frozen_protocol(self):
        assert_observational_only(
            build_transaction=self.allow_transaction_building,
            submit=self.allow_transaction_submission,
            sign=self.allow_signing,
            claim=self.allow_claims,
        )
        expected = {
            "highest_reward_top4_v1",
            "random_top4_v1",
            "least_crowded_v1",
            "rfc007_frozen_reference_v1",
            "no_deploy_v1",
        }
        ids = [arm.arm_id for arm in self.arms]
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise ValueError("RFC-008 requires exactly the five frozen arms")
        by_id = {arm.arm_id: arm for arm in self.arms}
        if by_id["rfc007_frozen_reference_v1"].statistical_independent:
            raise ValueError("RFC-007 alias is not statistically independent")
        if by_id["no_deploy_v1"].deployment_lamports != 0:
            raise ValueError("No-deploy must deploy zero")
        for arm_id, arm in by_id.items():
            if arm_id != "no_deploy_v1" and arm.deployment_lamports != 50000:
                raise ValueError("Every active arm must deploy 50000 lamports")
        return self

    @classmethod
    def from_path(cls, path: str | Path) -> "RFC008Config":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    @property
    def configuration_fingerprint(self) -> str:
        raw = canonical_json(self.model_dump(mode="json")).encode()
        return hashlib.sha256(raw).hexdigest()
