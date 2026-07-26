from __future__ import annotations

import glob
import hashlib
import json
import os
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
                raw_burn.get("schema_version") == 2,
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
            burn.quarantine.quarantine_test_passed,
            "Controlled quarantine validation failed",
        )
        check(
            "conflict_test_missing",
            burn.conflict.test_type == "controlled_conflict",
            "Separate conflict evidence is absent",
        )
        check(
            "conflict_test_failed",
            burn.conflict.conflict_test_passed,
            "Controlled conflict validation failed",
        )
        check(
            "restart_test_failed",
            burn.restart_retry.restart_test_passed
            and burn.restart_retry.retry_test_passed
            and burn.restart_retry.deterministic_jitter_test_passed,
            "Controlled restart, retry, or jitter validation failed",
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
