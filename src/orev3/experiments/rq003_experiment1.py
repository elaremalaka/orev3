"""RQ-003 Experiment 1: direct deployed-lamport ordering.

This module implements the frozen governing protocol without Strategy,
Deployment, RFC-010 evaluation, derived measurements, or RFC-011 economics.
Ranking is durably frozen before finalized outcomes are read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

from orev3.datasets.rq003_experiment0 import (
    RQ003_EXPERIMENT0_OUTPUT_NAMES,
    RQ003Experiment0Configuration,
    _selected_observation_index,
    build_fundamental_measurement_pipeline,
)
from orev3.features.rq003_contracts import canonical_encode
from orev3.features.rq003_deployed_lamports import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
)
from orev3.features.rq003_execution import (
    MeasurementVector,
    RQ003ExecutionContext,
)
from orev3.historical.models import RoundLifecycleIndexRecord
from orev3.replay.engine import select_by_slots_remaining
from orev3.replay.loader import load_round_index
from orev3.strategy_lab.runner import decision_context_from_replay_point


EXPERIMENT1_SCHEMA_VERSION = 1
EXPERIMENT1_PROTOCOL_REVISION = "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
EXPERIMENT1_DATASET_SHA256 = (
    "7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7"
)
EXPERIMENT1_REQUESTED_SLOTS_REMAINING = 5
EXPERIMENT1_FOLD_COUNT = 5
EXPERIMENT1_ADEQUATE_SUPPORT = 100
EXPERIMENT1_BOOTSTRAP_REPLICATES = 10_000
EXPERIMENT1_BOOTSTRAP_CONFIDENCE = 0.975

RANKING_ARTIFACT_NAME = "ranking_artifact.jsonl"
EVALUATION_ARTIFACT_NAME = "evaluation_artifact.jsonl"
METRICS_ARTIFACT_NAME = "metrics.json"
BOOTSTRAP_ARTIFACT_NAME = "bootstrap.json"
FOLDS_ARTIFACT_NAME = "chronological_folds.json"
CADENCE_ARTIFACT_NAME = "cadence.json"
LIFECYCLE_ARTIFACT_NAME = "lifecycle.json"
PROVENANCE_ARTIFACT_NAME = "provenance.json"
EXPERIMENT1_ARTIFACT_NAMES = (
    RANKING_ARTIFACT_NAME,
    EVALUATION_ARTIFACT_NAME,
    METRICS_ARTIFACT_NAME,
    BOOTSTRAP_ARTIFACT_NAME,
    FOLDS_ARTIFACT_NAME,
    CADENCE_ARTIFACT_NAME,
    LIFECYCLE_ARTIFACT_NAME,
    PROVENANCE_ARTIFACT_NAME,
)

_FEATURE_SET_DOMAIN = "rq003-experiment-001-feature-set-v1"
_PRIMARY_RANKING_DOMAIN = "rq003-experiment-001-primary-ranking-v1"
_ASCENDING_RANKING_DOMAIN = "rq003-experiment-001-ascending-sensitivity-v1"
_DETERMINISTIC_BASELINE_DOMAIN = (
    "rq003-experiment-001-deterministic-baseline-v1"
)
_SEEDED_RANDOM_DOMAIN = "rq003-experiment-001-seeded-random-v1"
_RANKING_RECORD_DOMAIN = "rq003-experiment-001-ranking-record-v1"
_EVALUATION_RECORD_DOMAIN = "rq003-experiment-001-evaluation-record-v1"
_REPORT_DOMAIN = "rq003-experiment-001-report-v1"
_BOOTSTRAP_DOMAIN = "rq003-experiment-001-moving-block-bootstrap-v1"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

EXPERIMENT1_FEATURE_SET_IDENTITY = hashlib.sha256(
    canonical_encode(
        {
            "domain": _FEATURE_SET_DOMAIN,
            "material": {
                "ordered_fields": ("deployed_lamports",),
                "source_definition_identity": (
                    DEPLOYED_LAMPORTS_DEFINITION.definition_identity
                ),
                "transformation": "identity",
            },
        }
    )
).hexdigest()

EXPERIMENT1_PRIMARY_RANKING_IDENTITY = hashlib.sha256(
    canonical_encode(
        {
            "domain": _PRIMARY_RANKING_DOMAIN,
            "material": {
                "direction": "descending",
                "field": "deployed_lamports",
                "tie_rule": "one_based_average_rank",
            },
        }
    )
).hexdigest()

EXPERIMENT1_ASCENDING_RANKING_IDENTITY = hashlib.sha256(
    canonical_encode(
        {
            "domain": _ASCENDING_RANKING_DOMAIN,
            "material": {
                "direction": "ascending",
                "field": "deployed_lamports",
                "role": "non_rescuing_sensitivity",
                "tie_rule": "one_based_average_rank",
            },
        }
    )
).hexdigest()

EXPERIMENT1_DETERMINISTIC_BASELINE_IDENTITY = hashlib.sha256(
    canonical_encode(
        {
            "domain": _DETERMINISTIC_BASELINE_DOMAIN,
            "material": {
                "candidate_order": tuple(range(25)),
                "information_role": "uninformed_structural_control",
            },
        }
    )
).hexdigest()

EXPERIMENT1_SEEDED_RANDOM_BASELINE_IDENTITY = hashlib.sha256(
    canonical_encode(
        {
            "domain": _SEEDED_RANDOM_DOMAIN,
            "material": {
                "candidate_count": 25,
                "digest": "sha256",
                "order": "ascending_digest",
                "seed_domain": _SEEDED_RANDOM_DOMAIN,
            },
        }
    )
).hexdigest()


@dataclass(frozen=True, slots=True)
class Experiment1Configuration:
    """Immutable paths and fixed governing-protocol parameters."""

    replay_dataset_path: Path
    output_directory: Path
    expected_dataset_sha256: str = EXPERIMENT1_DATASET_SHA256
    requested_slots_remaining: int = EXPERIMENT1_REQUESTED_SLOTS_REMAINING
    max_slot_distance: int | None = None
    decision_configuration_identity: str = field(init=False)

    def __post_init__(self) -> None:
        dataset = Path(self.replay_dataset_path)
        output = Path(self.output_directory)
        _require_sha256("expected_dataset_sha256", self.expected_dataset_sha256)
        if self.requested_slots_remaining != EXPERIMENT1_REQUESTED_SLOTS_REMAINING:
            raise ValueError("Experiment 1 requires requested_slots_remaining=5")
        if self.max_slot_distance is not None:
            raise ValueError("Experiment 1 does not permit a maximum slot distance")
        object.__setattr__(self, "replay_dataset_path", dataset)
        object.__setattr__(self, "output_directory", output)
        experiment0_configuration = RQ003Experiment0Configuration(
            replay_dataset_path=dataset,
            output_path=output / RANKING_ARTIFACT_NAME,
            requested_slots_remaining=self.requested_slots_remaining,
            max_slot_distance=self.max_slot_distance,
        )
        object.__setattr__(
            self,
            "decision_configuration_identity",
            experiment0_configuration.decision_point_configuration_identity,
        )


@dataclass(frozen=True, slots=True)
class Experiment1Result:
    """Deterministic execution summary without scientific interpretation."""

    dataset_sha256: str
    replay_rounds: int
    ranked_decisions: int
    primary_evaluations: int
    lifecycle_sensitivity_evaluations: int
    missing_outcomes: int
    artifacts: tuple[tuple[str, Path, str], ...]


def _identity(domain: str, material: object) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def _canonical_json(material: object) -> str:
    return json.dumps(
        material,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for line in lines:
                if "\n" in line:
                    raise ValueError("canonical JSONL records cannot contain newlines")
                handle.write(line)
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_write_json(path: Path, material: Mapping[str, Any]) -> None:
    _atomic_write_lines(path, (_canonical_json(material),))


def _average_ranks(values: Sequence[int], *, descending: bool) -> tuple[float, ...]:
    if len(values) != 25:
        raise ValueError("ranking requires exactly 25 candidates")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise ValueError("ranking values must be nonnegative integers")
    order = sorted(range(25), key=lambda square: values[square], reverse=descending)
    ranks: list[float] = [0.0] * 25
    first = 0
    while first < 25:
        last = first + 1
        while last < 25 and values[order[last]] == values[order[first]]:
            last += 1
        average_rank = ((first + 1) + last) / 2
        for position in range(first, last):
            ranks[order[position]] = average_rank
        first = last
    return tuple(ranks)


def _seeded_random_ranks(decision_identity: str) -> tuple[int, ...]:
    _require_sha256("decision_identity", decision_identity)
    digests = tuple(
        hashlib.sha256(
            canonical_encode(
                {
                    "candidate_square": square,
                    "decision_identity": decision_identity,
                    "domain": _SEEDED_RANDOM_DOMAIN,
                }
            )
        ).digest()
        for square in range(25)
    )
    if len(set(digests)) != 25:
        raise ValueError("seeded-random baseline digest collision")
    ordered = sorted(range(25), key=lambda square: digests[square])
    ranks = [0] * 25
    for rank, square in enumerate(ordered, start=1):
        ranks[square] = rank
    return tuple(ranks)


def _tie_sizes(values: Sequence[int]) -> tuple[int, ...]:
    counts = Counter(values)
    return tuple(counts[value] for value in values)


def _ranking_record(
    *,
    lifecycle: RoundLifecycleIndexRecord,
    observation_index: int,
    selected_rpc_slot: int,
    slot_distance: int,
    decision_identity: str,
    vectors: Sequence[MeasurementVector],
    deployed_lamports: Sequence[int],
    decision_configuration_identity: str,
) -> dict[str, Any]:
    primary_ranks = _average_ranks(deployed_lamports, descending=True)
    ascending_ranks = _average_ranks(deployed_lamports, descending=False)
    random_ranks = _seeded_random_ranks(decision_identity)
    tie_sizes = _tie_sizes(deployed_lamports)
    candidates = tuple(
        {
            "ascending_sensitivity_average_rank": ascending_ranks[square],
            "candidate_square": square,
            "deployed_lamports": deployed_lamports[square],
            "deterministic_baseline_rank": square + 1,
            "measurement_vector_identity": vectors[square].vector_identity,
            "primary_average_rank": primary_ranks[square],
            "primary_tie_group_size": tie_sizes[square],
            "seeded_random_baseline_rank": random_ranks[square],
        }
        for square in range(25)
    )
    material: dict[str, Any] = {
        "ascending_ranking_identity": EXPERIMENT1_ASCENDING_RANKING_IDENTITY,
        "candidates": candidates,
        "coverage_status": lifecycle.quality.coverage_status,
        "decision_configuration_identity": decision_configuration_identity,
        "decision_identity": decision_identity,
        "deployed_lamports_definition_identity": (
            DEPLOYED_LAMPORTS_DEFINITION.definition_identity
        ),
        "deployed_lamports_executable_binding_identity": (
            DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY
        ),
        "deterministic_baseline_identity": (
            EXPERIMENT1_DETERMINISTIC_BASELINE_IDENTITY
        ),
        "feature_set_identity": EXPERIMENT1_FEATURE_SET_IDENTITY,
        "observation_index": observation_index,
        "primary_ranking_identity": EXPERIMENT1_PRIMARY_RANKING_IDENTITY,
        "round_id": lifecycle.round_id,
        "schema_version": EXPERIMENT1_SCHEMA_VERSION,
        "seeded_random_baseline_identity": (
            EXPERIMENT1_SEEDED_RANDOM_BASELINE_IDENTITY
        ),
        "selected_rpc_slot": selected_rpc_slot,
        "slot_distance": slot_distance,
        "start_slot": lifecycle.start_slot,
    }
    material["ranking_record_identity"] = _identity(
        _RANKING_RECORD_DOMAIN, material
    )
    return material


def _load_ranking_artifact(path: Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    previous_order: tuple[int, int] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise ValueError(f"ranking line {line_number} lacks a newline")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"ranking line {line_number} is invalid JSON") from error
            if not isinstance(record, dict) or _canonical_json(record) + "\n" != line:
                raise ValueError(f"ranking line {line_number} is not canonical")
            identity = record.pop("ranking_record_identity", None)
            _require_sha256("ranking_record_identity", identity)
            if _identity(_RANKING_RECORD_DOMAIN, record) != identity:
                raise ValueError("ranking record identity does not reconstruct")
            record["ranking_record_identity"] = identity
            _validate_ranking_record(record)
            order = (record["start_slot"], record["round_id"])
            if previous_order is not None and order <= previous_order:
                raise ValueError("ranking artifact is not in strict replay order")
            previous_order = order
            records.append(record)
    if not records:
        raise ValueError("ranking artifact contains no decisions")
    return tuple(records)


def _validate_ranking_record(record: Mapping[str, Any]) -> None:
    prohibited = {
        "winning_square",
        "outcome",
        "outcome_source",
        "capture_mode",
        "finalized_outcome",
        "won",
    }
    if prohibited.intersection(record):
        raise ValueError("ranking artifact contains outcome information")
    if record.get("schema_version") != EXPERIMENT1_SCHEMA_VERSION:
        raise ValueError("ranking record schema is unsupported")
    for name, expected in (
        ("feature_set_identity", EXPERIMENT1_FEATURE_SET_IDENTITY),
        ("primary_ranking_identity", EXPERIMENT1_PRIMARY_RANKING_IDENTITY),
        ("ascending_ranking_identity", EXPERIMENT1_ASCENDING_RANKING_IDENTITY),
        (
            "deterministic_baseline_identity",
            EXPERIMENT1_DETERMINISTIC_BASELINE_IDENTITY,
        ),
        (
            "seeded_random_baseline_identity",
            EXPERIMENT1_SEEDED_RANDOM_BASELINE_IDENTITY,
        ),
    ):
        if record.get(name) != expected:
            raise ValueError(f"ranking record {name} is inconsistent")
    candidates = record.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 25:
        raise ValueError("ranking record must contain 25 candidates")
    if tuple(candidate.get("candidate_square") for candidate in candidates) != tuple(range(25)):
        raise ValueError("ranking candidate order is invalid")
    for candidate in candidates:
        if set(candidate) != {
            "ascending_sensitivity_average_rank",
            "candidate_square",
            "deployed_lamports",
            "deterministic_baseline_rank",
            "measurement_vector_identity",
            "primary_average_rank",
            "primary_tie_group_size",
            "seeded_random_baseline_rank",
        }:
            raise ValueError("ranking candidate schema is invalid")
        _require_sha256(
            "measurement_vector_identity",
            candidate["measurement_vector_identity"],
        )


def _freeze_rankings(
    configuration: Experiment1Configuration,
    lifecycles: Sequence[RoundLifecycleIndexRecord],
    ranking_path: Path,
) -> tuple[dict[str, Any], ...]:
    """Freeze rankings without reading any finalized outcome field."""

    pipeline = build_fundamental_measurement_pipeline()
    deployed_index = RQ003_EXPERIMENT0_OUTPUT_NAMES.index("deployed_lamports")
    selection_audit: list[dict[str, Any]] = []

    def lines() -> Iterable[str]:
        for lifecycle in lifecycles:
            try:
                selection = select_by_slots_remaining(
                    lifecycle,
                    requested_slots_remaining=(
                        configuration.requested_slots_remaining
                    ),
                    max_slot_distance=configuration.max_slot_distance,
                )
            except ValueError as error:
                message = str(error)
                if message.startswith("No observation for round"):
                    reason = "no_predeclared_decision_observation"
                elif "has no usable end_slot" in message:
                    reason = "no_usable_end_slot"
                else:
                    raise
                selection_audit.append(
                    {"round_id": lifecycle.round_id, "status": reason}
                )
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
            decision_identity: str | None = None
            for square in range(25):
                context = RQ003ExecutionContext(
                    decision_context=decision_context,
                    observation_index=observation_index,
                    structural_candidate_key=square,
                    decision_point_configuration_identity=(
                        configuration.decision_configuration_identity
                    ),
                )
                vector = pipeline.compute(context)
                if MeasurementVector.from_canonical_bytes(vector.canonical_bytes()) != vector:
                    raise ValueError("MeasurementVector does not reconstruct")
                if decision_identity is None:
                    decision_identity = context.decision_snapshot_identity
                elif context.decision_snapshot_identity != decision_identity:
                    raise ValueError("candidate decision identities are inconsistent")
                value = vector.ordered_values[deployed_index]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError("deployed_lamports output is invalid")
                vectors.append(vector)
                deployed.append(value)
            if decision_identity is None:
                raise ValueError("decision identity was not constructed")
            record = _ranking_record(
                lifecycle=lifecycle,
                observation_index=observation_index,
                selected_rpc_slot=point.rpc_slot,
                slot_distance=selection.slot_distance,
                decision_identity=decision_identity,
                vectors=vectors,
                deployed_lamports=deployed,
                decision_configuration_identity=(
                    configuration.decision_configuration_identity
                ),
            )
            selection_audit.append(
                {"round_id": lifecycle.round_id, "status": "ranked"}
            )
            yield _canonical_json(record)

    _atomic_write_lines(ranking_path, lines())
    return tuple(selection_audit)


def _evaluation_record(
    ranking: Mapping[str, Any], lifecycle: RoundLifecycleIndexRecord
) -> dict[str, Any]:
    outcome = lifecycle.finalized_outcome
    if outcome is None:
        raise ValueError("evaluation requires one finalized outcome")
    winner = outcome.winning_square
    if isinstance(winner, bool) or not isinstance(winner, int) or not 0 <= winner < 25:
        raise ValueError(f"round {lifecycle.round_id} has an invalid winning square")
    source = lifecycle.finalized_outcome_source
    if source not in {"observed", "enriched"}:
        raise ValueError(f"round {lifecycle.round_id} has ambiguous outcome source")
    capture_mode = lifecycle.finalized_outcome_capture_mode
    if source == "enriched" and capture_mode is not None:
        raise ValueError("enriched outcome cannot have an observer capture mode")
    if capture_mode not in {None, "current_round", "post_transition_predecessor"}:
        raise ValueError("outcome capture mode is unsupported")
    candidates = ranking["candidates"]
    candidate = candidates[winner]
    population = (
        "primary"
        if lifecycle.quality.coverage_status == "complete"
        else "lifecycle_sensitivity"
    )
    material: dict[str, Any] = {
        "ascending_sensitivity_reciprocal_rank": 1.0
        / candidate["ascending_sensitivity_average_rank"],
        "ascending_sensitivity_winner_rank": candidate[
            "ascending_sensitivity_average_rank"
        ],
        "capture_mode": capture_mode,
        "coverage_status": lifecycle.quality.coverage_status,
        "decision_identity": ranking["decision_identity"],
        "deterministic_baseline_reciprocal_rank": 1.0
        / candidate["deterministic_baseline_rank"],
        "deterministic_baseline_winner_rank": candidate[
            "deterministic_baseline_rank"
        ],
        "outcome_source": source,
        "population": population,
        "primary_reciprocal_rank": 1.0 / candidate["primary_average_rank"],
        "primary_tie_group_size": candidate["primary_tie_group_size"],
        "primary_winner_rank": candidate["primary_average_rank"],
        "ranking_record_identity": ranking["ranking_record_identity"],
        "round_id": lifecycle.round_id,
        "schema_version": EXPERIMENT1_SCHEMA_VERSION,
        "seeded_random_baseline_reciprocal_rank": 1.0
        / candidate["seeded_random_baseline_rank"],
        "seeded_random_baseline_winner_rank": candidate[
            "seeded_random_baseline_rank"
        ],
        "slot_distance": ranking["slot_distance"],
        "start_slot": lifecycle.start_slot,
        "winning_square": winner,
    }
    material["evaluation_record_identity"] = _identity(
        _EVALUATION_RECORD_DOMAIN, material
    )
    return material


def _join_outcomes(
    ranking_records: Sequence[Mapping[str, Any]],
    lifecycle_by_round: Mapping[int, RoundLifecycleIndexRecord],
    evaluation_path: Path,
) -> tuple[dict[str, Any], ...]:
    evaluations: list[dict[str, Any]] = []
    for ranking in ranking_records:
        lifecycle = lifecycle_by_round.get(ranking["round_id"])
        if lifecycle is None:
            raise ValueError("ranking round is absent from replay dataset")
        if lifecycle.finalized_outcome is None:
            continue
        evaluations.append(_evaluation_record(ranking, lifecycle))
    _atomic_write_lines(
        evaluation_path,
        (_canonical_json(record) for record in evaluations),
    )
    return tuple(evaluations)


def _load_evaluation_artifact(path: Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    previous_order: tuple[int, int] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise ValueError(f"evaluation line {line_number} lacks a newline")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"evaluation line {line_number} is invalid JSON"
                ) from error
            if not isinstance(record, dict) or _canonical_json(record) + "\n" != line:
                raise ValueError(f"evaluation line {line_number} is not canonical")
            identity = record.pop("evaluation_record_identity", None)
            _require_sha256("evaluation_record_identity", identity)
            if _identity(_EVALUATION_RECORD_DOMAIN, record) != identity:
                raise ValueError("evaluation record identity does not reconstruct")
            record["evaluation_record_identity"] = identity
            if record.get("schema_version") != EXPERIMENT1_SCHEMA_VERSION:
                raise ValueError("evaluation record schema is unsupported")
            order = (record["start_slot"], record["round_id"])
            if previous_order is not None and order <= previous_order:
                raise ValueError("evaluation artifact is not in replay order")
            previous_order = order
            records.append(record)
    if not records:
        raise ValueError("evaluation artifact contains no labeled rounds")
    return tuple(records)


def _load_report(path: Path, expected_kind: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) != 1 or not lines[0].endswith("\n"):
        raise ValueError(f"{path.name} must contain one newline-terminated report")
    try:
        report = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise ValueError(f"{path.name} is invalid JSON") from error
    if not isinstance(report, dict) or _canonical_json(report) + "\n" != lines[0]:
        raise ValueError(f"{path.name} is not canonical")
    identity = report.pop("artifact_identity", None)
    _require_sha256("artifact_identity", identity)
    if _identity(_REPORT_DOMAIN, report) != identity:
        raise ValueError(f"{path.name} identity does not reconstruct")
    report["artifact_identity"] = identity
    if report.get("kind") != expected_kind:
        raise ValueError(f"{path.name} report kind is inconsistent")
    if report.get("protocol_revision") != EXPERIMENT1_PROTOCOL_REVISION:
        raise ValueError(f"{path.name} protocol revision is inconsistent")
    return report


def validate_experiment1_artifacts(
    output_directory: str | Path,
) -> tuple[tuple[str, Path, str], ...]:
    """Fail closed while reconstructing all persisted Experiment 1 artifacts."""

    output = Path(output_directory)
    actual_names = tuple(
        sorted(path.name for path in output.iterdir() if path.is_file())
    )
    if actual_names != tuple(sorted(EXPERIMENT1_ARTIFACT_NAMES)):
        raise ValueError("output directory contains artifacts outside the protocol")
    rankings = _load_ranking_artifact(output / RANKING_ARTIFACT_NAME)
    evaluations = _load_evaluation_artifact(output / EVALUATION_ARTIFACT_NAME)
    ranking_identities = {
        record["ranking_record_identity"] for record in rankings
    }
    if any(
        record["ranking_record_identity"] not in ranking_identities
        for record in evaluations
    ):
        raise ValueError("evaluation references an unknown ranking record")
    reports = {
        METRICS_ARTIFACT_NAME: _load_report(
            output / METRICS_ARTIFACT_NAME, "metrics"
        ),
        BOOTSTRAP_ARTIFACT_NAME: _load_report(
            output / BOOTSTRAP_ARTIFACT_NAME, "bootstrap"
        ),
        FOLDS_ARTIFACT_NAME: _load_report(
            output / FOLDS_ARTIFACT_NAME, "chronological_folds"
        ),
        CADENCE_ARTIFACT_NAME: _load_report(
            output / CADENCE_ARTIFACT_NAME, "cadence"
        ),
        LIFECYCLE_ARTIFACT_NAME: _load_report(
            output / LIFECYCLE_ARTIFACT_NAME, "lifecycle"
        ),
        PROVENANCE_ARTIFACT_NAME: _load_report(
            output / PROVENANCE_ARTIFACT_NAME, "provenance"
        ),
    }
    metrics = reports[METRICS_ARTIFACT_NAME]
    if metrics.get("ranking_artifact_sha256") != _file_sha256(
        output / RANKING_ARTIFACT_NAME
    ):
        raise ValueError("metrics ranking artifact hash is inconsistent")
    if metrics.get("evaluation_artifact_sha256") != _file_sha256(
        output / EVALUATION_ARTIFACT_NAME
    ):
        raise ValueError("metrics evaluation artifact hash is inconsistent")
    if metrics.get("ranked_decision_count") != len(rankings):
        raise ValueError("metrics ranked decision count is inconsistent")
    if metrics.get("evaluation_record_count") != len(evaluations):
        raise ValueError("metrics evaluation record count is inconsistent")
    return tuple(
        (name, output / name, _file_sha256(output / name))
        for name in EXPERIMENT1_ARTIFACT_NAMES
    )


_PROCEDURES = (
    "primary",
    "deterministic_baseline",
    "seeded_random_baseline",
    "ascending_sensitivity",
)


def _metric_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    procedures: dict[str, Any] = {}
    for procedure in _PROCEDURES:
        rank_key = f"{procedure}_winner_rank"
        reciprocal_key = f"{procedure}_reciprocal_rank"
        ranks = [float(record[rank_key]) for record in records]
        reciprocals = [float(record[reciprocal_key]) for record in records]
        distribution = Counter(_rank_label(rank) for rank in ranks)
        procedures[procedure] = {
            "mean_reciprocal_rank": mean(reciprocals) if reciprocals else None,
            "mean_winner_rank": mean(ranks) if ranks else None,
            "median_winner_rank": median(ranks) if ranks else None,
            "top_1_hit_rate": _top_k_rate(ranks, 1),
            "top_3_hit_rate": _top_k_rate(ranks, 3),
            "top_5_hit_rate": _top_k_rate(ranks, 5),
            "winner_rank_distribution": dict(sorted(distribution.items())),
        }
    primary_rr = [float(record["primary_reciprocal_rank"]) for record in records]
    deterministic_rr = [
        float(record["deterministic_baseline_reciprocal_rank"])
        for record in records
    ]
    random_rr = [
        float(record["seeded_random_baseline_reciprocal_rank"])
        for record in records
    ]
    winning_ties = [
        int(record["primary_tie_group_size"]) for record in records
    ]
    return {
        "evaluation_count": len(records),
        "paired_mrr_differences": {
            "primary_minus_deterministic_baseline": (
                mean(a - b for a, b in zip(primary_rr, deterministic_rr, strict=True))
                if records
                else None
            ),
            "primary_minus_seeded_random_baseline": (
                mean(a - b for a, b in zip(primary_rr, random_rr, strict=True))
                if records
                else None
            ),
        },
        "procedures": procedures,
        "winning_square_tie_statistics": {
            "mean_tie_group_size": mean(winning_ties) if winning_ties else None,
            "tied_winner_count": sum(size > 1 for size in winning_ties),
            "tied_winner_rate": (
                sum(size > 1 for size in winning_ties) / len(winning_ties)
                if winning_ties
                else None
            ),
            "tie_group_size_distribution": dict(
                sorted(Counter(str(size) for size in winning_ties).items())
            ),
        },
    }


def _rank_label(rank: float) -> str:
    return str(int(rank)) if rank.is_integer() else str(rank)


def _top_k_rate(ranks: Sequence[float], k: int) -> float | None:
    return sum(rank <= k for rank in ranks) / len(ranks) if ranks else None


def _report(kind: str, material: Mapping[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "experiment": "rq003-experiment-001-direct-deployment-ordering",
        "kind": kind,
        "protocol_revision": EXPERIMENT1_PROTOCOL_REVISION,
        "schema_version": EXPERIMENT1_SCHEMA_VERSION,
        **material,
    }
    report["artifact_identity"] = _identity(_REPORT_DOMAIN, report)
    return report


def _integer_cube_root_ceiling(value: int) -> int:
    if value < 1:
        raise ValueError("cube-root input must be positive")
    result = 1
    while result**3 < value:
        result += 1
    return result


def _circular_block_sum(prefix: Sequence[float], start: int, length: int) -> float:
    return prefix[start + length] - prefix[start]


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _bootstrap(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(records) < 1:
        raise ValueError("bootstrap requires primary evaluations")
    deterministic = tuple(
        float(record["primary_reciprocal_rank"])
        - float(record["deterministic_baseline_reciprocal_rank"])
        for record in records
    )
    random = tuple(
        float(record["primary_reciprocal_rank"])
        - float(record["seeded_random_baseline_reciprocal_rank"])
        for record in records
    )
    count = len(records)
    block_length = _integer_cube_root_ceiling(count)
    blocks_per_replicate = math.ceil(count / block_length)
    doubled_det = deterministic + deterministic
    doubled_random = random + random
    prefix_det = [0.0]
    prefix_random = [0.0]
    for value in doubled_det:
        prefix_det.append(prefix_det[-1] + value)
    for value in doubled_random:
        prefix_random.append(prefix_random[-1] + value)
    det_samples: list[float] = []
    random_samples: list[float] = []
    for replicate in range(EXPERIMENT1_BOOTSTRAP_REPLICATES):
        det_sum = 0.0
        random_sum = 0.0
        remaining = count
        for block_index in range(blocks_per_replicate):
            digest = hashlib.sha256(
                canonical_encode(
                    {
                        "block_index": block_index,
                        "domain": _BOOTSTRAP_DOMAIN,
                        "replicate": replicate,
                    }
                )
            ).digest()
            start = int.from_bytes(digest[:8], "big") % count
            length = min(block_length, remaining)
            det_sum += _circular_block_sum(prefix_det, start, length)
            random_sum += _circular_block_sum(prefix_random, start, length)
            remaining -= length
        if remaining != 0:
            raise ValueError("bootstrap did not sample the declared population")
        det_samples.append(det_sum / count)
        random_samples.append(random_sum / count)
    tail = (1.0 - EXPERIMENT1_BOOTSTRAP_CONFIDENCE) / 2.0
    comparisons = {}
    for name, observed, samples in (
        (
            "primary_minus_deterministic_baseline",
            mean(deterministic),
            det_samples,
        ),
        (
            "primary_minus_seeded_random_baseline",
            mean(random),
            random_samples,
        ),
    ):
        comparisons[name] = {
            "adjusted_confidence_level": EXPERIMENT1_BOOTSTRAP_CONFIDENCE,
            "lower_bound": _percentile(samples, tail),
            "observed_paired_mrr_difference": observed,
            "upper_bound": _percentile(samples, 1.0 - tail),
        }
    return _report(
        "bootstrap",
        {
            "block_length": block_length,
            "comparison_count": 2,
            "familywise_error_rate": 0.05,
            "method": "deterministic_circular_moving_block_percentile",
            "ordered_round_identities": tuple(
                record["evaluation_record_identity"] for record in records
            ),
            "replicates": EXPERIMENT1_BOOTSTRAP_REPLICATES,
            "seed_domain": _BOOTSTRAP_DOMAIN,
            "comparisons": comparisons,
        },
    )


def _fold_report(primary: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    folds: list[dict[str, Any]] = []
    count = len(primary)
    base, remainder = divmod(count, EXPERIMENT1_FOLD_COUNT)
    offset = 0
    for index in range(EXPERIMENT1_FOLD_COUNT):
        size = base + (1 if index < remainder else 0)
        records = primary[offset : offset + size]
        offset += size
        folds.append(
            {
                "adequate_labeled_support": len(records)
                >= EXPERIMENT1_ADEQUATE_SUPPORT,
                "first_round_id": records[0]["round_id"] if records else None,
                "fold": index + 1,
                "last_round_id": records[-1]["round_id"] if records else None,
                "metrics": _metric_summary(records),
            }
        )
    return _report(
        "chronological_folds",
        {
            "adequate_support_threshold": EXPERIMENT1_ADEQUATE_SUPPORT,
            "fold_count": EXPERIMENT1_FOLD_COUNT,
            "folds": folds,
            "ordering": "start_slot_then_round_id",
        },
    )


def _group_report(
    kind: str,
    records: Sequence[Mapping[str, Any]],
    classifier: Any,
    categories: Sequence[str],
) -> dict[str, Any]:
    groups: dict[str, list[Mapping[str, Any]]] = {name: [] for name in categories}
    for record in records:
        category = classifier(record)
        if category not in groups:
            raise ValueError(f"unsupported {kind} category: {category}")
        groups[category].append(record)
    return _report(
        kind,
        {
            "adequate_support_threshold": EXPERIMENT1_ADEQUATE_SUPPORT,
            "groups": {
                category: {
                    "adequate_labeled_support": len(group)
                    >= EXPERIMENT1_ADEQUATE_SUPPORT,
                    "metrics": _metric_summary(group),
                }
                for category, group in groups.items()
            },
        },
    )


def _cadence_category(record: Mapping[str, Any]) -> str:
    distance = record["slot_distance"]
    if distance in (0, 1, 2):
        return str(distance)
    if isinstance(distance, int) and distance >= 3:
        return "3+"
    raise ValueError("evaluation slot distance is invalid")


def _provenance_category(record: Mapping[str, Any]) -> str:
    if record["outcome_source"] == "enriched":
        return "enriched"
    capture_mode = record["capture_mode"]
    if capture_mode == "current_round":
        return "current_round"
    if capture_mode == "post_transition_predecessor":
        return "post_transition_predecessor"
    if capture_mode is None:
        return "observed_legacy_unspecified"
    raise ValueError("outcome provenance is invalid")


def _lifecycle_report(
    lifecycles: Sequence[RoundLifecycleIndexRecord],
    selection_audit: Sequence[Mapping[str, Any]],
    evaluations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selection_by_round = {entry["round_id"]: entry["status"] for entry in selection_audit}
    if len(selection_by_round) != len(lifecycles):
        raise ValueError("selection audit does not cover every replay round")
    coverage = Counter(lifecycle.quality.coverage_status for lifecycle in lifecycles)
    selection = Counter(selection_by_round.values())
    outcome = Counter(
        "missing" if lifecycle.finalized_outcome is None else "available"
        for lifecycle in lifecycles
    )
    sensitivity = tuple(
        record for record in evaluations if record["population"] == "lifecycle_sensitivity"
    )
    return _report(
        "lifecycle",
        {
            "coverage_counts": dict(sorted(coverage.items())),
            "lifecycle_sensitivity_metrics": _metric_summary(sensitivity),
            "outcome_availability_counts": dict(sorted(outcome.items())),
            "replay_round_count": len(lifecycles),
            "selection_counts": dict(sorted(selection.items())),
        },
    )


def _metrics_report(
    lifecycles: Sequence[RoundLifecycleIndexRecord],
    ranking_records: Sequence[Mapping[str, Any]],
    primary: Sequence[Mapping[str, Any]],
    evaluation_count: int,
    dataset_sha256: str,
    ranking_sha256: str,
    evaluation_sha256: str,
) -> dict[str, Any]:
    all_tie_groups: Counter[str] = Counter()
    tied_decisions = 0
    for ranking in ranking_records:
        values = [candidate["deployed_lamports"] for candidate in ranking["candidates"]]
        groups = Counter(values)
        sizes = tuple(groups.values())
        all_tie_groups.update(str(size) for size in sizes)
        tied_decisions += any(size > 1 for size in sizes)
    return _report(
        "metrics",
        {
            "dataset_sha256": dataset_sha256,
            "evaluation_artifact_sha256": evaluation_sha256,
            "evaluation_record_count": evaluation_count,
            "feature_set_identity": EXPERIMENT1_FEATURE_SET_IDENTITY,
            "outcome_availability": {
                "available": sum(
                    lifecycle.finalized_outcome is not None for lifecycle in lifecycles
                ),
                "missing": sum(
                    lifecycle.finalized_outcome is None for lifecycle in lifecycles
                ),
            },
            "primary_metrics": _metric_summary(primary),
            "ranking_artifact_sha256": ranking_sha256,
            "ranked_decision_count": len(ranking_records),
            "replay_round_count": len(lifecycles),
            "tie_statistics": {
                "all_tie_group_size_distribution": dict(sorted(all_tie_groups.items())),
                "decisions_with_any_tie": tied_decisions,
                "decisions_with_any_tie_rate": tied_decisions / len(ranking_records),
            },
        },
    )


def execute_experiment1(configuration: Experiment1Configuration) -> Experiment1Result:
    """Execute and persist the exact eight governing-protocol artifacts."""

    if not isinstance(configuration, Experiment1Configuration):
        raise TypeError("configuration must be Experiment1Configuration")
    dataset_sha256 = _file_sha256(configuration.replay_dataset_path)
    if dataset_sha256 != configuration.expected_dataset_sha256:
        raise ValueError("replay dataset SHA-256 does not match the governing protocol")
    lifecycle_by_round = load_round_index(configuration.replay_dataset_path)
    lifecycles = tuple(
        sorted(
            lifecycle_by_round.values(),
            key=lambda lifecycle: (lifecycle.start_slot, lifecycle.round_id),
        )
    )
    if not lifecycles:
        raise ValueError("replay dataset contains no rounds")
    output = configuration.output_directory
    output.mkdir(parents=True, exist_ok=True)
    ranking_path = output / RANKING_ARTIFACT_NAME
    selection_audit = _freeze_rankings(configuration, lifecycles, ranking_path)
    ranking_sha256 = _file_sha256(ranking_path)
    ranking_records = _load_ranking_artifact(ranking_path)

    evaluation_path = output / EVALUATION_ARTIFACT_NAME
    evaluations = _join_outcomes(
        ranking_records, lifecycle_by_round, evaluation_path
    )
    evaluation_sha256 = _file_sha256(evaluation_path)
    primary = tuple(
        record for record in evaluations if record["population"] == "primary"
    )
    if not primary:
        raise ValueError("primary evaluation population is empty")

    reports = {
        METRICS_ARTIFACT_NAME: _metrics_report(
            lifecycles,
            ranking_records,
            primary,
            len(evaluations),
            dataset_sha256,
            ranking_sha256,
            evaluation_sha256,
        ),
        BOOTSTRAP_ARTIFACT_NAME: _bootstrap(primary),
        FOLDS_ARTIFACT_NAME: _fold_report(primary),
        CADENCE_ARTIFACT_NAME: _group_report(
            "cadence", primary, _cadence_category, ("0", "1", "2", "3+")
        ),
        LIFECYCLE_ARTIFACT_NAME: _lifecycle_report(
            lifecycles, selection_audit, evaluations
        ),
        PROVENANCE_ARTIFACT_NAME: _group_report(
            "provenance",
            primary,
            _provenance_category,
            (
                "current_round",
                "post_transition_predecessor",
                "enriched",
                "observed_legacy_unspecified",
            ),
        ),
    }
    for name, report in reports.items():
        _atomic_write_json(output / name, report)

    artifacts = validate_experiment1_artifacts(output)
    sensitivity_count = sum(
        record["population"] == "lifecycle_sensitivity" for record in evaluations
    )
    return Experiment1Result(
        dataset_sha256=dataset_sha256,
        replay_rounds=len(lifecycles),
        ranked_decisions=len(ranking_records),
        primary_evaluations=len(primary),
        lifecycle_sensitivity_evaluations=sensitivity_count,
        missing_outcomes=sum(
            lifecycle.finalized_outcome is None for lifecycle in lifecycles
        ),
        artifacts=artifacts,
    )


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    arguments = parser.parse_args(argv)
    result = execute_experiment1(
        Experiment1Configuration(
            replay_dataset_path=arguments.dataset,
            output_directory=arguments.output_directory,
        )
    )
    print(
        _canonical_json(
            {
                "artifacts": {
                    name: {"path": str(path), "sha256": digest}
                    for name, path, digest in result.artifacts
                },
                "dataset_sha256": result.dataset_sha256,
                "lifecycle_sensitivity_evaluations": (
                    result.lifecycle_sensitivity_evaluations
                ),
                "missing_outcomes": result.missing_outcomes,
                "primary_evaluations": result.primary_evaluations,
                "ranked_decisions": result.ranked_decisions,
                "replay_rounds": result.replay_rounds,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "EXPERIMENT1_ARTIFACT_NAMES",
    "EXPERIMENT1_DATASET_SHA256",
    "Experiment1Configuration",
    "Experiment1Result",
    "execute_experiment1",
    "validate_experiment1_artifacts",
)
