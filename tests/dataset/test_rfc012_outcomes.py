from __future__ import annotations

import base64
import json
import struct
from datetime import UTC, datetime
from pathlib import Path

import pytest

from orev3.dataset.management import (
    DatasetBuildConfiguration,
    build_replay_dataset,
)
from orev3.dataset.rfc012_outcomes import (
    Rfc012OutcomeConsumptionError,
    consume_rfc012_outcomes,
    discover_rfc012_evidence,
    freeze_decision_snapshots,
)
from orev3.datasets.rfc012_evidence import (
    CaptureMode,
    CanonicalPredecessorIdentity,
    ORE_PROGRAM_IDENTITY,
    OutcomeSource,
    PostTransitionEvidence,
    PreservedProtocolPayload,
    TerminalDisposition,
    TransitionContext,
    TransitionEvidence,
    ValidationOutcome,
    canonical_decode,
    canonical_encode,
)
from orev3.datasets.rfc012_transition import Rfc012EvidenceStore
from orev3.historical.assembler import assemble_rounds
from orev3.historical.models import (
    FinalizedRoundOutcome,
    NormalizedSnapshot,
    RoundLifecycleIndexRecord,
)
from orev3.historical.persistence import lifecycle_to_index_record
from orev3.observer.accounts import BOARD_ADDRESS, ROUND_ACCOUNT_TYPE, decode_round
from orev3.replay.engine import snapshot_to_replay_point
from orev3.strategy_lab.runner import _decision_context_from_replay_point


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def _round_bytes(
    *,
    round_id: int = 41,
    entropy: int = 7,
    total_winnings: int = 4_000,
) -> bytes:
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
            struct.pack("<QQQ", 3_000, total_winnings, 25),
            bytes(32),
        )
    )


def _decoded(raw: bytes) -> dict[str, object]:
    return decode_round(
        {"data": [base64.b64encode(raw).decode("ascii"), "base64"]}
    ).model_dump(mode="python")


def _snapshot(
    *,
    round_id: int = 41,
    finalized: bool = False,
    line_number: int = 1,
    source_file: str = "observer.jsonl",
) -> NormalizedSnapshot:
    raw = _decoded(_round_bytes(round_id=round_id))
    if not finalized:
        raw.update(
            {
                "slot_hash_hex": "00" * 32,
                "entropy": None,
                "total_vaulted": 0,
                "total_winnings": 0,
            }
        )
    return NormalizedSnapshot(
        source_schema_version=2,
        collector_session_id="fixture-session",
        observed_at_utc=NOW.replace(second=line_number),
        rpc_slot=900 + line_number,
        board={
            "round_id": round_id,
            "start_slot": 900,
            "end_slot": 1_000,
            "production_cost_ema": 1,
        },
        treasury={"motherlode": 100},
        round=raw,
        source_file=source_file,
        source_line_number=line_number,
    )


def _lifecycle(*, finalized: bool = False, round_id: int = 41):
    snapshots = [
        _snapshot(round_id=round_id, finalized=False, line_number=1),
        _snapshot(round_id=round_id, finalized=finalized, line_number=2),
    ]
    return assemble_rounds(snapshots).rounds[0]


def _write_evidence(
    path: Path,
    *,
    round_id: int = 41,
    raw: bytes | None = None,
    response_slot: int = 901,
    session: str = "observer-session-001",
    snapshot_identity: str = "a" * 64,
) -> PostTransitionEvidence:
    selected_raw = raw or _round_bytes(round_id=round_id)
    predecessor = CanonicalPredecessorIdentity.for_round(round_id)
    context = TransitionContext(
        network_identity=predecessor.network_identity,
        expected_genesis_hash=predecessor.expected_genesis_hash,
        provider_identity="primary-rpc",
        board_account_identity=str(BOARD_ADDRESS),
        predecessor_round_id=round_id,
        successor_round_id=round_id + 1,
        successor_snapshot_identity=snapshot_identity,
        board_response_commitment="confirmed",
        board_response_context_slot=900,
    )
    transition = TransitionEvidence.create(
        observer_session_identity=session,
        predecessor_identity=predecessor,
        successor_round_id=round_id + 1,
        successor_snapshot_identity=snapshot_identity,
        transition_context=context,
    )
    payload = PreservedProtocolPayload.create(
        raw_account_data=selected_raw,
        decoded_round=_decoded(selected_raw),
    )
    post = PostTransitionEvidence.create(
        transition_evidence=transition,
        attempt_timestamp=NOW,
        predecessor_response_context_slot=response_slot,
        predecessor_response_commitment="confirmed",
        response_raw_account_sha256=payload.raw_account_sha256,
        protocol_payload=payload,
        validation_outcome=ValidationOutcome.VALID,
        failure_category=None,
        terminal_disposition=TerminalDisposition.FINALIZED_PERSISTED,
        finalized_state=True,
        outcome_source=OutcomeSource.OBSERVED,
        capture_mode=CaptureMode.POST_TRANSITION_PREDECESSOR,
    )
    store = Rfc012EvidenceStore(path)
    store.append_transition(transition)
    store.append_finalized_payload(predecessor, payload)
    store.append_post_transition(post)
    return post


def _consume(lifecycle, path: Path):
    freeze = freeze_decision_snapshots((lifecycle,))
    return consume_rfc012_outcomes(
        (lifecycle,),
        evidence_paths=(path,),
        decision_snapshot_freeze=freeze,
    )[0]


def _snapshot_bytes(lifecycle) -> bytes:
    return canonical_encode(
        tuple(
            snapshot.model_dump(mode="json")
            for snapshot in lifecycle.observation_history
        )
    )


def test_discovers_evidence_separately_in_deterministic_order(tmp_path) -> None:
    root = tmp_path / "rfc012"
    root.mkdir()
    second = root / "b.jsonl"
    first = root / "a.jsonl"
    ignored = root / "not-evidence.txt"
    for path in (second, first, ignored):
        path.write_text("", encoding="utf-8")

    assert discover_rfc012_evidence(root) == (first, second)


def test_post_transition_outcome_joins_only_by_canonical_predecessor(tmp_path) -> None:
    lifecycle = _lifecycle()
    evidence_path = tmp_path / "evidence.jsonl"
    post = _write_evidence(evidence_path)

    result = _consume(lifecycle, evidence_path)

    assert result.finalized_outcome is not None
    assert result.finalized_outcome.winning_square == 7
    assert result.finalized_outcome_source == "observed"
    assert result.finalized_outcome_capture_mode == "post_transition_predecessor"
    assert result.finalized_outcome_evidence_identities == (
        post.evidence_identity.sha256,
    )


def test_nonmatching_round_does_not_join_by_time_file_or_successor(tmp_path) -> None:
    lifecycle = _lifecycle(round_id=42)
    evidence_path = tmp_path / "evidence.jsonl"
    _write_evidence(evidence_path, round_id=41)

    result = _consume(lifecycle, evidence_path)

    assert result.finalized_outcome is None
    assert result.finalized_outcome_source is None
    assert result.finalized_outcome_capture_mode is None


def test_decision_snapshot_freeze_is_checked_before_evidence_is_opened(
    tmp_path,
) -> None:
    lifecycle = _lifecycle()
    freeze = freeze_decision_snapshots((lifecycle,))
    changed_snapshot = lifecycle.observation_history[0].model_copy(
        update={"rpc_slot": lifecycle.observation_history[0].rpc_slot + 1}
    )
    changed = lifecycle.model_copy(
        update={
            "observation_history": [
                changed_snapshot,
                lifecycle.observation_history[1],
            ]
        }
    )
    malformed = tmp_path / "malformed.jsonl"
    malformed.write_text("not-json\n", encoding="utf-8")

    with pytest.raises(
        Rfc012OutcomeConsumptionError,
        match="decision snapshot freeze changed",
    ):
        consume_rfc012_outcomes(
            (changed,),
            evidence_paths=(malformed,),
            decision_snapshot_freeze=freeze,
        )


def test_acceptance_changes_only_outcome_fields_and_preserves_replay(tmp_path) -> None:
    lifecycle = _lifecycle()
    evidence_path = tmp_path / "evidence.jsonl"
    _write_evidence(evidence_path)
    before_snapshots = _snapshot_bytes(lifecycle)
    before_point = snapshot_to_replay_point(lifecycle.observation_history[-1])
    before_context = _decision_context_from_replay_point(before_point)

    result = _consume(lifecycle, evidence_path)
    after_point = snapshot_to_replay_point(result.observation_history[-1])
    after_context = _decision_context_from_replay_point(after_point)

    assert _snapshot_bytes(result) == before_snapshots
    assert result.observation_count == lifecycle.observation_count
    assert result.observation_history == lifecycle.observation_history
    assert after_point == before_point
    assert after_context == before_context
    assert after_context.information == before_context.information


def test_freeze_preserves_round_order() -> None:
    first = _lifecycle(round_id=41)
    second = _lifecycle(round_id=42)
    freeze = freeze_decision_snapshots((first, second))

    with pytest.raises(
        Rfc012OutcomeConsumptionError,
        match="decision snapshot freeze changed",
    ):
        freeze.verify((second, first))


def test_current_round_remains_canonical_when_post_evidence_agrees(tmp_path) -> None:
    lifecycle = _lifecycle(finalized=True)
    evidence_path = tmp_path / "evidence.jsonl"
    post = _write_evidence(evidence_path)

    result = _consume(lifecycle, evidence_path)

    assert result.finalized_outcome == lifecycle.finalized_outcome
    assert result.finalized_outcome_source == "observed"
    assert result.finalized_outcome_capture_mode == "current_round"
    assert result.finalized_outcome_evidence_identities == (
        post.evidence_identity.sha256,
    )


def test_post_transition_reconciliation_is_idempotent(tmp_path) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_evidence(evidence_path)
    first = _consume(_lifecycle(), evidence_path)
    second = _consume(first, evidence_path)

    assert second == first
    assert second.finalized_outcome_capture_mode == "post_transition_predecessor"


def test_agreeing_enrichment_yields_local_observed_provenance(tmp_path) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_evidence(evidence_path)
    observed = _consume(_lifecycle(), evidence_path)
    enriched = _lifecycle().model_copy(
        update={
            "finalized_outcome": observed.finalized_outcome.model_copy(
                update={"observed_at_utc": NOW.replace(hour=13), "rpc_slot": 999}
            ),
            "finalized_outcome_source": "enriched",
            "finalized_outcome_capture_mode": None,
            "finalized_outcome_evidence_identities": (),
        }
    )

    result = _consume(enriched, evidence_path)

    assert result.finalized_outcome_source == "observed"
    assert result.finalized_outcome_capture_mode == "post_transition_predecessor"
    assert result.finalized_outcome.observed_at_utc == NOW


@pytest.mark.parametrize("source", ("observed", "enriched"))
def test_conflicting_existing_outcome_fails_closed(tmp_path, source) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_evidence(evidence_path)
    baseline = _consume(_lifecycle(), evidence_path)
    conflicting_outcome = baseline.finalized_outcome.model_copy(
        update={"total_winnings": baseline.finalized_outcome.total_winnings + 1}
    )
    lifecycle = _lifecycle().model_copy(
        update={
            "finalized_outcome": conflicting_outcome,
            "finalized_outcome_source": source,
            "finalized_outcome_capture_mode": (
                "current_round" if source == "observed" else None
            ),
        }
    )

    with pytest.raises(Rfc012OutcomeConsumptionError, match="conflicting"):
        _consume(lifecycle, evidence_path)


def test_conflicting_post_transition_sources_fail_closed(tmp_path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    _write_evidence(first, raw=_round_bytes(entropy=7))
    _write_evidence(
        second,
        raw=_round_bytes(entropy=8),
        session="observer-session-002",
        snapshot_identity="b" * 64,
    )
    lifecycle = _lifecycle()
    freeze = freeze_decision_snapshots((lifecycle,))

    with pytest.raises(Rfc012OutcomeConsumptionError, match="conflicting"):
        consume_rfc012_outcomes(
            (lifecycle,),
            evidence_paths=(first, second),
            decision_snapshot_freeze=freeze,
        )


def test_missing_outcome_remains_missing_without_evidence(tmp_path) -> None:
    lifecycle = _lifecycle()
    freeze = freeze_decision_snapshots((lifecycle,))
    result = consume_rfc012_outcomes(
        (lifecycle,), evidence_paths=(), decision_snapshot_freeze=freeze
    )[0]

    assert result == lifecycle
    assert result.finalized_outcome is None


def test_malformed_evidence_fails_closed(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    path.write_text("not-json\n", encoding="utf-8")

    with pytest.raises(Rfc012OutcomeConsumptionError, match="invalid RFC-012"):
        _consume(_lifecycle(), path)


def test_unsupported_evidence_identity_fails_closed(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    _write_evidence(path)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    transition = records[0]
    payload = canonical_decode(
        base64.b64decode(transition["canonical_payload_base64"])
    )
    payload["producer_identity"] = "unsupported-producer"
    transition["canonical_payload_base64"] = base64.b64encode(
        canonical_encode(payload)
    ).decode("ascii")
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    with pytest.raises(Rfc012OutcomeConsumptionError, match="invalid RFC-012"):
        _consume(_lifecycle(), path)


@pytest.mark.parametrize(
    ("target_type", "field", "value"),
    (
        ("envelope", "schema_version", 99),
        ("finalized_payload", "decoder_identity", "unsupported-decoder"),
        ("finalized_payload", "protocol_revision", "unsupported-protocol"),
    ),
)
def test_unsupported_evidence_versions_fail_closed(
    tmp_path, target_type, field, value
) -> None:
    path = tmp_path / "evidence.jsonl"
    _write_evidence(path)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    if target_type == "envelope":
        records[0][field] = value
    else:
        record = next(
            item for item in records if item["record_type"] == target_type
        )
        payload = canonical_decode(
            base64.b64decode(record["canonical_payload_base64"])
        )
        payload["protocol_payload"][field] = value
        record["canonical_payload_base64"] = base64.b64encode(
            canonical_encode(payload)
        ).decode("ascii")
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    with pytest.raises(Rfc012OutcomeConsumptionError, match="invalid RFC-012"):
        _consume(_lifecycle(), path)


def test_invalid_context_and_missing_durable_payload_fail_closed(tmp_path) -> None:
    invalid_context = tmp_path / "invalid-context.jsonl"
    _write_evidence(invalid_context, response_slot=899)
    with pytest.raises(Rfc012OutcomeConsumptionError, match="response context"):
        _consume(_lifecycle(), invalid_context)

    incomplete = tmp_path / "incomplete.jsonl"
    _write_evidence(incomplete)
    records = [
        json.loads(line)
        for line in incomplete.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["record_type"] != "finalized_payload"
    ]
    incomplete.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    with pytest.raises(Rfc012OutcomeConsumptionError, match="durable payload"):
        _consume(_lifecycle(), incomplete)


def test_terminal_evidence_requires_its_transition_record(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    _write_evidence(path)
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["record_type"] != "transition"
    ]
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    with pytest.raises(Rfc012OutcomeConsumptionError, match="transition record"):
        _consume(_lifecycle(), path)


def test_capture_mode_and_evidence_identity_persist_in_index(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    post = _write_evidence(path)
    lifecycle = _consume(_lifecycle(), path)
    record = lifecycle_to_index_record(lifecycle)
    restored = RoundLifecycleIndexRecord.model_validate_json(
        record.model_dump_json()
    )

    assert restored.finalized_outcome_capture_mode == "post_transition_predecessor"
    assert restored.finalized_outcome_evidence_identities == (
        post.evidence_identity.sha256,
    )


def test_pre_rfc012_index_remains_loadable() -> None:
    record = lifecycle_to_index_record(_lifecycle(finalized=True)).model_dump(
        mode="json"
    )
    record.pop("finalized_outcome_capture_mode")
    record.pop("finalized_outcome_evidence_identities")

    restored = RoundLifecycleIndexRecord.model_validate(record)

    assert restored.finalized_outcome_source == "observed"
    assert restored.finalized_outcome_capture_mode is None
    assert restored.finalized_outcome_evidence_identities == ()


def test_managed_builder_consumes_evidence_after_freeze(tmp_path) -> None:
    raw_path = tmp_path / "observer.jsonl"
    snapshots = [_snapshot(line_number=1), _snapshot(line_number=2)]
    raw_path.write_text(
        "".join(
            json.dumps(
                {
                    "schema_version": 2,
                    "collector_session_id": snapshot.collector_session_id,
                    "observed_at_utc": snapshot.observed_at_utc.isoformat(),
                    "rpc_slot": snapshot.rpc_slot,
                    "board": snapshot.board.model_dump(mode="json"),
                    "treasury": snapshot.treasury.model_dump(mode="json"),
                    "round": snapshot.round.model_dump(mode="json"),
                }
            )
            + "\n"
            for snapshot in snapshots
        ),
        encoding="utf-8",
    )
    evidence_path = tmp_path / "evidence.jsonl"
    post = _write_evidence(evidence_path)
    output = tmp_path / "dataset.jsonl"

    build_replay_dataset(
        DatasetBuildConfiguration(
            output_path=output,
            metadata_path=tmp_path / "metadata.json",
            dataset_version="rfc012-fixture-v1",
            observer_paths=(raw_path,),
            rfc012_evidence_paths=(evidence_path,),
            enrich_missing_outcomes=False,
            created_at_utc=NOW,
        )
    )
    record = RoundLifecycleIndexRecord.model_validate_json(
        output.read_text(encoding="utf-8").strip()
    )

    assert record.observation_count == 2
    assert record.finalized_outcome.winning_square == 7
    assert record.finalized_outcome_source == "observed"
    assert record.finalized_outcome_capture_mode == "post_transition_predecessor"
    assert record.finalized_outcome_evidence_identities == (
        post.evidence_identity.sha256,
    )


def test_enriched_provenance_cannot_claim_local_capture() -> None:
    lifecycle = _lifecycle()
    outcome = FinalizedRoundOutcome(
        observed_at_utc=NOW,
        rpc_slot=999,
        entropy=7,
        winning_square=7,
        deployed_lamports=list(range(25)),
        miner_counts=[1] * 25,
        reward_buckets=list(range(100, 125)),
        total_vaulted=3_000,
        total_winnings=4_000,
        total_miners=25,
        round_motherlode=2_000,
        top_miner=str(ORE_PROGRAM_IDENTITY),
    )
    invalid = lifecycle.model_copy(
        update={
            "finalized_outcome": outcome,
            "finalized_outcome_source": "enriched",
            "finalized_outcome_capture_mode": "current_round",
        }
    )
    freeze = freeze_decision_snapshots((invalid,))

    with pytest.raises(Rfc012OutcomeConsumptionError, match="enriched provenance"):
        consume_rfc012_outcomes(
            (invalid,), evidence_paths=(), decision_snapshot_freeze=freeze
        )
