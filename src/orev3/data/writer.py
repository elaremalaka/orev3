from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from orev3.data.models import ObserverSnapshot


class JsonlSnapshotWriter:
    """
    Append-only JSONL writer for immutable Observer snapshots.

    Files are rotated by UTC date:

        data/raw/observer_YYYY-MM-DD.jsonl
    """

    def __init__(
        self,
        output_dir: str | Path = "data/raw",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
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

        line = snapshot.model_dump_json()

        with path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(line)
            file.write("\n")

        return path
