from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from orev3.data.models import (
    ObserverSnapshot,
    RoundState,
)


ZERO_SLOT_HASH = "00" * 32
UNINITIALIZED_SLOT_HASH = "ff" * 32


def is_finalized_round(
    round_state: RoundState,
) -> bool:
    """
    Return whether decoded protocol state reports finalization.

    This matches the explicit finalized-state indicators used by
    historical lifecycle assembly. It does not derive or reinterpret
    any outcome field.
    """

    slot_hash = round_state.slot_hash_hex.lower()

    return (
        slot_hash
        not in {
            ZERO_SLOT_HASH,
            UNINITIALIZED_SLOT_HASH,
        }
        or round_state.entropy is not None
        or round_state.total_vaulted > 0
        or round_state.total_winnings > 0
    )


def append_json_line(
    path: Path,
    payload: dict[str, Any] | str,
    *,
    durable: bool = False,
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

    path_existed = path.exists()

    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_APPEND,
        0o600,
    )

    try:
        written = os.write(
            fd,
            data,
        )

        if written != len(data):
            raise OSError(
                "Incomplete JSONL append: "
                f"wrote {written} of "
                f"{len(data)} bytes."
            )

        if durable:
            os.fsync(fd)
    finally:
        os.close(fd)

    if durable and not path_existed:
        directory_fd = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


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
        self._finalized_round_ids: set[int] = set()
        self._checked_round_ids: set[int] = set()

    def _finalized_round_exists(
        self,
        round_id: int,
    ) -> bool:
        if round_id in self._finalized_round_ids:
            return True

        if round_id in self._checked_round_ids:
            return False

        self._checked_round_ids.add(round_id)

        if not self.output_dir.exists():
            return False

        for path in sorted(
            self.output_dir.glob(
                "observer_*.jsonl"
            ),
            reverse=True,
        ):
            with path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                for line_number, line in enumerate(
                    handle,
                    start=1,
                ):
                    if not line.strip():
                        continue

                    try:
                        payload = json.loads(line)
                    except Exception as exc:
                        raise ValueError(
                            "Cannot establish finalized "
                            "snapshot identity from "
                            f"{path}:{line_number}."
                        ) from exc

                    round_payload = payload.get(
                        "round"
                    )
                    if not isinstance(
                        round_payload,
                        dict,
                    ):
                        raise ValueError(
                            "Cannot establish finalized "
                            "snapshot identity from "
                            f"{path}:{line_number}."
                        )

                    if (
                        round_payload.get(
                            "round_id"
                        )
                        != round_id
                    ):
                        continue

                    try:
                        round_state = (
                            RoundState.model_validate(
                                round_payload
                            )
                        )
                    except Exception as exc:
                        raise ValueError(
                            "Cannot establish finalized "
                            "snapshot identity from "
                            f"{path}:{line_number}."
                        ) from exc

                    if is_finalized_round(
                        round_state
                    ):
                        self._finalized_round_ids.add(
                            round_id
                        )
                        return True

        return False

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

        finalized = is_finalized_round(
            snapshot.round
        )

        if finalized:
            if self._finalized_round_exists(
                snapshot.round.round_id
            ):
                return path

        append_json_line(
            path,
            snapshot.model_dump_json(),
            durable=finalized,
        )

        if finalized:
            self._finalized_round_ids.add(
                snapshot.round.round_id
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
