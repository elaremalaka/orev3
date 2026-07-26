from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.schemas import ExperimentMarker
from orev3.rfc008.storage import strict_json


MARKER_AUTHORIZATION = "RFC008_MARKER_CREATION_AUTHORIZED"


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repository_state(root: str | Path) -> tuple[str, str, bool]:
    cwd = str(Path(root))
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=cwd, text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=cwd, text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=cwd,
        text=True,
    )
    return commit, branch, not bool(status.strip())


def marker_preflight(
    *,
    config_path: str | Path,
    marker_path: str | Path,
    approval_manifest_path: str | Path,
    repository_root: str | Path,
    expected_branch: str,
) -> dict[str, object]:
    config = RFC008Config.from_path(config_path)
    marker = Path(marker_path)
    approval = Path(approval_manifest_path)
    commit, branch, clean = repository_state(repository_root)
    approval_hash = sha256_file(approval)
    checks = {
        "configuration_valid": True,
        "approval_manifest_exists": approval.exists(),
        "approval_manifest_matches": approval_hash
        == config.approval_manifest_sha256,
        "marker_path_available": not marker.exists(),
        "marker_hash_path_available": not Path(str(marker) + ".sha256").exists(),
        "branch_matches": branch == expected_branch,
        "tracked_worktree_clean": clean,
        "paper_only": True,
        "rpc_recovery_disabled": not config.allow_rpc_outcome_recovery,
        "no_live_actions_reachable": True,
    }
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "experiment_id": config.experiment_id,
        "configuration_fingerprint": config.configuration_fingerprint,
        "repository_commit": commit,
        "branch": branch,
        "marker_path": str(marker),
        "marker_created": False,
    }


def create_marker(
    *,
    config_path: str | Path,
    marker_path: str | Path,
    approval_manifest_path: str | Path,
    repository_root: str | Path,
    expected_branch: str,
    latest_preholdout_round_id: int,
    source_identities: tuple[str, ...],
    authorization_token: str,
    created_at: datetime | None = None,
) -> ExperimentMarker:
    if authorization_token != MARKER_AUTHORIZATION:
        raise PermissionError("Explicit RFC-008 marker authorization is required")
    preflight = marker_preflight(
        config_path=config_path,
        marker_path=marker_path,
        approval_manifest_path=approval_manifest_path,
        repository_root=repository_root,
        expected_branch=expected_branch,
    )
    if not preflight["ready"]:
        raise ValueError(f"Marker preflight failed: {preflight['checks']}")
    config = RFC008Config.from_path(config_path)
    value = ExperimentMarker(
        experiment_id=config.experiment_id,
        protocol_version=config.protocol_version,
        created_at=created_at or datetime.now(timezone.utc),
        repository_commit=str(preflight["repository_commit"]),
        branch=str(preflight["branch"]),
        approval_manifest_path=str(approval_manifest_path),
        approval_manifest_sha256=config.approval_manifest_sha256,
        candidate_configuration_sha256=config.candidate_configuration_sha256,
        configuration_fingerprint=config.configuration_fingerprint,
        latest_preholdout_round_id=latest_preholdout_round_id,
        first_eligible_round_id=latest_preholdout_round_id + 1,
        source_identities=source_identities,
        start_conditions={
            "minimum_analyzable_rounds": 600,
            "maximum_started_rounds": 632,
            "maximum_calendar_days": 14,
            "collection_requires_separate_authorization": True,
            "paper_only": True,
        },
    )
    target = Path(marker_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (strict_json(value) + "\n").encode()
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    return value


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
    return marker
