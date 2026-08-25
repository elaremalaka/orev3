"""Outcome-blind ranking capability for RQ-003 Experiment 005.

The public inputs in this module contain no outcome, winner, label, outcome
provider, or future-observation capability.  Outcome-authorized evaluation is
implemented in :mod:`orev3.experiments.rq003_experiment5_evaluation` and is
not imported here.
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping, Sequence

from orev3.datasets.rq003_experiment0 import (
    RQ003_EXPERIMENT0_OUTPUT_NAMES,
    build_fundamental_measurement_pipeline,
)
from orev3.experiments.rq003_experiment2a import (
    CanonicalRational,
    deployment_per_miner,
)
from orev3.experiments.rq003_experiment5 import (
    EXPERIMENT5_CANDIDATES,
    EXPERIMENT5_DATASET_SCHEMA_IDENTITY,
    EXPERIMENT5_DATASET_SHA256,
    EXPERIMENT5_DECISION_SELECTION_IDENTITY,
    EXPERIMENT5_FEATURE_SET_IDENTITY,
    EXPERIMENT5_IDENTIFIER,
    EXPERIMENT5_PROCEDURE_IDENTITIES,
    EXPERIMENT5_PROTOCOL_SHA256,
    EXPERIMENT5_PROTOCOL_REVISION_POPULATION_IDENTITY,
    EXPERIMENT5_SHARE_IMBALANCE_DEFINITION_IDENTITY,
    EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION,
    SignedRational,
    average_ranks,
    identity,
    immutable_material,
    require_sha256,
    seeded_random_ranks,
    share_imbalance,
    tie_group_sizes,
)
from orev3.features.rq003_contracts import canonical_decode, canonical_encode
from orev3.features.rq003_execution import (
    MeasurementVector,
    RQ003_PIPELINE_IMPLEMENTATION_IDENTITY,
    RQ003ExecutionContext,
)
from orev3.strategy_lab.interfaces import DecisionContext


_RANKING_RECORD_IDENTITY_DOMAIN = "rq003-experiment-005-ranking-record-v1"
_RANKING_ARTIFACT_IDENTITY_DOMAIN = "rq003-experiment-005-ranking-artifact-v1"
_RANKING_EXCLUSION_IDENTITY_DOMAIN = "rq003-experiment-005-ranking-exclusion-v1"
_OBSERVATION_REFERENCE_IDENTITY_DOMAIN = (
    "rq003-experiment-005-observation-reference-v1"
)
_SELECTED_SOURCE_PROJECTION_BINDING_IDENTITY_DOMAIN = (
    "rq003-experiment-005-selected-source-projection-binding-v1"
)
_SELECTED_DECISION_IDENTITY_DOMAIN = (
    "rq003-experiment-005-authenticated-selected-decision-v1"
)
_SELECTED_SOURCE_PARSED_RECORD_IDENTITY_DOMAIN = (
    "rq003-experiment-005-selected-source-parsed-record-v1"
)
_REPLAY_IDENTITY_DOMAIN = "rq003-experiment-005-replay-v1"
_REPLAY_ROUND_IDENTITY_DOMAIN = "rq003-experiment-005-replay-round-v1"
_SHARE_IMBALANCE_MEASUREMENT_IDENTITY_DOMAIN = (
    "rq003-experiment-005-share-imbalance-measurement-v1"
)
_FUNDAMENTAL_MEASUREMENT_PIPELINE = build_fundamental_measurement_pipeline()
_LIFECYCLE_STATES = {
    "complete",
    "partial_start",
    "partial_end",
    "partial_both",
}
_FORBIDDEN_RANKING_KEYS = {
    "capture_mode",
    "evaluation",
    "evaluation_result",
    "finalized_outcome",
    "label",
    "outcome",
    "outcome_availability",
    "outcome_provenance",
    "outcome_provider",
    "outcome_resolver",
    "outcome_source",
    "result",
    "winner",
    "winning_square",
    "won",
}


def _require_int(name: str, value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _require_nonempty_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be a nonempty canonical string")
    return value


def _require_finite_nonnegative(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return 0.0 if result == 0.0 else result


def _require_sorted_unique_strings(name: str, values: object) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not all(
        isinstance(value, str) and value for value in values
    ):
        raise TypeError(f"{name} must be an immutable tuple of nonempty strings")
    if values != tuple(sorted(set(values))):
        raise ValueError(f"{name} must be sorted and duplicate-free")
    return values


def _require_sorted_unique_ints(name: str, values: object) -> tuple[int, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    normalized = tuple(_require_int(name, value, minimum=1) for value in values)
    if not normalized or normalized != tuple(sorted(set(normalized))):
        raise ValueError(f"{name} must be nonempty, sorted, and duplicate-free")
    return normalized


@dataclass(frozen=True, slots=True)
class ObservationReferenceAuthority:
    """Canonical Replay member reference used to order equal-slot observations."""

    observed_at_utc: datetime
    rpc_slot: int
    source_file: str
    source_line_number: int
    source_member_identity: str = field(init=False)
    reference_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.observed_at_utc, datetime)
            or self.observed_at_utc.tzinfo is None
            or self.observed_at_utc.utcoffset() != UTC.utcoffset(self.observed_at_utc)
        ):
            raise ValueError("observed_at_utc must be an aware UTC datetime")
        _require_int("rpc_slot", self.rpc_slot)
        if not isinstance(self.source_file, str) or not self.source_file:
            raise ValueError("source_file must be nonempty")
        _require_int("source_line_number", self.source_line_number, minimum=1)
        object.__setattr__(
            self,
            "source_member_identity",
            identity(
                "rq003-experiment-005-source-member-v1",
                {"source_file": self.source_file},
            ),
        )
        object.__setattr__(
            self,
            "reference_identity",
            identity(_OBSERVATION_REFERENCE_IDENTITY_DOMAIN, self.to_identity_material()),
        )

    def canonical_order_key(self) -> tuple[datetime, str, int]:
        return (
            self.observed_at_utc,
            self.source_file,
            self.source_line_number,
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "observed_at_utc": self.observed_at_utc.isoformat(),
            "rpc_slot": self.rpc_slot,
            "source_file": self.source_file,
            "source_line_number": self.source_line_number,
            "source_member_identity": self.source_member_identity,
        }

    def to_material(self) -> dict[str, object]:
        return {**self.to_identity_material(), "reference_identity": self.reference_identity}

    @classmethod
    def from_material(cls, material: object) -> ObservationReferenceAuthority:
        if not isinstance(material, Mapping) or set(material) != {
            "observed_at_utc",
            "reference_identity",
            "rpc_slot",
            "source_file",
            "source_line_number",
            "source_member_identity",
        }:
            raise ValueError("observation reference material is not closed")
        result = cls(
            observed_at_utc=datetime.fromisoformat(material["observed_at_utc"]),
            rpc_slot=material["rpc_slot"],
            source_file=material["source_file"],
            source_line_number=material["source_line_number"],
        )
        if result.to_material() != material:
            raise ValueError("observation reference does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class DecisionSnapshotAuthority:
    """Closed pre-outcome state sufficient to reconstruct fundamental vectors."""

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
        _require_int("structural_round_key", self.structural_round_key)
        _require_int("observation_index", self.observation_index)
        for name, values in (
            ("deployed_lamports", self.deployed_lamports),
            ("miner_counts", self.miner_counts),
        ):
            if not isinstance(values, tuple) or len(values) != 25:
                raise ValueError(f"{name} must contain exactly 25 values")
            for value in values:
                _require_int(name, value)
        for name in (
            "total_miners",
            "active_round_motherlode",
            "pre_finalization_total_vaulted",
            "pre_finalization_total_winnings",
            "production_cost_ema",
            "treasury_motherlode",
        ):
            _require_int(name, getattr(self, name))
        if self.active_round_motherlode != 0:
            raise ValueError("active_round_motherlode must be decision-time zero")
        require_sha256(
            "decision_point_configuration_identity",
            self.decision_point_configuration_identity,
        )
        context = self.execution_context(0)
        object.__setattr__(
            self, "decision_snapshot_identity", context.decision_snapshot_identity
        )

    def decision_context(self) -> DecisionContext:
        return DecisionContext(
            information={
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
                "board": {
                    "round_id": self.structural_round_key,
                    "production_cost_ema": self.production_cost_ema,
                },
                "treasury": {"motherlode": self.treasury_motherlode},
            }
        )

    def execution_context(self, candidate_square: int) -> RQ003ExecutionContext:
        return RQ003ExecutionContext(
            decision_context=self.decision_context(),
            observation_index=self.observation_index,
            structural_candidate_key=candidate_square,
            decision_point_configuration_identity=(
                self.decision_point_configuration_identity
            ),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "active_round_motherlode": self.active_round_motherlode,
            "decision_point_configuration_identity": (
                self.decision_point_configuration_identity
            ),
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

    @classmethod
    def from_material(cls, material: object) -> DecisionSnapshotAuthority:
        if not isinstance(material, Mapping) or set(material) != {
            "active_round_motherlode", "decision_point_configuration_identity",
            "decision_snapshot_identity", "deployed_lamports", "miner_counts",
            "observation_index", "pre_finalization_total_vaulted",
            "pre_finalization_total_winnings", "production_cost_ema",
            "structural_round_key", "total_miners", "treasury_motherlode",
        }:
            raise ValueError("decision snapshot material is not closed")
        kwargs = dict(material)
        supplied_identity = kwargs.pop("decision_snapshot_identity")
        result = cls(**kwargs)
        if result.decision_snapshot_identity != supplied_identity or result.to_identity_material() != material:
            raise ValueError("decision snapshot authority does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class DecisionObservation:
    """Scientific state for the one canonically selected observation only."""

    reference: ObservationReferenceAuthority
    valid_normal_observation: bool
    snapshot: DecisionSnapshotAuthority
    measurement_vector_bytes: tuple[bytes, ...]
    measurement_vectors: tuple[MeasurementVector, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.reference, ObservationReferenceAuthority):
            raise TypeError("reference must be ObservationReferenceAuthority")
        if not isinstance(self.valid_normal_observation, bool):
            raise TypeError("valid_normal_observation must be boolean")
        if not isinstance(self.snapshot, DecisionSnapshotAuthority):
            raise TypeError("snapshot must be DecisionSnapshotAuthority")
        if (
            not isinstance(self.measurement_vector_bytes, tuple)
            or len(self.measurement_vector_bytes) != 25
            or not all(isinstance(value, bytes) for value in self.measurement_vector_bytes)
        ):
            raise ValueError("measurement_vector_bytes must contain 25 byte strings")
        reconstructed: list[MeasurementVector] = []
        for square, raw in enumerate(self.measurement_vector_bytes):
            supplied = MeasurementVector.from_canonical_bytes(raw)
            expected = _FUNDAMENTAL_MEASUREMENT_PIPELINE.compute(
                self.snapshot.execution_context(square)
            )
            if supplied.canonical_bytes() != expected.canonical_bytes():
                raise ValueError("fundamental MeasurementVector authority mismatch")
            if supplied.structural_candidate_key != square:
                raise ValueError("fundamental measurement candidate order mismatch")
            if tuple(field.name for field in supplied.ordered_output_fields) != (
                RQ003_EXPERIMENT0_OUTPUT_NAMES
            ):
                raise ValueError("fundamental measurement output schema mismatch")
            reconstructed.append(supplied)
        object.__setattr__(self, "measurement_vectors", tuple(reconstructed))

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
    def deployed_lamports(self) -> tuple[int, ...]:
        index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("deployed_lamports")
        return tuple(int(vector.ordered_values[index]) for vector in self.measurement_vectors)

    @property
    def miner_counts(self) -> tuple[int, ...]:
        index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("miner_count")
        return tuple(int(vector.ordered_values[index]) for vector in self.measurement_vectors)

    @property
    def measurement_vector_identities(self) -> tuple[str, ...]:
        return tuple(vector.vector_identity for vector in self.measurement_vectors)

    def to_material(self) -> dict[str, object]:
        return {
            "fundamental_measurement_vector_canonical_hex": tuple(
                value.hex() for value in self.measurement_vector_bytes
            ),
            "reference": self.reference.to_material(),
            "snapshot": self.snapshot.to_identity_material(),
            "valid_normal_observation": self.valid_normal_observation,
        }

    @classmethod
    def from_material(cls, material: object) -> DecisionObservation:
        if not isinstance(material, Mapping) or set(material) != {
            "fundamental_measurement_vector_canonical_hex",
            "reference",
            "snapshot",
            "valid_normal_observation",
        }:
            raise ValueError("decision observation material is not closed")
        vector_hex = material["fundamental_measurement_vector_canonical_hex"]
        if not isinstance(vector_hex, tuple) or not all(
            isinstance(value, str) for value in vector_hex
        ):
            raise ValueError("measurement vector hex sequence is not canonical")
        try:
            vector_bytes = tuple(bytes.fromhex(value) for value in vector_hex)
        except ValueError as exc:
            raise ValueError("measurement vector canonical hex is invalid") from exc
        result = cls(
            reference=ObservationReferenceAuthority.from_material(material["reference"]),
            valid_normal_observation=material["valid_normal_observation"],
            snapshot=DecisionSnapshotAuthority.from_material(material["snapshot"]),
            measurement_vector_bytes=vector_bytes,
        )
        if result.to_material() != material:
            raise ValueError("decision observation authority does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class DecisionObservationReference:
    """Reference-only Replay authority used to select one decision observation."""

    reference: ObservationReferenceAuthority
    observation_index: int
    valid_normal_observation: bool

    def __post_init__(self) -> None:
        if not isinstance(self.reference, ObservationReferenceAuthority):
            raise TypeError("reference must be ObservationReferenceAuthority")
        _require_int("observation_index", self.observation_index)
        if not isinstance(self.valid_normal_observation, bool):
            raise TypeError("valid_normal_observation must be boolean")

    def to_material(self) -> dict[str, object]:
        return {
            "observation_index": self.observation_index,
            "reference": self.reference.to_material(),
            "valid_normal_observation": self.valid_normal_observation,
        }

    @classmethod
    def from_material(cls, material: object) -> DecisionObservationReference:
        if not isinstance(material, Mapping) or set(material) != {
            "observation_index",
            "reference",
            "valid_normal_observation",
        }:
            raise ValueError("decision observation reference material is not closed")
        result = cls(
            reference=ObservationReferenceAuthority.from_material(material["reference"]),
            observation_index=material["observation_index"],
            valid_normal_observation=material["valid_normal_observation"],
        )
        if result.to_material() != material:
            raise ValueError("decision observation reference does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class SelectedSourceProjectionBinding:
    """Closed dependency on upstream-authenticated selected-source material.

    This binding does not authenticate filesystem bytes. A future governed
    Source-S capability must establish the external-input, record, decoder,
    projection, and Replay identities before constructing this value. Slice 1
    validates canonical form and the exact relationship to the selected
    reference, snapshot, and fundamental MeasurementVectors.
    """

    external_input_identifier: str
    external_input_identity: str
    immutable_input_snapshot_identity: str
    ordered_collection_manifest_identity: str
    logical_member_identifier: str
    member_order: int
    member_byte_count: int
    member_sha256: str
    external_schema_identity: str
    source_file: str
    source_line_number: int
    persisted_record_byte_sha256: str
    canonical_parsed_record_identity: str
    source_schema_version: int
    protocol_revision: str
    observed_at_utc: datetime
    rpc_slot: int
    valid_normal_observation: bool
    collector_session_id: str | None
    decoder_component_identity: str
    decoder_configuration_identity: str
    parser_component_identity: str
    projector_component_identity: str
    projection_schema_identity: str
    projection_sha256: str
    projection_identity: str
    dataset_identity: str
    dataset_content_identity: str
    replay_source_unit_identity: str
    selected_decision_identity: str
    selected_reference_identity: str
    selected_observation_index: int
    selected_snapshot_identity: str
    fundamental_measurement_vector_identities: tuple[str, ...]
    selected_source_projection_binding_identity: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "external_input_identifier",
            "logical_member_identifier",
            "source_file",
        ):
            _require_nonempty_string(name, getattr(self, name))
        for name in (
            "external_input_identity",
            "immutable_input_snapshot_identity",
            "ordered_collection_manifest_identity",
            "member_sha256",
            "external_schema_identity",
            "persisted_record_byte_sha256",
            "canonical_parsed_record_identity",
            "decoder_component_identity",
            "decoder_configuration_identity",
            "parser_component_identity",
            "projector_component_identity",
            "projection_schema_identity",
            "projection_sha256",
            "projection_identity",
            "dataset_identity",
            "dataset_content_identity",
            "replay_source_unit_identity",
            "selected_decision_identity",
            "selected_reference_identity",
            "selected_snapshot_identity",
        ):
            require_sha256(name, getattr(self, name))
        _require_int("member_order", self.member_order)
        _require_int("member_byte_count", self.member_byte_count)
        _require_int("source_line_number", self.source_line_number, minimum=1)
        _require_int("source_schema_version", self.source_schema_version, minimum=1)
        _require_int("rpc_slot", self.rpc_slot)
        _require_int("selected_observation_index", self.selected_observation_index)
        if self.protocol_revision != EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION:
            raise ValueError("selected-source protocol revision is unsupported")
        if (
            not isinstance(self.observed_at_utc, datetime)
            or self.observed_at_utc.tzinfo is None
            or self.observed_at_utc.utcoffset()
            != UTC.utcoffset(self.observed_at_utc)
        ):
            raise ValueError("selected-source observed_at_utc must be aware UTC")
        if not isinstance(self.valid_normal_observation, bool):
            raise TypeError("valid_normal_observation must be boolean")
        if self.collector_session_id is not None:
            _require_nonempty_string("collector_session_id", self.collector_session_id)
        vectors = self.fundamental_measurement_vector_identities
        if not isinstance(vectors, tuple) or len(vectors) != 25:
            raise ValueError(
                "fundamental_measurement_vector_identities must contain 25 identities"
            )
        for vector_identity in vectors:
            require_sha256("fundamental MeasurementVector identity", vector_identity)
        object.__setattr__(
            self,
            "selected_source_projection_binding_identity",
            identity(
                _SELECTED_SOURCE_PROJECTION_BINDING_IDENTITY_DOMAIN,
                self.to_identity_material(),
            ),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "canonical_parsed_record_identity": self.canonical_parsed_record_identity,
            "collector_session_id": self.collector_session_id,
            "dataset_content_identity": self.dataset_content_identity,
            "dataset_identity": self.dataset_identity,
            "decoder_component_identity": self.decoder_component_identity,
            "decoder_configuration_identity": self.decoder_configuration_identity,
            "external_input_identifier": self.external_input_identifier,
            "external_input_identity": self.external_input_identity,
            "external_schema_identity": self.external_schema_identity,
            "fundamental_measurement_vector_identities": (
                self.fundamental_measurement_vector_identities
            ),
            "immutable_input_snapshot_identity": self.immutable_input_snapshot_identity,
            "logical_member_identifier": self.logical_member_identifier,
            "member_byte_count": self.member_byte_count,
            "member_order": self.member_order,
            "member_sha256": self.member_sha256,
            "observed_at_utc": self.observed_at_utc.isoformat(),
            "ordered_collection_manifest_identity": (
                self.ordered_collection_manifest_identity
            ),
            "parser_component_identity": self.parser_component_identity,
            "persisted_record_byte_sha256": self.persisted_record_byte_sha256,
            "projection_identity": self.projection_identity,
            "projection_schema_identity": self.projection_schema_identity,
            "projection_sha256": self.projection_sha256,
            "projector_component_identity": self.projector_component_identity,
            "protocol_revision": self.protocol_revision,
            "replay_source_unit_identity": self.replay_source_unit_identity,
            "rpc_slot": self.rpc_slot,
            "selected_decision_identity": self.selected_decision_identity,
            "selected_observation_index": self.selected_observation_index,
            "selected_reference_identity": self.selected_reference_identity,
            "selected_snapshot_identity": self.selected_snapshot_identity,
            "source_file": self.source_file,
            "source_line_number": self.source_line_number,
            "source_schema_version": self.source_schema_version,
            "valid_normal_observation": self.valid_normal_observation,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "selected_source_projection_binding_identity": (
                self.selected_source_projection_binding_identity
            ),
        }

    @classmethod
    def from_material(cls, material: object) -> SelectedSourceProjectionBinding:
        fields = {item.name for item in cls.__dataclass_fields__.values() if item.init}
        if not isinstance(material, Mapping) or set(material) != fields | {
            "selected_source_projection_binding_identity"
        }:
            raise ValueError("selected-source projection binding material is not closed")
        kwargs = {name: material[name] for name in fields}
        kwargs["observed_at_utc"] = datetime.fromisoformat(material["observed_at_utc"])
        result = cls(**kwargs)
        if result.to_material() != material:
            raise ValueError("selected-source projection binding does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class RankingRoundInput:
    """Closed pre-outcome input for one Replay round."""

    round_identity: str
    round_id: int
    start_slot: int
    end_slot: int
    lifecycle_status: str
    observation_count: int
    significant_gap_count: int
    max_observation_gap_seconds: float
    significant_gap_threshold_seconds: float
    collector_session_ids: tuple[str, ...]
    collector_session_count: int
    source_schema_versions: tuple[int, ...]
    protocol_revision: str
    observation_references: tuple[DecisionObservationReference, ...]
    selected_observation: DecisionObservation | None
    selected_source_projection_binding: SelectedSourceProjectionBinding | None
    selected_reference_science_binding_identity: str | None = field(
        init=False, compare=False
    )

    def __post_init__(self) -> None:
        require_sha256("round_identity", self.round_identity)
        _require_int("round_id", self.round_id)
        _require_int("start_slot", self.start_slot)
        _require_int("end_slot", self.end_slot)
        if self.end_slot < 5:
            raise ValueError("end_slot cannot represent the frozen decision boundary")
        if self.lifecycle_status not in _LIFECYCLE_STATES:
            raise ValueError("lifecycle_status is unsupported")
        _require_int("observation_count", self.observation_count)
        _require_int("significant_gap_count", self.significant_gap_count)
        object.__setattr__(
            self,
            "max_observation_gap_seconds",
            _require_finite_nonnegative(
                "max_observation_gap_seconds", self.max_observation_gap_seconds
            ),
        )
        object.__setattr__(
            self,
            "significant_gap_threshold_seconds",
            _require_finite_nonnegative(
                "significant_gap_threshold_seconds",
                self.significant_gap_threshold_seconds,
            ),
        )
        if (
            self.significant_gap_count == 0
            and self.max_observation_gap_seconds
            > self.significant_gap_threshold_seconds
        ) or (
            self.significant_gap_count > 0
            and self.max_observation_gap_seconds
            <= self.significant_gap_threshold_seconds
        ):
            raise ValueError("significant-gap metadata is internally inconsistent")
        sessions = _require_sorted_unique_strings(
            "collector_session_ids", self.collector_session_ids
        )
        _require_int("collector_session_count", self.collector_session_count)
        if self.collector_session_count != len(sessions):
            raise ValueError("collector_session_count does not reconcile")
        _require_sorted_unique_ints("source_schema_versions", self.source_schema_versions)
        if self.protocol_revision != EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION:
            raise ValueError("protocol_revision is unsupported")
        if not isinstance(self.observation_references, tuple):
            raise TypeError("observation_references must be an immutable tuple")
        if self.observation_count != len(self.observation_references):
            raise ValueError("observation_count does not reconcile")
        ordered = tuple(
            sorted(
                self.observation_references,
                key=lambda observation: observation.reference.canonical_order_key(),
            )
        )
        source_coordinates = tuple(
            (item.reference.source_file, item.reference.source_line_number)
            for item in ordered
        )
        if len(source_coordinates) != len(set(source_coordinates)):
            raise ValueError("duplicate immutable source coordinate")
        reference_identities = tuple(
            observation.reference.reference_identity for observation in ordered
        )
        if len(reference_identities) != len(set(reference_identities)):
            raise ValueError("duplicate canonical observation reference")
        indices = tuple(observation.observation_index for observation in ordered)
        if indices != tuple(range(len(self.observation_references))):
            raise ValueError("observation indices do not match canonical source ordering")
        object.__setattr__(self, "observation_references", ordered)
        expected_round_identity = replay_round_identity(
            round_id=self.round_id,
            start_slot=self.start_slot,
            end_slot=self.end_slot,
            references=tuple(observation.reference for observation in ordered),
        )
        if self.round_identity != expected_round_identity:
            raise ValueError("round identity does not reconstruct from Replay authority")
        selected_reference = _select_reference(self)
        if selected_reference is None:
            if (
                self.selected_observation is not None
                or self.selected_source_projection_binding is not None
            ):
                raise ValueError(
                    "scientific state or source binding exists without an eligible "
                    "selected reference"
                )
            object.__setattr__(
                self, "selected_reference_science_binding_identity", None
            )
        else:
            if not isinstance(self.selected_observation, DecisionObservation):
                raise ValueError("selected reference lacks selected scientific authority")
            if not isinstance(
                self.selected_source_projection_binding,
                SelectedSourceProjectionBinding,
            ):
                raise ValueError(
                    "selected reference lacks upstream-authentication dependency"
                )
            selected = self.selected_observation
            source_binding = self.selected_source_projection_binding
            if (
                selected.reference.to_material()
                != selected_reference.reference.to_material()
                or selected.observation_index != selected_reference.observation_index
                or selected.valid_normal_observation
                != selected_reference.valid_normal_observation
            ):
                raise ValueError("selected reference/scientific authority mismatch")
            if selected.snapshot.structural_round_key != self.round_id:
                raise ValueError("selected observation round authority does not match Replay round")
            expected_selected_decision_identity = identity(
                _SELECTED_DECISION_IDENTITY_DOMAIN,
                {
                    "decision_selection_identity": (
                        EXPERIMENT5_DECISION_SELECTION_IDENTITY
                    ),
                    "fundamental_measurement_vector_identities": (
                        selected.measurement_vector_identities
                    ),
                    "replay_source_unit_identity": (
                        source_binding.replay_source_unit_identity
                    ),
                    "round_identity": self.round_identity,
                    "selected_observation_index": selected.observation_index,
                    "selected_reference_identity": (
                        selected.reference.reference_identity
                    ),
                    "selected_snapshot_identity": selected.decision_snapshot_identity,
                },
            )
            expected_parsed_record_identity = identity(
                _SELECTED_SOURCE_PARSED_RECORD_IDENTITY_DOMAIN,
                {
                    "reference": selected.reference.to_material(),
                    "snapshot": selected.snapshot.to_identity_material(),
                    "valid_normal_observation": (
                        selected.valid_normal_observation
                    ),
                },
            )
            source_binding_checks = {
                "canonical parsed record identity": (
                    source_binding.canonical_parsed_record_identity
                    == expected_parsed_record_identity
                ),
                "fundamental MeasurementVector identities": (
                    source_binding.fundamental_measurement_vector_identities
                    == selected.measurement_vector_identities
                ),
                "source file": (
                    source_binding.source_file
                    == selected.reference.source_file
                ),
                "observation index": (
                    source_binding.selected_observation_index
                    == selected.observation_index
                ),
                "observation timestamp": (
                    source_binding.observed_at_utc == selected.observed_at_utc
                ),
                "protocol revision": (
                    source_binding.protocol_revision == self.protocol_revision
                ),
                "Replay decision identity": (
                    source_binding.selected_decision_identity
                    == expected_selected_decision_identity
                ),
                "RPC slot": source_binding.rpc_slot == selected.rpc_slot,
                "selected reference identity": (
                    source_binding.selected_reference_identity
                    == selected.reference.reference_identity
                ),
                "selected snapshot identity": (
                    source_binding.selected_snapshot_identity
                    == selected.decision_snapshot_identity
                ),
                "source line": (
                    source_binding.source_line_number
                    == selected.reference.source_line_number
                ),
                "source schema version": (
                    source_binding.source_schema_version
                    in self.source_schema_versions
                ),
                "valid-normal status": (
                    source_binding.valid_normal_observation
                    == selected.valid_normal_observation
                ),
            }
            if source_binding.collector_session_id is not None:
                source_binding_checks["collector session"] = (
                    source_binding.collector_session_id in self.collector_session_ids
                )
            mismatches = tuple(
                name for name, matches in source_binding_checks.items() if not matches
            )
            if mismatches:
                raise ValueError(
                    "selected-source projection binding mismatch: "
                    + ", ".join(mismatches)
                )
            object.__setattr__(
                self,
                "selected_reference_science_binding_identity",
                identity(
                    "rq003-experiment-005-selected-reference-science-binding-v1",
                    {
                        "fundamental_measurement_vector_identities": (
                            selected.measurement_vector_identities
                        ),
                        "observation_index": selected.observation_index,
                        "reference_identity": selected.reference.reference_identity,
                        "selected_decision_snapshot_identity": (
                            selected.decision_snapshot_identity
                        ),
                    },
                ),
            )

    def audit_material(self) -> dict[str, object]:
        return {
            "collector_session_count": self.collector_session_count,
            "collector_session_ids": self.collector_session_ids,
            "end_slot": self.end_slot,
            "lifecycle_status": self.lifecycle_status,
            "max_observation_gap_seconds": self.max_observation_gap_seconds,
            "observation_count": self.observation_count,
            "protocol_revision": self.protocol_revision,
            "round_id": self.round_id,
            "round_identity": self.round_identity,
            "significant_gap_count": self.significant_gap_count,
            "significant_gap_threshold_seconds": self.significant_gap_threshold_seconds,
            "source_schema_versions": self.source_schema_versions,
            "start_slot": self.start_slot,
        }

    def source_reference_material(self) -> tuple[dict[str, object], ...]:
        return tuple(
            observation.reference.to_material()
            for observation in self.observation_references
        )

    def to_material(self) -> dict[str, object]:
        return {
            **self.audit_material(),
            "observation_references": tuple(
                observation.to_material() for observation in self.observation_references
            ),
            "selected_decision_scientific_material": (
                self.selected_observation.to_material()
                if self.selected_observation is not None
                else None
            ),
            "selected_source_projection_binding": (
                self.selected_source_projection_binding.to_material()
                if self.selected_source_projection_binding is not None
                else None
            ),
            "selected_reference_science_binding_identity": (
                self.selected_reference_science_binding_identity
            ),
        }

    @classmethod
    def from_material(cls, material: object) -> RankingRoundInput:
        fields = {item.name for item in cls.__dataclass_fields__.values() if item.init}
        material_fields = (
            fields - {"selected_observation", "selected_source_projection_binding"}
        ) | {
            "selected_decision_scientific_material",
            "selected_source_projection_binding",
            "selected_reference_science_binding_identity",
        }
        if not isinstance(material, Mapping) or set(material) != material_fields:
            raise ValueError("ranking round input material is not closed")
        references = material["observation_references"]
        if not isinstance(references, tuple):
            raise ValueError("ranking round references are not canonical")
        kwargs = {
            name: material[name]
            for name in fields
            if name
            not in {"selected_observation", "selected_source_projection_binding"}
        }
        kwargs["observation_references"] = tuple(
            DecisionObservationReference.from_material(value) for value in references
        )
        scientific = material["selected_decision_scientific_material"]
        kwargs["selected_observation"] = (
            DecisionObservation.from_material(scientific)
            if scientific is not None
            else None
        )
        source_binding = material["selected_source_projection_binding"]
        kwargs["selected_source_projection_binding"] = (
            SelectedSourceProjectionBinding.from_material(source_binding)
            if source_binding is not None
            else None
        )
        result = cls(**kwargs)
        if result.to_material() != material:
            raise ValueError("ranking round authority does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class CandidateRanking:
    candidate_square: int
    deployed_lamports: int
    miner_count: int
    share_imbalance: SignedRational
    deployment_per_miner: CanonicalRational
    measurement_vector_identity: str
    measurement_vector_canonical_hex: str
    primary_average_rank: float
    ascending_sensitivity_average_rank: float
    deployment_per_miner_average_rank: float
    deterministic_baseline_rank: int
    seeded_random_baseline_rank: int
    primary_tie_group_size: int
    deployment_per_miner_tie_group_size: int

    def __post_init__(self) -> None:
        if self.candidate_square not in EXPERIMENT5_CANDIDATES:
            raise ValueError("candidate square is outside 0..24")
        _require_int("deployed_lamports", self.deployed_lamports)
        _require_int("miner_count", self.miner_count)
        require_sha256("measurement_vector_identity", self.measurement_vector_identity)
        if not isinstance(self.measurement_vector_canonical_hex, str):
            raise TypeError("measurement_vector_canonical_hex must be text")
        try:
            raw = bytes.fromhex(self.measurement_vector_canonical_hex)
        except ValueError as exc:
            raise ValueError("measurement vector canonical hex is invalid") from exc
        vector = MeasurementVector.from_canonical_bytes(raw)
        if (
            vector.vector_identity != self.measurement_vector_identity
            or vector.structural_candidate_key != self.candidate_square
        ):
            raise ValueError("candidate MeasurementVector identity does not reconstruct")
        deployed_index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("deployed_lamports")
        miner_index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("miner_count")
        if (
            vector.ordered_values[deployed_index] != self.deployed_lamports
            or vector.ordered_values[miner_index] != self.miner_count
        ):
            raise ValueError("candidate fundamental values do not reconstruct")
        for name in (
            "primary_average_rank",
            "ascending_sensitivity_average_rank",
            "deployment_per_miner_average_rank",
        ):
            value = getattr(self, name)
            if not isinstance(value, float) or not 1.0 <= value <= 25.0:
                raise ValueError(f"{name} is invalid")
        for name in ("deterministic_baseline_rank", "seeded_random_baseline_rank"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 25:
                raise ValueError(f"{name} is invalid")
        for name in ("primary_tie_group_size", "deployment_per_miner_tie_group_size"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 25:
                raise ValueError(f"{name} is invalid")

    def to_material(self) -> dict[str, object]:
        return {
            "ascending_sensitivity_average_rank": self.ascending_sensitivity_average_rank,
            "candidate_square": self.candidate_square,
            "deployed_lamports": self.deployed_lamports,
            "deployment_per_miner": self.deployment_per_miner.to_dict(),
            "deployment_per_miner_average_rank": self.deployment_per_miner_average_rank,
            "deployment_per_miner_tie_group_size": self.deployment_per_miner_tie_group_size,
            "deterministic_baseline_rank": self.deterministic_baseline_rank,
            "measurement_vector_identity": self.measurement_vector_identity,
            "measurement_vector_canonical_hex": self.measurement_vector_canonical_hex,
            "miner_count": self.miner_count,
            "primary_average_rank": self.primary_average_rank,
            "primary_tie_group_size": self.primary_tie_group_size,
            "seeded_random_baseline_rank": self.seeded_random_baseline_rank,
            "signed_share_imbalance": self.share_imbalance.to_material(),
        }

    @classmethod
    def from_material(cls, material: object) -> CandidateRanking:
        if not isinstance(material, dict) or set(material) != {
            "ascending_sensitivity_average_rank",
            "candidate_square",
            "deployed_lamports",
            "deployment_per_miner",
            "deployment_per_miner_average_rank",
            "deployment_per_miner_tie_group_size",
            "deterministic_baseline_rank",
            "measurement_vector_canonical_hex",
            "measurement_vector_identity",
            "miner_count",
            "primary_average_rank",
            "primary_tie_group_size",
            "seeded_random_baseline_rank",
            "signed_share_imbalance",
        }:
            raise ValueError("candidate ranking material is not closed")
        return cls(
            candidate_square=material["candidate_square"],
            deployed_lamports=material["deployed_lamports"],
            miner_count=material["miner_count"],
            share_imbalance=SignedRational.from_material(
                material["signed_share_imbalance"]
            ),
            deployment_per_miner=CanonicalRational.from_dict(
                material["deployment_per_miner"]
            ),
            measurement_vector_identity=material["measurement_vector_identity"],
            measurement_vector_canonical_hex=(
                material["measurement_vector_canonical_hex"]
            ),
            primary_average_rank=material["primary_average_rank"],
            ascending_sensitivity_average_rank=(
                material["ascending_sensitivity_average_rank"]
            ),
            deployment_per_miner_average_rank=(
                material["deployment_per_miner_average_rank"]
            ),
            deterministic_baseline_rank=material["deterministic_baseline_rank"],
            seeded_random_baseline_rank=material["seeded_random_baseline_rank"],
            primary_tie_group_size=material["primary_tie_group_size"],
            deployment_per_miner_tie_group_size=(
                material["deployment_per_miner_tie_group_size"]
            ),
        )


def _derive_ranked_science(
    round_input: RankingRoundInput,
) -> tuple[
    DecisionObservation | None,
    tuple[CandidateRanking, ...] | None,
    str | None,
    str | None,
]:
    """Derive every ranking-side scientific consequence from canonical roots."""

    selected = select_decision(round_input)
    if selected is None:
        return None, None, None, "no_predeclared_decision_observation"
    try:
        imbalance = share_imbalance(selected.deployed_lamports, selected.miner_counts)
    except ValueError as exc:
        reason = {
            "zero total deployed lamports": "zero_total_deployed_lamports",
            "zero total per-square Miner Count": "zero_total_miner_count",
        }.get(str(exc))
        if reason is None:
            raise
        return selected, None, None, reason
    ratios: list[CanonicalRational] = []
    for deployed, miners in zip(
        selected.deployed_lamports, selected.miner_counts, strict=True
    ):
        try:
            ratio, _empty_extension = deployment_per_miner(deployed, miners)
        except ValueError as exc:
            if str(exc) != "positive deployment with zero miners is invalid":
                raise
            return selected, None, None, "undefined_deployment_per_miner"
        ratios.append(ratio)
    ratio_values = tuple(ratios)
    primary_ranks = average_ranks(imbalance, descending=True)
    ascending_ranks = average_ranks(imbalance, descending=False)
    comparator_ranks = average_ranks(ratio_values, descending=True)
    random_ranks = seeded_random_ranks(selected.decision_snapshot_identity)
    primary_ties = tie_group_sizes(imbalance)
    comparator_ties = tie_group_sizes(ratio_values)
    share_measurement_identity = identity(
        _SHARE_IMBALANCE_MEASUREMENT_IDENTITY_DOMAIN,
        {
            "candidate_order": EXPERIMENT5_CANDIDATES,
            "decision_snapshot_identity": selected.decision_snapshot_identity,
            "definition_identity": EXPERIMENT5_SHARE_IMBALANCE_DEFINITION_IDENTITY,
            "fundamental_measurement_vector_identities": (
                selected.measurement_vector_identities
            ),
            "values": tuple(value.to_material() for value in imbalance),
        },
    )
    candidates = tuple(
        CandidateRanking(
            candidate_square=square,
            deployed_lamports=selected.deployed_lamports[square],
            miner_count=selected.miner_counts[square],
            share_imbalance=imbalance[square],
            deployment_per_miner=ratio_values[square],
            measurement_vector_identity=selected.measurement_vector_identities[square],
            measurement_vector_canonical_hex=(
                selected.measurement_vector_bytes[square].hex()
            ),
            primary_average_rank=primary_ranks[square],
            ascending_sensitivity_average_rank=ascending_ranks[square],
            deployment_per_miner_average_rank=comparator_ranks[square],
            deterministic_baseline_rank=square + 1,
            seeded_random_baseline_rank=random_ranks[square],
            primary_tie_group_size=primary_ties[square],
            deployment_per_miner_tie_group_size=comparator_ties[square],
        )
        for square in EXPERIMENT5_CANDIDATES
    )
    return selected, candidates, share_measurement_identity, None


@dataclass(frozen=True, slots=True)
class RankingRecord:
    round_input_material: Mapping[str, object]
    round_identity: str
    round_id: int
    start_slot: int
    end_slot: int
    observation_index: int
    selected_rpc_slot: int
    decision_distance_slots: int
    decision_snapshot_identity: str
    decision_snapshot_material: dict[str, object]
    selected_reference_identity: str
    source_references: tuple[dict[str, object], ...]
    share_imbalance_measurement_identity: str
    lifecycle_status: str
    observation_count: int
    significant_gap_count: int
    max_observation_gap_seconds: float
    significant_gap_threshold_seconds: float
    collector_session_ids: tuple[str, ...]
    collector_session_count: int
    source_schema_versions: tuple[int, ...]
    protocol_revision: str
    candidates: tuple[CandidateRanking, ...]
    temporal_isolation_validated: bool = field(init=False, compare=False)
    ranking_record_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        frozen_round_input = immutable_material(self.round_input_material)
        if not isinstance(frozen_round_input, Mapping):
            raise TypeError("round_input_material must be a canonical mapping")
        frozen_snapshot = immutable_material(self.decision_snapshot_material)
        if not isinstance(frozen_snapshot, Mapping):
            raise TypeError("decision_snapshot_material must be a canonical mapping")
        frozen_references = immutable_material(self.source_references)
        if not isinstance(frozen_references, tuple):
            raise TypeError("source_references must be a canonical sequence")
        object.__setattr__(self, "round_input_material", frozen_round_input)
        object.__setattr__(self, "decision_snapshot_material", frozen_snapshot)
        object.__setattr__(self, "source_references", frozen_references)
        round_input = RankingRoundInput.from_material(self.round_input_material)
        selected, expected_candidates, expected_share_identity, exclusion_reason = (
            _derive_ranked_science(round_input)
        )
        if selected is None or expected_candidates is None or exclusion_reason is not None:
            raise ValueError("ranking record root authority derives an exclusion")
        require_sha256("round_identity", self.round_identity)
        require_sha256("decision_snapshot_identity", self.decision_snapshot_identity)
        reconstructed_snapshot = DecisionSnapshotAuthority.from_material(
            self.decision_snapshot_material
        )
        if reconstructed_snapshot.decision_snapshot_identity != self.decision_snapshot_identity:
            raise ValueError("decision snapshot material does not bind its identity")
        require_sha256("selected_reference_identity", self.selected_reference_identity)
        require_sha256(
            "share_imbalance_measurement_identity",
            self.share_imbalance_measurement_identity,
        )
        if not isinstance(self.source_references, tuple):
            raise TypeError("source_references must be an immutable tuple")
        reconstructed_references = tuple(
            ObservationReferenceAuthority.from_material(material)
            for material in self.source_references
        )
        expected_references = round_input.source_reference_material()
        if self.source_references != expected_references:
            raise ValueError("source-reference authority does not reconstruct")
        expected_audit = round_input.audit_material()
        for name, value in expected_audit.items():
            if getattr(self, name) != value:
                raise ValueError(f"ranking audit field does not reconstruct: {name}")
        if self.round_identity != replay_round_identity(
            round_id=self.round_id,
            start_slot=self.start_slot,
            end_slot=self.end_slot,
            references=reconstructed_references,
        ):
            raise ValueError("ranking round identity does not reconstruct")
        selected_expectations = {
            "observation_index": selected.observation_index,
            "selected_rpc_slot": selected.rpc_slot,
            "decision_distance_slots": (round_input.end_slot - 5) - selected.rpc_slot,
            "decision_snapshot_identity": selected.decision_snapshot_identity,
            "selected_reference_identity": selected.reference.reference_identity,
        }
        for name, value in selected_expectations.items():
            if getattr(self, name) != value:
                raise ValueError(f"selected decision field does not reconstruct: {name}")
        if self.decision_snapshot_material != selected.snapshot.to_identity_material():
            raise ValueError("selected decision snapshot does not reconstruct")
        if self.protocol_revision != EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION:
            raise ValueError("ranking record revision is unsupported")
        if tuple(candidate.to_material() for candidate in self.candidates) != tuple(
            candidate.to_material() for candidate in expected_candidates
        ):
            raise ValueError("derived ranking science does not reconstruct")
        if self.share_imbalance_measurement_identity != expected_share_identity:
            raise ValueError("derived Share-Imbalance authority does not reconstruct")
        material = self.to_identity_material()
        _reject_forbidden_ranking_keys(material)
        object.__setattr__(self, "temporal_isolation_validated", True)
        object.__setattr__(
            self,
            "ranking_record_identity",
            identity(_RANKING_RECORD_IDENTITY_DOMAIN, material),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "candidates": tuple(candidate.to_material() for candidate in self.candidates),
            "collector_session_count": self.collector_session_count,
            "collector_session_ids": self.collector_session_ids,
            "decision_distance_slots": self.decision_distance_slots,
            "decision_snapshot_identity": self.decision_snapshot_identity,
            "decision_snapshot_material": self.decision_snapshot_material,
            "end_slot": self.end_slot,
            "lifecycle_status": self.lifecycle_status,
            "max_observation_gap_seconds": self.max_observation_gap_seconds,
            "observation_count": self.observation_count,
            "observation_index": self.observation_index,
            "protocol_revision": self.protocol_revision,
            "round_id": self.round_id,
            "round_identity": self.round_identity,
            "round_input_material": self.round_input_material,
            "selected_rpc_slot": self.selected_rpc_slot,
            "selected_reference_identity": self.selected_reference_identity,
            "share_imbalance_measurement_identity": (
                self.share_imbalance_measurement_identity
            ),
            "significant_gap_count": self.significant_gap_count,
            "significant_gap_threshold_seconds": self.significant_gap_threshold_seconds,
            "source_schema_versions": self.source_schema_versions,
            "source_references": self.source_references,
            "start_slot": self.start_slot,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "ranking_record_identity": self.ranking_record_identity,
        }

    @classmethod
    def from_material(cls, material: object) -> RankingRecord:
        if not isinstance(material, dict):
            raise ValueError("ranking record material must be a mapping")
        identity_value = material.get("ranking_record_identity")
        candidates = material.get("candidates")
        if not isinstance(candidates, tuple):
            raise ValueError("ranking record candidates must be canonical")
        fields = {field.name for field in cls.__dataclass_fields__.values() if field.init}
        if set(material) != fields | {"ranking_record_identity"}:
            raise ValueError("ranking record material is not closed")
        kwargs = {name: material[name] for name in fields}
        kwargs["candidates"] = tuple(
            CandidateRanking.from_material(candidate) for candidate in candidates
        )
        result = cls(**kwargs)
        if result.ranking_record_identity != identity_value or result.to_material() != material:
            raise ValueError("ranking record identity does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class RankingExclusion:
    round_input_material: Mapping[str, object]
    round_identity: str
    round_id: int
    start_slot: int
    end_slot: int
    protocol_revision: str
    observation_count: int
    source_references: tuple[dict[str, object], ...]
    reason: str
    temporal_isolation_validated: bool = field(init=False, compare=False)
    exclusion_identity: str = field(init=False)

    def __post_init__(self) -> None:
        frozen_round_input = immutable_material(self.round_input_material)
        frozen_references = immutable_material(self.source_references)
        if not isinstance(frozen_round_input, Mapping) or not isinstance(
            frozen_references, tuple
        ):
            raise TypeError("exclusion root authority is not canonical")
        object.__setattr__(self, "round_input_material", frozen_round_input)
        object.__setattr__(self, "source_references", frozen_references)
        round_input = RankingRoundInput.from_material(self.round_input_material)
        _selected, expected_candidates, _share_identity, expected_reason = (
            _derive_ranked_science(round_input)
        )
        if expected_candidates is not None or expected_reason is None:
            raise ValueError("ranking exclusion root authority derives a ranked record")
        require_sha256("round_identity", self.round_identity)
        if self.protocol_revision != EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION:
            raise ValueError("excluded round revision is unsupported")
        _require_int("observation_count", self.observation_count)
        references = tuple(
            ObservationReferenceAuthority.from_material(value)
            for value in self.source_references
        )
        if len(references) != self.observation_count:
            raise ValueError("excluded source-reference count does not reconcile")
        if self.source_references != round_input.source_reference_material():
            raise ValueError("excluded source-reference authority does not reconstruct")
        for name in (
            "round_identity",
            "round_id",
            "start_slot",
            "end_slot",
            "protocol_revision",
            "observation_count",
        ):
            if getattr(self, name) != getattr(round_input, name):
                raise ValueError(f"excluded audit field does not reconstruct: {name}")
        if self.reason != expected_reason:
            raise ValueError("ranking exclusion reason does not reconstruct")
        if self.reason not in {
            "no_predeclared_decision_observation",
            "undefined_deployment_per_miner",
            "zero_total_deployed_lamports",
            "zero_total_miner_count",
        }:
            raise ValueError("ranking exclusion reason is not governed")
        object.__setattr__(self, "temporal_isolation_validated", True)
        object.__setattr__(
            self,
            "exclusion_identity",
            identity(_RANKING_EXCLUSION_IDENTITY_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "reason": self.reason,
            "end_slot": self.end_slot,
            "observation_count": self.observation_count,
            "protocol_revision": self.protocol_revision,
            "round_id": self.round_id,
            "round_identity": self.round_identity,
            "round_input_material": self.round_input_material,
            "source_references": self.source_references,
            "start_slot": self.start_slot,
        }

    def to_material(self) -> dict[str, object]:
        return {**self.to_identity_material(), "exclusion_identity": self.exclusion_identity}

    @classmethod
    def from_material(cls, material: object) -> RankingExclusion:
        fields = {item.name for item in cls.__dataclass_fields__.values() if item.init}
        if not isinstance(material, dict) or set(material) != fields | {"exclusion_identity"}:
            raise ValueError("ranking exclusion material is not closed")
        result = cls(**{name: material[name] for name in fields})
        if result.to_material() != material:
            raise ValueError("ranking exclusion identity does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class RankingArtifact:
    records: tuple[RankingRecord, ...]
    exclusions: tuple[RankingExclusion, ...]
    ranking_artifact_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        all_rounds = tuple(
            (item.start_slot, item.round_id)
            for item in (*self.records, *self.exclusions)
        )
        if len(all_rounds) != len(set(all_rounds)):
            raise ValueError("ranking population contains duplicate rounds")
        round_identities = tuple(
            item.round_identity for item in (*self.records, *self.exclusions)
        )
        if len(round_identities) != len(set(round_identities)):
            raise ValueError("ranking population contains duplicate round identities")
        revisions = {
            item.protocol_revision for item in (*self.records, *self.exclusions)
        }
        if revisions != {EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION}:
            raise ValueError("ranking population pools protocol revisions")
        if tuple((item.start_slot, item.round_id) for item in self.records) != tuple(
            sorted((item.start_slot, item.round_id) for item in self.records)
        ):
            raise ValueError("ranking records are not chronologically ordered")
        if tuple((item.start_slot, item.round_id) for item in self.exclusions) != tuple(
            sorted((item.start_slot, item.round_id) for item in self.exclusions)
        ):
            raise ValueError("ranking exclusions are not chronologically ordered")
        material = self.to_identity_material()
        _reject_forbidden_ranking_keys(material)
        object.__setattr__(
            self,
            "ranking_artifact_identity",
            identity(_RANKING_ARTIFACT_IDENTITY_DOMAIN, material),
        )

    def to_identity_material(self) -> dict[str, object]:
        replay_order = tuple(
            item.round_identity
            for item in sorted(
                (*self.records, *self.exclusions),
                key=lambda item: (item.start_slot, item.round_id),
            )
        )
        replay_identity = identity(
            _REPLAY_IDENTITY_DOMAIN,
            {
                "dataset_sha256": EXPERIMENT5_DATASET_SHA256,
                "ordered_round_identities": replay_order,
                "protocol_revision_population_identity": (
                    EXPERIMENT5_PROTOCOL_REVISION_POPULATION_IDENTITY
                ),
            },
        )
        return {
            "authority": {
                "dataset_persisted_byte_identity": EXPERIMENT5_DATASET_SHA256,
                "dataset_schema_identity": EXPERIMENT5_DATASET_SCHEMA_IDENTITY,
                "decision_selection_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
                "feature_set_identity": EXPERIMENT5_FEATURE_SET_IDENTITY,
                "fundamental_measurement_pipeline_identity": (
                    RQ003_PIPELINE_IMPLEMENTATION_IDENTITY
                ),
                "procedure_identities": EXPERIMENT5_PROCEDURE_IDENTITIES,
                "protocol_revision_population_identity": (
                    EXPERIMENT5_PROTOCOL_REVISION_POPULATION_IDENTITY
                ),
                "replay_identity": replay_identity,
                "share_imbalance_definition_identity": (
                    EXPERIMENT5_SHARE_IMBALANCE_DEFINITION_IDENTITY
                ),
            },
            "candidate_order": EXPERIMENT5_CANDIDATES,
            "experiment_identifier": EXPERIMENT5_IDENTIFIER,
            "exclusions": tuple(item.to_material() for item in self.exclusions),
            "information_flow": "outcome_blind",
            "population_accounting": {
                "excluded_round_count": len(self.exclusions),
                "ranked_round_count": len(self.records),
                "replay_round_count": len(self.records) + len(self.exclusions),
            },
            "ordered_replay_round_identities": replay_order,
            "protocol_sha256": EXPERIMENT5_PROTOCOL_SHA256,
            "ranking_audits": {
                "deterministic_reconstruction": "pass",
                "fundamental_measurement_conformance": "pass",
                "future_information_excluded": all(
                    item.temporal_isolation_validated
                    for item in (*self.records, *self.exclusions)
                ),
                "outcome_fields_excluded": True,
                "procedure_population_parity": "pass",
                "selected_source_projection_contract_reconstruction": "pass",
                "source_reference_reconstruction": "pass",
                "upstream_authentication_dependency": (
                    "bound_not_independently_authenticated_by_slice1"
                ),
            },
            "ranking_records": tuple(item.to_material() for item in self.records),
            "schema_version": 1,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "ranking_artifact_identity": self.ranking_artifact_identity,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_encode(self.to_material())

    @classmethod
    def from_material(cls, material: object) -> RankingArtifact:
        if not isinstance(material, dict) or set(material) != {
            "authority", "candidate_order", "experiment_identifier", "exclusions",
            "information_flow", "ordered_replay_round_identities",
            "population_accounting", "protocol_sha256", "ranking_artifact_identity",
            "ranking_audits", "ranking_records", "schema_version",
        }:
            raise ValueError("ranking artifact material is not closed")
        records = material["ranking_records"]
        exclusions = material["exclusions"]
        if not isinstance(records, tuple) or not isinstance(exclusions, tuple):
            raise ValueError("ranking artifact populations must be canonical sequences")
        result = cls(
            records=tuple(RankingRecord.from_material(value) for value in records),
            exclusions=tuple(RankingExclusion.from_material(value) for value in exclusions),
        )
        if result.to_material() != material:
            raise ValueError("ranking artifact authority does not reconstruct")
        return result

    @classmethod
    def from_canonical_bytes(cls, raw: bytes) -> RankingArtifact:
        result = cls.from_material(canonical_decode(raw))
        if result.canonical_bytes() != raw:
            raise ValueError("ranking artifact bytes are not canonical")
        return result


def _reject_forbidden_ranking_keys(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key.casefold() in _FORBIDDEN_RANKING_KEYS:
                raise ValueError(f"ranking material contains prohibited field: {key}")
            _reject_forbidden_ranking_keys(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _reject_forbidden_ranking_keys(item)


def replay_round_identity(
    *,
    round_id: int,
    start_slot: int,
    end_slot: int,
    references: Sequence[ObservationReferenceAuthority],
) -> str:
    """Reconstruct the Experiment 3/4-style first-order Replay round identity."""

    return identity(
        _REPLAY_ROUND_IDENTITY_DOMAIN,
        {
            "end_slot": end_slot,
            "observation_count": len(references),
            "observation_references": tuple(
                {
                    "observed_at_utc": reference.observed_at_utc.isoformat(),
                    "rpc_slot": reference.rpc_slot,
                    "source_file": reference.source_file,
                    "source_line_number": reference.source_line_number,
                }
                for reference in references
            ),
            "round_id": round_id,
            "start_slot": start_slot,
        },
    )
def select_decision(round_input: RankingRoundInput) -> DecisionObservation | None:
    """Select closest RPC slot at or before ``end_slot - 5``; latest tie wins."""

    selected_reference = _select_reference(round_input)
    if selected_reference is None:
        return None
    selected = round_input.selected_observation
    if selected is None:
        raise RuntimeError("selected reference lacks validated scientific authority")
    return selected


def _select_reference(
    round_input: RankingRoundInput,
) -> DecisionObservationReference | None:
    """Select from the complete reference-only Replay graph."""

    target_slot = round_input.end_slot - 5
    eligible = tuple(
        observation
        for observation in round_input.observation_references
        if observation.valid_normal_observation
        and observation.reference.rpc_slot <= target_slot
    )
    if not eligible:
        return None
    best_rpc_slot = max(observation.reference.rpc_slot for observation in eligible)
    return tuple(
        observation
        for observation in eligible
        if observation.reference.rpc_slot == best_rpc_slot
    )[-1]


def _exclusion(round_input: RankingRoundInput, reason: str) -> RankingExclusion:
    return RankingExclusion(
        round_input_material=round_input.to_material(),
        round_identity=round_input.round_identity,
        round_id=round_input.round_id,
        start_slot=round_input.start_slot,
        end_slot=round_input.end_slot,
        protocol_revision=round_input.protocol_revision,
        observation_count=round_input.observation_count,
        source_references=round_input.source_reference_material(),
        reason=reason,
    )


def rank_round(
    round_input: RankingRoundInput,
) -> RankingRecord | RankingExclusion:
    """Construct one closed outcome-blind ranking record or governed exclusion."""

    selected, candidates, share_measurement_identity, exclusion_reason = (
        _derive_ranked_science(round_input)
    )
    if exclusion_reason is not None:
        return _exclusion(round_input, exclusion_reason)
    if selected is None or candidates is None or share_measurement_identity is None:
        raise RuntimeError("ranked derivation returned an impossible state")
    return RankingRecord(
        round_input_material=round_input.to_material(),
        **round_input.audit_material(),
        observation_index=selected.observation_index,
        selected_rpc_slot=selected.rpc_slot,
        decision_distance_slots=(round_input.end_slot - 5) - selected.rpc_slot,
        decision_snapshot_identity=selected.decision_snapshot_identity,
        decision_snapshot_material=selected.snapshot.to_identity_material(),
        selected_reference_identity=selected.reference.reference_identity,
        source_references=round_input.source_reference_material(),
        share_imbalance_measurement_identity=share_measurement_identity,
        candidates=candidates,
    )


def construct_ranking_artifact(
    rounds: Sequence[RankingRoundInput],
) -> RankingArtifact:
    """Rank one canonical chronological Replay population."""

    if not rounds:
        raise ValueError("ranking population cannot be empty")
    ordered = tuple(rounds)
    if tuple((item.start_slot, item.round_id) for item in ordered) != tuple(
        sorted((item.start_slot, item.round_id) for item in ordered)
    ):
        raise ValueError("Replay rounds are not in canonical chronology")
    results = tuple(rank_round(item) for item in ordered)
    records = tuple(item for item in results if isinstance(item, RankingRecord))
    exclusions = tuple(item for item in results if isinstance(item, RankingExclusion))
    return RankingArtifact(records=records, exclusions=exclusions)


__all__ = (
    "CandidateRanking",
    "DecisionObservation",
    "DecisionObservationReference",
    "DecisionSnapshotAuthority",
    "ObservationReferenceAuthority",
    "RankingArtifact",
    "RankingExclusion",
    "RankingRecord",
    "RankingRoundInput",
    "SelectedSourceProjectionBinding",
    "construct_ranking_artifact",
    "rank_round",
    "replay_round_identity",
    "select_decision",
)
