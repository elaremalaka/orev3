from __future__ import annotations

from datetime import datetime, timezone

from orev3.collection.schemas import CollectorRunEvidence, CursorCheckpoint


PROOF_COMPLETE = "restart_proof_complete"
TERMINAL_FAILURES = {
    "cursor_regression_detected",
    "duplicate_source_records_detected",
    "duplicate_opportunities_detected",
    "duplicate_decisions_detected",
    "source_corruption_detected",
    "database_lock_failure_detected",
    "run_identity_reused",
    "configuration_changed_since_prior_run",
    "writer_lease_not_exclusive",
    "live_action_detected",
    "skipped_record_detected",
}


def cursor_map(
    checkpoints: list[CursorCheckpoint],
) -> dict[str, CursorCheckpoint]:
    return {item.source_id: item for item in checkpoints}


def same_checkpoint(
    left: list[CursorCheckpoint],
    right: list[CursorCheckpoint],
) -> bool:
    return [
        item.model_dump(mode="json")
        for item in sorted(left, key=lambda value: value.source_id)
    ] == [
        item.model_dump(mode="json")
        for item in sorted(right, key=lambda value: value.source_id)
    ]


def assess_restart_proof(
    run: CollectorRunEvidence,
    prior: CollectorRunEvidence | None,
    *,
    validated_at: datetime | None = None,
) -> CollectorRunEvidence:
    reason = _failure_reason(run, prior)
    status = "proven" if reason == PROOF_COMPLETE else (
        "failed" if reason in TERMINAL_FAILURES else "pending"
    )
    return run.model_copy(
        update={
            "validation_status": status,
            "validation_timestamp": validated_at or datetime.now(timezone.utc),
            "failure_reason": None if status == "proven" else reason,
        }
    )


def _failure_reason(
    run: CollectorRunEvidence,
    prior: CollectorRunEvidence | None,
) -> str:
    if (
        run.validation_status == "failed"
        and run.failure_reason in TERMINAL_FAILURES
    ):
        return run.failure_reason
    if prior is None:
        return "no_prior_run_exists"
    if run.run_id == prior.run_id:
        return "run_identity_reused"
    if run.configuration_hash != prior.configuration_hash:
        return "configuration_changed_since_prior_run"
    if not prior.latest_cursors:
        return "prior_run_had_no_durable_cursor"
    if not run.lease_exclusive:
        return "writer_lease_not_exclusive"
    if (
        not run.resumed_from_checkpoint
        or not same_checkpoint(run.starting_cursors, prior.latest_cursors)
    ):
        return "current_run_did_not_resume_from_prior_cursor"

    starting = cursor_map(run.starting_cursors)
    latest = cursor_map(run.latest_cursors)
    for source_id, checkpoint in starting.items():
        current = latest.get(source_id)
        if (
            current is None
            or current.source_inode != checkpoint.source_inode
            or current.byte_offset < checkpoint.byte_offset
            or current.line_number < checkpoint.line_number
        ):
            return "cursor_regression_detected"

    if run.latest_counters.get("source_records_duplicate", 0):
        return "duplicate_source_records_detected"
    if run.latest_counters.get("duplicate_opportunities", 0):
        return "duplicate_opportunities_detected"
    if run.latest_counters.get("duplicate_decisions", 0):
        return "duplicate_decisions_detected"
    if run.latest_counters.get("source_corruption", 0):
        return "source_corruption_detected"
    if run.latest_counters.get("database_lock_failures", 0):
        return "database_lock_failure_detected"
    if run.latest_counters.get("live_actions", 0):
        return "live_action_detected"

    if run.first_post_resume_record_id is None:
        return "no_post_resume_record_imported"
    first_source = starting.get(run.first_post_resume_source_id or "")
    if first_source is None:
        first_is_new_source = (
            run.first_post_resume_line_number == 1
            and run.first_post_resume_start_offset == 0
        )
        if not first_is_new_source:
            return "skipped_record_detected"
    elif (
        run.first_post_resume_line_number != first_source.line_number + 1
        or run.first_post_resume_start_offset != first_source.byte_offset
    ):
        return "skipped_record_detected"
    if run.latest_source_records <= run.starting_source_records:
        return "no_post_resume_record_imported"
    return PROOF_COMPLETE
