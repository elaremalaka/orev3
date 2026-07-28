from __future__ import annotations

import hashlib
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from orev3.rfc008.config import RFC008Config
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
    validate_active_release,
)


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
    collection_authorization_valid: bool
    ledger_initialization_authorized: bool
    collector_absent: bool
    gate_reasons: tuple[str, ...]
    ready: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "active_release_validation": (
                self.active_release_validation.as_dict()
            ),
            "lifecycle": self.lifecycle_report,
            "collection_authorization_valid": (
                self.collection_authorization_valid
            ),
            "ledger_initialization_authorized": (
                self.ledger_initialization_authorized
            ),
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
    expected_implementation_commit: str | None = None,
    expected_predecessor_sha256: str | None = None,
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
                expected_implementation_commit=(
                    expected_implementation_commit
                ),
                expected_predecessor_sha256=(
                    expected_predecessor_sha256
                ),
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
    collection_authorization_valid: bool,
    ledger_initialization_authorized: bool,
    collector_running: bool = False,
) -> CollectionPreflightResult:
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
    )
    reasons: list[str] = []
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
    if not collection_authorization_valid:
        reasons.append("separate_collection_authorization_required")
    if not ledger_initialization_authorized:
        reasons.append(
            "production_ledger_initialization_requires_separately_authorized_run"
        )
    if not collector_running:
        reasons.append("collector_absent_by_design")
    blocking = tuple(
        reason
        for reason in reasons
        if reason != "collector_absent_by_design"
    )
    return CollectionPreflightResult(
        active_release_validation=active,
        lifecycle_report=lifecycle,
        collection_authorization_valid=collection_authorization_valid,
        ledger_initialization_authorized=ledger_initialization_authorized,
        collector_absent=not collector_running,
        gate_reasons=tuple(dict.fromkeys(reasons)),
        ready=not blocking and not collector_running,
    )
