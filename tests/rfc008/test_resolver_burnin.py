from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from orev3.observer.accounts import derive_round_address
from orev3.rfc008.burnin import (
    DEFAULT_OPERATIONAL_SAMPLE_SIZE,
    FixtureOutcomeProvider,
    RpcAccounting,
    _round_account_bytes,
    run_resolver_burn_in,
    select_operational_rounds,
)
from orev3.rfc008.decisions import build_decisions, snapshot_from_opportunity
from orev3.rfc008.outcomes import enqueue_pending
from orev3.rfc008.resolver import FinalizedOutcomeResolver, derive_round_pda
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import (
    REQUIRED_PROCESS_COMMAND_IDENTITIES,
    ResolverBurnInEvidence,
)
from orev3.rfc008.storage import RFC008Store
from orev3.rfc008.collector import RFC008Collector

from .conftest import CONFIG_PATH, make_opportunity


RESOLVER_CONFIG_PATH = (
    CONFIG_PATH.parents[0] / "rfc008_resolver_v1.json"
)


def prepare_round(store, config, round_id, at):
    store.start_round(round_id, at)
    snapshot = snapshot_from_opportunity(
        make_opportunity(round_id),
        config,
        source_content_sha256=f"{round_id:064x}"[-64:],
    )
    store.insert_snapshot_and_decisions(
        snapshot, build_decisions(snapshot, config)
    )
    enqueue_pending(store, round_id, at=at)


def providers_for(resolver_config, round_id, *, second_entropy=26):
    pda = derive_round_pda(
        round_id, resolver_config.expected_program_owner
    )
    return (
        FixtureOutcomeProvider(
            resolver_config.provider_ids[0],
            resolver_config,
            {pda: _round_account_bytes(round_id, entropy=26)},
        ),
        FixtureOutcomeProvider(
            resolver_config.provider_ids[1],
            resolver_config,
            {pda: _round_account_bytes(round_id, entropy=second_entropy)},
        ),
    )


def test_pda_finalized_validation_provenance_and_idempotency(store, config):
    value, _ = store
    resolver_config = ResolverConfig.from_path(RESOLVER_CONFIG_PATH)
    round_id = 346200
    now = datetime(2026, 7, 25, tzinfo=timezone.utc)
    assert derive_round_pda(
        round_id, resolver_config.expected_program_owner
    ) == str(derive_round_address(round_id))
    with value.connection:
        prepare_round(value, config, round_id, now)
        resolver = FinalizedOutcomeResolver(
            store=value,
            experiment_config=config,
            resolver_config=resolver_config,
            providers=providers_for(resolver_config, round_id),
        )
        resolver.validate_provider_networks()
        assert resolver.resolve_round(round_id, now=now) == "accepted"
        assert resolver.resolve_round(round_id, now=now) == "duplicate"
    outcome = value.accepted_outcome(round_id)
    assert outcome is not None
    assert outcome.commitment == "finalized"
    assert outcome.program_owner == resolver_config.expected_program_owner
    assert outcome.provider_ids == resolver_config.provider_ids
    assert len(outcome.provider_response_sha256) == 2
    assert value.count("experiment_rounds", "state='finalized_primary'") == 1


def test_retry_schedule_persists_and_is_deterministic(store, config):
    value, path = store
    resolver_config = ResolverConfig.from_path(RESOLVER_CONFIG_PATH)
    round_id = 346201
    now = datetime(2026, 7, 25, tzinfo=timezone.utc)
    pda = derive_round_pda(round_id, resolver_config.expected_program_owner)
    failing = (
        FixtureOutcomeProvider(
            resolver_config.provider_ids[0],
            resolver_config,
            {pda: _round_account_bytes(round_id)},
            failures_remaining=1,
        ),
        FixtureOutcomeProvider(
            resolver_config.provider_ids[1],
            resolver_config,
            {pda: _round_account_bytes(round_id)},
        ),
    )
    with value.connection:
        prepare_round(value, config, round_id, now)
        resolver = FinalizedOutcomeResolver(
            store=value,
            experiment_config=config,
            resolver_config=resolver_config,
            providers=failing,
        )
        assert resolver.resolve_round(round_id, now=now) == "retry"
    retry_at = value.queue(round_id).next_retry_at
    value.connection.commit()
    with RFC008Store(path, config=config) as restarted:
        assert restarted.queue(round_id).next_retry_at == retry_at
        with restarted.connection:
            resolver = FinalizedOutcomeResolver(
                store=restarted,
                experiment_config=config,
                resolver_config=resolver_config,
                providers=providers_for(resolver_config, round_id),
            )
            assert resolver.process_due(
                now=retry_at - timedelta(microseconds=1)
            )["accepted"] == 0
            assert resolver.process_due(now=retry_at)["accepted"] == 1


def test_provider_disagreement_conflicts_and_malformed_retries(store, config):
    value, _ = store
    resolver_config = ResolverConfig.from_path(RESOLVER_CONFIG_PATH)
    now = datetime(2026, 7, 25, tzinfo=timezone.utc)
    conflict_round = 346202
    with value.connection:
        prepare_round(value, config, conflict_round, now)
        resolver = FinalizedOutcomeResolver(
            store=value,
            experiment_config=config,
            resolver_config=resolver_config,
            providers=providers_for(
                resolver_config, conflict_round, second_entropy=27
            ),
        )
        assert resolver.resolve_round(conflict_round, now=now) == "conflict"
    assert value.queue(conflict_round).state == "conflicted"
    assert value.count("outcome_conflicts") == 1

    malformed_round = 346203
    pda = derive_round_pda(
        malformed_round, resolver_config.expected_program_owner
    )
    with value.connection:
        prepare_round(value, config, malformed_round, now)
        malformed = FixtureOutcomeProvider(
            resolver_config.provider_ids[0], resolver_config, {}
        )
        good = FixtureOutcomeProvider(
            resolver_config.provider_ids[1],
            resolver_config,
            {pda: _round_account_bytes(malformed_round)},
        )
        resolver = FinalizedOutcomeResolver(
            store=value,
            experiment_config=config,
            resolver_config=resolver_config,
            providers=(malformed, good),
        )
        assert resolver.resolve_round(malformed_round, now=now) == "retry"
    assert value.queue(malformed_round).state == "pending"


def test_fixture_burn_in_proves_restart_retry_conflict_and_provenance(
    tmp_path,
):
    result = run_resolver_burn_in(
        ledger_path=tmp_path / "resolver_burn_in.sqlite",
        output_path=tmp_path / "resolver_burn_in.json",
        experiment_config_path=CONFIG_PATH,
        resolver_config_path=RESOLVER_CONFIG_PATH,
        mode="fixture",
        control_round_id=346250,
        now=datetime(2026, 7, 25, tzinfo=timezone.utc),
    )
    assert result["passed"]
    assert not result["primary_authoritative_capable"]
    assert {
        "operational_summary",
        "real_rpc_request_counts",
        "attempt_reconciliation",
        "restart_result",
        "retry_result",
        "jitter_result",
        "conflict_result",
        "quarantine_result",
        "process_preservation",
        "source_boundary",
        "recomputed_primary_authoritative_capable",
        "marker_authorized",
        "collection_authorized",
    } <= set(result)
    assert result["retry_result"]
    assert result["jitter_result"]["passed"]
    assert result["jitter_result"]["tested_round_id"] == 346250
    assert result["jitter_result"]["retry_numbers_tested"] == [1, 2, 3]
    assert (tmp_path / "resolver_burn_in.json").exists()
    assert (tmp_path / "resolver_burn_in.json.sha256").exists()
    evidence = ResolverBurnInEvidence.model_validate_json(
        (tmp_path / "resolver_burn_in.json").read_text()
    )
    assert evidence.schema_version == 3
    assert evidence.real_rpc_request_counts.total == 0
    assert evidence.conflict.conflict_test_passed
    assert evidence.quarantine.quarantine_test_passed
    assert (
        evidence.conflict.round_id
        != evidence.quarantine.quarantine_round_id
    )
    assert evidence.quarantine.quarantine_restart_persistence
    assert evidence.quarantine.quarantine_overwrite_refused
    assert evidence.jitter.jitter_test_passed
    assert evidence.source_boundary.source_path.startswith("fixture://")
    assert {
        value.role for value in evidence.protected_processes
    } == {"observer", "observer_caffeinate", "rfc007_collector"}


def test_operational_selection_is_bounded_distinct_and_deterministic():
    assert DEFAULT_OPERATIONAL_SAMPLE_SIZE == 5
    expected = (346295, 346296, 346297, 346298, 346299)
    assert select_operational_rounds(346300) == expected
    assert select_operational_rounds(346300) == expected
    assert len(set(expected)) == 5
    with pytest.raises(ValueError, match="at least 5"):
        select_operational_rounds(346300, 4)
    with pytest.raises(ValueError, match="cannot supply"):
        select_operational_rounds(5, 5)


def test_rpc_accounting_counts_failures_retries_and_reconciles():
    counts = RpcAccounting(("primary", "secondary"))
    counts.begin("primary", "get_genesis_hash")
    counts.success()
    counts.begin("secondary", "get_genesis_hash")
    counts.success()
    counts.begin("primary", "get_account_info_with_context", "pda")
    counts.unavailable("primary", "get_account_info_with_context", "pda")
    counts.begin("primary", "get_account_info_with_context", "pda")
    counts.success()
    value = counts.evidence()
    assert value.total == 4
    assert value.by_provider == {"primary": 3, "secondary": 1}
    assert value.by_method["get_account_info_with_context"] == 2
    assert value.retried_requests == 1
    assert value.unavailable_responses == 1
    assert value.successful_responses == 3


def test_synthetic_operational_five_round_evidence_and_rpc_counts(
    tmp_path, monkeypatch
):
    resolver_config = ResolverConfig.from_path(RESOLVER_CONFIG_PATH)
    boundary_round = 346300
    selected = select_operational_rounds(boundary_round)
    accounts = {
        derive_round_pda(round_id, resolver_config.expected_program_owner):
        _round_account_bytes(round_id)
        for round_id in selected
    }

    def provider(provider_id, _url):
        return FixtureOutcomeProvider(
            provider_id, resolver_config, accounts
        )

    monkeypatch.setattr(
        "orev3.rfc008.burnin.RpcRecoveryProvider", provider
    )
    monkeypatch.setattr(
        "orev3.rfc008.burnin.derive_runtime_source_boundary",
        lambda _glob: (
            SimpleNamespace(
                round_id=boundary_round,
                source_path="/tmp/observer.jsonl",
                source_inode=1,
                source_byte_offset=100,
                source_line_number=5,
                source_record_sha256="a" * 64,
                source_observed_at=datetime(
                    2026, 7, 25, tzinfo=timezone.utc
                ),
            ),
            (),
        ),
    )
    monkeypatch.setenv("ORE_RECOVERY_PRIMARY_RPC_URL", "mock://primary")
    monkeypatch.setenv("ORE_RECOVERY_SECONDARY_RPC_URL", "mock://secondary")
    monkeypatch.setattr(
        "orev3.rfc008.burnin._process_snapshot",
        lambda _pids: {
            pid: (
                "a" * 64,
                REQUIRED_PROCESS_COMMAND_IDENTITIES[role],
                datetime(2026, 7, 25, tzinfo=timezone.utc),
            )
            for pid, role in {
                48404: "observer",
                48405: "observer_caffeinate",
                78317: "rfc007_collector",
            }.items()
        },
    )
    result = run_resolver_burn_in(
        ledger_path=tmp_path / "operational.sqlite",
        output_path=tmp_path / "operational.json",
        experiment_config_path=CONFIG_PATH,
        resolver_config_path=RESOLVER_CONFIG_PATH,
        mode="operational",
        preserve_process_ids=(48404, 48405, 78317),
        authorization_token="RFC008_OPERATIONAL_RESOLVER_BURN_IN_AUTHORIZED",
        now=datetime(2026, 7, 25, tzinfo=timezone.utc),
    )
    assert result["passed"]
    assert result["primary_authoritative_capable"]
    evidence = ResolverBurnInEvidence.model_validate_json(
        (tmp_path / "operational.json").read_text()
    )
    assert evidence.operational.selected_round_ids == selected
    assert evidence.operational.successful_authoritative_count == 5
    assert evidence.operational.complete_provenance_count == 5
    assert evidence.real_rpc_request_counts.total == 12
    assert evidence.real_rpc_request_counts.genesis_hash_reads == 2
    assert evidence.real_rpc_request_counts.finalized_account_reads == 10
    assert evidence.real_rpc_request_counts.by_provider == {
        "primary": 6,
        "secondary": 6,
    }
    assert evidence.real_rpc_request_counts.by_provider_and_method[
        "primary"
    ]["get_account_info_with_context"] == 5


def test_operational_burn_in_rejects_below_minimum_before_provider_use(
    tmp_path,
):
    with pytest.raises(ValueError, match="at least 5"):
        run_resolver_burn_in(
            ledger_path=tmp_path / "operational.sqlite",
            output_path=tmp_path / "operational.json",
            experiment_config_path=CONFIG_PATH,
            resolver_config_path=RESOLVER_CONFIG_PATH,
            mode="operational",
            sample_size=4,
            authorization_token=(
                "RFC008_OPERATIONAL_RESOLVER_BURN_IN_AUTHORIZED"
            ),
        )
    assert not (tmp_path / "operational.sqlite").exists()


def test_evidence_fails_closed_for_small_sample_and_missing_quarantine(
    tmp_path, monkeypatch
):
    # Generate a complete fixture artifact, then prove strict v2 rejects
    # unsupported/missing controlled evidence instead of accepting legacy flags.
    run_resolver_burn_in(
        ledger_path=tmp_path / "fixture.sqlite",
        output_path=tmp_path / "fixture.json",
        experiment_config_path=CONFIG_PATH,
        resolver_config_path=RESOLVER_CONFIG_PATH,
        mode="fixture",
        now=datetime(2026, 7, 25, tzinfo=timezone.utc),
    )
    raw = json.loads((tmp_path / "fixture.json").read_text())
    raw.pop("quarantine")
    with pytest.raises(ValidationError):
        ResolverBurnInEvidence.model_validate(raw)
    raw = json.loads((tmp_path / "fixture.json").read_text())
    raw["schema_version"] = 2
    with pytest.raises(ValidationError):
        ResolverBurnInEvidence.model_validate(raw)


def test_resolver_quarantines_expired_queue_before_provider_attempt(
    store, config
):
    value, _ = store
    resolver_config = ResolverConfig.from_path(RESOLVER_CONFIG_PATH)
    round_id = 346260
    old = datetime(2026, 7, 24, tzinfo=timezone.utc)
    with value.connection:
        prepare_round(value, config, round_id, old)
        resolver = FinalizedOutcomeResolver(
            store=value,
            experiment_config=config,
            resolver_config=resolver_config,
            providers=providers_for(resolver_config, round_id),
        )
        result = resolver.process_due(now=old + timedelta(days=1, seconds=1))
    assert result["quarantined"] == 1
    assert result["accepted"] == 0
    assert value.queue(round_id).state == "quarantined"


def test_collector_poll_loop_invokes_persisted_resolver(
    store, config, marker_file, monkeypatch
):
    value, _ = store
    marker, digest = marker_file
    calls = []
    probe = SimpleNamespace(
        config=SimpleNamespace(fingerprint="e" * 64),
        process_due=lambda: calls.append("processed"),
    )
    monkeypatch.setattr("orev3.rfc008.collector.glob.glob", lambda value: [])
    collector = RFC008Collector(
        store=value,
        config=config,
        marker_path=marker,
        expected_marker_sha256=digest,
        resolver=probe,
    )
    assert collector.poll_once() == 0
    assert calls == ["processed"]
