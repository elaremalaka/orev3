"""Deterministic, outcome-free RQ-003 Experiment 0 generation.

Experiment 0 proves that Replay-selected decision points can traverse the
complete fundamental Measurement Library. It creates no derived measurement,
feature set, label, ranking, Strategy action, evaluation, or economic result.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orev3.features.rq003_active_round_motherlode import (
    ACTIVE_ROUND_MOTHERLODE_DEFINITION,
    ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION,
    ACTIVE_ROUND_MOTHERLODE_MEASUREMENT,
    ACTIVE_ROUND_MOTHERLODE_PROTOCOL_SOURCE_REVISION,
    validate_active_round_motherlode_definition,
)
from orev3.features.rq003_contracts import canonical_encode
from orev3.features.rq003_deployed_lamports import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION,
    validate_deployed_lamports_definition,
)
from orev3.features.rq003_execution import (
    ExecutableMeasurementBinding,
    MeasurementVector,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
)
from orev3.features.rq003_miner_count import (
    MINER_COUNT_DEFINITION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_MEASUREMENT,
    MINER_COUNT_PROTOCOL_SOURCE_REVISION,
    validate_miner_count_definition,
)
from orev3.features.rq003_production_cost_ema import (
    PRODUCTION_COST_EMA_DEFINITION,
    PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    PRODUCTION_COST_EMA_MEASUREMENT,
    PRODUCTION_COST_EMA_PROTOCOL_SOURCE_REVISION,
    validate_production_cost_ema_definition,
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
    TOTAL_MINERS_PROTOCOL_SOURCE_REVISION,
    validate_total_miners_definition,
)
from orev3.features.rq003_total_vaulted import (
    TOTAL_VAULTED_DEFINITION,
    TOTAL_VAULTED_ELIGIBILITY_DECISION,
    TOTAL_VAULTED_MEASUREMENT,
    TOTAL_VAULTED_PROTOCOL_SOURCE_REVISION,
    validate_total_vaulted_definition,
)
from orev3.features.rq003_total_winnings import (
    TOTAL_WINNINGS_DEFINITION,
    TOTAL_WINNINGS_ELIGIBILITY_DECISION,
    TOTAL_WINNINGS_MEASUREMENT,
    TOTAL_WINNINGS_PROTOCOL_SOURCE_REVISION,
    validate_total_winnings_definition,
)
from orev3.features.rq003_treasury_motherlode import (
    TREASURY_MOTHERLODE_DEFINITION,
    TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    TREASURY_MOTHERLODE_MEASUREMENT,
    TREASURY_MOTHERLODE_PROTOCOL_SOURCE_REVISION,
    validate_treasury_motherlode_definition,
)
from orev3.historical.models import RoundLifecycleIndexRecord
from orev3.replay.engine import select_by_slots_remaining
from orev3.replay.loader import load_round_index
from orev3.strategy_lab.runner import decision_context_from_replay_point


RQ003_EXPERIMENT0_SCHEMA_VERSION = 1
RQ003_EXPERIMENT0_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)
RQ003_EXPERIMENT0_OUTPUT_NAMES = (
    "deployed_lamports",
    "miner_count",
    "total_miners",
    "board_production_cost_ema",
    "active_round_motherlode",
    "treasury_motherlode",
    "pre_finalization_total_vaulted",
    "pre_finalization_total_winnings",
)

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_DECISION_CONFIGURATION_IDENTITY_DOMAIN = (
    "rq003-experiment0-decision-configuration-v1"
)

_DEFINITIONS = (
    DEPLOYED_LAMPORTS_DEFINITION,
    MINER_COUNT_DEFINITION,
    TOTAL_MINERS_DEFINITION,
    PRODUCTION_COST_EMA_DEFINITION,
    ACTIVE_ROUND_MOTHERLODE_DEFINITION,
    TREASURY_MOTHERLODE_DEFINITION,
    TOTAL_VAULTED_DEFINITION,
    TOTAL_WINNINGS_DEFINITION,
)
_DECISIONS = (
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    TOTAL_MINERS_ELIGIBILITY_DECISION,
    PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION,
    TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    TOTAL_VAULTED_ELIGIBILITY_DECISION,
    TOTAL_WINNINGS_ELIGIBILITY_DECISION,
)
_COMPUTATIONS = (
    DEPLOYED_LAMPORTS_MEASUREMENT,
    MINER_COUNT_MEASUREMENT,
    TOTAL_MINERS_MEASUREMENT,
    PRODUCTION_COST_EMA_MEASUREMENT,
    ACTIVE_ROUND_MOTHERLODE_MEASUREMENT,
    TREASURY_MOTHERLODE_MEASUREMENT,
    TOTAL_VAULTED_MEASUREMENT,
    TOTAL_WINNINGS_MEASUREMENT,
)
_DEFINITION_VALIDATORS = (
    validate_deployed_lamports_definition,
    validate_miner_count_definition,
    validate_total_miners_definition,
    validate_production_cost_ema_definition,
    validate_active_round_motherlode_definition,
    validate_treasury_motherlode_definition,
    validate_total_vaulted_definition,
    validate_total_winnings_definition,
)
_PROTOCOL_SOURCE_REVISIONS = (
    DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION,
    MINER_COUNT_PROTOCOL_SOURCE_REVISION,
    TOTAL_MINERS_PROTOCOL_SOURCE_REVISION,
    PRODUCTION_COST_EMA_PROTOCOL_SOURCE_REVISION,
    ACTIVE_ROUND_MOTHERLODE_PROTOCOL_SOURCE_REVISION,
    TREASURY_MOTHERLODE_PROTOCOL_SOURCE_REVISION,
    TOTAL_VAULTED_PROTOCOL_SOURCE_REVISION,
    TOTAL_WINNINGS_PROTOCOL_SOURCE_REVISION,
)


@dataclass(frozen=True, slots=True)
class RQ003Experiment0Configuration:
    """Immutable selection and output configuration for Experiment 0."""

    replay_dataset_path: Path
    output_path: Path
    requested_slots_remaining: int
    max_slot_distance: int | None = None
    decision_point_configuration_identity: str = field(init=False)

    def __post_init__(self) -> None:
        replay_path = Path(self.replay_dataset_path)
        output_path = Path(self.output_path)
        if replay_path.resolve() == output_path.resolve():
            raise ValueError("output_path must not replace the replay dataset")
        _require_nonnegative_integer(
            "requested_slots_remaining", self.requested_slots_remaining
        )
        if self.max_slot_distance is not None:
            _require_nonnegative_integer(
                "max_slot_distance", self.max_slot_distance
            )
        object.__setattr__(self, "replay_dataset_path", replay_path)
        object.__setattr__(self, "output_path", output_path)
        object.__setattr__(
            self,
            "decision_point_configuration_identity",
            _identity(
                _DECISION_CONFIGURATION_IDENTITY_DOMAIN,
                {
                    "candidate_order": tuple(range(25)),
                    "lifecycle_order": ("start_slot", "round_id"),
                    "max_slot_distance": self.max_slot_distance,
                    "requested_slots_remaining": (
                        self.requested_slots_remaining
                    ),
                    "selection_rule": "latest_observation_at_or_before_slot",
                },
            ),
        )


@dataclass(frozen=True, slots=True)
class RQ003Experiment0Record:
    """One candidate's outcome-free fundamental measurement record."""

    decision_identity: str
    candidate_square: int
    measurement_vector_identity: str
    ordered_fundamental_measurement_values: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_sha256("decision_identity", self.decision_identity)
        _require_candidate_square(self.candidate_square)
        _require_sha256(
            "measurement_vector_identity", self.measurement_vector_identity
        )
        values = self.ordered_fundamental_measurement_values
        if not isinstance(values, tuple):
            raise TypeError(
                "ordered_fundamental_measurement_values must be a tuple"
            )
        if len(values) != len(RQ003_EXPERIMENT0_OUTPUT_NAMES):
            raise ValueError("fundamental measurement value count is invalid")
        for index, value in enumerate(values):
            _require_u64(f"measurement value {index}", value)

    def to_canonical_json(self) -> str:
        return json.dumps(
            {
                "candidate_square": self.candidate_square,
                "decision_identity": self.decision_identity,
                "measurement_vector_identity": (
                    self.measurement_vector_identity
                ),
                "ordered_fundamental_measurement_values": list(
                    self.ordered_fundamental_measurement_values
                ),
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


@dataclass(frozen=True, slots=True)
class RQ003Experiment0Result:
    """Non-persisted deterministic summary of one completed generation."""

    output_path: Path
    decision_count: int
    record_count: int
    output_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", Path(self.output_path))
        _require_nonnegative_integer("decision_count", self.decision_count)
        _require_nonnegative_integer("record_count", self.record_count)
        if self.record_count != self.decision_count * 25:
            raise ValueError("record_count must equal decision_count times 25")
        _require_sha256("output_sha256", self.output_sha256)


def build_fundamental_measurement_pipeline() -> RQ003MeasurementPipeline:
    """Build the closed Measurement Library execution registry.

    Registry membership here is the complete fundamental library, not a
    research Feature Set selection.
    """

    _validate_protocol_dependencies()
    for validator in _DEFINITION_VALIDATORS:
        validator()
    if tuple(
        output.name
        for definition in _DEFINITIONS
        for output in definition.output_fields
    ) != RQ003_EXPERIMENT0_OUTPUT_NAMES:
        raise ValueError("fundamental measurement output order is invalid")
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


def generate_rq003_experiment0_dataset(
    configuration: RQ003Experiment0Configuration,
) -> RQ003Experiment0Result:
    """Atomically generate the outcome-free Experiment 0 JSONL dataset."""

    if not isinstance(configuration, RQ003Experiment0Configuration):
        raise TypeError("configuration must be RQ003Experiment0Configuration")
    pipeline = build_fundamental_measurement_pipeline()
    lifecycles = _load_chronological_lifecycles(
        configuration.replay_dataset_path
    )
    if not lifecycles:
        raise ValueError("replay dataset contains no decisions")
    destination = configuration.output_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    decision_count = 0
    record_count = 0
    try:
        with os.fdopen(
            file_descriptor, "w", encoding="utf-8", newline="\n"
        ) as handle:
            for lifecycle in lifecycles:
                selection = select_by_slots_remaining(
                    lifecycle,
                    requested_slots_remaining=(
                        configuration.requested_slots_remaining
                    ),
                    max_slot_distance=configuration.max_slot_distance,
                )
                if not selection.within_tolerance:
                    raise ValueError(
                        "replay selection is outside the configured slot "
                        f"tolerance for round {lifecycle.round_id}"
                    )
                observation_index = _selected_observation_index(
                    lifecycle, selection.replay_point.source_file,
                    selection.replay_point.source_line_number,
                )
                decision_context = decision_context_from_replay_point(
                    selection.replay_point
                )
                decision_identity: str | None = None
                for candidate_square in range(25):
                    execution_context = RQ003ExecutionContext(
                        decision_context=decision_context,
                        observation_index=observation_index,
                        structural_candidate_key=candidate_square,
                        decision_point_configuration_identity=(
                            configuration
                            .decision_point_configuration_identity
                        ),
                    )
                    vector = pipeline.compute(execution_context)
                    reconstructed = MeasurementVector.from_canonical_bytes(
                        vector.canonical_bytes()
                    )
                    if reconstructed != vector:
                        raise ValueError(
                            "measurement vector does not reconstruct"
                        )
                    if decision_identity is None:
                        decision_identity = (
                            execution_context.decision_snapshot_identity
                        )
                    elif decision_identity != (
                        execution_context.decision_snapshot_identity
                    ):
                        raise ValueError(
                            "candidate contexts do not share a decision identity"
                        )
                    record = RQ003Experiment0Record(
                        decision_identity=decision_identity,
                        candidate_square=candidate_square,
                        measurement_vector_identity=vector.vector_identity,
                        ordered_fundamental_measurement_values=tuple(
                            _require_u64(
                                f"measurement output {index}", value
                            )
                            for index, value in enumerate(
                                vector.ordered_values
                            )
                        ),
                    )
                    handle.write(record.to_canonical_json())
                    handle.write("\n")
                    record_count += 1
                decision_count += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return RQ003Experiment0Result(
        output_path=destination,
        decision_count=decision_count,
        record_count=record_count,
        output_sha256=_file_sha256(destination),
    )


def load_rq003_experiment0_dataset(
    path: str | Path,
) -> tuple[RQ003Experiment0Record, ...]:
    """Fail closed while reconstructing canonical Experiment 0 records."""

    records: list[RQ003Experiment0Record] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise ValueError(
                    f"Experiment 0 line {line_number} lacks a newline"
                )
            try:
                material = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Experiment 0 line {line_number} is invalid JSON"
                ) from error
            expected = {
                "candidate_square",
                "decision_identity",
                "measurement_vector_identity",
                "ordered_fundamental_measurement_values",
            }
            if not isinstance(material, dict) or set(material) != expected:
                raise ValueError(
                    f"Experiment 0 line {line_number} fields are invalid"
                )
            raw_values = material[
                "ordered_fundamental_measurement_values"
            ]
            if not isinstance(raw_values, list):
                raise ValueError(
                    f"Experiment 0 line {line_number} values are invalid"
                )
            record = RQ003Experiment0Record(
                decision_identity=material["decision_identity"],
                candidate_square=material["candidate_square"],
                measurement_vector_identity=(
                    material["measurement_vector_identity"]
                ),
                ordered_fundamental_measurement_values=tuple(raw_values),
            )
            if record.to_canonical_json() + "\n" != line:
                raise ValueError(
                    f"Experiment 0 line {line_number} is not canonical"
                )
            records.append(record)
    if not records:
        raise ValueError("Experiment 0 dataset contains no records")
    return tuple(records)


def _load_chronological_lifecycles(
    dataset_path: Path,
) -> tuple[RoundLifecycleIndexRecord, ...]:
    index = load_round_index(dataset_path)
    return tuple(
        sorted(
            index.values(),
            key=lambda lifecycle: (lifecycle.start_slot, lifecycle.round_id),
        )
    )


def _selected_observation_index(
    lifecycle: RoundLifecycleIndexRecord,
    source_file: str,
    source_line_number: int,
) -> int:
    ordered = sorted(
        lifecycle.observation_references,
        key=lambda reference: (
            reference.observed_at_utc,
            reference.source_file,
            reference.source_line_number,
        ),
    )
    matches = tuple(
        index
        for index, reference in enumerate(ordered)
        if reference.source_file == source_file
        and reference.source_line_number == source_line_number
    )
    if len(matches) != 1:
        raise ValueError("selected replay observation identity is ambiguous")
    return matches[0]


def _validate_protocol_dependencies() -> None:
    if (
        len(set(_PROTOCOL_SOURCE_REVISIONS)) != 1
        or _PROTOCOL_SOURCE_REVISIONS[0]
        != RQ003_EXPERIMENT0_PROTOCOL_SOURCE_REVISION
    ):
        raise ValueError(
            "fundamental measurements do not share the supported revision"
        )


def _identity(domain: str, material: object) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_nonnegative_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _require_candidate_square(value: object) -> int:
    value = _require_nonnegative_integer("candidate_square", value)
    if value >= 25:
        raise ValueError("candidate_square must be between 0 and 24")
    return value


def _require_u64(name: str, value: object) -> int:
    value = _require_nonnegative_integer(name, value)
    if value > (1 << 64) - 1:
        raise ValueError(f"{name} must be an unsigned 64-bit integer")
    return value


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


__all__ = (
    "RQ003_EXPERIMENT0_OUTPUT_NAMES",
    "RQ003_EXPERIMENT0_PROTOCOL_SOURCE_REVISION",
    "RQ003_EXPERIMENT0_SCHEMA_VERSION",
    "RQ003Experiment0Configuration",
    "RQ003Experiment0Record",
    "RQ003Experiment0Result",
    "build_fundamental_measurement_pipeline",
    "generate_rq003_experiment0_dataset",
    "load_rq003_experiment0_dataset",
)
