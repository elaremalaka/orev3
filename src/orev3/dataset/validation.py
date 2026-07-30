"""Fail-closed validation for managed historical replay datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from pydantic import ValidationError

from orev3.historical.assembler import U64_MAX
from orev3.historical.models import NormalizedSnapshot, RoundLifecycleIndexRecord
from orev3.historical.reader import normalize_snapshot


@dataclass(frozen=True, slots=True)
class DatasetValidationIssue:
    code: str
    message: str
    line_number: int | None = None
    round_identifier: int | None = None


@dataclass(frozen=True, slots=True)
class DatasetValidationResult:
    dataset_path: Path
    replay_round_count: int
    snapshot_count: int
    complete_round_count: int
    incomplete_round_count: int
    missing_outcome_count: int
    first_round_identifier: int | None
    last_round_identifier: int | None
    first_observed_at_utc: str | None
    last_observed_at_utc: str | None
    issues: tuple[DatasetValidationIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.issues

    @property
    def integrity_valid(self) -> bool:
        readiness_codes = {
            "incomplete_round",
            "missing_finalized_outcome",
        }
        return not any(issue.code not in readiness_codes for issue in self.issues)

    @property
    def ready_for_replay(self) -> bool:
        return (
            self.integrity_valid
            and self.replay_round_count > 0
            and self.incomplete_round_count == 0
            and self.missing_outcome_count == 0
        )


class DatasetValidationError(ValueError):
    def __init__(self, result: DatasetValidationResult) -> None:
        self.result = result
        summary = "; ".join(
            f"{issue.code}: {issue.message}" for issue in result.issues
        )
        super().__init__(summary or "replay dataset validation failed")


def validate_replay_dataset(
    path: str | Path,
    *,
    fail_closed: bool = True,
) -> DatasetValidationResult:
    """Validate dataset structure, observations, chronology, and replay facts."""

    dataset_path = Path(path)
    records, parse_issues = _read_records(dataset_path)
    issues = list(parse_issues)
    seen_rounds: set[int] = set()
    previous_key: tuple[int, int] | None = None
    previous_observed_at = None
    snapshot_count = 0
    complete_round_count = 0
    missing_outcome_count = 0
    source_reader = _ObservationSourceReader()

    for line_number, record in records:
        if record.round_id in seen_rounds:
            issues.append(
                DatasetValidationIssue(
                    "duplicate_round",
                    f"round {record.round_id} appears more than once",
                    line_number,
                    record.round_id,
                )
            )
        seen_rounds.add(record.round_id)
        key = (record.start_slot, record.round_id)
        if previous_key is not None and key <= previous_key:
            issues.append(
                DatasetValidationIssue(
                    "chronological_order",
                    "round records are not in strict chronological order",
                    line_number,
                    record.round_id,
                )
            )
        previous_key = key
        if (
            previous_observed_at is not None
            and record.first_observed_at_utc < previous_observed_at
        ):
            issues.append(
                DatasetValidationIssue(
                    "chronological_order",
                    "round observation times regress",
                    line_number,
                    record.round_id,
                )
            )
        previous_observed_at = record.first_observed_at_utc
        snapshot_count += record.observation_count
        if record.quality.coverage_status == "complete":
            complete_round_count += 1
        else:
            issues.append(
                DatasetValidationIssue(
                    "incomplete_round",
                    f"coverage is {record.quality.coverage_status}",
                    line_number,
                    record.round_id,
                )
            )
        if record.finalized_outcome is None:
            missing_outcome_count += 1
            issues.append(
                DatasetValidationIssue(
                    "missing_finalized_outcome",
                    "round has no finalized historical outcome",
                    line_number,
                    record.round_id,
                )
            )
        _validate_record(record, line_number, issues, source_reader)

    source_reader.close()

    ordered_records = tuple(record for _, record in records)
    result = DatasetValidationResult(
        dataset_path=dataset_path,
        replay_round_count=len(records),
        snapshot_count=snapshot_count,
        complete_round_count=complete_round_count,
        incomplete_round_count=len(records) - complete_round_count,
        missing_outcome_count=missing_outcome_count,
        first_round_identifier=(
            ordered_records[0].round_id if ordered_records else None
        ),
        last_round_identifier=(
            ordered_records[-1].round_id if ordered_records else None
        ),
        first_observed_at_utc=(
            ordered_records[0].first_observed_at_utc.isoformat()
            if ordered_records
            else None
        ),
        last_observed_at_utc=(
            ordered_records[-1].last_observed_at_utc.isoformat()
            if ordered_records
            else None
        ),
        issues=tuple(issues),
    )
    if fail_closed and not result.valid:
        raise DatasetValidationError(result)
    return result


def _read_records(
    path: Path,
) -> tuple[
    list[tuple[int, RoundLifecycleIndexRecord]],
    tuple[DatasetValidationIssue, ...],
]:
    records: list[tuple[int, RoundLifecycleIndexRecord]] = []
    issues: list[DatasetValidationIssue] = []
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        result = DatasetValidationResult(
            path,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            None,
            None,
            (DatasetValidationIssue("dataset_unreadable", str(exc)),),
        )
        raise DatasetValidationError(result) from exc
    with handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                raw = json.loads(line)
                record = RoundLifecycleIndexRecord.model_validate(raw)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                issues.append(
                    DatasetValidationIssue(
                        "corrupted_record",
                        str(exc),
                        line_number,
                    )
                )
                continue
            records.append((line_number, record))
    if not records and not issues:
        issues.append(
            DatasetValidationIssue(
                "empty_dataset",
                "dataset contains no replay rounds",
            )
        )
    return records, tuple(issues)


def _validate_record(
    record: RoundLifecycleIndexRecord,
    line_number: int,
    issues: list[DatasetValidationIssue],
    source_reader: _ObservationSourceReader,
) -> None:
    def issue(code: str, message: str) -> None:
        issues.append(
            DatasetValidationIssue(
                code,
                message,
                line_number,
                record.round_id,
            )
        )

    if record.first_observed_at_utc > record.last_observed_at_utc:
        issue("chronological_observations", "first observation follows last")
    if record.first_observed_rpc_slot > record.last_observed_rpc_slot:
        issue("rpc_slot_order", "first RPC slot exceeds last RPC slot")
    if record.observation_count != len(record.observation_references):
        issue(
            "snapshot_count_mismatch",
            "observation_count does not match observation references",
        )
    reference_keys = tuple(
        (reference.source_file, reference.source_line_number)
        for reference in record.observation_references
    )
    if len(set(reference_keys)) != len(reference_keys):
        issue(
            "duplicate_observation_reference",
            "an observation reference appears more than once",
        )
    reference_order = tuple(
        (
            reference.observed_at_utc,
            reference.source_file,
            reference.source_line_number,
        )
        for reference in record.observation_references
    )
    if reference_order != tuple(sorted(reference_order)):
        issue(
            "observation_order",
            "observation references are not in chronological order",
        )
    if set(record.source_files) != {
        reference.source_file for reference in record.observation_references
    }:
        issue(
            "source_collection_mismatch",
            "lifecycle source files do not match observation references",
        )
    try:
        snapshots = [
            source_reader.load(
                reference.source_file,
                reference.source_line_number,
            )
            for reference in record.observation_references
        ]
        snapshots.sort(
            key=lambda snapshot: (
                snapshot.observed_at_utc,
                snapshot.source_file,
                snapshot.source_line_number,
            )
        )
    except Exception as exc:
        issue("corrupted_observation", str(exc))
        return
    if len(snapshots) != record.observation_count:
        issue(
            "snapshot_count_mismatch",
            "resolved observation count does not match lifecycle count",
        )
    if not snapshots:
        issue("missing_observations", "round has no replay observations")
        return
    if any(snapshot.board.round_id != record.round_id for snapshot in snapshots):
        issue(
            "round_reference_mismatch",
            "an observation belongs to a different round",
        )
    if any(
        snapshot.board.end_slot != U64_MAX
        and snapshot.board.start_slot != record.start_slot
        for snapshot in snapshots
    ):
        issue(
            "round_start_mismatch",
            "an initialized observation has a different round start slot",
        )
    for reference, snapshot in zip(record.observation_references, snapshots):
        if (
            reference.observed_at_utc != snapshot.observed_at_utc
            or reference.rpc_slot != snapshot.rpc_slot
        ):
            issue(
                "observation_reference_mismatch",
                "reference facts do not match the source observation",
            )
            break
    first = snapshots[0]
    last = snapshots[-1]
    if (
        first.observed_at_utc != record.first_observed_at_utc
        or last.observed_at_utc != record.last_observed_at_utc
        or first.rpc_slot != record.first_observed_rpc_slot
        or last.rpc_slot != record.last_observed_rpc_slot
    ):
        issue(
            "lifecycle_boundary_mismatch",
            "lifecycle boundaries do not match resolved observations",
        )
    outcome = record.finalized_outcome
    if (outcome is None) != (record.finalized_outcome_source is None):
        issue(
            "finalized_outcome_source_mismatch",
            "outcome and outcome source presence are inconsistent",
        )
    if (
        outcome is not None
        and outcome.entropy is not None
        and outcome.winning_square != outcome.entropy % 25
    ):
        issue(
            "finalized_outcome_mismatch",
            "winning square is inconsistent with finalized entropy",
        )


class _ObservationSourceReader:
    """Resolve references using one binary offset scan per observer file."""

    def __init__(self) -> None:
        self._handles: dict[Path, BinaryIO] = {}
        self._offsets: dict[Path, tuple[int, ...]] = {}

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()
        self._offsets.clear()

    def load(self, source_file: str, line_number: int) -> NormalizedSnapshot:
        if line_number < 1:
            raise ValueError("source_line_number must be >= 1")
        path = Path(source_file)
        if path not in self._handles:
            handle = path.open("rb")
            offsets: list[int] = []
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                offsets.append(offset)
            self._handles[path] = handle
            self._offsets[path] = tuple(offsets)
        offsets = self._offsets[path]
        if line_number > len(offsets):
            raise ValueError(
                f"snapshot reference not found: {source_file}:{line_number}"
            )
        handle = self._handles[path]
        handle.seek(offsets[line_number - 1])
        raw = json.loads(handle.readline())
        return normalize_snapshot(
            raw=raw,
            source_file=path,
            source_line_number=line_number,
        )


__all__ = (
    "DatasetValidationError",
    "DatasetValidationIssue",
    "DatasetValidationResult",
    "validate_replay_dataset",
)
