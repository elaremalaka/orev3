"""Canonical RQ-003 protocol-published Board production-cost EMA.

This module defines one fundamental Measurement Library family. It reads the
frozen protocol field unchanged and contains no EMA calculation, derived
measurement, feature set, dataset, baseline, ranking, or interpretation.
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
from orev3.features.rq003_measurement_support import (
    domain_identity as _identity,
    reconstruct_single_u64_output,
    require_u64,
    validate_dependency_items,
)
from orev3.features.rq003_registry import FeatureDefinition
from orev3.features.types import FeatureValues


PRODUCTION_COST_EMA_MEASUREMENT_SCHEMA_VERSION = 1
PRODUCTION_COST_EMA_FEATURE_NAME = "board_production_cost_ema"
PRODUCTION_COST_EMA_FEATURE_VERSION = "1.0.0"
PRODUCTION_COST_EMA_FEATURE_GROUP = "raw_current_state"
PRODUCTION_COST_EMA_OUTPUT_NAME = "board_production_cost_ema"
PRODUCTION_COST_EMA_SOURCE_PATH = "board.production_cost_ema"
PRODUCTION_COST_EMA_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_DEPENDENCY_IDENTITY_DOMAIN = "rq003-production-cost-ema-dependencies-v1"
_IMPLEMENTATION_IDENTITY_DOMAIN = "rq003-production-cost-ema-implementation-v1"
_AUTHORITY_IDENTITY_DOMAIN = "rq003-production-cost-ema-authority-v1"
_RATIONALE_IDENTITY_DOMAIN = "rq003-production-cost-ema-rationale-v1"


PRODUCTION_COST_EMA_PROTOCOL_DEPENDENCIES: tuple[
    tuple[str, str | int], ...
] = (
    ("source_path", PRODUCTION_COST_EMA_SOURCE_PATH),
    ("source_scalar", "unsigned_64_bit_integer"),
    ("semantic_unit", "lamports_per_whole_ore"),
    ("measurement_scope", "board_at_frozen_normal_observation"),
    (
        "protocol_semantics",
        "protocol_maintained_production_cost_exponential_moving_average",
    ),
    ("temporal_semantics", "lagged_qualifying_reset_maintained_value"),
    ("carry_forward_semantics", "may_persist_across_board_transition"),
    ("measurement_transformation", "identity_no_recomputation"),
    ("supplementary_reads", "prohibited"),
    ("cross_account_repair", "prohibited"),
)

PRODUCTION_COST_EMA_REVISION_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    (
        "official_source_revision",
        PRODUCTION_COST_EMA_PROTOCOL_SOURCE_REVISION,
    ),
    (
        "cross_revision_reuse",
        "requires_authoritative_semantic_compatibility_declaration",
    ),
    (
        "revision_information_role",
        "validation_and_population_control_only",
    ),
    ("revision_feature_visibility", "prohibited"),
)

_IMPLEMENTATION_DECLARATION: tuple[tuple[str, str | int], ...] = (
    ("implementation_schema_version", 1),
    (
        "implementation",
        "orev3.features.rq003_production_cost_ema."
        "ProductionCostEmaMeasurement.compute",
    ),
    ("input", "context.board.production_cost_ema"),
    ("input_validation", "exact_non_boolean_u64"),
    ("output", "immutable_single_integer_mapping"),
    ("transformation", "identity"),
    ("ema_calculation", "none"),
    ("history", "unused"),
    ("supplementary_reads", "none"),
)

_AUTHORITY_REFERENCES = (
    "docs/research/questions/RQ-003-winning-square-predictability.md",
    "docs/research/investigations/rq003-feature-set-1-design.md",
    "docs/research/investigations/rq003-measurement-catalog.md",
    "docs/research/investigations/rq003-protocol-state-discovery.md",
    "docs/research/investigations/rq003-phase3a-immutable-context.md",
    "docs/research/investigations/rq003-phase4-pipeline-review.md",
    "rfcs/RFC-014-PROTOCOL-REVISION-PROVENANCE.md",
)


def reconstruct_production_cost_ema_dependency_identity(
    protocol_dependencies: tuple[
        tuple[str, str | int], ...
    ] = PRODUCTION_COST_EMA_PROTOCOL_DEPENDENCIES,
    revision_dependencies: tuple[
        tuple[str, str], ...
    ] = PRODUCTION_COST_EMA_REVISION_DEPENDENCIES,
) -> str:
    """Reconstruct the canonical protocol/revision dependency identity."""

    validate_dependency_items("protocol_dependencies", protocol_dependencies)
    validate_dependency_items("revision_dependencies", revision_dependencies)
    return _identity(
        _DEPENDENCY_IDENTITY_DOMAIN,
        {
            "measurement_schema_version": (
                PRODUCTION_COST_EMA_MEASUREMENT_SCHEMA_VERSION
            ),
            "protocol_dependencies": protocol_dependencies,
            "revision_dependencies": revision_dependencies,
        },
    )


def reconstruct_production_cost_ema_implementation_identity(
    implementation_declaration: tuple[
        tuple[str, str | int], ...
    ] = _IMPLEMENTATION_DECLARATION,
) -> str:
    """Reconstruct the canonical reviewed-implementation identity."""

    validate_dependency_items(
        "implementation_declaration", implementation_declaration
    )
    return _identity(
        _IMPLEMENTATION_IDENTITY_DOMAIN,
        implementation_declaration,
    )


PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY = (
    reconstruct_production_cost_ema_dependency_identity()
)
PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY = (
    reconstruct_production_cost_ema_implementation_identity()
)

PRODUCTION_COST_EMA_METADATA = FeatureMetadata(
    metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
    feature_name=PRODUCTION_COST_EMA_FEATURE_NAME,
    feature_version=PRODUCTION_COST_EMA_FEATURE_VERSION,
    feature_group=PRODUCTION_COST_EMA_FEATURE_GROUP,
    description=(
        "Exact protocol-published Board production-cost EMA at the frozen "
        "normal observation; a lagged, qualifying-reset-maintained aggregate "
        "read without recomputation or interpretation."
    ),
    input_fields=(PRODUCTION_COST_EMA_SOURCE_PATH,),
    history_policy=FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    ),
    output_fields=(
        FeatureOutputField(
            name=PRODUCTION_COST_EMA_OUTPUT_NAME,
            scalar_type="integer",
            nullable=False,
            semantic_unit="lamports_per_whole_ore",
            candidate_scope="context_wide_replicated",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    ),
    missingness_policy="fail",
    determinism_contract=(
        "Return the exact non-boolean unsigned 64-bit integer published as "
        "board.production_cost_ema in the frozen normal observation; perform "
        "no arithmetic, EMA calculation, normalization, ranking, history "
        "access, supplementary read, cross-account repair, or interpretation."
    ),
    configuration_identity=PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY,
    implementation_identity=PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY,
    authority_references=_AUTHORITY_REFERENCES,
)

PRODUCTION_COST_EMA_DEFINITION = FeatureDefinition(
    metadata=PRODUCTION_COST_EMA_METADATA
)

_AUTHORITY_DOCUMENT_IDENTITY = _identity(
    _AUTHORITY_IDENTITY_DOMAIN,
    {
        "authority_references": _AUTHORITY_REFERENCES,
        "measurement": PRODUCTION_COST_EMA_FEATURE_NAME,
    },
)
_DECISION_RATIONALE_DIGEST = _identity(
    _RATIONALE_IDENTITY_DOMAIN,
    (
        "The governing RQ-003 documents identify the exact Board "
        "production-cost EMA at the frozen normal observation as a direct, "
        "atomic, deterministic, revision-bound protocol-state measurement."
    ),
)

PRODUCTION_COST_EMA_ELIGIBILITY_DECISION = FeatureEligibilityDecision(
    eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    feature_name=PRODUCTION_COST_EMA_FEATURE_NAME,
    feature_version=PRODUCTION_COST_EMA_FEATURE_VERSION,
    feature_semantic_identity=PRODUCTION_COST_EMA_METADATA.semantic_identity,
    feature_class=PRODUCTION_COST_EMA_FEATURE_GROUP,
    status=FeatureEligibilityStatus.APPROVED,
    governing_concern=(
        "Exact frozen protocol-published value only; no EMA calculation, "
        "historical reconstruction, supplementary read, repair, or "
        "interpretive semantics."
    ),
    authority_document_identity=_AUTHORITY_DOCUMENT_IDENTITY,
    decision_rationale_digest=_DECISION_RATIONALE_DIGEST,
    effective_catalog_version=1,
)

PRODUCTION_COST_EMA_EXECUTABLE_BINDING_IDENTITY = (
    reconstruct_executable_binding_identity(
        PRODUCTION_COST_EMA_METADATA,
        PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    )
)


@dataclass(frozen=True, slots=True)
class ProductionCostEmaMeasurement(Feature):
    """Pure identity measurement of the frozen Board protocol value."""

    name: ClassVar[str] = PRODUCTION_COST_EMA_FEATURE_NAME
    family: ClassVar[str] = PRODUCTION_COST_EMA_FEATURE_GROUP
    output_columns: ClassVar[tuple[str, ...]] = (
        PRODUCTION_COST_EMA_OUTPUT_NAME,
    )
    metadata: ClassVar[FeatureMetadata] = PRODUCTION_COST_EMA_METADATA
    definition: ClassVar[FeatureDefinition] = PRODUCTION_COST_EMA_DEFINITION
    eligibility_decision: ClassVar[FeatureEligibilityDecision] = (
        PRODUCTION_COST_EMA_ELIGIBILITY_DECISION
    )

    def compute(self, context: FeatureContext) -> FeatureValues:
        """Return the exact frozen Board value without interpretation."""

        if not isinstance(context, FeatureContext):
            raise TypeError("context must be FeatureContext")
        value = context.board.production_cost_ema  # type: ignore[attr-defined]
        _validate_production_cost_ema_value(value)
        return MappingProxyType({PRODUCTION_COST_EMA_OUTPUT_NAME: value})

    def canonical_output(self, context: FeatureContext) -> bytes:
        """Return the canonical encoding of the immutable output mapping."""

        return canonical_encode(self.compute(context))

    @staticmethod
    def reconstruct_canonical_output(raw: bytes) -> Mapping[str, int]:
        """Validate and reconstruct one canonical measurement output."""

        return reconstruct_single_u64_output(
            raw,
            output_name=PRODUCTION_COST_EMA_OUTPUT_NAME,
            artifact_name="production-cost-ema",
        )


PRODUCTION_COST_EMA_MEASUREMENT = ProductionCostEmaMeasurement()


def validate_production_cost_ema_definition() -> None:
    """Fail closed unless the complete canonical definition reconstructs."""

    metadata = PRODUCTION_COST_EMA_METADATA
    if (
        reconstruct_production_cost_ema_dependency_identity()
        != PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY
    ):
        raise ValueError("production-cost EMA dependency identity mismatch")
    if metadata.configuration_identity != PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY:
        raise ValueError("metadata does not bind canonical dependencies")
    if (
        reconstruct_production_cost_ema_implementation_identity()
        != PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("production-cost EMA implementation identity mismatch")
    if (
        metadata.implementation_identity
        != PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("metadata does not bind canonical implementation")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("production-cost EMA semantic identity mismatch")
    if metadata.reconstruct_definition_identity() != metadata.definition_identity:
        raise ValueError("production-cost EMA definition identity mismatch")
    if PRODUCTION_COST_EMA_DEFINITION.metadata != metadata:
        raise ValueError("definition does not bind canonical metadata")
    decision = PRODUCTION_COST_EMA_ELIGIBILITY_DECISION
    if (
        decision.reconstruct_eligibility_decision_identity()
        != decision.eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity mismatch")
    if (
        reconstruct_executable_binding_identity(metadata, decision)
        != PRODUCTION_COST_EMA_EXECUTABLE_BINDING_IDENTITY
    ):
        raise ValueError("executable binding identity mismatch")
    if tuple(field.name for field in metadata.output_fields) != (
        PRODUCTION_COST_EMA_OUTPUT_NAME,
    ):
        raise ValueError("production-cost EMA output schema is not canonical")
    if metadata.input_fields != (PRODUCTION_COST_EMA_SOURCE_PATH,):
        raise ValueError("production-cost EMA input surface is not canonical")


def _validate_production_cost_ema_value(value: object) -> None:
    require_u64("production_cost_ema", value)


validate_production_cost_ema_definition()


__all__ = (
    "PRODUCTION_COST_EMA_DEFINITION",
    "PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY",
    "PRODUCTION_COST_EMA_ELIGIBILITY_DECISION",
    "PRODUCTION_COST_EMA_EXECUTABLE_BINDING_IDENTITY",
    "PRODUCTION_COST_EMA_FEATURE_GROUP",
    "PRODUCTION_COST_EMA_FEATURE_NAME",
    "PRODUCTION_COST_EMA_FEATURE_VERSION",
    "PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY",
    "PRODUCTION_COST_EMA_MEASUREMENT",
    "PRODUCTION_COST_EMA_MEASUREMENT_SCHEMA_VERSION",
    "PRODUCTION_COST_EMA_METADATA",
    "PRODUCTION_COST_EMA_OUTPUT_NAME",
    "PRODUCTION_COST_EMA_PROTOCOL_DEPENDENCIES",
    "PRODUCTION_COST_EMA_PROTOCOL_SOURCE_REVISION",
    "PRODUCTION_COST_EMA_REVISION_DEPENDENCIES",
    "PRODUCTION_COST_EMA_SOURCE_PATH",
    "ProductionCostEmaMeasurement",
    "reconstruct_production_cost_ema_dependency_identity",
    "reconstruct_production_cost_ema_implementation_identity",
    "validate_production_cost_ema_definition",
)
