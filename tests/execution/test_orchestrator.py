from __future__ import annotations

import copy
import hashlib
import itertools
import threading

import pytest

from orev3.execution.attempts import AllocationDisposition, AllocationTransactionResult, build_allocation_bundle
from orev3.execution.canonical import canonical_bytes, domain_identity
from orev3.execution.control_storage import (
    AppendDisposition, AppendResult, ControlAuthority, ControlStorageObservation,
    RecoveryAuthority, RecoveryPrerequisiteAuthority, reconstruct_control_history,
)
import orev3.execution.orchestrator as orchestrator_module
import orev3.execution.outcome_gate as outcome_gate_module
from orev3.execution.orchestrator import (
    AuthenticatedLaunchInputs, CharacterizationFreezeResult, FailureObservation,
    LaunchPrerequisiteAuthority, LaunchRestartRequired, OfficialExecutionRequest,
    OfficialOrchestrator, OrchestrationIncomplete, OrchestrationStateMachine,
    OrchestratorError, OrchestratorPorts, OrchestratorState, PreparedLaunchInputs,
    RankingExecutionCapability, ScientificTerminalCandidate, TerminalEvidenceContext,
    Slice2PrerequisiteAuthority, ValidatedTerminalEvidence,
)
from orev3.execution.outcome_gate import (
    OutcomeAuthorization, OutcomeGateError, RankingAuthority, RankingCandidate, RankingFreezeResult,
)
from orev3.execution.readiness import RemoteHeadRevalidation

SHA = tuple(str(index) * 64 for index in range(10))
GIT = "a" * 40
PROJECTION = canonical_bytes({"projection": "authenticated-outcome-blind"})
PROJECTION_SCHEMA = canonical_bytes({
    "additionalProperties": False,
    "properties": {"projection": {"type": "string"}},
    "required": ["projection"],
    "type": "object",
})
PROJECTION_SCHEMA_IDENTITY = domain_identity(
    "orev3:experiment-outcome-blind-projection-schema:v1\n",
    {
        "additionalProperties": False,
        "properties": {"projection": {"type": "string"}},
        "required": ["projection"],
        "type": "object",
    },
)
RANKING = canonical_bytes({"ranking": "independently-frozen"})
TERMINAL = canonical_bytes({"manifest": "independently-validated"})
PROJECTION_COMPONENT = SHA[5]
FREEZE_COMPONENT = SHA[6]
RECONSTRUCTION_COMPONENT = SHA[7]
AUTHORIZATION_COMPONENT = SHA[8]
TERMINAL_COMPONENT = SHA[9]
TERMINAL_CONTRACT = SHA[1]


def launch_authority(profile: str = "outcome_aware_v1", **changes: object):
    aware = profile == "outcome_aware_v1"
    projection_digest = hashlib.sha256(PROJECTION).hexdigest()
    values: dict[str, object] = {
        "allocation_authority_identity": SHA[0], "allocator_contract_identity": SHA[1],
        "authorization_contract_component_identity": AUTHORIZATION_COMPONENT if aware else None,
        "authorization_contract_identity": SHA[2] if aware else None,
        "dataset_identity": SHA[3], "experiment_identifier": "synthetic-experiment",
        "expected_external_input_snapshot_identities": (SHA[4],),
        "launch_authority_snapshot_identity": SHA[5],
        "outcome_blind_provenance_identity": SHA[6],
        "outcome_source_identity": SHA[7] if aware else None,
        "profile_identity": SHA[8], "profile_name": profile,
        "projection_component_identity": PROJECTION_COMPONENT,
        "projection_decoder_identity": SHA[3], "projection_field_names": ("projection",),
        "projection_schema_identity": PROJECTION_SCHEMA_IDENTITY,
        "projection_sha256": projection_digest,
        "ranking_contract_identity": SHA[9], "ranking_freeze_contract_identity": SHA[2],
        "ranking_freeze_component_identity": FREEZE_COMPONENT if aware else None,
        "ranking_reconstruction_component_identity": RECONSTRUCTION_COMPONENT if aware else None,
        "readiness_identity": SHA[0], "readiness_seal_commit": GIT,
        "remote_head_commit": GIT, "replay_identity": SHA[1], "source_commit": GIT,
        "terminal_evidence_component_identity": TERMINAL_COMPONENT,
        "terminal_manifest_contract_identity": TERMINAL_CONTRACT,
    }
    values["projection_identity"] = domain_identity(
        orchestrator_module.PROJECTION_IDENTITY_DOMAIN,
        {
            "dataset_identity": values["dataset_identity"],
            "external_input_snapshot_identities": list(values["expected_external_input_snapshot_identities"]),
            "launch_authority_snapshot_identity": values["launch_authority_snapshot_identity"],
            "projection_decoder_identity": values["projection_decoder_identity"],
            "projection_schema_identity": values["projection_schema_identity"],
            "projection_sha256": projection_digest,
        },
    )
    values.update(changes)
    return LaunchPrerequisiteAuthority(**values)  # type: ignore[arg-type]


def prerequisite_root(
    authority: LaunchPrerequisiteAuthority, **changes: object
) -> Slice2PrerequisiteAuthority:
    names = (
        "authorization_contract_component_identity", "authorization_contract_identity",
        "dataset_identity", "experiment_identifier", "outcome_blind_provenance_identity",
        "outcome_source_identity", "profile_identity", "profile_name",
        "projection_component_identity", "projection_decoder_identity",
        "projection_schema_identity", "ranking_contract_identity",
        "ranking_freeze_component_identity", "ranking_freeze_contract_identity",
        "ranking_reconstruction_component_identity", "readiness_identity",
        "readiness_seal_commit", "replay_identity", "source_commit",
        "terminal_evidence_component_identity", "terminal_manifest_contract_identity",
    )
    values = {name: getattr(authority, name) for name in names}
    values["projection_schema_canonical"] = PROJECTION_SCHEMA
    values.update(changes)
    return Slice2PrerequisiteAuthority(**values)  # type: ignore[arg-type]


def projection_authority(
    schema: dict[str, object], material: dict[str, object]
) -> tuple[LaunchPrerequisiteAuthority, bytes, bytes]:
    schema_canonical = canonical_bytes(schema)
    schema_identity = domain_identity(
        "orev3:experiment-outcome-blind-projection-schema:v1\n", schema
    )
    raw = canonical_bytes(material)
    digest = hashlib.sha256(raw).hexdigest()
    seed = launch_authority(
        projection_schema_identity=schema_identity, projection_sha256=digest
    )
    projection_identity = domain_identity(
        orchestrator_module.PROJECTION_IDENTITY_DOMAIN,
        {
            "dataset_identity": seed.dataset_identity,
            "external_input_snapshot_identities": list(
                seed.expected_external_input_snapshot_identities
            ),
            "launch_authority_snapshot_identity": seed.launch_authority_snapshot_identity,
            "projection_decoder_identity": seed.projection_decoder_identity,
            "projection_schema_identity": schema_identity,
            "projection_sha256": digest,
        },
    )
    authority = launch_authority(
        projection_identity=projection_identity,
        projection_schema_identity=schema_identity,
        projection_sha256=digest,
    )
    return authority, raw, schema_canonical


def official(configured: OrchestratorPorts) -> OfficialOrchestrator:
    return OfficialOrchestrator(
        prerequisite_root(configured.readiness.authority), configured  # type: ignore[attr-defined]
    )


class Opener:
    def __init__(self, *, fail=False): self.calls = 0; self.fail = fail
    def open_authorized_outcome(self, identity):
        self.calls += 1
        if self.fail: raise RuntimeError("synthetic opener failure")
        return b"synthetic-outcome"


class Resolver:
    def __init__(self, authority): self.authority = authority
    def resolve_current_launch(self, experiment_identifier): return self.authority


class Preparer:
    def __init__(self, authority, opener): self.authority = authority; self.opener = opener; self.raw = PROJECTION
    def prepare_launch_inputs(self, authority):
        return PreparedLaunchInputs(
            authority, (SHA[4],), self.raw,
            authority.projection_identity,
            hashlib.sha256(self.raw).hexdigest(), authority.projection_decoder_identity,
            authority.projection_schema_identity, self.opener,
        )


class Authenticator:
    def __init__(self, component_identity=PROJECTION_COMPONENT):
        self.calls = 0; self.component_identity = component_identity
    def authenticate_launch_inputs(self, authority, candidate):
        self.calls += 1
        return AuthenticatedLaunchInputs(
            authority, candidate.external_input_snapshot_identities, candidate.projection_canonical,
            candidate.projection_identity, candidate.projection_sha256,
            candidate.projection_decoder_identity, candidate.projection_schema_identity,
            domain_identity(orchestrator_module.PROJECTION_RECONSTRUCTION_DOMAIN, {
                "projection_component_identity": self.component_identity,
                "projection_identity": candidate.projection_identity,
                "projection_sha256": candidate.projection_sha256,
            }), candidate.outcome_opener,
        )


class Smoke:
    def __init__(self): self.calls = 0
    def run_launch_smoke(self, prepared): self.calls += 1


class SecondFetch:
    def __init__(self, result=RemoteHeadRevalidation.UNCHANGED): self.result=result
    def revalidate_remote_head(self, authority): return self.result


class Allocator:
    _ordinals = itertools.count(10_000)

    def __init__(self, ordinal=None):
        self.calls=0; self.last_bundle=None
        self.ordinal = next(self._ordinals) if ordinal is None else ordinal
    def atomic_allocate(self, request):
        self.calls += 1
        bundle=build_allocation_bundle(request,self.ordinal); self.last_bundle=bundle
        return AllocationTransactionResult(AllocationDisposition.COMMITTED,self.ordinal,bundle)


class ControlStore:
    def __init__(self): self.observations=[]; self.append_results=[]; self.recovery_calls=0
    def read_snapshot(self, attempt_identity): return reconstruct_control_history(tuple(self.observations))
    def compare_and_append(self, operation):
        if self.append_results:
            disposition=self.append_results.pop(0)
            if disposition is not AppendDisposition.COMMITTED: return AppendResult(disposition,None)
        self.observations.append(operation.proposed_observation)
        return AppendResult(AppendDisposition.COMMITTED,operation.record)
    def compare_fence_no_live_owner_and_append_failed(self, operation):
        self.recovery_calls += 1
        self.observations.append(operation.proposed_observation)
        return AppendResult(AppendDisposition.COMMITTED,operation.failed_record)


class Ranking:
    def __init__(self): self.calls=0; self.capability=None
    def run_ranking(self, capability): self.calls+=1; self.capability=capability; return RankingCandidate(RANKING)


class FreezePort:
    def __init__(self, freeze_component_identity=FREEZE_COMPONENT,
                 reconstruction_component_identity=RECONSTRUCTION_COMPONENT):
        self.raw=None; self.authority=None; self.calls=0
        self.freeze_component_identity=freeze_component_identity
        self.reconstruction_component_identity=reconstruction_component_identity
    def freeze_and_reconstruct(self, candidate, expected):
        self.calls += 1; self.raw=candidate.raw
        self.authority=RankingAuthority(
            expected.attempt_identity,expected.dataset_identity,expected.external_input_snapshot_identities,
            expected.outcome_blind_provenance_identity,expected.profile_identity,
            domain_identity("orev3:test-ranking:v1\n",{"sha256":hashlib.sha256(candidate.raw).hexdigest()}),
            expected.ranking_contract_identity, self.freeze_component_identity,
            expected.ranking_freeze_contract_identity, self.reconstruction_component_identity,
            expected.replay_identity)
        return RankingFreezeResult(self.authority,len(self.raw),hashlib.sha256(self.raw).hexdigest(),SHA[5])
    def read_and_reconstruct(self, freeze): return self.raw,self.authority


class ContractAuthority:
    def __init__(self, identity=SHA[2], component_identity=AUTHORIZATION_COMPONENT):
        self.identity=identity; self.component_identity=component_identity
    def reconstruct_authorization_contract(self, readiness_identity, profile_identity): return self.identity


class Evaluation:
    def __init__(self): self.calls=0; self.capability=None; self.authorization=None
    def evaluate(self, capability, authorization):
        self.calls += 1; self.capability=capability; self.authorization=authorization
        capability.open_outcomes(authorization)
        return ScientificTerminalCandidate("VALID",TERMINAL)


class Characterization:
    def __init__(self): self.capability=None
    def run_characterization(self, capability):
        self.capability=capability
        return CharacterizationFreezeResult(ScientificTerminalCandidate("VALID",TERMINAL))


class TerminalAuthority:
    def __init__(self, component_identity=TERMINAL_COMPONENT,
                 manifest_contract_identity=TERMINAL_CONTRACT):
        self.reject=False; self.component_identity=component_identity
        self.manifest_contract_identity=manifest_contract_identity
    def reconstruct_terminal_evidence(self,candidate,expected):
        if self.reject: raise OrchestratorError("scientific evidence did not reconstruct")
        digest=hashlib.sha256(candidate.raw).hexdigest()
        evidence=ValidatedTerminalEvidence(candidate.disposition,
            domain_identity("orev3:test-terminal:v1\n",{"sha256":digest}),digest,expected)
        return candidate.raw,evidence


def ports(profile="outcome_aware_v1", *, second=None, control=None, contract=None,
          terminal=None, allocator=None):
    authority=launch_authority(profile); opener=Opener() if profile=="outcome_aware_v1" else None
    return authority,opener,OrchestratorPorts(
        readiness=Resolver(authority), preparation=Preparer(authority,opener),
        launch_authenticator=Authenticator(), smoke=Smoke(), second_fetch=second or SecondFetch(),
        allocator=allocator or Allocator(), control=control or ControlStore(),
        terminal_evidence=terminal or TerminalAuthority(),
        ranking_freeze=FreezePort() if profile=="outcome_aware_v1" else None,
        authorization_contract=contract or (ContractAuthority() if profile=="outcome_aware_v1" else None),
        ranking=Ranking() if profile=="outcome_aware_v1" else None,
        characterization=Characterization() if profile!="outcome_aware_v1" else None,
        evaluation=Evaluation() if profile=="outcome_aware_v1" else None,
    )


def test_bound_projection_authority_rejects_caller_selected_authenticator() -> None:
    authority, _, configured = ports()
    object.__setattr__(configured, "launch_authenticator", Authenticator(SHA[0]))
    with pytest.raises(OrchestratorError, match="projection implementation differs"):
        official(configured).execute(OfficialExecutionRequest(authority.experiment_identifier))
    assert configured.allocator.calls == 0  # type: ignore[attr-defined]


def test_colluding_ranking_wrappers_cannot_replace_governed_components() -> None:
    authority, _, configured = ports()
    object.__setattr__(configured, "ranking_freeze", FreezePort(SHA[0], SHA[1]))
    with pytest.raises(OrchestratorError, match="ranking freeze implementation differs"):
        official(configured).execute(OfficialExecutionRequest(authority.experiment_identifier))
    assert configured.allocator.calls == 0  # type: ignore[attr-defined]


def test_colluding_terminal_validator_cannot_replace_governed_component() -> None:
    authority, _, configured = ports(terminal=TerminalAuthority(SHA[0], SHA[1]))
    with pytest.raises(OrchestratorError, match="terminal implementation differs"):
        official(configured).execute(OfficialExecutionRequest(authority.experiment_identifier))
    assert configured.allocator.calls == 0  # type: ignore[attr-defined]


def test_caller_selected_authorization_component_is_rejected() -> None:
    authority, _, configured = ports(contract=ContractAuthority(SHA[2], SHA[0]))
    with pytest.raises(OrchestratorError, match="authorization-contract implementation differs"):
        official(configured).execute(OfficialExecutionRequest(authority.experiment_identifier))
    assert configured.allocator.calls == 0  # type: ignore[attr-defined]


def test_state_machine_advance_cannot_mint_ranking_authority() -> None:
    machine = OrchestrationStateMachine()
    for state in (OrchestratorState.CURRENT_READY, OrchestratorState.LAUNCH_PREPARED,
                  OrchestratorState.SMOKE_PASSED, OrchestratorState.SECOND_FETCH_PASSED,
                  OrchestratorState.ALLOCATED, OrchestratorState.STARTED):
        machine.advance(state)
    assert not hasattr(official(ports()[2]), "_issuer")
    with pytest.raises(OrchestratorError, match="durable STARTED"):
        RankingExecutionCapability(machine)


def test_legal_lifecycle_and_independent_terminalization() -> None:
    _,opener,configured=ports()
    result=official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert result.trace==tuple(OrchestratorState)
    assert result.terminal_record.state=="VALID" and opener.calls==1
    assert configured.ranking_freeze.calls==1  # type: ignore[union-attr]


def test_changed_second_fetch_prevents_allocation() -> None:
    _,_,configured=ports(second=SecondFetch(RemoteHeadRevalidation.RESTART_REQUIRED))
    with pytest.raises(LaunchRestartRequired):
        official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert configured.allocator.calls==0  # type: ignore[attr-defined]


@pytest.mark.parametrize("disposition",(AppendDisposition.STALE,AppendDisposition.UNAVAILABLE,AppendDisposition.AMBIGUOUS))
def test_no_ranking_before_durable_started(disposition) -> None:
    control=ControlStore(); control.append_results=[disposition]
    _,opener,configured=ports(control=control)
    with pytest.raises(OrchestrationIncomplete):
        official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert configured.ranking.calls==0 and opener.calls==0  # type: ignore[union-attr]


def test_module_token_removed_and_direct_capability_fails() -> None:
    assert not hasattr(orchestrator_module,"_CAPABILITY_TOKEN")
    _,_,configured=ports()
    candidate=configured.preparation.prepare_launch_inputs(configured.readiness.authority)  # type: ignore[attr-defined]
    authenticated=configured.launch_authenticator.authenticate_launch_inputs(candidate.authority,candidate)
    fake_authority=ControlAuthority(SHA[0],SHA[1],"official",(SHA[4],),SHA[5],1,SHA[8],SHA[0],GIT,GIT,GIT)
    with pytest.raises(OrchestratorError,match="orchestrator-issued"):
        RankingExecutionCapability(object(),control_authority=fake_authority,launch=authenticated)


@pytest.mark.parametrize("key",("winning_square","won","outcome","label","winner","result_code","target_value"))
def test_outcome_shaped_projection_rejected_before_allocation(key) -> None:
    _,_,configured=ports(); configured.preparation.raw=canonical_bytes({key:1})  # type: ignore[attr-defined]
    with pytest.raises(OrchestratorError,match="projection digest differs|exact fields"):
        official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert configured.allocator.calls==0  # type: ignore[attr-defined]


def test_worker_cannot_supply_colluding_reconstructor() -> None:
    assert set(RankingCandidate.__dataclass_fields__)=={"raw"}
    with pytest.raises(TypeError):
        RankingCandidate(RANKING,reconstructor=object())  # type: ignore[call-arg]


def test_fake_terminal_hashes_cannot_bypass_independent_validator() -> None:
    terminal=TerminalAuthority(); terminal.reject=True
    _,_,configured=ports(terminal=terminal)
    with pytest.raises(OrchestrationIncomplete,match="scientific evidence"):
        official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert len(configured.control.observations)==1  # type: ignore[attr-defined]


def test_authorization_contract_substitution_fails() -> None:
    _,opener,configured=ports(contract=ContractAuthority(SHA[9]))
    with pytest.raises(OrchestrationIncomplete,match="contract differs"):
        official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert opener.calls==0


def test_characterization_has_no_gate_ports_or_outcome() -> None:
    _,opener,configured=ports("outcome_blind_characterization_v1")
    result=official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert opener is None and result.authorization is None
    cap=configured.characterization.capability  # type: ignore[union-attr]
    assert not any("outcome" in name or "authorization" in name for name in dir(cap))


def test_state_machine_illegal_transition_and_post_authorization_close() -> None:
    machine=OrchestrationStateMachine()
    with pytest.raises(OrchestratorError): machine.advance(OrchestratorState.ALLOCATED)
    for state in (OrchestratorState.CURRENT_READY,OrchestratorState.LAUNCH_PREPARED,
                  OrchestratorState.SMOKE_PASSED,OrchestratorState.SECOND_FETCH_PASSED,
                  OrchestratorState.ALLOCATED,OrchestratorState.STARTED,
                  OrchestratorState.PRIMARY_FROZEN,OrchestratorState.AUTHORIZED): machine.advance(state)
    with pytest.raises(OrchestratorError): machine.advance(OrchestratorState.STARTED)


def test_recovery_progress_is_trace_derived_and_one_handoff_use() -> None:
    class FailingRanking(Ranking):
        def run_ranking(self,capability): super().run_ranking(capability); raise RuntimeError("ranking stopped")
    _,_,configured=ports(); configured=copy.copy(configured)
    object.__setattr__(configured,"ranking",FailingRanking())
    orchestrator=official(configured)
    with pytest.raises(OrchestrationIncomplete) as caught:
        orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
    handoff=caught.value.handoff
    assert not hasattr(handoff, "trace") and not hasattr(handoff, "control_authority")
    started=configured.control.observations[0].record  # type: ignore[attr-defined]
    material=started.authority_material
    material["external_input_snapshot_identities"]=tuple(material["external_input_snapshot_identities"])
    control_authority=ControlAuthority(**material)
    snapshot=configured.control.read_snapshot(control_authority.attempt_identity)
    prerequisite=RecoveryPrerequisiteAuthority(SHA[0],control_authority.attempt_identity,SHA[2],SHA[3],SHA[4],snapshot.snapshot_identity)
    no_live=RecoveryAuthority(SHA[0],control_authority.attempt_identity,SHA[3],SHA[4],snapshot.snapshot_identity)
    with pytest.raises(OrchestratorError, match="non-copyable"):
        copy.copy(handoff)
    with pytest.raises(OrchestratorError, match="not bound"):
        official(ports()[2]).request_recovery(
            handoff=handoff, snapshot=snapshot, failure=FailureObservation(owner_terminated=True),
            prerequisite=prerequisite, no_live_owner=no_live,
        )
    failed=orchestrator.request_recovery(handoff=handoff,snapshot=snapshot,
        failure=FailureObservation(owner_terminated=True),prerequisite=prerequisite,no_live_owner=no_live)
    assert failed.material["state"]["failure_control_evidence"]["failure_boundary"]=="post_start_pre_ranking_freeze"
    with pytest.raises(OrchestratorError,match="not bound"):
        orchestrator.request_recovery(handoff=handoff,snapshot=snapshot,
            failure=FailureObservation(owner_terminated=True),prerequisite=prerequisite,no_live_owner=no_live)


def _recover_from_handoff(orchestrator, configured, handoff):
    started = configured.control.observations[0].record
    material = started.authority_material
    material["external_input_snapshot_identities"] = tuple(
        material["external_input_snapshot_identities"]
    )
    control_authority = ControlAuthority(**material)
    snapshot = configured.control.read_snapshot(control_authority.attempt_identity)
    prerequisite = RecoveryPrerequisiteAuthority(
        SHA[0], control_authority.attempt_identity, SHA[2], SHA[3], SHA[4],
        snapshot.snapshot_identity,
    )
    no_live = RecoveryAuthority(
        SHA[0], control_authority.attempt_identity, SHA[3], SHA[4],
        snapshot.snapshot_identity,
    )
    return orchestrator.request_recovery(
        handoff=handoff, snapshot=snapshot,
        failure=FailureObservation(owner_terminated=True),
        prerequisite=prerequisite, no_live_owner=no_live,
    )


def test_recovery_handoff_snapshots_started_progress_despite_later_interaction() -> None:
    class FailingRanking(Ranking):
        def run_ranking(self, capability):
            super().run_ranking(capability)
            raise RuntimeError("ranking stopped")

    _, _, configured = ports(allocator=Allocator(50_010))
    object.__setattr__(configured, "ranking", FailingRanking())
    orchestrator = official(configured)
    with pytest.raises(OrchestrationIncomplete) as caught:
        orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
    handoff = caught.value.handoff

    unrelated = OrchestrationStateMachine()
    for state in (
        OrchestratorState.CURRENT_READY, OrchestratorState.LAUNCH_PREPARED,
        OrchestratorState.SMOKE_PASSED, OrchestratorState.SECOND_FETCH_PASSED,
        OrchestratorState.ALLOCATED, OrchestratorState.STARTED,
        OrchestratorState.PRIMARY_FROZEN, OrchestratorState.AUTHORIZED,
        OrchestratorState.EVALUATED, OrchestratorState.TERMINALIZING,
        OrchestratorState.TERMINAL,
    ):
        unrelated.advance(state)

    failed = _recover_from_handoff(orchestrator, configured, handoff)
    evidence = failed.material["state"]["failure_control_evidence"]
    assert evidence["failure_boundary"] == "post_start_pre_ranking_freeze"


def test_recovery_handoff_created_later_snapshots_authorized_progress() -> None:
    class FailingEvaluation(Evaluation):
        def evaluate(self, capability, authorization):
            capability.open_outcomes(authorization)
            raise RuntimeError("evaluation stopped after authorization")

    _, _, configured = ports(allocator=Allocator(50_011))
    object.__setattr__(configured, "evaluation", FailingEvaluation())
    orchestrator = official(configured)
    with pytest.raises(OrchestrationIncomplete) as caught:
        orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))

    failed = _recover_from_handoff(orchestrator, configured, caught.value.handoff)
    evidence = failed.material["state"]["failure_control_evidence"]
    assert evidence["failure_boundary"] == "post_authorization_pre_terminal"


def test_official_entry_accepts_only_identifier() -> None:
    with pytest.raises(TypeError):
        OfficialExecutionRequest("synthetic-experiment",source_commit=GIT)  # type: ignore[call-arg]


def test_full_execution_root_substitution_rejected_before_allocation() -> None:
    authority_a, _, configured = ports()
    root_a = prerequisite_root(authority_a)
    authority_b = launch_authority(
        projection_component_identity=SHA[0],
        ranking_freeze_component_identity=SHA[1],
        ranking_reconstruction_component_identity=SHA[2],
        authorization_contract_component_identity=SHA[3],
        authorization_contract_identity=SHA[4],
        terminal_evidence_component_identity=SHA[5],
        terminal_manifest_contract_identity=SHA[6],
    )
    configured.readiness.authority = authority_b  # type: ignore[attr-defined]
    configured.preparation.authority = authority_b  # type: ignore[attr-defined]
    object.__setattr__(configured, "launch_authenticator", Authenticator(SHA[0]))
    object.__setattr__(configured, "ranking_freeze", FreezePort(SHA[1], SHA[2]))
    object.__setattr__(configured, "authorization_contract", ContractAuthority(SHA[4], SHA[3]))
    object.__setattr__(configured, "terminal_evidence", TerminalAuthority(SHA[5], SHA[6]))
    with pytest.raises(OrchestratorError, match="prerequisite root"):
        OfficialOrchestrator(root_a, configured)
    assert configured.allocator.calls == 0 and configured.ranking.calls == 0  # type: ignore[attr-defined,union-attr]


@pytest.mark.parametrize(
    "nested",
    (
        {"metadata": {"result_code": "won", "target_value": 17}},
        {"metadata": {"winner": 4}},
        {"metadata": {"winning_square": 4}},
        {"metadata": {"won": True}},
        {"metadata": {"label": 1}},
        {"metadata": {"outcome": "x"}},
    ),
)
def test_closed_projection_schema_rejects_nested_aliases_before_allocation(nested) -> None:
    authority_a, _, configured = ports()
    root_a = prerequisite_root(authority_a)
    raw = canonical_bytes({"projection": nested})
    digest = hashlib.sha256(raw).hexdigest()
    authority_b = launch_authority(
        projection_sha256=digest,
        projection_identity=domain_identity(
            orchestrator_module.PROJECTION_IDENTITY_DOMAIN,
            {
                "dataset_identity": authority_a.dataset_identity,
                "external_input_snapshot_identities": list(
                    authority_a.expected_external_input_snapshot_identities
                ),
                "launch_authority_snapshot_identity": authority_a.launch_authority_snapshot_identity,
                "projection_decoder_identity": authority_a.projection_decoder_identity,
                "projection_schema_identity": authority_a.projection_schema_identity,
                "projection_sha256": digest,
            },
        ),
    )
    configured.readiness.authority = authority_b  # type: ignore[attr-defined]
    configured.preparation.authority = authority_b  # type: ignore[attr-defined]
    configured.preparation.raw = raw  # type: ignore[attr-defined]
    with pytest.raises(OrchestratorError, match="schema|projection"):
        OfficialOrchestrator(root_a, configured).execute(
            OfficialExecutionRequest("synthetic-experiment")
        )
    assert configured.allocator.calls == 0  # type: ignore[attr-defined]


def test_fixed_root_rejects_colluding_freezer_and_terminal_and_contract_graphs() -> None:
    authority, _, configured = ports()
    root = prerequisite_root(authority)
    for field, replacement, message in (
        ("ranking_freeze", FreezePort(SHA[0], SHA[1]), "ranking freeze implementation"),
        ("terminal_evidence", TerminalAuthority(SHA[0], SHA[1]), "terminal implementation"),
        ("authorization_contract", ContractAuthority(SHA[1], SHA[0]), "authorization-contract implementation"),
    ):
        changed = copy.copy(configured)
        object.__setattr__(changed, field, replacement)
        with pytest.raises(OrchestratorError, match=message):
            OfficialOrchestrator(root, changed)
        assert changed.allocator.calls == 0  # type: ignore[attr-defined]


def test_gate_state_cannot_be_rebound_and_forged_wrapper_cannot_open() -> None:
    _, opener, configured = ports()
    result = official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    capability = configured.evaluation.capability  # type: ignore[union-attr]
    authorization = configured.evaluation.authorization  # type: ignore[union-attr]
    assert capability.__slots__ == ("_handle", "_sealed")
    assert not hasattr(capability, "_state")
    for name in capability.__slots__:
        retained = object.__getattribute__(capability, name)
        assert not hasattr(retained, "open_authorized_outcome")
        assert not callable(retained)
    forged = object.__new__(type(capability))
    object.__setattr__(forged, "_handle", capability._handle)
    object.__setattr__(forged, "_sealed", True)
    with pytest.raises(OutcomeGateError, match="exact gate-owned"):
        forged.open_outcomes(authorization)
    with pytest.raises(OutcomeGateError, match="exact gate-owned"):
        outcome_gate_module._consume_and_open_evaluation(
            forged, capability._handle, authorization
        )
    assert not hasattr(outcome_gate_module, "_EVALUATION_BROKER")
    unrelated = object.__new__(type(capability))
    object.__setattr__(unrelated, "_handle", object())
    object.__setattr__(unrelated, "_sealed", True)
    with pytest.raises(OutcomeGateError, match="exact gate-owned"):
        unrelated.open_outcomes(authorization)
    with pytest.raises(OutcomeGateError, match="immutable"):
        capability._handle = object()
    with pytest.raises(OutcomeGateError, match="already consumed"):
        capability.open_outcomes(authorization)
    assert result.authorization == authorization and opener.calls == 1


@pytest.mark.parametrize(
    "schema,material",
    (
        (
            {
                "additionalProperties": False,
                "properties": {"projection": {}},
                "required": ["projection"],
                "type": "object",
            },
            {"projection": {"metadata": {"result_code": "won", "target_value": 17}}},
        ),
        (
            {
                "additionalProperties": False,
                "properties": {
                    "projection": {"properties": {"signal": {"type": "string"}}, "type": "object"}
                },
                "required": ["projection"],
                "type": "object",
            },
            {"projection": {"signal": "outcome-blind", "winner": 4}},
        ),
        (
            {
                "additionalProperties": False,
                "properties": {
                    "projection": {
                        "additionalProperties": False,
                        "patternProperties": {".*": {"type": "string"}},
                        "properties": {},
                        "type": "object",
                    }
                },
                "required": ["projection"],
                "type": "object",
            },
            {"projection": {"outcome": "won"}},
        ),
        (
            {
                "additionalProperties": False,
                "properties": {"projection": {"items": {}, "type": "array"}},
                "required": ["projection"],
                "type": "object",
            },
            {"projection": [{"label": 1}]},
        ),
        (
            {
                "additionalProperties": False,
                "properties": {
                    "projection": {
                        "oneOf": [{"type": "string"}, {}],
                    }
                },
                "required": ["projection"],
                "type": "object",
            },
            {"projection": {"result": "won"}},
        ),
        (
            {
                "additionalProperties": False,
                "properties": {"projection": {"type": "string", "unevaluatedProperties": True}},
                "required": ["projection"],
                "type": "object",
            },
            {"projection": "outcome-blind"},
        ),
    ),
)
def test_projection_root_rejects_every_unconstrained_schema_path(
    schema: dict[str, object], material: dict[str, object]
) -> None:
    authority, _, schema_canonical = projection_authority(schema, material)
    with pytest.raises(OrchestratorError, match="projection schema|projection-schema|closed|supported"):
        prerequisite_root(authority, projection_schema_canonical=schema_canonical)


def test_recursively_closed_projection_reaches_ranking_unchanged() -> None:
    schema = {
        "additionalProperties": False,
        "properties": {
            "projection": {
                "additionalProperties": False,
                "properties": {
                    "signals": {"items": {"type": "integer"}, "type": "array"}
                },
                "required": ["signals"],
                "type": "object",
            }
        },
        "required": ["projection"],
        "type": "object",
    }
    material = {"projection": {"signals": [1, 2, 3]}}
    authority, raw, schema_canonical = projection_authority(schema, material)
    _, _, configured = ports()
    configured.readiness.authority = authority  # type: ignore[attr-defined]
    configured.preparation.authority = authority  # type: ignore[attr-defined]
    configured.preparation.raw = raw  # type: ignore[attr-defined]
    root = prerequisite_root(authority, projection_schema_canonical=schema_canonical)
    OfficialOrchestrator(root, configured).execute(
        OfficialExecutionRequest("synthetic-experiment")
    )
    assert configured.ranking.capability.projection_canonical == raw  # type: ignore[union-attr]


def test_evaluation_capability_copy_pickle_and_opener_failure_are_fail_closed() -> None:
    import pickle

    _, _, configured = ports()
    configured.preparation.opener.fail = True  # type: ignore[attr-defined]
    orchestrator = official(configured)
    with pytest.raises(OrchestrationIncomplete, match="synthetic opener failure"):
        orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
    capability = configured.evaluation.capability  # type: ignore[union-attr]
    authorization = configured.evaluation.authorization  # type: ignore[union-attr]
    for operation in (
        lambda: copy.copy(capability),
        lambda: copy.deepcopy(capability),
        lambda: pickle.dumps(capability),
    ):
        with pytest.raises(OutcomeGateError):
            operation()
    assert capability.consumed
    with pytest.raises(OutcomeGateError, match="already consumed"):
        capability.open_outcomes(authorization)
    assert configured.preparation.opener.calls == 1  # type: ignore[attr-defined]


def test_same_orchestrator_cannot_issue_second_lifecycle() -> None:
    _, opener, configured = ports()
    orchestrator = official(configured)
    orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
    with pytest.raises(OrchestratorError, match="already owns"):
        orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
    assert opener.calls == 1


def test_concurrent_same_orchestrator_execution_has_one_issuance_winner() -> None:
    _, opener, configured = ports()
    orchestrator = official(configured)
    barrier = threading.Barrier(3)
    results: list[str] = []

    def execute() -> None:
        barrier.wait()
        try:
            orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
            results.append("issued")
        except OrchestratorError:
            results.append("rejected")

    threads = [threading.Thread(target=execute) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["issued", "rejected"] and opener.calls == 1


def test_concurrent_capability_opening_has_one_winner() -> None:
    class ConcurrentEvaluation(Evaluation):
        def evaluate(self, capability, authorization):
            self.calls += 1
            self.capability = capability
            self.authorization = authorization
            barrier = threading.Barrier(3)
            outcomes: list[str] = []

            def open_once() -> None:
                barrier.wait()
                try:
                    capability.open_outcomes(authorization)
                    outcomes.append("opened")
                except OutcomeGateError:
                    outcomes.append("rejected")

            threads = [threading.Thread(target=open_once) for _ in range(2)]
            for thread in threads:
                thread.start()
            barrier.wait()
            for thread in threads:
                thread.join()
            assert sorted(outcomes) == ["opened", "rejected"]
            return ScientificTerminalCandidate("VALID", TERMINAL)

    _, opener, configured = ports()
    object.__setattr__(configured, "evaluation", ConcurrentEvaluation())
    official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert opener.calls == 1


def test_execution_ports_alone_cannot_supply_prerequisite_root() -> None:
    configured = ports()[2]
    with pytest.raises(TypeError, match="missing 1 required positional argument"):
        OfficialOrchestrator(configured)  # type: ignore[call-arg]


def test_module_issuer_cannot_establish_lifecycle_authority() -> None:
    _, _, configured = ports(allocator=Allocator(50_001))
    orchestrator = official(configured)
    result = orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
    assert result.authorization is not None
    equivalent = OutcomeAuthorization.from_canonical(result.authorization.canonical)
    freezer = configured.ranking_freeze
    assert freezer is not None and freezer.raw is not None and freezer.authority is not None
    freeze = RankingFreezeResult(
        freezer.authority, len(freezer.raw), hashlib.sha256(freezer.raw).hexdigest(), SHA[5]
    )
    for lifecycle in (object(), official(ports(allocator=Allocator(50_099))[2])):
        with pytest.raises(OutcomeGateError, match="governed lifecycle"):
            outcome_gate_module._issue_evaluation_capability(
                lifecycle, equivalent, freeze, freezer, Opener()
            )
    lifecycle = official(ports(allocator=Allocator(50_098))[2])
    with pytest.raises(OrchestratorError, match="immutable"):
        lifecycle._pending_gate_authority = (equivalent, freeze, freezer, Opener())


def test_same_authorization_cannot_be_issued_by_another_governed_lifecycle() -> None:
    _, opener_a, configured_a = ports(allocator=Allocator(50_002))
    _, opener_b, configured_b = ports(allocator=Allocator(50_002))
    first = official(configured_a).execute(OfficialExecutionRequest("synthetic-experiment"))
    with pytest.raises(OrchestrationIncomplete, match="already issued"):
        official(configured_b).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert first.authorization is not None
    assert opener_a.calls == 1 and opener_b.calls == 0


def test_concurrent_same_authorization_issuance_has_one_winner() -> None:
    barrier = threading.Barrier(2)

    class BarrierContract(ContractAuthority):
        def reconstruct_authorization_contract(self, readiness_identity, profile_identity):
            value = super().reconstruct_authorization_contract(readiness_identity, profile_identity)
            barrier.wait()
            return value

    _, opener_a, configured_a = ports(
        allocator=Allocator(50_003), contract=BarrierContract()
    )
    _, opener_b, configured_b = ports(
        allocator=Allocator(50_003), contract=BarrierContract()
    )
    orchestrators = (official(configured_a), official(configured_b))
    outcomes: list[str] = []

    def execute(orchestrator):
        try:
            orchestrator.execute(OfficialExecutionRequest("synthetic-experiment"))
            outcomes.append("issued")
        except OrchestrationIncomplete as exc:
            assert "already issued" in str(exc)
            outcomes.append("rejected")

    threads = [threading.Thread(target=execute, args=(item,)) for item in orchestrators]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["issued", "rejected"]
    assert opener_a.calls + opener_b.calls == 1


def test_opener_failure_does_not_release_authorization_for_reissuance() -> None:
    _, opener_a, configured_a = ports(allocator=Allocator(50_004))
    opener_a.fail = True
    _, opener_b, configured_b = ports(allocator=Allocator(50_004))
    with pytest.raises(OrchestrationIncomplete, match="synthetic opener failure"):
        official(configured_a).execute(OfficialExecutionRequest("synthetic-experiment"))
    with pytest.raises(OrchestrationIncomplete, match="already issued"):
        official(configured_b).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert opener_a.calls == 1 and opener_b.calls == 0


def test_projection_schema_bytes_and_identity_must_reconstruct_in_root() -> None:
    authority = launch_authority()
    with pytest.raises(OrchestratorError, match="schema identity does not reconstruct"):
        prerequisite_root(authority, projection_schema_identity=SHA[0])


def test_characterization_has_no_gate_module_surface() -> None:
    import orev3.execution.outcome_gate as gate_module

    _, _, configured = ports("outcome_blind_characterization_v1")
    official(configured).execute(OfficialExecutionRequest("synthetic-experiment"))
    assert not hasattr(gate_module, "OutcomeGateLifecycle")
    with pytest.raises(OutcomeGateError, match="orchestrator-issued"):
        gate_module.EvaluationCapability(object())
