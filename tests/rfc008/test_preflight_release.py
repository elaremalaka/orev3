from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from orev3.rfc008.marker import marker_preflight
from orev3.rfc008.migrations import migration_set_hash
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.schemas import ResolverBurnInEvidence, RuntimeSourceBoundary
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
    value = ResolverBurnInEvidence(
        evidence_type="rfc008_resolver_burn_in",
        mode="operational",
        created_at=created_at,
        resolver_configuration_sha256=resolver.fingerprint,
        experiment_configuration_fingerprint=config.configuration_fingerprint,
        resolver_version=resolver.resolver_version,
        decoder_version=resolver.decoder_version,
        provider_ids=resolver.provider_ids,
        direct_finalization_passed=True,
        owner_identity_passed=True,
        round_identity_passed=True,
        restart_recovery_passed=True,
        retry_passed=True,
        deterministic_jitter_passed=True,
        provenance_passed=True,
        conflict_quarantine_passed=True,
        primary_authoritative_capable=True,
        fixture_only=False,
        ledger_sha256="b" * 64,
        checks={},
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
    assert {failure["check"] for failure in missing["failures"]} >= {
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
