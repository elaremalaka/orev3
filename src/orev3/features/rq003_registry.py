"""Immutable RQ-003 eligibility catalog and frozen feature registry.

This module implements Phase 2 contracts only. Definitions contain immutable
metadata, not computation. The registry establishes eligibility, ordering,
ownership, and identity; it does not execute features or produce vectors.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from orev3.features.rq003_contracts import (
    FeatureEligibilityDecision,
    FeatureEligibilityStatus,
    FeatureMetadata,
    FeatureOutputField,
    canonical_encode,
    reconstruct_executable_binding_identity,
)


ELIGIBILITY_CATALOG_SCHEMA_VERSION = 1
FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION = 1
FEATURE_SET_SCHEMA_VERSION = 1

_CATALOG_IDENTITY_DOMAIN = "rq003-eligibility-catalog-v1"
_REGISTRY_IDENTITY_DOMAIN = "rq003-frozen-feature-registry-v1"
_FEATURE_SET_IDENTITY_DOMAIN = "rq003-feature-set-v1"
_REGISTRY_VALIDATION_IDENTITY_DOMAIN = "rq003-registry-validation-v1"

# These sources are never feature-visible under RQ-003. Absolute slots are
# intentionally absent: an approved relative-timing definition may read them
# as structural inputs without exposing them as output values.
_PROHIBITED_INPUT_SEGMENTS = frozenset(
    {
        "capture_mode",
        "collector_session_id",
        "collector_process_identity",
        "coverage_status",
        "created_at",
        "dataset_identity",
        "dataset_path",
        "deployment_decision",
        "economic_result",
        "economic_state",
        "enrichment",
        "evaluation_result",
        "exact_match",
        "finalized",
        "finalized_outcome",
        "future_observation",
        "lifecycle_completeness",
        "mass",
        "observation_count",
        "observation_index",
        "observed_at_utc",
        "outcome",
        "outcome_available",
        "outcome_source",
        "replay_selection",
        "replay_identity",
        "rfc012_evidence",
        "round_id",
        "round_observation_count",
        "round_progress",
        "slot_distance",
        "source_file",
        "source_line",
        "source_path",
        "square_identifier",
        "square_index",
        "tolerance",
        "top_miner",
        "winning_square",
        "won",
    }
)
_PROHIBITED_OUTPUT_NAMES = _PROHIBITED_INPUT_SEGMENTS.union(
    {
        "end_slot",
        "expires_at",
        "rpc_slot",
        "start_slot",
    }
)


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    """One immutable feature definition contract without computation."""

    metadata: FeatureMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, FeatureMetadata):
            raise TypeError("metadata must be FeatureMetadata")
        _validate_metadata_identity(self.metadata)

    @property
    def feature_name(self) -> str:
        return self.metadata.feature_name

    @property
    def feature_group(self) -> str:
        return self.metadata.feature_group

    @property
    def semantic_identity(self) -> str:
        return self.metadata.semantic_identity

    @property
    def definition_identity(self) -> str:
        return self.metadata.definition_identity

    @property
    def output_fields(self) -> tuple[FeatureOutputField, ...]:
        return self.metadata.output_fields


@dataclass(frozen=True, slots=True)
class EligibilityCatalog:
    """Immutable append-only history of RQ-003 eligibility decisions."""

    catalog_schema_version: int
    decisions: tuple[FeatureEligibilityDecision, ...]
    catalog_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema_version(
            "catalog_schema_version",
            self.catalog_schema_version,
            ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        )
        if not isinstance(self.decisions, tuple):
            raise TypeError("decisions must be an immutable tuple")
        if not all(
            isinstance(decision, FeatureEligibilityDecision)
            for decision in self.decisions
        ):
            raise TypeError(
                "decisions must contain only FeatureEligibilityDecision values"
            )

        _validate_decision_history(self.decisions)
        object.__setattr__(
            self,
            "catalog_identity",
            self.reconstruct_catalog_identity(),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "catalog_schema_version": self.catalog_schema_version,
            "ordered_eligibility_decision_identities": tuple(
                decision.eligibility_decision_identity
                for decision in self.decisions
            ),
        }

    def reconstruct_catalog_identity(self) -> str:
        return _identity(
            _CATALOG_IDENTITY_DOMAIN,
            self.to_identity_material(),
        )

    def decision_history(
        self,
        feature_semantic_identity: str,
    ) -> tuple[FeatureEligibilityDecision, ...]:
        history = tuple(
            decision
            for decision in self.decisions
            if decision.feature_semantic_identity
            == feature_semantic_identity
        )
        if not history:
            raise ValueError("feature semantic identity is unknown")
        return history

    def resolve_terminal(
        self,
        feature_semantic_identity: str,
    ) -> FeatureEligibilityDecision:
        history = self.decision_history(feature_semantic_identity)
        superseded = {
            decision.superseded_decision_identity
            for decision in history
            if decision.superseded_decision_identity is not None
        }
        terminal = tuple(
            decision
            for decision in history
            if decision.eligibility_decision_identity not in superseded
        )
        if len(terminal) != 1:
            raise ValueError(
                "feature semantics do not have exactly one terminal decision"
            )
        return terminal[0]

    def append(
        self,
        decision: FeatureEligibilityDecision,
    ) -> EligibilityCatalog:
        """Return a new catalog whose only change is one appended decision."""

        if not isinstance(decision, FeatureEligibilityDecision):
            raise TypeError("decision must be FeatureEligibilityDecision")
        if (
            self.decisions
            and decision.effective_catalog_version
            < self.decisions[-1].effective_catalog_version
        ):
            raise ValueError(
                "appended decision cannot move catalog version backward"
            )
        matching = tuple(
            item
            for item in self.decisions
            if item.feature_semantic_identity
            == decision.feature_semantic_identity
        )
        if matching:
            terminal = self.resolve_terminal(
                decision.feature_semantic_identity
            )
            if (
                decision.superseded_decision_identity
                != terminal.eligibility_decision_identity
            ):
                raise ValueError(
                    "appended decision must supersede the current terminal"
                )
            if (
                decision.effective_catalog_version
                <= terminal.effective_catalog_version
            ):
                raise ValueError(
                    "a superseding decision requires a later catalog version"
                )
        elif decision.superseded_decision_identity is not None:
            raise ValueError(
                "a new semantic history cannot name a predecessor"
            )
        return EligibilityCatalog(
            catalog_schema_version=self.catalog_schema_version,
            decisions=self.decisions + (decision,),
        )


@dataclass(frozen=True, slots=True)
class FrozenFeatureRegistry:
    """Explicitly ordered immutable registry of terminal-approved definitions."""

    registry_schema_version: int
    eligibility_catalog: EligibilityCatalog
    definitions: tuple[FeatureDefinition, ...]
    ordered_executable_feature_identities: tuple[str, ...] = field(init=False)
    ordered_output_fields: tuple[FeatureOutputField, ...] = field(init=False)
    output_owner_items: tuple[tuple[str, str], ...] = field(init=False)
    ordered_groups: tuple[str, ...] = field(init=False)
    registry_identity: str = field(init=False)
    feature_set_identity: str = field(init=False)
    validation_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema_version(
            "registry_schema_version",
            self.registry_schema_version,
            FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        )
        if not isinstance(self.eligibility_catalog, EligibilityCatalog):
            raise TypeError(
                "eligibility_catalog must be EligibilityCatalog"
            )
        if (
            self.eligibility_catalog.reconstruct_catalog_identity()
            != self.eligibility_catalog.catalog_identity
        ):
            raise ValueError("eligibility catalog identity does not reconstruct")
        if not isinstance(self.definitions, tuple):
            raise TypeError("definitions must be an immutable tuple")
        if not self.definitions:
            raise ValueError("definitions cannot be empty")
        if not all(
            isinstance(definition, FeatureDefinition)
            for definition in self.definitions
        ):
            raise TypeError(
                "definitions must contain only FeatureDefinition values"
            )

        names: set[str] = set()
        semantic_identities: set[str] = set()
        definition_identities: set[str] = set()
        output_names: set[str] = set()
        executable_identity_set: set[str] = set()
        executable_identities: list[str] = []
        output_fields: list[FeatureOutputField] = []
        output_owners: list[tuple[str, str]] = []
        groups: list[str] = []

        for definition in self.definitions:
            metadata = definition.metadata
            _validate_metadata_identity(metadata)
            _reject_duplicate(
                "feature name", metadata.feature_name, names
            )
            _reject_duplicate(
                "feature semantic identity",
                metadata.semantic_identity,
                semantic_identities,
            )
            _reject_duplicate(
                "feature definition identity",
                metadata.definition_identity,
                definition_identities,
            )
            _validate_registration_schema(metadata)

            terminal = self.eligibility_catalog.resolve_terminal(
                metadata.semantic_identity
            )
            executable_identity = reconstruct_executable_binding_identity(
                metadata,
                terminal,
            )
            _reject_duplicate(
                "executable feature identity",
                executable_identity,
                executable_identity_set,
            )
            executable_identities.append(executable_identity)

            if metadata.feature_group not in groups:
                groups.append(metadata.feature_group)
            for output_field in metadata.output_fields:
                _reject_duplicate(
                    "feature output name",
                    output_field.name,
                    output_names,
                )
                output_fields.append(output_field)
                output_owners.append(
                    (output_field.name, metadata.definition_identity)
                )

        object.__setattr__(
            self,
            "ordered_executable_feature_identities",
            tuple(executable_identities),
        )
        object.__setattr__(self, "ordered_output_fields", tuple(output_fields))
        object.__setattr__(self, "output_owner_items", tuple(output_owners))
        object.__setattr__(self, "ordered_groups", tuple(groups))
        object.__setattr__(
            self,
            "registry_identity",
            self.reconstruct_registry_identity(),
        )
        object.__setattr__(
            self,
            "feature_set_identity",
            self.reconstruct_feature_set_identity(),
        )
        object.__setattr__(
            self,
            "validation_identity",
            self.reconstruct_validation_identity(),
        )

    @property
    def output_owners(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.output_owner_items))

    def to_registry_identity_material(self) -> dict[str, Any]:
        return {
            "eligibility_catalog_identity": (
                self.eligibility_catalog.catalog_identity
            ),
            "ordered_executable_feature_identities": (
                self.ordered_executable_feature_identities
            ),
            "registry_schema_version": self.registry_schema_version,
        }

    def reconstruct_registry_identity(self) -> str:
        return _identity(
            _REGISTRY_IDENTITY_DOMAIN,
            self.to_registry_identity_material(),
        )

    def to_feature_set_identity_material(self) -> dict[str, Any]:
        return {
            "feature_set_schema_version": FEATURE_SET_SCHEMA_VERSION,
            "ordered_feature_configurations": tuple(
                {
                    "definition_identity": definition.definition_identity,
                    "history_configuration_identity": (
                        definition.metadata.history_policy.configuration_identity
                    ),
                    "metadata_configuration_identity": (
                        definition.metadata.configuration_identity
                    ),
                }
                for definition in self.definitions
            ),
            "ordered_output_schema": tuple(
                output.to_identity_material()
                for output in self.ordered_output_fields
            ),
            "registry_identity": self.registry_identity,
        }

    def reconstruct_feature_set_identity(self) -> str:
        return _identity(
            _FEATURE_SET_IDENTITY_DOMAIN,
            self.to_feature_set_identity_material(),
        )

    def reconstruct_validation_identity(self) -> str:
        return _identity(
            _REGISTRY_VALIDATION_IDENTITY_DOMAIN,
            {
                "catalog_identity_reconstructed": True,
                "definition_count": len(self.definitions),
                "eligibility_resolved": True,
                "feature_set_identity": self.feature_set_identity,
                "identity_validation_complete": True,
                "output_count": len(self.ordered_output_fields),
                "output_ownership_unique": True,
                "registry_identity": self.registry_identity,
                "schema_validation_complete": True,
            },
        )


def _validate_decision_history(
    decisions: tuple[FeatureEligibilityDecision, ...],
) -> None:
    identities = tuple(
        decision.eligibility_decision_identity for decision in decisions
    )
    if len(identities) != len(set(identities)):
        raise ValueError("eligibility decision identities must be unique")

    by_identity = dict(zip(identities, decisions, strict=True))
    index_by_identity = {
        identity: index for index, identity in enumerate(identities)
    }
    prior_catalog_version: int | None = None
    for decision in decisions:
        if (
            prior_catalog_version is not None
            and decision.effective_catalog_version < prior_catalog_version
        ):
            raise ValueError(
                "eligibility catalog versions must be nondecreasing"
            )
        prior_catalog_version = decision.effective_catalog_version
        predecessor = decision.superseded_decision_identity
        if predecessor is not None and predecessor not in by_identity:
            raise ValueError("eligibility decision predecessor is missing")

    _reject_decision_cycles(decisions, by_identity)

    child_count: dict[str, int] = {}
    by_semantic: dict[str, list[FeatureEligibilityDecision]] = {}
    for decision in decisions:
        by_semantic.setdefault(
            decision.feature_semantic_identity, []
        ).append(decision)
        predecessor_identity = decision.superseded_decision_identity
        if predecessor_identity is None:
            continue
        predecessor = by_identity[predecessor_identity]
        if index_by_identity[predecessor_identity] >= index_by_identity[
            decision.eligibility_decision_identity
        ]:
            raise ValueError(
                "eligibility decisions must follow append-only order"
            )
        if (
            predecessor.effective_catalog_version
            >= decision.effective_catalog_version
        ):
            raise ValueError(
                "a superseding decision requires a later catalog version"
            )
        if (
            predecessor.feature_semantic_identity
            != decision.feature_semantic_identity
            or predecessor.feature_name != decision.feature_name
            or predecessor.feature_version != decision.feature_version
            or predecessor.feature_class != decision.feature_class
        ):
            raise ValueError(
                "eligibility predecessor targets different feature semantics"
            )
        child_count[predecessor_identity] = (
            child_count.get(predecessor_identity, 0) + 1
        )
        if child_count[predecessor_identity] > 1:
            raise ValueError("eligibility decision history contains a fork")

    for history in by_semantic.values():
        roots = tuple(
            decision
            for decision in history
            if decision.superseded_decision_identity is None
        )
        if len(roots) != 1:
            raise ValueError(
                "feature semantics must have exactly one eligibility root"
            )
        terminals = tuple(
            decision
            for decision in history
            if child_count.get(decision.eligibility_decision_identity, 0) == 0
        )
        if len(terminals) != 1:
            raise ValueError(
                "feature semantics must have exactly one terminal decision"
            )

    for decision in decisions:
        if (
            decision.reconstruct_eligibility_decision_identity()
            != decision.eligibility_decision_identity
        ):
            raise ValueError(
                "eligibility decision identity does not reconstruct"
            )


def _reject_decision_cycles(
    decisions: tuple[FeatureEligibilityDecision, ...],
    by_identity: Mapping[str, FeatureEligibilityDecision],
) -> None:
    for decision in decisions:
        visited: set[str] = set()
        cursor: FeatureEligibilityDecision | None = decision
        while cursor is not None:
            identity = cursor.eligibility_decision_identity
            if identity in visited:
                raise ValueError("eligibility decision history contains a cycle")
            visited.add(identity)
            predecessor = cursor.superseded_decision_identity
            cursor = by_identity.get(predecessor) if predecessor else None


def _validate_registration_schema(metadata: FeatureMetadata) -> None:
    if metadata.history_policy.mode == "prior_round_state":
        raise ValueError(
            "prior_round_state is deferred and cannot be registered"
        )
    for input_path in metadata.input_fields:
        prohibited = _PROHIBITED_INPUT_SEGMENTS.intersection(
            input_path.split(".")
        )
        if prohibited:
            raise ValueError(
                "feature input path contains prohibited RQ-003 source: "
                + ", ".join(sorted(prohibited))
            )
    for output_field in metadata.output_fields:
        if (
            output_field.name in _PROHIBITED_OUTPUT_NAMES
            or output_field.name.startswith("has_")
        ):
            raise ValueError(
                "feature output name is prohibited under RQ-003: "
                f"{output_field.name}"
            )


def _validate_metadata_identity(metadata: FeatureMetadata) -> None:
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("feature semantic identity does not reconstruct")
    if metadata.reconstruct_definition_identity() != metadata.definition_identity:
        raise ValueError("feature definition identity does not reconstruct")


def _reject_duplicate(name: str, value: str, seen: set[str]) -> None:
    if value in seen:
        raise ValueError(f"duplicate {name}: {value}")
    seen.add(value)


def _require_schema_version(name: str, value: object, expected: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"{name} is unsupported")


def _identity(domain: str, material: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


__all__ = (
    "ELIGIBILITY_CATALOG_SCHEMA_VERSION",
    "FEATURE_SET_SCHEMA_VERSION",
    "FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION",
    "EligibilityCatalog",
    "FeatureDefinition",
    "FrozenFeatureRegistry",
)
