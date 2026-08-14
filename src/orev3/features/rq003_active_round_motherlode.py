"""Canonical RQ-003 protocol-published Active-Round motherlode.

This module defines one fundamental Measurement Library family. It reads the
frozen pre-finalization Round field unchanged and contains no derived
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


ACTIVE_ROUND_MOTHERLODE_MEASUREMENT_SCHEMA_VERSION = 1
ACTIVE_ROUND_MOTHERLODE_FEATURE_NAME = "active_round_motherlode"
ACTIVE_ROUND_MOTHERLODE_FEATURE_VERSION = "1.0.0"
ACTIVE_ROUND_MOTHERLODE_FEATURE_GROUP = "raw_current_state"
ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME = "active_round_motherlode"
ACTIVE_ROUND_MOTHERLODE_SOURCE_PATH = "round.motherlode"
ACTIVE_ROUND_MOTHERLODE_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_DEPENDENCY_IDENTITY_DOMAIN = "rq003-active-round-motherlode-dependencies-v1"
_IMPLEMENTATION_IDENTITY_DOMAIN = (
    "rq003-active-round-motherlode-implementation-v1"
)
_AUTHORITY_IDENTITY_DOMAIN = "rq003-active-round-motherlode-authority-v1"
_RATIONALE_IDENTITY_DOMAIN = "rq003-active-round-motherlode-rationale-v1"


ACTIVE_ROUND_MOTHERLODE_PROTOCOL_DEPENDENCIES: tuple[
    tuple[str, str | int], ...
] = (
    ("source_path", ACTIVE_ROUND_MOTHERLODE_SOURCE_PATH),
    ("source_account", "active_round_pda"),
    ("source_scalar", "unsigned_64_bit_integer"),
    ("semantic_unit", "indivisible_ore_units"),
    ("measurement_scope", "active_round_at_frozen_normal_observation"),
    ("protocol_semantics", "initialized_pre_finalization_payout_field"),
    ("active_decision_value", "zero"),
    ("live_treasury_pool", "not_represented"),
    ("finalized_nonzero_value", "outcome_information_prohibited"),
    ("measurement_transformation", "identity"),
    ("supplementary_reads", "prohibited"),
    ("cross_account_repair", "prohibited"),
)

ACTIVE_ROUND_MOTHERLODE_REVISION_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    (
        "official_source_revision",
        ACTIVE_ROUND_MOTHERLODE_PROTOCOL_SOURCE_REVISION,
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
        "orev3.features.rq003_active_round_motherlode."
        "ActiveRoundMotherlodeMeasurement.compute",
    ),
    ("input", "context.round.motherlode"),
    ("input_validation", "exact_pre_finalization_zero_u64"),
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


def reconstruct_active_round_motherlode_dependency_identity(
    protocol_dependencies: tuple[
        tuple[str, str | int], ...
    ] = ACTIVE_ROUND_MOTHERLODE_PROTOCOL_DEPENDENCIES,
    revision_dependencies: tuple[
        tuple[str, str], ...
    ] = ACTIVE_ROUND_MOTHERLODE_REVISION_DEPENDENCIES,
) -> str:
    """Reconstruct the canonical protocol/revision dependency identity."""

    validate_dependency_items("protocol_dependencies", protocol_dependencies)
    validate_dependency_items("revision_dependencies", revision_dependencies)
    return _identity(
        _DEPENDENCY_IDENTITY_DOMAIN,
        {
            "measurement_schema_version": (
                ACTIVE_ROUND_MOTHERLODE_MEASUREMENT_SCHEMA_VERSION
            ),
            "protocol_dependencies": protocol_dependencies,
            "revision_dependencies": revision_dependencies,
        },
    )


def reconstruct_active_round_motherlode_implementation_identity(
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


ACTIVE_ROUND_MOTHERLODE_DEPENDENCY_IDENTITY = (
    reconstruct_active_round_motherlode_dependency_identity()
)
ACTIVE_ROUND_MOTHERLODE_IMPLEMENTATION_IDENTITY = (
    reconstruct_active_round_motherlode_implementation_identity()
)

ACTIVE_ROUND_MOTHERLODE_METADATA = FeatureMetadata(
    metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
    feature_name=ACTIVE_ROUND_MOTHERLODE_FEATURE_NAME,
    feature_version=ACTIVE_ROUND_MOTHERLODE_FEATURE_VERSION,
    feature_group=ACTIVE_ROUND_MOTHERLODE_FEATURE_GROUP,
    description=(
        "Exact protocol-published active Round motherlode at the frozen "
        "normal observation; the initialized pre-finalization payout field, "
        "not the live Treasury pool."
    ),
    input_fields=(ACTIVE_ROUND_MOTHERLODE_SOURCE_PATH,),
    history_policy=FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    ),
    output_fields=(
        FeatureOutputField(
            name=ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME,
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
        "round.motherlode in the frozen normal observation, accepting only "
        "the pre-finalization decision-time value zero; perform no arithmetic, "
        "normalization, ranking, history access, supplementary read, "
        "cross-account repair, or interpretation."
    ),
    configuration_identity=ACTIVE_ROUND_MOTHERLODE_DEPENDENCY_IDENTITY,
    implementation_identity=ACTIVE_ROUND_MOTHERLODE_IMPLEMENTATION_IDENTITY,
    authority_references=_AUTHORITY_REFERENCES,
)

ACTIVE_ROUND_MOTHERLODE_DEFINITION = FeatureDefinition(
    metadata=ACTIVE_ROUND_MOTHERLODE_METADATA
)

_AUTHORITY_DOCUMENT_IDENTITY = _identity(
    _AUTHORITY_IDENTITY_DOMAIN,
    {
        "authority_references": _AUTHORITY_REFERENCES,
        "measurement": ACTIVE_ROUND_MOTHERLODE_FEATURE_NAME,
    },
)
_DECISION_RATIONALE_DIGEST = _identity(
    _RATIONALE_IDENTITY_DOMAIN,
    (
        "The governing RQ-003 documents identify the active Round's exact "
        "initialized pre-finalization motherlode payout field at the frozen "
        "normal observation as a direct, atomic, deterministic, "
        "revision-bound protocol-state measurement."
    ),
)

ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION = FeatureEligibilityDecision(
    eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    feature_name=ACTIVE_ROUND_MOTHERLODE_FEATURE_NAME,
    feature_version=ACTIVE_ROUND_MOTHERLODE_FEATURE_VERSION,
    feature_semantic_identity=(
        ACTIVE_ROUND_MOTHERLODE_METADATA.semantic_identity
    ),
    feature_class=ACTIVE_ROUND_MOTHERLODE_FEATURE_GROUP,
    status=FeatureEligibilityStatus.APPROVED,
    governing_concern=(
        "Exact frozen active-Round pre-finalization value only; finalized "
        "nonzero payout state, Treasury pool semantics, supplementary reads, "
        "repair, history, and interpretation are prohibited."
    ),
    authority_document_identity=_AUTHORITY_DOCUMENT_IDENTITY,
    decision_rationale_digest=_DECISION_RATIONALE_DIGEST,
    effective_catalog_version=1,
)

ACTIVE_ROUND_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY = (
    reconstruct_executable_binding_identity(
        ACTIVE_ROUND_MOTHERLODE_METADATA,
        ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION,
    )
)


@dataclass(frozen=True, slots=True)
class ActiveRoundMotherlodeMeasurement(Feature):
    """Pure identity measurement of the frozen active-Round field."""

    name: ClassVar[str] = ACTIVE_ROUND_MOTHERLODE_FEATURE_NAME
    family: ClassVar[str] = ACTIVE_ROUND_MOTHERLODE_FEATURE_GROUP
    output_columns: ClassVar[tuple[str, ...]] = (
        ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME,
    )
    metadata: ClassVar[FeatureMetadata] = ACTIVE_ROUND_MOTHERLODE_METADATA
    definition: ClassVar[FeatureDefinition] = (
        ACTIVE_ROUND_MOTHERLODE_DEFINITION
    )
    eligibility_decision: ClassVar[FeatureEligibilityDecision] = (
        ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION
    )

    def compute(self, context: FeatureContext) -> FeatureValues:
        """Return the exact frozen pre-finalization Round value."""

        if not isinstance(context, FeatureContext):
            raise TypeError("context must be FeatureContext")
        value = context.round.motherlode  # type: ignore[attr-defined]
        _validate_active_round_motherlode_value(value)
        return MappingProxyType({ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME: value})

    def canonical_output(self, context: FeatureContext) -> bytes:
        """Return the canonical encoding of the immutable output mapping."""

        return canonical_encode(self.compute(context))

    @staticmethod
    def reconstruct_canonical_output(raw: bytes) -> Mapping[str, int]:
        """Validate and reconstruct one canonical measurement output."""

        reconstructed = reconstruct_single_u64_output(
            raw,
            output_name=ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME,
            artifact_name="active-round-motherlode",
        )
        _validate_active_round_motherlode_value(
            reconstructed[ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME]
        )
        return reconstructed


ACTIVE_ROUND_MOTHERLODE_MEASUREMENT = ActiveRoundMotherlodeMeasurement()


def validate_active_round_motherlode_definition() -> None:
    """Fail closed unless the complete canonical definition reconstructs."""

    metadata = ACTIVE_ROUND_MOTHERLODE_METADATA
    if (
        reconstruct_active_round_motherlode_dependency_identity()
        != ACTIVE_ROUND_MOTHERLODE_DEPENDENCY_IDENTITY
    ):
        raise ValueError("active-Round motherlode dependency identity mismatch")
    if (
        metadata.configuration_identity
        != ACTIVE_ROUND_MOTHERLODE_DEPENDENCY_IDENTITY
    ):
        raise ValueError("metadata does not bind canonical dependencies")
    if (
        reconstruct_active_round_motherlode_implementation_identity()
        != ACTIVE_ROUND_MOTHERLODE_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("active-Round motherlode implementation identity mismatch")
    if (
        metadata.implementation_identity
        != ACTIVE_ROUND_MOTHERLODE_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("metadata does not bind canonical implementation")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("active-Round motherlode semantic identity mismatch")
    if metadata.reconstruct_definition_identity() != metadata.definition_identity:
        raise ValueError("active-Round motherlode definition identity mismatch")
    if ACTIVE_ROUND_MOTHERLODE_DEFINITION.metadata != metadata:
        raise ValueError("definition does not bind canonical metadata")
    decision = ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION
    if (
        decision.reconstruct_eligibility_decision_identity()
        != decision.eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity mismatch")
    if (
        reconstruct_executable_binding_identity(metadata, decision)
        != ACTIVE_ROUND_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY
    ):
        raise ValueError("executable binding identity mismatch")
    if tuple(field.name for field in metadata.output_fields) != (
        ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME,
    ):
        raise ValueError("active-Round motherlode output schema is not canonical")
    if metadata.input_fields != (ACTIVE_ROUND_MOTHERLODE_SOURCE_PATH,):
        raise ValueError("active-Round motherlode input surface is not canonical")


def _validate_active_round_motherlode_value(value: object) -> None:
    require_u64("active_round_motherlode", value)
    if value != 0:
        raise ValueError(
            "active_round_motherlode must be the pre-finalization "
            "decision-time value zero"
        )


validate_active_round_motherlode_definition()


__all__ = (
    "ACTIVE_ROUND_MOTHERLODE_DEFINITION",
    "ACTIVE_ROUND_MOTHERLODE_DEPENDENCY_IDENTITY",
    "ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION",
    "ACTIVE_ROUND_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY",
    "ACTIVE_ROUND_MOTHERLODE_FEATURE_GROUP",
    "ACTIVE_ROUND_MOTHERLODE_FEATURE_NAME",
    "ACTIVE_ROUND_MOTHERLODE_FEATURE_VERSION",
    "ACTIVE_ROUND_MOTHERLODE_IMPLEMENTATION_IDENTITY",
    "ACTIVE_ROUND_MOTHERLODE_MEASUREMENT",
    "ACTIVE_ROUND_MOTHERLODE_MEASUREMENT_SCHEMA_VERSION",
    "ACTIVE_ROUND_MOTHERLODE_METADATA",
    "ACTIVE_ROUND_MOTHERLODE_OUTPUT_NAME",
    "ACTIVE_ROUND_MOTHERLODE_PROTOCOL_DEPENDENCIES",
    "ACTIVE_ROUND_MOTHERLODE_PROTOCOL_SOURCE_REVISION",
    "ACTIVE_ROUND_MOTHERLODE_REVISION_DEPENDENCIES",
    "ACTIVE_ROUND_MOTHERLODE_SOURCE_PATH",
    "ActiveRoundMotherlodeMeasurement",
    "reconstruct_active_round_motherlode_dependency_identity",
    "reconstruct_active_round_motherlode_implementation_identity",
    "validate_active_round_motherlode_definition",
)
