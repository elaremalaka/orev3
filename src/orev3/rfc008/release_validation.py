from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from orev3.rfc008.approval import (
    RELEASE_ARTIFACT_TYPE,
    RELEASE_BRANCH,
    RELEASE_RFC_IDENTIFIER,
    RELEASE_SCHEMA_VERSION,
    ReleaseApprovalPolicy,
    registry_authoritative_values,
    validate_release_approval_chain,
)
from orev3.rfc008.approval_contract import (
    SCHEMA2_APPROVAL_FIELDS,
    active_schema2_structure_failures,
    decode_approval_json,
    get_path,
    leaf_paths,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import ExperimentMarker, ResolverBurnInEvidence


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class ReleaseValidationCheck:
    check: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class ActiveReleaseValidationResult:
    parsed_active_approval: Mapping[str, Any] | None
    active_approval_sha256: str | None
    schema_valid: bool
    artifact_identity_valid: bool
    field_contract_valid: bool
    derived_field_valid: bool
    policy_field_valid: bool
    authorization_field_valid: bool
    approval_chain_valid: bool
    marker_binding_valid: bool
    checks: tuple[ReleaseValidationCheck, ...]
    approval_hashes: tuple[str, ...]
    valid: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "parsed_active_approval": (
                _thaw(self.parsed_active_approval)
                if self.parsed_active_approval is not None
                else None
            ),
            "active_approval_sha256": self.active_approval_sha256,
            "schema_valid": self.schema_valid,
            "artifact_identity_valid": self.artifact_identity_valid,
            "field_contract_valid": self.field_contract_valid,
            "derived_field_valid": self.derived_field_valid,
            "policy_field_valid": self.policy_field_valid,
            "authorization_field_valid": self.authorization_field_valid,
            "approval_chain_valid": self.approval_chain_valid,
            "marker_binding_valid": self.marker_binding_valid,
            "checks": [asdict(value) for value in self.checks],
            "reasons": [
                {"check": value.check, "reason": value.reason}
                for value in self.checks
                if not value.passed
            ],
            "approval_hashes": list(self.approval_hashes),
            "valid": self.valid,
        }


@dataclass(frozen=True)
class GitReleaseAuthority:
    branch: str
    approval_commit: str
    implementation_commit: str
    predecessor_approval_sha256: str
    approval_committed_at_head: bool
    approval_commit_is_approval_only: bool


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _git(root: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def repository_release_authority(
    *,
    repository_root: Path,
    release_path: Path,
) -> GitReleaseAuthority:
    head = _git(repository_root, "rev-parse", "HEAD").decode().strip()
    parent = _git(repository_root, "rev-parse", "HEAD^").decode().strip()
    branch = (
        _git(repository_root, "branch", "--show-current").decode().strip()
    )
    changed = {
        value
        for value in _git(
            repository_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
        )
        .decode()
        .splitlines()
        if value
    }
    release_relative = str(release_path.resolve().relative_to(repository_root))
    approval_only = changed == {release_relative}
    committed_release = _git(
        repository_root,
        "show",
        f"{head}:{release_relative}",
    )
    approval_committed_at_head = release_path.read_bytes() == committed_release
    if approval_committed_at_head and not approval_only:
        raise ValueError(
            "Committed active approval must be an approval-only commit"
        )
    if not approval_committed_at_head and approval_only:
        raise ValueError(
            "Pending approval cannot approve an approval-only commit"
        )
    implementation = parent if approval_committed_at_head else head
    previous = _git(
        repository_root,
        "show",
        f"{implementation}:{release_relative}",
    )
    return GitReleaseAuthority(
        branch=branch,
        approval_commit=head,
        implementation_commit=implementation,
        predecessor_approval_sha256=hashlib.sha256(previous).hexdigest(),
        approval_committed_at_head=approval_committed_at_head,
        approval_commit_is_approval_only=approval_only,
    )


def repository_approval_history(
    *,
    repository_root: Path,
    release_path: Path,
) -> dict[str, bytes]:
    relative = str(release_path.resolve().relative_to(repository_root))
    commits = (
        _git(
            repository_root,
            "log",
            "--format=%H",
            "--all",
            "--",
            relative,
        )
        .decode()
        .splitlines()
    )
    documents: dict[str, bytes] = {}
    for commit in commits:
        raw = _git(repository_root, "show", f"{commit}:{relative}")
        documents[hashlib.sha256(raw).hexdigest()] = raw
    return documents


def _semantic_migration_hash(root: Path) -> str:
    source = root / "src/orev3/rfc008/migrations.py"
    if not source.is_file():
        raise ValueError("Canonical RFC-008 migration source is absent")
    command = (
        "from orev3.rfc008.migrations import migration_set_hash;"
        "print(migration_set_hash())"
    )
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        (sys.executable, "-c", command),
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    if len(value) != 64:
        raise ValueError("Canonical RFC-008 migration hash is malformed")
    return value


def _source_matches_implementation(
    root: Path,
    implementation: str,
    relative: str,
) -> bool:
    path = root / relative
    if not path.is_file():
        return False
    try:
        committed = _git(root, "show", f"{implementation}:{relative}")
    except subprocess.CalledProcessError:
        return False
    return path.read_bytes() == committed


def _sidecar_digest(sidecar: Path, marker: Path) -> str:
    raw = sidecar.read_text(encoding="utf-8")
    suffix = f"  {marker.name}\n"
    if not raw.endswith(suffix):
        raise ValueError("Marker sidecar filename or format mismatch")
    value = raw[: -len(suffix)]
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Marker sidecar SHA-256 is invalid")
    return value


def validate_active_release(
    *,
    repository_root: str | Path,
    config_path: str | Path,
    resolver_config_path: str | Path,
    burn_in_evidence_path: str | Path,
    release_approval_path: str | Path,
    approval_manifest_path: str | Path,
    marker_path: str | Path | None = None,
) -> ActiveReleaseValidationResult:
    root = Path(repository_root).resolve()
    release_path = Path(release_approval_path).resolve()
    marker = (
        Path(marker_path).resolve()
        if marker_path is not None
        else root / "data/ledger/rfc008_marker_v1.json"
    )
    sidecar = Path(str(marker) + ".sha256")
    burn_path = Path(burn_in_evidence_path).resolve()
    burn_ledger = burn_path.with_suffix(".sqlite")
    manifest_path = Path(approval_manifest_path).resolve()
    cli_path = root / "src/orev3/rfc008/cli.py"
    runbook_path = root / "docs/research/RFC-008-OPERATOR-RUNBOOK.md"
    checks: list[ReleaseValidationCheck] = []

    def record(name: str, passed: bool, reason: str) -> bool:
        checks.append(ReleaseValidationCheck(name, passed, reason))
        return passed

    approval: dict[str, Any] | None = None
    approval_hash: str | None = None
    try:
        raw = release_path.read_bytes()
        approval_hash = hashlib.sha256(raw).hexdigest()
        approval = decode_approval_json(raw)
        record(
            "active_release_duplicate_keys_rejected",
            True,
            "Active approval raw JSON has unique keys",
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        record("active_release_contract_valid", False, str(exc))

    schema_valid = record(
        "active_release_schema_supported",
        approval is not None
        and type(approval.get("schema_version")) is int
        and approval.get("schema_version") == RELEASE_SCHEMA_VERSION,
        "Active RFC-008 release approval must use exact schema 2",
    )
    artifact_identity_valid = record(
        "active_release_artifact_identity_valid",
        approval is not None
        and approval.get("artifact_type") == RELEASE_ARTIFACT_TYPE
        and approval.get("rfc_identifier") == RELEASE_RFC_IDENTIFIER,
        "Active approval artifact type or RFC identity is invalid",
    )
    structure_failures = (
        active_schema2_structure_failures(approval)
        if approval is not None and schema_valid
        else []
    )
    for name, reason in structure_failures:
        record(name, False, reason)
    structure_valid = record(
        "active_release_contract_valid",
        approval is not None
        and schema_valid
        and artifact_identity_valid
        and not structure_failures,
        "Active release does not match the exact registry field contract",
    )

    marker_document: ExperimentMarker | None = None
    evidence: ResolverBurnInEvidence | None = None
    config: RFC008Config | None = None
    resolver: ResolverConfig | None = None
    marker_hash: str | None = None
    sidecar_hash: str | None = None
    source_failures = False
    try:
        config = RFC008Config.from_path(config_path)
        resolver = ResolverConfig.from_path(resolver_config_path)
        marker_hash = sha256_file(marker)
        sidecar_hash = sha256_file(sidecar)
        if _sidecar_digest(sidecar, marker) != marker_hash:
            raise ValueError("Marker checksum sidecar does not bind marker bytes")
        marker_document = ExperimentMarker.model_validate_json(
            marker.read_text(encoding="utf-8")
        )
        evidence = ResolverBurnInEvidence.model_validate_json(
            burn_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        source_failures = True
        record("active_release_authoritative_sources_available", False, str(exc))

    git_authority: GitReleaseAuthority | None = None
    implementation: str | None = None
    predecessor: str | None = None
    try:
        git_authority = repository_release_authority(
            repository_root=root,
            release_path=release_path,
        )
        implementation = git_authority.implementation_commit
        predecessor = git_authority.predecessor_approval_sha256
        record(
            "active_release_repository_branch_matches",
            git_authority.branch == RELEASE_BRANCH,
            "Active release repository branch does not match RFC-008",
        )
        if git_authority.branch != RELEASE_BRANCH:
            source_failures = True
        record(
            "approval_commit_is_approval_only",
            (
                not git_authority.approval_committed_at_head
                or git_authority.approval_commit_is_approval_only
            ),
            "Committed active approval is not an approval-only child",
        )
        record(
            "approval_commit_is_direct_child_of_implementation",
            (
                not git_authority.approval_committed_at_head
                or _git(root, "rev-parse", "HEAD^").decode().strip()
                == implementation
            ),
            "Active approval commit is not the direct child of implementation",
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        source_failures = True
        record(
            "active_release_git_authority_available",
            False,
            f"Cannot derive active approval Git relationship: {exc}",
        )

    policy: ReleaseApprovalPolicy | None = None
    if (
        marker_document is not None
        and evidence is not None
        and config is not None
        and resolver is not None
        and marker_hash is not None
        and sidecar_hash is not None
        and implementation is not None
        and predecessor is not None
    ):
        try:
            actual_ledger_hash = sha256_file(burn_ledger)
            actual_manifest_hash = sha256_file(manifest_path)
            actual_cli_hash = sha256_file(cli_path)
            actual_runbook_hash = sha256_file(runbook_path)
            actual_migration_hash = _semantic_migration_hash(root)
            policy = ReleaseApprovalPolicy(
                expected_implementation_commit=implementation,
                expected_predecessor_sha256=predecessor,
                marker_sha256=marker_hash,
                marker_sidecar_sha256=sidecar_hash,
                marker_original_approval_sha256=(
                    marker_document.release_approval_sha256
                ),
                marker_repository_commit=marker_document.repository_commit,
                configuration_fingerprint=config.configuration_fingerprint,
                candidate_configuration_sha256=(
                    config.candidate_configuration_sha256
                ),
                resolver_configuration_sha256=resolver.fingerprint,
                burn_in_evidence_sha256=sha256_file(burn_path),
                burn_in_ledger_sha256=actual_ledger_hash,
                burn_in_repository_commit=evidence.repository_commit,
                resolver_version=resolver.resolver_version,
                decoder_version=resolver.decoder_version,
                external_rpc_burn_in_performed=(
                    evidence.mode == "operational"
                    and evidence.real_rpc_request_counts.total > 0
                ),
                cli_sha256=actual_cli_hash,
                runbook_sha256=actual_runbook_hash,
                approval_manifest_sha256=actual_manifest_hash,
                migration_set_sha256=actual_migration_hash,
                repository_branch=RELEASE_BRANCH,
            )
            record(
                "burn_in_ledger_bytes_hashed",
                actual_ledger_hash == evidence.ledger_sha256,
                "Burn-in ledger bytes do not match evidence",
            )
            record(
                "migration_source_matches_implementation",
                _source_matches_implementation(
                    root,
                    implementation,
                    "src/orev3/rfc008/migrations.py",
                ),
                "Migration source bytes differ from the approved implementation",
            )
            record(
                "cli_source_matches_implementation",
                _source_matches_implementation(
                    root,
                    implementation,
                    "src/orev3/rfc008/cli.py",
                ),
                "CLI source bytes differ from the approved implementation",
            )
            record(
                "runbook_source_matches_implementation",
                _source_matches_implementation(
                    root,
                    implementation,
                    "docs/research/RFC-008-OPERATOR-RUNBOOK.md",
                ),
                "Runbook bytes differ from the approved implementation",
            )
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            source_failures = True
            record(
                "active_release_derived_sources_current",
                False,
                f"Cannot recompute an authoritative derived source: {exc}",
            )

    derived_valid = False
    policy_valid = False
    authorization_valid = False
    exact_valid = False
    if approval is not None and policy is not None and structure_valid:
        expected = registry_authoritative_values(policy)
        present = leaf_paths(approval)

        def authority_matches(authority: str) -> bool:
            fields = tuple(
                item
                for item in SCHEMA2_APPROVAL_FIELDS
                if item.authority == authority
            )
            return all(
                item.path in present
                and get_path(approval, item.path) == expected[item.path]
                for item in fields
            )

        derived_valid = authority_matches("release_bound_derived")
        policy_valid = authority_matches("policy_bound")
        exact_valid = authority_matches("release_bound_exact")
        authorization_valid = authority_matches("authorization")
    record(
        "approved_implementation_commit_matches_git_parent",
        approval is not None
        and implementation is not None
        and approval.get("approved_implementation_commit") == implementation,
        "Approved implementation does not match Git-derived implementation",
    )
    record(
        "predecessor_matches_immediate_chain_entry",
        approval is not None
        and predecessor is not None
        and approval.get(
            "supersedes_release_implementation_approval_sha256"
        )
        == predecessor,
        "Approval predecessor does not match immediate Git-derived entry",
    )
    record(
        "active_release_derived_fields_valid",
        derived_valid and not source_failures,
        "One or more derived fields do not match authoritative source state",
    )
    record(
        "active_release_policy_fields_valid",
        policy_valid,
        "One or more policy-bound fields do not match",
    )
    record(
        "active_release_exact_fields_valid",
        exact_valid,
        "One or more exact release fields do not match",
    )
    record(
        "active_release_authorization_fields_valid",
        authorization_valid,
        "Every active authorization field must be exact boolean false",
    )

    marker_binding_valid = record(
        "active_release_marker_binding_valid",
        approval is not None
        and marker_document is not None
        and marker_hash is not None
        and sidecar_hash is not None
        and approval.get("validated_production_marker_sha256") == marker_hash
        and approval.get("validated_production_marker_sidecar_sha256")
        == sidecar_hash
        and approval.get(
            "validated_production_marker_release_approval_sha256"
        )
        == marker_document.release_approval_sha256
        and approval.get("validated_production_marker_repository_commit")
        == marker_document.repository_commit,
        "Active approval does not bind the immutable production marker pair",
    )

    chain_valid = False
    approval_hashes: tuple[str, ...] = ()
    if policy is not None:
        try:
            trusted = repository_approval_history(
                repository_root=root,
                release_path=release_path,
            )
            chain = validate_release_approval_chain(
                release_path=release_path,
                history_directory=(
                    release_path.parent / "release_approval_history"
                ),
                trusted_approval_documents=trusted,
                policy=policy,
            )
            chain_valid = bool(chain["valid"])
            approval_hashes = tuple(chain["approval_hashes"])
            for failure in chain["failures"]:
                record(
                    str(failure["check"]),
                    False,
                    str(failure["reason"]),
                )
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            record(
                "active_release_chain_valid",
                False,
                f"Cannot traverse active release chain: {exc}",
            )
    record(
        "active_release_chain_valid",
        chain_valid,
        "Active release approval chain is invalid",
    )

    required = (
        schema_valid,
        artifact_identity_valid,
        structure_valid,
        derived_valid,
        policy_valid,
        exact_valid,
        authorization_valid,
        chain_valid,
        marker_binding_valid,
        not source_failures,
        all(
            item.passed
            for item in checks
            if item.check
            in {
                "burn_in_ledger_bytes_hashed",
                "migration_source_matches_implementation",
                "cli_source_matches_implementation",
                "runbook_source_matches_implementation",
            }
        ),
    )
    valid = all(required)
    return ActiveReleaseValidationResult(
        parsed_active_approval=(
            _freeze(approval) if approval is not None else None
        ),
        active_approval_sha256=approval_hash,
        schema_valid=schema_valid,
        artifact_identity_valid=artifact_identity_valid,
        field_contract_valid=structure_valid and exact_valid,
        derived_field_valid=derived_valid and not source_failures,
        policy_field_valid=policy_valid,
        authorization_field_valid=authorization_valid,
        approval_chain_valid=chain_valid,
        marker_binding_valid=marker_binding_valid,
        checks=tuple(checks),
        approval_hashes=approval_hashes,
        valid=valid,
    )
