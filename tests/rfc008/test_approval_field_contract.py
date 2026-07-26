from __future__ import annotations

import json
from pathlib import Path

import pytest

from orev3.rfc008.approval import generate_release_approval
from orev3.rfc008.approval_contract import (
    SCHEMA2_APPROVAL_FIELDS,
    authority_manifest,
    get_path,
    leaf_paths,
    render_authority_markdown_table,
)
from .test_approval_supersession import (
    checks,
    valid_chain,
    validate,
    write_json,
)


MANIFEST_PATH = (
    Path(__file__).parents[2]
    / "docs/research/rfc008/schema2_approval_field_authority_v1.json"
)
RUNBOOK_PATH = (
    Path(__file__).parents[2]
    / "docs/research/RFC-008-OPERATOR-RUNBOOK.md"
)
INFORMATIONAL_PATHS = {
    field.path
    for field in SCHEMA2_APPROVAL_FIELDS
    if field.authority == "informational"
}
AUTHORITATIVE_FIELDS = tuple(
    field
    for field in SCHEMA2_APPROVAL_FIELDS
    if field.authority != "informational"
)
_WRONG_VALUE = object()
CLASS_MUTATIONS = {
    "release_bound_exact": (
        "wrong_value",
        "missing",
        "null",
        "empty",
        "wrong_type",
        "alternate_alias",
        "duplicate_conflict",
    ),
    "release_bound_derived": (
        "wrong_value",
        "copied_release_value",
        "missing",
        "malformed",
        "wrong_type",
        "derived_mismatch",
    ),
    "authorization": (
        "true",
        "missing",
        "null",
        "string_false",
        "integer_zero",
        "empty",
        "duplicate_conflict",
    ),
    "policy_bound": (
        "wrong_policy_value",
        "unsupported_version",
        "missing",
        "malformed",
        "wrong_type",
        "unrecognized_identifier",
    ),
}
AUTHORITATIVE_MUTATIONS = tuple(
    (field, mutation)
    for field in AUTHORITATIVE_FIELDS
    for mutation in CLASS_MUTATIONS[field.authority]
)


def _delete_path(value: dict[str, object], path: str) -> None:
    parts = path.split(".")
    current = value
    for part in parts[:-1]:
        current = current[part]  # type: ignore[assignment]
    current.pop(parts[-1])


def _set_path(value: dict[str, object], path: str, replacement: object) -> None:
    parts = path.split(".")
    current = value
    for part in parts[:-1]:
        current = current[part]  # type: ignore[assignment]
    current[parts[-1]] = replacement


def _wrong_type(json_type: str) -> object:
    return {
        "string": 7,
        "integer": "7",
        "boolean": "false",
    }[json_type]


def _wrong_value(actual: object) -> object:
    if type(actual) is str:
        return f"{actual}-mutated"
    if type(actual) is int:
        return actual + 1
    if type(actual) is bool:
        return not actual
    raise AssertionError(f"Unsupported registered value: {actual!r}")


def _valid_looking_wrong(actual: object) -> object:
    if type(actual) is str:
        if len(actual) in {40, 64} and all(
            character in "0123456789abcdef" for character in actual
        ):
            replacement = "f" * len(actual)
            return "e" * len(actual) if replacement == actual else replacement
        return "rfc008-unrecognized-v999"
    return _wrong_value(actual)


def _write_duplicate(
    release: Path,
    field_path: str,
    replacement: object,
) -> None:
    document = json.loads(release.read_text())
    actual = get_path(document, field_path)
    leaf = field_path.rsplit(".", 1)[-1]
    raw = release.read_text()
    original = f'"{leaf}": {json.dumps(actual, allow_nan=False)}'
    duplicate = (
        f'"{leaf}": {json.dumps(replacement, allow_nan=False)},\n'
        f'    "{leaf}": {json.dumps(actual, allow_nan=False)}'
    )
    assert original in raw
    release.write_text(raw.replace(original, duplicate, 1))


def _mutated_report(
    tmp_path: Path,
    field_path: str,
    replacement: object,
    *,
    missing: bool = False,
    alias: bool = False,
    duplicate: bool = False,
):
    release, history, policy = valid_chain(tmp_path)
    document = json.loads(release.read_text())
    if duplicate:
        _write_duplicate(release, field_path, replacement)
    elif missing:
        _delete_path(document, field_path)
        write_json(release, document)
    elif alias:
        actual = get_path(document, field_path)
        _delete_path(document, field_path)
        alias_path = f"{field_path}_alias"
        _set_path(document, alias_path, actual)
        write_json(release, document)
    else:
        if replacement is _WRONG_VALUE:
            replacement = _wrong_value(get_path(document, field_path))
        _set_path(document, field_path, replacement)
        write_json(release, document)
    return validate(release, history, policy)


def _flatten_in_order(
    value: dict[str, object],
    prefix: str = "",
) -> list[str]:
    paths: list[str] = []
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            paths.extend(_flatten_in_order(item, path))
        else:
            paths.append(path)
    return paths


def test_registry_is_unique_complete_and_documented() -> None:
    paths = [field.path for field in SCHEMA2_APPROVAL_FIELDS]
    assert len(paths) == 54
    assert len(paths) == len(set(paths))
    assert all(field.required for field in SCHEMA2_APPROVAL_FIELDS)
    assert all(field.generated for field in SCHEMA2_APPROVAL_FIELDS)
    assert all(field.documented for field in SCHEMA2_APPROVAL_FIELDS)
    assert json.loads(MANIFEST_PATH.read_text()) == authority_manifest()
    assert render_authority_markdown_table() in RUNBOOK_PATH.read_text()


def test_generator_uses_registry_for_exact_deterministic_shape(tmp_path) -> None:
    release, _, policy = valid_chain(tmp_path)
    existing = json.loads(release.read_text())
    generated = generate_release_approval(
        policy=policy,
        audit_correction_identifier=get_path(
            existing, "audit_correction_identifier"
        ),
        focused_lifecycle_test_count=get_path(
            existing, "verification.focused_lifecycle_test_count"
        ),
        rfc008_test_count=get_path(
            existing, "verification.rfc008_test_count"
        ),
        full_test_count=get_path(existing, "verification.full_test_count"),
    )
    expected_paths = [field.path for field in SCHEMA2_APPROVAL_FIELDS]
    assert leaf_paths(generated) == set(expected_paths)
    assert _flatten_in_order(generated) == expected_paths
    assert generated == existing


@pytest.mark.parametrize(
    ("field", "mutation"),
    AUTHORITATIVE_MUTATIONS,
    ids=lambda item: item.path if hasattr(item, "path") else item,
)
def test_every_authoritative_field_mutation_fails_closed(
    tmp_path,
    field,
    mutation,
) -> None:
    release, _, _ = valid_chain(tmp_path / "source")
    actual = get_path(json.loads(release.read_text()), field.path)
    if mutation == "missing":
        report = _mutated_report(
            tmp_path, field.path, None, missing=True
        )
    elif mutation == "null":
        report = _mutated_report(tmp_path, field.path, None)
    elif mutation in {"wrong_type", "string_false"}:
        report = _mutated_report(
            tmp_path, field.path, _wrong_type(field.json_type)
        )
    elif mutation == "integer_zero":
        report = _mutated_report(tmp_path, field.path, 0)
    elif mutation == "true":
        report = _mutated_report(tmp_path, field.path, True)
    elif mutation in {"empty", "malformed"}:
        report = _mutated_report(tmp_path, field.path, "")
    elif mutation == "alternate_alias":
        report = _mutated_report(
            tmp_path, field.path, None, alias=True
        )
    elif mutation == "duplicate_conflict":
        report = _mutated_report(
            tmp_path,
            field.path,
            _valid_looking_wrong(actual),
            duplicate=True,
        )
    elif mutation in {
        "copied_release_value",
        "derived_mismatch",
        "wrong_policy_value",
        "unsupported_version",
        "unrecognized_identifier",
    }:
        report = _mutated_report(
            tmp_path, field.path, _valid_looking_wrong(actual)
        )
    else:
        report = _mutated_report(tmp_path, field.path, _WRONG_VALUE)
    assert not report["valid"]
    if mutation == "duplicate_conflict":
        assert "release_chain_valid" in checks(report)
    else:
        assert field.failure_reason in checks(report)


@pytest.mark.parametrize(
    "field",
    [
        field
        for field in SCHEMA2_APPROVAL_FIELDS
        if field.authority == "informational"
    ],
    ids=lambda field: field.path,
)
@pytest.mark.parametrize("mutation", ("missing", "null", "wrong_type"))
def test_informational_fields_are_required_and_typed(
    tmp_path,
    field,
    mutation,
) -> None:
    if mutation == "missing":
        report = _mutated_report(
            tmp_path, field.path, None, missing=True
        )
    elif mutation == "null":
        report = _mutated_report(tmp_path, field.path, None)
    else:
        report = _mutated_report(
            tmp_path, field.path, _wrong_type(field.json_type)
        )
    assert not report["valid"]
    assert field.failure_reason in checks(report)


@pytest.mark.parametrize(
    ("path", "value"),
    (
        ("audit_correction_identifier", "rfc008-independent-review-v2"),
        ("verification.focused_lifecycle_test_count", 123),
        ("verification.rfc008_test_count", 456),
        ("verification.full_test_count", 789),
    ),
)
def test_valid_informational_alternatives_do_not_grant_authority(
    tmp_path,
    path,
    value,
) -> None:
    report = _mutated_report(tmp_path, path, value)
    assert report["valid"]


@pytest.mark.parametrize(
    ("path", "value"),
    (
        ("audit_correction_identifier", "free form"),
        ("verification.focused_lifecycle_test_count", -1),
        ("verification.rfc008_test_count", -1),
        ("verification.full_test_count", -1),
    ),
)
def test_malformed_informational_values_fail_closed(
    tmp_path,
    path,
    value,
) -> None:
    report = _mutated_report(tmp_path, path, value)
    assert not report["valid"]
    assert "release_informational_metadata_valid" in checks(report)


@pytest.mark.parametrize(
    ("path", "value"),
    (
        ("unknown_top_level", True),
        ("verification.unknown_nested", 1),
        ("authorization_boundary.claim_authorized", False),
        ("database_schema", 3),
    ),
)
def test_unknown_and_alias_fields_are_rejected(
    tmp_path,
    path,
    value,
) -> None:
    release, history, policy = valid_chain(tmp_path)
    document = json.loads(release.read_text())
    _set_path(document, path, value)
    write_json(release, document)
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_unknown_field_forbidden" in checks(report)


def test_nested_duplicate_json_field_is_rejected_before_mapping(
    tmp_path,
) -> None:
    release, history, policy = valid_chain(tmp_path)
    raw = release.read_text()
    release.write_text(
        raw.replace(
            '"full_test_count": 0,',
            '"full_test_count": 0,\n    "full_test_count": 999,',
            1,
        )
    )
    report = validate(release, history, policy)
    assert not report["valid"]
    assert "release_chain_valid" in checks(report)


def test_mutation_inventory_has_no_uncovered_active_fields() -> None:
    exercised = {field.path for field in AUTHORITATIVE_FIELDS}
    exercised.update(INFORMATIONAL_PATHS)
    assert exercised == {
        field.path for field in SCHEMA2_APPROVAL_FIELDS
    }


def test_full_mutation_harness_accounting_is_frozen() -> None:
    authoritative_attempts = len(AUTHORITATIVE_MUTATIONS)
    informational_rejections = len(INFORMATIONAL_PATHS) * 4
    informational_acceptances = len(INFORMATIONAL_PATHS)
    assert {
        "total_registered_fields": len(SCHEMA2_APPROVAL_FIELDS),
        "authoritative_fields": len(AUTHORITATIVE_FIELDS),
        "informational_fields": len(INFORMATIONAL_PATHS),
        "legacy_only_fields": 0,
        "forbidden_fields": 0,
        "mutations_attempted": (
            authoritative_attempts
            + informational_rejections
            + informational_acceptances
        ),
        "expected_rejections": (
            authoritative_attempts + informational_rejections
        ),
        "expected_informational_acceptances": informational_acceptances,
        "unexpected_acceptances": 0,
        "unexpected_rejections": 0,
        "uncovered_fields": 0,
    } == {
        "total_registered_fields": 54,
        "authoritative_fields": 50,
        "informational_fields": 4,
        "legacy_only_fields": 0,
        "forbidden_fields": 0,
        "mutations_attempted": 336,
        "expected_rejections": 332,
        "expected_informational_acceptances": 4,
        "unexpected_acceptances": 0,
        "unexpected_rejections": 0,
        "uncovered_fields": 0,
    }


def _assert_rejected(
    tmp_path: Path,
    path: str,
    value: object,
    reason: str,
    *,
    missing: bool = False,
) -> None:
    report = _mutated_report(
        tmp_path, path, value, missing=missing
    )
    assert not report["valid"]
    assert reason in checks(report)


def test_wrong_operational_burn_in_repository_commit(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "validated_operational_burn_in_repository_commit",
        "f" * 40,
        "release_burn_in_repository_matches",
    )


def test_missing_operational_burn_in_repository_commit(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "validated_operational_burn_in_repository_commit",
        None,
        "release_burn_in_repository_matches",
        missing=True,
    )


def test_unrelated_valid_operational_burn_in_repository_commit(
    tmp_path,
) -> None:
    test_wrong_operational_burn_in_repository_commit(tmp_path)


def test_malformed_operational_burn_in_repository_commit(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "validated_operational_burn_in_repository_commit",
        "not-a-commit",
        "release_burn_in_repository_matches",
    )


def test_mutated_audit_version_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "audit_version",
        "rfc008-release-preflight-v999",
        "release_audit_version_matches",
    )


def test_wrong_type_audit_version_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "audit_version",
        5,
        "release_audit_version_matches",
    )


def test_mutated_audit_correction_identifier_remains_valid(
    tmp_path,
) -> None:
    report = _mutated_report(
        tmp_path,
        "audit_correction_identifier",
        "rfc008-human-readable-correction-v2",
    )
    assert report["valid"]


def test_wrong_type_audit_correction_identifier_is_rejected(
    tmp_path,
) -> None:
    _assert_rejected(
        tmp_path,
        "audit_correction_identifier",
        1,
        "release_informational_metadata_valid",
    )


def test_mutated_resolver_version_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "resolver_version",
        "rfc008-finalized-resolver-v999",
        "release_resolver_version_matches",
    )


def test_mutated_decoder_version_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "decoder_version",
        "ore-round-decoder-v999",
        "release_decoder_version_matches",
    )


def test_mutated_minimum_operational_sample_size_is_rejected(
    tmp_path,
) -> None:
    _assert_rejected(
        tmp_path,
        "minimum_operational_sample_size",
        6,
        "release_minimum_sample_size_matches",
    )


def test_too_small_operational_sample_size_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "minimum_operational_sample_size",
        4,
        "release_minimum_sample_size_matches",
    )


def test_wrong_type_operational_sample_size_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "minimum_operational_sample_size",
        "5",
        "release_minimum_sample_size_matches",
    )


def test_mutated_protected_process_policy_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "protected_process_policy.48404.role",
        "replacement_observer",
        "release_protected_process_policy_matches",
    )


def test_unrecognized_protected_process_policy_is_rejected(
    tmp_path,
) -> None:
    _assert_rejected(
        tmp_path,
        "protected_process_policy.78317.sanitized_command_identity",
        "unrecognized collector",
        "release_protected_process_policy_matches",
    )


def test_modified_authoritative_verification_member_is_rejected(
    tmp_path,
) -> None:
    _assert_rejected(
        tmp_path,
        "verification.external_rpc_burn_in_performed",
        False,
        "release_operational_burn_in_matches",
    )


def test_modified_informational_verification_member_remains_valid(
    tmp_path,
) -> None:
    report = _mutated_report(
        tmp_path, "verification.full_test_count", 999
    )
    assert report["valid"]


def test_missing_required_verification_member_is_rejected(tmp_path) -> None:
    _assert_rejected(
        tmp_path,
        "verification.fixture_resolver_burn_in_required",
        None,
        "release_verification_policy_matches",
        missing=True,
    )
