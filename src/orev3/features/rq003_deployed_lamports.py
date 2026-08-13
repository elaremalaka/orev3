"""Canonical RQ-003 per-square deployed-lamports measurement.

This module begins the Phase 5 Measurement Library with one fundamental
measurement family. It contains no derived measurement, feature set, dataset,
baseline, ranking procedure, or protocol-revision signal.
"""

from __future__ import annotations

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
    canonical_encode,
    reconstruct_executable_binding_identity,
)
from orev3.features.rq003_registry import FeatureDefinition
from orev3.features.rq003_measurement_support import (
    domain_identity as _identity,
    reconstruct_single_u64_output,
    require_u64,
    validate_dependency_items,
)
from orev3.features.types import FeatureValues


DEPLOYED_LAMPORTS_MEASUREMENT_SCHEMA_VERSION = 1
DEPLOYED_LAMPORTS_FEATURE_NAME = "per_square_deployed_lamports"
DEPLOYED_LAMPORTS_FEATURE_VERSION = "1.0.0"
DEPLOYED_LAMPORTS_FEATURE_GROUP = "raw_current_state"
DEPLOYED_LAMPORTS_OUTPUT_NAME = "deployed_lamports"
DEPLOYED_LAMPORTS_SOURCE_PATH = "round.deployed_lamports"
DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_DEPENDENCY_IDENTITY_DOMAIN = "rq003-deployed-lamports-dependencies-v1"
_IMPLEMENTATION_IDENTITY_DOMAIN = (
    "rq003-deployed-lamports-implementation-v1"
)
_AUTHORITY_IDENTITY_DOMAIN = "rq003-deployed-lamports-authority-v1"
_RATIONALE_IDENTITY_DOMAIN = "rq003-deployed-lamports-rationale-v1"


DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES: tuple[
    tuple[str, str | int], ...
] = (
    ("board_square_count", 25),
    ("canonical_square_order", "zero_based_ascending_0_through_24"),
    ("source_path", DEPLOYED_LAMPORTS_SOURCE_PATH),
    ("source_scalar", "unsigned_64_bit_integer"),
    ("semantic_unit", "lamports"),
    ("measurement_scope", "one_square_at_frozen_normal_observation"),
    ("protocol_semantics", "aggregate_deployed_lamports_per_square"),
)

DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES: tuple[
    tuple[str, str], ...
] = (
    (
        "official_source_revision",
        DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION,
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
        "orev3.features.rq003_deployed_lamports."
        "DeployedLamportsMeasurement.compute",
    ),
    ("input", "context.square.deployed_lamports"),
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


def reconstruct_deployed_lamports_dependency_identity(
    protocol_dependencies: tuple[
        tuple[str, str | int], ...
    ] = DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES,
    revision_dependencies: tuple[
        tuple[str, str], ...
    ] = DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES,
) -> str:
    """Reconstruct the canonical protocol/revision dependency identity."""

    validate_dependency_items(
        "protocol_dependencies",
        protocol_dependencies,
    )
    validate_dependency_items(
        "revision_dependencies",
        revision_dependencies,
    )
    return _identity(
        _DEPENDENCY_IDENTITY_DOMAIN,
        {
            "measurement_schema_version": (
                DEPLOYED_LAMPORTS_MEASUREMENT_SCHEMA_VERSION
            ),
            "protocol_dependencies": protocol_dependencies,
            "revision_dependencies": revision_dependencies,
        },
    )


def reconstruct_deployed_lamports_implementation_identity(
    implementation_declaration: tuple[
        tuple[str, str | int], ...
    ] = _IMPLEMENTATION_DECLARATION,
) -> str:
    """Reconstruct the canonical reviewed-implementation identity."""

    validate_dependency_items(
        "implementation_declaration",
        implementation_declaration,
    )
    return _identity(
        _IMPLEMENTATION_IDENTITY_DOMAIN,
        implementation_declaration,
    )


DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY = (
    reconstruct_deployed_lamports_dependency_identity()
)
DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY = (
    reconstruct_deployed_lamports_implementation_identity()
)

DEPLOYED_LAMPORTS_METADATA = FeatureMetadata(
    metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
    feature_name=DEPLOYED_LAMPORTS_FEATURE_NAME,
    feature_version=DEPLOYED_LAMPORTS_FEATURE_VERSION,
    feature_group=DEPLOYED_LAMPORTS_FEATURE_GROUP,
    description=(
        "Protocol-published deployed lamports for one candidate square at "
        "the frozen normal decision observation."
    ),
    input_fields=(DEPLOYED_LAMPORTS_SOURCE_PATH,),
    history_policy=FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    ),
    output_fields=(
        FeatureOutputField(
            name=DEPLOYED_LAMPORTS_OUTPUT_NAME,
            scalar_type="integer",
            nullable=False,
            semantic_unit="lamports",
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
    configuration_identity=DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY,
    implementation_identity=DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY,
    authority_references=_AUTHORITY_REFERENCES,
)

DEPLOYED_LAMPORTS_DEFINITION = FeatureDefinition(
    metadata=DEPLOYED_LAMPORTS_METADATA,
)

_AUTHORITY_DOCUMENT_IDENTITY = _identity(
    _AUTHORITY_IDENTITY_DOMAIN,
    {
        "authority_references": _AUTHORITY_REFERENCES,
        "measurement": DEPLOYED_LAMPORTS_FEATURE_NAME,
    },
)
_DECISION_RATIONALE_DIGEST = _identity(
    _RATIONALE_IDENTITY_DOMAIN,
    (
        "The governing RQ-003 Feature Set 1 Design identifies exact "
        "per-square deployed lamports as a fundamental, direct, atomic, "
        "deterministic decision-time measurement."
    ),
)

DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION = FeatureEligibilityDecision(
    eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    feature_name=DEPLOYED_LAMPORTS_FEATURE_NAME,
    feature_version=DEPLOYED_LAMPORTS_FEATURE_VERSION,
    feature_semantic_identity=DEPLOYED_LAMPORTS_METADATA.semantic_identity,
    feature_class=DEPLOYED_LAMPORTS_FEATURE_GROUP,
    status=FeatureEligibilityStatus.APPROVED,
    governing_concern=(
        "Exact protocol-published decision-time measurement only; no "
        "derived or interpretive semantics."
    ),
    authority_document_identity=_AUTHORITY_DOCUMENT_IDENTITY,
    decision_rationale_digest=_DECISION_RATIONALE_DIGEST,
    effective_catalog_version=1,
)

DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY = (
    reconstruct_executable_binding_identity(
        DEPLOYED_LAMPORTS_METADATA,
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    )
)


@dataclass(frozen=True, slots=True)
class DeployedLamportsMeasurement(Feature):
    """Pure identity measurement of one square's deployed lamports."""

    name: ClassVar[str] = DEPLOYED_LAMPORTS_FEATURE_NAME
    family: ClassVar[str] = DEPLOYED_LAMPORTS_FEATURE_GROUP
    output_columns: ClassVar[tuple[str, ...]] = (
        DEPLOYED_LAMPORTS_OUTPUT_NAME,
    )
    metadata: ClassVar[FeatureMetadata] = DEPLOYED_LAMPORTS_METADATA
    definition: ClassVar[FeatureDefinition] = DEPLOYED_LAMPORTS_DEFINITION
    eligibility_decision: ClassVar[FeatureEligibilityDecision] = (
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION
    )

    def compute(self, context: FeatureContext) -> FeatureValues:
        """Return the exact current square value without interpretation."""

        if not isinstance(context, FeatureContext):
            raise TypeError("context must be FeatureContext")
        value = context.square.deployed_lamports
        _validate_deployed_lamports_value(value)
        return MappingProxyType({DEPLOYED_LAMPORTS_OUTPUT_NAME: value})

    def canonical_output(self, context: FeatureContext) -> bytes:
        """Return the canonical encoding of the immutable output mapping."""

        return canonical_encode(self.compute(context))

    @staticmethod
    def reconstruct_canonical_output(raw: bytes) -> Mapping[str, int]:
        """Validate and reconstruct one canonical measurement output."""

        return reconstruct_single_u64_output(
            raw,
            output_name=DEPLOYED_LAMPORTS_OUTPUT_NAME,
            artifact_name="deployed-lamports",
        )


DEPLOYED_LAMPORTS_MEASUREMENT = DeployedLamportsMeasurement()


def validate_deployed_lamports_definition() -> None:
    """Fail closed unless the complete canonical definition reconstructs."""

    metadata = DEPLOYED_LAMPORTS_METADATA
    if (
        reconstruct_deployed_lamports_dependency_identity()
        != DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY
    ):
        raise ValueError("deployed-lamports dependency identity mismatch")
    if metadata.configuration_identity != (
        DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY
    ):
        raise ValueError("metadata does not bind canonical dependencies")
    if (
        reconstruct_deployed_lamports_implementation_identity()
        != DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("deployed-lamports implementation identity mismatch")
    if metadata.implementation_identity != (
        DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("metadata does not bind canonical implementation")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("deployed-lamports semantic identity mismatch")
    if (
        metadata.reconstruct_definition_identity()
        != metadata.definition_identity
    ):
        raise ValueError("deployed-lamports definition identity mismatch")
    if DEPLOYED_LAMPORTS_DEFINITION.metadata != metadata:
        raise ValueError("definition does not bind canonical metadata")
    if (
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION
        .reconstruct_eligibility_decision_identity()
        != DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION
        .eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity mismatch")
    if (
        reconstruct_executable_binding_identity(
            metadata,
            DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        )
        != DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY
    ):
        raise ValueError("executable binding identity mismatch")
    if tuple(field.name for field in metadata.output_fields) != (
        DEPLOYED_LAMPORTS_OUTPUT_NAME,
    ):
        raise ValueError("deployed-lamports output schema is not canonical")
    if metadata.input_fields != (DEPLOYED_LAMPORTS_SOURCE_PATH,):
        raise ValueError("deployed-lamports input surface is not canonical")


def _validate_deployed_lamports_value(value: object) -> None:
    require_u64("deployed_lamports", value)


validate_deployed_lamports_definition()


__all__ = (
    "DEPLOYED_LAMPORTS_DEFINITION",
    "DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY",
    "DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION",
    "DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY",
    "DEPLOYED_LAMPORTS_FEATURE_GROUP",
    "DEPLOYED_LAMPORTS_FEATURE_NAME",
    "DEPLOYED_LAMPORTS_FEATURE_VERSION",
    "DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY",
    "DEPLOYED_LAMPORTS_MEASUREMENT",
    "DEPLOYED_LAMPORTS_MEASUREMENT_SCHEMA_VERSION",
    "DEPLOYED_LAMPORTS_METADATA",
    "DEPLOYED_LAMPORTS_OUTPUT_NAME",
    "DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES",
    "DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION",
    "DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES",
    "DEPLOYED_LAMPORTS_SOURCE_PATH",
    "DeployedLamportsMeasurement",
    "reconstruct_deployed_lamports_dependency_identity",
    "reconstruct_deployed_lamports_implementation_identity",
    "validate_deployed_lamports_definition",
)
