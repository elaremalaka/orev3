from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from orev3.historical.models import (
    MalformedRecord,
    NormalizedSnapshot,
    SnapshotReadResult,
)


SUPPORTED_SCHEMA_VERSIONS = {
    1,
    2,
}


def normalize_snapshot(
    raw: dict[str, Any],
    source_file: Path,
    source_line_number: int,
) -> NormalizedSnapshot:
    """
    Normalize one raw Observer record into the
    schema-independent historical representation.

    Raw source data is never modified.
    """

    schema_version = int(
        raw.get(
            "schema_version",
            1,
        )
    )

    if (
        schema_version
        not in SUPPORTED_SCHEMA_VERSIONS
    ):
        raise ValueError(
            "Unsupported Observer "
            f"schema_version={schema_version}"
        )

    collector_session_id = (
        raw.get("collector_session_id")
        if schema_version >= 2
        else None
    )

    return NormalizedSnapshot(
        source_schema_version=schema_version,
        collector_session_id=collector_session_id,
        observed_at_utc=raw["observed_at_utc"],
        rpc_slot=raw["rpc_slot"],
        board=raw["board"],
        treasury=raw["treasury"],
        round=raw["round"],
        source_file=str(source_file),
        source_line_number=source_line_number,
    )


def read_observer_file(
    path: str | Path,
) -> SnapshotReadResult:
    """
    Read and normalize one Observer JSONL file.

    Malformed or unsupported records are reported
    rather than causing the entire read to fail.
    """

    source_path = Path(path)

    snapshots: list[
        NormalizedSnapshot
    ] = []

    malformed_records: list[
        MalformedRecord
    ] = []

    lines_read = 0

    with source_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            lines_read += 1

            try:
                raw = json.loads(
                    line
                )

                snapshot = normalize_snapshot(
                    raw=raw,
                    source_file=source_path,
                    source_line_number=line_number,
                )

                snapshots.append(
                    snapshot
                )

            except (
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
                ValidationError,
            ) as exc:
                malformed_records.append(
                    MalformedRecord(
                        source_file=str(
                            source_path
                        ),
                        source_line_number=(
                            line_number
                        ),
                        error_type=(
                            type(exc).__name__
                        ),
                        error_message=str(
                            exc
                        ),
                    )
                )

    return SnapshotReadResult(
        snapshots=snapshots,
        malformed_records=(
            malformed_records
        ),
        files_read=1,
        lines_read=lines_read,
    )


def read_observer_files(
    paths: Iterable[str | Path],
) -> SnapshotReadResult:
    """
    Read multiple Observer JSONL files into one
    normalized historical snapshot collection.

    Input files are processed in sorted path order.
    """

    snapshots: list[
        NormalizedSnapshot
    ] = []

    malformed_records: list[
        MalformedRecord
    ] = []

    files_read = 0
    lines_read = 0

    sorted_paths = sorted(
        Path(path)
        for path in paths
    )

    for path in sorted_paths:
        result = read_observer_file(
            path
        )

        snapshots.extend(
            result.snapshots
        )

        malformed_records.extend(
            result.malformed_records
        )

        files_read += (
            result.files_read
        )

        lines_read += (
            result.lines_read
        )

    snapshots.sort(
        key=lambda snapshot: (
            snapshot.observed_at_utc,
            snapshot.source_file,
            snapshot.source_line_number,
        )
    )

    return SnapshotReadResult(
        snapshots=snapshots,
        malformed_records=(
            malformed_records
        ),
        files_read=files_read,
        lines_read=lines_read,
    )
