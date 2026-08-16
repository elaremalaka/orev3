"""RQ-003 Experiment 2C: outcome-blind Miner Count characterization.

The module compares direct Miner Count ordering with the governed raw
Deployment and Deployment-per-Miner reference orderings.  It has no outcome,
baseline, evaluation, Strategy, or economic capability.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from orev3.datasets.rq003_experiment0 import (
    RQ003_EXPERIMENT0_OUTPUT_NAMES,
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
from orev3.experiments.rq003_experiment2a import (
    DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
    IDENTICAL_RANK_VECTORS,
    ORDERING_CLASSES,
    STRICT_ORDERING_CHANGE,
    TIE_ONLY_CHANGE,
    CanonicalRational,
    OutcomeBlindReplayPopulation,
    deployment_per_miner,
    exact_average_ranks,
)
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


EXPERIMENT2C_SCHEMA_VERSION = 1
EXPERIMENT2C_PROTOCOL_REVISION = "1"
EXPERIMENT2C_PROTOCOL_DOCUMENT_SHA256 = (
    "d18d2eb8603f079f56a0aadcbde17d87855ddbb1c06f21b94d4f3d0772384d23"
)
EXPERIMENT2C_PROTOCOL_SOURCE_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)
EXPERIMENT2C_REQUESTED_SLOTS_REMAINING = 5

CHARACTERIZATION_ARTIFACT_NAME = "characterization_artifact.jsonl"
POPULATION_ARTIFACT_NAME = "population.json"
MEASUREMENT_BINDING_ARTIFACT_NAME = "measurement_binding.json"
ORDERING_DISTRIBUTIONS_ARTIFACT_NAME = "ordering_distributions.json"
BOARD_CHARACTERISTICS_ARTIFACT_NAME = "board_characteristics.json"
CONFORMANCE_ARTIFACT_NAME = "conformance.json"

EXPERIMENT2C_ARTIFACT_NAMES = (
    PROFILED_PROVENANCE_NAME,
    CHARACTERIZATION_ARTIFACT_NAME,
    POPULATION_ARTIFACT_NAME,
    MEASUREMENT_BINDING_ARTIFACT_NAME,
    ORDERING_DISTRIBUTIONS_ARTIFACT_NAME,
    BOARD_CHARACTERISTICS_ARTIFACT_NAME,
    CONFORMANCE_ARTIFACT_NAME,
    PROFILED_AUDIT_MANIFEST_NAME,
)

MINER_VS_DEPLOYMENT = "miner_count_vs_raw_deployment"
MINER_VS_DEPLOYMENT_PER_MINER = "miner_count_vs_deployment_per_miner"
COMPARISON_NAMES = (MINER_VS_DEPLOYMENT, MINER_VS_DEPLOYMENT_PER_MINER)

_MINER_ORDERING_DOMAIN = "rq003-experiment-002c-miner-ordering-v1"
_DEPLOYMENT_ORDERING_DOMAIN = "rq003-experiment-002c-deployment-reference-ordering-v1"
_DPM_ORDERING_DOMAIN = "rq003-experiment-002c-dpm-reference-ordering-v1"
_CHARACTERIZATION_RECORD_DOMAIN = "rq003-experiment-002c-characterization-record-v1"
_REPORT_DOMAIN = "rq003-experiment-002c-report-v1"
_EXPERIMENT_CONFIGURATION_DOMAIN = "rq003-experiment-002c-configuration-v1"
_DECISION_CONFIGURATION_DOMAIN = "rq003-experiment-002c-decision-selection-v1"
_REPLAY_DATASET_SCHEMA_DOMAIN = "rq003-experiment-002c-replay-dataset-schema-v1"
_REPLAY_ROUND_DOMAIN = "rq003-experiment-002c-replay-round-v1"
_PROTOCOL_REVISION_POPULATION_DOMAIN = "rq003-experiment-002c-protocol-revision-population-v1"
_MEASUREMENT_COMPONENT_SET_DOMAIN = "rq003-experiment-002c-measurement-component-set-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_SOURCE_SCOPES = (
    "docs/research/experiments/rq003-experiment-002c-miner-count-characterization.md",
    "docs/research/specifications/rq003-research-execution-specification-v2.md",
    "src/orev3",
)

EXPERIMENT2C_SPECIFICATION_BINDING = ExecutionSpecificationV2Binding(
    EXECUTION_SPECIFICATION_V2_REVISION,
    EXECUTION_SPECIFICATION_V2_SHA256,
)
EXPERIMENT2C_PROFILE_BINDING = ExecutionProfileBinding(
    OUTCOME_BLIND_CHARACTERIZATION_PROFILE
)
EXPERIMENT2C_DATASET_SCHEMA_IDENTITY = execution_identity(
    _REPLAY_DATASET_SCHEMA_DOMAIN,
    {"lifecycle_schema_version": 1, "record_kind": "RoundLifecycleIndexRecord"},
)
EXPERIMENT2C_PROTOCOL_REVISION_POPULATION_IDENTITY = execution_identity(
    _PROTOCOL_REVISION_POPULATION_DOMAIN,
    {
        "official_source_revision": EXPERIMENT2C_PROTOCOL_SOURCE_REVISION,
        "scope": "homogeneous_legacy_replay_population",
    },
)
EXPERIMENT2C_MEASUREMENT_COMPONENT_SET_IDENTITY = execution_identity(
    _MEASUREMENT_COMPONENT_SET_DOMAIN,
    {
        "ordered_definition_identities": (
            MINER_COUNT_DEFINITION.definition_identity,
            DEPLOYED_LAMPORTS_DEFINITION.definition_identity,
            TOTAL_MINERS_DEFINITION.definition_identity,
            DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
        ),
        "ordered_executable_binding_identities": (
            MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
            DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
            TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY,
        ),
        "pipeline_implementation_identity": RQ003_PIPELINE_IMPLEMENTATION_IDENTITY,
    },
)


@dataclass(frozen=True, slots=True)
class Experiment2CConfiguration:
    replay_dataset_path: Path
    replay_population: OutcomeBlindReplayPopulation
    output_directory: Path
    expected_dataset_sha256: str
    requested_slots_remaining: int = EXPERIMENT2C_REQUESTED_SLOTS_REMAINING
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
        if self.requested_slots_remaining != EXPERIMENT2C_REQUESTED_SLOTS_REMAINING:
            raise ValueError("Experiment 2C requires requested_slots_remaining=5")
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
                "artifact_names": EXPERIMENT2C_ARTIFACT_NAMES,
                "candidate_order": tuple(range(25)),
                "comparison_names": COMPARISON_NAMES,
                "dataset_sha256": self.expected_dataset_sha256,
                "decision_configuration_identity": decision_identity,
                "miner_count_definition_identity": MINER_COUNT_DEFINITION.definition_identity,
                "protocol_document_sha256": EXPERIMENT2C_PROTOCOL_DOCUMENT_SHA256,
                "protocol_revision": EXPERIMENT2C_PROTOCOL_REVISION,
                "reference_definition_identity": DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
                "requested_slots_remaining": self.requested_slots_remaining,
            },
        )
        object.__setattr__(self, "experiment_specific_configuration_identity", specific_identity)
        object.__setattr__(
            self,
            "profiled_configuration",
            ProfiledExperimentConfiguration(EXPERIMENT2C_PROFILE_BINDING, specific_identity),
        )


@dataclass(frozen=True, slots=True)
class Experiment2CResult:
    dataset_sha256: str
    replay_identity: str
    audit_manifest_identity: str
    source_commit_sha: str
    replay_rounds: int
    eligible_decisions: int
    excluded_decisions: int
    artifacts: tuple[tuple[str, Path, str], ...]

    def __post_init__(self) -> None:
        for name in ("dataset_sha256", "replay_identity", "audit_manifest_identity"):
            _require_sha256(name, getattr(self, name))
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.source_commit_sha):
            raise ValueError("source_commit_sha is invalid")
        for name in ("replay_rounds", "eligible_decisions", "excluded_decisions"):
            _require_nonnegative_integer(name, getattr(self, name))
        if self.eligible_decisions + self.excluded_decisions != self.replay_rounds:
            raise ValueError("Experiment 2C population accounting is incomplete")


def characterize_miner_count_ordering(
    deployed_lamports: Sequence[int],
    miner_counts: Sequence[int],
) -> dict[str, Any]:
    """Characterize Miner Count against both governed reference orderings."""

    if len(deployed_lamports) != 25 or len(miner_counts) != 25:
        raise ValueError("characterization requires exactly 25 candidates")
    deployed = tuple(_require_u64("deployed_lamports", value) for value in deployed_lamports)
    miners = tuple(_require_u64("miner_count", value) for value in miner_counts)
    dpm = tuple(
        deployment_per_miner(deployed[square], miners[square])[0]
        for square in range(25)
    )
    miner_ranks = exact_average_ranks(miners)
    deployment_ranks = exact_average_ranks(deployed)
    dpm_ranks = exact_average_ranks(dpm)
    comparisons = {
        MINER_VS_DEPLOYMENT: _compare_orderings(
            miners, miner_ranks, deployed, deployment_ranks
        ),
        MINER_VS_DEPLOYMENT_PER_MINER: _compare_orderings(
            miners, miner_ranks, dpm, dpm_ranks
        ),
    }
    return {
        "comparisons": comparisons,
        "deployment_average_ranks": tuple(value.to_dict() for value in deployment_ranks),
        "deployment_ordering_identity": _ordering_identity(
            _DEPLOYMENT_ORDERING_DOMAIN,
            deployed,
            deployment_ranks,
            DEPLOYED_LAMPORTS_DEFINITION.definition_identity,
        ),
        "deployment_per_miner": tuple(value.to_dict() for value in dpm),
        "deployment_per_miner_average_ranks": tuple(value.to_dict() for value in dpm_ranks),
        "deployment_per_miner_ordering_identity": _ordering_identity(
            _DPM_ORDERING_DOMAIN,
            dpm,
            dpm_ranks,
            DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
        ),
        "miner_count_average_ranks": tuple(value.to_dict() for value in miner_ranks),
        "miner_count_ordering_identity": _ordering_identity(
            _MINER_ORDERING_DOMAIN,
            miners,
            miner_ranks,
            MINER_COUNT_DEFINITION.definition_identity,
        ),
        "tie_statistics": {
            "deployment": _tie_statistics(deployed),
            "deployment_per_miner": _tie_statistics(dpm),
            "miner_count": _tie_statistics(miners),
        },
    }


def execute_experiment2c(configuration: Experiment2CConfiguration) -> Experiment2CResult:
    """Execute the complete v2 outcome-blind Experiment 2C lifecycle."""

    if not isinstance(configuration, Experiment2CConfiguration):
        raise TypeError("configuration must be Experiment2CConfiguration")
    source_commit = _bind_execution_source(configuration)
    dataset_sha256 = file_sha256(configuration.replay_dataset_path)
    if dataset_sha256 != configuration.expected_dataset_sha256:
        raise ValueError("replay dataset SHA-256 does not match configuration")
    lifecycles = configuration.replay_population.lifecycles
    dataset = ReplayDatasetBinding(
        "replay-dataset-v1",
        EXPERIMENT2C_DATASET_SCHEMA_IDENTITY,
        configuration.replay_dataset_path.stat().st_size,
        dataset_sha256,
    )
    experiment = _experiment_binding(configuration)
    round_identity_by_id = {
        lifecycle.round_id: _replay_round_identity(lifecycle)
        for lifecycle in lifecycles
    }
    replay = ProfiledReplayIdentity(
        specification_identity=EXPERIMENT2C_SPECIFICATION_BINDING.specification_identity,
        profile_identity=EXPERIMENT2C_PROFILE_BINDING.profile_identity,
        experiment_binding_identity=experiment.experiment_binding_identity,
        experiment_configuration_identity=configuration.profiled_configuration.experiment_configuration_identity,
        source_commit_provenance_identity=source_commit.source_commit_provenance_identity,
        dataset=dataset,
        protocol_revision_identity=EXPERIMENT2C_PROTOCOL_REVISION_POPULATION_IDENTITY,
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
        specification=EXPERIMENT2C_SPECIFICATION_BINDING,
        profile=EXPERIMENT2C_PROFILE_BINDING,
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
                        EXPERIMENT2C_PROFILE_BINDING.profile_identity, declaration
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
            EXPERIMENT2C_PROFILE_BINDING,
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
                EXPERIMENT2C_PROFILE_BINDING,
            )
        artifact_contracts = {
            PROFILED_PROVENANCE_NAME: provenance_contract,
            CHARACTERIZATION_ARTIFACT_NAME: characterization_contract,
            **report_contracts,
        }
        manifest = ProfiledExperimentAuditManifest(
            outcome_blind_provenance=block,
            artifact_contracts=tuple(sorted(artifact_contracts.items())),
            terminal=OutcomeBlindCharacterizationTerminal(dispositions),
            execution_conformance_result="passed",
        )
        seal_profiled_audit_manifest(temporary / PROFILED_AUDIT_MANIFEST_NAME, manifest)
        artifacts = validate_experiment2c_artifacts(
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

    return Experiment2CResult(
        dataset_sha256=dataset_sha256,
        replay_identity=replay.replay_identity,
        audit_manifest_identity=manifest.audit_manifest_identity,
        source_commit_sha=source_commit.commit_sha,
        replay_rounds=len(lifecycles),
        eligible_decisions=len(records),
        excluded_decisions=len(lifecycles) - len(records),
        artifacts=tuple((name, destination / name, digest) for name, _, digest in artifacts),
    )


def validate_experiment2c_artifacts(
    output_directory: str | Path,
    *,
    replay_dataset_path: str | Path,
    expected_manifest: ProfiledExperimentAuditManifest | None = None,
) -> tuple[tuple[str, Path, str], ...]:
    """Reconstruct the complete outcome-blind Experiment 2C artifact graph."""

    output = Path(output_directory)
    actual_names = tuple(sorted(path.name for path in output.iterdir() if path.is_file()))
    if actual_names != tuple(sorted(EXPERIMENT2C_ARTIFACT_NAMES)):
        raise ValueError("output directory contains artifacts outside the protocol")
    records = _load_characterization_artifact(output / CHARACTERIZATION_ARTIFACT_NAME)
    reports = {
        name: _load_report(output / name, name.removesuffix(".json"))
        for name in EXPERIMENT2C_ARTIFACT_NAMES
        if name.endswith(".json")
        and name not in {PROFILED_PROVENANCE_NAME, PROFILED_AUDIT_MANIFEST_NAME}
    }
    _validate_report_consistency(records, reports)
    manifest = validate_profiled_audit_manifest(
        output / PROFILED_AUDIT_MANIFEST_NAME, expected=expected_manifest
    )
    if manifest["execution_profile"]["execution_profile"] != OUTCOME_BLIND_CHARACTERIZATION_PROFILE:
        raise ValueError("Experiment 2C manifest has the wrong execution profile")
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
        for name in sorted(EXPERIMENT2C_ARTIFACT_NAMES)
    )


def _compare_orderings(
    primary_values: Sequence[int] | Sequence[CanonicalRational],
    primary_ranks: Sequence[CanonicalRational],
    reference_values: Sequence[int] | Sequence[CanonicalRational],
    reference_ranks: Sequence[CanonicalRational],
) -> dict[str, Any]:
    primary = _as_rationals(primary_values)
    reference = _as_rationals(reference_values)
    disagreements = 0
    reversals = 0
    tie_to_strict = 0
    strict_to_tie = 0
    for left in range(25):
        for right in range(left + 1, 25):
            primary_sign = primary[left].compare(primary[right])
            reference_sign = reference[left].compare(reference[right])
            if primary_sign != reference_sign:
                disagreements += 1
            if primary_sign and reference_sign and primary_sign == -reference_sign:
                reversals += 1
            elif primary_sign == 0 and reference_sign != 0:
                tie_to_strict += 1
            elif primary_sign != 0 and reference_sign == 0:
                strict_to_tie += 1
    primary_rank_tuple = tuple(primary_ranks)
    reference_rank_tuple = tuple(reference_ranks)
    if primary_rank_tuple == reference_rank_tuple:
        classification = IDENTICAL_RANK_VECTORS
    elif reversals:
        classification = STRICT_ORDERING_CHANGE
    else:
        if tie_to_strict + strict_to_tie == 0:
            raise ValueError("different rank vectors lack a protocol classification")
        classification = TIE_ONLY_CHANGE
    displacements = tuple(
        primary_rank_tuple[square].absolute_difference(reference_rank_tuple[square])
        for square in range(25)
    )
    total = _sum_rationals(displacements)
    top_k: dict[str, Any] = {}
    for k in (1, 3, 5):
        boundary = CanonicalRational.make(k)
        primary_members = {
            square for square, rank in enumerate(primary_rank_tuple) if rank <= boundary
        }
        reference_members = {
            square for square, rank in enumerate(reference_rank_tuple) if rank <= boundary
        }
        top_k[str(k)] = {
            "changed": primary_members != reference_members,
            "primary_only_count": len(primary_members - reference_members),
            "reference_only_count": len(reference_members - primary_members),
        }
    return {
        "absolute_rank_displacements": tuple(value.to_dict() for value in displacements),
        "classification": classification,
        "maximum_absolute_rank_displacement": max(displacements).to_dict(),
        "mean_absolute_rank_displacement": total.divide_by_integer(25).to_dict(),
        "pairwise_sign_disagreements": disagreements,
        "strict_reversals": reversals,
        "strict_to_tie_changes": strict_to_tie,
        "tie_to_strict_changes": tie_to_strict,
        "top_k_membership_changes": top_k,
        "total_rank_displacement": total.to_dict(),
        "unordered_candidate_pair_count": 300,
    }


def _build_characterizations(
    configuration: Experiment2CConfiguration,
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
            audit.append({"round_id": lifecycle.round_id, "status": "incomplete_lifecycle"})
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
        if decision_identity is None or total_miners is None:
            raise ValueError("decision state was not constructed")
        material: dict[str, Any] = {
            **characterize_miner_count_ordering(deployed, miners),
            "board_characteristics": _board_characteristics(deployed, miners, total_miners),
            "candidate_order": tuple(range(25)),
            "decision_configuration_identity": configuration.decision_configuration_identity,
            "decision_identity": decision_identity,
            "deployed_lamports": tuple(deployed),
            "measurement_vector_identities": tuple(vector.vector_identity for vector in vectors),
            "miner_counts": tuple(miners),
            "observation_index": observation_index,
            "round_id": lifecycle.round_id,
            "schema_version": EXPERIMENT2C_SCHEMA_VERSION,
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
    common = {
        "experiment_protocol_revision": EXPERIMENT2C_PROTOCOL_REVISION,
        "protocol_source_revision": EXPERIMENT2C_PROTOCOL_SOURCE_REVISION,
        "schema_version": EXPERIMENT2C_SCHEMA_VERSION,
    }
    comparison_reports = {
        comparison_name: _comparison_distribution_report(records, comparison_name)
        for comparison_name in COMPARISON_NAMES
    }
    tie_distributions = _tie_distribution_report(records)
    reports = {
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
        MEASUREMENT_BINDING_ARTIFACT_NAME: _report(
            "measurement_binding",
            {
                **common,
                "governed_measurement": "miner_count",
                "miner_count_definition_identity": MINER_COUNT_DEFINITION.definition_identity,
                "miner_count_executable_binding_identity": MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
                "reference_orderings": {
                    "deployment": DEPLOYED_LAMPORTS_DEFINITION.definition_identity,
                    "deployment_per_miner": DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY,
                },
            },
        ),
        ORDERING_DISTRIBUTIONS_ARTIFACT_NAME: _report(
            "ordering_distributions",
            {
                **common,
                "comparisons": comparison_reports,
                "decision_count": len(records),
                "tie_distributions": tie_distributions,
            },
        ),
        BOARD_CHARACTERISTICS_ARTIFACT_NAME: _report(
            "board_characteristics",
            {**common, "tables": _board_characteristic_tables(records)},
        ),
        CONFORMANCE_ARTIFACT_NAME: _report(
            "conformance",
            {
                **common,
                "artifact_profile": OUTCOME_BLIND_CHARACTERIZATION_PROFILE,
                "candidate_order": tuple(range(25)),
                "comparison_names": COMPARISON_NAMES,
                "decision_count": len(records),
                "deterministic_reconstruction": "validated",
                "outcome_access": "prohibited_and_not_performed",
                "population_accounting": len(dispositions),
                "status": "passed",
            },
        ),
    }
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
        MEASUREMENT_BINDING_ARTIFACT_NAME,
        ORDERING_DISTRIBUTIONS_ARTIFACT_NAME,
        BOARD_CHARACTERISTICS_ARTIFACT_NAME,
    ):
        declarations[name] = ArtifactDeclaration(
            "descriptive_report", 1, "json", "single_canonical_record"
        )
    return declarations


def _experiment_binding(configuration: Experiment2CConfiguration) -> ExperimentProtocolV2Binding:
    return ExperimentProtocolV2Binding(
        experiment_identifier="rq003_experiment_002c",
        protocol_revision=EXPERIMENT2C_PROTOCOL_REVISION,
        protocol_document_sha256=EXPERIMENT2C_PROTOCOL_DOCUMENT_SHA256,
        specification=EXPERIMENT2C_SPECIFICATION_BINDING,
        profile=EXPERIMENT2C_PROFILE_BINDING,
        configuration=configuration.profiled_configuration,
    )


def _bind_execution_source(configuration: Experiment2CConfiguration) -> SourceCommitProvenance:
    commit = configuration.source_commit_sha
    if commit is None:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=configuration.repository_root, text=True
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
                ("deployment_per_miner_reference", DEPLOYMENT_PER_MINER_DEFINITION_IDENTITY),
                ("deployment_reference", DEPLOYED_LAMPORTS_DEFINITION.definition_identity),
                ("deployed_lamports_binding", DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY),
                ("measurement_component_set", EXPERIMENT2C_MEASUREMENT_COMPONENT_SET_IDENTITY),
                ("measurement_pipeline", RQ003_PIPELINE_IMPLEMENTATION_IDENTITY),
                ("miner_count_binding", MINER_COUNT_EXECUTABLE_BINDING_IDENTITY),
                ("miner_count_definition", MINER_COUNT_DEFINITION.definition_identity),
                ("total_miners_binding", TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY),
                ("total_miners_definition", TOTAL_MINERS_DEFINITION.definition_identity),
            )
        )
    )


def _ordering_identity(
    domain: str,
    values: Sequence[int] | Sequence[CanonicalRational],
    ranks: Sequence[CanonicalRational],
    definition_identity: str,
) -> str:
    return execution_identity(
        domain,
        {
            "definition_identity": definition_identity,
            "ranks": tuple(rank.to_dict() for rank in ranks),
            "values": tuple(
                value.to_dict() if isinstance(value, CanonicalRational) else value
                for value in values
            ),
        },
    )


def _tie_statistics(values: Sequence[int] | Sequence[CanonicalRational]) -> dict[str, Any]:
    groups = _tie_groups(_as_rationals(values))
    non_singleton = tuple(size for size in groups if size > 1)
    return {
        "candidate_tie_count": sum(non_singleton),
        "group_count": len(groups),
        "largest_group_size": max(groups),
        "non_singleton_group_count": len(non_singleton),
        "non_singleton_group_sizes": non_singleton,
    }


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


def _as_rationals(
    values: Sequence[int] | Sequence[CanonicalRational],
) -> tuple[CanonicalRational, ...]:
    normalized = tuple(
        CanonicalRational.make(value)
        if isinstance(value, int) and not isinstance(value, bool)
        else value
        for value in values
    )
    if len(normalized) != 25 or not all(
        isinstance(value, CanonicalRational) for value in normalized
    ):
        raise TypeError("ordering requires 25 integers or canonical rationals")
    return normalized  # type: ignore[return-value]


def _board_characteristics(
    deployed: Sequence[int], miners: Sequence[int], total_miners: int
) -> dict[str, Any]:
    positive_miners = tuple(value for value in miners if value > 0)
    miner_ties = _tie_statistics(miners)
    deployment_ties = _tie_statistics(deployed)
    dpm = tuple(
        deployment_per_miner(deployed[square], miners[square])[0]
        for square in range(25)
    )
    dpm_ties = _tie_statistics(dpm)
    return {
        "deployment_per_miner_tie_group_count": dpm_ties["group_count"],
        "miner_count_largest_tie_group_size": miner_ties["largest_group_size"],
        "miner_count_tie_group_count": miner_ties["group_count"],
        "positive_deployment_square_count": sum(value > 0 for value in deployed),
        "positive_miner_count_range": (
            max(positive_miners) - min(positive_miners) if positive_miners else None
        ),
        "positive_miner_square_count": len(positive_miners),
        "raw_deployment_tie_group_count": deployment_ties["group_count"],
        "round_total_miners": total_miners,
        "sum_miner_memberships": sum(miners),
        "total_deployed_lamports": sum(deployed),
    }


def _board_characteristic_tables(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    names = tuple(sorted(records[0]["board_characteristics"]))
    result: dict[str, Any] = {}
    for name in names:
        counts: Counter[tuple[object, str, str]] = Counter(
            (
                record["board_characteristics"][name],
                comparison_name,
                record["comparisons"][comparison_name]["classification"],
            )
            for record in records
            for comparison_name in COMPARISON_NAMES
        )
        entries = sorted(
            counts,
            key=lambda item: (
                _optional_numeric_sort_key(item[0]),
                COMPARISON_NAMES.index(item[1]),
                ORDERING_CLASSES.index(item[2]),
            ),
        )
        result[name] = tuple(
            {
                "classification": classification,
                "comparison": comparison_name,
                "count": counts[(value, comparison_name, classification)],
                "proportion": CanonicalRational.make(
                    counts[(value, comparison_name, classification)], len(records)
                ).to_dict(),
                "value": value,
            }
            for value, comparison_name, classification in entries
        )
    return result


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


def _exact_distribution(
    values: tuple[CanonicalRational, ...], *, allow_empty: bool = False
) -> tuple[dict[str, Any], ...]:
    if not values:
        if allow_empty:
            return ()
        raise ValueError("exact distribution cannot be empty")
    counts = Counter(values)
    return tuple(
        {
            "count": counts[value],
            "proportion": CanonicalRational.make(counts[value], len(values)).to_dict(),
            "value": value.to_dict(),
        }
        for value in sorted(counts)
    )


def _comparison_distribution_report(
    records: Sequence[Mapping[str, Any]], comparison_name: str
) -> dict[str, Any]:
    if comparison_name not in COMPARISON_NAMES:
        raise ValueError("comparison name is unsupported")
    comparisons = tuple(record["comparisons"][comparison_name] for record in records)
    if not comparisons:
        raise ValueError("comparison distribution requires decisions")
    class_counts = Counter(value["classification"] for value in comparisons)
    scalar_fields = (
        "unordered_candidate_pair_count",
        "pairwise_sign_disagreements",
        "strict_reversals",
        "tie_to_strict_changes",
        "strict_to_tie_changes",
        "total_rank_displacement",
        "mean_absolute_rank_displacement",
        "maximum_absolute_rank_displacement",
    )
    distributions = {
        field_name: _exact_distribution(
            tuple(_distribution_value(value[field_name]) for value in comparisons)
        )
        for field_name in scalar_fields
    }
    distributions["candidate_absolute_rank_displacement"] = _exact_distribution(
        tuple(
            _distribution_value(item)
            for comparison in comparisons
            for item in comparison["absolute_rank_displacements"]
        )
    )
    for k in ("1", "3", "5"):
        for field_name in ("changed", "primary_only_count", "reference_only_count"):
            distributions[f"top_{k}_{field_name}"] = _exact_distribution(
                tuple(
                    _distribution_value(
                        comparison["top_k_membership_changes"][k][field_name]
                    )
                    for comparison in comparisons
                )
            )
    return {
        "class_counts": tuple(
            {
                "classification": classification,
                "count": class_counts[classification],
                "proportion": CanonicalRational.make(
                    class_counts[classification], len(records)
                ).to_dict(),
            }
            for classification in ORDERING_CLASSES
        ),
        "distributions": distributions,
    }


def _tie_distribution_report(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for ordering_name in ("deployment", "deployment_per_miner", "miner_count"):
        for field_name in (
            "candidate_tie_count",
            "group_count",
            "largest_group_size",
            "non_singleton_group_count",
        ):
            result[f"{ordering_name}_{field_name}"] = _exact_distribution(
                tuple(
                    _distribution_value(
                        record["tie_statistics"][ordering_name][field_name]
                    )
                    for record in records
                )
            )
        result[f"{ordering_name}_non_singleton_group_size"] = _exact_distribution(
            tuple(
                _distribution_value(size)
                for record in records
                for size in record["tie_statistics"][ordering_name][
                    "non_singleton_group_sizes"
                ]
            ),
            allow_empty=True,
        )
    return result


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
    if record.get("schema_version") != EXPERIMENT2C_SCHEMA_VERSION:
        raise ValueError("characterization schema is unsupported")
    if tuple(record.get("candidate_order", ())) != tuple(range(25)):
        raise ValueError("candidate order is invalid")
    if len(record.get("deployed_lamports", ())) != 25 or len(record.get("miner_counts", ())) != 25:
        raise ValueError("fundamental measurement vector length is invalid")
    vector_identities = record.get("measurement_vector_identities")
    if not isinstance(vector_identities, list) or len(vector_identities) != 25:
        raise ValueError("measurement vector identity count is invalid")
    for vector_identity in vector_identities:
        _require_sha256("measurement_vector_identity", vector_identity)
    reconstructed = characterize_miner_count_ordering(
        record["deployed_lamports"], record["miner_counts"]
    )
    for key, value in reconstructed.items():
        if record.get(key) != json.loads(_canonical_json(value)):
            raise ValueError(f"characterization field {key} does not reconstruct")
    total_miners = record.get("board_characteristics", {}).get("round_total_miners")
    _require_u64("round_total_miners", total_miners)
    expected_board = _board_characteristics(
        record["deployed_lamports"], record["miner_counts"], total_miners
    )
    if record.get("board_characteristics") != json.loads(_canonical_json(expected_board)):
        raise ValueError("board characteristics do not reconstruct")


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
    distributions = reports[ORDERING_DISTRIBUTIONS_ARTIFACT_NAME]
    if tuple(distributions["comparisons"]) != tuple(sorted(COMPARISON_NAMES)):
        raise ValueError("comparison report order is invalid")
    for comparison_name in COMPARISON_NAMES:
        report = distributions["comparisons"][comparison_name]
        expected = json.loads(
            _canonical_json(_comparison_distribution_report(records, comparison_name))
        )
        if report != expected:
            raise ValueError(f"{comparison_name} distributions do not reconstruct")
    expected_ties = json.loads(_canonical_json(_tie_distribution_report(records)))
    if distributions["tie_distributions"] != expected_ties:
        raise ValueError("tie distributions do not reconstruct")
    expected_board = json.loads(_canonical_json(_board_characteristic_tables(records)))
    if reports[BOARD_CHARACTERISTICS_ARTIFACT_NAME]["tables"] != expected_board:
        raise ValueError("board characteristic tables do not reconstruct")
    population = reports[POPULATION_ARTIFACT_NAME]
    if population["eligible"] != len(records):
        raise ValueError("eligible population does not reconcile")
    conformance = reports[CONFORMANCE_ARTIFACT_NAME]
    if (
        conformance["status"] != "passed"
        or conformance["outcome_access"] != "prohibited_and_not_performed"
    ):
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
    return json.dumps(
        material,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _require_nonnegative_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
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
    "COMPARISON_NAMES",
    "CONFORMANCE_ARTIFACT_NAME",
    "EXPERIMENT2C_ARTIFACT_NAMES",
    "EXPERIMENT2C_PROTOCOL_DOCUMENT_SHA256",
    "EXPERIMENT2C_PROTOCOL_REVISION",
    "EXPERIMENT2C_SCHEMA_VERSION",
    "Experiment2CConfiguration",
    "Experiment2CResult",
    "MEASUREMENT_BINDING_ARTIFACT_NAME",
    "MINER_VS_DEPLOYMENT",
    "MINER_VS_DEPLOYMENT_PER_MINER",
    "ORDERING_DISTRIBUTIONS_ARTIFACT_NAME",
    "POPULATION_ARTIFACT_NAME",
    "characterize_miner_count_ordering",
    "execute_experiment2c",
    "validate_experiment2c_artifacts",
)
