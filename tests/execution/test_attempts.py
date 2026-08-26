from __future__ import annotations

import hashlib
import threading

import pytest

from orev3.execution.attempts import (
    ALLOCATION_RECEIPT_DOMAIN,
    ATTEMPT_IDENTITY_DOMAIN,
    OUTPUT_NAMESPACE_DOMAIN,
    AllocationCompletionAmbiguous,
    AllocationContractError,
    AllocationDisposition,
    AllocationRejected,
    AllocationRequest,
    AllocationTransactionResult,
    allocate,
    allocation_authority_identity,
    build_allocation_bundle,
)
from orev3.execution.canonical import CanonicalControlError, canonical_bytes


Z = "0" * 64
O = "1" * 64
G = "a" * 40


def request(**changes: object) -> AllocationRequest:
    values: dict[str, object] = {
        "allocation_authority_identity": Z,
        "allocator_contract_identity": O,
        "attempt_kind": "official",
        "experiment_identifier": "synthetic-experiment",
        "external_input_snapshot_identities": (Z,),
        "launch_authority_snapshot_identity": Z,
        "output_policy_revision": "readiness-v1-output-policy",
        "readiness_identity": Z,
        "readiness_seal_commit": G,
        "remote_head_commit": G,
        "source_commit": G,
    }
    values.update(changes)
    return AllocationRequest(**values)  # type: ignore[arg-type]


class SyntheticAtomicAllocator:
    """Test-only serialized authority; never imported by production source."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.next_by_scope: dict[tuple[str, str], int] = {}
        self.receipts: dict[str, object] = {}
        self.namespaces: set[str] = set()
        self.ambiguous_next = False
        self.reject_next = False
        self.collision_next: str | None = None

    def atomic_allocate(self, value: AllocationRequest) -> AllocationTransactionResult:
        with self.lock:
            if self.reject_next or self.collision_next is not None:
                self.reject_next = False
                self.collision_next = None
                return AllocationTransactionResult(AllocationDisposition.REJECTED, None, None)
            ordinal = self.next_by_scope.get(value.ordinal_scope, 1)
            self.next_by_scope[value.ordinal_scope] = ordinal + 1
            if self.ambiguous_next:
                self.ambiguous_next = False
                return AllocationTransactionResult(AllocationDisposition.AMBIGUOUS, ordinal, None)
            bundle = build_allocation_bundle(value, ordinal)
            if bundle.output_namespace_identity in self.namespaces:
                return AllocationTransactionResult(AllocationDisposition.REJECTED, None, None)
            self.namespaces.add(bundle.output_namespace_identity)
            self.receipts[bundle.allocation_receipt_identity] = bundle
            return AllocationTransactionResult(AllocationDisposition.COMMITTED, ordinal, bundle)


def test_known_answer_identity_chain_is_independently_framed() -> None:
    bundle = build_allocation_bundle(request(), 1)
    assert bundle.output_namespace_identity == hashlib.sha256(
        OUTPUT_NAMESPACE_DOMAIN.encode() + canonical_bytes(bundle.namespace_material)
    ).hexdigest() == "14004b36d3fceef5578d65796bafc333e220682f85da5e0ca266cd5ef34275bc"
    assert bundle.attempt_identity == hashlib.sha256(
        ATTEMPT_IDENTITY_DOMAIN.encode() + canonical_bytes(bundle.attempt_material)
    ).hexdigest() == "24885b5bc7cc46342f8e37cdef54d6acff426435daa29aa4e7f01c3a1a164f8d"
    receipt = dict(bundle.receipt_material)
    receipt.pop("allocation_receipt_identity")
    assert bundle.allocation_receipt_identity == hashlib.sha256(
        ALLOCATION_RECEIPT_DOMAIN.encode() + canonical_bytes(receipt)
    ).hexdigest() == "abba7261b70412b5b88e820b5a98d103d5f996aa7fdd50f8110a7227d8beb497"


def test_namespace_excludes_later_authority() -> None:
    material = build_allocation_bundle(request(), 1).namespace_material
    assert "attempt_identity" not in material
    assert "allocation_receipt_identity" not in material
    assert "readiness_identity" not in material


def test_allocation_bundle_material_is_deeply_immutable() -> None:
    bundle = build_allocation_bundle(request(), 1)
    before = bundle.attempt_canonical
    exposed = bundle.attempt_material
    exposed["ordinal"] = 2
    exposed["external_input_snapshot_identities"][0] = O  # type: ignore[index]
    assert bundle.attempt_canonical == before
    assert bundle.attempt_material["ordinal"] == 1


@pytest.mark.parametrize("ordinal", (True, 0, -1))
def test_invalid_ordinals_fail_closed(ordinal: object) -> None:
    with pytest.raises(CanonicalControlError):
        build_allocation_bundle(request(), ordinal)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    (("attempt_kind", "legacy_reproduction"), ("experiment_identifier", "Bad"),
     ("allocation_authority_identity", "x" * 64),
     ("external_input_snapshot_identities", (Z, Z))),
)
def test_malformed_request_fails(field: str, value: object) -> None:
    with pytest.raises(CanonicalControlError):
        request(**{field: value})


def test_allocation_authority_identifier_is_closed() -> None:
    assert len(allocation_authority_identity(
        allocation_authority_identifier="shared-attempts-v1",
        repository_authority_identifier="orev3-primary-repository-v1",
    )) == 64
    for value in ("", "UPPER", "a//b", "a..b", "a b"):
        with pytest.raises(CanonicalControlError):
            allocation_authority_identity(
                allocation_authority_identifier=value,
                repository_authority_identifier="orev3-primary-repository-v1",
            )


@pytest.mark.parametrize(
    "value", ("", "BAD PATH", "bad/path", "../bad", " bad", "bad\\path")
)
def test_repository_authority_identifier_is_closed(value: str) -> None:
    with pytest.raises(CanonicalControlError):
        allocation_authority_identity(
            allocation_authority_identifier="shared-attempts-v1",
            repository_authority_identifier=value,
        )


def test_output_policy_revision_is_exact() -> None:
    with pytest.raises(AllocationContractError, match="not governed"):
        request(output_policy_revision="attacker-controlled-revision")


def test_ambiguous_completion_burns_ordinal_and_retry_advances() -> None:
    backend = SyntheticAtomicAllocator()
    backend.ambiguous_next = True
    with pytest.raises(AllocationCompletionAmbiguous, match="ordinal 1"):
        allocate(backend, request())
    assert allocate(backend, request()).attempt_material["ordinal"] == 2


def test_rejection_does_not_consume_ordinal() -> None:
    backend = SyntheticAtomicAllocator(); backend.reject_next = True
    with pytest.raises(AllocationRejected):
        allocate(backend, request())
    assert allocate(backend, request()).attempt_material["ordinal"] == 1


@pytest.mark.parametrize("object_kind", ("file", "directory", "empty_directory", "symlink", "unexpected"))
def test_every_preexisting_namespace_object_is_a_collision(object_kind: str) -> None:
    backend = SyntheticAtomicAllocator(); backend.collision_next = object_kind
    with pytest.raises(AllocationRejected): allocate(backend, request())
    assert allocate(backend, request()).attempt_material["ordinal"] == 1


def test_deterministic_race_produces_unique_permanent_ordinals() -> None:
    backend = SyntheticAtomicAllocator()
    barrier = threading.Barrier(3)
    results: list[int] = []
    def worker() -> None:
        barrier.wait()
        results.append(int(allocate(backend, request()).attempt_material["ordinal"]))
    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads: thread.start()
    barrier.wait()
    for thread in threads: thread.join()
    assert sorted(results) == [1, 2]
    assert len(backend.receipts) == 2


def test_backend_cannot_substitute_bundle_for_request() -> None:
    class Forged:
        def atomic_allocate(self, value: AllocationRequest) -> AllocationTransactionResult:
            return AllocationTransactionResult(
                AllocationDisposition.COMMITTED, 1,
                build_allocation_bundle(request(experiment_identifier="other"), 1),
            )
    with pytest.raises(AllocationContractError, match="differs from request"):
        allocate(Forged(), request())


def test_malformed_backend_dispositions_fail_closed() -> None:
    class LeakingReject:
        def atomic_allocate(self, value: AllocationRequest) -> AllocationTransactionResult:
            return AllocationTransactionResult(
                AllocationDisposition.REJECTED, 1, build_allocation_bundle(value, 1)
            )
    with pytest.raises(AllocationContractError, match="leaked authority"):
        allocate(LeakingReject(), request())
