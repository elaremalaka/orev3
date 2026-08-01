from __future__ import annotations

import base64
import dataclasses
import hashlib
import struct
from datetime import datetime, timedelta, timezone

import pytest

from orev3.datasets.rfc012_evidence import (
    CanonicalPredecessorIdentity,
    CaptureMode,
    EvidenceIdentity,
    FailureCategory,
    OutcomeSource,
    PostTransitionEvidence,
    PreservedProtocolPayload,
    ResponseIdentity,
    TerminalDisposition,
    TransitionContext,
    TransitionEvidence,
    TransitionIdentity,
    ValidationOutcome,
    canonical_decode,
    canonical_encode,
)
from orev3.observer.accounts import ROUND_ACCOUNT_TYPE, decode_round


def _round_account_bytes(*, round_id: int = 41, entropy: int = 7) -> bytes:
    header = bytes([ROUND_ACCOUNT_TYPE]) + bytes(7)
    slot_hash = struct.pack("<QQQQ", entropy, 0, 0, 0)
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
            struct.pack("<QQQ", 3_000, 4_000, 25),
            bytes(32),
        )
    )


def _decoded_round(raw: bytes) -> dict[str, object]:
    encoded = base64.b64encode(raw).decode("ascii")
    return decode_round({"data": [encoded, "base64"]}).model_dump(
        mode="python"
    )


def _transition(
    *,
    round_id: int = 41,
    session: str = "observer-session-001",
    snapshot: str = "a" * 64,
    slot: int = 900,
    provider: str = "primary-rpc",
    board: str = "BrcSxdp1nXFzou1YyDnQJcPNBNHgoypZmTsyKBSLLXzi",
    commitment: str = "confirmed",
) -> TransitionEvidence:
    predecessor = CanonicalPredecessorIdentity.for_round(round_id)
    context = TransitionContext(
        network_identity=predecessor.network_identity,
        expected_genesis_hash=predecessor.expected_genesis_hash,
        provider_identity=provider,
        board_account_identity=board,
        predecessor_round_id=round_id,
        successor_round_id=round_id + 1,
        successor_snapshot_identity=snapshot,
        board_response_commitment=commitment,
        board_response_context_slot=slot,
    )
    return TransitionEvidence.create(
        observer_session_identity=session,
        predecessor_identity=predecessor,
        successor_round_id=round_id + 1,
        successor_snapshot_identity=snapshot,
        transition_context=context,
    )


def _payload(
    *,
    raw: bytes | None = None,
    decoded: dict[str, object] | None = None,
) -> PreservedProtocolPayload:
    selected_raw = raw if raw is not None else _round_account_bytes()
    return PreservedProtocolPayload.create(
        raw_account_data=selected_raw,
        decoded_round=(
            decoded if decoded is not None else _decoded_round(selected_raw)
        ),
    )


def _finalized(
    *,
    transition: TransitionEvidence | None = None,
    payload: PreservedProtocolPayload | None = None,
    attempt_timestamp: datetime | None = None,
) -> PostTransitionEvidence:
    selected_payload = payload or _payload()
    return PostTransitionEvidence.create(
        transition_evidence=transition or _transition(),
        attempt_timestamp=attempt_timestamp
        or datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
        predecessor_response_context_slot=901,
        predecessor_response_commitment="confirmed",
        response_raw_account_sha256=selected_payload.raw_account_sha256,
        protocol_payload=selected_payload,
        validation_outcome=ValidationOutcome.VALID,
        failure_category=None,
        terminal_disposition=TerminalDisposition.FINALIZED_PERSISTED,
        finalized_state=True,
        outcome_source=OutcomeSource.OBSERVED,
        capture_mode=CaptureMode.POST_TRANSITION_PREDECESSOR,
    )


def _no_response_failure() -> PostTransitionEvidence:
    return PostTransitionEvidence.create(
        transition_evidence=_transition(),
        attempt_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
        predecessor_response_context_slot=None,
        predecessor_response_commitment=None,
        response_raw_account_sha256=None,
        protocol_payload=None,
        validation_outcome=ValidationOutcome.UNAVAILABLE,
        failure_category=FailureCategory.ACCOUNT_UNAVAILABLE,
        terminal_disposition=TerminalDisposition.ACCOUNT_UNAVAILABLE,
        finalized_state=None,
        outcome_source=None,
        capture_mode=None,
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _transition().transition_context,
        lambda: _transition().predecessor_identity,
        lambda: _transition().transition_identity,
        lambda: _finalized().response_identity,
        lambda: _finalized().evidence_identity,
        _transition,
        _payload,
        _finalized,
    ],
)
def test_public_contracts_are_immutable(factory) -> None:
    contract = factory()
    assert contract is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        contract.unexpected = "mutation"


def test_decoded_payload_is_deeply_immutable() -> None:
    payload = _payload()
    decoded = payload.decoded_round
    assert decoded is not None
    decoded["round_id"] = 999
    with pytest.raises(AttributeError):
        decoded["deployed_lamports"].append(4)

    restored = payload.decoded_round
    assert restored is not None
    assert restored["round_id"] == 41
    assert restored["deployed_lamports"] == tuple(range(25))


def test_canonical_encoding_ignores_mapping_and_traversal_order() -> None:
    left = {"z": [3, 2, 1], "a": {"second": 2, "first": 1}}
    right = {"a": {"first": 1, "second": 2}, "z": (3, 2, 1)}
    assert canonical_encode(left) == canonical_encode(right)


def test_canonical_type_tags_prevent_marker_shaped_mapping_collisions() -> None:
    marker_shaped = {"type": "bytes", "value": "YWJj"}
    assert canonical_encode(marker_shaped) != canonical_encode(b"abc")
    assert canonical_decode(canonical_encode(marker_shaped)) == marker_shaped


def test_canonical_encoding_rejects_noncanonical_or_malformed_input() -> None:
    with pytest.raises(ValueError, match="malformed"):
        canonical_decode(b"not-json")
    with pytest.raises(ValueError, match="version"):
        canonical_decode(
            b'{"canonical_encoding_version":2,"value":null}'
        )
    with pytest.raises(TypeError, match="floats"):
        canonical_encode({"not_protocol_exact": 1.5})


def test_identical_inputs_reconstruct_byte_identically() -> None:
    first = _finalized()
    second = _finalized()
    assert first == second
    assert first.to_canonical_bytes() == second.to_canonical_bytes()
    assert first.evidence_identity == second.evidence_identity
    assert first.response_identity == second.response_identity
    assert first.protocol_payload is not None
    assert second.protocol_payload is not None
    assert (
        first.protocol_payload.protocol_payload_sha256
        == second.protocol_payload.protocol_payload_sha256
    )


@pytest.mark.parametrize(
    "change",
    [
        {"session": "observer-session-002"},
        {"snapshot": "b" * 64},
        {"slot": 901},
        {"round_id": 42},
        {"provider": "secondary-rpc"},
        {"board": "DifferentBoardIdentity"},
        {"commitment": "finalized"},
    ],
)
def test_normative_transition_inputs_change_transition_identity(change) -> None:
    assert (
        _transition().transition_identity
        != _transition(**change).transition_identity
    )


def test_response_inputs_change_response_identity() -> None:
    first = _finalized()
    second_payload = _payload(raw=_round_account_bytes(round_id=42))
    second = _finalized(payload=second_payload)
    assert first.response_identity != second.response_identity


def test_normative_evidence_inputs_change_evidence_identity() -> None:
    finalized = _finalized()
    payload = _payload()
    not_finalized = PostTransitionEvidence.create(
        transition_evidence=_transition(),
        attempt_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
        predecessor_response_context_slot=901,
        predecessor_response_commitment="confirmed",
        response_raw_account_sha256=payload.raw_account_sha256,
        protocol_payload=payload,
        validation_outcome=ValidationOutcome.VALID,
        failure_category=None,
        terminal_disposition=TerminalDisposition.NOT_FINALIZED,
        finalized_state=False,
        outcome_source=None,
        capture_mode=None,
    )
    unavailable = _no_response_failure()
    assert len(
        {
            finalized.evidence_identity.sha256,
            not_finalized.evidence_identity.sha256,
            unavailable.evidence_identity.sha256,
        }
    ) == 3


def test_timestamp_is_evidence_but_not_an_identity_input() -> None:
    first = _finalized(
        attempt_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc)
    )
    second = _finalized(
        attempt_timestamp=datetime(2026, 8, 2, tzinfo=timezone.utc)
    )
    assert first.attempt_timestamp != second.attempt_timestamp
    assert first.evidence_identity == second.evidence_identity
    assert first.to_canonical_bytes() != second.to_canonical_bytes()


@pytest.mark.parametrize(
    "provider",
    [
        "https://rpc.example.invalid/key",
        "rpc.example.invalid?api-key=secret",
        "user@example.invalid",
        "provider/secret",
    ],
)
def test_provider_identity_rejects_secret_bearing_values(provider: str) -> None:
    predecessor = CanonicalPredecessorIdentity.for_round(41)
    with pytest.raises(ValueError, match="redacted"):
        TransitionContext(
            network_identity=predecessor.network_identity,
            expected_genesis_hash=predecessor.expected_genesis_hash,
            provider_identity=provider,
            board_account_identity="board",
            predecessor_round_id=41,
            successor_round_id=42,
            successor_snapshot_identity="a" * 64,
            board_response_commitment="confirmed",
            board_response_context_slot=900,
        )


def test_absent_response_and_payload_do_not_collide_with_empty_payload() -> None:
    absent = _no_response_failure()
    empty_payload = PreservedProtocolPayload.create(
        raw_account_data=b"",
        decoded_round=None,
    )
    present = PostTransitionEvidence.create(
        transition_evidence=_transition(),
        attempt_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
        predecessor_response_context_slot=901,
        predecessor_response_commitment="confirmed",
        response_raw_account_sha256=hashlib.sha256(b"").hexdigest(),
        protocol_payload=empty_payload,
        validation_outcome=ValidationOutcome.INVALID,
        failure_category=FailureCategory.PAYLOAD_MALFORMED,
        terminal_disposition=TerminalDisposition.INVALID_OR_AMBIGUOUS,
        finalized_state=None,
        outcome_source=None,
        capture_mode=None,
    )
    assert absent.response_identity is None
    assert present.response_identity is not None
    assert absent.evidence_identity != present.evidence_identity


def test_identity_domains_cannot_collide() -> None:
    evidence = _finalized()
    assert evidence.protocol_payload is not None
    digests = {
        evidence.transition_evidence.transition_identity.sha256,
        evidence.response_identity.sha256,
        evidence.protocol_payload.protocol_payload_sha256,
        evidence.evidence_identity.sha256,
    }
    assert len(digests) == 4


def test_raw_payload_hash_mismatch_is_rejected() -> None:
    payload = _payload()
    with pytest.raises(ValueError, match="raw account payload hash"):
        dataclasses.replace(payload, raw_account_sha256="0" * 64)


def test_decoded_payload_hash_mismatch_is_rejected() -> None:
    payload = _payload()
    with pytest.raises(ValueError, match="decoded Round hash"):
        dataclasses.replace(payload, decoded_round_sha256="0" * 64)


def test_raw_and_decoded_provenance_disagreement_is_rejected() -> None:
    raw = _round_account_bytes()
    with pytest.raises(ValueError, match="provenance disagree"):
        PreservedProtocolPayload.create(
            raw_account_data=raw,
            decoded_round=_decoded_round(raw),
            decoded_from_raw_sha256="0" * 64,
        )


def test_raw_and_decoded_semantic_disagreement_is_rejected() -> None:
    raw = _round_account_bytes()
    decoded = _decoded_round(raw)
    decoded["round_id"] = 42
    with pytest.raises(ValueError, match="pinned decoder"):
        PreservedProtocolPayload.create(
            raw_account_data=raw,
            decoded_round=decoded,
        )


def test_malformed_response_can_preserve_raw_payload_without_decoded_fields() -> None:
    payload = PreservedProtocolPayload.create(
        raw_account_data=b"malformed-round-account",
        decoded_round=None,
    )
    evidence = PostTransitionEvidence.create(
        transition_evidence=_transition(),
        attempt_timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc),
        predecessor_response_context_slot=901,
        predecessor_response_commitment="confirmed",
        response_raw_account_sha256=payload.raw_account_sha256,
        protocol_payload=payload,
        validation_outcome=ValidationOutcome.INVALID,
        failure_category=FailureCategory.PAYLOAD_MALFORMED,
        terminal_disposition=TerminalDisposition.INVALID_OR_AMBIGUOUS,
        finalized_state=None,
        outcome_source=None,
        capture_mode=None,
    )
    assert evidence.protocol_payload is not None
    assert evidence.protocol_payload.raw_account_data == b"malformed-round-account"
    assert evidence.protocol_payload.decoded_round is None
    assert (
        PostTransitionEvidence.from_canonical_bytes(
            evidence.to_canonical_bytes()
        )
        == evidence
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_identifier", "orev3.rfc012.unknown", "schema identifier"),
        ("schema_version", 2, "schema version"),
        ("producer_identity", "other-producer", "producer identity"),
    ],
)
def test_unsupported_contract_header_is_rejected(field, value, message) -> None:
    with pytest.raises(ValueError, match=message):
        dataclasses.replace(_transition(), **{field: value})


def test_unsupported_program_protocol_decoder_and_network_are_rejected() -> None:
    predecessor = _transition().predecessor_identity
    with pytest.raises(ValueError, match="ore_program_identity"):
        dataclasses.replace(predecessor, ore_program_identity="other-program")
    with pytest.raises(ValueError, match="protocol_revision"):
        dataclasses.replace(predecessor, protocol_revision="future")
    with pytest.raises(ValueError, match="network_identity"):
        dataclasses.replace(predecessor, network_identity="solana-devnet")
    with pytest.raises(ValueError, match="decoder_identity"):
        dataclasses.replace(_payload(), decoder_identity="other-decoder")


def test_noncanonical_predecessor_pda_and_owner_are_rejected() -> None:
    predecessor = _transition().predecessor_identity
    with pytest.raises(ValueError, match="canonical_round_pda"):
        dataclasses.replace(predecessor, canonical_round_pda="invalid")
    with pytest.raises(ValueError, match="expected_account_owner"):
        dataclasses.replace(predecessor, expected_account_owner="other")


def test_transition_context_must_match_evidence_bindings() -> None:
    transition = _transition()
    mismatched = dataclasses.replace(
        transition.transition_context,
        successor_snapshot_identity="b" * 64,
    )
    with pytest.raises(ValueError, match="context identity bindings"):
        dataclasses.replace(transition, transition_context=mismatched)


def test_invalid_provenance_combinations_are_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be enriched"):
        dataclasses.replace(_finalized(), outcome_source=OutcomeSource.ENRICHED)
    with pytest.raises(ValueError, match="invalid capture mode"):
        dataclasses.replace(_finalized(), capture_mode=CaptureMode.CURRENT_ROUND)
    with pytest.raises(ValueError, match="must be paired"):
        dataclasses.replace(_finalized(), capture_mode=None)


def test_terminal_disposition_contracts_fail_closed() -> None:
    with pytest.raises(ValueError, match="finalized_persisted"):
        dataclasses.replace(_finalized(), finalized_state=False)
    with pytest.raises(ValueError, match="failure category"):
        dataclasses.replace(
            _no_response_failure(),
            failure_category=None,
        )


def test_transition_roundtrip_reconstructs_identity() -> None:
    transition = _transition()
    reconstructed = TransitionEvidence.from_canonical_bytes(
        transition.to_canonical_bytes()
    )
    assert reconstructed == transition
    assert reconstructed.reconstruct_identity() == transition.transition_identity


def test_post_transition_roundtrip_reconstructs_all_identities() -> None:
    evidence = _finalized()
    reconstructed = PostTransitionEvidence.from_canonical_bytes(
        evidence.to_canonical_bytes()
    )
    assert reconstructed == evidence
    assert reconstructed.reconstruct_identity() == evidence.evidence_identity
    assert reconstructed.response_identity == evidence.response_identity
    assert reconstructed.protocol_payload == evidence.protocol_payload


def test_identity_wrappers_reject_malformed_digests() -> None:
    for identity_type in (
        TransitionIdentity,
        ResponseIdentity,
        EvidenceIdentity,
    ):
        with pytest.raises(ValueError, match="SHA-256"):
            identity_type("NOT-A-DIGEST")


def test_naive_attempt_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _finalized(attempt_timestamp=datetime(2026, 8, 1))


def test_attempt_timestamp_timezone_normalizes_canonically() -> None:
    utc = _finalized(
        attempt_timestamp=datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
    )
    offset = _finalized(
        attempt_timestamp=datetime(
            2026,
            8,
            1,
            5,
            tzinfo=timezone(-timedelta(hours=7)),
        )
    )
    assert utc.to_canonical_bytes() == offset.to_canonical_bytes()
