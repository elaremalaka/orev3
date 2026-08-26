from __future__ import annotations

import threading
import pytest

import orev3.execution.control_storage as control_storage_module
from orev3.execution.canonical import CanonicalControlError
from orev3.execution.control_storage import (
    AppendDisposition, AppendOperation, AppendResult, ControlAuthority, ControlContractError,
    ControlHistoryConflict, ControlStorageObservation, FailureFacts, IncompleteControlSnapshot,
    ExecutionProgressFacts, RecoveryAuthority, RecoveryOperation,
    RecoveryPrerequisiteAuthority, StaleControlSnapshot, append_failed, append_record,
    build_control_record, build_failed_record, classify_failure,
    reconstruct_control_history, recover_failed,
)

Z, O, T, G = "0" * 64, "1" * 64, "2" * 64, "a" * 40


def authority(**changes: object) -> ControlAuthority:
    values: dict[str, object] = {
        "allocation_receipt_identity": Z, "attempt_identity": O, "attempt_kind": "official",
        "external_input_snapshot_identities": (Z,), "launch_authority_snapshot_identity": Z,
        "ordinal": 1, "profile_identity": Z, "readiness_identity": Z,
        "readiness_seal_commit": G, "remote_head_commit": G, "source_commit": G,
    }
    values.update(changes)
    return ControlAuthority(**values)  # type: ignore[arg-type]


def started(auth: ControlAuthority | None = None):
    return build_control_record(auth or authority(), sequence=1, predecessor={"status": "absent"},
                                state={"control_state": "STARTED"})


def valid(predecessor: str, auth: ControlAuthority | None = None, sequence: int = 2):
    return build_control_record(auth or authority(), sequence=sequence,
        predecessor={"identity": predecessor, "status": "known"},
        state={"control_state": "VALID", "experiment_audit_manifest_identity": Z,
               "experiment_audit_manifest_sha256": O})


def observations(*records):
    return tuple(ControlStorageObservation(i, record) for i, record in enumerate(records, 1))


def recovery_authority(snapshot, **changes: str) -> RecoveryAuthority:
    values = {"allocation_authority_identity": Z, "attempt_identity": O,
              "recovery_component_identity": O, "recovery_policy_identity": T,
              "snapshot_identity": snapshot.snapshot_identity}
    values.update(changes)
    return RecoveryAuthority(**values)


def recovery_prerequisite(snapshot, **changes: str) -> RecoveryPrerequisiteAuthority:
    values = {"allocation_authority_identity": Z, "attempt_identity": O,
              "control_storage_contract_identity": "4" * 64,
              "recovery_component_identity": O, "recovery_policy_identity": T,
              "expected_snapshot_identity": snapshot.snapshot_identity}
    values.update(changes)
    return RecoveryPrerequisiteAuthority(**values)


def facts(*, ranking_frozen: bool = False, outcome_authorized: bool = False,
          terminalization_started: bool = False, **changes: bool) -> FailureFacts:
    return FailureFacts(ExecutionProgressFacts(ranking_frozen, outcome_authorized,
                                               terminalization_started), **changes)


def forged_recovery_record(snapshot, failure: FailureFacts, *, sequence: int | None = None):
    """Construct canonical recovery material without using the governed builder."""
    state = {
        "control_state": "FAILED",
        "failure_control_evidence": control_storage_module._failure_evidence(snapshot, failure),
        "no_live_owner_evidence": {
            "allocation_authority_identity": Z,
            "no_live_owner_established": True,
            "recovery_component_identity": O,
            "recovery_operation": "atomic_compare_no_live_owner_and_append_failed",
            "recovery_policy_identity": T,
        },
        "recovery_mode": "recovery_no_live_owner_established",
    }
    return control_storage_module._build_control_record(
        authority(),
        sequence=sequence if sequence is not None else max(
            (record.sequence for record in snapshot.records), default=0
        ) + 1,
        predecessor={"status": "absent"} if snapshot.is_conflicting or not snapshot.common_prefix else {
            "identity": snapshot.common_prefix[-1].identity,
            "status": "known",
        },
        state=state,
    )


class SyntheticControlStore:
    def __init__(self, values=()) -> None:
        self.lock = threading.Lock(); self.observations = list(values)
        self.unavailable = False; self.ambiguous = False; self.live_owner = False

    def read_snapshot(self, attempt_identity: str):
        if self.unavailable: raise ControlContractError("authority unavailable")
        return reconstruct_control_history(tuple(self.observations))

    def compare_and_append(self, operation: AppendOperation):
        with self.lock:
            current = reconstruct_control_history(tuple(self.observations))
            if current.snapshot_identity != operation.expected_snapshot.snapshot_identity:
                return AppendResult(AppendDisposition.STALE, None)
            if self.unavailable: return AppendResult(AppendDisposition.UNAVAILABLE, None)
            self.observations.append(operation.proposed_observation)
            if self.ambiguous: return AppendResult(AppendDisposition.AMBIGUOUS, None)
            return AppendResult(AppendDisposition.COMMITTED, operation.record)

    def compare_fence_no_live_owner_and_append_failed(self, operation: RecoveryOperation):
        with self.lock:
            current = reconstruct_control_history(tuple(self.observations))
            if current.snapshot_identity != operation.expected_snapshot.snapshot_identity:
                return AppendResult(AppendDisposition.STALE, None)
            if self.unavailable or self.live_owner: return AppendResult(AppendDisposition.UNAVAILABLE, None)
            self.observations.append(operation.proposed_observation)
            if self.ambiguous: return AppendResult(AppendDisposition.AMBIGUOUS, None)
            return AppendResult(AppendDisposition.COMMITTED, operation.failed_record)


def test_coherent_history_and_known_identity() -> None:
    first = started(); second = valid(first.identity)
    assert first.identity == "8585546050c1501ccd37b03076eef351ccac988b3beec1ec89662e93682e9a4d"
    snapshot = reconstruct_control_history(observations(first, second))
    assert not snapshot.is_conflicting
    assert [record.state for record in snapshot.common_prefix] == ["STARTED", "VALID"]
    assert snapshot.terminal_identity == second.identity
    single = reconstruct_control_history(observations(first))
    assert single.snapshot_identity == "89ad62f3368c084014aadb44f8d249bb796780643ef8ac799fb126f5f240fece"


@pytest.mark.parametrize("field,value", [
    ("allocation_receipt_identity", T), ("attempt_identity", T), ("attempt_kind", "reproduction"),
    ("external_input_snapshot_identities", (T,)), ("launch_authority_snapshot_identity", T),
    ("ordinal", 2), ("profile_identity", T), ("readiness_identity", T),
    ("readiness_seal_commit", "b" * 40), ("remote_head_commit", "b" * 40),
    ("source_commit", "b" * 40),
])
def test_every_common_authority_field_is_enforced(field: str, value: object) -> None:
    first = started()
    snapshot = reconstruct_control_history(observations(first, valid(first.identity, authority(**{field: value}))))
    assert snapshot.is_conflicting
    with pytest.raises(ControlHistoryConflict):
        append_record(SyntheticControlStore(snapshot.observations), snapshot, valid(first.identity))


def test_authority_slots_preserve_conflicts_and_missing_slot() -> None:
    first = started(); other = valid(first.identity)
    cases = [
        ((ControlStorageObservation(1, first), ControlStorageObservation(1, first)), "duplicate_valid_record"),
        ((ControlStorageObservation(1, first), ControlStorageObservation(1, other)), "multiple_valid_records"),
        ((ControlStorageObservation(1, malformed=True),), "malformed_only"),
    ]
    for values, fact in cases:
        snapshot = reconstruct_control_history(values)
        assert snapshot.is_conflicting
        assert snapshot.failure_history_material["observed_control_objects"][0]["normalized_slot_fact"] == fact
    missing = reconstruct_control_history((ControlStorageObservation(2, first),))
    assert missing.is_conflicting and not missing.common_prefix


@pytest.mark.parametrize("values", (
    lambda first: (ControlStorageObservation(2, first),),
    lambda first: (ControlStorageObservation(1, first), ControlStorageObservation(3, malformed=True)),
))
def test_incomplete_enumeration_rejects_builder_and_direct_recovery(values) -> None:
    snapshot = reconstruct_control_history(values(started()))
    assert snapshot.is_conflicting and not snapshot.enumeration_complete
    failure = facts(terminalization_started=True, conflicting=True)
    prerequisite = recovery_prerequisite(snapshot)
    no_live_owner = recovery_authority(snapshot)
    with pytest.raises(IncompleteControlSnapshot, match="complete authority enumeration"):
        build_failed_record(authority(), snapshot, failure,
            recovery_prerequisite=prerequisite,
            no_live_owner_authority=no_live_owner)
    forged = forged_recovery_record(snapshot, failure)
    proposed_slot = max(item.authority_sequence for item in snapshot.observations) + 1
    with pytest.raises(IncompleteControlSnapshot, match="complete authority enumeration"):
        RecoveryOperation(snapshot, authority(), failure, prerequisite, no_live_owner,
                          ControlStorageObservation(proposed_slot, forged))


def test_conflicting_slot_order_is_invariant_and_retains_malformed_fact() -> None:
    first = started()
    values = (ControlStorageObservation(1, first), ControlStorageObservation(1, malformed=True))
    forward = reconstruct_control_history(values)
    reverse = reconstruct_control_history(tuple(reversed(values)))
    assert forward.snapshot_identity == reverse.snapshot_identity
    assert forward.failure_history_canonical == reverse.failure_history_canonical
    observed = forward.failure_history_material["observed_control_objects"]
    assert observed == [{
        "authority_sequence": 1,
        "normalized_slot_fact": "valid_and_malformed",
        "object_kind": "conflicting_control_slot",
        "validated_records": [{
            "control_record_identity": first.identity,
            "declared_control_sequence": 1,
            "predecessor_control_record_identity": {"status": "absent"},
        }],
    }]


def test_explicit_observation_order_is_canonical_and_bare_records_reject() -> None:
    first = started(); second = valid(first.identity)
    forward = observations(first, second)
    reversed_snapshot = reconstruct_control_history(tuple(reversed(forward)))
    normal = reconstruct_control_history(forward)
    assert reversed_snapshot.snapshot_identity == normal.snapshot_identity
    assert reversed_snapshot.failure_history_canonical == normal.failure_history_canonical
    assert reversed_snapshot.observations == normal.observations
    with pytest.raises(TypeError, match="explicit storage observations"):
        reconstruct_control_history((first, second))  # type: ignore[arg-type]


def test_fork_is_preserved_without_branch_selection() -> None:
    first = started(); fork = valid(first.identity, sequence=3)
    snapshot = reconstruct_control_history(observations(first, fork))
    assert snapshot.is_conflicting
    assert [record.identity for record in snapshot.common_prefix] == [first.identity]


def test_global_frontier_excludes_every_competing_successor() -> None:
    first = started(); accepted = valid(first.identity)
    rejected = build_control_record(authority(), sequence=2,
        predecessor={"identity": first.identity, "status": "known"},
        state={"control_state": "INVALID", "governing_invalidity_evidence_identity": Z,
               "governing_invalidity_evidence_sha256": O,
               "required_scientific_manifest_bindings": []})
    values = (ControlStorageObservation(1, first), ControlStorageObservation(2, accepted),
              ControlStorageObservation(3, rejected))
    snapshot = reconstruct_control_history(values)
    reversed_snapshot = reconstruct_control_history(tuple(reversed(values)))
    assert snapshot.is_conflicting
    assert snapshot.conflict_frontier_authority_sequence == 2
    assert snapshot.common_prefix == (first,)
    assert snapshot.last_durable_control_state == "STARTED"
    assert reversed_snapshot.snapshot_identity == snapshot.snapshot_identity
    assert reversed_snapshot.common_prefix == snapshot.common_prefix


def test_failed_is_snapshot_derived_with_precedence() -> None:
    first = started(); snapshot = reconstruct_control_history(observations(first))
    with pytest.raises(ControlContractError, match="reconstructed"):
        build_control_record(authority(), sequence=2, predecessor={"identity": first.identity, "status": "known"},
                             state={"control_state": "FAILED"})
    record = build_failed_record(authority(), snapshot,
        facts(terminalization_started=True, premature_outcome_access=True, shared_storage_failure=True))
    evidence = record.material["state"]["failure_control_evidence"]
    assert evidence["control_history"] == snapshot.failure_history_material
    assert evidence["last_durable_control_state"] == "STARTED"
    assert (evidence["failure_class"], evidence["normalized_failure_fact"]) == (
        "validity_not_established", "premature_outcome_access")
    known = build_failed_record(authority(), snapshot,
        facts(terminalization_started=True, owner_unavailable=True))
    assert known.identity == "e440c8f7403a61a1991bc143b85469ee1d1c143fd48637133437f9f7bd467966"
    store = SyntheticControlStore(observations(first))
    assert append_failed(store, snapshot, authority(),
        facts(terminalization_started=True, premature_outcome_access=True, shared_storage_failure=True)).state == "FAILED"


def test_failure_boundary_is_derived_only_from_explicit_progress() -> None:
    first = started(); snapshot = reconstruct_control_history(observations(first))
    before_freeze = build_failed_record(authority(), snapshot, facts(owner_unavailable=True))
    after_freeze = build_failed_record(authority(), snapshot,
        facts(ranking_frozen=True, owner_unavailable=True))
    assert before_freeze.material["state"]["failure_control_evidence"]["failure_boundary"] == "post_start_pre_ranking_freeze"
    assert after_freeze.material["state"]["failure_control_evidence"]["failure_boundary"] == "post_ranking_freeze_pre_authorization"
    with pytest.raises(TypeError, match="governed execution progress"):
        FailureFacts("terminalization", owner_unavailable=True)  # type: ignore[arg-type]


def test_conflict_failed_requires_recovery_and_absent_predecessor() -> None:
    first = started()
    snapshot = reconstruct_control_history((ControlStorageObservation(1, first),
                                            ControlStorageObservation(1, malformed=True)))
    failure = facts(terminalization_started=True, conflicting=True)
    with pytest.raises(ControlContractError, match="governed recovery"):
        build_failed_record(authority(), snapshot, failure)
    record = build_failed_record(authority(), snapshot, failure,
        recovery_prerequisite=recovery_prerequisite(snapshot),
        no_live_owner_authority=recovery_authority(snapshot))
    assert record.predecessor == {"status": "absent"}
    assert record.material["state"]["failure_control_evidence"]["control_history"] == snapshot.failure_history_material
    assert snapshot.enumeration_complete
    operation = RecoveryOperation(snapshot, authority(), failure,
        recovery_prerequisite(snapshot), recovery_authority(snapshot),
        ControlStorageObservation(2, record))
    assert operation.failed_record == record


def test_mixed_common_authority_conflict_cannot_be_recovered_by_selection() -> None:
    first = started(); other = started(authority(profile_identity=T))
    snapshot = reconstruct_control_history((ControlStorageObservation(1, first),
                                            ControlStorageObservation(1, other)))
    with pytest.raises(ControlContractError, match="ambiguous common control authority"):
        build_failed_record(authority(), snapshot, facts(terminalization_started=True, conflicting=True),
            recovery_prerequisite=recovery_prerequisite(snapshot),
            no_live_owner_authority=recovery_authority(snapshot))


def test_conflict_with_terminal_candidate_cannot_recover() -> None:
    first = started(); terminal = valid(first.identity)
    snapshot = reconstruct_control_history((ControlStorageObservation(1, first), ControlStorageObservation(1, terminal)))
    with pytest.raises(ControlContractError, match="terminal candidate"):
        build_failed_record(authority(), snapshot, facts(terminalization_started=True, conflicting=True),
            recovery_prerequisite=recovery_prerequisite(snapshot),
            no_live_owner_authority=recovery_authority(snapshot))


def test_terminal_conflict_rejects_builder_and_direct_canonical_recovery() -> None:
    first = started()
    accepted = valid(first.identity)
    rejected = build_control_record(authority(), sequence=2,
        predecessor={"identity": first.identity, "status": "known"},
        state={"control_state": "INVALID", "governing_invalidity_evidence_identity": Z,
               "governing_invalidity_evidence_sha256": O,
               "required_scientific_manifest_bindings": []})
    snapshot = reconstruct_control_history((ControlStorageObservation(1, first),
                                            ControlStorageObservation(2, accepted),
                                            ControlStorageObservation(3, rejected)))
    assert snapshot.enumeration_complete and snapshot.has_terminal_candidate
    failure = facts(terminalization_started=True, conflicting=True)
    prerequisite = recovery_prerequisite(snapshot)
    no_live_owner = recovery_authority(snapshot)
    with pytest.raises(ControlContractError, match="terminal candidate"):
        build_failed_record(authority(), snapshot, failure,
            recovery_prerequisite=prerequisite,
            no_live_owner_authority=no_live_owner)
    forged = forged_recovery_record(snapshot, failure)
    with pytest.raises(ControlContractError, match="terminal candidate"):
        RecoveryOperation(snapshot, authority(), failure, prerequisite, no_live_owner,
                          ControlStorageObservation(4, forged))


def test_every_terminal_candidate_shape_rejects_direct_recovery() -> None:
    first = started()
    accepted = valid(first.identity)
    rejected = build_control_record(authority(), sequence=2,
        predecessor={"identity": first.identity, "status": "known"},
        state={"control_state": "INVALID", "governing_invalidity_evidence_identity": Z,
               "governing_invalidity_evidence_sha256": O,
               "required_scientific_manifest_bindings": []})
    started_snapshot = reconstruct_control_history(observations(first))
    failed = build_failed_record(authority(), started_snapshot,
                                 facts(owner_unavailable=True))
    other_authority_terminal = valid(first.identity, authority(profile_identity=T))
    snapshots = (
        reconstruct_control_history(observations(first, accepted)),
        reconstruct_control_history(observations(first, rejected)),
        reconstruct_control_history(observations(first, failed)),
        reconstruct_control_history((ControlStorageObservation(1, first),
                                     ControlStorageObservation(2, accepted),
                                     ControlStorageObservation(2, malformed=True))),
        reconstruct_control_history((ControlStorageObservation(1, first),
                                     ControlStorageObservation(2, malformed=True),
                                     ControlStorageObservation(3, accepted))),
        reconstruct_control_history((ControlStorageObservation(1, first),
                                     ControlStorageObservation(2, accepted),
                                     ControlStorageObservation(2, accepted))),
        reconstruct_control_history((ControlStorageObservation(1, first),
                                     ControlStorageObservation(2, other_authority_terminal))),
    )
    base_prerequisite = recovery_prerequisite(started_snapshot)
    base_no_live_owner = recovery_authority(started_snapshot)
    base_candidate = build_failed_record(authority(), started_snapshot,
        facts(owner_unavailable=True), recovery_prerequisite=base_prerequisite,
        no_live_owner_authority=base_no_live_owner)
    for snapshot in snapshots:
        assert snapshot.has_terminal_candidate
        failure = facts(terminalization_started=True, conflicting=snapshot.is_conflicting,
                        owner_unavailable=not snapshot.is_conflicting)
        candidate = forged_recovery_record(snapshot, failure) if snapshot.is_conflicting else base_candidate
        proposed_slot = max(item.authority_sequence for item in snapshot.observations) + 1
        with pytest.raises(ControlContractError, match="terminal candidate"):
            RecoveryOperation(snapshot, authority(), failure, recovery_prerequisite(snapshot),
                              recovery_authority(snapshot),
                              ControlStorageObservation(proposed_slot, candidate))


@pytest.mark.parametrize("field", ["allocation_authority_identity", "attempt_identity",
    "recovery_component_identity", "recovery_policy_identity", "snapshot_identity"])
def test_recovery_operation_cross_binds_all_authority(field: str) -> None:
    first = started(); snapshot = reconstruct_control_history(observations(first)); ra = recovery_authority(snapshot)
    failure = facts(terminalization_started=True, owner_unavailable=True)
    prerequisite = recovery_prerequisite(snapshot)
    record = build_failed_record(authority(), snapshot, failure,
        recovery_prerequisite=prerequisite, no_live_owner_authority=ra)
    wrong = recovery_authority(snapshot, **{field: "3" * 64})
    with pytest.raises(ControlContractError):
        RecoveryOperation(snapshot, authority(), failure, prerequisite, wrong,
            ControlStorageObservation(2, record))


def test_recovery_operation_requires_exact_failed_state_and_sequence() -> None:
    first = started(); snapshot = reconstruct_control_history(observations(first))
    failure = facts(terminalization_started=True, owner_unavailable=True)
    prerequisite = recovery_prerequisite(snapshot)
    no_live_owner = recovery_authority(snapshot)
    with pytest.raises(ControlContractError, match="exact FAILED candidate"):
        RecoveryOperation(snapshot, authority(), failure, prerequisite, no_live_owner,
                          ControlStorageObservation(2, valid(first.identity)))
    wrong_sequence = forged_recovery_record(snapshot, failure, sequence=3)
    with pytest.raises(ControlContractError, match="sequence does not reconstruct"):
        RecoveryOperation(snapshot, authority(), failure, prerequisite, no_live_owner,
                          ControlStorageObservation(2, wrong_sequence))


def test_fixed_recovery_prerequisite_rejects_rebuilt_alternate_authority() -> None:
    first = started(); snapshot = reconstruct_control_history(observations(first))
    fixed = recovery_prerequisite(snapshot)
    alternate = recovery_authority(snapshot, allocation_authority_identity="3" * 64)
    with pytest.raises(ControlContractError, match="prerequisite allocation_authority_identity"):
        build_failed_record(authority(), snapshot,
            facts(terminalization_started=True, owner_unavailable=True),
            recovery_prerequisite=fixed, no_live_owner_authority=alternate)


@pytest.mark.parametrize("defect", ("unknown-predecessor", "sequence-gap", "mixed-authority", "post-terminal"))
def test_append_operation_is_closed_without_wrapper(defect: str) -> None:
    first = started(); snapshot = reconstruct_control_history(observations(first))
    if defect == "unknown-predecessor":
        candidate = valid("f" * 64, sequence=2)
        proposed = ControlStorageObservation(2, candidate)
    elif defect == "sequence-gap":
        candidate = valid(first.identity, sequence=3)
        proposed = ControlStorageObservation(2, candidate)
    elif defect == "mixed-authority":
        candidate = valid(first.identity, authority(profile_identity=T))
        proposed = ControlStorageObservation(2, candidate)
    else:
        terminal = valid(first.identity)
        terminal_snapshot = reconstruct_control_history(observations(first, terminal))
        candidate = build_control_record(authority(), sequence=3,
            predecessor={"identity": terminal.identity, "status": "known"},
            state={"control_state": "INVALID", "governing_invalidity_evidence_identity": Z,
                   "governing_invalidity_evidence_sha256": O,
                   "required_scientific_manifest_bindings": []})
        with pytest.raises(ControlContractError, match="coherent nonterminal"):
            AppendOperation(terminal_snapshot, ControlStorageObservation(3, candidate))
        return
    with pytest.raises(ControlContractError, match="unique coherent successor"):
        AppendOperation(snapshot, proposed)


def test_append_operation_rejects_wrong_storage_slot() -> None:
    first = started(); snapshot = reconstruct_control_history(observations(first))
    with pytest.raises(ControlContractError, match="unique successor slot"):
        AppendOperation(snapshot, ControlStorageObservation(3, valid(first.identity)))


def test_append_and_recovery_races_have_one_winner() -> None:
    first = started(); store = SyntheticControlStore(observations(first)); snapshot = store.read_snapshot(O)
    candidates = [valid(first.identity), build_control_record(authority(), sequence=2,
        predecessor={"identity": first.identity, "status": "known"},
        state={"control_state": "INVALID", "governing_invalidity_evidence_identity": Z,
               "governing_invalidity_evidence_sha256": O, "required_scientific_manifest_bindings": []})]
    barrier = threading.Barrier(3); results: list[str] = []
    def aw(record):
        barrier.wait()
        try: append_record(store, snapshot, record); results.append("committed")
        except StaleControlSnapshot: results.append("stale")
    threads = [threading.Thread(target=aw, args=(r,)) for r in candidates]
    [t.start() for t in threads]; barrier.wait(); [t.join() for t in threads]
    assert sorted(results) == ["committed", "stale"]

    store = SyntheticControlStore(observations(first)); snapshot = store.read_snapshot(O)
    barrier = threading.Barrier(3); results = []
    def rw():
        barrier.wait()
        try:
            recover_failed(store, snapshot, authority(),
                facts(terminalization_started=True, owner_unavailable=True),
                recovery_prerequisite(snapshot), recovery_authority(snapshot)); results.append("committed")
        except StaleControlSnapshot: results.append("stale")
    threads = [threading.Thread(target=rw) for _ in range(2)]
    [t.start() for t in threads]; barrier.wait(); [t.join() for t in threads]
    assert sorted(results) == ["committed", "stale"]


def test_recovery_live_owner_and_ambiguous_fail_closed() -> None:
    first = started(); failure = facts(terminalization_started=True, owner_unavailable=True)
    for flag in ("live_owner", "ambiguous"):
        store = SyntheticControlStore(observations(first)); snapshot = store.read_snapshot(O)
        setattr(store, flag, True)
        with pytest.raises(ControlContractError, match="not durably confirmed"):
            recover_failed(store, snapshot, authority(), failure,
                           recovery_prerequisite(snapshot), recovery_authority(snapshot))


def test_deep_immutability_bool_rejection_and_precedence() -> None:
    state = {"control_state": "STARTED"}
    record = build_control_record(authority(), sequence=1, predecessor={"status": "absent"}, state=state)
    before = record.canonical; state["control_state"] = "FAILED"; assert record.canonical == before
    exposed = reconstruct_control_history(observations(record)).failure_history_material
    exposed["common_prefix_record_identities"] = []
    assert reconstruct_control_history(observations(record)).failure_history_material["common_prefix_record_identities"]
    with pytest.raises(CanonicalControlError): authority(ordinal=True)
    assert classify_failure(conflicting=True, shared_storage_failure=True) == (
        "ambiguous_state", "conflicting_authoritative_control_records")
