from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal


AuthorityClass = Literal[
    "release_bound_exact",
    "release_bound_derived",
    "authorization",
    "policy_bound",
    "informational",
    "legacy_compatibility",
    "forbidden",
]


@dataclass(frozen=True)
class ApprovalField:
    path: str
    authority: AuthorityClass
    json_type: Literal["string", "integer", "boolean"]
    allowed_schema_versions: tuple[int, ...]
    required: bool
    applicability: Literal["active", "active_and_legacy", "legacy"]
    accepted_in_active_schema2: bool
    legacy_only: bool
    affects_acceptance: bool
    exact_expected_value: bool
    independently_recomputed: bool
    authorization_bearing: bool
    informational_only: bool
    deprecated_or_forbidden: bool
    validation_source: str
    validator: str
    failure_reason: str
    mutation_policy: str
    canonical: str
    parser_behavior: str
    generation_behavior: str
    duplicate_keys_possible_in_raw_json: bool
    participates_in_approval_hash: bool
    generated: bool = True
    documented: bool = True


def _field(
    path: str,
    authority: AuthorityClass,
    json_type: Literal["string", "integer", "boolean"],
    source: str,
    reason: str,
    mutation: str = "reject_mutation",
    applicability: Literal[
        "active", "active_and_legacy", "legacy"
    ] = "active_and_legacy",
) -> ApprovalField:
    active = applicability != "legacy"
    legacy = applicability != "active"
    return ApprovalField(
        path=path,
        authority=authority,
        json_type=json_type,
        allowed_schema_versions=(1, 2) if legacy and active else (1,) if legacy else (2,),
        required=True,
        applicability=applicability,
        accepted_in_active_schema2=active,
        legacy_only=not active,
        affects_acceptance=authority != "informational",
        exact_expected_value=authority
        in {"release_bound_exact", "authorization", "policy_bound"},
        independently_recomputed=authority == "release_bound_derived",
        authorization_bearing=authority == "authorization",
        informational_only=authority == "informational",
        deprecated_or_forbidden=authority == "forbidden",
        validation_source=source,
        validator=(
            "format_only"
            if authority == "informational"
            else "derive_and_compare"
            if authority == "release_bound_derived"
            else "exact_value"
        ),
        failure_reason=reason,
        mutation_policy=mutation,
        canonical=(
            "lowercase_full_sha256"
            if "sha256" in path or path.endswith("_fingerprint")
            else "lowercase_full_git_commit"
            if path.endswith("_commit")
            else "exact_json_boolean"
            if json_type == "boolean"
            else "non_negative_integer"
            if json_type == "integer"
            else "exact_utf8_string"
        ),
        parser_behavior="strict_required_leaf",
        generation_behavior="emit_in_registry_order",
        duplicate_keys_possible_in_raw_json=True,
        participates_in_approval_hash=True,
    )


SCHEMA2_APPROVAL_FIELDS: tuple[ApprovalField, ...] = (
    _field("artifact_type", "release_bound_exact", "string", "constant", "release_artifact_type_matches"),
    _field("schema_version", "release_bound_exact", "integer", "constant", "release_schema_supported"),
    _field("rfc_identifier", "release_bound_exact", "string", "constant", "release_rfc_identity_matches", applicability="active"),
    _field("repository_branch", "release_bound_exact", "string", "git_branch", "release_repository_matches", applicability="active"),
    _field("status", "release_bound_exact", "string", "constant", "release_status_matches"),
    _field("approved_implementation_commit", "release_bound_derived", "string", "git_approval_parent", "approved_implementation_commit_matches"),
    _field("approval_commit_policy", "policy_bound", "string", "constant", "release_commit_policy_matches"),
    _field("supersedes_release_implementation_approval_sha256", "release_bound_derived", "string", "git_parent_approval", "release_predecessor_matches"),
    _field("validated_production_marker_sha256", "release_bound_derived", "string", "marker_bytes", "release_marker_hash_matches"),
    _field("validated_production_marker_sidecar_sha256", "release_bound_derived", "string", "marker_sidecar_bytes", "release_marker_sidecar_hash_matches"),
    _field("validated_production_marker_repository_commit", "release_bound_derived", "string", "marker_document", "release_repository_matches"),
    _field("validated_production_marker_release_approval_sha256", "release_bound_derived", "string", "marker_document", "release_chain_valid"),
    _field("validated_production_marker_collection_authorized", "authorization", "boolean", "marker_document_false", "release_collection_authorization_false"),
    _field("validated_operational_burn_in_evidence_sha256", "release_bound_derived", "string", "burn_in_evidence_bytes", "release_burn_in_evidence_matches"),
    _field("validated_operational_burn_in_ledger_sha256", "release_bound_derived", "string", "burn_in_ledger_bytes", "release_burn_in_ledger_matches"),
    _field("validated_operational_burn_in_repository_commit", "release_bound_derived", "string", "burn_in_evidence_document", "release_burn_in_repository_matches"),
    _field("frozen_approval_manifest_sha256", "release_bound_derived", "string", "approval_manifest_bytes", "release_approval_manifest_matches"),
    _field("configuration_fingerprint", "release_bound_derived", "string", "experiment_config", "release_experiment_fingerprint_matches"),
    _field("candidate_configuration_sha256", "release_bound_derived", "string", "marker_document", "release_candidate_hash_matches"),
    _field("resolver_configuration_sha256", "release_bound_derived", "string", "resolver_config", "release_resolver_fingerprint_matches"),
    _field("audit_version", "policy_bound", "string", "constant", "release_audit_version_matches"),
    _field("audit_correction_identifier", "informational", "string", "format_only", "release_informational_metadata_valid", "accept_valid_alternative"),
    _field("resolver_version", "policy_bound", "string", "resolver_config", "release_resolver_version_matches"),
    _field("decoder_version", "policy_bound", "string", "resolver_config", "release_decoder_version_matches"),
    _field("database_family", "release_bound_exact", "string", "constant", "release_database_schema_matches"),
    _field("database_schema_version", "release_bound_exact", "integer", "constant", "release_database_schema_matches"),
    _field("migration_set_sha256", "release_bound_derived", "string", "migration_registry", "release_migration_set_matches"),
    _field("burn_in_evidence_schema_version", "release_bound_exact", "integer", "constant", "release_evidence_schema_matches"),
    _field("marker_schema_version", "release_bound_exact", "integer", "constant", "release_marker_schema_matches"),
    _field("minimum_operational_sample_size", "policy_bound", "integer", "constant", "release_minimum_sample_size_matches"),
    _field("protected_process_policy.48404.role", "policy_bound", "string", "protected_process_registry", "release_protected_process_policy_matches"),
    _field("protected_process_policy.48404.sanitized_command_identity", "policy_bound", "string", "protected_process_registry", "release_protected_process_policy_matches"),
    _field("protected_process_policy.48405.role", "policy_bound", "string", "protected_process_registry", "release_protected_process_policy_matches"),
    _field("protected_process_policy.48405.sanitized_command_identity", "policy_bound", "string", "protected_process_registry", "release_protected_process_policy_matches"),
    _field("protected_process_policy.78317.role", "policy_bound", "string", "protected_process_registry", "release_protected_process_policy_matches"),
    _field("protected_process_policy.78317.sanitized_command_identity", "policy_bound", "string", "protected_process_registry", "release_protected_process_policy_matches"),
    _field("cli_version", "release_bound_exact", "string", "constant", "release_cli_contract_matches"),
    _field("cli_sha256", "release_bound_derived", "string", "cli_bytes", "release_cli_hash_matches"),
    _field("runbook_version", "release_bound_exact", "string", "constant", "release_runbook_version_matches"),
    _field("runbook_sha256", "release_bound_derived", "string", "runbook_bytes", "release_runbook_hash_matches"),
    _field("verification.focused_lifecycle_test_count", "informational", "integer", "format_only", "release_informational_metadata_valid", "accept_valid_alternative"),
    _field("verification.rfc008_test_count", "informational", "integer", "format_only", "release_informational_metadata_valid", "accept_valid_alternative"),
    _field("verification.full_test_count", "informational", "integer", "format_only", "release_informational_metadata_valid", "accept_valid_alternative"),
    _field("verification.fixture_resolver_burn_in_required", "policy_bound", "boolean", "constant", "release_verification_policy_matches"),
    _field("verification.operational_resolver_burn_in_required_before_marker", "policy_bound", "boolean", "constant", "release_verification_policy_matches"),
    _field("verification.external_rpc_burn_in_performed", "release_bound_derived", "boolean", "burn_in_evidence_document", "release_operational_burn_in_matches"),
    _field("authorization_boundary.implementation_authorized", "policy_bound", "boolean", "constant", "release_implementation_policy_matches"),
    _field("authorization_boundary.fixture_burn_in_authorized", "policy_bound", "boolean", "constant", "release_fixture_burn_in_policy_matches"),
    _field("authorization_boundary.operational_rpc_burn_in_authorized", "policy_bound", "boolean", "constant", "release_operational_rpc_policy_matches"),
    _field("authorization_boundary.marker_creation_authorized", "policy_bound", "boolean", "constant", "release_marker_creation_policy_matches"),
    _field("authorization_boundary.collection_authorized", "authorization", "boolean", "explicit_false", "release_collection_authorization_false"),
    _field("authorization_boundary.wallet_access_authorized", "authorization", "boolean", "explicit_false", "release_wallet_authorization_false"),
    _field("authorization_boundary.live_action_authorized", "authorization", "boolean", "explicit_false", "release_live_authorization_false"),
    _field("authorization_boundary.transaction_authorized", "authorization", "boolean", "explicit_false", "release_transaction_authorization_false", applicability="active"),
)


SCHEMA2_FIELD_BY_PATH = {
    field.path: field for field in SCHEMA2_APPROVAL_FIELDS
}
if len(SCHEMA2_FIELD_BY_PATH) != len(SCHEMA2_APPROVAL_FIELDS):
    raise RuntimeError("Duplicate RFC-008 approval field registry path")


def get_path(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def set_path(value: dict[str, Any], path: str, item: Any) -> None:
    parts = path.split(".")
    current = value
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = item


def leaf_paths(value: dict[str, Any], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            paths.update(leaf_paths(item, path))
        else:
            paths.add(path)
    return paths


def active_schema2_structure_failures(
    value: dict[str, Any],
) -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    registered = set(SCHEMA2_FIELD_BY_PATH)
    prefixes = {
        ".".join(path.split(".")[:index])
        for path in registered
        for index in range(1, len(path.split(".")))
    }

    def visit(document: dict[str, Any], prefix: str = "") -> None:
        for key, item in document.items():
            path = f"{prefix}.{key}" if prefix else key
            if path not in registered and path not in prefixes:
                failures.append(
                    (
                        "release_unknown_field_forbidden",
                        f"Unknown active approval field: {path}",
                    )
                )
            if isinstance(item, dict):
                visit(item, path)

    visit(value)
    present = leaf_paths(value)
    json_types = {"string": str, "integer": int, "boolean": bool}
    for field in SCHEMA2_APPROVAL_FIELDS:
        if field.path not in present:
            failures.append(
                (
                    field.failure_reason,
                    f"Required active approval field is missing: {field.path}",
                )
            )
            continue
        actual = get_path(value, field.path)
        if type(actual) is not json_types[field.json_type]:
            failures.append(
                (
                    field.failure_reason,
                    f"Active approval field has wrong type: {field.path}",
                )
            )
    return failures


def generate_schema2_approval(values: dict[str, Any]) -> dict[str, Any]:
    expected = {
        field.path
        for field in SCHEMA2_APPROVAL_FIELDS
        if field.applicability != "legacy" and field.generated
    }
    if set(values) != expected:
        missing = sorted(expected - set(values))
        unknown = sorted(set(values) - expected)
        raise ValueError(
            f"Approval generation field mismatch; missing={missing}, "
            f"unknown={unknown}"
        )
    document: dict[str, Any] = {}
    for field in SCHEMA2_APPROVAL_FIELDS:
        if field.path in values and field.generated:
            set_path(document, field.path, values[field.path])
    return document


def decode_approval_json(raw: bytes | str) -> dict[str, Any]:
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


def authority_manifest() -> dict[str, Any]:
    counts: dict[str, int] = {}
    for field in SCHEMA2_APPROVAL_FIELDS:
        counts[field.authority] = counts.get(field.authority, 0) + 1
    fields = []
    for field in SCHEMA2_APPROVAL_FIELDS:
        entry = asdict(field)
        entry["allowed_schema_versions"] = list(
            entry["allowed_schema_versions"]
        )
        fields.append(entry)
    return {
        "artifact_type": "rfc008_schema2_approval_field_authority",
        "schema_version": 1,
        "active_leaf_field_count": len(SCHEMA2_APPROVAL_FIELDS),
        "authority_counts": dict(sorted(counts.items())),
        "unknown_active_field_policy": "reject",
        "duplicate_key_policy": "reject_before_mapping",
        "legacy_policy": (
            "schema_1_only_when_hash_addressed_in_immutable_history"
        ),
        "fields": fields,
    }


def render_authority_markdown_table() -> str:
    rows = [
        "| Field path | Authority class | Required | Validation source | "
        "Applicability | Mutation behavior |",
        "|---|---|---:|---|---|---|",
    ]
    for field in SCHEMA2_APPROVAL_FIELDS:
        rows.append(
            f"| `{field.path}` | `{field.authority}` | yes | "
            f"`{field.validation_source}` | `{field.applicability}` | "
            f"`{field.mutation_policy}` |"
        )
    return "\n".join(rows)
