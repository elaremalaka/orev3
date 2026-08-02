from __future__ import annotations

import base64
import hashlib
import struct
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from orev3.data.models import BoardState, ObserverSnapshot, TreasuryState
from orev3.dataset import (
    DeterministicRate,
    EffectivenessWindow,
    Rfc012ConformanceAssessment,
    Rfc012ReportingError,
    build_rfc012_observability_report,
)
from orev3.datasets.rfc012_evidence import (
    CaptureMode,
    CanonicalPredecessorIdentity,
    FailureCategory,
    OutcomeSource,
    PostTransitionEvidence,
    PreservedProtocolPayload,
    TerminalDisposition,
    TransitionContext,
    TransitionEvidence,
    ValidationOutcome,
)
from orev3.datasets.rfc012_transition import (
    TransitionCandidateStatus,
    TransitionProcessResult,
)
from orev3.historical.assembler import assemble_rounds
from orev3.historical.models import FinalizedRoundOutcome, NormalizedSnapshot
from orev3.observer.accounts import BOARD_ADDRESS, ROUND_ACCOUNT_TYPE, decode_round


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def _round_bytes(*, round_id: int, finalized: bool) -> bytes:
    entropy = (round_id % 24) + 1
    header = bytes([ROUND_ACCOUNT_TYPE]) + bytes(7)
    slot_hash = (
        struct.pack("<QQQQ", entropy, 0, 0, 0)
        if finalized
        else bytes(32)
    )
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


def _round_state(*, round_id: int, finalized: bool):
    raw = _round_bytes(round_id=round_id, finalized=finalized)
    return decode_round(
        {"data": [base64.b64encode(raw).decode("ascii"), "base64"]}
    )


def _observer_snapshot(
    *, round_id: int, observed_at: datetime, identity_seed: str
) -> tuple[ObserverSnapshot, str]:
    successor = round_id + 1
    snapshot = ObserverSnapshot(
        collector_session_id="observer-session-001",
        observed_at_utc=observed_at,
        rpc_slot=10_000 + successor,
        board=BoardState(
            round_id=successor,
            start_slot=10_000,
            end_slot=11_000,
        ),
        treasury=TreasuryState(motherlode=10),
        round=_round_state(round_id=successor, finalized=False),
    )
    identity = hashlib.sha256(identity_seed.encode("utf-8")).hexdigest()
    return snapshot, identity


def _processed_result(
    *,
    round_id: int,
    disposition: TerminalDisposition,
    observed_at: datetime | None = None,
    attempt_delay_microseconds: int = 500_000,
    identity_seed: str | None = None,
) -> TransitionProcessResult:
    observed = observed_at or NOW
    snapshot, snapshot_identity = _observer_snapshot(
        round_id=round_id,
        observed_at=observed,
        identity_seed=identity_seed or f"snapshot-{round_id}-{disposition.value}",
    )
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
        board_response_context_slot=10_000,
    )
    transition = TransitionEvidence.create(
        observer_session_identity="observer-session-001",
        predecessor_identity=predecessor,
        successor_round_id=round_id + 1,
        successor_snapshot_identity=snapshot_identity,
        transition_context=context,
    )
    attempt = observed + timedelta(microseconds=attempt_delay_microseconds)
    if disposition is TerminalDisposition.FINALIZED_PERSISTED:
        raw = _round_bytes(round_id=round_id, finalized=True)
        payload = PreservedProtocolPayload.create(
            raw_account_data=raw,
            decoded_round=_round_state(
                round_id=round_id, finalized=True
            ).model_dump(mode="python"),
        )
        arguments = {
            "predecessor_response_context_slot": 10_001,
            "predecessor_response_commitment": "confirmed",
            "response_raw_account_sha256": payload.raw_account_sha256,
            "protocol_payload": payload,
            "validation_outcome": ValidationOutcome.VALID,
            "failure_category": None,
            "finalized_state": True,
            "outcome_source": OutcomeSource.OBSERVED,
            "capture_mode": CaptureMode.POST_TRANSITION_PREDECESSOR,
        }
        observation_count = 1
    elif disposition is TerminalDisposition.NOT_FINALIZED:
        raw = _round_bytes(round_id=round_id, finalized=False)
        payload = PreservedProtocolPayload.create(
            raw_account_data=raw,
            decoded_round=_round_state(
                round_id=round_id, finalized=False
            ).model_dump(mode="python"),
        )
        arguments = {
            "predecessor_response_context_slot": 10_001,
            "predecessor_response_commitment": "confirmed",
            "response_raw_account_sha256": payload.raw_account_sha256,
            "protocol_payload": payload,
            "validation_outcome": ValidationOutcome.VALID,
            "failure_category": None,
            "finalized_state": False,
            "outcome_source": None,
            "capture_mode": None,
        }
        observation_count = 1
    elif disposition is TerminalDisposition.ALREADY_DURABLE:
        arguments = {
            "predecessor_response_context_slot": None,
            "predecessor_response_commitment": None,
            "response_raw_account_sha256": None,
            "protocol_payload": None,
            "validation_outcome": ValidationOutcome.NOT_EVALUATED,
            "failure_category": None,
            "finalized_state": None,
            "outcome_source": None,
            "capture_mode": None,
        }
        observation_count = 0
    else:
        category = {
            TerminalDisposition.ACCOUNT_UNAVAILABLE: (
                FailureCategory.ACCOUNT_UNAVAILABLE
            ),
            TerminalDisposition.CONTEXT_UNPROVEN: FailureCategory.CONTEXT_UNPROVEN,
            TerminalDisposition.INVALID_OR_AMBIGUOUS: (
                FailureCategory.PAYLOAD_MALFORMED
            ),
            TerminalDisposition.OPERATIONAL_FAILURE: (
                FailureCategory.OBSERVATION_FAILURE
            ),
        }[disposition]
        outcome = (
            ValidationOutcome.UNAVAILABLE
            if disposition is TerminalDisposition.ACCOUNT_UNAVAILABLE
            else ValidationOutcome.OPERATIONAL_FAILURE
            if disposition is TerminalDisposition.OPERATIONAL_FAILURE
            else ValidationOutcome.INVALID
        )
        arguments = {
            "predecessor_response_context_slot": None,
            "predecessor_response_commitment": None,
            "response_raw_account_sha256": None,
            "protocol_payload": None,
            "validation_outcome": outcome,
            "failure_category": category,
            "finalized_state": None,
            "outcome_source": None,
            "capture_mode": None,
        }
        observation_count = 1
    post = PostTransitionEvidence.create(
        transition_evidence=transition,
        attempt_timestamp=attempt,
        terminal_disposition=disposition,
        **arguments,
    )
    return TransitionProcessResult(
        status=TransitionCandidateStatus.PROCESSED,
        successor_snapshot=snapshot,
        successor_snapshot_identity=snapshot_identity,
        observation_count=observation_count,
        transition_evidence=transition,
        post_transition_evidence=post,
    )


def _noncandidate_result(
    *, status: TransitionCandidateStatus, seed: str, observed_at: datetime = NOW
) -> TransitionProcessResult:
    snapshot, identity = _observer_snapshot(
        round_id=500, observed_at=observed_at, identity_seed=seed
    )
    return TransitionProcessResult(
        status=status,
        successor_snapshot=snapshot,
        successor_snapshot_identity=identity,
        observation_count=0,
    )


def _normalized_snapshot(*, round_id: int) -> NormalizedSnapshot:
    state = _round_state(round_id=round_id, finalized=False)
    return NormalizedSnapshot(
        source_schema_version=2,
        observed_at_utc=NOW,
        rpc_slot=9_000 + round_id,
        collector_session_id="dataset-session",
        board={
            "round_id": round_id,
            "start_slot": 9_000,
            "end_slot": 10_000,
            "production_cost_ema": 1,
        },
        treasury={"motherlode": 10},
        round=state.model_dump(mode="python"),
        source_file="observer.jsonl",
        source_line_number=round_id,
    )


def _outcome(*, round_id: int, observed_at: datetime = NOW) -> FinalizedRoundOutcome:
    state = _round_state(round_id=round_id, finalized=True)
    assert state.entropy is not None
    return FinalizedRoundOutcome(
        observed_at_utc=observed_at,
        rpc_slot=10_001,
        entropy=state.entropy,
        winning_square=state.entropy % 25,
        deployed_lamports=state.deployed_lamports,
        miner_counts=state.miner_counts,
        reward_buckets=state.rewards,
        total_vaulted=state.total_vaulted,
        total_winnings=state.total_winnings,
        total_miners=state.total_miners,
        round_motherlode=state.motherlode,
        top_miner=state.top_miner,
    )


def _lifecycle(
    *,
    round_id: int,
    source: str | None = None,
    capture: str | None = None,
    evidence_ids: tuple[str, ...] = (),
    outcome: FinalizedRoundOutcome | None = None,
):
    base = assemble_rounds((_normalized_snapshot(round_id=round_id),)).rounds[0]
    return base.model_copy(
        update={
            "finalized_outcome": outcome,
            "finalized_outcome_source": source,
            "finalized_outcome_capture_mode": capture,
            "finalized_outcome_evidence_identities": evidence_ids,
        }
    )


def _window() -> EffectivenessWindow:
    return EffectivenessWindow(NOW, NOW + timedelta(hours=1))


def _report(results, baseline, reconciled, window=None):
    return build_rfc012_observability_report(
        transition_results=results,
        baseline_lifecycles=baseline,
        reconciled_lifecycles=reconciled,
        window=window or _window(),
    )


def test_window_identity_is_canonical_and_half_open() -> None:
    pacific = timezone(timedelta(hours=-7))
    equivalent_start = NOW.astimezone(pacific)
    first = EffectivenessWindow(NOW, NOW + timedelta(hours=1))
    second = EffectivenessWindow(
        equivalent_start,
        (NOW + timedelta(hours=1)).astimezone(pacific),
    )

    assert first == second
    assert first.contains(NOW)
    assert not first.contains(NOW + timedelta(hours=1))
    assert len(first.window_identity) == 64


def test_window_rejects_naive_or_reversed_boundaries() -> None:
    with pytest.raises(TypeError, match="timezone-aware"):
        EffectivenessWindow(NOW.replace(tzinfo=None), NOW)
    with pytest.raises(ValueError, match="precedes"):
        EffectivenessWindow(NOW, NOW - timedelta(seconds=1))


def test_operational_aggregates_cover_every_status_and_disposition() -> None:
    dispositions = tuple(TerminalDisposition)
    results = [
        _processed_result(round_id=100 + index, disposition=disposition)
        for index, disposition in enumerate(dispositions)
    ]
    results.extend(
        (
            _noncandidate_result(
                status=TransitionCandidateStatus.INITIAL, seed="initial"
            ),
            _noncandidate_result(
                status=TransitionCandidateStatus.SKIPPED, seed="skipped"
            ),
        )
    )
    baseline = []
    reconciled = []
    for index, (result, disposition) in enumerate(zip(results, dispositions)):
        round_id = 100 + index
        if disposition is TerminalDisposition.FINALIZED_PERSISTED:
            post = result.post_transition_evidence
            assert post is not None
            baseline.append(_lifecycle(round_id=round_id))
            reconciled.append(
                _lifecycle(
                    round_id=round_id,
                    source="observed",
                    capture="post_transition_predecessor",
                    evidence_ids=(post.evidence_identity.sha256,),
                    outcome=_outcome(round_id=round_id),
                )
            )
        elif disposition is TerminalDisposition.ALREADY_DURABLE:
            outcome = _outcome(round_id=round_id)
            baseline.append(
                _lifecycle(round_id=round_id, source="observed", outcome=outcome)
            )
            reconciled.append(
                _lifecycle(
                    round_id=round_id,
                    source="observed",
                    capture="current_round",
                    outcome=outcome,
                )
            )
        else:
            baseline.append(_lifecycle(round_id=round_id))
            reconciled.append(_lifecycle(round_id=round_id))

    report = _report(results, baseline, reconciled)

    assert report.operational.evaluated_transition_results == 9
    assert report.operational.contiguous_transition_candidates == 7
    assert report.operational.skipped_transitions == 1
    assert report.operational.already_durable_candidates == 1
    assert report.operational.supplementary_observations_attempted == 6
    assert report.operational.finalized_predecessor_outcomes_persisted == 1
    assert report.operational.valid_nonfinal_responses == 1
    assert report.operational.unavailable_predecessors == 1
    assert report.operational.context_unproven_results == 1
    assert report.operational.invalid_or_ambiguous_results == 1
    assert report.operational.operational_failures == 1
    assert report.operational.duplicate_finalized_observations_prevented == 1
    assert report.operational.attempt_success_rate == DeterministicRate(1, 6)
    assert len(report.operational.transition_to_observation_latencies) == 6
    assert {item.count for item in report.operational.terminal_disposition_counts} == {
        1
    }


def test_repeated_reconstruction_and_input_order_are_deterministic() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.FINALIZED_PERSISTED
    )
    post = result.post_transition_evidence
    assert post is not None
    before = _lifecycle(round_id=41)
    after = _lifecycle(
        round_id=41,
        source="observed",
        capture="post_transition_predecessor",
        evidence_ids=(post.evidence_identity.sha256,),
        outcome=_outcome(round_id=41),
    )
    skipped = _noncandidate_result(
        status=TransitionCandidateStatus.SKIPPED, seed="skip"
    )

    first = _report((result, skipped), (before,), (after,))
    second = _report((skipped, result), (before,), (after,))

    assert first == second
    assert first.to_canonical_bytes() == second.to_canonical_bytes()
    assert first.report_identity == first.reconstruct_identity()


def test_identical_duplicate_result_is_counted_once() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.NOT_FINALIZED
    )
    lifecycle = _lifecycle(round_id=41)

    report = _report((result, result), (lifecycle,), (lifecycle,))

    assert report.operational.contiguous_transition_candidates == 1
    assert len(report.transition_result_identities) == 1


def test_conflicting_results_for_one_snapshot_fail_closed() -> None:
    first = _processed_result(
        round_id=41,
        disposition=TerminalDisposition.NOT_FINALIZED,
        identity_seed="shared",
    )
    second = _processed_result(
        round_id=41,
        disposition=TerminalDisposition.ACCOUNT_UNAVAILABLE,
        identity_seed="shared",
    )
    lifecycle = _lifecycle(round_id=41)

    with pytest.raises(Rfc012ReportingError, match="conflicting transition"):
        _report((first, second), (lifecycle,), (lifecycle,))


def test_window_excludes_results_at_end_boundary() -> None:
    inside = _noncandidate_result(
        status=TransitionCandidateStatus.SKIPPED,
        seed="inside",
        observed_at=NOW,
    )
    outside = _noncandidate_result(
        status=TransitionCandidateStatus.SKIPPED,
        seed="outside",
        observed_at=NOW + timedelta(hours=1),
    )

    report = _report((outside, inside), (), ())

    assert report.operational.evaluated_transition_results == 1
    assert report.operational.skipped_transitions == 1


def test_empty_window_and_zero_denominators_are_deterministic() -> None:
    report = _report((), (), (), EffectivenessWindow(NOW, NOW))

    assert report.operational.attempt_success_rate == DeterministicRate(0, 0)
    assert report.effectiveness.outcome_completeness_rate == DeterministicRate(
        0, 0
    )
    assert report.effectiveness.bounded_round_ids == ()
    assert report.conformance.conformant


def test_enrichment_avoided_uses_exact_bounded_counterfactual() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.FINALIZED_PERSISTED
    )
    post = result.post_transition_evidence
    assert post is not None
    enriched = _outcome(round_id=41, observed_at=NOW - timedelta(days=1))
    local = _outcome(round_id=41)
    baseline = _lifecycle(round_id=41, source="enriched", outcome=enriched)
    reconciled = _lifecycle(
        round_id=41,
        source="observed",
        capture="post_transition_predecessor",
        evidence_ids=(post.evidence_identity.sha256,),
        outcome=local,
    )

    report = _report((result,), (baseline,), (reconciled,))

    assert report.effectiveness.enrichment_avoided == 1
    assert report.effectiveness.total_locally_observed_finalized_outcomes == 1
    assert report.effectiveness.outcomes_still_requiring_enrichment == 0


def test_missing_counterfactual_is_not_enrichment_avoided() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.FINALIZED_PERSISTED
    )
    post = result.post_transition_evidence
    assert post is not None
    baseline = _lifecycle(round_id=41)
    reconciled = _lifecycle(
        round_id=41,
        source="observed",
        capture="post_transition_predecessor",
        evidence_ids=(post.evidence_identity.sha256,),
        outcome=_outcome(round_id=41),
    )

    report = _report((result,), (baseline,), (reconciled,))

    assert report.effectiveness.enrichment_avoided == 0
    assert report.effectiveness.post_transition_observed_outcomes == 1


def test_pre_rfc012_observed_classification_remains_current_round() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.ALREADY_DURABLE
    )
    legacy = _lifecycle(
        round_id=41, source="observed", outcome=_outcome(round_id=41)
    )
    current = legacy.model_copy(
        update={"finalized_outcome_capture_mode": "current_round"}
    )

    report = _report((result,), (legacy,), (current,))

    assert report.effectiveness.total_locally_observed_finalized_outcomes == 1
    assert report.effectiveness.post_transition_observed_outcomes == 0
    assert report.effectiveness.enrichment_avoided == 0


def test_failed_attempt_cannot_claim_post_transition_outcome() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.ACCOUNT_UNAVAILABLE
    )
    evidence_id = result.post_transition_evidence.evidence_identity.sha256
    before = _lifecycle(round_id=41)
    after = _lifecycle(
        round_id=41,
        source="observed",
        capture="post_transition_predecessor",
        evidence_ids=(evidence_id,),
        outcome=_outcome(round_id=41),
    )

    with pytest.raises(Rfc012ReportingError, match="finalized evidence"):
        _report((result,), (before,), (after,))


def test_conflicting_enrichment_and_local_outcome_fails_closed() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.FINALIZED_PERSISTED
    )
    post = result.post_transition_evidence
    assert post is not None
    conflicting = _outcome(round_id=41).model_copy(
        update={"total_winnings": 99_999}
    )
    before = _lifecycle(round_id=41, source="enriched", outcome=conflicting)
    after = _lifecycle(
        round_id=41,
        source="observed",
        capture="post_transition_predecessor",
        evidence_ids=(post.evidence_identity.sha256,),
        outcome=_outcome(round_id=41),
    )

    with pytest.raises(Rfc012ReportingError, match="conflict"):
        _report((result,), (before,), (after,))


def test_decision_snapshot_change_fails_before_reporting() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.NOT_FINALIZED
    )
    before = _lifecycle(round_id=41)
    changed_snapshot = before.observation_history[0].model_copy(
        update={"rpc_slot": before.observation_history[0].rpc_slot + 1}
    )
    after = before.model_copy(
        update={
            "observation_history": [changed_snapshot],
            "first_observation": changed_snapshot,
            "last_observation": changed_snapshot,
        }
    )

    with pytest.raises(Rfc012ReportingError, match="decision snapshot"):
        _report((result,), (before,), (after,))


def test_report_generation_does_not_mutate_inputs() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.NOT_FINALIZED
    )
    lifecycle = _lifecycle(round_id=41)
    snapshot_before = lifecycle.model_dump(mode="json")

    report = _report((result,), (lifecycle,), (lifecycle,))

    assert lifecycle.model_dump(mode="json") == snapshot_before
    with pytest.raises(FrozenInstanceError):
        report.report_identity = "0" * 64


def test_conformance_is_independent_of_effectiveness() -> None:
    success = _processed_result(
        round_id=41, disposition=TerminalDisposition.FINALIZED_PERSISTED
    )
    post = success.post_transition_evidence
    assert post is not None
    successful_report = _report(
        (success,),
        (_lifecycle(round_id=41),),
        (
            _lifecycle(
                round_id=41,
                source="observed",
                capture="post_transition_predecessor",
                evidence_ids=(post.evidence_identity.sha256,),
                outcome=_outcome(round_id=41),
            ),
        ),
    )
    failure = _processed_result(
        round_id=42, disposition=TerminalDisposition.ACCOUNT_UNAVAILABLE
    )
    missing = _lifecycle(round_id=42)
    failed_report = _report((failure,), (missing,), (missing,))

    assert successful_report.conformance == failed_report.conformance
    assert successful_report.conformance.conformant
    assert not successful_report.conformance.effectiveness_threshold_applied
    assert successful_report.effectiveness != failed_report.effectiveness


def test_conformance_rejects_effectiveness_threshold() -> None:
    with pytest.raises(ValueError, match="effectiveness threshold"):
        Rfc012ConformanceAssessment(True, True, True, True)


def test_negative_transition_latency_fails_closed() -> None:
    result = _processed_result(
        round_id=41,
        disposition=TerminalDisposition.NOT_FINALIZED,
        attempt_delay_microseconds=-1,
    )
    lifecycle = _lifecycle(round_id=41)

    with pytest.raises(Rfc012ReportingError, match="predates"):
        _report((result,), (lifecycle,), (lifecycle,))


def test_missing_bounded_dataset_round_fails_closed() -> None:
    result = _processed_result(
        round_id=41, disposition=TerminalDisposition.NOT_FINALIZED
    )

    with pytest.raises(Rfc012ReportingError, match="lacks transition round"):
        _report((result,), (), ())


def test_public_api_exposes_phase4_reporting_contracts() -> None:
    from orev3 import dataset

    assert dataset.EffectivenessWindow is EffectivenessWindow
    assert dataset.DeterministicRate is DeterministicRate
    assert (
        dataset.build_rfc012_observability_report
        is build_rfc012_observability_report
    )
