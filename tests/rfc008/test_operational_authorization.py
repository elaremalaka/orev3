from __future__ import annotations

import argparse
import json
import multiprocessing
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import orev3.rfc008.cli as rfc008_cli
import orev3.rfc008.lifecycle as rfc008_lifecycle
from orev3.rfc008.authorization import (
    CollectionAuthorizationRecord,
    CollectionAuthorizationStore,
    build_authorization_record,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.collector import RFC008Collector
from orev3.rfc008.decisions import build_decisions, snapshot_from_opportunity
from orev3.rfc008.migrations import (
    APPLICATION_ID,
    MIGRATIONS,
    apply_migrations,
)
from orev3.rfc008.storage import (
    CollectionContractError,
    CollectionTargetReached,
    LedgerInitialization,
    RFC008Store,
    create_authorized_ledger,
)
from orev3.rfc008.supervision import SupervisionError

from .conftest import make_opportunity
from .test_marker_collector_status import raw_record


def test_static_collection_authorization_literals_are_not_active_source() -> None:
    root = Path(__file__).parents[2] / "src/orev3/rfc008"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "cli.py", root / "collector.py")
    )
    assert "RFC008_HOLDOUT_COLLECTION_AUTHORIZED" not in source
    assert "RFC008_PRODUCTION_LEDGER_INITIALIZATION_AUTHORIZED" not in source
    assert "collection_authorization_valid" not in source
    assert "ledger_initialization_authorized" not in source


def test_cross_database_completion_contract_is_explicit() -> None:
    root = Path(__file__).parents[2]
    rfc = (
        root
        / "docs/rfcs/RFC-008-PREREGISTERED-ROUND-LEVEL-STRATEGY-EVALUATION.md"
    ).read_text(encoding="utf-8")
    runbook = (
        root / "docs/research/RFC-008-OPERATOR-RUNBOOK.md"
    ).read_text(encoding="utf-8")
    normalized_runbook = " ".join(runbook.split())
    normalized_rfc = " ".join(rfc.split())
    for document in (rfc, runbook):
        assert "separate SQLite databases" in document
        assert "Opportunity 600" in document
        assert "opportunity 601" in document
        assert "mandatory" in document
        assert "idempotent" in document
    assert (
        "Cross-database same-transaction completion is deliberately not "
        "part of the RFC-008 contract"
    ) in normalized_runbook
    assert (
        "The temporary combination `ledger=completed` and "
        "`authorization=active` is recoverable metadata lag"
    ) in normalized_rfc


def test_authorization_path_is_separate_and_sqlite_backed(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    kwargs = {
        "ledger_name": "same.sqlite",
        "authorization_name": "same.sqlite",
    }
    with pytest.raises(ValueError, match="must be separate"):
        record_for(tmp_path, config, **kwargs)
    with pytest.raises(ValueError, match="SQLite path"):
        record_for(
            tmp_path,
            config,
            authorization_name="authorization.json",
        )


def record_for(
    tmp_path: Path,
    config: RFC008Config,
    *,
    ledger_name: str = "rfc008_paper_ledger_v1.sqlite",
    authorization_name: str = "rfc008_collection_authorization_v1.sqlite",
    marker_sha256: str = "f" * 64,
):
    return build_authorization_record(
        authorization_path=tmp_path / authorization_name,
        ledger_path=tmp_path / ledger_name,
        branch="research/rfc-007-paper-collection-burn-in",
        repository_head="a" * 40,
        implementation_commit="b" * 40,
        active_approval_sha256="c" * 64,
        immediate_predecessor_sha256="d" * 64,
        approval_chain_anchor="e" * 64,
        marker_sha256=marker_sha256,
        marker_sidecar_sha256="1" * 64,
        candidate_sha256=config.candidate_configuration_sha256,
        experiment_id=config.experiment_id,
        protocol_version=config.protocol_version,
        configuration_fingerprint=config.configuration_fingerprint,
        resolver_fingerprint="2" * 64,
        migration_set_sha256="3" * 64,
        cli_sha256="4" * 64,
        runbook_sha256="5" * 64,
        burn_in_evidence_sha256="6" * 64,
        burn_in_ledger_sha256="7" * 64,
        approval_manifest_sha256=config.approval_manifest_sha256,
        external_rpc_burn_in_performed=True,
        nonce="fixture-authorization-nonce",
        created_at="2026-07-28T00:00:00+00:00",
    )


def issue_and_initialize(
    tmp_path: Path,
    config: RFC008Config,
    *,
    marker_sha256: str = "f" * 64,
) -> tuple[Path, Path]:
    record = record_for(
        tmp_path, config, marker_sha256=marker_sha256
    )
    authorization_path = Path(record.authorization_storage_path)
    ledger_path = Path(record.canonical_ledger_path)
    CollectionAuthorizationStore.issue(authorization_path, record)
    with CollectionAuthorizationStore(authorization_path) as authorization:
        authorization.consume_initialization()
        create_authorized_ledger(
            ledger_path,
            config=config,
            initialization=LedgerInitialization(
                authorization=record,
                collection_seed_cursors=(
                    {"source_path": "/tmp/source", "source_byte_offset": 10},
                ),
                publication_cursors=(
                    {"source_path": "/tmp/source", "source_byte_offset": 10},
                ),
            ),
        )
        authorization.mark_initialized()
    return authorization_path, ledger_path


def commit_opportunity(
    store: RFC008Store,
    config: RFC008Config,
    round_id: int,
) -> bool:
    snapshot = snapshot_from_opportunity(
        make_opportunity(round_id),
        config,
        source_content_sha256=f"{round_id:064x}"[-64:],
    )
    return store.insert_snapshot_and_decisions(
        snapshot, build_decisions(snapshot, config)
    )


def seed_active_collection_at_599(
    tmp_path: Path,
    config: RFC008Config,
    *,
    first_round_id: int,
) -> tuple[Path, Path]:
    authorization_path, ledger_path = issue_and_initialize(tmp_path, config)
    with CollectionAuthorizationStore(authorization_path) as authorization:
        authorization.consume_launch("crashed-session")
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            store.begin_collection_session("crashed-session")
            for round_id in range(first_round_id, first_round_id + 599):
                assert commit_opportunity(store, config, round_id)
        assert store.collection_contract().committed_opportunity_count == 599
    return authorization_path, ledger_path


def process_final_opportunity(
    ledger_path: str,
    config_path: str,
    round_id: int,
    start: multiprocessing.synchronize.Event,
    ready: multiprocessing.queues.Queue,
    results: multiprocessing.queues.Queue,
) -> None:
    try:
        config = RFC008Config.from_path(config_path)
        with RFC008Store(ledger_path, config=config) as store:
            ready.put("ready")
            if not start.wait(timeout=10):
                results.put("start_timeout")
                return
            try:
                with store.connection:
                    commit_opportunity(store, config, round_id)
                results.put("committed")
            except CollectionTargetReached:
                results.put("target_reached")
            except CollectionContractError:
                results.put("contract_mismatch")
    except Exception as exc:
        results.put(f"unexpected:{type(exc).__name__}:{exc}")


def force_last_opportunity_identity(
    ledger_path: Path,
    identity: str | None,
) -> None:
    connection = sqlite3.connect(ledger_path)
    connection.execute("DROP TRIGGER collection_contract_last_identity_guard")
    connection.execute(
        """
        UPDATE collection_contract
        SET last_committed_opportunity_identity=?
        WHERE singleton=1
        """,
        (identity,),
    )
    connection.commit()
    connection.close()


def test_authorization_is_single_use_and_transition_history_is_tamper_evident(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    record = record_for(tmp_path, config)
    path = Path(record.authorization_storage_path)
    CollectionAuthorizationStore.issue(path, record)
    with pytest.raises(FileExistsError):
        CollectionAuthorizationStore.issue(path, record)
    with CollectionAuthorizationStore(path) as store:
        store.consume_initialization()
        with pytest.raises(PermissionError):
            store.consume_initialization()
        store.mark_initialized()
        store.consume_launch("session-1")
        with pytest.raises(PermissionError):
            store.consume_launch("session-2")
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE authorization SET lifecycle_state='completed' WHERE singleton=1"
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="event history"):
        CollectionAuthorizationStore(path, read_only=True)


def test_begin_run_fails_authorization_closed_if_session_creation_fails(
    tmp_path: Path,
    config: RFC008Config,
    marker_file,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker, digest = marker_file
    authorization_path, ledger_path = issue_and_initialize(
        tmp_path,
        config,
        marker_sha256=digest,
    )
    with (
        CollectionAuthorizationStore(authorization_path) as authorization,
        RFC008Store(ledger_path, config=config) as store,
    ):
        collector = RFC008Collector(
            store=store,
            config=config,
            marker_path=marker,
            expected_marker_sha256=digest,
            authorization_store=authorization,
            session_identifier="failed-startup-session",
        )
        monkeypatch.setattr(
            store,
            "begin_collection_session",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("fixture session failure")
            ),
        )
        with pytest.raises(RuntimeError, match="fixture session failure"):
            collector.begin_run()
        assert authorization.status().lifecycle_state == "failed"
        assert store.collection_contract().collection_state == "initialized"
        assert store.collection_contract().active_session_identity is None
        assert store.count("decision_snapshots") == 0


def test_begin_run_commits_supervisor_visible_startup_handshake(
    tmp_path: Path,
    config: RFC008Config,
    marker_file,
) -> None:
    marker, digest = marker_file
    authorization_path, ledger_path = issue_and_initialize(
        tmp_path,
        config,
        marker_sha256=digest,
    )
    with (
        CollectionAuthorizationStore(authorization_path) as authorization,
        RFC008Store(ledger_path, config=config) as store,
    ):
        collector = RFC008Collector(
            store=store,
            config=config,
            marker_path=marker,
            expected_marker_sha256=digest,
            authorization_store=authorization,
            session_identifier="startup-session",
        )
        assert collector.begin_run() == "startup-session"
        assert not store.connection.in_transaction

        with (
            CollectionAuthorizationStore(
                authorization_path, read_only=True
            ) as observer_authorization,
            RFC008Store(
                ledger_path, config=config, read_only=True
            ) as observer_store,
        ):
            contract = observer_store.validate_collection_contract(
                config=config,
                authorization=observer_authorization.status().record,
            )
            run = observer_store.connection.execute(
                """
                SELECT run_id,ended_at
                FROM collector_runs
                WHERE run_id=?
                """,
                ("startup-session",),
            ).fetchone()

        assert contract.active_session_identity == "startup-session"
        assert run is not None
        assert run["run_id"] == "startup-session"
        assert run["ended_at"] is None
        assert authorization.status().lifecycle_state == "active"
        with store.connection:
            collector.finish_run()


def test_startup_is_visible_while_first_poll_is_blocked(
    tmp_path: Path,
    config: RFC008Config,
    marker_file,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker, digest = marker_file
    authorization_path, ledger_path = issue_and_initialize(
        tmp_path,
        config,
        marker_sha256=digest,
    )
    poll_started = Event()
    release_poll = Event()
    worker_finished = Event()
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            with (
                CollectionAuthorizationStore(
                    authorization_path
                ) as authorization,
                RFC008Store(ledger_path, config=config) as store,
            ):
                collector = RFC008Collector(
                    store=store,
                    config=config,
                    marker_path=marker,
                    expected_marker_sha256=digest,
                    authorization_store=authorization,
                    session_identifier="blocked-poll-session",
                )
                monkeypatch.setattr(
                    collector, "install_signal_handlers", lambda: None
                )

                def blocked_poll() -> int:
                    poll_started.set()
                    assert release_poll.wait(timeout=5.0)
                    collector.stop_requested.set()
                    return 0

                monkeypatch.setattr(collector, "poll_once", blocked_poll)
                collector.run()
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)
        finally:
            worker_finished.set()

    thread = Thread(target=worker)
    thread.start()
    assert poll_started.wait(timeout=5.0)

    with (
        CollectionAuthorizationStore(
            authorization_path, read_only=True
        ) as observer_authorization,
        RFC008Store(
            ledger_path, config=config, read_only=True
        ) as observer_store,
    ):
        contract = observer_store.validate_collection_contract(
            config=config,
            authorization=observer_authorization.status().record,
        )
        run = observer_store.connection.execute(
            """
            SELECT run_id,ended_at
            FROM collector_runs
            WHERE run_id=?
            """,
            ("blocked-poll-session",),
        ).fetchone()

    assert contract.active_session_identity == "blocked-poll-session"
    assert run is not None
    assert run["ended_at"] is None
    assert not worker_finished.is_set()

    release_poll.set()
    thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert not errors
    with RFC008Store(
        ledger_path, config=config, read_only=True
    ) as observer_store:
        assert (
            observer_store.validate_collection_contract(
                config=config
            ).active_session_identity
            is None
        )


def test_supervised_collector_waits_for_acknowledgement_before_long_poll(
    tmp_path: Path,
    config: RFC008Config,
    marker_file,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker, digest = marker_file
    authorization_path, ledger_path = issue_and_initialize(
        tmp_path,
        config,
        marker_sha256=digest,
    )
    acknowledgement_started = Event()
    release_acknowledgement = Event()
    poll_started = Event()
    release_poll = Event()
    finished = Event()
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            with (
                CollectionAuthorizationStore(
                    authorization_path
                ) as authorization,
                RFC008Store(ledger_path, config=config) as store,
            ):
                def acknowledge(_session: str, _stop: Event) -> bool:
                    acknowledgement_started.set()
                    return release_acknowledgement.wait(timeout=5.0)

                collector = RFC008Collector(
                    store=store,
                    config=config,
                    marker_path=marker,
                    expected_marker_sha256=digest,
                    authorization_store=authorization,
                    session_identifier="acknowledged-session",
                    startup_acknowledgement=acknowledge,
                )
                monkeypatch.setattr(
                    collector, "install_signal_handlers", lambda: None
                )

                def long_poll() -> int:
                    poll_started.set()
                    assert release_poll.wait(timeout=5.0)
                    collector.stop_requested.set()
                    return 0

                monkeypatch.setattr(collector, "poll_once", long_poll)
                collector.run()
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)
        finally:
            finished.set()

    thread = Thread(target=worker)
    thread.start()
    assert acknowledgement_started.wait(timeout=5.0)
    assert not poll_started.is_set()
    assert not finished.is_set()

    with RFC008Store(
        ledger_path, config=config, read_only=True
    ) as observer:
        assert (
            observer.collection_contract().active_session_identity
            == "acknowledged-session"
        )

    release_acknowledgement.set()
    assert poll_started.wait(timeout=5.0)
    assert not finished.is_set()
    release_poll.set()
    thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert not errors


def test_failed_startup_acknowledgement_polls_and_commits_nothing(
    tmp_path: Path,
    config: RFC008Config,
    marker_file,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker, digest = marker_file
    authorization_path, ledger_path = issue_and_initialize(
        tmp_path,
        config,
        marker_sha256=digest,
    )
    poll_count = 0

    with (
        CollectionAuthorizationStore(authorization_path) as authorization,
        RFC008Store(ledger_path, config=config) as store,
    ):
        def reject_acknowledgement(_session: str, _stop: Event) -> bool:
            raise SupervisionError("fixture acknowledgment timeout")

        collector = RFC008Collector(
            store=store,
            config=config,
            marker_path=marker,
            expected_marker_sha256=digest,
            authorization_store=authorization,
            session_identifier="timed-out-session",
            startup_acknowledgement=reject_acknowledgement,
        )
        monkeypatch.setattr(
            collector, "install_signal_handlers", lambda: None
        )

        def forbidden_poll() -> int:
            nonlocal poll_count
            poll_count += 1
            return 0

        monkeypatch.setattr(collector, "poll_once", forbidden_poll)
        with pytest.raises(SupervisionError, match="acknowledgment timeout"):
            collector.run()

        assert poll_count == 0
        assert store.count("decision_snapshots") == 0
        assert store.count("arm_decisions") == 0
        assert store.collection_contract().active_session_identity is None
        run = store.connection.execute(
            "SELECT ended_at FROM collector_runs WHERE run_id=?",
            ("timed-out-session",),
        ).fetchone()
        assert run is not None
        assert run["ended_at"] is not None


def test_authorization_rejects_copy_digest_tamper_and_timestamp_tamper(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    record = record_for(tmp_path, config)
    path = Path(record.authorization_storage_path)
    CollectionAuthorizationStore.issue(path, record)
    copied = tmp_path / "copied-authorization.sqlite"
    shutil.copy2(path, copied)
    with pytest.raises(ValueError, match="Copied"):
        CollectionAuthorizationStore(copied, read_only=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE authorization SET authorization_digest=? WHERE singleton=1",
        ("0" * 64,),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="digest column"):
        CollectionAuthorizationStore(path, read_only=True)

    second = record_for(
        tmp_path,
        config,
        authorization_name="second-authorization.sqlite",
        ledger_name="second-ledger.sqlite",
    )
    second_path = Path(second.authorization_storage_path)
    CollectionAuthorizationStore.issue(second_path, second)
    with CollectionAuthorizationStore(second_path) as store:
        store.consume_initialization()
    connection = sqlite3.connect(second_path)
    connection.execute(
        """
        UPDATE authorization
        SET initialization_consumed_at='tampered'
        WHERE singleton=1
        """
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="timestamp was tampered"):
        CollectionAuthorizationStore(second_path, read_only=True)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("collection_target", 599),
        ("collection_target", 601),
        ("collection_target", "600"),
        ("collection_target", True),
        ("collection_mode", "live"),
        ("analysis_authorized", True),
        ("freeze_authorized", True),
        ("deployment_authorized", True),
        ("wallet_authorized", True),
        ("transaction_authorized", True),
        ("live_mining_authorized", True),
    ),
)
def test_authorization_schema_rejects_unsafe_scope(
    tmp_path: Path,
    config: RFC008Config,
    field: str,
    value: object,
) -> None:
    record = record_for(tmp_path, config)
    raw = record.model_dump(mode="json")
    raw[field] = value
    with pytest.raises(ValidationError):
        CollectionAuthorizationRecord.model_validate(raw)


def test_authorization_rejects_missing_unknown_and_duplicate_json_fields(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    record = record_for(tmp_path, config)
    raw = record.model_dump(mode="json")
    raw.pop("marker_sha256")
    with pytest.raises(ValidationError):
        CollectionAuthorizationRecord.model_validate(raw)
    raw = record.model_dump(mode="json")
    raw["unknown"] = True
    with pytest.raises(ValidationError):
        CollectionAuthorizationRecord.model_validate(raw)
    path = Path(record.authorization_storage_path)
    CollectionAuthorizationStore.issue(path, record)
    connection = sqlite3.connect(path)
    text = json.dumps(record.model_dump(mode="json"))
    duplicated = text[:-1] + ',"marker_sha256":"' + "f" * 64 + '"}'
    connection.execute(
        "UPDATE authorization SET immutable_json=? WHERE singleton=1",
        (duplicated,),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        CollectionAuthorizationStore(path, read_only=True)


def test_authorization_concurrent_consumption_has_one_winner(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    record = record_for(tmp_path, config)
    path = Path(record.authorization_storage_path)
    CollectionAuthorizationStore.issue(path, record)

    def consume() -> str:
        try:
            with CollectionAuthorizationStore(path) as store:
                return store.consume_initialization().lifecycle_state
        except PermissionError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: consume(), range(2)))
    assert results.count("initialization_consumed") == 1
    assert results.count("rejected") == 1


def test_ledger_binding_is_exact_immutable_and_copy_resistant(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    authorization_path, ledger_path = issue_and_initialize(tmp_path, config)
    with CollectionAuthorizationStore(
        authorization_path, read_only=True
    ) as authorization:
        with RFC008Store(
            ledger_path, config=config, read_only=True
        ) as store:
            contract = store.validate_collection_contract(
                config=config,
                authorization=authorization.status().record,
            )
            assert contract.collection_target == 600
            assert contract.collection_mode == "paper"
            assert contract.collection_seed_cursors
            assert contract.publication_cursors
    copied = tmp_path / "copied-ledger.sqlite"
    shutil.copy2(ledger_path, copied)
    with pytest.raises(CollectionContractError, match="canonical ledger path"):
        RFC008Store(copied, config=config, read_only=True)
    connection = sqlite3.connect(ledger_path)
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute(
            """
            UPDATE collection_contract SET collection_target=599
            WHERE singleton=1
            """
        )
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute(
            """
            UPDATE metadata SET value='changed'
            WHERE key='configuration_fingerprint'
            """
        )
    connection.close()
    with pytest.raises(FileExistsError):
        create_authorized_ledger(
            ledger_path,
            config=config,
            initialization=LedgerInitialization(
                authorization=record_for(tmp_path, config),
                collection_seed_cursors=(),
                publication_cursors=(),
            ),
        )
    with CollectionAuthorizationStore(
        authorization_path, read_only=True
    ) as authorization:
        with pytest.raises(CollectionContractError, match="does not bind"):
            create_authorized_ledger(
                tmp_path / "second-ledger.sqlite",
                config=config,
                initialization=LedgerInitialization(
                    authorization=authorization.status().record,
                    collection_seed_cursors=(),
                    publication_cursors=(),
                ),
            )


def test_partial_production_schema_fails_closed_without_migration(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    path = tmp_path / "rfc008_paper_ledger_v1.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
    apply_migrations(connection, MIGRATIONS[:3])
    connection.executemany(
        "INSERT INTO metadata(key,value) VALUES (?,?)",
        (
            ("schema_version", "3"),
            ("database_family", "orev3-rfc008"),
            ("experiment_id", config.experiment_id),
            (
                "configuration_fingerprint",
                config.configuration_fingerprint,
            ),
        ),
    )
    connection.commit()
    connection.close()
    with pytest.raises(ValueError, match="explicit release authorization"):
        RFC008Store(path, config=config)
    connection = sqlite3.connect(path)
    assert (
        connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        == 3
    )
    connection.close()


def test_empty_schema_four_migrates_additively_to_sequence_contract() -> None:
    connection = sqlite3.connect(":memory:")
    apply_migrations(connection, MIGRATIONS[:4])
    apply_migrations(connection)
    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(decision_snapshots)"
        )
    }
    triggers = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        )
    }
    assert (
        connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0]
        == 7
    )
    assert "committed_opportunity_sequence" in columns
    assert "collection_contract_last_identity_guard" in triggers
    connection.close()


def test_populated_schema_four_refuses_ambiguous_sequence_migration() -> None:
    connection = sqlite3.connect(":memory:")
    apply_migrations(connection, MIGRATIONS[:4])
    connection.execute("DROP TRIGGER decision_snapshot_target_guard")
    connection.execute(
        """
        INSERT INTO decision_snapshots(
          snapshot_id,round_id,source_content_sha256,record_json
        ) VALUES ('legacy',1,?, '{}')
        """,
        ("a" * 64,),
    )
    connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        apply_migrations(connection)
    assert (
        connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0]
        == 4
    )
    assert "committed_opportunity_sequence" not in {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(decision_snapshots)"
        )
    }
    connection.close()


def test_counter_duplicate_crash_and_restart_semantics(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    _, ledger_path = issue_and_initialize(tmp_path, config)
    with RFC008Store(ledger_path, config=config) as store:
        assert store.collection_contract().committed_opportunity_count == 0
        malformed = snapshot_from_opportunity(
            make_opportunity(349999),
            config,
            source_content_sha256=f"{349999:064x}"[-64:],
        ).model_copy(update={"miner_counts": (1,)})
        with pytest.raises(ValidationError):
            store.insert_snapshot_and_decisions(
                malformed,
                build_decisions(
                    snapshot_from_opportunity(
                        make_opportunity(349999),
                        config,
                        source_content_sha256=f"{349999:064x}"[-64:],
                    ),
                    config,
                ),
            )
        assert store.collection_contract().committed_opportunity_count == 0
        assert commit_opportunity(store, config, 350000)
        store.connection.commit()
        assert not commit_opportunity(store, config, 350000)
        assert store.collection_contract().committed_opportunity_count == 1
        store.connection.execute("SAVEPOINT crash_before_commit")
        snapshot = snapshot_from_opportunity(
            make_opportunity(350001),
            config,
            source_content_sha256=f"{350001:064x}"[-64:],
        )
        store.connection.execute(
            """
            INSERT INTO decision_snapshots(
              snapshot_id,round_id,source_content_sha256,record_json,
              committed_opportunity_sequence
            ) VALUES (?,?,?,?,?)
            """,
            (
                snapshot.snapshot_id,
                snapshot.round_id,
                snapshot.source_content_sha256,
                snapshot.model_dump_json(),
                2,
            ),
        )
        store.connection.execute("ROLLBACK TO SAVEPOINT crash_before_commit")
        store.connection.execute("RELEASE SAVEPOINT crash_before_commit")
        contract = store.collection_contract()
        assert contract.committed_opportunity_count == 1
        assert (
            contract.last_committed_opportunity_identity
            == store.connection.execute(
                """
                SELECT snapshot_id FROM decision_snapshots
                WHERE committed_opportunity_sequence=1
                """
            ).fetchone()[0]
        )
        assert store.count("decision_snapshots") == 1
    with RFC008Store(
        ledger_path, config=config, read_only=True
    ) as reopened:
        assert reopened.collection_contract().committed_opportunity_count == 1


def test_recovery_preserves_target_count_and_replaces_only_stale_session(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    authorization_path, ledger_path = issue_and_initialize(tmp_path, config)
    with CollectionAuthorizationStore(authorization_path) as authorization:
        authorization.consume_launch("first-session")
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            store.begin_collection_session("first-session")
            assert commit_opportunity(store, config, 350100)
        assert store.collection_contract().committed_opportunity_count == 1
    with CollectionAuthorizationStore(authorization_path) as authorization:
        recovered = authorization.consume_launch(
            "recovery-session",
            recovery=True,
        )
        assert recovered.recovery_count == 1
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            store.begin_collection_session(
                "recovery-session",
                recovery=True,
            )
        contract = store.validate_collection_contract(config=config)
        assert contract.collection_target == 600
        assert contract.committed_opportunity_count == 1
        assert contract.active_session_identity == "recovery-session"


def test_recovery_closes_stale_run_before_opening_new_session(
    tmp_path: Path,
    config: RFC008Config,
    marker_file,
) -> None:
    marker, digest = marker_file
    authorization_path, ledger_path = issue_and_initialize(
        tmp_path,
        config,
        marker_sha256=digest,
    )
    with (
        CollectionAuthorizationStore(authorization_path) as authorization,
        RFC008Store(ledger_path, config=config) as store,
    ):
        first = RFC008Collector(
            store=store,
            config=config,
            marker_path=marker,
            expected_marker_sha256=digest,
            authorization_store=authorization,
            session_identifier="first-session",
        )
        with store.connection:
            first.begin_run()
    with (
        CollectionAuthorizationStore(authorization_path) as authorization,
        RFC008Store(ledger_path, config=config) as store,
    ):
        recovery = RFC008Collector(
            store=store,
            config=config,
            marker_path=marker,
            expected_marker_sha256=digest,
            authorization_store=authorization,
            recovery=True,
            session_identifier="recovery-session",
        )
        with store.connection:
            recovery.begin_run()
        runs = store.connection.execute(
            "SELECT run_id,ended_at FROM collector_runs ORDER BY started_at"
        ).fetchall()
        assert len(runs) == 2
        assert runs[0]["run_id"] == "first-session"
        assert runs[0]["ended_at"] is not None
        assert runs[1]["run_id"] == "recovery-session"
        assert runs[1]["ended_at"] is None
        assert (
            store.collection_contract().active_session_identity
            == "recovery-session"
        )
        assert (
            authorization.status().consuming_session_identity
            == "recovery-session"
        )


def test_validator_uses_one_snapshot_across_final_commit(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    _, ledger_path = seed_active_collection_at_599(
        tmp_path,
        config,
        first_round_id=350500,
    )
    contract_read = Event()
    writer_finished = Event()

    def commit_final_opportunity() -> None:
        assert contract_read.wait(timeout=10)
        try:
            with RFC008Store(ledger_path, config=config) as writer:
                with writer.connection:
                    assert commit_opportunity(writer, config, 351099)
        finally:
            writer_finished.set()

    with (
        RFC008Store(ledger_path, config=config) as validator,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        original = validator.collection_contract

        def pause_after_contract_read():
            contract = original()
            contract_read.set()
            assert writer_finished.wait(timeout=10)
            return contract

        validator.collection_contract = pause_after_contract_read
        future = executor.submit(commit_final_opportunity)
        before_commit = validator.validate_collection_contract(config=config)
        future.result(timeout=10)
        validator.collection_contract = original
        after_commit = validator.validate_collection_contract(config=config)

    assert before_commit.committed_opportunity_count == 599
    assert before_commit.collection_state == "active"
    assert after_commit.committed_opportunity_count == 600
    assert after_commit.collection_state == "completed"
    assert after_commit.completion_timestamp is not None
    assert after_commit.last_committed_opportunity_identity is not None


@pytest.mark.parametrize("stress_iteration", range(5))
def test_target_600_thread_race_is_atomic_and_restart_safe(
    tmp_path: Path,
    config: RFC008Config,
    stress_iteration: int,
) -> None:
    authorization_path, ledger_path = seed_active_collection_at_599(
        tmp_path,
        config,
        first_round_id=352000 + stress_iteration * 1000,
    )
    start = Event()

    def attempt(round_id: int) -> str:
        with RFC008Store(ledger_path, config=config) as store:
            assert start.wait(timeout=10)
            try:
                with store.connection:
                    commit_opportunity(store, config, round_id)
                return "committed"
            except CollectionTargetReached:
                return "target_reached"
            except CollectionContractError:
                return "contract_mismatch"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(attempt, 360000),
            executor.submit(attempt, 360001),
        )
        start.set()
        results = [future.result(timeout=10) for future in futures]
    assert results.count("committed") == 1
    assert results.count("target_reached") == 1
    assert results.count("contract_mismatch") == 0
    with RFC008Store(
        ledger_path, config=config, read_only=True
    ) as store:
        contract = store.validate_collection_contract(config=config)
        assert contract.committed_opportunity_count == 600
        assert contract.collection_state == "completed"
        assert contract.completion_timestamp
        assert contract.last_committed_opportunity_identity
        assert store.count("decision_snapshots") == 600
        ledger_instance = contract.ledger_instance_identifier
    with CollectionAuthorizationStore(authorization_path) as authorization:
        completed = authorization.reconcile_completed_ledger(ledger_instance)
        assert completed.lifecycle_state == "completed"
    with RFC008Store(ledger_path, config=config) as store:
        with pytest.raises(CollectionTargetReached):
            commit_opportunity(store, config, 352002)
        assert store.collection_contract().committed_opportunity_count == 600


@pytest.mark.parametrize("stress_iteration", range(3))
def test_target_600_process_race_has_one_winner(
    tmp_path: Path,
    config: RFC008Config,
    stress_iteration: int,
) -> None:
    _, ledger_path = seed_active_collection_at_599(
        tmp_path,
        config,
        first_round_id=370000 + stress_iteration * 1000,
    )
    context = multiprocessing.get_context("fork")
    start = context.Event()
    ready = context.Queue()
    results = context.Queue()
    config_path = str(
        Path(__file__).parents[2] / "config/collection/rfc008_paper_v1.json"
    )
    processes = tuple(
        context.Process(
            target=process_final_opportunity,
            args=(
                str(ledger_path),
                config_path,
                round_id,
                start,
                ready,
                results,
            ),
        )
        for round_id in (380000, 380001)
    )
    for process in processes:
        process.start()
    assert [ready.get(timeout=10) for _ in processes] == ["ready", "ready"]
    start.set()
    outcomes = [results.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0

    assert outcomes.count("committed") == 1
    assert outcomes.count("target_reached") == 1
    assert outcomes.count("contract_mismatch") == 0
    with RFC008Store(
        ledger_path, config=config, read_only=True
    ) as store:
        contract = store.validate_collection_contract(config=config)
        assert contract.committed_opportunity_count == 600
        assert contract.collection_state == "completed"
        assert store.count("decision_snapshots") == 600


def test_last_identity_uses_formal_commit_sequence_not_round_order(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    _, ledger_path = issue_and_initialize(tmp_path, config)
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            store.begin_collection_session("ordering-session")
            assert commit_opportunity(store, config, 390100)
            assert commit_opportunity(store, config, 390000)
        rows = store.connection.execute(
            """
            SELECT committed_opportunity_sequence,round_id,snapshot_id
            FROM decision_snapshots
            ORDER BY committed_opportunity_sequence
            """
        ).fetchall()
        contract = store.validate_collection_contract(config=config)

    assert [(row[0], row[1]) for row in rows] == [
        (1, 390100),
        (2, 390000),
    ]
    assert contract.committed_opportunity_count == 2
    assert contract.collection_state == "active"
    assert contract.last_committed_opportunity_identity == rows[-1][2]


@pytest.mark.parametrize(
    "corruption",
    (
        "wrong_below_target",
        "missing_below_target",
        "unexpected_at_zero",
        "wrong_at_completion",
    ),
)
def test_last_identity_corruption_fails_closed(
    tmp_path: Path,
    config: RFC008Config,
    corruption: str,
) -> None:
    if corruption == "unexpected_at_zero":
        _, ledger_path = issue_and_initialize(tmp_path, config)
        replacement = "wrong-identity"
    elif corruption == "wrong_at_completion":
        _, ledger_path = seed_active_collection_at_599(
            tmp_path,
            config,
            first_round_id=391000,
        )
        with RFC008Store(ledger_path, config=config) as store:
            with store.connection:
                assert commit_opportunity(store, config, 391599)
        replacement = "wrong-identity"
    else:
        _, ledger_path = issue_and_initialize(tmp_path, config)
        with RFC008Store(ledger_path, config=config) as store:
            with store.connection:
                store.begin_collection_session("corruption-session")
                assert commit_opportunity(store, config, 392000)
                assert commit_opportunity(store, config, 391999)
            prior = store.connection.execute(
                """
                SELECT snapshot_id FROM decision_snapshots
                WHERE committed_opportunity_sequence=1
                """
            ).fetchone()[0]
        replacement = (
            None if corruption == "missing_below_target" else str(prior)
        )

    force_last_opportunity_identity(ledger_path, replacement)
    with pytest.raises(CollectionContractError):
        RFC008Store(ledger_path, config=config, read_only=True)


def test_missing_canonical_last_row_fails_closed(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    _, ledger_path = issue_and_initialize(tmp_path, config)
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            assert commit_opportunity(store, config, 393000)
            assert commit_opportunity(store, config, 393001)
    connection = sqlite3.connect(ledger_path)
    connection.execute("DROP TRIGGER decision_snapshot_no_delete")
    connection.execute(
        """
        DELETE FROM decision_snapshots
        WHERE committed_opportunity_sequence=2
        """
    )
    connection.commit()
    connection.close()
    with pytest.raises(CollectionContractError):
        RFC008Store(ledger_path, config=config, read_only=True)


def test_correct_last_identity_at_completion_passes(
    tmp_path: Path,
    config: RFC008Config,
) -> None:
    _, ledger_path = seed_active_collection_at_599(
        tmp_path,
        config,
        first_round_id=394000,
    )
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            assert commit_opportunity(store, config, 394599)
        contract = store.validate_collection_contract(config=config)
        final = store.connection.execute(
            """
            SELECT snapshot_id FROM decision_snapshots
            WHERE committed_opportunity_sequence=600
            """
        ).fetchone()[0]
        arm_count = store.connection.execute(
            "SELECT COUNT(*) FROM arm_decisions WHERE round_id=394599"
        ).fetchone()[0]

    assert contract.completed
    assert contract.committed_opportunity_count == 600
    assert contract.last_committed_opportunity_identity == final
    assert contract.completion_timestamp is not None
    assert arm_count == 5


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_text_below_target",
        "prior_identity_below_target",
        "null_below_target",
        "wrong_text_after_completion",
        "prior_identity_after_completion",
        "null_after_completion",
        "unexpected_at_zero",
    ),
)
def test_direct_sql_last_identity_mutation_is_rejected(
    tmp_path: Path,
    config: RFC008Config,
    mutation: str,
) -> None:
    completed = mutation.endswith("after_completion")
    if completed:
        _, ledger_path = seed_active_collection_at_599(
            tmp_path,
            config,
            first_round_id=395000,
        )
        with RFC008Store(ledger_path, config=config) as store:
            with store.connection:
                assert commit_opportunity(store, config, 395599)
            prior = store.connection.execute(
                """
                SELECT snapshot_id FROM decision_snapshots
                WHERE committed_opportunity_sequence=599
                """
            ).fetchone()[0]
    else:
        _, ledger_path = issue_and_initialize(tmp_path, config)
        prior = "unused"
        if mutation != "unexpected_at_zero":
            with RFC008Store(ledger_path, config=config) as store:
                with store.connection:
                    assert commit_opportunity(store, config, 396000)
                    assert commit_opportunity(store, config, 396001)
                prior = store.connection.execute(
                    """
                    SELECT snapshot_id FROM decision_snapshots
                    WHERE committed_opportunity_sequence=1
                    """
                ).fetchone()[0]
    replacement = (
        None
        if mutation.startswith("null")
        else prior
        if mutation.startswith("prior_identity")
        else "wrong-identity"
    )
    connection = sqlite3.connect(ledger_path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            UPDATE collection_contract
            SET last_committed_opportunity_identity=?
            WHERE singleton=1
            """,
            (replacement,),
        )
    connection.close()
    with RFC008Store(
        ledger_path,
        config=config,
        read_only=True,
    ) as store:
        store.validate_collection_contract(config=config)


def test_collector_requests_its_own_shutdown_at_600_without_downstream_work(
    config: RFC008Config,
    marker_file,
    tmp_path: Path,
) -> None:
    marker_path, marker_digest = marker_file
    authorization_path, ledger_path = issue_and_initialize(
        tmp_path,
        config,
        marker_sha256=marker_digest,
    )
    marker_before = marker_path.read_bytes()
    with (
        CollectionAuthorizationStore(authorization_path) as authorization,
        RFC008Store(ledger_path, config=config) as value,
    ):
        with value.connection:
            for round_id in range(353000, 353599):
                assert commit_opportunity(value, config, round_id)
        collector = RFC008Collector(
            store=value,
            config=config,
            marker_path=marker_path,
            expected_marker_sha256=marker_digest,
            authorization_store=authorization,
            session_identifier="fixture-session",
        )
        with value.connection:
            collector.begin_run()
        with value.connection:
            collector.process_record(raw_record(353599, 1))
        assert collector.stop_requested.is_set()
        assert value.collection_contract().completed
        assert value.collection_contract().committed_opportunity_count == 600
        with value.connection:
            collector.finish_run()
        assert authorization.status().lifecycle_state == "completed"
        assert value.collection_contract().active_session_identity is None
        collector.run()
        assert (
            value.connection.execute(
                "SELECT COUNT(*) FROM collector_runs"
            ).fetchone()[0]
            == 1
        )
    assert marker_path.read_bytes() == marker_before
    assert not (tmp_path / "data/freeze").exists()
    assert not (tmp_path / "data/analysis").exists()


def test_crash_after_600_reconciliation_is_fail_closed_and_idempotent(
    config: RFC008Config,
    marker_file,
    tmp_path: Path,
) -> None:
    marker_path, marker_digest = marker_file
    authorization_path, ledger_path = seed_active_collection_at_599(
        tmp_path,
        config,
        first_round_id=397000,
    )
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            assert commit_opportunity(store, config, 397599)
        crashed = store.validate_collection_contract(config=config)
        canonical = store.connection.execute(
            """
            SELECT
              COUNT(*) AS row_count,
              MIN(committed_opportunity_sequence) AS minimum_sequence,
              MAX(committed_opportunity_sequence) AS maximum_sequence,
              MAX(
                CASE WHEN committed_opportunity_sequence=600
                THEN snapshot_id END
              ) AS final_identity
            FROM decision_snapshots
            """
        ).fetchone()
        assert crashed.completed
        assert crashed.committed_opportunity_count == 600
        assert canonical["row_count"] == 600
        assert canonical["minimum_sequence"] == 1
        assert canonical["maximum_sequence"] == 600
        assert (
            crashed.last_committed_opportunity_identity
            == canonical["final_identity"]
        )
        assert crashed.active_session_identity == "crashed-session"
        with pytest.raises(CollectionTargetReached):
            commit_opportunity(store, config, 397600)
        with pytest.raises(CollectionTargetReached):
            store.begin_collection_session("new-session", recovery=True)
        collector = RFC008Collector(
            store=store,
            config=config,
            marker_path=marker_path,
            expected_marker_sha256=marker_digest,
        )
        with store.connection:
            collector.process_record(raw_record(397600, 1))
        assert store.count("decision_snapshots") == 600
        with store.connection:
            reconciled = store.reconcile_completed_session()
        assert reconciled.active_session_identity is None
        with store.connection:
            repeated = store.reconcile_completed_session()
        assert repeated.active_session_identity is None

    with CollectionAuthorizationStore(authorization_path) as authorization:
        active = authorization.status()
        assert active.lifecycle_state == "active"
        with pytest.raises(
            PermissionError,
            match="reconciliation identity mismatch",
        ):
            authorization.reconcile_completed_ledger("wrong-ledger")
        completed = authorization.reconcile_completed_ledger(
            crashed.ledger_instance_identifier
        )
        repeated = authorization.reconcile_completed_ledger(
            crashed.ledger_instance_identifier
        )
        assert completed.lifecycle_state == "completed"
        assert repeated.lifecycle_state == "completed"
        assert repeated.completed_at == completed.completed_at
        assert (
            authorization.connection.execute(
                """
                SELECT COUNT(*) FROM authorization_events
                WHERE action='completed'
                """
            ).fetchone()[0]
            == 1
        )

    copied = tmp_path / "copied-ledger.sqlite"
    shutil.copy2(ledger_path, copied)
    with pytest.raises(CollectionContractError):
        with RFC008Store(
            copied,
            config=config,
            read_only=True,
        ) as copied_store:
            copied_store.validate_collection_contract(config=config)


def test_completed_recovery_command_reconciles_without_starting_collector(
    config: RFC008Config,
    marker_file,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    marker_path, marker_digest = marker_file
    authorization_path, ledger_path = seed_active_collection_at_599(
        tmp_path,
        config,
        first_round_id=398000,
    )
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            assert commit_opportunity(store, config, 398599)
        assert store.collection_contract().active_session_identity

    readiness = SimpleNamespace(
        ready=True,
        gate_reasons=(),
        active_release_validation=SimpleNamespace(
            parsed_active_approval={
                "validated_production_marker_sha256": marker_digest,
            },
        ),
    )
    monkeypatch.setattr(
        rfc008_cli,
        "validate_collection_preflight",
        lambda **_kwargs: readiness,
    )

    def provider_forbidden(*_args, **_kwargs):
        raise AssertionError("completed recovery reached outcome providers")

    monkeypatch.setattr(rfc008_cli, "RpcRecoveryProvider", provider_forbidden)
    args = argparse.Namespace(
        recovery=True,
        repository_root=str(tmp_path),
        config=str(Path("config/collection/rfc008_paper_v1.json")),
        resolver_config=str(Path("config/collection/rfc008_resolver_v1.json")),
        burn_in_evidence=str(tmp_path / "unused-burn.json"),
        release_approval=str(tmp_path / "unused-approval.json"),
        approval_manifest=str(tmp_path / "unused-manifest.json"),
        marker=str(marker_path),
        expected_marker_sha256=marker_digest,
        expected_marker_sha256_file=None,
        ledger=str(ledger_path),
        authorization=str(authorization_path),
    )

    rfc008_cli._command_run(args)
    first = json.loads(capsys.readouterr().out)
    assert first["collection_state"] == "completed"
    assert first["committed_opportunity_count"] == 600
    assert first["authorization_state"] == "completed"
    assert first["collector_started"] is False
    with RFC008Store(ledger_path, config=config, read_only=True) as store:
        assert store.collection_contract().active_session_identity is None
        assert (
            store.connection.execute(
                "SELECT COUNT(*) FROM collector_runs"
            ).fetchone()[0]
            == 0
        )

    rfc008_cli._command_run(args)
    second = json.loads(capsys.readouterr().out)
    assert second == first
    with CollectionAuthorizationStore(
        authorization_path,
        read_only=True,
    ) as authorization:
        assert authorization.status().lifecycle_state == "completed"


def test_preflight_classifies_completed_active_authorization_as_reconciliation(
    config: RFC008Config,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    ledger_relative = "data/ledger/rfc008_paper_ledger_v1.sqlite"
    authorization_relative = (
        "data/ledger/rfc008_collection_authorization_v1.sqlite"
    )
    (root / "data/ledger").mkdir(parents=True)
    record = record_for(
        root,
        config,
        ledger_name=ledger_relative,
        authorization_name=authorization_relative,
    )
    authorization_path = Path(record.authorization_storage_path)
    ledger_path = Path(record.canonical_ledger_path)
    CollectionAuthorizationStore.issue(authorization_path, record)
    with CollectionAuthorizationStore(authorization_path) as authorization:
        authorization.consume_initialization()
        create_authorized_ledger(
            ledger_path,
            config=config,
            initialization=LedgerInitialization(
                authorization=record,
                collection_seed_cursors=(
                    {"source_path": "/tmp/source", "source_byte_offset": 10},
                ),
                publication_cursors=(
                    {"source_path": "/tmp/source", "source_byte_offset": 10},
                ),
            ),
        )
        authorization.mark_initialized()
        authorization.consume_launch("crashed-session")
    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            store.begin_collection_session("crashed-session")
            for round_id in range(399000, 399600):
                assert commit_opportunity(store, config, round_id)

    approval = {
        "validated_production_marker_sha256": record.marker_sha256,
        "validated_production_marker_sidecar_sha256": (
            record.marker_sidecar_sha256
        ),
        "candidate_configuration_sha256": record.candidate_sha256,
        "resolver_configuration_sha256": record.resolver_fingerprint,
        "migration_set_sha256": record.migration_set_sha256,
        "cli_sha256": record.cli_sha256,
        "runbook_sha256": record.runbook_sha256,
        "validated_operational_burn_in_evidence_sha256": (
            record.burn_in_evidence_sha256
        ),
        "validated_operational_burn_in_ledger_sha256": (
            record.burn_in_ledger_sha256
        ),
        "frozen_approval_manifest_sha256": (
            record.approval_manifest_sha256
        ),
        "verification": {"external_rpc_burn_in_performed": True},
    }
    release = SimpleNamespace(
        valid=True,
        checks=(),
        parsed_active_approval=approval,
        active_approval_sha256=record.active_approval_sha256,
        approval_hashes=(
            record.active_approval_sha256,
            record.approval_chain_anchor,
        ),
    )
    monkeypatch.setattr(
        rfc008_lifecycle,
        "validate_active_release",
        lambda **_kwargs: release,
    )
    monkeypatch.setattr(
        rfc008_lifecycle,
        "validate_post_marker_pre_collection_state",
        lambda **_kwargs: {"ready": True, "failures": []},
    )
    monkeypatch.setattr(
        rfc008_lifecycle,
        "repository_release_authority",
        lambda **_kwargs: SimpleNamespace(
            branch=record.branch,
            implementation_commit=record.implementation_commit,
            predecessor_approval_sha256=(
                record.immediate_predecessor_sha256
            ),
        ),
    )
    monkeypatch.setattr(
        rfc008_lifecycle.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout=record.repository_head + "\n"
        ),
    )
    paths = {
        "repository_root": root,
        "config_path": Path("config/collection/rfc008_paper_v1.json"),
        "resolver_config_path": Path("unused-resolver.json"),
        "burn_in_evidence_path": Path("unused-burn.json"),
        "release_approval_path": Path("unused-approval.json"),
        "approval_manifest_path": Path("unused-manifest.json"),
        "marker_path": root / "data/ledger/rfc008_marker_v1.json",
        "authorization_path": authorization_path,
        "ledger_path": ledger_path,
        "collector_running": False,
    }
    recovery = rfc008_lifecycle.validate_collection_preflight(
        **paths,
        action="recovery",
    )
    launch = rfc008_lifecycle.validate_collection_preflight(
        **paths,
        action="launch",
    )
    assert recovery.collection_completed
    assert recovery.reconciliation_required
    assert recovery.recovery_permitted
    assert recovery.ready
    assert "collection_completed" in recovery.gate_reasons
    assert not launch.ready

    with RFC008Store(ledger_path, config=config) as store:
        with store.connection:
            contract = store.reconcile_completed_session()
    with CollectionAuthorizationStore(authorization_path) as authorization:
        authorization.reconcile_completed_ledger(
            contract.ledger_instance_identifier
        )
    repeated = rfc008_lifecycle.validate_collection_preflight(
        **paths,
        action="recovery",
    )
    assert repeated.collection_completed
    assert not repeated.reconciliation_required
    assert repeated.recovery_permitted
    assert repeated.ready


@pytest.mark.parametrize(
    ("stored_count", "state"),
    ((599, "completed"), (601, "active")),
)
def test_counter_or_state_corruption_fails_closed(
    tmp_path: Path,
    config: RFC008Config,
    stored_count: int,
    state: str,
) -> None:
    _, ledger_path = issue_and_initialize(tmp_path, config)
    connection = sqlite3.connect(ledger_path)
    connection.execute("PRAGMA ignore_check_constraints=ON")
    connection.execute(
        """
        UPDATE collection_contract
        SET committed_opportunity_count=?,collection_state=?
        WHERE singleton=1
        """,
        (stored_count, state),
    )
    connection.commit()
    connection.close()
    with pytest.raises(CollectionContractError):
        RFC008Store(ledger_path, config=config, read_only=True)
