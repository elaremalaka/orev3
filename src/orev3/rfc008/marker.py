from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.migrations import migration_set_hash
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import (
    ExperimentMarker,
    RFC008_BURN_IN_AUDIT_VERSION,
    RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION,
    RFC008_CLI_VERSION,
    RFC008_RUNBOOK_VERSION,
    REQUIRED_PROCESS_COMMAND_IDENTITIES,
    REQUIRED_PROTECTED_PROCESSES,
    ResolverBurnInEvidence,
    RuntimeSourceBoundary,
)
from orev3.rfc008.storage import strict_json


MARKER_AUTHORIZATION = "RFC008_MARKER_CREATION_AUTHORIZED"


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repository_state(root: str | Path) -> dict[str, object]:
    cwd = str(Path(root))
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=cwd, text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=cwd, text=True
    ).strip()
    tracked = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=cwd,
        text=True,
    )
    complete = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=cwd,
        text=True,
    )
    try:
        parent = subprocess.check_output(
            ["git", "rev-parse", "HEAD^"], cwd=cwd, text=True
        ).strip()
    except subprocess.CalledProcessError:
        parent = ""
    return {
        "commit": commit,
        "parent": parent,
        "branch": branch,
        "tracked_clean": not bool(tracked.strip()),
        "untracked_clean": not bool(complete.strip()),
    }


def _last_complete_record(path: Path) -> RuntimeSourceBoundary:
    raw = path.read_bytes()
    if not raw:
        raise ValueError(f"Observer source is empty: {path}")
    complete = raw if raw.endswith(b"\n") else raw[: raw.rfind(b"\n") + 1]
    if not complete:
        raise ValueError(f"Observer source has no complete records: {path}")
    lines = complete.splitlines(keepends=True)
    last = lines[-1]
    payload = last.rstrip(b"\r\n")
    value = json.loads(payload)
    observed = value.get("observed_at_utc")
    round_id = value.get("board", {}).get("round_id")
    if observed is None or round_id is None:
        raise ValueError("Latest source record lacks timestamp or round identity")
    stat = path.stat()
    return RuntimeSourceBoundary(
        source_path=str(path.resolve()),
        source_inode=stat.st_ino,
        source_byte_offset=len(complete),
        source_line_number=len(lines),
        source_record_sha256=hashlib.sha256(payload).hexdigest(),
        source_observed_at=observed,
        round_id=int(round_id),
    )


def derive_runtime_source_boundary(
    source_glob: str,
) -> tuple[RuntimeSourceBoundary, tuple[str, ...]]:
    boundaries = [
        _last_complete_record(Path(name)) for name in sorted(glob.glob(source_glob))
    ]
    if not boundaries:
        raise ValueError("No observer source files match RFC-008 configuration")
    latest = max(
        boundaries,
        key=lambda boundary: (
            boundary.source_observed_at,
            boundary.source_path,
        ),
    )
    identities = tuple(
        "|".join(
            (
                boundary.source_path,
                str(boundary.source_inode),
                str(boundary.source_byte_offset),
                str(boundary.source_line_number),
            )
        )
        for boundary in boundaries
    )
    return latest, identities


def _load_release_approval(path: str | Path) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("artifact_type") != "rfc008_implementation_release_approval":
        raise ValueError("Invalid RFC-008 release approval artifact")
    return value


def marker_preflight(
    *,
    config_path: str | Path,
    resolver_config_path: str | Path,
    burn_in_evidence_path: str | Path,
    release_approval_path: str | Path,
    marker_path: str | Path,
    ledger_path: str | Path,
    approval_manifest_path: str | Path,
    repository_root: str | Path,
    expected_branch: str,
    now: datetime | None = None,
) -> dict[str, object]:
    failures: list[dict[str, str]] = []

    def check(name: str, condition: bool, reason: str) -> bool:
        if not condition:
            failures.append({"check": name, "reason": reason})
        return condition

    current = now or datetime.now(timezone.utc)
    config = RFC008Config.from_path(config_path)
    resolver = ResolverConfig.from_path(resolver_config_path)
    repository = repository_state(repository_root)
    approval_hash = sha256_file(approval_manifest_path)
    release = _load_release_approval(release_approval_path)
    release_hash = sha256_file(release_approval_path)
    burn_path = Path(burn_in_evidence_path)
    burn: ResolverBurnInEvidence | None = None
    if burn_path.exists():
        try:
            raw_burn = json.loads(burn_path.read_text(encoding="utf-8"))
            check(
                "burnin_schema_supported",
                raw_burn.get("schema_version")
                == RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION,
                "Operational burn-in evidence schema version is unsupported",
            )
            check(
                "rpc_counts_missing",
                isinstance(raw_burn.get("real_rpc_request_counts"), dict),
                "Operational burn-in RPC counts are absent",
            )
            check(
                "quarantine_test_missing",
                isinstance(raw_burn.get("quarantine"), dict),
                "Separate quarantine evidence is absent",
            )
            check(
                "conflict_test_missing",
                isinstance(raw_burn.get("conflict"), dict),
                "Separate conflict evidence is absent",
            )
            check(
                "jitter_test_missing",
                isinstance(raw_burn.get("jitter"), dict),
                "Separate jitter evidence is absent",
            )
            check(
                "source_boundary_missing",
                isinstance(raw_burn.get("source_boundary"), dict),
                "Structured source-boundary evidence is absent",
            )
            check(
                "attempt_history_missing",
                isinstance(raw_burn.get("operational_attempts"), list),
                "Operational attempt evidence is absent",
            )
            check(
                "protected_process_evidence_incomplete",
                isinstance(raw_burn.get("protected_processes"), list),
                "Protected-process evidence is absent",
            )
            raw_operational = raw_burn.get("operational")
            raw_rounds = (
                raw_operational.get("rounds", [])
                if isinstance(raw_operational, dict)
                else []
            )
            raw_success_count = (
                raw_operational.get("successful_authoritative_count")
                if isinstance(raw_operational, dict)
                else None
            )
            check(
                "deployment_validation_incomplete",
                bool(raw_rounds)
                and all(
                    isinstance(value, dict)
                    and value.get("deployment_vector_validated") is True
                    for value in raw_rounds
                )
                and raw_operational.get(
                    "deployment_validation_pass_count"
                )
                == raw_success_count,
                "Deployment-vector validation is incomplete",
            )
            check(
                "accounting_validation_incomplete",
                bool(raw_rounds)
                and all(
                    isinstance(value, dict)
                    and value.get("accounting_validated") is True
                    for value in raw_rounds
                )
                and raw_operational.get(
                    "accounting_validation_pass_count"
                )
                == raw_success_count,
                "Accounting validation is incomplete",
            )
            raw_attempts = raw_burn.get("operational_attempts")
            raw_requests = raw_burn.get("operational_requests")
            check(
                "attempt_history_missing",
                isinstance(raw_attempts, list) and bool(raw_attempts),
                "Operational attempt evidence is absent",
            )
            attempts_by_round = (
                {
                    value.get("round_id"): sum(
                        item.get("round_id") == value.get("round_id")
                        for item in raw_attempts
                        if isinstance(item, dict)
                    )
                    for value in raw_rounds
                    if isinstance(value, dict)
                }
                if isinstance(raw_attempts, list)
                else {}
            )
            check(
                "attempt_count_mismatch",
                bool(raw_rounds)
                and all(
                    isinstance(value, dict)
                    and value.get("attempt_count", 0) >= 1
                    and value.get("attempt_count")
                    == attempts_by_round.get(value.get("round_id"), 0)
                    for value in raw_rounds
                ),
                "Operational attempt counts do not match persisted evidence",
            )
            raw_provider_ids = raw_burn.get("provider_ids", [])
            check(
                "provider_request_coverage_incomplete",
                isinstance(raw_requests, list)
                and bool(raw_rounds)
                and all(
                    {
                        request.get("provider_id")
                        for request in raw_requests
                        if isinstance(request, dict)
                        and isinstance(value, dict)
                        and request.get("round_id") == value.get("round_id")
                        and request.get("method")
                        == "get_account_info_with_context"
                        and request.get("classification") == "successful"
                    }
                    == set(raw_provider_ids)
                    for value in raw_rounds
                ),
                "Both providers did not cover every operational round",
            )
            raw_counts = raw_burn.get("real_rpc_request_counts")
            raw_methods = (
                "get_genesis_hash",
                "get_account_info_with_context",
            )
            derived_by_provider = (
                {
                    provider_id: sum(
                        isinstance(value, dict)
                        and value.get("provider_id") == provider_id
                        for value in raw_requests
                    )
                    for provider_id in raw_provider_ids
                }
                if isinstance(raw_requests, list)
                else {}
            )
            derived_by_method = (
                {
                    method: sum(
                        isinstance(value, dict)
                        and value.get("method") == method
                        for value in raw_requests
                    )
                    for method in raw_methods
                }
                if isinstance(raw_requests, list)
                else {}
            )
            derived_by_provider_and_method = (
                {
                    provider_id: {
                        method: sum(
                            isinstance(value, dict)
                            and value.get("provider_id") == provider_id
                            and value.get("method") == method
                            for value in raw_requests
                        )
                        for method in raw_methods
                    }
                    for provider_id in raw_provider_ids
                }
                if isinstance(raw_requests, list)
                else {}
            )
            raw_attempt_links_valid = (
                isinstance(raw_attempts, list)
                and isinstance(raw_requests, list)
                and all(
                    isinstance(attempt, dict)
                    and set(attempt.get("provider_request_ids", []))
                    == {
                        request.get("request_id")
                        for request in raw_requests
                        if isinstance(request, dict)
                        and request.get("attempt_id")
                        == attempt.get("attempt_id")
                    }
                    and all(
                        request.get("retry_request")
                        == (attempt.get("attempt_number", 0) > 1)
                        for request in raw_requests
                        if isinstance(request, dict)
                        and request.get("attempt_id")
                        == attempt.get("attempt_id")
                    )
                    for attempt in raw_attempts
                )
            )
            raw_request_by_id = (
                {
                    value.get("request_id"): value
                    for value in raw_requests
                    if isinstance(value, dict)
                }
                if isinstance(raw_requests, list)
                else {}
            )
            raw_provider_provenance_valid = bool(raw_rounds) and all(
                isinstance(round_value, dict)
                and all(
                    isinstance(provider_value, dict)
                    and (
                        request := raw_request_by_id.get(
                            provider_value.get("request_id")
                        )
                    )
                    is not None
                    and request.get("round_id")
                    == round_value.get("round_id")
                    and request.get("provider_id")
                    == provider_value.get("provider_id")
                    and request.get("method")
                    == provider_value.get("request_method")
                    and request.get("classification") == "successful"
                    and request.get("commitment")
                    == provider_value.get("commitment")
                    and request.get("round_pda")
                    == provider_value.get("returned_account_identity")
                    for provider_value in round_value.get(
                        "provider_evidence", []
                    )
                )
                for round_value in raw_rounds
            )
            raw_rpc_reconciles = (
                isinstance(raw_requests, list)
                and isinstance(raw_counts, dict)
                and raw_counts.get("total") == len(raw_requests)
                and raw_counts.get("by_provider") == derived_by_provider
                and raw_counts.get("by_method") == derived_by_method
                and raw_counts.get("by_provider_and_method")
                == derived_by_provider_and_method
                and raw_counts.get("successful_responses")
                == sum(
                    isinstance(value, dict)
                    and value.get("classification") == "successful"
                    for value in raw_requests
                )
                and raw_counts.get("unavailable_responses")
                == sum(
                    isinstance(value, dict)
                    and value.get("classification") == "unavailable"
                    for value in raw_requests
                )
                and raw_counts.get("malformed_responses")
                == sum(
                    isinstance(value, dict)
                    and value.get("classification") == "malformed"
                    for value in raw_requests
                )
                and raw_counts.get("failed_responses")
                == sum(
                    isinstance(value, dict)
                    and value.get("classification")
                    in {"unavailable", "malformed"}
                    for value in raw_requests
                )
                and raw_counts.get("retried_requests")
                == sum(
                    isinstance(value, dict)
                    and value.get("retry_request") is True
                    for value in raw_requests
                )
                and raw_counts.get("finalized_account_reads")
                == derived_by_method.get(
                    "get_account_info_with_context", 0
                )
                and raw_counts.get("genesis_hash_reads")
                == derived_by_method.get("get_genesis_hash", 0)
                and raw_attempt_links_valid
                and raw_provider_provenance_valid
            )
            check(
                "rpc_attempt_reconciliation_failed",
                raw_burn.get("rpc_attempt_reconciliation_passed") is True
                and raw_burn.get("rpc_attempt_reconciliation_errors") == [],
                "Serialized RPC/attempt reconciliation did not pass",
            )
            check(
                "rpc_attempt_reconciliation_failed",
                raw_rpc_reconciles,
                "RPC requests do not reconcile with persisted attempts",
            )
            check(
                "provider_provenance_invalid",
                raw_provider_provenance_valid,
                "Provider provenance does not reference a matching successful request",
            )
            raw_conflict = raw_burn.get("conflict")
            raw_quarantine = raw_burn.get("quarantine")
            check(
                "conflict_quarantine_identity_collision",
                isinstance(raw_conflict, dict)
                and isinstance(raw_quarantine, dict)
                and raw_conflict.get("round_id")
                != raw_quarantine.get("quarantine_round_id"),
                "Conflict and quarantine rounds collide",
            )
            raw_conflict_required = {
                "round_id",
                "injected_non_authoritative_disagreement",
                "conflict_state",
                "provider_provenance_count",
                "provenance_retained",
                "disagreement_details_retained",
                "terminal_conflict_persisted",
                "overwrite_attempted",
                "overwrite_refused",
                "later_success_replacement_refused",
                "primary_analysis_ineligible",
                "recomputed_conflict_test_passed",
                "conflict_test_passed",
            }
            check(
                "conflict_test_missing",
                isinstance(raw_conflict, dict)
                and raw_conflict_required <= set(raw_conflict),
                "Controlled conflict evidence is incomplete",
            )
            check(
                "conflict_overwrite_refusal_missing",
                isinstance(raw_conflict, dict)
                and "overwrite_refused" in raw_conflict,
                "Conflict overwrite-refusal evidence is absent",
            )
            check(
                "conflict_overwrite_refusal_failed",
                isinstance(raw_conflict, dict)
                and raw_conflict.get("overwrite_refused") is True,
                "Conflict overwrite attempt was not refused",
            )
            raw_conflict_pass = (
                isinstance(raw_conflict, dict)
                and raw_conflict_required <= set(raw_conflict)
                and raw_conflict.get(
                    "injected_non_authoritative_disagreement"
                )
                is True
                and raw_conflict.get("conflict_state") == "conflicted"
                and raw_conflict.get("provider_provenance_count") == 2
                and raw_conflict.get("provenance_retained") is True
                and raw_conflict.get("disagreement_details_retained") is True
                and raw_conflict.get("terminal_conflict_persisted") is True
                and raw_conflict.get("overwrite_attempted") is True
                and raw_conflict.get("overwrite_refused") is True
                and raw_conflict.get(
                    "later_success_replacement_refused"
                )
                is True
                and raw_conflict.get("primary_analysis_ineligible") is True
            )
            check(
                "conflict_pass_state_mismatch",
                isinstance(raw_conflict, dict)
                and raw_conflict.get("recomputed_conflict_test_passed")
                == raw_conflict_pass
                and raw_conflict.get("conflict_test_passed")
                == raw_conflict_pass,
                "Serialized conflict pass state differs from recomputation",
            )
            check(
                "conflict_test_failed",
                raw_conflict_pass,
                "Controlled conflict validation failed",
            )
            raw_quarantine_required = {
                "quarantine_round_id",
                "configured_expiration_seconds",
                "quarantine_initial_state",
                "expiry_reached",
                "production_transition_invoked",
                "quarantine_final_state",
                "quarantine_restart_persistence",
                "overwrite_attempted",
                "quarantine_overwrite_refused",
                "later_success_replacement_refused",
                "primary_analysis_ineligible",
                "recomputed_quarantine_test_passed",
                "quarantine_test_passed",
            }
            check(
                "quarantine_test_missing",
                isinstance(raw_quarantine, dict)
                and raw_quarantine_required <= set(raw_quarantine),
                "Controlled quarantine evidence is incomplete",
            )
            check(
                "quarantine_overwrite_refusal_missing",
                isinstance(raw_quarantine, dict)
                and "quarantine_overwrite_refused" in raw_quarantine,
                "Quarantine overwrite-refusal evidence is absent",
            )
            check(
                "quarantine_overwrite_refusal_failed",
                isinstance(raw_quarantine, dict)
                and raw_quarantine.get("quarantine_overwrite_refused")
                is True,
                "Quarantine overwrite attempt was not refused",
            )
            raw_quarantine_pass = (
                isinstance(raw_quarantine, dict)
                and raw_quarantine_required <= set(raw_quarantine)
                and raw_quarantine.get("quarantine_initial_state")
                == "pending"
                and raw_quarantine.get("expiry_reached") is True
                and raw_quarantine.get("production_transition_invoked")
                is True
                and raw_quarantine.get("quarantine_final_state")
                == "quarantined"
                and raw_quarantine.get("quarantine_restart_persistence")
                is True
                and raw_quarantine.get("overwrite_attempted") is True
                and raw_quarantine.get("quarantine_overwrite_refused")
                is True
                and raw_quarantine.get(
                    "later_success_replacement_refused"
                )
                is True
                and raw_quarantine.get("primary_analysis_ineligible")
                is True
            )
            check(
                "quarantine_pass_state_mismatch",
                isinstance(raw_quarantine, dict)
                and raw_quarantine.get(
                    "recomputed_quarantine_test_passed"
                )
                == raw_quarantine_pass
                and raw_quarantine.get("quarantine_test_passed")
                == raw_quarantine_pass,
                "Serialized quarantine pass state differs from recomputation",
            )
            check(
                "quarantine_test_failed",
                raw_quarantine_pass,
                "Controlled quarantine validation failed",
            )
            raw_restart = raw_burn.get("restart_retry")
            raw_selected = (
                set(raw_operational.get("selected_round_ids", []))
                if isinstance(raw_operational, dict)
                else set()
            )
            raw_controlled_ids = (
                {
                    raw_restart.get("round_id"),
                    raw_conflict.get("round_id"),
                    raw_quarantine.get("quarantine_round_id"),
                }
                if all(
                    isinstance(value, dict)
                    for value in (raw_restart, raw_conflict, raw_quarantine)
                )
                else set()
            )
            check(
                "controlled_round_overlaps_operational_sample",
                bool(raw_controlled_ids)
                and not (raw_controlled_ids & raw_selected),
                "A controlled round overlaps the operational sample",
            )
            raw_jitter = raw_burn.get("jitter")
            check(
                "controlled_evidence_not_independent",
                isinstance(raw_jitter, dict)
                and isinstance(raw_restart, dict)
                and raw_jitter.get("round_id")
                == raw_restart.get("round_id")
                and len(raw_controlled_ids) == 3,
                "Controlled evidence identities are not independent",
            )
            check(
                "jitter_test_failed",
                isinstance(raw_jitter, dict)
                and raw_jitter.get("retry_numbers_tested") == [1, 2, 3]
                and raw_jitter.get("expected_delays_seconds")
                == raw_jitter.get("recomputed_delays_seconds")
                and raw_jitter.get("deterministic_match") is True
                and raw_jitter.get("bounded_delay_result") is True
                and raw_jitter.get("persisted_schedule_match") is True
                and raw_jitter.get("jitter_derivation_version")
                == "rfc008-retry-jitter-v1"
                and raw_jitter.get("recomputed_jitter_test_passed")
                is True
                and raw_jitter.get("jitter_test_passed") is True,
                "Controlled deterministic-jitter validation failed",
            )
            raw_processes = raw_burn.get("protected_processes")
            raw_process_map = (
                {
                    value.get("pid"): value.get("role")
                    for value in raw_processes
                    if isinstance(value, dict)
                }
                if isinstance(raw_processes, list)
                else {}
            )
            check(
                "protected_process_missing",
                raw_process_map == REQUIRED_PROTECTED_PROCESSES,
                "One or more required protected processes are absent",
            )
            check(
                "protected_process_role_missing",
                isinstance(raw_processes, list)
                and {
                    value.get("role")
                    for value in raw_processes
                    if isinstance(value, dict)
                }
                == set(REQUIRED_PROTECTED_PROCESSES.values()),
                "One or more required protected-process roles are absent",
            )
            check(
                "protected_process_evidence_incomplete",
                isinstance(raw_processes, list)
                and len(raw_processes) == 3
                and all(
                    value.get("observed_before") is True
                    and value.get("observed_after") is True
                    and value.get("unchanged") is True
                    for value in raw_processes
                    if isinstance(value, dict)
                ),
                "Protected-process before/after evidence is incomplete",
            )
            check(
                "protected_process_command_changed",
                isinstance(raw_processes, list)
                and len(raw_processes) == 3
                and all(
                    isinstance(value, dict)
                    and value.get("before_command_sha256")
                    == value.get("after_command_sha256")
                    for value in raw_processes
                ),
                "A protected process command changed during burn-in",
            )
            check(
                "protected_process_identity_mismatch",
                isinstance(raw_processes, list)
                and len(raw_processes) == 3
                and all(
                    isinstance(value, dict)
                    and value.get("sanitized_command_identity")
                    == REQUIRED_PROCESS_COMMAND_IDENTITIES.get(
                        str(value.get("role"))
                    )
                    for value in raw_processes
                ),
                "A protected-process command identity is not approved",
            )
            raw_boundary = raw_burn.get("source_boundary")
            required_boundary = {
                "round_id",
                "source_path",
                "inode",
                "byte_offset",
                "line_number",
                "record_sha256",
                "record_timestamp",
                "observed_at",
            }
            check(
                "source_boundary_incomplete",
                isinstance(raw_boundary, dict)
                and required_boundary <= set(raw_boundary),
                "Structured source-boundary evidence is incomplete",
            )
            check(
                "source_boundary_hash_invalid",
                isinstance(raw_boundary, dict)
                and bool(
                    re.fullmatch(
                        r"[0-9a-f]{64}",
                        str(raw_boundary.get("record_sha256", "")),
                    )
                ),
                "Source-boundary record hash is invalid",
            )
            timestamps_valid = False
            if isinstance(raw_boundary, dict):
                try:
                    timestamps = (
                        datetime.fromisoformat(
                            str(raw_boundary["record_timestamp"])
                        ),
                        datetime.fromisoformat(
                            str(raw_boundary["observed_at"])
                        ),
                    )
                    timestamps_valid = all(
                        value.utcoffset() is not None for value in timestamps
                    )
                except (KeyError, TypeError, ValueError):
                    timestamps_valid = False
            check(
                "source_boundary_timestamp_invalid",
                timestamps_valid,
                "Source-boundary timestamps are invalid or timezone-naive",
            )
            boundary_selection_valid = False
            if (
                isinstance(raw_boundary, dict)
                and isinstance(raw_operational, dict)
            ):
                try:
                    boundary_round = int(raw_boundary["round_id"])
                    sample_size = int(
                        raw_operational["requested_sample_size"]
                    )
                    boundary_selection_valid = (
                        raw_operational.get("selection_boundary_round_id")
                        == boundary_round
                        and raw_operational.get("selected_round_ids")
                        == list(
                            range(
                                boundary_round - sample_size,
                                boundary_round,
                            )
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    boundary_selection_valid = False
            check(
                "source_boundary_selection_mismatch",
                boundary_selection_valid,
                "Operational sample differs from the structured source boundary",
            )
            burn = ResolverBurnInEvidence.model_validate(raw_burn)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            failures.append(
                {
                    "check": "burnin_evidence_invalid",
                    "reason": f"Strict burn-in evidence validation failed: {exc}",
                }
            )
    burn_sidecar = Path(str(burn_path) + ".sha256")
    check(
        "approval_manifest_matches",
        approval_hash == config.approval_manifest_sha256,
        "Frozen approval manifest SHA-256 mismatch",
    )
    check(
        "configuration_fingerprint_approved",
        release.get("configuration_fingerprint")
        == config.configuration_fingerprint,
        "Release approval does not bind the experiment configuration",
    )
    check(
        "candidate_hash_approved",
        release.get("candidate_configuration_sha256")
        == config.candidate_configuration_sha256,
        "Release approval does not bind the frozen candidate",
    )
    check(
        "resolver_configuration_approved",
        release.get("resolver_configuration_sha256") == resolver.fingerprint,
        "Release approval does not bind resolver configuration",
    )
    check(
        "migration_set_approved",
        release.get("migration_set_sha256") == migration_set_hash(),
        "Release approval does not bind the migration set",
    )
    check(
        "burnin_schema_approved",
        release.get("burn_in_evidence_schema_version")
        == RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION,
        "Release approval does not bind the burn-in evidence schema",
    )
    check(
        "burnin_audit_approved",
        release.get("audit_version") == RFC008_BURN_IN_AUDIT_VERSION,
        "Release approval does not bind the current adversarial audit",
    )
    check(
        "minimum_operational_sample_approved",
        release.get("minimum_operational_sample_size") == 5,
        "Release approval does not bind the five-round minimum",
    )
    check(
        "protected_process_policy_approved",
        release.get("protected_process_policy")
        == {
            str(pid): {
                "role": role,
                "sanitized_command_identity": (
                    REQUIRED_PROCESS_COMMAND_IDENTITIES[role]
                ),
            }
            for pid, role in REQUIRED_PROTECTED_PROCESSES.items()
        },
        "Release approval does not bind the protected-process policy",
    )
    check(
        "cli_version_approved",
        release.get("cli_version") == RFC008_CLI_VERSION,
        "Release approval does not bind the CLI contract version",
    )
    check(
        "runbook_version_approved",
        release.get("runbook_version") == RFC008_RUNBOOK_VERSION,
        "Release approval does not bind the runbook contract version",
    )
    root = Path(repository_root)
    check(
        "cli_implementation_approved",
        release.get("cli_sha256")
        == sha256_file(root / "src/orev3/rfc008/cli.py"),
        "Release approval does not bind the CLI implementation",
    )
    check(
        "runbook_approved",
        release.get("runbook_sha256")
        == sha256_file(root / "docs/research/RFC-008-OPERATOR-RUNBOOK.md"),
        "Release approval does not bind the operator runbook",
    )
    check(
        "branch_matches",
        repository["branch"] == expected_branch,
        "Repository branch differs from approved branch",
    )
    approved_implementation = str(
        release.get("approved_implementation_commit", "")
    )
    check(
        "head_approved",
        repository["commit"] == approved_implementation
        or repository["parent"] == approved_implementation,
        "HEAD is not the approved implementation or its approval-only child",
    )
    check(
        "tracked_worktree_clean",
        bool(repository["tracked_clean"]),
        "Tracked worktree is dirty",
    )
    check(
        "untracked_worktree_clean",
        bool(repository["untracked_clean"]),
        "Untracked worktree is dirty",
    )
    marker = Path(marker_path)
    ledger = Path(ledger_path)
    artifacts_absent = not any(
        (
            marker.exists(),
            Path(str(marker) + ".sha256").exists(),
            ledger.exists(),
            Path(str(ledger) + "-wal").exists(),
            Path(str(ledger) + "-shm").exists(),
            Path(str(ledger) + ".writer.lock").exists(),
        )
    )
    check(
        "production_artifacts_absent",
        artifacts_absent,
        "Unexpected RFC-008 production runtime artifact exists",
    )
    check("burn_in_exists", burn is not None, "Resolver burn-in evidence is absent")
    sidecar_matches = False
    if burn_path.exists() and burn_sidecar.exists():
        sidecar_matches = (
            burn_sidecar.read_text(encoding="utf-8").split()[0]
            == sha256_file(burn_path)
        )
    check(
        "burn_in_hash_matches",
        sidecar_matches,
        "Resolver burn-in checksum is absent or mismatched",
    )
    if burn is not None:
        age = (current - burn.created_at).total_seconds()
        check(
            "burn_in_configuration_matches",
            burn.resolver_configuration_sha256 == resolver.fingerprint
            and burn.experiment_configuration_fingerprint
            == config.configuration_fingerprint,
            "Burn-in evidence configuration mismatch",
        )
        check(
            "resolver_fingerprint_mismatch",
            burn.resolver_configuration_sha256 == resolver.fingerprint,
            "Burn-in resolver fingerprint differs from current configuration",
        )
        check(
            "burn_in_recent",
            0 <= age <= resolver.burn_in_maximum_age_seconds,
            "Burn-in evidence is stale or future-dated",
        )
        check(
            "burnin_evidence_stale",
            0 <= age <= resolver.burn_in_maximum_age_seconds,
            "Burn-in evidence is stale or future-dated",
        )
        check(
            "burnin_release_approval_matches",
            burn.release_implementation_approval_sha256 == release_hash,
            "Burn-in evidence does not bind the current release approval",
        )
        check(
            "burnin_repository_matches",
            burn.repository_commit == repository["commit"]
            and burn.repository_branch == repository["branch"],
            "Burn-in evidence repository identity differs from preflight",
        )
        check(
            "operational_sample_too_small",
            burn.operational.selected_round_count >= 5,
            "Operational burn-in selected fewer than five real rounds",
        )
        check(
            "operational_success_count_too_small",
            burn.operational.successful_authoritative_count >= 5,
            "Operational burn-in has fewer than five authoritative successes",
        )
        check(
            "duplicate_operational_rounds",
            burn.operational.distinct_round_count
            == burn.operational.selected_round_count,
            "Operational burn-in contains duplicate round identities",
        )
        expected_account_reads = (
            burn.operational.selected_round_count * len(burn.provider_ids)
        )
        rpc_counts_present = (
            burn.real_rpc_request_counts.total > 0
            and burn.real_rpc_request_counts.genesis_hash_reads
            == len(burn.provider_ids)
        )
        check(
            "rpc_counts_missing",
            rpc_counts_present,
            "Operational burn-in RPC counts are absent",
        )
        check(
            "rpc_counts_inconsistent",
            burn.real_rpc_request_counts.finalized_account_reads
            == expected_account_reads,
            "Operational burn-in RPC counts do not match selected rounds",
        )
        check(
            "quarantine_test_missing",
            burn.quarantine.test_type == "controlled_quarantine",
            "Separate quarantine evidence is absent",
        )
        check(
            "quarantine_test_failed",
            burn.quarantine.recomputed_quarantine_test_passed
            and burn.quarantine.quarantine_test_passed,
            "Controlled quarantine validation failed",
        )
        check(
            "quarantine_overwrite_refusal_failed",
            burn.quarantine.overwrite_attempted
            and burn.quarantine.quarantine_overwrite_refused
            and burn.quarantine.later_success_replacement_refused,
            "Quarantine overwrite attempt was not durably refused",
        )
        check(
            "quarantine_terminal_state_invalid",
            burn.quarantine.quarantine_final_state == "quarantined"
            and burn.quarantine.quarantine_restart_persistence
            and burn.quarantine.primary_analysis_ineligible,
            "Quarantine terminal state did not persist safely",
        )
        check(
            "conflict_test_missing",
            burn.conflict.test_type == "controlled_conflict",
            "Separate conflict evidence is absent",
        )
        check(
            "conflict_test_failed",
            burn.conflict.recomputed_conflict_test_passed
            and burn.conflict.conflict_test_passed,
            "Controlled conflict validation failed",
        )
        check(
            "conflict_overwrite_refusal_failed",
            burn.conflict.overwrite_attempted
            and burn.conflict.overwrite_refused
            and burn.conflict.later_success_replacement_refused,
            "Conflict overwrite attempt was not durably refused",
        )
        check(
            "conflict_terminal_state_invalid",
            burn.conflict.conflict_state == "conflicted"
            and burn.conflict.terminal_conflict_persisted
            and burn.conflict.provider_provenance_count == 2
            and burn.conflict.provenance_retained
            and burn.conflict.disagreement_details_retained
            and burn.conflict.primary_analysis_ineligible,
            "Conflict terminal state or provenance did not persist safely",
        )
        check(
            "restart_test_failed",
            burn.restart_retry.recomputed_restart_test_passed
            and burn.restart_retry.recomputed_retry_test_passed
            and burn.restart_retry.restart_test_passed
            and burn.restart_retry.retry_test_passed,
            "Controlled restart or retry validation failed",
        )
        check(
            "jitter_test_missing",
            burn.jitter.test_type == "controlled_jitter",
            "Separate jitter evidence is absent",
        )
        check(
            "jitter_test_failed",
            burn.jitter.recomputed_jitter_test_passed
            and burn.jitter.jitter_test_passed,
            "Controlled deterministic-jitter validation failed",
        )
        check(
            "provider_agreement_incomplete",
            burn.operational.provider_agreement_count
            == burn.operational.selected_round_count
            and burn.genesis_agreement_passed,
            "Provider agreement is incomplete",
        )
        check(
            "provenance_incomplete",
            burn.operational.complete_provenance_count
            == burn.operational.selected_round_count,
            "Operational provider provenance is incomplete",
        )
        check(
            "deployment_validation_incomplete",
            burn.operational.deployment_validation_pass_count
            == burn.operational.successful_authoritative_count,
            "Deployment-vector validation is incomplete",
        )
        check(
            "accounting_validation_incomplete",
            burn.operational.accounting_validation_pass_count
            == burn.operational.successful_authoritative_count,
            "Accounting validation is incomplete",
        )
        check(
            "attempt_history_missing",
            bool(burn.operational_attempts),
            "Operational attempt evidence is absent",
        )
        check(
            "attempt_count_mismatch",
            all(
                value.attempt_count
                == sum(
                    attempt.round_id == value.round_id
                    for attempt in burn.operational_attempts
                )
                and value.attempt_count >= 1
                for value in burn.operational.rounds
            ),
            "Operational attempt counts do not match persisted evidence",
        )
        check(
            "rpc_attempt_reconciliation_failed",
            burn.rpc_attempt_reconciliation_passed
            and not burn.rpc_attempt_reconciliation_errors,
            "RPC requests do not reconcile with persisted attempts",
        )
        check(
            "provider_request_coverage_incomplete",
            all(
                {
                    request.provider_id
                    for request in burn.operational_requests
                    if request.round_id == value.round_id
                    and request.method == "get_account_info_with_context"
                    and request.classification == "successful"
                }
                == set(burn.provider_ids)
                for value in burn.operational.rounds
            ),
            "Both providers did not cover every operational round",
        )
        controlled_ids = {
            burn.restart_retry.round_id,
            burn.conflict.round_id,
            burn.quarantine.quarantine_round_id,
        }
        check(
            "conflict_quarantine_identity_collision",
            burn.conflict.round_id != burn.quarantine.quarantine_round_id,
            "Conflict and quarantine rounds collide",
        )
        check(
            "controlled_round_overlaps_operational_sample",
            not (
                controlled_ids
                & set(burn.operational.selected_round_ids)
            ),
            "A controlled round overlaps the operational sample",
        )
        check(
            "controlled_evidence_not_independent",
            burn.restart_retry.round_id == burn.jitter.round_id
            and len(controlled_ids) == 3,
            "Controlled evidence identities are not independent",
        )
        process_map = {
            value.pid: value.role for value in burn.protected_processes
        }
        check(
            "protected_process_missing",
            process_map == REQUIRED_PROTECTED_PROCESSES,
            "One or more required protected processes are absent",
        )
        check(
            "protected_process_role_missing",
            {value.role for value in burn.protected_processes}
            == set(REQUIRED_PROTECTED_PROCESSES.values()),
            "One or more required protected-process roles are absent",
        )
        check(
            "protected_process_identity_mismatch",
            len(process_map) == len(burn.protected_processes) == 3
            and all(
                value.sanitized_command_identity
                == REQUIRED_PROCESS_COMMAND_IDENTITIES[value.role]
                for value in burn.protected_processes
            ),
            "Protected-process PID, role, or command identity is invalid",
        )
        check(
            "protected_process_command_changed",
            all(value.unchanged for value in burn.protected_processes),
            "A protected process command changed during burn-in",
        )
        check(
            "protected_process_evidence_incomplete",
            all(
                value.observed_before
                and value.observed_after
                and value.evidence_mode == "operational"
                for value in burn.protected_processes
            ),
            "Protected-process before/after evidence is incomplete",
        )
        expected_selection = tuple(
            range(
                burn.source_boundary.round_id
                - burn.operational.requested_sample_size,
                burn.source_boundary.round_id,
            )
        )
        check(
            "source_boundary_selection_mismatch",
            expected_selection == burn.operational.selected_round_ids,
            "Operational sample differs from the structured source boundary",
        )
        passed = all(
            (
                burn.mode == "operational",
                not burn.fixture_only,
                burn.operational.five_round_criterion_passed,
                burn.primary_authoritative_capable,
                burn.sqlite_integrity == "ok",
                burn.safety_inspection_passed,
                burn.production_artifacts_absent,
                burn.running_processes_preserved,
            )
        )
        check(
            "operational_burn_in_passed",
            passed,
            "A recent passing operational burn-in is required",
        )
    boundary: RuntimeSourceBoundary | None = None
    identities: tuple[str, ...] = ()
    try:
        boundary, identities = derive_runtime_source_boundary(config.source_glob)
    except Exception as exc:
        failures.append(
            {"check": "runtime_source_boundary", "reason": str(exc)}
        )
    return {
        "ready": not failures,
        "failures": failures,
        "experiment_id": config.experiment_id,
        "configuration_fingerprint": config.configuration_fingerprint,
        "resolver_compatible": burn is not None
        and burn.primary_authoritative_capable,
        "burn_in_evidence_sha256": (
            sha256_file(burn_path) if burn_path.exists() else None
        ),
        "release_approval_sha256": release_hash,
        "repository": repository,
        "source_cursor_boundary": (
            boundary.model_dump(mode="json") if boundary else None
        ),
        "source_identities": list(identities),
        "production_artifacts_absent": artifacts_absent,
        "marker_created": False,
    }


def _build_marker(
    *,
    preflight: dict[str, object],
    config: RFC008Config,
    resolver: ResolverConfig,
    approval_manifest_path: str | Path,
    repository_commit: str,
    branch: str,
    created_at: datetime | None,
) -> ExperimentMarker:
    boundary = RuntimeSourceBoundary.model_validate(
        preflight["source_cursor_boundary"]
    )
    return ExperimentMarker(
        experiment_id=config.experiment_id,
        protocol_version=config.protocol_version,
        created_at=created_at or datetime.now(timezone.utc),
        repository_commit=repository_commit,
        branch=branch,
        approval_manifest_path=str(approval_manifest_path),
        approval_manifest_sha256=config.approval_manifest_sha256,
        candidate_configuration_sha256=config.candidate_configuration_sha256,
        configuration_fingerprint=config.configuration_fingerprint,
        latest_preholdout_round_id=boundary.round_id,
        first_eligible_round_id=boundary.round_id + 1,
        source_identities=tuple(preflight["source_identities"]),
        runtime_source_path=boundary.source_path,
        runtime_source_inode=boundary.source_inode,
        runtime_source_byte_offset=boundary.source_byte_offset,
        runtime_source_line_number=boundary.source_line_number,
        runtime_source_record_sha256=boundary.source_record_sha256,
        runtime_source_observed_at=boundary.source_observed_at,
        resolver_configuration_sha256=resolver.fingerprint,
        resolver_burn_in_evidence_sha256=str(
            preflight["burn_in_evidence_sha256"]
        ),
        release_approval_sha256=str(preflight["release_approval_sha256"]),
        start_conditions={
            "minimum_analyzable_rounds": 600,
            "maximum_started_rounds": 632,
            "maximum_calendar_days": 14,
            "collection_requires_separate_authorization": True,
            "paper_only": True,
        },
    )


def _atomic_marker_pair(
    marker: ExperimentMarker,
    marker_path: str | Path,
    *,
    failure_injector: Callable[[str], None] | None = None,
) -> str:
    target = Path(marker_path)
    sidecar = Path(str(target) + ".sha256")
    if target.exists() or sidecar.exists():
        raise FileExistsError("Marker or checksum destination already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (strict_json(marker) + "\n").encode()
    digest = hashlib.sha256(payload).hexdigest()
    sidecar_payload = f"{digest}  {target.name}\n".encode()
    marker_temp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    sidecar_temp = sidecar.with_name(f".{sidecar.name}.{os.getpid()}.tmp")
    sidecar_visible = False
    try:
        for path, content in (
            (marker_temp, payload),
            (sidecar_temp, sidecar_payload),
        ):
            with path.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        ExperimentMarker.model_validate_json(marker_temp.read_text())
        if failure_injector:
            failure_injector("before_publish")
        os.link(sidecar_temp, sidecar)
        sidecar_visible = True
        if failure_injector:
            failure_injector("between_sidecar_and_marker")
        os.link(marker_temp, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        if target.exists():
            target.unlink()
        if sidecar_visible and sidecar.exists():
            sidecar.unlink()
        raise
    finally:
        marker_temp.unlink(missing_ok=True)
        sidecar_temp.unlink(missing_ok=True)
    return digest


def create_marker_pair(
    *,
    config_path: str | Path,
    resolver_config_path: str | Path,
    burn_in_evidence_path: str | Path,
    release_approval_path: str | Path,
    marker_path: str | Path,
    ledger_path: str | Path,
    approval_manifest_path: str | Path,
    repository_root: str | Path,
    expected_branch: str,
    authorization_token: str,
    created_at: datetime | None = None,
    failure_injector: Callable[[str], None] | None = None,
) -> tuple[ExperimentMarker, str]:
    if authorization_token != MARKER_AUTHORIZATION:
        raise PermissionError("Explicit RFC-008 marker authorization is required")
    preflight = marker_preflight(
        config_path=config_path,
        resolver_config_path=resolver_config_path,
        burn_in_evidence_path=burn_in_evidence_path,
        release_approval_path=release_approval_path,
        marker_path=marker_path,
        ledger_path=ledger_path,
        approval_manifest_path=approval_manifest_path,
        repository_root=repository_root,
        expected_branch=expected_branch,
        now=created_at,
    )
    if not preflight["ready"]:
        raise ValueError(f"Marker preflight failed: {preflight['failures']}")
    # Re-derive immediately before publication to reject cursor races.
    config = RFC008Config.from_path(config_path)
    boundary, _ = derive_runtime_source_boundary(config.source_glob)
    if boundary.model_dump(mode="json") != preflight["source_cursor_boundary"]:
        raise ValueError("Runtime source cursor changed after preflight")
    repository = preflight["repository"]
    assert isinstance(repository, dict)
    marker = _build_marker(
        preflight=preflight,
        config=config,
        resolver=ResolverConfig.from_path(resolver_config_path),
        approval_manifest_path=approval_manifest_path,
        repository_commit=str(repository["commit"]),
        branch=str(repository["branch"]),
        created_at=created_at,
    )
    digest = _atomic_marker_pair(
        marker, marker_path, failure_injector=failure_injector
    )
    return marker, digest


def verify_marker(
    marker_path: str | Path,
    config: RFC008Config,
    *,
    expected_sha256: str | None = None,
) -> ExperimentMarker:
    path = Path(marker_path)
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise ValueError("RFC-008 marker SHA-256 mismatch")
    marker = ExperimentMarker.model_validate_json(path.read_text())
    if marker.experiment_id != config.experiment_id:
        raise ValueError("RFC-008 marker experiment mismatch")
    if marker.configuration_fingerprint != config.configuration_fingerprint:
        raise ValueError("RFC-008 marker configuration mismatch")
    if marker.approval_manifest_sha256 != config.approval_manifest_sha256:
        raise ValueError("RFC-008 marker approval mismatch")
    if marker.collection_authorized:
        raise ValueError("Marker must not embed collection authorization")
    if marker.first_eligible_round_id != marker.latest_preholdout_round_id + 1:
        raise ValueError("RFC-008 marker boundary is inconsistent")
    return marker
