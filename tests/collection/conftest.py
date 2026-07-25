from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orev3.collection.config import CollectionConfig


NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def snapshot(
    *,
    round_id: int = 42,
    observed_index: int = 0,
    miners: list[int] | None = None,
    deployed: list[int] | None = None,
) -> dict:
    return {
        "schema_version": 2,
        "collector_session_id": "fixture-session",
        "observed_at_utc": (
            f"2026-07-25T12:{observed_index // 60:02d}:"
            f"{observed_index % 60:02d}+00:00"
        ),
        "rpc_slot": 100 + observed_index,
        "board": {
            "round_id": round_id,
            "start_slot": 90,
            "end_slot": 200,
            "production_cost_ema": 1,
        },
        "treasury": {"motherlode": 0},
        "round": {
            "round_id": round_id,
            "deployed_lamports": deployed or list(range(25)),
            "mass": [0] * 25,
            "miner_counts": miners or list(range(25)),
            "slot_hash_hex": "00" * 32,
            "expires_at": 200,
            "motherlode": 0,
            "rewards": list(range(25)),
            "total_vaulted": 0,
            "total_winnings": 0,
            "total_miners": 300,
            "top_miner": "11111111111111111111111111111111",
            "entropy": None,
        },
    }


def lifecycle(round_id: int = 42, winner: int = 0) -> dict:
    return {
        "lifecycle_schema_version": 1,
        "round_id": round_id,
        "finalized_outcome_source": "observed",
        "finalized_outcome": {
            "observed_at_utc": "2026-07-25T12:10:00+00:00",
            "rpc_slot": 300,
            "entropy": 0,
            "winning_square": winner,
            "deployed_lamports": [100_000] * 25,
            "miner_counts": [1] * 25,
            "reward_buckets": [0] * 25,
            "total_vaulted": 1_000_000,
            "total_winnings": 2_000_000,
            "total_miners": 25,
            "round_motherlode": 0,
            "top_miner": "11111111111111111111111111111111",
        },
    }


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    path = tmp_path / "observer.jsonl"
    path.write_text(
        json.dumps(snapshot()) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def outcome_file(tmp_path: Path) -> Path:
    path = tmp_path / "outcomes.jsonl"
    path.write_text(
        json.dumps(lifecycle()) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def config(outcome_file: Path) -> CollectionConfig:
    return CollectionConfig(
        collector_version="rfc007-test",
        source_glob="unused",
        outcome_source=str(outcome_file),
        poll_interval_seconds=0.01,
        batch_size=25,
        strategy_id="existing_least_crowded",
        strategy_version="1.0.0",
        square_count=4,
        allocation_rule="equal",
        deployment_total_lamports=50_000,
        random_seed=20_260_725,
        assumed_deploy_fee_lamports=5_000,
        assumed_claim_fee_lamports=5_000,
        retain_verbose_payloads=False,
        busy_timeout_ms=1_000,
        checkpoint_every_records=10,
        live_start_mode="end",
        chronological_blocks=[
            {
                "block_id": f"block_{index + 1}",
                "start_index": index * 250,
                "end_index": index * 250 + 249,
                "target_opportunities": 250,
                "report_only": index == 3,
            }
            for index in range(4)
        ],
    )
