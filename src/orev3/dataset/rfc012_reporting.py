"""Deterministic RFC-012 Phase 4 observability reporting.

This module reads immutable Phase 2 transition results and Phase 3 dataset
classifications.  It performs no observation, persistence, dataset assembly,
replay, runtime integration, or command-line work.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from orev3.dataset.rfc012_outcomes import freeze_decision_snapshots
from orev3.datasets.rfc012_evidence import (
    CaptureMode,
    OutcomeSource,
    TerminalDisposition,
    canonical_encode,
)
from orev3.datasets.rfc012_transition import (
    TransitionCandidateStatus,
    TransitionProcessResult,
)
from orev3.historical.models import FinalizedRoundOutcome, RoundLifecycle


EFFECTIVENESS_WINDOW_SCHEMA = "orev3.rfc012.effectiveness-window"
EFFECTIVENESS_WINDOW_VERSION = 1
OBSERVABILITY_REPORT_SCHEMA = "orev3.rfc012.observability-report"
OBSERVABILITY_REPORT_VERSION = 1

_WINDOW_IDENTITY_DOMAIN = "orev3:rfc012:effectiveness-window:v1"
_RESULT_IDENTITY_DOMAIN = "orev3:rfc012:transition-result:v1"
_CLASSIFICATION_IDENTITY_DOMAIN = "orev3:rfc012:outcome-classification:v1"
_REPORT_IDENTITY_DOMAIN = "orev3:rfc012:observability-report:v1"


class Rfc012ReportingError(ValueError):
    """Fail-closed reporting input or reconciliation error."""


@dataclass(frozen=True, slots=True)
class DeterministicRate:
    """Exact rate that gives zero-denominator windows a canonical form."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        _require_nonnegative("numerator", self.numerator)
        _require_nonnegative("denominator", self.denominator)
        if self.numerator > self.denominator:
            raise ValueError("rate numerator cannot exceed denominator")
        if self.denominator == 0 and self.numerator != 0:
            raise ValueError("zero-denominator rate must have zero numerator")

    def to_identity_material(self) -> dict[str, int]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
        }


@dataclass(frozen=True, slots=True)
class AggregateCount:
    """One deterministically ordered categorical count."""

    category: str
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.category, str) or not self.category:
            raise ValueError("aggregate category must be a nonempty string")
        _require_nonnegative("count", self.count)

    def to_identity_material(self) -> dict[str, object]:
        return {"category": self.category, "count": self.count}


@dataclass(frozen=True, slots=True)
class AggregateRate:
    """One deterministically ordered categorical rate."""

    category: str
    rate: DeterministicRate

    def __post_init__(self) -> None:
        if not isinstance(self.category, str) or not self.category:
            raise ValueError("aggregate category must be a nonempty string")
        if not isinstance(self.rate, DeterministicRate):
            raise TypeError("rate must be DeterministicRate")

    def to_identity_material(self) -> dict[str, object]:
        return {"category": self.category, "rate": self.rate}


@dataclass(frozen=True, slots=True)
class TransitionLatency:
    """Exact successor-observation to predecessor-attempt latency."""

    transition_identity: str
    latency_microseconds: int

    def __post_init__(self) -> None:
        _require_sha256("transition_identity", self.transition_identity)
        _require_nonnegative("latency_microseconds", self.latency_microseconds)

    def to_identity_material(self) -> dict[str, object]:
        return {
            "transition_identity": self.transition_identity,
            "latency_microseconds": self.latency_microseconds,
        }


@dataclass(frozen=True, slots=True)
class EffectivenessWindow:
    """Half-open UTC reporting window: ``[start, end)``."""

    start_at_utc: datetime
    end_at_utc: datetime
    window_identity: str = ""

    def __post_init__(self) -> None:
        start = _utc("start_at_utc", self.start_at_utc)
        end = _utc("end_at_utc", self.end_at_utc)
        if end < start:
            raise ValueError("effectiveness window end precedes start")
        object.__setattr__(self, "start_at_utc", start)
        object.__setattr__(self, "end_at_utc", end)
        expected = _digest(
            _WINDOW_IDENTITY_DOMAIN,
            {
                "schema": EFFECTIVENESS_WINDOW_SCHEMA,
                "version": EFFECTIVENESS_WINDOW_VERSION,
                "start_at_utc": start,
                "end_at_utc": end,
            },
        )
        if self.window_identity and self.window_identity != expected:
            raise ValueError("effectiveness window identity does not reconstruct")
        object.__setattr__(self, "window_identity", expected)

    def contains(self, value: datetime) -> bool:
        timestamp = _utc("timestamp", value)
        return self.start_at_utc <= timestamp < self.end_at_utc

    def to_identity_material(self) -> dict[str, object]:
        return {
            "schema": EFFECTIVENESS_WINDOW_SCHEMA,
            "version": EFFECTIVENESS_WINDOW_VERSION,
            "start_at_utc": self.start_at_utc,
            "end_at_utc": self.end_at_utc,
            "window_identity": self.window_identity,
        }


@dataclass(frozen=True, slots=True)
class Rfc012OperationalAggregates:
    """Operational counts reconstructed from immutable transition results."""

    evaluated_transition_results: int
    contiguous_transition_candidates: int
    skipped_transitions: int
    read_eligible_candidates: int
    already_durable_candidates: int
    supplementary_observations_attempted: int
    finalized_predecessor_outcomes_persisted: int
    valid_nonfinal_responses: int
    unavailable_predecessors: int
    context_unproven_results: int
    invalid_or_ambiguous_results: int
    operational_failures: int
    duplicate_finalized_observations_prevented: int
    transition_status_counts: tuple[AggregateCount, ...]
    terminal_disposition_counts: tuple[AggregateCount, ...]
    terminal_disposition_rates: tuple[AggregateRate, ...]
    transition_to_observation_latencies: tuple[TransitionLatency, ...]
    attempt_success_rate: DeterministicRate

    def __post_init__(self) -> None:
        for name in (
            "evaluated_transition_results",
            "contiguous_transition_candidates",
            "skipped_transitions",
            "read_eligible_candidates",
            "already_durable_candidates",
            "supplementary_observations_attempted",
            "finalized_predecessor_outcomes_persisted",
            "valid_nonfinal_responses",
            "unavailable_predecessors",
            "context_unproven_results",
            "invalid_or_ambiguous_results",
            "operational_failures",
            "duplicate_finalized_observations_prevented",
        ):
            _require_nonnegative(name, getattr(self, name))
        _validate_category_tuple(
            "transition_status_counts", self.transition_status_counts, AggregateCount
        )
        _validate_category_tuple(
            "terminal_disposition_counts",
            self.terminal_disposition_counts,
            AggregateCount,
        )
        _validate_category_tuple(
            "terminal_disposition_rates",
            self.terminal_disposition_rates,
            AggregateRate,
        )
        if not isinstance(self.attempt_success_rate, DeterministicRate):
            raise TypeError("attempt_success_rate must be DeterministicRate")
        if not isinstance(self.transition_to_observation_latencies, tuple):
            raise TypeError("transition latencies must be immutable")
        if not all(
            isinstance(item, TransitionLatency)
            for item in self.transition_to_observation_latencies
        ):
            raise TypeError("transition latencies contain an invalid item")
        latency_ids = tuple(
            item.transition_identity
            for item in self.transition_to_observation_latencies
        )
        if latency_ids != tuple(sorted(latency_ids)):
            raise ValueError("transition latencies are not canonical")
        status_counts = {
            item.category: item.count for item in self.transition_status_counts
        }
        expected_statuses = {item.value for item in TransitionCandidateStatus}
        if set(status_counts) != expected_statuses:
            raise ValueError("transition status distribution is incomplete")
        terminal_counts = {
            item.category: item.count
            for item in self.terminal_disposition_counts
        }
        expected_terminals = {item.value for item in TerminalDisposition}
        if set(terminal_counts) != expected_terminals:
            raise ValueError("terminal disposition distribution is incomplete")
        terminal_rates = {
            item.category: item.rate for item in self.terminal_disposition_rates
        }
        if set(terminal_rates) != expected_terminals:
            raise ValueError("terminal disposition rates are incomplete")
        if sum(status_counts.values()) != self.evaluated_transition_results:
            raise ValueError("transition status counts do not reconcile")
        if (
            status_counts[TransitionCandidateStatus.PROCESSED.value]
            != self.contiguous_transition_candidates
            or status_counts[TransitionCandidateStatus.SKIPPED.value]
            != self.skipped_transitions
        ):
            raise ValueError("transition aggregate counts do not reconcile")
        if sum(terminal_counts.values()) != self.contiguous_transition_candidates:
            raise ValueError("terminal disposition counts do not reconcile")
        if any(
            terminal_rates[name]
            != DeterministicRate(
                terminal_counts[name], self.contiguous_transition_candidates
            )
            for name in expected_terminals
        ):
            raise ValueError("terminal disposition rates do not reconcile")
        expected_named_counts = {
            "already_durable_candidates": TerminalDisposition.ALREADY_DURABLE,
            "finalized_predecessor_outcomes_persisted": (
                TerminalDisposition.FINALIZED_PERSISTED
            ),
            "valid_nonfinal_responses": TerminalDisposition.NOT_FINALIZED,
            "unavailable_predecessors": TerminalDisposition.ACCOUNT_UNAVAILABLE,
            "context_unproven_results": TerminalDisposition.CONTEXT_UNPROVEN,
            "invalid_or_ambiguous_results": (
                TerminalDisposition.INVALID_OR_AMBIGUOUS
            ),
            "operational_failures": TerminalDisposition.OPERATIONAL_FAILURE,
        }
        if any(
            getattr(self, field) != terminal_counts[disposition.value]
            for field, disposition in expected_named_counts.items()
        ):
            raise ValueError("named terminal aggregates do not reconcile")
        if (
            self.read_eligible_candidates
            != self.supplementary_observations_attempted
            or len(self.transition_to_observation_latencies)
            != self.supplementary_observations_attempted
            or self.duplicate_finalized_observations_prevented
            != self.already_durable_candidates
            or self.attempt_success_rate
            != DeterministicRate(
                self.finalized_predecessor_outcomes_persisted,
                self.supplementary_observations_attempted,
            )
        ):
            raise ValueError("operational attempt aggregates do not reconcile")

    def to_identity_material(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True)
class Rfc012EffectivenessMetrics:
    """Dataset-bounded effectiveness, separate from conformance."""

    bounded_replay_rounds: int
    total_locally_observed_finalized_outcomes: int
    post_transition_observed_outcomes: int
    outcomes_still_requiring_enrichment: int
    unresolved_outcomes: int
    enrichment_avoided: int
    outcome_completeness_rate: DeterministicRate
    provenance_counts: tuple[AggregateCount, ...]
    capture_mode_counts: tuple[AggregateCount, ...]
    bounded_round_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        for name in (
            "bounded_replay_rounds",
            "total_locally_observed_finalized_outcomes",
            "post_transition_observed_outcomes",
            "outcomes_still_requiring_enrichment",
            "unresolved_outcomes",
            "enrichment_avoided",
        ):
            _require_nonnegative(name, getattr(self, name))
        if not isinstance(self.outcome_completeness_rate, DeterministicRate):
            raise TypeError("outcome_completeness_rate must be DeterministicRate")
        _validate_category_tuple(
            "provenance_counts", self.provenance_counts, AggregateCount
        )
        _validate_category_tuple(
            "capture_mode_counts", self.capture_mode_counts, AggregateCount
        )
        if self.bounded_round_ids != tuple(sorted(set(self.bounded_round_ids))):
            raise ValueError("bounded round identities are not canonical")
        if len(self.bounded_round_ids) != self.bounded_replay_rounds:
            raise ValueError("bounded round count does not reconcile")
        provenance = {
            item.category: item.count for item in self.provenance_counts
        }
        if set(provenance) != {"observed", "enriched", "missing"}:
            raise ValueError("outcome provenance distribution is incomplete")
        captures = {
            item.category: item.count for item in self.capture_mode_counts
        }
        if set(captures) != {
            "current_round",
            "post_transition_predecessor",
            "none",
        }:
            raise ValueError("capture-mode distribution is incomplete")
        if (
            sum(provenance.values()) != self.bounded_replay_rounds
            or sum(captures.values()) != self.bounded_replay_rounds
            or provenance["observed"]
            != self.total_locally_observed_finalized_outcomes
            or provenance["enriched"]
            != self.outcomes_still_requiring_enrichment
            or provenance["missing"] != self.unresolved_outcomes
            or captures["post_transition_predecessor"]
            != self.post_transition_observed_outcomes
            or self.enrichment_avoided
            > self.post_transition_observed_outcomes
            or self.outcome_completeness_rate
            != DeterministicRate(
                provenance["observed"] + provenance["enriched"],
                self.bounded_replay_rounds,
            )
        ):
            raise ValueError("effectiveness aggregates do not reconcile")

    def to_identity_material(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True)
class Rfc012ConformanceAssessment:
    """Structural report conformance; never an effectiveness threshold."""

    immutable_source_identities_valid: bool
    terminal_dispositions_reconcile: bool
    dataset_classifications_reconcile: bool
    effectiveness_threshold_applied: bool = False

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a boolean")
        if self.effectiveness_threshold_applied:
            raise ValueError(
                "RFC-012 conformance cannot use an effectiveness threshold"
            )

    @property
    def conformant(self) -> bool:
        return (
            self.immutable_source_identities_valid
            and self.terminal_dispositions_reconcile
            and self.dataset_classifications_reconcile
        )

    def to_identity_material(self) -> dict[str, bool]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }


@dataclass(frozen=True, slots=True)
class Rfc012ObservabilityReport:
    """Immutable combined operational and effectiveness report."""

    window: EffectivenessWindow
    transition_result_identities: tuple[str, ...]
    baseline_classification_identities: tuple[str, ...]
    reconciled_classification_identities: tuple[str, ...]
    operational: Rfc012OperationalAggregates
    effectiveness: Rfc012EffectivenessMetrics
    conformance: Rfc012ConformanceAssessment
    report_identity: str

    def __post_init__(self) -> None:
        if not isinstance(self.window, EffectivenessWindow):
            raise TypeError("window must be EffectivenessWindow")
        for name in (
            "transition_result_identities",
            "baseline_classification_identities",
            "reconciled_classification_identities",
        ):
            values = getattr(self, name)
            if values != tuple(sorted(set(values))):
                raise ValueError(f"{name} is not canonical")
            for value in values:
                _require_sha256(name, value)
        if not isinstance(self.operational, Rfc012OperationalAggregates):
            raise TypeError("operational aggregates are invalid")
        if not isinstance(self.effectiveness, Rfc012EffectivenessMetrics):
            raise TypeError("effectiveness metrics are invalid")
        if not isinstance(self.conformance, Rfc012ConformanceAssessment):
            raise TypeError("conformance assessment is invalid")
        if (
            len(self.transition_result_identities)
            != self.operational.evaluated_transition_results
            or len(self.baseline_classification_identities)
            != self.effectiveness.bounded_replay_rounds
            or len(self.reconciled_classification_identities)
            != self.effectiveness.bounded_replay_rounds
        ):
            raise ValueError("report source identities do not reconcile")
        _require_sha256("report_identity", self.report_identity)
        if self.report_identity != self.reconstruct_identity():
            raise ValueError("observability report identity does not reconstruct")

    def _identity_material(self) -> dict[str, object]:
        return {
            "schema": OBSERVABILITY_REPORT_SCHEMA,
            "version": OBSERVABILITY_REPORT_VERSION,
            "window": self.window,
            "transition_result_identities": self.transition_result_identities,
            "baseline_classification_identities": (
                self.baseline_classification_identities
            ),
            "reconciled_classification_identities": (
                self.reconciled_classification_identities
            ),
            "operational": self.operational,
            "effectiveness": self.effectiveness,
            "conformance": self.conformance,
        }

    def reconstruct_identity(self) -> str:
        return _digest(_REPORT_IDENTITY_DOMAIN, self._identity_material())

    def to_canonical_bytes(self) -> bytes:
        return canonical_encode(
            {**self._identity_material(), "report_identity": self.report_identity}
        )


@dataclass(frozen=True, slots=True)
class _OutcomeClassification:
    round_id: int
    outcome_identity: str | None
    source: str | None
    capture_mode: str | None
    evidence_identities: tuple[str, ...]
    classification_identity: str

    def to_identity_material(self) -> dict[str, object]:
        return {
            "round_id": self.round_id,
            "outcome_identity": self.outcome_identity,
            "source": self.source,
            "capture_mode": self.capture_mode,
            "evidence_identities": self.evidence_identities,
        }


def build_rfc012_observability_report(
    *,
    transition_results: Iterable[TransitionProcessResult],
    baseline_lifecycles: Iterable[RoundLifecycle],
    reconciled_lifecycles: Iterable[RoundLifecycle],
    window: EffectivenessWindow,
) -> Rfc012ObservabilityReport:
    """Build a deterministic report without mutating any source artifact."""

    if not isinstance(window, EffectivenessWindow):
        raise TypeError("window must be EffectivenessWindow")
    baseline = tuple(baseline_lifecycles)
    reconciled = tuple(reconciled_lifecycles)
    baseline_freeze = freeze_decision_snapshots(baseline)
    reconciled_freeze = freeze_decision_snapshots(reconciled)
    if baseline_freeze != reconciled_freeze:
        raise Rfc012ReportingError(
            "RFC-012 reporting inputs disagree at the decision snapshot boundary"
        )

    selected_results, result_identities = _select_results(
        tuple(transition_results), window
    )
    operational = _operational_aggregates(selected_results)
    round_ids = tuple(
        sorted(
            {
                result.transition_evidence.predecessor_identity.predecessor_round_id
                for result in selected_results
                if result.status is TransitionCandidateStatus.PROCESSED
                and result.transition_evidence is not None
            }
        )
    )
    baseline_classes = _classifications(baseline, round_ids)
    reconciled_classes = _classifications(reconciled, round_ids)
    effectiveness = _effectiveness(
        selected_results, baseline_classes, reconciled_classes, round_ids
    )
    baseline_ids = tuple(
        sorted(item.classification_identity for item in baseline_classes.values())
    )
    reconciled_ids = tuple(
        sorted(item.classification_identity for item in reconciled_classes.values())
    )
    conformance = Rfc012ConformanceAssessment(True, True, True)
    material = {
        "schema": OBSERVABILITY_REPORT_SCHEMA,
        "version": OBSERVABILITY_REPORT_VERSION,
        "window": window,
        "transition_result_identities": result_identities,
        "baseline_classification_identities": baseline_ids,
        "reconciled_classification_identities": reconciled_ids,
        "operational": operational,
        "effectiveness": effectiveness,
        "conformance": conformance,
    }
    return Rfc012ObservabilityReport(
        window=window,
        transition_result_identities=result_identities,
        baseline_classification_identities=baseline_ids,
        reconciled_classification_identities=reconciled_ids,
        operational=operational,
        effectiveness=effectiveness,
        conformance=conformance,
        report_identity=_digest(_REPORT_IDENTITY_DOMAIN, material),
    )


def _select_results(
    results: tuple[TransitionProcessResult, ...],
    window: EffectivenessWindow,
) -> tuple[tuple[TransitionProcessResult, ...], tuple[str, ...]]:
    selected: dict[str, tuple[TransitionProcessResult, str]] = {}
    for result in results:
        if not isinstance(result, TransitionProcessResult):
            raise TypeError("transition_results contains an invalid item")
        if not window.contains(result.successor_snapshot.observed_at_utc):
            continue
        identity = _transition_result_identity(result)
        key = result.successor_snapshot_identity
        previous = selected.get(key)
        if previous is not None and previous[1] != identity:
            raise Rfc012ReportingError(
                "conflicting transition results share a successor snapshot"
            )
        selected[key] = (result, identity)
    ordered = tuple(
        item[0]
        for item in sorted(
            selected.values(),
            key=lambda item: (
                item[0].successor_snapshot.observed_at_utc,
                item[1],
            ),
        )
    )
    identities = tuple(sorted(item[1] for item in selected.values()))
    return ordered, identities


def _transition_result_identity(result: TransitionProcessResult) -> str:
    transition_identity = (
        result.transition_evidence.transition_identity.sha256
        if result.transition_evidence is not None
        else None
    )
    terminal_identity = (
        result.post_transition_evidence.evidence_identity.sha256
        if result.post_transition_evidence is not None
        else None
    )
    return _digest(
        _RESULT_IDENTITY_DOMAIN,
        {
            "status": result.status.value,
            "successor_snapshot_identity": result.successor_snapshot_identity,
            "successor_observed_at_utc": result.successor_snapshot.observed_at_utc,
            "observation_count": result.observation_count,
            "transition_identity": transition_identity,
            "terminal_evidence_identity": terminal_identity,
        },
    )


def _operational_aggregates(
    results: tuple[TransitionProcessResult, ...],
) -> Rfc012OperationalAggregates:
    status_counts = {status: 0 for status in TransitionCandidateStatus}
    disposition_counts = {item: 0 for item in TerminalDisposition}
    latencies: list[TransitionLatency] = []
    for result in results:
        status_counts[result.status] += 1
        if result.status is not TransitionCandidateStatus.PROCESSED:
            continue
        transition = result.transition_evidence
        post = result.post_transition_evidence
        assert transition is not None and post is not None
        if post.transition_evidence != transition:
            raise Rfc012ReportingError(
                "terminal evidence disagrees with transition evidence"
            )
        disposition_counts[post.terminal_disposition] += 1
        if result.observation_count == 1:
            latency = _microseconds_between(
                result.successor_snapshot.observed_at_utc,
                post.attempt_timestamp,
            )
            latencies.append(
                TransitionLatency(transition.transition_identity.sha256, latency)
            )

    candidates = status_counts[TransitionCandidateStatus.PROCESSED]
    attempted = sum(item.observation_count for item in results)
    finalized = disposition_counts[TerminalDisposition.FINALIZED_PERSISTED]
    counts = tuple(
        AggregateCount(item.value, status_counts[item])
        for item in sorted(TransitionCandidateStatus, key=lambda item: item.value)
    )
    terminals = tuple(
        AggregateCount(item.value, disposition_counts[item])
        for item in sorted(TerminalDisposition, key=lambda item: item.value)
    )
    terminal_rates = tuple(
        AggregateRate(
            item.value,
            DeterministicRate(disposition_counts[item], candidates),
        )
        for item in sorted(TerminalDisposition, key=lambda item: item.value)
    )
    already = disposition_counts[TerminalDisposition.ALREADY_DURABLE]
    return Rfc012OperationalAggregates(
        evaluated_transition_results=len(results),
        contiguous_transition_candidates=candidates,
        skipped_transitions=status_counts[TransitionCandidateStatus.SKIPPED],
        read_eligible_candidates=attempted,
        already_durable_candidates=already,
        supplementary_observations_attempted=attempted,
        finalized_predecessor_outcomes_persisted=finalized,
        valid_nonfinal_responses=disposition_counts[TerminalDisposition.NOT_FINALIZED],
        unavailable_predecessors=disposition_counts[
            TerminalDisposition.ACCOUNT_UNAVAILABLE
        ],
        context_unproven_results=disposition_counts[
            TerminalDisposition.CONTEXT_UNPROVEN
        ],
        invalid_or_ambiguous_results=disposition_counts[
            TerminalDisposition.INVALID_OR_AMBIGUOUS
        ],
        operational_failures=disposition_counts[
            TerminalDisposition.OPERATIONAL_FAILURE
        ],
        duplicate_finalized_observations_prevented=already,
        transition_status_counts=counts,
        terminal_disposition_counts=terminals,
        terminal_disposition_rates=terminal_rates,
        transition_to_observation_latencies=tuple(
            sorted(latencies, key=lambda item: item.transition_identity)
        ),
        attempt_success_rate=DeterministicRate(finalized, attempted),
    )


def _classifications(
    lifecycles: tuple[RoundLifecycle, ...],
    round_ids: tuple[int, ...],
) -> dict[int, _OutcomeClassification]:
    by_round: dict[int, RoundLifecycle] = {}
    for lifecycle in lifecycles:
        if lifecycle.round_id in by_round:
            raise Rfc012ReportingError(
                f"duplicate dataset lifecycle for round {lifecycle.round_id}"
            )
        by_round[lifecycle.round_id] = lifecycle
    result: dict[int, _OutcomeClassification] = {}
    for round_id in round_ids:
        lifecycle = by_round.get(round_id)
        if lifecycle is None:
            raise Rfc012ReportingError(
                f"bounded dataset lacks transition round {round_id}"
            )
        result[round_id] = _classification(lifecycle)
    return result


def _classification(lifecycle: RoundLifecycle) -> _OutcomeClassification:
    outcome = lifecycle.finalized_outcome
    source = lifecycle.finalized_outcome_source
    capture = lifecycle.finalized_outcome_capture_mode
    evidence_ids = tuple(lifecycle.finalized_outcome_evidence_identities)
    if evidence_ids != tuple(sorted(set(evidence_ids))):
        raise Rfc012ReportingError("outcome evidence identities are not canonical")
    for identity in evidence_ids:
        _require_sha256("outcome evidence identity", identity)
    if outcome is None:
        if source is not None or capture is not None or evidence_ids:
            raise Rfc012ReportingError("missing outcome contains provenance")
    elif source == OutcomeSource.OBSERVED.value:
        if capture is None:
            if evidence_ids:
                raise Rfc012ReportingError("legacy observed outcome is ambiguous")
            capture = CaptureMode.CURRENT_ROUND.value
        elif capture == CaptureMode.POST_TRANSITION_PREDECESSOR.value:
            if not evidence_ids:
                raise Rfc012ReportingError(
                    "post-transition outcome lacks evidence identity"
                )
        elif capture != CaptureMode.CURRENT_ROUND.value:
            raise Rfc012ReportingError("observed capture mode is invalid")
    elif source == OutcomeSource.ENRICHED.value:
        if capture is not None or evidence_ids:
            raise Rfc012ReportingError("enriched outcome claims local evidence")
    else:
        raise Rfc012ReportingError("finalized outcome provenance is invalid")
    material = {
        "round_id": lifecycle.round_id,
        "outcome_identity": _outcome_identity(outcome),
        "source": source,
        "capture_mode": capture,
        "evidence_identities": evidence_ids,
    }
    return _OutcomeClassification(
        round_id=lifecycle.round_id,
        outcome_identity=material["outcome_identity"],
        source=source,
        capture_mode=capture,
        evidence_identities=evidence_ids,
        classification_identity=_digest(
            _CLASSIFICATION_IDENTITY_DOMAIN, material
        ),
    )


def _effectiveness(
    results: tuple[TransitionProcessResult, ...],
    baseline: dict[int, _OutcomeClassification],
    reconciled: dict[int, _OutcomeClassification],
    round_ids: tuple[int, ...],
) -> Rfc012EffectivenessMetrics:
    finalized_evidence_by_round: dict[int, set[str]] = {}
    for result in results:
        if result.status is not TransitionCandidateStatus.PROCESSED:
            continue
        transition = result.transition_evidence
        post = result.post_transition_evidence
        assert transition is not None and post is not None
        if post.terminal_disposition is TerminalDisposition.FINALIZED_PERSISTED:
            finalized_evidence_by_round.setdefault(
                transition.predecessor_identity.predecessor_round_id, set()
            ).add(post.evidence_identity.sha256)

    provenance = {"observed": 0, "enriched": 0, "missing": 0}
    captures = {
        CaptureMode.CURRENT_ROUND.value: 0,
        CaptureMode.POST_TRANSITION_PREDECESSOR.value: 0,
        "none": 0,
    }
    enrichment_avoided = 0
    for round_id in round_ids:
        before = baseline[round_id]
        after = reconciled[round_id]
        _validate_reconciliation(
            before,
            after,
            finalized_evidence_by_round.get(round_id, set()),
        )
        if after.source is None:
            provenance["missing"] += 1
            captures["none"] += 1
        else:
            provenance[after.source] += 1
            assert after.capture_mode is not None or after.source == "enriched"
            captures[after.capture_mode or "none"] += 1
        if (
            before.source == OutcomeSource.ENRICHED.value
            and after.source == OutcomeSource.OBSERVED.value
            and after.capture_mode
            == CaptureMode.POST_TRANSITION_PREDECESSOR.value
        ):
            enrichment_avoided += 1

    observed = provenance[OutcomeSource.OBSERVED.value]
    enriched = provenance[OutcomeSource.ENRICHED.value]
    unresolved = provenance["missing"]
    return Rfc012EffectivenessMetrics(
        bounded_replay_rounds=len(round_ids),
        total_locally_observed_finalized_outcomes=observed,
        post_transition_observed_outcomes=captures[
            CaptureMode.POST_TRANSITION_PREDECESSOR.value
        ],
        outcomes_still_requiring_enrichment=enriched,
        unresolved_outcomes=unresolved,
        enrichment_avoided=enrichment_avoided,
        outcome_completeness_rate=DeterministicRate(
            observed + enriched, len(round_ids)
        ),
        provenance_counts=tuple(
            AggregateCount(name, provenance[name])
            for name in sorted(provenance)
        ),
        capture_mode_counts=tuple(
            AggregateCount(name, captures[name])
            for name in sorted(captures)
        ),
        bounded_round_ids=round_ids,
    )


def _validate_reconciliation(
    before: _OutcomeClassification,
    after: _OutcomeClassification,
    finalized_evidence_ids: set[str],
) -> None:
    if before.round_id != after.round_id:
        raise Rfc012ReportingError("outcome classification round mismatch")
    if after.capture_mode == CaptureMode.POST_TRANSITION_PREDECESSOR.value:
        if after.source != OutcomeSource.OBSERVED.value:
            raise Rfc012ReportingError(
                "post-transition capture is not locally observed"
            )
        if not finalized_evidence_ids.intersection(after.evidence_identities):
            raise Rfc012ReportingError(
                "post-transition classification lacks finalized evidence"
            )
        if before.source == OutcomeSource.OBSERVED.value:
            raise Rfc012ReportingError(
                "post-transition evidence replaced an existing local observation"
            )
        if before.outcome_identity is not None and (
            before.outcome_identity != after.outcome_identity
        ):
            raise Rfc012ReportingError(
                "post-transition and prior finalized outcomes conflict"
            )
        return
    if (
        before.outcome_identity != after.outcome_identity
        or before.source != after.source
        or (before.capture_mode or CaptureMode.CURRENT_ROUND.value)
        != (after.capture_mode or CaptureMode.CURRENT_ROUND.value)
    ):
        raise Rfc012ReportingError(
            "dataset classification changed outside post-transition consumption"
        )


def _outcome_identity(outcome: FinalizedRoundOutcome | None) -> str | None:
    if outcome is None:
        return None
    material = outcome.model_dump(
        mode="json", exclude={"observed_at_utc", "rpc_slot"}
    )
    return hashlib.sha256(canonical_encode(material)).hexdigest()


def _microseconds_between(start: datetime, end: datetime) -> int:
    delta = _utc("attempt start", end) - _utc("successor observation", start)
    microseconds = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    if microseconds < 0:
        raise Rfc012ReportingError(
            "predecessor observation predates its successor transition"
        )
    return microseconds


def _validate_category_tuple(
    name: str,
    values: tuple[object, ...],
    expected_type: type,
) -> None:
    if not isinstance(values, tuple) or not all(
        isinstance(item, expected_type) for item in values
    ):
        raise TypeError(f"{name} must be an immutable categorical tuple")
    categories = tuple(item.category for item in values)
    if categories != tuple(sorted(set(categories))):
        raise ValueError(f"{name} is not canonical")


def _utc(name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise TypeError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _require_nonnegative(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _require_sha256(name: str, value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _digest(domain: str, material: object) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


__all__ = (
    "AggregateCount",
    "AggregateRate",
    "DeterministicRate",
    "EffectivenessWindow",
    "Rfc012ConformanceAssessment",
    "Rfc012EffectivenessMetrics",
    "Rfc012ObservabilityReport",
    "Rfc012OperationalAggregates",
    "Rfc012ReportingError",
    "TransitionLatency",
    "build_rfc012_observability_report",
)
