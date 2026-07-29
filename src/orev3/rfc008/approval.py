from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orev3.rfc008.approval_contract import (
    SCHEMA2_APPROVAL_FIELDS,
    active_schema2_structure_failures,
    decode_approval_json,
    generate_schema2_approval,
    get_path,
    leaf_paths,
)


RELEASE_ARTIFACT_TYPE = "rfc008_implementation_release_approval"
RELEASE_SCHEMA_VERSION = 2
RELEASE_RFC_IDENTIFIER = "RFC-008"
RELEASE_BRANCH = "research/rfc-007-paper-collection-burn-in"
RELEASE_APPROVAL_COMMIT_POLICY = (
    "head_must_equal_approved_implementation_or_be_its_approval_artifact_child"
)
RELEASE_STATUS = "schema2_field_authority_defined_for_independent_review_only"
DATABASE_FAMILY = "orev3-rfc008"
DATABASE_SCHEMA_VERSION = 5
MARKER_SCHEMA_VERSION = 2
BURN_IN_EVIDENCE_SCHEMA_VERSION = 4
CLI_VERSION = "rfc008-cli-v9"
RUNBOOK_VERSION = "rfc008-operator-runbook-v10"
MIGRATION_SET_SHA256 = (
    "ff322eed205ad084cf6bd7342b68de6399d328184f50b9fa065dfa64d12f1576"
)
APPROVAL_MANIFEST_SHA256 = (
    "9fe94099ed3d9e15e015eef72db5543f16c756b1c3c5463f014e18467a44d789"
)
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class ReleaseApprovalPolicy:
    expected_implementation_commit: str
    expected_predecessor_sha256: str
    marker_sha256: str
    marker_sidecar_sha256: str
    marker_original_approval_sha256: str
    marker_repository_commit: str
    configuration_fingerprint: str
    candidate_configuration_sha256: str
    resolver_configuration_sha256: str
    burn_in_evidence_sha256: str
    burn_in_ledger_sha256: str
    burn_in_repository_commit: str
    resolver_version: str
    decoder_version: str
    external_rpc_burn_in_performed: bool
    cli_sha256: str
    runbook_sha256: str
    approval_manifest_sha256: str = APPROVAL_MANIFEST_SHA256
    migration_set_sha256: str = MIGRATION_SET_SHA256
    repository_branch: str = RELEASE_BRANCH
    audit_version: str = "rfc008-release-preflight-v5"
    minimum_operational_sample_size: int = 5
    protected_process_policy: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            "48404": {
                "role": "observer",
                "sanitized_command_identity": "-m orev3.observer.collect",
            },
            "48405": {
                "role": "observer_caffeinate",
                "sanitized_command_identity": (
                    "caffeinate -i python -m orev3.observer.collect"
                ),
            },
            "78317": {
                "role": "rfc007_collector",
                "sanitized_command_identity": (
                    "-m orev3.collection.cli run --config "
                    "config/collection/rfc007_burn_in_v1.json --ledger "
                    "data/ledger/rfc007_live_ledger_v1.sqlite"
                ),
            },
        }
    )


def registry_authoritative_values(
    policy: ReleaseApprovalPolicy,
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "artifact_type": RELEASE_ARTIFACT_TYPE,
        "schema_version": RELEASE_SCHEMA_VERSION,
        "rfc_identifier": RELEASE_RFC_IDENTIFIER,
        "repository_branch": policy.repository_branch,
        "status": RELEASE_STATUS,
        "approved_implementation_commit": policy.expected_implementation_commit,
        "approval_commit_policy": RELEASE_APPROVAL_COMMIT_POLICY,
        "supersedes_release_implementation_approval_sha256": (
            policy.expected_predecessor_sha256
        ),
        "validated_production_marker_sha256": policy.marker_sha256,
        "validated_production_marker_sidecar_sha256": (
            policy.marker_sidecar_sha256
        ),
        "validated_production_marker_repository_commit": (
            policy.marker_repository_commit
        ),
        "validated_production_marker_release_approval_sha256": (
            policy.marker_original_approval_sha256
        ),
        "validated_production_marker_collection_authorized": False,
        "validated_operational_burn_in_evidence_sha256": (
            policy.burn_in_evidence_sha256
        ),
        "validated_operational_burn_in_ledger_sha256": (
            policy.burn_in_ledger_sha256
        ),
        "validated_operational_burn_in_repository_commit": (
            policy.burn_in_repository_commit
        ),
        "frozen_approval_manifest_sha256": policy.approval_manifest_sha256,
        "configuration_fingerprint": policy.configuration_fingerprint,
        "candidate_configuration_sha256": (
            policy.candidate_configuration_sha256
        ),
        "resolver_configuration_sha256": (
            policy.resolver_configuration_sha256
        ),
        "audit_version": policy.audit_version,
        "resolver_version": policy.resolver_version,
        "decoder_version": policy.decoder_version,
        "database_family": DATABASE_FAMILY,
        "database_schema_version": DATABASE_SCHEMA_VERSION,
        "migration_set_sha256": policy.migration_set_sha256,
        "burn_in_evidence_schema_version": BURN_IN_EVIDENCE_SCHEMA_VERSION,
        "marker_schema_version": MARKER_SCHEMA_VERSION,
        "minimum_operational_sample_size": (
            policy.minimum_operational_sample_size
        ),
        "cli_version": CLI_VERSION,
        "cli_sha256": policy.cli_sha256,
        "runbook_version": RUNBOOK_VERSION,
        "runbook_sha256": policy.runbook_sha256,
        "verification.fixture_resolver_burn_in_required": True,
        "verification.operational_resolver_burn_in_required_before_marker": True,
        "verification.external_rpc_burn_in_performed": (
            policy.external_rpc_burn_in_performed
        ),
        "authorization_boundary.implementation_authorized": True,
        "authorization_boundary.fixture_burn_in_authorized": True,
        "authorization_boundary.operational_rpc_burn_in_authorized": False,
        "authorization_boundary.marker_creation_authorized": False,
        "authorization_boundary.collection_authorized": False,
        "authorization_boundary.wallet_access_authorized": False,
        "authorization_boundary.live_action_authorized": False,
        "authorization_boundary.transaction_authorized": False,
    }
    for pid, process in policy.protected_process_policy.items():
        for key, item in process.items():
            values[f"protected_process_policy.{pid}.{key}"] = item
    authoritative_paths = {
        field.path
        for field in SCHEMA2_APPROVAL_FIELDS
        if field.authority != "informational"
    }
    if set(values) != authoritative_paths:
        raise RuntimeError(
            "Registry authority source coverage mismatch; "
            f"missing={sorted(authoritative_paths - set(values))}, "
            f"unknown={sorted(set(values) - authoritative_paths)}"
        )
    return {
        field.path: values[field.path]
        for field in SCHEMA2_APPROVAL_FIELDS
        if field.authority != "informational"
    }


def generate_release_approval(
    *,
    policy: ReleaseApprovalPolicy,
    audit_correction_identifier: str,
    focused_lifecycle_test_count: int,
    rfc008_test_count: int,
    full_test_count: int,
) -> dict[str, Any]:
    values = registry_authoritative_values(policy)
    values.update(
        {
            "audit_correction_identifier": audit_correction_identifier,
            "verification.focused_lifecycle_test_count": (
                focused_lifecycle_test_count
            ),
            "verification.rfc008_test_count": rfc008_test_count,
            "verification.full_test_count": full_test_count,
        }
    )
    return generate_schema2_approval(values)


def _failure(
    failures: list[dict[str, str]],
    check: str,
    reason: str,
) -> None:
    failures.append({"check": check, "reason": reason})


def _exact(
    value: dict[str, Any],
    field: str,
    expected: object,
    check: str,
    failures: list[dict[str, str]],
) -> None:
    if field not in value or type(value[field]) is not type(expected):
        _failure(failures, check, f"{field} is missing or has the wrong type")
    elif value[field] != expected:
        _failure(failures, check, f"{field} does not match the frozen value")


def _false_authorization(
    boundary: object,
    field: str,
    check: str,
    failures: list[dict[str, str]],
) -> None:
    if not isinstance(boundary, dict) or boundary.get(field) is not False:
        _failure(failures, check, f"{field} must be explicitly false")


def _load_json_object(
    path: Path,
    failures: list[dict[str, str]],
) -> dict[str, Any] | None:
    try:
        value = decode_approval_json(path.read_bytes())
    except (OSError, ValueError) as exc:
        _failure(failures, "release_chain_valid", str(exc))
        return None
    if not isinstance(value, dict):
        _failure(
            failures,
            "release_chain_valid",
            "Release approval must be a JSON object",
        )
        return None
    return value


def _validate_historical_identity(
    value: dict[str, Any],
    *,
    terminal: bool,
    policy: ReleaseApprovalPolicy,
    failures: list[dict[str, str]],
) -> None:
    _exact(
        value,
        "artifact_type",
        RELEASE_ARTIFACT_TYPE,
        "release_artifact_type_matches",
        failures,
    )
    schema = value.get("schema_version")
    if schema != 1:
        _failure(
            failures,
            "release_schema_supported",
            "Historical approval must use the anchored schema version 1",
        )
    # Schema-v1 encoded RFC identity in the canonical artifact type.
    if value.get("artifact_type") != RELEASE_ARTIFACT_TYPE:
        _failure(
            failures,
            "release_rfc_identity_matches",
            "Historical approval is not an RFC-008 approval",
        )
    implementation = value.get("approved_implementation_commit")
    if not isinstance(implementation, str) or not HEX_40.fullmatch(
        implementation
    ):
        _failure(
            failures,
            "approved_implementation_commit_matches",
            "Historical implementation commit is not a full commit identity",
        )
    boundary = value.get("authorization_boundary")
    _false_authorization(
        boundary,
        "collection_authorized",
        "release_collection_authorization_false",
        failures,
    )
    _false_authorization(
        boundary,
        "live_action_authorized",
        "release_live_authorization_false",
        failures,
    )
    _false_authorization(
        boundary,
        "wallet_access_authorized",
        "release_wallet_authorization_false",
        failures,
    )
    if not terminal:
        _exact(
            value,
            "validated_production_marker_sha256",
            policy.marker_sha256,
            "release_marker_hash_matches",
            failures,
        )
        _exact(
            value,
            "validated_production_marker_sidecar_sha256",
            policy.marker_sidecar_sha256,
            "release_marker_sidecar_hash_matches",
            failures,
        )


def _validate_historical_schema2_identity(
    value: dict[str, Any],
    *,
    policy: ReleaseApprovalPolicy,
    failures: list[dict[str, str]],
) -> None:
    _exact(
        value,
        "artifact_type",
        RELEASE_ARTIFACT_TYPE,
        "release_artifact_type_matches",
        failures,
    )
    _exact(
        value,
        "schema_version",
        RELEASE_SCHEMA_VERSION,
        "release_schema_supported",
        failures,
    )
    for check, reason in active_schema2_structure_failures(value):
        _failure(failures, check, reason)
    present = leaf_paths(value)
    for item in SCHEMA2_APPROVAL_FIELDS:
        if item.path not in present:
            continue
        actual = get_path(value, item.path)
        if item.canonical == "lowercase_full_sha256" and (
            not isinstance(actual, str) or not HEX_64.fullmatch(actual)
        ):
            _failure(
                failures,
                item.failure_reason,
                f"Historical SHA-256 is not canonical: {item.path}",
            )
        if item.canonical == "lowercase_full_git_commit" and (
            not isinstance(actual, str) or not HEX_40.fullmatch(actual)
        ):
            _failure(
                failures,
                item.failure_reason,
                f"Historical commit is not canonical: {item.path}",
            )
    expected = registry_authoritative_values(policy)
    for item in SCHEMA2_APPROVAL_FIELDS:
        if not item.historical_invariant:
            continue
        path = item.path
        if path in present and get_path(value, path) != expected[path]:
            _failure(
                failures,
                item.failure_reason,
                f"Historical schema-2 invariant changed: {path}",
            )


def _validate_historical_approval(
    value: dict[str, Any],
    *,
    terminal: bool,
    policy: ReleaseApprovalPolicy,
    failures: list[dict[str, str]],
) -> None:
    if value.get("schema_version") == RELEASE_SCHEMA_VERSION:
        if terminal:
            _failure(
                failures,
                "release_chain_valid",
                "Marker-anchored terminal approval must remain schema 1",
            )
        _validate_historical_schema2_identity(
            value,
            policy=policy,
            failures=failures,
        )
        return
    _validate_historical_identity(
        value,
        terminal=terminal,
        policy=policy,
        failures=failures,
    )


def _validate_current_release(
    value: dict[str, Any],
    policy: ReleaseApprovalPolicy,
    failures: list[dict[str, str]],
) -> None:
    _exact(
        value,
        "artifact_type",
        RELEASE_ARTIFACT_TYPE,
        "release_artifact_type_matches",
        failures,
    )
    _exact(
        value,
        "schema_version",
        RELEASE_SCHEMA_VERSION,
        "release_schema_supported",
        failures,
    )
    for check, reason in active_schema2_structure_failures(value):
        _failure(failures, check, reason)
    present = leaf_paths(value)
    expected_values = registry_authoritative_values(policy)

    for item in SCHEMA2_APPROVAL_FIELDS:
        if item.path not in present:
            continue
        actual = get_path(value, item.path)
        json_type = {"string": str, "integer": int, "boolean": bool}[
            item.json_type
        ]
        if type(actual) is not json_type:
            continue
        if item.authority == "informational":
            if item.json_type == "integer" and actual < 0:
                _failure(
                    failures,
                    item.failure_reason,
                    f"Informational count must be non-negative: {item.path}",
                )
            if (
                item.path == "audit_correction_identifier"
                and not re.fullmatch(r"rfc008-[a-z0-9-]+-v[0-9]+", actual)
            ):
                _failure(
                    failures,
                    item.failure_reason,
                    "Audit correction identifier is malformed",
                )
            continue
        if item.authority == "authorization":
            continue
        expected = expected_values.get(item.path)
        if actual != expected:
            _failure(
                failures,
                item.failure_reason,
                f"Active approval field does not match authority: {item.path}",
            )

    implementation = value.get("approved_implementation_commit")
    if not isinstance(implementation, str) or not HEX_40.fullmatch(
        implementation
    ):
        _failure(
            failures,
            "approved_implementation_commit_matches",
            "Implementation commit must be a lowercase full commit identity",
        )
    predecessor = value.get(
        "supersedes_release_implementation_approval_sha256"
    )
    if not isinstance(predecessor, str) or not HEX_64.fullmatch(predecessor):
        _failure(
            failures,
            "release_predecessor_matches",
            "Predecessor must be a lowercase SHA-256",
        )


def _validate_current_authorizations(
    value: dict[str, Any],
    failures: list[dict[str, str]],
) -> None:
    present = leaf_paths(value)
    for item in SCHEMA2_APPROVAL_FIELDS:
        if item.authority != "authorization" or item.path not in present:
            continue
        actual = get_path(value, item.path)
        if type(actual) is bool and actual is not False:
            _failure(
                failures,
                item.failure_reason,
                f"Authorization must be explicitly false: {item.path}",
            )


def validate_release_approval_chain(
    *,
    release_path: str | Path,
    history_directory: str | Path,
    policy: ReleaseApprovalPolicy,
    trusted_approval_documents: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    path = Path(release_path)
    history = Path(history_directory)
    failures: list[dict[str, str]] = []
    current = _load_json_object(path, failures)
    if current is None:
        return {"valid": False, "failures": failures, "approval_hashes": []}
    current_hash = sha256_file(path)
    if current_hash == policy.marker_original_approval_sha256:
        _validate_historical_identity(
            current,
            terminal=True,
            policy=policy,
            failures=failures,
        )
        return {
            "valid": not failures,
            "failures": failures,
            "approval_hashes": [current_hash],
        }
    _validate_current_release(current, policy, failures)
    hashes = [current_hash]
    predecessor = current.get(
        "supersedes_release_implementation_approval_sha256"
    )
    while isinstance(predecessor, str):
        if predecessor in hashes:
            _failure(
                failures,
                "release_chain_valid",
                "Approval chain contains a cycle or duplicate approval",
            )
            break
        predecessor_path = history / f"{predecessor}.json"
        predecessor_bytes: bytes | None = None
        if predecessor_path.is_file():
            predecessor_bytes = predecessor_path.read_bytes()
        elif trusted_approval_documents is not None:
            predecessor_bytes = trusted_approval_documents.get(predecessor)
        if predecessor_bytes is None:
            _failure(
                failures,
                "release_chain_valid",
                f"Approval predecessor is missing: {predecessor}",
            )
            break
        if hashlib.sha256(predecessor_bytes).hexdigest() != predecessor:
            _failure(
                failures,
                "release_chain_valid",
                f"Approval predecessor hash is invalid: {predecessor}",
            )
            break
        try:
            predecessor_value = decode_approval_json(predecessor_bytes)
        except (UnicodeDecodeError, ValueError) as exc:
            _failure(failures, "release_chain_valid", str(exc))
            break
        if not isinstance(predecessor_value, dict):
            _failure(
                failures,
                "release_chain_valid",
                "Approval predecessor must be a JSON object",
            )
            break
        hashes.append(predecessor)
        terminal = predecessor == policy.marker_original_approval_sha256
        _validate_historical_approval(
            predecessor_value,
            terminal=terminal,
            policy=policy,
            failures=failures,
        )
        if terminal:
            break
        predecessor = predecessor_value.get(
            "supersedes_release_implementation_approval_sha256"
        )
        if not isinstance(predecessor, str) or not HEX_64.fullmatch(predecessor):
            _failure(
                failures,
                "release_chain_valid",
                "Approval predecessor link is missing or malformed",
            )
            break
    if not hashes or hashes[-1] != policy.marker_original_approval_sha256:
        _failure(
            failures,
            "release_chain_valid",
            "Approval chain does not terminate at the marker approval",
        )
    _validate_current_authorizations(current, failures)
    return {
        "valid": not failures,
        "failures": failures,
        "approval_hashes": hashes,
    }
