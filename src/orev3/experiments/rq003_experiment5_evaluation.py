"""Outcome-authorized evaluation capability for RQ-003 Experiment 005.

This module consumes an already frozen :class:`RankingArtifact`.  It has no
dataset loader and cannot construct or alter rankings.  Slice-1 tests use only
synthetic labels; this code does not itself grant outcome-access authority.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import math
from statistics import median
from typing import Callable, Mapping, Sequence

from orev3.experiments.rq003_experiment2a import CanonicalRational
from orev3.experiments.rq003_experiment5 import (
    EXPERIMENT5_ADEQUATE_SUPPORT,
    EXPERIMENT5_IDENTIFIER,
    EXPERIMENT5_PROTOCOL_SHA256,
    BootstrapResult,
    construct_bootstrap,
    five_consecutive_folds,
    identity,
    immutable_material,
    reciprocal_rank,
    represented_mean,
    require_sha256,
    subtract64,
)
from orev3.experiments.rq003_experiment5_ranking import (
    RankingArtifact,
    RankingRecord,
)
from orev3.features.rq003_contracts import canonical_decode, canonical_encode


PRIMARY_DISPOSITIONS = (
    "invalid_execution",
    "evidence_insufficient",
    "null_not_rejected",
    "provisional_support_for_confirmation",
)
INCREMENTAL_DISPOSITIONS = (
    "paired_improvement_supported",
    "paired_improvement_not_established",
    "paired_comparison_insufficient",
)
COMPARABILITY_STATES = (
    "comparability_not_assessable",
    "material_comparability_failure",
    "generalization_warning",
    "comparable_for_bounded_labeled_inference",
)
_PROVENANCE = {
    "current_round",
    "post_transition_predecessor",
    "enriched",
}
_EVALUATION_RECORD_IDENTITY_DOMAIN = "rq003-experiment-005-evaluation-record-v1"
_EVALUATION_REPORT_IDENTITY_DOMAIN = "rq003-experiment-005-evaluation-report-v1"
_COMPARABILITY_IDENTITY_DOMAIN = "rq003-experiment-005-comparability-v1"
_INVALID_EXECUTION_ARTIFACT_DOMAIN = "rq003-experiment-005-invalid-execution-v1"
_GOVERNED_INVALID_REASONS = {
    "authorization_ranking_binding_mismatch",
    "duplicate_outcome_label",
    "label_outside_ranking_population",
    "malformed_or_nonconforming_ranking_authority",
    "outcome_source_binding_mismatch",
}


def _require_int(name: str, value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class EvaluationAuthorizationBinding:
    """A structural binding supplied by a later authorized execution layer."""

    ranking_artifact_identity: str
    outcome_source_identity: str
    authorization_identity: str

    def __post_init__(self) -> None:
        require_sha256("ranking_artifact_identity", self.ranking_artifact_identity)
        require_sha256("outcome_source_identity", self.outcome_source_identity)
        require_sha256("authorization_identity", self.authorization_identity)


@dataclass(frozen=True, slots=True)
class OutcomeLabel:
    """One post-freeze label; this type is intentionally evaluation-only."""

    round_identity: str
    winning_square: int
    provenance: str
    outcome_source_identity: str

    def __post_init__(self) -> None:
        require_sha256("round_identity", self.round_identity)
        require_sha256("outcome_source_identity", self.outcome_source_identity)
        if (
            isinstance(self.winning_square, bool)
            or not isinstance(self.winning_square, int)
            or self.winning_square not in range(25)
        ):
            raise ValueError("winning_square must be in 0..24")
        if self.provenance not in _PROVENANCE:
            raise ValueError("outcome provenance is not permitted")


@dataclass(frozen=True, slots=True)
class InvalidExecutionArtifact:
    """Canonical no-science result for a governed malformed authority graph."""

    failed_input_sha256: str
    authorization_identity: str
    outcome_source_identity: str
    reasons: tuple[str, ...]
    invalid_execution_artifact_identity: str = field(init=False)

    @property
    def primary_disposition(self) -> str:
        return "invalid_execution"

    @property
    def primary_reasons(self) -> tuple[str, ...]:
        return self.reasons

    @property
    def incremental_disposition(self) -> None:
        return None

    def __post_init__(self) -> None:
        require_sha256("failed_input_sha256", self.failed_input_sha256)
        require_sha256("authorization_identity", self.authorization_identity)
        require_sha256("outcome_source_identity", self.outcome_source_identity)
        if not self.reasons or self.reasons != tuple(sorted(set(self.reasons))):
            raise ValueError("invalid execution reasons must be canonical")
        if not set(self.reasons).issubset(_GOVERNED_INVALID_REASONS):
            raise ValueError("invalid execution reason is not governed")
        object.__setattr__(
            self,
            "invalid_execution_artifact_identity",
            identity(_INVALID_EXECUTION_ARTIFACT_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "authorization_identity": self.authorization_identity,
            "failed_input_sha256": self.failed_input_sha256,
            "incremental_disposition": None,
            "outcome_source_identity": self.outcome_source_identity,
            "primary_disposition": "invalid_execution",
            "reasons": self.reasons,
            "scientific_metrics_interpretable": False,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_encode(self.to_material())

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "invalid_execution_artifact_identity": (
                self.invalid_execution_artifact_identity
            ),
        }

    @classmethod
    def from_material(cls, material: object) -> InvalidExecutionArtifact:
        if not isinstance(material, Mapping) or set(material) != {
            "authorization_identity",
            "failed_input_sha256",
            "incremental_disposition",
            "invalid_execution_artifact_identity",
            "outcome_source_identity",
            "primary_disposition",
            "reasons",
            "scientific_metrics_interpretable",
        }:
            raise ValueError("invalid execution artifact material is not closed")
        if (
            material["primary_disposition"] != "invalid_execution"
            or material["incremental_disposition"] is not None
            or material["scientific_metrics_interpretable"] is not False
        ):
            raise ValueError("invalid execution artifact contains scientific claims")
        result = cls(
            failed_input_sha256=material["failed_input_sha256"],
            authorization_identity=material["authorization_identity"],
            outcome_source_identity=material["outcome_source_identity"],
            reasons=material["reasons"],
        )
        if result.to_material() != material:
            raise ValueError("invalid execution artifact does not reconstruct")
        return result

    @classmethod
    def from_canonical_bytes(cls, raw: bytes) -> InvalidExecutionArtifact:
        result = cls.from_material(canonical_decode(raw))
        if result.canonical_bytes() != raw:
            raise ValueError("invalid execution artifact bytes are not canonical")
        return result


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    round_identity: str
    ranking_record_identity: str
    round_id: int
    start_slot: int
    lifecycle_status: str
    provenance: str
    winning_square: int
    decision_distance_slots: int
    primary_winner_rank: float
    deterministic_baseline_winner_rank: float
    seeded_random_baseline_winner_rank: float
    deployment_per_miner_winner_rank: float
    ascending_sensitivity_winner_rank: float
    primary_reciprocal_rank: float
    deterministic_baseline_reciprocal_rank: float
    seeded_random_baseline_reciprocal_rank: float
    deployment_per_miner_reciprocal_rank: float
    ascending_sensitivity_reciprocal_rank: float
    primary_tie_group_size: int
    evaluation_record_identity: str = field(init=False)

    def __post_init__(self) -> None:
        require_sha256("round_identity", self.round_identity)
        require_sha256("ranking_record_identity", self.ranking_record_identity)
        if self.provenance not in _PROVENANCE:
            raise ValueError("outcome provenance is invalid")
        if (
            isinstance(self.winning_square, bool)
            or not isinstance(self.winning_square, int)
            or self.winning_square not in range(25)
        ):
            raise ValueError("winning square is invalid")
        for name in (
            "primary_winner_rank", "deterministic_baseline_winner_rank",
            "seeded_random_baseline_winner_rank",
            "deployment_per_miner_winner_rank", "ascending_sensitivity_winner_rank",
            "primary_reciprocal_rank", "deterministic_baseline_reciprocal_rank",
            "seeded_random_baseline_reciprocal_rank",
            "deployment_per_miner_reciprocal_rank",
            "ascending_sensitivity_reciprocal_rank",
        ):
            value = getattr(self, name)
            if not isinstance(value, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite binary64")
        _require_int("primary_tie_group_size", self.primary_tie_group_size, minimum=1)
        material = self.to_identity_material()
        object.__setattr__(
            self,
            "evaluation_record_identity",
            identity(_EVALUATION_RECORD_IDENTITY_DOMAIN, material),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "ascending_sensitivity_reciprocal_rank": self.ascending_sensitivity_reciprocal_rank,
            "ascending_sensitivity_winner_rank": self.ascending_sensitivity_winner_rank,
            "decision_distance_slots": self.decision_distance_slots,
            "deployment_per_miner_reciprocal_rank": self.deployment_per_miner_reciprocal_rank,
            "deployment_per_miner_winner_rank": self.deployment_per_miner_winner_rank,
            "deterministic_baseline_reciprocal_rank": self.deterministic_baseline_reciprocal_rank,
            "deterministic_baseline_winner_rank": self.deterministic_baseline_winner_rank,
            "lifecycle_status": self.lifecycle_status,
            "primary_reciprocal_rank": self.primary_reciprocal_rank,
            "primary_tie_group_size": self.primary_tie_group_size,
            "primary_winner_rank": self.primary_winner_rank,
            "provenance": self.provenance,
            "ranking_record_identity": self.ranking_record_identity,
            "round_id": self.round_id,
            "round_identity": self.round_identity,
            "seeded_random_baseline_reciprocal_rank": self.seeded_random_baseline_reciprocal_rank,
            "seeded_random_baseline_winner_rank": self.seeded_random_baseline_winner_rank,
            "start_slot": self.start_slot,
            "winning_square": self.winning_square,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "evaluation_record_identity": self.evaluation_record_identity,
        }

    @classmethod
    def from_material(cls, material: object) -> EvaluationRecord:
        fields = {item.name for item in cls.__dataclass_fields__.values() if item.init}
        if not isinstance(material, dict) or set(material) != fields | {"evaluation_record_identity"}:
            raise ValueError("evaluation record material is not closed")
        result = cls(**{name: material[name] for name in fields})
        if result.to_material() != material:
            raise ValueError("evaluation record identity does not reconstruct")
        return result


@dataclass(frozen=True, slots=True)
class ComparabilityRow:
    category: str
    labeled_count: int
    missing_count: int
    labeled_proportion: CanonicalRational | None
    missing_proportion: CanonicalRational | None

    @property
    def total(self) -> int:
        return self.labeled_count + self.missing_count

    def to_material(self) -> dict[str, object]:
        return {
            "category": self.category,
            "labeled_count": self.labeled_count,
            "labeled_proportion": (
                self.labeled_proportion.to_dict()
                if self.labeled_proportion is not None
                else "not_available"
            ),
            "missing_count": self.missing_count,
            "missing_proportion": (
                self.missing_proportion.to_dict()
                if self.missing_proportion is not None
                else "not_available"
            ),
            "stratum_total": self.total,
        }


@dataclass(frozen=True, slots=True)
class ComparabilityDimension:
    name: str
    rows: tuple[ComparabilityRow, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))

    def to_material(self) -> dict[str, object]:
        return {"dimension": self.name, "rows": tuple(row.to_material() for row in self.rows)}


@dataclass(frozen=True, slots=True)
class ComparabilityResult:
    state: str
    warning_dimensions: tuple[str, ...]
    reasons: tuple[str, ...]
    dimensions: tuple[ComparabilityDimension, ...]
    comparability_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "warning_dimensions", tuple(self.warning_dimensions))
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(self, "dimensions", tuple(self.dimensions))
        if self.state not in COMPARABILITY_STATES:
            raise ValueError("comparability state is invalid")
        object.__setattr__(
            self,
            "comparability_identity",
            identity(_COMPARABILITY_IDENTITY_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "dimensions": tuple(item.to_material() for item in self.dimensions),
            "reasons": self.reasons,
            "state": self.state,
            "warning_dimensions": self.warning_dimensions,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "comparability_identity": self.comparability_identity,
        }


@dataclass(frozen=True, slots=True)
class ControlResult:
    family: str
    status: str
    adequate_groups: int
    conflicting_groups: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    group_metrics: tuple[tuple[str, Mapping[str, object]], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "conflicting_groups", tuple(self.conflicting_groups))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        if self.status not in {"pass", "insufficient", "conflict"}:
            raise ValueError("control status is invalid")
        frozen_metrics: list[tuple[str, Mapping[str, object]]] = []
        for name, metrics in self.group_metrics:
            frozen = immutable_material(metrics)
            if not isinstance(name, str) or not isinstance(frozen, Mapping):
                raise TypeError("control group metrics are not canonical")
            frozen_metrics.append((name, frozen))
        object.__setattr__(self, "group_metrics", tuple(frozen_metrics))

    def to_material(self) -> dict[str, object]:
        return {
            "adequate_groups": self.adequate_groups,
            "conflicting_groups": self.conflicting_groups,
            "family": self.family,
            "group_metrics": dict(self.group_metrics),
            "limitations": self.limitations,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    ranking_artifact: RankingArtifact = field(repr=False, compare=False)
    authorization: EvaluationAuthorizationBinding = field(repr=False, compare=False)
    evaluation_records: tuple[EvaluationRecord, ...]
    missing_round_identities: tuple[str, ...]
    comparability: ComparabilityResult
    bootstrap: BootstrapResult | None
    controls: tuple[ControlResult, ...]
    primary_disposition: str
    primary_reasons: tuple[str, ...]
    incremental_disposition: str | None
    confirmation_required: bool
    ranking_artifact_identity: str = field(init=False)
    authorization_identity: str = field(init=False)
    outcome_source_identity: str = field(init=False)
    evaluation_report_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evaluation_records", tuple(self.evaluation_records))
        object.__setattr__(
            self, "missing_round_identities", tuple(self.missing_round_identities)
        )
        object.__setattr__(self, "controls", tuple(self.controls))
        object.__setattr__(self, "primary_reasons", tuple(self.primary_reasons))
        if not isinstance(self.ranking_artifact, RankingArtifact):
            raise TypeError("ranking_artifact must be accepted RankingArtifact authority")
        if not isinstance(self.authorization, EvaluationAuthorizationBinding):
            raise TypeError("authorization must be EvaluationAuthorizationBinding")
        if (
            self.authorization.ranking_artifact_identity
            != self.ranking_artifact.ranking_artifact_identity
        ):
            raise ValueError("evaluation authorization does not bind ranking artifact")
        object.__setattr__(
            self,
            "ranking_artifact_identity",
            self.ranking_artifact.ranking_artifact_identity,
        )
        object.__setattr__(
            self, "authorization_identity", self.authorization.authorization_identity
        )
        object.__setattr__(
            self, "outcome_source_identity", self.authorization.outcome_source_identity
        )
        record_rounds = tuple(record.round_identity for record in self.evaluation_records)
        if len(record_rounds) != len(set(record_rounds)):
            raise ValueError("evaluation records contain duplicate rounds")
        if len(self.missing_round_identities) != len(set(self.missing_round_identities)):
            raise ValueError("missing population contains duplicate rounds")
        if set(record_rounds) & set(self.missing_round_identities):
            raise ValueError("labeled and missing populations overlap")
        for value in self.missing_round_identities:
            require_sha256("missing round identity", value)
        if self.primary_disposition not in PRIMARY_DISPOSITIONS:
            raise ValueError("primary disposition is invalid")
        if (
            self.incremental_disposition is not None
            and self.incremental_disposition not in INCREMENTAL_DISPOSITIONS
        ):
            raise ValueError("incremental disposition is invalid")
        if self.primary_disposition == "invalid_execution" and self.incremental_disposition is not None:
            raise ValueError("invalid execution cannot have a secondary disposition")
        if self.primary_disposition == "provisional_support_for_confirmation" and not self.confirmation_required:
            raise ValueError("provisional support must require confirmation")
        expected = _reconstruct_evaluation_components(
            self.ranking_artifact,
            self.evaluation_records,
            self.outcome_source_identity,
        )
        supplied = {
            "bootstrap": self.bootstrap,
            "comparability": self.comparability,
            "confirmation_required": self.confirmation_required,
            "controls": self.controls,
            "incremental_disposition": self.incremental_disposition,
            "missing_round_identities": self.missing_round_identities,
            "primary_disposition": self.primary_disposition,
            "primary_reasons": self.primary_reasons,
        }
        if not _evaluation_components_equal(supplied, expected):
            raise ValueError("evaluation science does not reconstruct from canonical records")
        object.__setattr__(
            self,
            "evaluation_report_identity",
            identity(_EVALUATION_REPORT_IDENTITY_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, object]:
        primary = tuple(
            record for record in self.evaluation_records
            if record.lifecycle_status == "complete"
        )
        vectors = paired_vectors(primary) if primary else {
            "primary_minus_deployment_per_miner": (),
            "primary_minus_deterministic_baseline": (),
            "primary_minus_seeded_random_baseline": (),
        }
        fold_report = tuple(
            {
                "adequate": stop - start >= EXPERIMENT5_ADEQUATE_SUPPORT,
                "fold": index,
                "metrics": _metric_summary(primary[start:stop]),
                "ordered_round_identities": tuple(
                    record.round_identity for record in primary[start:stop]
                ),
                "support": stop - start,
            }
            for index, (start, stop) in enumerate(
                five_consecutive_folds(len(primary)), start=1
            )
        )
        return {
            "authorization_identity": self.authorization_identity,
            "bootstrap": self.bootstrap.to_material() if self.bootstrap else None,
            "comparability": self.comparability.to_material(),
            "confirmation_boundary": {
                "alternative_supported_available": False,
                "disjoint_confirmation_required": self.confirmation_required,
                "chronologically_later": True,
                "immutable_disjoint_population": True,
                "no_performance_based_stopping": True,
                "same_frozen_scientific_contract": True,
            },
            "controls": tuple(item.to_material() for item in self.controls),
            "evaluation_records": tuple(item.to_material() for item in self.evaluation_records),
            "experiment_identifier": EXPERIMENT5_IDENTIFIER,
            "incremental_disposition": self.incremental_disposition,
            "metrics": _evaluation_metric_material(self.evaluation_records),
            "chronological_fold_report": fold_report,
            "round_level_paired_vectors": tuple(
                {
                    "evaluation_record_identity": record.evaluation_record_identity,
                    "round_identity": record.round_identity,
                    **{
                        name: vectors[name][offset]
                        for name in (
                            "primary_minus_deployment_per_miner",
                            "primary_minus_deterministic_baseline",
                            "primary_minus_seeded_random_baseline",
                        )
                    },
                }
                for offset, record in enumerate(primary)
            ),
            "missing_round_identities": self.missing_round_identities,
            "outcome_source_identity": self.outcome_source_identity,
            "outcome_join_report": {
                "labeled_round_identities": tuple(
                    record.round_identity for record in self.evaluation_records
                ),
                "missing_round_identities": self.missing_round_identities,
                "provenance_counts": dict(
                    sorted(Counter(record.provenance for record in self.evaluation_records).items())
                ),
            },
            "primary_disposition": self.primary_disposition,
            "primary_reasons": self.primary_reasons,
            "protocol_sha256": EXPERIMENT5_PROTOCOL_SHA256,
            "population_accounting": {
                "complete_lifecycle_primary_count": sum(
                    record.lifecycle_status == "complete"
                    for record in self.evaluation_records
                ),
                "labeled_round_count": len(self.evaluation_records),
                "lifecycle_sensitivity_count": sum(
                    record.lifecycle_status != "complete"
                    for record in self.evaluation_records
                ),
                "missing_label_count": len(self.missing_round_identities),
                "ranked_round_count": (
                    len(self.evaluation_records) + len(self.missing_round_identities)
                ),
            },
            "ranking_artifact_identity": self.ranking_artifact_identity,
            "evaluation_audits": {
                "deterministic_reconstruction": "pass",
                "population_parity": (
                    "not_interpreted"
                    if self.primary_disposition == "invalid_execution" else "pass"
                ),
                "ranking_immutability": (
                    "not_interpreted"
                    if self.primary_disposition == "invalid_execution" else "pass"
                ),
                "secondary_and_sensitivities_non_rescuing": True,
            },
            "schema_version": 1,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "evaluation_report_identity": self.evaluation_report_identity,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_encode(self.to_material())

    @classmethod
    def from_material(
        cls,
        material: object,
        ranking_artifact: RankingArtifact,
        authorization: EvaluationAuthorizationBinding,
    ) -> EvaluationReport:
        if not isinstance(material, dict) or set(material) != {
            "authorization_identity", "bootstrap", "comparability",
            "confirmation_boundary", "controls", "evaluation_records",
            "chronological_fold_report", "evaluation_audits",
            "evaluation_report_identity", "experiment_identifier",
            "incremental_disposition", "metrics", "missing_round_identities",
            "outcome_source_identity", "population_accounting",
            "outcome_join_report",
            "round_level_paired_vectors",
            "primary_disposition", "primary_reasons", "protocol_sha256",
            "ranking_artifact_identity", "schema_version",
        }:
            raise ValueError("evaluation report material is not closed")
        records = material["evaluation_records"]
        controls = material["controls"]
        if not isinstance(records, tuple) or not isinstance(controls, tuple):
            raise ValueError("evaluation report sequences are not canonical")
        result = cls(
            ranking_artifact=ranking_artifact,
            authorization=authorization,
            evaluation_records=tuple(EvaluationRecord.from_material(value) for value in records),
            missing_round_identities=material["missing_round_identities"],
            comparability=_comparability_from_material(material["comparability"]),
            bootstrap=(
                BootstrapResult.from_material(material["bootstrap"])
                if material["bootstrap"] is not None else None
            ),
            controls=tuple(_control_from_material(value) for value in controls),
            primary_disposition=material["primary_disposition"],
            primary_reasons=material["primary_reasons"],
            incremental_disposition=material["incremental_disposition"],
            confirmation_required=material["confirmation_boundary"][
                "disjoint_confirmation_required"
            ],
        )
        if result.to_material() != material:
            raise ValueError("evaluation report authority does not reconstruct")
        return result

    @classmethod
    def from_canonical_bytes(
        cls,
        raw: bytes,
        ranking_artifact: RankingArtifact,
        authorization: EvaluationAuthorizationBinding,
    ) -> EvaluationReport:
        result = cls.from_material(canonical_decode(raw), ranking_artifact, authorization)
        if result.canonical_bytes() != raw:
            raise ValueError("evaluation report bytes are not canonical")
        return result


def _comparability_from_material(material: object) -> ComparabilityResult:
    if not isinstance(material, dict) or set(material) != {
        "comparability_identity", "dimensions", "reasons", "state",
        "warning_dimensions",
    }:
        raise ValueError("comparability material is not closed")
    dimensions: list[ComparabilityDimension] = []
    for item in material["dimensions"]:
        if not isinstance(item, dict) or set(item) != {"dimension", "rows"}:
            raise ValueError("comparability dimension is not closed")
        rows: list[ComparabilityRow] = []
        for row in item["rows"]:
            if not isinstance(row, dict) or set(row) != {
                "category", "labeled_count", "labeled_proportion",
                "missing_count", "missing_proportion", "stratum_total",
            }:
                raise ValueError("comparability row is not closed")
            def rational(value: object) -> CanonicalRational | None:
                return None if value == "not_available" else CanonicalRational.from_dict(value)
            value = ComparabilityRow(
                category=row["category"], labeled_count=row["labeled_count"],
                missing_count=row["missing_count"],
                labeled_proportion=rational(row["labeled_proportion"]),
                missing_proportion=rational(row["missing_proportion"]),
            )
            if value.to_material() != row:
                raise ValueError("comparability row does not reconstruct")
            rows.append(value)
        dimensions.append(ComparabilityDimension(item["dimension"], tuple(rows)))
    result = ComparabilityResult(
        state=material["state"], warning_dimensions=material["warning_dimensions"],
        reasons=material["reasons"], dimensions=tuple(dimensions),
    )
    if result.to_material() != material:
        raise ValueError("comparability identity does not reconstruct")
    return result


def _control_from_material(material: object) -> ControlResult:
    if not isinstance(material, dict) or set(material) != {
        "adequate_groups", "conflicting_groups", "family", "group_metrics",
        "limitations", "status"
    }:
        raise ValueError("control material is not closed")
    return ControlResult(
        family=material["family"], status=material["status"],
        adequate_groups=material["adequate_groups"],
        conflicting_groups=material["conflicting_groups"],
        limitations=material["limitations"],
        group_metrics=tuple(sorted(material["group_metrics"].items())),
    )


def _join_one(ranking: RankingRecord, label: OutcomeLabel) -> EvaluationRecord:
    if ranking.round_identity != label.round_identity:
        raise ValueError("outcome label does not match ranking round")
    candidate = ranking.candidates[label.winning_square]
    primary_rank = candidate.primary_average_rank
    deterministic_rank = float(candidate.deterministic_baseline_rank)
    random_rank = float(candidate.seeded_random_baseline_rank)
    comparator_rank = candidate.deployment_per_miner_average_rank
    ascending_rank = candidate.ascending_sensitivity_average_rank
    return EvaluationRecord(
        round_identity=ranking.round_identity,
        ranking_record_identity=ranking.ranking_record_identity,
        round_id=ranking.round_id,
        start_slot=ranking.start_slot,
        lifecycle_status=ranking.lifecycle_status,
        provenance=label.provenance,
        winning_square=label.winning_square,
        decision_distance_slots=ranking.decision_distance_slots,
        primary_winner_rank=primary_rank,
        deterministic_baseline_winner_rank=deterministic_rank,
        seeded_random_baseline_winner_rank=random_rank,
        deployment_per_miner_winner_rank=comparator_rank,
        ascending_sensitivity_winner_rank=ascending_rank,
        primary_reciprocal_rank=reciprocal_rank(primary_rank),
        deterministic_baseline_reciprocal_rank=reciprocal_rank(deterministic_rank),
        seeded_random_baseline_reciprocal_rank=reciprocal_rank(random_rank),
        deployment_per_miner_reciprocal_rank=reciprocal_rank(comparator_rank),
        ascending_sensitivity_reciprocal_rank=reciprocal_rank(ascending_rank),
        primary_tie_group_size=candidate.primary_tie_group_size,
    )


def _distance_category(record: RankingRecord) -> str:
    distance = record.decision_distance_slots
    if distance in {0, 1, 2}:
        return str(distance)
    if distance >= 3:
        return "3+"
    raise ValueError("decision distance is invalid")


def _cadence_category(record: RankingRecord) -> str:
    return "no_significant_gap" if record.significant_gap_count == 0 else "significant_gap_present"


def _collector_category(record: RankingRecord) -> str:
    if not record.collector_session_ids:
        return "collector_regime_metadata_unavailable"
    return canonical_encode(
        {
            "collector_session_ids": record.collector_session_ids,
            "source_schema_versions": record.source_schema_versions,
        }
    ).hex()


def _exact_float_category(value: float) -> str:
    return canonical_encode(value).hex()


def _build_dimension(
    *,
    name: str,
    records: Sequence[RankingRecord],
    labeled: set[str],
    classifier: Callable[[RankingRecord], str],
    category_order: Sequence[str] | None = None,
) -> ComparabilityDimension:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for record in records:
        category = classifier(record)
        counts[category][0 if record.round_identity in labeled else 1] += 1
    categories = tuple(category_order) if category_order is not None else tuple(sorted(counts))
    extras = set(counts) - set(categories)
    if extras:
        raise ValueError(f"{name} produced unsupported categories")
    total_labeled = len(labeled)
    total_missing = len(records) - total_labeled
    rows = tuple(
        ComparabilityRow(
            category=category,
            labeled_count=counts[category][0],
            missing_count=counts[category][1],
            labeled_proportion=(
                CanonicalRational.make(counts[category][0], total_labeled)
                if total_labeled
                else None
            ),
            missing_proportion=(
                CanonicalRational.make(counts[category][1], total_missing)
                if total_missing
                else None
            ),
        )
        for category in categories
        if counts[category][0] or counts[category][1]
    )
    if sum(row.total for row in rows) != len(records):
        raise ValueError(f"{name} comparability table does not reconcile")
    return ComparabilityDimension(name=name, rows=rows)


def missingness_comparability(
    records: Sequence[RankingRecord], labels: Mapping[str, OutcomeLabel]
) -> ComparabilityResult:
    """Construct the exact decision-neutral labeled-versus-missing audit."""

    ranked = tuple(records)
    if not ranked:
        raise ValueError("comparability requires ranked records")
    labeled = set(labels)
    if not labeled.issubset({record.round_identity for record in ranked}):
        raise ValueError("outcome labels contain a non-ranking round")
    fold_by_round: dict[str, str] = {}
    for fold, (start, stop) in enumerate(five_consecutive_folds(len(ranked)), start=1):
        for record in ranked[start:stop]:
            fold_by_round[record.round_identity] = str(fold)
    dimensions = (
        _build_dimension(
            name="chronology_partition",
            records=ranked,
            labeled=labeled,
            classifier=lambda record: fold_by_round[record.round_identity],
            category_order=("1", "2", "3", "4", "5"),
        ),
        _build_dimension(
            name="observation_count",
            records=ranked,
            labeled=labeled,
            classifier=lambda record: str(record.observation_count),
            category_order=tuple(
                str(value) for value in sorted({record.observation_count for record in ranked})
            ),
        ),
        _build_dimension(
            name="significant_gap_count",
            records=ranked,
            labeled=labeled,
            classifier=lambda record: str(record.significant_gap_count),
            category_order=tuple(
                str(value)
                for value in sorted({record.significant_gap_count for record in ranked})
            ),
        ),
        _build_dimension(
            name="max_observation_gap_seconds",
            records=ranked,
            labeled=labeled,
            classifier=lambda record: _exact_float_category(record.max_observation_gap_seconds),
            category_order=tuple(
                _exact_float_category(value)
                for value in sorted({record.max_observation_gap_seconds for record in ranked})
            ),
        ),
        _build_dimension(
            name="significant_gap_threshold_seconds",
            records=ranked,
            labeled=labeled,
            classifier=lambda record: _exact_float_category(
                record.significant_gap_threshold_seconds
            ),
            category_order=tuple(
                _exact_float_category(value)
                for value in sorted(
                    {record.significant_gap_threshold_seconds for record in ranked}
                )
            ),
        ),
        _build_dimension(
            name="decision_distance",
            records=ranked,
            labeled=labeled,
            classifier=_distance_category,
            category_order=("0", "1", "2", "3+"),
        ),
        _build_dimension(
            name="cadence_regime",
            records=ranked,
            labeled=labeled,
            classifier=_cadence_category,
            category_order=("no_significant_gap", "significant_gap_present"),
        ),
        _build_dimension(
            name="lifecycle",
            records=ranked,
            labeled=labeled,
            classifier=lambda record: record.lifecycle_status,
            category_order=("complete", "partial_start", "partial_end", "partial_both"),
        ),
        _build_dimension(
            name="collector_regime",
            records=ranked,
            labeled=labeled,
            classifier=_collector_category,
        ),
        _build_dimension(
            name="collector_session_count",
            records=ranked,
            labeled=labeled,
            classifier=lambda record: str(record.collector_session_count),
            category_order=tuple(
                str(value)
                for value in sorted({record.collector_session_count for record in ranked})
            ),
        ),
    )
    missing_count = len(ranked) - len(labeled)
    if missing_count == 0:
        return ComparabilityResult(
            state="comparable_for_bounded_labeled_inference",
            warning_dimensions=(),
            reasons=("complete_outcome_coverage",),
            dimensions=dimensions,
        )
    reasons: list[str] = []
    unavailable_collector_count = sum(
        not record.collector_session_ids for record in ranked
    )
    thresholds = {record.significant_gap_threshold_seconds for record in ranked}
    collector_dimension = next(item for item in dimensions if item.name == "collector_regime")
    adequate_collector = any(
        row.total >= EXPERIMENT5_ADEQUATE_SUPPORT
        and row.labeled_count >= EXPERIMENT5_ADEQUATE_SUPPORT
        and row.category != "collector_regime_metadata_unavailable"
        for row in collector_dimension.rows
    )
    if not labeled:
        reasons.append("no_valid_labels")
    if unavailable_collector_count >= EXPERIMENT5_ADEQUATE_SUPPORT:
        reasons.append("collector_regime_metadata_unavailable")
    if len(thresholds) != 1:
        reasons.append("heterogeneous_significant_gap_thresholds")
    if not adequate_collector:
        reasons.append("no_label_supported_collector_regime")
    if reasons:
        return ComparabilityResult(
            state="comparability_not_assessable",
            warning_dimensions=(),
            reasons=tuple(sorted(set(reasons))),
            dimensions=dimensions,
        )
    principal_names = {
        "chronology_partition",
        "decision_distance",
        "cadence_regime",
        "lifecycle",
        "collector_regime",
    }
    failures = tuple(
        f"{dimension.name}:{row.category}"
        for dimension in dimensions
        if dimension.name in principal_names
        for row in dimension.rows
        if row.total >= EXPERIMENT5_ADEQUATE_SUPPORT
        and row.labeled_count < EXPERIMENT5_ADEQUATE_SUPPORT
    )
    if failures:
        return ComparabilityResult(
            state="material_comparability_failure",
            warning_dimensions=(),
            reasons=failures,
            dimensions=dimensions,
        )
    warning_dimensions = tuple(
        dimension.name
        for dimension in dimensions
        if any(
            row.labeled_proportion is not None
            and row.missing_proportion is not None
            and row.labeled_proportion != row.missing_proportion
            for row in dimension.rows
        )
    )
    state = (
        "generalization_warning"
        if warning_dimensions
        else "comparable_for_bounded_labeled_inference"
    )
    return ComparabilityResult(
        state=state,
        warning_dimensions=warning_dimensions,
        reasons=(),
        dimensions=dimensions,
    )


def paired_vectors(
    records: Sequence[EvaluationRecord],
) -> dict[str, tuple[float, ...]]:
    return {
        "primary_minus_deployment_per_miner": tuple(
            subtract64(
                record.primary_reciprocal_rank,
                record.deployment_per_miner_reciprocal_rank,
            )
            for record in records
        ),
        "primary_minus_deterministic_baseline": tuple(
            subtract64(
                record.primary_reciprocal_rank,
                record.deterministic_baseline_reciprocal_rank,
            )
            for record in records
        ),
        "primary_minus_seeded_random_baseline": tuple(
            subtract64(
                record.primary_reciprocal_rank,
                record.seeded_random_baseline_reciprocal_rank,
            )
            for record in records
        ),
    }


def _metric_summary(records: Sequence[EvaluationRecord]) -> dict[str, object]:
    procedures = {
        "ascending_sensitivity": (
            "ascending_sensitivity_winner_rank",
            "ascending_sensitivity_reciprocal_rank",
        ),
        "deployment_per_miner": (
            "deployment_per_miner_winner_rank",
            "deployment_per_miner_reciprocal_rank",
        ),
        "deterministic_baseline": (
            "deterministic_baseline_winner_rank",
            "deterministic_baseline_reciprocal_rank",
        ),
        "primary": ("primary_winner_rank", "primary_reciprocal_rank"),
        "seeded_random_baseline": (
            "seeded_random_baseline_winner_rank",
            "seeded_random_baseline_reciprocal_rank",
        ),
    }
    summaries: dict[str, object] = {}
    for name, (rank_field, reciprocal_field) in procedures.items():
        ranks = tuple(float(getattr(record, rank_field)) for record in records)
        reciprocals = tuple(
            float(getattr(record, reciprocal_field)) for record in records
        )
        rank_distribution = Counter(
            str(int(rank)) if rank.is_integer() else str(rank) for rank in ranks
        )
        summaries[name] = {
            "mean_reciprocal_rank": represented_mean(reciprocals) if records else None,
            "mean_winner_rank": represented_mean(ranks) if records else None,
            "median_winner_rank": float(median(ranks)) if records else None,
            "top_1_hit_rate": (
                represented_mean(tuple(float(rank <= 1.0) for rank in ranks))
                if records
                else None
            ),
            "top_3_hit_rate": (
                represented_mean(tuple(float(rank <= 3.0) for rank in ranks))
                if records
                else None
            ),
            "top_5_hit_rate": (
                represented_mean(tuple(float(rank <= 5.0) for rank in ranks))
                if records
                else None
            ),
            "winner_rank_distribution": dict(sorted(rank_distribution.items())),
        }
    vectors = paired_vectors(records) if records else {
        "primary_minus_deployment_per_miner": (),
        "primary_minus_deterministic_baseline": (),
        "primary_minus_seeded_random_baseline": (),
    }
    tie_sizes = tuple(record.primary_tie_group_size for record in records)
    return {
        "evaluation_count": len(records),
        "paired_mrr_differences": {
            name: represented_mean(vector) if vector else None
            for name, vector in vectors.items()
        },
        "procedures": summaries,
        "winning_square_tie_statistics": {
            "tie_group_size_distribution": dict(
                sorted(Counter(str(size) for size in tie_sizes).items())
            ),
            "tied_winner_count": sum(size > 1 for size in tie_sizes),
            "tied_winner_rate": (
                represented_mean(tuple(float(size > 1) for size in tie_sizes))
                if tie_sizes
                else None
            ),
        },
    }


def _evaluation_metric_material(
    records: Sequence[EvaluationRecord],
) -> dict[str, object]:
    primary = tuple(
        record for record in records if record.lifecycle_status == "complete"
    )
    sensitivity = {
        lifecycle: tuple(
            record for record in records if record.lifecycle_status == lifecycle
        )
        for lifecycle in ("partial_start", "partial_end", "partial_both")
    }
    return {
        "complete_lifecycle_primary": _metric_summary(primary),
        "lifecycle_sensitivity": {
            lifecycle: _metric_summary(group)
            for lifecycle, group in sensitivity.items()
        },
    }


def _group_control(
    family: str,
    groups: Mapping[str, Sequence[EvaluationRecord]],
    *,
    zero_is_insufficient: bool,
) -> ControlResult:
    supported = {
        name: tuple(records)
        for name, records in groups.items()
        if len(records) >= EXPERIMENT5_ADEQUATE_SUPPORT
    }
    conflicts = tuple(
        name
        for name, records in sorted(supported.items())
        if not (
            represented_mean(paired_vectors(records)["primary_minus_deterministic_baseline"]) > 0.0
            and represented_mean(paired_vectors(records)["primary_minus_seeded_random_baseline"]) > 0.0
        )
    )
    if conflicts:
        status = "conflict"
    elif not supported and zero_is_insufficient:
        status = "insufficient"
    else:
        status = "pass"
    limitations = (
        (f"homogeneous_{family}",) if len(supported) == 1 else ()
    )
    return ControlResult(
        family=family,
        status=status,
        adequate_groups=len(supported),
        conflicting_groups=conflicts,
        limitations=limitations,
        group_metrics=tuple(
            (name, _metric_summary(records))
            for name, records in sorted(groups.items())
        ),
    )


def _controls(
    rankings: Sequence[RankingRecord],
    primary: Sequence[EvaluationRecord],
    sensitivity: Sequence[EvaluationRecord],
    comparability: ComparabilityResult,
) -> tuple[ControlResult, ...]:
    folds: dict[str, tuple[EvaluationRecord, ...]] = {}
    for index, (start, stop) in enumerate(five_consecutive_folds(len(primary)), start=1):
        folds[str(index)] = tuple(primary[start:stop])
    chronology = _group_control("chronological_folds", folds, zero_is_insufficient=True)
    if len([records for records in folds.values() if len(records) >= 100]) != 5:
        chronology = ControlResult(
            family="chronological_folds",
            status="insufficient",
            adequate_groups=sum(len(records) >= 100 for records in folds.values()),
            conflicting_groups=chronology.conflicting_groups,
            group_metrics=chronology.group_metrics,
        )
    distance_groups: dict[str, list[EvaluationRecord]] = defaultdict(list)
    provenance_groups: dict[str, list[EvaluationRecord]] = defaultdict(list)
    for record in primary:
        category = str(record.decision_distance_slots) if record.decision_distance_slots < 3 else "3+"
        distance_groups[category].append(record)
        provenance_groups[record.provenance].append(record)
    decision_distance = _group_control(
        "decision_distance", distance_groups, zero_is_insufficient=True
    )
    provenance = _group_control(
        "outcome_provenance", provenance_groups, zero_is_insufficient=True
    )
    lifecycle_groups: dict[str, list[EvaluationRecord]] = defaultdict(list)
    for record in sensitivity:
        lifecycle_groups[record.lifecycle_status].append(record)
    lifecycle = _group_control(
        "lifecycle_sensitivity", lifecycle_groups, zero_is_insufficient=False
    )
    if comparability.state in {
        "comparability_not_assessable",
        "material_comparability_failure",
    }:
        missingness = ControlResult(
            family="missingness_comparability",
            status="insufficient",
            adequate_groups=0,
            conflicting_groups=(),
            limitations=(comparability.state,),
        )
    else:
        missingness = ControlResult(
            family="missingness_comparability",
            status="pass",
            adequate_groups=1,
            conflicting_groups=(),
            limitations=(
                ("bounded_labeled_population",)
                if comparability.state == "generalization_warning"
                else ()
            ),
        )
    cadence_groups: dict[str, list[EvaluationRecord]] = defaultdict(list)
    collector_groups: dict[str, list[EvaluationRecord]] = defaultdict(list)
    ranking_by_identity = {record.round_identity: record for record in rankings}
    for record in primary:
        ranking = ranking_by_identity[record.round_identity]
        cadence_groups[_cadence_category(ranking)].append(record)
        collector_groups[_collector_category(ranking)].append(record)
    cadence = _group_control("cadence", cadence_groups, zero_is_insufficient=False)
    collector = _group_control("collector_regime", collector_groups, zero_is_insufficient=False)
    if missingness.status == "pass" and (
        cadence.status == "conflict" or collector.status == "conflict"
    ):
        conflicts = tuple(
            f"{control.family}:{item}"
            for control in (cadence, collector)
            for item in control.conflicting_groups
        )
        missingness = ControlResult(
            family="missingness_comparability",
            status="conflict",
            adequate_groups=cadence.adequate_groups + collector.adequate_groups,
            conflicting_groups=conflicts,
            limitations=missingness.limitations,
        )
    return (
        chronology,
        decision_distance,
        lifecycle,
        provenance,
        cadence,
        collector,
        missingness,
    )


@lru_cache(maxsize=16)
def _construct_bootstrap_cached(
    ordered_round_identities: tuple[str, ...],
    ordered_evaluation_record_identities: tuple[str, ...],
    primary_minus_deployment_per_miner: tuple[float, ...],
    primary_minus_deterministic_baseline: tuple[float, ...],
    primary_minus_seeded_random_baseline: tuple[float, ...],
) -> BootstrapResult:
    return construct_bootstrap(
        ordered_round_identities=ordered_round_identities,
        ordered_evaluation_record_identities=ordered_evaluation_record_identities,
        primary_minus_deployment_per_miner=primary_minus_deployment_per_miner,
        primary_minus_deterministic_baseline=primary_minus_deterministic_baseline,
        primary_minus_seeded_random_baseline=primary_minus_seeded_random_baseline,
    )


def _reconstruct_evaluation_components(
    ranking_artifact: RankingArtifact,
    evaluation_records: Sequence[EvaluationRecord],
    outcome_source_identity: str,
) -> dict[str, object]:
    """Reconstruct every conclusion from accepted ranking and joined records."""

    require_sha256("outcome_source_identity", outcome_source_identity)
    records = tuple(evaluation_records)
    ranking_by_round = {
        record.round_identity: record for record in ranking_artifact.records
    }
    supplied_order = tuple(record.round_identity for record in records)
    if len(supplied_order) != len(set(supplied_order)):
        raise ValueError("evaluation records contain duplicate rounds")
    if not set(supplied_order).issubset(ranking_by_round):
        raise ValueError("evaluation record is outside ranking population")
    expected_order = tuple(
        record.round_identity
        for record in ranking_artifact.records
        if record.round_identity in set(supplied_order)
    )
    if supplied_order != expected_order:
        raise ValueError("evaluation records are not in canonical ranking order")
    labels: dict[str, OutcomeLabel] = {}
    for record in records:
        label = OutcomeLabel(
            round_identity=record.round_identity,
            winning_square=record.winning_square,
            provenance=record.provenance,
            outcome_source_identity=outcome_source_identity,
        )
        expected_record = _join_one(ranking_by_round[record.round_identity], label)
        if expected_record.to_material() != record.to_material():
            raise ValueError("evaluation record does not reconstruct from ranking")
        labels[record.round_identity] = label
    missing = tuple(
        record.round_identity
        for record in ranking_artifact.records
        if record.round_identity not in labels
    )
    if ranking_artifact.records:
        comparability = missingness_comparability(ranking_artifact.records, labels)
    else:
        comparability = ComparabilityResult(
            state="comparability_not_assessable",
            warning_dimensions=(),
            reasons=("no_ranked_rounds",),
            dimensions=(),
        )
    primary = tuple(record for record in records if record.lifecycle_status == "complete")
    sensitivity = tuple(record for record in records if record.lifecycle_status != "complete")
    controls = _controls(
        ranking_artifact.records, primary, sensitivity, comparability
    )
    insufficiency: list[str] = []
    bootstrap: BootstrapResult | None = None
    aggregate_primary_passes = False
    if len(primary) < 500:
        insufficiency.append("fewer_than_five_adequate_primary_folds")
    if primary:
        vectors = paired_vectors(primary)
        bootstrap = _construct_bootstrap_cached(
            tuple(record.round_identity for record in primary),
            tuple(record.evaluation_record_identity for record in primary),
            vectors["primary_minus_deployment_per_miner"],
            vectors["primary_minus_deterministic_baseline"],
            vectors["primary_minus_seeded_random_baseline"],
        )
        comparison_by_name = dict(bootstrap.comparisons)
        aggregate_primary_passes = all(
            represented_mean(vectors[name]) > 0.0
            and comparison_by_name[name].lower_bound > 0.0
            for name in (
                "primary_minus_deterministic_baseline",
                "primary_minus_seeded_random_baseline",
            )
        )
    else:
        insufficiency.append("no_primary_labeled_rounds")
    primary_disposition, primary_reasons = resolve_primary_disposition(
        invalid_reasons=(),
        insufficient_reasons=insufficiency,
        aggregate_primary_passes=aggregate_primary_passes,
        controls=controls,
    )
    secondary = (
        dict(bootstrap.comparisons)["primary_minus_deployment_per_miner"]
        if bootstrap is not None
        else None
    )
    incremental = resolve_incremental_disposition(
        primary_disposition=primary_disposition,
        paired_evidence_sufficient=bootstrap is not None and len(primary) >= 500,
        paired_lower_bound=secondary.lower_bound if secondary is not None else None,
    )
    return {
        "bootstrap": bootstrap,
        "comparability": comparability,
        "confirmation_required": (
            primary_disposition == "provisional_support_for_confirmation"
        ),
        "controls": controls,
        "incremental_disposition": incremental,
        "missing_round_identities": missing,
        "primary_disposition": primary_disposition,
        "primary_reasons": primary_reasons,
    }


def _evaluation_components_equal(
    supplied: Mapping[str, object], expected: Mapping[str, object]
) -> bool:
    def materialize(value: object) -> object:
        if isinstance(value, (BootstrapResult, ComparabilityResult, ControlResult)):
            return value.to_material()
        if isinstance(value, tuple):
            return tuple(materialize(item) for item in value)
        return value

    return canonical_encode(
        {name: materialize(value) for name, value in supplied.items()}
    ) == canonical_encode(
        {name: materialize(value) for name, value in expected.items()}
    )


def resolve_primary_disposition(
    *,
    invalid_reasons: Sequence[str],
    insufficient_reasons: Sequence[str],
    aggregate_primary_passes: bool,
    controls: Sequence[ControlResult],
) -> tuple[str, tuple[str, ...]]:
    """Apply the frozen invalid/insufficient/null/provisional precedence."""

    invalid = tuple(sorted(set(invalid_reasons)))
    if invalid:
        return "invalid_execution", invalid
    insufficient = set(insufficient_reasons)
    insufficient.update(
        f"{control.family}:insufficient"
        for control in controls
        if control.status == "insufficient"
    )
    if insufficient:
        return "evidence_insufficient", tuple(sorted(insufficient))
    conflicts = tuple(
        f"{control.family}:{item}"
        for control in controls
        if control.status == "conflict"
        for item in (control.conflicting_groups or ("conflict",))
    )
    if not aggregate_primary_passes or conflicts:
        reasons = conflicts or ("aggregate_primary_criteria_failed",)
        return "null_not_rejected", tuple(sorted(reasons))
    return "provisional_support_for_confirmation", ()


def _invalid_evaluation_report(
    ranking_artifact: RankingArtifact,
    authorization: EvaluationAuthorizationBinding,
    reasons: Sequence[str],
) -> InvalidExecutionArtifact:
    """Represent governed input/authority failures without laundering bugs."""

    return InvalidExecutionArtifact(
        failed_input_sha256=hashlib.sha256(
            ranking_artifact.canonical_bytes()
        ).hexdigest(),
        authorization_identity=authorization.authorization_identity,
        outcome_source_identity=authorization.outcome_source_identity,
        reasons=tuple(sorted(set(reasons))),
    )


def resolve_incremental_disposition(
    *,
    primary_disposition: str,
    paired_evidence_sufficient: bool,
    paired_lower_bound: float | None,
) -> str | None:
    """Resolve paired evidence independently, then apply the fixed primary gate."""

    if primary_disposition not in PRIMARY_DISPOSITIONS:
        raise ValueError("primary disposition is invalid")
    if primary_disposition == "invalid_execution":
        return None
    if not paired_evidence_sufficient:
        return "paired_comparison_insufficient"
    if paired_lower_bound is None:
        raise ValueError("adequate paired evidence requires a lower bound")
    return (
        "paired_improvement_supported"
        if primary_disposition == "provisional_support_for_confirmation"
        and paired_lower_bound > 0.0
        else "paired_improvement_not_established"
    )


def evaluate_canonical_ranking_artifact(
    ranking_artifact_bytes: bytes,
    labels: Sequence[OutcomeLabel],
    authorization: EvaluationAuthorizationBinding,
) -> EvaluationReport | InvalidExecutionArtifact:
    """Parse the governed ranking boundary before entering scientific evaluation."""

    if not isinstance(ranking_artifact_bytes, bytes):
        raise TypeError("ranking_artifact_bytes must be bytes")
    try:
        artifact = RankingArtifact.from_canonical_bytes(ranking_artifact_bytes)
    except (TypeError, ValueError):
        return InvalidExecutionArtifact(
            failed_input_sha256=hashlib.sha256(ranking_artifact_bytes).hexdigest(),
            authorization_identity=authorization.authorization_identity,
            outcome_source_identity=authorization.outcome_source_identity,
            reasons=("malformed_or_nonconforming_ranking_authority",),
        )
    return evaluate_rankings(artifact, labels, authorization)


def evaluate_rankings(
    ranking_artifact: RankingArtifact,
    labels: Sequence[OutcomeLabel],
    authorization: EvaluationAuthorizationBinding,
) -> EvaluationReport | InvalidExecutionArtifact:
    """Evaluate one frozen ranking artifact after an external authorization binding."""

    if authorization.ranking_artifact_identity != ranking_artifact.ranking_artifact_identity:
        return _invalid_evaluation_report(
            ranking_artifact, authorization, ("authorization_ranking_binding_mismatch",)
        )
    label_by_round: dict[str, OutcomeLabel] = {}
    for label in labels:
        if label.round_identity in label_by_round:
            return _invalid_evaluation_report(
                ranking_artifact, authorization, ("duplicate_outcome_label",)
            )
        if label.outcome_source_identity != authorization.outcome_source_identity:
            return _invalid_evaluation_report(
                ranking_artifact, authorization, ("outcome_source_binding_mismatch",)
            )
        label_by_round[label.round_identity] = label
    ranked_identities = {record.round_identity for record in ranking_artifact.records}
    if not set(label_by_round).issubset(ranked_identities):
        return _invalid_evaluation_report(
            ranking_artifact, authorization, ("label_outside_ranking_population",)
        )
    evaluations = tuple(
        _join_one(record, label_by_round[record.round_identity])
        for record in ranking_artifact.records
        if record.round_identity in label_by_round
    )
    components = _reconstruct_evaluation_components(
        ranking_artifact, evaluations, authorization.outcome_source_identity
    )
    return EvaluationReport(
        ranking_artifact=ranking_artifact,
        authorization=authorization,
        evaluation_records=evaluations,
        missing_round_identities=components["missing_round_identities"],
        comparability=components["comparability"],
        bootstrap=components["bootstrap"],
        controls=components["controls"],
        primary_disposition=components["primary_disposition"],
        primary_reasons=components["primary_reasons"],
        incremental_disposition=components["incremental_disposition"],
        confirmation_required=components["confirmation_required"],
    )


__all__ = (
    "COMPARABILITY_STATES",
    "INCREMENTAL_DISPOSITIONS",
    "PRIMARY_DISPOSITIONS",
    "ComparabilityDimension",
    "ComparabilityResult",
    "ComparabilityRow",
    "ControlResult",
    "EvaluationAuthorizationBinding",
    "EvaluationRecord",
    "EvaluationReport",
    "InvalidExecutionArtifact",
    "OutcomeLabel",
    "evaluate_rankings",
    "evaluate_canonical_ranking_artifact",
    "missingness_comparability",
    "paired_vectors",
    "resolve_primary_disposition",
    "resolve_incremental_disposition",
)
