"""RFC-012 Phase 3 outcome-only Dataset Builder consumption.

Normal observation histories are frozen before this module opens an RFC-012
evidence source.  Accepted post-transition evidence may replace or populate
only finalized outcome and provenance fields on newly copied lifecycle
objects; it never becomes a replay snapshot.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping

from orev3.data.models import RoundState
from orev3.datasets.rfc012_evidence import (
    CaptureMode,
    CanonicalPredecessorIdentity,
    ORE_PROTOCOL_REVISION,
    OutcomeSource,
    PostTransitionEvidence,
    TerminalDisposition,
    canonical_encode,
)
from orev3.datasets.rfc012_transition import (
    EvidenceStoreError,
    Rfc012EvidenceStore,
)
from orev3.historical.enricher import is_finalized_round_state
from orev3.historical.models import (
    FinalizedRoundOutcome,
    RoundLifecycle,
)


DEFAULT_RFC012_EVIDENCE_ROOT = Path("data/raw/rfc012")
DEFAULT_RFC012_EVIDENCE_PATTERN = "*.jsonl"

_COMMITMENT_ORDER = {"processed": 0, "confirmed": 1, "finalized": 2}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Rfc012OutcomeConsumptionError(ValueError):
    """Fail-closed RFC-012 evidence or reconciliation error."""


@dataclass(frozen=True, slots=True)
class DecisionSnapshotIdentity:
    """Byte-stable identity of one round's ordered decision snapshots."""

    round_id: int
    observation_count: int
    ordered_snapshots_sha256: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.round_id, bool)
            or not isinstance(self.round_id, int)
            or self.round_id < 0
        ):
            raise ValueError("round_id must be a nonnegative integer")
        if (
            isinstance(self.observation_count, bool)
            or not isinstance(self.observation_count, int)
            or self.observation_count < 1
        ):
            raise ValueError("observation_count must be a positive integer")
        if not _SHA256.fullmatch(self.ordered_snapshots_sha256):
            raise ValueError(
                "ordered_snapshots_sha256 must be a lowercase SHA-256 digest"
            )


@dataclass(frozen=True, slots=True)
class DecisionSnapshotFreeze:
    """Immutable proof created before any RFC-012 evidence is parsed."""

    rounds: tuple[DecisionSnapshotIdentity, ...]
    freeze_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.rounds, tuple) or not all(
            isinstance(item, DecisionSnapshotIdentity) for item in self.rounds
        ):
            raise TypeError("rounds must be immutable snapshot identities")
        round_ids = tuple(item.round_id for item in self.rounds)
        if len(set(round_ids)) != len(round_ids):
            raise ValueError("decision snapshot freeze contains duplicate rounds")
        if not _SHA256.fullmatch(self.freeze_sha256):
            raise ValueError("freeze_sha256 must be a lowercase SHA-256 digest")

    def verify(self, lifecycles: Iterable[RoundLifecycle]) -> None:
        reconstructed = freeze_decision_snapshots(lifecycles)
        if reconstructed != self:
            raise Rfc012OutcomeConsumptionError(
                "decision snapshot freeze changed during outcome consumption"
            )


@dataclass(frozen=True, slots=True)
class Rfc012FinalizedOutcomeEvidence:
    """Validated outcome-only projection of one finalized Phase 2 record."""

    predecessor_identity: CanonicalPredecessorIdentity
    outcome: FinalizedRoundOutcome
    canonical_outcome_sha256: str
    protocol_payload_sha256: str
    evidence_identity: str

    def __post_init__(self) -> None:
        for name in (
            "canonical_outcome_sha256",
            "protocol_payload_sha256",
            "evidence_identity",
        ):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def discover_rfc012_evidence(
    root: str | Path = DEFAULT_RFC012_EVIDENCE_ROOT,
    *,
    pattern: str = DEFAULT_RFC012_EVIDENCE_PATTERN,
) -> tuple[Path, ...]:
    """Discover Phase 2 evidence separately and in deterministic path order."""

    source_root = Path(root)
    if not source_root.exists():
        return ()
    return tuple(
        sorted(
            path
            for path in source_root.rglob(pattern)
            if path.is_file()
        )
    )


def freeze_decision_snapshots(
    lifecycles: Iterable[RoundLifecycle],
) -> DecisionSnapshotFreeze:
    """Freeze the exact ordered normal-snapshot state of every lifecycle."""

    identities: list[DecisionSnapshotIdentity] = []
    seen: set[int] = set()
    for lifecycle in tuple(lifecycles):
        if lifecycle.round_id in seen:
            raise Rfc012OutcomeConsumptionError(
                f"duplicate lifecycle for round {lifecycle.round_id}"
            )
        seen.add(lifecycle.round_id)
        if lifecycle.observation_count != len(lifecycle.observation_history):
            raise Rfc012OutcomeConsumptionError(
                f"round {lifecycle.round_id} observation count is inconsistent"
            )
        material = tuple(
            snapshot.model_dump(mode="json")
            for snapshot in lifecycle.observation_history
        )
        digest = hashlib.sha256(canonical_encode(material)).hexdigest()
        identities.append(
            DecisionSnapshotIdentity(
                round_id=lifecycle.round_id,
                observation_count=lifecycle.observation_count,
                ordered_snapshots_sha256=digest,
            )
        )
    freeze_material = tuple(
        {
            "round_id": identity.round_id,
            "observation_count": identity.observation_count,
            "ordered_snapshots_sha256": identity.ordered_snapshots_sha256,
        }
        for identity in identities
    )
    return DecisionSnapshotFreeze(
        rounds=tuple(identities),
        freeze_sha256=hashlib.sha256(
            canonical_encode(freeze_material)
        ).hexdigest(),
    )


def consume_rfc012_outcomes(
    lifecycles: Iterable[RoundLifecycle],
    *,
    evidence_paths: Iterable[str | Path],
    decision_snapshot_freeze: DecisionSnapshotFreeze,
) -> tuple[RoundLifecycle, ...]:
    """Apply valid evidence only after verifying the decision-state freeze."""

    original = tuple(lifecycles)
    if not isinstance(decision_snapshot_freeze, DecisionSnapshotFreeze):
        raise TypeError("decision_snapshot_freeze must be DecisionSnapshotFreeze")

    # This verification precedes path traversal, file opening, or evidence
    # parsing and is the executable Phase 3 freeze boundary.
    decision_snapshot_freeze.verify(original)
    paths = tuple(sorted({Path(path) for path in evidence_paths}))
    evidence = _read_finalized_evidence(paths)
    reconciled = _reconcile(original, evidence)
    decision_snapshot_freeze.verify(reconciled)
    return reconciled


def _read_finalized_evidence(
    paths: tuple[Path, ...],
) -> tuple[Rfc012FinalizedOutcomeEvidence, ...]:
    accepted: list[Rfc012FinalizedOutcomeEvidence] = []
    seen_evidence: dict[str, Rfc012FinalizedOutcomeEvidence] = {}
    for path in paths:
        if not path.is_file():
            raise Rfc012OutcomeConsumptionError(
                f"RFC-012 evidence source is unavailable: {path}"
            )
        store = Rfc012EvidenceStore(path)
        try:
            transitions = store.transitions()
            finalized_payloads = store.finalized_payloads()
            posts = store.post_transitions()
        except (EvidenceStoreError, KeyError, TypeError, ValueError) as exc:
            raise Rfc012OutcomeConsumptionError(
                f"invalid RFC-012 evidence source: {path}"
            ) from exc

        transitions_by_identity = {
            transition.transition_identity.sha256: transition
            for transition in transitions
        }
        payloads_by_predecessor: dict[
            CanonicalPredecessorIdentity,
            dict[str, object],
        ] = {}
        for predecessor, payload in finalized_payloads:
            values = payloads_by_predecessor.setdefault(predecessor, {})
            existing = values.get(payload.protocol_payload_sha256)
            if existing is None:
                values[payload.protocol_payload_sha256] = payload
            elif existing != payload:
                raise Rfc012OutcomeConsumptionError(
                    "ambiguous RFC-012 finalized payload identity"
                )

        for post in posts:
            if post.terminal_disposition is not TerminalDisposition.FINALIZED_PERSISTED:
                continue
            transition_identity = (
                post.transition_evidence.transition_identity.sha256
            )
            if (
                transitions_by_identity.get(transition_identity)
                != post.transition_evidence
            ):
                raise Rfc012OutcomeConsumptionError(
                    "RFC-012 terminal evidence lacks its transition record"
                )
            projected = _project_finalized_post(post, payloads_by_predecessor)
            previous = seen_evidence.get(projected.evidence_identity)
            if previous is not None and previous != projected:
                raise Rfc012OutcomeConsumptionError(
                    "conflicting RFC-012 evidence identity"
                )
            if previous is None:
                seen_evidence[projected.evidence_identity] = projected
                accepted.append(projected)
    return tuple(
        sorted(
            accepted,
            key=lambda item: (
                item.predecessor_identity.predecessor_round_id,
                item.evidence_identity,
            ),
        )
    )


def _project_finalized_post(
    post: PostTransitionEvidence,
    payloads_by_predecessor: Mapping[
        CanonicalPredecessorIdentity,
        Mapping[str, object],
    ],
) -> Rfc012FinalizedOutcomeEvidence:
    transition = post.transition_evidence
    predecessor = transition.predecessor_identity
    context = transition.transition_context
    if (
        post.predecessor_response_context_slot is None
        or post.predecessor_response_commitment not in _COMMITMENT_ORDER
        or post.predecessor_response_context_slot
        < context.board_response_context_slot
        or _COMMITMENT_ORDER[post.predecessor_response_commitment]
        < _COMMITMENT_ORDER[context.board_response_commitment]
    ):
        raise Rfc012OutcomeConsumptionError(
            "RFC-012 finalized evidence has invalid response context"
        )
    payload = post.protocol_payload
    if (
        payload is None
        or payload.protocol_revision != ORE_PROTOCOL_REVISION
        or payload.decoded_round is None
    ):
        raise Rfc012OutcomeConsumptionError(
            "RFC-012 finalized evidence has invalid protocol payload"
        )
    persisted = payloads_by_predecessor.get(predecessor, {}).get(
        payload.protocol_payload_sha256
    )
    if persisted != payload:
        raise Rfc012OutcomeConsumptionError(
            "RFC-012 finalized disposition lacks its durable payload"
        )
    try:
        round_state = RoundState.model_validate(payload.decoded_round)
    except Exception as exc:
        raise Rfc012OutcomeConsumptionError(
            "RFC-012 decoded Round payload is invalid"
        ) from exc
    if (
        round_state.round_id != predecessor.predecessor_round_id
        or not is_finalized_round_state(round_state)
    ):
        raise Rfc012OutcomeConsumptionError(
            "RFC-012 payload is not an explicit finalized predecessor"
        )
    outcome = _round_state_to_outcome(
        round_state,
        observed_at_utc=post.attempt_timestamp,
        rpc_slot=post.predecessor_response_context_slot,
    )
    return Rfc012FinalizedOutcomeEvidence(
        predecessor_identity=predecessor,
        outcome=outcome,
        canonical_outcome_sha256=_outcome_sha256(outcome),
        protocol_payload_sha256=payload.protocol_payload_sha256,
        evidence_identity=post.evidence_identity.sha256,
    )


def _reconcile(
    lifecycles: tuple[RoundLifecycle, ...],
    evidence: tuple[Rfc012FinalizedOutcomeEvidence, ...],
) -> tuple[RoundLifecycle, ...]:
    by_round: dict[int, list[Rfc012FinalizedOutcomeEvidence]] = {}
    for item in evidence:
        by_round.setdefault(
            item.predecessor_identity.predecessor_round_id, []
        ).append(item)

    result: list[RoundLifecycle] = []
    for lifecycle in lifecycles:
        candidates = by_round.get(lifecycle.round_id, [])
        if not candidates:
            result.append(_canonicalize_existing_provenance(lifecycle))
            continue
        canonical_predecessor = CanonicalPredecessorIdentity.for_round(
            lifecycle.round_id
        )
        if any(
            candidate.predecessor_identity != canonical_predecessor
            for candidate in candidates
        ):
            raise Rfc012OutcomeConsumptionError(
                f"round {lifecycle.round_id} predecessor identity mismatch"
            )
        outcome_hashes = {
            candidate.canonical_outcome_sha256 for candidate in candidates
        }
        if len(outcome_hashes) != 1:
            raise Rfc012OutcomeConsumptionError(
                f"conflicting RFC-012 outcomes for round {lifecycle.round_id}"
            )
        selected = candidates[0]
        identities = tuple(
            sorted(
                set(lifecycle.finalized_outcome_evidence_identities)
                | {candidate.evidence_identity for candidate in candidates}
            )
        )
        existing = lifecycle.finalized_outcome
        source = lifecycle.finalized_outcome_source
        if existing is not None:
            if _outcome_sha256(existing) != selected.canonical_outcome_sha256:
                raise Rfc012OutcomeConsumptionError(
                    f"conflicting finalized outcomes for round {lifecycle.round_id}"
                )
            if source not in {
                OutcomeSource.OBSERVED.value,
                OutcomeSource.ENRICHED.value,
            }:
                raise Rfc012OutcomeConsumptionError(
                    f"invalid outcome provenance for round {lifecycle.round_id}"
                )
        if source == OutcomeSource.OBSERVED.value:
            outcome = existing
            capture_mode = (
                CaptureMode.POST_TRANSITION_PREDECESSOR.value
                if lifecycle.finalized_outcome_capture_mode
                == CaptureMode.POST_TRANSITION_PREDECESSOR.value
                else CaptureMode.CURRENT_ROUND.value
            )
        else:
            outcome = selected.outcome
            capture_mode = CaptureMode.POST_TRANSITION_PREDECESSOR.value
        result.append(
            lifecycle.model_copy(
                update={
                    "finalized_outcome": outcome,
                    "finalized_outcome_source": OutcomeSource.OBSERVED.value,
                    "finalized_outcome_capture_mode": capture_mode,
                    "finalized_outcome_evidence_identities": identities,
                }
            )
        )
    return tuple(result)


def _canonicalize_existing_provenance(
    lifecycle: RoundLifecycle,
) -> RoundLifecycle:
    outcome = lifecycle.finalized_outcome
    source = lifecycle.finalized_outcome_source
    if outcome is None:
        if (
            source is not None
            or lifecycle.finalized_outcome_capture_mode is not None
            or lifecycle.finalized_outcome_evidence_identities
        ):
            raise Rfc012OutcomeConsumptionError(
                f"round {lifecycle.round_id} has provenance without an outcome"
            )
        return lifecycle
    if source == OutcomeSource.OBSERVED.value:
        capture = lifecycle.finalized_outcome_capture_mode
        if capture is None:
            if lifecycle.finalized_outcome_evidence_identities:
                raise Rfc012OutcomeConsumptionError(
                    f"round {lifecycle.round_id} has ambiguous legacy provenance"
                )
            return lifecycle.model_copy(
                update={
                    "finalized_outcome_capture_mode": CaptureMode.CURRENT_ROUND.value
                }
            )
        if capture == CaptureMode.POST_TRANSITION_PREDECESSOR.value:
            if not lifecycle.finalized_outcome_evidence_identities:
                raise Rfc012OutcomeConsumptionError(
                    f"round {lifecycle.round_id} lacks post-transition evidence"
                )
            return lifecycle
        if capture != CaptureMode.CURRENT_ROUND.value:
            raise Rfc012OutcomeConsumptionError(
                f"round {lifecycle.round_id} has invalid observed capture mode"
            )
        return lifecycle
    if source == OutcomeSource.ENRICHED.value:
        if (
            lifecycle.finalized_outcome_capture_mode is not None
            or lifecycle.finalized_outcome_evidence_identities
        ):
            raise Rfc012OutcomeConsumptionError(
                f"round {lifecycle.round_id} has invalid enriched provenance"
            )
        return lifecycle
    raise Rfc012OutcomeConsumptionError(
        f"round {lifecycle.round_id} has invalid outcome provenance"
    )


def _round_state_to_outcome(
    round_state: RoundState,
    *,
    observed_at_utc: datetime,
    rpc_slot: int,
) -> FinalizedRoundOutcome:
    entropy = round_state.entropy
    return FinalizedRoundOutcome(
        observed_at_utc=observed_at_utc,
        rpc_slot=rpc_slot,
        entropy=entropy,
        winning_square=entropy % 25 if entropy is not None else None,
        deployed_lamports=round_state.deployed_lamports,
        miner_counts=round_state.miner_counts,
        reward_buckets=round_state.rewards,
        total_vaulted=round_state.total_vaulted,
        total_winnings=round_state.total_winnings,
        total_miners=round_state.total_miners,
        round_motherlode=round_state.motherlode,
        top_miner=round_state.top_miner,
    )


def _outcome_sha256(outcome: FinalizedRoundOutcome) -> str:
    # Capture time and response slot describe provenance, not protocol outcome
    # identity, so independently captured agreeing outcomes remain comparable.
    material = outcome.model_dump(mode="json", exclude={"observed_at_utc", "rpc_slot"})
    return hashlib.sha256(canonical_encode(material)).hexdigest()


__all__ = (
    "DEFAULT_RFC012_EVIDENCE_PATTERN",
    "DEFAULT_RFC012_EVIDENCE_ROOT",
    "DecisionSnapshotFreeze",
    "DecisionSnapshotIdentity",
    "Rfc012FinalizedOutcomeEvidence",
    "Rfc012OutcomeConsumptionError",
    "consume_rfc012_outcomes",
    "discover_rfc012_evidence",
    "freeze_decision_snapshots",
)
