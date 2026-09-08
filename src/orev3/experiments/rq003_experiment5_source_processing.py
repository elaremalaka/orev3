"""Finite, outcome-blind source processing for RQ-003 Experiment 005.

This module authenticates an ordered lifecycle/observation collection and
emits the frozen flat projection.  It has no outcome opener or evaluation
capability and is not an adapter, Source S, or execution entry point.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from array import array
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

from pydantic import TypeAdapter, ValidationError

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    parse_json,
    validate_json_schema_instance,
)
from orev3.execution.replay_preparation import SOURCE_UNIT_DOMAIN
from orev3.experiments.rq003_experiment5_source_measurements import (
    PIPELINE,
    SourceDecisionObservation,
    SourceDecisionSnapshot,
    SourceObservationReference,
)

SOURCE_CONVENTION_REVISION = "rq003-experiment-005-two-tier-source-v1"
CONFIGURATION_IDENTIFIER = "rq003-experiment-005-source-processing-v1"
DECODER_IDENTIFIER = "rq003-experiment-005-source-decoder-v1"
PROJECTOR_IDENTIFIER = "rq003-experiment-005-outcome-blind-projector-v1"
DATASET_VERSION = "replay-dataset-v1"
EXECUTION_SPECIFICATION_REVISION = "rq003-research-execution-specification-v2"
EXPERIMENT5_CANDIDATES = tuple(range(25))
EXPERIMENT5_DATASET_SHA256 = "7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7"
EXPERIMENT5_DECISION_SELECTION_IDENTITY = "203588f4a5acb6befd71c088a84145096f185addb8b605c386aa4c1f70bd9622"
EXPERIMENT5_MINIMUM_EFFECT_CLARIFICATION_SHA256 = "f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b"
EXPERIMENT5_PROTOCOL_SHA256 = "38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc"
EXPERIMENT5_SOURCE_PROCESSING_PREREQUISITE_SHA256 = "d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4"
EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION = "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]*")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_TRACKED_INTEGER_ADAPTER = TypeAdapter(int)
MAX_FRAMED_RECORD_BYTES = 22_694
MAX_DECODED_STRING_VALUE_BYTES = 64
MAX_DECODED_OBJECT_KEY_BYTES = 37
MAX_CANONICAL_SCALAR_BYTES = 20
MAX_JSON_DEPTH = 4
MAX_OBJECT_MEMBERS = 18
MAX_ARRAY_CARDINALITY = 146
MAX_LIFECYCLE_REFERENCES = 146
MAX_PROJECTION_RECORD_BYTES = 227_867_665
_CONFIGURATION_FIELDS = frozenset({
    "candidate_order", "configuration_identifier", "controller_identifier",
    "dataset_version", "decision_selection_identifier",
    "decision_selection_identity", "decoder_identifier", "identity_domains",
    "lifecycle_schema_authority", "lifecycle_schema_identity",
    "lifecycle_schema_version",
    "maximum_aggregate_bytes", "maximum_member_bytes", "maximum_members",
    "maximum_projection_bytes", "maximum_records",
    "minimum_effect_clarification_sha256", "observation_schema_authorities",
    "observation_schema_identities",
    "observation_schema_versions", "projection_schema_identity",
    "projection_schema_path", "projection_schema_sha256",
    "projector_identifier", "protocol_sha256",
    "source_processing_prerequisite_sha256", "supported_protocol_revision",
})
BOUNDED_STREAMING_MEASUREMENT_MODE = "BOUNDED_STREAMING_MEASUREMENT_CANDIDATE"
BOUNDED_STREAMING_ADOPTED_MODE = "BOUNDED_STREAMING_NUMERIC_ENVELOPE_ADOPTED"
BOUNDED_STREAMING_AUTHORITY_GENERATION = (
    "prospective-v1.1-adapter-v4-experiment5-bounded-streaming"
)
BOUNDED_STREAMING_POLICY_IDENTIFIER = (
    "experiment-evidence-preparation-policy-bounded-streaming-v1"
)
BOUNDED_STREAMING_POLICY_PATH = (
    "config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json"
)
BOUNDED_STREAMING_POLICY_REVISION = "1"
BOUNDED_SOURCE_CONFIGURATION_MATERIAL_DOMAIN = (
    "orev3:rq003-experiment-005:bounded-source-processing-configuration-material:v1\n"
)
BOUNDED_POLICY_BINDING_DOMAIN = (
    "orev3:rq003-experiment-005:bounded-evidence-preparation-policy-binding:v1\n"
)
DEFERRED_NUMERIC_FIELDS = (
    "max_controller_peak_rss_bytes",
    "max_projection_bytes",
    "max_temporary_disk_bytes",
    "max_worker_peak_rss_bytes",
    "watchdog_poll_interval_milliseconds",
    "watchdog_rss_bytes",
)
_BOUNDED_COMMON_FIELDS = frozenset(
    {"bounded_evidence_preparation_policy_binding_identity", "numeric_envelope_mode"}
)
_BOUNDED_MEASUREMENT_FIELDS = _CONFIGURATION_FIELDS | _BOUNDED_COMMON_FIELDS | {
    "deferred_numeric_fields"
}
_BOUNDED_ADOPTED_FIELDS = _CONFIGURATION_FIELDS | _BOUNDED_COMMON_FIELDS

_LIFECYCLE_PATHS = frozenset(
    {
        "lifecycle_schema_version", "round_id", "start_slot", "end_slot",
        "first_observed_at_utc", "last_observed_at_utc",
        "first_observed_rpc_slot", "last_observed_rpc_slot",
        "observation_count", "collector_session_ids", "source_schema_versions",
        "source_files", "observation_references.*.source_file",
        "observation_references.*.source_line_number",
        "observation_references.*.observed_at_utc",
        "observation_references.*.rpc_slot", "quality.coverage_status",
        "quality.initialization_state_observed",
        "quality.rpc_slot_regression_count", "quality.largest_rpc_slot_regression",
        "quality.duplicate_rpc_slot_count", "quality.max_observation_gap_seconds",
        "quality.significant_gap_count", "quality.significant_gap_threshold_seconds",
        "quality.collector_session_count",
    }
)
_OBSERVATION_PATHS = frozenset(
    {
        "schema_version", "collector_session_id", "observed_at_utc", "rpc_slot",
        "board.round_id", "board.start_slot", "board.end_slot",
        "board.production_cost_ema", "treasury.motherlode", "round.round_id",
        "round.deployed_lamports", "round.miner_counts", "round.motherlode",
        "round.total_vaulted", "round.total_winnings", "round.total_miners",
    }
)
_TRACKED_OPAQUE_OBSERVATION_SHAPES = frozenset(
    {
        "round.entropy",
        "round.expires_at",
        "round.mass",
        "round.rewards",
        "round.slot_hash_hex",
        "round.top_miner",
    }
)
_FORBIDDEN_PROJECTION_KEYS = frozenset(
    {"winner", "winning_square", "finalized_outcome", "label", "won",
     "outcome", "outcome_availability", "outcome_provenance", "capture_mode",
     "outcome_source", "outcome_locator", "outcome_opener", "outcome_parser",
     "outcome_provider", "outcome_resolver", "evaluation", "join_callback"}
)
_EXTERNAL_INPUT_MEMBER_DOMAIN = "orev3:readiness-adapter-external-input-member:v1"
_EXTERNAL_INPUT_MANIFEST_DOMAIN = "orev3:readiness-adapter-external-input-manifest:v1"
_EXTERNAL_INPUT_DECLARATION_DOMAIN = "orev3:readiness-adapter-external-input:v1"
_INPUT_SNAPSHOT_DOMAIN = "orev3:experiment-input-snapshot:v1"
_DECODER_CONFIGURATION_DOMAIN = "orev3:readiness-adapter-decoder-configuration:v1"
_COMPONENT_BINDING_DOMAIN = "orev3:experiment-phase3b-component-binding:v1"
_RAW_SCHEMA_CONTRACT_DOMAIN = "orev3:experiment-raw-dataset-schema:v1"
_PROJECTION_SCHEMA_CONTRACT_DOMAIN = "orev3:experiment-outcome-blind-projection-schema:v1"
_DATASET_CONTENT_DOMAIN = "orev3:experiment-dataset-content:v1"
_PROJECTION_EVIDENCE_DOMAIN = "orev3:experiment-outcome-blind-projection:v1"

_TRACKED_MODEL_BLOB = {
    "git_blob_identity": "eeb5e237aa5fc763adc166f812a3024cc70b3265",
    "path": "src/orev3/historical/models.py",
    "sha256": "e062903f86f81a7bf825ce0f30eaebc4af880510364a112fd90f13395367c4b6",
}
_TRACKED_READER_BLOB = {
    "git_blob_identity": "8644b71da9bd41e30754a09633861fa1f20b4e76",
    "path": "src/orev3/historical/reader.py",
    "sha256": "0c7acec0a98e6d5967171c7f900a40daf0ee9b1dd46cf973fae59e06049b7359",
}
_TRACKED_LOADER_BLOB = {
    "git_blob_identity": "76747354f1a89e6952322cca2a6ce7db312da90e",
    "path": "src/orev3/replay/loader.py",
    "sha256": "e4f71b6a985ced0411df348dfa525db1dcaf359747bd328ebc85a3eeeba80963",
}


def _expected_lifecycle_schema_authority() -> dict[str, Any]:
    return {
        "authority_kind": "tracked-pydantic-model-and-loader-v1",
        "loader": dict(_TRACKED_LOADER_BLOB),
        "loader_qualname": "orev3.replay.loader:load_round_index",
        "model": dict(_TRACKED_MODEL_BLOB),
        "model_qualname": "orev3.historical.models:RoundLifecycleIndexRecord",
        "schema_version": 1,
    }


def _expected_observation_schema_authority(version: int) -> dict[str, Any]:
    return {
        "authority_kind": "tracked-normalized-snapshot-v1",
        "model": dict(_TRACKED_MODEL_BLOB),
        "model_qualname": "orev3.historical.models:NormalizedSnapshot",
        "normalizer": dict(_TRACKED_READER_BLOB),
        "normalizer_qualname": "orev3.historical.reader:normalize_snapshot",
        "schema_version": version,
        "supported_versions_qualname": "orev3.historical.reader:SUPPORTED_SCHEMA_VERSIONS",
    }


def reconstruct_tracked_schema_identities(
    configuration: Mapping[str, Any],
) -> tuple[str, Mapping[str, str]]:
    lifecycle = configuration.get("lifecycle_schema_authority")
    observations = configuration.get("observation_schema_authorities")
    if lifecycle != _expected_lifecycle_schema_authority() or not isinstance(
        observations, Mapping
    ) or observations != {
        "1": _expected_observation_schema_authority(1),
        "2": _expected_observation_schema_authority(2),
    }:
        raise _fail("RAW_SCHEMA_AUTHORITY_MISMATCH")
    lifecycle_identity = _identity(_RAW_SCHEMA_CONTRACT_DOMAIN, lifecycle)
    observation_identities = {
        version: _identity(_RAW_SCHEMA_CONTRACT_DOMAIN, authority)
        for version, authority in observations.items()
    }
    if configuration.get("lifecycle_schema_identity") != lifecycle_identity or configuration.get(
        "observation_schema_identities"
    ) != observation_identities:
        raise _fail("RAW_SCHEMA_IDENTITY_SUBSTITUTION")
    return lifecycle_identity, observation_identities


def _fail(code: str) -> CanonicalControlError:
    return CanonicalControlError(code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _identity(domain: str, material: Mapping[str, Any]) -> str:
    return domain_identity(domain + "\n", material)


def authenticate_configuration(
    raw: bytes, *, expected_byte_count: int, expected_sha256: str,
    configuration_path: str = "config/research/readiness/rq003-experiment-005-source-processing-v1.json",
    configuration_git_blob_identity: str = "0" * 40,
) -> tuple[Mapping[str, Any], str, str]:
    """Authenticate the one finite decoder/configuration authority object."""
    if len(raw) != expected_byte_count or _sha(raw) != expected_sha256:
        raise _fail("CONFIGURATION_SUBSTITUTION")
    parsed = parse_json(raw)
    if not isinstance(parsed, dict):
        raise _fail("CONFIGURATION_INVALID")
    fields = set(parsed)
    if fields == _CONFIGURATION_FIELDS:
        configuration_mode = "legacy"
    elif fields == _BOUNDED_MEASUREMENT_FIELDS:
        configuration_mode = "measurement"
    elif fields == _BOUNDED_ADOPTED_FIELDS:
        configuration_mode = "adopted"
    else:
        raise _fail("CONFIGURATION_INVALID")
    if canonical_bytes(parsed) != raw:
        raise _fail("CONFIGURATION_NONCANONICAL")
    expected = {
        "configuration_identifier": CONFIGURATION_IDENTIFIER,
        "controller_identifier": "rq003-experiment-005-source-controller-v1",
        "dataset_version": DATASET_VERSION,
        "decision_selection_identifier": "end-slot-minus-5-latest-normal-v1",
        "decoder_identifier": DECODER_IDENTIFIER,
        "lifecycle_schema_version": 1,
        "candidate_order": list(EXPERIMENT5_CANDIDATES),
        "decision_selection_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
        "minimum_effect_clarification_sha256": EXPERIMENT5_MINIMUM_EFFECT_CLARIFICATION_SHA256,
        "observation_schema_versions": [1, 2],
        "projection_schema_path": "src/orev3/execution/schemas/v1/rq003-experiment-005-projection.schema.json",
        "projector_identifier": PROJECTOR_IDENTIFIER,
        "protocol_sha256": EXPERIMENT5_PROTOCOL_SHA256,
        "source_processing_prerequisite_sha256": EXPERIMENT5_SOURCE_PROCESSING_PREREQUISITE_SHA256,
        "supported_protocol_revision": EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION,
    }
    if any(parsed.get(key) != value for key, value in expected.items()):
        raise _fail("CONFIGURATION_AUTHORITY_MISMATCH")
    if parsed.get("identity_domains") != {
        "component": _COMPONENT_BINDING_DOMAIN,
        "decoder_configuration": _DECODER_CONFIGURATION_DOMAIN,
        "external_input": _EXTERNAL_INPUT_DECLARATION_DOMAIN,
        "external_input_manifest": _EXTERNAL_INPUT_MANIFEST_DOMAIN,
        "external_input_member": _EXTERNAL_INPUT_MEMBER_DOMAIN,
        "input_snapshot": _INPUT_SNAPSHOT_DOMAIN,
        "projection_schema": _PROJECTION_SCHEMA_CONTRACT_DOMAIN,
        "raw_schema": _RAW_SCHEMA_CONTRACT_DOMAIN,
    }:
        raise _fail("CONFIGURATION_AUTHORITY_MISMATCH")
    if parsed.get("observation_schema_versions") != [1, 2]:
        raise _fail("CONFIGURATION_AUTHORITY_MISMATCH")
    reconstruct_tracked_schema_identities(parsed)
    expected_limits = (
        {
            "maximum_aggregate_bytes": 268_435_456,
            "maximum_member_bytes": 67_108_864,
            "maximum_members": 256,
            "maximum_projection_bytes": 134_217_728,
            "maximum_records": 100_000,
        }
        if configuration_mode == "legacy"
        else {
            "maximum_aggregate_bytes": 1_749_809_411,
            "maximum_member_bytes": 227_867_665,
            "maximum_members": 256,
            "maximum_projection_bytes": 328_739_211_471_540,
            "maximum_records": 1_442_676,
        }
    )
    if {key: parsed.get(key) for key in expected_limits} != expected_limits:
        raise _fail("CONFIGURATION_AUTHORITY_MISMATCH")
    if configuration_mode == "measurement" and (
        parsed.get("numeric_envelope_mode") != BOUNDED_STREAMING_MEASUREMENT_MODE
        or parsed.get("deferred_numeric_fields") != list(DEFERRED_NUMERIC_FIELDS)
    ):
        raise _fail("CONFIGURATION_AUTHORITY_MISMATCH")
    if configuration_mode == "adopted" and parsed.get(
        "numeric_envelope_mode"
    ) != BOUNDED_STREAMING_ADOPTED_MODE:
        raise _fail("CONFIGURATION_AUTHORITY_MISMATCH")
    schema_sha = parsed.get("projection_schema_sha256")
    if not isinstance(schema_sha, str) or _SHA256.fullmatch(schema_sha) is None:
        raise _fail("CONFIGURATION_INVALID")
    configuration_identity = _identity(_DECODER_CONFIGURATION_DOMAIN, {
        "configuration_byte_count": expected_byte_count,
        "configuration_git_blob_identity": configuration_git_blob_identity,
        "configuration_path": configuration_path,
        "configuration_sha256": expected_sha256,
    })
    schema_identity = str(parsed.get("projection_schema_identity", ""))
    if _SHA256.fullmatch(schema_identity) is None:
        raise _fail("CONFIGURATION_INVALID")
    return parsed, configuration_identity, schema_identity


def reconstruct_bounded_source_processing_material_identity(
    configuration: Mapping[str, Any],
) -> str:
    material = dict(configuration)
    material.pop("bounded_evidence_preparation_policy_binding_identity", None)
    return domain_identity(BOUNDED_SOURCE_CONFIGURATION_MATERIAL_DOMAIN, material)


def reconstruct_rq003_experiment5_bounded_policy_binding_identity(
    configuration: Mapping[str, Any], policy: Mapping[str, Any]
) -> str:
    mode = configuration.get("numeric_envelope_mode")
    limits = policy.get("limits")
    if not isinstance(limits, Mapping) or limits.get("numeric_envelope_mode") != mode:
        raise _fail("PROFILE_POLICY_MISMATCH")
    if mode == BOUNDED_STREAMING_MEASUREMENT_MODE:
        deferred = configuration.get("deferred_numeric_fields")
        if deferred != limits.get("deferred_numeric_fields") or deferred != list(
            DEFERRED_NUMERIC_FIELDS
        ):
            raise _fail("PROFILE_POLICY_MISMATCH")
    elif mode == BOUNDED_STREAMING_ADOPTED_MODE:
        if "deferred_numeric_fields" in configuration or "deferred_numeric_fields" in limits:
            raise _fail("PROFILE_POLICY_MISMATCH")
        deferred = None
    else:
        raise _fail("PROFILE_POLICY_MISMATCH")
    generic_limits = {
        "max_aggregate_collection_bytes": limits.get("max_aggregate_collection_bytes"),
        "max_collection_members": limits.get("max_collection_members"),
        "max_file_bytes": limits.get("max_file_bytes"),
        "max_projection_bytes": limits.get("max_projection_bytes"),
        "max_source_records": limits.get("max_source_records"),
    }
    source_limits = {
        "maximum_aggregate_bytes": configuration.get("maximum_aggregate_bytes"),
        "maximum_member_bytes": configuration.get("maximum_member_bytes"),
        "maximum_members": configuration.get("maximum_members"),
        "maximum_projection_bytes": configuration.get("maximum_projection_bytes"),
        "maximum_records": configuration.get("maximum_records"),
    }
    if any(
        configuration[source_name] != limits[policy_name]
        for source_name, policy_name in (
            ("maximum_members", "max_collection_members"),
            ("maximum_aggregate_bytes", "max_aggregate_collection_bytes"),
            ("maximum_member_bytes", "max_file_bytes"),
            ("maximum_records", "max_source_records"),
            ("maximum_projection_bytes", "max_projection_bytes"),
        )
    ):
        raise _fail("PROFILE_POLICY_MISMATCH")
    material: dict[str, Any] = {
        "authority_generation": BOUNDED_STREAMING_AUTHORITY_GENERATION,
        "evidence_preparation_policy_identifier": BOUNDED_STREAMING_POLICY_IDENTIFIER,
        "evidence_preparation_policy_identity": policy.get("policy_identity"),
        "evidence_preparation_policy_path": BOUNDED_STREAMING_POLICY_PATH,
        "evidence_preparation_policy_revision": BOUNDED_STREAMING_POLICY_REVISION,
        "generic_limits": generic_limits,
        "numeric_envelope_mode": mode,
        "source_processing_configuration_identifier": CONFIGURATION_IDENTIFIER,
        "source_processing_configuration_material_identity": reconstruct_bounded_source_processing_material_identity(
            configuration
        ),
        "source_processing_limits": source_limits,
    }
    if deferred is not None:
        material["deferred_numeric_fields"] = deferred
    return domain_identity(BOUNDED_POLICY_BINDING_DOMAIN, material)


def _integer(name: str, value: object, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise _fail(f"INVALID_{name.upper()}")
    return value


def _timestamp(value: object) -> tuple[str, datetime]:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise _fail("INVALID_TIMESTAMP")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise _fail("INVALID_TIMESTAMP")
    fraction = value.removesuffix("Z").partition(".")[2]
    if fraction and fraction.endswith("0"):
        raise _fail("NONCANONICAL_TIMESTAMP")
    return value, parsed


def _decimal_microseconds(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise _fail(f"INVALID_{name.upper()}")
    value = str(value)
    if "e" in value.lower() or value.startswith("-") or value == "-0":
        raise _fail(f"INVALID_{name.upper()}")
    try:
        result = Decimal(value) * 1_000_000
    except InvalidOperation as exc:
        raise _fail(f"INVALID_{name.upper()}") from exc
    if not result.is_finite() or result != result.to_integral_value():
        raise _fail(f"INVALID_{name.upper()}")
    return int(result)


def _tracked_integer_accepted(value: object) -> bool:
    try:
        _TRACKED_INTEGER_ADAPTER.validate_python(value)
    except ValidationError:
        return False
    return True


class _SelectiveParser:
    """Strict JSON parser that never materializes values outside a whitelist."""

    def __init__(self, raw: bytes, paths: frozenset[str]) -> None:
        if len(raw) + 1 > MAX_FRAMED_RECORD_BYTES:
            raise _fail("RESOURCE_MEMORY_EXCEEDED")
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
            raise _fail("INVALID_JSON_FRAMING")
        try:
            self.text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _fail("INVALID_UTF8") from exc
        self.paths = paths
        self.i = 0
        self.decoder = json.JSONDecoder()
        self.seen_paths: set[str] = set()
        self.opaque_shapes: dict[str, object] = {}

    def parse(self) -> dict[str, Any]:
        result = self._value((), 1)
        self._ws()
        if self.i != len(self.text) or not isinstance(result, dict):
            raise _fail("MALFORMED_JSON")
        return result

    def _ws(self) -> None:
        while self.i < len(self.text) and self.text[self.i] in " \t\n\r":
            self.i += 1

    def _wanted(self, path: tuple[str, ...]) -> tuple[bool, bool]:
        key = ".".join(path)
        exact = key in self.paths
        prefix = any(item.startswith(key + ".") for item in self.paths) if key else True
        return exact, prefix

    def _string(self, *, key: bool = False) -> str:
        try:
            value, end = self.decoder.raw_decode(self.text, self.i)
        except (json.JSONDecodeError, ValueError) as exc:
            raise _fail("MALFORMED_JSON") from exc
        if not isinstance(value, str) or unicodedata.normalize("NFC", value) != value:
            raise _fail("INVALID_STRING")
        maximum = (
            MAX_DECODED_OBJECT_KEY_BYTES if key else MAX_DECODED_STRING_VALUE_BYTES
        )
        if len(value.encode("utf-8")) > maximum:
            raise _fail("RESOURCE_MEMORY_EXCEEDED")
        self.i = end
        return value

    def _value(self, path: tuple[str, ...], depth: int) -> Any:
        if depth > MAX_JSON_DEPTH:
            raise _fail("RESOURCE_MEMORY_EXCEEDED")
        self._ws()
        exact, prefix = self._wanted(path)
        if not exact and not prefix:
            self._skip(path, depth)
            return _OMITTED
        if self.i >= len(self.text):
            raise _fail("MALFORMED_JSON")
        char = self.text[self.i]
        if char == "{":
            return self._object(path, depth)
        if char == "[":
            return self._array(path, depth)
        try:
            value, end = self.decoder.raw_decode(self.text, self.i)
        except (json.JSONDecodeError, ValueError) as exc:
            raise _fail("MALFORMED_JSON") from exc
        if isinstance(value, float):
            if not math.isfinite(value):
                raise _fail("MALFORMED_JSON")
            lexeme = self.text[self.i:end]
            value = lexeme
        elif isinstance(value, str):
            if len(value.encode("utf-8")) > MAX_DECODED_STRING_VALUE_BYTES:
                raise _fail("RESOURCE_MEMORY_EXCEEDED")
        elif len(self.text[self.i:end].encode("utf-8")) > MAX_CANONICAL_SCALAR_BYTES:
            raise _fail("RESOURCE_MEMORY_EXCEEDED")
        self.i = end
        return value

    def _object(self, path: tuple[str, ...], depth: int) -> dict[str, Any]:
        self.i += 1
        result: dict[str, Any] = {}
        seen: set[str] = set()
        self._ws()
        if self.i < len(self.text) and self.text[self.i] == "}":
            self.i += 1
            return result
        while True:
            self._ws()
            key = self._string(key=True)
            if key in seen:
                raise _fail("DUPLICATE_JSON_KEY")
            seen.add(key)
            if len(seen) > MAX_OBJECT_MEMBERS:
                raise _fail("RESOURCE_MEMORY_EXCEEDED")
            self.seen_paths.add(".".join(path + (key,)))
            self._ws()
            if self.i >= len(self.text) or self.text[self.i] != ":":
                raise _fail("MALFORMED_JSON")
            self.i += 1
            value = self._value(path + (key,), depth + 1)
            if value is not _OMITTED:
                result[key] = value
            self._ws()
            if self.i >= len(self.text):
                raise _fail("MALFORMED_JSON")
            char = self.text[self.i]
            self.i += 1
            if char == "}":
                return result
            if char != ",":
                raise _fail("MALFORMED_JSON")

    def _array(self, path: tuple[str, ...], depth: int) -> list[Any]:
        self.i += 1
        result: list[Any] = []
        cardinality = 0
        exact, _ = self._wanted(path)
        child_path = path if exact else path + ("*",)
        self._ws()
        if self.i < len(self.text) and self.text[self.i] == "]":
            self.i += 1
            return result
        while True:
            if cardinality >= MAX_ARRAY_CARDINALITY:
                raise _fail("RESOURCE_MEMORY_EXCEEDED")
            value = self._value(child_path, depth + 1)
            cardinality += 1
            if value is not _OMITTED:
                result.append(value)
            self._ws()
            if self.i >= len(self.text):
                raise _fail("MALFORMED_JSON")
            char = self.text[self.i]
            self.i += 1
            if char == "]":
                return result
            if char != ",":
                raise _fail("MALFORMED_JSON")

    def _skip(self, path: tuple[str, ...] = (), depth: int = 1) -> object:
        """Validate one JSON value lexically without decoding its semantics."""
        if depth > MAX_JSON_DEPTH:
            raise _fail("RESOURCE_MEMORY_EXCEEDED")
        self._ws()
        if self.i >= len(self.text):
            raise _fail("MALFORMED_JSON")
        char = self.text[self.i]
        path_key = ".".join(path)
        if char == '"':
            start = self.i
            self._skip_string()
            value = json.loads(self.text[start:self.i])
            if len(value.encode("utf-8")) > MAX_DECODED_STRING_VALUE_BYTES:
                raise _fail("RESOURCE_MEMORY_EXCEEDED")
            shape: object = ("string", _tracked_integer_accepted(value))
            if path_key in _TRACKED_OPAQUE_OBSERVATION_SHAPES:
                self.opaque_shapes[path_key] = shape
            return shape
        if char == "{":
            self.i += 1; seen: set[str] = set(); self._ws()
            if self.i < len(self.text) and self.text[self.i] == "}":
                self.i += 1
                shape = ("object",)
                if path_key in _TRACKED_OPAQUE_OBSERVATION_SHAPES:
                    self.opaque_shapes[path_key] = shape
                return shape
            while True:
                self._ws(); key = self._string(key=True)
                if key in seen: raise _fail("DUPLICATE_JSON_KEY")
                seen.add(key)
                if len(seen) > MAX_OBJECT_MEMBERS:
                    raise _fail("RESOURCE_MEMORY_EXCEEDED")
                self._ws()
                if self.i >= len(self.text) or self.text[self.i] != ":": raise _fail("MALFORMED_JSON")
                self.i += 1; self._skip(path + (key,), depth + 1); self._ws()
                if self.i >= len(self.text): raise _fail("MALFORMED_JSON")
                token = self.text[self.i]; self.i += 1
                if token == "}":
                    shape = ("object",)
                    if path_key in _TRACKED_OPAQUE_OBSERVATION_SHAPES:
                        self.opaque_shapes[path_key] = shape
                    return shape
                if token != ",": raise _fail("MALFORMED_JSON")
        elif char == "[":
            self.i += 1; self._ws(); element_shapes: list[object] = []
            if self.i < len(self.text) and self.text[self.i] == "]":
                self.i += 1
                shape = ("array", 0, ())
                if path_key in _TRACKED_OPAQUE_OBSERVATION_SHAPES:
                    self.opaque_shapes[path_key] = shape
                return shape
            while True:
                if len(element_shapes) >= MAX_ARRAY_CARDINALITY:
                    raise _fail("RESOURCE_MEMORY_EXCEEDED")
                element_shapes.append(self._skip(path + ("*",), depth + 1)); self._ws()
                if self.i >= len(self.text): raise _fail("MALFORMED_JSON")
                token = self.text[self.i]; self.i += 1
                if token == "]":
                    shape = ("array", len(element_shapes), tuple(element_shapes))
                    if path_key in _TRACKED_OPAQUE_OBSERVATION_SHAPES:
                        self.opaque_shapes[path_key] = shape
                    return shape
                if token != ",": raise _fail("MALFORMED_JSON")
        else:
            match = re.match(
                r"(?:-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false|null)",
                self.text[self.i:],
            )
            if match is None:
                raise _fail("MALFORMED_JSON")
            lexeme = match.group(0)
            if len(lexeme.encode("utf-8")) > MAX_CANONICAL_SCALAR_BYTES:
                raise _fail("RESOURCE_MEMORY_EXCEEDED")
            self.i += len(lexeme)
            semantic_scalar = json.loads(lexeme)
            if lexeme == "null":
                shape = ("null",)
            elif lexeme in {"true", "false"}:
                shape = ("boolean", _tracked_integer_accepted(semantic_scalar))
            elif re.fullmatch(r"-?(?:0|[1-9][0-9]*)", lexeme):
                shape = ("integer", _tracked_integer_accepted(semantic_scalar))
            else:
                shape = ("number", _tracked_integer_accepted(semantic_scalar))
            if path_key in _TRACKED_OPAQUE_OBSERVATION_SHAPES:
                self.opaque_shapes[path_key] = shape
            return shape

    def _skip_string(self) -> None:
        if self.i >= len(self.text) or self.text[self.i] != '"':
            raise _fail("MALFORMED_JSON")
        self.i += 1
        while self.i < len(self.text):
            char = self.text[self.i]
            if char == '"':
                self.i += 1
                return
            if ord(char) < 0x20:
                raise _fail("MALFORMED_JSON")
            if char != "\\":
                self.i += 1
                continue
            self.i += 1
            if self.i >= len(self.text):
                raise _fail("MALFORMED_JSON")
            escape = self.text[self.i]
            if escape in '"\\/bfnrt':
                self.i += 1
                continue
            if escape == "u" and re.fullmatch(
                r"[0-9a-fA-F]{4}", self.text[self.i + 1:self.i + 5]
            ):
                self.i += 5
                continue
            raise _fail("MALFORMED_JSON")
        raise _fail("MALFORMED_JSON")


_OMITTED = object()


@dataclass(frozen=True, slots=True)
class SourceMember:
    logical_identifier: str
    member_path: str
    member_order: int
    persisted_bytes: bytes
    expected_byte_count: int
    expected_sha256: str
    declared_member_identity: str = ""

    def __post_init__(self) -> None:
        if _IDENTIFIER.fullmatch(self.logical_identifier) is None:
            raise _fail("INVALID_MEMBER_IDENTIFIER")
        path = PurePosixPath(self.member_path)
        if str(path) != self.member_path or path.is_absolute() or ".." in path.parts:
            raise _fail("INVALID_MEMBER_PATH")
        _integer("member_order", self.member_order)
        if len(self.persisted_bytes) != self.expected_byte_count or _sha(self.persisted_bytes) != self.expected_sha256:
            raise _fail("INPUT_SUBSTITUTION")
        if not self.persisted_bytes.endswith(b"\n") or b"\r" in self.persisted_bytes:
            raise _fail("INVALID_JSONL_FRAMING")
        if self.declared_member_identity and self.declared_member_identity != self.member_identity:
            raise _fail("MEMBER_IDENTITY_SUBSTITUTION")

    @property
    def member_identity(self) -> str:
        return _identity(_EXTERNAL_INPUT_MEMBER_DOMAIN, {
            "byte_count": self.expected_byte_count, "logical_identifier": self.logical_identifier,
            "member_order": self.member_order, "member_path": self.member_path,
            "sha256": self.expected_sha256,
        })


@dataclass(frozen=True, slots=True)
class SnapshotSourceMember:
    """Authenticated path-backed member; source payload bytes are never retained."""

    logical_identifier: str
    member_path: str
    member_order: int
    content_object: Path
    expected_byte_count: int
    expected_sha256: str
    declared_member_identity: str = ""

    def __post_init__(self) -> None:
        if _IDENTIFIER.fullmatch(self.logical_identifier) is None:
            raise _fail("INVALID_MEMBER_IDENTIFIER")
        path = PurePosixPath(self.member_path)
        if str(path) != self.member_path or path.is_absolute() or ".." in path.parts:
            raise _fail("INVALID_MEMBER_PATH")
        _integer("member_order", self.member_order)
        if (
            _SHA256.fullmatch(self.expected_sha256) is None
            or self.expected_byte_count < 1
        ):
            raise _fail("INPUT_SUBSTITUTION")
        if self.declared_member_identity and self.declared_member_identity != self.member_identity:
            raise _fail("MEMBER_IDENTITY_SUBSTITUTION")

    @property
    def member_identity(self) -> str:
        return _identity(_EXTERNAL_INPUT_MEMBER_DOMAIN, {
            "byte_count": self.expected_byte_count,
            "logical_identifier": self.logical_identifier,
            "member_order": self.member_order,
            "member_path": self.member_path,
            "sha256": self.expected_sha256,
        })


class _IndexedRecords(Sequence[tuple[bytes, dict[str, Any]]]):
    """Compact offsets over a descriptor-pinned, completely authenticated member."""

    __slots__ = ("_descriptor", "_lengths", "_offsets", "_paths")

    def __init__(
        self, member: SnapshotSourceMember, paths: frozenset[str]
    ) -> None:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(member.content_object, flags)
        except OSError as exc:
            raise _fail("INPUT_SUBSTITUTION") from exc
        self._descriptor = descriptor
        self._paths = paths
        self._offsets = array("Q")
        self._lengths = array("I")
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or opened.st_size != member.expected_byte_count
            ):
                raise _fail("INPUT_SUBSTITUTION")
            digest = hashlib.sha256()
            total = 0
            line_start = 0
            pending = bytearray()
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
                if total > member.expected_byte_count:
                    raise _fail("INPUT_SUBSTITUTION")
                pending.extend(chunk)
                while True:
                    newline = pending.find(b"\n")
                    if newline < 0:
                        if len(pending) >= MAX_FRAMED_RECORD_BYTES:
                            raise _fail("RESOURCE_MEMORY_EXCEEDED")
                        break
                    framed = newline + 1
                    if framed > MAX_FRAMED_RECORD_BYTES:
                        raise _fail("RESOURCE_MEMORY_EXCEEDED")
                    if framed == 1 or b"\r" in pending[:framed]:
                        raise _fail("INVALID_JSONL_FRAMING")
                    self._offsets.append(line_start)
                    self._lengths.append(framed)
                    del pending[:framed]
                    line_start += framed
            closed = os.fstat(descriptor)
            fingerprint = lambda value: (
                value.st_dev, value.st_ino, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns,
            )
            if (
                pending
                or total != member.expected_byte_count
                or digest.hexdigest() != member.expected_sha256
                or fingerprint(opened) != fingerprint(closed)
            ):
                raise _fail("INPUT_SUBSTITUTION")
        except BaseException:
            os.close(descriptor)
            self._descriptor = -1
            raise

    def __len__(self) -> int:
        return len(self._offsets)

    def __getitem__(self, index: int) -> tuple[bytes, dict[str, Any]]:
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError(index)
        length = int(self._lengths[index])
        raw = os.pread(self._descriptor, length, int(self._offsets[index]))
        if len(raw) != length or not raw.endswith(b"\n"):
            raise _fail("INPUT_MUTATED")
        parser = _SelectiveParser(raw[:-1], self._paths)
        return raw, _require_tracked_record(parser, self._paths)

    def __iter__(self) -> Iterator[tuple[bytes, dict[str, Any]]]:
        for index in range(len(self)):
            yield self[index]

    def close(self) -> None:
        if self._descriptor >= 0:
            os.close(self._descriptor)
            self._descriptor = -1

    def __del__(self) -> None:
        self.close()


@dataclass(frozen=True, slots=True)
class SourceProcessingAuthority:
    external_input_identifier: str
    external_input_identity: str
    ordered_collection_manifest_identity: str
    immutable_input_snapshot_identity: str
    decoder_component_identity: str
    decoder_configuration_identity: str
    parser_component_identity: str
    projector_component_identity: str
    raw_schema_identity: str
    projection_schema_identity: str

    def __post_init__(self) -> None:
        if _IDENTIFIER.fullmatch(self.external_input_identifier) is None:
            raise _fail("INVALID_EXTERNAL_INPUT_IDENTIFIER")
        for name in self.__dataclass_fields__:
            if name == "external_input_identifier": continue
            if _SHA256.fullmatch(getattr(self, name)) is None:
                raise _fail("INVALID_AUTHORITY_IDENTITY")


def reconstruct_source_authority(
    *, declaration: Mapping[str, Any], snapshot: Mapping[str, Any],
    decoder: Mapping[str, Any], parser_component: Mapping[str, Any],
    projector_component: Mapping[str, Any], raw_schema: Mapping[str, Any],
    projection_schema: Mapping[str, Any],
) -> SourceProcessingAuthority:
    """Reconstruct every governed root; no supplied hash-shaped root is trusted."""
    members = declaration.get("members")
    if not isinstance(members, list) or not members:
        raise _fail("DECLARATION_INVALID")
    reconstructed_members = []
    member_paths: set[str] = set()
    logical_identifiers: set[str] = set()
    member_identities: set[str] = set()
    for order, member in enumerate(members):
        if not isinstance(member, Mapping) or member.get("member_order") != order:
            raise _fail("MEMBER_IDENTITY_SUBSTITUTION")
        material = {key: value for key, value in member.items() if key != "member_identity"}
        if _identity(_EXTERNAL_INPUT_MEMBER_DOMAIN, material) != member.get("member_identity"):
            raise _fail("MEMBER_IDENTITY_SUBSTITUTION")
        if (
            member["member_path"] in member_paths
            or member["logical_identifier"] in logical_identifiers
            or member["member_identity"] in member_identities
        ):
            raise _fail("DUPLICATE_MEMBER_AUTHORITY")
        member_paths.add(member["member_path"])
        logical_identifiers.add(member["logical_identifier"])
        member_identities.add(member["member_identity"])
        reconstructed_members.append(dict(member))
    manifest_material = {
        "external_input_identifier": declaration.get("external_input_identifier"),
        "input_version": declaration.get("input_version"),
        "manifest_revision": declaration.get("manifest_revision"),
        "members": reconstructed_members,
    }
    manifest_identity = _identity(_EXTERNAL_INPUT_MANIFEST_DOMAIN, manifest_material)
    if manifest_identity != declaration.get("manifest_identity"):
        raise _fail("MANIFEST_IDENTITY_SUBSTITUTION")
    declaration_material = {
        key: value for key, value in declaration.items()
        if key != "external_input_identity"
    }
    external_identity = _identity(_EXTERNAL_INPUT_DECLARATION_DOMAIN, declaration_material)
    if external_identity != declaration.get("external_input_identity"):
        raise _fail("EXTERNAL_INPUT_IDENTITY_SUBSTITUTION")
    snapshot_material = {
        key: value for key, value in snapshot.items()
        if key != "input_snapshot_identity"
    }
    snapshot_identity = _identity(_INPUT_SNAPSHOT_DOMAIN, snapshot_material)
    if snapshot_identity != snapshot.get("input_snapshot_identity"):
        raise _fail("SNAPSHOT_IDENTITY_SUBSTITUTION")
    expected_snapshot_members = [
        {"byte_count": item["byte_count"],
         "logical_member_identifier": item["logical_identifier"],
         "member_order": item["member_order"], "sha256": item["sha256"]}
        for item in reconstructed_members
    ]
    if snapshot.get("members") != expected_snapshot_members:
        raise _fail("SNAPSHOT_MEMBER_SUBSTITUTION")

    def component_identity(material: Mapping[str, Any]) -> str:
        fields = {key: material.get(key) for key in (
            "git_object_identity", "identifier", "path", "revision", "sha256",
            "worker_kind",
        )}
        result = _identity(_COMPONENT_BINDING_DOMAIN, fields)
        if result != material.get("component_identity"):
            raise _fail("COMPONENT_IDENTITY_SUBSTITUTION")
        return result

    decoder_component_material = {
        "git_object_identity": decoder.get("implementation_git_blob_identity"),
        "identifier": decoder.get("decoder_identifier"),
        "path": decoder.get("implementation_path"),
        "revision": decoder.get("decoder_revision"),
        "sha256": decoder.get("implementation_sha256"),
        "worker_kind": "INPUT_PROJECTOR",
    }
    decoder_component = _identity(_COMPONENT_BINDING_DOMAIN, decoder_component_material)
    if decoder_component != decoder.get("decoder_component_identity"):
        raise _fail("COMPONENT_IDENTITY_SUBSTITUTION")
    parser_identity = component_identity(parser_component)
    projector_identity = component_identity(projector_component)
    configuration_material = {
        "configuration_byte_count": decoder.get("configuration_byte_count"),
        "configuration_git_blob_identity": decoder.get("configuration_git_blob_identity"),
        "configuration_path": decoder.get("configuration_path"),
        "configuration_sha256": decoder.get("configuration_sha256"),
    }
    configuration_identity = _identity(_DECODER_CONFIGURATION_DOMAIN, configuration_material)
    if configuration_identity != decoder.get("configuration_identity"):
        raise _fail("CONFIGURATION_IDENTITY_SUBSTITUTION")
    raw_schema_identity = _identity(_RAW_SCHEMA_CONTRACT_DOMAIN, raw_schema)
    if raw_schema_identity != declaration.get("schema_identity"):
        raise _fail("RAW_SCHEMA_IDENTITY_SUBSTITUTION")
    projection_schema_identity = _identity(
        _PROJECTION_SCHEMA_CONTRACT_DOMAIN, projection_schema
    )
    return SourceProcessingAuthority(
        external_input_identifier=str(declaration["external_input_identifier"]),
        external_input_identity=external_identity,
        ordered_collection_manifest_identity=manifest_identity,
        immutable_input_snapshot_identity=snapshot_identity,
        decoder_component_identity=decoder_component,
        decoder_configuration_identity=configuration_identity,
        parser_component_identity=parser_identity,
        projector_component_identity=projector_identity,
        raw_schema_identity=raw_schema_identity,
        projection_schema_identity=projection_schema_identity,
    )


@dataclass(frozen=True, slots=True)
class SourceProcessingResult:
    records: tuple[Mapping[str, Any], ...]
    projection_bytes: bytes
    projection_sha256: str
    projection_identity: str
    dataset_content_identity: str
    logical_projection_content_identity: str
    projection_record_identities: tuple[str, ...]
    selected_observations: Mapping[int, SourceDecisionObservation]
    selected_parsed_observation_identities: Mapping[int, str]
    observation_members: Mapping[int, SourceMember]


@dataclass(frozen=True, slots=True)
class StreamingSourceProcessingResult:
    private_projection_path: Path
    byte_count: int
    record_count: int
    projection_sha256: str
    projection_identity: str
    dataset_content_identity: str
    logical_projection_content_identity: str
    projection_record_identities: tuple[str, ...]
    lifecycle_record_sha256s: tuple[str, ...]


class _PrivateProjectionSink:
    __slots__ = ("byte_count", "digest", "path", "record_count", "_descriptor", "_trusted")

    def __init__(self, path: Path) -> None:
        self.path = path
        self._descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        self.byte_count = 0
        self.record_count = 0
        self.digest = hashlib.sha256()
        self._trusted = False

    def append(self, framed_record: bytes, *, maximum_bytes: int) -> None:
        proposed = self.byte_count + len(framed_record)
        if proposed > maximum_bytes:
            raise _fail("RESOURCE_PROJECTION_BYTES_EXCEEDED")
        view = memoryview(framed_record)
        while view:
            written = os.write(self._descriptor, view)
            if written <= 0:
                raise _fail("PROJECTION_WRITE_FAILED")
            view = view[written:]
        self.digest.update(framed_record)
        self.byte_count = proposed
        self.record_count += 1

    def finish(self) -> None:
        os.fsync(self._descriptor)
        os.close(self._descriptor)
        self._descriptor = -1
        self._trusted = True

    def abort(self) -> None:
        if self._descriptor >= 0:
            os.close(self._descriptor)
            self._descriptor = -1
        if not self._trusted:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def __del__(self) -> None:
        self.abort()


@dataclass(frozen=True, slots=True)
class SourceProcessingLimits:
    maximum_members: int
    maximum_aggregate_bytes: int
    maximum_member_bytes: int
    maximum_records: int
    maximum_projection_bytes: int

    @classmethod
    def from_configuration(
        cls, configuration: Mapping[str, Any]
    ) -> SourceProcessingLimits:
        return cls(
            *(
                _integer(field, configuration.get(field), 1)
                for field in cls.__dataclass_fields__
            )
        )


def _require_tracked_record(
    parser: _SelectiveParser, paths: frozenset[str]
) -> dict[str, Any]:
        parsed = parser.parse()
        if paths is _LIFECYCLE_PATHS:
            required = {
                "lifecycle_schema_version", "round_id", "start_slot", "end_slot",
                "first_observed_at_utc", "last_observed_at_utc",
                "first_observed_rpc_slot", "last_observed_rpc_slot",
                "observation_count", "collector_session_ids",
                "source_schema_versions", "source_files", "observation_references",
                "finalized_outcome", "finalized_outcome_source", "quality",
            }
            if not required.issubset(parser.seen_paths):
                raise _fail("MALFORMED_LIFECYCLE_AUTHORITY")
        elif paths is _OBSERVATION_PATHS:
            # These tracked-model locations must exist, but their values stay
            # opaque because they are outside the frozen semantic whitelist.
            required = {
                "observed_at_utc", "rpc_slot", "board", "board.round_id",
                "board.start_slot", "board.end_slot", "board.production_cost_ema",
                "treasury", "treasury.motherlode", "round", "round.round_id",
                "round.deployed_lamports", "round.mass", "round.miner_counts",
                "round.slot_hash_hex", "round.expires_at", "round.motherlode",
                "round.rewards", "round.total_vaulted", "round.total_winnings",
                "round.total_miners", "round.top_miner",
            }
            if not required.issubset(parser.seen_paths):
                raise _fail("MALFORMED_OBSERVATION")
            for field in ("round.mass", "round.rewards"):
                shape = parser.opaque_shapes.get(field)
                if (
                    not isinstance(shape, tuple)
                    or len(shape) != 3
                    or shape[0] != "array"
                    or shape[1] != 25
                    or any(
                        not isinstance(item, tuple)
                        or len(item) != 2
                        or item[1] is not True
                        for item in shape[2]
                    )
                ):
                    raise _fail("MALFORMED_TRACKED_OBSERVATION_FIELD")
            for field in ("round.slot_hash_hex", "round.top_miner"):
                shape = parser.opaque_shapes.get(field)
                if not isinstance(shape, tuple) or not shape or shape[0] != "string":
                    raise _fail("MALFORMED_TRACKED_OBSERVATION_FIELD")
            expires_shape = parser.opaque_shapes.get("round.expires_at")
            if (
                not isinstance(expires_shape, tuple)
                or len(expires_shape) != 2
                or expires_shape[1] is not True
            ):
                raise _fail("MALFORMED_TRACKED_OBSERVATION_FIELD")
            if "round.entropy" in parser.seen_paths:
                entropy_shape = parser.opaque_shapes.get("round.entropy")
                if entropy_shape != ("null",) and (
                    not isinstance(entropy_shape, tuple)
                    or len(entropy_shape) != 2
                    or entropy_shape[1] is not True
                ):
                    raise _fail("MALFORMED_TRACKED_OBSERVATION_FIELD")
        return parsed


def _records(
    member: SourceMember | SnapshotSourceMember, paths: frozenset[str]
) -> Sequence[tuple[bytes, dict[str, Any]]]:
    if isinstance(member, SnapshotSourceMember):
        return _IndexedRecords(member, paths)
    result = []
    for line in member.persisted_bytes.splitlines(keepends=True):
        if line == b"\n" or not line.endswith(b"\n"):
            raise _fail("INVALID_JSONL_FRAMING")
        parser = _SelectiveParser(line[:-1], paths)
        result.append((line, _require_tracked_record(parser, paths)))
    return result


def _reference_material(member: SourceMember, line_number: int, raw_line: bytes, raw: Mapping[str, Any]) -> dict[str, Any]:
    version = raw.get("schema_version", 1)
    if isinstance(version, bool) or version not in {1, 2}:
        raise _fail("UNSUPPORTED_OBSERVATION_SCHEMA")
    session = raw.get("collector_session_id") if version == 2 else None
    if session is not None and (not isinstance(session, str) or not session or session.strip() != session or unicodedata.normalize("NFC", session) != session):
        raise _fail("INVALID_COLLECTOR_SESSION")
    observed, _ = _timestamp(raw.get("observed_at_utc"))
    rpc = _integer("rpc_slot", raw.get("rpc_slot"))
    material = {
        "logical_member_identifier": member.logical_identifier,
        "source_file": member.member_path,
        "source_line_number": line_number,
        "source_member_identity": member.member_identity,
        "source_member_byte_count": member.expected_byte_count,
        "source_member_sha256": member.expected_sha256,
        "persisted_record_byte_count": len(raw_line),
        "persisted_record_byte_sha256": _sha(raw_line),
        "observed_at_utc": observed,
        "rpc_slot": rpc,
        "source_schema_version": version,
        "observation_classification": "normal",
        "collector_session_available": session is not None,
        "collector_session_id": session or "",
    }
    material["canonical_parsed_observation_identity"] = _identity(
        "orev3:rq003-experiment-005:referenced-observation:v1", {**material, "scientific": raw}
    )
    return material


def _snapshot(round_id: int, index: int, raw: Mapping[str, Any]) -> SourceDecisionSnapshot:
    board, round_state, treasury = raw.get("board"), raw.get("round"), raw.get("treasury")
    if not all(isinstance(value, Mapping) for value in (board, round_state, treasury)):
        raise _fail("MALFORMED_OBSERVATION")
    if board.get("round_id") != round_id or round_state.get("round_id") != round_id:
        raise _fail("ROUND_ID_MISMATCH")
    deployed = tuple(_integer("deployed_lamports", value) for value in round_state.get("deployed_lamports", ()))
    miners = tuple(_integer("miner_counts", value) for value in round_state.get("miner_counts", ()))
    if len(deployed) != 25 or len(miners) != 25:
        raise _fail("CANDIDATE_CARDINALITY_MISMATCH")
    total_miners = _integer("total_miners", round_state.get("total_miners"))
    if total_miners != sum(miners): raise _fail("TOTAL_MINERS_MISMATCH")
    return SourceDecisionSnapshot(
        structural_round_key=round_id, observation_index=index,
        deployed_lamports=deployed, miner_counts=miners, total_miners=total_miners,
        active_round_motherlode=_integer("active_round_motherlode", round_state.get("motherlode")),
        pre_finalization_total_vaulted=_integer("total_vaulted", round_state.get("total_vaulted")),
        pre_finalization_total_winnings=_integer("total_winnings", round_state.get("total_winnings")),
        production_cost_ema=_integer("production_cost_ema", board.get("production_cost_ema")),
        treasury_motherlode=_integer("treasury_motherlode", treasury.get("motherlode")),
        decision_point_configuration_identity=EXPERIMENT5_DECISION_SELECTION_IDENTITY,
    )


def _validate_normal_observation(
    *, round_id: int, start_slot: int, lifecycle_end_slot: int | None,
    raw: Mapping[str, Any], rpc_slot: int,
) -> None:
    board, round_state, treasury = raw.get("board"), raw.get("round"), raw.get("treasury")
    if not all(isinstance(value, Mapping) for value in (board, round_state, treasury)):
        raise _fail("MALFORMED_OBSERVATION")
    if board.get("round_id") != round_id or round_state.get("round_id") != round_id:
        raise _fail("ROUND_ID_MISMATCH")
    if board.get("start_slot") != start_slot:
        raise _fail("START_SLOT_MISMATCH")
    observation_end = _integer("observation_end_slot", board.get("end_slot"))
    if lifecycle_end_slot is not None and observation_end not in {
        lifecycle_end_slot, (1 << 64) - 1,
    }:
        raise _fail("OBSERVATION_END_SLOT_MISMATCH")
    deployed = tuple(
        _integer("deployed_lamports", value)
        for value in round_state.get("deployed_lamports", ())
    )
    miners = tuple(
        _integer("miner_counts", value)
        for value in round_state.get("miner_counts", ())
    )
    if len(deployed) != 25 or len(miners) != 25:
        raise _fail("CANDIDATE_CARDINALITY_MISMATCH")
    total_miners = _integer("total_miners", round_state.get("total_miners"))
    if total_miners != sum(miners):
        raise _fail("TOTAL_MINERS_MISMATCH")
    for name, value in (
        ("active_round_motherlode", round_state.get("motherlode")),
        ("total_vaulted", round_state.get("total_vaulted")),
        ("total_winnings", round_state.get("total_winnings")),
        ("treasury_motherlode", treasury.get("motherlode")),
    ):
        _integer(name, value)
    production_cost = board.get("production_cost_ema")
    if production_cost is not None:
        _integer("production_cost_ema", production_cost)
    if rpc_slot < start_slot or (
        lifecycle_end_slot is not None and rpc_slot > lifecycle_end_slot
    ):
        raise _fail("ROUND_SLOT_CONTRADICTION")


def _lifecycle_core(
    *, lifecycle_source_file: str, lifecycle_source_line_number: int,
    round_id: int, start_slot: int, end_slot: int | None,
    first_observed_at_utc: str, last_observed_at_utc: str,
    first_observed_rpc_slot: int, last_observed_rpc_slot: int,
    lifecycle_status: str, initialization_state_observed: bool,
    rpc_slot_regression_count: int, largest_rpc_slot_regression: int,
    duplicate_rpc_slot_count: int, significant_gap_count: int,
    max_observation_gap_microseconds: int,
    significant_gap_threshold_microseconds: int,
    collector_session_ids: Sequence[str], source_schema_versions: Sequence[int],
    source_files: Sequence[str], observation_references: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    references = [
        {key: value for key, value in reference.items() if key != "observation_index"}
        for reference in observation_references
    ]
    return {
        "collector_regime_metadata_unavailable": len(collector_session_ids) == 0,
        "collector_session_count": len(collector_session_ids),
        "collector_session_ids": list(collector_session_ids),
        "duplicate_rpc_slot_count": duplicate_rpc_slot_count,
        "end_slot": end_slot if end_slot is not None else 0,
        "end_slot_available": end_slot is not None,
        "first_observed_at_utc": first_observed_at_utc,
        "first_observed_rpc_slot": first_observed_rpc_slot,
        "initialization_state_observed": initialization_state_observed,
        "largest_rpc_slot_regression": largest_rpc_slot_regression,
        "last_observed_at_utc": last_observed_at_utc,
        "last_observed_rpc_slot": last_observed_rpc_slot,
        "lifecycle_source_file": lifecycle_source_file,
        "lifecycle_source_line_number": lifecycle_source_line_number,
        "lifecycle_status": lifecycle_status,
        "max_observation_gap_microseconds": max_observation_gap_microseconds,
        "normal_observation_count": len(references),
        "observation_count": len(references),
        "observation_references": references,
        "raw_lifecycle_schema_version": 1,
        "round_id": round_id,
        "rpc_slot_regression_count": rpc_slot_regression_count,
        "significant_gap_count": significant_gap_count,
        "significant_gap_threshold_microseconds": significant_gap_threshold_microseconds,
        "source_convention_revision": SOURCE_CONVENTION_REVISION,
        "source_files": list(source_files),
        "source_schema_versions": list(source_schema_versions),
        "start_slot": start_slot,
    }


def _lifecycle_core_from_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    references = record.get("observation_references")
    if not isinstance(references, list) or not references:
        raise _fail("LIFECYCLE_CORE_SUBSTITUTION")
    return _lifecycle_core(
        lifecycle_source_file=record["lifecycle_source_file"],
        lifecycle_source_line_number=record["lifecycle_source_line_number"],
        round_id=record["round_id"], start_slot=record["start_slot"],
        end_slot=record["end_slot"] if record["end_slot_available"] else None,
        first_observed_at_utc=record["first_observed_at_utc"],
        last_observed_at_utc=record["last_observed_at_utc"],
        first_observed_rpc_slot=references[0]["rpc_slot"],
        last_observed_rpc_slot=references[-1]["rpc_slot"],
        lifecycle_status=record["lifecycle_status"],
        initialization_state_observed=record["initialization_state_observed"],
        rpc_slot_regression_count=record["rpc_slot_regression_count"],
        largest_rpc_slot_regression=record["largest_rpc_slot_regression"],
        duplicate_rpc_slot_count=record["duplicate_rpc_slot_count"],
        significant_gap_count=record["significant_gap_count"],
        max_observation_gap_microseconds=record["max_observation_gap_microseconds"],
        significant_gap_threshold_microseconds=record[
            "significant_gap_threshold_microseconds"
        ],
        collector_session_ids=record["collector_session_ids"],
        source_schema_versions=record["source_schema_versions"],
        source_files=record["source_files"], observation_references=references,
    )


def _process_source_collection(
    members: Sequence[SourceMember | SnapshotSourceMember], *, authority: SourceProcessingAuthority,
    projection_schema: Mapping[str, Any], expected_lifecycle_sha256: str,
    limits: SourceProcessingLimits, private_projection_path: Path | None = None,
) -> SourceProcessingResult | StreamingSourceProcessingResult:
    """Authenticate, normalize, select, and project one ordered collection."""
    if len(members) > limits.maximum_members:
        raise _fail("RESOURCE_MEMBER_COUNT_EXCEEDED")
    if any(member.expected_byte_count > limits.maximum_member_bytes for member in members):
        raise _fail("RESOURCE_MEMBER_BYTES_EXCEEDED")
    if sum(member.expected_byte_count for member in members) > limits.maximum_aggregate_bytes:
        raise _fail("RESOURCE_AGGREGATE_BYTES_EXCEEDED")
    if not members or members[0].logical_identifier != "lifecycle" or members[0].member_order != 0:
        raise _fail("INVALID_MEMBER_ORDER")
    expected = [members[0], *sorted(members[1:], key=lambda item: (item.logical_identifier, item.member_path))]
    if list(members) != expected or [item.member_order for item in members] != list(range(len(members))):
        raise _fail("INVALID_MEMBER_ORDER")
    if (
        len({m.logical_identifier for m in members}) != len(members)
        or len({m.member_path for m in members}) != len(members)
        or len({m.member_identity for m in members}) != len(members)
    ):
        raise _fail("DUPLICATE_MEMBER")
    if members[0].expected_sha256 != expected_lifecycle_sha256:
        raise _fail("FIXED_DATASET_MISMATCH")
    by_path = {item.member_path: item for item in members[1:]}
    observation_lines = {item.member_path: _records(item, _OBSERVATION_PATHS) for item in members[1:]}
    lifecycle_lines = _records(members[0], _LIFECYCLE_PATHS)
    total_record_count = len(lifecycle_lines) + sum(
        len(records) for records in observation_lines.values()
    )
    if total_record_count > limits.maximum_records:
        raise _fail("RESOURCE_RECORD_COUNT_EXCEEDED")
    projected: list[dict[str, Any]] = []
    sink = (
        _PrivateProjectionSink(private_projection_path)
        if private_projection_path is not None
        else None
    )
    projection_record_identities: list[str] = []
    lifecycle_record_sha256s: list[str] = []
    selected_map: dict[int, SourceDecisionObservation] = {}
    selected_parsed_identities: dict[int, str] = {}
    selected_members: dict[int, SourceMember] = {}
    seen_rounds: set[int] = set(); seen_coordinates: set[tuple[str, str, int]] = set()
    previous_chronology: tuple[int, int] | None = None
    logical_ids = {member.member_path: member.logical_identifier for member in members[1:]}
    for lifecycle_line_number, (lifecycle_bytes, lifecycle) in enumerate(lifecycle_lines, 1):
        if lifecycle.get("lifecycle_schema_version") != 1: raise _fail("UNSUPPORTED_LIFECYCLE_SCHEMA")
        round_id = _integer("round_id", lifecycle.get("round_id")); start_slot = _integer("start_slot", lifecycle.get("start_slot"))
        if round_id in seen_rounds: raise _fail("DUPLICATE_ROUND")
        seen_rounds.add(round_id)
        chronology = (start_slot, round_id)
        if previous_chronology is not None and chronology <= previous_chronology: raise _fail("LIFECYCLE_CHRONOLOGY_MISMATCH")
        previous_chronology = chronology
        end_raw = lifecycle.get("end_slot")
        if end_raw is not None: end_raw = _integer("end_slot", end_raw)
        refs = lifecycle.get("observation_references")
        if not isinstance(refs, list) or not refs: raise _fail("MISSING_OBSERVATION_REFERENCE")
        normalized_refs: list[dict[str, Any]] = []; normalized_obs: list[tuple[dict[str, Any], Mapping[str, Any], SourceMember]] = []
        for ref in refs:
            if not isinstance(ref, Mapping): raise _fail("MALFORMED_REFERENCE")
            path = ref.get("source_file"); line_no = _integer("source_line_number", ref.get("source_line_number"), 1)
            if path not in by_path or line_no > len(observation_lines[path]): raise _fail("MISSING_REFERENCED_RECORD")
            coordinate = (logical_ids[path], path, line_no)
            if coordinate in seen_coordinates: raise _fail("DUPLICATE_SOURCE_COORDINATE")
            seen_coordinates.add(coordinate)
            raw_line, raw = observation_lines[path][line_no - 1]; member = by_path[path]
            normalized = _reference_material(member, line_no, raw_line, raw)
            if ref.get("observed_at_utc") != normalized["observed_at_utc"] or ref.get("rpc_slot") != normalized["rpc_slot"]:
                raise _fail("REFERENCE_MISMATCH")
            _validate_normal_observation(
                round_id=round_id, start_slot=start_slot,
                lifecycle_end_slot=end_raw, raw=raw,
                rpc_slot=normalized["rpc_slot"],
            )
            normalized_refs.append(normalized); normalized_obs.append((normalized, raw, member))
        order = sorted(range(len(normalized_refs)), key=lambda index: (normalized_refs[index]["observed_at_utc"], normalized_refs[index]["source_file"], normalized_refs[index]["source_line_number"]))
        normalized_refs = [normalized_refs[index] for index in order]; normalized_obs = [normalized_obs[index] for index in order]
        if lifecycle.get("observation_count") != len(normalized_refs): raise _fail("OBSERVATION_COUNT_MISMATCH")
        first, last = normalized_refs[0], normalized_refs[-1]
        for field, expected_value in (("first_observed_at_utc", first["observed_at_utc"]), ("last_observed_at_utc", last["observed_at_utc"]), ("first_observed_rpc_slot", first["rpc_slot"]), ("last_observed_rpc_slot", last["rpc_slot"])):
            if lifecycle.get(field) != expected_value: raise _fail("REFERENCE_BOUNDARY_MISMATCH")
        versions = sorted({item["source_schema_version"] for item in normalized_refs}); files = sorted({item["source_file"] for item in normalized_refs}); sessions = sorted({item["collector_session_id"] for item in normalized_refs if item["collector_session_available"]})
        if lifecycle.get("source_schema_versions") != versions or lifecycle.get("source_files") != files or lifecycle.get("collector_session_ids") != sessions:
            raise _fail("LIFECYCLE_SET_MISMATCH")
        quality = lifecycle.get("quality")
        if not isinstance(quality, Mapping): raise _fail("MALFORMED_QUALITY")
        coverage = quality.get("coverage_status")
        if coverage == "unknown": raise _fail("LIFECYCLE_AUTHORITY_UNAVAILABLE")
        if coverage not in {"complete", "partial_start", "partial_end", "partial_both"}: raise _fail("INVALID_COVERAGE_STATUS")
        if quality.get("collector_session_count") != len(sessions): raise _fail("COLLECTOR_SESSION_COUNT_MISMATCH")
        rpc_regressions = _integer("rpc_slot_regression_count", quality.get("rpc_slot_regression_count"))
        largest_rpc_regression = _integer("largest_rpc_slot_regression", quality.get("largest_rpc_slot_regression"))
        duplicate_rpc_slots = _integer("duplicate_rpc_slot_count", quality.get("duplicate_rpc_slot_count"))
        significant_gaps = _integer("significant_gap_count", quality.get("significant_gap_count"))
        initialization_observed = quality.get("initialization_state_observed")
        if not isinstance(initialization_observed, bool): raise _fail("INVALID_INITIALIZATION_STATE")
        max_gap_us = _decimal_microseconds("max_observation_gap_seconds", quality.get("max_observation_gap_seconds"))
        threshold_us = _decimal_microseconds("significant_gap_threshold_seconds", quality.get("significant_gap_threshold_seconds"))
        datetimes = [_timestamp(item["observed_at_utc"])[1] for item in normalized_refs]
        gaps = [
            (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
            for delta in (right - left for left, right in zip(datetimes, datetimes[1:]))
        ]
        if max_gap_us != max(gaps, default=0) or significant_gaps != sum(gap > threshold_us for gap in gaps): raise _fail("GAP_METADATA_MISMATCH")
        selected_index: int | None = None
        if end_raw is not None:
            candidates = [i for i, (ref, _, _) in enumerate(normalized_obs) if ref["rpc_slot"] <= end_raw - 5]
            if candidates:
                max_rpc = max(normalized_refs[i]["rpc_slot"] for i in candidates)
                selected_index = max(i for i in candidates if normalized_refs[i]["rpc_slot"] == max_rpc)
        selected: SourceDecisionObservation | None = None
        if selected_index is not None:
            ref, raw, member = normalized_obs[selected_index]
            selected_board_end = raw.get("board", {}).get("end_slot")
            if end_raw is None or selected_board_end != end_raw:
                raise _fail("SELECTED_END_SLOT_MISMATCH")
            snapshot = _snapshot(round_id, selected_index, raw)
            selected = SourceDecisionObservation(
                reference=SourceObservationReference(_timestamp(ref["observed_at_utc"])[1], ref["rpc_slot"], ref["source_file"], ref["source_line_number"]),
                snapshot=snapshot,
                measurement_vector_bytes=tuple(PIPELINE.compute(snapshot.execution_context(square)).canonical_bytes() for square in EXPERIMENT5_CANDIDATES),
            )
            if sink is None:
                selected_map[round_id] = selected; selected_members[round_id] = member
                selected_parsed_identities[round_id] = ref[
                    "canonical_parsed_observation_identity"
                ]
        lifecycle_core = _lifecycle_core(
            lifecycle_source_file=members[0].member_path,
            lifecycle_source_line_number=lifecycle_line_number,
            round_id=round_id, start_slot=start_slot, end_slot=end_raw,
            first_observed_at_utc=first["observed_at_utc"],
            last_observed_at_utc=last["observed_at_utc"],
            first_observed_rpc_slot=first["rpc_slot"],
            last_observed_rpc_slot=last["rpc_slot"], lifecycle_status=coverage,
            initialization_state_observed=initialization_observed,
            rpc_slot_regression_count=rpc_regressions,
            largest_rpc_slot_regression=largest_rpc_regression,
            duplicate_rpc_slot_count=duplicate_rpc_slots,
            significant_gap_count=significant_gaps,
            max_observation_gap_microseconds=max_gap_us,
            significant_gap_threshold_microseconds=threshold_us,
            collector_session_ids=sessions, source_schema_versions=versions,
            source_files=files, observation_references=normalized_refs,
        )
        lifecycle_identity = _identity(
            "orev3:rq003-experiment-005:lifecycle-record:v1", lifecycle_core
        )
        selected_observation_identity = (
            _identity("orev3:rq003-experiment-005:selected-observation:v1", {
                "canonical_parsed_observation_identity": normalized_refs[selected_index]["canonical_parsed_observation_identity"],
                "decision_selection_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
                "observation_index": selected_index,
                "reference": normalized_refs[selected_index],
            }) if selected_index is not None else ""
        )
        selected_scientific_state_identity = (
            _identity("orev3:rq003-experiment-005:selected-scientific-state:v1", {
                "canonical_lifecycle_record_identity": lifecycle_identity,
                "decision_point_configuration_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
                "decoder_component_identity": authority.decoder_component_identity,
                "decoder_configuration_identity": authority.decoder_configuration_identity,
                "fundamental_measurement_vector_identities": list(selected.measurement_vector_identities),
                "immutable_input_snapshot_identity": authority.immutable_input_snapshot_identity,
                "ordered_collection_manifest_identity": authority.ordered_collection_manifest_identity,
                "selected_observation_identity": selected_observation_identity,
                "selected_snapshot_identity": selected.decision_snapshot_identity,
            }) if selected else ""
        )
        record: dict[str, Any] = {
            "projection_schema_version": 1, "source_unit_key": str(round_id),
            "lifecycle_source_file": members[0].member_path, "lifecycle_source_line_number": lifecycle_line_number,
            "lifecycle_member_identity": members[0].member_identity, "lifecycle_record_byte_count": len(lifecycle_bytes), "lifecycle_record_byte_sha256": _sha(lifecycle_bytes), "canonical_lifecycle_record_identity": lifecycle_identity,
            "external_input_identifier": authority.external_input_identifier, "external_input_identity": authority.external_input_identity, "ordered_collection_manifest_identity": authority.ordered_collection_manifest_identity, "immutable_input_snapshot_identity": authority.immutable_input_snapshot_identity,
            "decoder_component_identity": authority.decoder_component_identity, "decoder_configuration_identity": authority.decoder_configuration_identity, "parser_component_identity": authority.parser_component_identity, "projector_component_identity": authority.projector_component_identity, "projection_schema_identity": authority.projection_schema_identity,
            "decision_selection_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY, "dataset_version": DATASET_VERSION, "protocol_revision": EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION, "research_execution_specification_revision": EXECUTION_SPECIFICATION_REVISION,
            "round_id": round_id, "start_slot": start_slot, "end_slot_available": end_raw is not None, "end_slot": end_raw or 0,
            "first_observed_at_utc": first["observed_at_utc"], "last_observed_at_utc": last["observed_at_utc"], "lifecycle_status": coverage,
            "observation_count": len(normalized_refs), "normal_observation_count": len(normalized_refs),
            "initialization_state_observed": initialization_observed, "rpc_slot_regression_count": rpc_regressions, "largest_rpc_slot_regression": largest_rpc_regression, "duplicate_rpc_slot_count": duplicate_rpc_slots, "significant_gap_count": significant_gaps, "max_observation_gap_microseconds": max_gap_us, "significant_gap_threshold_microseconds": threshold_us,
            "collector_session_count": len(sessions), "collector_session_ids": sessions, "source_schema_versions": versions, "source_files": files, "observation_references": [{**item, "observation_index": index} for index, item in enumerate(normalized_refs)],
            "candidates": list(EXPERIMENT5_CANDIDATES), "selected": selected is not None, "eligible": selected is not None, "exclusion_reason": "not_applicable" if selected else "no_predeclared_decision_observation", "observation_index": selected_index or 0,
            "selected_references": ([{**normalized_refs[selected_index], "observation_index": selected_index}] if selected_index is not None else []),
            "selected_observation_identities": ([selected_observation_identity] if selected_index is not None else []),
            "selected_scientific_state_identities": ([selected_scientific_state_identity] if selected else []),
            "selected_snapshot_identities": ([selected.decision_snapshot_identity] if selected else []), "fundamental_measurement_vector_identities": (list(selected.measurement_vector_identities) if selected else []),
            "deployed_lamports": (list(selected.snapshot.deployed_lamports) if selected else []), "miner_counts": (list(selected.snapshot.miner_counts) if selected else []),
            "total_miners_values": ([selected.snapshot.total_miners] if selected else []), "active_round_motherlode_values": ([selected.snapshot.active_round_motherlode] if selected else []), "pre_finalization_total_vaulted_values": ([selected.snapshot.pre_finalization_total_vaulted] if selected else []), "pre_finalization_total_winnings_values": ([selected.snapshot.pre_finalization_total_winnings] if selected else []), "production_cost_ema_values": ([selected.snapshot.production_cost_ema] if selected else []), "treasury_motherlode_values": ([selected.snapshot.treasury_motherlode] if selected else []),
        }
        if set(record) & _FORBIDDEN_PROJECTION_KEYS: raise _fail("OUTCOME_LEAKAGE")
        validate_json_schema_instance(record, projection_schema, schema_registry={})
        framed_record = canonical_bytes(record)
        projection_record_identities.append(
            _identity("orev3:rq003-experiment-005:projection-record:v1", record)
        )
        lifecycle_record_sha256s.append(_sha(lifecycle_bytes))
        if sink is None:
            projected.append(record)
        else:
            sink.append(framed_record, maximum_bytes=limits.maximum_projection_bytes)
            del framed_record, record, normalized_obs, normalized_refs, selected
    if sink is not None:
        sink.finish()
        projection_sha = sink.digest.hexdigest()
        projection_identity = _identity(_PROJECTION_EVIDENCE_DOMAIN, {
            "byte_count": sink.byte_count,
            "ordered_record_count": sink.record_count,
            "parser_component_identity": authority.parser_component_identity,
            "projection_schema_identity": authority.projection_schema_identity,
            "projector_component_identity": authority.projector_component_identity,
            "sha256": projection_sha,
        })
        dataset_content = _identity(_DATASET_CONTENT_DOMAIN, {
            "ordered_record_sha256s": lifecycle_record_sha256s,
            "record_count": sink.record_count,
        })
        projection_content = _identity(
            "orev3:rq003-experiment-005:projection-content:v1",
            {
                "ordered_projection_record_identities": projection_record_identities,
                "record_count": sink.record_count,
            },
        )
        result = StreamingSourceProcessingResult(
            private_projection_path,
            sink.byte_count,
            sink.record_count,
            projection_sha,
            projection_identity,
            dataset_content,
            projection_content,
            tuple(projection_record_identities),
            tuple(lifecycle_record_sha256s),
        )
        try:
            validate_streaming_projection(
                result, authority=authority, projection_schema=projection_schema
            )
        except BaseException:
            try:
                private_projection_path.unlink()
            except FileNotFoundError:
                pass
            raise
        return result
    projection = b"".join(canonical_bytes(record) for record in projected)
    if len(projection) > limits.maximum_projection_bytes:
        raise _fail("RESOURCE_PROJECTION_BYTES_EXCEEDED")
    projection_sha = _sha(projection)
    projection_identity = _identity(_PROJECTION_EVIDENCE_DOMAIN, {
        "byte_count": len(projection),
        "ordered_record_count": len(projected),
        "parser_component_identity": authority.parser_component_identity,
        "projection_schema_identity": authority.projection_schema_identity,
        "projector_component_identity": authority.projector_component_identity,
        "sha256": projection_sha,
    })
    dataset_content = _identity(_DATASET_CONTENT_DOMAIN, {
        "ordered_record_sha256s": [_sha(line) for line, _ in lifecycle_lines],
        "record_count": len(lifecycle_lines),
    })
    legacy_record_identities = tuple(projection_record_identities)
    projection_content = _identity("orev3:rq003-experiment-005:projection-content:v1", {"ordered_projection_record_identities": list(legacy_record_identities), "record_count": len(projected)})
    result = SourceProcessingResult(tuple(projected), projection, projection_sha, projection_identity, dataset_content, projection_content, legacy_record_identities, selected_map, selected_parsed_identities, selected_members)
    validate_projection_population(result, authority=authority)
    return result


def validate_streaming_projection(
    result: StreamingSourceProcessingResult,
    *,
    authority: SourceProcessingAuthority,
    projection_schema: Mapping[str, Any],
) -> None:
    """Independently validate canonical projection bytes with bounded storage."""

    descriptor = os.open(
        result.private_projection_path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    digest = hashlib.sha256()
    byte_count = 0
    record_count = 0
    record_identities: list[str] = []
    lifecycle_hashes: list[str] = []
    pending = bytearray()
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise _fail("PROJECTION_SUBSTITUTION")
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            byte_count += len(chunk)
            if byte_count > result.byte_count:
                raise _fail("PROJECTION_SUBSTITUTION")
            pending.extend(chunk)
            while True:
                newline = pending.find(b"\n")
                if newline < 0:
                    if len(pending) >= MAX_PROJECTION_RECORD_BYTES:
                        raise _fail("RESOURCE_MEMORY_EXCEEDED")
                    break
                framed_size = newline + 1
                if framed_size > MAX_PROJECTION_RECORD_BYTES:
                    raise _fail("RESOURCE_MEMORY_EXCEEDED")
                framed = bytes(pending[:framed_size])
                del pending[:framed_size]
                record = parse_json(framed[:-1], max_bytes=MAX_PROJECTION_RECORD_BYTES)
                if not isinstance(record, Mapping) or canonical_bytes(record) != framed:
                    raise _fail("PROJECTION_SUBSTITUTION")
                validate_json_schema_instance(
                    record, projection_schema, schema_registry={}
                )
                record_identities.append(
                    _identity(
                        "orev3:rq003-experiment-005:projection-record:v1", record
                    )
                )
                lifecycle_hash = record.get("lifecycle_record_byte_sha256")
                if not isinstance(lifecycle_hash, str):
                    raise _fail("PROJECTION_SUBSTITUTION")
                lifecycle_hashes.append(lifecycle_hash)
                record_count += 1
        closed = os.fstat(descriptor)
        fingerprint = lambda value: (
            value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns,
        )
        if pending or fingerprint(opened) != fingerprint(closed):
            raise _fail("PROJECTION_SUBSTITUTION")
    finally:
        os.close(descriptor)
    if (
        byte_count != result.byte_count
        or record_count != result.record_count
        or digest.hexdigest() != result.projection_sha256
        or tuple(record_identities) != result.projection_record_identities
        or tuple(lifecycle_hashes) != result.lifecycle_record_sha256s
    ):
        raise _fail("PROJECTION_SUBSTITUTION")
    if result.dataset_content_identity != _identity(
        _DATASET_CONTENT_DOMAIN,
        {"ordered_record_sha256s": lifecycle_hashes, "record_count": record_count},
    ):
        raise _fail("DATASET_CONTENT_IDENTITY_SUBSTITUTION")
    if result.logical_projection_content_identity != _identity(
        "orev3:rq003-experiment-005:projection-content:v1",
        {
            "ordered_projection_record_identities": record_identities,
            "record_count": record_count,
        },
    ):
        raise _fail("PROJECTION_CONTENT_IDENTITY_SUBSTITUTION")
    expected_projection_identity = _identity(_PROJECTION_EVIDENCE_DOMAIN, {
        "byte_count": byte_count,
        "ordered_record_count": record_count,
        "parser_component_identity": authority.parser_component_identity,
        "projection_schema_identity": authority.projection_schema_identity,
        "projector_component_identity": authority.projector_component_identity,
        "sha256": result.projection_sha256,
    })
    if result.projection_identity != expected_projection_identity:
        raise _fail("PROJECTION_IDENTITY_SUBSTITUTION")


_SINGLE_SELECTED_CONTAINERS = (
    "selected_references", "selected_observation_identities",
    "selected_scientific_state_identities", "selected_snapshot_identities",
    "total_miners_values", "active_round_motherlode_values",
    "pre_finalization_total_vaulted_values",
    "pre_finalization_total_winnings_values", "production_cost_ema_values",
    "treasury_motherlode_values",
)
_VECTOR_SELECTED_CONTAINERS = (
    "fundamental_measurement_vector_identities", "deployed_lamports",
    "miner_counts",
)


def validate_projection_population(
    result: SourceProcessingResult, *, authority: SourceProcessingAuthority
) -> None:
    """Reconstruct every record and state before Replay or binding is trusted."""
    records = result.records
    if not records:
        raise _fail("PROJECTION_POPULATION_EMPTY")
    if result.projection_bytes != b"".join(canonical_bytes(record) for record in records):
        raise _fail("PROJECTION_SUBSTITUTION")
    if _sha(result.projection_bytes) != result.projection_sha256:
        raise _fail("PROJECTION_SUBSTITUTION")
    expected_record_identities = tuple(
        _identity("orev3:rq003-experiment-005:projection-record:v1", record)
        for record in records
    )
    if result.projection_record_identities != expected_record_identities:
        raise _fail("PROJECTION_RECORD_IDENTITY_SUBSTITUTION")
    expected_content_identity = _identity(
        "orev3:rq003-experiment-005:projection-content:v1",
        {
            "ordered_projection_record_identities": list(expected_record_identities),
            "record_count": len(records),
        },
    )
    if result.logical_projection_content_identity != expected_content_identity:
        raise _fail("PROJECTION_CONTENT_IDENTITY_SUBSTITUTION")
    expected_dataset_content = _identity(
        _DATASET_CONTENT_DOMAIN,
        {
            "ordered_record_sha256s": [
                record["lifecycle_record_byte_sha256"] for record in records
            ],
            "record_count": len(records),
        },
    )
    if result.dataset_content_identity != expected_dataset_content:
        raise _fail("DATASET_CONTENT_IDENTITY_SUBSTITUTION")
    expected_projection_identity = _identity(
        _PROJECTION_EVIDENCE_DOMAIN,
        {
            "byte_count": len(result.projection_bytes),
            "ordered_record_count": len(records),
            "parser_component_identity": authority.parser_component_identity,
            "projection_schema_identity": authority.projection_schema_identity,
            "projector_component_identity": authority.projector_component_identity,
            "sha256": result.projection_sha256,
        },
    )
    if result.projection_identity != expected_projection_identity:
        raise _fail("PROJECTION_IDENTITY_SUBSTITUTION")
    chronology = [(record["start_slot"], record["round_id"]) for record in records]
    if chronology != sorted(chronology) or len({item[1] for item in chronology}) != len(records):
        raise _fail("PROJECTION_RECORD_ORDER_SUBSTITUTION")

    for record in records:
        round_id = record.get("round_id")
        if (
            isinstance(round_id, bool)
            or not isinstance(round_id, int)
            or round_id < 0
            or record.get("source_unit_key") != str(round_id)
        ):
            raise _fail("SOURCE_UNIT_KEY_MISMATCH")
        references = record.get("observation_references")
        if not isinstance(references, list) or [
            reference.get("observation_index")
            for reference in references if isinstance(reference, Mapping)
        ] != list(range(len(references))):
            raise _fail("REFERENCE_ORDER_SUBSTITUTION")
        if record.get("observation_count") != len(references) or record.get(
            "normal_observation_count"
        ) != len(references):
            raise _fail("OBSERVATION_COUNT_MISMATCH")
        if (
            record.get("collector_session_count")
            != len(record.get("collector_session_ids", ()))
            or record.get("first_observed_at_utc") != references[0].get("observed_at_utc")
            or record.get("last_observed_at_utc") != references[-1].get("observed_at_utc")
            or record.get("source_files")
            != sorted({reference.get("source_file") for reference in references})
            or record.get("source_schema_versions")
            != sorted({reference.get("source_schema_version") for reference in references})
        ):
            raise _fail("LIFECYCLE_CORE_SUBSTITUTION")
        lifecycle_identity = _identity(
            "orev3:rq003-experiment-005:lifecycle-record:v1",
            _lifecycle_core_from_projection(record),
        )
        if record.get("canonical_lifecycle_record_identity") != lifecycle_identity:
            raise _fail("LIFECYCLE_CORE_SUBSTITUTION")

        selected = record.get("selected")
        eligible = record.get("eligible")
        observation = result.selected_observations.get(round_id)
        if selected is True:
            if eligible is not True or record.get("exclusion_reason") != "not_applicable":
                raise _fail("SELECTED_STATE_SHAPE_MISMATCH")
            if observation is None:
                raise _fail("SELECTED_STATE_AUTHORITY_MISSING")
            if any(len(record.get(field, ())) != 1 for field in _SINGLE_SELECTED_CONTAINERS):
                raise _fail("SELECTED_STATE_SHAPE_MISMATCH")
            if any(len(record.get(field, ())) != 25 for field in _VECTOR_SELECTED_CONTAINERS):
                raise _fail("SELECTED_STATE_SHAPE_MISMATCH")
            index = record.get("observation_index")
            if index != observation.observation_index or not isinstance(index, int):
                raise _fail("SELECTED_STATE_SHAPE_MISMATCH")
            if index >= len(references) or record["selected_references"] != [references[index]]:
                raise _fail("SELECTED_REFERENCE_SUBSTITUTION")
            selected_reference = references[index]
            if (
                selected_reference.get("canonical_parsed_observation_identity")
                != result.selected_parsed_observation_identities.get(round_id)
                or selected_reference.get("observed_at_utc")
                != observation.reference.to_material()["observed_at_utc"].replace(
                    "+00:00", "Z"
                )
                or selected_reference.get("rpc_slot") != observation.rpc_slot
                or selected_reference.get("source_file")
                != observation.reference.source_file
                or selected_reference.get("source_line_number")
                != observation.reference.source_line_number
            ):
                raise _fail("SELECTED_REFERENCE_SUBSTITUTION")
            reconstructed_vectors = tuple(
                PIPELINE.compute(
                    observation.snapshot.execution_context(square)
                ).canonical_bytes()
                for square in EXPERIMENT5_CANDIDATES
            )
            if reconstructed_vectors != observation.measurement_vector_bytes:
                raise _fail("MEASUREMENT_VECTOR_SUBSTITUTION")
            selected_observation_identity = _identity(
                "orev3:rq003-experiment-005:selected-observation:v1",
                {
                    "canonical_parsed_observation_identity": selected_reference[
                        "canonical_parsed_observation_identity"
                    ],
                    "decision_selection_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
                    "observation_index": index,
                    "reference": {
                        key: value for key, value in selected_reference.items()
                        if key != "observation_index"
                    },
                },
            )
            if record["selected_observation_identities"] != [selected_observation_identity]:
                raise _fail("SELECTED_OBSERVATION_SUBSTITUTION")
            expected_selected = {
                "selected_snapshot_identities": [observation.decision_snapshot_identity],
                "fundamental_measurement_vector_identities": list(observation.measurement_vector_identities),
                "deployed_lamports": list(observation.snapshot.deployed_lamports),
                "miner_counts": list(observation.snapshot.miner_counts),
                "total_miners_values": [observation.snapshot.total_miners],
                "active_round_motherlode_values": [observation.snapshot.active_round_motherlode],
                "pre_finalization_total_vaulted_values": [observation.snapshot.pre_finalization_total_vaulted],
                "pre_finalization_total_winnings_values": [observation.snapshot.pre_finalization_total_winnings],
                "production_cost_ema_values": [observation.snapshot.production_cost_ema],
                "treasury_motherlode_values": [observation.snapshot.treasury_motherlode],
            }
            if any(record.get(key) != value for key, value in expected_selected.items()):
                raise _fail("SELECTED_SCIENTIFIC_STATE_SUBSTITUTION")
            selected_scientific_identity = _identity(
                "orev3:rq003-experiment-005:selected-scientific-state:v1",
                {
                    "canonical_lifecycle_record_identity": lifecycle_identity,
                    "decision_point_configuration_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
                    "decoder_component_identity": authority.decoder_component_identity,
                    "decoder_configuration_identity": authority.decoder_configuration_identity,
                    "fundamental_measurement_vector_identities": list(observation.measurement_vector_identities),
                    "immutable_input_snapshot_identity": authority.immutable_input_snapshot_identity,
                    "ordered_collection_manifest_identity": authority.ordered_collection_manifest_identity,
                    "selected_observation_identity": selected_observation_identity,
                    "selected_snapshot_identity": observation.decision_snapshot_identity,
                },
            )
            if record["selected_scientific_state_identities"] != [selected_scientific_identity]:
                raise _fail("SELECTED_SCIENTIFIC_STATE_SUBSTITUTION")
        elif selected is False:
            if (
                eligible is not False
                or record.get("exclusion_reason") != "no_predeclared_decision_observation"
                or record.get("observation_index") != 0
                or observation is not None
                or any(record.get(field) != [] for field in (*_SINGLE_SELECTED_CONTAINERS, *_VECTOR_SELECTED_CONTAINERS))
            ):
                raise _fail("NONSELECTED_STATE_SHAPE_MISMATCH")
        else:
            raise _fail("SELECTED_STATE_SHAPE_MISMATCH")


def process_source_collection(
    members: Sequence[SourceMember], *, authority: SourceProcessingAuthority,
    projection_schema: Mapping[str, Any], configuration: Mapping[str, Any],
) -> SourceProcessingResult:
    """Governed production entry point; fixed dataset authentication is mandatory."""
    return _process_source_collection(
        members,
        authority=authority,
        projection_schema=projection_schema,
        expected_lifecycle_sha256=EXPERIMENT5_DATASET_SHA256,
        limits=SourceProcessingLimits.from_configuration(configuration),
    )


def process_source_collection_to_path(
    members: Sequence[SnapshotSourceMember],
    *,
    authority: SourceProcessingAuthority,
    projection_schema: Mapping[str, Any],
    configuration: Mapping[str, Any],
    private_projection_path: Path,
) -> StreamingSourceProcessingResult:
    """Governed bounded-generation entry point with no projection materialization."""

    result = _process_source_collection(
        members,
        authority=authority,
        projection_schema=projection_schema,
        expected_lifecycle_sha256=EXPERIMENT5_DATASET_SHA256,
        limits=SourceProcessingLimits.from_configuration(configuration),
        private_projection_path=private_projection_path,
    )
    if not isinstance(result, StreamingSourceProcessingResult):
        raise _fail("PROJECTION_INVALID")
    return result


def construct_selected_source_binding(
    result: SourceProcessingResult, *, round_id: int, authority: SourceProcessingAuthority,
    replay_evidence: Mapping[str, Any], dataset_identity: str,
) -> object:
    from orev3.experiments.rq003_experiment5_ranking import (
        ObservationReferenceAuthority,
        SelectedSourceProjectionBinding,
        replay_round_identity,
    )
    """Reconstruct one acyclic selected-source binding from authenticated roots."""
    validate_projection_population(result, authority=authority)
    observation = result.selected_observations.get(round_id)
    if observation is None: raise _fail("NO_SELECTED_DECISION")
    record = next((item for item in result.records if item["round_id"] == round_id), None)
    if record is None or record["source_unit_key"] != str(round_id): raise _fail("SOURCE_UNIT_KEY_MISMATCH")
    if _sha(result.projection_bytes) != result.projection_sha256 or result.projection_bytes != b"".join(canonical_bytes(item) for item in result.records):
        raise _fail("PROJECTION_SUBSTITUTION")
    reconstructed_vectors = tuple(
        PIPELINE.compute(observation.snapshot.execution_context(square)).canonical_bytes()
        for square in EXPERIMENT5_CANDIDATES
    )
    if reconstructed_vectors != observation.measurement_vector_bytes:
        raise _fail("MEASUREMENT_VECTOR_SUBSTITUTION")
    expected_selected_state = {
        "selected": True,
        "eligible": True,
        "exclusion_reason": "not_applicable",
        "observation_index": observation.observation_index,
        "selected_snapshot_identities": [observation.decision_snapshot_identity],
        "fundamental_measurement_vector_identities": list(observation.measurement_vector_identities),
        "deployed_lamports": list(observation.snapshot.deployed_lamports),
        "miner_counts": list(observation.snapshot.miner_counts),
        "total_miners_values": [observation.snapshot.total_miners],
        "active_round_motherlode_values": [observation.snapshot.active_round_motherlode],
        "pre_finalization_total_vaulted_values": [observation.snapshot.pre_finalization_total_vaulted],
        "pre_finalization_total_winnings_values": [observation.snapshot.pre_finalization_total_winnings],
        "production_cost_ema_values": [observation.snapshot.production_cost_ema],
        "treasury_motherlode_values": [observation.snapshot.treasury_motherlode],
    }
    if any(record.get(key) != value for key, value in expected_selected_state.items()):
        raise _fail("SELECTED_SCIENTIFIC_STATE_SUBSTITUTION")
    if len(record.get("selected_references", ())) != 1 or len(record.get("selected_observation_identities", ())) != 1 or len(record.get("selected_scientific_state_identities", ())) != 1:
        raise _fail("SELECTED_STATE_SHAPE_MISMATCH")
    selected_reference = record["selected_references"][0]
    if (
        selected_reference.get("observed_at_utc")
        != observation.reference.to_material()["observed_at_utc"].replace("+00:00", "Z")
        or selected_reference.get("rpc_slot") != observation.rpc_slot
        or selected_reference.get("source_file") != observation.reference.source_file
        or selected_reference.get("source_line_number")
        != observation.reference.source_line_number
    ):
        raise _fail("SELECTED_REFERENCE_SUBSTITUTION")
    selected_observation_identity = _identity(
        "orev3:rq003-experiment-005:selected-observation:v1",
        {
            "canonical_parsed_observation_identity": selected_reference["canonical_parsed_observation_identity"],
            "decision_selection_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
            "observation_index": observation.observation_index,
            "reference": {key: value for key, value in selected_reference.items() if key != "observation_index"},
        },
    )
    if record["selected_observation_identities"] != [selected_observation_identity]:
        raise _fail("SELECTED_OBSERVATION_SUBSTITUTION")
    selected_scientific_state_identity = _identity(
        "orev3:rq003-experiment-005:selected-scientific-state:v1",
        {
            "canonical_lifecycle_record_identity": record["canonical_lifecycle_record_identity"],
            "decision_point_configuration_identity": EXPERIMENT5_DECISION_SELECTION_IDENTITY,
            "decoder_component_identity": authority.decoder_component_identity,
            "decoder_configuration_identity": authority.decoder_configuration_identity,
            "fundamental_measurement_vector_identities": list(observation.measurement_vector_identities),
            "immutable_input_snapshot_identity": authority.immutable_input_snapshot_identity,
            "ordered_collection_manifest_identity": authority.ordered_collection_manifest_identity,
            "selected_observation_identity": selected_observation_identity,
            "selected_snapshot_identity": observation.decision_snapshot_identity,
        },
    )
    if record["selected_scientific_state_identities"] != [selected_scientific_state_identity]:
        raise _fail("SELECTED_SCIENTIFIC_STATE_SUBSTITUTION")
    ordered_sources = replay_evidence.get("ordered_source_unit_identities")
    ordered_decisions = replay_evidence.get("ordered_decision_identities")
    if not isinstance(ordered_sources, list) or not isinstance(ordered_decisions, list): raise _fail("REPLAY_AUTHORITY_MISMATCH")
    replay_source = domain_identity(SOURCE_UNIT_DOMAIN, {"dataset_identity": dataset_identity, "source_unit_key": str(round_id)})
    if replay_source not in ordered_sources: raise _fail("REPLAY_SOURCE_SUBSTITUTION")
    dispositions = replay_evidence.get("dispositions")
    matching_dispositions = [] if dispositions is None else [
        item for item in dispositions
        if (
        isinstance(item, Mapping)
        and item.get("source_unit_identity") == replay_source
        and item.get("status") == "replay_included"
        and item.get("decision_identity") in ordered_decisions
        )
    ]
    if dispositions is not None and len(matching_dispositions) != 1:
        raise _fail("SELECTED_DECISION_SUBSTITUTION")
    member = result.observation_members[round_id]
    references = tuple(
        ObservationReferenceAuthority(
            _timestamp(item["observed_at_utc"])[1], item["rpc_slot"],
            item["source_file"], item["source_line_number"],
        )
        for item in record["observation_references"]
    )
    round_identity = replay_round_identity(
        round_id=round_id, start_slot=record["start_slot"], end_slot=record["end_slot"],
        references=references,
    )
    if not matching_dispositions:
        raise _fail("SELECTED_DECISION_SUBSTITUTION")
    selected_decision = matching_dispositions[0]["decision_identity"]
    parsed_identity = selected_reference["canonical_parsed_observation_identity"]
    return SelectedSourceProjectionBinding(
        external_input_identifier=authority.external_input_identifier, external_input_identity=authority.external_input_identity, immutable_input_snapshot_identity=authority.immutable_input_snapshot_identity, ordered_collection_manifest_identity=authority.ordered_collection_manifest_identity,
        logical_member_identifier=member.logical_identifier, member_order=member.member_order, member_byte_count=member.expected_byte_count, member_sha256=member.expected_sha256,
        external_schema_identity=authority.raw_schema_identity, source_file=observation.reference.source_file, source_line_number=observation.reference.source_line_number, persisted_record_byte_sha256=selected_reference["persisted_record_byte_sha256"], canonical_parsed_record_identity=parsed_identity, source_schema_version=selected_reference["source_schema_version"], protocol_revision=EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION, observed_at_utc=observation.observed_at_utc, rpc_slot=observation.rpc_slot, valid_normal_observation=True, collector_session_id=(selected_reference["collector_session_id"] or None), decoder_component_identity=authority.decoder_component_identity, decoder_configuration_identity=authority.decoder_configuration_identity, parser_component_identity=authority.parser_component_identity, projector_component_identity=authority.projector_component_identity, projection_schema_identity=authority.projection_schema_identity, projection_sha256=result.projection_sha256, projection_identity=result.projection_identity, dataset_identity=dataset_identity, dataset_content_identity=result.dataset_content_identity, replay_source_unit_identity=replay_source, selected_decision_identity=selected_decision, selected_reference_identity=observation.reference.reference_identity, selected_observation_index=observation.observation_index, selected_snapshot_identity=observation.decision_snapshot_identity, fundamental_measurement_vector_identities=observation.measurement_vector_identities,
    )


def authority_byte_parity() -> Mapping[str, str]:
    return {"protocol": EXPERIMENT5_PROTOCOL_SHA256, "minimum_effect": EXPERIMENT5_MINIMUM_EFFECT_CLARIFICATION_SHA256, "source_processing": EXPERIMENT5_SOURCE_PROCESSING_PREREQUISITE_SHA256}


__all__ = ["SourceMember", "SourceProcessingAuthority", "SourceProcessingResult", "authenticate_configuration", "authority_byte_parity", "construct_selected_source_binding", "process_source_collection", "reconstruct_bounded_source_processing_material_identity", "reconstruct_rq003_experiment5_bounded_policy_binding_identity", "reconstruct_source_authority"]
