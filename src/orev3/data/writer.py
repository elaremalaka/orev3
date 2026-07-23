from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from orev3.data.models import ObserverSnapshot


def append_json_line(
    path: Path,
    payload: dict[str, Any] | str,
) -> None:
    """
    Append exactly one complete JSON line.

    Uses O_APPEND and a single os.write call to reduce the
    chance of partial/interleaved writes.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if isinstance(payload, str):
        line = payload
    else:
        line = json.dumps(
            payload,
            separators=(",", ":"),
            default=str,
        )

    data = (
        line.rstrip("\n") + "\n"
    ).encode("utf-8")

    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_APPEND,
        0o600,
    )

    try:
        os.write(
            fd,
            data,
        )
    finally:
        os.close(fd)


class JsonlSnapshotWriter:
    """
    Append-only JSONL writer for immutable Observer snapshots.

    Files rotate by UTC date.
    """

    def __init__(
        self,
        output_dir: str | Path = "data/raw",
    ) -> None:
        self.output_dir = Path(
            output_dir
        )

    def _path_for_snapshot(
        self,
        snapshot: ObserverSnapshot,
    ) -> Path:
        observed_at = (
            snapshot.observed_at_utc
        )

        if observed_at.tzinfo is None:
            raise ValueError(
                "Snapshot timestamp must "
                "include timezone information."
            )

        date_string = (
            observed_at
            .astimezone(timezone.utc)
            .strftime("%Y-%m-%d")
        )

        return (
            self.output_dir
            / f"observer_{date_string}.jsonl"
        )

    def write(
        self,
        snapshot: ObserverSnapshot,
    ) -> Path:
        path = self._path_for_snapshot(
            snapshot
        )

        append_json_line(
            path,
            snapshot.model_dump_json(),
        )

        return path


class CollectorEventWriter:
    """
    Structured local collector event log.

    These logs are operational metadata and remain
    outside the raw protocol dataset.
    """

    def __init__(
        self,
        output_dir: str | Path = "logs",
    ) -> None:
        self.output_dir = Path(
            output_dir
        )

    def write(
        self,
        event: dict[str, Any],
    ) -> Path:
        now = datetime.now(
            timezone.utc
        )

        date_string = now.strftime(
            "%Y-%m-%d"
        )

        path = (
            self.output_dir
            / f"collector_events_{date_string}.jsonl"
        )

        append_json_line(
            path,
            event,
        )

        return path
