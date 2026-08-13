"""Canonical RQ-003 per-square miner-count measurement.

This module adds one Phase 5 fundamental measurement family. It contains no
derived measurement, feature set, dataset, baseline, ranking procedure, or
protocol-revision signal.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar

from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.rq003_contracts import (
    FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    FEATURE_METADATA_SCHEMA_VERSION,
    FeatureEligibilityDecision,
    FeatureEligibilityStatus,
    FeatureHistoryPolicy,
    FeatureMetadata,
    FeatureOutputField,
    canonical_decode,
    canonical_encode,
    reconstruct_executable_binding_identity,
)
from orev3.features.rq003_registry import FeatureDefinition
from orev3.features.types import FeatureValues


MINER_COUNT_MEASUREMENT_SCHEMA_VERSION = 1
MINER_COUNT_FEATURE_NAME = "per_square_miner_count"
MINER_COUNT_FEATURE_VERSION = "1.0.0"
MINER_COUNT_FEATURE_GROUP = "raw_current_state"
MINER_COUNT_OUTPUT_NAME = "miner_count"
MINER_COUNT_SOURCE_PATH = "round.miner_counts"
MINER_COUNT_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_U64_MAX = (1 << 64) - 1
_DEPENDENCY_IDENTITY_DOMAIN = "rq003-miner-count-dependencies-v1"
_IMPLEMENTATION_IDENTITY_DOMAIN = "rq003-miner-count-implementation-v1"
_AUTHORITY_IDENTITY_DOMAIN = "rq003-miner-count-authority-v1"
_RATIONALE_IDENTITY_DOMAIN = "rq003-miner-count-rationale-v1"


MINER_COUNT_PROTOCOL_DEPENDENCIES: tuple[
    tuple[str, str | int], ...
] = (
    ("board_square_count", 25),
    ("canonical_square_order", "zero_based_ascending_0_through_24"),
    ("source_path", MINER_COUNT_SOURCE_PATH),
    ("source_scalar", "unsigned_64_bit_integer"),
    ("semantic_unit", "miner_authority_count"),
    ("measurement_scope", "one_square_at_frozen_normal_observation"),
    (
        "protocol_semantics",
        "distinct_miner_authorities_recorded_on_square",
    ),
)

MINER_COUNT_REVISION_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    (
        "official_source_revision",
        MINER_COUNT_PROTOCOL_SOURCE_REVISION,
    ),
    (
        "cross_revision_reuse",
        "requires_authoritative_semantic_compatibility_declaration",
    ),
    (
        "revision_information_role",
        "validation_and_population_control_only",
    ),
    (
        "revision_feature_visibility",
        "prohibited",
    ),
)

_IMPLEMENTATION_DECLARATION: tuple[tuple[str, str | int], ...] = (
    ("implementation_schema_version", 1),
    (
        "implementation",
        "orev3.features.rq003_miner_count.MinerCountMeasurement.compute",
    ),
    ("input", "context.square.miner_count"),
    ("input_validation", "exact_non_boolean_u64"),
    ("output", "immutable_single_integer_mapping"),
    ("transformation", "identity"),
    ("history", "unused"),
)

_AUTHORITY_REFERENCES = (
    "docs/research/questions/RQ-003-winning-square-predictability.md",
    "docs/research/investigations/rq003-feature-set-1-design.md",
    "docs/research/investigations/rq003-measurement-catalog.md",
    "docs/research/investigations/"
    "rq003-measurement-implementation-alignment.md",
    "docs/research/investigations/rq003-phase3-design-review.md",
    "rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md",
)


def _identity(domain: str, material: object) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def _validate_dependency_items(name: str, items: object) -> None:
    if not isinstance(items, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    keys: list[str] = []
    for item in items:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or not isinstance(item[1], (str, int))
            or isinstance(item[1], bool)
        ):
            raise TypeError(
                f"{name} must contain canonical key/value tuples"
            )
        if not isinstance(item[1], int) and (
            not item[1] or item[1].strip() != item[1]
        ):
            raise ValueError(f"{name} contains a noncanonical value")
        keys.append(item[0])
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name} keys must be unique")


def reconstruct_miner_count_dependency_identity(
    protocol_dependencies: tuple[
        tuple[str, str | int], ...
    ] = MINER_COUNT_PROTOCOL_DEPENDENCIES,
    revision_dependencies: tuple[
        tuple[str, str], ...
    ] = MINER_COUNT_REVISION_DEPENDENCIES,
) -> str:
    """Reconstruct the canonical protocol/revision dependency identity."""

    _validate_dependency_items(
        "protocol_dependencies",
        protocol_dependencies,
    )
    _validate_dependency_items(
        "revision_dependencies",
        revision_dependencies,
    )
    return _identity(
        _DEPENDENCY_IDENTITY_DOMAIN,
        {
            "measurement_schema_version": MINER_COUNT_MEASUREMENT_SCHEMA_VERSION,
            "protocol_dependencies": protocol_dependencies,
            "revision_dependencies": revision_dependencies,
        },
    )


def reconstruct_miner_count_implementation_identity(
    implementation_declaration: tuple[
        tuple[str, str | int], ...
    ] = _IMPLEMENTATION_DECLARATION,
) -> str:
    """Reconstruct the canonical reviewed-implementation identity."""

    _validate_dependency_items(
        "implementation_declaration",
        implementation_declaration,
    )
    return _identity(
        _IMPLEMENTATION_IDENTITY_DOMAIN,
        implementation_declaration,
    )


MINER_COUNT_DEPENDENCY_IDENTITY = reconstruct_miner_count_dependency_identity()
MINER_COUNT_IMPLEMENTATION_IDENTITY = (
    reconstruct_miner_count_implementation_identity()
)

MINER_COUNT_METADATA = FeatureMetadata(
    metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
    feature_name=MINER_COUNT_FEATURE_NAME,
    feature_version=MINER_COUNT_FEATURE_VERSION,
    feature_group=MINER_COUNT_FEATURE_GROUP,
    description=(
        "Protocol-published count of distinct Miner authorities recorded on "
        "one candidate square at the frozen normal decision observation."
    ),
    input_fields=(MINER_COUNT_SOURCE_PATH,),
    history_policy=FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    ),
    output_fields=(
        FeatureOutputField(
            name=MINER_COUNT_OUTPUT_NAME,
            scalar_type="integer",
            nullable=False,
            semantic_unit="miner_authority_count",
            candidate_scope="per_square",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    ),
    missingness_policy="fail",
    determinism_contract=(
        "Return the exact non-boolean unsigned 64-bit integer published for "
        "the selected square in the frozen normal observation; perform no "
        "arithmetic, comparison, normalization, ranking, history access, or "
        "interpretation."
    ),
    configuration_identity=MINER_COUNT_DEPENDENCY_IDENTITY,
    implementation_identity=MINER_COUNT_IMPLEMENTATION_IDENTITY,
    authority_references=_AUTHORITY_REFERENCES,
)

MINER_COUNT_DEFINITION = FeatureDefinition(metadata=MINER_COUNT_METADATA)

_AUTHORITY_DOCUMENT_IDENTITY = _identity(
    _AUTHORITY_IDENTITY_DOMAIN,
    {
        "authority_references": _AUTHORITY_REFERENCES,
        "measurement": MINER_COUNT_FEATURE_NAME,
    },
)
_DECISION_RATIONALE_DIGEST = _identity(
    _RATIONALE_IDENTITY_DOMAIN,
    (
        "The governing RQ-003 Feature Set 1 Design identifies exact "
        "per-square miner counts as a fundamental, direct, atomic, "
        "deterministic decision-time measurement."
    ),
)

MINER_COUNT_ELIGIBILITY_DECISION = FeatureEligibilityDecision(
    eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    feature_name=MINER_COUNT_FEATURE_NAME,
    feature_version=MINER_COUNT_FEATURE_VERSION,
    feature_semantic_identity=MINER_COUNT_METADATA.semantic_identity,
    feature_class=MINER_COUNT_FEATURE_GROUP,
    status=FeatureEligibilityStatus.APPROVED,
    governing_concern=(
        "Exact protocol-published decision-time measurement only; no "
        "derived or interpretive semantics."
    ),
    authority_document_identity=_AUTHORITY_DOCUMENT_IDENTITY,
    decision_rationale_digest=_DECISION_RATIONALE_DIGEST,
    effective_catalog_version=1,
)

MINER_COUNT_EXECUTABLE_BINDING_IDENTITY = (
    reconstruct_executable_binding_identity(
        MINER_COUNT_METADATA,
        MINER_COUNT_ELIGIBILITY_DECISION,
    )
)


@dataclass(frozen=True, slots=True)
class MinerCountMeasurement(Feature):
    """Pure identity measurement of one square's Miner-authority count."""

    name: ClassVar[str] = MINER_COUNT_FEATURE_NAME
    family: ClassVar[str] = MINER_COUNT_FEATURE_GROUP
    output_columns: ClassVar[tuple[str, ...]] = (MINER_COUNT_OUTPUT_NAME,)
    metadata: ClassVar[FeatureMetadata] = MINER_COUNT_METADATA
    definition: ClassVar[FeatureDefinition] = MINER_COUNT_DEFINITION
    eligibility_decision: ClassVar[FeatureEligibilityDecision] = (
        MINER_COUNT_ELIGIBILITY_DECISION
    )

    def compute(self, context: FeatureContext) -> FeatureValues:
        """Return the exact current square value without interpretation."""

        if not isinstance(context, FeatureContext):
            raise TypeError("context must be FeatureContext")
        value = context.square.miner_count
        _validate_miner_count_value(value)
        return MappingProxyType({MINER_COUNT_OUTPUT_NAME: value})

    def canonical_output(self, context: FeatureContext) -> bytes:
        """Return the canonical encoding of the immutable output mapping."""

        return canonical_encode(self.compute(context))

    @staticmethod
    def reconstruct_canonical_output(raw: bytes) -> Mapping[str, int]:
        """Validate and reconstruct one canonical measurement output."""

        decoded = canonical_decode(raw)
        if not isinstance(decoded, dict):
            raise ValueError("miner-count output must be a mapping")
        if set(decoded) != {MINER_COUNT_OUTPUT_NAME}:
            raise ValueError(
                "miner-count output must contain exactly its declared field"
            )
        value = decoded[MINER_COUNT_OUTPUT_NAME]
        _validate_miner_count_value(value)
        return MappingProxyType({MINER_COUNT_OUTPUT_NAME: value})


MINER_COUNT_MEASUREMENT = MinerCountMeasurement()


def validate_miner_count_definition() -> None:
    """Fail closed unless the complete canonical definition reconstructs."""

    metadata = MINER_COUNT_METADATA
    if (
        reconstruct_miner_count_dependency_identity()
        != MINER_COUNT_DEPENDENCY_IDENTITY
    ):
        raise ValueError("miner-count dependency identity mismatch")
    if metadata.configuration_identity != MINER_COUNT_DEPENDENCY_IDENTITY:
        raise ValueError("metadata does not bind canonical dependencies")
    if (
        reconstruct_miner_count_implementation_identity()
        != MINER_COUNT_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("miner-count implementation identity mismatch")
    if metadata.implementation_identity != MINER_COUNT_IMPLEMENTATION_IDENTITY:
        raise ValueError("metadata does not bind canonical implementation")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("miner-count semantic identity mismatch")
    if (
        metadata.reconstruct_definition_identity()
        != metadata.definition_identity
    ):
        raise ValueError("miner-count definition identity mismatch")
    if MINER_COUNT_DEFINITION.metadata != metadata:
        raise ValueError("definition does not bind canonical metadata")
    if (
        MINER_COUNT_ELIGIBILITY_DECISION
        .reconstruct_eligibility_decision_identity()
        != MINER_COUNT_ELIGIBILITY_DECISION.eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity mismatch")
    if (
        reconstruct_executable_binding_identity(
            metadata,
            MINER_COUNT_ELIGIBILITY_DECISION,
        )
        != MINER_COUNT_EXECUTABLE_BINDING_IDENTITY
    ):
        raise ValueError("executable binding identity mismatch")
    if tuple(field.name for field in metadata.output_fields) != (
        MINER_COUNT_OUTPUT_NAME,
    ):
        raise ValueError("miner-count output schema is not canonical")
    if metadata.input_fields != (MINER_COUNT_SOURCE_PATH,):
        raise ValueError("miner-count input surface is not canonical")


def _validate_miner_count_value(value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > _U64_MAX
    ):
        raise ValueError("miner_count must be an unsigned 64-bit integer")


validate_miner_count_definition()


__all__ = (
    "MINER_COUNT_DEFINITION",
    "MINER_COUNT_DEPENDENCY_IDENTITY",
    "MINER_COUNT_ELIGIBILITY_DECISION",
    "MINER_COUNT_EXECUTABLE_BINDING_IDENTITY",
    "MINER_COUNT_FEATURE_GROUP",
    "MINER_COUNT_FEATURE_NAME",
    "MINER_COUNT_FEATURE_VERSION",
    "MINER_COUNT_IMPLEMENTATION_IDENTITY",
    "MINER_COUNT_MEASUREMENT",
    "MINER_COUNT_MEASUREMENT_SCHEMA_VERSION",
    "MINER_COUNT_METADATA",
    "MINER_COUNT_OUTPUT_NAME",
    "MINER_COUNT_PROTOCOL_DEPENDENCIES",
    "MINER_COUNT_PROTOCOL_SOURCE_REVISION",
    "MINER_COUNT_REVISION_DEPENDENCIES",
    "MINER_COUNT_SOURCE_PATH",
    "MinerCountMeasurement",
    "reconstruct_miner_count_dependency_identity",
    "reconstruct_miner_count_implementation_identity",
    "validate_miner_count_definition",
)
