from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from orev3.dataset.management import (
    DatasetInspection,
)
from orev3.dataset.metadata import DatasetMetadata
from orev3.dataset.validation import (
    DatasetValidationIssue,
    DatasetValidationResult,
)
from orev3.strategy_lab import (
    ReplayReadiness,
    assess_replay_readiness,
)


def test_complete_readiness_separates_integrity_and_completeness() -> None:
    assessment = assess_replay_readiness(
        _inspection()
    )

    assert (
        assessment.readiness
        is ReplayReadiness.COMPLETE
    )
    assert assessment.integrity_valid
    assert assessment.finalized_outcome_count == 4
    assert assessment.skipped_round_count == 0
    assert assessment.completeness_percentage == 100.0


def test_partial_readiness_counts_only_missing_outcomes() -> None:
    assessment = assess_replay_readiness(
        _inspection(missing_outcomes=3)
    )

    assert (
        assessment.readiness
        is ReplayReadiness.PARTIAL
    )
    assert assessment.integrity_valid
    assert assessment.finalized_outcome_count == 1
    assert assessment.skipped_round_count == 3
    assert assessment.completeness_percentage == 25.0


def test_validator_integrity_remains_authoritative_for_incomplete_coverage(
) -> None:
    assessment = assess_replay_readiness(
        _inspection(
            incomplete_rounds=1,
        )
    )

    assert (
        assessment.readiness
        is ReplayReadiness.COMPLETE
    )
    assert assessment.integrity_valid
    assert assessment.reasons == ()


def test_metadata_or_structural_integrity_failure_is_invalid() -> None:
    assessment = assess_replay_readiness(
        _inspection(
            integrity_issue=True,
            metadata_issue=True,
        )
    )

    assert (
        assessment.readiness
        is ReplayReadiness.INVALID
    )
    assert not assessment.integrity_valid
    assert assessment.reasons == (
        "metadata mismatch",
        "dataset structural integrity is invalid",
    )


def _inspection(
    *,
    missing_outcomes: int = 0,
    incomplete_rounds: int = 0,
    integrity_issue: bool = False,
    metadata_issue: bool = False,
) -> DatasetInspection:
    replay_rounds = 4
    ready = (
        missing_outcomes == 0
        and incomplete_rounds == 0
    )
    metadata = DatasetMetadata(
        dataset_version="readiness-fixture-v1",
        created_at_utc=datetime(
            2026,
            1,
            1,
            tzinfo=UTC,
        ),
        source_collection=(
            "/tmp/observer.jsonl",
        ),
        malformed_source_record_count=0,
        replay_round_count=replay_rounds,
        snapshot_count=replay_rounds,
        complete_round_count=(
            replay_rounds
            - incomplete_rounds
        ),
        incomplete_round_count=(
            incomplete_rounds
        ),
        missing_outcome_count=(
            missing_outcomes
        ),
        integrity_status="valid",
        ready_for_replay=ready,
        dataset_sha256="0" * 64,
    )
    validation = DatasetValidationResult(
        dataset_path=Path(
            "/tmp/replay.jsonl"
        ),
        replay_round_count=replay_rounds,
        snapshot_count=replay_rounds,
        complete_round_count=(
            replay_rounds
            - incomplete_rounds
        ),
        incomplete_round_count=(
            incomplete_rounds
        ),
        missing_outcome_count=(
            missing_outcomes
        ),
        first_round_identifier=1,
        last_round_identifier=4,
        first_observed_at_utc=(
            "2026-01-01T00:00:00+00:00"
        ),
        last_observed_at_utc=(
            "2026-01-01T00:00:03+00:00"
        ),
        issues=(
            (
                DatasetValidationIssue(
                    code="corrupted_record",
                    message="corrupt",
                ),
            )
            if integrity_issue
            else ()
        ),
    )
    return DatasetInspection(
        metadata=metadata,
        validation=validation,
        metadata_issues=(
            ("metadata mismatch",)
            if metadata_issue
            else ()
        ),
    )
