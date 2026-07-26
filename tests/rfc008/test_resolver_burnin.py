from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from orev3.observer.accounts import derive_round_address
from orev3.rfc008.burnin import (
    FixtureOutcomeProvider,
    _round_account_bytes,
    run_resolver_burn_in,
)
from orev3.rfc008.decisions import build_decisions, snapshot_from_opportunity
from orev3.rfc008.outcomes import enqueue_pending
from orev3.rfc008.resolver import FinalizedOutcomeResolver, derive_round_pda
from orev3.rfc008.resolver_config import ResolverConfig
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
    assert (tmp_path / "resolver_burn_in.json").exists()
    assert (tmp_path / "resolver_burn_in.json.sha256").exists()


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
