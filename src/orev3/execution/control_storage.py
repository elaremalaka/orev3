"""Backend-neutral append-only attempt-control semantics for readiness v1.1.

No store is configured here.  The port methods represent indivisible backend
transactions; production use must supply a shared authority capable of proving
their atomic and durable semantics.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    parse_canonical_bytes,
    require_boolean,
    require_git_object,
    require_integer,
    require_sha256,
    require_string,
    validate_exact_fields,
)


CONTROL_RECORD_DOMAIN = "orev3:experiment-attempt-control:v1\n"
CONTROL_SNAPSHOT_DOMAIN = "orev3:experiment-control-snapshot-cas:v1\n"
CONTROL_STATES = frozenset({"STARTED", "VALID", "INVALID", "FAILED"})
TERMINAL_STATES = frozenset({"VALID", "INVALID", "FAILED"})
FAILURE_BOUNDARIES = (
    "post_allocation_pre_start",
    "post_start_pre_ranking_freeze",
    "post_ranking_freeze_pre_authorization",
    "post_authorization_pre_terminal",
    "terminalization",
)
FAILURE_FACTS = {
    "ambiguous_state": (
        "conflicting_authoritative_control_records",
        "indeterminate_authoritative_control_state",
    ),
    "infrastructure_failure": (
        "shared_control_storage_failure",
        "execution_infrastructure_failure",
    ),
    "interruption": ("governed_owner_terminated", "governed_owner_unavailable"),
    "validity_not_established": (
        "premature_outcome_access",
        "terminal_scientific_authority_not_established",
    ),
}


class ControlContractError(CanonicalControlError):
    pass


class ControlHistoryConflict(ControlContractError):
    pass


class StaleControlSnapshot(ControlContractError):
    pass


def _git(name: str, value: object) -> str:
    if isinstance(value, str) and len(value) == 64:
        return require_git_object(name, value, "sha256")
    return require_git_object(name, value, "sha1")


def _predecessor(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ControlContractError("predecessor must be a closed object")
    status = value.get("status")
    if status == "absent":
        validate_exact_fields(value, {"status"}, label="absent predecessor")
        return {"status": "absent"}
    if status == "known":
        validate_exact_fields(value, {"identity", "status"}, label="known predecessor")
        return {"identity": require_sha256("predecessor identity", value["identity"]), "status": "known"}
    raise ControlContractError("predecessor branch is unsupported")


@dataclass(frozen=True, slots=True)
class ControlAuthority:
    allocation_receipt_identity: str
    attempt_identity: str
    attempt_kind: str
    external_input_snapshot_identities: tuple[str, ...]
    launch_authority_snapshot_identity: str
    ordinal: int
    profile_identity: str
    readiness_identity: str
    readiness_seal_commit: str
    remote_head_commit: str
    source_commit: str

    def __post_init__(self) -> None:
        require_sha256("allocation_receipt_identity", self.allocation_receipt_identity)
        require_sha256("attempt_identity", self.attempt_identity)
        if self.attempt_kind not in {"official", "reproduction"}:
            raise ControlContractError("attempt_kind is not governed")
        if not isinstance(self.external_input_snapshot_identities, tuple):
            raise ControlContractError("external input identities must be a tuple")
        if len(set(self.external_input_snapshot_identities)) != len(self.external_input_snapshot_identities):
            raise ControlContractError("external input identities must be unique")
        for identity in self.external_input_snapshot_identities:
            require_sha256("external input snapshot identity", identity)
        require_sha256("launch authority snapshot identity", self.launch_authority_snapshot_identity)
        require_integer("ordinal", self.ordinal, minimum=1)
        require_sha256("profile identity", self.profile_identity)
        require_sha256("readiness identity", self.readiness_identity)
        _git("readiness seal commit", self.readiness_seal_commit)
        _git("remote head commit", self.remote_head_commit)
        _git("source commit", self.source_commit)

    @property
    def material(self) -> dict[str, Any]:
        return {
            "allocation_receipt_identity": self.allocation_receipt_identity,
            "attempt_identity": self.attempt_identity,
            "attempt_kind": self.attempt_kind,
            "external_input_snapshot_identities": list(self.external_input_snapshot_identities),
            "launch_authority_snapshot_identity": self.launch_authority_snapshot_identity,
            "ordinal": self.ordinal,
            "profile_identity": self.profile_identity,
            "readiness_identity": self.readiness_identity,
            "readiness_seal_commit": self.readiness_seal_commit,
            "remote_head_commit": self.remote_head_commit,
            "source_commit": self.source_commit,
        }


@dataclass(frozen=True, slots=True)
class ControlRecord:
    """Canonical bytes are retained so nested caller objects cannot mutate authority."""

    canonical: bytes
    identity: str

    @property
    def material(self) -> dict[str, Any]:
        return parse_canonical_bytes(self.canonical)

    @property
    def state(self) -> str:
        return str(self.material["state"]["control_state"])

    @property
    def sequence(self) -> int:
        return int(self.material["sequence"])

    @property
    def predecessor(self) -> dict[str, str]:
        return dict(self.material["predecessor_control_record_identity"])

    @property
    def authority_material(self) -> dict[str, Any]:
        material = self.material
        return {key: material[key] for key in ControlAuthority.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ControlStorageObservation:
    """One authority-assigned slot from a complete atomic storage enumeration."""

    authority_sequence: int
    record: ControlRecord | None = None
    malformed: bool = False

    def __post_init__(self) -> None:
        require_integer("authority_sequence", self.authority_sequence, minimum=1)
        if (self.record is None) == (not self.malformed):
            raise ControlContractError("slot must contain exactly a record or malformed material")
        if self.record is not None:
            validate_control_record(self.record)


@dataclass(frozen=True, slots=True)
class ExecutionProgressFacts:
    ranking_frozen: bool = False
    outcome_authorized: bool = False
    terminalization_started: bool = False

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            require_boolean(name, getattr(self, name))
        if self.outcome_authorized and not self.ranking_frozen:
            raise ControlContractError("outcome authorization requires ranking freeze")


@dataclass(frozen=True, slots=True)
class FailureFacts:
    progress: ExecutionProgressFacts
    conflicting: bool = False
    indeterminate: bool = False
    premature_outcome_access: bool = False
    shared_storage_failure: bool = False
    execution_infrastructure_failure: bool = False
    owner_terminated: bool = False
    owner_unavailable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.progress, ExecutionProgressFacts):
            raise TypeError("failure facts require governed execution progress")
        for name in self.__dataclass_fields__:
            if name != "progress":
                require_boolean(name, getattr(self, name))

    @property
    def classification(self) -> tuple[str, str]:
        return classify_failure(**{name: getattr(self, name) for name in self.__dataclass_fields__ if name != "progress"})


def validate_failure_evidence(value: Mapping[str, Any]) -> None:
    required = {
        "control_history", "failure_boundary", "failure_class",
        "last_durable_control_state", "normalized_failure_fact",
        "scientific_invalidity_established", "scientific_validity_established",
    }
    validate_exact_fields(value, required, label="failure control evidence")
    failure_class = require_string("failure_class", value["failure_class"])
    fact = require_string("normalized_failure_fact", value["normalized_failure_fact"])
    if failure_class not in FAILURE_FACTS or fact not in FAILURE_FACTS[failure_class]:
        raise ControlContractError("failure class/fact pair is not governed")
    if value["failure_boundary"] not in FAILURE_BOUNDARIES:
        raise ControlContractError("failure boundary is not governed")
    if value["last_durable_control_state"] not in {"ALLOCATED", "STARTED"}:
        raise ControlContractError("last durable state is invalid")
    if require_boolean("scientific_validity_established", value["scientific_validity_established"]):
        raise ControlContractError("FAILED cannot establish scientific validity")
    if require_boolean("scientific_invalidity_established", value["scientific_invalidity_established"]):
        raise ControlContractError("FAILED cannot establish scientific invalidity")
    history = value["control_history"]
    if not isinstance(history, Mapping):
        raise ControlContractError("failure control history must be an object")
    validate_exact_fields(
        history,
        {"common_prefix_record_identities", "control_history_kind", "observed_control_objects"},
        label="failure control history",
    )
    kind = history["control_history_kind"]
    if kind not in {"coherent", "conflicting"}:
        raise ControlContractError("control history kind is invalid")
    if fact == "conflicting_authoritative_control_records" and kind != "conflicting":
        raise ControlContractError("conflicting fact requires conflicting history")
    if fact != "conflicting_authoritative_control_records" and kind != "coherent":
        raise ControlContractError("non-conflicting fact requires coherent history")
    _validate_control_history_material(history)


def _validate_control_history_material(history: Mapping[str, Any]) -> None:
    prefixes = history["common_prefix_record_identities"]
    observed = history["observed_control_objects"]
    if not isinstance(prefixes, list) or len(set(prefixes)) != len(prefixes):
        raise ControlContractError("common-prefix identities must be a unique array")
    for identity in prefixes:
        require_sha256("common-prefix record identity", identity)
    if not isinstance(observed, list):
        raise ControlContractError("observed control objects must be an array")
    authority_sequences: list[int] = []
    for item in observed:
        if not isinstance(item, Mapping):
            raise ControlContractError("observed control object must be an object")
        kind = item.get("object_kind")
        if kind == "validated_control_record":
            validate_exact_fields(item, {"authority_sequence", "control_record_identity", "declared_control_sequence", "object_kind", "predecessor_control_record_identity"}, label="validated control history object")
            require_sha256("control record identity", item["control_record_identity"])
            require_integer("declared control sequence", item["declared_control_sequence"], minimum=1)
            _predecessor(item["predecessor_control_record_identity"])
        elif kind == "conflicting_control_slot":
            validate_exact_fields(item, {"authority_sequence", "normalized_slot_fact", "object_kind", "validated_records"}, label="conflicting control slot")
            fact = item["normalized_slot_fact"]
            records = item["validated_records"]
            if fact not in {"malformed_only", "duplicate_valid_record", "multiple_valid_records", "valid_and_malformed"} or not isinstance(records, list):
                raise ControlContractError("conflicting slot branch is invalid")
            required_count = {"malformed_only": (0, 0), "duplicate_valid_record": (1, 1), "multiple_valid_records": (2, None), "valid_and_malformed": (1, None)}[fact]
            if len(records) < required_count[0] or (required_count[1] is not None and len(records) > required_count[1]):
                raise ControlContractError("conflicting slot cardinality is invalid")
            identities: list[str] = []
            for entry in records:
                if not isinstance(entry, Mapping):
                    raise ControlContractError("validated slot entry must be an object")
                validate_exact_fields(entry, {"control_record_identity", "declared_control_sequence", "predecessor_control_record_identity"}, label="validated slot entry")
                identities.append(require_sha256("slot control record identity", entry["control_record_identity"]))
                require_integer("slot declared sequence", entry["declared_control_sequence"], minimum=1)
                _predecessor(entry["predecessor_control_record_identity"])
            if identities != sorted(identities) or len(set(identities)) != len(identities):
                raise ControlContractError("validated slot identities are not canonical")
        else:
            raise ControlContractError("observed control object kind is invalid")
        authority_sequences.append(require_integer("authority sequence", item["authority_sequence"], minimum=1))
    if authority_sequences != sorted(authority_sequences) or len(set(authority_sequences)) != len(authority_sequences):
        raise ControlContractError("authority sequences are not canonical and unique")


def _validate_no_live_owner(value: Mapping[str, Any]) -> None:
    validate_exact_fields(
        value,
        {"allocation_authority_identity", "no_live_owner_established", "recovery_component_identity", "recovery_operation", "recovery_policy_identity"},
        label="no-live-owner evidence",
    )
    require_sha256("allocation authority identity", value["allocation_authority_identity"])
    if require_boolean("no_live_owner_established", value["no_live_owner_established"]) is not True:
        raise ControlContractError("no-live-owner fact must be established")
    require_sha256("recovery component identity", value["recovery_component_identity"])
    if value["recovery_operation"] != "atomic_compare_no_live_owner_and_append_failed":
        raise ControlContractError("recovery operation is unsupported")
    require_sha256("recovery policy identity", value["recovery_policy_identity"])


def _validate_state(state: Mapping[str, Any]) -> None:
    control_state = state.get("control_state")
    if control_state == "STARTED":
        validate_exact_fields(state, {"control_state"}, label="STARTED state")
        return
    if control_state == "VALID":
        validate_exact_fields(state, {"control_state", "experiment_audit_manifest_identity", "experiment_audit_manifest_sha256"}, label="VALID state")
        require_sha256("experiment audit manifest identity", state["experiment_audit_manifest_identity"])
        require_sha256("experiment audit manifest sha256", state["experiment_audit_manifest_sha256"])
        return
    if control_state == "INVALID":
        validate_exact_fields(state, {"control_state", "governing_invalidity_evidence_identity", "governing_invalidity_evidence_sha256", "required_scientific_manifest_bindings"}, label="INVALID state")
        require_sha256("invalidity evidence identity", state["governing_invalidity_evidence_identity"])
        require_sha256("invalidity evidence sha256", state["governing_invalidity_evidence_sha256"])
        bindings = state["required_scientific_manifest_bindings"]
        if not isinstance(bindings, Sequence) or isinstance(bindings, (str, bytes)):
            raise ControlContractError("scientific manifest bindings must be an array")
        identifiers: list[str] = []
        for binding in bindings:
            if not isinstance(binding, Mapping):
                raise ControlContractError("scientific manifest binding must be an object")
            validate_exact_fields(binding, {"manifest_identifier", "manifest_identity", "manifest_sha256"}, label="scientific manifest binding")
            identifiers.append(require_string("manifest identifier", binding["manifest_identifier"]))
            require_sha256("manifest identity", binding["manifest_identity"])
            require_sha256("manifest sha256", binding["manifest_sha256"])
        if identifiers != sorted(identifiers) or len(set(identifiers)) != len(identifiers):
            raise ControlContractError("scientific manifest bindings are not canonical")
        return
    if control_state == "FAILED":
        validate_exact_fields(state, {"control_state", "failure_control_evidence", "no_live_owner_evidence", "recovery_mode"}, label="FAILED state")
        evidence = state["failure_control_evidence"]
        if not isinstance(evidence, Mapping):
            raise ControlContractError("failure evidence must be an object")
        validate_failure_evidence(evidence)
        if state["recovery_mode"] == "not_recovery_generated":
            if state["no_live_owner_evidence"] != "absent":
                raise ControlContractError("non-recovery FAILED must omit recovery evidence")
        elif state["recovery_mode"] == "recovery_no_live_owner_established":
            if not isinstance(state["no_live_owner_evidence"], Mapping):
                raise ControlContractError("recovery FAILED requires no-live-owner evidence")
            _validate_no_live_owner(state["no_live_owner_evidence"])
        else:
            raise ControlContractError("recovery mode is unsupported")
        return
    raise ControlContractError("control state is unsupported")


def _build_control_record(
    authority: ControlAuthority,
    *,
    sequence: int,
    predecessor: Mapping[str, Any],
    state: Mapping[str, Any],
) -> ControlRecord:
    sequence = require_integer("control sequence", sequence, minimum=1)
    predecessor_material = _predecessor(predecessor)
    if not isinstance(state, Mapping):
        raise ControlContractError("state must be an object")
    state_material = parse_canonical_bytes(canonical_bytes(dict(state)))
    _validate_state(state_material)
    material = {
        "allocation_receipt_identity": authority.allocation_receipt_identity,
        "attempt_control_record_identity": "",
        "attempt_identity": authority.attempt_identity,
        "attempt_kind": authority.attempt_kind,
        "external_input_snapshot_identities": list(authority.external_input_snapshot_identities),
        "launch_authority_snapshot_identity": authority.launch_authority_snapshot_identity,
        "ordinal": authority.ordinal,
        "predecessor_control_record_identity": predecessor_material,
        "profile_identity": authority.profile_identity,
        "readiness_identity": authority.readiness_identity,
        "readiness_seal_commit": authority.readiness_seal_commit,
        "remote_head_commit": authority.remote_head_commit,
        "schema_version": 1,
        "sequence": sequence,
        "source_commit": authority.source_commit,
        "state": state_material,
    }
    identity_material = dict(material)
    identity_material.pop("attempt_control_record_identity")
    identity = domain_identity(CONTROL_RECORD_DOMAIN, identity_material)
    material["attempt_control_record_identity"] = identity
    return ControlRecord(canonical_bytes(material), identity)


def build_control_record(authority: ControlAuthority, *, sequence: int,
                         predecessor: Mapping[str, Any], state: Mapping[str, Any]) -> ControlRecord:
    if isinstance(state, Mapping) and state.get("control_state") == "FAILED":
        raise ControlContractError("FAILED must be reconstructed from an authoritative snapshot")
    return _build_control_record(authority, sequence=sequence, predecessor=predecessor, state=state)


def validate_control_record(record: ControlRecord) -> None:
    material = record.material
    validate_exact_fields(material, {
        "allocation_receipt_identity", "attempt_control_record_identity", "attempt_identity", "attempt_kind",
        "external_input_snapshot_identities", "launch_authority_snapshot_identity", "ordinal",
        "predecessor_control_record_identity", "profile_identity", "readiness_identity", "readiness_seal_commit",
        "remote_head_commit", "schema_version", "sequence", "source_commit", "state",
    }, label="attempt control record")
    stored = require_sha256("attempt control record identity", material["attempt_control_record_identity"])
    identity_material = dict(material); identity_material.pop("attempt_control_record_identity")
    if domain_identity(CONTROL_RECORD_DOMAIN, identity_material) != stored or record.identity != stored:
        raise ControlContractError("control record identity does not reconstruct")
    ControlAuthority(
        material["allocation_receipt_identity"], material["attempt_identity"], material["attempt_kind"],
        tuple(material["external_input_snapshot_identities"]), material["launch_authority_snapshot_identity"],
        material["ordinal"], material["profile_identity"], material["readiness_identity"],
        material["readiness_seal_commit"], material["remote_head_commit"], material["source_commit"],
    )
    require_integer("sequence", material["sequence"], minimum=1)
    _predecessor(material["predecessor_control_record_identity"])
    _validate_state(material["state"])


@dataclass(frozen=True, slots=True)
class ControlSnapshot:
    observations: tuple[ControlStorageObservation, ...]
    records: tuple[ControlRecord, ...]
    common_prefix: tuple[ControlRecord, ...]
    snapshot_identity: str
    terminal_identity: str | None
    failure_history_canonical: bytes
    common_authority_canonical: bytes | None
    conflict_frontier_authority_sequence: int | None

    @property
    def failure_history_material(self) -> Mapping[str, Any]:
        """Return a fresh parsed copy of immutable failure-history authority."""
        return parse_canonical_bytes(self.failure_history_canonical)

    @property
    def is_conflicting(self) -> bool:
        return self.failure_history_material["control_history_kind"] == "conflicting"

    @property
    def last_durable_control_state(self) -> str:
        return self.common_prefix[-1].state if self.common_prefix else "ALLOCATED"

    @property
    def has_terminal_candidate(self) -> bool:
        return any(record.state in TERMINAL_STATES for record in self.records)

    @property
    def enumeration_complete(self) -> bool:
        """Whether authority-assigned storage slots form a complete prefix."""
        slots = {observation.authority_sequence for observation in self.observations}
        return not slots or slots == set(range(1, max(slots) + 1))


class IncompleteControlSnapshot(ControlContractError):
    pass


def _validate_recovery_snapshot_eligibility(snapshot: ControlSnapshot) -> None:
    """Enforce the frozen snapshot predicates required before recovery mutation."""
    validate_control_snapshot(snapshot)
    if not snapshot.enumeration_complete:
        raise IncompleteControlSnapshot("recovery requires complete authority enumeration")
    if snapshot.has_terminal_candidate:
        raise ControlContractError("FAILED cannot replace a terminal candidate")
    if snapshot.records and snapshot.common_authority_canonical is None:
        raise ControlContractError("recovery cannot select ambiguous common control authority")


def _slot_record_material(record: ControlRecord) -> dict[str, Any]:
    return {
        "control_record_identity": record.identity,
        "declared_control_sequence": record.sequence,
        "predecessor_control_record_identity": record.predecessor,
    }


def _canonical_observations(values: Sequence[ControlStorageObservation]) -> tuple[ControlStorageObservation, ...]:
    if isinstance(values, (str, bytes)):
        raise ControlContractError("control snapshot must be an observation sequence")
    result = tuple(values)
    if any(not isinstance(value, ControlStorageObservation) for value in result):
        raise TypeError("authoritative reconstruction requires explicit storage observations")
    return tuple(sorted(result, key=lambda item: (
        item.authority_sequence, item.malformed,
        item.record.identity if item.record is not None else "",
    )))


def reconstruct_control_history(values: Sequence[ControlStorageObservation]) -> ControlSnapshot:
    observations = _canonical_observations(values)
    assigned_slots = sorted({o.authority_sequence for o in observations})
    expected_slots = list(range(1, max(assigned_slots, default=0) + 1))
    missing_slots = sorted(set(expected_slots) - set(assigned_slots))
    by_slot: dict[int, list[ControlStorageObservation]] = {}
    for observation in observations:
        by_slot.setdefault(observation.authority_sequence, []).append(observation)
    entries = tuple((o.authority_sequence, o.record) for o in observations if o.record is not None)
    distinct_records = {record.identity: record for _, record in entries}
    all_records = tuple(sorted(distinct_records.values(), key=lambda record: (record.sequence, record.identity)))
    observed: list[dict[str, Any]] = []
    unique_by_slot: list[tuple[int, ControlRecord]] = []
    conflict_slots: list[int] = list(missing_slots)
    for slot in sorted(by_slot):
        slot_entries = by_slot[slot]
        records = [o.record for o in slot_entries if o.record is not None]
        malformed = any(o.malformed for o in slot_entries)
        counts: dict[str, int] = {}
        distinct: dict[str, ControlRecord] = {}
        for record in records:
            counts[record.identity] = counts.get(record.identity, 0) + 1
            distinct[record.identity] = record
        if len(slot_entries) == 1 and len(distinct) == 1 and not malformed:
            record = next(iter(distinct.values()))
            observed.append({"authority_sequence": slot, "object_kind": "validated_control_record", **_slot_record_material(record)})
            unique_by_slot.append((slot, record))
            continue
        conflict_slots.append(slot)
        if malformed and distinct:
            fact = "valid_and_malformed"
        elif malformed:
            fact = "malformed_only"
        elif len(distinct) == 1 and any(count > 1 for count in counts.values()):
            fact = "duplicate_valid_record"
        else:
            fact = "multiple_valid_records"
        observed.append({"authority_sequence": slot, "normalized_slot_fact": fact,
                         "object_kind": "conflicting_control_slot",
                         "validated_records": [_slot_record_material(distinct[i]) for i in sorted(distinct)]})
    slots_by_identity: dict[str, list[int]] = {}
    for slot, record in entries:
        slots_by_identity.setdefault(record.identity, []).append(slot)
    for slots in slots_by_identity.values():
        if len(slots) > 1:
            conflict_slots.append(min(slots))
    by_declared: dict[int, list[tuple[int, ControlRecord]]] = {}
    by_predecessor: dict[str, list[tuple[int, ControlRecord]]] = {}
    roots: list[tuple[int, ControlRecord]] = []
    record_slots = {identity: min(slots) for identity, slots in slots_by_identity.items()}
    graph_records = tuple(sorted(((record_slots[identity], record) for identity, record in distinct_records.items()),
                                 key=lambda item: (item[0], item[1].identity)))
    for slot, record in graph_records:
        by_declared.setdefault(record.sequence, []).append((slot, record))
        predecessor = record.predecessor
        if predecessor == {"status": "absent"}:
            roots.append((slot, record))
        else:
            predecessor_identity = predecessor["identity"]
            by_predecessor.setdefault(predecessor_identity, []).append((slot, record))
            if predecessor_identity not in distinct_records:
                conflict_slots.append(slot)
        if (record.sequence == 1) != (predecessor == {"status": "absent"}):
            conflict_slots.append(slot)
        if record.sequence == 1 and record.state not in {"STARTED", "FAILED"}:
            conflict_slots.append(slot)
        if record.sequence > 1 and record.state == "STARTED":
            conflict_slots.append(slot)
    for group in by_declared.values():
        if len(group) > 1:
            conflict_slots.append(min(slot for slot, _ in group))
    for group in by_predecessor.values():
        if len(group) > 1:
            conflict_slots.append(min(slot for slot, _ in group))
    if len(roots) != 1 and all_records:
        conflict_slots.append(min(slot for slot, _ in (roots or graph_records)))
    terminal_entries = [(min(slots_by_identity[r.identity]), r) for r in all_records if r.state in TERMINAL_STATES]
    if len(terminal_entries) > 1:
        conflict_slots.append(min(slot for slot, _ in terminal_entries))
    for slot, terminal in terminal_entries:
        if by_predecessor.get(terminal.identity):
            conflict_slots.append(slot)
    authority_values = {canonical_bytes(record.authority_material) for record in all_records}
    common_authority = next(iter(authority_values)) if len(authority_values) == 1 else None
    if len(authority_values) > 1:
        root_authority = canonical_bytes(roots[0][1].authority_material) if len(roots) == 1 else None
        differing = [slot for slot, record in graph_records if root_authority is None or canonical_bytes(record.authority_material) != root_authority]
        conflict_slots.append(min(differing or [slot for slot, _ in graph_records]))
    # A cycle has no unique root-origin interpretation; retain its earliest participant.
    for identity, record in distinct_records.items():
        seen: list[str] = []
        cursor = record
        while cursor.predecessor.get("status") == "known":
            predecessor_identity = cursor.predecessor["identity"]
            if predecessor_identity in seen:
                cycle = seen[seen.index(predecessor_identity):] + [predecessor_identity]
                conflict_slots.append(min(record_slots[item] for item in cycle))
                break
            seen.append(predecessor_identity)
            if predecessor_identity not in distinct_records:
                break
            cursor = distinct_records[predecessor_identity]
    conflict_frontier = min(conflict_slots) if conflict_slots else None
    prefix: list[ControlRecord] = []
    if len(roots) == 1:
        slot, current = roots[0]
        while conflict_frontier is None or slot < conflict_frontier:
            if current.sequence != len(prefix) + 1:
                break
            prefix.append(current)
            successors = by_predecessor.get(current.identity, [])
            if len(successors) != 1 or current.state in TERMINAL_STATES:
                break
            slot, current = successors[0]
    coherent = conflict_frontier is None and len(prefix) == len(all_records)
    history = {"common_prefix_record_identities": [r.identity for r in prefix],
               "control_history_kind": "coherent" if coherent else "conflicting",
               "observed_control_objects": observed}
    _validate_control_history_material(history)
    snapshot_identity = domain_identity(CONTROL_SNAPSHOT_DOMAIN, {"control_history": history})
    terminal = prefix[-1].identity if coherent and prefix and prefix[-1].state in TERMINAL_STATES else None
    return ControlSnapshot(observations, all_records, tuple(prefix), snapshot_identity, terminal,
                           canonical_bytes(history), common_authority, conflict_frontier)


def validate_control_snapshot(snapshot: ControlSnapshot) -> None:
    if not isinstance(snapshot, ControlSnapshot):
        raise TypeError("control snapshot has an unsupported type")
    expected = reconstruct_control_history(snapshot.observations)
    if (
        snapshot.snapshot_identity != expected.snapshot_identity
        or snapshot.terminal_identity != expected.terminal_identity
        or snapshot.failure_history_canonical != expected.failure_history_canonical
        or snapshot.common_authority_canonical != expected.common_authority_canonical
        or snapshot.conflict_frontier_authority_sequence != expected.conflict_frontier_authority_sequence
    ):
        raise ControlContractError("control snapshot does not reconstruct")


def classify_failure(*, conflicting: bool = False, indeterminate: bool = False,
                     premature_outcome_access: bool = False, shared_storage_failure: bool = False,
                     execution_infrastructure_failure: bool = False,
                     owner_terminated: bool = False, owner_unavailable: bool = False) -> tuple[str, str]:
    if conflicting:
        return "ambiguous_state", "conflicting_authoritative_control_records"
    if indeterminate:
        return "ambiguous_state", "indeterminate_authoritative_control_state"
    if premature_outcome_access:
        return "validity_not_established", "premature_outcome_access"
    if shared_storage_failure:
        return "infrastructure_failure", "shared_control_storage_failure"
    if execution_infrastructure_failure:
        return "infrastructure_failure", "execution_infrastructure_failure"
    if owner_terminated:
        return "interruption", "governed_owner_terminated"
    if owner_unavailable:
        return "interruption", "governed_owner_unavailable"
    return "validity_not_established", "terminal_scientific_authority_not_established"


class AppendDisposition(str, Enum):
    COMMITTED = "committed"
    STALE = "stale_snapshot"
    UNAVAILABLE = "authority_unavailable"
    AMBIGUOUS = "ambiguous_completion"


@dataclass(frozen=True, slots=True)
class AppendResult:
    disposition: AppendDisposition
    record: ControlRecord | None


@dataclass(frozen=True, slots=True)
class RecoveryAuthority:
    allocation_authority_identity: str
    attempt_identity: str
    recovery_component_identity: str
    recovery_policy_identity: str
    snapshot_identity: str

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            require_sha256(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class RecoveryPrerequisiteAuthority:
    """Independently selected committed authority, outside recovery evidence."""

    allocation_authority_identity: str
    attempt_identity: str
    control_storage_contract_identity: str
    recovery_component_identity: str
    recovery_policy_identity: str
    expected_snapshot_identity: str

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            require_sha256(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class AppendOperation:
    expected_snapshot: ControlSnapshot
    proposed_observation: ControlStorageObservation
    control_authority: ControlAuthority | None = None
    facts: FailureFacts | None = None

    def __post_init__(self) -> None:
        validate_control_snapshot(self.expected_snapshot)
        if self.expected_snapshot.is_conflicting or self.expected_snapshot.terminal_identity is not None:
            raise ControlContractError("append requires a coherent nonterminal snapshot")
        if self.proposed_observation.malformed or self.proposed_observation.record is None:
            raise ControlContractError("append requires one validated control record")
        expected_slot = max((item.authority_sequence for item in self.expected_snapshot.observations), default=0) + 1
        if self.proposed_observation.authority_sequence != expected_slot:
            raise ControlContractError("proposed authority slot is not the unique successor slot")
        record = self.proposed_observation.record
        validate_control_record(record)
        prospective = reconstruct_control_history((*self.expected_snapshot.observations, self.proposed_observation))
        if prospective.is_conflicting or prospective.common_prefix != (*self.expected_snapshot.common_prefix, record):
            raise ControlContractError("proposed record is not the unique coherent successor")
        if record.state == "FAILED":
            if self.control_authority is None or self.facts is None:
                raise ControlContractError("FAILED append lacks reconstruction authority")
            if record.authority_material != self.control_authority.material:
                raise ControlContractError("FAILED record binds another common control authority")
            if record.material["state"]["failure_control_evidence"] != _failure_evidence(self.expected_snapshot, self.facts):
                raise ControlContractError("FAILED evidence does not reconstruct from snapshot and facts")
        elif self.control_authority is not None or self.facts is not None:
            raise ControlContractError("non-FAILED append must not carry failure authority")

    @property
    def record(self) -> ControlRecord:
        assert self.proposed_observation.record is not None
        return self.proposed_observation.record


@dataclass(frozen=True, slots=True)
class RecoveryOperation:
    expected_snapshot: ControlSnapshot
    control_authority: ControlAuthority
    facts: FailureFacts
    prerequisite_authority: RecoveryPrerequisiteAuthority
    no_live_owner_authority: RecoveryAuthority
    proposed_observation: ControlStorageObservation

    def __post_init__(self) -> None:
        _validate_recovery_snapshot_eligibility(self.expected_snapshot)
        if self.proposed_observation.malformed or self.proposed_observation.record is None:
            raise ControlContractError("recovery requires one validated FAILED observation")
        expected_slot = max((item.authority_sequence for item in self.expected_snapshot.observations), default=0) + 1
        if self.proposed_observation.authority_sequence != expected_slot:
            raise ControlContractError("recovery authority slot is not the unique successor slot")
        failed_record = self.proposed_observation.record
        validate_control_record(failed_record)
        if failed_record.state != "FAILED":
            raise ControlContractError("recovery requires an exact FAILED candidate")
        expected_sequence = max((record.sequence for record in self.expected_snapshot.records), default=0) + 1
        if failed_record.sequence != expected_sequence:
            raise ControlContractError("recovery FAILED sequence does not reconstruct")
        prerequisite = self.prerequisite_authority
        evidence_authority = self.no_live_owner_authority
        if prerequisite.expected_snapshot_identity != self.expected_snapshot.snapshot_identity:
            raise ControlContractError("recovery prerequisite binds another snapshot")
        if evidence_authority.snapshot_identity != self.expected_snapshot.snapshot_identity:
            raise ControlContractError("recovery authority binds another snapshot")
        if prerequisite.attempt_identity != evidence_authority.attempt_identity:
            raise ControlContractError("recovery evidence binds another attempt")
        if evidence_authority.attempt_identity != failed_record.material["attempt_identity"]:
            raise ControlContractError("recovery authority binds another attempt")
        if failed_record.authority_material != self.control_authority.material:
            raise ControlContractError("recovery record binds another common control authority")
        if self.expected_snapshot.records and self.expected_snapshot.common_authority_canonical is None:
            raise ControlContractError("recovery cannot select ambiguous common control authority")
        if self.expected_snapshot.common_authority_canonical is not None and self.expected_snapshot.common_authority_canonical != canonical_bytes(self.control_authority.material):
            raise ControlContractError("recovery control authority differs from committed history")
        for name in ("allocation_authority_identity", "recovery_component_identity", "recovery_policy_identity"):
            if getattr(prerequisite, name) != getattr(evidence_authority, name):
                raise ControlContractError(f"recovery evidence differs from prerequisite {name}")
        state = failed_record.material["state"]
        if state["failure_control_evidence"] != _failure_evidence(self.expected_snapshot, self.facts):
            raise ControlContractError("FAILED evidence does not reconstruct from snapshot and facts")
        expected_predecessor = {"status": "absent"} if self.expected_snapshot.is_conflicting or not self.expected_snapshot.common_prefix else {
            "identity": self.expected_snapshot.common_prefix[-1].identity, "status": "known"}
        if failed_record.predecessor != expected_predecessor:
            raise ControlContractError("recovery predecessor does not reconstruct")
        evidence = failed_record.material["state"]["no_live_owner_evidence"]
        if not isinstance(evidence, Mapping):
            raise ControlContractError("recovery operation lacks no-live-owner evidence")
        expected = {
            "allocation_authority_identity": prerequisite.allocation_authority_identity,
            "no_live_owner_established": True,
            "recovery_component_identity": prerequisite.recovery_component_identity,
            "recovery_operation": "atomic_compare_no_live_owner_and_append_failed",
            "recovery_policy_identity": prerequisite.recovery_policy_identity,
        }
        if dict(evidence) != expected:
            raise ControlContractError("no-live-owner evidence is not cross-bound")

    @property
    def failed_record(self) -> ControlRecord:
        assert self.proposed_observation.record is not None
        return self.proposed_observation.record


@runtime_checkable
class AtomicControlStoragePort(Protocol):
    def read_snapshot(self, attempt_identity: str) -> ControlSnapshot: ...
    def compare_and_append(self, operation: AppendOperation) -> AppendResult: ...
    def compare_fence_no_live_owner_and_append_failed(self, operation: RecoveryOperation) -> AppendResult: ...


def _failure_evidence(snapshot: ControlSnapshot, facts: FailureFacts) -> dict[str, Any]:
    failure_class, normalized_fact = facts.classification
    if snapshot.is_conflicting != (normalized_fact == "conflicting_authoritative_control_records"):
        raise ControlContractError("failure fact does not match normalized snapshot")
    if normalized_fact in {
        "shared_control_storage_failure",
        "terminal_scientific_authority_not_established",
    }:
        boundary = "terminalization"
    elif facts.progress.terminalization_started:
        boundary = "terminalization"
    elif facts.progress.outcome_authorized:
        boundary = "post_authorization_pre_terminal"
    elif facts.progress.ranking_frozen:
        boundary = "post_ranking_freeze_pre_authorization"
    elif snapshot.last_durable_control_state == "STARTED":
        boundary = "post_start_pre_ranking_freeze"
    else:
        boundary = "post_allocation_pre_start"
    return {
        "control_history": snapshot.failure_history_material,
        "failure_boundary": boundary,
        "failure_class": failure_class,
        "last_durable_control_state": snapshot.last_durable_control_state,
        "normalized_failure_fact": normalized_fact,
        "scientific_invalidity_established": False,
        "scientific_validity_established": False,
    }


def build_failed_record(authority: ControlAuthority, snapshot: ControlSnapshot, facts: FailureFacts,
                        *, recovery_prerequisite: RecoveryPrerequisiteAuthority | None = None,
                        no_live_owner_authority: RecoveryAuthority | None = None) -> ControlRecord:
    validate_control_snapshot(snapshot)
    if snapshot.has_terminal_candidate:
        raise ControlContractError("FAILED cannot replace a terminal candidate")
    if snapshot.common_authority_canonical is not None and snapshot.common_authority_canonical != canonical_bytes(authority.material):
        raise ControlContractError("FAILED authority differs from snapshot")
    if recovery_prerequisite is None and no_live_owner_authority is None:
        if snapshot.is_conflicting:
            raise ControlContractError("conflicting failure requires governed recovery")
        mode: object = "absent"
        recovery_mode = "not_recovery_generated"
    else:
        if recovery_prerequisite is None or no_live_owner_authority is None:
            raise ControlContractError("recovery requires prerequisite and no-live-owner authority")
        _validate_recovery_snapshot_eligibility(snapshot)
        if recovery_prerequisite.attempt_identity != authority.attempt_identity or recovery_prerequisite.expected_snapshot_identity != snapshot.snapshot_identity:
            raise ControlContractError("recovery prerequisite does not bind expected control authority")
        if no_live_owner_authority.attempt_identity != authority.attempt_identity or no_live_owner_authority.snapshot_identity != snapshot.snapshot_identity:
            raise ControlContractError("recovery authority does not bind expected control authority")
        for name in ("allocation_authority_identity", "recovery_component_identity", "recovery_policy_identity"):
            if getattr(recovery_prerequisite, name) != getattr(no_live_owner_authority, name):
                raise ControlContractError(f"recovery authority differs from prerequisite {name}")
        mode = {"allocation_authority_identity": recovery_prerequisite.allocation_authority_identity,
                "no_live_owner_established": True,
                "recovery_component_identity": recovery_prerequisite.recovery_component_identity,
                "recovery_operation": "atomic_compare_no_live_owner_and_append_failed",
                "recovery_policy_identity": recovery_prerequisite.recovery_policy_identity}
        recovery_mode = "recovery_no_live_owner_established"
    predecessor = {"status": "absent"} if snapshot.is_conflicting or not snapshot.common_prefix else {
        "identity": snapshot.common_prefix[-1].identity, "status": "known"}
    sequence = max((record.sequence for record in snapshot.records), default=0) + 1
    return _build_control_record(authority, sequence=sequence, predecessor=predecessor,
        state={"control_state": "FAILED", "failure_control_evidence": _failure_evidence(snapshot, facts),
               "no_live_owner_evidence": mode, "recovery_mode": recovery_mode})


def append_record(backend: AtomicControlStoragePort, snapshot: ControlSnapshot, record: ControlRecord) -> ControlRecord:
    validate_control_snapshot(snapshot)
    validate_control_record(record)
    if record.state == "FAILED":
        raise ControlContractError("FAILED append requires snapshot-derived failure operation")
    if snapshot.is_conflicting:
        raise ControlHistoryConflict("ordinary append cannot select a conflict branch")
    successor = ControlStorageObservation(max((item.authority_sequence for item in snapshot.observations), default=0) + 1, record)
    operation = AppendOperation(snapshot, successor)
    result = backend.compare_and_append(operation)
    if result.disposition is AppendDisposition.COMMITTED and result.record == record:
        return record
    if result.disposition is AppendDisposition.STALE:
        raise StaleControlSnapshot("control snapshot changed before append")
    raise ControlContractError("control append was not durably confirmed")


def append_failed(backend: AtomicControlStoragePort, snapshot: ControlSnapshot,
                  authority: ControlAuthority, facts: FailureFacts) -> ControlRecord:
    failed_record = build_failed_record(authority, snapshot, facts)
    successor = ControlStorageObservation(max((item.authority_sequence for item in snapshot.observations), default=0) + 1, failed_record)
    operation = AppendOperation(snapshot, successor, authority, facts)
    result = backend.compare_and_append(operation)
    if result.disposition is AppendDisposition.COMMITTED and result.record == failed_record:
        return failed_record
    if result.disposition is AppendDisposition.STALE:
        raise StaleControlSnapshot("control snapshot changed before FAILED append")
    raise ControlContractError("FAILED append was not durably confirmed")


def recover_failed(backend: AtomicControlStoragePort, snapshot: ControlSnapshot, authority: ControlAuthority,
                   facts: FailureFacts, recovery_prerequisite: RecoveryPrerequisiteAuthority,
                   no_live_owner_authority: RecoveryAuthority) -> ControlRecord:
    validate_control_snapshot(snapshot)
    failed_record = build_failed_record(authority, snapshot, facts,
        recovery_prerequisite=recovery_prerequisite,
        no_live_owner_authority=no_live_owner_authority)
    successor = ControlStorageObservation(max((item.authority_sequence for item in snapshot.observations), default=0) + 1, failed_record)
    operation = RecoveryOperation(snapshot, authority, facts, recovery_prerequisite,
                                  no_live_owner_authority, successor)
    result = backend.compare_fence_no_live_owner_and_append_failed(operation)
    if result.disposition is AppendDisposition.COMMITTED and result.record == failed_record:
        return failed_record
    if result.disposition is AppendDisposition.STALE:
        raise StaleControlSnapshot("control snapshot changed during recovery")
    raise ControlContractError("no-live-owner recovery was not durably confirmed")


__all__ = [
    "AppendDisposition", "AppendOperation", "AppendResult", "AtomicControlStoragePort",
    "ControlAuthority", "ControlContractError", "ControlHistoryConflict", "ControlRecord",
    "ControlSnapshot", "ControlStorageObservation", "ExecutionProgressFacts", "FailureFacts",
    "IncompleteControlSnapshot", "RecoveryAuthority", "RecoveryOperation",
    "RecoveryPrerequisiteAuthority", "StaleControlSnapshot", "append_failed", "append_record",
    "build_control_record", "build_failed_record", "classify_failure", "reconstruct_control_history",
    "recover_failed", "validate_control_record", "validate_control_snapshot", "validate_failure_evidence",
]
