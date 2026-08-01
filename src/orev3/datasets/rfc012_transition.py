"""Isolated RFC-012 Phase 2 transition processing.

The processor in this module is intentionally not wired into the continuous
Observer.  It accepts an already validated and durably persisted successor,
performs at most one context-bound predecessor observation, and appends an
immutable RFC-012 evidence stream.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Protocol

from orev3.data.models import ObserverSnapshot, RoundState
from orev3.data.writer import append_json_line, is_finalized_round
from orev3.datasets.rfc012_evidence import (
    CaptureMode,
    CanonicalPredecessorIdentity,
    FailureCategory,
    ORE_PROGRAM_IDENTITY,
    ORE_PROTOCOL_REVISION,
    OutcomeSource,
    PostTransitionEvidence,
    PreservedProtocolPayload,
    ROUND_DECODER_IDENTITY,
    TerminalDisposition,
    TransitionContext,
    TransitionEvidence,
    TransitionIdentity,
    ValidationOutcome,
    canonical_decode,
    canonical_encode,
)
from orev3.observer.accounts import decode_round


_COMMITMENT_ORDER = {"processed": 0, "confirmed": 1, "finalized": 2}
_RECORD_SCHEMA = "orev3.rfc012.transition-store"
_RECORD_VERSION = 1


class TransitionCandidateStatus(str, Enum):
    """Outcome of transition-candidate detection before the bounded branch."""

    INITIAL = "initial"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    REGRESSED = "regressed"
    AMBIGUOUS = "ambiguous"
    INVALID_SUCCESSOR = "invalid_successor"
    PROCESSED = "processed"


@dataclass(frozen=True, slots=True)
class PredecessorObservation:
    """One non-secret, context-preserving predecessor RPC result."""

    network_identity: str
    expected_genesis_hash: str
    provider_identity: str
    account_address: str | None
    response_context_slot: int | None
    response_commitment: str | None
    account_owner: str | None
    raw_account_data: bytes | None
    ore_program_identity: str
    protocol_revision: str
    decoder_identity: str

    def __post_init__(self) -> None:
        if self.response_context_slot is not None and (
            isinstance(self.response_context_slot, bool)
            or not isinstance(self.response_context_slot, int)
            or self.response_context_slot < 0
        ):
            raise ValueError("response_context_slot must be nonnegative")
        if self.raw_account_data is not None and not isinstance(
            self.raw_account_data, bytes
        ):
            raise TypeError("raw_account_data must be immutable bytes")


class PredecessorReader(Protocol):
    """Boundary that submits one logical context-bound observation."""

    def observe_predecessor(
        self,
        account_address: str,
        *,
        commitment: str,
        min_context_slot: int,
    ) -> PredecessorObservation: ...


class FinalizedHistory(Protocol):
    """Read-only durable finalized-identity boundary."""

    def has_finalized(
        self, predecessor_identity: CanonicalPredecessorIdentity
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class TransitionProcessResult:
    """Immutable result of one isolated processor invocation."""

    status: TransitionCandidateStatus
    successor_snapshot: ObserverSnapshot
    successor_snapshot_identity: str
    observation_count: int
    transition_evidence: TransitionEvidence | None = None
    post_transition_evidence: PostTransitionEvidence | None = None

    def __post_init__(self) -> None:
        if self.observation_count not in (0, 1):
            raise ValueError("observation_count must be zero or one")
        if self.status is TransitionCandidateStatus.PROCESSED:
            if (
                self.transition_evidence is None
                or self.post_transition_evidence is None
            ):
                raise ValueError("processed result requires complete evidence")
        elif (
            self.transition_evidence is not None
            or self.post_transition_evidence is not None
        ):
            raise ValueError("non-candidate result cannot contain transition evidence")


class EvidenceStoreError(RuntimeError):
    """Base failure for the append-only Phase 2 evidence boundary."""


class EvidenceAmbiguityError(EvidenceStoreError):
    """Existing immutable evidence conflicts with the requested append."""


@dataclass(frozen=True, slots=True)
class _StoredRecord:
    record_type: str
    key: str
    canonical_payload: bytes


class Rfc012EvidenceStore:
    """Append-only durable RFC-012 producer/reader boundary.

    The physical JSONL envelope is an implementation choice.  Semantic data
    remains the canonical Phase 1 encoding and is never emitted as an Observer
    current-round snapshot.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append_transition(self, evidence: TransitionEvidence) -> bool:
        return self._append(
            "transition",
            evidence.transition_identity.sha256,
            evidence.to_canonical_bytes(),
        )

    def append_finalized_payload(
        self,
        predecessor: CanonicalPredecessorIdentity,
        payload: PreservedProtocolPayload,
    ) -> bool:
        material = {
            "predecessor_identity": predecessor.to_identity_material(),
            "protocol_payload": _payload_mapping(payload),
            "outcome_source": OutcomeSource.OBSERVED.value,
            "capture_mode": CaptureMode.POST_TRANSITION_PREDECESSOR.value,
        }
        return self._append(
            "finalized_payload",
            _predecessor_key(predecessor),
            canonical_encode(material),
        )

    def append_post_transition(self, evidence: PostTransitionEvidence) -> bool:
        return self._append(
            "post_transition",
            evidence.transition_evidence.transition_identity.sha256,
            evidence.to_canonical_bytes(),
        )

    def has_finalized(
        self, predecessor_identity: CanonicalPredecessorIdentity
    ) -> bool:
        return any(
            predecessor == predecessor_identity
            for predecessor, _ in self.finalized_payloads()
        )

    def finalized_payloads(
        self,
    ) -> tuple[
        tuple[CanonicalPredecessorIdentity, PreservedProtocolPayload], ...
    ]:
        """Return fully reconstructed, identity-validated finalized payloads."""

        return tuple(
            _finalized_payload_from_record(record)
            for record in self._records()
            if record.record_type == "finalized_payload"
        )

    def find_post_transition(
        self, transition_identity: TransitionIdentity
    ) -> PostTransitionEvidence | None:
        matches = [
            record
            for record in self._records()
            if record.record_type == "post_transition"
            and record.key == transition_identity.sha256
        ]
        if not matches:
            return None
        first = matches[0]
        if any(
            record.canonical_payload != first.canonical_payload
            for record in matches[1:]
        ):
            raise EvidenceAmbiguityError("conflicting terminal evidence exists")
        return PostTransitionEvidence.from_canonical_bytes(first.canonical_payload)

    def record_types(self) -> tuple[str, ...]:
        return tuple(record.record_type for record in self._records())

    def transitions(self) -> tuple[TransitionEvidence, ...]:
        return tuple(
            TransitionEvidence.from_canonical_bytes(record.canonical_payload)
            for record in self._records()
            if record.record_type == "transition"
        )

    def post_transitions(self) -> tuple[PostTransitionEvidence, ...]:
        return tuple(
            PostTransitionEvidence.from_canonical_bytes(record.canonical_payload)
            for record in self._records()
            if record.record_type == "post_transition"
        )

    def _append(self, record_type: str, key: str, canonical_payload: bytes) -> bool:
        matches = [
            record
            for record in self._records()
            if record.record_type == record_type and record.key == key
        ]
        if matches:
            if all(record.canonical_payload == canonical_payload for record in matches):
                return False
            raise EvidenceAmbiguityError(
                f"conflicting immutable {record_type} record exists"
            )
        append_json_line(
            self.path,
            {
                "schema_identifier": _RECORD_SCHEMA,
                "schema_version": _RECORD_VERSION,
                "record_type": record_type,
                "key": key,
                "canonical_payload_base64": base64.b64encode(
                    canonical_payload
                ).decode("ascii"),
            },
            durable=True,
        )
        return True

    def _records(self) -> tuple[_StoredRecord, ...]:
        if not self.path.exists():
            return ()
        records: list[_StoredRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise EvidenceStoreError(
                        f"malformed RFC-012 evidence at line {line_number}"
                    ) from exc
                expected = {
                    "schema_identifier",
                    "schema_version",
                    "record_type",
                    "key",
                    "canonical_payload_base64",
                }
                if not isinstance(value, dict) or set(value) != expected:
                    raise EvidenceStoreError(
                        f"invalid RFC-012 evidence envelope at line {line_number}"
                    )
                if (
                    value["schema_identifier"] != _RECORD_SCHEMA
                    or value["schema_version"] != _RECORD_VERSION
                    or value["record_type"]
                    not in {"transition", "finalized_payload", "post_transition"}
                    or not isinstance(value["key"], str)
                ):
                    raise EvidenceStoreError(
                        f"unsupported RFC-012 evidence at line {line_number}"
                    )
                try:
                    payload = base64.b64decode(
                        value["canonical_payload_base64"], validate=True
                    )
                    canonical_decode(payload)
                except (TypeError, ValueError) as exc:
                    raise EvidenceStoreError(
                        f"invalid canonical RFC-012 evidence at line {line_number}"
                    ) from exc
                records.append(
                    _StoredRecord(value["record_type"], value["key"], payload)
                )
        for record in records:
            _validate_stored_record(record)
        return tuple(records)


class _NoFinalizedHistory:
    def has_finalized(
        self, predecessor_identity: CanonicalPredecessorIdentity
    ) -> bool:
        return False


class Rfc012TransitionProcessor:
    """Process one already-persisted successor without runtime integration."""

    def __init__(
        self,
        *,
        reader: PredecessorReader,
        evidence_store: Rfc012EvidenceStore,
        finalized_history: FinalizedHistory | None = None,
        clock: Callable[[], datetime] | None = None,
        decode_round_fields: Callable[[bytes], Mapping[str, object]] | None = None,
    ) -> None:
        self._reader = reader
        self._store = evidence_store
        self._history = finalized_history or _NoFinalizedHistory()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._decode_round_fields = decode_round_fields or _decode_round_fields

    def process(
        self,
        *,
        previous_round_id: int | None,
        successor_snapshot: ObserverSnapshot,
        successor_snapshot_identity: str,
        transition_context: TransitionContext | None,
        successor_validated: bool,
        successor_durably_persisted: bool,
        transition_unambiguous: bool = True,
    ) -> TransitionProcessResult:
        status = _candidate_status(
            previous_round_id=previous_round_id,
            successor_snapshot=successor_snapshot,
            successor_snapshot_identity=successor_snapshot_identity,
            transition_context=transition_context,
            successor_validated=successor_validated,
            successor_durably_persisted=successor_durably_persisted,
            transition_unambiguous=transition_unambiguous,
        )
        if status is not TransitionCandidateStatus.PROCESSED:
            return TransitionProcessResult(
                status=status,
                successor_snapshot=successor_snapshot,
                successor_snapshot_identity=successor_snapshot_identity,
                observation_count=0,
            )

        assert previous_round_id is not None
        assert transition_context is not None
        predecessor = CanonicalPredecessorIdentity.for_round(previous_round_id)
        transition = TransitionEvidence.create(
            observer_session_identity=successor_snapshot.collector_session_id,
            predecessor_identity=predecessor,
            successor_round_id=successor_snapshot.round.round_id,
            successor_snapshot_identity=successor_snapshot_identity,
            transition_context=transition_context,
        )
        self._store.append_transition(transition)

        existing = self._store.find_post_transition(transition.transition_identity)
        if existing is not None:
            return _processed_result(
                successor_snapshot,
                successor_snapshot_identity,
                transition,
                existing,
                0,
            )

        try:
            already_finalized = self._store.has_finalized(
                predecessor
            ) or self._history.has_finalized(predecessor)
        except Exception:
            post = self._post(
                transition,
                terminal_disposition=TerminalDisposition.INVALID_OR_AMBIGUOUS,
                validation_outcome=ValidationOutcome.AMBIGUOUS,
                failure_category=FailureCategory.DUPLICATE_IDENTITY_AMBIGUOUS,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot,
                successor_snapshot_identity,
                transition,
                post,
                0,
            )

        if already_finalized:
            post = self._post(
                transition,
                terminal_disposition=TerminalDisposition.ALREADY_DURABLE,
                validation_outcome=ValidationOutcome.NOT_EVALUATED,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 0
            )

        try:
            response = self._reader.observe_predecessor(
                predecessor.canonical_round_pda,
                commitment=transition_context.board_response_commitment,
                min_context_slot=transition_context.board_response_context_slot,
            )
        except Exception:
            post = self._post(
                transition,
                terminal_disposition=TerminalDisposition.OPERATIONAL_FAILURE,
                validation_outcome=ValidationOutcome.OPERATIONAL_FAILURE,
                failure_category=FailureCategory.OBSERVATION_FAILURE,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        context_failure = _context_failure(response, transition_context)
        raw_payload = _raw_payload(response)
        if context_failure:
            evidence_response = (
                response
                if response.response_context_slot is not None
                and response.response_commitment is not None
                else None
            )
            post = self._post(
                transition,
                response=evidence_response,
                protocol_payload=(raw_payload if evidence_response else None),
                terminal_disposition=TerminalDisposition.CONTEXT_UNPROVEN,
                validation_outcome=ValidationOutcome.INVALID,
                failure_category=FailureCategory.CONTEXT_UNPROVEN,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        if response.account_address != predecessor.canonical_round_pda:
            post = self._invalid_post(
                transition,
                response,
                FailureCategory.TRANSITION_IDENTITY_INVALID,
                raw_payload,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        if response.raw_account_data is None:
            post = self._post(
                transition,
                response=response,
                terminal_disposition=TerminalDisposition.ACCOUNT_UNAVAILABLE,
                validation_outcome=ValidationOutcome.UNAVAILABLE,
                failure_category=FailureCategory.ACCOUNT_UNAVAILABLE,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        failure = _identity_failure(response, predecessor)
        if failure is not None:
            post = self._invalid_post(transition, response, failure, raw_payload)
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        try:
            decoded_fields = self._decode_round_fields(response.raw_account_data)
            payload = PreservedProtocolPayload.create(
                raw_account_data=response.raw_account_data,
                decoded_round=decoded_fields,
                decoder_identity=response.decoder_identity,
                protocol_revision=response.protocol_revision,
            )
            round_state = RoundState.model_validate(decoded_fields)
        except Exception as exc:
            category = (
                FailureCategory.PAYLOAD_MISMATCH
                if "pinned decoder" in str(exc) or "disagree" in str(exc)
                else FailureCategory.PAYLOAD_MALFORMED
            )
            post = self._invalid_post(transition, response, category, raw_payload)
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        if round_state.round_id != predecessor.predecessor_round_id:
            post = self._invalid_post(
                transition,
                response,
                FailureCategory.ROUND_IDENTITY_MISMATCH,
                payload,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        if not is_finalized_round(round_state):
            post = self._post(
                transition,
                response=response,
                protocol_payload=payload,
                terminal_disposition=TerminalDisposition.NOT_FINALIZED,
                validation_outcome=ValidationOutcome.VALID,
                finalized_state=False,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        try:
            self._store.append_finalized_payload(predecessor, payload)
        except Exception:
            post = self._post(
                transition,
                response=response,
                protocol_payload=payload,
                terminal_disposition=TerminalDisposition.OPERATIONAL_FAILURE,
                validation_outcome=ValidationOutcome.OPERATIONAL_FAILURE,
                failure_category=FailureCategory.PERSISTENCE_FAILURE,
                finalized_state=True,
            )
            self._store.append_post_transition(post)
            return _processed_result(
                successor_snapshot, successor_snapshot_identity, transition, post, 1
            )

        post = self._post(
            transition,
            response=response,
            protocol_payload=payload,
            terminal_disposition=TerminalDisposition.FINALIZED_PERSISTED,
            validation_outcome=ValidationOutcome.VALID,
            finalized_state=True,
            outcome_source=OutcomeSource.OBSERVED,
            capture_mode=CaptureMode.POST_TRANSITION_PREDECESSOR,
        )
        self._store.append_post_transition(post)
        return _processed_result(
            successor_snapshot, successor_snapshot_identity, transition, post, 1
        )

    def _invalid_post(
        self,
        transition: TransitionEvidence,
        response: PredecessorObservation,
        failure_category: FailureCategory,
        protocol_payload: PreservedProtocolPayload | None,
    ) -> PostTransitionEvidence:
        return self._post(
            transition,
            response=response,
            protocol_payload=protocol_payload,
            terminal_disposition=TerminalDisposition.INVALID_OR_AMBIGUOUS,
            validation_outcome=ValidationOutcome.INVALID,
            failure_category=failure_category,
        )

    def _post(
        self,
        transition: TransitionEvidence,
        *,
        response: PredecessorObservation | None = None,
        protocol_payload: PreservedProtocolPayload | None = None,
        terminal_disposition: TerminalDisposition,
        validation_outcome: ValidationOutcome,
        failure_category: FailureCategory | None = None,
        finalized_state: bool | None = None,
        outcome_source: OutcomeSource | None = None,
        capture_mode: CaptureMode | None = None,
    ) -> PostTransitionEvidence:
        raw_hash = (
            hashlib.sha256(response.raw_account_data).hexdigest()
            if response is not None and response.raw_account_data is not None
            else None
        )
        return PostTransitionEvidence.create(
            transition_evidence=transition,
            attempt_timestamp=self._clock(),
            predecessor_response_context_slot=(
                response.response_context_slot if response is not None else None
            ),
            predecessor_response_commitment=(
                response.response_commitment if response is not None else None
            ),
            response_raw_account_sha256=raw_hash,
            protocol_payload=protocol_payload,
            validation_outcome=validation_outcome,
            failure_category=failure_category,
            terminal_disposition=terminal_disposition,
            finalized_state=finalized_state,
            outcome_source=outcome_source,
            capture_mode=capture_mode,
        )


def _candidate_status(
    *,
    previous_round_id: int | None,
    successor_snapshot: ObserverSnapshot,
    successor_snapshot_identity: str,
    transition_context: TransitionContext | None,
    successor_validated: bool,
    successor_durably_persisted: bool,
    transition_unambiguous: bool,
) -> TransitionCandidateStatus:
    current = successor_snapshot.round.round_id
    if previous_round_id is None:
        return TransitionCandidateStatus.INITIAL
    if current == previous_round_id:
        return TransitionCandidateStatus.UNCHANGED
    if current < previous_round_id:
        return TransitionCandidateStatus.REGRESSED
    if current > previous_round_id + 1:
        return TransitionCandidateStatus.SKIPPED
    if not transition_unambiguous:
        return TransitionCandidateStatus.AMBIGUOUS
    if (
        not successor_validated
        or not successor_durably_persisted
        or successor_snapshot.board.round_id != current
        or transition_context is None
        or transition_context.predecessor_round_id != previous_round_id
        or transition_context.successor_round_id != current
        or transition_context.successor_snapshot_identity
        != successor_snapshot_identity
    ):
        return TransitionCandidateStatus.INVALID_SUCCESSOR
    return TransitionCandidateStatus.PROCESSED


def _context_failure(
    response: PredecessorObservation, context: TransitionContext
) -> bool:
    if (
        response.response_context_slot is None
        or response.response_commitment not in _COMMITMENT_ORDER
        or response.response_context_slot < context.board_response_context_slot
        or response.network_identity != context.network_identity
        or response.expected_genesis_hash != context.expected_genesis_hash
        or response.provider_identity != context.provider_identity
    ):
        return True
    return (
        _COMMITMENT_ORDER[response.response_commitment]
        < _COMMITMENT_ORDER[context.board_response_commitment]
    )


def _identity_failure(
    response: PredecessorObservation,
    predecessor: CanonicalPredecessorIdentity,
) -> FailureCategory | None:
    if response.account_owner != predecessor.expected_account_owner:
        return FailureCategory.OWNER_MISMATCH
    if (
        response.ore_program_identity != predecessor.ore_program_identity
        or response.protocol_revision != predecessor.protocol_revision
    ):
        return FailureCategory.PROTOCOL_UNSUPPORTED
    if response.decoder_identity != ROUND_DECODER_IDENTITY:
        return FailureCategory.DECODER_UNSUPPORTED
    return None


def _raw_payload(
    response: PredecessorObservation,
) -> PreservedProtocolPayload | None:
    if response.raw_account_data is None:
        return None
    try:
        return PreservedProtocolPayload.create(
            raw_account_data=response.raw_account_data,
            decoded_round=None,
            decoder_identity=ROUND_DECODER_IDENTITY,
            protocol_revision=ORE_PROTOCOL_REVISION,
        )
    except Exception:
        return None


def _decode_round_fields(raw_account_data: bytes) -> Mapping[str, object]:
    account_info = {
        "data": [base64.b64encode(raw_account_data).decode("ascii"), "base64"]
    }
    return decode_round(account_info).model_dump(mode="json")


def _payload_mapping(payload: PreservedProtocolPayload) -> dict[str, object]:
    return {
        "raw_account_data": payload.raw_account_data,
        "raw_account_sha256": payload.raw_account_sha256,
        "decoder_identity": payload.decoder_identity,
        "protocol_revision": payload.protocol_revision,
        "decoded_round_canonical": payload.decoded_round_canonical,
        "decoded_round_sha256": payload.decoded_round_sha256,
        "decoded_from_raw_sha256": payload.decoded_from_raw_sha256,
        "protocol_payload_sha256": payload.protocol_payload_sha256,
    }


def _payload_from_mapping(value: object) -> PreservedProtocolPayload:
    if not isinstance(value, dict):
        raise EvidenceStoreError("stored protocol payload must be an object")
    try:
        return PreservedProtocolPayload(**value)
    except (TypeError, ValueError) as exc:
        raise EvidenceStoreError("stored protocol payload is invalid") from exc


def _finalized_payload_from_record(
    record: _StoredRecord,
) -> tuple[CanonicalPredecessorIdentity, PreservedProtocolPayload]:
    value = canonical_decode(record.canonical_payload)
    if not isinstance(value, dict) or set(value) != {
        "predecessor_identity",
        "protocol_payload",
        "outcome_source",
        "capture_mode",
    }:
        raise EvidenceStoreError("stored finalized payload fields are invalid")
    predecessor_value = value["predecessor_identity"]
    if not isinstance(predecessor_value, dict):
        raise EvidenceStoreError("stored predecessor identity is invalid")
    try:
        predecessor = CanonicalPredecessorIdentity(**predecessor_value)
    except (TypeError, ValueError) as exc:
        raise EvidenceStoreError("stored predecessor identity is invalid") from exc
    payload = _payload_from_mapping(value["protocol_payload"])
    if (
        value["outcome_source"] != OutcomeSource.OBSERVED.value
        or value["capture_mode"]
        != CaptureMode.POST_TRANSITION_PREDECESSOR.value
        or record.key != _predecessor_key(predecessor)
    ):
        raise EvidenceStoreError("stored finalized payload binding is invalid")
    return predecessor, payload


def _validate_stored_record(record: _StoredRecord) -> None:
    try:
        if record.record_type == "transition":
            evidence = TransitionEvidence.from_canonical_bytes(
                record.canonical_payload
            )
            if record.key != evidence.transition_identity.sha256:
                raise EvidenceStoreError("stored transition key is invalid")
        elif record.record_type == "post_transition":
            evidence = PostTransitionEvidence.from_canonical_bytes(
                record.canonical_payload
            )
            if (
                record.key
                != evidence.transition_evidence.transition_identity.sha256
            ):
                raise EvidenceStoreError("stored terminal key is invalid")
        else:
            _finalized_payload_from_record(record)
    except EvidenceStoreError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceStoreError(
            f"stored {record.record_type} evidence is invalid"
        ) from exc


def _predecessor_key(predecessor: CanonicalPredecessorIdentity) -> str:
    return hashlib.sha256(
        canonical_encode(predecessor.to_identity_material())
    ).hexdigest()


def _processed_result(
    successor_snapshot: ObserverSnapshot,
    successor_snapshot_identity: str,
    transition: TransitionEvidence,
    post: PostTransitionEvidence,
    observation_count: int,
) -> TransitionProcessResult:
    return TransitionProcessResult(
        status=TransitionCandidateStatus.PROCESSED,
        successor_snapshot=successor_snapshot,
        successor_snapshot_identity=successor_snapshot_identity,
        observation_count=observation_count,
        transition_evidence=transition,
        post_transition_evidence=post,
    )
