"""Immutable RQ-003 feature contracts and canonical identities.

This module implements Phase 1 contracts only. It contains no feature
computation, registry, dataset, feature vector, or execution behavior.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


CANONICAL_ENCODING_VERSION = 1
FEATURE_METADATA_SCHEMA_VERSION = 1
FEATURE_ELIGIBILITY_SCHEMA_VERSION = 1

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SAFE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
_FEATURE_VERSION_PATTERN = re.compile(
    r"(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*)\."
    r"(?:0|[1-9][0-9]*)"
)
_INPUT_PATH_PATTERN = re.compile(
    r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*"
)
_INTEGER_PATTERN = re.compile(r"0|-?[1-9][0-9]*")
_FLOAT64_HEX_PATTERN = re.compile(r"[0-9a-f]{16}")

_SEMANTIC_IDENTITY_DOMAIN = "rq003-feature-semantic-v1"
_DEFINITION_IDENTITY_DOMAIN = "rq003-feature-definition-v1"
_ELIGIBILITY_IDENTITY_DOMAIN = "rq003-feature-eligibility-decision-v1"
_EXECUTABLE_BINDING_IDENTITY_DOMAIN = "rq003-executable-feature-binding-v1"

_HISTORY_MODES = frozenset(
    {
        "current_observation_only",
        "same_round_history_through_current",
        "prior_round_state",
    }
)
_MISSING_HISTORY_DISPOSITIONS = frozenset(
    {"fail", "preserve_null", "deterministic_fallback"}
)
_MISSINGNESS_POLICIES = frozenset(
    {"fail", "preserve_null", "deterministic_fallback"}
)
_SCALAR_TYPES = frozenset({"integer", "float64", "boolean"})
_CANDIDATE_SCOPES = frozenset({"per_square", "context_wide_replicated"})
_CANONICAL_RULES_BY_SCALAR = {
    "integer": frozenset({"decimal_integer"}),
    "float64": frozenset(
        {
            "ieee754_binary64_preserve_negative_zero",
            "ieee754_binary64_normalize_negative_zero",
        }
    ),
    "boolean": frozenset({"json_boolean"}),
}


class FeatureEligibilityStatus(str, Enum):
    """Closed RQ-003 eligibility status."""

    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class FeatureHistoryPolicy:
    """Immutable declaration of a feature's permitted temporal reach."""

    mode: str
    exact_contiguous_history: bool
    maximum_history_length: int | None
    full_through_current: bool
    missing_history_disposition: str
    require_wall_clock_span: bool = False
    require_slot_span: bool = False
    configuration_identity: str | None = None

    def __post_init__(self) -> None:
        _require_member("mode", self.mode, _HISTORY_MODES)
        _require_bool("exact_contiguous_history", self.exact_contiguous_history)
        _require_bool("full_through_current", self.full_through_current)
        _require_member(
            "missing_history_disposition",
            self.missing_history_disposition,
            _MISSING_HISTORY_DISPOSITIONS,
        )
        _require_bool("require_wall_clock_span", self.require_wall_clock_span)
        _require_bool("require_slot_span", self.require_slot_span)
        if self.maximum_history_length is not None:
            _require_positive_integer(
                "maximum_history_length", self.maximum_history_length
            )
        if self.configuration_identity is not None:
            _require_sha256(
                "configuration_identity", self.configuration_identity
            )

        if self.mode == "current_observation_only":
            if self.maximum_history_length != 1:
                raise ValueError(
                    "current_observation_only requires "
                    "maximum_history_length=1"
                )
            if self.full_through_current:
                raise ValueError(
                    "current_observation_only cannot use full history"
                )
            if self.exact_contiguous_history:
                raise ValueError(
                    "current_observation_only cannot require contiguous history"
                )
        elif (self.maximum_history_length is None) == (
            not self.full_through_current
        ):
            raise ValueError(
                "historical policies require exactly one of a maximum "
                "history length or full_through_current"
            )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "configuration_identity": self.configuration_identity,
            "exact_contiguous_history": self.exact_contiguous_history,
            "full_through_current": self.full_through_current,
            "maximum_history_length": self.maximum_history_length,
            "missing_history_disposition": self.missing_history_disposition,
            "mode": self.mode,
            "require_slot_span": self.require_slot_span,
            "require_wall_clock_span": self.require_wall_clock_span,
        }


@dataclass(frozen=True, slots=True)
class FeatureOutputField:
    """Immutable schema for one ordered feature output."""

    name: str
    scalar_type: str
    nullable: bool
    semantic_unit: str
    candidate_scope: str
    tie_rule: str | None
    canonical_encoding_rule: str

    def __post_init__(self) -> None:
        _require_safe_name("name", self.name)
        _require_member("scalar_type", self.scalar_type, _SCALAR_TYPES)
        _require_bool("nullable", self.nullable)
        _require_nonempty_string("semantic_unit", self.semantic_unit)
        _require_member(
            "candidate_scope", self.candidate_scope, _CANDIDATE_SCOPES
        )
        if self.tie_rule is not None:
            _require_nonempty_string("tie_rule", self.tie_rule)
        _require_member(
            "canonical_encoding_rule",
            self.canonical_encoding_rule,
            _CANONICAL_RULES_BY_SCALAR[self.scalar_type],
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "candidate_scope": self.candidate_scope,
            "canonical_encoding_rule": self.canonical_encoding_rule,
            "name": self.name,
            "nullable": self.nullable,
            "scalar_type": self.scalar_type,
            "semantic_unit": self.semantic_unit,
            "tie_rule": self.tie_rule,
        }


@dataclass(frozen=True, slots=True)
class FeatureMetadata:
    """Complete immutable semantics and implementation binding for a feature."""

    metadata_schema_version: int
    feature_name: str
    feature_version: str
    feature_group: str
    description: str
    input_fields: tuple[str, ...]
    history_policy: FeatureHistoryPolicy
    output_fields: tuple[FeatureOutputField, ...]
    missingness_policy: str
    determinism_contract: str
    configuration_identity: str | None
    implementation_identity: str
    authority_references: tuple[str, ...]
    semantic_identity: str = field(init=False)
    definition_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            isinstance(self.metadata_schema_version, bool)
            or self.metadata_schema_version != FEATURE_METADATA_SCHEMA_VERSION
        ):
            raise ValueError("metadata_schema_version is unsupported")
        _require_safe_name("feature_name", self.feature_name)
        if not isinstance(self.feature_version, str) or not (
            _FEATURE_VERSION_PATTERN.fullmatch(self.feature_version)
        ):
            raise ValueError("feature_version must use MAJOR.MINOR.PATCH")
        _require_safe_name("feature_group", self.feature_group)
        _require_nonempty_string("description", self.description)

        input_fields = _freeze_string_tuple("input_fields", self.input_fields)
        if not input_fields:
            raise ValueError("input_fields cannot be empty")
        for input_field in input_fields:
            if not _INPUT_PATH_PATTERN.fullmatch(input_field):
                raise ValueError(f"invalid input field path: {input_field!r}")
        _require_unique("input_fields", input_fields)
        object.__setattr__(self, "input_fields", input_fields)

        if not isinstance(self.history_policy, FeatureHistoryPolicy):
            raise TypeError("history_policy must be FeatureHistoryPolicy")

        if not isinstance(self.output_fields, tuple):
            raise TypeError("output_fields must be an immutable tuple")
        output_fields = self.output_fields
        if not output_fields:
            raise ValueError("output_fields cannot be empty")
        if not all(isinstance(item, FeatureOutputField) for item in output_fields):
            raise TypeError(
                "output_fields must contain only FeatureOutputField values"
            )
        _require_unique(
            "output field names", tuple(item.name for item in output_fields)
        )
        object.__setattr__(self, "output_fields", output_fields)

        _require_member(
            "missingness_policy",
            self.missingness_policy,
            _MISSINGNESS_POLICIES,
        )
        _require_nonempty_string(
            "determinism_contract", self.determinism_contract
        )
        if self.configuration_identity is not None:
            _require_sha256(
                "configuration_identity", self.configuration_identity
            )
        _require_sha256("implementation_identity", self.implementation_identity)

        authority_references = _freeze_string_tuple(
            "authority_references", self.authority_references
        )
        if not authority_references:
            raise ValueError("authority_references cannot be empty")
        _require_unique("authority_references", authority_references)
        object.__setattr__(self, "authority_references", authority_references)

        semantic_identity = self.reconstruct_semantic_identity()
        object.__setattr__(self, "semantic_identity", semantic_identity)
        object.__setattr__(
            self,
            "definition_identity",
            self.reconstruct_definition_identity(),
        )

    def to_semantic_identity_material(self) -> dict[str, Any]:
        """Return all semantic fields except implementation identity."""

        return {
            "authority_references": self.authority_references,
            "configuration_identity": self.configuration_identity,
            "description": self.description,
            "determinism_contract": self.determinism_contract,
            "feature_group": self.feature_group,
            "feature_name": self.feature_name,
            "feature_version": self.feature_version,
            "history_policy": self.history_policy.to_identity_material(),
            "input_fields": self.input_fields,
            "metadata_schema_version": self.metadata_schema_version,
            "missingness_policy": self.missingness_policy,
            "output_fields": tuple(
                item.to_identity_material() for item in self.output_fields
            ),
        }

    def reconstruct_semantic_identity(self) -> str:
        return _domain_identity(
            _SEMANTIC_IDENTITY_DOMAIN,
            self.to_semantic_identity_material(),
        )

    def reconstruct_definition_identity(self) -> str:
        semantic_identity = self.reconstruct_semantic_identity()
        return _domain_identity(
            _DEFINITION_IDENTITY_DOMAIN,
            {
                "feature_semantic_identity": semantic_identity,
                "implementation_identity": self.implementation_identity,
            },
        )


@dataclass(frozen=True, slots=True)
class FeatureEligibilityDecision:
    """Immutable reviewed eligibility decision for exact feature semantics."""

    eligibility_schema_version: int
    feature_name: str
    feature_version: str
    feature_semantic_identity: str
    feature_class: str
    status: FeatureEligibilityStatus
    governing_concern: str
    authority_document_identity: str
    decision_rationale_digest: str
    effective_catalog_version: int
    superseded_decision_identity: str | None = None
    eligibility_decision_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            isinstance(self.eligibility_schema_version, bool)
            or self.eligibility_schema_version
            != FEATURE_ELIGIBILITY_SCHEMA_VERSION
        ):
            raise ValueError("eligibility_schema_version is unsupported")
        _require_safe_name("feature_name", self.feature_name)
        if not isinstance(self.feature_version, str) or not (
            _FEATURE_VERSION_PATTERN.fullmatch(self.feature_version)
        ):
            raise ValueError("feature_version must use MAJOR.MINOR.PATCH")
        _require_sha256(
            "feature_semantic_identity", self.feature_semantic_identity
        )
        _require_safe_name("feature_class", self.feature_class)
        if not isinstance(self.status, FeatureEligibilityStatus):
            raise TypeError("status must be FeatureEligibilityStatus")
        _require_nonempty_string("governing_concern", self.governing_concern)
        _require_sha256(
            "authority_document_identity", self.authority_document_identity
        )
        _require_sha256(
            "decision_rationale_digest", self.decision_rationale_digest
        )
        _require_positive_integer(
            "effective_catalog_version", self.effective_catalog_version
        )
        if self.superseded_decision_identity is not None:
            _require_sha256(
                "superseded_decision_identity",
                self.superseded_decision_identity,
            )

        identity = self.reconstruct_eligibility_decision_identity()
        if self.superseded_decision_identity == identity:
            raise ValueError("an eligibility decision cannot supersede itself")
        object.__setattr__(self, "eligibility_decision_identity", identity)

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "authority_document_identity": self.authority_document_identity,
            "decision_rationale_digest": self.decision_rationale_digest,
            "effective_catalog_version": self.effective_catalog_version,
            "eligibility_schema_version": self.eligibility_schema_version,
            "feature_class": self.feature_class,
            "feature_name": self.feature_name,
            "feature_semantic_identity": self.feature_semantic_identity,
            "feature_version": self.feature_version,
            "governing_concern": self.governing_concern,
            "status": self.status.value,
            "superseded_decision_identity": self.superseded_decision_identity,
        }

    def reconstruct_eligibility_decision_identity(self) -> str:
        return _domain_identity(
            _ELIGIBILITY_IDENTITY_DOMAIN,
            self.to_identity_material(),
        )


def reconstruct_executable_binding_identity(
    metadata: FeatureMetadata,
    terminal_decision: FeatureEligibilityDecision,
) -> str:
    """Reconstruct the approved binding identity without implementing a catalog.

    Phase 2 will prove which decision is terminal. This Phase 1 constructor
    validates that the supplied decision is approved and targets the exact
    semantic definition.
    """

    if not isinstance(metadata, FeatureMetadata):
        raise TypeError("metadata must be FeatureMetadata")
    if not isinstance(terminal_decision, FeatureEligibilityDecision):
        raise TypeError(
            "terminal_decision must be FeatureEligibilityDecision"
        )
    if terminal_decision.status is not FeatureEligibilityStatus.APPROVED:
        raise ValueError("executable binding requires an approved decision")
    if terminal_decision.feature_semantic_identity != metadata.semantic_identity:
        raise ValueError("eligibility decision targets different semantics")
    if terminal_decision.feature_name != metadata.feature_name:
        raise ValueError("eligibility decision feature name disagrees")
    if terminal_decision.feature_version != metadata.feature_version:
        raise ValueError("eligibility decision feature version disagrees")
    if terminal_decision.feature_class != metadata.feature_group:
        raise ValueError("eligibility decision feature class disagrees")
    if (
        terminal_decision.reconstruct_eligibility_decision_identity()
        != terminal_decision.eligibility_decision_identity
    ):
        raise ValueError("eligibility decision identity does not reconstruct")
    if metadata.reconstruct_semantic_identity() != metadata.semantic_identity:
        raise ValueError("feature semantic identity does not reconstruct")
    if metadata.reconstruct_definition_identity() != metadata.definition_identity:
        raise ValueError("feature definition identity does not reconstruct")

    return _domain_identity(
        _EXECUTABLE_BINDING_IDENTITY_DOMAIN,
        {
            "feature_definition_identity": metadata.definition_identity,
            "terminal_eligibility_decision_identity": (
                terminal_decision.eligibility_decision_identity
            ),
        },
    )


def canonical_encode(value: object) -> bytes:
    """Encode supported identity material as canonical UTF-8 JSON."""

    envelope = {
        "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
        "value": _canonical_value(value),
    }
    return json.dumps(
        envelope,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_decode(raw: bytes) -> Any:
    """Decode canonical material and reject noncanonical representations."""

    if not isinstance(raw, bytes):
        raise TypeError("canonical input must be bytes")
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("RQ-003 canonical encoding is malformed") from exc
    if not isinstance(envelope, dict):
        raise ValueError("RQ-003 canonical envelope must be an object")
    if set(envelope) != {"canonical_encoding_version", "value"}:
        raise ValueError("RQ-003 canonical envelope fields are invalid")
    encoding_version = envelope["canonical_encoding_version"]
    if (
        isinstance(encoding_version, bool)
        or encoding_version != CANONICAL_ENCODING_VERSION
    ):
        raise ValueError("RQ-003 canonical encoding version is unsupported")
    value = _decode_canonical_value(envelope["value"])
    if canonical_encode(value) != raw:
        raise ValueError("RQ-003 canonical encoding is not canonical")
    return value


def _canonical_value(value: object) -> Any:
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if hasattr(value, "to_identity_material"):
        return _canonical_value(value.to_identity_material())
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical floats must be finite")
        return {
            "type": "float64",
            "value": struct.pack(">d", value).hex(),
        }
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical mapping keys must be strings")
        return {
            "type": "mapping",
            "value": [
                [key, _canonical_value(item)]
                for key, item in sorted(value.items())
            ],
        }
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return {
            "type": "sequence",
            "value": [_canonical_value(item) for item in value],
        }
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _decode_canonical_value(value: Any) -> Any:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise ValueError("RQ-003 canonical value is invalid")
    value_type = value["type"]
    if value_type == "null":
        if set(value) != {"type"}:
            raise ValueError("RQ-003 canonical null is invalid")
        return None
    if set(value) != {"type", "value"}:
        raise ValueError("RQ-003 canonical value fields are invalid")
    encoded = value["value"]
    if value_type == "boolean":
        if not isinstance(encoded, bool):
            raise ValueError("RQ-003 canonical boolean is invalid")
        return encoded
    if value_type == "string":
        if not isinstance(encoded, str):
            raise ValueError("RQ-003 canonical string is invalid")
        return encoded
    if value_type == "integer":
        if not isinstance(encoded, str) or not _INTEGER_PATTERN.fullmatch(encoded):
            raise ValueError("RQ-003 canonical integer is invalid")
        return int(encoded)
    if value_type == "float64":
        if not isinstance(encoded, str) or not _FLOAT64_HEX_PATTERN.fullmatch(
            encoded
        ):
            raise ValueError("RQ-003 canonical float64 is invalid")
        result = struct.unpack(">d", bytes.fromhex(encoded))[0]
        if not math.isfinite(result):
            raise ValueError("RQ-003 canonical float64 must be finite")
        return result
    if value_type == "sequence":
        if not isinstance(encoded, list):
            raise ValueError("RQ-003 canonical sequence is invalid")
        return tuple(_decode_canonical_value(item) for item in encoded)
    if value_type == "mapping":
        if not isinstance(encoded, list):
            raise ValueError("RQ-003 canonical mapping is invalid")
        result: dict[str, Any] = {}
        prior_key: str | None = None
        for pair in encoded:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not isinstance(pair[0], str)
            ):
                raise ValueError("RQ-003 canonical mapping entry is invalid")
            key = pair[0]
            if key in result or (prior_key is not None and key <= prior_key):
                raise ValueError("RQ-003 canonical mapping keys are not ordered")
            result[key] = _decode_canonical_value(pair[1])
            prior_key = key
        return result
    raise ValueError("RQ-003 canonical value type is unsupported")


def _domain_identity(domain: str, material: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def _require_sha256(name: str, value: object) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _require_safe_name(name: str, value: object) -> None:
    if not isinstance(value, str) or not _SAFE_NAME_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase canonical name")


def _require_nonempty_string(name: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
    ):
        raise ValueError(f"{name} must be a nonempty canonical string")


def _require_member(name: str, value: object, allowed: frozenset[str]) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{name} is unsupported")


def _require_bool(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")


def _require_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _freeze_string_tuple(name: str, values: object) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be an immutable tuple of strings")
    frozen = values
    if not all(
        isinstance(item, str) and item and item.strip() == item
        for item in frozen
    ):
        raise ValueError(f"{name} must contain canonical nonempty strings")
    return frozen


def _require_unique(name: str, values: tuple[str, ...]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must be unique")


__all__ = (
    "CANONICAL_ENCODING_VERSION",
    "FEATURE_ELIGIBILITY_SCHEMA_VERSION",
    "FEATURE_METADATA_SCHEMA_VERSION",
    "FeatureEligibilityDecision",
    "FeatureEligibilityStatus",
    "FeatureHistoryPolicy",
    "FeatureMetadata",
    "FeatureOutputField",
    "canonical_decode",
    "canonical_encode",
    "reconstruct_executable_binding_identity",
)
