"""Profile-bound execution mechanics for RQ-003 specification v2.

Version 2 is additive.  The v1 module remains the sole authority for legacy
executions; this module reuses its artifact and source contracts while adding
an explicit execution-profile binding and a discriminated terminal manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.experiments.rq003_execution_specification import (
    ArtifactContract,
    ArtifactDeclaration,
    EvaluationDisposition,
    PopulationDisposition,
    ReplayDatasetBinding,
    SourceCommitProvenance,
    canonical_json,
    construct_artifact_contract,
    identity,
    read_external_source_records,
    write_canonical_json_once,
)
from orev3.features.rq003_contracts import CANONICAL_ENCODING_VERSION


EXECUTION_SPECIFICATION_V2_REVISION = "rq003-research-execution-specification-v2"
EXECUTION_SPECIFICATION_V2_SHA256 = (
    "75597ab27d2d2867c68be886785c1884db83b9a26c0428c337ff23d218ef9497"
)
EXECUTION_SPECIFICATION_V2_SCHEMA_VERSION = 2
PROFILED_PROVENANCE_SCHEMA_VERSION = 2
PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION = 2

OUTCOME_AWARE_PROFILE = "outcome_aware_v1"
OUTCOME_BLIND_CHARACTERIZATION_PROFILE = (
    "outcome_blind_characterization_v1"
)
SUPPORTED_EXECUTION_PROFILES = frozenset(
    {OUTCOME_AWARE_PROFILE, OUTCOME_BLIND_CHARACTERIZATION_PROFILE}
)

PROFILED_PROVENANCE_NAME = "outcome_blind_provenance.json"
PROFILED_AUDIT_MANIFEST_NAME = "experiment_audit_manifest.json"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_SAFE_NAME = re.compile(r"[a-z][a-z0-9_.-]*(?:_[a-z0-9_.-]+)*")

_SPECIFICATION_DOMAIN = "rq003-execution-specification-binding-v2"
_PROFILE_DOMAIN = "rq003-execution-profile-binding-v2"
_CONFIGURATION_DOMAIN = "rq003-profiled-experiment-configuration-v2"
_EXPERIMENT_DOMAIN = "rq003-experiment-protocol-binding-v2"
_REPLAY_DOMAIN = "rq003-research-replay-identity-v2"
_PROVENANCE_DOMAIN = "rq003-profiled-outcome-blind-provenance-v2"
_PROFILED_DECLARATION_DOMAIN = "rq003-profiled-artifact-declaration-v2"
_OUTCOME_AUTHORIZATION_DOMAIN = "rq003-profiled-outcome-join-authorization-v2"
_AWARE_TERMINAL_DOMAIN = "rq003-outcome-aware-terminal-v2"
_BLIND_TERMINAL_DOMAIN = "rq003-outcome-blind-characterization-terminal-v2"
_MANIFEST_DOMAIN = "rq003-profiled-experiment-audit-manifest-v2"

_V1_IDENTITY_DOMAINS = {
    "artifact_contract_identity": "rq003-artifact-contract-v1",
    "declaration_identity": "rq003-artifact-declaration-v1",
    "evaluation_disposition_identity": "rq003-evaluation-disposition-v1",
    "disposition_identity": "rq003-population-disposition-v1",
    "dataset_identity": "rq003-replay-dataset-binding-v1",
    "source_commit_provenance_identity": "rq003-source-commit-provenance-v1",
}

_OUTCOME_FIELDS = frozenset(
    {
        "capture_mode",
        "evaluation",
        "evaluation_result",
        "finalized_outcome",
        "finalized_outcome_capture_mode",
        "finalized_outcome_evidence_identities",
        "finalized_outcome_source",
        "label",
        "outcome",
        "outcome_provenance",
        "outcome_source",
        "winning_square",
        "won",
    }
)
_OUTCOME_AWARE_ARTIFACT_KINDS = frozenset(
    {"outcome_source", "outcome_join", "evaluation", "outcome_report"}
)


@dataclass(frozen=True, slots=True)
class ExecutionSpecificationV2Binding:
    revision: str = EXECUTION_SPECIFICATION_V2_REVISION
    document_sha256: str = EXECUTION_SPECIFICATION_V2_SHA256
    schema_version: int = EXECUTION_SPECIFICATION_V2_SCHEMA_VERSION
    specification_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.revision != EXECUTION_SPECIFICATION_V2_REVISION:
            raise ValueError("execution specification revision is unsupported")
        if self.document_sha256 != EXECUTION_SPECIFICATION_V2_SHA256:
            raise ValueError("execution specification document digest is unsupported")
        if self.schema_version != EXECUTION_SPECIFICATION_V2_SCHEMA_VERSION:
            raise ValueError("execution specification schema is unsupported")
        object.__setattr__(
            self,
            "specification_identity",
            identity(_SPECIFICATION_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "document_sha256": self.document_sha256,
            "revision": self.revision,
            "schema_version": self.schema_version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "specification_identity": self.specification_identity}


@dataclass(frozen=True, slots=True)
class ExecutionProfileBinding:
    profile: str
    profile_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.profile not in SUPPORTED_EXECUTION_PROFILES:
            raise ValueError("execution profile is unsupported")
        object.__setattr__(
            self,
            "profile_identity",
            identity(_PROFILE_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "execution_profile": self.profile,
            "schema_version": PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "profile_identity": self.profile_identity}


@dataclass(frozen=True, slots=True)
class ProfiledExperimentConfiguration:
    profile: ExecutionProfileBinding
    experiment_specific_configuration_identity: str
    experiment_configuration_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.profile, ExecutionProfileBinding):
            raise TypeError("profile must be ExecutionProfileBinding")
        _require_sha256(
            "experiment_specific_configuration_identity",
            self.experiment_specific_configuration_identity,
        )
        object.__setattr__(
            self,
            "experiment_configuration_identity",
            identity(_CONFIGURATION_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "experiment_specific_configuration_identity": self.experiment_specific_configuration_identity,
            "profile_identity": self.profile.profile_identity,
            "schema_version": PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "experiment_configuration_identity": self.experiment_configuration_identity}


@dataclass(frozen=True, slots=True)
class ExperimentProtocolV2Binding:
    experiment_identifier: str
    protocol_revision: str
    protocol_document_sha256: str
    specification: ExecutionSpecificationV2Binding
    profile: ExecutionProfileBinding
    configuration: ProfiledExperimentConfiguration
    experiment_binding_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_safe_name("experiment_identifier", self.experiment_identifier)
        _require_nonempty("protocol_revision", self.protocol_revision)
        _require_sha256("protocol_document_sha256", self.protocol_document_sha256)
        if not isinstance(self.specification, ExecutionSpecificationV2Binding):
            raise TypeError("specification must be ExecutionSpecificationV2Binding")
        if not isinstance(self.profile, ExecutionProfileBinding):
            raise TypeError("profile must be ExecutionProfileBinding")
        if not isinstance(self.configuration, ProfiledExperimentConfiguration):
            raise TypeError("configuration must be ProfiledExperimentConfiguration")
        if self.configuration.profile != self.profile:
            raise ValueError("configuration and execution profile bindings disagree")
        object.__setattr__(
            self,
            "experiment_binding_identity",
            identity(_EXPERIMENT_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "configuration": self.configuration.to_dict(),
            "experiment_identifier": self.experiment_identifier,
            "execution_profile": self.profile.to_dict(),
            "protocol_document_sha256": self.protocol_document_sha256,
            "protocol_revision": self.protocol_revision,
            "schema_version": PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION,
            "specification": self.specification.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "experiment_binding_identity": self.experiment_binding_identity}

    @property
    def experiment_configuration_identity(self) -> str:
        return self.configuration.experiment_configuration_identity


@dataclass(frozen=True, slots=True)
class ProfiledReplayIdentity:
    specification_identity: str
    profile_identity: str
    experiment_binding_identity: str
    experiment_configuration_identity: str
    source_commit_provenance_identity: str
    dataset: ReplayDatasetBinding
    protocol_revision_identity: str
    decision_selection_configuration_identity: str
    ordered_replay_round_identities: tuple[str, ...]
    canonical_candidate_order: tuple[int, ...]
    replay_identity: str = field(init=False)

    def __post_init__(self) -> None:
        for name in (
            "specification_identity",
            "profile_identity",
            "experiment_binding_identity",
            "experiment_configuration_identity",
            "source_commit_provenance_identity",
            "protocol_revision_identity",
            "decision_selection_configuration_identity",
        ):
            _require_sha256(name, getattr(self, name))
        if not isinstance(self.dataset, ReplayDatasetBinding):
            raise TypeError("dataset must be ReplayDatasetBinding")
        _require_sha_tuple("ordered_replay_round_identities", self.ordered_replay_round_identities)
        if not self.ordered_replay_round_identities:
            raise ValueError("Replay must contain at least one round identity")
        if len(set(self.ordered_replay_round_identities)) != len(self.ordered_replay_round_identities):
            raise ValueError("Replay round identities must be unique")
        if not isinstance(self.canonical_candidate_order, tuple) or not self.canonical_candidate_order:
            raise TypeError("canonical_candidate_order must be a nonempty tuple")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in self.canonical_candidate_order):
            raise TypeError("candidate order must contain integers")
        if len(set(self.canonical_candidate_order)) != len(self.canonical_candidate_order):
            raise ValueError("candidate order must be unique")
        object.__setattr__(self, "replay_identity", identity(_REPLAY_DOMAIN, self.to_identity_material()))

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_candidate_order": self.canonical_candidate_order,
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "dataset": self.dataset.to_dict(),
            "decision_selection_configuration_identity": self.decision_selection_configuration_identity,
            "experiment_binding_identity": self.experiment_binding_identity,
            "experiment_configuration_identity": self.experiment_configuration_identity,
            "ordered_replay_round_identities": self.ordered_replay_round_identities,
            "profile_identity": self.profile_identity,
            "protocol_revision_identity": self.protocol_revision_identity,
            "schema_version": PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION,
            "source_commit_provenance_identity": self.source_commit_provenance_identity,
            "specification_identity": self.specification_identity,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "replay_identity": self.replay_identity}


def validate_profiled_population_accounting(
    replay: ProfiledReplayIdentity,
    dispositions: tuple[PopulationDisposition, ...],
) -> None:
    if not isinstance(replay, ProfiledReplayIdentity):
        raise TypeError("replay must be ProfiledReplayIdentity")
    if not isinstance(dispositions, tuple):
        raise TypeError("dispositions must be an immutable tuple")
    actual = tuple(item.round_identity for item in dispositions)
    if actual != replay.ordered_replay_round_identities:
        raise ValueError("population dispositions do not exactly preserve Replay order")


@dataclass(frozen=True, slots=True)
class ProfiledArtifactDeclaration:
    profile_identity: str
    declaration: ArtifactDeclaration
    profiled_declaration_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_sha256("profile_identity", self.profile_identity)
        if not isinstance(self.declaration, ArtifactDeclaration):
            raise TypeError("declaration must be ArtifactDeclaration")
        object.__setattr__(
            self,
            "profiled_declaration_identity",
            identity(_PROFILED_DECLARATION_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "declaration": self.declaration.to_dict(),
            "profile_identity": self.profile_identity,
            "schema_version": PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "profiled_declaration_identity": self.profiled_declaration_identity}


@dataclass(frozen=True, slots=True)
class ProfiledOutcomeBlindProvenanceBlock:
    specification: ExecutionSpecificationV2Binding
    profile: ExecutionProfileBinding
    experiment: ExperimentProtocolV2Binding
    source_commit: SourceCommitProvenance
    replay: ProfiledReplayIdentity
    component_identities: tuple[tuple[str, str], ...]
    population_dispositions: tuple[PopulationDisposition, ...]
    upstream_artifact_contracts: tuple[tuple[str, ArtifactContract], ...]
    downstream_artifact_declarations: tuple[tuple[str, ProfiledArtifactDeclaration], ...]
    provenance_block_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.experiment.specification != self.specification:
            raise ValueError("experiment and specification bindings disagree")
        if self.experiment.profile != self.profile:
            raise ValueError("experiment and execution profile bindings disagree")
        if (
            self.replay.specification_identity != self.specification.specification_identity
            or self.replay.profile_identity != self.profile.profile_identity
            or self.replay.experiment_binding_identity != self.experiment.experiment_binding_identity
            or self.replay.source_commit_provenance_identity != self.source_commit.source_commit_provenance_identity
        ):
            raise ValueError("Replay provenance does not match execution bindings")
        validate_profiled_population_accounting(self.replay, self.population_dispositions)
        _validate_named_identities(self.component_identities)
        _validate_named_contracts(self.upstream_artifact_contracts)
        _validate_named_profiled_declarations(self.downstream_artifact_declarations)
        if any(
            value.profile_identity != self.profile.profile_identity
            for _, value in self.downstream_artifact_declarations
        ):
            raise ValueError("artifact declaration profile identity is discontinuous")
        object.__setattr__(
            self,
            "provenance_block_identity",
            identity(_PROVENANCE_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "component_identities": tuple({"identity": value, "name": name} for name, value in self.component_identities),
            "downstream_artifact_declarations": tuple({"declaration": value.to_dict(), "name": name} for name, value in self.downstream_artifact_declarations),
            "experiment": self.experiment.to_dict(),
            "population_dispositions": tuple(value.to_dict() for value in self.population_dispositions),
            "execution_profile": self.profile.to_dict(),
            "replay": self.replay.to_dict(),
            "schema_version": PROFILED_PROVENANCE_SCHEMA_VERSION,
            "source_commit": self.source_commit.to_dict(),
            "specification": self.specification.to_dict(),
            "upstream_artifact_contracts": tuple({"contract": value.to_dict(), "name": name} for name, value in self.upstream_artifact_contracts),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "provenance_block_identity": self.provenance_block_identity}


def freeze_profiled_outcome_blind_provenance(
    path: str | Path,
    block: ProfiledOutcomeBlindProvenanceBlock,
) -> ArtifactContract:
    if not isinstance(block, ProfiledOutcomeBlindProvenanceBlock):
        raise TypeError("block must be ProfiledOutcomeBlindProvenanceBlock")
    material = block.to_dict()
    write_canonical_json_once(path, material)
    declaration = ArtifactDeclaration(
        "outcome_blind_provenance",
        PROFILED_PROVENANCE_SCHEMA_VERSION,
        "json",
        "single_canonical_record",
    )
    return construct_artifact_contract(
        path,
        declaration,
        (material,),
        (
            block.specification.specification_identity,
            block.profile.profile_identity,
            block.experiment.experiment_binding_identity,
            block.source_commit.source_commit_provenance_identity,
            block.replay.replay_identity,
        ),
    )


def construct_profile_artifact_contract(
    path: str | Path,
    declaration: ArtifactDeclaration,
    records: Sequence[Mapping[str, Any]],
    upstream_dependency_identities: tuple[str, ...],
    profile: ExecutionProfileBinding,
) -> ArtifactContract:
    """Construct one profile-valid artifact using the shared v1 contract."""

    if not isinstance(profile, ExecutionProfileBinding):
        raise TypeError("profile must be ExecutionProfileBinding")
    if declaration.artifact_kind in {"ranking", "characterization", "descriptive_report", "conformance"}:
        _validate_outcome_blind_records(records)
    if (
        profile.profile == OUTCOME_BLIND_CHARACTERIZATION_PROFILE
        and declaration.artifact_kind in _OUTCOME_AWARE_ARTIFACT_KINDS
    ):
        raise ValueError("outcome-aware artifact is prohibited by execution profile")
    return construct_artifact_contract(
        path,
        declaration,
        records,
        upstream_dependency_identities,
    )


@dataclass(frozen=True, slots=True)
class ProfiledOutcomeJoinAuthorization:
    profile_identity: str
    provenance_block_identity: str
    ranking_artifact_contract_identity: str
    authorization_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_sha256("profile_identity", self.profile_identity)
        _require_sha256("provenance_block_identity", self.provenance_block_identity)
        _require_sha256(
            "ranking_artifact_contract_identity",
            self.ranking_artifact_contract_identity,
        )
        object.__setattr__(
            self,
            "authorization_identity",
            identity(_OUTCOME_AUTHORIZATION_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "profile_identity": self.profile_identity,
            "provenance_block_identity": self.provenance_block_identity,
            "ranking_artifact_contract_identity": self.ranking_artifact_contract_identity,
            "schema_version": PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "authorization_identity": self.authorization_identity}


def authorize_profiled_outcome_join(
    block: ProfiledOutcomeBlindProvenanceBlock,
    ranking_contract: ArtifactContract,
) -> ProfiledOutcomeJoinAuthorization:
    if block.profile.profile != OUTCOME_AWARE_PROFILE:
        raise ValueError("execution profile prohibits outcome authorization")
    if ranking_contract.declaration.artifact_kind != "ranking":
        raise ValueError("outcome authorization requires a ranking artifact")
    if block.provenance_block_identity not in ranking_contract.upstream_dependency_identities:
        raise ValueError("ranking artifact does not bind the frozen provenance")
    return ProfiledOutcomeJoinAuthorization(
        profile_identity=block.profile.profile_identity,
        provenance_block_identity=block.provenance_block_identity,
        ranking_artifact_contract_identity=ranking_contract.artifact_contract_identity,
    )


def open_profiled_outcome_source(
    path: str | Path,
    authorization: ProfiledOutcomeJoinAuthorization,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(authorization, ProfiledOutcomeJoinAuthorization):
        raise TypeError("outcome source requires ProfiledOutcomeJoinAuthorization")
    return read_external_source_records(path)


@dataclass(frozen=True, slots=True)
class OutcomeAwareTerminal:
    outcome_join_authorization: ProfiledOutcomeJoinAuthorization
    evaluation_dispositions: tuple[EvaluationDisposition, ...]
    outcome_access: str = "authorized_after_primary_validation"
    terminal_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(
            self.outcome_join_authorization,
            ProfiledOutcomeJoinAuthorization,
        ):
            raise TypeError(
                "outcome_join_authorization must be ProfiledOutcomeJoinAuthorization"
            )
        if not isinstance(self.evaluation_dispositions, tuple) or not all(
            isinstance(value, EvaluationDisposition) for value in self.evaluation_dispositions
        ):
            raise TypeError("evaluation_dispositions must be an immutable tuple")
        if self.outcome_access != "authorized_after_primary_validation":
            raise ValueError("outcome-aware terminal has invalid outcome disposition")
        object.__setattr__(self, "terminal_identity", identity(_AWARE_TERMINAL_DOMAIN, self.to_identity_material()))

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "evaluation_dispositions": tuple(value.to_dict() for value in self.evaluation_dispositions),
            "outcome_access": self.outcome_access,
            "outcome_join_authorization": self.outcome_join_authorization.to_dict(),
            "terminal_kind": "outcome_aware",
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "terminal_identity": self.terminal_identity}


@dataclass(frozen=True, slots=True)
class OutcomeBlindCharacterizationTerminal:
    population_dispositions: tuple[PopulationDisposition, ...]
    outcome_access: str = "prohibited_and_not_performed"
    outcome_aware_extension: str = "absent"
    terminal_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.population_dispositions, tuple) or not all(
            isinstance(value, PopulationDisposition) for value in self.population_dispositions
        ):
            raise TypeError("population_dispositions must be an immutable tuple")
        if self.outcome_access != "prohibited_and_not_performed":
            raise ValueError("outcome-blind profile prohibits outcome access")
        if self.outcome_aware_extension != "absent":
            raise ValueError("outcome-blind profile prohibits an outcome-aware extension")
        object.__setattr__(self, "terminal_identity", identity(_BLIND_TERMINAL_DOMAIN, self.to_identity_material()))

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "outcome_access": self.outcome_access,
            "outcome_aware_extension": self.outcome_aware_extension,
            "population_dispositions": tuple(value.to_dict() for value in self.population_dispositions),
            "terminal_kind": "outcome_blind_characterization",
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "terminal_identity": self.terminal_identity}


TerminalExtension = OutcomeAwareTerminal | OutcomeBlindCharacterizationTerminal


@dataclass(frozen=True, slots=True)
class ProfiledExperimentAuditManifest:
    outcome_blind_provenance: ProfiledOutcomeBlindProvenanceBlock
    artifact_contracts: tuple[tuple[str, ArtifactContract], ...]
    terminal: TerminalExtension
    execution_conformance_result: str
    audit_manifest_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_named_contracts(self.artifact_contracts)
        if not self.artifact_contracts:
            raise ValueError("audit manifest requires artifact contracts")
        if self.execution_conformance_result != "passed":
            raise ValueError("only a conformant execution can be sealed")
        profile = self.outcome_blind_provenance.profile.profile
        if profile == OUTCOME_AWARE_PROFILE and not isinstance(self.terminal, OutcomeAwareTerminal):
            raise ValueError("outcome-aware profile requires OutcomeAwareTerminal")
        if profile == OUTCOME_BLIND_CHARACTERIZATION_PROFILE and not isinstance(self.terminal, OutcomeBlindCharacterizationTerminal):
            raise ValueError("outcome-blind profile requires OutcomeBlindCharacterizationTerminal")
        _validate_manifest_graph(
            self.outcome_blind_provenance,
            self.artifact_contracts,
            self.terminal,
        )
        object.__setattr__(self, "audit_manifest_identity", identity(_MANIFEST_DOMAIN, self.to_identity_material()))

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "artifact_contracts": tuple({"contract": value.to_dict(), "name": name} for name, value in self.artifact_contracts),
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "execution_conformance_result": self.execution_conformance_result,
            "outcome_blind_provenance": self.outcome_blind_provenance.to_dict(),
            "execution_profile": self.outcome_blind_provenance.profile.to_dict(),
            "schema_version": PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION,
            "terminal": self.terminal.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "audit_manifest_identity": self.audit_manifest_identity}


def seal_profiled_audit_manifest(
    path: str | Path,
    manifest: ProfiledExperimentAuditManifest,
) -> tuple[str, int]:
    if not isinstance(manifest, ProfiledExperimentAuditManifest):
        raise TypeError("manifest must be ProfiledExperimentAuditManifest")
    write_canonical_json_once(path, manifest.to_dict())
    validate_profiled_audit_manifest(path, expected=manifest)
    persisted = Path(path).read_bytes()
    return hashlib.sha256(persisted).hexdigest(), len(persisted)


def validate_profiled_audit_manifest(
    path: str | Path,
    *,
    expected: ProfiledExperimentAuditManifest | None = None,
) -> dict[str, Any]:
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) != 1 or not lines[0].endswith("\n"):
        raise ValueError("audit manifest must be one newline-terminated record")
    try:
        material = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise ValueError("audit manifest is malformed") from error
    if not isinstance(material, dict) or canonical_json(material) + "\n" != lines[0]:
        raise ValueError("audit manifest is not canonical")
    _validate_embedded_identities(material)
    _validate_serialized_manifest(material)
    if expected is not None and canonical_json(material) != canonical_json(expected.to_dict()):
        raise ValueError("audit manifest differs from reconstructed execution")
    return material


def _validate_manifest_graph(
    block: ProfiledOutcomeBlindProvenanceBlock,
    artifact_contracts: tuple[tuple[str, ArtifactContract], ...],
    terminal: TerminalExtension,
) -> None:
    contracts_by_kind: dict[str, list[ArtifactContract]] = {}
    for _, contract in artifact_contracts:
        contracts_by_kind.setdefault(contract.declaration.artifact_kind, []).append(contract)
    if len(contracts_by_kind.get("outcome_blind_provenance", ())) != 1:
        raise ValueError("manifest requires one frozen provenance artifact")
    declared = {
        value.declaration.declaration_identity
        for _, value in block.downstream_artifact_declarations
    }
    for kind, contracts in contracts_by_kind.items():
        for contract in contracts:
            if kind != "outcome_blind_provenance" and contract.declaration.declaration_identity not in declared:
                raise ValueError("artifact was not declared before the profile boundary")

    if isinstance(terminal, OutcomeAwareTerminal):
        required = {"ranking", "outcome_source", "evaluation"}
        if missing := required.difference(contracts_by_kind):
            raise ValueError("outcome-aware manifest is missing lifecycle artifacts: " + ", ".join(sorted(missing)))
        if "characterization" in contracts_by_kind:
            raise ValueError("outcome-aware profile cannot use characterization primary")
        if len(contracts_by_kind["ranking"]) != 1:
            raise ValueError("outcome-aware profile requires one ranking primary")
        ranking = contracts_by_kind["ranking"][0]
        if block.provenance_block_identity not in ranking.upstream_dependency_identities:
            raise ValueError("ranking artifact is not bound to frozen provenance")
        authorization = terminal.outcome_join_authorization
        if (
            authorization.profile_identity != block.profile.profile_identity
            or authorization.provenance_block_identity != block.provenance_block_identity
            or authorization.ranking_artifact_contract_identity
            != ranking.artifact_contract_identity
        ):
            raise ValueError("outcome authorization does not bind frozen execution")
        eligible = tuple(item.round_identity for item in block.population_dispositions if item.status == "eligible")
        if tuple(item.round_identity for item in terminal.evaluation_dispositions) != eligible:
            raise ValueError("evaluation dispositions do not reconcile with eligibility")
        outcome_ids = {item.artifact_contract_identity for item in contracts_by_kind["outcome_source"]}
        for evaluation in contracts_by_kind["evaluation"]:
            dependencies = set(evaluation.upstream_dependency_identities)
            if ranking.artifact_contract_identity not in dependencies or not outcome_ids.intersection(dependencies):
                raise ValueError("evaluation artifact is missing frozen inputs")
        return

    prohibited = _OUTCOME_AWARE_ARTIFACT_KINDS.intersection(contracts_by_kind)
    if prohibited:
        raise ValueError("outcome-blind manifest contains outcome-aware artifacts")
    if len(contracts_by_kind.get("characterization", ())) != 1:
        raise ValueError("outcome-blind profile requires one characterization primary")
    if not contracts_by_kind.get("descriptive_report"):
        raise ValueError("outcome-blind profile requires a descriptive report")
    if not contracts_by_kind.get("conformance"):
        raise ValueError("outcome-blind profile requires a conformance report")
    characterization = contracts_by_kind["characterization"][0]
    if block.provenance_block_identity not in characterization.upstream_dependency_identities:
        raise ValueError("characterization artifact is not bound to frozen provenance")
    if terminal.population_dispositions != block.population_dispositions:
        raise ValueError("terminal population does not preserve pre-outcome accounting")
    outcome_ids = {
        contract.artifact_contract_identity
        for kind in _OUTCOME_AWARE_ARTIFACT_KINDS
        for contract in contracts_by_kind.get(kind, ())
    }
    for _, contract in artifact_contracts:
        if outcome_ids.intersection(contract.upstream_dependency_identities):
            raise ValueError("outcome-blind artifact depends on outcome-aware material")


def _validate_serialized_manifest(material: Mapping[str, Any]) -> None:
    required = {
        "artifact_contracts",
        "audit_manifest_identity",
        "canonical_encoding_version",
        "execution_conformance_result",
        "outcome_blind_provenance",
        "execution_profile",
        "schema_version",
        "terminal",
    }
    if set(material) != required:
        raise ValueError("audit_manifest_identity schema is invalid")
    if material["schema_version"] != PROFILED_AUDIT_MANIFEST_SCHEMA_VERSION:
        raise ValueError("audit manifest schema is unsupported")
    if material["execution_conformance_result"] != "passed":
        raise ValueError("audit manifest does not record conformance")
    block = material["outcome_blind_provenance"]
    profile = material["execution_profile"]
    terminal = material["terminal"]
    specification = block["specification"]
    experiment = block["experiment"]
    replay = block["replay"]
    if experiment["specification"] != specification:
        raise ValueError("experiment and specification bindings disagree")
    if (
        block["execution_profile"] != profile
        or block["experiment"]["execution_profile"] != profile
    ):
        raise ValueError("profile binding is discontinuous")
    if experiment["configuration"]["profile_identity"] != profile["profile_identity"]:
        raise ValueError("experiment configuration profile identity is discontinuous")
    for entry in block["downstream_artifact_declarations"]:
        if entry["declaration"]["profile_identity"] != profile["profile_identity"]:
            raise ValueError("artifact declaration profile identity is discontinuous")
    if (
        replay["profile_identity"] != profile["profile_identity"]
        or replay["specification_identity"] != specification["specification_identity"]
        or replay["experiment_binding_identity"] != experiment["experiment_binding_identity"]
        or replay["source_commit_provenance_identity"]
        != block["source_commit"]["source_commit_provenance_identity"]
    ):
        raise ValueError("Replay profile identity is discontinuous")
    replay_rounds = replay["ordered_replay_round_identities"]
    dispositions = block["population_dispositions"]
    if [entry["round_identity"] for entry in dispositions] != replay_rounds:
        raise ValueError("population accounting does not preserve Replay order")

    artifact_entries = material["artifact_contracts"]
    if not isinstance(artifact_entries, list) or not artifact_entries:
        raise ValueError("audit manifest requires artifact contracts")
    names = [entry.get("name") for entry in artifact_entries if isinstance(entry, dict)]
    if len(names) != len(artifact_entries) or names != sorted(set(names)):
        raise ValueError("artifact contracts are not unique and canonically ordered")
    contracts_by_kind: dict[str, list[Mapping[str, Any]]] = {}
    for entry in artifact_entries:
        if set(entry) != {"contract", "name"} or not isinstance(entry["contract"], dict):
            raise ValueError("artifact contract entry schema is invalid")
        contract = entry["contract"]
        if contract["reconstruction_status"] != "validated":
            raise ValueError("artifact reconstruction was not validated")
        kind = contract["declaration"]["artifact_kind"]
        contracts_by_kind.setdefault(kind, []).append(contract)
    if len(contracts_by_kind.get("outcome_blind_provenance", ())) != 1:
        raise ValueError("manifest requires one frozen provenance artifact")
    declared = {
        entry["declaration"]["declaration"]["declaration_identity"]
        for entry in block["downstream_artifact_declarations"]
    }
    for kind, contracts in contracts_by_kind.items():
        for contract in contracts:
            if kind != "outcome_blind_provenance" and contract["declaration"]["declaration_identity"] not in declared:
                raise ValueError("artifact was not declared before the profile boundary")

    if profile["execution_profile"] == OUTCOME_AWARE_PROFILE:
        if terminal["terminal_kind"] != "outcome_aware":
            raise ValueError("profile and terminal disagree")
        required_kinds = {"ranking", "outcome_source", "evaluation"}
        if missing := required_kinds.difference(contracts_by_kind):
            raise ValueError("outcome-aware manifest is missing lifecycle artifacts: " + ", ".join(sorted(missing)))
        if len(contracts_by_kind["ranking"]) != 1 or "characterization" in contracts_by_kind:
            raise ValueError("outcome-aware primary artifact is invalid")
        ranking = contracts_by_kind["ranking"][0]
        if block["provenance_block_identity"] not in ranking["upstream_dependency_identities"]:
            raise ValueError("ranking artifact is not bound to frozen provenance")
        authorization = terminal["outcome_join_authorization"]
        if (
            authorization["profile_identity"] != profile["profile_identity"]
            or authorization["provenance_block_identity"]
            != block["provenance_block_identity"]
            or authorization["ranking_artifact_contract_identity"]
            != ranking["artifact_contract_identity"]
        ):
            raise ValueError("outcome authorization does not bind frozen execution")
        eligible = [entry["round_identity"] for entry in dispositions if entry["status"] == "eligible"]
        if [entry["round_identity"] for entry in terminal["evaluation_dispositions"]] != eligible:
            raise ValueError("evaluation dispositions do not reconcile with eligibility")
        outcome_identities = {
            contract["artifact_contract_identity"]
            for contract in contracts_by_kind["outcome_source"]
        }
        for evaluation in contracts_by_kind["evaluation"]:
            dependencies = set(evaluation["upstream_dependency_identities"])
            if ranking["artifact_contract_identity"] not in dependencies or not outcome_identities.intersection(dependencies):
                raise ValueError("evaluation artifact is missing frozen inputs")
    elif profile["execution_profile"] == OUTCOME_BLIND_CHARACTERIZATION_PROFILE:
        if terminal["terminal_kind"] != "outcome_blind_characterization":
            raise ValueError("profile and terminal disagree")
        if terminal["outcome_access"] != "prohibited_and_not_performed" or terminal["outcome_aware_extension"] != "absent":
            raise ValueError("outcome-blind terminal disposition is invalid")
        if terminal["population_dispositions"] != block["population_dispositions"]:
            raise ValueError("terminal population does not preserve accounting")
        if _OUTCOME_AWARE_ARTIFACT_KINDS.intersection(contracts_by_kind):
            raise ValueError("outcome-blind manifest contains outcome-aware artifacts")
        if len(contracts_by_kind.get("characterization", ())) != 1:
            raise ValueError("outcome-blind profile requires one characterization primary")
        if not contracts_by_kind.get("descriptive_report") or not contracts_by_kind.get("conformance"):
            raise ValueError("outcome-blind profile requires descriptive and conformance reports")
        characterization = contracts_by_kind["characterization"][0]
        if block["provenance_block_identity"] not in characterization["upstream_dependency_identities"]:
            raise ValueError("characterization artifact is not bound to frozen provenance")
    else:
        raise ValueError("execution profile is unsupported")


def _validate_embedded_identities(value: object) -> None:
    if isinstance(value, list):
        for item in value:
            _validate_embedded_identities(item)
        return
    if not isinstance(value, dict):
        return
    for item in value.values():
        _validate_embedded_identities(item)
    domains = {
        "audit_manifest_identity": _MANIFEST_DOMAIN,
        "authorization_identity": _OUTCOME_AUTHORIZATION_DOMAIN,
        "terminal_identity": (
            _AWARE_TERMINAL_DOMAIN
            if value.get("terminal_kind") == "outcome_aware"
            else _BLIND_TERMINAL_DOMAIN
        ),
        "provenance_block_identity": _PROVENANCE_DOMAIN,
        "profiled_declaration_identity": _PROFILED_DECLARATION_DOMAIN,
        "replay_identity": _REPLAY_DOMAIN,
        "experiment_binding_identity": _EXPERIMENT_DOMAIN,
        "experiment_configuration_identity": _CONFIGURATION_DOMAIN,
        "profile_identity": _PROFILE_DOMAIN,
        "specification_identity": _SPECIFICATION_DOMAIN,
        **_V1_IDENTITY_DOMAINS,
    }
    for field_name, domain in domains.items():
        if field_name in value:
            stored = value[field_name]
            _require_sha256(field_name, stored)
            material = {key: item for key, item in value.items() if key != field_name}
            if identity(domain, material) != stored:
                raise ValueError(f"{field_name} does not reconstruct")
            break


def _validate_outcome_blind_records(records: Sequence[Mapping[str, Any]]) -> None:
    def inspect(value: object) -> None:
        if isinstance(value, (list, tuple)):
            for item in value:
                inspect(item)
            return
        if not isinstance(value, Mapping):
            return
        if intersection := _OUTCOME_FIELDS.intersection(value):
            raise ValueError("outcome-blind artifact contains outcome information: " + ", ".join(sorted(intersection)))
        for item in value.values():
            inspect(item)

    for record in records:
        inspect(record)


def _validate_named_identities(values: tuple[tuple[str, str], ...]) -> None:
    _validate_named(values, str, "component identities")
    for _, value in values:
        _require_sha256("component identity", value)


def _validate_named_contracts(values: tuple[tuple[str, ArtifactContract], ...]) -> None:
    _validate_named(values, ArtifactContract, "artifact contracts")


def _validate_named_profiled_declarations(
    values: tuple[tuple[str, ProfiledArtifactDeclaration], ...],
) -> None:
    _validate_named(values, ProfiledArtifactDeclaration, "artifact declarations")


def _validate_named(values: object, value_type: type[Any], label: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be an immutable tuple")
    names: list[str] = []
    for entry in values:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise TypeError(f"{label} entries must be pairs")
        name, value = entry
        _require_safe_name(label, name)
        if not isinstance(value, value_type):
            raise TypeError(f"{label} contains an unsupported value")
        names.append(name)
    if names != sorted(set(names)):
        raise ValueError(f"{label} must be unique and canonically ordered")


def _require_sha256(name: str, value: object) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _require_sha_tuple(name: str, value: object) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    for item in value:
        _require_sha256(name, item)


def _require_nonempty(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be a canonical nonempty string")


def _require_safe_name(name: str, value: object) -> None:
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase canonical name")


__all__ = (
    "EXECUTION_SPECIFICATION_V2_REVISION",
    "EXECUTION_SPECIFICATION_V2_SCHEMA_VERSION",
    "EXECUTION_SPECIFICATION_V2_SHA256",
    "OUTCOME_AWARE_PROFILE",
    "OUTCOME_BLIND_CHARACTERIZATION_PROFILE",
    "PROFILED_AUDIT_MANIFEST_NAME",
    "PROFILED_PROVENANCE_NAME",
    "ExecutionProfileBinding",
    "ExecutionSpecificationV2Binding",
    "ExperimentProtocolV2Binding",
    "OutcomeAwareTerminal",
    "OutcomeBlindCharacterizationTerminal",
    "ProfiledExperimentAuditManifest",
    "ProfiledExperimentConfiguration",
    "ProfiledArtifactDeclaration",
    "ProfiledOutcomeBlindProvenanceBlock",
    "ProfiledOutcomeJoinAuthorization",
    "ProfiledReplayIdentity",
    "authorize_profiled_outcome_join",
    "construct_profile_artifact_contract",
    "freeze_profiled_outcome_blind_provenance",
    "open_profiled_outcome_source",
    "seal_profiled_audit_manifest",
    "validate_profiled_audit_manifest",
    "validate_profiled_population_accounting",
)
