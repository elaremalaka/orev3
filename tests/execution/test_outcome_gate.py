from __future__ import annotations

import hashlib

import pytest

from orev3.execution.canonical import canonical_bytes, domain_identity
import orev3.execution.outcome_gate as gate_module
from orev3.execution.outcome_gate import (
    EvaluationCapability, OutcomeAuthorization, OutcomeGateError,
    OutcomeGatePrerequisiteAuthority, RankingAuthority, RankingCandidate,
    RankingContextAuthority, RankingFreezeResult, build_outcome_authorization,
    validate_outcome_gate_authority,
)

SHA = tuple(str(index) * 64 for index in range(10))
GIT = "a" * 40
RAW = canonical_bytes({"ranking": "independently-frozen"})
AUTH_COMPONENT = SHA[7]
FREEZE_COMPONENT = SHA[8]
RECON_COMPONENT = SHA[6]


def prerequisite(**changes: object) -> OutcomeGatePrerequisiteAuthority:
    values: dict[str, object] = {
        "authorization_contract_component_identity": AUTH_COMPONENT,
        "authorization_contract_identity": SHA[0],
        "attempt_identity": SHA[1],
        "dataset_identity": SHA[2],
        "external_input_snapshot_identities": (SHA[3], SHA[4]),
        "launch_authority_snapshot_identity": SHA[0],
        "outcome_blind_provenance_identity": SHA[5],
        "outcome_source_identity": SHA[9],
        "profile_identity": SHA[6],
        "profile_name": "outcome_aware_v1",
        "ranking_contract_identity": SHA[8],
        "ranking_freeze_contract_identity": SHA[0],
        "ranking_freeze_component_identity": FREEZE_COMPONENT,
        "ranking_reconstruction_component_identity": RECON_COMPONENT,
        "readiness_identity": SHA[5],
        "readiness_seal_commit": GIT,
        "replay_identity": SHA[9],
        "source_commit": GIT,
    }
    values.update(changes)
    return OutcomeGatePrerequisiteAuthority(**values)  # type: ignore[arg-type]


class FreezePort:
    def __init__(self) -> None:
        self.freeze_component_identity = FREEZE_COMPONENT
        self.reconstruction_component_identity = RECON_COMPONENT
        self.raw = RAW
        self.authority = RankingAuthority(
            SHA[1], SHA[2], (SHA[3], SHA[4]), SHA[5], SHA[6], SHA[7], SHA[8],
            FREEZE_COMPONENT, SHA[0], RECON_COMPONENT, SHA[9],
        )

    def freeze_and_reconstruct(
        self, candidate: RankingCandidate, expected: RankingContextAuthority
    ) -> RankingFreezeResult:
        authority = RankingAuthority(
            expected.attempt_identity, expected.dataset_identity,
            expected.external_input_snapshot_identities,
            expected.outcome_blind_provenance_identity, expected.profile_identity,
            domain_identity(
                "orev3:test-ranking-artifact:v1\n",
                {"sha256": hashlib.sha256(candidate.raw).hexdigest()},
            ),
            expected.ranking_contract_identity, self.freeze_component_identity,
            expected.ranking_freeze_contract_identity,
            self.reconstruction_component_identity, expected.replay_identity,
        )
        self.raw = candidate.raw
        self.authority = authority
        return RankingFreezeResult(
            authority, len(candidate.raw), hashlib.sha256(candidate.raw).hexdigest(), SHA[4]
        )

    def read_and_reconstruct(self, freeze: RankingFreezeResult):
        return self.raw, self.authority


class ContractAuthority:
    def __init__(
        self, identity: str = SHA[0], component_identity: str = AUTH_COMPONENT
    ) -> None:
        self.identity = identity
        self.component_identity = component_identity

    def reconstruct_authorization_contract(
        self, readiness_identity: str, profile_identity: str
    ) -> str:
        assert readiness_identity == SHA[5] and profile_identity == SHA[6]
        return self.identity


class Opener:
    def open_authorized_outcome(self, outcome_source_identity: str):
        assert outcome_source_identity == SHA[9]
        return b"synthetic-outcome-sentinel"


def frozen() -> tuple[FreezePort, RankingFreezeResult]:
    port = FreezePort()
    result = RankingFreezeResult(
        port.authority, len(port.raw), hashlib.sha256(port.raw).hexdigest(), SHA[4]
    )
    return port, result


def test_authorization_known_answer_and_round_trip() -> None:
    port, freeze = frozen()
    ranking = validate_outcome_gate_authority(
        prerequisite(), freeze, Opener(), ContractAuthority(), port
    )
    authorization = build_outcome_authorization(prerequisite(), ranking)
    assert authorization.identity == "73e2460aaeff23af0d5ffa8b7ced1bb911fc566ba70efe9f786bec1e6322f3b2"
    assert OutcomeAuthorization.from_canonical(authorization.canonical) == authorization


def test_no_direct_gate_lifecycle_or_capability_constructor() -> None:
    assert not hasattr(gate_module, "OutcomeGateLifecycle")
    assert not hasattr(gate_module, "_issue_outcome_gate_invocation")
    assert not hasattr(gate_module, "authorize_outcomes")
    with pytest.raises(OutcomeGateError, match="orchestrator-issued"):
        EvaluationCapability(object())


def test_authorization_contract_substitution_fails_before_authorization() -> None:
    port, freeze = frozen()
    with pytest.raises(OutcomeGateError, match="contract differs"):
        validate_outcome_gate_authority(
            prerequisite(), freeze, Opener(), ContractAuthority(SHA[8]), port
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("attempt_identity", SHA[0]),
        ("dataset_identity", SHA[0]),
        ("external_input_snapshot_identities", (SHA[3],)),
        ("outcome_blind_provenance_identity", SHA[0]),
        ("profile_identity", SHA[0]),
        ("ranking_contract_identity", SHA[0]),
        ("ranking_freeze_contract_identity", SHA[1]),
        ("replay_identity", SHA[0]),
    ),
)
def test_ranking_authority_substitution_rejected(field: str, value: object) -> None:
    port, freeze = frozen()
    changed = RankingAuthority(
        **{
            **{name: getattr(port.authority, name) for name in RankingAuthority.__dataclass_fields__},
            field: value,
        }
    )
    port.authority = changed
    changed_freeze = RankingFreezeResult(
        changed, len(RAW), hashlib.sha256(RAW).hexdigest(), freeze.frozen_reference_identity
    )
    ranking = validate_outcome_gate_authority(
        prerequisite(), changed_freeze, Opener(), ContractAuthority(), port
    )
    with pytest.raises(OutcomeGateError, match="differs from gate authority"):
        build_outcome_authorization(prerequisite(), ranking)


def test_ranking_worker_cannot_supply_reader_or_reconstructor() -> None:
    assert set(RankingCandidate.__dataclass_fields__) == {"raw"}
    with pytest.raises(TypeError):
        RankingCandidate(RAW, reader=object(), reconstructor=object())  # type: ignore[call-arg]


def test_characterization_prerequisite_has_no_route() -> None:
    with pytest.raises(OutcomeGateError, match="no outcome-authorization route"):
        prerequisite(profile_name="outcome_blind_characterization_v1")
