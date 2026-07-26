from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orev3.rfc008.marker import sha256_file


RELEASE_ARTIFACT_TYPE = "rfc008_implementation_release_approval"
RELEASE_SCHEMA_VERSION = 2
RELEASE_RFC_IDENTIFIER = "RFC-008"
RELEASE_BRANCH = "research/rfc-007-paper-collection-burn-in"
RELEASE_APPROVAL_COMMIT_POLICY = (
    "head_must_equal_approved_implementation_or_be_its_approval_artifact_child"
)
RELEASE_STATUS = "approval_supersession_hardened_for_independent_review_only"
DATABASE_FAMILY = "orev3-rfc008"
DATABASE_SCHEMA_VERSION = 3
MARKER_SCHEMA_VERSION = 2
BURN_IN_EVIDENCE_SCHEMA_VERSION = 4
CLI_VERSION = "rfc008-cli-v4"
CLI_SHA256 = "2fadb7a12ea2b7e3533ce75f5b42f48810561ecbfe841d7112e26c94b50be4d5"
RUNBOOK_VERSION = "rfc008-operator-runbook-v5"
RUNBOOK_SHA256 = (
    "a1d2c952f7da20c3ddc0db47ac45123ccdaa5e1d4d41c2d56b7bc7ba9066a4c6"
)
MIGRATION_SET_SHA256 = (
    "ece66b7732cdc61af7c549aa8e2161d6f1f305e533e43165cf58e9ad492c2bd5"
)
APPROVAL_MANIFEST_SHA256 = (
    "9fe94099ed3d9e15e015eef72db5543f16c756b1c3c5463f014e18467a44d789"
)
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


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
    cli_sha256: str
    runbook_sha256: str
    repository_branch: str = RELEASE_BRANCH


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
        value = _decode_json_object(path.read_bytes())
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


def _decode_json_object(raw: bytes) -> dict[str, Any]:
    def reject_duplicates(pairs):
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON field: {key}")
            value[key] = item
        return value

    value = json.loads(raw, object_pairs_hook=reject_duplicates)
    if not isinstance(value, dict):
        raise ValueError("Release approval must be a JSON object")
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


def _validate_current_release(
    value: dict[str, Any],
    policy: ReleaseApprovalPolicy,
    failures: list[dict[str, str]],
) -> None:
    expected = (
        (
            "artifact_type",
            RELEASE_ARTIFACT_TYPE,
            "release_artifact_type_matches",
        ),
        ("schema_version", RELEASE_SCHEMA_VERSION, "release_schema_supported"),
        (
            "rfc_identifier",
            RELEASE_RFC_IDENTIFIER,
            "release_rfc_identity_matches",
        ),
        ("repository_branch", policy.repository_branch, "release_repository_matches"),
        ("status", RELEASE_STATUS, "release_schema_supported"),
        (
            "approval_commit_policy",
            RELEASE_APPROVAL_COMMIT_POLICY,
            "approved_implementation_commit_matches",
        ),
        (
            "approved_implementation_commit",
            policy.expected_implementation_commit,
            "approved_implementation_commit_matches",
        ),
        (
            "supersedes_release_implementation_approval_sha256",
            policy.expected_predecessor_sha256,
            "release_predecessor_matches",
        ),
        (
            "validated_production_marker_sha256",
            policy.marker_sha256,
            "release_marker_hash_matches",
        ),
        (
            "validated_production_marker_sidecar_sha256",
            policy.marker_sidecar_sha256,
            "release_marker_sidecar_hash_matches",
        ),
        (
            "validated_production_marker_repository_commit",
            policy.marker_repository_commit,
            "release_repository_matches",
        ),
        (
            "validated_production_marker_release_approval_sha256",
            policy.marker_original_approval_sha256,
            "release_chain_valid",
        ),
        (
            "validated_production_marker_collection_authorized",
            False,
            "release_collection_authorization_false",
        ),
        (
            "validated_operational_burn_in_evidence_sha256",
            policy.burn_in_evidence_sha256,
            "release_configuration_binding_matches",
        ),
        (
            "validated_operational_burn_in_ledger_sha256",
            policy.burn_in_ledger_sha256,
            "release_configuration_binding_matches",
        ),
        (
            "frozen_approval_manifest_sha256",
            APPROVAL_MANIFEST_SHA256,
            "release_approval_manifest_matches",
        ),
        (
            "configuration_fingerprint",
            policy.configuration_fingerprint,
            "release_experiment_fingerprint_matches",
        ),
        (
            "candidate_configuration_sha256",
            policy.candidate_configuration_sha256,
            "release_candidate_hash_matches",
        ),
        (
            "resolver_configuration_sha256",
            policy.resolver_configuration_sha256,
            "release_resolver_fingerprint_matches",
        ),
        (
            "migration_set_sha256",
            MIGRATION_SET_SHA256,
            "release_migration_set_matches",
        ),
        (
            "marker_schema_version",
            MARKER_SCHEMA_VERSION,
            "release_marker_schema_matches",
        ),
        (
            "burn_in_evidence_schema_version",
            BURN_IN_EVIDENCE_SCHEMA_VERSION,
            "release_evidence_schema_matches",
        ),
        (
            "database_family",
            DATABASE_FAMILY,
            "release_database_schema_matches",
        ),
        (
            "database_schema_version",
            DATABASE_SCHEMA_VERSION,
            "release_database_schema_matches",
        ),
        ("cli_version", CLI_VERSION, "release_cli_contract_matches"),
        ("cli_sha256", policy.cli_sha256, "release_cli_hash_matches"),
        ("runbook_version", RUNBOOK_VERSION, "release_runbook_hash_matches"),
        ("runbook_sha256", policy.runbook_sha256, "release_runbook_hash_matches"),
    )
    for field, frozen, check in expected:
        _exact(value, field, frozen, check, failures)
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
    _false_authorization(
        boundary,
        "transaction_authorized",
        "release_transaction_authorization_false",
        failures,
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
            predecessor_value = _decode_json_object(predecessor_bytes)
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
        _validate_historical_identity(
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
    return {
        "valid": not failures,
        "failures": failures,
        "approval_hashes": hashes,
    }
