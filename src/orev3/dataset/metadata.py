"""Immutable canonical metadata for managed replay datasets."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    """Immutable provenance and integrity metadata for one dataset build."""

    dataset_version: str
    created_at_utc: datetime
    source_collection: tuple[str, ...]
    replay_round_count: int
    snapshot_count: int
    complete_round_count: int
    incomplete_round_count: int
    missing_outcome_count: int
    integrity_status: Literal["valid"]
    ready_for_replay: bool
    dataset_sha256: str
    metadata_schema_version: int = 1

    def __post_init__(self) -> None:
        if self.metadata_schema_version != 1:
            raise ValueError("metadata_schema_version must be 1")
        _canonical_text("dataset_version", self.dataset_version)
        created_at = self.created_at_utc
        if not isinstance(created_at, datetime) or created_at.tzinfo is None:
            raise ValueError("created_at_utc must be timezone-aware")
        object.__setattr__(self, "created_at_utc", created_at.astimezone(UTC))
        sources = tuple(self.source_collection)
        if not sources or any(
            not isinstance(source, str) or not source for source in sources
        ):
            raise ValueError("source_collection must contain source paths")
        if tuple(sorted(set(sources))) != sources:
            raise ValueError(
                "source_collection must be sorted and contain no duplicates"
            )
        object.__setattr__(self, "source_collection", sources)
        for name in (
            "replay_round_count",
            "snapshot_count",
            "complete_round_count",
            "incomplete_round_count",
            "missing_outcome_count",
        ):
            _nonnegative_integer(name, getattr(self, name))
        if (
            self.complete_round_count + self.incomplete_round_count
            != self.replay_round_count
        ):
            raise ValueError(
                "complete and incomplete counts must equal replay_round_count"
            )
        if self.integrity_status != "valid":
            raise ValueError("only validated datasets may receive metadata")
        if not isinstance(self.ready_for_replay, bool):
            raise TypeError("ready_for_replay must be a boolean")
        if self.ready_for_replay != (
            self.incomplete_round_count == 0
            and self.missing_outcome_count == 0
        ):
            raise ValueError("ready_for_replay is inconsistent with completeness")
        if (
            not isinstance(self.dataset_sha256, str)
            or len(self.dataset_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.dataset_sha256)
        ):
            raise ValueError("dataset_sha256 must be a lowercase SHA-256 digest")


def dataset_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_metadata(metadata: DatasetMetadata, path: str | Path) -> Path:
    """Atomically persist canonical metadata without mutating the dataset."""

    if not isinstance(metadata, DatasetMetadata):
        raise TypeError("metadata must be DatasetMetadata")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_metadata_json(metadata) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def load_metadata(path: str | Path) -> DatasetMetadata:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {
        "complete_round_count",
        "created_at_utc",
        "dataset_sha256",
        "dataset_version",
        "incomplete_round_count",
        "integrity_status",
        "metadata_schema_version",
        "missing_outcome_count",
        "ready_for_replay",
        "replay_round_count",
        "snapshot_count",
        "source_collection",
    }:
        raise ValueError("dataset metadata fields are invalid")
    return DatasetMetadata(
        metadata_schema_version=raw["metadata_schema_version"],
        dataset_version=raw["dataset_version"],
        created_at_utc=datetime.fromisoformat(raw["created_at_utc"]),
        source_collection=tuple(raw["source_collection"]),
        replay_round_count=raw["replay_round_count"],
        snapshot_count=raw["snapshot_count"],
        complete_round_count=raw["complete_round_count"],
        incomplete_round_count=raw["incomplete_round_count"],
        missing_outcome_count=raw["missing_outcome_count"],
        integrity_status=raw["integrity_status"],
        ready_for_replay=raw["ready_for_replay"],
        dataset_sha256=raw["dataset_sha256"],
    )


def _canonical_metadata_json(metadata: DatasetMetadata) -> str:
    value: dict[str, Any] = asdict(metadata)
    value["created_at_utc"] = metadata.created_at_utc.isoformat()
    value["source_collection"] = list(metadata.source_collection)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be a nonempty canonical string")


def _nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


__all__ = (
    "DatasetMetadata",
    "dataset_sha256",
    "load_metadata",
    "write_metadata",
)
