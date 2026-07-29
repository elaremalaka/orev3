from __future__ import annotations

import subprocess
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.authorization import (
    CollectionAuthorizationRecord,
    CollectionAuthorizationStore,
    canonical_path,
)
from orev3.rfc008.marker import (
    HistoricalSourceBoundaryError,
    sha256_file,
    validate_historical_source_boundary,
    verify_marker,
)
from orev3.rfc008.schemas import (
    BurnInSourceBoundary,
    ExperimentMarker,
    ResolverBurnInEvidence,
)
from orev3.rfc008.release_validation import (
    ActiveReleaseValidationResult,
    repository_release_authority,
    validate_active_release,
)
from orev3.rfc008.storage import RFC008Store


@dataclass(frozen=True)
class FileSnapshot:
    exists: bool
    sha256: str | None = None
    inode: int | None = None
    size: int | None = None
    permissions: str | None = None
    created_at: float | None = None
    modified_at: float | None = None


@dataclass(frozen=True)
class MarkerPairSnapshot:
    marker: FileSnapshot
    sidecar: FileSnapshot


@dataclass(frozen=True)
class CollectionPreflightResult:
    active_release_validation: ActiveReleaseValidationResult
    lifecycle_report: dict[str, Any]
    authorization_present: bool
    authorization_valid: bool
    authorization_state: str | None
    ledger_present: bool
    ledger_valid: bool
    collection_completed: bool
    reconciliation_required: bool
    recovery_permitted: bool
    collector_absent: bool
    gate_reasons: tuple[str, ...]
    ready: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "active_release_validation": (
                self.active_release_validation.as_dict()
            ),
            "lifecycle": self.lifecycle_report,
            "authorization_present": self.authorization_present,
            "authorization_valid": self.authorization_valid,
            "authorization_state": self.authorization_state,
            "ledger_present": self.ledger_present,
            "ledger_valid": self.ledger_valid,
            "collection_completed": self.collection_completed,
            "reconciliation_required": self.reconciliation_required,
            "recovery_permitted": self.recovery_permitted,
            "collector_absent": self.collector_absent,
            "gate_reasons": list(self.gate_reasons),
            "ready": self.ready,
        }


def _file_snapshot(path: Path) -> FileSnapshot:
    if not path.exists():
        return FileSnapshot(exists=False)
    metadata = path.stat()
    return FileSnapshot(
        exists=True,
        sha256=sha256_file(path),
        inode=metadata.st_ino,
        size=metadata.st_size,
        permissions=stat.filemode(metadata.st_mode),
        created_at=getattr(metadata, "st_birthtime", metadata.st_ctime),
        modified_at=metadata.st_mtime,
    )


def capture_marker_pair(marker_path: str | Path) -> MarkerPairSnapshot:
    marker = Path(marker_path)
    return MarkerPairSnapshot(
        marker=_file_snapshot(marker),
        sidecar=_file_snapshot(Path(str(marker) + ".sha256")),
    )


def marker_pair_unchanged(
    before: MarkerPairSnapshot,
    after: MarkerPairSnapshot,
) -> bool:
    return before == after


def _failure(
    failures: list[dict[str, str]],
    check: str,
    reason: str,
) -> None:
    failures.append({"check": check, "reason": reason})


def _downstream_paths(root: Path) -> dict[str, tuple[Path, ...]]:
    ledger = root / "data/ledger/rfc008_paper_ledger_v1.sqlite"
    return {
        "production_ledger_family_absent": (
            ledger,
            Path(str(ledger) + "-wal"),
            Path(str(ledger) + "-shm"),
            Path(str(ledger) + ".writer.lock"),
        ),
        "dataset_artifacts_absent": (
            root / "data/analysis/rfc008_dataset_v1",
        ),
        "freeze_artifacts_absent": (
            root / "data/freeze/rfc008_final_freeze_v1.json",
        ),
        "analysis_artifacts_absent": (
            root / "data/analysis/rfc008_results_v1",
        ),
    }


def _check_downstream_absence(
    root: Path,
    failures: list[dict[str, str]],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for check, paths in _downstream_paths(root).items():
        absent = not any(path.exists() for path in paths)
        checks[check] = absent
        if not absent:
            _failure(
                failures,
                check,
                "RFC-008 downstream production artifact exists",
            )
    return checks


def validate_pre_marker_state(
    *,
    repository_root: str | Path,
    collector_running: bool = False,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    marker = root / "data/ledger/rfc008_marker_v1.json"
    sidecar = Path(str(marker) + ".sha256")
    failures: list[dict[str, str]] = []
    if marker.exists():
        _failure(
            failures,
            "pre_marker_marker_absent",
            "Marker exists during a pre-marker lifecycle phase",
        )
    if sidecar.exists():
        _failure(
            failures,
            "pre_marker_sidecar_absent",
            "Marker sidecar exists during a pre-marker lifecycle phase",
        )
    downstream = _check_downstream_absence(root, failures)
    if collector_running:
        _failure(
            failures,
            "collector_absent",
            "RFC-008 collector is running before marker publication",
        )
    return {
        "phase": "pre_marker",
        "ready": not failures,
        "failures": failures,
        "marker_present": marker.exists(),
        "sidecar_present": sidecar.exists(),
        "collector_absent": not collector_running,
        **downstream,
    }


def _read_sidecar(sidecar: Path, marker: Path) -> str:
    raw = sidecar.read_text(encoding="utf-8")
    expected_suffix = f"  {marker.name}\n"
    if not raw.endswith(expected_suffix):
        raise ValueError("Marker sidecar filename or format mismatch")
    digest = raw[: -len(expected_suffix)]
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError("Marker sidecar SHA-256 is invalid")
    return digest


def _historical_boundary_matches(
    marker: ExperimentMarker,
    boundary: BurnInSourceBoundary,
) -> bool:
    return all(
        (
            marker.latest_preholdout_round_id == boundary.round_id,
            marker.first_eligible_round_id == boundary.round_id + 1,
            marker.runtime_source_path == boundary.source_path,
            marker.runtime_source_inode == boundary.inode,
            marker.runtime_source_byte_offset == boundary.byte_offset,
            marker.runtime_source_line_number == boundary.line_number,
            marker.runtime_source_record_sha256 == boundary.record_sha256,
            marker.runtime_source_observed_at == boundary.record_timestamp,
            marker.burn_in_boundary_observed_at == boundary.observed_at,
        )
    )


def _collection_seed_cursors(
    marker: ExperimentMarker,
) -> tuple[dict[str, object], ...]:
    values = []
    for identity in marker.source_identities:
        parts = identity.rsplit("|", 3)
        if len(parts) != 4:
            raise ValueError("Marker publication source identity is invalid")
        path, inode, offset, line = parts
        values.append(
            {
                "source_path": path,
                "source_inode": int(inode),
                "source_byte_offset": int(offset),
                "source_line_number": int(line),
            }
        )
    return tuple(values)


def validate_post_marker_pre_collection_state(
    *,
    repository_root: str | Path,
    config_path: str | Path,
    burn_in_evidence_path: str | Path,
    release_approval_path: str | Path,
    approval_manifest_path: str | Path,
    resolver_config_path: str | Path | None = None,
    collector_running: bool = False,
    expected_snapshot: MarkerPairSnapshot | None = None,
    allow_production_ledger: bool = False,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    marker_path = root / "data/ledger/rfc008_marker_v1.json"
    sidecar_path = Path(str(marker_path) + ".sha256")
    failures: list[dict[str, str]] = []
    marker: ExperimentMarker | None = None
    evidence: ResolverBurnInEvidence | None = None
    marker_sha256: str | None = None
    sidecar_sha256: str | None = None
    historical: dict[str, object] | None = None
    seed_cursors: tuple[dict[str, object], ...] = ()
    release_validation = None

    candidates = tuple(marker_path.parent.glob("rfc008_marker*.json"))
    if candidates != (marker_path,):
        _failure(
            failures,
            "exactly_one_marker_set",
            "Expected exactly one marker at the canonical RFC-008 path",
        )
    if not marker_path.exists() or not sidecar_path.exists():
        _failure(
            failures,
            "complete_marker_pair_present",
            "Marker and checksum sidecar must both exist",
        )
    else:
        try:
            marker_sha256 = sha256_file(marker_path)
            sidecar_sha256 = sha256_file(sidecar_path)
            if _read_sidecar(sidecar_path, marker_path) != marker_sha256:
                raise ValueError("Marker SHA-256 does not match sidecar")
            config = RFC008Config.from_path(config_path)
            marker = verify_marker(
                marker_path,
                config,
                expected_sha256=marker_sha256,
            )
            evidence_path = Path(burn_in_evidence_path)
            if sha256_file(evidence_path) != marker.resolver_burn_in_evidence_sha256:
                raise ValueError("Marker burn-in evidence binding mismatch")
            evidence = ResolverBurnInEvidence.model_validate_json(
                evidence_path.read_text(encoding="utf-8")
            )
            if evidence.resolver_configuration_sha256 != (
                marker.resolver_configuration_sha256
            ):
                raise ValueError("Marker resolver binding mismatch")
            if not _historical_boundary_matches(
                marker,
                evidence.source_boundary,
            ):
                raise ValueError("Historical eligibility boundary mismatch")
            selected = tuple(evidence.operational.selected_round_ids)
            expected_selected = tuple(
                range(
                    evidence.source_boundary.round_id - 5,
                    evidence.source_boundary.round_id,
                )
            )
            if selected != expected_selected:
                raise ValueError("Historical burn-in round selection mismatch")
            validate_historical_source_boundary(
                evidence.source_boundary,
                config.source_glob,
            )
            approval_path = Path(approval_manifest_path)
            if sha256_file(approval_path) != marker.approval_manifest_sha256:
                raise ValueError("Frozen approval manifest binding mismatch")
            release_path = Path(release_approval_path)
            release_validation = validate_active_release(
                repository_root=root,
                config_path=config_path,
                resolver_config_path=(
                    resolver_config_path
                    or root / "config/collection/rfc008_resolver_v1.json"
                ),
                burn_in_evidence_path=evidence_path,
                release_approval_path=release_path,
                approval_manifest_path=approval_path,
                marker_path=marker_path,
            )
            failures.extend(
                {
                    "check": value.check,
                    "reason": value.reason,
                }
                for value in release_validation.checks
                if not value.passed
            )
            if not release_validation.valid:
                _failure(
                    failures,
                    "active_release_validation_valid",
                    "Shared active release validation failed",
                )
            if (
                marker.release_approval_sha256
                not in release_validation.approval_hashes
            ):
                _failure(
                    failures,
                    "marker_binding_valid",
                    "Marker release approval is not in the validated chain",
                )
            seed_cursors = _collection_seed_cursors(marker)
            historical_seeds = tuple(
                value
                for value in seed_cursors
                if value["source_path"] == marker.runtime_source_path
            )
            if len(historical_seeds) != 1:
                raise ValueError(
                    "Historical source lacks one collection seed cursor"
                )
            seed = historical_seeds[0]
            if (
                seed["source_inode"] != marker.runtime_source_inode
                or seed["source_byte_offset"] < marker.runtime_source_byte_offset
                or seed["source_line_number"] < marker.runtime_source_line_number
            ):
                raise ValueError(
                    "Collection seed cursor precedes historical boundary"
                )
            historical = {
                "round_id": marker.latest_preholdout_round_id,
                "source_path": marker.runtime_source_path,
                "source_inode": marker.runtime_source_inode,
                "source_byte_offset": marker.runtime_source_byte_offset,
                "source_line_number": marker.runtime_source_line_number,
                "source_record_sha256": marker.runtime_source_record_sha256,
                "source_observed_at": marker.runtime_source_observed_at.isoformat(),
                "selected_round_ids": list(selected),
            }
        except (
            HistoricalSourceBoundaryError,
            OSError,
            ValueError,
        ) as exc:
            _failure(
                failures,
                "valid_immutable_marker_pair",
                str(exc),
            )

    downstream = _check_downstream_absence(root, failures)
    if allow_production_ledger:
        failures[:] = [
            value
            for value in failures
            if value["check"] != "production_ledger_family_absent"
        ]
    if collector_running:
        _failure(
            failures,
            "collector_absent",
            "RFC-008 collector is running before collection authorization",
        )
    current_snapshot = capture_marker_pair(marker_path)
    if (
        expected_snapshot is not None
        and not marker_pair_unchanged(expected_snapshot, current_snapshot)
    ):
        _failure(
            failures,
            "marker_pair_unchanged",
            "Marker or sidecar changed during the observed operation",
        )
    if marker is not None and marker.collection_authorized:
        _failure(
            failures,
            "collection_authorization_absent",
            "Marker unexpectedly authorizes collection",
        )
    return {
        "phase": "post_marker_pre_collection",
        "ready": not failures,
        "failures": failures,
        "marker_present": marker_path.exists(),
        "sidecar_present": sidecar_path.exists(),
        "marker_sha256": marker_sha256,
        "sidecar_sha256": sidecar_sha256,
        "marker_schema_version": (
            marker.marker_schema_version if marker is not None else None
        ),
        "marker_compatible": marker is not None,
        "collection_authorized": (
            marker.collection_authorized if marker is not None else None
        ),
        "collector_absent": not collector_running,
        "historical_eligibility_boundary": historical,
        "marker_publication_source_cursors": list(seed_cursors),
        "collection_seed_cursors": list(seed_cursors),
        "cursor_identities_required_equal": False,
        "active_release_validation": (
            release_validation.as_dict()
            if release_validation is not None
            else None
        ),
        "active_release_validation_valid": (
            release_validation.valid
            if release_validation is not None
            else False
        ),
        "derived_sources_current": (
            release_validation.derived_field_valid
            if release_validation is not None
            else False
        ),
        "approval_chain_valid": (
            release_validation.approval_chain_valid
            if release_validation is not None
            else False
        ),
        "marker_binding_valid": (
            release_validation.marker_binding_valid
            if release_validation is not None
            else False
        ),
        "post_marker_state_valid": not failures,
        "marker_pair_snapshot": asdict(current_snapshot),
        **downstream,
    }


def validate_production_isolation(
    *,
    repository_root: str | Path,
    config_path: str | Path,
    expected_snapshot: MarkerPairSnapshot,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    marker = root / "data/ledger/rfc008_marker_v1.json"
    sidecar = Path(str(marker) + ".sha256")
    if not marker.exists() and not sidecar.exists():
        report = validate_pre_marker_state(repository_root=root)
        if capture_marker_pair(marker) != expected_snapshot:
            report["ready"] = False
            report["failures"].append(
                {
                    "check": "marker_pair_unchanged",
                    "reason": "Marker pair appeared during operation",
                }
            )
        return report
    return validate_post_marker_pre_collection_state(
        repository_root=root,
        config_path=config_path,
        burn_in_evidence_path=(
            root / "data/resolver/rfc008_operational_burn_in_v1.json"
        ),
        release_approval_path=(
            root
            / "docs/research/rfc008/release_implementation_approval_v1.json"
        ),
        approval_manifest_path=(
            root / "docs/research/rfc008/approval_manifest_v1.json"
        ),
        expected_snapshot=expected_snapshot,
    )


def validate_collection_preflight(
    *,
    repository_root: str | Path,
    config_path: str | Path,
    resolver_config_path: str | Path,
    burn_in_evidence_path: str | Path,
    release_approval_path: str | Path,
    approval_manifest_path: str | Path,
    marker_path: str | Path,
    authorization_path: str | Path,
    ledger_path: str | Path,
    action: str = "launch",
    collector_running: bool = False,
) -> CollectionPreflightResult:
    if action not in {"initialize", "launch", "recovery"}:
        raise ValueError("Unsupported RFC-008 collection preflight action")
    authorization_file = Path(authorization_path)
    ledger_file = Path(ledger_path)
    authorization_present = authorization_file.exists()
    ledger_present = ledger_file.exists()
    active = validate_active_release(
        repository_root=repository_root,
        config_path=config_path,
        resolver_config_path=resolver_config_path,
        burn_in_evidence_path=burn_in_evidence_path,
        release_approval_path=release_approval_path,
        approval_manifest_path=approval_manifest_path,
        marker_path=marker_path,
    )
    lifecycle = validate_post_marker_pre_collection_state(
        repository_root=repository_root,
        config_path=config_path,
        resolver_config_path=resolver_config_path,
        burn_in_evidence_path=burn_in_evidence_path,
        release_approval_path=release_approval_path,
        approval_manifest_path=approval_manifest_path,
        collector_running=collector_running,
        allow_production_ledger=ledger_present,
    )
    reasons: list[str] = []
    from orev3.rfc008.rotation import rotation_status

    if rotation_status(repository_root)["recovery_required"]:
        reasons.append("artifact_rotation_recovery_required")
    canonical_marker = (
        Path(repository_root).resolve()
        / "data/ledger/rfc008_marker_v1.json"
    )
    if Path(marker_path).resolve() != canonical_marker:
        reasons.append("canonical_production_marker_path_required")
    if not active.valid:
        reasons.extend(
            value.check for value in active.checks if not value.passed
        )
    if not lifecycle["ready"]:
        reasons.extend(
            str(value["check"]) for value in lifecycle["failures"]
        )
    authorization_valid = False
    authorization_state: str | None = None
    authorization: CollectionAuthorizationRecord | None = None
    if not authorization_present:
        reasons.append("collection_authorization_absent")
    else:
        try:
            with CollectionAuthorizationStore(
                authorization_file, read_only=True
            ) as authorization_store:
                status = authorization_store.status()
            authorization = status.record
            authorization_state = status.lifecycle_state
            config = RFC008Config.from_path(config_path)
            mismatches = authorization_release_mismatches(
                repository_root=repository_root,
                release_approval_path=release_approval_path,
                ledger_path=ledger_file,
                config=config,
                active_release=active,
                authorization=authorization,
            )
            if mismatches:
                reasons.append(
                    "authorization_release_mismatch:"
                    + ",".join(mismatches)
                )
            elif (
                authorization.collection_target != 600
                or authorization.collection_mode != "paper"
            ):
                reasons.append("authorization_target_or_mode_mismatch")
            else:
                authorization_valid = True
        except (OSError, ValueError, PermissionError, subprocess.CalledProcessError):
            reasons.append("collection_authorization_malformed")

    ledger_valid = False
    collection_completed = False
    if not ledger_present:
        reasons.append("production_ledger_absent")
    elif authorization is None:
        reasons.append("ledger_authorization_unverifiable")
    else:
        try:
            config = RFC008Config.from_path(config_path)
            with RFC008Store(
                ledger_file,
                config=config,
                read_only=True,
            ) as store:
                contract = store.validate_collection_contract(
                    config=config,
                    authorization=authorization,
                )
            ledger_valid = True
            if contract.completed:
                collection_completed = True
                reasons.append("collection_completed")
            if contract.collection_target != 600:
                reasons.append("collection_target_mismatch")
        except (OSError, ValueError):
            reasons.append("ledger_metadata_mismatch")

    allowed_states = {
        "initialize": {"issued", "initialization_consumed"},
        "launch": {"initialized"},
        "recovery": (
            {"active", "completed"}
            if collection_completed
            else {"active"}
        ),
    }
    if authorization_state is not None and (
        authorization_state not in allowed_states[action]
    ):
        reasons.append(
            f"authorization_state_rejected:{authorization_state}"
        )
    if (
        action == "initialize"
        and ledger_present
        and not (
            authorization_state == "initialization_consumed"
            and ledger_valid
        )
    ):
        reasons.append("production_ledger_already_exists")
    if action in {"launch", "recovery"} and not ledger_present:
        reasons.append("production_ledger_required")
    if not collector_running:
        reasons.append("collector_absent_by_design")
    else:
        reasons.append("collector_already_running")
    blocking = tuple(
        reason
        for reason in reasons
        if reason != "collector_absent_by_design"
    )
    if action == "initialize":
        blocking = tuple(
            value
            for value in blocking
            if value != "production_ledger_absent"
        )
    if (
        action == "recovery"
        and collection_completed
        and authorization_state in {"active", "completed"}
    ):
        blocking = tuple(
            value for value in blocking if value != "collection_completed"
        )
    reconciliation_required = (
        collection_completed and authorization_state == "active"
    )
    return CollectionPreflightResult(
        active_release_validation=active,
        lifecycle_report=lifecycle,
        authorization_present=authorization_present,
        authorization_valid=authorization_valid,
        authorization_state=authorization_state,
        ledger_present=ledger_present,
        ledger_valid=ledger_valid,
        collection_completed=collection_completed,
        reconciliation_required=reconciliation_required,
        recovery_permitted=(
            action == "recovery"
            and authorization_state in {"active", "completed"}
            and not collector_running
        ),
        collector_absent=not collector_running,
        gate_reasons=tuple(dict.fromkeys(reasons)),
        ready=not blocking and not collector_running and (
            (action == "initialize" and authorization_valid)
            or (
                action in {"launch", "recovery"}
                and authorization_valid
                and ledger_valid
            )
        ),
    )


def authorization_release_mismatches(
    *,
    repository_root: str | Path,
    release_approval_path: str | Path,
    ledger_path: str | Path,
    config: RFC008Config,
    active_release: Any,
    authorization: CollectionAuthorizationRecord,
) -> tuple[str, ...]:
    """Compare persisted authorization authority with the active Git release."""
    approval = active_release.parsed_active_approval or {}
    authority = repository_release_authority(
        repository_root=Path(repository_root).resolve(),
        release_path=Path(release_approval_path).resolve(),
    )
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(repository_root).resolve(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    expected = {
        "branch": authority.branch,
        "repository_head": head,
        "implementation_commit": authority.implementation_commit,
        "active_approval_sha256": active_release.active_approval_sha256,
        "immediate_predecessor_sha256": (
            authority.predecessor_approval_sha256
        ),
        "approval_chain_anchor": (
            active_release.approval_hashes[-1]
            if active_release.approval_hashes
            else None
        ),
        "marker_sha256": approval.get(
            "validated_production_marker_sha256"
        ),
        "marker_sidecar_sha256": approval.get(
            "validated_production_marker_sidecar_sha256"
        ),
        "candidate_sha256": config.candidate_configuration_sha256,
        "experiment_id": config.experiment_id,
        "configuration_fingerprint": config.configuration_fingerprint,
        "resolver_fingerprint": approval.get(
            "resolver_configuration_sha256"
        ),
        "migration_set_sha256": approval.get("migration_set_sha256"),
        "cli_sha256": approval.get("cli_sha256"),
        "runbook_sha256": approval.get("runbook_sha256"),
        "burn_in_evidence_sha256": approval.get(
            "validated_operational_burn_in_evidence_sha256"
        ),
        "burn_in_ledger_sha256": approval.get(
            "validated_operational_burn_in_ledger_sha256"
        ),
        "approval_manifest_sha256": approval.get(
            "frozen_approval_manifest_sha256"
        ),
        "external_rpc_burn_in_performed": approval.get(
            "verification", {}
        ).get("external_rpc_burn_in_performed"),
        "canonical_ledger_path": canonical_path(ledger_path),
        "collection_target": 600,
        "collection_mode": "paper",
    }
    return tuple(
        name
        for name, expected_value in expected.items()
        if getattr(authorization, name) != expected_value
    )
