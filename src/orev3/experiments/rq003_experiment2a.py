"""RQ-003 Experiment 2A: outcome-blind ordering characterization.

The module characterizes the exact ordering induced by deployed lamports per
protocol-published miner membership.  It has no outcome-source capability and
contains no baseline, evaluation, Strategy, or economic behavior.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import total_ordering
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from orev3.datasets.rq003_experiment0 import (
    RQ003_EXPERIMENT0_OUTPUT_NAMES,
    RQ003Experiment0Configuration,
    _selected_observation_index,
    build_fundamental_measurement_pipeline,
)
from orev3.experiments.rq003_execution_specification import (
    ArtifactContract,
    ArtifactDeclaration,
    PopulationDisposition,
    ReplayDatasetBinding,
    SourceCommitProvenance,
    bind_source_commit,
    file_sha256,
    identity as execution_identity,
    write_canonical_json_once,
    write_canonical_jsonl_once,
)
from orev3.experiments.rq003_execution_specification_v2 import (
    EXECUTION_SPECIFICATION_V2_REVISION,
    EXECUTION_SPECIFICATION_V2_SHA256,
    OUTCOME_BLIND_CHARACTERIZATION_PROFILE,
    PROFILED_AUDIT_MANIFEST_NAME,
    PROFILED_PROVENANCE_NAME,
    ExecutionProfileBinding,
    ExecutionSpecificationV2Binding,
    ExperimentProtocolV2Binding,
    OutcomeBlindCharacterizationTerminal,
    ProfiledArtifactDeclaration,
    ProfiledExperimentAuditManifest,
    ProfiledExperimentConfiguration,
    ProfiledOutcomeBlindProvenanceBlock,
    ProfiledReplayIdentity,
    construct_profile_artifact_contract,
    freeze_profiled_outcome_blind_provenance,
    seal_profiled_audit_manifest,
    validate_profiled_audit_manifest,
)
from orev3.features.rq003_contracts import canonical_encode
from orev3.features.rq003_deployed_lamports import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
)
from orev3.features.rq003_execution import (
    MeasurementVector,
    RQ003_PIPELINE_IMPLEMENTATION_IDENTITY,
    RQ003ExecutionContext,
)
from orev3.features.rq003_miner_count import (
    MINER_COUNT_DEFINITION,
    MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
)
from orev3.features.rq003_total_miners import (
    TOTAL_MINERS_DEFINITION,
    TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY,
)
from orev3.historical.models import RoundLifecycleIndexRecord
from orev3.replay.engine import select_by_slots_remaining
from orev3.strategy_lab.runner import decision_context_from_replay_point


EXPERIMENT2A_SCHEMA_VERSION = 1
EXPERIMENT2A_PROTOCOL_REVISION = "1"
EXPERIMENT2A_PROTOCOL_DOCUMENT_SHA256 = (
    "7a4e2fd5dfa3752711d34f7401658d4586103394c0e243b48365c6a6dbcc8113"
)
EXPERIMENT2A_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)
EXPERIMENT2A_REQUESTED_SLOTS_REMAINING = 5

CHARACTERIZATION_ARTIFACT_NAME = "characterization_artifact.jsonl"
POPULATION_ARTIFACT_NAME = "population.json"
DERIVED_MEASUREMENT_ARTIFACT_NAME = "derived_measurement.json"
ORDERING_DISTRIBUTIONS_ARTIFACT_NAME = "ordering_distributions.json"
BOARD_CHARACTERISTICS_ARTIFACT_NAME = "board_characteristics.json"
THEORETICAL_BOUND_ARTIFACT_NAME = "theoretical_bound.json"
GOVERNANCE_DISPOSITION_ARTIFACT_NAME = "governance_disposition.json"
FINDING_002_ARTIFACT_NAME = "finding_002.json"
CONFORMANCE_ARTIFACT_NAME = "conformance.json"

EXPERIMENT2A_ARTIFACT_NAMES = (
    PROFILED_PROVENANCE_NAME,
    CHARACTERIZATION_ARTIFACT_NAME,
    POPULATION_ARTIFACT_NAME,
    DERIVED_MEASUREMENT_ARTIFACT_NAME,
    ORDERING_DISTRIBUTIONS_ARTIFACT_NAME,
    BOARD_CHARACTERISTICS_ARTIFACT_NAME,
    THEORETICAL_BOUND_ARTIFACT_NAME,
    GOVERNANCE_DISPOSITION_ARTIFACT_NAME,
    FINDING_002_ARTIFACT_NAME,
    CONFORMANCE_ARTIFACT_NAME,
    PROFILED_AUDIT_MANIFEST_NAME,
)

IDENTICAL_RANK_VECTORS = "identical_average_rank_vectors"
TIE_ONLY_CHANGE = "tie_only_change"
STRICT_ORDERING_CHANGE = "strict_ordering_change"
ORDERING_CLASSES = (
    IDENTICAL_RANK_VECTORS,
    TIE_ONLY_CHANGE,
    STRICT_ORDERING_CHANGE,
)

_RATIONAL_DOMAIN = "rq003-experiment-002a-canonical-rational-v1"
_DERIVED_DEFINITION_DOMAIN = "rq003-experiment-002a-deployment-per-miner-definition-v1"
_RAW_ORDERING_DOMAIN = "rq003-experiment-002a-raw-ordering-v1"
_DERIVED_ORDERING_DOMAIN = "rq003-experiment-002a-derived-ordering-v1"
_CHARACTERIZATION_RECORD_DOMAIN = "rq003-experiment-002a-characterization-record-v1"
_REPORT_DOMAIN = "rq003-experiment-002a-report-v1"
_EXPERIMENT_CONFIGURATION_DOMAIN = "rq003-experiment-002a-configuration-v1"
_DECISION_CONFIGURATION_DOMAIN = "rq003-experiment-002a-decision-selection-v1"
_REPLAY_DATASET_SCHEMA_DOMAIN = "rq003-experiment-002a-replay-dataset-schema-v1"
_REPLAY_ROUND_DOMAIN = "rq003-experiment-002a-replay-round-v1"
_PROTOCOL_REVISION_POPULATION_DOMAIN = "rq003-experiment-002a-protocol-revision-population-v1"
_MEASUREMENT_COMPONENT_SET_DOMAIN = "rq003-experiment-002a-measurement-component-set-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_SOURCE_SCOPES = (
    "docs/research/experiments/rq003-experiment-002a-deployment-per-miner-characterization.md",
    "docs/research/specifications/rq003-research-execution-specification-v2.md",
    "src/orev3",
)

EXPERIMENT2A_SPECIFICATION_BINDING = ExecutionSpecificationV2Binding(
    EXECUTION_SPECIFICATION_V2_REVISION,
    EXECUTION_SPECIFICATION_V2_SHA256,
)
EXPERIMENT2A_PROFILE_BINDING = ExecutionProfileBinding(
    OUTCOME_BLIND_CHARACTERIZATION_PROFILE
)
EXPERIMENT2A_DATASET_SCHEMA_IDENTITY = execution_identity(
    _REPLAY_DATASET_SCHEMA_DOMAIN,
    {"lifecycle_schema_version": 1, "record_kind": "RoundLifecycleIndexRecord"},
)
EXPERIMENT2A_PROTOCOL_REVISION_POPULATION_IDENTITY = execution_identity(
    _PROTOCOL_REVISION_POPULATION_DOMAIN,
    {
        "official_source_revision": EXPERIMENT2A_PROTOCOL_SOURCE_REVISION,
        "scope": "homogeneous_legacy_replay_population",
    },
)
EXPERIMENT2A_MEASUREMENT_COMPONENT_SET_IDENTITY = execution_identity(
    _MEASUREMENT_COMPONENT_SET_DOMAIN,
    {
        "ordered_definition_identities": (
            DEPLOYED_LAMPORTS_DEFINITION.definition_identity,
            MINER_COUNT_DEFINITION.definition_identity,
            TOTAL_MINERS_DEFINITION.definition_identity,
        ),
        "ordered_executable_binding_identities": (
            DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
            MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
            TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY,
        ),
        "pipeline_implementation_identity": RQ003_PIPELINE_IMPLEMENTATION_IDENTITY,
    },
)


@total_ordering
@dataclass(frozen=True, slots=True)
class CanonicalRational:
    """One exact reduced non-negative rational value."""

    numerator: int
    denominator: int
    rational_identity: str = field(init=False, compare=False)

    def __post_init__(self) -> None:
        _require_nonnegative_integer("numerator", self.numerator)
        _require_positive_integer("denominator", self.denominator)
        divisor = math.gcd(self.numerator, self.denominator)
        if divisor != 1:
            raise ValueError("rational pair must be canonically reduced")
        object.__setattr__(
            self,
            "rational_identity",
            execution_identity(_RATIONAL_DOMAIN, self.to_identity_material()),
        )

    @classmethod
    def make(cls, numerator: int, denominator: int = 1) -> CanonicalRational:
        _require_nonnegative_integer("numerator", numerator)
        _require_positive_integer("denominator", denominator)
        divisor = math.gcd(numerator, denominator)
        return cls(numerator // divisor, denominator // divisor)

    @classmethod
    def from_dict(cls, material: Mapping[str, Any]) -> CanonicalRational:
        if set(material) != {"denominator", "numerator", "rational_identity"}:
            raise ValueError("canonical rational schema is invalid")
        value = cls(material["numerator"], material["denominator"])
        if value.rational_identity != material["rational_identity"]:
            raise ValueError("canonical rational identity does not reconstruct")
        return value

    def to_identity_material(self) -> dict[str, int]:
        return {"denominator": self.denominator, "numerator": self.numerator}

    def to_dict(self) -> dict[str, Any]:
        return {**self.to_identity_material(), "rational_identity": self.rational_identity}

    def compare(self, other: CanonicalRational) -> int:
        if not isinstance(other, CanonicalRational):
            raise TypeError("rational comparison requires CanonicalRational")
        left = self.numerator * other.denominator
        right = other.numerator * self.denominator
        return (left > right) - (left < right)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, CanonicalRational):
            return NotImplemented
        return self.compare(other) < 0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CanonicalRational) and (
            self.numerator == other.numerator
            and self.denominator == other.denominator
        )

    def add(self, other: CanonicalRational) -> CanonicalRational:
        return CanonicalRational.make(
            self.numerator * other.denominator
            + other.numerator * self.denominator,
            self.denominator * other.denominator,
        )

    def subtract_nonnegative(self, other: CanonicalRational) -> CanonicalRational:
        numerator = (
            self.numerator * other.denominator
            - other.numerator * self.denominator
        )
        if numerator < 0:
            raise ValueError("rational difference is negative")
        return CanonicalRational.make(numerator, self.denominator * other.denominator)

    def absolute_difference(self, other: CanonicalRational) -> CanonicalRational:
        if self >= other:
            return self.subtract_nonnegative(other)
        return other.subtract_nonnegative(self)

    def divide_by_integer(self, divisor: int) -> CanonicalRational:
        _require_positive_integer("divisor", divisor)
        return CanonicalRational.make(self.numerator, self.denominator * divisor)

    def reciprocal(self) -> CanonicalRational:
        if self.numerator == 0:
            raise ValueError("zero has no reciprocal")
        return CanonicalRational.make(self.denominator, self.numerator)


DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY = execution_identity(
    _DERIVED_DEFINITION_DOMAIN,
    {
        "comparison": "exact_integer_cross_multiplication",
        "deployed_lamports_definition_identity": DEPLOYED_LAMPORTS_DEFINITION.definition_identity,
        "empty_square_extension": {"denominator": 1, "numerator": 0},
        "miner_count_definition_identity": MINER_COUNT_DEFINITION.definition_identity,
        "name": "deployment_per_miner",
        "positive_deployment_zero_miners": "invalid",
        "representation": "reduced_nonnegative_rational_pair",
        "unit": "lamports_per_protocol_published_miner_membership",
    },
)


@dataclass(frozen=True, slots=True)
class OutcomeBlindReplayPopulation:
    """Replay-owned immutable population exposed to characterization."""

    lifecycles: tuple[RoundLifecycleIndexRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.lifecycles, tuple) or not all(
            isinstance(value, RoundLifecycleIndexRecord) for value in self.lifecycles
        ):
            raise TypeError("lifecycles must be an immutable tuple")
        if not self.lifecycles:
            raise ValueError("outcome-blind Replay population cannot be empty")
        order = tuple((value.start_slot, value.round_id) for value in self.lifecycles)
        if order != tuple(sorted(set(order))):
            raise ValueError("outcome-blind Replay population is not canonical")
        for lifecycle in self.lifecycles:
            if (
                lifecycle.finalized_outcome is not None
                or lifecycle.finalized_outcome_source is not None
                or lifecycle.finalized_outcome_capture_mode is not None
                or lifecycle.finalized_outcome_evidence_identities
                or lifecycle.quality.finalized_state_observed
            ):
                raise ValueError("outcome-blind Replay population exposes outcome state")


@dataclass(frozen=True, slots=True)
class Experiment2AConfiguration:
    replay_dataset_path: Path
    replay_population: OutcomeBlindReplayPopulation
    output_directory: Path
    expected_dataset_sha256: str
    requested_slots_remaining: int = EXPERIMENT2A_REQUESTED_SLOTS_REMAINING
    source_commit_sha: str | None = None
    repository_root: Path = _REPOSITORY_ROOT
    decision_configuration_identity: str = field(init=False)
    experiment_specific_configuration_identity: str = field(init=False)
    profiled_configuration: ProfiledExperimentConfiguration = field(init=False)

    def __post_init__(self) -> None:
        replay_path = Path(self.replay_dataset_path)
        output = Path(self.output_directory)
        if not isinstance(self.replay_population, OutcomeBlindReplayPopulation):
            raise TypeError("replay_population must be OutcomeBlindReplayPopulation")
        if replay_path.resolve() == output.resolve():
            raise ValueError("output directory cannot replace the replay dataset")
        _require_sha256("expected_dataset_sha256", self.expected_dataset_sha256)
        if self.requested_slots_remaining != EXPERIMENT2A_REQUESTED_SLOTS_REMAINING:
            raise ValueError("Experiment 2A requires requested_slots_remaining=5")
        if self.source_commit_sha is not None and not re.fullmatch(
            r"[0-9a-f]{40}|[0-9a-f]{64}", self.source_commit_sha
        ):
            raise ValueError("source_commit_sha must be a full Git identity")
        object.__setattr__(self, "replay_dataset_path", replay_path)
        object.__setattr__(self, "output_directory", output)
        object.__setattr__(self, "repository_root", Path(self.repository_root).resolve())
        decision_identity = execution_identity(
            _DECISION_CONFIGURATION_DOMAIN,
            {
                "candidate_order": tuple(range(25)),
                "lifecycle_order": ("start_slot", "round_id"),
                "requested_slots_remaining": self.requested_slots_remaining,
                "selection_rule": "latest_observation_at_or_before_slot",
            },
        )
        object.__setattr__(self, "decision_configuration_identity", decision_identity)
        specific_identity = execution_identity(
            _EXPERIMENT_CONFIGURATION_DOMAIN,
            {
                "artifact_names": EXPERIMENT2A_ARTIFACT_NAMES,
                "candidate_order": tuple(range(25)),
                "dataset_sha256": self.expected_dataset_sha256,
                "decision_configuration_identity": decision_identity,
                "derived_measurement_identity": DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
                "ordering_classes": ORDERING_CLASSES,
                "protocol_document_sha256": EXPERIMENT2A_PROTOCOL_DOCUMENT_SHA256,
                "protocol_revision": EXPERIMENT2A_PROTOCOL_REVISION,
                "requested_slots_remaining": self.requested_slots_remaining,
            },
        )
        object.__setattr__(self, "experiment_specific_configuration_identity", specific_identity)
        object.__setattr__(
            self,
            "profiled_configuration",
            ProfiledExperimentConfiguration(EXPERIMENT2A_PROFILE_BINDING, specific_identity),
        )


@dataclass(frozen=True, slots=True)
class Experiment2AResult:
    dataset_sha256: str
    replay_identity: str
    audit_manifest_identity: str
    source_commit_sha: str
    replay_rounds: int
    eligible_decisions: int
    excluded_decisions: int
    artifacts: tuple[tuple[str, Path, str], ...]

    def __post_init__(self) -> None:
        for name in (
            "dataset_sha256",
            "replay_identity",
            "audit_manifest_identity",
        ):
            _require_sha256(name, getattr(self, name))
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.source_commit_sha):
            raise ValueError("source_commit_sha is invalid")
        for name in ("replay_rounds", "eligible_decisions", "excluded_decisions"):
            _require_nonnegative_integer(name, getattr(self, name))
        if self.eligible_decisions + self.excluded_decisions != self.replay_rounds:
            raise ValueError("Experiment 2A population accounting is incomplete")


def deployment_per_miner(
    deployed_lamports: int,
    miner_count: int,
) -> tuple[CanonicalRational, bool]:
    """Return the exact protocol-defined ratio and empty-extension flag."""

    _require_u64("deployed_lamports", deployed_lamports)
    _require_u64("miner_count", miner_count)
    if miner_count > 0:
        return CanonicalRational.make(deployed_lamports, miner_count), False
    if deployed_lamports == 0:
        return CanonicalRational.make(0, 1), True
    raise ValueError("positive deployment with zero miners is invalid")


def exact_average_ranks(
    values: Sequence[int] | Sequence[CanonicalRational],
) -> tuple[CanonicalRational, ...]:
    """Return descending one-based average ranks with exact ties."""

    if len(values) != 25:
        raise ValueError("ordering requires exactly 25 candidates")
    normalized: tuple[CanonicalRational, ...] = tuple(
        CanonicalRational.make(value)
        if isinstance(value, int) and not isinstance(value, bool)
        else value
        for value in values
    )  # type: ignore[arg-type]
    if not all(isinstance(value, CanonicalRational) for value in normalized):
        raise TypeError("ordering values must be integers or CanonicalRational")
    order = sorted(range(25), key=lambda square: normalized[square], reverse=True)
    ranks: list[CanonicalRational | None] = [None] * 25
    first = 0
    while first < 25:
        last = first + 1
        while last < 25 and normalized[order[last]] == normalized[order[first]]:
            last += 1
        average = CanonicalRational.make(2 * first + (last - first) + 1, 2)
        for position in range(first, last):
            ranks[order[position]] = average
        first = last
    if any(value is None for value in ranks):
        raise ValueError("average-rank vector is incomplete")
    return tuple(ranks)  # type: ignore[return-value]


def characterize_orderings(
    deployed_lamports: Sequence[int],
    miner_counts: Sequence[int],
) -> dict[str, Any]:
    """Characterize one decision with exact, outcome-free arithmetic."""

    if len(deployed_lamports) != 25 or len(miner_counts) != 25:
        raise ValueError("characterization requires exactly 25 candidates")
    deployed = tuple(_require_u64("deployed_lamports", value) for value in deployed_lamports)
    miners = tuple(_require_u64("miner_count", value) for value in miner_counts)
    ratios_with_flags = tuple(
        deployment_per_miner(deployed[square], miners[square])
        for square in range(25)
    )
    ratios = tuple(value for value, _ in ratios_with_flags)
    empty_flags = tuple(flag for _, flag in ratios_with_flags)
    raw_ranks = exact_average_ranks(deployed)
    derived_ranks = exact_average_ranks(ratios)

    disagreements = 0
    reversals = 0
    tie_to_strict = 0
    strict_to_tie = 0
    for left in range(25):
        for right in range(left + 1, 25):
            raw_sign = (deployed[left] > deployed[right]) - (deployed[left] < deployed[right])
            derived_sign = ratios[left].compare(ratios[right])
            if raw_sign != derived_sign:
                disagreements += 1
            if raw_sign and derived_sign and raw_sign == -derived_sign:
                reversals += 1
            elif raw_sign == 0 and derived_sign != 0:
                tie_to_strict += 1
            elif raw_sign != 0 and derived_sign == 0:
                strict_to_tie += 1

    if raw_ranks == derived_ranks:
        classification = IDENTICAL_RANK_VECTORS
    elif reversals:
        classification = STRICT_ORDERING_CHANGE
    else:
        if tie_to_strict + strict_to_tie == 0:
            raise ValueError("different rank vectors lack a protocol classification")
        classification = TIE_ONLY_CHANGE

    displacements = tuple(
        raw_ranks[square].absolute_difference(derived_ranks[square])
        for square in range(25)
    )
    total_displacement = _sum_rationals(displacements)
    mean_displacement = total_displacement.divide_by_integer(25)
    maximum_displacement = max(displacements)
    raw_groups = _tie_groups(tuple(CanonicalRational.make(value) for value in deployed))
    derived_groups = _tie_groups(ratios)
    top_k = {
        str(k): tuple(
            square for square, rank in enumerate(raw_ranks) if rank <= CanonicalRational.make(k)
        )
        != tuple(
            square for square, rank in enumerate(derived_ranks) if rank <= CanonicalRational.make(k)
        )
        for k in (1, 3, 5)
    }
    improvements = tuple(
        derived_ranks[square].reciprocal().subtract_nonnegative(
            raw_ranks[square].reciprocal()
        )
        if derived_ranks[square] <= raw_ranks[square]
        else CanonicalRational.make(0)
        for square in range(25)
    )
    upper_bound = max(improvements)
    return {
        "absolute_rank_displacements": tuple(
            value.to_dict() for value in displacements
        ),
        "classification": classification,
        "deployment_per_miner": tuple(value.to_dict() for value in ratios),
        "derived_average_ranks": tuple(value.to_dict() for value in derived_ranks),
        "derived_ordering_identity": execution_identity(
            _DERIVED_ORDERING_DOMAIN,
            {
                "definition_identity": DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
                "ranks": tuple(value.to_dict() for value in derived_ranks),
                "values": tuple(value.to_dict() for value in ratios),
            },
        ),
        "derived_tie_group_count": len(derived_groups),
        "derived_largest_tie_group_size": max(derived_groups),
        "derived_tie_group_sizes": derived_groups,
        "empty_square_extension_count": sum(empty_flags),
        "maximum_absolute_rank_displacement": maximum_displacement.to_dict(),
        "mean_absolute_rank_displacement": mean_displacement.to_dict(),
        "pairwise_sign_disagreements": disagreements,
        "unordered_candidate_pair_count": 300,
        "raw_average_ranks": tuple(value.to_dict() for value in raw_ranks),
        "raw_ordering_identity": execution_identity(
            _RAW_ORDERING_DOMAIN,
            {
                "ranks": tuple(value.to_dict() for value in raw_ranks),
                "values": deployed,
            },
        ),
        "raw_tie_group_count": len(raw_groups),
        "raw_largest_tie_group_size": max(raw_groups),
        "raw_tie_group_sizes": raw_groups,
        "strict_reversals": reversals,
        "strict_to_tie_changes": strict_to_tie,
        "theoretical_mrr_improvement_upper_bound": upper_bound.to_dict(),
        "tie_to_strict_changes": tie_to_strict,
        "top_k_membership_changes": top_k,
        "total_rank_displacement": total_displacement.to_dict(),
    }


def execute_experiment2a(configuration: Experiment2AConfiguration) -> Experiment2AResult:
    """Execute the complete v2 outcome-blind characterization lifecycle."""

    if not isinstance(configuration, Experiment2AConfiguration):
        raise TypeError("configuration must be Experiment2AConfiguration")
    source_commit = _bind_execution_source(configuration)
    dataset_sha256 = file_sha256(configuration.replay_dataset_path)
    if dataset_sha256 != configuration.expected_dataset_sha256:
        raise ValueError("replay dataset SHA-256 does not match configuration")
    lifecycles = configuration.replay_population.lifecycles
    dataset = ReplayDatasetBinding(
        "replay-dataset-v1",
        EXPERIMENT2A_DATASET_SCHEMA_IDENTITY,
        configuration.replay_dataset_path.stat().st_size,
        dataset_sha256,
    )
    experiment = _experiment_binding(configuration)
    round_identity_by_id = {
        lifecycle.round_id: _replay_round_identity(lifecycle)
        for lifecycle in lifecycles
    }
    replay = ProfiledReplayIdentity(
        specification_identity=EXPERIMENT2A_SPECIFICATION_BINDING.specification_identity,
        profile_identity=EXPERIMENT2A_PROFILE_BINDING.profile_identity,
        experiment_binding_identity=experiment.experiment_binding_identity,
        experiment_configuration_identity=configuration.profiled_configuration.experiment_configuration_identity,
        source_commit_provenance_identity=source_commit.source_commit_provenance_identity,
        dataset=dataset,
        protocol_revision_identity=EXPERIMENT2A_PROTOCOL_REVISION_POPULATION_IDENTITY,
        decision_selection_configuration_identity=configuration.decision_configuration_identity,
        ordered_replay_round_identities=tuple(
            round_identity_by_id[lifecycle.round_id] for lifecycle in lifecycles
        ),
        canonical_candidate_order=tuple(range(25)),
    )
    records, selection_audit = _build_characterizations(configuration, lifecycles)
    dispositions = _population_dispositions(
        lifecycles, selection_audit, records, round_identity_by_id
    )
    declarations = _artifact_declarations()
    block = ProfiledOutcomeBlindProvenanceBlock(
        specification=EXPERIMENT2A_SPECIFICATION_BINDING,
        profile=EXPERIMENT2A_PROFILE_BINDING,
        experiment=experiment,
        source_commit=source_commit,
        replay=replay,
        component_identities=_component_identities(),
        population_dispositions=dispositions,
        upstream_artifact_contracts=(),
        downstream_artifact_declarations=tuple(
            sorted(
                (
                    name,
                    ProfiledArtifactDeclaration(
                        EXPERIMENT2A_PROFILE_BINDING.profile_identity,
                        declaration,
                    ),
                )
                for name, declaration in declarations.items()
            )
        ),
    )

    destination = configuration.output_directory
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("output directory must be absent or empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=destination.name + ".", dir=destination.parent))
    try:
        provenance_contract = freeze_profiled_outcome_blind_provenance(
            temporary / PROFILED_PROVENANCE_NAME, block
        )
        write_canonical_jsonl_once(temporary / CHARACTERIZATION_ARTIFACT_NAME, records)
        characterization_contract = construct_profile_artifact_contract(
            temporary / CHARACTERIZATION_ARTIFACT_NAME,
            declarations[CHARACTERIZATION_ARTIFACT_NAME],
            records,
            (block.provenance_block_identity,),
            EXPERIMENT2A_PROFILE_BINDING,
        )

        reports = _build_reports(lifecycles, dispositions, records, selection_audit)
        report_contracts: dict[str, ArtifactContract] = {}
        for name, report in reports.items():
            write_canonical_json_once(temporary / name, report)
            report_contracts[name] = construct_profile_artifact_contract(
                temporary / name,
                declarations[name],
                (report,),
                (characterization_contract.artifact_contract_identity,),
                EXPERIMENT2A_PROFILE_BINDING,
            )

        artifact_contracts = {
            PROFILED_PROVENANCE_NAME: provenance_contract,
            CHARACTERIZATION_ARTIFACT_NAME: characterization_contract,
            **report_contracts,
        }
        terminal = OutcomeBlindCharacterizationTerminal(dispositions)
        manifest = ProfiledExperimentAuditManifest(
            outcome_blind_provenance=block,
            artifact_contracts=tuple(sorted(artifact_contracts.items())),
            terminal=terminal,
            execution_conformance_result="passed",
        )
        seal_profiled_audit_manifest(
            temporary / PROFILED_AUDIT_MANIFEST_NAME, manifest
        )
        artifacts = validate_experiment2a_artifacts(
            temporary,
            replay_dataset_path=configuration.replay_dataset_path,
            expected_manifest=manifest,
        )
        if destination.exists():
            destination.rmdir()
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return Experiment2AResult(
        dataset_sha256=dataset_sha256,
        replay_identity=replay.replay_identity,
        audit_manifest_identity=manifest.audit_manifest_identity,
        source_commit_sha=source_commit.commit_sha,
        replay_rounds=len(lifecycles),
        eligible_decisions=len(records),
        excluded_decisions=len(lifecycles) - len(records),
        artifacts=tuple(
            (name, destination / name, digest) for name, _, digest in artifacts
        ),
    )


def validate_experiment2a_artifacts(
    output_directory: str | Path,
    *,
    replay_dataset_path: str | Path,
    expected_manifest: ProfiledExperimentAuditManifest | None = None,
) -> tuple[tuple[str, Path, str], ...]:
    """Reconstruct the entire outcome-blind Experiment 2A artifact graph."""

    output = Path(output_directory)
    actual_names = tuple(sorted(path.name for path in output.iterdir() if path.is_file()))
    if actual_names != tuple(sorted(EXPERIMENT2A_ARTIFACT_NAMES)):
        raise ValueError("output directory contains artifacts outside the protocol")
    records = _load_characterization_artifact(output / CHARACTERIZATION_ARTIFACT_NAME)
    reports = {
        name: _load_report(output / name, name.removesuffix(".json"))
        for name in EXPERIMENT2A_ARTIFACT_NAMES
        if name.endswith(".json")
        and name not in {PROFILED_PROVENANCE_NAME, PROFILED_AUDIT_MANIFEST_NAME}
    }
    _validate_report_consistency(records, reports)
    manifest = validate_profiled_audit_manifest(
        output / PROFILED_AUDIT_MANIFEST_NAME,
        expected=expected_manifest,
    )
    if manifest["execution_profile"]["execution_profile"] != OUTCOME_BLIND_CHARACTERIZATION_PROFILE:
        raise ValueError("Experiment 2A manifest has the wrong execution profile")
    replay_path = Path(replay_dataset_path)
    if manifest["outcome_blind_provenance"]["replay"]["dataset"]["sha256"] != file_sha256(replay_path):
        raise ValueError("replay source changed after provenance freeze")
    prohibited = {
        "winning_square",
        "won",
        "label",
        "outcome",
        "outcome_source",
        "outcome_provenance",
        "evaluation",
        "baseline",
    }
    for path in output.iterdir():
        if path.is_file() and path.suffix in {".json", ".jsonl"}:
            _reject_prohibited_fields(path, prohibited)
    return tuple(
        (name, output / name, file_sha256(output / name))
        for name in sorted(EXPERIMENT2A_ARTIFACT_NAMES)
    )


def _build_characterizations(
    configuration: Experiment2AConfiguration,
    lifecycles: Sequence[RoundLifecycleIndexRecord],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    pipeline = build_fundamental_measurement_pipeline()
    deployed_index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("deployed_lamports")
    miner_index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("miner_count")
    total_miners_index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("total_miners")
    records: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for lifecycle in lifecycles:
        if lifecycle.quality.coverage_status != "complete":
            audit.append(
                {"round_id": lifecycle.round_id, "status": "incomplete_lifecycle"}
            )
            continue
        try:
            selection = select_by_slots_remaining(
                lifecycle,
                requested_slots_remaining=configuration.requested_slots_remaining,
                max_slot_distance=None,
            )
        except ValueError as error:
            message = str(error)
            if message.startswith("No observation for round"):
                reason = "no_predeclared_decision_observation"
            elif "has no usable end_slot" in message:
                reason = "no_usable_end_slot"
            else:
                raise
            audit.append({"round_id": lifecycle.round_id, "status": reason})
            continue
        point = selection.replay_point
        if selection.slot_distance is None:
            raise ValueError("selected replay point lacks slot distance")
        observation_index = _selected_observation_index(
            lifecycle, point.source_file, point.source_line_number
        )
        decision_context = decision_context_from_replay_point(point)
        vectors: list[MeasurementVector] = []
        deployed: list[int] = []
        miners: list[int] = []
        decision_identity: str | None = None
        total_miners: int | None = None
        for square in range(25):
            context = RQ003ExecutionContext(
                decision_context=decision_context,
                observation_index=observation_index,
                structural_candidate_key=square,
                decision_point_configuration_identity=configuration.decision_configuration_identity,
            )
            vector = pipeline.compute(context)
            if MeasurementVector.from_canonical_bytes(vector.canonical_bytes()) != vector:
                raise ValueError("MeasurementVector does not reconstruct")
            if decision_identity is None:
                decision_identity = context.decision_snapshot_identity
            elif decision_identity != context.decision_snapshot_identity:
                raise ValueError("candidate contexts do not share a decision identity")
            deployed.append(_require_u64("deployed_lamports", vector.ordered_values[deployed_index]))
            miners.append(_require_u64("miner_count", vector.ordered_values[miner_index]))
            observed_total = _require_u64("total_miners", vector.ordered_values[total_miners_index])
            if total_miners is None:
                total_miners = observed_total
            elif total_miners != observed_total:
                raise ValueError("round.total_miners changed within frozen observation")
            vectors.append(vector)
        characterization = characterize_orderings(deployed, miners)
        if decision_identity is None or total_miners is None:
            raise ValueError("decision state was not constructed")
        board = _board_characteristics(deployed, miners, total_miners)
        material: dict[str, Any] = {
            **characterization,
            "board_characteristics": board,
            "candidate_order": tuple(range(25)),
            "decision_configuration_identity": configuration.decision_configuration_identity,
            "decision_identity": decision_identity,
            "deployed_lamports": tuple(deployed),
            "deployment_per_miner_definition_identity": DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
            "measurement_vector_identities": tuple(vector.vector_identity for vector in vectors),
            "miner_counts": tuple(miners),
            "observation_index": observation_index,
            "round_id": lifecycle.round_id,
            "schema_version": EXPERIMENT2A_SCHEMA_VERSION,
            "selected_rpc_slot": point.rpc_slot,
            "slot_distance": selection.slot_distance,
            "start_slot": lifecycle.start_slot,
        }
        material["characterization_record_identity"] = execution_identity(
            _CHARACTERIZATION_RECORD_DOMAIN, material
        )
        records.append(material)
        audit.append({"round_id": lifecycle.round_id, "status": "eligible"})
    if not records:
        raise ValueError("characterization contains no eligible decisions")
    return tuple(records), tuple(audit)


def _build_reports(
    lifecycles: Sequence[RoundLifecycleIndexRecord],
    dispositions: tuple[PopulationDisposition, ...],
    records: tuple[dict[str, Any], ...],
    selection_audit: tuple[dict[str, Any], ...],
) -> dict[str, dict[str, Any]]:
    class_counts = Counter(record["classification"] for record in records)
    upper_bounds = tuple(
        CanonicalRational.from_dict(record["theoretical_mrr_improvement_upper_bound"])
        for record in records
    )
    population_upper_bound = _sum_rationals(upper_bounds).divide_by_integer(len(records))
    scalar_fields = (
        "unordered_candidate_pair_count",
        "pairwise_sign_disagreements",
        "strict_reversals",
        "tie_to_strict_changes",
        "strict_to_tie_changes",
        "empty_square_extension_count",
        "raw_tie_group_count",
        "derived_tie_group_count",
        "raw_largest_tie_group_size",
        "derived_largest_tie_group_size",
        "total_rank_displacement",
        "mean_absolute_rank_displacement",
        "maximum_absolute_rank_displacement",
        "theoretical_mrr_improvement_upper_bound",
    )
    distributions = {
        field_name: _exact_distribution(
            tuple(_distribution_value(record[field_name]) for record in records)
        )
        for field_name in scalar_fields
    }
    distributions["candidate_absolute_rank_displacement"] = _exact_distribution(
        tuple(
            _distribution_value(value)
            for record in records
            for value in record["absolute_rank_displacements"]
        )
    )
    distributions["raw_tie_group_size"] = _exact_distribution(
        tuple(
            _distribution_value(value)
            for record in records
            for value in record["raw_tie_group_sizes"]
        )
    )
    distributions["derived_tie_group_size"] = _exact_distribution(
        tuple(
            _distribution_value(value)
            for record in records
            for value in record["derived_tie_group_sizes"]
        )
    )
    for k in ("1", "3", "5"):
        distributions[f"top_{k}_membership_change"] = _exact_distribution(
            tuple(
                _distribution_value(
                    int(record["top_k_membership_changes"][k])
                )
                for record in records
            )
        )
    empty_candidates = sum(record["empty_square_extension_count"] for record in records)
    decisions_with_empty = sum(record["empty_square_extension_count"] > 0 for record in records)
    common = {
        "experiment_protocol_revision": EXPERIMENT2A_PROTOCOL_REVISION,
        "protocol_source_revision": EXPERIMENT2A_PROTOCOL_SOURCE_REVISION,
        "schema_version": EXPERIMENT2A_SCHEMA_VERSION,
    }
    reports: dict[str, dict[str, Any]] = {
        POPULATION_ARTIFACT_NAME: _report(
            "population",
            {
                **common,
                "eligible": sum(item.status == "eligible" for item in dispositions),
                "excluded": sum(item.status == "excluded" for item in dispositions),
                "ordered_dispositions": tuple(item.to_dict() for item in dispositions),
                "replay_rounds": len(lifecycles),
                "selection_audit": selection_audit,
            },
        ),
        DERIVED_MEASUREMENT_ARTIFACT_NAME: _report(
            "derived_measurement",
            {
                **common,
                "definition_identity": DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
                "denominator": "miner_count",
                "empty_square_extension": CanonicalRational.make(0).to_dict(),
                "numerator": "deployed_lamports",
                "positive_deployment_zero_miners": "invalid",
                "representation": "canonical_reduced_rational_pair",
            },
        ),
        ORDERING_DISTRIBUTIONS_ARTIFACT_NAME: _report(
            "ordering_distributions",
            {
                **common,
                "class_counts": tuple(
                    {
                        "classification": classification,
                        "count": class_counts[classification],
                        "proportion": CanonicalRational.make(class_counts[classification], len(records)).to_dict(),
                    }
                    for classification in ORDERING_CLASSES
                ),
                "decision_count": len(records),
                "distributions": distributions,
                "empty_square_extension": {
                    "candidate_instances": empty_candidates,
                    "candidate_instance_proportion": CanonicalRational.make(empty_candidates, len(records) * 25).to_dict(),
                    "decisions": decisions_with_empty,
                    "decision_proportion": CanonicalRational.make(decisions_with_empty, len(records)).to_dict(),
                },
            },
        ),
        BOARD_CHARACTERISTICS_ARTIFACT_NAME: _report(
            "board_characteristics",
            {
                **common,
                "tables": _board_characteristic_tables(records),
            },
        ),
        THEORETICAL_BOUND_ARTIFACT_NAME: _report(
            "theoretical_bound",
            {
                **common,
                "decision_bounds": tuple(
                    {
                        "characterization_record_identity": record["characterization_record_identity"],
                        "round_id": record["round_id"],
                        "upper_bound": record["theoretical_mrr_improvement_upper_bound"],
                    }
                    for record in records
                ),
                "eligible_decisions": len(records),
                "population_upper_bound": population_upper_bound.to_dict(),
            },
        ),
        GOVERNANCE_DISPOSITION_ARTIFACT_NAME: _report(
            "governance_disposition",
            {
                **common,
                "continuation_disposition": "research_governance_decision_required",
                "delta_min": None,
                "delta_min_governance_identity": None,
                "experiment_2b_authorized": False,
            },
        ),
    }
    reports[FINDING_002_ARTIFACT_NAME] = _report(
        "finding_002",
        {
            **common,
            "characterization_validity": "valid",
            "class_counts": reports[ORDERING_DISTRIBUTIONS_ARTIFACT_NAME]["class_counts"],
            "continuation_disposition": "research_governance_decision_required",
            "delta_min_governance_status": "not_established",
            "empty_square_extension": reports[ORDERING_DISTRIBUTIONS_ARTIFACT_NAME]["empty_square_extension"],
            "pairwise_divergence_summaries": distributions["pairwise_sign_disagreements"],
            "rank_displacement_summaries": {
                "candidate": distributions["candidate_absolute_rank_displacement"],
                "maximum": distributions["maximum_absolute_rank_displacement"],
                "mean": distributions["mean_absolute_rank_displacement"],
                "total": distributions["total_rank_displacement"],
            },
            "theoretical_population_upper_bound": population_upper_bound.to_dict(),
            "tie_statistics": {
                "derived_group_count": distributions["derived_tie_group_count"],
                "derived_group_size": distributions["derived_tie_group_size"],
                "derived_largest_group_size": distributions["derived_largest_tie_group_size"],
                "raw_group_count": distributions["raw_tie_group_count"],
                "raw_group_size": distributions["raw_tie_group_size"],
                "raw_largest_group_size": distributions["raw_largest_tie_group_size"],
                "strict_to_tie": distributions["strict_to_tie_changes"],
                "tie_to_strict": distributions["tie_to_strict_changes"],
            },
            "top_k_membership_change_summaries": {
                k: distributions[f"top_{k}_membership_change"] for k in ("1", "3", "5")
            },
        },
    )
    reports[CONFORMANCE_ARTIFACT_NAME] = _report(
        "conformance",
        {
            **common,
            "artifact_profile": OUTCOME_BLIND_CHARACTERIZATION_PROFILE,
            "candidate_order": tuple(range(25)),
            "classification_accounting": sum(class_counts.values()),
            "decision_count": len(records),
            "deterministic_reconstruction": "validated",
            "outcome_access": "prohibited_and_not_performed",
            "population_accounting": len(dispositions),
            "status": "passed",
        },
    )
    return reports


def _artifact_declarations() -> dict[str, ArtifactDeclaration]:
    declarations = {
        CHARACTERIZATION_ARTIFACT_NAME: ArtifactDeclaration(
            "characterization", 1, "jsonl", "start_slot_then_round_id"
        ),
        CONFORMANCE_ARTIFACT_NAME: ArtifactDeclaration(
            "conformance", 1, "json", "single_canonical_record"
        ),
    }
    for name in (
        POPULATION_ARTIFACT_NAME,
        DERIVED_MEASUREMENT_ARTIFACT_NAME,
        ORDERING_DISTRIBUTIONS_ARTIFACT_NAME,
        BOARD_CHARACTERISTICS_ARTIFACT_NAME,
        THEORETICAL_BOUND_ARTIFACT_NAME,
        GOVERNANCE_DISPOSITION_ARTIFACT_NAME,
        FINDING_002_ARTIFACT_NAME,
    ):
        declarations[name] = ArtifactDeclaration(
            "descriptive_report", 1, "json", "single_canonical_record"
        )
    return declarations


def _experiment_binding(configuration: Experiment2AConfiguration) -> ExperimentProtocolV2Binding:
    return ExperimentProtocolV2Binding(
        experiment_identifier="rq003_experiment_002a",
        protocol_revision=EXPERIMENT2A_PROTOCOL_REVISION,
        protocol_document_sha256=EXPERIMENT2A_PROTOCOL_DOCUMENT_SHA256,
        specification=EXPERIMENT2A_SPECIFICATION_BINDING,
        profile=EXPERIMENT2A_PROFILE_BINDING,
        configuration=configuration.profiled_configuration,
    )


def _bind_execution_source(configuration: Experiment2AConfiguration) -> SourceCommitProvenance:
    commit = configuration.source_commit_sha
    if commit is None:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=configuration.repository_root,
            text=True,
        ).strip()
    return bind_source_commit(configuration.repository_root, commit, _SOURCE_SCOPES)


def _replay_round_identity(lifecycle: RoundLifecycleIndexRecord) -> str:
    return execution_identity(
        _REPLAY_ROUND_DOMAIN,
        {
            "end_slot": lifecycle.end_slot,
            "observation_count": lifecycle.observation_count,
            "observation_references": tuple(
                {
                    "observed_at_utc": reference.observed_at_utc.isoformat(),
                    "rpc_slot": reference.rpc_slot,
                    "source_file": reference.source_file,
                    "source_line_number": reference.source_line_number,
                }
                for reference in lifecycle.observation_references
            ),
            "round_id": lifecycle.round_id,
            "start_slot": lifecycle.start_slot,
        },
    )


def _population_dispositions(
    lifecycles: Sequence[RoundLifecycleIndexRecord],
    audit: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    round_identity_by_id: Mapping[int, str],
) -> tuple[PopulationDisposition, ...]:
    status_by_round = {int(item["round_id"]): str(item["status"]) for item in audit}
    record_by_round = {int(item["round_id"]): item for item in records}
    dispositions: list[PopulationDisposition] = []
    for lifecycle in lifecycles:
        status = status_by_round.get(lifecycle.round_id)
        if status is None:
            raise ValueError("selection audit does not cover Replay population")
        if status == "eligible":
            record = record_by_round.get(lifecycle.round_id)
            if record is None:
                raise ValueError("eligible round lacks characterization record")
            dispositions.append(
                PopulationDisposition(
                    round_identity_by_id[lifecycle.round_id],
                    str(lifecycle.round_id),
                    "eligible",
                    None,
                    str(record["decision_identity"]),
                )
            )
        else:
            dispositions.append(
                PopulationDisposition(
                    round_identity_by_id[lifecycle.round_id],
                    str(lifecycle.round_id),
                    "excluded",
                    status,
                    None,
                )
            )
    return tuple(dispositions)


def _component_identities() -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (
                ("deployment_per_miner_definition", DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY),
                ("deployed_lamports_definition", DEPLOYED_LAMPORTS_DEFINITION.definition_identity),
                ("deployed_lamports_binding", DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY),
                ("measurement_component_set", EXPERIMENT2A_MEASUREMENT_COMPONENT_SET_IDENTITY),
                ("measurement_pipeline", RQ003_PIPELINE_IMPLEMENTATION_IDENTITY),
                ("miner_count_definition", MINER_COUNT_DEFINITION.definition_identity),
                ("miner_count_binding", MINER_COUNT_EXECUTABLE_BINDING_IDENTITY),
                ("total_miners_definition", TOTAL_MINERS_DEFINITION.definition_identity),
                ("total_miners_binding", TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY),
            )
        )
    )


def _board_characteristics(
    deployed: Sequence[int], miners: Sequence[int], total_miners: int
) -> dict[str, Any]:
    positive_miners = tuple(value for value in miners if value > 0)
    raw_groups = _tie_groups(tuple(CanonicalRational.make(value) for value in deployed))
    return {
        "largest_raw_deployment_tie_group": max(raw_groups),
        "positive_deployment_square_count": sum(value > 0 for value in deployed),
        "positive_miner_count_range": (
            max(positive_miners) - min(positive_miners) if positive_miners else None
        ),
        "positive_miner_square_count": len(positive_miners),
        "raw_deployment_tie_group_count": len(raw_groups),
        "round_total_miners": total_miners,
        "sum_miner_memberships": sum(miners),
        "total_deployed_lamports": sum(deployed),
    }


def _board_characteristic_tables(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    names = tuple(sorted(records[0]["board_characteristics"]))
    result: dict[str, Any] = {}
    for name in names:
        counts: Counter[tuple[object, str]] = Counter(
            (record["board_characteristics"][name], record["classification"])
            for record in records
        )
        entries = sorted(
            counts,
            key=lambda item: (_optional_numeric_sort_key(item[0]), ORDERING_CLASSES.index(item[1])),
        )
        result[name] = tuple(
            {
                "classification": classification,
                "count": counts[(value, classification)],
                "proportion": CanonicalRational.make(counts[(value, classification)], len(records)).to_dict(),
                "value": value,
            }
            for value, classification in entries
        )
    return result


def _tie_groups(values: tuple[CanonicalRational, ...]) -> tuple[int, ...]:
    ordered = sorted(values, reverse=True)
    groups: list[int] = []
    first = 0
    while first < len(ordered):
        last = first + 1
        while last < len(ordered) and ordered[last] == ordered[first]:
            last += 1
        groups.append(last - first)
        first = last
    return tuple(groups)


def _sum_rationals(values: Iterable[CanonicalRational]) -> CanonicalRational:
    total = CanonicalRational.make(0)
    for value in values:
        total = total.add(value)
    return total


def _distribution_value(value: object) -> CanonicalRational:
    if isinstance(value, bool):
        return CanonicalRational.make(int(value))
    if isinstance(value, int):
        return CanonicalRational.make(value)
    if isinstance(value, Mapping):
        return CanonicalRational.from_dict(value)
    raise TypeError("distribution values must be exact numeric values")


def _exact_distribution(values: tuple[CanonicalRational, ...]) -> tuple[dict[str, Any], ...]:
    counts = Counter(values)
    return tuple(
        {
            "count": counts[value],
            "proportion": CanonicalRational.make(counts[value], len(values)).to_dict(),
            "value": value.to_dict(),
        }
        for value in sorted(counts)
    )


def _report(kind: str, material: Mapping[str, Any]) -> dict[str, Any]:
    report = {"kind": kind, **material}
    report["artifact_identity"] = execution_identity(_REPORT_DOMAIN, report)
    return report


def _load_characterization_artifact(path: Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    previous: tuple[int, int] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise ValueError(f"characterization line {line_number} lacks newline")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"characterization line {line_number} is malformed") from error
            if not isinstance(record, dict) or _canonical_json(record) + "\n" != line:
                raise ValueError(f"characterization line {line_number} is not canonical")
            stored = record.pop("characterization_record_identity", None)
            _require_sha256("characterization_record_identity", stored)
            if execution_identity(_CHARACTERIZATION_RECORD_DOMAIN, record) != stored:
                raise ValueError("characterization record identity does not reconstruct")
            record["characterization_record_identity"] = stored
            _validate_characterization_record(record)
            order = (record["start_slot"], record["round_id"])
            if previous is not None and order <= previous:
                raise ValueError("characterization artifact is not in Replay order")
            previous = order
            records.append(record)
    if not records:
        raise ValueError("characterization artifact contains no decisions")
    return tuple(records)


def _validate_characterization_record(record: Mapping[str, Any]) -> None:
    if record.get("schema_version") != EXPERIMENT2A_SCHEMA_VERSION:
        raise ValueError("characterization schema is unsupported")
    if record.get("classification") not in ORDERING_CLASSES:
        raise ValueError("ordering classification is unsupported")
    if tuple(record.get("candidate_order", ())) != tuple(range(25)):
        raise ValueError("candidate order is invalid")
    for name in (
        "absolute_rank_displacements",
        "deployment_per_miner",
        "derived_average_ranks",
        "raw_average_ranks",
    ):
        values = record.get(name)
        if not isinstance(values, list) or len(values) != 25:
            raise ValueError(f"{name} must contain 25 exact values")
        tuple(CanonicalRational.from_dict(value) for value in values)
    if len(record.get("deployed_lamports", ())) != 25 or len(record.get("miner_counts", ())) != 25:
        raise ValueError("fundamental measurement vector length is invalid")
    vector_identities = record.get("measurement_vector_identities")
    if not isinstance(vector_identities, list) or len(vector_identities) != 25:
        raise ValueError("measurement vector identity count is invalid")
    for vector_identity in vector_identities:
        _require_sha256("measurement_vector_identity", vector_identity)
    total_miners = record.get("board_characteristics", {}).get("round_total_miners")
    _require_u64("round_total_miners", total_miners)
    if record.get("board_characteristics") != json.loads(
        _canonical_json(
            _board_characteristics(
                record["deployed_lamports"], record["miner_counts"], total_miners
            )
        )
    ):
        raise ValueError("board characteristics do not reconstruct")
    reconstructed = characterize_orderings(record["deployed_lamports"], record["miner_counts"])
    for key, value in reconstructed.items():
        if record.get(key) != json.loads(_canonical_json(value)):
            raise ValueError(f"characterization field {key} does not reconstruct")


def _load_report(path: Path, kind: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) != 1 or not lines[0].endswith("\n"):
        raise ValueError(f"{path.name} must contain one canonical record")
    try:
        report = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise ValueError(f"{path.name} is malformed") from error
    if not isinstance(report, dict) or _canonical_json(report) + "\n" != lines[0]:
        raise ValueError(f"{path.name} is not canonical")
    stored = report.pop("artifact_identity", None)
    _require_sha256("artifact_identity", stored)
    if execution_identity(_REPORT_DOMAIN, report) != stored:
        raise ValueError(f"{path.name} identity does not reconstruct")
    report["artifact_identity"] = stored
    if report.get("kind") != kind:
        raise ValueError(f"{path.name} kind is invalid")
    return report


def _validate_report_consistency(
    records: Sequence[Mapping[str, Any]], reports: Mapping[str, Mapping[str, Any]]
) -> None:
    distribution = reports[ORDERING_DISTRIBUTIONS_ARTIFACT_NAME]
    if sum(entry["count"] for entry in distribution["class_counts"]) != len(records):
        raise ValueError("classification counts do not reconcile")
    bound = reports[THEORETICAL_BOUND_ARTIFACT_NAME]
    expected = _sum_rationals(
        CanonicalRational.from_dict(record["theoretical_mrr_improvement_upper_bound"])
        for record in records
    ).divide_by_integer(len(records))
    if bound["population_upper_bound"] != expected.to_dict():
        raise ValueError("population upper bound does not reconstruct")
    conformance = reports[CONFORMANCE_ARTIFACT_NAME]
    if conformance["status"] != "passed" or conformance["outcome_access"] != "prohibited_and_not_performed":
        raise ValueError("outcome-blind conformance report is invalid")


def _reject_prohibited_fields(path: Path, prohibited: set[str]) -> None:
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            material = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path.name} line {line_number} is malformed") from error

        def inspect(value: object) -> None:
            if isinstance(value, list):
                for item in value:
                    inspect(item)
            elif isinstance(value, dict):
                if intersection := prohibited.intersection(value):
                    raise ValueError(
                        f"{path.name} contains prohibited outcome or evaluation fields: "
                        + ", ".join(sorted(intersection))
                    )
                for item in value.values():
                    inspect(item)

        inspect(material)


def _optional_numeric_sort_key(value: object) -> tuple[int, int]:
    if value is None:
        return (0, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("board characteristic must be integer or null")
    return (1, value)


def _canonical_json(material: object) -> str:
    return json.dumps(material, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _require_nonnegative_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _require_positive_integer(name: str, value: object) -> int:
    value = _require_nonnegative_integer(name, value)
    if value == 0:
        raise ValueError(f"{name} must be positive")
    return value


def _require_u64(name: str, value: object) -> int:
    value = _require_nonnegative_integer(name, value)
    if value > (1 << 64) - 1:
        raise ValueError(f"{name} must be an unsigned 64-bit integer")
    return value


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


__all__ = (
    "BOARD_CHARACTERISTICS_ARTIFACT_NAME",
    "CHARACTERIZATION_ARTIFACT_NAME",
    "CONFORMANCE_ARTIFACT_NAME",
    "DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY",
    "DERIVED_MEASUREMENT_ARTIFACT_NAME",
    "EXPERIMENT2A_ARTIFACT_NAMES",
    "EXPERIMENT2A_PROTOCOL_DOCUMENT_SHA256",
    "EXPERIMENT2A_PROTOCOL_REVISION",
    "EXPERIMENT2A_SCHEMA_VERSION",
    "Experiment2AConfiguration",
    "Experiment2AResult",
    "FINDING_002_ARTIFACT_NAME",
    "GOVERNANCE_DISPOSITION_ARTIFACT_NAME",
    "IDENTICAL_RANK_VECTORS",
    "ORDERING_DISTRIBUTIONS_ARTIFACT_NAME",
    "OutcomeBlindReplayPopulation",
    "POPULATION_ARTIFACT_NAME",
    "STRICT_ORDERING_CHANGE",
    "THEORETICAL_BOUND_ARTIFACT_NAME",
    "TIE_ONLY_CHANGE",
    "CanonicalRational",
    "characterize_orderings",
    "deployment_per_miner",
    "exact_average_ranks",
    "execute_experiment2a",
    "validate_experiment2a_artifacts",
)
