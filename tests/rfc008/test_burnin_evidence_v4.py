from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from orev3.rfc008.schemas import ResolverBurnInEvidence

from .test_preflight_release import write_release_and_burn_in


def valid_evidence(tmp_path, config) -> dict:
    _, path = write_release_and_burn_in(tmp_path, config)
    return ResolverBurnInEvidence.model_validate_json(
        path.read_text()
    ).model_dump(mode="python")


def rejected(value: dict) -> None:
    with pytest.raises(ValidationError):
        ResolverBurnInEvidence.model_validate(value)


@pytest.mark.parametrize(
    "field",
    ("deployment_vector_validated", "accounting_validated"),
)
def test_false_per_round_validation_fails_closed(tmp_path, config, field):
    value = valid_evidence(tmp_path, config)
    value["operational"]["rounds"][0][field] = False
    rejected(value)


@pytest.mark.parametrize(
    "field",
    ("deployment_vector_validated", "accounting_validated"),
)
def test_missing_per_round_validation_fails_closed(tmp_path, config, field):
    value = valid_evidence(tmp_path, config)
    value["operational"]["rounds"][0].pop(field)
    rejected(value)


@pytest.mark.parametrize(
    "field",
    (
        "deployment_validation_pass_count",
        "accounting_validation_pass_count",
    ),
)
def test_validation_aggregate_mismatch_fails_closed(tmp_path, config, field):
    value = valid_evidence(tmp_path, config)
    value["operational"][field] -= 1
    rejected(value)


def test_zero_attempt_success_fails_closed(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["operational"]["rounds"][0]["attempt_count"] = 0
    rejected(value)


def test_missing_attempt_record_fails_closed(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["operational_attempts"] = value["operational_attempts"][:-1]
    rejected(value)


def test_missing_provider_request_fails_closed(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["operational_requests"] = value["operational_requests"][:-1]
    rejected(value)


@pytest.mark.parametrize("delta", (-1, 1))
def test_rpc_total_mutation_fails_closed(tmp_path, config, delta):
    value = valid_evidence(tmp_path, config)
    value["real_rpc_request_counts"]["total"] += delta
    rejected(value)


def test_retry_total_mutation_fails_closed(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["real_rpc_request_counts"]["retried_requests"] = 1
    rejected(value)


def test_failed_response_total_mutation_fails_closed(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["real_rpc_request_counts"]["failed_responses"] = 1
    rejected(value)


def test_provider_trace_request_link_must_reconcile(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["operational"]["rounds"][0]["provider_evidence"][0][
        "request_id"
    ] = "missing-request"
    rejected(value)


def test_attempt_terminal_state_must_reconcile(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["operational_attempts"][0]["status"] = "retry"
    rejected(value)


def test_fixture_request_cannot_be_counted_as_operational(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    request = copy.deepcopy(value["operational_requests"][-1])
    request["request_id"] = "fixture-misclassified"
    request["operational"] = False
    value["operational_requests"] = value["operational_requests"] + (
        request,
    )
    rejected(value)


def test_valid_attempt_request_history_passes(tmp_path, config):
    ResolverBurnInEvidence.model_validate(valid_evidence(tmp_path, config))


def test_conflict_and_quarantine_identity_collision_fails(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["quarantine"]["quarantine_round_id"] = value["conflict"]["round_id"]
    rejected(value)


@pytest.mark.parametrize("controlled", ("conflict", "quarantine"))
def test_controlled_round_overlap_fails(tmp_path, config, controlled):
    value = valid_evidence(tmp_path, config)
    round_id = value["operational"]["selected_round_ids"][0]
    if controlled == "conflict":
        value["conflict"]["round_id"] = round_id
    else:
        value["quarantine"]["quarantine_round_id"] = round_id
    rejected(value)


def test_copied_conflict_cannot_be_quarantine(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["quarantine"] = copy.deepcopy(value["conflict"])
    rejected(value)


@pytest.mark.parametrize(
    "field",
    (
        "overwrite_refused",
        "provenance_retained",
        "disagreement_details_retained",
        "terminal_conflict_persisted",
        "overwrite_attempted",
        "later_success_replacement_refused",
        "primary_analysis_ineligible",
    ),
)
def test_conflict_pass_is_derived_from_every_subcheck(
    tmp_path, config, field
):
    value = valid_evidence(tmp_path, config)
    value["conflict"][field] = False
    rejected(value)


def test_conflict_overwrite_missing_or_pass_mismatch_fails(
    tmp_path, config
):
    missing = valid_evidence(tmp_path, config)
    missing["conflict"].pop("overwrite_refused")
    rejected(missing)
    serialized_false = valid_evidence(tmp_path, config)
    serialized_false["conflict"]["conflict_test_passed"] = False
    rejected(serialized_false)
    recomputed_false = valid_evidence(tmp_path, config)
    recomputed_false["conflict"][
        "recomputed_conflict_test_passed"
    ] = False
    rejected(recomputed_false)


def test_consistently_failed_conflict_is_non_authoritative(
    tmp_path, config
):
    value = valid_evidence(tmp_path, config)
    value["conflict"]["overwrite_refused"] = False
    value["conflict"]["recomputed_conflict_test_passed"] = False
    value["conflict"]["conflict_test_passed"] = False
    value["primary_authoritative_capable"] = False
    parsed = ResolverBurnInEvidence.model_validate(value)
    assert not parsed.conflict.recomputed_conflict_test_passed
    assert not parsed.primary_authoritative_capable


@pytest.mark.parametrize(
    "field",
    (
        "expiry_reached",
        "production_transition_invoked",
        "quarantine_restart_persistence",
        "overwrite_attempted",
        "quarantine_overwrite_refused",
        "later_success_replacement_refused",
        "primary_analysis_ineligible",
    ),
)
def test_quarantine_pass_is_derived_from_every_subcheck(
    tmp_path, config, field
):
    value = valid_evidence(tmp_path, config)
    value["quarantine"][field] = False
    rejected(value)


def test_quarantine_terminal_state_and_pass_mismatch_fail(
    tmp_path, config
):
    wrong_state = valid_evidence(tmp_path, config)
    wrong_state["quarantine"]["quarantine_final_state"] = "pending"
    rejected(wrong_state)
    missing = valid_evidence(tmp_path, config)
    missing["quarantine"].pop("quarantine_overwrite_refused")
    rejected(missing)
    serialized_false = valid_evidence(tmp_path, config)
    serialized_false["quarantine"]["quarantine_test_passed"] = False
    rejected(serialized_false)
    recomputed_false = valid_evidence(tmp_path, config)
    recomputed_false["quarantine"][
        "recomputed_quarantine_test_passed"
    ] = False
    rejected(recomputed_false)


def test_consistently_failed_quarantine_is_non_authoritative(
    tmp_path, config
):
    value = valid_evidence(tmp_path, config)
    value["quarantine"]["quarantine_overwrite_refused"] = False
    value["quarantine"]["recomputed_quarantine_test_passed"] = False
    value["quarantine"]["quarantine_test_passed"] = False
    value["primary_authoritative_capable"] = False
    parsed = ResolverBurnInEvidence.model_validate(value)
    assert not parsed.quarantine.recomputed_quarantine_test_passed
    assert not parsed.primary_authoritative_capable


def test_single_arbitrary_process_fails(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["protected_processes"] = [value["protected_processes"][0]]
    value["protected_processes"][0]["pid"] = 1
    rejected(value)


@pytest.mark.parametrize(
    "role", ("observer", "observer_caffeinate", "rfc007_collector")
)
def test_missing_required_process_role_fails(tmp_path, config, role):
    value = valid_evidence(tmp_path, config)
    value["protected_processes"] = [
        process
        for process in value["protected_processes"]
        if process["role"] != role
    ]
    rejected(value)


def test_changed_process_command_fails(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["protected_processes"][0]["after_command_sha256"] = "0" * 64
    rejected(value)


@pytest.mark.parametrize("field", ("pid", "role"))
def test_duplicate_process_identity_fails(tmp_path, config, field):
    value = valid_evidence(tmp_path, config)
    value["protected_processes"][1][field] = (
        value["protected_processes"][0][field]
    )
    rejected(value)


def test_complete_three_process_evidence_passes(tmp_path, config):
    ResolverBurnInEvidence.model_validate(valid_evidence(tmp_path, config))


def test_missing_or_failed_jitter_fails(tmp_path, config):
    missing = valid_evidence(tmp_path, config)
    missing.pop("jitter")
    rejected(missing)
    failed = valid_evidence(tmp_path, config)
    failed["jitter"]["persisted_schedule_match"] = False
    failed["jitter"]["recomputed_jitter_test_passed"] = False
    failed["jitter"]["jitter_test_passed"] = False
    failed["primary_authoritative_capable"] = False
    parsed = ResolverBurnInEvidence.model_validate(failed)
    assert not parsed.jitter.recomputed_jitter_test_passed


def test_retry_cannot_substitute_for_jitter(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["jitter"] = copy.deepcopy(value["restart_retry"])
    rejected(value)


def test_retry_failure_with_passing_jitter_fails(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["restart_retry"]["retry_test_passed"] = False
    rejected(value)


@pytest.mark.parametrize(
    ("section", "field"),
    (
        ("restart_retry", "recomputed_restart_test_passed"),
        ("restart_retry", "recomputed_retry_test_passed"),
        ("jitter", "recomputed_jitter_test_passed"),
    ),
)
def test_controlled_recomputed_flags_must_match(
    tmp_path, config, section, field
):
    value = valid_evidence(tmp_path, config)
    value[section][field] = False
    rejected(value)


def test_jitter_requires_exact_retry_coverage(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["jitter"]["retry_numbers_tested"] = (1, 2)
    value["jitter"]["expected_delays_seconds"] = (2, 4)
    value["jitter"]["recomputed_delays_seconds"] = (2, 4)
    rejected(value)


@pytest.mark.parametrize(
    "field",
    (
        "source_path",
        "inode",
        "byte_offset",
        "line_number",
        "record_sha256",
        "record_timestamp",
        "observed_at",
    ),
)
def test_incomplete_source_boundary_fails(tmp_path, config, field):
    value = valid_evidence(tmp_path, config)
    value["source_boundary"].pop(field)
    rejected(value)


def test_malformed_source_boundary_fails(tmp_path, config):
    invalid_hash = valid_evidence(tmp_path, config)
    invalid_hash["source_boundary"]["record_sha256"] = "not-a-hash"
    rejected(invalid_hash)
    invalid_time = valid_evidence(tmp_path, config)
    invalid_time["source_boundary"]["observed_at"] = "not-a-timestamp"
    rejected(invalid_time)


def test_source_boundary_selection_mismatch_fails(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["source_boundary"]["round_id"] += 1
    rejected(value)


def test_serialized_capability_must_equal_recomputed(tmp_path, config):
    value = valid_evidence(tmp_path, config)
    value["primary_authoritative_capable"] = False
    rejected(value)


@pytest.mark.parametrize("schema_version", (2, 3))
def test_legacy_operational_evidence_is_unsupported(
    tmp_path, config, schema_version
):
    value = valid_evidence(tmp_path, config)
    value["schema_version"] = schema_version
    rejected(value)
