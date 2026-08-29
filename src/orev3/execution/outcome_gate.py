"""Non-operational outcome-gate semantics for readiness v1.1.

This module owns no configured authority or outcome source. A lifecycle-bound
session receives independently selected contract and ranking validators and may
issue exactly one process-local, non-copyable evaluation capability.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import threading
from typing import Any, Protocol, runtime_checkable

from orev3.execution.canonical import (
    CanonicalControlError, canonical_bytes, domain_identity, parse_canonical_bytes,
    require_boolean, require_git_object, require_integer, require_sha256,
    validate_exact_fields,
)

OUTCOME_AUTHORIZATION_DOMAIN = "orev3:experiment-outcome-authorization:v1\n"
OUTCOME_AWARE_PROFILE = "outcome_aware_v1"


class OutcomeGateError(CanonicalControlError):
    pass


def _git(name: str, value: object) -> str:
    kind = "sha256" if isinstance(value, str) and len(value) == 64 else "sha1"
    return require_git_object(name, value, kind)


@dataclass(frozen=True, slots=True)
class RankingAuthority:
    attempt_identity: str
    dataset_identity: str
    external_input_snapshot_identities: tuple[str, ...]
    outcome_blind_provenance_identity: str
    profile_identity: str
    ranking_artifact_identity: str
    ranking_contract_identity: str
    ranking_freeze_component_identity: str
    ranking_freeze_contract_identity: str
    ranking_reconstruction_component_identity: str
    replay_identity: str

    def __post_init__(self) -> None:
        for name in (
            "attempt_identity", "dataset_identity", "outcome_blind_provenance_identity",
            "profile_identity", "ranking_artifact_identity", "ranking_contract_identity",
            "ranking_freeze_component_identity", "ranking_freeze_contract_identity",
            "ranking_reconstruction_component_identity", "replay_identity",
        ):
            require_sha256(name, getattr(self, name))
        if not isinstance(self.external_input_snapshot_identities, tuple):
            raise OutcomeGateError("external input snapshot identities must be a tuple")
        if len(set(self.external_input_snapshot_identities)) != len(self.external_input_snapshot_identities):
            raise OutcomeGateError("external input snapshot identities must be unique")
        for identity in self.external_input_snapshot_identities:
            require_sha256("external input snapshot identity", identity)


@dataclass(frozen=True, slots=True)
class RankingCandidate:
    """Untrusted scientific output returned by the ranking worker."""

    raw: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.raw, bytes) or not self.raw:
            raise OutcomeGateError("ranking candidate bytes are unavailable")


@dataclass(frozen=True, slots=True)
class RankingContextAuthority:
    """Independently selected ranking context, before artifact construction."""

    attempt_identity: str
    dataset_identity: str
    external_input_snapshot_identities: tuple[str, ...]
    outcome_blind_provenance_identity: str
    profile_identity: str
    ranking_contract_identity: str
    ranking_freeze_component_identity: str
    ranking_freeze_contract_identity: str
    ranking_reconstruction_component_identity: str
    replay_identity: str

    def __post_init__(self) -> None:
        RankingAuthority(
            self.attempt_identity, self.dataset_identity,
            self.external_input_snapshot_identities,
            self.outcome_blind_provenance_identity, self.profile_identity,
            "0" * 64, self.ranking_contract_identity, self.ranking_freeze_component_identity,
            self.ranking_freeze_contract_identity, self.ranking_reconstruction_component_identity,
            self.replay_identity,
        )


@dataclass(frozen=True, slots=True)
class RankingFreezeResult:
    """Authority returned only by an independently selected freeze port."""

    ranking_authority: RankingAuthority
    ranking_byte_count: int
    ranking_sha256: str
    frozen_reference_identity: str

    def __post_init__(self) -> None:
        if not isinstance(self.ranking_authority, RankingAuthority):
            raise TypeError("ranking freeze requires RankingAuthority")
        require_integer("ranking byte count", self.ranking_byte_count, minimum=1)
        require_sha256("ranking sha256", self.ranking_sha256)
        require_sha256("frozen ranking reference identity", self.frozen_reference_identity)


@runtime_checkable
class IndependentRankingFreezePort(Protocol):
    @property
    def freeze_component_identity(self) -> str: ...

    @property
    def reconstruction_component_identity(self) -> str: ...

    def freeze_and_reconstruct(
        self, candidate: RankingCandidate, expected: RankingContextAuthority
    ) -> RankingFreezeResult: ...

    def read_and_reconstruct(self, freeze: RankingFreezeResult) -> tuple[bytes, RankingAuthority]: ...


@runtime_checkable
class AuthorizationContractAuthority(Protocol):
    @property
    def component_identity(self) -> str: ...

    def reconstruct_authorization_contract(self, readiness_identity: str, profile_identity: str) -> str: ...


@runtime_checkable
class SealedOutcomeOpener(Protocol):
    def open_authorized_outcome(self, outcome_source_identity: str) -> object: ...


@dataclass(frozen=True, slots=True)
class OutcomeGatePrerequisiteAuthority:
    authorization_contract_component_identity: str
    authorization_contract_identity: str
    attempt_identity: str
    dataset_identity: str
    external_input_snapshot_identities: tuple[str, ...]
    launch_authority_snapshot_identity: str
    outcome_blind_provenance_identity: str
    outcome_source_identity: str
    profile_identity: str
    profile_name: str
    ranking_contract_identity: str
    ranking_freeze_component_identity: str
    ranking_freeze_contract_identity: str
    ranking_reconstruction_component_identity: str
    readiness_identity: str
    readiness_seal_commit: str
    replay_identity: str
    source_commit: str

    def __post_init__(self) -> None:
        for name in (
            "authorization_contract_component_identity", "authorization_contract_identity",
            "attempt_identity", "dataset_identity",
            "launch_authority_snapshot_identity", "outcome_blind_provenance_identity",
            "outcome_source_identity", "profile_identity", "ranking_contract_identity",
            "ranking_freeze_component_identity", "ranking_freeze_contract_identity",
            "ranking_reconstruction_component_identity", "readiness_identity", "replay_identity",
        ):
            require_sha256(name, getattr(self, name))
        if not isinstance(self.external_input_snapshot_identities, tuple):
            raise OutcomeGateError("gate input snapshot identities must be a tuple")
        if len(set(self.external_input_snapshot_identities)) != len(self.external_input_snapshot_identities):
            raise OutcomeGateError("gate input snapshot identities must be unique")
        for identity in self.external_input_snapshot_identities:
            require_sha256("gate input snapshot identity", identity)
        if self.profile_name != OUTCOME_AWARE_PROFILE:
            raise OutcomeGateError("profile has no outcome-authorization route")
        _git("readiness_seal_commit", self.readiness_seal_commit)
        _git("source_commit", self.source_commit)


_AUTHORIZATION_FIELDS = {
    "attempt_identity", "dataset_identity", "external_input_snapshot_identities",
    "frozen_ranking_artifact_identity", "launch_authority_snapshot_identity",
    "non_replayable", "outcome_authorization_identity",
    "outcome_blind_provenance_identity", "outcome_source_identity",
    "profile_identity", "ranking_contract_identity", "readiness_identity",
    "readiness_seal_commit", "replay_identity", "schema_version", "source_commit",
}


def _validate_authorization_material(value: dict[str, Any]) -> None:
    validate_exact_fields(value, _AUTHORIZATION_FIELDS, label="outcome authorization")
    stored = require_sha256("outcome authorization identity", value["outcome_authorization_identity"])
    identity_material = dict(value)
    identity_material.pop("outcome_authorization_identity")
    if domain_identity(OUTCOME_AUTHORIZATION_DOMAIN, identity_material) != stored:
        raise OutcomeGateError("outcome authorization identity does not reconstruct")
    for name in (
        "attempt_identity", "dataset_identity", "frozen_ranking_artifact_identity",
        "launch_authority_snapshot_identity", "outcome_blind_provenance_identity",
        "outcome_source_identity", "profile_identity", "ranking_contract_identity",
        "readiness_identity", "replay_identity",
    ):
        require_sha256(name, value[name])
    snapshots = value["external_input_snapshot_identities"]
    if not isinstance(snapshots, list) or len(set(snapshots)) != len(snapshots):
        raise OutcomeGateError("external input snapshot identities are not canonical")
    for identity in snapshots:
        require_sha256("external input snapshot identity", identity)
    if require_boolean("non_replayable", value["non_replayable"]) is not True:
        raise OutcomeGateError("outcome authorization must be non-replayable")
    if require_integer("schema_version", value["schema_version"], minimum=1) != 1:
        raise OutcomeGateError("outcome authorization schema is unsupported")
    _git("readiness_seal_commit", value["readiness_seal_commit"])
    _git("source_commit", value["source_commit"])


@dataclass(frozen=True, slots=True)
class OutcomeAuthorization:
    canonical: bytes
    identity: str

    def __post_init__(self) -> None:
        material = parse_canonical_bytes(self.canonical, validator=_validate_authorization_material)
        if material["outcome_authorization_identity"] != require_sha256("identity", self.identity):
            raise OutcomeGateError("authorization object and stored identity differ")

    @property
    def material(self) -> dict[str, Any]:
        return parse_canonical_bytes(self.canonical, validator=_validate_authorization_material)

    @classmethod
    def from_canonical(cls, raw: bytes) -> "OutcomeAuthorization":
        material = parse_canonical_bytes(raw, validator=_validate_authorization_material)
        return cls(raw, material["outcome_authorization_identity"])


def build_outcome_authorization(prerequisite: OutcomeGatePrerequisiteAuthority,
                                ranking: RankingAuthority) -> OutcomeAuthorization:
    expected = (
        ("attempt", ranking.attempt_identity, prerequisite.attempt_identity),
        ("dataset", ranking.dataset_identity, prerequisite.dataset_identity),
        ("input snapshots", ranking.external_input_snapshot_identities, prerequisite.external_input_snapshot_identities),
        ("outcome-blind provenance", ranking.outcome_blind_provenance_identity, prerequisite.outcome_blind_provenance_identity),
        ("profile", ranking.profile_identity, prerequisite.profile_identity),
        ("ranking contract", ranking.ranking_contract_identity, prerequisite.ranking_contract_identity),
        ("ranking freeze component", ranking.ranking_freeze_component_identity,
         prerequisite.ranking_freeze_component_identity),
        ("ranking freeze contract", ranking.ranking_freeze_contract_identity, prerequisite.ranking_freeze_contract_identity),
        ("ranking reconstruction component", ranking.ranking_reconstruction_component_identity,
         prerequisite.ranking_reconstruction_component_identity),
        ("Replay", ranking.replay_identity, prerequisite.replay_identity),
    )
    for label, actual, governed in expected:
        if actual != governed:
            raise OutcomeGateError(f"ranking {label} differs from gate authority")
    material: dict[str, Any] = {
        "attempt_identity": ranking.attempt_identity,
        "dataset_identity": ranking.dataset_identity,
        "external_input_snapshot_identities": list(ranking.external_input_snapshot_identities),
        "frozen_ranking_artifact_identity": ranking.ranking_artifact_identity,
        "launch_authority_snapshot_identity": prerequisite.launch_authority_snapshot_identity,
        "non_replayable": True,
        "outcome_blind_provenance_identity": ranking.outcome_blind_provenance_identity,
        "outcome_source_identity": prerequisite.outcome_source_identity,
        "profile_identity": prerequisite.profile_identity,
        "ranking_contract_identity": ranking.ranking_contract_identity,
        "readiness_identity": prerequisite.readiness_identity,
        "readiness_seal_commit": prerequisite.readiness_seal_commit,
        "replay_identity": ranking.replay_identity,
        "schema_version": 1,
        "source_commit": prerequisite.source_commit,
    }
    identity = domain_identity(OUTCOME_AUTHORIZATION_DOMAIN, material)
    material["outcome_authorization_identity"] = identity
    return OutcomeAuthorization(canonical_bytes(material), identity)


def validate_outcome_gate_authority(
    prerequisite: OutcomeGatePrerequisiteAuthority,
    freeze: RankingFreezeResult,
    opener: SealedOutcomeOpener,
    contract: AuthorizationContractAuthority,
    freeze_port: IndependentRankingFreezePort,
) -> RankingAuthority:
    """Validate gate inputs; capability issuance remains orchestrator-owned."""

    if not isinstance(prerequisite, OutcomeGatePrerequisiteAuthority):
        raise TypeError("gate validation lacks prerequisite authority")
    if not isinstance(freeze, RankingFreezeResult) or not isinstance(opener, SealedOutcomeOpener):
        raise TypeError("gate validation lacks frozen ranking or sealed opener")
    if not isinstance(contract, AuthorizationContractAuthority) \
            or not isinstance(freeze_port, IndependentRankingFreezePort):
        raise TypeError("gate validation lacks governed implementations")
    if contract.component_identity != prerequisite.authorization_contract_component_identity:
        raise OutcomeGateError("authorization-contract component differs from prerequisite authority")
    if freeze_port.freeze_component_identity != prerequisite.ranking_freeze_component_identity:
        raise OutcomeGateError("ranking-freeze component differs from prerequisite authority")
    if freeze_port.reconstruction_component_identity != prerequisite.ranking_reconstruction_component_identity:
        raise OutcomeGateError("ranking reconstruction component differs from prerequisite authority")
    reconstructed_contract = contract.reconstruct_authorization_contract(
        prerequisite.readiness_identity, prerequisite.profile_identity
    )
    if require_sha256(
        "reconstructed authorization contract", reconstructed_contract
    ) != prerequisite.authorization_contract_identity:
        raise OutcomeGateError("authorization contract differs from readiness/profile authority")
    raw, ranking = freeze_port.read_and_reconstruct(freeze)
    if not isinstance(raw, bytes) or len(raw) != freeze.ranking_byte_count \
            or hashlib.sha256(raw).hexdigest() != freeze.ranking_sha256:
        raise OutcomeGateError("frozen ranking bytes do not reconstruct")
    if ranking != freeze.ranking_authority:
        raise OutcomeGateError("frozen ranking authority does not reconstruct")
    return ranking


def _build_evaluation_broker():
    """Create one lexical gate-owned issuance and consumption boundary."""

    entries: dict[object, dict[str, object]] = {}
    issued_lifecycles: set[object] = set()
    issued_authorizations: set[str] = set()
    lock = threading.Lock()

    def issue(
        lifecycle: object, authorization: OutcomeAuthorization,
        freeze: RankingFreezeResult, freeze_port: IndependentRankingFreezePort,
        opener: SealedOutcomeOpener,
    ) -> "EvaluationCapability":
        if not isinstance(authorization, OutcomeAuthorization) \
                or not isinstance(freeze, RankingFreezeResult) \
                or not isinstance(freeze_port, IndependentRankingFreezePort) \
                or not isinstance(opener, SealedOutcomeOpener):
            raise OutcomeGateError("evaluation issuance lacks governed authority")
        from orev3.execution.orchestrator import OfficialOrchestrator

        if type(lifecycle) is not OfficialOrchestrator \
                or not lifecycle._claim_evaluation_issuance(
                    authorization, freeze, freeze_port, opener
                ):
            raise OutcomeGateError("evaluation issuance lacks governed lifecycle authority")
        with lock:
            if lifecycle in issued_lifecycles \
                    or authorization.identity in issued_authorizations:
                raise OutcomeGateError("lifecycle authorization was already issued")
            handle = object()
            capability = object.__new__(EvaluationCapability)
            object.__setattr__(capability, "_handle", handle)
            object.__setattr__(capability, "_sealed", True)
            entries[handle] = {
                "authorization": authorization,
                "capability": capability,
                "freeze": freeze,
                "freeze_port": freeze_port,
                "opener": opener,
                "used": False,
            }
            issued_lifecycles.add(lifecycle)
            issued_authorizations.add(authorization.identity)
            return capability

    def consumed_by(capability: "EvaluationCapability", handle: object) -> bool:
        with lock:
            entry = entries.get(handle)
            if entry is None or entry["capability"] is not capability:
                raise OutcomeGateError("evaluation capability is not the exact gate-owned issuance")
            return bool(entry["used"])

    def consume_and_open(
        capability: "EvaluationCapability", handle: object,
        authorization: OutcomeAuthorization,
    ) -> object:
        with lock:
            entry = entries.get(handle)
            if entry is None or entry["capability"] is not capability:
                raise OutcomeGateError("evaluation capability is not the exact gate-owned issuance")
            expected_authorization = entry["authorization"]
            if not isinstance(expected_authorization, OutcomeAuthorization) \
                    or authorization.canonical != expected_authorization.canonical:
                raise OutcomeGateError("evaluation authorization was substituted")
            freeze_port = entry["freeze_port"]
            freeze = entry["freeze"]
            if not isinstance(freeze_port, IndependentRankingFreezePort) \
                    or not isinstance(freeze, RankingFreezeResult):
                raise OutcomeGateError("evaluation issuance authority is unavailable")
            raw, reconstructed = freeze_port.read_and_reconstruct(freeze)
            if not isinstance(raw, bytes) or not raw:
                raise OutcomeGateError("frozen ranking bytes are unavailable")
            if len(raw) != freeze.ranking_byte_count \
                    or hashlib.sha256(raw).hexdigest() != freeze.ranking_sha256:
                raise OutcomeGateError("frozen ranking bytes changed")
            if reconstructed != freeze.ranking_authority:
                raise OutcomeGateError("frozen ranking authority changed")
            if authorization.material["frozen_ranking_artifact_identity"] \
                    != reconstructed.ranking_artifact_identity:
                raise OutcomeGateError("evaluation ranking was substituted")
            if entry["used"]:
                raise OutcomeGateError("evaluation capability was already consumed")
            entry["used"] = True
            opener = entry["opener"]
            if not isinstance(opener, SealedOutcomeOpener):
                raise OutcomeGateError("sealed outcome opener is unavailable")
            outcome_source_identity = authorization.material["outcome_source_identity"]
        return opener.open_authorized_outcome(outcome_source_identity)

    return issue, consumed_by, consume_and_open


(
    _issue_evaluation_capability,
    _evaluation_capability_consumed,
    _consume_and_open_evaluation,
) = _build_evaluation_broker()
del _build_evaluation_broker


class EvaluationCapability:
    __slots__ = ("_handle", "_sealed")

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise OutcomeGateError("evaluation capability is orchestrator-issued only")

    def __copy__(self):
        raise OutcomeGateError("evaluation capability is non-copyable")

    def __deepcopy__(self, memo):
        raise OutcomeGateError("evaluation capability is non-copyable")

    def __reduce__(self):
        raise OutcomeGateError("evaluation capability is non-serializable")

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise OutcomeGateError("evaluation capability is immutable")
        object.__setattr__(self, name, value)

    @property
    def authorization(self) -> OutcomeAuthorization:
        raise OutcomeGateError("authorization material is supplied separately")

    @property
    def consumed(self) -> bool:
        return _evaluation_capability_consumed(self, self._handle)

    def open_outcomes(self, authorization: OutcomeAuthorization) -> object:
        if not isinstance(authorization, OutcomeAuthorization):
            raise TypeError("outcome opening requires canonical authorization")
        return _consume_and_open_evaluation(self, self._handle, authorization)


__all__ = [
    "AuthorizationContractAuthority", "EvaluationCapability", "IndependentRankingFreezePort",
    "OutcomeAuthorization", "OutcomeGateError",
    "OutcomeGatePrerequisiteAuthority", "RankingAuthority", "RankingCandidate", "RankingContextAuthority",
    "RankingFreezeResult", "SealedOutcomeOpener", "build_outcome_authorization",
    "validate_outcome_gate_authority",
]
