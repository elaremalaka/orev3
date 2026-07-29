from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.storage import RFC008Store
from orev3.rfc009.continuation import (
    ContinuationApproval,
    continuity_state_sha256,
    semantic_compatibility_sha256,
)


def _approval(**changes):
    value = {
        "artifact_type": "rfc009_continuation_approval",
        "schema_version": 1,
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
    }
    value.update(changes)
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
