from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from orev3.rfc008.approval import (
    APPROVAL_MANIFEST_SHA256,
    BURN_IN_EVIDENCE_SCHEMA_VERSION,
    CLI_VERSION,
    DATABASE_FAMILY,
    DATABASE_SCHEMA_VERSION,
    MARKER_SCHEMA_VERSION,
    MIGRATION_SET_SHA256,
    RELEASE_APPROVAL_COMMIT_POLICY,
    RELEASE_ARTIFACT_TYPE,
    RELEASE_BRANCH,
    RELEASE_RFC_IDENTIFIER,
    RELEASE_SCHEMA_VERSION,
    RELEASE_STATUS,
    RUNBOOK_VERSION,
    ReleaseApprovalPolicy,
    validate_release_approval_chain,
)


SHA = {
    "implementation": "1" * 40,
    "approval_child": "2" * 40,
    "unrelated_commit": "3" * 40,
    "marker": "4" * 64,
    "sidecar": "5" * 64,
    "evidence": "6" * 64,
    "ledger": "7" * 64,
    "experiment": "8" * 64,
    "candidate": "9" * 64,
    "resolver": "a" * 64,
    "cli": "b" * 64,
    "runbook": "c" * 64,
    "marker_repository": "d" * 40,
}


def write_json(path: Path, value: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def legacy_approval(
    *,
    predecessor: str,
    marker_fields: bool,
) -> dict[str, object]:
    value: dict[str, object] = {
        "artifact_type": RELEASE_ARTIFACT_TYPE,
        "schema_version": 1,
        "approved_implementation_commit": "e" * 40,
        "supersedes_release_implementation_approval_sha256": predecessor,
        "authorization_boundary": {
            "collection_authorized": False,
            "live_action_authorized": False,
            "wallet_access_authorized": False,
        },
    }
    if marker_fields:
        value.update(
            {
                "validated_production_marker_sha256": SHA["marker"],
                "validated_production_marker_sidecar_sha256": SHA["sidecar"],
            }
        )
    return value


def current_approval(predecessor: str) -> dict[str, object]:
    return {
        "artifact_type": RELEASE_ARTIFACT_TYPE,
        "schema_version": RELEASE_SCHEMA_VERSION,
        "rfc_identifier": RELEASE_RFC_IDENTIFIER,
        "repository_branch": RELEASE_BRANCH,
        "status": RELEASE_STATUS,
        "approved_implementation_commit": SHA["implementation"],
        "approval_commit_policy": RELEASE_APPROVAL_COMMIT_POLICY,
        "supersedes_release_implementation_approval_sha256": predecessor,
        "validated_production_marker_sha256": SHA["marker"],
        "validated_production_marker_sidecar_sha256": SHA["sidecar"],
        "validated_production_marker_repository_commit": SHA[
            "marker_repository"
        ],
        "validated_production_marker_release_approval_sha256": "",
        "validated_production_marker_collection_authorized": False,
        "validated_operational_burn_in_evidence_sha256": SHA["evidence"],
        "validated_operational_burn_in_ledger_sha256": SHA["ledger"],
        "frozen_approval_manifest_sha256": APPROVAL_MANIFEST_SHA256,
        "configuration_fingerprint": SHA["experiment"],
        "candidate_configuration_sha256": SHA["candidate"],
        "resolver_configuration_sha256": SHA["resolver"],
        "migration_set_sha256": MIGRATION_SET_SHA256,
        "marker_schema_version": MARKER_SCHEMA_VERSION,
        "burn_in_evidence_schema_version": BURN_IN_EVIDENCE_SCHEMA_VERSION,
        "database_family": DATABASE_FAMILY,
        "database_schema_version": DATABASE_SCHEMA_VERSION,
        "cli_version": CLI_VERSION,
        "cli_sha256": SHA["cli"],
        "runbook_version": RUNBOOK_VERSION,
        "runbook_sha256": SHA["runbook"],
        "authorization_boundary": {
            "collection_authorized": False,
            "live_action_authorized": False,
            "wallet_access_authorized": False,
            "transaction_authorized": False,
        },
    }


def valid_chain(tmp_path: Path):
    history = tmp_path / "history"
    original_path = tmp_path / "original.json"
    original = legacy_approval(predecessor="f" * 64, marker_fields=False)
    original_hash = write_json(original_path, original)
    (history / f"{original_hash}.json").parent.mkdir(parents=True)
    (history / f"{original_hash}.json").write_bytes(original_path.read_bytes())

    prior_path = tmp_path / "prior.json"
    prior = legacy_approval(predecessor=original_hash, marker_fields=True)
    prior_hash = write_json(prior_path, prior)
    (history / f"{prior_hash}.json").write_bytes(prior_path.read_bytes())

    release = tmp_path / "release.json"
    value = current_approval(prior_hash)
    value["validated_production_marker_release_approval_sha256"] = original_hash
    write_json(release, value)
    policy = ReleaseApprovalPolicy(
        expected_implementation_commit=SHA["implementation"],
        expected_predecessor_sha256=prior_hash,
        marker_sha256=SHA["marker"],
        marker_sidecar_sha256=SHA["sidecar"],
        marker_original_approval_sha256=original_hash,
        marker_repository_commit=SHA["marker_repository"],
        configuration_fingerprint=SHA["experiment"],
        candidate_configuration_sha256=SHA["candidate"],
        resolver_configuration_sha256=SHA["resolver"],
        burn_in_evidence_sha256=SHA["evidence"],
        burn_in_ledger_sha256=SHA["ledger"],
        cli_sha256=SHA["cli"],
        runbook_sha256=SHA["runbook"],
    )
    return release, history, policy


def validate(release: Path, history: Path, policy: ReleaseApprovalPolicy):
    return validate_release_approval_chain(
        release_path=release,
        history_directory=history,
        policy=policy,
    )


def mutate(release: Path, field: str, value: object) -> None:
    document = json.loads(release.read_text())
    if "." in field:
        parent, child = field.split(".", 1)
        document[parent][child] = value
    elif value is _MISSING:
        document.pop(field, None)
    else:
        document[field] = value
    write_json(release, document)


_MISSING = object()


def checks(report) -> set[str]:
    return {failure["check"] for failure in report["failures"]}


def test_current_valid_multi_step_approval_chain(tmp_path) -> None:
    release, history, policy = valid_chain(tmp_path)
    report = validate(release, history, policy)
    assert report["valid"]
    assert len(report["approval_hashes"]) == 3


def test_valid_one_step_supersession(tmp_path) -> None:
    release, history, policy = valid_chain(tmp_path)
    mutate(
        release,
        "supersedes_release_implementation_approval_sha256",
        policy.marker_original_approval_sha256,
    )
    policy = ReleaseApprovalPolicy(
        **{
            **policy.__dict__,
            "expected_predecessor_sha256": (
                policy.marker_original_approval_sha256
            ),
        }
    )
    report = validate(release, history, policy)
    assert report["valid"]
    assert len(report["approval_hashes"]) == 2


@pytest.mark.parametrize(
    ("field", "replacement", "expected_check"),
    (
        ("artifact_type", "generic_approval", "release_artifact_type_matches"),
        ("artifact_type", _MISSING, "release_artifact_type_matches"),
        ("schema_version", 99, "release_schema_supported"),
        ("schema_version", _MISSING, "release_schema_supported"),
        ("rfc_identifier", "RFC-007", "release_rfc_identity_matches"),
        ("rfc_identifier", _MISSING, "release_rfc_identity_matches"),
        (
            "approved_implementation_commit",
            "3" * 40,
            "approved_implementation_commit_matches",
        ),
        (
            "approved_implementation_commit",
            _MISSING,
            "approved_implementation_commit_matches",
        ),
        (
            "approved_implementation_commit",
            "2" * 40,
            "approved_implementation_commit_matches",
        ),
        (
            "approved_implementation_commit",
            "e" * 40,
            "approved_implementation_commit_matches",
        ),
        (
            "approved_implementation_commit",
            "not-a-commit",
            "approved_implementation_commit_matches",
        ),
        (
            "configuration_fingerprint",
            "0" * 64,
            "release_experiment_fingerprint_matches",
        ),
        (
            "candidate_configuration_sha256",
            "0" * 64,
            "release_candidate_hash_matches",
        ),
        (
            "resolver_configuration_sha256",
            "0" * 64,
            "release_resolver_fingerprint_matches",
        ),
        (
            "migration_set_sha256",
            "0" * 64,
            "release_migration_set_matches",
        ),
        ("marker_schema_version", 1, "release_marker_schema_matches"),
        (
            "burn_in_evidence_schema_version",
            3,
            "release_evidence_schema_matches",
        ),
        ("database_schema_version", 2, "release_database_schema_matches"),
        ("cli_version", "rfc008-cli-v3", "release_cli_contract_matches"),
        ("cli_sha256", "0" * 64, "release_cli_hash_matches"),
        ("runbook_sha256", "0" * 64, "release_runbook_hash_matches"),
        (
            "validated_operational_burn_in_evidence_sha256",
            "0" * 64,
            "release_configuration_binding_matches",
        ),
        (
            "frozen_approval_manifest_sha256",
            "0" * 64,
            "release_approval_manifest_matches",
        ),
        ("repository_branch", "unrelated/branch", "release_repository_matches"),
        (
            "validated_production_marker_sha256",
            "0" * 64,
            "release_marker_hash_matches",
        ),
        (
            "validated_production_marker_sha256",
            _MISSING,
            "release_marker_hash_matches",
        ),
        (
            "validated_production_marker_sidecar_sha256",
            "0" * 64,
            "release_marker_sidecar_hash_matches",
        ),
        (
            "validated_production_marker_sidecar_sha256",
            _MISSING,
            "release_marker_sidecar_hash_matches",
        ),
        (
            "authorization_boundary.collection_authorized",
            True,
            "release_collection_authorization_false",
        ),
        (
            "authorization_boundary.live_action_authorized",
            True,
            "release_live_authorization_false",
        ),
        (
            "authorization_boundary.wallet_access_authorized",
            True,
            "release_wallet_authorization_false",
        ),
        (
            "authorization_boundary.transaction_authorized",
            True,
            "release_transaction_authorization_false",
        ),
        (
            "authorization_boundary.collection_authorized",
            "false",
            "release_collection_authorization_false",
        ),
    ),
)
def test_frozen_release_mutations_fail_closed(
    tmp_path,
    field,
    replacement,
    expected_check,
) -> None:
    release, history, policy = valid_chain(tmp_path)
    mutate(release, field, replacement)
    report = validate(release, history, policy)
    assert not report["valid"]
    assert expected_check in checks(report)


@pytest.mark.parametrize(
    ("field", "expected_check"),
    (
        (
            "authorization_boundary.collection_authorized",
            "release_collection_authorization_false",
        ),
        (
            "authorization_boundary.live_action_authorized",
            "release_live_authorization_false",
        ),
        (
            "authorization_boundary.wallet_access_authorized",
            "release_wallet_authorization_false",
        ),
        (
            "authorization_boundary.transaction_authorized",
            "release_transaction_authorization_false",
        ),
    ),
)
def test_authorization_flags_must_be_present_and_false(
    tmp_path,
    field,
    expected_check,
) -> None:
    release, history, policy = valid_chain(tmp_path)
    document = json.loads(release.read_text())
    _, child = field.split(".", 1)
    document["authorization_boundary"].pop(child)
    write_json(release, document)
    report = validate(release, history, policy)
    assert not report["valid"]
    assert expected_check in checks(report)


def test_wrong_or_missing_immediate_predecessor_fails(tmp_path) -> None:
    release, history, policy = valid_chain(tmp_path)
    mutate(
        release,
        "supersedes_release_implementation_approval_sha256",
        "0" * 64,
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_predecessor_matches" in checks(report)
    assert "release_chain_valid" in checks(report)


def test_missing_immediate_predecessor_fails(tmp_path) -> None:
    release, history, policy = valid_chain(tmp_path)
    mutate(
        release,
        "supersedes_release_implementation_approval_sha256",
        _MISSING,
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_predecessor_matches" in checks(report)
    assert "release_chain_valid" in checks(report)


def test_skipped_predecessor_fails_even_if_marker_anchor_is_reached(
    tmp_path,
) -> None:
    release, history, policy = valid_chain(tmp_path)
    mutate(
        release,
        "supersedes_release_implementation_approval_sha256",
        policy.marker_original_approval_sha256,
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_predecessor_matches" in checks(report)


def test_unrelated_middle_artifact_with_copied_marker_hashes_fails(
    tmp_path,
) -> None:
    release, history, policy = valid_chain(tmp_path)
    prior_path = history / f"{policy.expected_predecessor_sha256}.json"
    prior = json.loads(prior_path.read_text())
    prior["artifact_type"] = "generic_approval"
    replacement = tmp_path / "unrelated.json"
    replacement_hash = write_json(replacement, prior)
    (history / f"{replacement_hash}.json").write_bytes(replacement.read_bytes())
    mutate(
        release,
        "supersedes_release_implementation_approval_sha256",
        replacement_hash,
    )
    policy = ReleaseApprovalPolicy(
        **{
            **policy.__dict__,
            "expected_predecessor_sha256": replacement_hash,
        }
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_artifact_type_matches" in checks(report)
    assert "release_rfc_identity_matches" in checks(report)


def test_unrelated_current_artifact_with_copied_marker_hashes_fails(
    tmp_path,
) -> None:
    release, history, policy = valid_chain(tmp_path)
    mutate(release, "artifact_type", "rfc008_collection_authorization")
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_artifact_type_matches" in checks(report)


def test_duplicate_conflicting_json_field_fails_closed(tmp_path) -> None:
    release, history, policy = valid_chain(tmp_path)
    raw = release.read_text()
    release.write_text(
        raw.replace(
            '"artifact_type": "rfc008_implementation_release_approval",',
            '"artifact_type": "generic_approval",\n'
            '  "artifact_type": "rfc008_implementation_release_approval",',
            1,
        )
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_chain_valid" in checks(report)


@pytest.mark.parametrize("kind", ("reordered", "duplicate", "circular"))
def test_malformed_chain_topologies_fail_closed(tmp_path, kind) -> None:
    release, history, policy = valid_chain(tmp_path)
    if kind == "reordered":
        link = policy.marker_original_approval_sha256
    else:
        link = hashlib.sha256(release.read_bytes()).hexdigest()
    mutate(
        release,
        "supersedes_release_implementation_approval_sha256",
        link,
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert (
        "release_predecessor_matches" in checks(report)
        or "release_chain_valid" in checks(report)
    )


def test_broken_original_marker_approval_termination_fails(tmp_path) -> None:
    release, history, policy = valid_chain(tmp_path)
    prior_path = history / f"{policy.expected_predecessor_sha256}.json"
    prior = json.loads(prior_path.read_text())
    prior["supersedes_release_implementation_approval_sha256"] = "0" * 64
    replacement = tmp_path / "broken.json"
    replacement_hash = write_json(replacement, prior)
    (history / f"{replacement_hash}.json").write_bytes(replacement.read_bytes())
    mutate(
        release,
        "supersedes_release_implementation_approval_sha256",
        replacement_hash,
    )
    policy = ReleaseApprovalPolicy(
        **{
            **policy.__dict__,
            "expected_predecessor_sha256": replacement_hash,
        }
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_chain_valid" in checks(report)


def test_terminal_original_marker_approval_is_valid(tmp_path) -> None:
    release, history, policy = valid_chain(tmp_path)
    original = history / f"{policy.marker_original_approval_sha256}.json"
    report = validate_release_approval_chain(
        release_path=original,
        history_directory=history,
        policy=policy,
    )
    assert report["valid"]
