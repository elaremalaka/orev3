"""Immutable preparation-input snapshots for readiness Phase 3B.

This module copies bytes only.  It never parses scientific records and never
grants a snapshot scientific authority merely because it exists on disk.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from os import PathLike
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import CanonicalControlError, domain_identity
from orev3.execution.filesystem_capability import (
    open_pinned_regular,
    publish_content_addressed_bytes,
    verify_opened_regular,
)

INPUT_SNAPSHOT_DOMAIN = "orev3:experiment-input-snapshot:v1\n"


class InputSnapshotError(CanonicalControlError):
    """A mutable input could not be made into a coherent immutable object."""


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    max_file_bytes: int
    max_collection_members: int
    max_aggregate_collection_bytes: int
    max_projection_bytes: int
    max_replay_units: int
    max_subprocess_seconds: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    max_temporary_disk_bytes: int

    @classmethod
    def from_policy(cls, policy: Mapping[str, Any]) -> "ResourceLimits":
        limits = policy["limits"]
        return cls(*(limits[name] for name in cls.__dataclass_fields__))


@dataclass(frozen=True, slots=True)
class SnapshotMember:
    logical_identifier: str
    byte_count: int
    sha256: str
    content_object: Path


@dataclass(frozen=True, slots=True)
class ImmutableInputSnapshot:
    material: Mapping[str, Any]
    identity: str
    members: tuple[SnapshotMember, ...]


PathArgument = str | PathLike[str]


def _open_regular_unlinked(path: PathArgument) -> tuple[int, os.stat_result]:
    try:
        return open_pinned_regular(
            path,
            error_code="INPUT_UNSAFE_TYPE: symlink component",
            missing_error_code="INPUT_UNAVAILABLE",
            nonblocking=True,
        )
    except CanonicalControlError as exc:
        raise InputSnapshotError(str(exc)) from exc


def snapshot_regular_file(
    source: PathArgument,
    *,
    logical_identifier: str,
    declared_byte_count: int,
    declared_sha256: str,
    object_store: Path,
    max_file_bytes: int,
) -> SnapshotMember:
    """Snapshot one descriptor-pinned source and publish verified bytes."""

    descriptor, _ = _open_regular_unlinked(source)
    try:
        try:
            payload = verify_opened_regular(
                descriptor,
                expected_size=declared_byte_count,
                expected_sha256=declared_sha256,
                limit=max_file_bytes,
                error_code="INPUT_MISMATCH",
                mutation_error_code="INPUT_MUTATED",
            )
        except CanonicalControlError as exc:
            message = "RESOURCE_LIMIT_EXCEEDED" if declared_byte_count > max_file_bytes else str(exc)
            raise InputSnapshotError(message) from exc
    finally:
        os.close(descriptor)
    try:
        destination = publish_content_addressed_bytes(
            payload,
            store=object_store,
            expected_sha256=declared_sha256,
            limit=max_file_bytes,
            error_code="INPUT_MISMATCH: content-addressed collision",
        )
    except CanonicalControlError as exc:
        raise InputSnapshotError(str(exc)) from exc
    return SnapshotMember(logical_identifier, len(payload), declared_sha256, destination)


def snapshot_declared_input(
    declaration: Mapping[str, Any],
    *,
    locator_paths: Mapping[str, PathArgument],
    object_store: Path,
    limits: ResourceLimits,
) -> ImmutableInputSnapshot:
    declared = declaration["members"]
    if declaration.get("input_kind") != "regular_file" or len(declared) != 1:
        raise InputSnapshotError("INPUT_SCHEMA_MISMATCH: ordered collections are unsupported in Phase-3B v1")
    if not declared or len(declared) > limits.max_collection_members:
        raise InputSnapshotError("RESOURCE_LIMIT_EXCEEDED")
    identifiers = [member["logical_identifier"] for member in declared]
    paths = [member["member_path"] for member in declared]
    if len(set(identifiers)) != len(identifiers) or len(set(paths)) != len(paths):
        raise InputSnapshotError("INPUT_MISMATCH: duplicate collection member")
    declared_total = sum(member["byte_count"] for member in declared)
    if declared_total > limits.max_aggregate_collection_bytes or declared_total > limits.max_temporary_disk_bytes:
        raise InputSnapshotError("RESOURCE_LIMIT_EXCEEDED")
    members: list[SnapshotMember] = []
    for member in declared:
        locator = locator_paths.get(member["member_path"])
        if locator is None:
            raise InputSnapshotError("INPUT_UNAVAILABLE")
        members.append(snapshot_regular_file(
            locator,
            logical_identifier=member["logical_identifier"],
            declared_byte_count=member["byte_count"],
            declared_sha256=member["sha256"],
            object_store=object_store,
            max_file_bytes=limits.max_file_bytes,
        ))
    if sum(member.byte_count for member in members) > limits.max_aggregate_collection_bytes:
        raise InputSnapshotError("RESOURCE_LIMIT_EXCEEDED")
    material = {
        "external_input_identifier": declaration["external_input_identifier"],
        "input_kind": declaration["input_kind"],
        "members": [
            {"byte_count": item.byte_count, "logical_member_identifier": item.logical_identifier, "member_order": index, "sha256": item.sha256}
            for index, item in enumerate(members)
        ],
        "schema_version": 1,
        "input_snapshot_identity": "0" * 64,
    }
    identity = domain_identity(INPUT_SNAPSHOT_DOMAIN, {key: value for key, value in material.items() if key != "input_snapshot_identity"})
    material["input_snapshot_identity"] = identity
    return ImmutableInputSnapshot(material, identity, tuple(members))


__all__ = ["INPUT_SNAPSHOT_DOMAIN", "ImmutableInputSnapshot", "InputSnapshotError", "ResourceLimits", "SnapshotMember", "snapshot_declared_input", "snapshot_regular_file"]
