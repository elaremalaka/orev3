from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from orev3.collection.schemas import CompleteOpportunity
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.decisions import build_decisions, snapshot_from_opportunity
from orev3.rfc008.migrations import APPLICATION_ID, MIGRATIONS, apply_migrations
from orev3.rfc008.storage import RFC008Store
import orev3.rfc008.storage as storage_module
from orev3.rfc009.continuation import (
    CANONICAL_APPROVAL,
    CONTINUATION_ACTIVATION_TOKEN,
    ContinuationApproval,
    ContinuationPreflight,
    LegacyContinuationApproval,
    _continuation_identifier,
    _decode_approval,
    _release_epochs,
    _strict_json,
    _validate_interrupted_ledger,
    activate_continuation,
    build_continuation_approval,
    canonical_approval_path,
    continuity_state_sha256,
    issue_continuation_approval,
    semantic_compatibility_sha256,
    validate_release_epoch_chain,
)
import orev3.rfc009.continuation as continuation_module


def _approval(**changes):
    value = {
        "artifact_type": "rfc009_continuation_approval",
        "schema_version": 1,
        "continuation_schema_version": 2,
        "rfc_identifier": "RFC-009",
        "continuation_identifier": "09b577bf-23d5-5aeb-8c6b-5d3eab71e42d",
        "created_at": "2026-07-29T00:00:00+00:00",
        "original_authorization_identifier": "original",
        "original_authorization_digest": "1" * 64,
        "ledger_instance_identifier": "ledger",
        "ledger_path_identity": "2" * 64,
        "starting_committed_count": 100,
        "starting_last_opportunity_identity": "snapshot-100",
        "continuity_state_sha256": "3" * 64,
        "successor_release_approval_sha256": "4" * 64,
        "approved_implementation_diff_sha256": "5" * 64,
        "semantic_compatibility_sha256": "6" * 64,
        "release_epoch_number": 2,
        "predecessor_epoch_number": 1,
        "predecessor_authority_identifier": "original",
        "predecessor_authority_digest": "1" * 64,
        "predecessor_release_approval_sha256": "7" * 64,
    }
    value.update(changes)
    if "continuation_identifier" not in changes:
        value["continuation_identifier"] = _continuation_identifier(value)
    return value


def test_continuation_schema_is_strict_and_digest_is_deterministic() -> None:
    first = ContinuationApproval.model_validate(_approval())
    second = ContinuationApproval.model_validate(_approval())
    assert first.digest == second.digest
    with pytest.raises(ValidationError):
        ContinuationApproval.model_validate(_approval(extra=True))
    with pytest.raises(ValidationError):
        ContinuationApproval.model_validate(
            _approval(starting_committed_count=0)
        )
    with pytest.raises(ValidationError, match="follow predecessor"):
        ContinuationApproval.model_validate(
            _approval(release_epoch_number=4, predecessor_epoch_number=2)
        )


def test_legacy_approval_schema_remains_byte_compatible() -> None:
    value = _approval()
    for field in (
        "continuation_schema_version",
        "release_epoch_number",
        "predecessor_epoch_number",
        "predecessor_authority_identifier",
        "predecessor_authority_digest",
        "predecessor_release_approval_sha256",
    ):
        value.pop(field)
    value["continuation_identifier"] = _continuation_identifier(value)
    decoded = _decode_approval(
        (__import__("json").dumps(value, sort_keys=True) + "\n").encode()
    )
    assert isinstance(decoded, LegacyContinuationApproval)


def test_release_epochs_are_additive_unique_and_immutable(
    tmp_path: Path,
) -> None:
    config = RFC008Config.from_path(
        "config/collection/rfc008_paper_v1.json"
    )
    path = tmp_path / "ledger.sqlite"
    with RFC008Store(path, config=config, create=True) as store:
        epochs = store.release_epochs()
        assert len(epochs) == 1
        assert epochs[0]["epoch_number"] == 1
        assert epochs[0]["start_sequence"] == 1
        with pytest.raises(sqlite3.IntegrityError):
            store.connection.execute(
                "UPDATE collection_release_epochs SET start_sequence=2"
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.connection.execute(
                "DELETE FROM collection_release_epochs"
            )


def test_continuity_and_semantic_hashes_are_stable(tmp_path: Path) -> None:
    config = RFC008Config.from_path(
        "config/collection/rfc008_paper_v1.json"
    )
    path = tmp_path / "ledger.sqlite"
    with RFC008Store(path, config=config, create=True) as store:
        first = continuity_state_sha256(
            store.connection, ledger_path=path
        )
        second = continuity_state_sha256(
            store.connection, ledger_path=path
        )
        assert first == second
        contract = store.collection_contract()
        assert semantic_compatibility_sha256(
            contract.immutable_release
        ) == semantic_compatibility_sha256(contract.immutable_release)


def _built_approval(tmp_path: Path) -> ContinuationApproval:
    config = RFC008Config.from_path(
        "config/collection/rfc008_paper_v1.json"
    )
    with RFC008Store(
        tmp_path / "fixture.sqlite", config=config, create=True
    ) as store:
        authorization = store.collection_contract().immutable_release
    return build_continuation_approval(
        created_at="2026-07-29T00:00:00+00:00",
        authorization=authorization,
        starting_committed_count=100,
        starting_last_opportunity_identity="snapshot-100",
        continuity_sha256="3" * 64,
        successor_release_approval_sha256="4" * 64,
        implementation_diff_sha256_value="5" * 64,
    )


def _commit_opportunity(
    store: RFC008Store,
    config: RFC008Config,
    round_id: int,
) -> None:
    opportunity = CompleteOpportunity(
        round_id=round_id,
        observation_index=1,
        observed_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
        rpc_slot=500,
        start_slot=400,
        end_slot=575,
        slots_remaining=75,
        miner_counts=[5] * 25,
        deployed_lamports=[250000] * 25,
        reward_raw=[0] * 25,
        treasury_motherlode_raw=0,
        source_reference=f"fixture:{round_id}",
    )
    snapshot = snapshot_from_opportunity(
        opportunity,
        config,
        source_content_sha256=f"{round_id:064x}"[-64:],
    )
    assert store.insert_snapshot_and_decisions(
        snapshot, build_decisions(snapshot, config)
    )


def _activate_fixture_epoch(
    store: RFC008Store,
    *,
    epoch: int,
    release: str,
    identifier: str,
    digest: str,
) -> None:
    if epoch == 2:
        store.connection.execute(
            """
            INSERT INTO collection_release_epochs
            VALUES (2,?,?,'rfc009_continuation',?,?,?)
            """,
            (
                store.collection_contract().committed_opportunity_count + 1,
                release,
                identifier,
                digest,
                "2026-07-29T00:00:00+00:00",
            ),
        )
        return
    predecessor = store.release_epochs()[-1]
    store.connection.execute(
        """
        INSERT INTO collection_release_successor_epochs(
          epoch_number,start_sequence,release_approval_sha256,
          authority_type,authority_identifier,authority_digest,activated_at,
          predecessor_epoch_number,predecessor_authority_identifier,
          predecessor_authority_digest,predecessor_release_approval_sha256
        ) VALUES (?, ?,?,'rfc009_continuation',?,?,?,?,?,?,?)
        """,
        (
            epoch,
            store.collection_contract().committed_opportunity_count + 1,
            release,
            identifier,
            digest,
            "2026-07-29T00:00:00+00:00",
            predecessor["epoch_number"],
            predecessor["authority_identifier"],
            predecessor["authority_digest"],
            predecessor["release_approval_sha256"],
        ),
    )


def test_successor_epoch_chain_is_linear_immutable_and_replay_safe(
    tmp_path: Path,
) -> None:
    config = RFC008Config.from_path(
        "config/collection/rfc008_paper_v1.json"
    )
    path = tmp_path / "ledger.sqlite"
    with RFC008Store(path, config=config, create=True) as store:
        authorization = store.collection_contract().immutable_release
        _commit_opportunity(store, config, 1)
        _activate_fixture_epoch(
            store,
            epoch=2,
            release="2" * 64,
            identifier="epoch-2",
            digest="a" * 64,
        )
        _commit_opportunity(store, config, 2)
        _activate_fixture_epoch(
            store,
            epoch=3,
            release="3" * 64,
            identifier="epoch-3",
            digest="b" * 64,
        )
        _commit_opportunity(store, config, 3)
        _activate_fixture_epoch(
            store,
            epoch=4,
            release="4" * 64,
            identifier="epoch-4",
            digest="c" * 64,
        )
        epochs = _release_epochs(store.connection)
        validate_release_epoch_chain(epochs, authorization=authorization)
        assert [row["epoch_number"] for row in epochs] == [1, 2, 3, 4]
        assert store.release_epochs()[-1]["authority_identifier"] == "epoch-4"
        with pytest.raises(sqlite3.IntegrityError):
            _activate_fixture_epoch(
                store,
                epoch=4,
                release="5" * 64,
                identifier="replay",
                digest="d" * 64,
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.connection.execute(
                """
                UPDATE collection_release_successor_epochs
                SET predecessor_authority_identifier='fork'
                WHERE epoch_number=3
                """
            )


@pytest.mark.parametrize(
    "corruption",
    ("skipped", "fork", "cycle", "duplicate"),
)
def test_chain_validation_rejects_ambiguous_history(
    tmp_path: Path, corruption: str
) -> None:
    config = RFC008Config.from_path(
        "config/collection/rfc008_paper_v1.json"
    )
    path = tmp_path / "ledger.sqlite"
    with RFC008Store(path, config=config, create=True) as store:
        authorization = store.collection_contract().immutable_release
        original = dict(_release_epochs(store.connection)[0])
    second = {
        "epoch_number": 2,
        "start_sequence": 2,
        "release_approval_sha256": "2" * 64,
        "authority_type": "rfc009_continuation",
        "authority_identifier": "epoch-2",
        "authority_digest": "a" * 64,
        "activated_at": "2026-07-29T00:00:00+00:00",
        "predecessor_epoch_number": None,
        "predecessor_authority_identifier": None,
        "predecessor_authority_digest": None,
        "predecessor_release_approval_sha256": None,
    }
    third = {
        **second,
        "epoch_number": 3,
        "start_sequence": 3,
        "release_approval_sha256": "3" * 64,
        "authority_identifier": "epoch-3",
        "authority_digest": "b" * 64,
        "predecessor_epoch_number": 2,
        "predecessor_authority_identifier": "epoch-2",
        "predecessor_authority_digest": "a" * 64,
        "predecessor_release_approval_sha256": "2" * 64,
    }
    epochs = [original, second, third]
    if corruption == "skipped":
        third["epoch_number"] = 4
    elif corruption == "fork":
        third["predecessor_authority_identifier"] = "other"
    elif corruption == "cycle":
        third["predecessor_authority_identifier"] = "epoch-3"
    else:
        third["authority_digest"] = second["authority_digest"]
    with pytest.raises(ValueError):
        validate_release_epoch_chain(
            tuple(epochs), authorization=authorization
        )


def test_schema_six_epoch_two_migrates_without_rewriting_history(
    tmp_path: Path,
) -> None:
    config = RFC008Config.from_path(
        "config/collection/rfc008_paper_v1.json"
    )
    path = tmp_path / "legacy.sqlite"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
    apply_migrations(connection, MIGRATIONS[:6])
    legacy = object.__new__(RFC008Store)
    legacy.path = path
    legacy.identity_path = path
    legacy.connection = connection
    current_schema = storage_module.SCHEMA_VERSION
    storage_module.SCHEMA_VERSION = 6
    try:
        legacy.initialize(
            config, RFC008Store._fixture_initialization(config, path)
        )
    finally:
        storage_module.SCHEMA_VERSION = current_schema
    _commit_opportunity(legacy, config, 1)
    _activate_fixture_epoch(
        legacy,
        epoch=2,
        release="2" * 64,
        identifier="epoch-2",
        digest="a" * 64,
    )
    before = legacy.release_epochs()
    connection.commit()
    connection.close()
    with RFC008Store(path, config=config, read_only=True) as read_only:
        assert read_only.release_epochs() == before
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    apply_migrations(connection)
    migrated = object.__new__(RFC008Store)
    migrated.path = path
    migrated.identity_path = path
    migrated.connection = connection
    after = migrated.release_epochs()
    assert before == after
    assert dict(
        connection.execute(
            "SELECT key,value FROM metadata WHERE key='schema_version'"
        )
    )["schema_version"] == "7"
    assert connection.execute(
        "SELECT COUNT(*) FROM collection_release_successor_epochs"
    ).fetchone()[0] == 0
    connection.close()


def test_activation_appends_exact_successor_and_rejects_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = Path("config/collection/rfc008_paper_v1.json")
    config = RFC008Config.from_path(config_path)
    path = tmp_path / "ledger.sqlite"
    with RFC008Store(path, config=config, create=True) as store:
        authorization = store.collection_contract().immutable_release
        _commit_opportunity(store, config, 1)
        _activate_fixture_epoch(
            store,
            epoch=2,
            release="2" * 64,
            identifier="epoch-2",
            digest="a" * 64,
        )
        _commit_opportunity(store, config, 2)
        contract = store.collection_contract()
        approval = build_continuation_approval(
            created_at="2026-07-29T00:00:00+00:00",
            authorization=authorization,
            starting_committed_count=2,
            starting_last_opportunity_identity=(
                contract.last_committed_opportunity_identity
            ),
            continuity_sha256=continuity_state_sha256(
                store.connection,
                ledger_path=path,
                include_release_epochs=True,
            ),
            successor_release_approval_sha256="3" * 64,
            implementation_diff_sha256_value="4" * 64,
            release_epoch_number=3,
            predecessor_epoch_number=2,
            predecessor_authority_identifier="epoch-2",
            predecessor_authority_digest="a" * 64,
            predecessor_release_approval_sha256="2" * 64,
        )
        store.connection.commit()

    def ready(**kwargs):
        return ContinuationPreflight(
            ready=True,
            activated=kwargs.get("require_activated", False),
            approval_sha256="f" * 64,
            continuation_identifier=approval.continuation_identifier,
            successor_release_approval_sha256=(
                approval.successor_release_approval_sha256
            ),
            starting_committed_count=2,
            current_committed_count=2,
            release_epochs=(),
            gate_reasons=(),
        )

    monkeypatch.setattr(continuation_module, "preflight_continuation", ready)
    monkeypatch.setattr(
        continuation_module,
        "_strict_json",
        lambda path: (approval, "f" * 64),
    )
    result = activate_continuation(
        authorization_token=CONTINUATION_ACTIVATION_TOKEN,
        config_path=config_path,
        ledger_path=path,
        continuation_approval_path=tmp_path / "approval.json",
    )
    assert result.ready
    with RFC008Store(path, config=config, read_only=True) as store:
        epochs = store.release_epochs()
        assert len(epochs) == 3
        assert epochs[-1]["epoch_number"] == 3
        assert epochs[-1]["authority_identifier"] == (
            approval.continuation_identifier
        )
    with pytest.raises(sqlite3.IntegrityError):
        activate_continuation(
            authorization_token=CONTINUATION_ACTIVATION_TOKEN,
            config_path=config_path,
            ledger_path=path,
            continuation_approval_path=tmp_path / "approval.json",
        )


def test_successor_approval_path_and_identifier_are_deterministic(
    tmp_path: Path,
) -> None:
    first = _built_approval(tmp_path)
    raw = first.model_dump(mode="json")
    raw.update(
        release_epoch_number=3,
        predecessor_epoch_number=2,
        predecessor_authority_identifier=first.continuation_identifier,
        predecessor_authority_digest=first.digest,
        predecessor_release_approval_sha256=(
            first.successor_release_approval_sha256
        ),
    )
    raw["continuation_identifier"] = _continuation_identifier(raw)
    successor = ContinuationApproval.model_validate(raw)
    assert successor == ContinuationApproval.model_validate(raw)
    assert canonical_approval_path(3).endswith("_epoch_3.json")


def test_issuance_boundary_uses_current_authoritative_epoch(
    tmp_path: Path,
) -> None:
    config = RFC008Config.from_path(
        "config/collection/rfc008_paper_v1.json"
    )
    path = tmp_path / "ledger.sqlite"
    with RFC008Store(path, config=config, create=True) as store:
        authorization = store.collection_contract().immutable_release
        _commit_opportunity(store, config, 1)
        _activate_fixture_epoch(
            store,
            epoch=2,
            release="2" * 64,
            identifier="epoch-2",
            digest="a" * 64,
        )
        _commit_opportunity(store, config, 2)
        store.connection.execute(
            """
            UPDATE collection_contract
            SET collection_state='active'
            WHERE singleton=1
            """
        )
        expected_last = (
            store.collection_contract().last_committed_opportunity_identity
        )
        store.connection.commit()
    count, last_identity, continuity, epochs = (
        _validate_interrupted_ledger(
            ledger_path=path,
            config=config,
            authorization=authorization,
        )
    )
    assert count == 2
    assert last_identity == expected_last
    assert len(continuity) == 64
    assert epochs[-1]["epoch_number"] == 2
    assert epochs[-1]["authority_identifier"] == "epoch-2"


def test_issuance_is_deterministic_valid_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    approval = _built_approval(tmp_path)
    root = tmp_path / "repository"
    output = root / CANONICAL_APPROVAL
    monkeypatch.setattr(
        continuation_module,
        "derive_continuation_approval",
        lambda **kwargs: approval,
    )
    first, first_digest = issue_continuation_approval(
        repository_root=root,
        continuation_approval_path=output,
    )
    first_bytes = output.read_bytes()
    parsed, parsed_digest = _strict_json(output)
    assert first == parsed == approval
    assert first_digest == parsed_digest
    with pytest.raises(FileExistsError):
        issue_continuation_approval(
            repository_root=root,
            continuation_approval_path=output,
        )
    output.unlink()
    second, second_digest = issue_continuation_approval(
        repository_root=root,
        continuation_approval_path=output,
    )
    assert output.read_bytes() == first_bytes
    assert second == first
    assert second_digest == first_digest


def test_successor_issuance_uses_epoch_specific_immutable_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _built_approval(tmp_path)
    raw = first.model_dump(mode="json")
    raw.update(
        release_epoch_number=3,
        predecessor_epoch_number=2,
        predecessor_authority_identifier=first.continuation_identifier,
        predecessor_authority_digest=first.digest,
        predecessor_release_approval_sha256=(
            first.successor_release_approval_sha256
        ),
    )
    raw["continuation_identifier"] = _continuation_identifier(raw)
    approval = ContinuationApproval.model_validate(raw)
    root = tmp_path / "repository"
    output = root / canonical_approval_path(3)
    monkeypatch.setattr(
        continuation_module,
        "derive_continuation_approval",
        lambda **kwargs: approval,
    )
    persisted, _ = issue_continuation_approval(
        repository_root=root,
        continuation_approval_path=output,
    )
    assert persisted == approval
    with pytest.raises(FileExistsError):
        issue_continuation_approval(
            repository_root=root,
            continuation_approval_path=output,
        )


@pytest.mark.parametrize(
    ("exception", "message"),
    (
        (PermissionError, "authorization invalid"),
        (ValueError, "ledger invalid"),
        (PermissionError, "successor release invalid"),
    ),
)
def test_issuance_fails_closed_on_invalid_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exception: type[Exception],
    message: str,
) -> None:
    root = tmp_path / "repository"
    output = root / CANONICAL_APPROVAL

    def reject(**kwargs):
        raise exception(message)

    monkeypatch.setattr(
        continuation_module, "derive_continuation_approval", reject
    )
    with pytest.raises(exception, match=message):
        issue_continuation_approval(
            repository_root=root,
            continuation_approval_path=output,
        )
    assert not output.exists()
