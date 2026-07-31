from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from orev3.data.models import (
    BoardState,
    ObserverSnapshot,
    RoundState,
    TreasuryState,
)
from orev3.data.writer import JsonlSnapshotWriter


def test_finalized_snapshot_is_persisted_durably(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fsync_calls: list[int] = []
    monkeypatch.setattr(
        "orev3.data.writer.os.fsync",
        fsync_calls.append,
    )

    writer = JsonlSnapshotWriter(tmp_path)
    snapshot = _snapshot(41, finalized=True)

    path = writer.write(snapshot)

    assert _read_rounds(path) == [41]
    assert len(fsync_calls) == 2
    assert (
        json.loads(
            path.read_text(encoding="utf-8")
        )["round"]
        == snapshot.model_dump(mode="json")["round"]
    )


def test_successor_append_preserves_finalized_snapshot(
    tmp_path: Path,
) -> None:
    writer = JsonlSnapshotWriter(tmp_path)

    path = writer.write(
        _snapshot(41, finalized=True)
    )
    finalized_bytes = path.read_bytes()

    writer.write(
        _snapshot(42, finalized=False)
    )

    assert path.read_bytes().startswith(
        finalized_bytes
    )
    assert _read_rounds(path) == [41, 42]


def test_duplicate_finalized_snapshot_is_not_written(
    tmp_path: Path,
) -> None:
    writer = JsonlSnapshotWriter(tmp_path)
    first = _snapshot(41, finalized=True)
    duplicate = _snapshot(
        41,
        finalized=True,
        rpc_slot=999,
    )

    path = writer.write(first)
    first_bytes = path.read_bytes()
    writer.write(duplicate)

    assert path.read_bytes() == first_bytes
    assert _read_rounds(path) == [41]


def test_restart_reconstructs_finalized_deduplication(
    tmp_path: Path,
) -> None:
    first_writer = JsonlSnapshotWriter(tmp_path)
    path = first_writer.write(
        _snapshot(41, finalized=True)
    )
    first_bytes = path.read_bytes()

    restarted_writer = JsonlSnapshotWriter(
        tmp_path
    )
    restarted_writer.write(
        _snapshot(
            41,
            finalized=True,
            rpc_slot=999,
        )
    )

    assert path.read_bytes() == first_bytes

    restarted_writer.write(
        _snapshot(42, finalized=False)
    )

    assert _read_rounds(path) == [41, 42]


def _read_rounds(path: Path) -> list[int]:
    return [
        int(json.loads(line)["round"]["round_id"])
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]


def _snapshot(
    round_id: int,
    *,
    finalized: bool,
    rpc_slot: int | None = None,
) -> ObserverSnapshot:
    return ObserverSnapshot(
        collector_session_id="test-session",
        observed_at_utc=datetime(
            2026,
            7,
            30,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        rpc_slot=(
            rpc_slot
            if rpc_slot is not None
            else round_id * 10
        ),
        board=BoardState(
            round_id=round_id,
            start_slot=round_id * 10,
            end_slot=round_id * 10 + 9,
        ),
        treasury=TreasuryState(
            motherlode=100,
        ),
        round=RoundState(
            round_id=round_id,
            deployed_lamports=list(range(25)),
            mass=[0] * 25,
            miner_counts=[1] * 25,
            slot_hash_hex=(
                "01" * 32
                if finalized
                else "00" * 32
            ),
            expires_at=round_id * 10 + 9,
            motherlode=100,
            rewards=(
                [10] + [0] * 24
                if finalized
                else [0] * 25
            ),
            total_vaulted=(
                1000 if finalized else 0
            ),
            total_winnings=(
                100 if finalized else 0
            ),
            total_miners=(
                25 if finalized else 0
            ),
            top_miner="test-miner",
            entropy=(
                round_id if finalized else None
            ),
        ),
    )
