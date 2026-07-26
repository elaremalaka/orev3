from __future__ import annotations

import hashlib
import json
import os
from datetime import timedelta
from pathlib import Path

import pytest

from orev3.rfc008.lifecycle import (
    capture_marker_pair,
    marker_pair_unchanged,
    validate_post_marker_pre_collection_state,
    validate_pre_marker_state,
)
from orev3.rfc008.storage import strict_json

from . import test_marker_publication_race as race


def lifecycle_environment(tmp_path: Path, monkeypatch):
    environment = race.build_environment(tmp_path, monkeypatch)
    environment["marker"] = (
        tmp_path / "data/ledger/rfc008_marker_v1.json"
    )
    environment["ledger"] = (
        tmp_path / "data/ledger/rfc008_paper_ledger_v1.sqlite"
    )
    marker, digest = race.create(environment)
    return environment, marker, digest


def validate(environment, tmp_path, **updates):
    arguments = {
        "repository_root": tmp_path,
        "config_path": environment["config_path"],
        "burn_in_evidence_path": environment["burn"],
        "release_approval_path": environment["release"],
        "approval_manifest_path": race.APPROVAL,
    }
    arguments.update(updates)
    return validate_post_marker_pre_collection_state(**arguments)


def rewrite_marker(environment, mutate):
    value = json.loads(environment["marker"].read_text())
    mutate(value)
    environment["marker"].write_text(strict_json(value) + "\n")
    digest = hashlib.sha256(environment["marker"].read_bytes()).hexdigest()
    Path(str(environment["marker"]) + ".sha256").write_text(
        f"{digest}  {environment['marker'].name}\n"
    )


def checks(report):
    return {failure["check"] for failure in report["failures"]}


def test_pre_marker_lifecycle_is_explicit(tmp_path) -> None:
    report = validate_pre_marker_state(repository_root=tmp_path)
    assert report["ready"]
    marker = tmp_path / "data/ledger/rfc008_marker_v1.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}\n")
    report = validate_pre_marker_state(repository_root=tmp_path)
    assert not report["ready"]
    assert "pre_marker_marker_absent" in checks(report)


def test_valid_post_marker_pre_collection_state(
    tmp_path, monkeypatch
) -> None:
    environment, marker, _ = lifecycle_environment(tmp_path, monkeypatch)
    report = validate(environment, tmp_path)
    assert report["ready"]
    assert report["marker_compatible"]
    assert report["collection_authorized"] is False
    assert report["production_ledger_family_absent"]
    assert report["dataset_artifacts_absent"]
    assert report["freeze_artifacts_absent"]
    assert report["analysis_artifacts_absent"]
    assert report["historical_eligibility_boundary"]["round_id"] == (
        marker.latest_preholdout_round_id
    )
    assert report["marker_publication_source_cursors"]
    assert report["collection_seed_cursors"]
    assert report["cursor_identities_required_equal"] is False


def test_read_only_validation_preserves_marker_pair(
    tmp_path, monkeypatch
) -> None:
    environment, _, _ = lifecycle_environment(tmp_path, monkeypatch)
    before = capture_marker_pair(environment["marker"])
    report = validate(
        environment,
        tmp_path,
        expected_snapshot=before,
    )
    assert report["ready"]
    assert marker_pair_unchanged(
        before,
        capture_marker_pair(environment["marker"]),
    )


@pytest.mark.parametrize("missing", ("marker", "sidecar"))
def test_partial_marker_pair_fails(
    tmp_path, monkeypatch, missing
) -> None:
    environment, _, _ = lifecycle_environment(tmp_path, monkeypatch)
    target = (
        environment["marker"]
        if missing == "marker"
        else Path(str(environment["marker"]) + ".sha256")
    )
    target.unlink()
    report = validate(environment, tmp_path)
    assert not report["ready"]
    assert "complete_marker_pair_present" in checks(report)


@pytest.mark.parametrize(
    "corruption",
    (
        "marker_bytes",
        "sidecar_bytes",
        "invalid_schema",
        "approval_binding",
        "evidence_binding",
    ),
)
def test_marker_corruption_fails_closed(
    tmp_path, monkeypatch, corruption
) -> None:
    environment, _, _ = lifecycle_environment(tmp_path, monkeypatch)
    marker = environment["marker"]
    sidecar = Path(str(marker) + ".sha256")
    if corruption == "marker_bytes":
        marker.write_bytes(marker.read_bytes() + b" ")
    elif corruption == "sidecar_bytes":
        sidecar.write_text(f"{'0' * 64}  {marker.name}\n")
    elif corruption == "invalid_schema":
        rewrite_marker(
            environment,
            lambda value: value.__setitem__("marker_schema_version", 1),
        )
    elif corruption == "approval_binding":
        rewrite_marker(
            environment,
            lambda value: value.__setitem__(
                "release_approval_sha256", "0" * 64
            ),
        )
    else:
        rewrite_marker(
            environment,
            lambda value: value.__setitem__(
                "resolver_burn_in_evidence_sha256", "0" * 64
            ),
        )
    report = validate(environment, tmp_path)
    assert not report["ready"]
    assert "valid_immutable_marker_pair" in checks(report)


def test_unexpected_second_marker_fails(tmp_path, monkeypatch) -> None:
    environment, _, _ = lifecycle_environment(tmp_path, monkeypatch)
    extra = environment["marker"].with_name("rfc008_marker_extra.json")
    extra.write_text("{}\n")
    report = validate(environment, tmp_path)
    assert not report["ready"]
    assert "exactly_one_marker_set" in checks(report)


@pytest.mark.parametrize(
    ("relative_path", "expected_check", "directory"),
    (
        (
            "data/ledger/rfc008_paper_ledger_v1.sqlite",
            "production_ledger_family_absent",
            False,
        ),
        (
            "data/ledger/rfc008_paper_ledger_v1.sqlite-wal",
            "production_ledger_family_absent",
            False,
        ),
        (
            "data/ledger/rfc008_paper_ledger_v1.sqlite-shm",
            "production_ledger_family_absent",
            False,
        ),
        (
            "data/ledger/rfc008_paper_ledger_v1.sqlite.writer.lock",
            "production_ledger_family_absent",
            False,
        ),
        (
            "data/analysis/rfc008_dataset_v1",
            "dataset_artifacts_absent",
            True,
        ),
        (
            "data/freeze/rfc008_final_freeze_v1.json",
            "freeze_artifacts_absent",
            False,
        ),
        (
            "data/analysis/rfc008_results_v1",
            "analysis_artifacts_absent",
            True,
        ),
    ),
)
def test_forbidden_downstream_artifacts_fail(
    tmp_path,
    monkeypatch,
    relative_path,
    expected_check,
    directory,
) -> None:
    environment, _, _ = lifecycle_environment(tmp_path, monkeypatch)
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if directory:
        target.mkdir()
    else:
        target.touch()
    report = validate(environment, tmp_path)
    assert not report["ready"]
    assert expected_check in checks(report)


def test_collector_presence_fails_post_marker_gate(
    tmp_path, monkeypatch
) -> None:
    environment, _, _ = lifecycle_environment(tmp_path, monkeypatch)
    report = validate(
        environment,
        tmp_path,
        collector_running=True,
    )
    assert not report["ready"]
    assert "collector_absent" in checks(report)


def test_later_append_does_not_change_historical_eligibility(
    tmp_path, monkeypatch
) -> None:
    environment, marker, _ = lifecycle_environment(tmp_path, monkeypatch)
    race.append_record(
        environment["source"],
        marker.latest_preholdout_round_id + 1,
        race.NOW + timedelta(seconds=10),
    )
    report = validate(environment, tmp_path)
    assert report["ready"]
    historical = report["historical_eligibility_boundary"]
    assert historical["round_id"] == marker.latest_preholdout_round_id
    assert historical["source_byte_offset"] == (
        marker.runtime_source_byte_offset
    )


def test_source_replacement_fails_historical_validation(
    tmp_path, monkeypatch
) -> None:
    environment, _, _ = lifecycle_environment(tmp_path, monkeypatch)
    replacement = tmp_path / "observer_replacement.jsonl"
    replacement.write_bytes(environment["source"].read_bytes())
    os.replace(replacement, environment["source"])
    report = validate(environment, tmp_path)
    assert not report["ready"]
    assert "valid_immutable_marker_pair" in checks(report)


def test_collection_seed_cannot_precede_historical_boundary(
    tmp_path, monkeypatch
) -> None:
    environment, marker, _ = lifecycle_environment(tmp_path, monkeypatch)

    def move_seed_back(value):
        values = []
        for identity in value["source_identities"]:
            path, inode, offset, line = identity.rsplit("|", 3)
            if path == marker.runtime_source_path:
                offset = str(marker.runtime_source_byte_offset - 1)
                line = str(marker.runtime_source_line_number - 1)
            values.append("|".join((path, inode, offset, line)))
        value["source_identities"] = values

    rewrite_marker(environment, move_seed_back)
    report = validate(environment, tmp_path)
    assert not report["ready"]
    assert "valid_immutable_marker_pair" in checks(report)
