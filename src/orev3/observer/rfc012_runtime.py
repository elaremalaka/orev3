"""Supported RFC-012 Observer runtime integration.

This module wires the completed Phase 1–4 components.  It deliberately owns no
transition, response-validation, persistence-ordering, dataset, or reporting
calculation logic.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from orev3.data.models import ObserverSnapshot
from orev3.data.writer import CollectorEventWriter, JsonlSnapshotWriter
from orev3.datasets.rfc012_evidence import (
    ORE_PROGRAM_IDENTITY,
    ORE_PROTOCOL_REVISION,
    ROUND_DECODER_IDENTITY,
    SOLANA_MAINNET_GENESIS_HASH,
    SOLANA_MAINNET_NETWORK,
    CanonicalPredecessorIdentity,
    TransitionContext,
    canonical_encode,
)
from orev3.datasets.rfc012_transition import (
    PredecessorObservation,
    Rfc012EvidenceStore,
    Rfc012TransitionProcessor,
    TransitionProcessResult,
)
from orev3.observer.accounts import BOARD_ADDRESS, decode_account_data
from orev3.observer.rpc import SolanaRpcClient


DEFAULT_RFC012_RUNTIME_EVIDENCE_ROOT = Path("data/raw/rfc012")
_SNAPSHOT_IDENTITY_DOMAIN = "orev3:rfc012:successor-snapshot:v1"


class ImmutableRfc012Report(Protocol):
    """Structural Phase 4 output accepted by the existing event writer."""

    report_identity: str

    def to_canonical_bytes(self) -> bytes: ...


@dataclass(frozen=True, slots=True)
class ContextualObserverSnapshot:
    """Normal snapshot plus the exact Board response context that selected it."""

    snapshot: ObserverSnapshot
    snapshot_identity: str
    provider_identity: str
    board_response_commitment: str
    board_response_context_slot: int

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ObserverSnapshot):
            raise TypeError("snapshot must be ObserverSnapshot")
        expected = observer_snapshot_identity(self.snapshot)
        if self.snapshot_identity != expected:
            raise ValueError("successor snapshot identity does not reconstruct")
        if not isinstance(self.provider_identity, str) or not self.provider_identity:
            raise ValueError("provider_identity must be nonempty")
        if self.board_response_commitment not in {
            "processed",
            "confirmed",
            "finalized",
        }:
            raise ValueError("board response commitment is unsupported")
        if (
            isinstance(self.board_response_context_slot, bool)
            or not isinstance(self.board_response_context_slot, int)
            or self.board_response_context_slot < 0
        ):
            raise ValueError("board response context slot must be nonnegative")


def observer_snapshot_identity(snapshot: ObserverSnapshot) -> str:
    """Bind Phase 1 evidence to one byte-stable normal successor snapshot."""

    if not isinstance(snapshot, ObserverSnapshot):
        raise TypeError("snapshot must be ObserverSnapshot")
    material = {
        "domain": _SNAPSHOT_IDENTITY_DOMAIN,
        "snapshot": snapshot.model_dump(mode="json"),
    }
    return hashlib.sha256(canonical_encode(material)).hexdigest()


@dataclass(frozen=True, slots=True)
class SolanaPredecessorReader:
    """Adapt the existing read-only RPC client to Phase 2's reader protocol."""

    rpc: SolanaRpcClient

    def observe_predecessor(
        self,
        account_address: str,
        *,
        commitment: str,
        min_context_slot: int,
    ) -> PredecessorObservation:
        response = self.rpc.get_account_info_with_context(
            account_address,
            commitment=commitment,
            min_context_slot=min_context_slot,
        )
        context = response["context"]
        value = response["value"]
        context_slot = int(context["slot"])
        if value is None:
            owner = None
            raw_account_data = None
        else:
            if not isinstance(value, dict):
                raise ValueError("predecessor account response is malformed")
            owner_value = value.get("owner")
            owner = owner_value if isinstance(owner_value, str) else None
            raw_account_data = decode_account_data(value)
        return PredecessorObservation(
            network_identity=SOLANA_MAINNET_NETWORK,
            expected_genesis_hash=SOLANA_MAINNET_GENESIS_HASH,
            provider_identity=self.rpc.provider_identity,
            account_address=account_address,
            response_context_slot=context_slot,
            response_commitment=commitment,
            account_owner=owner,
            raw_account_data=raw_account_data,
            ore_program_identity=ORE_PROGRAM_IDENTITY,
            protocol_revision=ORE_PROTOCOL_REVISION,
            decoder_identity=ROUND_DECODER_IDENTITY,
        )


@dataclass(frozen=True, slots=True)
class SnapshotFinalizedHistory:
    """Delegate duplicate detection to the existing normal snapshot writer."""

    writer: JsonlSnapshotWriter

    def has_finalized(
        self,
        predecessor_identity: CanonicalPredecessorIdentity,
    ) -> bool:
        return self.writer.has_finalized_round(
            predecessor_identity.predecessor_round_id
        )


class Rfc012RuntimeIntegration:
    """Invoke completed RFC-012 components at the supported runtime boundary."""

    def __init__(
        self,
        *,
        processor: Rfc012TransitionProcessor,
        event_writer: CollectorEventWriter,
    ) -> None:
        self._processor = processor
        self._event_writer = event_writer

    def process_transition(
        self,
        *,
        previous_round_id: int | None,
        successor: ContextualObserverSnapshot,
        successor_durably_persisted: bool,
    ) -> TransitionProcessResult:
        current_round_id = successor.snapshot.round.round_id
        transition_context = (
            TransitionContext(
                network_identity=SOLANA_MAINNET_NETWORK,
                expected_genesis_hash=SOLANA_MAINNET_GENESIS_HASH,
                provider_identity=successor.provider_identity,
                board_account_identity=str(BOARD_ADDRESS),
                predecessor_round_id=previous_round_id,
                successor_round_id=current_round_id,
                successor_snapshot_identity=successor.snapshot_identity,
                board_response_commitment=successor.board_response_commitment,
                board_response_context_slot=(
                    successor.board_response_context_slot
                ),
            )
            if previous_round_id is not None
            and current_round_id == previous_round_id + 1
            else None
        )
        return self._processor.process(
            previous_round_id=previous_round_id,
            successor_snapshot=successor.snapshot,
            successor_snapshot_identity=successor.snapshot_identity,
            transition_context=transition_context,
            successor_validated=True,
            successor_durably_persisted=successor_durably_persisted,
            transition_unambiguous=True,
        )

    def expose_report(self, report: ImmutableRfc012Report) -> Path:
        """Expose an already-computed Phase 4 report without recalculation."""

        canonical = report.to_canonical_bytes()
        return self._event_writer.write(
            {
                "event": "rfc012_observability_report",
                "report_identity": report.report_identity,
                "canonical_report_base64": base64.b64encode(canonical).decode(
                    "ascii"
                ),
            }
        )


def create_supported_rfc012_runtime(
    *,
    rpc: SolanaRpcClient,
    snapshot_writer: JsonlSnapshotWriter,
    event_writer: CollectorEventWriter,
    evidence_root: str | Path = DEFAULT_RFC012_RUNTIME_EVIDENCE_ROOT,
) -> Rfc012RuntimeIntegration:
    """Wire the supported runtime to the durable Phase 2 boundaries."""

    evidence_path = Path(evidence_root) / "transition_evidence_v1.jsonl"
    processor = Rfc012TransitionProcessor(
        reader=SolanaPredecessorReader(rpc),
        evidence_store=Rfc012EvidenceStore(evidence_path),
        finalized_history=SnapshotFinalizedHistory(snapshot_writer),
    )
    return Rfc012RuntimeIntegration(
        processor=processor,
        event_writer=event_writer,
    )


__all__ = (
    "ContextualObserverSnapshot",
    "DEFAULT_RFC012_RUNTIME_EVIDENCE_ROOT",
    "ImmutableRfc012Report",
    "Rfc012RuntimeIntegration",
    "SnapshotFinalizedHistory",
    "SolanaPredecessorReader",
    "create_supported_rfc012_runtime",
    "observer_snapshot_identity",
)
