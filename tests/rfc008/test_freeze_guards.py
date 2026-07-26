from __future__ import annotations

import sqlite3

import pytest

from orev3.rfc008.freeze import (
    FINAL_FREEZE_AUTHORIZATION,
    freeze_experiment,
)
from orev3.rfc008.outcomes import enqueue_pending
from orev3.rfc008.writer import RFC008WriterLease

from .conftest import CONFIG_PATH


def freeze_args(path, marker, digest, output):
    return {
        "ledger_path": path,
        "config_path": CONFIG_PATH,
        "marker_path": marker,
        "expected_marker_sha256": digest,
        "output_path": output,
        "collection_stop_reason": "fixture_terminal_boundary",
    }


def test_final_freeze_requires_authorization_and_no_active_writer(
    store, marker_file, tmp_path
):
    _, path = store
    marker, digest = marker_file
    arguments = freeze_args(path, marker, digest, tmp_path / "freeze.json")
    with pytest.raises(PermissionError):
        freeze_experiment(**arguments, authorization_token="wrong")
    with RFC008WriterLease(path):
        with pytest.raises(ValueError, match="writer lease"):
            freeze_experiment(
                **arguments,
                authorization_token=FINAL_FREEZE_AUTHORIZATION,
            )
    assert not (tmp_path / "freeze.json").exists()


def test_pending_outcome_blocks_freeze(store, marker_file, tmp_path):
    value, path = store
    marker, digest = marker_file
    with value.connection:
        from datetime import datetime, timezone

        value.start_round(346300, datetime(2026, 7, 25, tzinfo=timezone.utc))
        enqueue_pending(
            value, 346300, at=datetime(2026, 7, 25, tzinfo=timezone.utc)
        )
    with pytest.raises(ValueError, match="Pending"):
        freeze_experiment(
            **freeze_args(path, marker, digest, tmp_path / "freeze.json"),
            authorization_token=FINAL_FREEZE_AUTHORIZATION,
        )


def test_freeze_is_idempotent_and_blocks_existing_connection_writes(
    store, marker_file, tmp_path
):
    value, path = store
    marker, digest = marker_file
    output = tmp_path / "freeze.json"
    arguments = freeze_args(path, marker, digest, output)
    first = freeze_experiment(
        **arguments, authorization_token=FINAL_FREEZE_AUTHORIZATION
    )
    second = freeze_experiment(
        **arguments, authorization_token=FINAL_FREEZE_AUTHORIZATION
    )
    assert first["ledger_frozen"]
    assert second["idempotent"]
    with pytest.raises(sqlite3.DatabaseError, match="frozen"):
        value.increment("should_not_write")
