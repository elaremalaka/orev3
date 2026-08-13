"""Canonical RQ-003 protocol-published total-miners measurement.

This module adds one fundamental Measurement Library family. It contains no
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


TOTAL_MINERS_MEASUREMENT_SCHEMA_VERSION = 1
TOTAL_MINERS_FEATURE_NAME = "total_miners"
TOTAL_MINERS_FEATURE_VERSION = "1.0.0"
TOTAL_MINERS_FEATURE_GROUP = "raw_current_state"
TOTAL_MINERS_OUTPUT_NAME = "total_miners"
TOTAL_MINERS_SOURCE_PATH = "round.total_miners"
TOTAL_MINERS_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_U64_MAX = (1 << 64) - 1
_DEPENDENCY_IDENTITY_DOMAIN = "rq003-total-miners-dependencies-v1"
_IMPLEMENTATION_IDENTITY_DOMAIN = "rq003-total-miners-implementation-v1"
_AUTHORITY_IDENTITY_DOMAIN = "rq003-total-miners-authority-v1"
_RATIONALE_IDENTITY_DOMAIN = "rq003-total-miners-rationale-v1"


TOTAL_MINERS_PROTOCOL_DEPENDENCIES: tuple[
    tuple[str, str | int], ...
] = (
    ("source_path", TOTAL_MINERS_SOURCE_PATH),
    ("source_scalar", "unsigned_64_bit_integer"),
    ("semantic_unit", "unique_miner_authority_count"),
    ("measurement_scope", "active_round_at_frozen_normal_observation"),
    ("protocol_semantics", "unique_miner_authorities_in_active_round"),
    ("counting_event", "first_participation_per_miner_authority"),
    ("per_square_count_independence", "not_reconstructed_from_square_counts"),
)

TOTAL_MINERS_REVISION_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    (
        "official_source_revision",
        TOTAL_MINERS_PROTOCOL_SOURCE_REVISION,
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
        "orev3.features.rq003_total_miners.TotalMinersMeasurement.compute",
    ),
    ("input", "context.round.total_miners"),
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
    "docs/research/investigations/rq003-phase3a-immutable-context.md",
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
            raise TypeError(f"{name} must contain canonical key/value tuples")
        if not isinstance(item[1], int) and (
            not item[1] or item[1].strip() != item[1]
        ):
            raise ValueError(f"{name} contains a noncanonical value")
        keys.append(item[0])
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name} keys must be unique")


def reconstruct_total_miners_dependency_identity(
    protocol_dependencies: tuple[
        tuple[str, str | int], ...
    ] = TOTAL_MINERS_PROTOCOL_DEPENDENCIES,
    revision_dependencies: tuple[
        tuple[str, str], ...
    ] = TOTAL_MINERS_REVISION_DEPENDENCIES,
) -> str:
    """Reconstruct the canonical protocol/revision dependency identity."""

    _validate_dependency_items("protocol_dependencies", protocol_dependencies)
    _validate_dependency_items("revision_dependencies", revision_dependencies)
    return _identity(
        _DEPENDENCY_IDENTITY_DOMAIN,
        {
            "measurement_schema_version": TOTAL_MINERS_MEASUREMENT_SCHEMA_VERSION,
            "protocol_dependencies": protocol_dependencies,
            "revision_dependencies": revision_dependencies,
        },
    )


def reconstruct_total_miners_implementation_identity(
    implementation_declaration: tuple[
        tuple[str, str | int], ...
    ] = _IMPLEMENTATION_DECLARATION,
) -> str:
    """Reconstruct the canonical reviewed-implementation identity."""

    _validate_dependency_items(
        "implementation_declaration", implementation_declaration
    )
    return _identity(
        _IMPLEMENTATION_IDENTITY_DOMAIN,
        implementation_declaration,
    )


TOTAL_MINERS_DEPENDENCY_IDENTITY = reconstruct_total_miners_dependency_identity()
TOTAL_MINERS_IMPLEMENTATION_IDENTITY = (
    reconstruct_total_miners_implementation_identity()
)

TOTAL_MINERS_METADATA = FeatureMetadata(
    metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
    feature_name=TOTAL_MINERS_FEATURE_NAME,
    feature_version=TOTAL_MINERS_FEATURE_VERSION,
    feature_group=TOTAL_MINERS_FEATURE_GROUP,
    description=(
        "Protocol-published number of unique Miner authorities that have "
        "participated in the active round at the frozen normal observation."
    ),
    input_fields=(TOTAL_MINERS_SOURCE_PATH,),
    history_policy=FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    ),
    output_fields=(
        FeatureOutputField(
            name=TOTAL_MINERS_OUTPUT_NAME,
            scalar_type="integer",
            nullable=False,
            semantic_unit="unique_miner_authority_count",
            candidate_scope="context_wide_replicated",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    ),
    missingness_policy="fail",
    determinism_contract=(
        "Return the exact non-boolean unsigned 64-bit integer published as "
        "round.total_miners in the frozen normal observation; perform no "
        "arithmetic, normalization, ranking, history access, reconstruction, "
        "or interpretation."
    ),
    configuration_identity=TOTAL_MINERS_DEPENDENCY_IDENTITY,
    implementation_identity=TOTAL_MINERS_IMPLEMENTATION_IDENTITY,
    authority_references=_AUTHORITY_REFERENCES,
)

TOTAL_MINERS_DEFINITION = FeatureDefinition(metadata=TOTAL_MINERS_METADATA)

_AUTHORITY_DOCUMENT_IDENTITY = _identity(
    _AUTHORITY_IDENTITY_DOMAIN,
    {
        "authority_references": _AUTHORITY_REFERENCES,
        "measurement": TOTAL_MINERS_FEATURE_NAME,
    },
)
_DECISION_RATIONALE_DIGEST = _identity(
    _RATIONALE_IDENTITY_DOMAIN,
    (
        "The governing RQ-003 Feature Set 1 Design identifies the exact "
        "protocol-published active-round total-miner count as a fundamental, "
        "direct, atomic, deterministic decision-time measurement."
    ),
)

TOTAL_MINERS_ELIGIBILITY_DECISION = FeatureEligibilityDecision(
    eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    feature_name=TOTAL_MINERS_FEATURE_NAME,
    feature_version=TOTAL_MINERS_FEATURE_VERSION,
    feature_semantic_identity=TOTAL_MINERS_METADATA.semantic_identity,
    feature_class=TOTAL_MINERS_FEATURE_GROUP,
    status=FeatureEligibilityStatus.APPROVED,
    governing_concern=(
        "Exact protocol-published decision-time measurement only; no "
        "reconstruction from per-square counts or interpretive semantics."
    ),
    authority_document_identity=_AUTHORITY_DOCUMENT_IDENTITY,
    decision_rationale_digest=_DECISION_RATIONALE_DIGEST,
    effective_catalog_version=1,
)

TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY = (
    reconstruct_executable_binding_identity(
        TOTAL_MINERS_METADATA,
        TOTAL_MINERS_ELIGIBILITY_DECISION,
    )
)


@dataclass(frozen=True, slots=True)
class TotalMinersMeasurement(Feature):
    """Pure identity measurement of the active Round total-miner count."""

    name: ClassVar[str] = TOTAL_MINERS_FEATURE_NAME
    family: ClassVar[str] = TOTAL_MINERS_FEATURE_GROUP
    output_columns: ClassVar[tuple[str, ...]] = (TOTAL_MINERS_OUTPUT_NAME,)
    metadata: ClassVar[FeatureMetadata] = TOTAL_MINERS_METADATA
    definition: ClassVar[FeatureDefinition] = TOTAL_MINERS_DEFINITION
    eligibility_decision: ClassVar[FeatureEligibilityDecision] = (
        TOTAL_MINERS_ELIGIBILITY_DECISION
    )

    def compute(self, context: FeatureContext) -> FeatureValues:
        """Return the exact current Round value without interpretation."""

        if not isinstance(context, FeatureContext):
            raise TypeError("context must be FeatureContext")
        value = context.round.total_miners  # type: ignore[attr-defined]
        _validate_total_miners_value(value)
        return MappingProxyType({TOTAL_MINERS_OUTPUT_NAME: value})

    def canonical_output(self, context: FeatureContext) -> bytes:
        """Return the canonical encoding of the immutable output mapping."""

        return canonical_encode(self.compute(context))

    @staticmethod
    def reconstruct_canonical_output(raw: bytes) -> Mapping[str, int]:
        """Validate and reconstruct one canonical measurement output."""

        decoded = canonical_decode(raw)
        if not isinstance(decoded, dict):
            raise ValueError("total-miners output must be a mapping")
        if set(decoded) != {TOTAL_MINERS_OUTPUT_NAME}:
            raise ValueError(
                "total-miners output must contain exactly its declared field"
            )
        value = decoded[TOTAL_MINERS_OUTPUT_NAME]
        _validate_total_miners_value(value)
        return MappingProxyType({TOTAL_MINERS_OUTPUT_NAME: value})


TOTAL_MINERS_MEASUREMENT = TotalMinersMeasurement()


def validate_total_miners_definition() -> None:
    """Fail closed unless the complete canonical definition reconstructs."""

    metadata = TOTAL_MINERS_METADATA
    if (
        reconstruct_total_miners_dependency_identity()
        != TOTAL_MINERS_DEPENDENCY_IDENTITY
    ):
        raise ValueError("total-miners dependency identity mismatch")
    if metadata.configuration_identity != TOTAL_MINERS_DEPENDENCY_IDENTITY:
        raise ValueError("metadata does not bind canonical dependencies")
    if (
        reconstruct_total_miners_implementation_identity()
        != TOTAL_MINERS_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("total-miners implementation identity mismatch")
    if metadata.implementation_identity != TOTAL_MINERS_IMPLEMENTATION_IDENTITY:
        raise ValueError("metadata does not bind canonical implementation")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("total-miners semantic identity mismatch")
    if (
        metadata.reconstruct_definition_identity()
        != metadata.definition_identity
    ):
        raise ValueError("total-miners definition identity mismatch")
    if TOTAL_MINERS_DEFINITION.metadata != metadata:
        raise ValueError("definition does not bind canonical metadata")
    decision = TOTAL_MINERS_ELIGIBILITY_DECISION
    if (
        decision.reconstruct_eligibility_decision_identity()
        != decision.eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity mismatch")
    if (
        reconstruct_executable_binding_identity(metadata, decision)
        != TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY
    ):
        raise ValueError("executable binding identity mismatch")
    if tuple(field.name for field in metadata.output_fields) != (
        TOTAL_MINERS_OUTPUT_NAME,
    ):
        raise ValueError("total-miners output schema is not canonical")
    if metadata.input_fields != (TOTAL_MINERS_SOURCE_PATH,):
        raise ValueError("total-miners input surface is not canonical")


def _validate_total_miners_value(value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > _U64_MAX
    ):
        raise ValueError("total_miners must be an unsigned 64-bit integer")


validate_total_miners_definition()


__all__ = (
    "TOTAL_MINERS_DEFINITION",
    "TOTAL_MINERS_DEPENDENCY_IDENTITY",
    "TOTAL_MINERS_ELIGIBILITY_DECISION",
    "TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY",
    "TOTAL_MINERS_FEATURE_GROUP",
    "TOTAL_MINERS_FEATURE_NAME",
    "TOTAL_MINERS_FEATURE_VERSION",
    "TOTAL_MINERS_IMPLEMENTATION_IDENTITY",
    "TOTAL_MINERS_MEASUREMENT",
    "TOTAL_MINERS_MEASUREMENT_SCHEMA_VERSION",
    "TOTAL_MINERS_METADATA",
    "TOTAL_MINERS_OUTPUT_NAME",
    "TOTAL_MINERS_PROTOCOL_DEPENDENCIES",
    "TOTAL_MINERS_PROTOCOL_SOURCE_REVISION",
    "TOTAL_MINERS_REVISION_DEPENDENCIES",
    "TOTAL_MINERS_SOURCE_PATH",
    "TotalMinersMeasurement",
    "reconstruct_total_miners_dependency_identity",
    "reconstruct_total_miners_implementation_identity",
    "validate_total_miners_definition",
)
