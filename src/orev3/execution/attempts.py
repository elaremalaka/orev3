"""Deterministic attempt-allocation semantics for readiness v1.1.

This module defines the repository-owned allocation contract.  It deliberately
contains no configured authority, transport, filesystem root, or live backend.
Providers must implement :class:`AtomicAllocationPort` with one durable atomic
transaction; an implementation unable to do so cannot be used officially.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping
import re
from typing import Protocol, runtime_checkable

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    normalize_experiment_identifier,
    parse_canonical_bytes,
    require_git_object,
    require_integer,
    require_sha256,
    require_string,
)


ALLOCATION_AUTHORITY_DOMAIN = "orev3:experiment-attempt-allocation-authority:v1\n"
OUTPUT_NAMESPACE_DOMAIN = "orev3:experiment-output-namespace:v1\n"
ATTEMPT_IDENTITY_DOMAIN = "orev3:experiment-attempt:v1\n"
ALLOCATION_RECEIPT_DOMAIN = "orev3:experiment-attempt-allocation:v1\n"
OUTPUT_NAMESPACE_REVISION = "output-namespace-identity-material-v1"
ATTEMPT_IDENTITY_SCHEMA = "attempt-identity-material-v1"
OUTPUT_POLICY_REVISION = "readiness-v1-output-policy"
ATTEMPT_KINDS = frozenset({"official", "reproduction"})
SAFE_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]*")


class AllocationContractError(CanonicalControlError):
    """The requested or returned allocation violates the governed contract."""


class AllocationRejected(AllocationContractError):
    """No ordinal was consumed and no allocation authority was created."""


class AllocationCompletionAmbiguous(AllocationContractError):
    """Completion is unknown; the exposed ordinal is permanently consumed."""

    def __init__(self, ordinal: int) -> None:
        self.ordinal = require_integer("ambiguous ordinal", ordinal, minimum=1)
        super().__init__(f"allocation completion is ambiguous for ordinal {ordinal}")


def _attempt_kind(value: object) -> str:
    value = require_string("attempt_kind", value)
    if value not in ATTEMPT_KINDS:
        raise AllocationContractError("attempt_kind is not governed")
    return value


def _git(name: str, value: object) -> str:
    if isinstance(value, str) and len(value) == 64:
        return require_git_object(name, value, "sha256")
    return require_git_object(name, value, "sha1")


def allocation_authority_identity(
    *,
    allocation_authority_identifier: str,
    repository_authority_identifier: str,
) -> str:
    identifier = require_string("allocation_authority_identifier", allocation_authority_identifier)
    if len(identifier) > 64:
        raise AllocationContractError("allocation authority identifier is too long")
    if re.fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", identifier) is None:
        raise AllocationContractError("allocation authority identifier is not canonical")
    repository = require_string(
        "repository_authority_identifier",
        repository_authority_identifier,
        pattern=SAFE_IDENTIFIER,
    )
    return domain_identity(
        ALLOCATION_AUTHORITY_DOMAIN,
        {
            "allocation_authority_identifier": identifier,
            "allocation_authority_schema_revision": "allocation-authority-identity-material-v1",
            "repository_authority_identifier": repository,
        },
    )


@dataclass(frozen=True, slots=True)
class AllocationRequest:
    """Immutable launch authority required before an ordinal may be consumed."""

    allocation_authority_identity: str
    allocator_contract_identity: str
    attempt_kind: str
    experiment_identifier: str
    external_input_snapshot_identities: tuple[str, ...]
    launch_authority_snapshot_identity: str
    output_policy_revision: str
    readiness_identity: str
    readiness_seal_commit: str
    remote_head_commit: str
    source_commit: str

    def __post_init__(self) -> None:
        require_sha256("allocation_authority_identity", self.allocation_authority_identity)
        require_sha256("allocator_contract_identity", self.allocator_contract_identity)
        _attempt_kind(self.attempt_kind)
        normalize_experiment_identifier(self.experiment_identifier)
        if not isinstance(self.external_input_snapshot_identities, tuple):
            raise AllocationContractError("external input identities must be a tuple")
        if len(set(self.external_input_snapshot_identities)) != len(
            self.external_input_snapshot_identities
        ):
            raise AllocationContractError("external input identities must be unique")
        for value in self.external_input_snapshot_identities:
            require_sha256("external_input_snapshot_identity", value)
        require_sha256(
            "launch_authority_snapshot_identity", self.launch_authority_snapshot_identity
        )
        if self.output_policy_revision != OUTPUT_POLICY_REVISION:
            raise AllocationContractError("output_policy_revision is not governed")
        require_sha256("readiness_identity", self.readiness_identity)
        _git("readiness_seal_commit", self.readiness_seal_commit)
        _git("remote_head_commit", self.remote_head_commit)
        _git("source_commit", self.source_commit)

    @property
    def ordinal_scope(self) -> tuple[str, str]:
        return self.experiment_identifier, self.attempt_kind


@dataclass(frozen=True, slots=True)
class AllocationBundle:
    """The acyclic namespace, attempt, and immutable receipt authority."""

    namespace_canonical: bytes
    output_namespace_identity: str
    attempt_canonical: bytes
    attempt_identity: str
    receipt_canonical: bytes
    allocation_receipt_identity: str

    def __post_init__(self) -> None:
        validate_allocation_bundle(self)

    @property
    def namespace_material(self) -> dict[str, object]:
        return parse_canonical_bytes(self.namespace_canonical)

    @property
    def attempt_material(self) -> dict[str, object]:
        return parse_canonical_bytes(self.attempt_canonical)

    @property
    def receipt_material(self) -> dict[str, object]:
        return parse_canonical_bytes(self.receipt_canonical)


def build_allocation_bundle(request: AllocationRequest, ordinal: int) -> AllocationBundle:
    ordinal = require_integer("permanent_ordinal", ordinal, minimum=1)
    namespace = {
        "allocation_authority_identity": request.allocation_authority_identity,
        "allocator_contract_identity": request.allocator_contract_identity,
        "attempt_kind": request.attempt_kind,
        "experiment_identifier": request.experiment_identifier,
        "output_namespace_schema_revision": OUTPUT_NAMESPACE_REVISION,
        "output_policy_revision": request.output_policy_revision,
        "permanent_ordinal": ordinal,
    }
    namespace_identity = domain_identity(OUTPUT_NAMESPACE_DOMAIN, namespace)
    attempt = {
        "allocation_authority_identity": request.allocation_authority_identity,
        "allocator_contract_identity": request.allocator_contract_identity,
        "attempt_identity_schema_identifier": ATTEMPT_IDENTITY_SCHEMA,
        "attempt_kind": request.attempt_kind,
        "experiment_identifier": request.experiment_identifier,
        "external_input_snapshot_identities": list(
            request.external_input_snapshot_identities
        ),
        "launch_authority_snapshot_identity": request.launch_authority_snapshot_identity,
        "ordinal": ordinal,
        "output_namespace_identity": namespace_identity,
        "output_policy_revision": request.output_policy_revision,
        "readiness_identity": request.readiness_identity,
        "readiness_seal_commit": request.readiness_seal_commit,
        "remote_head_commit": request.remote_head_commit,
        "schema_version": 1,
        "source_commit": request.source_commit,
    }
    attempt_identity = domain_identity(ATTEMPT_IDENTITY_DOMAIN, attempt)
    receipt = {
        "allocation_authority_identity": request.allocation_authority_identity,
        "allocator_contract_identity": request.allocator_contract_identity,
        "attempt_identity": attempt_identity,
        "attempt_kind": request.attempt_kind,
        "experiment_identifier": request.experiment_identifier,
        "external_input_snapshot_identities": list(
            request.external_input_snapshot_identities
        ),
        "launch_authority_snapshot_identity": request.launch_authority_snapshot_identity,
        "ordinal": ordinal,
        "output_namespace_identity": namespace_identity,
        "readiness_identity": request.readiness_identity,
        "readiness_seal_commit": request.readiness_seal_commit,
        "remote_head_commit": request.remote_head_commit,
        "schema_version": 1,
        "source_commit": request.source_commit,
    }
    receipt_identity = domain_identity(ALLOCATION_RECEIPT_DOMAIN, receipt)
    receipt["allocation_receipt_identity"] = receipt_identity
    return AllocationBundle(
        canonical_bytes(namespace), namespace_identity, canonical_bytes(attempt),
        attempt_identity, canonical_bytes(receipt), receipt_identity
    )


def validate_allocation_bundle(bundle: AllocationBundle) -> None:
    ordinal = require_integer("ordinal", bundle.attempt_material.get("ordinal"), minimum=1)
    request = AllocationRequest(
        allocation_authority_identity=str(bundle.attempt_material.get("allocation_authority_identity")),
        allocator_contract_identity=str(bundle.attempt_material.get("allocator_contract_identity")),
        attempt_kind=str(bundle.attempt_material.get("attempt_kind")),
        experiment_identifier=str(bundle.attempt_material.get("experiment_identifier")),
        external_input_snapshot_identities=tuple(
            bundle.attempt_material.get("external_input_snapshot_identities", ())
        ),
        launch_authority_snapshot_identity=str(
            bundle.attempt_material.get("launch_authority_snapshot_identity")
        ),
        output_policy_revision=str(bundle.attempt_material.get("output_policy_revision")),
        readiness_identity=str(bundle.attempt_material.get("readiness_identity")),
        readiness_seal_commit=str(bundle.attempt_material.get("readiness_seal_commit")),
        remote_head_commit=str(bundle.attempt_material.get("remote_head_commit")),
        source_commit=str(bundle.attempt_material.get("source_commit")),
    )
    expected = _unvalidated_bundle(request, ordinal)
    if canonical_bytes(bundle.namespace_material) != canonical_bytes(expected[0]) or bundle.output_namespace_identity != expected[1]:
        raise AllocationContractError("output namespace does not reconstruct")
    if canonical_bytes(bundle.attempt_material) != canonical_bytes(expected[2]) or bundle.attempt_identity != expected[3]:
        raise AllocationContractError("attempt identity does not reconstruct")
    if canonical_bytes(bundle.receipt_material) != canonical_bytes(expected[4]) or bundle.allocation_receipt_identity != expected[5]:
        raise AllocationContractError("allocation receipt does not reconstruct")


def _unvalidated_bundle(request: AllocationRequest, ordinal: int) -> tuple[object, ...]:
    namespace = {
        "allocation_authority_identity": request.allocation_authority_identity,
        "allocator_contract_identity": request.allocator_contract_identity,
        "attempt_kind": request.attempt_kind,
        "experiment_identifier": request.experiment_identifier,
        "output_namespace_schema_revision": OUTPUT_NAMESPACE_REVISION,
        "output_policy_revision": request.output_policy_revision,
        "permanent_ordinal": ordinal,
    }
    namespace_identity = domain_identity(OUTPUT_NAMESPACE_DOMAIN, namespace)
    attempt = {
        "allocation_authority_identity": request.allocation_authority_identity,
        "allocator_contract_identity": request.allocator_contract_identity,
        "attempt_identity_schema_identifier": ATTEMPT_IDENTITY_SCHEMA,
        "attempt_kind": request.attempt_kind,
        "experiment_identifier": request.experiment_identifier,
        "external_input_snapshot_identities": list(request.external_input_snapshot_identities),
        "launch_authority_snapshot_identity": request.launch_authority_snapshot_identity,
        "ordinal": ordinal,
        "output_namespace_identity": namespace_identity,
        "output_policy_revision": request.output_policy_revision,
        "readiness_identity": request.readiness_identity,
        "readiness_seal_commit": request.readiness_seal_commit,
        "remote_head_commit": request.remote_head_commit,
        "schema_version": 1,
        "source_commit": request.source_commit,
    }
    attempt_identity = domain_identity(ATTEMPT_IDENTITY_DOMAIN, attempt)
    receipt = {
        "allocation_authority_identity": request.allocation_authority_identity,
        "allocation_receipt_identity": "",
        "allocator_contract_identity": request.allocator_contract_identity,
        "attempt_identity": attempt_identity,
        "attempt_kind": request.attempt_kind,
        "experiment_identifier": request.experiment_identifier,
        "external_input_snapshot_identities": list(request.external_input_snapshot_identities),
        "launch_authority_snapshot_identity": request.launch_authority_snapshot_identity,
        "ordinal": ordinal,
        "output_namespace_identity": namespace_identity,
        "readiness_identity": request.readiness_identity,
        "readiness_seal_commit": request.readiness_seal_commit,
        "remote_head_commit": request.remote_head_commit,
        "schema_version": 1,
        "source_commit": request.source_commit,
    }
    identity_material = dict(receipt)
    identity_material.pop("allocation_receipt_identity")
    receipt_identity = domain_identity(ALLOCATION_RECEIPT_DOMAIN, identity_material)
    receipt["allocation_receipt_identity"] = receipt_identity
    return namespace, namespace_identity, attempt, attempt_identity, receipt, receipt_identity


class AllocationDisposition(str, Enum):
    COMMITTED = "committed"
    REJECTED = "rejected_before_consumption"
    AMBIGUOUS = "ambiguous_ordinal_consumed"


@dataclass(frozen=True, slots=True)
class AllocationTransactionResult:
    disposition: AllocationDisposition
    ordinal: int | None
    bundle: AllocationBundle | None


@runtime_checkable
class AtomicAllocationPort(Protocol):
    """Provider boundary; the method must be one durable atomic transaction."""

    def atomic_allocate(self, request: AllocationRequest) -> AllocationTransactionResult: ...


def allocate(backend: AtomicAllocationPort, request: AllocationRequest) -> AllocationBundle:
    if not isinstance(backend, AtomicAllocationPort):
        raise TypeError("backend does not implement AtomicAllocationPort")
    result = backend.atomic_allocate(request)
    if not isinstance(result, AllocationTransactionResult):
        raise TypeError("backend returned an unsupported allocation result")
    if result.disposition is AllocationDisposition.REJECTED:
        if result.ordinal is not None or result.bundle is not None:
            raise AllocationContractError("rejected allocation leaked authority")
        raise AllocationRejected("allocation rejected before ordinal consumption")
    if result.disposition is AllocationDisposition.AMBIGUOUS:
        if result.bundle is not None or result.ordinal is None:
            raise AllocationContractError("ambiguous allocation result is malformed")
        raise AllocationCompletionAmbiguous(result.ordinal)
    if result.disposition is not AllocationDisposition.COMMITTED:
        raise AllocationContractError("allocation disposition is not governed")
    if result.ordinal is None or result.bundle is None:
        raise AllocationContractError("committed allocation lacks durable authority")
    validate_allocation_bundle(result.bundle)
    if result.bundle.attempt_material["ordinal"] != result.ordinal:
        raise AllocationContractError("backend ordinal and allocation bundle differ")
    expected = build_allocation_bundle(request, result.ordinal)
    if (
        result.bundle.output_namespace_identity != expected.output_namespace_identity
        or result.bundle.attempt_identity != expected.attempt_identity
        or result.bundle.allocation_receipt_identity != expected.allocation_receipt_identity
        or canonical_bytes(result.bundle.namespace_material) != canonical_bytes(expected.namespace_material)
        or canonical_bytes(result.bundle.attempt_material) != canonical_bytes(expected.attempt_material)
        or canonical_bytes(result.bundle.receipt_material) != canonical_bytes(expected.receipt_material)
    ):
        raise AllocationContractError("backend allocation differs from request")
    return result.bundle


__all__ = [
    "ALLOCATION_AUTHORITY_DOMAIN", "ALLOCATION_RECEIPT_DOMAIN",
    "ATTEMPT_IDENTITY_DOMAIN", "OUTPUT_NAMESPACE_DOMAIN", "AllocationBundle",
    "AllocationCompletionAmbiguous", "AllocationContractError",
    "AllocationDisposition", "AllocationRejected", "AllocationRequest",
    "AllocationTransactionResult", "AtomicAllocationPort", "allocate",
    "allocation_authority_identity", "build_allocation_bundle",
    "validate_allocation_bundle",
]
