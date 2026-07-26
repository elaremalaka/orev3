from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orev3.rfc008.marker import marker_preflight
from orev3.rfc008.migrations import migration_set_hash
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import (
    REQUIRED_PROCESS_COMMAND_IDENTITIES,
    REQUIRED_PROTECTED_PROCESSES,
    RFC008_BURN_IN_AUDIT_VERSION,
    RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION,
    RFC008_CLI_VERSION,
    RFC008_RUNBOOK_VERSION,
    ResolverBurnInEvidence,
    RuntimeSourceBoundary,
)
from orev3.rfc008.storage import strict_json
from pydantic import ValidationError

from .conftest import CONFIG_PATH


ROOT = CONFIG_PATH.parents[2]
APPROVAL = ROOT / "docs/research/rfc008/approval_manifest_v1.json"
RESOLVER_CONFIG = CONFIG_PATH.parent / "rfc008_resolver_v1.json"
NOW = datetime(2026, 7, 25, 12, tzinfo=timezone.utc)


def write_release_and_burn_in(tmp_path, config, *, created_at=NOW):
    resolver = ResolverConfig.from_path(RESOLVER_CONFIG)
    release = tmp_path / "release.json"
    release.write_text(
        strict_json(
            {
                "artifact_type": "rfc008_implementation_release_approval",
                "approved_implementation_commit": "a" * 40,
                "configuration_fingerprint": config.configuration_fingerprint,
                "candidate_configuration_sha256": (
                    config.candidate_configuration_sha256
                ),
                "resolver_configuration_sha256": resolver.fingerprint,
                "migration_set_sha256": migration_set_hash(),
                "burn_in_evidence_schema_version": (
                    RFC008_BURN_IN_EVIDENCE_SCHEMA_VERSION
                ),
                "audit_version": RFC008_BURN_IN_AUDIT_VERSION,
                "minimum_operational_sample_size": 5,
                "protected_process_policy": {
                    str(pid): {
                        "role": role,
                        "sanitized_command_identity": (
                            REQUIRED_PROCESS_COMMAND_IDENTITIES[role]
                        ),
                    }
                    for pid, role in REQUIRED_PROTECTED_PROCESSES.items()
                },
                "cli_version": RFC008_CLI_VERSION,
                "runbook_version": RFC008_RUNBOOK_VERSION,
                "cli_sha256": hashlib.sha256(
                    (ROOT / "src/orev3/rfc008/cli.py").read_bytes()
                ).hexdigest(),
                "runbook_sha256": hashlib.sha256(
                    (
                        ROOT
                        / "docs/research/RFC-008-OPERATOR-RUNBOOK.md"
                    ).read_bytes()
                ).hexdigest(),
            }
        )
        + "\n"
    )
    burn = tmp_path / "burn.json"
    release_sha256 = hashlib.sha256(release.read_bytes()).hexdigest()
    round_ids = tuple(range(346000, 346005))
    rounds = []
    attempts = []
    requests = [
        {
            "request_id": f"genesis-{provider_id}",
            "attempt_id": None,
            "round_id": None,
            "round_pda": None,
            "provider_id": provider_id,
            "method": "get_genesis_hash",
            "requested_at": created_at,
            "classification": "successful",
            "retry_request": False,
            "commitment": None,
            "operational": True,
        }
        for provider_id in resolver.provider_ids
    ]
    for order, round_id in enumerate(round_ids, 1):
        pda = f"pda:{round_id}"
        attempt_id = f"attempt-{round_id}"
        request_ids = tuple(
            f"request-{round_id}-{provider_id}"
            for provider_id in resolver.provider_ids
        )
        provider_evidence = [
            {
                "request_id": request_id,
                "provider_id": provider_id,
                "request_method": "get_account_info_with_context",
                "requested_at": created_at,
                "commitment": "finalized",
                "genesis_hash": resolver.expected_genesis_hash,
                "response_context_slot": 500,
                "raw_response_sha256": f"{order:064x}",
                "canonical_response_sha256": "c" * 64,
                "account_owner": resolver.expected_program_owner,
                "returned_account_identity": pda,
                "decoded_round_id": round_id,
            }
            for provider_id, request_id in zip(
                resolver.provider_ids, request_ids
            )
        ]
        requests.extend(
            {
                "request_id": request_id,
                "attempt_id": attempt_id,
                "round_id": round_id,
                "round_pda": pda,
                "provider_id": provider_id,
                "method": "get_account_info_with_context",
                "requested_at": created_at,
                "classification": "successful",
                "retry_request": False,
                "commitment": "finalized",
                "operational": True,
            }
            for provider_id, request_id in zip(
                resolver.provider_ids, request_ids
            )
        )
        attempts.append(
            {
                "attempt_id": attempt_id,
                "round_id": round_id,
                "attempt_number": 1,
                "attempted_at": created_at,
                "status": "accepted",
                "provider_request_ids": request_ids,
                "persisted": True,
            }
        )
        rounds.append(
            {
                "round_id": round_id,
                "round_pda": pda,
                "selection_order": order,
                "provider_ids": resolver.provider_ids,
                "provider_evidence": provider_evidence,
                "entropy": 26,
                "winning_square": 1,
                "deployment_vector_validated": True,
                "accounting_validated": True,
                "provider_agreement": True,
                "owner_validation_passed": True,
                "pda_validation_passed": True,
                "account_identity_passed": True,
                "decoded_round_identity_passed": True,
                "finalized_validation_passed": True,
                "provenance_complete": True,
                "final_state": "accepted",
                "attempt_count": 1,
                "request_timestamps": [created_at, created_at],
            }
        )
    value = ResolverBurnInEvidence(
        evidence_type="rfc008_resolver_burn_in",
        mode="operational",
        created_at=created_at,
        completed_at=created_at,
        repository_commit="a" * 40,
        repository_branch="research/rfc-007-paper-collection-burn-in",
        release_implementation_approval_sha256=release_sha256,
        resolver_configuration_sha256=resolver.fingerprint,
        experiment_configuration_fingerprint=config.configuration_fingerprint,
        resolver_version=resolver.resolver_version,
        decoder_version=resolver.decoder_version,
        provider_ids=resolver.provider_ids,
        provider_independence_passed=True,
        provider_genesis_hashes={
            provider_id: resolver.expected_genesis_hash
            for provider_id in resolver.provider_ids
        },
        genesis_agreement_passed=True,
        source_boundary={
            "round_id": 346005,
            "source_path": "/tmp/observer.jsonl",
            "inode": 1,
            "byte_offset": 100,
            "line_number": 5,
            "record_sha256": "d" * 64,
            "record_timestamp": created_at,
            "observed_at": created_at,
        },
        operational={
            "requested_sample_size": 5,
            "minimum_required_sample_size": 5,
            "selection_policy": "fixture preflight evidence",
            "selection_source": "fixture",
            "selection_boundary_round_id": 346005,
            "selected_round_ids": round_ids,
            "selected_round_count": 5,
            "distinct_round_count": 5,
            "successful_authoritative_count": 5,
            "failed_count": 0,
            "unresolved_count": 0,
            "conflicted_count": 0,
            "quarantined_count": 0,
            "provider_agreement_count": 5,
            "owner_validation_pass_count": 5,
            "identity_validation_pass_count": 5,
            "finalized_validation_pass_count": 5,
            "deployment_validation_pass_count": 5,
            "accounting_validation_pass_count": 5,
            "complete_provenance_count": 5,
            "five_round_criterion_passed": True,
            "rounds": rounds,
        },
        operational_attempts=attempts,
        operational_requests=requests,
        real_rpc_request_counts={
            "total": 12,
            "by_provider": {"primary": 6, "secondary": 6},
            "by_method": {
                "get_genesis_hash": 2,
                "get_account_info_with_context": 10,
            },
            "by_provider_and_method": {
                "primary": {
                    "get_genesis_hash": 1,
                    "get_account_info_with_context": 5,
                },
                "secondary": {
                    "get_genesis_hash": 1,
                    "get_account_info_with_context": 5,
                },
            },
            "successful_responses": 12,
            "unavailable_responses": 0,
            "malformed_responses": 0,
            "failed_responses": 0,
            "retried_requests": 0,
            "finalized_account_reads": 10,
            "genesis_hash_reads": 2,
        },
        rpc_attempt_reconciliation_passed=True,
        rpc_attempt_reconciliation_errors=(),
        controlled_fixture_call_counts={"get_account_info_with_context": 7},
        restart_retry={
            "test_type": "controlled_restart_retry",
            "evidence_mode": "fixture",
            "round_id": 446000,
            "initial_state": "pending",
            "persisted_retry_count": 1,
            "persisted_next_retry_time": created_at + timedelta(seconds=2),
            "persisted_pda": "fixture-pda",
            "persisted_attempt_count": 1,
            "restart_state": "pending",
            "final_result": "accepted",
            "final_state": "finalized",
            "restart_test_passed": True,
            "retry_test_passed": True,
        },
        jitter={
            "test_type": "controlled_jitter",
            "evidence_mode": "fixture",
            "round_id": 446000,
            "retry_numbers_tested": [1, 2, 3],
            "expected_delays_seconds": [2, 4, 8],
            "recomputed_delays_seconds": [2, 4, 8],
            "deterministic_match": True,
            "bounded_delay_result": True,
            "persisted_schedule_match": True,
            "jitter_derivation_version": "rfc008-retry-jitter-v1",
            "jitter_test_passed": True,
        },
        conflict={
            "test_type": "controlled_conflict",
            "evidence_mode": "fixture",
            "round_id": 446001,
            "injected_non_authoritative_disagreement": True,
            "conflict_state": "conflicted",
            "provenance_retained": True,
            "overwrite_refused": True,
            "primary_analysis_ineligible": True,
            "conflict_test_passed": True,
        },
        quarantine={
            "test_type": "controlled_quarantine",
            "evidence_mode": "fixture",
            "quarantine_round_id": 446002,
            "configured_expiration_seconds": 86400,
            "quarantine_initial_state": "pending",
            "quarantine_final_state": "quarantined",
            "quarantine_restart_persistence": True,
            "quarantine_overwrite_refused": True,
            "primary_analysis_ineligible": True,
            "quarantine_test_passed": True,
        },
        sqlite_integrity="ok",
        safety_inspection_passed=True,
        production_artifacts_absent=True,
        running_processes_preserved=True,
        protected_processes=[
            {
                "pid": pid,
                "role": role,
                "sanitized_command_identity": {
                    "observer": "-m orev3.observer.collect",
                    "observer_caffeinate": (
                        "caffeinate -i python -m orev3.observer.collect"
                    ),
                    "rfc007_collector": (
                        "-m orev3.collection.cli run --config "
                        "config/collection/rfc007_burn_in_v1.json --ledger "
                        "data/ledger/rfc007_live_ledger_v1.sqlite"
                    ),
                }[role],
                "observed_before": True,
                "observed_after": True,
                "before_command_sha256": digest,
                "after_command_sha256": digest,
                "before_observed_at": created_at,
                "after_observed_at": created_at,
                "unchanged": True,
                "evidence_mode": "operational",
            }
            for pid, role, digest in (
                (48404, "observer", "d" * 64),
                (48405, "observer_caffeinate", "e" * 64),
                (78317, "rfc007_collector", "f" * 64),
            )
        ],
        primary_authoritative_capable=True,
        fixture_only=False,
        ledger_sha256="b" * 64,
        limitations=(),
    )
    burn.write_text(strict_json(value) + "\n")
    digest = hashlib.sha256(burn.read_bytes()).hexdigest()
    (tmp_path / "burn.json.sha256").write_text(f"{digest}  burn.json\n")
    return release, burn


def run_preflight(tmp_path, config, monkeypatch, release, burn, **updates):
    repository = {
        "commit": "a" * 40,
        "parent": "9" * 40,
        "branch": "research/rfc-007-paper-collection-burn-in",
        "tracked_clean": True,
        "untracked_clean": True,
    }
    repository.update(updates.pop("repository", {}))
    monkeypatch.setattr(
        "orev3.rfc008.marker.repository_state", lambda root: repository
    )
    boundary = RuntimeSourceBoundary(
        source_path="/tmp/observer.jsonl",
        source_inode=1,
        source_byte_offset=100,
        source_line_number=2,
        source_record_sha256="c" * 64,
        source_observed_at=NOW,
        round_id=346000,
    )
    monkeypatch.setattr(
        "orev3.rfc008.marker.derive_runtime_source_boundary",
        lambda source_glob: (boundary, ("/tmp/observer.jsonl|1|100|2",)),
    )
    return marker_preflight(
        config_path=CONFIG_PATH,
        resolver_config_path=RESOLVER_CONFIG,
        burn_in_evidence_path=burn,
        release_approval_path=release,
        marker_path=tmp_path / "production_marker.json",
        ledger_path=tmp_path / "production_ledger.sqlite",
        approval_manifest_path=APPROVAL,
        repository_root=ROOT,
        expected_branch="research/rfc-007-paper-collection-burn-in",
        now=NOW,
    )


def rewrite_burn(path, mutate):
    value = json.loads(path.read_text())
    mutate(value)
    path.write_text(strict_json(value) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(str(path) + ".sha256").write_text(
        f"{digest}  {path.name}\n"
    )


def test_truthful_preflight_ready_and_structured_failures(
    tmp_path, config, monkeypatch
):
    release, burn = write_release_and_burn_in(tmp_path, config)
    ready = run_preflight(
        tmp_path, config, monkeypatch, release, burn
    )
    assert ready["ready"]
    assert ready["resolver_compatible"]
    assert ready["source_cursor_boundary"]["round_id"] == 346000
    assert ready["burn_in_evidence_sha256"]

    missing = run_preflight(
        tmp_path, config, monkeypatch, release, tmp_path / "missing.json"
    )
    assert not missing["ready"]
    assert {failure["check"] for failure in missing["failures"]} == {
        "burn_in_exists",
        "burn_in_hash_matches",
    }


@pytest.mark.parametrize(
    ("repository_update", "expected_check"),
    (
        ({"branch": "wrong"}, "branch_matches"),
        ({"commit": "8" * 40, "parent": "7" * 40}, "head_approved"),
        ({"tracked_clean": False}, "tracked_worktree_clean"),
        ({"untracked_clean": False}, "untracked_worktree_clean"),
    ),
)
def test_preflight_rejects_repository_drift(
    tmp_path,
    config,
    monkeypatch,
    repository_update,
    expected_check,
):
    release, burn = write_release_and_burn_in(tmp_path, config)
    result = run_preflight(
        tmp_path,
        config,
        monkeypatch,
        release,
        burn,
        repository=repository_update,
    )
    assert not result["ready"]
    assert expected_check in {
        failure["check"] for failure in result["failures"]
    }


def test_preflight_rejects_stale_or_hash_mismatched_burn_in(
    tmp_path, config, monkeypatch
):
    release, stale = write_release_and_burn_in(
        tmp_path, config, created_at=NOW - timedelta(days=2)
    )
    result = run_preflight(
        tmp_path, config, monkeypatch, release, stale
    )
    assert not result["ready"]
    assert "burn_in_recent" in {
        failure["check"] for failure in result["failures"]
    }
    (tmp_path / "burn.json.sha256").write_text(f"{'0' * 64}  burn.json\n")
    result = run_preflight(
        tmp_path, config, monkeypatch, release, stale
    )
    assert "burn_in_hash_matches" in {
        failure["check"] for failure in result["failures"]
    }


def test_preflight_rejects_existing_production_artifact(
    tmp_path, config, monkeypatch
):
    release, burn = write_release_and_burn_in(tmp_path, config)
    (tmp_path / "production_ledger.sqlite").touch()
    result = run_preflight(
        tmp_path, config, monkeypatch, release, burn
    )
    assert not result["ready"]
    assert "production_artifacts_absent" in {
        failure["check"] for failure in result["failures"]
    }


def test_resolver_configuration_rejects_confirmed_or_single_provider():
    resolver = ResolverConfig.from_path(RESOLVER_CONFIG)
    raw = resolver.model_dump(mode="json")
    raw["commitment"] = "confirmed"
    with pytest.raises(ValidationError):
        ResolverConfig.model_validate(raw)
    raw = resolver.model_dump(mode="json")
    raw["provider_ids"] = ["primary"]
    raw["provider_url_environment_variables"] = ["PRIMARY_URL"]
    with pytest.raises(ValueError, match="exactly two"):
        ResolverConfig.model_validate(raw)


def test_preflight_rejects_four_round_operational_evidence(
    tmp_path, config, monkeypatch
):
    release, burn = write_release_and_burn_in(tmp_path, config)

    def reduce_to_four(value):
        operational = value["operational"]
        operational["selected_round_ids"] = operational["selected_round_ids"][:4]
        operational["rounds"] = operational["rounds"][:4]
        for name in (
            "selected_round_count",
            "distinct_round_count",
            "successful_authoritative_count",
            "provider_agreement_count",
            "owner_validation_pass_count",
                "identity_validation_pass_count",
                "finalized_validation_pass_count",
                "deployment_validation_pass_count",
                "accounting_validation_pass_count",
                "complete_provenance_count",
        ):
            operational[name] = 4
            operational["requested_sample_size"] = 4
            operational["five_round_criterion_passed"] = False
            value["source_boundary"]["round_id"] = 346004
            value["operational_attempts"] = value["operational_attempts"][:4]
            allowed_attempts = {
                attempt["attempt_id"]
                for attempt in value["operational_attempts"]
            }
            value["operational_requests"] = [
                request
                for request in value["operational_requests"]
                if request["attempt_id"] is None
                or request["attempt_id"] in allowed_attempts
            ]
        counts = value["real_rpc_request_counts"]
        counts["total"] = 10
        counts["by_provider"] = {"primary": 5, "secondary": 5}
        counts["by_method"]["get_account_info_with_context"] = 8
        counts["by_provider_and_method"]["primary"][
            "get_account_info_with_context"
        ] = 4
        counts["by_provider_and_method"]["secondary"][
            "get_account_info_with_context"
        ] = 4
        counts["successful_responses"] = 10
        counts["finalized_account_reads"] = 8
        value["primary_authoritative_capable"] = False

    rewrite_burn(burn, reduce_to_four)
    result = run_preflight(
        tmp_path, config, monkeypatch, release, burn
    )
    checks = {failure["check"] for failure in result["failures"]}
    assert not result["ready"]
    assert "operational_sample_too_small" in checks
    assert "operational_success_count_too_small" in checks


@pytest.mark.parametrize(
    ("field", "expected"),
    (
        ("real_rpc_request_counts", "rpc_counts_missing"),
        ("quarantine", "quarantine_test_missing"),
        ("conflict", "conflict_test_missing"),
    ),
)
def test_preflight_rejects_missing_required_burnin_section(
    tmp_path, config, monkeypatch, field, expected
):
    release, burn = write_release_and_burn_in(tmp_path, config)
    rewrite_burn(burn, lambda value: value.pop(field))
    result = run_preflight(
        tmp_path, config, monkeypatch, release, burn
    )
    checks = {failure["check"] for failure in result["failures"]}
    assert not result["ready"]
    assert expected in checks
    assert "burnin_evidence_invalid" in checks


@pytest.mark.parametrize(
    ("mutate", "expected"),
    (
        (
            lambda value: value["operational"]["rounds"][0].__setitem__(
                "deployment_vector_validated", False
            ),
            "deployment_validation_incomplete",
        ),
        (
            lambda value: value["operational"]["rounds"][0].__setitem__(
                "accounting_validated", False
            ),
            "accounting_validation_incomplete",
        ),
        (
            lambda value: value.__setitem__("operational_attempts", []),
            "attempt_history_missing",
        ),
        (
            lambda value: value.__setitem__(
                "rpc_attempt_reconciliation_passed", False
            ),
            "rpc_attempt_reconciliation_failed",
        ),
        (
            lambda value: value["quarantine"].__setitem__(
                "quarantine_round_id", value["conflict"]["round_id"]
            ),
            "conflict_quarantine_identity_collision",
        ),
        (
            lambda value: value.__setitem__(
                "protected_processes", value["protected_processes"][:1]
            ),
            "protected_process_missing",
        ),
        (
            lambda value: value.pop("jitter"),
            "jitter_test_missing",
        ),
        (
            lambda value: value["source_boundary"].pop("source_path"),
            "source_boundary_incomplete",
        ),
        (
            lambda value: value["source_boundary"].__setitem__(
                "record_sha256", "invalid"
            ),
            "source_boundary_hash_invalid",
        ),
        (
            lambda value: value["source_boundary"].__setitem__(
                "observed_at", "not-a-time"
            ),
            "source_boundary_timestamp_invalid",
        ),
    ),
)
def test_preflight_surfaces_v3_structured_failures(
    tmp_path, config, monkeypatch, mutate, expected
):
    release, burn = write_release_and_burn_in(tmp_path, config)
    rewrite_burn(burn, mutate)
    result = run_preflight(
        tmp_path, config, monkeypatch, release, burn
    )
    checks = {failure["check"] for failure in result["failures"]}
    assert not result["ready"]
    assert expected in checks
