from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from orev3.collection.collector import PaperCollector
from orev3.collection.config import CollectionConfig
from orev3.collection.cursor_store import CollectionStore
from orev3.collection.health import deterministic_health, health_snapshot
from orev3.collection.metrics import evaluate_burn_in
from orev3.collection.reporting import export_collection
from orev3.ledger.validation import assert_observational_only

from .conftest import lifecycle, snapshot


def burn_in_files(tmp_path: Path, count: int) -> tuple[Path, Path]:
    source = tmp_path / "observer.jsonl"
    outcomes = tmp_path / "outcomes.jsonl"
    source.write_text(
        "\n".join(
            json.dumps(
                snapshot(
                    round_id=1000 + index,
                    observed_index=index,
                )
            )
            for index in range(count)
        )
        + "\n"
    )
    outcomes.write_text(
        "\n".join(
            json.dumps(lifecycle(round_id=1000 + index))
            for index in range(count)
        )
        + "\n"
    )
    return source, outcomes


def run_burn_in(tmp_path: Path, config, count: int):
    source, outcomes = burn_in_files(tmp_path, count)
    configured = config.model_copy(update={"outcome_source": str(outcomes)})
    store = CollectionStore(tmp_path / "ledger.sqlite")
    store.initialize()
    with store.connection:
        store.set_metadata("configuration_hash", configured.configuration_hash)
        store.set_metadata("collector_version", configured.collector_version)
        store.set_metadata("restart_resume_proven", "1")
        store.set_metadata("observer_modified", "0")
    collector = PaperCollector(
        store=store,
        config=configured,
        mode="historical_replay_burn_in",
    )
    collector.replay(source, max_opportunities=count)
    return store


def test_gate_a_passes_100_consecutive_and_distinguishes_mode(
    tmp_path: Path, config
) -> None:
    with run_burn_in(tmp_path, config, 100) as store:
        replay = evaluate_burn_in(
            store, mode="historical_replay_burn_in"
        )
        real_time_label = evaluate_burn_in(
            store, mode="real_time_burn_in"
        )
        assert replay.passed
        assert replay.consecutive_eligible_opportunities == 100
        assert replay.opportunity_to_decision_linkage == 1
        assert replay.outcome_linkage == 1
        assert replay.duplicate_decisions == 0
        assert real_time_label.mode == "real_time_burn_in"


def test_gate_a_fails_with_99_duplicate_linkage_and_provenance(
    tmp_path: Path, config
) -> None:
    with run_burn_in(tmp_path, config, 99) as store:
        result = evaluate_burn_in(
            store, mode="historical_replay_burn_in"
        )
        assert not result.passed
        assert "fewer_than_100_consecutive_opportunities" in result.failed_criteria
        with store.connection:
            store.increment("duplicate_decisions")
            store.connection.execute(
                "DELETE FROM paper_decisions WHERE opportunity_id = "
                "(SELECT opportunity_id FROM paper_decisions ORDER BY opportunity_id LIMIT 1)"
            )
            row = store.connection.execute(
                "SELECT accounting_id, record_json FROM paper_accounting LIMIT 1"
            ).fetchone()
            value = json.loads(row[1])
            value["provenance"]["paper_net_sol_before_fees"] = "wallet_realized"
            store.connection.execute(
                "UPDATE paper_accounting SET record_json=? WHERE accounting_id=?",
                (json.dumps(value, sort_keys=True), row[0]),
            )
        failed = evaluate_burn_in(
            store, mode="historical_replay_burn_in"
        )
        assert "duplicate_decisions" in failed.failed_criteria
        assert (
            "opportunity_to_decision_linkage_below_99_percent"
            in failed.failed_criteria
        )
        assert "paper_accounting_provenance_incomplete" in failed.failed_criteria


def test_deterministic_exports_health_and_strict_json(
    tmp_path: Path, config
) -> None:
    with run_burn_in(tmp_path, config, 3) as store:
        first = export_collection(
            store, tmp_path / "first", mode="historical_replay_burn_in"
        )
        second = export_collection(
            store, tmp_path / "second", mode="historical_replay_burn_in"
        )
        health = health_snapshot(
            store,
            mode="historical_replay_burn_in",
            uptime_seconds=12,
            processing_latency_ms=4,
        )
        assert deterministic_health(health)["collector_uptime_seconds"] == 0
    first_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in first
    }
    second_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in second
    }
    assert first_hashes == second_hashes
    for path in first:
        if path.suffix == ".json":
            json.loads(
                path.read_text(),
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(value)
                ),
            )


def test_config_and_live_actions_are_rejected(config) -> None:
    with pytest.raises(PermissionError):
        config.model_copy(
            update={"allow_signing": True}
        ).__class__.model_validate(
            {**config.model_dump(), "allow_signing": True}
        )
    for key in ("submit", "sign", "claim", "build_transaction"):
        with pytest.raises(PermissionError):
            assert_observational_only(**{key: True})


def test_no_secret_or_mutating_imports_and_artifacts_ignored() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/orev3/collection").glob("*.py")
    )
    assert "from solders.keypair" not in source
    assert "send_transaction(" not in source
    assert "sendTransaction" not in source
    assert "claim_transaction" not in source
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "data/ledger/rfc007_*" in ignore
    assert "logs/rfc007_*" in ignore
