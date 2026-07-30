"""Research-only orchestration for rebuilding and inspecting replay datasets."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from orev3.dataset.metadata import (
    DatasetMetadata,
    dataset_sha256,
    load_metadata,
    write_metadata,
)
from orev3.dataset.validation import (
    DatasetValidationResult,
    validate_replay_dataset,
)
from orev3.historical.assembler import assemble_rounds
from orev3.historical.enricher import enrich_rounds
from orev3.historical.persistence import (
    lifecycle_to_index_record,
    write_round_index,
)
from orev3.historical.reader import read_observer_files
from orev3.observer.rpc import SolanaRpcClient


DEFAULT_OBSERVER_ROOT = Path("data/raw")
DEFAULT_OBSERVER_PATTERN = "observer*.jsonl"
DEFAULT_DATASET_PATH = Path("data/derived/replay_dataset_v1.jsonl")
DEFAULT_METADATA_PATH = Path("data/derived/replay_dataset_v1.metadata.json")
DEFAULT_DATASET_VERSION = "replay-dataset-v1"


@dataclass(frozen=True, slots=True)
class DatasetBuildConfiguration:
    output_path: Path = DEFAULT_DATASET_PATH
    metadata_path: Path = DEFAULT_METADATA_PATH
    dataset_version: str = DEFAULT_DATASET_VERSION
    observer_paths: tuple[Path, ...] = ()
    observer_root: Path = DEFAULT_OBSERVER_ROOT
    observer_pattern: str = DEFAULT_OBSERVER_PATTERN
    enrich_missing_outcomes: bool = True
    enrichment_delay_seconds: float = 0.25
    created_at_utc: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_path", Path(self.output_path))
        object.__setattr__(self, "metadata_path", Path(self.metadata_path))
        object.__setattr__(self, "observer_root", Path(self.observer_root))
        paths = tuple(sorted({Path(path) for path in self.observer_paths}))
        object.__setattr__(self, "observer_paths", paths)
        if (
            not isinstance(self.dataset_version, str)
            or not self.dataset_version
            or self.dataset_version.strip() != self.dataset_version
        ):
            raise ValueError("dataset_version must be a canonical string")
        if (
            not isinstance(self.observer_pattern, str)
            or not self.observer_pattern
        ):
            raise ValueError("observer_pattern must be nonempty")
        if not isinstance(self.enrich_missing_outcomes, bool):
            raise TypeError("enrich_missing_outcomes must be a boolean")
        delay = float(self.enrichment_delay_seconds)
        if delay < 0:
            raise ValueError("enrichment_delay_seconds must be nonnegative")
        object.__setattr__(self, "enrichment_delay_seconds", delay)
        created_at = self.created_at_utc
        if not isinstance(created_at, datetime) or created_at.tzinfo is None:
            raise ValueError("created_at_utc must be timezone-aware")
        object.__setattr__(self, "created_at_utc", created_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class DatasetBuildResult:
    dataset_path: Path
    metadata_path: Path
    metadata: DatasetMetadata
    source_file_count: int
    source_line_count: int
    malformed_source_record_count: int
    observed_outcome_count: int
    enriched_outcome_count: int


@dataclass(frozen=True, slots=True)
class DatasetInspection:
    metadata: DatasetMetadata
    validation: DatasetValidationResult
    metadata_issues: tuple[str, ...]

    @property
    def ready_for_replay(self) -> bool:
        return (
            not self.metadata_issues
            and self.metadata.ready_for_replay
            and self.validation.ready_for_replay
        )


def discover_observer_data(
    root: str | Path = DEFAULT_OBSERVER_ROOT,
    *,
    pattern: str = DEFAULT_OBSERVER_PATTERN,
) -> tuple[Path, ...]:
    """Discover observer JSONL sources in deterministic path order."""

    source_root = Path(root)
    if not source_root.exists():
        return ()
    return tuple(
        sorted(
            path
            for path in source_root.rglob(pattern)
            if path.is_file()
        )
    )


def build_replay_dataset(
    configuration: DatasetBuildConfiguration,
) -> DatasetBuildResult:
    """Rebuild a validated replay index using existing historical semantics."""

    if not isinstance(configuration, DatasetBuildConfiguration):
        raise TypeError("configuration must be DatasetBuildConfiguration")
    source_paths = configuration.observer_paths or discover_observer_data(
        configuration.observer_root,
        pattern=configuration.observer_pattern,
    )
    if not source_paths:
        raise ValueError("no observer data files were discovered")

    read_result = read_observer_files(source_paths)
    if read_result.malformed_records:
        first = read_result.malformed_records[0]
        raise ValueError(
            "observer data is malformed at "
            f"{first.source_file}:{first.source_line_number}: "
            f"{first.error_type}: {first.error_message}"
        )
    assembled = assemble_rounds(read_result.snapshots)
    rounds = list(assembled.rounds)
    observed_outcome_count = sum(
        lifecycle.finalized_outcome_source == "observed"
        for lifecycle in rounds
    )
    if (
        configuration.enrich_missing_outcomes
        and any(lifecycle.finalized_outcome is None for lifecycle in rounds)
    ):
        rpc = SolanaRpcClient()
        try:
            rounds, _ = enrich_rounds(
                rpc=rpc,
                lifecycles=rounds,
                limit=None,
                delay_seconds=configuration.enrichment_delay_seconds,
            )
        finally:
            rpc.close()
    records = sorted(
        (lifecycle_to_index_record(lifecycle) for lifecycle in rounds),
        key=lambda record: (record.start_slot, record.round_id),
    )
    output_path = configuration.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=output_path.name + ".",
        suffix=".validation.jsonl",
        dir=output_path.parent,
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        write_round_index(records, temporary_path)
        validation = validate_replay_dataset(temporary_path)
        os.replace(temporary_path, output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    metadata = DatasetMetadata(
        dataset_version=configuration.dataset_version,
        created_at_utc=configuration.created_at_utc,
        source_collection=tuple(str(path) for path in source_paths),
        replay_round_count=validation.replay_round_count,
        snapshot_count=validation.snapshot_count,
        complete_round_count=validation.complete_round_count,
        incomplete_round_count=validation.incomplete_round_count,
        missing_outcome_count=validation.missing_outcome_count,
        integrity_status="valid",
        ready_for_replay=validation.ready_for_replay,
        dataset_sha256=dataset_sha256(output_path),
    )
    metadata_path = write_metadata(metadata, configuration.metadata_path)
    return DatasetBuildResult(
        dataset_path=output_path,
        metadata_path=metadata_path,
        metadata=metadata,
        source_file_count=read_result.files_read,
        source_line_count=read_result.lines_read,
        malformed_source_record_count=len(read_result.malformed_records),
        observed_outcome_count=observed_outcome_count,
        enriched_outcome_count=sum(
            lifecycle.finalized_outcome_source == "enriched"
            for lifecycle in rounds
        ),
    )


def inspect_replay_dataset(
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
) -> DatasetInspection:
    """Read metadata and independently validate its referenced dataset."""

    dataset = Path(dataset_path)
    metadata = load_metadata(metadata_path)
    validation = validate_replay_dataset(dataset, fail_closed=False)
    issues: list[str] = []
    if dataset_sha256(dataset) != metadata.dataset_sha256:
        issues.append("dataset SHA-256 does not match metadata")
    expected = {
        "replay_round_count": validation.replay_round_count,
        "snapshot_count": validation.snapshot_count,
        "complete_round_count": validation.complete_round_count,
        "incomplete_round_count": validation.incomplete_round_count,
        "missing_outcome_count": validation.missing_outcome_count,
        "ready_for_replay": validation.ready_for_replay,
    }
    for field_name, value in expected.items():
        if getattr(metadata, field_name) != value:
            issues.append(f"metadata {field_name} does not match dataset")
    return DatasetInspection(
        metadata=metadata,
        validation=validation,
        metadata_issues=tuple(issues),
    )


__all__ = (
    "DEFAULT_DATASET_PATH",
    "DEFAULT_DATASET_VERSION",
    "DEFAULT_METADATA_PATH",
    "DEFAULT_OBSERVER_PATTERN",
    "DEFAULT_OBSERVER_ROOT",
    "DatasetBuildConfiguration",
    "DatasetBuildResult",
    "DatasetInspection",
    "build_replay_dataset",
    "discover_observer_data",
    "inspect_replay_dataset",
)
