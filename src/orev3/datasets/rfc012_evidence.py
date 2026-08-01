"""Immutable evidence contracts for RFC-012 Phase 1.

This module defines data and identity contracts only.  It performs no RPC,
observer-loop, persistence, dataset, replay, or runtime integration work.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from solders.pubkey import Pubkey

from orev3.observer.accounts import decode_round


EVIDENCE_SCHEMA_IDENTIFIER = "orev3.rfc012.evidence"
EVIDENCE_SCHEMA_VERSION = 1
EVIDENCE_PRODUCER_IDENTIFIER = "orev3.observer.rfc012"
CANONICAL_ENCODING_VERSION = 1

SOLANA_MAINNET_NETWORK = "solana-mainnet-beta"
SOLANA_MAINNET_GENESIS_HASH = (
    "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d"
)
ORE_PROGRAM_IDENTITY = "oreV3EG1i9BEgiAJ8b177Z2S2rMarzak4NMv1kULvWv"
ORE_PROTOCOL_REVISION = "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
ROUND_DECODER_IDENTITY = "orev3.observer.accounts.decode_round:v1"

TRANSITION_IDENTITY_DOMAIN = "orev3:rfc012:transition:v1"
RESPONSE_IDENTITY_DOMAIN = "orev3:rfc012:response:v1"
PAYLOAD_IDENTITY_DOMAIN = "orev3:rfc012:payload:v1"
EVIDENCE_IDENTITY_DOMAIN = "orev3:rfc012:evidence:v1"

NO_RESPONSE_MARKER = "orev3:rfc012:no-response:v1"
NO_PAYLOAD_MARKER = "orev3:rfc012:no-payload:v1"
NO_DECODED_PAYLOAD_MARKER = "orev3:rfc012:no-decoded-payload:v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SAFE_IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_COMMITMENT_ORDER = {"processed": 0, "confirmed": 1, "finalized": 2}


class TerminalDisposition(str, Enum):
    """The exhaustive terminal outcomes for one transition candidate."""

    ALREADY_DURABLE = "already_durable"
    FINALIZED_PERSISTED = "finalized_persisted"
    NOT_FINALIZED = "not_finalized"
    ACCOUNT_UNAVAILABLE = "account_unavailable"
    CONTEXT_UNPROVEN = "context_unproven"
    INVALID_OR_AMBIGUOUS = "invalid_or_ambiguous"
    OPERATIONAL_FAILURE = "operational_failure"


class ValidationOutcome(str, Enum):
    """Result of validating a supplementary predecessor observation."""

    VALID = "valid"
    INVALID = "invalid"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"
    NOT_EVALUATED = "not_evaluated"
    OPERATIONAL_FAILURE = "operational_failure"


class FailureCategory(str, Enum):
    """Fail-closed categories preserved without runtime interpretation."""

    TRANSITION_IDENTITY_INVALID = "transition_identity_invalid"
    PREDECESSOR_IDENTITY_AMBIGUOUS = "predecessor_identity_ambiguous"
    PDA_DERIVATION_FAILED = "pda_derivation_failed"
    ACCOUNT_UNAVAILABLE = "account_unavailable"
    CONTEXT_UNPROVEN = "context_unproven"
    OWNER_MISMATCH = "owner_mismatch"
    SCHEMA_UNSUPPORTED = "schema_unsupported"
    ROUND_IDENTITY_MISMATCH = "round_identity_mismatch"
    PROTOCOL_UNSUPPORTED = "protocol_unsupported"
    DECODER_UNSUPPORTED = "decoder_unsupported"
    PAYLOAD_MALFORMED = "payload_malformed"
    PAYLOAD_MISMATCH = "payload_mismatch"
    DUPLICATE_IDENTITY_AMBIGUOUS = "duplicate_identity_ambiguous"
    OBSERVATION_FAILURE = "observation_failure"
    PERSISTENCE_FAILURE = "persistence_failure"


class OutcomeSource(str, Enum):
    """Existing broad finalized-outcome provenance vocabulary."""

    OBSERVED = "observed"
    ENRICHED = "enriched"


class CaptureMode(str, Enum):
    """Immutable local capture mode for an observed outcome."""

    CURRENT_ROUND = "current_round"
    POST_TRANSITION_PREDECESSOR = "post_transition_predecessor"


def canonical_encode(value: Any) -> bytes:
    """Return the RFC-012 versioned, byte-stable canonical encoding."""

    envelope = {
        "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
        "value": _canonical_value(value),
    }
    return json.dumps(
        envelope,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_decode(raw: bytes) -> Any:
    """Decode and verify an RFC-012 canonical encoding."""

    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("RFC-012 canonical encoding is malformed") from exc
    if not isinstance(envelope, dict):
        raise ValueError("RFC-012 canonical envelope must be an object")
    if envelope.get("canonical_encoding_version") != CANONICAL_ENCODING_VERSION:
        raise ValueError("RFC-012 canonical encoding version is unsupported")
    if set(envelope) != {"canonical_encoding_version", "value"}:
        raise ValueError("RFC-012 canonical envelope fields are invalid")
    value = _decode_canonical_value(envelope["value"])
    if canonical_encode(value) != raw:
        raise ValueError("RFC-012 canonical encoding is not canonical")
    return value


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if isinstance(value, _DigestIdentity):
        return _canonical_value(value.sha256)
    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("RFC-012 timestamps must be timezone-aware")
        normalized = value.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        return {"type": "datetime_utc", "value": normalized}
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        raise TypeError("RFC-012 canonical values do not permit floats")
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("RFC-012 canonical mapping keys must be strings")
        return {
            "type": "mapping",
            "value": [
                [key, _canonical_value(item)]
                for key, item in sorted(value.items())
            ],
        }
    if isinstance(value, (list, tuple)):
        return {
            "type": "sequence",
            "value": [_canonical_value(item) for item in value],
        }
    if hasattr(value, "to_identity_material"):
        return _canonical_value(value.to_identity_material())
    raise TypeError(
        f"Unsupported RFC-012 canonical value: {type(value).__name__}"
    )


def _decode_canonical_value(value: Any) -> Any:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise ValueError("RFC-012 canonical value is invalid")
    value_type = value["type"]
    if value_type == "null":
        if set(value) != {"type"}:
            raise ValueError("RFC-012 null value is invalid")
        return None
    if set(value) != {"type", "value"}:
        raise ValueError("RFC-012 canonical value fields are invalid")
    encoded_value = value["value"]
    if value_type == "bytes":
        if not isinstance(encoded_value, str):
            raise ValueError("RFC-012 byte value must contain a string")
        try:
            return base64.b64decode(encoded_value, validate=True)
        except ValueError as exc:
            raise ValueError("RFC-012 byte value is invalid") from exc
    if value_type == "datetime_utc":
        if not isinstance(encoded_value, str) or not encoded_value.endswith("Z"):
            raise ValueError("RFC-012 datetime value is invalid")
        try:
            return datetime.fromisoformat(encoded_value[:-1] + "+00:00")
        except ValueError as exc:
            raise ValueError("RFC-012 datetime value is invalid") from exc
    if value_type == "boolean":
        if not isinstance(encoded_value, bool):
            raise ValueError("RFC-012 boolean value is invalid")
        return encoded_value
    if value_type == "string":
        if not isinstance(encoded_value, str):
            raise ValueError("RFC-012 string value is invalid")
        return encoded_value
    if value_type == "integer":
        if not isinstance(encoded_value, str) or not re.fullmatch(
            r"0|-?[1-9][0-9]*", encoded_value
        ):
            raise ValueError("RFC-012 integer value is invalid")
        return int(encoded_value)
    if value_type == "sequence":
        if not isinstance(encoded_value, list):
            raise ValueError("RFC-012 sequence value is invalid")
        return tuple(_decode_canonical_value(item) for item in encoded_value)
    if value_type == "mapping":
        if not isinstance(encoded_value, list):
            raise ValueError("RFC-012 mapping value is invalid")
        result: dict[str, Any] = {}
        prior_key: str | None = None
        for pair in encoded_value:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not isinstance(pair[0], str)
            ):
                raise ValueError("RFC-012 mapping entry is invalid")
            key = pair[0]
            if key in result or (prior_key is not None and key <= prior_key):
                raise ValueError("RFC-012 mapping keys are not canonical")
            result[key] = _decode_canonical_value(pair[1])
            prior_key = key
        return result
    raise ValueError("RFC-012 canonical value type is unsupported")


def _identity(domain: str, material: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _require_safe_identity(name: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_IDENTITY_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a redacted canonical identity")


def _require_nonnegative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _require_commitment(name: str, value: str) -> None:
    if value not in _COMMITMENT_ORDER:
        raise ValueError(f"{name} is not a supported commitment")


@dataclass(frozen=True, slots=True)
class _DigestIdentity:
    sha256: str

    def __post_init__(self) -> None:
        _require_sha256(type(self).__name__, self.sha256)

    def __str__(self) -> str:
        return self.sha256


@dataclass(frozen=True, slots=True)
class TransitionIdentity(_DigestIdentity):
    """Domain-separated identity of one accepted contiguous transition."""


@dataclass(frozen=True, slots=True)
class ResponseIdentity(_DigestIdentity):
    """Domain-separated identity of one predecessor response."""


@dataclass(frozen=True, slots=True)
class EvidenceIdentity(_DigestIdentity):
    """Domain-separated identity of one post-transition evidence record."""


@dataclass(frozen=True, slots=True)
class TransitionContext:
    """Immutable context from the Board response selecting the successor."""

    network_identity: str
    expected_genesis_hash: str
    provider_identity: str
    board_account_identity: str
    predecessor_round_id: int
    successor_round_id: int
    successor_snapshot_identity: str
    board_response_commitment: str
    board_response_context_slot: int

    def __post_init__(self) -> None:
        if self.network_identity != SOLANA_MAINNET_NETWORK:
            raise ValueError("network_identity is unsupported")
        if self.expected_genesis_hash != SOLANA_MAINNET_GENESIS_HASH:
            raise ValueError("expected_genesis_hash is unsupported")
        _require_safe_identity("provider_identity", self.provider_identity)
        _require_safe_identity(
            "board_account_identity", self.board_account_identity
        )
        _require_nonnegative_integer(
            "predecessor_round_id", self.predecessor_round_id
        )
        if self.successor_round_id != self.predecessor_round_id + 1:
            raise ValueError("transition context must describe R to R + 1")
        _require_sha256(
            "successor_snapshot_identity", self.successor_snapshot_identity
        )
        _require_commitment(
            "board_response_commitment", self.board_response_commitment
        )
        _require_nonnegative_integer(
            "board_response_context_slot", self.board_response_context_slot
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "network_identity": self.network_identity,
            "expected_genesis_hash": self.expected_genesis_hash,
            "provider_identity": self.provider_identity,
            "board_account_identity": self.board_account_identity,
            "predecessor_round_id": self.predecessor_round_id,
            "successor_round_id": self.successor_round_id,
            "successor_snapshot_identity": self.successor_snapshot_identity,
            "board_response_commitment": self.board_response_commitment,
            "board_response_context_slot": self.board_response_context_slot,
        }


@dataclass(frozen=True, slots=True)
class CanonicalPredecessorIdentity:
    """Complete network-, program-, owner-, and PDA-bound Round identity."""

    network_identity: str
    expected_genesis_hash: str
    ore_program_identity: str
    protocol_revision: str
    predecessor_round_id: int
    canonical_round_pda: str
    expected_account_owner: str

    def __post_init__(self) -> None:
        if self.network_identity != SOLANA_MAINNET_NETWORK:
            raise ValueError("network_identity is unsupported")
        if self.expected_genesis_hash != SOLANA_MAINNET_GENESIS_HASH:
            raise ValueError("expected_genesis_hash is unsupported")
        if self.ore_program_identity != ORE_PROGRAM_IDENTITY:
            raise ValueError("ore_program_identity is unsupported")
        if self.protocol_revision != ORE_PROTOCOL_REVISION:
            raise ValueError("protocol_revision is unsupported")
        _require_nonnegative_integer(
            "predecessor_round_id", self.predecessor_round_id
        )
        if self.expected_account_owner != self.ore_program_identity:
            raise ValueError("expected_account_owner must be the ORE program")
        expected_pda = str(_derive_round_pda(self.predecessor_round_id))
        if self.canonical_round_pda != expected_pda:
            raise ValueError("canonical_round_pda is not canonical")

    @classmethod
    def for_round(cls, predecessor_round_id: int) -> "CanonicalPredecessorIdentity":
        """Construct the pinned canonical identity for a predecessor Round."""

        return cls(
            network_identity=SOLANA_MAINNET_NETWORK,
            expected_genesis_hash=SOLANA_MAINNET_GENESIS_HASH,
            ore_program_identity=ORE_PROGRAM_IDENTITY,
            protocol_revision=ORE_PROTOCOL_REVISION,
            predecessor_round_id=predecessor_round_id,
            canonical_round_pda=str(_derive_round_pda(predecessor_round_id)),
            expected_account_owner=ORE_PROGRAM_IDENTITY,
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "network_identity": self.network_identity,
            "expected_genesis_hash": self.expected_genesis_hash,
            "ore_program_identity": self.ore_program_identity,
            "protocol_revision": self.protocol_revision,
            "predecessor_round_id": self.predecessor_round_id,
            "canonical_round_pda": self.canonical_round_pda,
            "expected_account_owner": self.expected_account_owner,
        }


@dataclass(frozen=True, slots=True)
class PreservedProtocolPayload:
    """Lossless raw and canonical decoded predecessor Round payload."""

    raw_account_data: bytes
    raw_account_sha256: str
    decoder_identity: str
    protocol_revision: str
    decoded_round_canonical: bytes | None
    decoded_round_sha256: str | None
    decoded_from_raw_sha256: str | None
    protocol_payload_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.raw_account_data, bytes):
            raise TypeError("raw_account_data must be immutable bytes")
        _require_sha256("raw_account_sha256", self.raw_account_sha256)
        if hashlib.sha256(self.raw_account_data).hexdigest() != self.raw_account_sha256:
            raise ValueError("raw account payload hash does not match payload")
        if self.decoder_identity != ROUND_DECODER_IDENTITY:
            raise ValueError("decoder_identity is unsupported")
        if self.protocol_revision != ORE_PROTOCOL_REVISION:
            raise ValueError("protocol_revision is unsupported")
        decoded_values = (
            self.decoded_round_canonical,
            self.decoded_round_sha256,
            self.decoded_from_raw_sha256,
        )
        if decoded_values == (None, None, None):
            pass
        elif any(value is None for value in decoded_values):
            raise ValueError("decoded Round representation is incomplete")
        else:
            if not isinstance(self.decoded_round_canonical, bytes):
                raise TypeError("decoded_round_canonical must be immutable bytes")
            decoded = canonical_decode(self.decoded_round_canonical)
            if not isinstance(decoded, dict):
                raise ValueError("decoded Round fields must be a canonical object")
            pinned_decoded = _decode_pinned_round(self.raw_account_data)
            if canonical_encode(decoded) != canonical_encode(pinned_decoded):
                raise ValueError(
                    "raw and decoded payload disagree under the pinned decoder"
                )
            assert self.decoded_round_sha256 is not None
            _require_sha256("decoded_round_sha256", self.decoded_round_sha256)
            if (
                hashlib.sha256(self.decoded_round_canonical).hexdigest()
                != self.decoded_round_sha256
            ):
                raise ValueError(
                    "decoded Round hash does not match representation"
                )
            assert self.decoded_from_raw_sha256 is not None
            _require_sha256(
                "decoded_from_raw_sha256", self.decoded_from_raw_sha256
            )
            if self.decoded_from_raw_sha256 != self.raw_account_sha256:
                raise ValueError("raw and decoded payload provenance disagree")
        _require_sha256(
            "protocol_payload_sha256", self.protocol_payload_sha256
        )
        if self.protocol_payload_sha256 != self.reconstruct_identity():
            raise ValueError("protocol payload identity does not reconstruct")

    @classmethod
    def create(
        cls,
        *,
        raw_account_data: bytes,
        decoded_round: Mapping[str, Any] | None,
        decoder_identity: str = ROUND_DECODER_IDENTITY,
        protocol_revision: str = ORE_PROTOCOL_REVISION,
        decoded_from_raw_sha256: str | None = None,
    ) -> "PreservedProtocolPayload":
        raw_hash = hashlib.sha256(raw_account_data).hexdigest()
        if decoded_round is None:
            if decoded_from_raw_sha256 is not None:
                raise ValueError(
                    "decoded provenance cannot exist without decoded fields"
                )
            decoded_canonical = None
            decoded_hash = None
            source_hash = None
        else:
            decoded_canonical = canonical_encode(decoded_round)
            decoded_hash = hashlib.sha256(decoded_canonical).hexdigest()
            source_hash = decoded_from_raw_sha256 or raw_hash
        material = {
            "raw_account_sha256": raw_hash,
            "decoder_identity": decoder_identity,
            "protocol_revision": protocol_revision,
            "decoded_round_sha256": (
                decoded_hash
                if decoded_hash is not None
                else NO_DECODED_PAYLOAD_MARKER
            ),
            "decoded_from_raw_sha256": source_hash,
        }
        return cls(
            raw_account_data=raw_account_data,
            raw_account_sha256=raw_hash,
            decoder_identity=decoder_identity,
            protocol_revision=protocol_revision,
            decoded_round_canonical=decoded_canonical,
            decoded_round_sha256=decoded_hash,
            decoded_from_raw_sha256=source_hash,
            protocol_payload_sha256=_identity(PAYLOAD_IDENTITY_DOMAIN, material),
        )

    @property
    def decoded_round(self) -> Mapping[str, Any] | None:
        """Return a fresh decoded representation; stored evidence stays frozen."""

        if self.decoded_round_canonical is None:
            return None
        decoded = canonical_decode(self.decoded_round_canonical)
        assert isinstance(decoded, dict)
        return decoded

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "raw_account_sha256": self.raw_account_sha256,
            "decoder_identity": self.decoder_identity,
            "protocol_revision": self.protocol_revision,
            "decoded_round_sha256": (
                self.decoded_round_sha256
                if self.decoded_round_sha256 is not None
                else NO_DECODED_PAYLOAD_MARKER
            ),
            "decoded_from_raw_sha256": self.decoded_from_raw_sha256,
        }

    def reconstruct_identity(self) -> str:
        return _identity(PAYLOAD_IDENTITY_DOMAIN, self.to_identity_material())


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    """Immutable evidence that one verified contiguous transition occurred."""

    schema_identifier: str
    schema_version: int
    producer_identity: str
    observer_session_identity: str
    predecessor_identity: CanonicalPredecessorIdentity
    successor_round_id: int
    successor_snapshot_identity: str
    transition_context: TransitionContext
    transition_identity: TransitionIdentity

    def __post_init__(self) -> None:
        _validate_contract_header(
            self.schema_identifier, self.schema_version, self.producer_identity
        )
        _require_safe_identity(
            "observer_session_identity", self.observer_session_identity
        )
        if not isinstance(
            self.predecessor_identity, CanonicalPredecessorIdentity
        ):
            raise TypeError(
                "predecessor_identity must be CanonicalPredecessorIdentity"
            )
        if not isinstance(self.transition_context, TransitionContext):
            raise TypeError("transition_context must be TransitionContext")
        if not isinstance(self.transition_identity, TransitionIdentity):
            raise TypeError("transition_identity must be TransitionIdentity")
        expected_successor = (
            self.predecessor_identity.predecessor_round_id + 1
        )
        if self.successor_round_id != expected_successor:
            raise ValueError("successor Round must be contiguous")
        _require_nonnegative_integer("successor_round_id", self.successor_round_id)
        _require_sha256(
            "successor_snapshot_identity", self.successor_snapshot_identity
        )
        if (
            self.transition_context.network_identity
            != self.predecessor_identity.network_identity
            or self.transition_context.expected_genesis_hash
            != self.predecessor_identity.expected_genesis_hash
        ):
            raise ValueError("transition and predecessor network bindings disagree")
        if (
            self.transition_context.predecessor_round_id
            != self.predecessor_identity.predecessor_round_id
            or self.transition_context.successor_round_id
            != self.successor_round_id
            or self.transition_context.successor_snapshot_identity
            != self.successor_snapshot_identity
        ):
            raise ValueError("transition context identity bindings disagree")
        if self.transition_identity != self.reconstruct_identity():
            raise ValueError("transition identity does not reconstruct")

    @classmethod
    def create(
        cls,
        *,
        observer_session_identity: str,
        predecessor_identity: CanonicalPredecessorIdentity,
        successor_round_id: int,
        successor_snapshot_identity: str,
        transition_context: TransitionContext,
    ) -> "TransitionEvidence":
        material = _transition_identity_material(
            schema_version=EVIDENCE_SCHEMA_VERSION,
            observer_session_identity=observer_session_identity,
            predecessor_identity=predecessor_identity,
            successor_round_id=successor_round_id,
            successor_snapshot_identity=successor_snapshot_identity,
            transition_context=transition_context,
        )
        return cls(
            schema_identifier=EVIDENCE_SCHEMA_IDENTIFIER,
            schema_version=EVIDENCE_SCHEMA_VERSION,
            producer_identity=EVIDENCE_PRODUCER_IDENTIFIER,
            observer_session_identity=observer_session_identity,
            predecessor_identity=predecessor_identity,
            successor_round_id=successor_round_id,
            successor_snapshot_identity=successor_snapshot_identity,
            transition_context=transition_context,
            transition_identity=TransitionIdentity(
                _identity(TRANSITION_IDENTITY_DOMAIN, material)
            ),
        )

    def reconstruct_identity(self) -> TransitionIdentity:
        material = _transition_identity_material(
            schema_version=self.schema_version,
            observer_session_identity=self.observer_session_identity,
            predecessor_identity=self.predecessor_identity,
            successor_round_id=self.successor_round_id,
            successor_snapshot_identity=self.successor_snapshot_identity,
            transition_context=self.transition_context,
        )
        return TransitionIdentity(_identity(TRANSITION_IDENTITY_DOMAIN, material))

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "schema_identifier": self.schema_identifier,
            "schema_version": self.schema_version,
            "producer_identity": self.producer_identity,
            "observer_session_identity": self.observer_session_identity,
            "predecessor_identity": self.predecessor_identity,
            "successor_round_id": self.successor_round_id,
            "successor_snapshot_identity": self.successor_snapshot_identity,
            "transition_context": self.transition_context,
            "transition_identity": self.transition_identity,
        }

    def to_canonical_bytes(self) -> bytes:
        return canonical_encode(self.to_identity_material())

    @classmethod
    def from_canonical_bytes(cls, raw: bytes) -> "TransitionEvidence":
        value = canonical_decode(raw)
        if not isinstance(value, dict):
            raise ValueError("transition evidence must be an object")
        return _transition_evidence_from_mapping(value)


@dataclass(frozen=True, slots=True)
class PostTransitionEvidence:
    """Immutable terminal evidence for one supplementary branch."""

    schema_identifier: str
    schema_version: int
    producer_identity: str
    transition_evidence: TransitionEvidence
    attempt_timestamp: datetime
    response_identity: ResponseIdentity | None
    predecessor_response_context_slot: int | None
    predecessor_response_commitment: str | None
    response_raw_account_sha256: str | None
    protocol_payload: PreservedProtocolPayload | None
    validation_outcome: ValidationOutcome
    failure_category: FailureCategory | None
    terminal_disposition: TerminalDisposition
    finalized_state: bool | None
    outcome_source: OutcomeSource | None
    capture_mode: CaptureMode | None
    evidence_identity: EvidenceIdentity

    def __post_init__(self) -> None:
        _validate_contract_header(
            self.schema_identifier, self.schema_version, self.producer_identity
        )
        if not isinstance(self.transition_evidence, TransitionEvidence):
            raise TypeError("transition_evidence must be TransitionEvidence")
        if not isinstance(self.attempt_timestamp, datetime):
            raise TypeError("attempt_timestamp must be a datetime")
        if self.response_identity is not None and not isinstance(
            self.response_identity, ResponseIdentity
        ):
            raise TypeError("response_identity must be ResponseIdentity or None")
        if self.protocol_payload is not None and not isinstance(
            self.protocol_payload, PreservedProtocolPayload
        ):
            raise TypeError(
                "protocol_payload must be PreservedProtocolPayload or None"
            )
        if not isinstance(self.validation_outcome, ValidationOutcome):
            raise TypeError("validation_outcome must be ValidationOutcome")
        if self.failure_category is not None and not isinstance(
            self.failure_category, FailureCategory
        ):
            raise TypeError("failure_category must be FailureCategory or None")
        if not isinstance(self.terminal_disposition, TerminalDisposition):
            raise TypeError(
                "terminal_disposition must be TerminalDisposition"
            )
        if self.finalized_state is not None and not isinstance(
            self.finalized_state, bool
        ):
            raise TypeError("finalized_state must be a boolean or None")
        if self.outcome_source is not None and not isinstance(
            self.outcome_source, OutcomeSource
        ):
            raise TypeError("outcome_source must be OutcomeSource or None")
        if self.capture_mode is not None and not isinstance(
            self.capture_mode, CaptureMode
        ):
            raise TypeError("capture_mode must be CaptureMode or None")
        if not isinstance(self.evidence_identity, EvidenceIdentity):
            raise TypeError("evidence_identity must be EvidenceIdentity")
        if self.transition_evidence.schema_version != self.schema_version:
            raise ValueError("nested transition schema version disagrees")
        if self.transition_evidence.producer_identity != self.producer_identity:
            raise ValueError("nested transition producer disagrees")
        _canonical_value(self.attempt_timestamp)
        _validate_response_fields(self)
        _validate_provenance(self)
        _validate_disposition(self)
        if self.evidence_identity != self.reconstruct_identity():
            raise ValueError("evidence identity does not reconstruct")

    @classmethod
    def create(
        cls,
        *,
        transition_evidence: TransitionEvidence,
        attempt_timestamp: datetime,
        predecessor_response_context_slot: int | None,
        predecessor_response_commitment: str | None,
        response_raw_account_sha256: str | None,
        protocol_payload: PreservedProtocolPayload | None,
        validation_outcome: ValidationOutcome,
        failure_category: FailureCategory | None,
        terminal_disposition: TerminalDisposition,
        finalized_state: bool | None,
        outcome_source: OutcomeSource | None,
        capture_mode: CaptureMode | None,
    ) -> "PostTransitionEvidence":
        response_identity = _construct_response_identity(
            transition_evidence=transition_evidence,
            predecessor_response_context_slot=predecessor_response_context_slot,
            predecessor_response_commitment=predecessor_response_commitment,
            response_raw_account_sha256=response_raw_account_sha256,
            protocol_payload=protocol_payload,
        )
        material = _evidence_identity_material(
            schema_version=EVIDENCE_SCHEMA_VERSION,
            producer_identity=EVIDENCE_PRODUCER_IDENTIFIER,
            transition_identity=transition_evidence.transition_identity,
            response_identity=response_identity,
            validation_outcome=validation_outcome,
            terminal_disposition=terminal_disposition,
            finalized_state=finalized_state,
            protocol_payload=protocol_payload,
            outcome_source=outcome_source,
            capture_mode=capture_mode,
        )
        return cls(
            schema_identifier=EVIDENCE_SCHEMA_IDENTIFIER,
            schema_version=EVIDENCE_SCHEMA_VERSION,
            producer_identity=EVIDENCE_PRODUCER_IDENTIFIER,
            transition_evidence=transition_evidence,
            attempt_timestamp=attempt_timestamp,
            response_identity=response_identity,
            predecessor_response_context_slot=predecessor_response_context_slot,
            predecessor_response_commitment=predecessor_response_commitment,
            response_raw_account_sha256=response_raw_account_sha256,
            protocol_payload=protocol_payload,
            validation_outcome=validation_outcome,
            failure_category=failure_category,
            terminal_disposition=terminal_disposition,
            finalized_state=finalized_state,
            outcome_source=outcome_source,
            capture_mode=capture_mode,
            evidence_identity=EvidenceIdentity(
                _identity(EVIDENCE_IDENTITY_DOMAIN, material)
            ),
        )

    def reconstruct_identity(self) -> EvidenceIdentity:
        material = _evidence_identity_material(
            schema_version=self.schema_version,
            producer_identity=self.producer_identity,
            transition_identity=self.transition_evidence.transition_identity,
            response_identity=self.response_identity,
            validation_outcome=self.validation_outcome,
            terminal_disposition=self.terminal_disposition,
            finalized_state=self.finalized_state,
            protocol_payload=self.protocol_payload,
            outcome_source=self.outcome_source,
            capture_mode=self.capture_mode,
        )
        return EvidenceIdentity(_identity(EVIDENCE_IDENTITY_DOMAIN, material))

    def to_canonical_bytes(self) -> bytes:
        return canonical_encode(_post_transition_to_mapping(self))

    @classmethod
    def from_canonical_bytes(cls, raw: bytes) -> "PostTransitionEvidence":
        value = canonical_decode(raw)
        if not isinstance(value, dict):
            raise ValueError("post-transition evidence must be an object")
        return _post_transition_from_mapping(value)


def _derive_round_pda(round_id: int) -> Pubkey:
    _require_nonnegative_integer("round_id", round_id)
    if round_id > (2**64 - 1):
        raise ValueError("round_id must be representable as an unsigned u64")
    address, _ = Pubkey.find_program_address(
        [b"round", round_id.to_bytes(8, "little", signed=False)],
        Pubkey.from_string(ORE_PROGRAM_IDENTITY),
    )
    return address


def _decode_pinned_round(raw_account_data: bytes) -> Mapping[str, Any]:
    encoded = base64.b64encode(raw_account_data).decode("ascii")
    try:
        decoded = decode_round({"data": [encoded, "base64"]})
    except Exception as exc:
        raise ValueError(
            "raw account payload is not decodable by the pinned decoder"
        ) from exc
    return decoded.model_dump(mode="python")


def _validate_contract_header(
    schema_identifier: str, schema_version: int, producer_identity: str
) -> None:
    if schema_identifier != EVIDENCE_SCHEMA_IDENTIFIER:
        raise ValueError("evidence schema identifier is unsupported")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != EVIDENCE_SCHEMA_VERSION
    ):
        raise ValueError("evidence schema version is unsupported")
    if producer_identity != EVIDENCE_PRODUCER_IDENTIFIER:
        raise ValueError("evidence producer identity is unsupported")


def _transition_identity_material(
    *,
    schema_version: int,
    observer_session_identity: str,
    predecessor_identity: CanonicalPredecessorIdentity,
    successor_round_id: int,
    successor_snapshot_identity: str,
    transition_context: TransitionContext,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "observer_session_identity": observer_session_identity,
        "canonical_predecessor_identity": predecessor_identity,
        "successor_round_id": successor_round_id,
        "successor_snapshot_identity": successor_snapshot_identity,
        "board_account_identity": transition_context.board_account_identity,
        "provider_identity": transition_context.provider_identity,
        "board_response_commitment": transition_context.board_response_commitment,
        "board_response_context_slot": transition_context.board_response_context_slot,
    }


def _construct_response_identity(
    *,
    transition_evidence: TransitionEvidence,
    predecessor_response_context_slot: int | None,
    predecessor_response_commitment: str | None,
    response_raw_account_sha256: str | None,
    protocol_payload: PreservedProtocolPayload | None,
) -> ResponseIdentity | None:
    values = (
        predecessor_response_context_slot,
        predecessor_response_commitment,
        response_raw_account_sha256,
    )
    if values == (None, None, None):
        if protocol_payload is not None:
            raise ValueError("payload cannot exist without a predecessor response")
        return None
    if any(value is None for value in values):
        raise ValueError("predecessor response identity inputs are incomplete")
    assert predecessor_response_context_slot is not None
    assert predecessor_response_commitment is not None
    assert response_raw_account_sha256 is not None
    _require_nonnegative_integer(
        "predecessor_response_context_slot", predecessor_response_context_slot
    )
    _require_commitment(
        "predecessor_response_commitment", predecessor_response_commitment
    )
    _require_sha256(
        "response_raw_account_sha256", response_raw_account_sha256
    )
    decoder_identity = (
        protocol_payload.decoder_identity
        if protocol_payload is not None
        else ROUND_DECODER_IDENTITY
    )
    protocol_revision = (
        protocol_payload.protocol_revision
        if protocol_payload is not None
        else ORE_PROTOCOL_REVISION
    )
    material = {
        "transition_identity": transition_evidence.transition_identity,
        "canonical_predecessor_identity": transition_evidence.predecessor_identity,
        "predecessor_response_context_slot": predecessor_response_context_slot,
        "predecessor_response_commitment": predecessor_response_commitment,
        "raw_account_payload_sha256": response_raw_account_sha256,
        "decoder_identity": decoder_identity,
        "protocol_revision": protocol_revision,
    }
    return ResponseIdentity(_identity(RESPONSE_IDENTITY_DOMAIN, material))


def _evidence_identity_material(
    *,
    schema_version: int,
    producer_identity: str,
    transition_identity: TransitionIdentity,
    response_identity: ResponseIdentity | None,
    validation_outcome: ValidationOutcome,
    terminal_disposition: TerminalDisposition,
    finalized_state: bool | None,
    protocol_payload: PreservedProtocolPayload | None,
    outcome_source: OutcomeSource | None,
    capture_mode: CaptureMode | None,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "producer_identity": producer_identity,
        "transition_identity": transition_identity,
        "response_identity": (
            response_identity if response_identity is not None else NO_RESPONSE_MARKER
        ),
        "validation_outcome": validation_outcome,
        "terminal_disposition": terminal_disposition,
        "finalized_state": finalized_state,
        "protocol_payload_identity": (
            protocol_payload.protocol_payload_sha256
            if protocol_payload is not None
            else NO_PAYLOAD_MARKER
        ),
        "outcome_source": outcome_source.value if outcome_source else None,
        "capture_mode": capture_mode.value if capture_mode else None,
    }


def _validate_response_fields(evidence: PostTransitionEvidence) -> None:
    reconstructed = _construct_response_identity(
        transition_evidence=evidence.transition_evidence,
        predecessor_response_context_slot=evidence.predecessor_response_context_slot,
        predecessor_response_commitment=evidence.predecessor_response_commitment,
        response_raw_account_sha256=evidence.response_raw_account_sha256,
        protocol_payload=evidence.protocol_payload,
    )
    if reconstructed != evidence.response_identity:
        raise ValueError("response identity does not reconstruct")
    if evidence.protocol_payload is not None:
        if (
            evidence.response_raw_account_sha256
            != evidence.protocol_payload.raw_account_sha256
        ):
            raise ValueError("response and preserved payload hashes disagree")


def _validate_provenance(evidence: PostTransitionEvidence) -> None:
    if (evidence.outcome_source is None) != (evidence.capture_mode is None):
        raise ValueError("outcome source and capture mode must be paired")
    if evidence.outcome_source is not None:
        if evidence.outcome_source is not OutcomeSource.OBSERVED:
            raise ValueError("post-transition evidence cannot be enriched")
        if evidence.capture_mode is not CaptureMode.POST_TRANSITION_PREDECESSOR:
            raise ValueError("post-transition evidence has invalid capture mode")


def _validate_disposition(evidence: PostTransitionEvidence) -> None:
    if evidence.terminal_disposition is TerminalDisposition.FINALIZED_PERSISTED:
        if (
            evidence.validation_outcome is not ValidationOutcome.VALID
            or evidence.finalized_state is not True
            or evidence.protocol_payload is None
            or evidence.protocol_payload.decoded_round_canonical is None
            or evidence.outcome_source is not OutcomeSource.OBSERVED
            or evidence.capture_mode
            is not CaptureMode.POST_TRANSITION_PREDECESSOR
            or evidence.failure_category is not None
        ):
            raise ValueError("finalized_persisted evidence is inconsistent")
    elif evidence.terminal_disposition is TerminalDisposition.NOT_FINALIZED:
        if (
            evidence.validation_outcome is not ValidationOutcome.VALID
            or evidence.finalized_state is not False
            or evidence.protocol_payload is None
            or evidence.protocol_payload.decoded_round_canonical is None
            or evidence.failure_category is not None
        ):
            raise ValueError("not_finalized evidence is inconsistent")
    elif evidence.terminal_disposition is TerminalDisposition.ALREADY_DURABLE:
        if (
            evidence.validation_outcome is not ValidationOutcome.NOT_EVALUATED
            or evidence.response_identity is not None
            or evidence.protocol_payload is not None
            or evidence.failure_category is not None
        ):
            raise ValueError("already_durable evidence is inconsistent")
    else:
        if evidence.failure_category is None:
            raise ValueError("failure disposition requires a failure category")
        if evidence.outcome_source is not None or evidence.capture_mode is not None:
            raise ValueError("failure evidence cannot claim outcome provenance")


def _transition_evidence_from_mapping(value: Mapping[str, Any]) -> TransitionEvidence:
    predecessor_value = value["predecessor_identity"]
    context_value = value["transition_context"]
    if not isinstance(predecessor_value, dict) or not isinstance(context_value, dict):
        raise ValueError("transition nested contracts must be objects")
    predecessor = CanonicalPredecessorIdentity(**predecessor_value)
    context = TransitionContext(**context_value)
    return TransitionEvidence(
        schema_identifier=value["schema_identifier"],
        schema_version=value["schema_version"],
        producer_identity=value["producer_identity"],
        observer_session_identity=value["observer_session_identity"],
        predecessor_identity=predecessor,
        successor_round_id=value["successor_round_id"],
        successor_snapshot_identity=value["successor_snapshot_identity"],
        transition_context=context,
        transition_identity=TransitionIdentity(value["transition_identity"]),
    )


def _payload_to_mapping(payload: PreservedProtocolPayload) -> dict[str, Any]:
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


def _post_transition_to_mapping(evidence: PostTransitionEvidence) -> dict[str, Any]:
    return {
        "schema_identifier": evidence.schema_identifier,
        "schema_version": evidence.schema_version,
        "producer_identity": evidence.producer_identity,
        "transition_evidence": evidence.transition_evidence.to_identity_material(),
        "attempt_timestamp": evidence.attempt_timestamp,
        "response_identity": (
            evidence.response_identity.sha256 if evidence.response_identity else None
        ),
        "predecessor_response_context_slot": evidence.predecessor_response_context_slot,
        "predecessor_response_commitment": evidence.predecessor_response_commitment,
        "response_raw_account_sha256": evidence.response_raw_account_sha256,
        "protocol_payload": (
            _payload_to_mapping(evidence.protocol_payload)
            if evidence.protocol_payload is not None
            else None
        ),
        "validation_outcome": evidence.validation_outcome.value,
        "failure_category": (
            evidence.failure_category.value if evidence.failure_category else None
        ),
        "terminal_disposition": evidence.terminal_disposition.value,
        "finalized_state": evidence.finalized_state,
        "outcome_source": (
            evidence.outcome_source.value if evidence.outcome_source else None
        ),
        "capture_mode": evidence.capture_mode.value if evidence.capture_mode else None,
        "evidence_identity": evidence.evidence_identity.sha256,
    }


def _post_transition_from_mapping(value: Mapping[str, Any]) -> PostTransitionEvidence:
    transition_value = value["transition_evidence"]
    if not isinstance(transition_value, dict):
        raise ValueError("transition_evidence must be an object")
    transition = _transition_evidence_from_mapping(transition_value)
    payload_value = value["protocol_payload"]
    if payload_value is not None and not isinstance(payload_value, dict):
        raise ValueError("protocol_payload must be an object or null")
    payload = PreservedProtocolPayload(**payload_value) if payload_value else None
    response_value = value["response_identity"]
    return PostTransitionEvidence(
        schema_identifier=value["schema_identifier"],
        schema_version=value["schema_version"],
        producer_identity=value["producer_identity"],
        transition_evidence=transition,
        attempt_timestamp=value["attempt_timestamp"],
        response_identity=(
            ResponseIdentity(response_value) if response_value is not None else None
        ),
        predecessor_response_context_slot=value["predecessor_response_context_slot"],
        predecessor_response_commitment=value["predecessor_response_commitment"],
        response_raw_account_sha256=value["response_raw_account_sha256"],
        protocol_payload=payload,
        validation_outcome=ValidationOutcome(value["validation_outcome"]),
        failure_category=(
            FailureCategory(value["failure_category"])
            if value["failure_category"] is not None
            else None
        ),
        terminal_disposition=TerminalDisposition(value["terminal_disposition"]),
        finalized_state=value["finalized_state"],
        outcome_source=(
            OutcomeSource(value["outcome_source"])
            if value["outcome_source"] is not None
            else None
        ),
        capture_mode=(
            CaptureMode(value["capture_mode"])
            if value["capture_mode"] is not None
            else None
        ),
        evidence_identity=EvidenceIdentity(value["evidence_identity"]),
    )


__all__ = [
    "CanonicalPredecessorIdentity",
    "CaptureMode",
    "EvidenceIdentity",
    "FailureCategory",
    "OutcomeSource",
    "PostTransitionEvidence",
    "PreservedProtocolPayload",
    "ResponseIdentity",
    "TerminalDisposition",
    "TransitionContext",
    "TransitionEvidence",
    "TransitionIdentity",
    "ValidationOutcome",
    "canonical_decode",
    "canonical_encode",
]
