from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orev3.collection.schemas import TailRecord
from orev3.rfc008.cli import parser
from orev3.rfc008.collector import RFC008Collector
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.marker import (
    _atomic_marker_pair,
    sha256_file,
    verify_marker,
)
from orev3.rfc008.schemas import ExperimentMarker
from orev3.rfc008.status import status_report


ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config/collection/rfc008_paper_v1.json"
APPROVAL = ROOT / "docs/research/rfc008/approval_manifest_v1.json"


def raw_record(
    round_id: int,
    line: int,
    *,
    slots_remaining: int = 75,
) -> TailRecord:
    rpc_slot = 1000
    end_slot = rpc_slot + slots_remaining
    raw = {
        "observed_at_utc": "2026-07-25T00:00:00Z",
        "rpc_slot": rpc_slot,
        "board": {
            "round_id": round_id,
            "start_slot": 900,
            "end_slot": end_slot,
        },
        "round": {
            "round_id": round_id,
            "miner_counts": [2] * 25,
            "deployed_lamports": [100] * 25,
            "rewards": [0] * 25,
            "slot_hash_hex": "00" * 32,
            "total_vaulted": 0,
            "total_winnings": 0,
        },
        "treasury": {"motherlode": 0},
    }
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    return TailRecord(
        source_id="source",
        source_path="observer.jsonl",
        source_line_number=line,
        start_offset=line - 1,
        end_offset=line,
        record_id=f"record-{line}",
        content_sha256=digest,
        observed_at=datetime(2026, 7, 25, 0, 0, line, tzinfo=timezone.utc),
        raw=raw,
    )


def test_atomic_marker_pair_publishes_both_or_neither(
    tmp_path: Path, config: RFC008Config, marker_file
) -> None:
    source, _ = marker_file
    value = ExperimentMarker.model_validate_json(source.read_text())
    marker = tmp_path / "marker.json"
    _atomic_marker_pair(value, marker)
    assert Path(str(marker) + ".sha256").exists()
    assert verify_marker(marker, config, expected_sha256=sha256_file(marker))
    failed = tmp_path / "failed.json"
    with pytest.raises(RuntimeError):
        _atomic_marker_pair(
            value,
            failed,
            failure_injector=lambda point: (
                (_ for _ in ()).throw(RuntimeError(point))
                if point == "between_sidecar_and_marker"
                else None
            ),
        )
    assert not failed.exists()
    assert not Path(str(failed) + ".sha256").exists()


def test_marker_and_configuration_mismatch_refuse(marker_file, config) -> None:
    path, digest = marker_file
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_marker(path, config, expected_sha256="0" * 64)
    raw = config.model_dump(mode="json")
    raw["poll_interval_seconds"] = 3
    with pytest.raises(ValueError, match="configuration mismatch"):
        verify_marker(path, RFC008Config.model_validate(raw), expected_sha256=digest)


def test_collector_uses_one_snapshot_and_durable_transition_queue(
    store, config, marker_file
) -> None:
    value, _ = store
    marker, digest = marker_file
    collector = RFC008Collector(
        store=value,
        config=config,
        marker_path=marker,
        expected_marker_sha256=digest,
    )
    with value.connection:
        collector.process_record(raw_record(346000, 1))
        collector.process_record(raw_record(346000, 1))
        collector.process_record(raw_record(346001, 2))
    assert value.count("decision_snapshots") == 2
    assert value.count("arm_decisions") == 10
    assert value.queue(346000).state == "pending"
    assert value.counters()["duplicate_source_records"] == 1
    assert value.count("finalized_outcomes") == 0


def test_late_first_snapshot_is_excluded_on_transition(
    store, config, marker_file
) -> None:
    value, _ = store
    marker, digest = marker_file
    collector = RFC008Collector(
        store=value,
        config=config,
        marker_path=marker,
        expected_marker_sha256=digest,
    )
    with value.connection:
        collector.process_record(raw_record(346010, 10, slots_remaining=76))
        collector.process_record(raw_record(346011, 11))
    assert value.count(
        "experiment_rounds", "round_id=346010 AND state='excluded'"
    ) == 1
    assert value.queue(346010).state == "pending"


def test_finalized_label_record_cannot_become_decision_input(
    store, config, marker_file
) -> None:
    value, _ = store
    marker, digest = marker_file
    collector = RFC008Collector(
        store=value,
        config=config,
        marker_path=marker,
        expected_marker_sha256=digest,
    )
    record = raw_record(346015, 15, slots_remaining=0)
    raw = dict(record.raw)
    raw["commitment"] = "finalized"
    raw["round"] = {
        **raw["round"],
        "slot_hash_hex": "01" * 32,
        "entropy": 3,
        "total_vaulted": 1,
        "total_winnings": 5000000,
        "motherlode": 0,
    }
    record = record.model_copy(update={"raw": raw})
    with value.connection:
        collector.process_record(record)
    assert value.count("finalized_outcomes") == 0
    assert value.count("decision_snapshots") == 0
    assert value.count(
        "experiment_rounds", "round_id=346015 AND state='excluded'"
    ) == 1


def test_status_is_read_only_and_reports_caps_and_safety(
    store, config, marker_file
) -> None:
    value, path = store
    marker, digest = marker_file
    with value.connection:
        value.start_round(346020, datetime(2026, 7, 25, tzinfo=timezone.utc))
        value.increment("live_actions", 0)
    report = status_report(
        ledger_path=path,
        config_path=CONFIG_PATH,
        marker_path=marker,
        authorization_path=path.with_suffix(".authorization.sqlite"),
        expected_marker_sha256=digest,
        now=datetime(2026, 7, 25, 1, tzinfo=timezone.utc),
    )
    assert report["sqlite_integrity"] == "ok"
    assert report["started_rounds"] == 1
    assert report["primary_analyzable_rounds"] == 0
    assert report["collection_ready"]
    assert report["collection_authorized"]
    assert report["authorization_state"] == "initialized"
    assert report["collection_target"] == 600
    assert report["committed_opportunity_count"] == 0
    expired = status_report(
        ledger_path=path,
        config_path=CONFIG_PATH,
        marker_path=marker,
        authorization_path=path.with_suffix(".authorization.sqlite"),
        expected_marker_sha256=digest,
        now=datetime(2026, 8, 9, tzinfo=timezone.utc),
    )
    assert expired["calendar_cap_reached"]
    assert not expired["collection_ready"]


def test_cli_requires_explicit_commands_and_arguments() -> None:
    commands = parser()
    args = commands.parse_args(
        [
            "run",
            "--config",
            "config.json",
            "--resolver-config",
            "resolver.json",
            "--marker",
            "marker.json",
            "--expected-marker-sha256",
            "a" * 64,
            "--ledger",
            "ledger.sqlite",
            "--authorization",
            "authorization.sqlite",
            "--repository-root",
            ".",
            "--burn-in-evidence",
            "burn-in.json",
            "--release-approval",
            "release.json",
            "--approval-manifest",
            "approval.json",
        ]
    )
    assert args.command == "run"
    assert not args.recovery
    burn_in = commands.parse_args(
        [
            "resolver-burn-in",
            "--config",
            "config.json",
            "--resolver-config",
            "resolver.json",
            "--ledger",
            "burnin.sqlite",
            "--output",
            "burnin.json",
            "--mode",
            "operational",
        ]
    )
    assert burn_in.sample_size == 5
    assert burn_in.release_approval.endswith(
        "release_implementation_approval_v1.json"
    )
