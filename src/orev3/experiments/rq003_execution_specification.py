"""Reusable execution mechanics for RQ-003 research experiments.

This module implements RQ-003 Research Execution Specification v1.  It owns
identity, provenance, artifact, population, outcome-boundary, and manifest
mechanics only.  It contains no measurement, Feature Set, baseline, ranking,
metric, bootstrap, control, or scientific interpretation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.features.rq003_contracts import (
    CANONICAL_ENCODING_VERSION,
    canonical_encode,
)


EXECUTION_SPECIFICATION_REVISION = (
    "rq003-research-execution-specification-v1"
)
EXECUTION_SPECIFICATION_SHA256 = (
    "3f7da6977f3a4f7c31766c856fc9cc000ed6a6a0d4dffcbf6e5cd0193d948eb2"
)
EXECUTION_SPECIFICATION_SCHEMA_VERSION = 1
OUTCOME_BLIND_PROVENANCE_SCHEMA_VERSION = 1
ARTIFACT_CONTRACT_SCHEMA_VERSION = 1
AUDIT_MANIFEST_SCHEMA_VERSION = 1
CONTRACT_SCHEMA_VERSION = 1

OUTCOME_BLIND_PROVENANCE_NAME = "outcome_blind_provenance.json"
AUDIT_MANIFEST_NAME = "experiment_audit_manifest.json"

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_SAFE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_.-]*(?:_[a-z0-9_.-]+)*")

_SPECIFICATION_BINDING_DOMAIN = "rq003-execution-specification-binding-v1"
_EXPERIMENT_BINDING_DOMAIN = "rq003-experiment-protocol-binding-v1"
_SOURCE_COMMIT_DOMAIN = "rq003-source-commit-provenance-v1"
_DATASET_BINDING_DOMAIN = "rq003-replay-dataset-binding-v1"
_REPLAY_IDENTITY_DOMAIN = "rq003-research-replay-identity-v1"
_DISPOSITION_DOMAIN = "rq003-population-disposition-v1"
_EVALUATION_DISPOSITION_DOMAIN = "rq003-evaluation-disposition-v1"
_ARTIFACT_DECLARATION_DOMAIN = "rq003-artifact-declaration-v1"
_ARTIFACT_CONTENT_DOMAIN = "rq003-artifact-canonical-content-v1"
_ARTIFACT_CONTRACT_DOMAIN = "rq003-artifact-contract-v1"
_PROVENANCE_BLOCK_DOMAIN = "rq003-outcome-blind-provenance-v1"
_OUTCOME_AUTHORIZATION_DOMAIN = "rq003-outcome-join-authorization-v1"
_AUDIT_MANIFEST_DOMAIN = "rq003-experiment-audit-manifest-v1"


def identity(domain: str, material: object) -> str:
    """Construct one domain-separated canonical SHA-256 identity."""

    _require_nonempty("domain", domain)
    return hashlib.sha256(
        domain.encode("utf-8") + canonical_encode(material)
    ).hexdigest()


def canonical_json(material: object) -> str:
    """Persist ordinary JSON in one deterministic representation."""

    return json.dumps(
        material,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_canonical_json_once(path: str | Path, material: Mapping[str, Any]) -> None:
    _write_bytes_once(Path(path), (canonical_json(material) + "\n").encode("utf-8"))


def write_canonical_jsonl_once(
    path: str | Path, records: Sequence[Mapping[str, Any]]
) -> None:
    data = "".join(canonical_json(record) + "\n" for record in records)
    _write_bytes_once(Path(path), data.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class ExecutionSpecificationBinding:
    revision: str
    document_sha256: str
    schema_version: int = EXECUTION_SPECIFICATION_SCHEMA_VERSION
    specification_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.revision != EXECUTION_SPECIFICATION_REVISION:
            raise ValueError("execution specification revision is unsupported")
        if self.document_sha256 != EXECUTION_SPECIFICATION_SHA256:
            raise ValueError("execution specification document digest is unsupported")
        _require_version("schema_version", self.schema_version, 1)
        object.__setattr__(
            self,
            "specification_identity",
            identity(_SPECIFICATION_BINDING_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "document_sha256": self.document_sha256,
            "revision": self.revision,
            "schema_version": self.schema_version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_identity_material(),
            "specification_identity": self.specification_identity,
        }


@dataclass(frozen=True, slots=True)
class ExperimentProtocolBinding:
    experiment_identifier: str
    protocol_revision: str
    protocol_document_sha256: str
    specification: ExecutionSpecificationBinding
    experiment_configuration_identity: str
    experiment_binding_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_safe_name("experiment_identifier", self.experiment_identifier)
        _require_nonempty("protocol_revision", self.protocol_revision)
        _require_sha256("protocol_document_sha256", self.protocol_document_sha256)
        if not isinstance(self.specification, ExecutionSpecificationBinding):
            raise TypeError("specification must be ExecutionSpecificationBinding")
        _require_sha256(
            "experiment_configuration_identity",
            self.experiment_configuration_identity,
        )
        object.__setattr__(
            self,
            "experiment_binding_identity",
            identity(_EXPERIMENT_BINDING_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "experiment_configuration_identity": (
                self.experiment_configuration_identity
            ),
            "experiment_identifier": self.experiment_identifier,
            "protocol_document_sha256": self.protocol_document_sha256,
            "protocol_revision": self.protocol_revision,
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "specification": self.specification.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_identity_material(),
            "experiment_binding_identity": self.experiment_binding_identity,
        }


@dataclass(frozen=True, slots=True)
class SourceScopeBinding:
    repository_path: str
    git_object_identity: str

    def __post_init__(self) -> None:
        _require_relative_path("repository_path", self.repository_path)
        if not isinstance(self.git_object_identity, str) or not re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}", self.git_object_identity
        ):
            raise ValueError("git_object_identity is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "git_object_identity": self.git_object_identity,
            "repository_path": self.repository_path,
        }


@dataclass(frozen=True, slots=True)
class SourceCommitProvenance:
    commit_sha: str
    scopes: tuple[SourceScopeBinding, ...]
    source_commit_provenance_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.commit_sha, str) or not _GIT_COMMIT_PATTERN.fullmatch(
            self.commit_sha
        ):
            raise ValueError("commit_sha must be a full Git commit identity")
        _require_tuple("scopes", self.scopes, SourceScopeBinding)
        if not self.scopes:
            raise ValueError("source scopes cannot be empty")
        paths = tuple(scope.repository_path for scope in self.scopes)
        if len(paths) != len(set(paths)) or paths != tuple(sorted(paths)):
            raise ValueError("source scopes must be unique and canonically ordered")
        object.__setattr__(
            self,
            "source_commit_provenance_identity",
            identity(_SOURCE_COMMIT_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "commit_sha": self.commit_sha,
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "scopes": tuple(scope.to_dict() for scope in self.scopes),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_identity_material(),
            "source_commit_provenance_identity": (
                self.source_commit_provenance_identity
            ),
        }


def bind_source_commit(
    repository_root: str | Path,
    commit_sha: str,
    tracked_scopes: Sequence[str],
) -> SourceCommitProvenance:
    """Bind and verify one Git commit against all declared source scopes."""

    root = Path(repository_root).resolve()
    if not isinstance(commit_sha, str) or not _GIT_COMMIT_PATTERN.fullmatch(commit_sha):
        raise ValueError("commit_sha must be a full Git commit identity")
    scopes = tuple(sorted(tracked_scopes))
    if not scopes or len(scopes) != len(set(scopes)):
        raise ValueError("tracked_scopes must be nonempty and unique")
    for scope in scopes:
        _require_relative_path("tracked scope", scope)
    resolved = _git(root, "rev-parse", commit_sha).strip()
    if resolved != commit_sha:
        raise ValueError("source commit did not resolve to the exact full identity")
    bindings: list[SourceScopeBinding] = []
    for scope in scopes:
        status = subprocess.run(
            ["git", "diff", "--quiet", commit_sha, "--", scope],
            cwd=root,
            check=False,
        )
        if status.returncode != 0:
            raise ValueError(f"tracked source scope differs from commit: {scope}")
        untracked = _git(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            scope,
        ).strip()
        if untracked:
            raise ValueError(f"source scope contains untracked files: {scope}")
        object_identity = _git(root, "rev-parse", f"{commit_sha}:{scope}").strip()
        bindings.append(SourceScopeBinding(scope, object_identity))
    return SourceCommitProvenance(commit_sha, tuple(bindings))


@dataclass(frozen=True, slots=True)
class ReplayDatasetBinding:
    dataset_version: str
    schema_identity: str
    byte_count: int
    sha256: str
    dataset_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_nonempty("dataset_version", self.dataset_version)
        _require_sha256("schema_identity", self.schema_identity)
        _require_nonnegative_integer("byte_count", self.byte_count)
        _require_sha256("sha256", self.sha256)
        object.__setattr__(
            self,
            "dataset_identity",
            identity(_DATASET_BINDING_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "byte_count": self.byte_count,
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "dataset_version": self.dataset_version,
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "schema_identity": self.schema_identity,
            "sha256": self.sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "dataset_identity": self.dataset_identity}


@dataclass(frozen=True, slots=True)
class ReplayIdentity:
    specification_identity: str
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
            "experiment_binding_identity",
            "experiment_configuration_identity",
            "source_commit_provenance_identity",
            "protocol_revision_identity",
            "decision_selection_configuration_identity",
        ):
            _require_sha256(name, getattr(self, name))
        if not isinstance(self.dataset, ReplayDatasetBinding):
            raise TypeError("dataset must be ReplayDatasetBinding")
        _require_sha_tuple(
            "ordered_replay_round_identities",
            self.ordered_replay_round_identities,
        )
        if not self.ordered_replay_round_identities:
            raise ValueError("Replay must contain at least one round identity")
        if len(self.ordered_replay_round_identities) != len(
            set(self.ordered_replay_round_identities)
        ):
            raise ValueError("Replay round identities must be unique")
        if not isinstance(self.canonical_candidate_order, tuple) or not (
            self.canonical_candidate_order
        ):
            raise TypeError("canonical_candidate_order must be a nonempty tuple")
        if any(
            isinstance(candidate, bool) or not isinstance(candidate, int)
            for candidate in self.canonical_candidate_order
        ):
            raise TypeError("candidate order must contain integers")
        if len(self.canonical_candidate_order) != len(
            set(self.canonical_candidate_order)
        ):
            raise ValueError("candidate order must be unique")
        object.__setattr__(
            self,
            "replay_identity",
            identity(_REPLAY_IDENTITY_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_candidate_order": self.canonical_candidate_order,
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "dataset": self.dataset.to_dict(),
            "decision_selection_configuration_identity": (
                self.decision_selection_configuration_identity
            ),
            "experiment_binding_identity": self.experiment_binding_identity,
            "experiment_configuration_identity": (
                self.experiment_configuration_identity
            ),
            "ordered_replay_round_identities": self.ordered_replay_round_identities,
            "protocol_revision_identity": self.protocol_revision_identity,
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "source_commit_provenance_identity": (
                self.source_commit_provenance_identity
            ),
            "specification_identity": self.specification_identity,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "replay_identity": self.replay_identity}


@dataclass(frozen=True, slots=True)
class PopulationDisposition:
    round_identity: str
    round_reference: str
    status: str
    reason: str | None
    decision_identity: str | None
    disposition_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_sha256("round_identity", self.round_identity)
        _require_nonempty("round_reference", self.round_reference)
        if self.status not in {"eligible", "excluded"}:
            raise ValueError("pre-outcome disposition status is unsupported")
        if self.status == "eligible":
            if self.reason is not None:
                raise ValueError("eligible disposition cannot have an exclusion reason")
            _require_sha256("decision_identity", self.decision_identity)
        else:
            _require_nonempty("reason", self.reason)
            if self.decision_identity is not None:
                raise ValueError("excluded disposition cannot have a decision identity")
        object.__setattr__(
            self,
            "disposition_identity",
            identity(_DISPOSITION_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "decision_identity": self.decision_identity,
            "reason": self.reason,
            "round_identity": self.round_identity,
            "round_reference": self.round_reference,
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "status": self.status,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "disposition_identity": self.disposition_identity}


@dataclass(frozen=True, slots=True)
class EvaluationDisposition:
    round_identity: str
    round_reference: str
    status: str
    reason: str
    outcome_source_identity: str | None
    evaluation_disposition_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_sha256("round_identity", self.round_identity)
        _require_nonempty("round_reference", self.round_reference)
        if self.status not in {"evaluated", "excluded"}:
            raise ValueError("evaluation disposition status is unsupported")
        _require_nonempty("reason", self.reason)
        if self.status == "evaluated":
            _require_sha256("outcome_source_identity", self.outcome_source_identity)
        elif self.outcome_source_identity is not None:
            raise ValueError("excluded evaluation cannot bind an outcome source")
        object.__setattr__(
            self,
            "evaluation_disposition_identity",
            identity(_EVALUATION_DISPOSITION_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "outcome_source_identity": self.outcome_source_identity,
            "reason": self.reason,
            "round_identity": self.round_identity,
            "round_reference": self.round_reference,
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "status": self.status,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_identity_material(),
            "evaluation_disposition_identity": (
                self.evaluation_disposition_identity
            ),
        }


def validate_population_accounting(
    replay: ReplayIdentity,
    dispositions: Sequence[PopulationDisposition],
) -> None:
    if not isinstance(replay, ReplayIdentity):
        raise TypeError("replay must be ReplayIdentity")
    if not isinstance(dispositions, tuple):
        raise TypeError("dispositions must be an immutable tuple")
    actual = tuple(disposition.round_identity for disposition in dispositions)
    if actual != replay.ordered_replay_round_identities:
        raise ValueError("population dispositions do not exactly preserve Replay order")


@dataclass(frozen=True, slots=True)
class ArtifactDeclaration:
    artifact_kind: str
    schema_version: int
    container: str
    record_ordering: str
    declaration_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _require_safe_name("artifact_kind", self.artifact_kind)
        _require_positive_integer("schema_version", self.schema_version)
        if self.container not in {"json", "jsonl"}:
            raise ValueError("artifact container is unsupported")
        _require_nonempty("record_ordering", self.record_ordering)
        object.__setattr__(
            self,
            "declaration_identity",
            identity(_ARTIFACT_DECLARATION_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "container": self.container,
            "record_ordering": self.record_ordering,
            "schema_version": self.schema_version,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "declaration_identity": self.declaration_identity}


@dataclass(frozen=True, slots=True)
class ArtifactContract:
    declaration: ArtifactDeclaration
    upstream_dependency_identities: tuple[str, ...]
    canonical_content_identity: str
    persisted_sha256: str
    byte_count: int
    record_count: int
    reconstruction_status: str
    artifact_contract_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.declaration, ArtifactDeclaration):
            raise TypeError("declaration must be ArtifactDeclaration")
        _require_sha_tuple(
            "upstream_dependency_identities",
            self.upstream_dependency_identities,
        )
        if len(self.upstream_dependency_identities) != len(
            set(self.upstream_dependency_identities)
        ):
            raise ValueError("artifact dependencies must be unique")
        _require_sha256("canonical_content_identity", self.canonical_content_identity)
        _require_sha256("persisted_sha256", self.persisted_sha256)
        _require_nonnegative_integer("byte_count", self.byte_count)
        _require_nonnegative_integer("record_count", self.record_count)
        if self.reconstruction_status != "validated":
            raise ValueError("artifact reconstruction must be validated")
        object.__setattr__(
            self,
            "artifact_contract_identity",
            identity(_ARTIFACT_CONTRACT_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "byte_count": self.byte_count,
            "canonical_content_identity": self.canonical_content_identity,
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "declaration": self.declaration.to_dict(),
            "persisted_sha256": self.persisted_sha256,
            "reconstruction_status": self.reconstruction_status,
            "record_count": self.record_count,
            "upstream_dependency_identities": (
                self.upstream_dependency_identities
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_identity_material(),
            "artifact_contract_identity": self.artifact_contract_identity,
        }


def construct_artifact_contract(
    path: str | Path,
    declaration: ArtifactDeclaration,
    records: Sequence[Mapping[str, Any]],
    upstream_dependency_identities: tuple[str, ...],
) -> ArtifactContract:
    """Validate persisted canonical records and construct their contract."""

    artifact_path = Path(path)
    if not artifact_path.is_file():
        raise ValueError(f"required artifact is missing: {artifact_path.name}")
    if declaration.container == "json" and len(records) != 1:
        raise ValueError("JSON artifact must contain exactly one logical record")
    if declaration.artifact_kind == "ranking":
        _validate_outcome_blind_records(records)
    expected = "".join(canonical_json(record) + "\n" for record in records).encode(
        "utf-8"
    )
    actual = artifact_path.read_bytes()
    if actual != expected:
        raise ValueError(f"artifact is not canonical: {artifact_path.name}")
    content_identity = identity(
        _ARTIFACT_CONTENT_DOMAIN,
        {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "declaration_identity": declaration.declaration_identity,
            "records": tuple(records),
        },
    )
    return ArtifactContract(
        declaration=declaration,
        upstream_dependency_identities=upstream_dependency_identities,
        canonical_content_identity=content_identity,
        persisted_sha256=hashlib.sha256(actual).hexdigest(),
        byte_count=len(actual),
        record_count=len(records),
        reconstruction_status="validated",
    )


def _validate_outcome_blind_records(
    records: Sequence[Mapping[str, Any]],
) -> None:
    prohibited_fields = {
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

    def inspect(value: object) -> None:
        if isinstance(value, list) or isinstance(value, tuple):
            for item in value:
                inspect(item)
            return
        if not isinstance(value, Mapping):
            return
        intersection = prohibited_fields.intersection(value)
        if intersection:
            raise ValueError(
                "ranking artifact contains outcome information: "
                + ", ".join(sorted(intersection))
            )
        for item in value.values():
            inspect(item)

    for record in records:
        inspect(record)


@dataclass(frozen=True, slots=True)
class OutcomeBlindProvenanceBlock:
    specification: ExecutionSpecificationBinding
    experiment: ExperimentProtocolBinding
    source_commit: SourceCommitProvenance
    replay: ReplayIdentity
    component_identities: tuple[tuple[str, str], ...]
    population_dispositions: tuple[PopulationDisposition, ...]
    upstream_artifact_contracts: tuple[tuple[str, ArtifactContract], ...]
    downstream_artifact_declarations: tuple[tuple[str, ArtifactDeclaration], ...]
    provenance_block_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.experiment.specification != self.specification:
            raise ValueError("experiment and specification bindings disagree")
        if (
            self.replay.specification_identity
            != self.specification.specification_identity
            or self.replay.experiment_binding_identity
            != self.experiment.experiment_binding_identity
            or self.replay.source_commit_provenance_identity
            != self.source_commit.source_commit_provenance_identity
        ):
            raise ValueError("Replay provenance does not match execution bindings")
        validate_population_accounting(self.replay, self.population_dispositions)
        _validate_named_identity_pairs("component_identities", self.component_identities)
        _validate_named_objects(
            "upstream_artifact_contracts",
            self.upstream_artifact_contracts,
            ArtifactContract,
        )
        _validate_named_objects(
            "downstream_artifact_declarations",
            self.downstream_artifact_declarations,
            ArtifactDeclaration,
        )
        object.__setattr__(
            self,
            "provenance_block_identity",
            identity(_PROVENANCE_BLOCK_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "component_identities": tuple(
                {"identity": value, "name": name}
                for name, value in self.component_identities
            ),
            "downstream_artifact_declarations": tuple(
                {"declaration": declaration.to_dict(), "name": name}
                for name, declaration in self.downstream_artifact_declarations
            ),
            "experiment": self.experiment.to_dict(),
            "population_dispositions": tuple(
                disposition.to_dict()
                for disposition in self.population_dispositions
            ),
            "replay": self.replay.to_dict(),
            "schema_version": OUTCOME_BLIND_PROVENANCE_SCHEMA_VERSION,
            "source_commit": self.source_commit.to_dict(),
            "specification": self.specification.to_dict(),
            "upstream_artifact_contracts": tuple(
                {"contract": contract.to_dict(), "name": name}
                for name, contract in self.upstream_artifact_contracts
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_identity_material(),
            "provenance_block_identity": self.provenance_block_identity,
        }


def freeze_outcome_blind_provenance(
    path: str | Path, block: OutcomeBlindProvenanceBlock
) -> ArtifactContract:
    if not isinstance(block, OutcomeBlindProvenanceBlock):
        raise TypeError("block must be OutcomeBlindProvenanceBlock")
    material = block.to_dict()
    write_canonical_json_once(path, material)
    declaration = ArtifactDeclaration(
        artifact_kind="outcome_blind_provenance",
        schema_version=OUTCOME_BLIND_PROVENANCE_SCHEMA_VERSION,
        container="json",
        record_ordering="single_canonical_record",
    )
    return construct_artifact_contract(
        path,
        declaration,
        (material,),
        (
            block.specification.specification_identity,
            block.experiment.experiment_binding_identity,
            block.source_commit.source_commit_provenance_identity,
            block.replay.replay_identity,
        ),
    )


@dataclass(frozen=True, slots=True)
class OutcomeJoinAuthorization:
    provenance_block_identity: str
    ranking_artifact_contract_identity: str
    authorization_identity: str = field(init=False)

    def __post_init__(self) -> None:
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
            "provenance_block_identity": self.provenance_block_identity,
            "ranking_artifact_contract_identity": (
                self.ranking_artifact_contract_identity
            ),
            "schema_version": CONTRACT_SCHEMA_VERSION,
        }


def authorize_outcome_join(
    block: OutcomeBlindProvenanceBlock,
    ranking_contract: ArtifactContract,
) -> OutcomeJoinAuthorization:
    if block.provenance_block_identity not in (
        ranking_contract.upstream_dependency_identities
    ):
        raise ValueError("ranking artifact does not bind the provenance block")
    if ranking_contract.declaration.artifact_kind != "ranking":
        raise ValueError("outcome join requires a ranking artifact")
    return OutcomeJoinAuthorization(
        block.provenance_block_identity,
        ranking_contract.artifact_contract_identity,
    )


def open_canonical_outcome_source(
    path: str | Path,
    authorization: OutcomeJoinAuthorization,
) -> tuple[dict[str, Any], ...]:
    """Open one canonical JSONL outcome source after ranking authorization."""

    if not isinstance(authorization, OutcomeJoinAuthorization):
        raise TypeError("outcome source requires OutcomeJoinAuthorization")
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise ValueError(f"outcome source line {line_number} lacks newline")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"outcome source line {line_number} is malformed"
                ) from error
            if not isinstance(record, dict) or canonical_json(record) + "\n" != line:
                raise ValueError("outcome source is not canonical")
            records.append(record)
    if not records:
        raise ValueError("outcome source contains no records")
    return tuple(records)


@dataclass(frozen=True, slots=True)
class ExperimentAuditManifest:
    outcome_blind_provenance: OutcomeBlindProvenanceBlock
    artifact_contracts: tuple[tuple[str, ArtifactContract], ...]
    evaluation_dispositions: tuple[EvaluationDisposition, ...]
    execution_conformance_result: str
    audit_manifest_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_named_objects(
            "artifact_contracts", self.artifact_contracts, ArtifactContract
        )
        if not self.artifact_contracts:
            raise ValueError("audit manifest requires artifact contracts")
        _require_tuple(
            "evaluation_dispositions",
            self.evaluation_dispositions,
            EvaluationDisposition,
        )
        eligible = tuple(
            disposition.round_identity
            for disposition in self.outcome_blind_provenance.population_dispositions
            if disposition.status == "eligible"
        )
        actual = tuple(
            disposition.round_identity for disposition in self.evaluation_dispositions
        )
        if actual != eligible:
            raise ValueError("evaluation dispositions do not reconcile with eligibility")
        if self.execution_conformance_result != "passed":
            raise ValueError("only a conformant execution can be sealed")
        contracts_by_kind: dict[str, list[ArtifactContract]] = {}
        for _, contract in self.artifact_contracts:
            kind = contract.declaration.artifact_kind
            contracts_by_kind.setdefault(kind, []).append(contract)
        required_kinds = {
            "outcome_blind_provenance",
            "ranking",
            "outcome_source",
            "evaluation",
        }
        missing_kinds = required_kinds.difference(contracts_by_kind)
        if missing_kinds:
            raise ValueError(
                "audit manifest is missing lifecycle artifacts: "
                + ", ".join(sorted(missing_kinds))
            )
        if len(contracts_by_kind["outcome_blind_provenance"]) != 1:
            raise ValueError("manifest requires one frozen provenance artifact")
        if len(contracts_by_kind["ranking"]) != 1:
            raise ValueError("manifest requires one frozen ranking artifact")
        ranking = contracts_by_kind["ranking"][0]
        if (
            self.outcome_blind_provenance.provenance_block_identity
            not in ranking.upstream_dependency_identities
        ):
            raise ValueError("ranking artifact is not bound to frozen provenance")
        outcome_source_identities = {
            contract.artifact_contract_identity
            for contract in contracts_by_kind["outcome_source"]
        }
        for evaluation in contracts_by_kind["evaluation"]:
            dependencies = set(evaluation.upstream_dependency_identities)
            if ranking.artifact_contract_identity not in dependencies or not (
                outcome_source_identities.intersection(dependencies)
            ):
                raise ValueError("evaluation artifact is missing frozen inputs")
        declared = {
            declaration.declaration_identity
            for _, declaration in (
                self.outcome_blind_provenance.downstream_artifact_declarations
            )
        }
        for kind, contracts in contracts_by_kind.items():
            for contract in contracts:
                if kind == "outcome_blind_provenance":
                    continue
                if contract.declaration.declaration_identity not in declared:
                    raise ValueError(
                        f"artifact kind {kind} was not declared before the "
                        "outcome boundary"
                    )
        object.__setattr__(
            self,
            "audit_manifest_identity",
            identity(_AUDIT_MANIFEST_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, Any]:
        return {
            "artifact_contracts": tuple(
                {"contract": contract.to_dict(), "name": name}
                for name, contract in self.artifact_contracts
            ),
            "evaluation_dispositions": tuple(
                disposition.to_dict() for disposition in self.evaluation_dispositions
            ),
            "execution_conformance_result": self.execution_conformance_result,
            "outcome_blind_provenance": self.outcome_blind_provenance.to_dict(),
            "canonical_encoding_version": CANONICAL_ENCODING_VERSION,
            "schema_version": AUDIT_MANIFEST_SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_identity_material(),
            "audit_manifest_identity": self.audit_manifest_identity,
        }


def seal_audit_manifest(
    path: str | Path, manifest: ExperimentAuditManifest
) -> tuple[str, int]:
    if not isinstance(manifest, ExperimentAuditManifest):
        raise TypeError("manifest must be ExperimentAuditManifest")
    write_canonical_json_once(path, manifest.to_dict())
    validate_audit_manifest(path, expected=manifest)
    persisted = Path(path).read_bytes()
    return hashlib.sha256(persisted).hexdigest(), len(persisted)


def validate_audit_manifest(
    path: str | Path,
    *,
    expected: ExperimentAuditManifest | None = None,
) -> dict[str, Any]:
    """Validate canonical form and every embedded identity recursively."""

    manifest_path = Path(path)
    lines = manifest_path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) != 1 or not lines[0].endswith("\n"):
        raise ValueError("audit manifest must be one newline-terminated record")
    try:
        material = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise ValueError("audit manifest is malformed") from error
    if not isinstance(material, dict) or canonical_json(material) + "\n" != lines[0]:
        raise ValueError("audit manifest is not canonical")
    _validate_embedded_identities(material)
    _validate_manifest_semantics(material)
    if material.get("schema_version") != AUDIT_MANIFEST_SCHEMA_VERSION:
        raise ValueError("audit manifest schema is unsupported")
    if material.get("execution_conformance_result") != "passed":
        raise ValueError("audit manifest does not record conformance")
    if expected is not None and canonical_json(material) != canonical_json(
        expected.to_dict()
    ):
        raise ValueError("audit manifest differs from reconstructed execution")
    return material


def _validate_manifest_semantics(material: Mapping[str, Any]) -> None:
    block = material["outcome_blind_provenance"]
    specification = block["specification"]
    experiment = block["experiment"]
    replay = block["replay"]
    source = block["source_commit"]
    if experiment["specification"] != specification:
        raise ValueError("experiment and specification bindings disagree")
    if (
        replay["specification_identity"] != specification["specification_identity"]
        or replay["experiment_binding_identity"]
        != experiment["experiment_binding_identity"]
        or replay["source_commit_provenance_identity"]
        != source["source_commit_provenance_identity"]
    ):
        raise ValueError("Replay provenance does not match execution bindings")
    _validate_serialized_named_entries(
        block["component_identities"], "component identities", "identity"
    )
    _validate_serialized_named_entries(
        block["upstream_artifact_contracts"],
        "upstream artifact contracts",
        "contract",
    )
    _validate_serialized_named_entries(
        block["downstream_artifact_declarations"],
        "downstream artifact declarations",
        "declaration",
    )
    for scope in source["scopes"]:
        if not isinstance(scope, dict) or set(scope) != {
            "git_object_identity",
            "repository_path",
        }:
            raise ValueError("source scope schema is invalid")
    scope_paths = [entry["repository_path"] for entry in source["scopes"]]
    if scope_paths != sorted(set(scope_paths)) or not scope_paths:
        raise ValueError("source scopes are not canonical")

    replay_rounds = replay["ordered_replay_round_identities"]
    dispositions = block["population_dispositions"]
    disposition_rounds = [entry["round_identity"] for entry in dispositions]
    if disposition_rounds != replay_rounds or len(set(disposition_rounds)) != len(
        disposition_rounds
    ):
        raise ValueError("pre-outcome population accounting is inconsistent")
    eligible: list[str] = []
    for disposition in dispositions:
        if disposition["status"] == "eligible":
            if disposition["reason"] is not None:
                raise ValueError("eligible disposition has an exclusion reason")
            _require_sha256("decision_identity", disposition["decision_identity"])
            eligible.append(disposition["round_identity"])
        elif disposition["status"] == "excluded":
            _require_nonempty("reason", disposition["reason"])
            if disposition["decision_identity"] is not None:
                raise ValueError("excluded disposition has a decision identity")
        else:
            raise ValueError("pre-outcome disposition status is unsupported")

    evaluation_dispositions = material["evaluation_dispositions"]
    if [entry["round_identity"] for entry in evaluation_dispositions] != eligible:
        raise ValueError("post-outcome dispositions do not reconcile")
    for disposition in evaluation_dispositions:
        if disposition["status"] == "evaluated":
            _require_sha256(
                "outcome_source_identity", disposition["outcome_source_identity"]
            )
        elif disposition["status"] == "excluded":
            if disposition["outcome_source_identity"] is not None:
                raise ValueError("excluded evaluation binds an outcome source")
        else:
            raise ValueError("evaluation disposition status is unsupported")

    artifact_entries = material["artifact_contracts"]
    _validate_serialized_named_entries(
        artifact_entries, "artifact contracts", "contract"
    )
    contracts_by_kind: dict[str, list[Mapping[str, Any]]] = {}
    for entry in artifact_entries:
        contract = entry["contract"]
        if contract["reconstruction_status"] != "validated":
            raise ValueError("artifact reconstruction was not validated")
        _require_nonnegative_integer("byte_count", contract["byte_count"])
        _require_nonnegative_integer("record_count", contract["record_count"])
        dependencies = contract["upstream_dependency_identities"]
        if len(dependencies) != len(set(dependencies)):
            raise ValueError("artifact dependencies are duplicated")
        contracts_by_kind.setdefault(
            contract["declaration"]["artifact_kind"], []
        ).append(contract)
    required_kinds = {
        "outcome_blind_provenance",
        "ranking",
        "outcome_source",
        "evaluation",
    }
    if missing := required_kinds.difference(contracts_by_kind):
        raise ValueError(
            "audit manifest is missing lifecycle artifacts: "
            + ", ".join(sorted(missing))
        )
    if len(contracts_by_kind["outcome_blind_provenance"]) != 1 or len(
        contracts_by_kind["ranking"]
    ) != 1:
        raise ValueError("audit manifest has an ambiguous freeze boundary")
    ranking = contracts_by_kind["ranking"][0]
    if block["provenance_block_identity"] not in ranking[
        "upstream_dependency_identities"
    ]:
        raise ValueError("ranking artifact is not bound to frozen provenance")
    outcome_identities = {
        contract["artifact_contract_identity"]
        for contract in contracts_by_kind["outcome_source"]
    }
    for evaluation in contracts_by_kind["evaluation"]:
        dependencies = set(evaluation["upstream_dependency_identities"])
        if ranking["artifact_contract_identity"] not in dependencies or not (
            outcome_identities.intersection(dependencies)
        ):
            raise ValueError("evaluation artifact is missing frozen inputs")
    declarations = {
        entry["declaration"]["declaration_identity"]
        for entry in block["downstream_artifact_declarations"]
    }
    for kind, contracts in contracts_by_kind.items():
        if kind == "outcome_blind_provenance":
            continue
        for contract in contracts:
            if contract["declaration"]["declaration_identity"] not in declarations:
                raise ValueError("artifact was not declared before outcome join")


def _validate_serialized_named_entries(
    entries: object, name: str, payload_name: str
) -> None:
    if not isinstance(entries, list):
        raise ValueError(f"{name} must be an array")
    names: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{name} contain a malformed entry")
        if set(entry) != {"name", payload_name}:
            raise ValueError(f"{name} entry schema is invalid")
        entry_name = entry.get("name")
        _require_safe_name(name, entry_name)
        names.append(entry_name)
    if names != sorted(set(names)):
        raise ValueError(f"{name} are not unique and canonically ordered")


def _validate_embedded_identities(value: object) -> None:
    if isinstance(value, list):
        for item in value:
            _validate_embedded_identities(item)
        return
    if not isinstance(value, dict):
        return
    for item in value.values():
        _validate_embedded_identities(item)
    # A serialized contract can contain referenced identities with the same
    # field names as identities owned by nested contracts.  Validate exactly
    # the identity owned by this mapping, then recurse into nested mappings.
    # The order is from outermost to innermost contract type.
    domains = {
        "audit_manifest_identity": _AUDIT_MANIFEST_DOMAIN,
        "provenance_block_identity": _PROVENANCE_BLOCK_DOMAIN,
        "artifact_contract_identity": _ARTIFACT_CONTRACT_DOMAIN,
        "declaration_identity": _ARTIFACT_DECLARATION_DOMAIN,
        "evaluation_disposition_identity": _EVALUATION_DISPOSITION_DOMAIN,
        "disposition_identity": _DISPOSITION_DOMAIN,
        "replay_identity": _REPLAY_IDENTITY_DOMAIN,
        "dataset_identity": _DATASET_BINDING_DOMAIN,
        "source_commit_provenance_identity": _SOURCE_COMMIT_DOMAIN,
        "experiment_binding_identity": _EXPERIMENT_BINDING_DOMAIN,
        "specification_identity": _SPECIFICATION_BINDING_DOMAIN,
    }
    schemas = {
        "audit_manifest_identity": {
            "artifact_contracts",
            "audit_manifest_identity",
            "canonical_encoding_version",
            "evaluation_dispositions",
            "execution_conformance_result",
            "outcome_blind_provenance",
            "schema_version",
        },
        "provenance_block_identity": {
            "canonical_encoding_version",
            "component_identities",
            "downstream_artifact_declarations",
            "experiment",
            "population_dispositions",
            "provenance_block_identity",
            "replay",
            "schema_version",
            "source_commit",
            "specification",
            "upstream_artifact_contracts",
        },
        "artifact_contract_identity": {
            "artifact_contract_identity",
            "byte_count",
            "canonical_content_identity",
            "canonical_encoding_version",
            "declaration",
            "persisted_sha256",
            "reconstruction_status",
            "record_count",
            "upstream_dependency_identities",
        },
        "declaration_identity": {
            "artifact_kind",
            "canonical_encoding_version",
            "container",
            "declaration_identity",
            "record_ordering",
            "schema_version",
        },
        "evaluation_disposition_identity": {
            "canonical_encoding_version",
            "evaluation_disposition_identity",
            "outcome_source_identity",
            "reason",
            "round_identity",
            "round_reference",
            "schema_version",
            "status",
        },
        "disposition_identity": {
            "canonical_encoding_version",
            "decision_identity",
            "disposition_identity",
            "reason",
            "round_identity",
            "round_reference",
            "schema_version",
            "status",
        },
        "replay_identity": {
            "canonical_candidate_order",
            "canonical_encoding_version",
            "dataset",
            "decision_selection_configuration_identity",
            "experiment_binding_identity",
            "experiment_configuration_identity",
            "ordered_replay_round_identities",
            "protocol_revision_identity",
            "replay_identity",
            "schema_version",
            "source_commit_provenance_identity",
            "specification_identity",
        },
        "dataset_identity": {
            "byte_count",
            "canonical_encoding_version",
            "dataset_identity",
            "dataset_version",
            "schema_identity",
            "schema_version",
            "sha256",
        },
        "source_commit_provenance_identity": {
            "canonical_encoding_version",
            "commit_sha",
            "schema_version",
            "scopes",
            "source_commit_provenance_identity",
        },
        "experiment_binding_identity": {
            "canonical_encoding_version",
            "experiment_binding_identity",
            "experiment_configuration_identity",
            "experiment_identifier",
            "protocol_document_sha256",
            "protocol_revision",
            "schema_version",
            "specification",
        },
        "specification_identity": {
            "canonical_encoding_version",
            "document_sha256",
            "revision",
            "schema_version",
            "specification_identity",
        },
    }
    for field_name, domain in domains.items():
        if field_name in value:
            if set(value) != schemas[field_name]:
                raise ValueError(f"{field_name} schema is invalid")
            stored = value[field_name]
            _require_sha256(field_name, stored)
            identity_material = {
                key: item for key, item in value.items() if key != field_name
            }
            if identity(domain, identity_material) != stored:
                raise ValueError(f"{field_name} does not reconstruct")
            break


def _write_bytes_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"immutable artifact already exists: {path.name}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _git(root: Path, *arguments: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *arguments], cwd=root, text=True, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as error:
        raise ValueError(f"Git provenance validation failed: {' '.join(arguments)}") from error


def _require_sha256(name: str, value: object) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
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
    if not isinstance(value, str) or not _SAFE_NAME_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase canonical name")


def _require_relative_path(name: str, value: object) -> None:
    _require_nonempty(name, value)
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{name} must be a repository-relative path")


def _require_version(name: str, value: object, expected: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        raise ValueError(f"{name} is unsupported")


def _require_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _require_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _require_tuple(name: str, value: object, item_type: type[Any]) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    if not all(isinstance(item, item_type) for item in value):
        raise TypeError(f"{name} contains an unsupported value")


def _validate_named_identity_pairs(
    name: str, values: tuple[tuple[str, str], ...]
) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    names: list[str] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"{name} entries must be pairs")
        item_name, item_identity = item
        _require_safe_name(name, item_name)
        _require_sha256(name, item_identity)
        names.append(item_name)
    if tuple(names) != tuple(sorted(names)) or len(names) != len(set(names)):
        raise ValueError(f"{name} must be unique and canonically ordered")


def _validate_named_objects(
    name: str,
    values: tuple[tuple[str, Any], ...],
    item_type: type[Any],
) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    names: list[str] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"{name} entries must be pairs")
        item_name, value = item
        _require_safe_name(name, item_name)
        if not isinstance(value, item_type):
            raise TypeError(f"{name} contains an unsupported value")
        names.append(item_name)
    if tuple(names) != tuple(sorted(names)) or len(names) != len(set(names)):
        raise ValueError(f"{name} must be unique and canonically ordered")


__all__ = (
    "ARTIFACT_CONTRACT_SCHEMA_VERSION",
    "AUDIT_MANIFEST_NAME",
    "AUDIT_MANIFEST_SCHEMA_VERSION",
    "ArtifactContract",
    "ArtifactDeclaration",
    "EXECUTION_SPECIFICATION_REVISION",
    "EXECUTION_SPECIFICATION_SCHEMA_VERSION",
    "EXECUTION_SPECIFICATION_SHA256",
    "EvaluationDisposition",
    "ExecutionSpecificationBinding",
    "ExperimentAuditManifest",
    "ExperimentProtocolBinding",
    "OUTCOME_BLIND_PROVENANCE_NAME",
    "OUTCOME_BLIND_PROVENANCE_SCHEMA_VERSION",
    "OutcomeBlindProvenanceBlock",
    "OutcomeJoinAuthorization",
    "PopulationDisposition",
    "ReplayDatasetBinding",
    "ReplayIdentity",
    "SourceCommitProvenance",
    "SourceScopeBinding",
    "authorize_outcome_join",
    "bind_source_commit",
    "canonical_json",
    "construct_artifact_contract",
    "file_sha256",
    "freeze_outcome_blind_provenance",
    "identity",
    "open_canonical_outcome_source",
    "seal_audit_manifest",
    "validate_audit_manifest",
    "validate_population_accounting",
    "write_canonical_json_once",
    "write_canonical_jsonl_once",
)
