"""Non-executing Phase-2 readiness authority composition.

Success is intentionally limited to GIT_AUTHORITY_VALIDATED.  This module has
no attempt allocator, outcome capability, experiment callback, or official
execution entry point.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orev3.execution.canonical import (
    CanonicalControlError,
    normalize_experiment_identifier,
    validate_json_schema_instance,
)
from orev3.execution.git_state import (
    AuthorityDiagnostic,
    GitAuthorityError,
    GitDiagnosticCode,
    GitRepository,
    ReadinessSealDerivation,
    fetch_remote_head,
    derive_readiness_seal,
    validate_record_git_bindings,
)
from orev3.execution.readiness_record import (
    LaunchAuthoritySnapshotV1,
    ReadinessRecordV1,
    RepositoryAuthorityV1,
    build_launch_authority_snapshot,
    canonical_readiness_record_path,
    load_readiness_record_bytes,
    load_repository_authority_bytes,
)


class GitReadinessDisposition(str, Enum):
    READINESS_UNRESOLVED_REMOTE = "READINESS_UNRESOLVED_REMOTE"
    READINESS_AMBIGUOUS = "READINESS_AMBIGUOUS"
    READINESS_INVALID_RECORD = "READINESS_INVALID_RECORD"
    READINESS_ORPHANED = "READINESS_ORPHANED"
    SUPERSEDED = "SUPERSEDED"
    READINESS_STALE = "READINESS_STALE"
    GIT_AUTHORITY_VALIDATED = "GIT_AUTHORITY_VALIDATED"


REMAINING_READINESS_PREDICATES = (
    "detached_hermetic_reconstruction",
    "external_input_snapshot_validation",
    "mandatory_readiness_tests",
    "replay_and_population_reconstruction",
    "profile_specific_capability_validation",
    "allocation_and_control_storage_validation",
    "attempt_output_policy_validation",
)


@dataclass(frozen=True, slots=True)
class GitAuthorityAssessment:
    disposition: GitReadinessDisposition
    diagnostics: tuple[AuthorityDiagnostic, ...]
    remaining_predicates: tuple[str, ...]
    record: ReadinessRecordV1 | None = None
    seal: ReadinessSealDerivation | None = None
    launch_authority_snapshot: LaunchAuthoritySnapshotV1 | None = None

    @property
    def git_authority_validated(self) -> bool:
        return self.disposition == GitReadinessDisposition.GIT_AUTHORITY_VALIDATED


class RemoteHeadRevalidation(str, Enum):
    UNCHANGED = "unchanged"
    RESTART_REQUIRED = "restart_required"


def load_repository_authority(path: str | Path) -> RepositoryAuthorityV1:
    authority_path = Path(path)
    if authority_path.is_symlink():
        raise CanonicalControlError("repository authority configuration cannot be a symlink")
    if not authority_path.is_file():
        raise CanonicalControlError("repository authority configuration is unavailable")
    return load_repository_authority_bytes(authority_path.read_bytes())


def resolve_git_launch_authority(
    repository: GitRepository,
    authority: RepositoryAuthorityV1,
    remote_alias: str,
    experiment_identifier: str,
    *,
    allow_test_file_remote: bool = False,
) -> GitAuthorityAssessment:
    """Resolve only Git/control-object authority from fresh remote state."""

    try:
        identifier = normalize_experiment_identifier(experiment_identifier)
        remote = fetch_remote_head(
            repository,
            authority,
            remote_alias,
            allow_test_file=allow_test_file_remote,
        )
        path = str(canonical_readiness_record_path(identifier))
        try:
            entry = repository.tree_entry(remote.remote_head_commit, path)
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.OBJECT_NOT_FOUND:
                raise CanonicalControlError(
                    "canonical readiness record is absent at remote head"
                ) from exc
            raise
        if entry.object_type != "blob":
            raise CanonicalControlError("canonical readiness record is not a Git blob")
        raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
        record = load_readiness_record_bytes(
            raw, expected_experiment_identifier=identifier
        )
        if record.repository_authority_identifier != authority.repository_authority_identifier:
            raise CanonicalControlError("record repository authority is inconsistent")
        if record.approved_branch_ref != authority.approved_branch_ref:
            raise CanonicalControlError("record approved branch ref is inconsistent")
        try:
            schemas = validate_record_git_bindings(repository, record, authority)
            seal = derive_readiness_seal(
                repository,
                remote_head_commit=remote.remote_head_commit,
                record=record,
                record_blob_identity=entry.object_identity,
            )
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.OBJECT_NOT_FOUND:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISSING,
                    "required governed object cannot be established at S",
                    repository_path=exc.repository_path,
                ) from exc
            raise
        snapshot = build_launch_authority_snapshot(
            repository_authority_identifier=authority.repository_authority_identifier,
            approved_branch_ref=authority.approved_branch_ref,
            remote_head_commit=remote.remote_head_commit,
            canonical_record_path=path,
            readiness_record_blob_identity=entry.object_identity,
            readiness_seal_commit=seal.readiness_seal_commit,
            readiness_identity=record.readiness_identity,
            source_commit=record.source_commit,
            object_format=authority.git_object_format,
        )
        validate_json_schema_instance(
            snapshot.to_mapping(),
            schemas.schema_for("launch-authority-snapshot"),
            schema_registry=schemas.filename_registry(),
        )
        return GitAuthorityAssessment(
            GitReadinessDisposition.GIT_AUTHORITY_VALIDATED,
            (),
            REMAINING_READINESS_PREDICATES,
            record,
            seal,
            snapshot,
        )
    except CanonicalControlError as exc:
        return _failure(
            GitReadinessDisposition.READINESS_INVALID_RECORD,
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            str(exc),
        )
    except GitAuthorityError as exc:
        return _git_failure(exc)


def revalidate_remote_head(
    repository: GitRepository,
    authority: RepositoryAuthorityV1,
    remote_alias: str,
    snapshot: LaunchAuthoritySnapshotV1,
    *,
    allow_test_file_remote: bool = False,
) -> RemoteHeadRevalidation:
    """Perform the later phase's second-fetch H comparison without allocation."""

    remote = fetch_remote_head(
        repository,
        authority,
        remote_alias,
        allow_test_file=allow_test_file_remote,
    )
    if remote.remote_head_commit == snapshot.remote_head_commit:
        return RemoteHeadRevalidation.UNCHANGED
    return RemoteHeadRevalidation.RESTART_REQUIRED


def assess_historical_seal(
    current: GitAuthorityAssessment, queried_seal_commit: str
) -> GitReadinessDisposition:
    if not current.git_authority_validated or current.seal is None:
        return current.disposition
    if queried_seal_commit != current.seal.readiness_seal_commit:
        return GitReadinessDisposition.SUPERSEDED
    return GitReadinessDisposition.GIT_AUTHORITY_VALIDATED


def _failure(
    disposition: GitReadinessDisposition,
    code: GitDiagnosticCode,
    message: str,
    *,
    repository_path: str = "",
) -> GitAuthorityAssessment:
    return GitAuthorityAssessment(
        disposition,
        (AuthorityDiagnostic(code, message, repository_path),),
        REMAINING_READINESS_PREDICATES,
    )


def _git_failure(error: GitAuthorityError) -> GitAuthorityAssessment:
    unresolved = {
        GitDiagnosticCode.REMOTE_FETCH_FAILED,
        GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
        GitDiagnosticCode.REMOTE_REF_INVALID,
        GitDiagnosticCode.SHALLOW_HISTORY_INCOMPLETE,
        GitDiagnosticCode.GIT_COMMAND_FAILED,
        GitDiagnosticCode.GIT_COMMAND_TIMEOUT,
        GitDiagnosticCode.GIT_OUTPUT_LIMIT_EXCEEDED,
    }
    ambiguous = {
        GitDiagnosticCode.SEAL_AMBIGUOUS,
        GitDiagnosticCode.SEAL_COMMIT_SHAPE_INVALID,
    }
    invalid = {
        GitDiagnosticCode.OBJECT_NOT_FOUND,
        GitDiagnosticCode.OBJECT_TYPE_INVALID,
        GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
        GitDiagnosticCode.CANONICAL_RECORD_INVALID,
    }
    orphaned = {
        GitDiagnosticCode.SEAL_NOT_FOUND,
        GitDiagnosticCode.FIRST_PARENT_ANCESTRY_INVALID,
        GitDiagnosticCode.GOVERNED_OBJECT_MISSING,
    }
    if error.code in unresolved:
        disposition = GitReadinessDisposition.READINESS_UNRESOLVED_REMOTE
    elif error.code in ambiguous:
        disposition = GitReadinessDisposition.READINESS_AMBIGUOUS
    elif error.code in invalid:
        disposition = GitReadinessDisposition.READINESS_INVALID_RECORD
    elif error.code in orphaned:
        disposition = GitReadinessDisposition.READINESS_ORPHANED
    elif error.code == GitDiagnosticCode.SOURCE_STALE:
        disposition = GitReadinessDisposition.READINESS_STALE
    else:
        disposition = GitReadinessDisposition.READINESS_INVALID_RECORD
    return _failure(
        disposition,
        error.code,
        str(error),
        repository_path=error.repository_path,
    )


__all__ = [
    "GitAuthorityAssessment",
    "GitReadinessDisposition",
    "REMAINING_READINESS_PREDICATES",
    "RemoteHeadRevalidation",
    "assess_historical_seal",
    "load_repository_authority",
    "resolve_git_launch_authority",
    "revalidate_remote_head",
]
