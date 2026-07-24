from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from orev3.historical.models import (
    NormalizedSnapshot,
    RoundLifecycleIndexRecord,
)
from orev3.historical.reader import (
    normalize_snapshot,
)


def load_round_index(
    path: str | Path,
) -> dict[
    int,
    RoundLifecycleIndexRecord,
]:
    """
    Load the persistent historical round index.

    Returns records keyed by round_id.
    """

    index_path = Path(path)

    rounds: dict[
        int,
        RoundLifecycleIndexRecord,
    ] = {}

    with index_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line_number, line in enumerate(
            handle,
            start=1,
        ):
            raw = json.loads(
                line
            )

            record = (
                RoundLifecycleIndexRecord
                .model_validate(
                    raw
                )
            )

            if record.round_id in rounds:
                raise ValueError(
                    "Duplicate round_id "
                    f"{record.round_id} "
                    f"in {index_path} "
                    f"at line {line_number}"
                )

            rounds[
                record.round_id
            ] = record

    return rounds


@lru_cache(
    maxsize=None,
)
def _load_source_lines(
    source_file: str,
) -> tuple[str, ...]:
    """
    Read one snapshot JSONL file once per process.
    """

    path = Path(
        source_file
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return tuple(
            handle
        )


def load_snapshot_reference(
    source_file: str,
    source_line_number: int,
) -> NormalizedSnapshot:
    """
    Resolve one raw snapshot reference.

    JSONL line numbers are 1-based.
    """

    path = Path(
        source_file
    )

    if source_line_number < 1:
        raise ValueError(
            "source_line_number must be >= 1"
        )

    lines = _load_source_lines(
        source_file
    )

    zero_based_index = (
        source_line_number - 1
    )

    if zero_based_index >= len(
        lines
    ):
        raise ValueError(
            f"Snapshot reference not found: "
            f"{source_file}:"
            f"{source_line_number}"
        )

    raw = json.loads(
        lines[
            zero_based_index
        ]
    )

    return normalize_snapshot(
        raw=raw,
        source_file=path,
        source_line_number=(
            source_line_number
        ),
    )


def load_round_observations(
    lifecycle: RoundLifecycleIndexRecord,
) -> list[
    NormalizedSnapshot
]:
    """
    Resolve all raw observations referenced by one
    persistent round lifecycle record.
    """

    snapshots = [
        load_snapshot_reference(
            source_file=(
                reference.source_file
            ),
            source_line_number=(
                reference.source_line_number
            ),
        )
        for reference
        in lifecycle.observation_references
    ]

    snapshots.sort(
        key=lambda snapshot: (
            snapshot.observed_at_utc,
            snapshot.source_file,
            snapshot.source_line_number,
        )
    )

    return snapshots
