"""Governed raw parsing and exact outcome-blind projection.

This module exists only in the INPUT_PROJECTOR code capability.  It emits
stable failure codes and never includes raw record values in diagnostics.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    parse_json,
    validate_json_schema_instance,
)
from orev3.execution.dataset_validation import reconstruct_dataset_content_identity
from orev3.execution.filesystem_capability import open_pinned_regular, verify_opened_regular


def _require_closed_schema(schema: Mapping[str, Any], *, label: str) -> tuple[str, ...]:
    permitted_schema_keywords = {
        "$id",
        "$schema",
        "additionalProperties",
        "const",
        "enum",
        "items",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "pattern",
        "properties",
        "required",
        "type",
        "uniqueItems",
    }
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise CanonicalControlError(f"{label}_SCHEMA_INVALID")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, Mapping) or not isinstance(required, list):
        raise CanonicalControlError(f"{label}_SCHEMA_INVALID")
    if set(required) != set(properties) or len(required) != len(set(required)):
        raise CanonicalControlError(f"{label}_SCHEMA_INVALID")

    def closed(node: Any) -> None:
        if not isinstance(node, Mapping):
            return
        if not set(node).issubset(permitted_schema_keywords):
            raise CanonicalControlError(f"{label}_SCHEMA_INVALID")
        node_type = node.get("type")
        if node_type is not None and node_type not in {
            "array", "boolean", "integer", "number", "object", "string"
        }:
            raise CanonicalControlError(f"{label}_SCHEMA_INVALID")
        if node.get("type") == "object":
            if node.get("additionalProperties") is not False:
                raise CanonicalControlError(f"{label}_SCHEMA_INVALID")
            nested = node.get("properties")
            nested_required = node.get("required")
            if not isinstance(nested, Mapping) or not isinstance(nested_required, list) or set(nested_required) != set(nested):
                raise CanonicalControlError(f"{label}_SCHEMA_INVALID")
        nested_properties = node.get("properties")
        if isinstance(nested_properties, Mapping):
            for value in nested_properties.values():
                closed(value)
        if "items" in node:
            closed(node["items"])

    closed(schema)
    return tuple(required)


def validate_projection_schema(schema: Mapping[str, Any]) -> tuple[str, ...]:
    fields = _require_closed_schema(schema, label="PROJECTION")
    if not fields:
        raise CanonicalControlError("PROJECTION_SCHEMA_INVALID")
    return fields


def validate_raw_schema(schema: Mapping[str, Any]) -> tuple[str, ...]:
    return _require_closed_schema(schema, label="INPUT")


def validate_outcome_blind_records(
    records: Sequence[Mapping[str, Any]], *, projection_schema: Mapping[str, Any]
) -> None:
    validate_projection_schema(projection_schema)
    for record in records:
        validate_json_schema_instance(record, projection_schema, schema_registry={})


def canonical_jsonl(records: Sequence[Mapping[str, Any]], *, projection_schema: Mapping[str, Any]) -> bytes:
    validate_outcome_blind_records(records, projection_schema=projection_schema)
    return b"".join(canonical_bytes(record) for record in records)


def _verified_regular_file(path: Path, *, expected_sha256: str, expected_size: int, limit: int) -> bytes:
    try:
        descriptor, _ = open_pinned_regular(path, error_code="INPUT_MISMATCH")
    except CanonicalControlError as exc:
        raise CanonicalControlError("INPUT_MISMATCH") from exc
    try:
        return verify_opened_regular(
            descriptor,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
            limit=limit,
            error_code="INPUT_MISMATCH",
            mutation_error_code="INPUT_MUTATED",
        )
    finally:
        os.close(descriptor)


def project_jsonl(
    raw_path: Path,
    *,
    raw_schema: Mapping[str, Any],
    projection_schema: Mapping[str, Any],
    expected_raw_sha256: str,
    expected_raw_size: int,
    max_raw_bytes: int,
    max_projection_bytes: int,
    max_records: int,
) -> tuple[bytes, int, str]:
    """Validate raw records and emit only the governed positive projection."""

    projection_fields = validate_projection_schema(projection_schema)
    validate_raw_schema(raw_schema)
    raw_bytes = _verified_regular_file(
        raw_path, expected_sha256=expected_raw_sha256,
        expected_size=expected_raw_size, limit=max_raw_bytes,
    )
    records: list[dict[str, Any]] = []
    record_sha256s: list[str] = []
    lines = raw_bytes.splitlines()
    if len(lines) > max_records:
        raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    for line in lines:
        try:
            raw = parse_json(line, max_bytes=max_raw_bytes)
            if not isinstance(raw, dict):
                raise CanonicalControlError("INPUT_SCHEMA_MISMATCH")
            validate_json_schema_instance(raw, raw_schema, schema_registry={})
            record_sha256s.append(hashlib.sha256(canonical_bytes(raw)).hexdigest())
            projected = {field: raw[field] for field in projection_fields}
            validate_json_schema_instance(projected, projection_schema, schema_registry={})
        except CanonicalControlError:
            raise
        except Exception as exc:
            raise CanonicalControlError("INPUT_SCHEMA_MISMATCH") from exc
        records.append(projected)
    output = canonical_jsonl(records, projection_schema=projection_schema)
    if len(output) > max_projection_bytes:
        raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    return output, len(records), reconstruct_dataset_content_identity(record_sha256s)


__all__ = ["canonical_jsonl", "project_jsonl", "validate_outcome_blind_records", "validate_projection_schema", "validate_raw_schema"]
