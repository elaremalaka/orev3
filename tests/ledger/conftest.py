from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


WALLET = "11111111111111111111111111111111"
SIGNATURE = "1" * 64
NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def snapshot() -> dict:
    return {
        "schema_version": 2,
        "collector_session_id": "session-1",
        "observed_at_utc": "2026-07-25T12:00:00Z",
        "rpc_slot": 100,
        "board": {
            "round_id": 42,
            "start_slot": 90,
            "end_slot": 120,
            "production_cost_ema": 1,
        },
        "treasury": {"motherlode": 10},
        "round": {
            "round_id": 42,
            "deployed_lamports": [0] * 25,
            "mass": [0] * 25,
            "miner_counts": [0] * 25,
            "slot_hash_hex": "00",
            "expires_at": 120,
            "motherlode": 0,
            "rewards": [0] * 25,
            "total_vaulted": 0,
            "total_winnings": 0,
            "total_miners": 0,
            "top_miner": WALLET,
            "entropy": None,
        },
    }


@pytest.fixture
def snapshot_file(tmp_path: Path, snapshot: dict) -> Path:
    path = tmp_path / "observer.jsonl"
    path.write_text(json.dumps(snapshot) + "\n", encoding="utf-8")
    return path
