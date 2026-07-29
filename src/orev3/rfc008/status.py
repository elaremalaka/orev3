from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from orev3.rfc008.authorization import CollectionAuthorizationStore
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.marker import verify_marker
from orev3.rfc008.storage import RFC008Store
from orev3.rfc008.storage import SCHEMA_VERSION
from orev3.rfc008.supervision import (
    process_matches_metadata,
    process_snapshot,
    read_metadata,
    supervision_paths,
    writer_lease_status,
)


def active_identity_agrees(
    *,
    supervision: dict[str, object] | None,
    process: dict[str, object],
    lease: dict[str, object],
    open_run: object | None,
    authorization: object,
    contract: object,
    runtime_log_path: Path,
) -> bool:
    if supervision is None or open_run is None:
        return False
    return bool(
        supervision["collector_pid"] == process["pid"]
        and supervision["collector_process_start_identity"]
        == process["start_identity"]
        and supervision["authorization_identifier"]
        == authorization.record.authorization_identifier
        and supervision["authorization_digest"]
        == authorization.record.authorization_digest
        and supervision["ledger_instance_identifier"]
        == contract.ledger_instance_identifier
        and supervision["session_identity"] == contract.active_session_identity
        and str(open_run["run_id"]) == contract.active_session_identity
        and int(open_run["process_id"]) == process["pid"]
        and lease["recorded_process_id"] == process["pid"]
        and lease["recorded_process_start_identity"] == process["start_identity"]
        and supervision["branch"] == authorization.record.repository_branch
        and supervision["head"] == authorization.record.repository_head
        and supervision["target_count"] == contract.collection_target
        and Path(str(supervision["log_path"])).resolve()
        == runtime_log_path.resolve()
    )


def status_report(
    *,
    ledger_path: str | Path,
    config_path: str | Path,
    marker_path: str | Path,
    authorization_path: str | Path,
    authorization_binding_valid: bool,
    authorization_release_mismatches: tuple[str, ...],
    expected_marker_sha256: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    config = RFC008Config.from_path(config_path)
    marker = verify_marker(
        marker_path, config, expected_sha256=expected_marker_sha256
    )
    runtime_paths = supervision_paths(ledger_path)
    supervision = read_metadata(runtime_paths["metadata"])
    lease = writer_lease_status(ledger_path)
    process = process_snapshot(
        supervision["collector_pid"] if supervision is not None else None
    )
    with (
        CollectionAuthorizationStore(
            authorization_path, read_only=True
        ) as authorization_store,
        RFC008Store(ledger_path, config=config, read_only=True) as store,
    ):
        authorization = authorization_store.status()
        contract = store.validate_collection_contract(
            config=config,
            authorization=authorization.record,
        )
        started = store.count("experiment_rounds")
        primary = store.count(
            "experiment_rounds", "state='finalized_primary'"
        )
        sensitivity = store.count(
            "experiment_rounds", "state='finalized_sensitivity'"
        )
        excluded = store.count("experiment_rounds", "state='excluded'")
        pending = store.count(
            "outcome_queue", "state IN ('pending','resolving')"
        )
        conflicted = store.count("outcome_queue", "state='conflicted'")
        quarantined = store.count("outcome_queue", "state='quarantined'")
        failed = store.count("outcome_queue", "state='failed'")
        unusable = excluded + conflicted + quarantined + failed + sensitivity
        unusable_rate = unusable / started if started else 0.0
        counters = store.counters()
        integrity = store.integrity()
        canonical_count = store.count("decision_snapshots")
        arm_decision_count = store.count("arm_decisions")
        release_epochs = store.release_epochs()
        open_runs = store.connection.execute(
            """
            SELECT run_id,started_at,ended_at,process_id
            FROM collector_runs
            WHERE ended_at IS NULL
            ORDER BY started_at
            """
        ).fetchall()
        latest_run = store.connection.execute(
            """
            SELECT run_id,started_at,ended_at,process_id
            FROM collector_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()
        elapsed_days = (
            (now or datetime.now(timezone.utc)) - marker.created_at
        ).total_seconds() / 86400
        cap_reached = (
            started >= config.criteria.maximum_started_rounds
            or elapsed_days >= config.criteria.maximum_calendar_days
        )
        safety_failures = {
            "database_lock_failures": counters.get("database_lock_failures", 0),
            "skipped_records": counters.get("skipped_records", 0),
            "live_actions": counters.get("live_actions", 0),
            "source_corruption": counters.get("source_corruption", 0),
        }
        no_safety_failure = not any(safety_failures.values())
        process_identity_matches = (
            process_matches_metadata(supervision)
            if supervision is not None
            else False
        )
        open_run = open_runs[0] if len(open_runs) == 1 else None
        active_identity_agreement = active_identity_agrees(
            supervision=supervision,
            process=process,
            lease=lease,
            open_run=open_run,
            authorization=authorization,
            contract=contract,
            runtime_log_path=runtime_paths["log"],
        )
        process_ledger_agree = (
            (
                contract.collection_state == "initialized"
                and contract.active_session_identity is None
                and not lease["active"]
                and not process["alive"]
                and not open_runs
            )
            or (
                contract.collection_state == "active"
                and contract.active_session_identity is not None
                and authorization.lifecycle_state == "active"
                and authorization.consuming_session_identity
                == contract.active_session_identity
                and len(open_runs) == 1
                and process_identity_matches
                and lease["active"]
                and active_identity_agreement
            )
            or (
                contract.completed
                and contract.active_session_identity is None
                and authorization.lifecycle_state == "completed"
                and not open_runs
                and not process["alive"]
                and not lease["active"]
            )
        )
        runtime_seconds = None
        if (
            supervision is not None
            and supervision["collector_start_timestamp"] is not None
        ):
            started_at = datetime.fromisoformat(
                str(supervision["collector_start_timestamp"])
            )
            runtime_seconds = max(
                0.0,
                (
                    (now or datetime.now(timezone.utc)) - started_at
                ).total_seconds(),
            )
        ready = (
            integrity == "ok"
            and no_safety_failure
            and unusable_rate <= config.criteria.maximum_unusable_rate
            and not cap_reached
            and authorization_binding_valid
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "release_validity_required_by_cli": True,
            "experiment_id": config.experiment_id,
            "configuration_fingerprint": config.configuration_fingerprint,
            "marker_verified": True,
            "marker_sha256_verified": expected_marker_sha256 is not None,
            "sqlite_integrity": integrity,
            "started_rounds": started,
            "primary_analyzable_rounds": primary,
            "sensitivity_rounds": sensitivity,
            "excluded_rounds": excluded,
            "pending_outcomes": pending,
            "conflicted_outcomes": conflicted,
            "quarantined_outcomes": quarantined,
            "failed_outcomes": failed,
            "unusable_rounds": unusable,
            "unusable_rate": unusable_rate,
            "duplicate_source_records": counters.get(
                "duplicate_source_records", 0
            ),
            "duplicate_decisions": counters.get("duplicate_decisions", 0),
            "safety": safety_failures,
            "minimum_target_reached": primary
            >= config.criteria.minimum_analyzable_rounds,
            "started_round_cap_reached": started
            >= config.criteria.maximum_started_rounds,
            "calendar_cap_reached": elapsed_days
            >= config.criteria.maximum_calendar_days,
            "collection_complete": contract.completed,
            "collection_target_complete": contract.completed,
            "analysis_minimum_outcomes_reached": primary
            >= config.criteria.minimum_analyzable_rounds,
            "collection_ready": ready,
            "authorization_identifier": (
                authorization.record.authorization_identifier
            ),
            "authorization_state": authorization.lifecycle_state,
            "authorization_binding_valid": authorization_binding_valid,
            "authorization_release_mismatches": list(
                authorization_release_mismatches
            ),
            "active_release_compatible": authorization_binding_valid,
            "ledger_instance_identifier": (
                contract.ledger_instance_identifier
            ),
            "ledger_validation_result": "valid",
            "release_epochs": list(release_epochs),
            "active_release_epoch": (
                release_epochs[-1] if release_epochs else None
            ),
            "collection_state": contract.collection_state,
            "collection_target": contract.collection_target,
            "committed_opportunity_count": (
                contract.committed_opportunity_count
            ),
            "canonical_decision_snapshot_count": canonical_count,
            "arm_decision_count": arm_decision_count,
            "remaining_opportunity_count": (
                contract.remaining_opportunity_count
            ),
            "current_session": contract.active_session_identity,
            "writer_lease": lease,
            "collector_process_status": (
                "active_and_verified"
                if process_identity_matches and process_ledger_agree
                else (
                    "inactive"
                    if not process["alive"]
                    and contract.active_session_identity is None
                    else "inconsistent"
                )
            ),
            "supervision": {
                "metadata_path": str(runtime_paths["metadata"]),
                "metadata_present": supervision is not None,
                "state": (
                    supervision["supervision_state"]
                    if supervision is not None
                    else "absent"
                ),
                "recorded_branch": (
                    supervision["branch"] if supervision is not None else None
                ),
                "recorded_head": (
                    supervision["head"] if supervision is not None else None
                ),
                "collector_pid": (
                    supervision["collector_pid"]
                    if supervision is not None
                    else None
                ),
                "collector_pid_alive": process["alive"],
                "process_identity_matches": process_identity_matches,
                "collector_start_timestamp": (
                    supervision["collector_start_timestamp"]
                    if supervision is not None
                    else None
                ),
                "runtime_seconds": runtime_seconds,
                "log_path": (
                    supervision["log_path"]
                    if supervision is not None
                    else str(runtime_paths["log"])
                ),
                "session_identity": (
                    supervision["session_identity"]
                    if supervision is not None
                    else None
                ),
                "exit_code": (
                    supervision["exit_code"]
                    if supervision is not None
                    else None
                ),
                "failure_reason": (
                    supervision["failure_reason"]
                    if supervision is not None
                    else None
                ),
                "stale_recovery": (
                    supervision["stale_recovery"]
                    if supervision is not None
                    else None
                ),
                "process_and_ledger_agree": process_ledger_agree,
                "cross_source_identity_agreement": active_identity_agreement,
            },
            "collector_runs": {
                "total": int(
                    store.connection.execute(
                        "SELECT COUNT(*) FROM collector_runs"
                    ).fetchone()[0]
                ),
                "open": len(open_runs),
                "latest": (
                    dict(latest_run) if latest_run is not None else None
                ),
            },
            "stopped_automatically_at_target": bool(
                contract.completed
                and contract.committed_opportunity_count
                == contract.collection_target
                and not process["alive"]
                and not lease["active"]
            ),
            "reconciliation_required": bool(
                contract.completed
                and (
                    authorization.lifecycle_state != "completed"
                    or contract.active_session_identity is not None
                )
            ),
            "last_committed_opportunity": (
                contract.last_committed_opportunity_identity
            ),
            "completion_timestamp": contract.completion_timestamp,
            "collection_authorized": authorization.lifecycle_state
            in {"initialized", "active", "completed"},
            "analysis_authorized": False,
            "deployment_authorized": False,
            "paper_only": True,
        }
