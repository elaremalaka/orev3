"""Outcome-blind measurement reconstruction for Experiment 005 source input.

This module deliberately contains no lifecycle outcome model, opener, parser,
provider, evaluator, or filesystem capability.  It is the finite measurement
surface copied into the INPUT_PROJECTOR closure.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from orev3.features.rq003_active_round_motherlode import (
    ACTIVE_ROUND_MOTHERLODE_DEFINITION,
    ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION,
    ACTIVE_ROUND_MOTHERLODE_MEASUREMENT,
)
from orev3.features.rq003_deployed_lamports import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_MEASUREMENT,
)
from orev3.features.rq003_execution import (
    ExecutableMeasurementBinding,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
)
from orev3.features.rq003_miner_count import (
    MINER_COUNT_DEFINITION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_MEASUREMENT,
)
from orev3.features.rq003_production_cost_ema import (
    PRODUCTION_COST_EMA_DEFINITION,
    PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    PRODUCTION_COST_EMA_MEASUREMENT,
)
from orev3.features.rq003_registry import (
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    EligibilityCatalog,
    FrozenFeatureRegistry,
)
from orev3.features.rq003_total_miners import (
    TOTAL_MINERS_DEFINITION,
    TOTAL_MINERS_ELIGIBILITY_DECISION,
    TOTAL_MINERS_MEASUREMENT,
)
from orev3.features.rq003_total_vaulted import (
    TOTAL_VAULTED_DEFINITION,
    TOTAL_VAULTED_ELIGIBILITY_DECISION,
    TOTAL_VAULTED_MEASUREMENT,
)
from orev3.features.rq003_total_winnings import (
    TOTAL_WINNINGS_DEFINITION,
    TOTAL_WINNINGS_ELIGIBILITY_DECISION,
    TOTAL_WINNINGS_MEASUREMENT,
)
from orev3.features.rq003_treasury_motherlode import (
    TREASURY_MOTHERLODE_DEFINITION,
    TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    TREASURY_MOTHERLODE_MEASUREMENT,
)
from orev3.strategy_lab.interfaces import DecisionContext

OUTPUT_NAMES = (
    "deployed_lamports", "miner_count", "total_miners",
    "board_production_cost_ema", "active_round_motherlode",
    "treasury_motherlode", "pre_finalization_total_vaulted",
    "pre_finalization_total_winnings",
)
_DEFINITIONS = (
    DEPLOYED_LAMPORTS_DEFINITION, MINER_COUNT_DEFINITION,
    TOTAL_MINERS_DEFINITION, PRODUCTION_COST_EMA_DEFINITION,
    ACTIVE_ROUND_MOTHERLODE_DEFINITION, TREASURY_MOTHERLODE_DEFINITION,
    TOTAL_VAULTED_DEFINITION, TOTAL_WINNINGS_DEFINITION,
)
_DECISIONS = (
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION, MINER_COUNT_ELIGIBILITY_DECISION,
    TOTAL_MINERS_ELIGIBILITY_DECISION, PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION,
    TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    TOTAL_VAULTED_ELIGIBILITY_DECISION, TOTAL_WINNINGS_ELIGIBILITY_DECISION,
)
_COMPUTATIONS = (
    DEPLOYED_LAMPORTS_MEASUREMENT, MINER_COUNT_MEASUREMENT,
    TOTAL_MINERS_MEASUREMENT, PRODUCTION_COST_EMA_MEASUREMENT,
    ACTIVE_ROUND_MOTHERLODE_MEASUREMENT, TREASURY_MOTHERLODE_MEASUREMENT,
    TOTAL_VAULTED_MEASUREMENT, TOTAL_WINNINGS_MEASUREMENT,
)


def _identity(domain: str, material: object) -> str:
    raw = json.dumps(material, allow_nan=False, ensure_ascii=False,
                     separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(domain.encode() + b"\n" + raw).hexdigest()


def build_pipeline() -> RQ003MeasurementPipeline:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=_DECISIONS,
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=_DEFINITIONS,
    )
    bindings = tuple(
        ExecutableMeasurementBinding(
            definition=definition,
            terminal_decision=decision,
            computation=computation,
        )
        for definition, decision, computation in zip(
            _DEFINITIONS, _DECISIONS, _COMPUTATIONS, strict=True
        )
    )
    return RQ003MeasurementPipeline(registry=registry, bindings=bindings)


@dataclass(frozen=True, slots=True)
class SourceObservationReference:
    observed_at_utc: datetime
    rpc_slot: int
    source_file: str
    source_line_number: int
    reference_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_identity", _identity(
            "rq003-experiment-005-observation-reference-v1",
            self.to_material(),
        ))

    def to_material(self) -> dict[str, object]:
        return {
            "observed_at_utc": self.observed_at_utc.isoformat(),
            "rpc_slot": self.rpc_slot,
            "source_file": self.source_file,
            "source_line_number": self.source_line_number,
        }


@dataclass(frozen=True, slots=True)
class SourceDecisionSnapshot:
    structural_round_key: int
    observation_index: int
    deployed_lamports: tuple[int, ...]
    miner_counts: tuple[int, ...]
    total_miners: int
    active_round_motherlode: int
    pre_finalization_total_vaulted: int
    pre_finalization_total_winnings: int
    production_cost_ema: int
    treasury_motherlode: int
    decision_point_configuration_identity: str
    decision_snapshot_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision_snapshot_identity",
            self.execution_context(0).decision_snapshot_identity,
        )

    def decision_context(self) -> DecisionContext:
        return DecisionContext(information={
            "round_id": self.structural_round_key,
            "round": {
                "round_id": self.structural_round_key,
                "deployed_lamports": self.deployed_lamports,
                "miner_counts": self.miner_counts,
                "total_miners": self.total_miners,
                "motherlode": self.active_round_motherlode,
                "total_vaulted": self.pre_finalization_total_vaulted,
                "total_winnings": self.pre_finalization_total_winnings,
            },
            "board": {"round_id": self.structural_round_key,
                      "production_cost_ema": self.production_cost_ema},
            "treasury": {"motherlode": self.treasury_motherlode},
        })

    def execution_context(self, candidate_square: int) -> RQ003ExecutionContext:
        return RQ003ExecutionContext(
            decision_context=self.decision_context(),
            observation_index=self.observation_index,
            structural_candidate_key=candidate_square,
            decision_point_configuration_identity=self.decision_point_configuration_identity,
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "active_round_motherlode": self.active_round_motherlode,
            "decision_point_configuration_identity": self.decision_point_configuration_identity,
            "decision_snapshot_identity": self.decision_snapshot_identity,
            "deployed_lamports": self.deployed_lamports,
            "miner_counts": self.miner_counts,
            "observation_index": self.observation_index,
            "pre_finalization_total_vaulted": self.pre_finalization_total_vaulted,
            "pre_finalization_total_winnings": self.pre_finalization_total_winnings,
            "production_cost_ema": self.production_cost_ema,
            "structural_round_key": self.structural_round_key,
            "total_miners": self.total_miners,
            "treasury_motherlode": self.treasury_motherlode,
        }


@dataclass(frozen=True, slots=True)
class SourceDecisionObservation:
    reference: SourceObservationReference
    snapshot: SourceDecisionSnapshot
    measurement_vector_bytes: tuple[bytes, ...]

    @property
    def observation_index(self) -> int:
        return self.snapshot.observation_index

    @property
    def observed_at_utc(self) -> datetime:
        return self.reference.observed_at_utc

    @property
    def rpc_slot(self) -> int:
        return self.reference.rpc_slot

    @property
    def decision_snapshot_identity(self) -> str:
        return self.snapshot.decision_snapshot_identity

    @property
    def measurement_vector_identities(self) -> tuple[str, ...]:
        from orev3.features.rq003_execution import MeasurementVector
        return tuple(
            MeasurementVector.from_canonical_bytes(raw).vector_identity
            for raw in self.measurement_vector_bytes
        )


PIPELINE = build_pipeline()

__all__ = ["OUTPUT_NAMES", "PIPELINE", "SourceDecisionObservation",
           "SourceDecisionSnapshot", "SourceObservationReference"]
