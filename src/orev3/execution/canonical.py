"""Strict canonical JSON and identities for readiness-v1 control objects.

This module deliberately does not reuse the historical RQ-003 encoders.  The
readiness-v1 format is null-free, float-free, NFC-only JSON with an exact
byte-level representation and domain-separated identities.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any, NoReturn


MAX_CONTROL_OBJECT_BYTES = 1_048_576
MAX_NESTING_DEPTH = 64
MAX_COLLECTION_ITEMS = 16_384
MAX_STRING_CODEPOINTS = 262_144

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_SHA1_PATTERN = re.compile(r"[0-9a-f]{40}")
GIT_SHA256_PATTERN = SHA256_PATTERN
EXPERIMENT_IDENTIFIER_PATTERN = re.compile(
    r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*"
)


class CanonicalControlError(ValueError):
    """A readiness-v1 control object is malformed or noncanonical."""


def _reject_float(value: str) -> NoReturn:
    raise CanonicalControlError(
        f"floating-point and exponent numbers are prohibited: {value}"
    )


def _reject_constant(value: str) -> NoReturn:
    raise CanonicalControlError(f"non-JSON numeric constant is prohibited: {value}")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    normalized: set[str] = set()
    for key, value in pairs:
        if not isinstance(key, str):
            raise CanonicalControlError("object keys must be strings")
        nfc = unicodedata.normalize("NFC", key)
        if key != nfc:
            raise CanonicalControlError("object keys must already be NFC")
        if nfc in normalized:
            raise CanonicalControlError("duplicate object key after NFC normalization")
        normalized.add(nfc)
        result[key] = value
    return result


def parse_json(raw: bytes, *, max_bytes: int = MAX_CONTROL_OBJECT_BYTES) -> Any:
    """Parse strict readiness JSON without accepting alternate scalar types."""

    if not isinstance(raw, bytes):
        raise TypeError("canonical input must be bytes")
    if len(raw) > max_bytes:
        raise CanonicalControlError("canonical control object exceeds byte limit")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CanonicalControlError("UTF-8 BOM is prohibited")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalControlError("control object is not strict UTF-8 JSON") from exc
    validate_value(value)
    return value


def validate_value(value: Any, *, _depth: int = 0) -> None:
    """Validate scalar types, NFC, bounded structure, and null prohibition."""

    if _depth > MAX_NESTING_DEPTH:
        raise CanonicalControlError("canonical object exceeds nesting limit")
    if value is None:
        raise CanonicalControlError("JSON null is prohibited")
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise CanonicalControlError("floating-point values are prohibited")
    if isinstance(value, str):
        if len(value) > MAX_STRING_CODEPOINTS:
            raise CanonicalControlError("string exceeds canonical length limit")
        if unicodedata.normalize("NFC", value) != value:
            raise CanonicalControlError("strings must already be NFC")
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise CanonicalControlError("lone surrogates are prohibited")
        return
    if isinstance(value, Mapping):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise CanonicalControlError("object exceeds canonical member limit")
        seen: set[str] = set()
        for key, member in value.items():
            if not isinstance(key, str):
                raise CanonicalControlError("object keys must be strings")
            if unicodedata.normalize("NFC", key) != key:
                raise CanonicalControlError("object keys must already be NFC")
            if key in seen:
                raise CanonicalControlError("duplicate object key")
            seen.add(key)
            validate_value(member, _depth=_depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise CanonicalControlError("array exceeds canonical member limit")
        for member in value:
            validate_value(member, _depth=_depth + 1)
        return
    raise CanonicalControlError(f"unsupported canonical value type: {type(value).__name__}")


def _encode_string(value: str) -> str:
    result: list[str] = ['"']
    named = {
        '"': r'\"',
        "\\": r"\\",
        "\b": r"\b",
        "\t": r"\t",
        "\n": r"\n",
        "\f": r"\f",
        "\r": r"\r",
    }
    for char in value:
        if char in named:
            result.append(named[char])
        elif ord(char) <= 0x1F:
            result.append(f"\\u{ord(char):04x}")
        else:
            result.append(char)
    result.append('"')
    return "".join(result)


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, Mapping):
        return "{" + ",".join(
            f"{_encode_string(key)}:{_encode(value[key])}" for key in sorted(value)
        ) + "}"
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return "[" + ",".join(_encode(member) for member in value) + "]"
    raise CanonicalControlError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Serialize a validated value under readiness-v1 canonical JSON."""

    validate_value(value)
    return (_encode(value) + "\n").encode("utf-8")


def parse_canonical_bytes(
    raw: bytes,
    *,
    validator: Callable[[Mapping[str, Any]], None] | None = None,
    max_bytes: int = MAX_CONTROL_OBJECT_BYTES,
) -> dict[str, Any]:
    """Parse, schema-validate, and require exact byte-level canonicality."""

    value = parse_json(raw, max_bytes=max_bytes)
    if not isinstance(value, dict):
        raise CanonicalControlError("canonical control object must be an object")
    if validator is not None:
        validator(value)
    if canonical_bytes(value) != raw:
        raise CanonicalControlError("control object bytes are not canonical")
    return value


def domain_identity(domain_line: str, material: Mapping[str, Any]) -> str:
    """Return SHA-256(domain line || canonical material)."""

    if not isinstance(domain_line, str) or not domain_line.endswith("\n"):
        raise CanonicalControlError("identity domain must end with exactly one LF")
    if "\x00" in domain_line or unicodedata.normalize("NFC", domain_line) != domain_line:
        raise CanonicalControlError("identity domain is invalid")
    return hashlib.sha256(domain_line.encode("utf-8") + canonical_bytes(material)).hexdigest()


def validate_exact_fields(
    value: Mapping[str, Any], required: set[str] | frozenset[str], *, label: str
) -> None:
    actual = set(value)
    missing = sorted(required - actual)
    unknown = sorted(actual - required)
    if missing or unknown:
        raise CanonicalControlError(
            f"{label} fields are invalid; missing={missing}, unknown={unknown}"
        )


def require_string(name: str, value: Any, *, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise CanonicalControlError(f"{name} must be a canonical nonempty string")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise CanonicalControlError(f"{name} has invalid syntax")
    return value


def require_integer(name: str, value: Any, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CanonicalControlError(f"{name} must be an integer >= {minimum}")
    return value


def require_boolean(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise CanonicalControlError(f"{name} must be a boolean")
    return value


def require_sha256(name: str, value: Any) -> str:
    return require_string(name, value, pattern=SHA256_PATTERN)


def require_git_object(name: str, value: Any, object_format: str = "sha1") -> str:
    pattern = GIT_SHA1_PATTERN if object_format == "sha1" else GIT_SHA256_PATTERN
    return require_string(name, value, pattern=pattern)


def normalize_experiment_identifier(value: str) -> str:
    value = require_string(
        "experiment_identifier", value, pattern=EXPERIMENT_IDENTIFIER_PATTERN
    )
    if unicodedata.normalize("NFC", value) != value:
        raise CanonicalControlError("experiment identifier must be NFC")
    return value


def validate_repository_path(value: Any, *, label: str = "repository_path") -> str:
    path = require_string(label, value)
    if unicodedata.normalize("NFC", path) != path:
        raise CanonicalControlError(f"{label} must be NFC")
    if "\\" in path or "\x00" in path or path.startswith("/"):
        raise CanonicalControlError(f"{label} must be a relative POSIX path")
    segments = path.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise CanonicalControlError(f"{label} contains a prohibited segment")
    if str(PurePosixPath(path)) != path:
        raise CanonicalControlError(f"{label} is not normalized")
    return path


def require_sorted_unique(
    name: str,
    values: Any,
    *,
    key: Callable[[Any], Any],
    uniqueness: Callable[[Any], Any] | None = None,
) -> list[Any]:
    if not isinstance(values, list):
        raise CanonicalControlError(f"{name} must be an array")
    keys = [key(value) for value in values]
    if keys != sorted(keys):
        raise CanonicalControlError(f"{name} is not canonically ordered")
    unique_values = [uniqueness(value) for value in values] if uniqueness else keys
    if len(unique_values) != len(set(unique_values)):
        raise CanonicalControlError(f"{name} contains duplicate stable identifiers")
    return values


def validate_json_schema_instance(
    instance: Any,
    schema: Mapping[str, Any],
    *,
    schema_registry: Mapping[str, Mapping[str, Any]],
) -> None:
    """Validate the strict JSON-Schema subset used by readiness-v1.

    Phase 2 intentionally owns this small interpreter instead of adding an
    ambient dependency.  Unsupported schema keywords fail closed, while the
    repository extensions for canonical ordering and stable-key uniqueness
    are enforced rather than treated as comments.
    """

    _validate_schema_node(
        instance,
        schema,
        root_schema=schema,
        schema_registry=schema_registry,
        location="$",
    )


_SUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "$defs",
        "$id",
        "$ref",
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
        "oneOf",
        "pattern",
        "properties",
        "required",
        "title",
        "type",
        "uniqueItems",
        "x-canonical-order",
        "x-input-member-cardinality",
        "x-order-semantics",
        "x-unique-key",
    }
)


def _validate_schema_node(
    instance: Any,
    schema: Mapping[str, Any],
    *,
    root_schema: Mapping[str, Any],
    schema_registry: Mapping[str, Mapping[str, Any]],
    location: str,
) -> None:
    unknown = set(schema) - _SUPPORTED_SCHEMA_KEYWORDS
    if unknown:
        raise CanonicalControlError(
            f"schema at {location} uses unsupported keywords: {sorted(unknown)}"
        )
    if "$ref" in schema:
        if len(schema) != 1:
            raise CanonicalControlError(f"schema $ref at {location} must stand alone")
        target, target_root = _resolve_schema_reference(
            schema["$ref"], root_schema, schema_registry
        )
        _validate_schema_node(
            instance,
            target,
            root_schema=target_root,
            schema_registry=schema_registry,
            location=location,
        )
        return
    if "oneOf" in schema:
        branches = schema["oneOf"]
        if not isinstance(branches, list) or not branches:
            raise CanonicalControlError(f"oneOf at {location} is malformed")
        matches = 0
        for branch in branches:
            try:
                _validate_schema_node(
                    instance,
                    branch,
                    root_schema=root_schema,
                    schema_registry=schema_registry,
                    location=location,
                )
            except CanonicalControlError:
                continue
            matches += 1
        if matches != 1:
            raise CanonicalControlError(
                f"value at {location} matches {matches} oneOf branches"
            )
        return

    if "const" in schema and instance != schema["const"]:
        raise CanonicalControlError(f"value at {location} violates const")
    if "enum" in schema and instance not in schema["enum"]:
        raise CanonicalControlError(f"value at {location} is outside enum")
    expected_type = schema.get("type")
    if expected_type is not None and not _schema_type_matches(instance, expected_type):
        raise CanonicalControlError(f"value at {location} has the wrong type")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise CanonicalControlError(f"string at {location} is too short")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise CanonicalControlError(f"string at {location} is too long")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise CanonicalControlError(f"string at {location} violates pattern")
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise CanonicalControlError(f"integer at {location} is below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise CanonicalControlError(f"integer at {location} exceeds maximum")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise CanonicalControlError(f"array at {location} is too short")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise CanonicalControlError(f"array at {location} is too long")
        if schema.get("uniqueItems"):
            encoded = [canonical_bytes(item) for item in instance]
            if len(encoded) != len(set(encoded)):
                raise CanonicalControlError(f"array at {location} is not unique")
        if "items" in schema:
            for index, member in enumerate(instance):
                _validate_schema_node(
                    member,
                    schema["items"],
                    root_schema=root_schema,
                    schema_registry=schema_registry,
                    location=f"{location}[{index}]",
                )
        _validate_schema_collection_extensions(instance, schema, location)
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise CanonicalControlError(f"object schema at {location} is malformed")
        missing = set(required) - set(instance)
        if missing:
            raise CanonicalControlError(
                f"object at {location} is missing fields: {sorted(missing)}"
            )
        unknown_fields = set(instance) - set(properties)
        if unknown_fields and schema.get("additionalProperties") is False:
            raise CanonicalControlError(
                f"object at {location} has unknown fields: {sorted(unknown_fields)}"
            )
        for key, member in instance.items():
            if key in properties:
                _validate_schema_node(
                    member,
                    properties[key],
                    root_schema=root_schema,
                    schema_registry=schema_registry,
                    location=f"{location}.{key}",
                )
        if schema.get("x-input-member-cardinality") is True:
            if instance.get("input_kind") == "regular_file" and len(instance.get("members", [])) != 1:
                raise CanonicalControlError(
                    f"regular-file input at {location} must have exactly one member"
                )


def _resolve_schema_reference(
    reference: Any,
    root_schema: Mapping[str, Any],
    schema_registry: Mapping[str, Mapping[str, Any]],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(reference, str) or not reference:
        raise CanonicalControlError("schema reference is malformed")
    if reference.startswith("#/"):
        target: Any = root_schema
        for encoded in reference[2:].split("/"):
            key = encoded.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or key not in target:
                raise CanonicalControlError("local schema reference cannot be resolved")
            target = target[key]
        if not isinstance(target, dict):
            raise CanonicalControlError("local schema reference is not an object")
        return target, root_schema
    if "#" in reference or "/" in reference or "\\" in reference:
        raise CanonicalControlError("external schema reference is noncanonical")
    target = schema_registry.get(reference)
    if target is None:
        raise CanonicalControlError("external schema reference cannot be resolved")
    return target, target


def _schema_type_matches(instance: Any, expected: Any) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    raise CanonicalControlError(f"unsupported schema type: {expected!r}")


def _validate_schema_collection_extensions(
    values: list[Any], schema: Mapping[str, Any], location: str
) -> None:
    order = schema.get("x-canonical-order")
    if order is not None:
        if not isinstance(order, list) or not order:
            raise CanonicalControlError(f"canonical order at {location} is malformed")
        keys = [_schema_collection_key(item, order) for item in values]
        if keys != sorted(keys):
            raise CanonicalControlError(f"array at {location} is not canonically ordered")
    if schema.get("x-order-semantics") == "role-then-member-paths-then-identifier":
        keys = []
        for item in values:
            if not isinstance(item, dict):
                raise CanonicalControlError(
                    f"external input declaration at {location} is not an object"
                )
            members = item.get("members")
            if not isinstance(members, list):
                raise CanonicalControlError(
                    f"external input members at {location} are malformed"
                )
            keys.append(
                (
                    item.get("role", ""),
                    tuple(
                        member.get("member_path", "")
                        for member in members
                        if isinstance(member, dict)
                    ),
                    item.get("external_input_identifier", ""),
                )
            )
        if keys != sorted(keys):
            raise CanonicalControlError(
                f"external inputs at {location} are not canonically ordered"
            )
    unique = schema.get("x-unique-key")
    if unique is not None:
        if not isinstance(unique, list) or not unique:
            raise CanonicalControlError(f"unique key at {location} is malformed")
        keys = [_schema_collection_key(item, unique) for item in values]
        if len(keys) != len(set(keys)):
            raise CanonicalControlError(
                f"array at {location} has duplicate stable identifiers"
            )


def _schema_collection_key(item: Any, fields: list[Any]) -> tuple[Any, ...]:
    if fields == ["value"]:
        if isinstance(item, (dict, list)):
            raise CanonicalControlError("value ordering requires scalar array members")
        return (item,)
    if not isinstance(item, dict):
        raise CanonicalControlError("field ordering requires object array members")
    result: list[Any] = []
    for field in fields:
        if not isinstance(field, str) or field not in item:
            raise CanonicalControlError("schema collection key is unavailable")
        result.append(item[field])
    return tuple(result)


__all__ = [
    "CanonicalControlError",
    "EXPERIMENT_IDENTIFIER_PATTERN",
    "GIT_SHA1_PATTERN",
    "GIT_SHA256_PATTERN",
    "MAX_CONTROL_OBJECT_BYTES",
    "SHA256_PATTERN",
    "canonical_bytes",
    "domain_identity",
    "normalize_experiment_identifier",
    "parse_canonical_bytes",
    "parse_json",
    "require_boolean",
    "require_git_object",
    "require_integer",
    "require_sha256",
    "require_sorted_unique",
    "require_string",
    "validate_exact_fields",
    "validate_json_schema_instance",
    "validate_repository_path",
    "validate_value",
]
