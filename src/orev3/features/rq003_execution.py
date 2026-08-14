"""Deterministic RQ-003 measurement execution boundary.

This module implements the approved Phase 3A context and Phase 4 pipeline. It
does not define measurements, feature sets, datasets, baselines, rankings, or
Strategy behavior.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.rq003_contracts import (
    FeatureEligibilityDecision,
    FeatureEligibilityStatus,
    FeatureOutputField,
    canonical_decode,
    canonical_encode,
    reconstruct_executable_binding_identity,
)
from orev3.features.rq003_registry import (
    FeatureDefinition,
    FrozenFeatureRegistry,
)
from orev3.features.rq003_measurement_support import (
    require_mapping,
    require_u64,
    require_u64_vector,
)
from orev3.features.types import FeatureValues
from orev3.strategy_lab.interfaces import DecisionContext


RQ003_EXECUTION_CONTEXT_SCHEMA_VERSION = 4
RQ003_PATH_SCHEMA_VERSION = 4
EXECUTABLE_MEASUREMENT_BINDING_SCHEMA_VERSION = 1
DEFINITION_CONTEXT_VIEW_SCHEMA_VERSION = 2
MEASUREMENT_VECTOR_SCHEMA_VERSION = 1
RQ003_PIPELINE_SCHEMA_VERSION = 1

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_CONTEXT_BUILDER_IDENTITY_DOMAIN = "rq003-context-builder-v1"
_PATH_SCHEMA_IDENTITY_DOMAIN = "rq003-path-schema-v1"
_SNAPSHOT_IDENTITY_DOMAIN = "rq003-decision-snapshot-v1"
_HISTORY_IDENTITY_DOMAIN = "rq003-allowed-history-v1"
_CONTEXT_IDENTITY_DOMAIN = "rq003-execution-context-v1"
_VIEW_IDENTITY_DOMAIN = "rq003-definition-context-view-v1"
_BINDING_IDENTITY_DOMAIN = "rq003-executable-measurement-binding-v1"
_OUTPUT_IDENTITY_DOMAIN = "rq003-measurement-output-v1"
_VECTOR_IDENTITY_DOMAIN = "rq003-measurement-vector-v1"
_PIPELINE_IDENTITY_DOMAIN = "rq003-measurement-pipeline-v1"


@dataclass(frozen=True, slots=True)
class PathDescriptor:
    """Closed canonical resolver declaration for one context path."""

    path: str
    selected_property: str
    scalar_type: str
    nullable: bool
    semantic_unit: str
    candidate_scope: str
    source_cardinality: int
    history_supported: bool
    canonical_encoding_rule: str

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "candidate_scope": self.candidate_scope,
            "canonical_encoding_rule": self.canonical_encoding_rule,
            "history_supported": self.history_supported,
            "nullable": self.nullable,
            "path": self.path,
            "scalar_type": self.scalar_type,
            "selected_property": self.selected_property,
            "semantic_unit": self.semantic_unit,
            "source_cardinality": self.source_cardinality,
        }


RQ003_PATH_DESCRIPTORS = (
    PathDescriptor(
        path="round.deployed_lamports",
        selected_property="deployed_lamports",
        scalar_type="integer",
        nullable=False,
        semantic_unit="lamports",
        candidate_scope="per_square",
        source_cardinality=25,
        history_supported=False,
        canonical_encoding_rule="decimal_integer",
    ),
    PathDescriptor(
        path="round.miner_counts",
        selected_property="miner_count",
        scalar_type="integer",
        nullable=False,
        semantic_unit="miner_authority_count",
        candidate_scope="per_square",
        source_cardinality=25,
        history_supported=False,
        canonical_encoding_rule="decimal_integer",
    ),
    PathDescriptor(
        path="round.total_miners",
        selected_property="total_miners",
        scalar_type="integer",
        nullable=False,
        semantic_unit="unique_miner_authority_count",
        candidate_scope="context_wide_replicated",
        source_cardinality=1,
        history_supported=False,
        canonical_encoding_rule="decimal_integer",
    ),
    PathDescriptor(
        path="round.motherlode",
        selected_property="motherlode",
        scalar_type="integer",
        nullable=False,
        semantic_unit="indivisible_ore_units",
        candidate_scope="context_wide_replicated",
        source_cardinality=1,
        history_supported=False,
        canonical_encoding_rule="decimal_integer",
    ),
    PathDescriptor(
        path="board.production_cost_ema",
        selected_property="production_cost_ema",
        scalar_type="integer",
        nullable=False,
        semantic_unit="lamports_per_whole_ore",
        candidate_scope="context_wide_replicated",
        source_cardinality=1,
        history_supported=False,
        canonical_encoding_rule="decimal_integer",
    ),
)


def _identity(domain: str, material: object) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


RQ003_PATH_SCHEMA_IDENTITY = _identity(
    _PATH_SCHEMA_IDENTITY_DOMAIN,
    {
        "descriptors": tuple(
            descriptor.to_identity_material()
            for descriptor in RQ003_PATH_DESCRIPTORS
        ),
        "path_schema_version": RQ003_PATH_SCHEMA_VERSION,
    },
)
RQ003_CONTEXT_BUILDER_IDENTITY = _identity(
    _CONTEXT_BUILDER_IDENTITY_DOMAIN,
    {
        "builder": "RQ003ExecutionContext.from_decision_context",
        "execution_context_schema_version": (
            RQ003_EXECUTION_CONTEXT_SCHEMA_VERSION
        ),
        "path_schema_identity": RQ003_PATH_SCHEMA_IDENTITY,
    },
)
RQ003_PIPELINE_IMPLEMENTATION_IDENTITY = _identity(
    _PIPELINE_IDENTITY_DOMAIN,
    {
        "binding_schema_version": (
            EXECUTABLE_MEASUREMENT_BINDING_SCHEMA_VERSION
        ),
        "execution": "sequential_all_or_nothing",
        "context_builder_identity": RQ003_CONTEXT_BUILDER_IDENTITY,
        "path_schema_identity": RQ003_PATH_SCHEMA_IDENTITY,
        "pipeline_schema_version": RQ003_PIPELINE_SCHEMA_VERSION,
        "vector_schema_version": MEASUREMENT_VECTOR_SCHEMA_VERSION,
        "view_schema_version": DEFINITION_CONTEXT_VIEW_SCHEMA_VERSION,
    },
)

_PATH_BY_NAME = MappingProxyType(
    {descriptor.path: descriptor for descriptor in RQ003_PATH_DESCRIPTORS}
)


@dataclass(frozen=True, slots=True, init=False)
class RQ003ExecutionContext:
    """Deeply immutable state for one candidate at one decision freeze."""

    structural_round_key: int
    observation_index: int
    structural_candidate_key: int
    deployed_lamports: tuple[int, ...]
    miner_counts: tuple[int, ...]
    total_miners: int
    active_round_motherlode: int
    production_cost_ema: int
    decision_point_configuration_identity: str
    context_schema_version: int = RQ003_EXECUTION_CONTEXT_SCHEMA_VERSION
    path_schema_identity: str = RQ003_PATH_SCHEMA_IDENTITY
    context_builder_identity: str = RQ003_CONTEXT_BUILDER_IDENTITY
    decision_snapshot_identity: str = field(init=False)
    allowed_history_identity: str = field(init=False)
    context_identity: str = field(init=False)

    def __init__(
        self,
        *,
        decision_context: DecisionContext,
        observation_index: int,
        structural_candidate_key: int,
        decision_point_configuration_identity: str,
    ) -> None:
        """Atomically project participant state from one frozen decision."""

        if not isinstance(decision_context, DecisionContext):
            raise TypeError("decision_context must be DecisionContext")
        information = require_mapping(
            "decision_context.information", decision_context.information
        )
        round_state = require_mapping(
            "decision_context.information.round", information.get("round")
        )
        board_state = require_mapping(
            "decision_context.information.board", information.get("board")
        )
        structural_round_key = information.get("round_id")
        _require_nonnegative_integer(
            "decision_context.information.round_id", structural_round_key
        )
        if round_state.get("round_id") != structural_round_key:
            raise ValueError("decision context Round identity is inconsistent")
        if board_state.get("round_id") != structural_round_key:
            raise ValueError("decision context Board identity is inconsistent")

        object.__setattr__(self, "structural_round_key", structural_round_key)
        object.__setattr__(self, "observation_index", observation_index)
        object.__setattr__(
            self, "structural_candidate_key", structural_candidate_key
        )
        object.__setattr__(
            self,
            "deployed_lamports",
            require_u64_vector(
                "round.deployed_lamports",
                round_state.get("deployed_lamports"),
            ),
        )
        object.__setattr__(
            self,
            "miner_counts",
            require_u64_vector(
                "round.miner_counts", round_state.get("miner_counts")
            ),
        )
        object.__setattr__(
            self,
            "total_miners",
            require_u64("round.total_miners", round_state.get("total_miners")),
        )
        active_round_motherlode = require_u64(
            "round.motherlode", round_state.get("motherlode")
        )
        if active_round_motherlode != 0:
            raise ValueError(
                "round.motherlode must be the pre-finalization decision-time "
                "value zero"
            )
        object.__setattr__(
            self, "active_round_motherlode", active_round_motherlode
        )
        object.__setattr__(
            self,
            "production_cost_ema",
            require_u64(
                "board.production_cost_ema",
                board_state.get("production_cost_ema"),
            ),
        )
        object.__setattr__(
            self,
            "decision_point_configuration_identity",
            decision_point_configuration_identity,
        )
        object.__setattr__(
            self,
            "context_schema_version",
            RQ003_EXECUTION_CONTEXT_SCHEMA_VERSION,
        )
        object.__setattr__(
            self, "path_schema_identity", RQ003_PATH_SCHEMA_IDENTITY
        )
        object.__setattr__(
            self, "context_builder_identity", RQ003_CONTEXT_BUILDER_IDENTITY
        )
        self.__post_init__()

    def __post_init__(self) -> None:
        _require_schema(
            "context_schema_version",
            self.context_schema_version,
            RQ003_EXECUTION_CONTEXT_SCHEMA_VERSION,
        )
        _require_nonnegative_integer(
            "structural_round_key", self.structural_round_key
        )
        _require_nonnegative_integer("observation_index", self.observation_index)
        _require_candidate_key(self.structural_candidate_key)
        _require_sha256(
            "decision_point_configuration_identity",
            self.decision_point_configuration_identity,
        )
        if self.path_schema_identity != RQ003_PATH_SCHEMA_IDENTITY:
            raise ValueError("path schema identity is unsupported")
        if self.context_builder_identity != RQ003_CONTEXT_BUILDER_IDENTITY:
            raise ValueError("context builder identity is unsupported")

        deployed = _freeze_u64_vector(
            "deployed_lamports", self.deployed_lamports
        )
        miners = _freeze_u64_vector("miner_counts", self.miner_counts)
        _require_u64("total_miners", self.total_miners)
        _require_u64("active_round_motherlode", self.active_round_motherlode)
        if self.active_round_motherlode != 0:
            raise ValueError(
                "active_round_motherlode must remain the pre-finalization "
                "decision-time value zero"
            )
        _require_u64("production_cost_ema", self.production_cost_ema)
        object.__setattr__(self, "deployed_lamports", deployed)
        object.__setattr__(self, "miner_counts", miners)
        object.__setattr__(
            self,
            "decision_snapshot_identity",
            self.reconstruct_decision_snapshot_identity(),
        )
        object.__setattr__(
            self,
            "allowed_history_identity",
            self.reconstruct_allowed_history_identity(),
        )
        object.__setattr__(
            self,
            "context_identity",
            self.reconstruct_context_identity(),
        )

    @classmethod
    def from_decision_context(
        cls,
        context: DecisionContext,
        *,
        observation_index: int,
        structural_candidate_key: int,
        decision_point_configuration_identity: str,
    ) -> RQ003ExecutionContext:
        """Construct from one deeply immutable decision-time source boundary."""

        return cls(
            decision_context=context,
            observation_index=observation_index,
            structural_candidate_key=structural_candidate_key,
            decision_point_configuration_identity=decision_point_configuration_identity,
        )

    def decision_snapshot_material(self) -> dict[str, Any]:
        return {
            "deployed_lamports": self.deployed_lamports,
            "miner_counts": self.miner_counts,
            "active_round_motherlode": self.active_round_motherlode,
            "production_cost_ema": self.production_cost_ema,
            "total_miners": self.total_miners,
            "observation_index": self.observation_index,
            "path_schema_identity": self.path_schema_identity,
            "structural_round_key": self.structural_round_key,
        }

    def reconstruct_decision_snapshot_identity(self) -> str:
        return _identity(
            _SNAPSHOT_IDENTITY_DOMAIN,
            self.decision_snapshot_material(),
        )

    def reconstruct_allowed_history_identity(self) -> str:
        return _identity(
            _HISTORY_IDENTITY_DOMAIN,
            {
                "history": (),
                "history_policy_scope": "current_observation_only",
                "observation_index": self.observation_index,
                "structural_round_key": self.structural_round_key,
            },
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "allowed_history_identity": self.allowed_history_identity,
            "context_builder_identity": self.context_builder_identity,
            "context_schema_version": self.context_schema_version,
            "decision_point_configuration_identity": (
                self.decision_point_configuration_identity
            ),
            "decision_snapshot_identity": self.decision_snapshot_identity,
            "path_schema_identity": self.path_schema_identity,
            "structural_candidate_key": self.structural_candidate_key,
            "structural_round_key": self.structural_round_key,
        }

    def reconstruct_context_identity(self) -> str:
        return _identity(_CONTEXT_IDENTITY_DOMAIN, self.to_identity_material())

    def validate_identities(self) -> None:
        if (
            self.reconstruct_decision_snapshot_identity()
            != self.decision_snapshot_identity
        ):
            raise ValueError("decision snapshot identity does not reconstruct")
        if (
            self.reconstruct_allowed_history_identity()
            != self.allowed_history_identity
        ):
            raise ValueError("allowed history identity does not reconstruct")
        if self.reconstruct_context_identity() != self.context_identity:
            raise ValueError("execution context identity does not reconstruct")

    def _selected_value(self, path: str) -> int:
        descriptor = _PATH_BY_NAME.get(path)
        if descriptor is None:
            raise ValueError(f"undeclared or unsupported context path: {path}")
        if path == "round.deployed_lamports":
            return self.deployed_lamports[self.structural_candidate_key]
        if path == "round.miner_counts":
            return self.miner_counts[self.structural_candidate_key]
        if path == "round.total_miners":
            return self.total_miners
        if path == "round.motherlode":
            return self.active_round_motherlode
        if path == "board.production_cost_ema":
            return self.production_cost_ema
        raise ValueError(f"context path has no canonical resolver: {path}")


class _RestrictedSquareView:
    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, int]) -> None:
        object.__setattr__(self, "_values", MappingProxyType(dict(values)))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("DefinitionContextView square is immutable")

    def __getattribute__(self, name: str) -> Any:
        if name in {"__class__", "__repr__"}:
            return object.__getattribute__(self, name)
        values = object.__getattribute__(self, "_values")
        if name in values:
            return values[name]
        raise AttributeError(f"undeclared square field is inaccessible: {name}")

    def __repr__(self) -> str:
        values = object.__getattribute__(self, "_values")
        return f"RestrictedSquareView(fields={tuple(values)})"


class _RestrictedRoundView:
    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, int]) -> None:
        object.__setattr__(self, "_values", MappingProxyType(dict(values)))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("DefinitionContextView round is immutable")

    def __getattribute__(self, name: str) -> Any:
        if name in {"__class__", "__repr__"}:
            return object.__getattribute__(self, name)
        values = object.__getattribute__(self, "_values")
        if name in values:
            return values[name]
        raise AttributeError(f"undeclared round field is inaccessible: {name}")

    def __repr__(self) -> str:
        values = object.__getattribute__(self, "_values")
        return f"RestrictedRoundView(fields={tuple(values)})"


class _RestrictedBoardView:
    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, int]) -> None:
        object.__setattr__(self, "_values", MappingProxyType(dict(values)))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("DefinitionContextView board is immutable")

    def __getattribute__(self, name: str) -> Any:
        if name in {"__class__", "__repr__"}:
            return object.__getattribute__(self, name)
        values = object.__getattribute__(self, "_values")
        if name in values:
            return values[name]
        raise AttributeError(f"undeclared board field is inaccessible: {name}")

    def __repr__(self) -> str:
        values = object.__getattribute__(self, "_values")
        return f"RestrictedBoardView(fields={tuple(values)})"


class DefinitionContextView(FeatureContext):
    """FeatureContext-compatible facade exposing only declared paths."""

    __slots__ = (
        "_declared_paths",
        "_executable_binding_identity",
        "_execution_context_identity",
        "_history_identity",
        "_path_schema_identity",
        "_restricted_board",
        "_restricted_round",
        "_restricted_square",
        "_view_identity",
    )

    def __init__(
        self,
        *,
        execution_context: RQ003ExecutionContext,
        definition: FeatureDefinition,
        executable_binding_identity: str,
    ) -> None:
        execution_context.validate_identities()
        _require_sha256(
            "executable_binding_identity", executable_binding_identity
        )
        metadata = definition.metadata
        if metadata.history_policy.mode != "current_observation_only":
            raise ValueError("historical context dispatch is not implemented")
        declared_paths = metadata.input_fields
        if not declared_paths:
            raise ValueError("definition must declare at least one input path")
        selected_board: dict[str, int] = {}
        selected_round: dict[str, int] = {}
        selected_square: dict[str, int] = {}
        for path in declared_paths:
            descriptor = _PATH_BY_NAME.get(path)
            if descriptor is None:
                raise ValueError(
                    f"undeclared or unsupported context path: {path}"
                )
            if descriptor.candidate_scope == "per_square":
                selected = selected_square
            elif path.startswith("board."):
                selected = selected_board
            else:
                selected = selected_round
            selected[descriptor.selected_property] = (
                execution_context._selected_value(path)
            )
        if (
            len(selected_board) + len(selected_square) + len(selected_round)
            != len(declared_paths)
        ):
            raise ValueError("declared paths alias the same selected property")

        # Base slots are intentionally populated only for isinstance
        # compatibility with existing pure measurements. Public access to them
        # is denied by __getattribute__ below.
        object.__setattr__(self, "board", None)
        object.__setattr__(self, "square_index", None)
        object.__setattr__(self, "square_history", ())
        object.__setattr__(self, "board_history", ())
        object.__setattr__(
            self,
            "_restricted_board",
            _RestrictedBoardView(selected_board),
        )
        object.__setattr__(
            self,
            "_restricted_square",
            _RestrictedSquareView(selected_square),
        )
        object.__setattr__(
            self,
            "_restricted_round",
            _RestrictedRoundView(selected_round),
        )
        object.__setattr__(self, "_declared_paths", declared_paths)
        object.__setattr__(
            self, "_execution_context_identity", execution_context.context_identity
        )
        object.__setattr__(
            self, "_history_identity", execution_context.allowed_history_identity
        )
        object.__setattr__(
            self, "_path_schema_identity", execution_context.path_schema_identity
        )
        object.__setattr__(
            self, "_executable_binding_identity", executable_binding_identity
        )
        object.__setattr__(
            self,
            "_view_identity",
            self.reconstruct_view_identity(definition),
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("DefinitionContextView is immutable")

    def __getattribute__(self, name: str) -> Any:
        if name in {
            "__class__",
            "__repr__",
            "reconstruct_view_identity",
            "validate_identity",
        }:
            return object.__getattribute__(self, name)
        if name == "square":
            view = object.__getattribute__(self, "_restricted_square")
            if not object.__getattribute__(view, "_values"):
                raise AttributeError(
                    "undeclared context field is inaccessible: square"
                )
            return view
        if name == "board":
            view = object.__getattribute__(self, "_restricted_board")
            if not object.__getattribute__(view, "_values"):
                raise AttributeError(
                    "undeclared context field is inaccessible: board"
                )
            return view
        if name == "round":
            view = object.__getattribute__(self, "_restricted_round")
            if not object.__getattribute__(view, "_values"):
                raise AttributeError(
                    "undeclared context field is inaccessible: round"
                )
            return view
        raise AttributeError(f"undeclared context field is inaccessible: {name}")

    def __repr__(self) -> str:
        paths = object.__getattribute__(self, "_declared_paths")
        return f"DefinitionContextView(paths={paths!r})"

    def reconstruct_view_identity(self, definition: FeatureDefinition) -> str:
        return _identity(
            _VIEW_IDENTITY_DOMAIN,
            {
                "allowed_history_identity": object.__getattribute__(
                    self, "_history_identity"
                ),
                "declared_input_paths": object.__getattribute__(
                    self, "_declared_paths"
                ),
                "definition_context_view_schema_version": (
                    DEFINITION_CONTEXT_VIEW_SCHEMA_VERSION
                ),
                "execution_context_identity": object.__getattribute__(
                    self, "_execution_context_identity"
                ),
                "executable_binding_identity": object.__getattribute__(
                    self, "_executable_binding_identity"
                ),
                "feature_definition_identity": definition.definition_identity,
                "history_policy": (
                    definition.metadata.history_policy.to_identity_material()
                ),
                "output_candidate_scopes": tuple(
                    output.candidate_scope
                    for output in definition.metadata.output_fields
                ),
                "path_schema_identity": object.__getattribute__(
                    self, "_path_schema_identity"
                ),
            },
        )

    def validate_identity(self, definition: FeatureDefinition) -> None:
        if self.reconstruct_view_identity(definition) != object.__getattribute__(
            self, "_view_identity"
        ):
            raise ValueError("definition context view identity does not reconstruct")


def definition_context_view_identity(view: DefinitionContextView) -> str:
    if not isinstance(view, DefinitionContextView):
        raise TypeError("view must be DefinitionContextView")
    return object.__getattribute__(view, "_view_identity")


@dataclass(frozen=True, slots=True)
class ExecutableMeasurementBinding:
    """Immutable association of approved definition and exact computation."""

    definition: FeatureDefinition
    terminal_decision: FeatureEligibilityDecision
    computation: Feature
    binding_schema_version: int = EXECUTABLE_MEASUREMENT_BINDING_SCHEMA_VERSION
    executable_binding_identity: str = field(init=False)
    execution_entry_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema(
            "binding_schema_version",
            self.binding_schema_version,
            EXECUTABLE_MEASUREMENT_BINDING_SCHEMA_VERSION,
        )
        if not isinstance(self.definition, FeatureDefinition):
            raise TypeError("definition must be FeatureDefinition")
        if not isinstance(self.terminal_decision, FeatureEligibilityDecision):
            raise TypeError(
                "terminal_decision must be FeatureEligibilityDecision"
            )
        if not isinstance(self.computation, Feature):
            raise TypeError("computation must implement Feature")
        metadata = self.definition.metadata
        if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
            raise ValueError("feature semantic identity does not reconstruct")
        if (
            metadata.reconstruct_definition_identity()
            != metadata.definition_identity
        ):
            raise ValueError("feature definition identity does not reconstruct")
        executable = reconstruct_executable_binding_identity(
            metadata, self.terminal_decision
        )
        if self.terminal_decision.status is not FeatureEligibilityStatus.APPROVED:
            raise ValueError("executable measurement requires approval")
        if self.computation.name != metadata.feature_name:
            raise ValueError("computation feature name does not match metadata")
        if self.computation.family != metadata.feature_group:
            raise ValueError("computation feature group does not match metadata")
        if self.computation.output_columns != tuple(
            output.name for output in metadata.output_fields
        ):
            raise ValueError("computation output schema does not match metadata")
        computation_metadata = getattr(self.computation, "metadata", None)
        if computation_metadata != metadata:
            raise ValueError("computation does not bind exact metadata")
        computation_definition = getattr(self.computation, "definition", None)
        if computation_definition != self.definition:
            raise ValueError("computation does not bind exact definition")
        if metadata.implementation_identity != (
            computation_metadata.implementation_identity
        ):
            raise ValueError("computation implementation identity does not match")
        object.__setattr__(self, "executable_binding_identity", executable)
        object.__setattr__(
            self,
            "execution_entry_identity",
            self.reconstruct_execution_entry_identity(),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "binding_schema_version": self.binding_schema_version,
            "computation_implementation_identity": (
                self.definition.metadata.implementation_identity
            ),
            "executable_binding_identity": self.executable_binding_identity,
            "feature_definition_identity": self.definition.definition_identity,
            "ordered_output_schema": tuple(
                output.to_identity_material()
                for output in self.definition.output_fields
            ),
        }

    def reconstruct_execution_entry_identity(self) -> str:
        return _identity(_BINDING_IDENTITY_DOMAIN, self.to_identity_material())

    def validate(self) -> None:
        if (
            reconstruct_executable_binding_identity(
                self.definition.metadata, self.terminal_decision
            )
            != self.executable_binding_identity
        ):
            raise ValueError("executable binding identity does not reconstruct")
        if (
            self.reconstruct_execution_entry_identity()
            != self.execution_entry_identity
        ):
            raise ValueError("execution entry identity does not reconstruct")


@dataclass(frozen=True, slots=True)
class MeasurementVector:
    """Immutable ordered output of one complete measurement execution."""

    execution_context_identity: str
    allowed_history_identity: str
    definition_view_identities: tuple[str, ...]
    structural_candidate_key: int
    execution_registry_identity: str
    ordered_executable_binding_identities: tuple[str, ...]
    ordered_output_owner_definition_identities: tuple[str, ...]
    ordered_output_fields: tuple[FeatureOutputField, ...]
    ordered_values: tuple[int | float | bool | None, ...]
    per_definition_output_identities: tuple[str, ...]
    pipeline_implementation_identity: str
    vector_schema_version: int = MEASUREMENT_VECTOR_SCHEMA_VERSION
    vector_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_schema(
            "vector_schema_version",
            self.vector_schema_version,
            MEASUREMENT_VECTOR_SCHEMA_VERSION,
        )
        for name, identity in (
            ("execution_context_identity", self.execution_context_identity),
            ("allowed_history_identity", self.allowed_history_identity),
            ("execution_registry_identity", self.execution_registry_identity),
            (
                "pipeline_implementation_identity",
                self.pipeline_implementation_identity,
            ),
        ):
            _require_sha256(name, identity)
        _require_candidate_key(self.structural_candidate_key)
        _require_identity_tuple(
            "definition_view_identities", self.definition_view_identities
        )
        _require_identity_tuple(
            "ordered_executable_binding_identities",
            self.ordered_executable_binding_identities,
        )
        _require_identity_tuple(
            "ordered_output_owner_definition_identities",
            self.ordered_output_owner_definition_identities,
        )
        _require_identity_tuple(
            "per_definition_output_identities",
            self.per_definition_output_identities,
        )
        if not isinstance(self.ordered_output_fields, tuple) or not all(
            isinstance(item, FeatureOutputField)
            for item in self.ordered_output_fields
        ):
            raise TypeError("ordered_output_fields must be an immutable tuple")
        if not isinstance(self.ordered_values, tuple):
            raise TypeError("ordered_values must be an immutable tuple")
        if len(self.ordered_output_fields) != len(self.ordered_values):
            raise ValueError("output schema and values must have equal length")
        if len(self.ordered_output_fields) != len(
            self.ordered_output_owner_definition_identities
        ):
            raise ValueError("every output requires exactly one owner")
        if len(self.definition_view_identities) != len(
            self.ordered_executable_binding_identities
        ):
            raise ValueError("every binding requires exactly one view identity")
        if len(self.per_definition_output_identities) != len(
            self.ordered_executable_binding_identities
        ):
            raise ValueError("every binding requires exactly one output identity")
        names = tuple(output.name for output in self.ordered_output_fields)
        if len(names) != len(set(names)):
            raise ValueError("measurement vector output names must be unique")
        for output, value in zip(
            self.ordered_output_fields, self.ordered_values, strict=True
        ):
            _validate_output_scalar(output, value)
        object.__setattr__(
            self, "vector_identity", self.reconstruct_vector_identity()
        )

    @property
    def values(self) -> Mapping[str, int | float | bool | None]:
        return MappingProxyType(
            {
                output.name: value
                for output, value in zip(
                    self.ordered_output_fields,
                    self.ordered_values,
                    strict=True,
                )
            }
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "allowed_history_identity": self.allowed_history_identity,
            "definition_view_identities": self.definition_view_identities,
            "execution_context_identity": self.execution_context_identity,
            "execution_registry_identity": self.execution_registry_identity,
            "ordered_executable_binding_identities": (
                self.ordered_executable_binding_identities
            ),
            "ordered_output_fields": tuple(
                output.to_identity_material()
                for output in self.ordered_output_fields
            ),
            "ordered_output_owner_definition_identities": (
                self.ordered_output_owner_definition_identities
            ),
            "ordered_values": self.ordered_values,
            "per_definition_output_identities": (
                self.per_definition_output_identities
            ),
            "pipeline_implementation_identity": (
                self.pipeline_implementation_identity
            ),
            "structural_candidate_key": self.structural_candidate_key,
            "vector_schema_version": self.vector_schema_version,
        }

    def reconstruct_vector_identity(self) -> str:
        return _identity(_VECTOR_IDENTITY_DOMAIN, self.to_identity_material())

    def canonical_bytes(self) -> bytes:
        return canonical_encode(
            {
                **self.to_identity_material(),
                "vector_identity": self.vector_identity,
            }
        )

    @classmethod
    def from_canonical_bytes(cls, raw: bytes) -> MeasurementVector:
        material = canonical_decode(raw)
        if not isinstance(material, dict):
            raise ValueError("measurement vector must be a canonical mapping")
        expected = {
            "allowed_history_identity",
            "definition_view_identities",
            "execution_context_identity",
            "execution_registry_identity",
            "ordered_executable_binding_identities",
            "ordered_output_fields",
            "ordered_output_owner_definition_identities",
            "ordered_values",
            "per_definition_output_identities",
            "pipeline_implementation_identity",
            "structural_candidate_key",
            "vector_identity",
            "vector_schema_version",
        }
        if set(material) != expected:
            raise ValueError("measurement vector fields are invalid")
        output_material = material["ordered_output_fields"]
        if not isinstance(output_material, tuple):
            raise ValueError("measurement vector output schema is invalid")
        outputs = tuple(_output_field_from_material(item) for item in output_material)
        vector = cls(
            execution_context_identity=material["execution_context_identity"],
            allowed_history_identity=material["allowed_history_identity"],
            definition_view_identities=material["definition_view_identities"],
            structural_candidate_key=material["structural_candidate_key"],
            execution_registry_identity=material["execution_registry_identity"],
            ordered_executable_binding_identities=(
                material["ordered_executable_binding_identities"]
            ),
            ordered_output_owner_definition_identities=(
                material["ordered_output_owner_definition_identities"]
            ),
            ordered_output_fields=outputs,
            ordered_values=material["ordered_values"],
            per_definition_output_identities=(
                material["per_definition_output_identities"]
            ),
            pipeline_implementation_identity=(
                material["pipeline_implementation_identity"]
            ),
            vector_schema_version=material["vector_schema_version"],
        )
        if material["vector_identity"] != vector.vector_identity:
            raise ValueError("measurement vector identity does not reconstruct")
        if vector.canonical_bytes() != raw:
            raise ValueError("measurement vector encoding is not canonical")
        return vector


class RQ003MeasurementPipeline:
    """Sequential all-or-nothing execution of approved measurements."""

    __slots__ = ("_bindings", "_registry")

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("RQ003MeasurementPipeline is immutable")

    def __init__(
        self,
        *,
        registry: FrozenFeatureRegistry,
        bindings: tuple[ExecutableMeasurementBinding, ...],
    ) -> None:
        if not isinstance(registry, FrozenFeatureRegistry):
            raise TypeError("registry must be FrozenFeatureRegistry")
        if not isinstance(bindings, tuple) or not all(
            isinstance(binding, ExecutableMeasurementBinding)
            for binding in bindings
        ):
            raise TypeError("bindings must be an immutable tuple")
        if not bindings:
            raise ValueError("bindings cannot be empty")
        object.__setattr__(self, "_registry", registry)
        object.__setattr__(self, "_bindings", bindings)
        self._validate_preexecution_registry()

    @property
    def pipeline_implementation_identity(self) -> str:
        return RQ003_PIPELINE_IMPLEMENTATION_IDENTITY

    def _validate_preexecution_registry(self) -> None:
        registry = object.__getattribute__(self, "_registry")
        bindings = object.__getattribute__(self, "_bindings")
        if (
            registry.eligibility_catalog.reconstruct_catalog_identity()
            != registry.eligibility_catalog.catalog_identity
        ):
            raise ValueError("eligibility catalog identity does not reconstruct")
        if registry.reconstruct_registry_identity() != registry.registry_identity:
            raise ValueError("execution registry identity does not reconstruct")
        if (
            registry.reconstruct_validation_identity()
            != registry.validation_identity
        ):
            raise ValueError("registry validation identity does not reconstruct")
        if tuple(binding.definition for binding in bindings) != (
            registry.definitions
        ):
            raise ValueError("binding order does not match execution registry")
        if tuple(
            binding.executable_binding_identity for binding in bindings
        ) != registry.ordered_executable_feature_identities:
            raise ValueError("binding identities do not match execution registry")
        for binding in bindings:
            binding.validate()
            terminal = registry.eligibility_catalog.resolve_terminal(
                binding.definition.semantic_identity
            )
            if terminal != binding.terminal_decision:
                raise ValueError("binding decision is not registry terminal")

    def compute(self, context: RQ003ExecutionContext) -> MeasurementVector:
        if not isinstance(context, RQ003ExecutionContext):
            raise TypeError("context must be RQ003ExecutionContext")
        context.validate_identities()
        self._validate_preexecution_registry()
        registry = object.__getattribute__(self, "_registry")
        bindings = object.__getattribute__(self, "_bindings")

        view_identities: list[str] = []
        output_owners: list[str] = []
        output_fields: list[FeatureOutputField] = []
        ordered_values: list[int | float | bool | None] = []
        output_identities: list[str] = []

        for binding in bindings:
            view = DefinitionContextView(
                execution_context=context,
                definition=binding.definition,
                executable_binding_identity=(
                    binding.executable_binding_identity
                ),
            )
            view.validate_identity(binding.definition)
            result = binding.computation.compute(view)
            canonical_values = self._validate_definition_output(binding, result)
            view_identities.append(definition_context_view_identity(view))
            output_identities.append(
                _identity(
                    _OUTPUT_IDENTITY_DOMAIN,
                    {
                        "definition_context_view_identity": (
                            definition_context_view_identity(view)
                        ),
                        "executable_binding_identity": (
                            binding.executable_binding_identity
                        ),
                        "ordered_output_schema": tuple(
                            output.to_identity_material()
                            for output in binding.definition.output_fields
                        ),
                        "ordered_values": canonical_values,
                    },
                )
            )
            output_fields.extend(binding.definition.output_fields)
            ordered_values.extend(canonical_values)
            output_owners.extend(
                binding.definition.definition_identity
                for _ in binding.definition.output_fields
            )

        return MeasurementVector(
            execution_context_identity=context.context_identity,
            allowed_history_identity=context.allowed_history_identity,
            definition_view_identities=tuple(view_identities),
            structural_candidate_key=context.structural_candidate_key,
            execution_registry_identity=registry.registry_identity,
            ordered_executable_binding_identities=tuple(
                binding.executable_binding_identity for binding in bindings
            ),
            ordered_output_owner_definition_identities=tuple(output_owners),
            ordered_output_fields=tuple(output_fields),
            ordered_values=tuple(ordered_values),
            per_definition_output_identities=tuple(output_identities),
            pipeline_implementation_identity=(
                RQ003_PIPELINE_IMPLEMENTATION_IDENTITY
            ),
        )

    @staticmethod
    def _validate_definition_output(
        binding: ExecutableMeasurementBinding,
        result: FeatureValues,
    ) -> tuple[int | float | bool | None, ...]:
        if not isinstance(result, Mapping):
            raise TypeError("measurement output must be a mapping")
        expected = binding.definition.output_fields
        expected_names = tuple(output.name for output in expected)
        actual_names = tuple(result.keys())
        if actual_names != expected_names:
            raise ValueError("measurement output membership or order is invalid")
        values = tuple(result[name] for name in expected_names)
        for output, value in zip(expected, values, strict=True):
            _validate_output_scalar(output, value)
        # Canonical encoding must accept the exact ordered material.
        canonical_encode(
            tuple(zip(expected_names, values, strict=True))
        )
        return values


def _output_field_from_material(material: object) -> FeatureOutputField:
    if not isinstance(material, dict):
        raise ValueError("measurement output field material is invalid")
    expected = {
        "candidate_scope",
        "canonical_encoding_rule",
        "name",
        "nullable",
        "scalar_type",
        "semantic_unit",
        "tie_rule",
    }
    if set(material) != expected:
        raise ValueError("measurement output field material is invalid")
    return FeatureOutputField(
        name=material["name"],
        scalar_type=material["scalar_type"],
        nullable=material["nullable"],
        semantic_unit=material["semantic_unit"],
        candidate_scope=material["candidate_scope"],
        tie_rule=material["tie_rule"],
        canonical_encoding_rule=material["canonical_encoding_rule"],
    )


def _validate_output_scalar(
    output: FeatureOutputField,
    value: int | float | bool | None,
) -> None:
    if value is None:
        if not output.nullable:
            raise ValueError(f"output {output.name!r} cannot be null")
        return
    if output.scalar_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"output {output.name!r} must be an integer")
    elif output.scalar_type == "float64":
        if isinstance(value, bool) or not isinstance(value, float):
            raise TypeError(f"output {output.name!r} must be a float64")
        if not math.isfinite(value):
            raise ValueError(f"output {output.name!r} must be finite")
    elif output.scalar_type == "boolean":
        if not isinstance(value, bool):
            raise TypeError(f"output {output.name!r} must be a boolean")
    else:
        raise ValueError(f"output {output.name!r} has unsupported scalar type")
    canonical_encode(value)


def _freeze_u64_vector(name: str, values: object) -> tuple[int, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    if len(values) != 25:
        raise ValueError(f"{name} must contain exactly 25 values")
    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > (1 << 64) - 1
        ):
            raise ValueError(f"{name} values must be unsigned 64-bit integers")
    return values


def _require_u64(name: str, value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > (1 << 64) - 1
    ):
        raise ValueError(f"{name} must be an unsigned 64-bit integer")


def _require_schema(name: str, value: object, expected: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"{name} is unsupported")


def _require_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _require_candidate_key(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 25:
        raise ValueError("structural_candidate_key must be in [0, 24]")


def _require_sha256(name: str, value: object) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _require_identity_tuple(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    for value in values:
        _require_sha256(name, value)


__all__ = (
    "DEFINITION_CONTEXT_VIEW_SCHEMA_VERSION",
    "EXECUTABLE_MEASUREMENT_BINDING_SCHEMA_VERSION",
    "MEASUREMENT_VECTOR_SCHEMA_VERSION",
    "RQ003_CONTEXT_BUILDER_IDENTITY",
    "RQ003_EXECUTION_CONTEXT_SCHEMA_VERSION",
    "RQ003_PATH_DESCRIPTORS",
    "RQ003_PATH_SCHEMA_IDENTITY",
    "RQ003_PIPELINE_IMPLEMENTATION_IDENTITY",
    "RQ003_PIPELINE_SCHEMA_VERSION",
    "DefinitionContextView",
    "ExecutableMeasurementBinding",
    "MeasurementVector",
    "PathDescriptor",
    "RQ003ExecutionContext",
    "RQ003MeasurementPipeline",
    "definition_context_view_identity",
)
