from __future__ import annotations

import json
import multiprocessing
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from pydantic import ValidationError

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
              snapshot_id,round_id,source_content_sha256,record_json
            ) VALUES (?,?,?,?)
            """,
            (
                snapshot.snapshot_id,
                snapshot.round_id,
                snapshot.source_content_sha256,
                snapshot.model_dump_json(),
            ),
        )
        store.connection.execute("ROLLBACK TO SAVEPOINT crash_before_commit")
        store.connection.execute("RELEASE SAVEPOINT crash_before_commit")
        assert store.collection_contract().committed_opportunity_count == 1
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
