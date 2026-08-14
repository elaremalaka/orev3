"""Canonical RQ-003 protocol-published Treasury motherlode.

This module defines one fundamental Measurement Library family. It reads the
frozen Treasury protocol field unchanged and contains no derived measurement,
feature set, dataset, baseline, ranking, or interpretation.
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


TREASURY_MOTHERLODE_MEASUREMENT_SCHEMA_VERSION = 1
TREASURY_MOTHERLODE_FEATURE_NAME = "treasury_motherlode"
TREASURY_MOTHERLODE_FEATURE_VERSION = "1.0.0"
TREASURY_MOTHERLODE_FEATURE_GROUP = "raw_current_state"
TREASURY_MOTHERLODE_OUTPUT_NAME = "treasury_motherlode"
TREASURY_MOTHERLODE_SOURCE_PATH = "treasury.motherlode"
TREASURY_MOTHERLODE_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_DEPENDENCY_IDENTITY_DOMAIN = "rq003-treasury-motherlode-dependencies-v1"
_IMPLEMENTATION_IDENTITY_DOMAIN = "rq003-treasury-motherlode-implementation-v1"
_AUTHORITY_IDENTITY_DOMAIN = "rq003-treasury-motherlode-authority-v1"
_RATIONALE_IDENTITY_DOMAIN = "rq003-treasury-motherlode-rationale-v1"


TREASURY_MOTHERLODE_PROTOCOL_DEPENDENCIES: tuple[
    tuple[str, str | int], ...
] = (
    ("source_path", TREASURY_MOTHERLODE_SOURCE_PATH),
    ("source_account", "singleton_treasury"),
    ("source_scalar", "unsigned_64_bit_integer"),
    ("semantic_unit", "indivisible_ore_units"),
    ("measurement_scope", "treasury_at_frozen_normal_observation"),
    ("protocol_semantics", "live_motherlode_rewards_pool"),
    ("lifecycle_position", "post_previous_reset_decision_time_value"),
    ("active_round_payout_field", "not_represented"),
    ("measurement_transformation", "identity"),
    ("supplementary_reads", "prohibited"),
    ("cross_account_repair", "prohibited"),
)

TREASURY_MOTHERLODE_REVISION_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    (
        "official_source_revision",
        TREASURY_MOTHERLODE_PROTOCOL_SOURCE_REVISION,
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
        "orev3.features.rq003_treasury_motherlode."
        "TreasuryMotherlodeMeasurement.compute",
    ),
    ("input", "context.treasury.motherlode"),
    ("input_validation", "exact_non_boolean_u64"),
    ("output", "immutable_single_integer_mapping"),
    ("transformation", "identity"),
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


def reconstruct_treasury_motherlode_dependency_identity(
    protocol_dependencies: tuple[
        tuple[str, str | int], ...
    ] = TREASURY_MOTHERLODE_PROTOCOL_DEPENDENCIES,
    revision_dependencies: tuple[
        tuple[str, str], ...
    ] = TREASURY_MOTHERLODE_REVISION_DEPENDENCIES,
) -> str:
    """Reconstruct the canonical protocol/revision dependency identity."""

    validate_dependency_items("protocol_dependencies", protocol_dependencies)
    validate_dependency_items("revision_dependencies", revision_dependencies)
    return _identity(
        _DEPENDENCY_IDENTITY_DOMAIN,
        {
            "measurement_schema_version": (
                TREASURY_MOTHERLODE_MEASUREMENT_SCHEMA_VERSION
            ),
            "protocol_dependencies": protocol_dependencies,
            "revision_dependencies": revision_dependencies,
        },
    )


def reconstruct_treasury_motherlode_implementation_identity(
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


TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY = (
    reconstruct_treasury_motherlode_dependency_identity()
)
TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY = (
    reconstruct_treasury_motherlode_implementation_identity()
)

TREASURY_MOTHERLODE_METADATA = FeatureMetadata(
    metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
    feature_name=TREASURY_MOTHERLODE_FEATURE_NAME,
    feature_version=TREASURY_MOTHERLODE_FEATURE_VERSION,
    feature_group=TREASURY_MOTHERLODE_FEATURE_GROUP,
    description=(
        "Exact protocol-published Treasury motherlode at the frozen normal "
        "observation; the post-previous-reset live pool, not the active "
        "Round payout field."
    ),
    input_fields=(TREASURY_MOTHERLODE_SOURCE_PATH,),
    history_policy=FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    ),
    output_fields=(
        FeatureOutputField(
            name=TREASURY_MOTHERLODE_OUTPUT_NAME,
            scalar_type="integer",
            nullable=False,
            semantic_unit="indivisible_ore_units",
            candidate_scope="context_wide_replicated",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    ),
    missingness_policy="fail",
    determinism_contract=(
        "Return the exact non-boolean unsigned 64-bit integer published as "
        "treasury.motherlode in the frozen normal observation; perform no "
        "arithmetic, normalization, ranking, history access, supplementary "
        "read, cross-account repair, or interpretation."
    ),
    configuration_identity=TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY,
    implementation_identity=TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY,
    authority_references=_AUTHORITY_REFERENCES,
)

TREASURY_MOTHERLODE_DEFINITION = FeatureDefinition(
    metadata=TREASURY_MOTHERLODE_METADATA
)

_AUTHORITY_DOCUMENT_IDENTITY = _identity(
    _AUTHORITY_IDENTITY_DOMAIN,
    {
        "authority_references": _AUTHORITY_REFERENCES,
        "measurement": TREASURY_MOTHERLODE_FEATURE_NAME,
    },
)
_DECISION_RATIONALE_DIGEST = _identity(
    _RATIONALE_IDENTITY_DOMAIN,
    (
        "The governing RQ-003 documents identify the exact Treasury live "
        "motherlode pool at the frozen normal observation as a direct, "
        "atomic, deterministic, revision-bound treasury-state measurement."
    ),
)

TREASURY_MOTHERLODE_ELIGIBILITY_DECISION = FeatureEligibilityDecision(
    eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    feature_name=TREASURY_MOTHERLODE_FEATURE_NAME,
    feature_version=TREASURY_MOTHERLODE_FEATURE_VERSION,
    feature_semantic_identity=TREASURY_MOTHERLODE_METADATA.semantic_identity,
    feature_class=TREASURY_MOTHERLODE_FEATURE_GROUP,
    status=FeatureEligibilityStatus.APPROVED,
    governing_concern=(
        "Exact frozen Treasury live-pool value only; active-Round payout "
        "semantics, supplementary reads, later-value substitution, repair, "
        "history, and interpretation are prohibited."
    ),
    authority_document_identity=_AUTHORITY_DOCUMENT_IDENTITY,
    decision_rationale_digest=_DECISION_RATIONALE_DIGEST,
    effective_catalog_version=1,
)

TREASURY_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY = (
    reconstruct_executable_binding_identity(
        TREASURY_MOTHERLODE_METADATA,
        TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    )
)


@dataclass(frozen=True, slots=True)
class TreasuryMotherlodeMeasurement(Feature):
    """Pure identity measurement of the frozen Treasury protocol value."""

    name: ClassVar[str] = TREASURY_MOTHERLODE_FEATURE_NAME
    family: ClassVar[str] = TREASURY_MOTHERLODE_FEATURE_GROUP
    output_columns: ClassVar[tuple[str, ...]] = (
        TREASURY_MOTHERLODE_OUTPUT_NAME,
    )
    metadata: ClassVar[FeatureMetadata] = TREASURY_MOTHERLODE_METADATA
    definition: ClassVar[FeatureDefinition] = TREASURY_MOTHERLODE_DEFINITION
    eligibility_decision: ClassVar[FeatureEligibilityDecision] = (
        TREASURY_MOTHERLODE_ELIGIBILITY_DECISION
    )

    def compute(self, context: FeatureContext) -> FeatureValues:
        """Return the exact frozen Treasury value without interpretation."""

        if not isinstance(context, FeatureContext):
            raise TypeError("context must be FeatureContext")
        value = context.treasury.motherlode  # type: ignore[attr-defined]
        _validate_treasury_motherlode_value(value)
        return MappingProxyType({TREASURY_MOTHERLODE_OUTPUT_NAME: value})

    def canonical_output(self, context: FeatureContext) -> bytes:
        """Return the canonical encoding of the immutable output mapping."""

        return canonical_encode(self.compute(context))

    @staticmethod
    def reconstruct_canonical_output(raw: bytes) -> Mapping[str, int]:
        """Validate and reconstruct one canonical measurement output."""

        return reconstruct_single_u64_output(
            raw,
            output_name=TREASURY_MOTHERLODE_OUTPUT_NAME,
            artifact_name="treasury-motherlode",
        )


TREASURY_MOTHERLODE_MEASUREMENT = TreasuryMotherlodeMeasurement()


def validate_treasury_motherlode_definition() -> None:
    """Fail closed unless the complete canonical definition reconstructs."""

    metadata = TREASURY_MOTHERLODE_METADATA
    if (
        reconstruct_treasury_motherlode_dependency_identity()
        != TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY
    ):
        raise ValueError("Treasury motherlode dependency identity mismatch")
    if metadata.configuration_identity != TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY:
        raise ValueError("metadata does not bind canonical dependencies")
    if (
        reconstruct_treasury_motherlode_implementation_identity()
        != TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("Treasury motherlode implementation identity mismatch")
    if (
        metadata.implementation_identity
        != TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("metadata does not bind canonical implementation")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("Treasury motherlode semantic identity mismatch")
    if metadata.reconstruct_definition_identity() != metadata.definition_identity:
        raise ValueError("Treasury motherlode definition identity mismatch")
    if TREASURY_MOTHERLODE_DEFINITION.metadata != metadata:
        raise ValueError("definition does not bind canonical metadata")
    decision = TREASURY_MOTHERLODE_ELIGIBILITY_DECISION
    if (
        decision.reconstruct_eligibility_decision_identity()
        != decision.eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity mismatch")
    if (
        reconstruct_executable_binding_identity(metadata, decision)
        != TREASURY_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY
    ):
        raise ValueError("executable binding identity mismatch")
    if tuple(field.name for field in metadata.output_fields) != (
        TREASURY_MOTHERLODE_OUTPUT_NAME,
    ):
        raise ValueError("Treasury motherlode output schema is not canonical")
    if metadata.input_fields != (TREASURY_MOTHERLODE_SOURCE_PATH,):
        raise ValueError("Treasury motherlode input surface is not canonical")


def _validate_treasury_motherlode_value(value: object) -> None:
    require_u64("treasury_motherlode", value)


validate_treasury_motherlode_definition()


__all__ = (
    "TREASURY_MOTHERLODE_DEFINITION",
    "TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY",
    "TREASURY_MOTHERLODE_ELIGIBILITY_DECISION",
    "TREASURY_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY",
    "TREASURY_MOTHERLODE_FEATURE_GROUP",
    "TREASURY_MOTHERLODE_FEATURE_NAME",
    "TREASURY_MOTHERLODE_FEATURE_VERSION",
    "TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY",
    "TREASURY_MOTHERLODE_MEASUREMENT",
    "TREASURY_MOTHERLODE_MEASUREMENT_SCHEMA_VERSION",
    "TREASURY_MOTHERLODE_METADATA",
    "TREASURY_MOTHERLODE_OUTPUT_NAME",
    "TREASURY_MOTHERLODE_PROTOCOL_DEPENDENCIES",
    "TREASURY_MOTHERLODE_PROTOCOL_SOURCE_REVISION",
    "TREASURY_MOTHERLODE_REVISION_DEPENDENCIES",
    "TREASURY_MOTHERLODE_SOURCE_PATH",
    "TreasuryMotherlodeMeasurement",
    "reconstruct_treasury_motherlode_dependency_identity",
    "reconstruct_treasury_motherlode_implementation_identity",
    "validate_treasury_motherlode_definition",
)
