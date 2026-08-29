"""Port-driven, non-operational official-execution source semantics.

The implementation contains no configured authority.  Later adoption must bind
every port.  Process-local capabilities are coupled to one orchestrator
lifecycle and cannot be reconstructed from canonical hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import threading
from typing import Protocol, runtime_checkable

from orev3.execution.attempts import (
    AllocationBundle, AllocationRequest, AtomicAllocationPort,
    OUTPUT_POLICY_REVISION, allocate, validate_allocation_bundle,
)
from orev3.execution.canonical import (
    CanonicalControlError, canonical_bytes, domain_identity, normalize_experiment_identifier,
    parse_canonical_bytes, parse_json, require_git_object, require_sha256,
    validate_json_schema_instance,
)
from orev3.execution.control_storage import (
    AtomicControlStoragePort, ControlAuthority, ControlContractError, ControlRecord,
    ExecutionProgressFacts, FailureFacts, RecoveryAuthority,
    RecoveryPrerequisiteAuthority, append_record, build_control_record, recover_failed,
)
from orev3.execution.outcome_gate import (
    AuthorizationContractAuthority, EvaluationCapability, IndependentRankingFreezePort,
    OutcomeAuthorization, OutcomeGatePrerequisiteAuthority, RankingCandidate,
    RankingContextAuthority, RankingFreezeResult,
    SealedOutcomeOpener, _issue_evaluation_capability, build_outcome_authorization,
    validate_outcome_gate_authority,
)
from orev3.execution.phase3b_components import PROJECTION_SCHEMA_CONTRACT_DOMAIN
from orev3.execution.readiness import RemoteHeadRevalidation

OUTCOME_AWARE_PROFILE = "outcome_aware_v1"
CHARACTERIZATION_PROFILE = "outcome_blind_characterization_v1"
PROFILES = frozenset({OUTCOME_AWARE_PROFILE, CHARACTERIZATION_PROFILE})
PROJECTION_IDENTITY_DOMAIN = "orev3:outcome-blind-launch-projection:v1\n"
PROJECTION_RECONSTRUCTION_DOMAIN = "orev3:outcome-blind-launch-projection-reconstruction:v1\n"


class OrchestratorError(CanonicalControlError):
    pass


class LaunchRestartRequired(OrchestratorError):
    pass


class OrchestrationIncomplete(OrchestratorError):
    def __init__(self, message: str, handoff: "RecoveryProgressAuthority") -> None:
        super().__init__(message)
        self.handoff = handoff


class OrchestratorState(str, Enum):
    REQUESTED = "requested"
    CURRENT_READY = "current_ready"
    LAUNCH_PREPARED = "launch_prepared"
    SMOKE_PASSED = "smoke_passed"
    SECOND_FETCH_PASSED = "second_fetch_passed"
    ALLOCATED = "allocated"
    STARTED = "started"
    PRIMARY_FROZEN = "primary_frozen"
    AUTHORIZED = "authorized"
    EVALUATED = "evaluated"
    TERMINALIZING = "terminalizing"
    TERMINAL = "terminal"


_TRANSITIONS = {
    OrchestratorState.REQUESTED: {OrchestratorState.CURRENT_READY},
    OrchestratorState.CURRENT_READY: {OrchestratorState.LAUNCH_PREPARED},
    OrchestratorState.LAUNCH_PREPARED: {OrchestratorState.SMOKE_PASSED},
    OrchestratorState.SMOKE_PASSED: {OrchestratorState.SECOND_FETCH_PASSED},
    OrchestratorState.SECOND_FETCH_PASSED: {OrchestratorState.ALLOCATED},
    OrchestratorState.ALLOCATED: {OrchestratorState.STARTED},
    OrchestratorState.STARTED: {OrchestratorState.PRIMARY_FROZEN},
    OrchestratorState.PRIMARY_FROZEN: {OrchestratorState.AUTHORIZED, OrchestratorState.EVALUATED},
    OrchestratorState.AUTHORIZED: {OrchestratorState.EVALUATED},
    OrchestratorState.EVALUATED: {OrchestratorState.TERMINALIZING},
    OrchestratorState.TERMINALIZING: {OrchestratorState.TERMINAL},
    OrchestratorState.TERMINAL: set(),
}


class OrchestrationStateMachine:
    __slots__ = ("_trace",)

    def __init__(self) -> None:
        self._trace = [OrchestratorState.REQUESTED]

    @property
    def state(self) -> OrchestratorState:
        return self._trace[-1]

    @property
    def trace(self) -> tuple[OrchestratorState, ...]:
        return tuple(self._trace)

    def advance(self, state: OrchestratorState) -> None:
        if state not in _TRANSITIONS[self.state]:
            raise OrchestratorError(f"illegal official lifecycle transition: {self.state.value} -> {state.value}")
        self._trace.append(state)


def _require_closed_projection_schema(node: object, *, path: str = "projection schema") -> None:
    """Require the deliberately small, positively constrained projection subset."""

    if not isinstance(node, dict) or not node:
        raise OrchestratorError(f"{path} must be an object")
    unsupported = set(node) - {
        "$id", "$schema", "additionalProperties", "const", "enum", "items",
        "maxItems", "maxLength", "maximum", "minItems", "minLength", "minimum",
        "pattern", "properties", "required", "title", "type", "uniqueItems",
        "x-canonical-order", "x-input-member-cardinality", "x-order-semantics",
        "x-unique-key",
    }
    if unsupported:
        raise OrchestratorError(f"{path} uses unsupported projection-schema constructs")
    node_type = node.get("type")
    if node_type not in {"object", "array", "string", "integer", "boolean"}:
        raise OrchestratorError(f"{path} must have one explicit supported type")
    if node_type == "object":
        properties = node.get("properties")
        if node.get("additionalProperties") is not False or not isinstance(properties, dict):
            raise OrchestratorError(f"{path} is not closed")
        if set(node) - {
            "$id", "$schema", "additionalProperties", "properties", "required", "title", "type",
            "x-order-semantics",
        }:
            raise OrchestratorError(f"{path} contains unsupported object constraints")
        for name, child in properties.items():
            if not isinstance(name, str) or not name:
                raise OrchestratorError(f"{path} property name is invalid")
            _require_closed_projection_schema(child, path=f"{path}.{name}")
    elif node_type == "array":
        if "items" not in node or not isinstance(node["items"], dict):
            raise OrchestratorError(f"{path} array items are unavailable")
        if set(node) - {
            "$id", "$schema", "items", "maxItems", "minItems", "title", "type",
            "uniqueItems", "x-canonical-order", "x-input-member-cardinality",
            "x-order-semantics", "x-unique-key",
        }:
            raise OrchestratorError(f"{path} contains unsupported array constraints")
        _require_closed_projection_schema(node["items"], path=f"{path}[]")
    elif node_type == "string":
        if set(node) - {
            "$id", "$schema", "const", "enum", "maxLength", "minLength", "pattern", "title", "type",
        }:
            raise OrchestratorError(f"{path} contains unsupported string constraints")
    elif node_type == "integer":
        if set(node) - {"$id", "$schema", "const", "enum", "maximum", "minimum", "title", "type"}:
            raise OrchestratorError(f"{path} contains unsupported integer constraints")
    elif set(node) - {"$id", "$schema", "const", "enum", "title", "type"}:
        raise OrchestratorError(f"{path} contains unsupported boolean constraints")


@dataclass(frozen=True, slots=True)
class Slice2PrerequisiteAuthority:
    """Trusted Slice-2 semantic root; production provenance is deferred to Slice 3.

    This value is intentionally separate from execution-time ports.  Slice 2
    validates a supplied root but does not claim that it came from configured or
    remote authority.  Later adoption must establish that provenance.
    """

    authorization_contract_component_identity: str | None
    authorization_contract_identity: str | None
    dataset_identity: str
    experiment_identifier: str
    outcome_blind_provenance_identity: str
    outcome_source_identity: str | None
    profile_identity: str
    profile_name: str
    projection_component_identity: str
    projection_decoder_identity: str
    projection_schema_canonical: bytes
    projection_schema_identity: str
    ranking_contract_identity: str
    ranking_freeze_component_identity: str | None
    ranking_freeze_contract_identity: str
    ranking_reconstruction_component_identity: str | None
    readiness_identity: str
    readiness_seal_commit: str
    replay_identity: str
    source_commit: str
    terminal_evidence_component_identity: str
    terminal_manifest_contract_identity: str

    def __post_init__(self) -> None:
        normalize_experiment_identifier(self.experiment_identifier)
        if self.profile_name not in PROFILES:
            raise OrchestratorError("Slice-2 prerequisite profile is unsupported")
        for name in (
            "dataset_identity", "outcome_blind_provenance_identity", "profile_identity",
            "projection_component_identity", "projection_decoder_identity",
            "projection_schema_identity", "ranking_contract_identity",
            "ranking_freeze_contract_identity", "readiness_identity", "replay_identity",
            "terminal_evidence_component_identity", "terminal_manifest_contract_identity",
        ):
            require_sha256(name, getattr(self, name))
        _git("readiness_seal_commit", self.readiness_seal_commit)
        _git("source_commit", self.source_commit)
        schema = parse_canonical_bytes(self.projection_schema_canonical)
        _require_closed_projection_schema(schema)
        if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
            raise OrchestratorError("projection schema must govern one closed object")
        if domain_identity(PROJECTION_SCHEMA_CONTRACT_DOMAIN, schema) \
                != self.projection_schema_identity:
            raise OrchestratorError("projection schema identity does not reconstruct")
        aware = self.profile_name == OUTCOME_AWARE_PROFILE
        governed_optional = (
            self.authorization_contract_component_identity,
            self.authorization_contract_identity,
            self.outcome_source_identity,
            self.ranking_freeze_component_identity,
            self.ranking_reconstruction_component_identity,
        )
        if aware != all(value is not None for value in governed_optional):
            raise OrchestratorError("Slice-2 prerequisite outcome authority is inconsistent")
        if not aware and any(value is not None for value in governed_optional):
            raise OrchestratorError("characterization prerequisite contains outcome authority")
        for name, value in (
            ("authorization contract component identity", self.authorization_contract_component_identity),
            ("authorization contract identity", self.authorization_contract_identity),
            ("outcome source identity", self.outcome_source_identity),
            ("ranking freeze component identity", self.ranking_freeze_component_identity),
            ("ranking reconstruction component identity", self.ranking_reconstruction_component_identity),
        ):
            if value is not None:
                require_sha256(name, value)

    @property
    def projection_schema(self) -> dict[str, object]:
        return parse_canonical_bytes(self.projection_schema_canonical)


def _git(name: str, value: object) -> str:
    kind = "sha256" if isinstance(value, str) and len(value) == 64 else "sha1"
    return require_git_object(name, value, kind)


@dataclass(frozen=True, slots=True)
class OfficialExecutionRequest:
    experiment_identifier: str

    def __post_init__(self) -> None:
        normalize_experiment_identifier(self.experiment_identifier)


@dataclass(frozen=True, slots=True)
class LaunchPrerequisiteAuthority:
    allocation_authority_identity: str
    allocator_contract_identity: str
    authorization_contract_component_identity: str | None
    authorization_contract_identity: str | None
    dataset_identity: str
    experiment_identifier: str
    expected_external_input_snapshot_identities: tuple[str, ...]
    launch_authority_snapshot_identity: str
    outcome_blind_provenance_identity: str
    outcome_source_identity: str | None
    profile_identity: str
    profile_name: str
    projection_component_identity: str
    projection_decoder_identity: str
    projection_field_names: tuple[str, ...]
    projection_identity: str
    projection_schema_identity: str
    projection_sha256: str
    ranking_contract_identity: str
    ranking_freeze_component_identity: str | None
    ranking_freeze_contract_identity: str
    ranking_reconstruction_component_identity: str | None
    readiness_identity: str
    readiness_seal_commit: str
    remote_head_commit: str
    replay_identity: str
    source_commit: str
    terminal_evidence_component_identity: str
    terminal_manifest_contract_identity: str

    def __post_init__(self) -> None:
        normalize_experiment_identifier(self.experiment_identifier)
        if self.profile_name not in PROFILES:
            raise OrchestratorError("execution profile is unsupported")
        for name in (
            "allocation_authority_identity", "allocator_contract_identity", "dataset_identity",
            "launch_authority_snapshot_identity", "outcome_blind_provenance_identity",
            "profile_identity", "projection_component_identity", "projection_decoder_identity",
            "projection_identity", "projection_schema_identity", "projection_sha256",
            "ranking_contract_identity", "ranking_freeze_contract_identity",
            "readiness_identity", "replay_identity", "terminal_evidence_component_identity",
            "terminal_manifest_contract_identity",
        ):
            require_sha256(name, getattr(self, name))
        if not isinstance(self.expected_external_input_snapshot_identities, tuple):
            raise OrchestratorError("expected input snapshot identities must be a tuple")
        for identity in self.expected_external_input_snapshot_identities:
            require_sha256("expected input snapshot identity", identity)
        if len(set(self.expected_external_input_snapshot_identities)) != len(self.expected_external_input_snapshot_identities):
            raise OrchestratorError("expected input snapshot identities must be unique")
        if not isinstance(self.projection_field_names, tuple) or not self.projection_field_names:
            raise OrchestratorError("projection contract field names must be a nonempty tuple")
        if tuple(sorted(self.projection_field_names)) != self.projection_field_names \
                or len(set(self.projection_field_names)) != len(self.projection_field_names):
            raise OrchestratorError("projection contract field names must be sorted and unique")
        for name in self.projection_field_names:
            if not isinstance(name, str) or not name or not name.isascii():
                raise OrchestratorError("projection contract field name is invalid")
        _git("readiness_seal_commit", self.readiness_seal_commit)
        _git("remote_head_commit", self.remote_head_commit)
        _git("source_commit", self.source_commit)
        aware = self.profile_name == OUTCOME_AWARE_PROFILE
        if aware != (self.authorization_contract_identity is not None):
            raise OrchestratorError("profile authorization contract is inconsistent")
        if aware != (self.authorization_contract_component_identity is not None):
            raise OrchestratorError("profile authorization-contract component is inconsistent")
        if aware != (self.outcome_source_identity is not None):
            raise OrchestratorError("profile outcome source is inconsistent")
        if aware != (self.ranking_freeze_component_identity is not None):
            raise OrchestratorError("profile ranking-freeze component is inconsistent")
        if aware != (self.ranking_reconstruction_component_identity is not None):
            raise OrchestratorError("profile ranking-reconstruction component is inconsistent")
        if aware:
            require_sha256("authorization contract component identity", self.authorization_contract_component_identity)
            require_sha256("authorization contract identity", self.authorization_contract_identity)
            require_sha256("outcome source identity", self.outcome_source_identity)
            require_sha256("ranking freeze component identity", self.ranking_freeze_component_identity)
            require_sha256("ranking reconstruction component identity", self.ranking_reconstruction_component_identity)


@dataclass(frozen=True, slots=True)
class PreparedLaunchInputs:
    """Untrusted preparation output; it is never sent to a worker."""

    authority: LaunchPrerequisiteAuthority
    external_input_snapshot_identities: tuple[str, ...]
    projection_canonical: bytes
    projection_identity: str
    projection_sha256: str
    projection_decoder_identity: str
    projection_schema_identity: str
    outcome_opener: SealedOutcomeOpener | None

    def __post_init__(self) -> None:
        if not isinstance(self.authority, LaunchPrerequisiteAuthority):
            raise TypeError("prepared launch lacks authority")
        if not isinstance(self.external_input_snapshot_identities, tuple):
            raise OrchestratorError("prepared input snapshot identities must be a tuple")
        for identity in self.external_input_snapshot_identities:
            require_sha256("prepared input snapshot identity", identity)
        if not isinstance(self.projection_canonical, bytes) or not self.projection_canonical:
            raise OrchestratorError("prepared projection bytes are unavailable")
        for name in ("projection_identity", "projection_sha256", "projection_decoder_identity", "projection_schema_identity"):
            require_sha256(name, getattr(self, name))
        aware = self.authority.profile_name == OUTCOME_AWARE_PROFILE
        if aware and not isinstance(self.outcome_opener, SealedOutcomeOpener):
            raise OrchestratorError("outcome-aware launch lacks sealed opener")
        if not aware and self.outcome_opener is not None:
            raise OrchestratorError("characterization launch must not possess outcome opener")


@dataclass(frozen=True, slots=True)
class AuthenticatedLaunchInputs:
    """Independently reconstructed immutable launch/projection authority."""

    authority: LaunchPrerequisiteAuthority
    external_input_snapshot_identities: tuple[str, ...]
    projection_canonical: bytes
    projection_identity: str
    projection_sha256: str
    projection_decoder_identity: str
    projection_schema_identity: str
    reconstruction_identity: str
    outcome_opener: SealedOutcomeOpener | None

    def __post_init__(self) -> None:
        if not isinstance(self.authority, LaunchPrerequisiteAuthority):
            raise TypeError("authenticated launch lacks authority")
        require_sha256("launch input reconstruction identity", self.reconstruction_identity)


def _projection_identity_material(launch: LaunchPrerequisiteAuthority, digest: str) -> dict[str, object]:
    return {
        "dataset_identity": launch.dataset_identity,
        "external_input_snapshot_identities": list(launch.expected_external_input_snapshot_identities),
        "launch_authority_snapshot_identity": launch.launch_authority_snapshot_identity,
        "projection_decoder_identity": launch.projection_decoder_identity,
        "projection_schema_identity": launch.projection_schema_identity,
        "projection_sha256": digest,
    }


def validate_authenticated_launch_inputs(
    prerequisite: Slice2PrerequisiteAuthority, launch: LaunchPrerequisiteAuthority,
    candidate: PreparedLaunchInputs,
    authenticated: AuthenticatedLaunchInputs,
) -> None:
    if not isinstance(prerequisite, Slice2PrerequisiteAuthority):
        raise TypeError("launch validation lacks Slice-2 prerequisite authority")
    if not isinstance(authenticated, AuthenticatedLaunchInputs):
        raise TypeError("launch authenticator returned unsupported authority")
    if candidate.authority != launch or authenticated.authority != launch:
        raise OrchestratorError("launch input authority was substituted")
    if authenticated.external_input_snapshot_identities != launch.expected_external_input_snapshot_identities:
        raise OrchestratorError("immutable input snapshots differ from sealed launch authority")
    for name in ("projection_canonical", "projection_identity", "projection_sha256",
                 "projection_decoder_identity", "projection_schema_identity", "outcome_opener"):
        if getattr(authenticated, name) != getattr(candidate, name):
            raise OrchestratorError("authenticated launch input differs from prepared candidate")
    if authenticated.projection_decoder_identity != launch.projection_decoder_identity:
        raise OrchestratorError("projection decoder differs from launch authority")
    if authenticated.projection_schema_identity != launch.projection_schema_identity:
        raise OrchestratorError("projection schema differs from launch authority")
    if hashlib.sha256(authenticated.projection_canonical).hexdigest() != authenticated.projection_sha256:
        raise OrchestratorError("projection digest does not reconstruct")
    if authenticated.projection_sha256 != launch.projection_sha256:
        raise OrchestratorError("projection digest differs from sealed launch authority")
    expected_identity = domain_identity(
        PROJECTION_IDENTITY_DOMAIN,
        _projection_identity_material(launch, authenticated.projection_sha256),
    )
    if authenticated.projection_identity != launch.projection_identity \
            or authenticated.projection_identity != expected_identity:
        raise OrchestratorError("projection identity does not reconstruct from launch authority")
    value = parse_json(authenticated.projection_canonical)
    if canonical_bytes(value) != authenticated.projection_canonical:
        raise OrchestratorError("ranking projection bytes are not canonical")
    if not isinstance(value, dict):
        raise OrchestratorError("ranking projection must be one closed canonical object")
    try:
        validate_json_schema_instance(value, prerequisite.projection_schema, schema_registry={})
    except CanonicalControlError as exc:
        raise OrchestratorError("ranking projection violates the governed closed schema") from exc
    expected_reconstruction = domain_identity(
        PROJECTION_RECONSTRUCTION_DOMAIN,
        {
            "projection_component_identity": launch.projection_component_identity,
            "projection_identity": authenticated.projection_identity,
            "projection_sha256": authenticated.projection_sha256,
        },
    )
    if authenticated.reconstruction_identity != expected_reconstruction:
        raise OrchestratorError("projection reconstruction authority does not reconstruct")


@runtime_checkable
class LaunchInputAuthenticator(Protocol):
    @property
    def component_identity(self) -> str: ...

    def authenticate_launch_inputs(
        self, authority: LaunchPrerequisiteAuthority, candidate: PreparedLaunchInputs
    ) -> AuthenticatedLaunchInputs: ...


class RankingExecutionCapability:
    __slots__ = ("attempt_identity", "control_authority", "dataset_identity",
                 "projection_canonical", "projection_identity", "profile_identity",
                 "profile_name", "replay_identity")

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise OrchestratorError("ranking capability is orchestrator-issued after durable STARTED only")

    def __copy__(self):
        raise OrchestratorError("ranking capability is non-copyable")

    def __deepcopy__(self, memo):
        raise OrchestratorError("ranking capability is non-copyable")


@dataclass(frozen=True, slots=True)
class ScientificTerminalCandidate:
    disposition: str
    raw: bytes

    def __post_init__(self) -> None:
        if self.disposition not in {"VALID", "INVALID"}:
            raise OrchestratorError("terminal disposition is unsupported")
        if not isinstance(self.raw, bytes) or not self.raw:
            raise OrchestratorError("terminal evidence bytes are unavailable")


@dataclass(frozen=True, slots=True)
class TerminalEvidenceContext:
    attempt_identity: str
    profile_identity: str
    launch_authority_snapshot_identity: str
    external_input_snapshot_identities: tuple[str, ...]
    ranking_artifact_identity: str | None
    terminal_evidence_component_identity: str
    terminal_manifest_contract_identity: str

    def __post_init__(self) -> None:
        require_sha256("attempt identity", self.attempt_identity)
        require_sha256("profile identity", self.profile_identity)
        require_sha256("launch authority snapshot identity", self.launch_authority_snapshot_identity)
        for identity in self.external_input_snapshot_identities:
            require_sha256("terminal input snapshot identity", identity)
        if self.ranking_artifact_identity is not None:
            require_sha256("terminal ranking artifact identity", self.ranking_artifact_identity)
        require_sha256("terminal evidence component identity", self.terminal_evidence_component_identity)
        require_sha256("terminal manifest contract identity", self.terminal_manifest_contract_identity)


@dataclass(frozen=True, slots=True)
class ValidatedTerminalEvidence:
    disposition: str
    evidence_identity: str
    evidence_sha256: str
    context: TerminalEvidenceContext
    required_scientific_manifest_bindings: tuple[tuple[str, str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.disposition not in {"VALID", "INVALID"}:
            raise OrchestratorError("validated terminal disposition is unsupported")
        require_sha256("terminal evidence identity", self.evidence_identity)
        require_sha256("terminal evidence sha256", self.evidence_sha256)
        if not isinstance(self.context, TerminalEvidenceContext):
            raise TypeError("terminal evidence lacks context")
        if not isinstance(self.required_scientific_manifest_bindings, tuple):
            raise OrchestratorError("scientific manifest bindings must be a tuple")
        identifiers: list[str] = []
        for binding in self.required_scientific_manifest_bindings:
            if not isinstance(binding, tuple) or len(binding) != 3:
                raise OrchestratorError("scientific manifest binding is malformed")
            identifier, identity, digest = binding
            if not isinstance(identifier, str) or not identifier:
                raise OrchestratorError("scientific manifest identifier is invalid")
            require_sha256("scientific manifest identity", identity)
            require_sha256("scientific manifest sha256", digest)
            identifiers.append(identifier)
        if identifiers != sorted(identifiers) or len(set(identifiers)) != len(identifiers):
            raise OrchestratorError("scientific manifest bindings are not canonical")
        if self.disposition == "VALID" and self.required_scientific_manifest_bindings:
            raise OrchestratorError("VALID terminal has invalidity-only bindings")


@runtime_checkable
class TerminalEvidenceAuthority(Protocol):
    @property
    def component_identity(self) -> str: ...

    @property
    def manifest_contract_identity(self) -> str: ...

    def reconstruct_terminal_evidence(
        self, candidate: ScientificTerminalCandidate, expected: TerminalEvidenceContext
    ) -> tuple[bytes, ValidatedTerminalEvidence]: ...


@dataclass(frozen=True, slots=True)
class CharacterizationFreezeResult:
    terminal_candidate: ScientificTerminalCandidate


@runtime_checkable
class CurrentReadinessResolver(Protocol):
    def resolve_current_launch(self, experiment_identifier: str) -> LaunchPrerequisiteAuthority: ...


@runtime_checkable
class LaunchInputPreparer(Protocol):
    def prepare_launch_inputs(self, authority: LaunchPrerequisiteAuthority) -> PreparedLaunchInputs: ...


@runtime_checkable
class LaunchSmokeRunner(Protocol):
    def run_launch_smoke(self, prepared: AuthenticatedLaunchInputs) -> None: ...


@runtime_checkable
class SecondFetchPort(Protocol):
    def revalidate_remote_head(self, authority: LaunchPrerequisiteAuthority) -> RemoteHeadRevalidation: ...


@runtime_checkable
class RankingWorker(Protocol):
    def run_ranking(self, capability: RankingExecutionCapability) -> RankingCandidate: ...


@runtime_checkable
class CharacterizationWorker(Protocol):
    def run_characterization(self, capability: RankingExecutionCapability) -> CharacterizationFreezeResult: ...


@runtime_checkable
class EvaluationWorker(Protocol):
    def evaluate(self, capability: EvaluationCapability,
                 authorization: OutcomeAuthorization) -> ScientificTerminalCandidate: ...


@dataclass(frozen=True, slots=True)
class OrchestratorPorts:
    readiness: CurrentReadinessResolver
    preparation: LaunchInputPreparer
    launch_authenticator: LaunchInputAuthenticator
    smoke: LaunchSmokeRunner
    second_fetch: SecondFetchPort
    allocator: AtomicAllocationPort
    control: AtomicControlStoragePort
    terminal_evidence: TerminalEvidenceAuthority
    ranking_freeze: IndependentRankingFreezePort | None = None
    authorization_contract: AuthorizationContractAuthority | None = None
    ranking: RankingWorker | None = None
    characterization: CharacterizationWorker | None = None
    evaluation: EvaluationWorker | None = None

    def __post_init__(self) -> None:
        required = (
            ("readiness", CurrentReadinessResolver), ("preparation", LaunchInputPreparer),
            ("launch_authenticator", LaunchInputAuthenticator), ("smoke", LaunchSmokeRunner),
            ("second_fetch", SecondFetchPort), ("allocator", AtomicAllocationPort),
            ("control", AtomicControlStoragePort), ("terminal_evidence", TerminalEvidenceAuthority),
        )
        for name, protocol in required:
            if not isinstance(getattr(self, name), protocol):
                raise TypeError(f"orchestrator port {name} is unavailable")


@dataclass(frozen=True, slots=True)
class _BoundAuthoritySet:
    """Implementations checked against one separately supplied prerequisite root."""

    prerequisite: Slice2PrerequisiteAuthority
    projection: LaunchInputAuthenticator
    terminal: TerminalEvidenceAuthority
    ranking_freeze: IndependentRankingFreezePort | None
    authorization_contract: AuthorizationContractAuthority | None

    @classmethod
    def bind(
        cls, prerequisite: Slice2PrerequisiteAuthority, ports: OrchestratorPorts
    ) -> "_BoundAuthoritySet":
        if not isinstance(prerequisite, Slice2PrerequisiteAuthority):
            raise TypeError("official orchestrator requires independent Slice-2 prerequisite authority")
        bound = cls(
            prerequisite, ports.launch_authenticator, ports.terminal_evidence,
            ports.ranking_freeze, ports.authorization_contract,
        )
        bound._validate_implementations()
        return bound

    def _validate_implementations(self) -> None:
        root = self.prerequisite
        if require_sha256("projection component identity", self.projection.component_identity) \
                != root.projection_component_identity:
            raise OrchestratorError("projection implementation differs from prerequisite root")
        if require_sha256("terminal component identity", self.terminal.component_identity) \
                != root.terminal_evidence_component_identity:
            raise OrchestratorError("terminal implementation differs from prerequisite root")
        if require_sha256("terminal manifest contract identity", self.terminal.manifest_contract_identity) \
                != root.terminal_manifest_contract_identity:
            raise OrchestratorError("terminal contract differs from prerequisite root")
        if root.profile_name == OUTCOME_AWARE_PROFILE:
            if self.ranking_freeze is None or self.authorization_contract is None:
                raise OrchestratorError("outcome-aware prerequisite implementations are unavailable")
            if require_sha256("ranking freeze component identity", self.ranking_freeze.freeze_component_identity) \
                    != root.ranking_freeze_component_identity:
                raise OrchestratorError("ranking freeze implementation differs from prerequisite root")
            if require_sha256(
                "ranking reconstruction component identity",
                self.ranking_freeze.reconstruction_component_identity,
            ) != root.ranking_reconstruction_component_identity:
                raise OrchestratorError("ranking reconstruction differs from prerequisite root")
            if require_sha256(
                "authorization contract component identity",
                self.authorization_contract.component_identity,
            ) != root.authorization_contract_component_identity:
                raise OrchestratorError("authorization-contract implementation differs from prerequisite root")
        elif self.ranking_freeze is not None or self.authorization_contract is not None:
            raise OrchestratorError("characterization implementation set contains outcome authority")

    def validate_launch(self, launch: LaunchPrerequisiteAuthority) -> None:
        root = self.prerequisite
        comparisons = (
            ("experiment", launch.experiment_identifier, root.experiment_identifier),
            ("readiness", launch.readiness_identity, root.readiness_identity),
            ("readiness seal", launch.readiness_seal_commit, root.readiness_seal_commit),
            ("source", launch.source_commit, root.source_commit),
            ("profile", launch.profile_identity, root.profile_identity),
            ("profile name", launch.profile_name, root.profile_name),
            ("dataset", launch.dataset_identity, root.dataset_identity),
            ("Replay", launch.replay_identity, root.replay_identity),
            ("outcome-blind provenance", launch.outcome_blind_provenance_identity,
             root.outcome_blind_provenance_identity),
            ("outcome source", launch.outcome_source_identity, root.outcome_source_identity),
            ("projection component", launch.projection_component_identity,
             root.projection_component_identity),
            ("projection decoder", launch.projection_decoder_identity,
             root.projection_decoder_identity),
            ("projection schema", launch.projection_schema_identity,
             root.projection_schema_identity),
            ("ranking contract", launch.ranking_contract_identity,
             root.ranking_contract_identity),
            ("ranking freeze component", launch.ranking_freeze_component_identity,
             root.ranking_freeze_component_identity),
            ("ranking freeze contract", launch.ranking_freeze_contract_identity,
             root.ranking_freeze_contract_identity),
            ("ranking reconstruction component", launch.ranking_reconstruction_component_identity,
             root.ranking_reconstruction_component_identity),
            ("authorization contract component", launch.authorization_contract_component_identity,
             root.authorization_contract_component_identity),
            ("authorization contract", launch.authorization_contract_identity,
             root.authorization_contract_identity),
            ("terminal evidence component", launch.terminal_evidence_component_identity,
             root.terminal_evidence_component_identity),
            ("terminal manifest contract", launch.terminal_manifest_contract_identity,
             root.terminal_manifest_contract_identity),
        )
        for label, actual, expected in comparisons:
            if actual != expected:
                raise OrchestratorError(f"launch {label} differs from prerequisite root")
        properties = root.projection_schema["properties"]
        if launch.projection_field_names != tuple(sorted(properties)):
            raise OrchestratorError("launch projection fields differ from prerequisite root")


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    allocation: AllocationBundle
    started_record: ControlRecord
    terminal_record: ControlRecord
    trace: tuple[OrchestratorState, ...]
    authorization: OutcomeAuthorization | None


class RecoveryProgressAuthority:
    """Opaque handle; authoritative progress remains in its issuing orchestrator."""

    __slots__ = ()

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise OrchestratorError("recovery progress authority is orchestrator-issued only")

    def __copy__(self):
        raise OrchestratorError("recovery progress authority is non-copyable")

    def __deepcopy__(self, memo):
        raise OrchestratorError("recovery progress authority is non-copyable")

    def __reduce__(self):
        raise OrchestratorError("recovery progress authority is non-serializable")


@dataclass(frozen=True, slots=True)
class FailureObservation:
    conflicting: bool = False
    indeterminate: bool = False
    premature_outcome_access: bool = False
    shared_storage_failure: bool = False
    execution_infrastructure_failure: bool = False
    owner_terminated: bool = False
    owner_unavailable: bool = False

    def with_progress(self, progress: ExecutionProgressFacts) -> FailureFacts:
        return FailureFacts(
            progress, self.conflicting, self.indeterminate,
            self.premature_outcome_access, self.shared_storage_failure,
            self.execution_infrastructure_failure, self.owner_terminated,
            self.owner_unavailable,
        )


def execution_progress_for(state: OrchestratorState, *, profile_name: str = OUTCOME_AWARE_PROFILE) -> ExecutionProgressFacts:
    if profile_name not in PROFILES:
        raise OrchestratorError("execution progress profile is unsupported")
    authorized = profile_name == OUTCOME_AWARE_PROFILE and state in {
        OrchestratorState.AUTHORIZED, OrchestratorState.EVALUATED,
        OrchestratorState.TERMINALIZING, OrchestratorState.TERMINAL,
    }
    return ExecutionProgressFacts(
        ranking_frozen=state in {OrchestratorState.PRIMARY_FROZEN, OrchestratorState.AUTHORIZED,
                                 OrchestratorState.EVALUATED, OrchestratorState.TERMINALIZING,
                                 OrchestratorState.TERMINAL},
        outcome_authorized=authorized,
        terminalization_started=state in {OrchestratorState.TERMINALIZING, OrchestratorState.TERMINAL},
    )


def _control_authority(launch: LaunchPrerequisiteAuthority, allocation: AllocationBundle) -> ControlAuthority:
    material = allocation.receipt_material
    return ControlAuthority(
        allocation_receipt_identity=allocation.allocation_receipt_identity,
        attempt_identity=allocation.attempt_identity, attempt_kind=str(material["attempt_kind"]),
        external_input_snapshot_identities=tuple(material["external_input_snapshot_identities"]),
        launch_authority_snapshot_identity=str(material["launch_authority_snapshot_identity"]),
        ordinal=int(material["ordinal"]), profile_identity=launch.profile_identity,
        readiness_identity=str(material["readiness_identity"]),
        readiness_seal_commit=str(material["readiness_seal_commit"]),
        remote_head_commit=str(material["remote_head_commit"]), source_commit=str(material["source_commit"]),
    )


def _terminal_record(authority: ControlAuthority, predecessor: ControlRecord,
                     terminal: ValidatedTerminalEvidence) -> ControlRecord:
    if terminal.disposition == "VALID":
        state = {"control_state": "VALID", "experiment_audit_manifest_identity": terminal.evidence_identity,
                 "experiment_audit_manifest_sha256": terminal.evidence_sha256}
    else:
        state = {"control_state": "INVALID", "governing_invalidity_evidence_identity": terminal.evidence_identity,
                 "governing_invalidity_evidence_sha256": terminal.evidence_sha256,
                 "required_scientific_manifest_bindings": [
                     {"manifest_identifier": i, "manifest_identity": x, "manifest_sha256": d}
                     for i, x, d in terminal.required_scientific_manifest_bindings]}
    return build_control_record(authority, sequence=predecessor.sequence + 1,
                                predecessor={"identity": predecessor.identity, "status": "known"}, state=state)


class OfficialOrchestrator:
    """Source semantics suitable for later configured official binding."""

    __slots__ = ("_authority", "_ports", "_sealed")

    def __init__(
        self, prerequisite: Slice2PrerequisiteAuthority, ports: OrchestratorPorts
    ) -> None:
        if not isinstance(ports, OrchestratorPorts):
            raise TypeError("official orchestrator requires explicit ports")
        object.__setattr__(self, "_ports", ports)
        object.__setattr__(self, "_authority", _BoundAuthoritySet.bind(prerequisite, ports))
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise OrchestratorError("official orchestrator authority is immutable")
        object.__setattr__(self, name, value)

    def _profile_ports(self, profile: str) -> None:
        if profile == OUTCOME_AWARE_PROFILE:
            if not all((isinstance(self._ports.ranking, RankingWorker),
                        isinstance(self._ports.evaluation, EvaluationWorker),
                        isinstance(self._ports.ranking_freeze, IndependentRankingFreezePort),
                        isinstance(self._ports.authorization_contract, AuthorizationContractAuthority))) \
                    or self._ports.characterization is not None:
                raise OrchestratorError("outcome-aware worker capability set is invalid")
        elif not isinstance(self._ports.characterization, CharacterizationWorker) \
                or any((self._ports.ranking, self._ports.evaluation,
                        self._ports.ranking_freeze, self._ports.authorization_contract)):
            raise OrchestratorError("characterization worker capability set is invalid")

    def _execute_internal(
        self, request: OfficialExecutionRequest, begin_lifecycle,
        register_evaluation_eligibility, register_recovery,
    ) -> OrchestrationResult:
        if not isinstance(request, OfficialExecutionRequest):
            raise TypeError("official execution requires OfficialExecutionRequest")
        begin_lifecycle(self)
        machine = OrchestrationStateMachine()
        launch = self._ports.readiness.resolve_current_launch(request.experiment_identifier)
        if launch.experiment_identifier != request.experiment_identifier:
            raise OrchestratorError("current readiness resolved another experiment")
        self._authority.validate_launch(launch)
        self._authority._validate_implementations()
        machine.advance(OrchestratorState.CURRENT_READY)
        candidate = self._ports.preparation.prepare_launch_inputs(launch)
        authenticated = self._authority.projection.authenticate_launch_inputs(launch, candidate)
        validate_authenticated_launch_inputs(
            self._authority.prerequisite, launch, candidate, authenticated
        )
        self._profile_ports(launch.profile_name)
        machine.advance(OrchestratorState.LAUNCH_PREPARED)
        self._ports.smoke.run_launch_smoke(authenticated)
        machine.advance(OrchestratorState.SMOKE_PASSED)
        revalidation = self._ports.second_fetch.revalidate_remote_head(launch)
        if revalidation is RemoteHeadRevalidation.RESTART_REQUIRED:
            raise LaunchRestartRequired("remote head changed before allocation")
        if revalidation is not RemoteHeadRevalidation.UNCHANGED:
            raise OrchestratorError("second-fetch result is not governed")
        machine.advance(OrchestratorState.SECOND_FETCH_PASSED)
        request_material = AllocationRequest(
            launch.allocation_authority_identity, launch.allocator_contract_identity, "official",
            launch.experiment_identifier, authenticated.external_input_snapshot_identities,
            launch.launch_authority_snapshot_identity, OUTPUT_POLICY_REVISION,
            launch.readiness_identity, launch.readiness_seal_commit,
            launch.remote_head_commit, launch.source_commit,
        )
        allocation = allocate(self._ports.allocator, request_material)
        validate_allocation_bundle(allocation)
        machine.advance(OrchestratorState.ALLOCATED)
        control_authority = _control_authority(launch, allocation)
        try:
            initial = self._ports.control.read_snapshot(control_authority.attempt_identity)
            if initial.records or initial.observations:
                raise OrchestratorError("new allocation has pre-existing control history")
            started = build_control_record(control_authority, sequence=1,
                                           predecessor={"status": "absent"}, state={"control_state": "STARTED"})
            started = append_record(self._ports.control, initial, started)
            if started.state != "STARTED" or started.authority_material != control_authority.material:
                raise OrchestratorError("durable STARTED result differs from lifecycle authority")
            machine.advance(OrchestratorState.STARTED)
            capability = object.__new__(RankingExecutionCapability)
            capability.attempt_identity = control_authority.attempt_identity
            capability.control_authority = control_authority
            capability.dataset_identity = launch.dataset_identity
            capability.projection_canonical = authenticated.projection_canonical
            capability.projection_identity = authenticated.projection_identity
            capability.profile_identity = launch.profile_identity
            capability.profile_name = launch.profile_name
            capability.replay_identity = launch.replay_identity
            authorization: OutcomeAuthorization | None = None
            ranking_identity: str | None = None
            if launch.profile_name == OUTCOME_AWARE_PROFILE:
                assert self._ports.ranking and self._ports.evaluation
                assert self._authority.ranking_freeze and self._authority.authorization_contract
                ranking_candidate = self._ports.ranking.run_ranking(capability)
                if not isinstance(ranking_candidate, RankingCandidate):
                    raise OrchestratorError("ranking worker did not return ranking candidate bytes")
                expected = RankingContextAuthority(
                    allocation.attempt_identity, launch.dataset_identity,
                    authenticated.external_input_snapshot_identities,
                    launch.outcome_blind_provenance_identity, launch.profile_identity,
                    launch.ranking_contract_identity, launch.ranking_freeze_component_identity,
                    launch.ranking_freeze_contract_identity,
                    launch.ranking_reconstruction_component_identity,
                    launch.replay_identity,
                )
                self._authority._validate_implementations()
                freeze = self._authority.ranking_freeze.freeze_and_reconstruct(ranking_candidate, expected)
                raw, reconstructed = self._authority.ranking_freeze.read_and_reconstruct(freeze)
                if not isinstance(freeze, RankingFreezeResult) or reconstructed != freeze.ranking_authority:
                    raise OrchestratorError("ranking freeze authority does not independently reconstruct")
                if len(raw) != freeze.ranking_byte_count or hashlib.sha256(raw).hexdigest() != freeze.ranking_sha256:
                    raise OrchestratorError("ranking freeze bytes do not independently reconstruct")
                if RankingContextAuthority(
                    reconstructed.attempt_identity, reconstructed.dataset_identity,
                    reconstructed.external_input_snapshot_identities,
                    reconstructed.outcome_blind_provenance_identity, reconstructed.profile_identity,
                    reconstructed.ranking_contract_identity, reconstructed.ranking_freeze_component_identity,
                    reconstructed.ranking_freeze_contract_identity,
                    reconstructed.ranking_reconstruction_component_identity,
                    reconstructed.replay_identity,
                ) != expected:
                    raise OrchestratorError("ranking freeze differs from launch authority")
                ranking_identity = reconstructed.ranking_artifact_identity
                machine.advance(OrchestratorState.PRIMARY_FROZEN)
                prerequisite = OutcomeGatePrerequisiteAuthority(
                    launch.authorization_contract_component_identity,
                    launch.authorization_contract_identity, allocation.attempt_identity,
                    launch.dataset_identity, authenticated.external_input_snapshot_identities,
                    launch.launch_authority_snapshot_identity, launch.outcome_blind_provenance_identity,
                    launch.outcome_source_identity, launch.profile_identity, launch.profile_name,
                    launch.ranking_contract_identity, launch.ranking_freeze_component_identity,
                    launch.ranking_freeze_contract_identity,
                    launch.ranking_reconstruction_component_identity,
                    launch.readiness_identity, launch.readiness_seal_commit,
                    launch.replay_identity, launch.source_commit,
                )

                if machine.state is not OrchestratorState.PRIMARY_FROZEN:
                    raise OrchestratorError("gate authority is unavailable at this lifecycle state")
                ranking = validate_outcome_gate_authority(
                    prerequisite, freeze, authenticated.outcome_opener,
                    self._authority.authorization_contract, self._authority.ranking_freeze,
                )
                authorization = build_outcome_authorization(prerequisite, ranking)
                register_evaluation_eligibility(
                    self, machine, control_authority, started, authorization, freeze,
                    self._authority.ranking_freeze, authenticated.outcome_opener,
                )
                evaluation_capability = _issue_evaluation_capability(
                    self, authorization, freeze, self._authority.ranking_freeze,
                    authenticated.outcome_opener,
                )
                machine.advance(OrchestratorState.AUTHORIZED)
                terminal_candidate = self._ports.evaluation.evaluate(evaluation_capability, authorization)
                if not evaluation_capability.consumed:
                    raise OrchestratorError("evaluation completed without authorized outcome opening")
            else:
                assert self._ports.characterization
                primary = self._ports.characterization.run_characterization(capability)
                if not isinstance(primary, CharacterizationFreezeResult):
                    raise OrchestratorError("characterization did not return frozen terminal candidate")
                machine.advance(OrchestratorState.PRIMARY_FROZEN)
                terminal_candidate = primary.terminal_candidate
            if not isinstance(terminal_candidate, ScientificTerminalCandidate):
                raise OrchestratorError("worker terminal evidence is malformed")
            machine.advance(OrchestratorState.EVALUATED)
            machine.advance(OrchestratorState.TERMINALIZING)
            terminal_context = TerminalEvidenceContext(
                allocation.attempt_identity, launch.profile_identity,
                launch.launch_authority_snapshot_identity,
                authenticated.external_input_snapshot_identities, ranking_identity,
                launch.terminal_evidence_component_identity,
                launch.terminal_manifest_contract_identity,
            )
            self._authority._validate_implementations()
            evidence_raw, terminal = self._authority.terminal.reconstruct_terminal_evidence(
                terminal_candidate, terminal_context
            )
            if terminal.context != terminal_context or terminal.disposition != terminal_candidate.disposition:
                raise OrchestratorError("terminal evidence authority was substituted")
            if evidence_raw != terminal_candidate.raw or hashlib.sha256(evidence_raw).hexdigest() != terminal.evidence_sha256:
                raise OrchestratorError("terminal evidence bytes do not reconstruct")
            current = self._ports.control.read_snapshot(control_authority.attempt_identity)
            if current.is_conflicting or current.terminal_identity is not None:
                raise ControlContractError("terminalization requires unique nonterminal history")
            if not current.common_prefix or current.common_prefix[-1].identity != started.identity:
                raise ControlContractError("durable STARTED authority changed before terminalization")
            terminal_record = append_record(self._ports.control, current,
                                            _terminal_record(control_authority, started, terminal))
            machine.advance(OrchestratorState.TERMINAL)
            return OrchestrationResult(allocation, started, terminal_record, machine.trace, authorization)
        except OrchestrationIncomplete:
            raise
        except Exception as exc:
            raise OrchestrationIncomplete(
                str(exc), register_recovery(
                    self, machine, control_authority, launch.profile_name
                )
            ) from exc


def _bind_official_lifecycle_authority(orchestrator_type):
    """Install lifecycle methods backed only by lexical authority registries."""

    registry_lock = threading.RLock()
    active_lifecycles: set[object] = set()
    issued_lifecycles: set[object] = set()
    evaluation_eligibilities: dict[object, tuple[object, ...]] = {}
    recovery_registrations: dict[RecoveryProgressAuthority, tuple[object, ...]] = {}
    internal_execute = orchestrator_type._execute_internal
    delattr(orchestrator_type, "_execute_internal")

    expected_primary_trace = (
        OrchestratorState.REQUESTED,
        OrchestratorState.CURRENT_READY,
        OrchestratorState.LAUNCH_PREPARED,
        OrchestratorState.SMOKE_PASSED,
        OrchestratorState.SECOND_FETCH_PASSED,
        OrchestratorState.ALLOCATED,
        OrchestratorState.STARTED,
        OrchestratorState.PRIMARY_FROZEN,
    )

    def begin_lifecycle(owner: object) -> None:
        with registry_lock:
            if owner in active_lifecycles:
                raise OrchestratorError("orchestrator instance already owns a lifecycle")
            active_lifecycles.add(owner)

    def register_evaluation_eligibility(
        owner: object, machine: OrchestrationStateMachine,
        control_authority: ControlAuthority, started: ControlRecord,
        authorization: OutcomeAuthorization, freeze: RankingFreezeResult,
        freeze_port: IndependentRankingFreezePort, opener: SealedOutcomeOpener,
    ) -> None:
        if type(owner) is not orchestrator_type \
                or not isinstance(machine, OrchestrationStateMachine) \
                or not isinstance(control_authority, ControlAuthority) \
                or not isinstance(started, ControlRecord) \
                or not isinstance(authorization, OutcomeAuthorization) \
                or not isinstance(freeze, RankingFreezeResult) \
                or not isinstance(freeze_port, IndependentRankingFreezePort) \
                or not isinstance(opener, SealedOutcomeOpener):
            raise OrchestratorError("evaluation eligibility lacks governed lifecycle authority")
        trace = tuple(machine.trace)
        authority = owner._authority
        if trace != expected_primary_trace \
                or authority.prerequisite.profile_name != OUTCOME_AWARE_PROFILE \
                or started.state != "STARTED" \
                or started.authority_material != control_authority.material \
                or freeze.ranking_authority.attempt_identity != control_authority.attempt_identity \
                or authorization.material["attempt_identity"] != control_authority.attempt_identity \
                or authorization.material["frozen_ranking_artifact_identity"] \
                != freeze.ranking_authority.ranking_artifact_identity \
                or freeze_port is not authority.ranking_freeze:
            raise OrchestratorError("evaluation eligibility differs from actual PRIMARY_FROZEN lifecycle")
        entry = (
            authorization, freeze, freeze_port, opener, control_authority,
            started.identity, trace, authority.prerequisite,
        )
        with registry_lock:
            if owner not in active_lifecycles \
                    or owner in issued_lifecycles \
                    or owner in evaluation_eligibilities:
                raise OrchestratorError("lifecycle authorization was already registered")
            evaluation_eligibilities[owner] = entry

    def claim_evaluation_issuance(
        owner: object, authorization: OutcomeAuthorization, freeze: RankingFreezeResult,
        freeze_port: IndependentRankingFreezePort, opener: SealedOutcomeOpener,
    ) -> bool:
        with registry_lock:
            entry = evaluation_eligibilities.get(owner)
            if entry is None or owner in issued_lifecycles:
                return False
            (
                expected_authorization, expected_freeze, expected_freeze_port,
                expected_opener, control_authority, _started_identity, trace,
                prerequisite,
            ) = entry
            if authorization.canonical != expected_authorization.canonical \
                    or freeze != expected_freeze \
                    or freeze_port is not expected_freeze_port \
                    or opener is not expected_opener \
                    or not isinstance(control_authority, ControlAuthority) \
                    or trace != expected_primary_trace \
                    or prerequisite is not owner._authority.prerequisite:
                return False
            evaluation_eligibilities.pop(owner)
            issued_lifecycles.add(owner)
            return True

    def register_recovery(
        owner: object, machine: OrchestrationStateMachine,
        control_authority: ControlAuthority, profile_name: str,
    ) -> RecoveryProgressAuthority:
        if type(owner) is not orchestrator_type \
                or not isinstance(machine, OrchestrationStateMachine) \
                or not isinstance(control_authority, ControlAuthority) \
                or profile_name not in PROFILES:
            raise OrchestratorError("recovery progress lacks governed lifecycle authority")
        trace = tuple(machine.trace)
        progress = execution_progress_for(trace[-1], profile_name=profile_name)
        handoff = object.__new__(RecoveryProgressAuthority)
        registration = (owner, control_authority, profile_name, trace, progress)
        with registry_lock:
            recovery_registrations[handoff] = registration
        return handoff

    def execute(owner, request: OfficialExecutionRequest) -> OrchestrationResult:
        return internal_execute(
            owner, request, begin_lifecycle,
            register_evaluation_eligibility, register_recovery,
        )

    def request_recovery(
        owner, *, handoff: RecoveryProgressAuthority, snapshot,
        failure: FailureObservation, prerequisite: RecoveryPrerequisiteAuthority,
        no_live_owner: RecoveryAuthority,
    ) -> ControlRecord:
        if not isinstance(handoff, RecoveryProgressAuthority):
            raise OrchestratorError("recovery progress is not bound to this orchestrator lifecycle")
        if not isinstance(failure, FailureObservation):
            raise TypeError("recovery requires governed failure observations")
        with registry_lock:
            registration = recovery_registrations.get(handoff)
            if registration is None or registration[0] is not owner:
                raise OrchestratorError("recovery progress is not bound to this orchestrator lifecycle")
            recovery_registrations.pop(handoff)
        _, control_authority, _profile_name, _trace, progress = registration
        return recover_failed(
            owner._ports.control, snapshot, control_authority,
            failure.with_progress(progress), prerequisite, no_live_owner,
        )

    execute.__name__ = "execute"
    request_recovery.__name__ = "request_recovery"
    claim_evaluation_issuance.__name__ = "_claim_evaluation_issuance"
    orchestrator_type.execute = execute
    orchestrator_type.request_recovery = request_recovery
    orchestrator_type._claim_evaluation_issuance = claim_evaluation_issuance
    return orchestrator_type


OfficialOrchestrator = _bind_official_lifecycle_authority(OfficialOrchestrator)
del _bind_official_lifecycle_authority


__all__ = [
    "AuthenticatedLaunchInputs", "CharacterizationFreezeResult", "CharacterizationWorker",
    "CurrentReadinessResolver", "EvaluationWorker", "FailureObservation",
    "LaunchInputAuthenticator", "LaunchInputPreparer", "LaunchPrerequisiteAuthority",
    "LaunchRestartRequired", "LaunchSmokeRunner", "OfficialExecutionRequest",
    "OfficialOrchestrator", "OrchestrationIncomplete", "OrchestrationResult",
    "OrchestrationStateMachine", "OrchestratorError", "OrchestratorPorts", "OrchestratorState",
    "PreparedLaunchInputs", "RankingExecutionCapability", "RankingWorker",
    "RecoveryProgressAuthority", "ScientificTerminalCandidate", "SecondFetchPort",
    "Slice2PrerequisiteAuthority", "TerminalEvidenceAuthority", "TerminalEvidenceContext",
    "ValidatedTerminalEvidence",
    "execution_progress_for", "validate_authenticated_launch_inputs",
]
