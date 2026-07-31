"""Replay integrity and outcome-completeness states for Strategy Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from orev3.dataset.management import DatasetInspection


class ReplayReadiness(str, Enum):
    """Whether a managed dataset can support deterministic experimentation."""

    INVALID = "INVALID"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class ReplayReadinessAssessment:
    """Immutable separation of replay integrity from outcome completeness."""

    readiness: ReplayReadiness
    integrity_valid: bool
    replay_round_count: int
    finalized_outcome_count: int
    skipped_round_count: int
    completeness_percentage: float
    reasons: tuple[str, ...]


def assess_replay_readiness(
    inspection: DatasetInspection,
) -> ReplayReadinessAssessment:
    """Classify one inspected dataset without changing dataset validation."""

    if not isinstance(
        inspection,
        DatasetInspection,
    ):
        raise TypeError(
            "inspection must be a DatasetInspection"
        )

    validation = inspection.validation
    replay_round_count = (
        validation.replay_round_count
    )
    finalized_outcome_count = max(
        replay_round_count
        - validation.missing_outcome_count,
        0,
    )
    reasons = list(
        inspection.metadata_issues
    )

    if not validation.integrity_valid:
        reasons.append(
            "dataset structural integrity is invalid"
        )
    if replay_round_count == 0:
        reasons.append(
            "dataset contains no replay rounds"
        )

    integrity_valid = not reasons

    if not integrity_valid:
        readiness = ReplayReadiness.INVALID
    elif validation.missing_outcome_count:
        readiness = ReplayReadiness.PARTIAL
    else:
        readiness = ReplayReadiness.COMPLETE

    completeness_percentage = (
        0.0
        if replay_round_count == 0
        else (
            finalized_outcome_count
            / replay_round_count
            * 100.0
        )
    )

    return ReplayReadinessAssessment(
        readiness=readiness,
        integrity_valid=integrity_valid,
        replay_round_count=replay_round_count,
        finalized_outcome_count=(
            finalized_outcome_count
        ),
        skipped_round_count=(
            validation.missing_outcome_count
        ),
        completeness_percentage=(
            completeness_percentage
        ),
        reasons=tuple(reasons),
    )


__all__ = (
    "ReplayReadiness",
    "ReplayReadinessAssessment",
    "assess_replay_readiness",
)
