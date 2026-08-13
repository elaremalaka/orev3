"""Mechanical helpers shared by explicit RQ-003 measurements.

This module owns canonical mechanics only. Measurement semantics, metadata,
dependencies, eligibility, and protocol value access remain measurement-owned.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from orev3.features.rq003_contracts import canonical_decode, canonical_encode


U64_MAX = (1 << 64) - 1


def domain_identity(domain: str, material: object) -> str:
    """Return one domain-separated canonical SHA-256 identity."""

    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def validate_dependency_items(name: str, items: object) -> None:
    """Validate canonical immutable dependency declaration items."""

    if not isinstance(items, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    keys: list[str] = []
    for item in items:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or not isinstance(item[1], (str, int))
            or isinstance(item[1], bool)
        ):
            raise TypeError(f"{name} must contain canonical key/value tuples")
        if not isinstance(item[1], int) and (
            not item[1] or item[1].strip() != item[1]
        ):
            raise ValueError(f"{name} contains a noncanonical value")
        keys.append(item[0])
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name} keys must be unique")


def require_u64(name: str, value: object) -> int:
    """Return an exact non-boolean unsigned 64-bit integer or fail closed."""

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > U64_MAX
    ):
        raise ValueError(f"{name} must be an unsigned 64-bit integer")
    return value


def reconstruct_single_u64_output(
    raw: bytes,
    *,
    output_name: str,
    artifact_name: str,
) -> Mapping[str, int]:
    """Reconstruct one canonical single-field unsigned-integer output."""

    decoded = canonical_decode(raw)
    if not isinstance(decoded, dict):
        raise ValueError(f"{artifact_name} output must be a mapping")
    if set(decoded) != {output_name}:
        raise ValueError(
            f"{artifact_name} output must contain exactly its declared field"
        )
    value = require_u64(output_name, decoded[output_name])
    return MappingProxyType({output_name: value})


def require_mapping(name: str, value: object) -> Mapping[str, Any]:
    """Return a string-keyed immutable-compatible mapping or fail closed."""

    if not isinstance(value, Mapping) or not all(
        isinstance(key, str) for key in value
    ):
        raise TypeError(f"{name} must be a string-keyed mapping")
    return value


def require_u64_vector(name: str, values: object) -> tuple[int, ...]:
    """Return one exact immutable 25-element unsigned-integer vector."""

    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    if len(values) != 25:
        raise ValueError(f"{name} must contain exactly 25 values")
    return tuple(require_u64(f"{name} value", value) for value in values)


__all__ = (
    "U64_MAX",
    "domain_identity",
    "reconstruct_single_u64_output",
    "require_mapping",
    "require_u64",
    "require_u64_vector",
    "validate_dependency_items",
)
