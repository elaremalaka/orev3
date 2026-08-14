"""Canonical RQ-003 legacy pre-finalization total winnings.

This module defines one fundamental Measurement Library family. It reads the
frozen legacy Round protocol field unchanged and contains no derived
measurement, feature set, dataset, baseline, ranking, outcome substitution,
successor-field reinterpretation, or interpretation.
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


TOTAL_WINNINGS_MEASUREMENT_SCHEMA_VERSION = 1
TOTAL_WINNINGS_FEATURE_NAME = "pre_finalization_total_winnings"
TOTAL_WINNINGS_FEATURE_VERSION = "1.0.0"
TOTAL_WINNINGS_FEATURE_GROUP = "raw_current_state"
TOTAL_WINNINGS_OUTPUT_NAME = "pre_finalization_total_winnings"
TOTAL_WINNINGS_SOURCE_PATH = "round.total_winnings"
TOTAL_WINNINGS_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_DEPENDENCY_IDENTITY_DOMAIN = "rq003-total-winnings-dependencies-v1"
_IMPLEMENTATION_IDENTITY_DOMAIN = "rq003-total-winnings-implementation-v1"
_AUTHORITY_IDENTITY_DOMAIN = "rq003-total-winnings-authority-v1"
_RATIONALE_IDENTITY_DOMAIN = "rq003-total-winnings-rationale-v1"


TOTAL_WINNINGS_PROTOCOL_DEPENDENCIES: tuple[tuple[str, str | int], ...] = (
    ("source_path", TOTAL_WINNINGS_SOURCE_PATH),
    ("source_account", "active_round_pda"),
    ("source_scalar", "unsigned_64_bit_integer"),
    ("semantic_unit", "lamports"),
    ("measurement_scope", "active_round_at_frozen_normal_observation"),
    ("protocol_semantics", "legacy_pre_finalization_total_winnings"),
    ("successor_total_returned_sol", "semantically_incompatible"),
    ("serialized_position_equivalence", "does_not_prove_semantic_identity"),
    ("finalized_value_substitution", "prohibited"),
    ("outcome_derived_replacement", "prohibited"),
    ("measurement_transformation", "identity"),
    ("supplementary_reads", "prohibited"),
    ("cross_account_repair", "prohibited"),
)

TOTAL_WINNINGS_REVISION_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("official_source_revision", TOTAL_WINNINGS_PROTOCOL_SOURCE_REVISION),
    ("semantic_regime", "legacy_total_winnings_only"),
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
        "orev3.features.rq003_total_winnings."
        "TotalWinningsMeasurement.compute",
    ),
    ("input", "context.round.total_winnings"),
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


def reconstruct_total_winnings_dependency_identity(
    protocol_dependencies: tuple[
        tuple[str, str | int], ...
    ] = TOTAL_WINNINGS_PROTOCOL_DEPENDENCIES,
    revision_dependencies: tuple[
        tuple[str, str], ...
    ] = TOTAL_WINNINGS_REVISION_DEPENDENCIES,
) -> str:
    """Reconstruct the canonical protocol/revision dependency identity."""

    validate_dependency_items("protocol_dependencies", protocol_dependencies)
    validate_dependency_items("revision_dependencies", revision_dependencies)
    return _identity(
        _DEPENDENCY_IDENTITY_DOMAIN,
        {
            "measurement_schema_version": (
                TOTAL_WINNINGS_MEASUREMENT_SCHEMA_VERSION
            ),
            "protocol_dependencies": protocol_dependencies,
            "revision_dependencies": revision_dependencies,
        },
    )


def reconstruct_total_winnings_implementation_identity(
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


TOTAL_WINNINGS_DEPENDENCY_IDENTITY = (
    reconstruct_total_winnings_dependency_identity()
)
TOTAL_WINNINGS_IMPLEMENTATION_IDENTITY = (
    reconstruct_total_winnings_implementation_identity()
)

TOTAL_WINNINGS_METADATA = FeatureMetadata(
    metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
    feature_name=TOTAL_WINNINGS_FEATURE_NAME,
    feature_version=TOTAL_WINNINGS_FEATURE_VERSION,
    feature_group=TOTAL_WINNINGS_FEATURE_GROUP,
    description=(
        "Exact protocol-published legacy Round total winnings at the frozen "
        "normal observation; the revision-scoped pre-finalization aggregate, "
        "not successor total_returned_sol."
    ),
    input_fields=(TOTAL_WINNINGS_SOURCE_PATH,),
    history_policy=FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    ),
    output_fields=(
        FeatureOutputField(
            name=TOTAL_WINNINGS_OUTPUT_NAME,
            scalar_type="integer",
            nullable=False,
            semantic_unit="lamports",
            candidate_scope="context_wide_replicated",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    ),
    missingness_policy="fail",
    determinism_contract=(
        "Return the exact non-boolean unsigned 64-bit integer published as "
        "legacy round.total_winnings in the frozen normal observation; "
        "perform no arithmetic, normalization, ranking, history access, "
        "supplementary read, cross-account repair, finalized substitution, "
        "outcome-derived replacement, successor-field reinterpretation, or "
        "interpretation."
    ),
    configuration_identity=TOTAL_WINNINGS_DEPENDENCY_IDENTITY,
    implementation_identity=TOTAL_WINNINGS_IMPLEMENTATION_IDENTITY,
    authority_references=_AUTHORITY_REFERENCES,
)

TOTAL_WINNINGS_DEFINITION = FeatureDefinition(metadata=TOTAL_WINNINGS_METADATA)

_AUTHORITY_DOCUMENT_IDENTITY = _identity(
    _AUTHORITY_IDENTITY_DOMAIN,
    {
        "authority_references": _AUTHORITY_REFERENCES,
        "measurement": TOTAL_WINNINGS_FEATURE_NAME,
    },
)
_DECISION_RATIONALE_DIGEST = _identity(
    _RATIONALE_IDENTITY_DOMAIN,
    (
        "The governing RQ-003 documents identify the exact legacy "
        "pre-finalization Round total-winnings value from the frozen normal "
        "observation as a direct, atomic, deterministic, revision-bound "
        "measurement distinct from successor total_returned_sol."
    ),
)

TOTAL_WINNINGS_ELIGIBILITY_DECISION = FeatureEligibilityDecision(
    eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    feature_name=TOTAL_WINNINGS_FEATURE_NAME,
    feature_version=TOTAL_WINNINGS_FEATURE_VERSION,
    feature_semantic_identity=TOTAL_WINNINGS_METADATA.semantic_identity,
    feature_class=TOTAL_WINNINGS_FEATURE_GROUP,
    status=FeatureEligibilityStatus.APPROVED,
    governing_concern=(
        "Exact frozen legacy pre-finalization Round aggregate only; successor "
        "total_returned_sol, finalized or outcome-derived replacement, "
        "supplementary reads, repair, history, and interpretation are "
        "prohibited."
    ),
    authority_document_identity=_AUTHORITY_DOCUMENT_IDENTITY,
    decision_rationale_digest=_DECISION_RATIONALE_DIGEST,
    effective_catalog_version=1,
)

TOTAL_WINNINGS_EXECUTABLE_BINDING_IDENTITY = (
    reconstruct_executable_binding_identity(
        TOTAL_WINNINGS_METADATA,
        TOTAL_WINNINGS_ELIGIBILITY_DECISION,
    )
)


@dataclass(frozen=True, slots=True)
class TotalWinningsMeasurement(Feature):
    """Pure identity measurement of the frozen legacy Round value."""

    name: ClassVar[str] = TOTAL_WINNINGS_FEATURE_NAME
    family: ClassVar[str] = TOTAL_WINNINGS_FEATURE_GROUP
    output_columns: ClassVar[tuple[str, ...]] = (TOTAL_WINNINGS_OUTPUT_NAME,)
    metadata: ClassVar[FeatureMetadata] = TOTAL_WINNINGS_METADATA
    definition: ClassVar[FeatureDefinition] = TOTAL_WINNINGS_DEFINITION
    eligibility_decision: ClassVar[FeatureEligibilityDecision] = (
        TOTAL_WINNINGS_ELIGIBILITY_DECISION
    )

    def compute(self, context: FeatureContext) -> FeatureValues:
        """Return the exact frozen legacy pre-finalization Round value."""

        if not isinstance(context, FeatureContext):
            raise TypeError("context must be FeatureContext")
        value = context.round.total_winnings  # type: ignore[attr-defined]
        _validate_total_winnings_value(value)
        return MappingProxyType({TOTAL_WINNINGS_OUTPUT_NAME: value})

    def canonical_output(self, context: FeatureContext) -> bytes:
        """Return the canonical encoding of the immutable output mapping."""

        return canonical_encode(self.compute(context))

    @staticmethod
    def reconstruct_canonical_output(raw: bytes) -> Mapping[str, int]:
        """Validate and reconstruct one canonical measurement output."""

        return reconstruct_single_u64_output(
            raw,
            output_name=TOTAL_WINNINGS_OUTPUT_NAME,
            artifact_name="total-winnings",
        )


TOTAL_WINNINGS_MEASUREMENT = TotalWinningsMeasurement()


def validate_total_winnings_definition() -> None:
    """Fail closed unless the complete canonical definition reconstructs."""

    metadata = TOTAL_WINNINGS_METADATA
    if (
        reconstruct_total_winnings_dependency_identity()
        != TOTAL_WINNINGS_DEPENDENCY_IDENTITY
    ):
        raise ValueError("total-winnings dependency identity mismatch")
    if metadata.configuration_identity != TOTAL_WINNINGS_DEPENDENCY_IDENTITY:
        raise ValueError("metadata does not bind canonical dependencies")
    if (
        reconstruct_total_winnings_implementation_identity()
        != TOTAL_WINNINGS_IMPLEMENTATION_IDENTITY
    ):
        raise ValueError("total-winnings implementation identity mismatch")
    if metadata.implementation_identity != TOTAL_WINNINGS_IMPLEMENTATION_IDENTITY:
        raise ValueError("metadata does not bind canonical implementation")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("total-winnings semantic identity mismatch")
    if metadata.reconstruct_definition_identity() != metadata.definition_identity:
        raise ValueError("total-winnings definition identity mismatch")
    if TOTAL_WINNINGS_DEFINITION.metadata != metadata:
        raise ValueError("definition does not bind canonical metadata")
    decision = TOTAL_WINNINGS_ELIGIBILITY_DECISION
    if (
        decision.reconstruct_eligibility_decision_identity()
        != decision.eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity mismatch")
    if (
        reconstruct_executable_binding_identity(metadata, decision)
        != TOTAL_WINNINGS_EXECUTABLE_BINDING_IDENTITY
    ):
        raise ValueError("executable binding identity mismatch")
    if tuple(field.name for field in metadata.output_fields) != (
        TOTAL_WINNINGS_OUTPUT_NAME,
    ):
        raise ValueError("total-winnings output schema is not canonical")
    if metadata.input_fields != (TOTAL_WINNINGS_SOURCE_PATH,):
        raise ValueError("total-winnings input surface is not canonical")


def _validate_total_winnings_value(value: object) -> None:
    require_u64("pre_finalization_total_winnings", value)


validate_total_winnings_definition()


__all__ = (
    "TOTAL_WINNINGS_DEFINITION",
    "TOTAL_WINNINGS_DEPENDENCY_IDENTITY",
    "TOTAL_WINNINGS_ELIGIBILITY_DECISION",
    "TOTAL_WINNINGS_EXECUTABLE_BINDING_IDENTITY",
    "TOTAL_WINNINGS_FEATURE_GROUP",
    "TOTAL_WINNINGS_FEATURE_NAME",
    "TOTAL_WINNINGS_FEATURE_VERSION",
    "TOTAL_WINNINGS_IMPLEMENTATION_IDENTITY",
    "TOTAL_WINNINGS_MEASUREMENT",
    "TOTAL_WINNINGS_MEASUREMENT_SCHEMA_VERSION",
    "TOTAL_WINNINGS_METADATA",
    "TOTAL_WINNINGS_OUTPUT_NAME",
    "TOTAL_WINNINGS_PROTOCOL_DEPENDENCIES",
    "TOTAL_WINNINGS_PROTOCOL_SOURCE_REVISION",
    "TOTAL_WINNINGS_REVISION_DEPENDENCIES",
    "TOTAL_WINNINGS_SOURCE_PATH",
    "TotalWinningsMeasurement",
    "reconstruct_total_winnings_dependency_identity",
    "reconstruct_total_winnings_implementation_identity",
    "validate_total_winnings_definition",
)
