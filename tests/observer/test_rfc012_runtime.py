from __future__ import annotations

import base64
import json
import struct
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from orev3.data.models import (
    BoardState,
    ObserverSnapshot,
    RoundState,
    TreasuryState,
)
from orev3.data.writer import CollectorEventWriter, JsonlSnapshotWriter
from orev3.dataset.rfc012_outcomes import (
    consume_rfc012_outcomes,
    freeze_decision_snapshots,
)
from orev3.dataset.rfc012_reporting import (
    EffectivenessWindow,
    build_rfc012_observability_report,
)
from orev3.datasets.rfc012_evidence import (
    ORE_PROGRAM_IDENTITY,
    ORE_PROTOCOL_REVISION,
    ROUND_DECODER_IDENTITY,
    SOLANA_MAINNET_GENESIS_HASH,
    SOLANA_MAINNET_NETWORK,
    CanonicalPredecessorIdentity,
    CaptureMode,
    OutcomeSource,
    TerminalDisposition,
)
from orev3.datasets.rfc012_transition import (
    PredecessorObservation,
    Rfc012EvidenceStore,
    Rfc012TransitionProcessor,
    TransitionCandidateStatus,
)
from orev3.historical.assembler import assemble_rounds
from orev3.historical.models import NormalizedSnapshot
from orev3.observer import collect as collect_module
from orev3.observer.accounts import BOARD_ADDRESS, ROUND_ACCOUNT_TYPE, decode_round
from orev3.observer.collect import collect_iteration, collect_snapshot_with_context
from orev3.observer.rfc012_runtime import (
    ContextualObserverSnapshot,
    Rfc012RuntimeIntegration,
    SnapshotFinalizedHistory,
    SolanaPredecessorReader,
    create_supported_rfc012_runtime,
    observer_snapshot_identity,
)
from orev3.observer.rpc import SolanaRpcClient
from orev3.replay.engine import snapshot_to_replay_point
from orev3.strategy_lab.runner import _decision_context_from_replay_point


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def _round_bytes(*, round_id: int, finalized: bool) -> bytes:
    slot_hash = struct.pack("<QQQQ", 7, 0, 0, 0) if finalized else bytes(32)
    return b"".join(
        (
            bytes([ROUND_ACCOUNT_TYPE]) + bytes(7),
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


def _round_state(round_id: int, *, finalized: bool = False) -> RoundState:
    encoded = base64.b64encode(
        _round_bytes(round_id=round_id, finalized=finalized)
    ).decode("ascii")
    return decode_round({"data": [encoded, "base64"]})


def _snapshot(
    round_id: int,
    *,
    finalized: bool = False,
    session_id: str = "runtime-session",
) -> ObserverSnapshot:
    return ObserverSnapshot(
        collector_session_id=session_id,
        observed_at_utc=NOW,
        rpc_slot=900 + round_id,
        board=BoardState(round_id=round_id, start_slot=900, end_slot=1_000),
        treasury=TreasuryState(motherlode=10),
        round=_round_state(round_id, finalized=finalized),
    )


def _contextual(
    round_id: int,
    *,
    session_id: str = "runtime-session",
) -> ContextualObserverSnapshot:
    snapshot = _snapshot(round_id, session_id=session_id)
    return ContextualObserverSnapshot(
        snapshot=snapshot,
        snapshot_identity=observer_snapshot_identity(snapshot),
        provider_identity="runtime-provider",
        board_response_commitment="confirmed",
        board_response_context_slot=900,
    )


class _Reader:
    def __init__(self, *, finalized: bool = True) -> None:
        self.finalized = finalized
        self.calls: list[tuple[str, str, int]] = []

    def observe_predecessor(
        self,
        address: str,
        *,
        commitment: str,
        min_context_slot: int,
    ) -> PredecessorObservation:
        self.calls.append((address, commitment, min_context_slot))
        predecessor = CanonicalPredecessorIdentity.for_round(41)
        return PredecessorObservation(
            network_identity=SOLANA_MAINNET_NETWORK,
            expected_genesis_hash=SOLANA_MAINNET_GENESIS_HASH,
            provider_identity="runtime-provider",
            account_address=predecessor.canonical_round_pda,
            response_context_slot=min_context_slot + 1,
            response_commitment=commitment,
            account_owner=ORE_PROGRAM_IDENTITY,
            raw_account_data=_round_bytes(
                round_id=41,
                finalized=self.finalized,
            ),
            ore_program_identity=ORE_PROGRAM_IDENTITY,
            protocol_revision=ORE_PROTOCOL_REVISION,
            decoder_identity=ROUND_DECODER_IDENTITY,
        )


class _NoHistory:
    def has_finalized(self, identity) -> bool:
        return False


def _runtime(
    tmp_path: Path,
    *,
    reader: _Reader | None = None,
    history=None,
) -> tuple[Rfc012RuntimeIntegration, _Reader, Rfc012EvidenceStore]:
    selected_reader = reader or _Reader()
    store = Rfc012EvidenceStore(tmp_path / "evidence.jsonl")
    processor = Rfc012TransitionProcessor(
        reader=selected_reader,
        evidence_store=store,
        finalized_history=history or _NoHistory(),
        clock=lambda: NOW,
    )
    return (
        Rfc012RuntimeIntegration(
            processor=processor,
            event_writer=CollectorEventWriter(tmp_path / "events"),
        ),
        selected_reader,
        store,
    )


def _normalized_snapshot(round_id: int = 41) -> NormalizedSnapshot:
    state = _round_state(round_id)
    return NormalizedSnapshot(
        source_schema_version=2,
        collector_session_id="runtime-session",
        observed_at_utc=NOW,
        rpc_slot=941,
        board={"round_id": round_id, "start_slot": 900, "end_slot": 1_000},
        treasury={"motherlode": 10},
        round=state.model_dump(mode="python"),
        source_file="observer.jsonl",
        source_line_number=1,
    )


def test_collect_retains_exact_board_response_context(monkeypatch) -> None:
    board = BoardState(round_id=42, start_slot=900, end_slot=1_000)
    treasury = TreasuryState(motherlode=10)
    round_state = _round_state(42)

    class Rpc:
        provider_identity = "runtime-provider"

        def get_slot(self):
            return 942

        def get_multiple_accounts_with_context(self, addresses, *, commitment):
            assert commitment == "confirmed"
            return {"context": {"slot": 937}, "value": [{}, {}]}

        def get_account_info(self, address):
            return {}

    monkeypatch.setattr(collect_module, "decode_board", lambda value: board)
    monkeypatch.setattr(collect_module, "decode_treasury", lambda value: treasury)
    monkeypatch.setattr(collect_module, "decode_round", lambda value: round_state)

    result = collect_snapshot_with_context(Rpc(), "runtime-session")

    assert result.snapshot.board.round_id == 42
    assert result.board_response_context_slot == 937
    assert result.board_response_commitment == "confirmed"
    assert result.snapshot_identity == observer_snapshot_identity(result.snapshot)


def test_successor_is_fsynced_before_phase2_invocation(
    monkeypatch,
    tmp_path,
) -> None:
    ordering: list[str] = []
    successor = _contextual(42)
    runtime, _, _ = _runtime(tmp_path)
    original_process = runtime.process_transition

    def process(**kwargs):
        ordering.append("processor")
        return original_process(**kwargs)

    monkeypatch.setattr(runtime, "process_transition", process)
    monkeypatch.setattr(
        collect_module,
        "collect_snapshot_with_context",
        lambda rpc, session_id: successor,
    )
    monkeypatch.setattr(
        "orev3.data.writer.os.fsync",
        lambda descriptor: ordering.append("fsync"),
    )

    result = collect_iteration(
        rpc=object(),
        session_id="runtime-session",
        writer=JsonlSnapshotWriter(tmp_path / "raw"),
        event_writer=CollectorEventWriter(tmp_path / "events"),
        rfc012_runtime=runtime,
        previous_round_id=41,
    )

    assert ordering[0] == "fsync"
    assert ordering.index("processor") > ordering.index("fsync")
    assert result.transition_result.status is TransitionCandidateStatus.PROCESSED


def test_unchanged_snapshot_preserves_existing_nondurable_write(
    monkeypatch,
    tmp_path,
) -> None:
    fsync_calls: list[int] = []
    successor = _contextual(42)
    runtime, reader, _ = _runtime(tmp_path)
    monkeypatch.setattr(
        collect_module,
        "collect_snapshot_with_context",
        lambda rpc, session_id: successor,
    )
    monkeypatch.setattr(
        "orev3.data.writer.os.fsync",
        lambda descriptor: fsync_calls.append(descriptor),
    )

    result = collect_iteration(
        rpc=object(),
        session_id="runtime-session",
        writer=JsonlSnapshotWriter(tmp_path / "raw"),
        event_writer=CollectorEventWriter(tmp_path / "events"),
        rfc012_runtime=runtime,
        previous_round_id=42,
    )

    assert result.transition_result.status is TransitionCandidateStatus.UNCHANGED
    assert fsync_calls == []
    assert reader.calls == []


@pytest.mark.parametrize(
    ("previous", "current", "status"),
    [
        (None, 42, TransitionCandidateStatus.INITIAL),
        (42, 42, TransitionCandidateStatus.UNCHANGED),
        (40, 42, TransitionCandidateStatus.SKIPPED),
        (43, 42, TransitionCandidateStatus.REGRESSED),
    ],
)
def test_runtime_delegates_candidate_classification_with_zero_reads(
    tmp_path,
    previous,
    current,
    status,
) -> None:
    runtime, reader, _ = _runtime(tmp_path)

    result = runtime.process_transition(
        previous_round_id=previous,
        successor=_contextual(current),
        successor_durably_persisted=(
            previous is not None and current != previous
        ),
    )

    assert result.status is status
    assert result.observation_count == 0
    assert reader.calls == []


def test_runtime_finalized_path_reads_once_and_preserves_append_order(
    tmp_path,
) -> None:
    runtime, reader, store = _runtime(tmp_path)

    result = runtime.process_transition(
        previous_round_id=41,
        successor=_contextual(42),
        successor_durably_persisted=True,
    )

    assert result.status is TransitionCandidateStatus.PROCESSED
    assert result.observation_count == 1
    assert len(reader.calls) == 1
    assert store.record_types() == (
        "transition",
        "finalized_payload",
        "post_transition",
    )
    assert result.post_transition_evidence is not None
    assert (
        result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.FINALIZED_PERSISTED
    )


def test_supplementary_failure_preserves_successor_and_iteration(
    monkeypatch,
    tmp_path,
) -> None:
    class FailingReader(_Reader):
        def observe_predecessor(
            self,
            address: str,
            *,
            commitment: str,
            min_context_slot: int,
        ) -> PredecessorObservation:
            self.calls.append((address, commitment, min_context_slot))
            raise RuntimeError("controlled predecessor failure")

    successor = _contextual(42)
    runtime, reader, _ = _runtime(tmp_path, reader=FailingReader())
    monkeypatch.setattr(
        collect_module,
        "collect_snapshot_with_context",
        lambda rpc, session_id: successor,
    )

    iteration = collect_iteration(
        rpc=object(),
        session_id="runtime-session",
        writer=JsonlSnapshotWriter(tmp_path / "raw"),
        event_writer=CollectorEventWriter(tmp_path / "events"),
        rfc012_runtime=runtime,
        previous_round_id=41,
    )

    records = tuple((tmp_path / "raw").glob("observer_*.jsonl"))
    assert len(records) == 1
    assert json.loads(records[0].read_text(encoding="utf-8"))[
        "board"
    ]["round_id"] == 42
    assert len(reader.calls) == 1
    assert iteration.transition_result.post_transition_evidence is not None
    assert (
        iteration.transition_result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.OPERATIONAL_FAILURE
    )


def test_runtime_already_durable_path_performs_zero_reads(tmp_path) -> None:
    writer = JsonlSnapshotWriter(tmp_path / "raw")
    writer.write(_snapshot(41, finalized=True))
    runtime, reader, store = _runtime(
        tmp_path,
        history=SnapshotFinalizedHistory(writer),
    )

    result = runtime.process_transition(
        previous_round_id=41,
        successor=_contextual(42),
        successor_durably_persisted=True,
    )

    assert reader.calls == []
    assert result.observation_count == 0
    assert result.post_transition_evidence is not None
    assert (
        result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.ALREADY_DURABLE
    )
    assert store.record_types() == ("transition", "post_transition")


def test_rpc_adapter_preserves_context_and_uses_canonical_payload() -> None:
    raw = _round_bytes(round_id=41, finalized=True)

    class Rpc:
        provider_identity = "runtime-provider"

        def __init__(self):
            self.calls = []

        def get_account_info_with_context(
            self,
            address,
            *,
            commitment,
            min_context_slot,
        ):
            self.calls.append((address, commitment, min_context_slot))
            return {
                "context": {"slot": 902},
                "value": {
                    "owner": ORE_PROGRAM_IDENTITY,
                    "data": [base64.b64encode(raw).decode("ascii"), "base64"],
                },
            }

    rpc = Rpc()
    predecessor = CanonicalPredecessorIdentity.for_round(41)
    observed = SolanaPredecessorReader(rpc).observe_predecessor(
        predecessor.canonical_round_pda,
        commitment="confirmed",
        min_context_slot=900,
    )

    assert rpc.calls == [
        (predecessor.canonical_round_pda, "confirmed", 900)
    ]
    assert observed.response_context_slot == 902
    assert observed.raw_account_data == raw
    assert observed.account_owner == ORE_PROGRAM_IDENTITY


def test_provider_identity_is_stable_and_excludes_secrets() -> None:
    first = SolanaRpcClient(
        "https://user:secret@rpc.example:443/private?api-key=secret"
    )
    second = SolanaRpcClient("https://rpc.example:443/other?token=different")
    try:
        assert first.provider_identity == second.provider_identity
        assert "secret" not in first.provider_identity
        assert "private" not in first.provider_identity
        assert "rpc.example" not in first.provider_identity
    finally:
        first.close()
        second.close()


def test_supported_runtime_factory_preserves_duplicate_history_across_restart(
    tmp_path,
) -> None:
    class Rpc:
        provider_identity = "runtime-provider"

        def __init__(self):
            self.calls = 0

        def get_account_info_with_context(
            self,
            address,
            *,
            commitment,
            min_context_slot,
        ):
            self.calls += 1
            return {
                "context": {"slot": min_context_slot + 1},
                "value": {
                    "owner": ORE_PROGRAM_IDENTITY,
                    "data": [
                        base64.b64encode(
                            _round_bytes(round_id=41, finalized=True)
                        ).decode("ascii"),
                        "base64",
                    ],
                },
            }

    writer = JsonlSnapshotWriter(tmp_path / "raw")
    event_writer = CollectorEventWriter(tmp_path / "events")
    rpc = Rpc()
    first = create_supported_rfc012_runtime(
        rpc=rpc,
        snapshot_writer=writer,
        event_writer=event_writer,
        evidence_root=tmp_path / "evidence",
    )
    second = create_supported_rfc012_runtime(
        rpc=rpc,
        snapshot_writer=writer,
        event_writer=event_writer,
        evidence_root=tmp_path / "evidence",
    )

    first_result = first.process_transition(
        previous_round_id=41,
        successor=_contextual(42, session_id="session-a"),
        successor_durably_persisted=True,
    )
    second_result = second.process_transition(
        previous_round_id=41,
        successor=_contextual(42, session_id="session-b"),
        successor_durably_persisted=True,
    )
    assert first_result.observation_count == 1
    assert second_result.observation_count == 0
    assert rpc.calls == 1
    assert second_result.post_transition_evidence is not None
    assert (
        second_result.post_transition_evidence.terminal_disposition
        is TerminalDisposition.ALREADY_DURABLE
    )


def test_end_to_end_outcome_only_consumption_and_report_exposure(
    tmp_path,
) -> None:
    runtime, _, store = _runtime(tmp_path)
    transition_result = runtime.process_transition(
        previous_round_id=41,
        successor=_contextual(42),
        successor_durably_persisted=True,
    )
    baseline = assemble_rounds((_normalized_snapshot(),)).rounds[0]
    freeze = freeze_decision_snapshots((baseline,))

    reconciled = consume_rfc012_outcomes(
        (baseline,),
        evidence_paths=(store.path,),
        decision_snapshot_freeze=freeze,
    )[0]

    assert freeze_decision_snapshots((reconciled,)) == freeze
    assert reconciled.finalized_outcome_source == OutcomeSource.OBSERVED.value
    assert (
        reconciled.finalized_outcome_capture_mode
        == CaptureMode.POST_TRANSITION_PREDECESSOR.value
    )
    replay_point = snapshot_to_replay_point(reconciled.first_observation)
    context = _decision_context_from_replay_point(replay_point)
    forbidden = {
        "winning_square",
        "finalized_outcome",
        "post_transition_evidence",
        "capture_mode",
    }
    assert forbidden.isdisjoint(context.information)

    report = build_rfc012_observability_report(
        transition_results=(transition_result,),
        baseline_lifecycles=(baseline,),
        reconciled_lifecycles=(reconciled,),
        window=EffectivenessWindow(NOW, NOW + timedelta(minutes=1)),
    )
    event_path = runtime.expose_report(report)
    event = json.loads(event_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["report_identity"] == report.report_identity
    assert (
        base64.b64decode(event["canonical_report_base64"])
        == report.to_canonical_bytes()
    )


def test_legacy_collect_snapshot_api_returns_normal_snapshot(monkeypatch) -> None:
    successor = _contextual(42)
    monkeypatch.setattr(
        collect_module,
        "collect_snapshot_with_context",
        lambda rpc, session_id: successor,
    )

    assert collect_module.collect_snapshot(object(), "session") == successor.snapshot
