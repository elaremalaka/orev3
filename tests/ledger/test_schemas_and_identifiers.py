from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from orev3.ledger.event_types import EventType
from orev3.ledger.identifiers import (
    event_id,
    opportunity_id,
    source_record_id,
)
from orev3.ledger.schemas import LedgerEvent, TransactionCostRecord
from orev3.ledger.validation import assert_observational_only
from orev3.ledger.storage import LedgerStore

from .conftest import NOW, SIGNATURE


def event(**overrides) -> LedgerEvent:
    values = {
        "event_id": "event-1",
        "event_type": EventType.OBSERVATION_STARTED,
        "event_time": NOW,
        "observed_at": NOW,
        "source": "fixture",
        "source_record_id": "record-1",
        "run_id": "run-1",
        "session_id": "session-1",
        "round_id": 1,
        "payload": {},
    }
    values.update(overrides)
    return LedgerEvent(**values)


def test_valid_event_and_strict_json() -> None:
    value = event()
    encoded = value.model_dump_json()
    assert json.loads(encoded)["event_type"] == "observation_started"
    assert "NaN" not in encoded


def test_invalid_event_type_and_missing_identifier() -> None:
    with pytest.raises(ValidationError):
        event(event_type="not_an_event")
    with pytest.raises(ValidationError, match="requires"):
        event(round_id=None)


def test_non_finite_and_secret_payload_rejected() -> None:
    with pytest.raises(ValidationError, match="finite"):
        event(payload={"score": float("nan")})
    with pytest.raises(ValidationError, match="Secret material"):
        event(payload={"private_key": "forbidden"})


def test_invalid_wallet_and_signature_rejected() -> None:
    with pytest.raises(ValidationError, match="wallet"):
        event(wallet_public_key="not-a-wallet")
    with pytest.raises(ValidationError, match="signature"):
        event(transaction_signature="not-a-signature")


def test_negative_fees_and_inconsistent_fee_components_rejected() -> None:
    with pytest.raises(ValidationError):
        TransactionCostRecord(
            transaction_signature=SIGNATURE,
            base_fee_lamports=-1,
            total_fee_lamports=0,
            provenance="direct_rpc_observation",
        )
    with pytest.raises(ValidationError, match="components"):
        TransactionCostRecord(
            transaction_signature=SIGNATURE,
            base_fee_lamports=5,
            priority_fee_lamports=2,
            total_fee_lamports=8,
            provenance="direct_rpc_observation",
        )


def test_deterministic_identifiers_are_stable_and_distinct() -> None:
    assert opportunity_id(1, 2) == opportunity_id(1, 2)
    assert opportunity_id(1, 2) != opportunity_id(1, 3)
    first = source_record_id("a", 1, {"x": 1})
    assert first == source_record_id("a", 1, {"x": 1})
    assert first != source_record_id("a", 2, {"x": 1})
    assert event_id("x", "a", first) == event_id("x", "a", first)


def test_unknown_ledger_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO metadata VALUES ('schema_version', '999')")
    connection.commit()
    connection.close()
    with LedgerStore(path) as store:
        with pytest.raises(ValueError, match="Unsupported"):
            store.initialize()


@pytest.mark.parametrize(
    "kwargs", [{"submit": True}, {"sign": True}, {"claim": True}, {"build_transaction": True}]
)
def test_live_actions_are_forbidden(kwargs: dict) -> None:
    with pytest.raises(PermissionError, match="observational only"):
        assert_observational_only(**kwargs)
