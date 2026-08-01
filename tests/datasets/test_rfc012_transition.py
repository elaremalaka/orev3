from __future__ import annotations

import base64
import hashlib
import json
import struct
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orev3.data.models import BoardState, ObserverSnapshot, TreasuryState
from orev3.datasets.rfc012_evidence import (
    ORE_PROGRAM_IDENTITY,
    ORE_PROTOCOL_REVISION,
    ROUND_DECODER_IDENTITY,
    SOLANA_MAINNET_GENESIS_HASH,
    SOLANA_MAINNET_NETWORK,
    CanonicalPredecessorIdentity,
    FailureCategory,
    PostTransitionEvidence,
    TerminalDisposition,
    TransitionContext,
)
from orev3.datasets.rfc012_transition import (
    EvidenceAmbiguityError,
    EvidenceStoreError,
    PredecessorObservation,
    Rfc012EvidenceStore,
    Rfc012TransitionProcessor,
    TransitionCandidateStatus,
)
from orev3.observer.accounts import (
    BOARD_ADDRESS,
    ROUND_ACCOUNT_TYPE,
    decode_round,
)


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
SNAPSHOT_ID = "a" * 64
PROVIDER = "primary-rpc"


def _round_bytes(
    *,
    round_id: int = 41,
    finalized: bool = True,
    discriminator: int = ROUND_ACCOUNT_TYPE,
) -> bytes:
    header = bytes([discriminator]) + bytes(7)
    slot_hash = struct.pack("<QQQQ", 7, 0, 0, 0) if finalized else bytes(32)
    return b"".join(
        (
            header,
            struct.pack("<Q", round_id),
            struct.pack("<25Q", *range(25)),
            struct.pack("<25Q", *([0] * 25)),
            struct.pack("<25Q", *([1] * 25)),
            slot_hash,
            struct.pack("<Q", 1_000),
            struct.pack("<Q", 2_000),
            bytes(32),
            struct.pack("<25Q", *range(100, 125)),
            struct.pack(
                "<QQQ",
                3_000 if finalized else 0,
                4_000 if finalized else 0,
                25,
            ),
            bytes(32),
        )
    )


def _round_state(raw: bytes):
    return decode_round(
        {"data": [base64.b64encode(raw).decode("ascii"), "base64"]}
    )


def _snapshot(round_id: int = 42) -> ObserverSnapshot:
    return ObserverSnapshot(
        collector_session_id="observer-session-001",
        observed_at_utc=NOW,
        rpc_slot=901,
        board=BoardState(round_id=round_id, start_slot=900, end_slot=1_000),
        treasury=TreasuryState(motherlode=10),
        round=_round_state(_round_bytes(round_id=round_id, finalized=False)),
    )


def _context(
    *, predecessor: int = 41, snapshot_id: str = SNAPSHOT_ID, slot: int = 900,
    commitment: str = "confirmed",
) -> TransitionContext:
    return TransitionContext(
        network_identity=SOLANA_MAINNET_NETWORK,
        expected_genesis_hash=SOLANA_MAINNET_GENESIS_HASH,
        provider_identity=PROVIDER,
        board_account_identity=str(BOARD_ADDRESS),
        predecessor_round_id=predecessor,
        successor_round_id=predecessor + 1,
        successor_snapshot_identity=snapshot_id,
        board_response_commitment=commitment,
        board_response_context_slot=slot,
    )


def _response(
    *, raw: bytes | None = None, address: str | None = None,
    owner: str | None = ORE_PROGRAM_IDENTITY, slot: int | None = 901,
    commitment: str | None = "confirmed", network: str = SOLANA_MAINNET_NETWORK,
    genesis: str = SOLANA_MAINNET_GENESIS_HASH, provider: str = PROVIDER,
    program: str = ORE_PROGRAM_IDENTITY, protocol: str = ORE_PROTOCOL_REVISION,
    decoder: str = ROUND_DECODER_IDENTITY,
) -> PredecessorObservation:
    predecessor = CanonicalPredecessorIdentity.for_round(41)
    return PredecessorObservation(
        network_identity=network,
        expected_genesis_hash=genesis,
        provider_identity=provider,
        account_address=address or predecessor.canonical_round_pda,
        response_context_slot=slot,
        response_commitment=commitment,
        account_owner=owner,
        raw_account_data=_round_bytes() if raw is None else raw,
        ore_program_identity=program,
        protocol_revision=protocol,
        decoder_identity=decoder,
    )


class Reader:
    def __init__(self, response: PredecessorObservation | Exception) -> None:
        self.response = response
        self.calls: list[tuple[str, str, int]] = []

    def observe_predecessor(
        self, address: str, *, commitment: str, min_context_slot: int
    ) -> PredecessorObservation:
        self.calls.append((address, commitment, min_context_slot))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class History:
    def __init__(self, present: bool) -> None:
        self.present = present
        self.identities: list[CanonicalPredecessorIdentity] = []

    def has_finalized(self, identity: CanonicalPredecessorIdentity) -> bool:
        self.identities.append(identity)
        return self.present


class AmbiguousHistory(History):
    def has_finalized(self, identity: CanonicalPredecessorIdentity) -> bool:
        raise ValueError("ambiguous historical identity")


def _processor(
    tmp_path: Path, response: PredecessorObservation | Exception | None = None,
    *, history: History | None = None, store: Rfc012EvidenceStore | None = None,
    decoder=None,
) -> tuple[Rfc012TransitionProcessor, Reader, Rfc012EvidenceStore]:
    reader = Reader(response if response is not None else _response())
    selected_store = store or Rfc012EvidenceStore(tmp_path / "rfc012.jsonl")
    processor = Rfc012TransitionProcessor(
        reader=reader,
        evidence_store=selected_store,
        finalized_history=history,
        clock=lambda: NOW,
        decode_round_fields=decoder,
    )
    return processor, reader, selected_store


def _process(processor: Rfc012TransitionProcessor, **overrides):
    arguments = {
        "previous_round_id": 41,
        "successor_snapshot": _snapshot(),
        "successor_snapshot_identity": SNAPSHOT_ID,
        "transition_context": _context(),
        "successor_validated": True,
        "successor_durably_persisted": True,
        "transition_unambiguous": True,
    }
    arguments.update(overrides)
    return processor.process(**arguments)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"previous_round_id": None, "transition_context": None},
            TransitionCandidateStatus.INITIAL,
        ),
        (
            {"previous_round_id": 42, "transition_context": None},
            TransitionCandidateStatus.UNCHANGED,
        ),
        (
            {"previous_round_id": 43, "transition_context": None},
            TransitionCandidateStatus.REGRESSED,
        ),
        (
            {"previous_round_id": 40, "transition_context": None},
            TransitionCandidateStatus.SKIPPED,
        ),
        ({"transition_unambiguous": False}, TransitionCandidateStatus.AMBIGUOUS),
        ({"successor_validated": False}, TransitionCandidateStatus.INVALID_SUCCESSOR),
        (
            {"successor_durably_persisted": False},
            TransitionCandidateStatus.INVALID_SUCCESSOR,
        ),
        (
            {"successor_snapshot_identity": "b" * 64},
            TransitionCandidateStatus.INVALID_SUCCESSOR,
        ),
    ],
)
def test_non_candidates_issue_zero_reads(tmp_path, overrides, expected) -> None:
    processor, reader, store = _processor(tmp_path)
    result = _process(processor, **overrides)
    assert result.status is expected
    assert result.observation_count == 0
    assert reader.calls == []
    assert store.record_types() == ()


def test_already_durable_uses_zero_reads_and_records_disposition(tmp_path) -> None:
    history = History(True)
    processor, reader, store = _processor(tmp_path, history=history)
    result = _process(processor)
    assert reader.calls == []
    assert result.observation_count == 0
    assert (
        result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.ALREADY_DURABLE
    )
    assert store.record_types() == ("transition", "post_transition")
    assert history.identities == [CanonicalPredecessorIdentity.for_round(41)]


def test_ambiguous_finalized_history_fails_closed_without_read(tmp_path) -> None:
    processor, reader, store = _processor(
        tmp_path, history=AmbiguousHistory(False)
    )
    result = _process(processor)
    post = result.post_transition_evidence
    assert reader.calls == []
    assert post.terminal_disposition is TerminalDisposition.INVALID_OR_AMBIGUOUS
    assert post.failure_category is FailureCategory.DUPLICATE_IDENTITY_AMBIGUOUS
    assert store.record_types() == ("transition", "post_transition")


def test_read_uses_canonical_identity_and_exact_board_context(tmp_path) -> None:
    processor, reader, _ = _processor(tmp_path)
    result = _process(processor)
    predecessor = CanonicalPredecessorIdentity.for_round(41)
    assert reader.calls == [(predecessor.canonical_round_pda, "confirmed", 900)]
    assert result.observation_count == 1
    assert result.transition_evidence.predecessor_identity == predecessor
    assert result.transition_evidence.transition_context == _context()


@pytest.mark.parametrize(
    "response",
    [
        _response(slot=None, commitment=None),
        _response(slot=899),
        _response(network="solana-testnet"),
        _response(genesis="wrong-genesis"),
        _response(provider="secondary-rpc"),
        _response(commitment="processed"),
    ],
)
def test_rejected_context_is_context_unproven(tmp_path, response) -> None:
    processor, _, store = _processor(tmp_path, response)
    result = _process(processor)
    post = result.post_transition_evidence
    assert post.terminal_disposition is TerminalDisposition.CONTEXT_UNPROVEN
    assert post.failure_category is FailureCategory.CONTEXT_UNPROVEN
    assert not store.has_finalized(CanonicalPredecessorIdentity.for_round(41))


@pytest.mark.parametrize(
    ("response", "category"),
    [
        (
            _response(address=str(BOARD_ADDRESS)),
            FailureCategory.TRANSITION_IDENTITY_INVALID,
        ),
        (_response(owner=str(BOARD_ADDRESS)), FailureCategory.OWNER_MISMATCH),
        (_response(program=str(BOARD_ADDRESS)), FailureCategory.PROTOCOL_UNSUPPORTED),
        (
            _response(protocol="unsupported-revision"),
            FailureCategory.PROTOCOL_UNSUPPORTED,
        ),
        (_response(decoder="other-decoder"), FailureCategory.DECODER_UNSUPPORTED),
        (
            _response(raw=_round_bytes(discriminator=1)),
            FailureCategory.PAYLOAD_MALFORMED,
        ),
        (
            _response(raw=_round_bytes(round_id=40)),
            FailureCategory.ROUND_IDENTITY_MISMATCH,
        ),
    ],
)
def test_invalid_account_or_protocol_is_rejected(tmp_path, response, category) -> None:
    processor, _, store = _processor(tmp_path, response)
    result = _process(processor)
    post = result.post_transition_evidence
    assert post.terminal_disposition is TerminalDisposition.INVALID_OR_AMBIGUOUS
    assert post.failure_category is category
    assert not store.has_finalized(CanonicalPredecessorIdentity.for_round(41))


def test_raw_decoded_disagreement_is_rejected(tmp_path) -> None:
    def mismatched(raw):
        value = _round_state(raw).model_dump(mode="python")
        value["total_winnings"] += 1
        return value

    processor, _, _ = _processor(tmp_path, decoder=mismatched)
    result = _process(processor)
    assert (
        result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.INVALID_OR_AMBIGUOUS
    )
    assert (
        result.post_transition_evidence.failure_category
        is FailureCategory.PAYLOAD_MISMATCH
    )


def test_valid_nonfinal_response_is_preserved_without_finalized_append(
    tmp_path,
) -> None:
    processor, _, store = _processor(
        tmp_path, _response(raw=_round_bytes(finalized=False))
    )
    result = _process(processor)
    post = result.post_transition_evidence
    assert post.terminal_disposition is TerminalDisposition.NOT_FINALIZED
    assert post.finalized_state is False
    assert post.protocol_payload.decoded_round["round_id"] == 41
    assert store.record_types() == ("transition", "post_transition")


def test_unavailable_response_preserves_context(tmp_path) -> None:
    unavailable = _response(raw=b"")
    unavailable = replace(unavailable, raw_account_data=None, account_owner=None)
    processor, _, store = _processor(tmp_path, unavailable)
    result = _process(processor)
    post = result.post_transition_evidence
    assert post.terminal_disposition is TerminalDisposition.ACCOUNT_UNAVAILABLE
    assert post.predecessor_response_context_slot == 901
    assert post.predecessor_response_commitment == "confirmed"
    assert store.record_types() == ("transition", "post_transition")


def test_unavailable_response_for_wrong_address_is_invalid(tmp_path) -> None:
    unavailable = replace(
        _response(raw=b""),
        account_address=str(BOARD_ADDRESS),
        raw_account_data=None,
        account_owner=None,
    )
    processor, _, _ = _processor(tmp_path, unavailable)
    result = _process(processor)
    assert (
        result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.INVALID_OR_AMBIGUOUS
    )
    assert (
        result.post_transition_evidence.failure_category
        is FailureCategory.TRANSITION_IDENTITY_INVALID
    )


def test_observation_exception_is_operational_failure(tmp_path) -> None:
    processor, _, store = _processor(tmp_path, RuntimeError("offline"))
    result = _process(processor)
    post = result.post_transition_evidence
    assert post.terminal_disposition is TerminalDisposition.OPERATIONAL_FAILURE
    assert post.failure_category is FailureCategory.OBSERVATION_FAILURE
    assert store.record_types() == ("transition", "post_transition")


def test_finalized_payload_is_durable_before_terminal_evidence(
    tmp_path, monkeypatch
) -> None:
    calls: list[tuple[str, bool]] = []
    from orev3.datasets import rfc012_transition as module

    original = module.append_json_line

    def recording_append(path, payload, *, durable=False):
        calls.append((payload["record_type"], durable))
        return original(path, payload, durable=durable)

    monkeypatch.setattr(module, "append_json_line", recording_append)
    processor, _, store = _processor(tmp_path)
    result = _process(processor)
    assert (
        result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.FINALIZED_PERSISTED
    )
    assert calls == [
        ("transition", True),
        ("finalized_payload", True),
        ("post_transition", True),
    ]
    assert store.record_types() == (
        "transition",
        "finalized_payload",
        "post_transition",
    )


class FailingFinalizedStore(Rfc012EvidenceStore):
    def append_finalized_payload(self, predecessor, payload):
        raise OSError("fsync failed")


def test_finalized_persistence_failure_never_claims_success(tmp_path) -> None:
    store = FailingFinalizedStore(tmp_path / "rfc012.jsonl")
    processor, _, _ = _processor(tmp_path, store=store)
    result = _process(processor)
    post = result.post_transition_evidence
    assert post.terminal_disposition is TerminalDisposition.OPERATIONAL_FAILURE
    assert post.failure_category is FailureCategory.PERSISTENCE_FAILURE
    assert store.record_types() == ("transition", "post_transition")


def test_evidence_reconstructs_through_phase_one_contracts(tmp_path) -> None:
    processor, _, store = _processor(tmp_path)
    result = _process(processor)
    assert store.transitions() == (result.transition_evidence,)
    assert store.post_transitions() == (result.post_transition_evidence,)
    assert PostTransitionEvidence.from_canonical_bytes(
        result.post_transition_evidence.to_canonical_bytes()
    ) == result.post_transition_evidence
    finalized = store.finalized_payloads()
    assert finalized[0][0] == CanonicalPredecessorIdentity.for_round(41)
    assert finalized[0][1] == result.post_transition_evidence.protocol_payload


def test_repeat_and_restart_do_not_duplicate_finalized_evidence(tmp_path) -> None:
    path = tmp_path / "rfc012.jsonl"
    processor, reader, store = _processor(tmp_path, store=Rfc012EvidenceStore(path))
    first = _process(processor)
    restarted, restarted_reader, restarted_store = _processor(
        tmp_path, store=Rfc012EvidenceStore(path)
    )
    second = _process(restarted)
    assert first.post_transition_evidence == second.post_transition_evidence
    assert reader.calls and restarted_reader.calls == []
    assert restarted_store.record_types() == (
        "transition", "finalized_payload", "post_transition"
    )


def test_conflicting_immutable_record_fails_closed(tmp_path) -> None:
    processor, _, store = _processor(tmp_path)
    result = _process(processor)
    post = result.post_transition_evidence
    conflicting = replace(post, attempt_timestamp=NOW.replace(hour=13))
    with pytest.raises(EvidenceAmbiguityError):
        store.append_post_transition(conflicting)


def test_malformed_store_fails_closed(tmp_path) -> None:
    path = tmp_path / "rfc012.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    store = Rfc012EvidenceStore(path)
    with pytest.raises(EvidenceStoreError):
        store.record_types()


def test_every_branch_preserves_exact_successor_and_never_emits_snapshot(
    tmp_path,
) -> None:
    successor = _snapshot()
    processor, _, store = _processor(tmp_path)
    result = _process(processor, successor_snapshot=successor)
    assert result.successor_snapshot is successor
    records = [json.loads(line) for line in store.path.read_text().splitlines()]
    assert all(
        record["schema_identifier"] == "orev3.rfc012.transition-store"
        for record in records
    )
    assert all("board" not in record and "round" not in record for record in records)
    assert hashlib.sha256(
        successor.model_dump_json().encode()
    ).hexdigest() == hashlib.sha256(
        result.successor_snapshot.model_dump_json().encode()
    ).hexdigest()


def test_isolated_module_has_no_runtime_or_production_reachability() -> None:
    source = Path("src/orev3/datasets/rfc012_transition.py").read_text(encoding="utf-8")
    forbidden = (
        "wallet", "signer", "transaction submission", "mine", "claim",
        "deployment", "authorization", "production ledger",
    )
    assert all(token not in source.lower() for token in forbidden)
