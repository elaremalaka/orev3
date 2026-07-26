from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from solders.pubkey import Pubkey

from orev3.collection.outcome_recovery import (
    EVIDENCE_FILENAME,
    FORMAL_GATE_B_MISSING_ROUNDS,
    GATE_B_CONTROL_ROUND,
    MANIFEST_FILENAME,
    create_recovery_artifact,
    requery_recovery_artifact,
    validate_output_path,
    validate_round_pda,
    verify_recovery_artifact,
)
from orev3.observer.accounts import ORE_PROGRAM_ID


GENESIS = "genesis-fixture"
PROGRAM_ID = str(ORE_PROGRAM_ID)
SAMPLE_ID = "gate-b-sample"
MARKER_HASH = ""
FROZEN_TIME = datetime(2026, 7, 26, 1, 0, tzinfo=timezone.utc)


def round_account_bytes(
    round_id: int,
    *,
    entropy: int = 26,
    deployed: list[int] | None = None,
    slot_hash: bytes | None = None,
) -> bytes:
    deployed = deployed or [round_id + index for index in range(25)]
    slot_hash = slot_hash or struct.pack("<QQQQ", entropy, 0, 0, 0)
    body = b"".join(
        (
            struct.pack("<Q", round_id),
            struct.pack("<25Q", *deployed),
            struct.pack("<25Q", *([0] * 25)),
            struct.pack("<25Q", *([1] * 25)),
            slot_hash,
            struct.pack("<Q", 999),
            struct.pack("<Q", 7),
            bytes(32),
            struct.pack("<25Q", *([2] * 25)),
            struct.pack("<Q", 1_000),
            struct.pack("<Q", 2_000),
            struct.pack("<Q", 25),
            bytes(32),
        )
    )
    return bytes([109]) + bytes(7) + body


class FixtureProvider:
    def __init__(
        self,
        provider_id: str,
        accounts: dict[str, bytes],
        *,
        genesis: str = GENESIS,
        owner: str = PROGRAM_ID,
        context_slot: int = 500,
    ) -> None:
        self.provider_id = provider_id
        self.accounts = accounts
        self.genesis = genesis
        self.owner = owner
        self.context_slot = context_slot
        self.closed = False

    def get_genesis_hash(self) -> str:
        return self.genesis

    def get_account_info_with_context(
        self,
        address: str,
        *,
        commitment: str,
    ) -> dict:
        assert commitment == "finalized"
        raw = self.accounts.get(address)
        return {
            "context": {"slot": self.context_slot},
            "value": (
                None
                if raw is None
                else {
                    "owner": self.owner,
                    "data": [
                        base64.b64encode(raw).decode("ascii"),
                        "base64",
                    ],
                }
            ),
        }

    def get_signatures_for_address(
        self,
        address: str,
        *,
        commitment: str,
        limit: int,
    ) -> list[dict]:
        assert commitment == "finalized"
        assert limit == 1
        return [
            {
                "signature": f"signature-{self.provider_id}",
                "slot": self.context_slot - 1,
                "blockTime": 1_785_000_000,
                "confirmationStatus": "finalized",
                "err": None,
            }
        ]

    def close(self) -> None:
        self.closed = True


def pda(round_id: int) -> str:
    from orev3.collection.outcome_recovery import _derive_round_pda

    return _derive_round_pda(round_id, PROGRAM_ID)


def marker(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "gate_b_marker.json"
    path.write_text(
        json.dumps({"sample_id": SAMPLE_ID}),
        encoding="utf-8",
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def control_ledger(tmp_path: Path) -> Path:
    path = tmp_path / "control.sqlite"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE final_outcomes (
                outcome_id TEXT PRIMARY KEY,
                round_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                record_json TEXT NOT NULL
            )
            """
        )
        raw = round_account_bytes(GATE_B_CONTROL_ROUND)
        deployed = list(
            struct.unpack_from("<25Q", raw, 8 + 8)
        )
        outcome = {
            "winner_square": 1,
            "final_square_deployments": deployed,
            "total_winnings": 2_000,
            "motherlode_raw": 7,
        }
        connection.execute(
            "INSERT INTO final_outcomes VALUES (?, ?, ?, ?)",
            (
                "control",
                GATE_B_CONTROL_ROUND,
                1,
                json.dumps(outcome),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return path


def provider_pair(
    round_ids: list[int],
) -> tuple[FixtureProvider, FixtureProvider]:
    accounts = {
        pda(round_id): round_account_bytes(round_id)
        for round_id in round_ids
    }
    return (
        FixtureProvider("primary", dict(accounts), context_slot=500),
        FixtureProvider("secondary", dict(accounts), context_slot=501),
    )


def create_one(
    tmp_path: Path,
    *,
    primary: FixtureProvider | None = None,
    secondary: FixtureProvider | None = None,
    round_ids: list[int] | None = None,
    output_name: str = "artifact",
    decoder=None,
    replace=None,
) -> tuple[Path, dict]:
    requested = round_ids or [42]
    if primary is None or secondary is None:
        primary, secondary = provider_pair(requested)
    marker_path, marker_hash = marker(tmp_path)
    kwargs = {}
    if decoder is not None:
        kwargs["decoder"] = decoder
    if replace is not None:
        kwargs["replace"] = replace
    output = tmp_path / output_name
    manifest = create_recovery_artifact(
        output=output,
        round_ids=requested,
        primary=primary,
        secondary=secondary,
        network="solana-mainnet-beta",
        expected_genesis_hash=GENESIS,
        expected_program_id=PROGRAM_ID,
        sample_id=SAMPLE_ID,
        marker_path=marker_path,
        expected_marker_sha256=marker_hash,
        repository_commit="a" * 40,
        branch="research/rfc-007-paper-collection-burn-in",
        decoder_version="round-decoder-v1",
        recovery_protocol_version="rfc007-recovery-v1",
        recovery_method_version="finalized-dual-rpc-v1",
        live_ledger_path=tmp_path / "unused.sqlite",
        repository_root=tmp_path,
        clock=lambda: FROZEN_TIME,
        **kwargs,
    )
    return output, manifest


def records(artifact: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (artifact / EVIDENCE_FILENAME)
        .read_text(encoding="utf-8")
        .splitlines()
    ]


def test_successful_dual_provider_byte_agreement(tmp_path: Path) -> None:
    artifact, manifest = create_one(tmp_path)
    record = records(artifact)[0]
    assert manifest["accepted_round_list"] == [42]
    assert record["conflict_status"] == "accepted"
    assert record["agreement_policy"] == "raw_account_bytes"
    assert record["winner_square"] == 1
    assert record["transaction_corroboration"]["primary"]["available"]
    assert verify_recovery_artifact(artifact)["valid"]


def test_canonical_decoded_agreement_accepts_different_raw_bytes(
    tmp_path: Path,
) -> None:
    requested = [42]
    first, second = provider_pair(requested)
    second.accounts[pda(42)] = round_account_bytes(42) + b"ignored"

    def decoder(_account):
        return valid_state(42)

    artifact, _manifest = create_one(
        tmp_path,
        primary=first,
        secondary=second,
        decoder=decoder,
    )
    record = records(artifact)[0]
    assert record["conflict_status"] == "accepted"
    assert record["agreement_policy"] == "full_decoded_round_state"
    assert not record["validation_checks"]["raw_account_bytes_match"]


def test_provider_disagreement_is_quarantined(tmp_path: Path) -> None:
    first, second = provider_pair([42])
    second.accounts[pda(42)] = round_account_bytes(42, entropy=27)
    artifact, manifest = create_one(
        tmp_path,
        primary=first,
        secondary=second,
    )
    assert manifest["conflicted_round_list"] == [42]
    record = records(artifact)[0]
    assert record["conflict_status"] == "conflicted"
    assert record["winner_square"] is None


def test_wrong_genesis_hash_refuses_creation(tmp_path: Path) -> None:
    first, second = provider_pair([42])
    second.genesis = "wrong"
    with pytest.raises(ValueError, match="Secondary provider genesis"):
        create_one(tmp_path, primary=first, secondary=second)
    assert not (tmp_path / "artifact").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_owner",
        "wrong_round",
        "zero_slot_hash",
        "missing_entropy",
        "missing_account",
    ],
)
def test_invalid_provider_evidence_is_failed(
    tmp_path: Path,
    mutation: str,
) -> None:
    first, second = provider_pair([42])
    if mutation == "wrong_owner":
        second.owner = str(Pubkey.new_unique())
    elif mutation == "wrong_round":
        second.accounts[pda(42)] = round_account_bytes(43)
    elif mutation == "zero_slot_hash":
        second.accounts[pda(42)] = round_account_bytes(
            42,
            slot_hash=bytes(32),
        )
    elif mutation == "missing_entropy":
        second.accounts[pda(42)] = round_account_bytes(
            42,
            slot_hash=bytes([255]) * 32,
        )
    else:
        second.accounts.clear()
    artifact, manifest = create_one(
        tmp_path,
        primary=first,
        secondary=second,
    )
    assert manifest["failed_round_list"] == [42]
    failure = records(artifact)[0]["failure_reasons"]
    assert len(failure) == 1
    assert failure[0].startswith("secondary:validation:")


def valid_state(round_id: int):
    return SimpleNamespace(
        round_id=round_id,
        deployed_lamports=[1] * 25,
        mass=[0] * 25,
        miner_counts=[1] * 25,
        slot_hash_hex=struct.pack("<QQQQ", 26, 0, 0, 0).hex(),
        expires_at=100,
        motherlode=0,
        rewards=[0] * 25,
        total_vaulted=1,
        total_winnings=2,
        total_miners=25,
        top_miner="11111111111111111111111111111111",
        entropy=26,
    )


@pytest.mark.parametrize(
    "change",
    [
        "short_deployments",
        "negative_total",
        "nan_total",
    ],
)
def test_invalid_decoded_numeric_or_array_values_fail(
    tmp_path: Path,
    change: str,
) -> None:
    first, second = provider_pair([42])

    def decoder(_account):
        state = vars(valid_state(42)).copy()
        if change == "short_deployments":
            state["deployed_lamports"] = [1] * 24
        elif change == "negative_total":
            state["total_winnings"] = -1
        else:
            state["total_winnings"] = float("nan")
        return SimpleNamespace(**state)

    artifact, manifest = create_one(
        tmp_path,
        primary=first,
        secondary=second,
        decoder=decoder,
    )
    assert manifest["failed_round_list"] == [42]
    failures = records(artifact)[0]["failure_reasons"]
    assert len(failures) == 2
    assert all(":validation:" in value for value in failures)


def test_winner_derivation_is_versioned_and_in_range(tmp_path: Path) -> None:
    artifact, _manifest = create_one(tmp_path)
    record = records(artifact)[0]
    assert record["entropy"] == 26
    assert record["winner_square"] == 1
    assert record["winner_derivation_rule"] == "entropy_mod_25_v1"


def test_duplicate_and_incomplete_formal_round_requests_fail(
    tmp_path: Path,
) -> None:
    first, second = provider_pair([42])
    marker_path, marker_hash = marker(tmp_path)
    common = dict(
        output=tmp_path / "artifact",
        primary=first,
        secondary=second,
        network="solana-mainnet-beta",
        expected_genesis_hash=GENESIS,
        expected_program_id=PROGRAM_ID,
        sample_id=SAMPLE_ID,
        marker_path=marker_path,
        expected_marker_sha256=marker_hash,
        repository_commit="a" * 40,
        branch="branch",
        decoder_version="decoder",
        recovery_protocol_version="protocol",
        recovery_method_version="method",
        live_ledger_path=tmp_path / "ledger.sqlite",
        repository_root=tmp_path,
        clock=lambda: FROZEN_TIME,
    )
    with pytest.raises(ValueError, match="Duplicate"):
        create_recovery_artifact(round_ids=[42, 42], **common)
    with pytest.raises(ValueError, match="exactly all 13"):
        create_recovery_artifact(
            round_ids=list(FORMAL_GATE_B_MISSING_ROUNDS[:-1]),
            formal_gate_b=True,
            control_round_id=GATE_B_CONTROL_ROUND,
            **common,
        )


def test_wrong_pda_is_rejected() -> None:
    with pytest.raises(ValueError, match="Round PDA mismatch"):
        validate_round_pda(42, str(Pubkey.new_unique()), PROGRAM_ID)


def test_existing_output_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "artifact"
    output.mkdir()
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        create_one(tmp_path)


@pytest.mark.parametrize(
    "protected_kind",
    ("ledger", "wal", "shm", "lock", "marker", "observer"),
)
def test_runtime_output_paths_are_refused(
    tmp_path: Path,
    protected_kind: str,
) -> None:
    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    observer = raw / "observer_fixture.jsonl"
    observer.write_text("", encoding="utf-8")
    ledger = tmp_path / "live.sqlite"
    marker_path = tmp_path / "marker.json"
    marker_path.write_text("{}", encoding="utf-8")
    paths = {
        "ledger": ledger,
        "wal": Path(str(ledger) + "-wal"),
        "shm": Path(str(ledger) + "-shm"),
        "lock": Path(str(ledger) + ".writer.lock"),
        "marker": marker_path,
        "observer": observer,
    }
    with pytest.raises(ValueError, match="protected runtime path"):
        validate_output_path(
            paths[protected_kind],
            marker_path=marker_path,
            live_ledger_path=ledger,
            repository_root=tmp_path,
        )


def test_atomic_failure_leaves_no_partial_artifact(tmp_path: Path) -> None:
    def fail_replace(_source, _destination):
        raise OSError("injected atomic rename failure")

    with pytest.raises(OSError, match="injected"):
        create_one(tmp_path, replace=fail_replace)
    assert not (tmp_path / "artifact").exists()
    assert not list(tmp_path.glob(".artifact.tmp-*"))


def test_manifest_and_record_hashing_are_deterministic(
    tmp_path: Path,
) -> None:
    first, first_manifest = create_one(
        tmp_path,
        output_name="artifact-one",
    )
    second, second_manifest = create_one(
        tmp_path,
        output_name="artifact-two",
    )
    assert (first / EVIDENCE_FILENAME).read_bytes() == (
        second / EVIDENCE_FILENAME
    ).read_bytes()
    assert first_manifest == second_manifest
    assert (first / MANIFEST_FILENAME).read_bytes() == (
        second / MANIFEST_FILENAME
    ).read_bytes()


def test_verification_detects_tampering(tmp_path: Path) -> None:
    artifact, _manifest = create_one(tmp_path)
    path = artifact / EVIDENCE_FILENAME
    path.write_bytes(path.read_bytes().replace(b'"winner_square":1', b'"winner_square":2'))
    with pytest.raises(ValueError, match="verification failed"):
        verify_recovery_artifact(artifact)


def test_verification_detects_manifest_tampering(tmp_path: Path) -> None:
    artifact, _manifest = create_one(tmp_path)
    path = artifact / MANIFEST_FILENAME
    value = json.loads(path.read_text(encoding="utf-8"))
    value["branch"] = "tampered"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="verification failed"):
        verify_recovery_artifact(artifact)


def test_requery_conflict_does_not_overwrite_evidence(
    tmp_path: Path,
) -> None:
    first, second = provider_pair([42])
    artifact, _manifest = create_one(
        tmp_path,
        primary=first,
        secondary=second,
    )
    before = {
        path.name: path.read_bytes()
        for path in artifact.iterdir()
    }
    second.accounts[pda(42)] = round_account_bytes(42, entropy=27)
    result = requery_recovery_artifact(
        artifact,
        primary=first,
        secondary=second,
        clock=lambda: FROZEN_TIME,
    )
    assert result["conflicted_rounds"] == [42]
    assert not result["artifact_modified"]
    assert before == {
        path.name: path.read_bytes()
        for path in artifact.iterdir()
    }


def test_control_round_is_not_misclassified_and_matches_ledger(
    tmp_path: Path,
) -> None:
    requested = [42]
    first, second = provider_pair([42, GATE_B_CONTROL_ROUND])
    marker_path, marker_hash = marker(tmp_path)
    ledger = control_ledger(tmp_path)
    output = tmp_path / "artifact"
    manifest = create_recovery_artifact(
        output=output,
        round_ids=requested,
        primary=first,
        secondary=second,
        network="solana-mainnet-beta",
        expected_genesis_hash=GENESIS,
        expected_program_id=PROGRAM_ID,
        sample_id=SAMPLE_ID,
        marker_path=marker_path,
        expected_marker_sha256=marker_hash,
        repository_commit="a" * 40,
        branch="branch",
        decoder_version="decoder",
        recovery_protocol_version="protocol",
        recovery_method_version="method",
        live_ledger_path=ledger,
        control_round_id=GATE_B_CONTROL_ROUND,
        repository_root=tmp_path,
        clock=lambda: FROZEN_TIME,
    )
    control = next(
        record
        for record in records(output)
        if record["round_id"] == GATE_B_CONTROL_ROUND
    )
    assert control["outcome_observation_class"] == (
        "contemporaneously_observed_control"
    )
    assert control["conflict_status"] == "accepted"
    assert not manifest["recovery_qualified_readiness"]


def test_formal_conflict_prevents_recovery_qualified_readiness(
    tmp_path: Path,
) -> None:
    all_rounds = [
        *FORMAL_GATE_B_MISSING_ROUNDS,
        GATE_B_CONTROL_ROUND,
    ]
    first, second = provider_pair(all_rounds)
    second.accounts[pda(FORMAL_GATE_B_MISSING_ROUNDS[0])] = (
        round_account_bytes(FORMAL_GATE_B_MISSING_ROUNDS[0], entropy=27)
    )
    marker_path, marker_hash = marker(tmp_path)
    manifest = create_recovery_artifact(
        output=tmp_path / "formal",
        round_ids=list(FORMAL_GATE_B_MISSING_ROUNDS),
        primary=first,
        secondary=second,
        network="solana-mainnet-beta",
        expected_genesis_hash=GENESIS,
        expected_program_id=PROGRAM_ID,
        sample_id=SAMPLE_ID,
        marker_path=marker_path,
        expected_marker_sha256=marker_hash,
        repository_commit="a" * 40,
        branch="branch",
        decoder_version="decoder",
        recovery_protocol_version="protocol",
        recovery_method_version="method",
        live_ledger_path=control_ledger(tmp_path),
        control_round_id=GATE_B_CONTROL_ROUND,
        formal_gate_b=True,
        repository_root=tmp_path,
        clock=lambda: FROZEN_TIME,
    )
    assert not manifest["recovery_qualified_readiness"]
    assert manifest["conflicted_round_list"] == [
        FORMAL_GATE_B_MISSING_ROUNDS[0]
    ]


def test_recovery_module_has_no_live_or_economic_execution_paths() -> None:
    source = Path(
        "src/orev3/collection/outcome_recovery.py"
    ).read_text(encoding="utf-8").lower()
    forbidden = (
        "paper_accounting",
        "account_paper_decision",
        "sendtransaction",
        "sign_transaction",
        "submit_transaction",
        "claim_transaction",
        "deployment_intent",
        "strategy_id",
    )
    assert all(value not in source for value in forbidden)
