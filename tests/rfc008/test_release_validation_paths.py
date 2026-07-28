from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import shutil
import socket
import subprocess
import threading
from pathlib import Path

import pytest

import orev3.rfc008.cli as cli_module
from orev3.rfc008.approval_contract import (
    active_schema2_structure_failures,
)
from orev3.rfc008.cli import command_preflight_collection, command_run
from orev3.rfc008.lifecycle import (
    validate_collection_preflight,
    validate_post_marker_pre_collection_state,
)
from orev3.rfc008.marker import marker_preflight
from orev3.rfc008.release_validation import validate_active_release


ROOT = Path(__file__).parents[2]
BRANCH = "research/rfc-007-paper-collection-burn-in"


def _copy_runtime_inputs(target: Path) -> None:
    for relative in (
        "data/ledger/rfc008_marker_v1.json",
        "data/ledger/rfc008_marker_v1.json.sha256",
        "data/resolver/rfc008_operational_burn_in_v1.json",
        "data/resolver/rfc008_operational_burn_in_v1.json.sha256",
        "data/resolver/rfc008_operational_burn_in_v1.sqlite",
    ):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)


@pytest.fixture
def release_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    subprocess.run(
        ("git", "clone", "-q", "--no-hardlinks", str(ROOT), str(root)),
        check=True,
    )
    _copy_runtime_inputs(root)
    return root


def _paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "config/collection/rfc008_paper_v1.json",
        "resolver": root / "config/collection/rfc008_resolver_v1.json",
        "burn": root / "data/resolver/rfc008_operational_burn_in_v1.json",
        "release": (
            root
            / "docs/research/rfc008/release_implementation_approval_v1.json"
        ),
        "manifest": root / "docs/research/rfc008/approval_manifest_v1.json",
        "marker": root / "data/ledger/rfc008_marker_v1.json",
        "ledger": root / "data/ledger/rfc008_paper_ledger_v1.sqlite",
    }


def _active(root: Path):
    path = _paths(root)
    return validate_active_release(
        repository_root=root,
        config_path=path["config"],
        resolver_config_path=path["resolver"],
        burn_in_evidence_path=path["burn"],
        release_approval_path=path["release"],
        approval_manifest_path=path["manifest"],
        marker_path=path["marker"],
    )


def _lifecycle(root: Path):
    path = _paths(root)
    return validate_post_marker_pre_collection_state(
        repository_root=root,
        config_path=path["config"],
        resolver_config_path=path["resolver"],
        burn_in_evidence_path=path["burn"],
        release_approval_path=path["release"],
        approval_manifest_path=path["manifest"],
    )


def _collection(root: Path):
    path = _paths(root)
    return validate_collection_preflight(
        repository_root=root,
        config_path=path["config"],
        resolver_config_path=path["resolver"],
        burn_in_evidence_path=path["burn"],
        release_approval_path=path["release"],
        approval_manifest_path=path["manifest"],
        marker_path=path["marker"],
        collection_authorization_valid=False,
        ledger_initialization_authorized=False,
        collector_running=False,
    )


def _marker(root: Path):
    path = _paths(root)
    return marker_preflight(
        config_path=path["config"],
        resolver_config_path=path["resolver"],
        burn_in_evidence_path=path["burn"],
        release_approval_path=path["release"],
        marker_path=path["marker"],
        ledger_path=path["ledger"],
        approval_manifest_path=path["manifest"],
        repository_root=root,
        expected_branch=BRANCH,
    )


def _command_args(root: Path) -> argparse.Namespace:
    path = _paths(root)
    return argparse.Namespace(
        repository_root=str(root),
        config=str(path["config"]),
        resolver_config=str(path["resolver"]),
        burn_in_evidence=str(path["burn"]),
        release_approval=str(path["release"]),
        approval_manifest=str(path["manifest"]),
        marker=str(path["marker"]),
        ledger=str(path["ledger"]),
        expected_marker_sha256=hashlib.sha256(
            path["marker"].read_bytes()
        ).hexdigest(),
        expected_marker_sha256_file=None,
        create_new_ledger=True,
        authorization_token=None,
        ledger_initialization_token=None,
    )


def _preflight_args(root: Path) -> argparse.Namespace:
    path = _paths(root)
    return argparse.Namespace(
        repository_root=str(root),
        config=str(path["config"]),
        resolver_config=str(path["resolver"]),
        burn_in_evidence=str(path["burn"]),
        release_approval=str(path["release"]),
        approval_manifest=str(path["manifest"]),
        marker=str(path["marker"]),
    )


def _write_release(path: Path, value: dict[str, object]) -> None:
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _mutate_release(root: Path, mutation: str) -> None:
    path = _paths(root)["release"]
    value = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "active_schema_1":
        value["schema_version"] = 1
    elif mutation == "unsupported_schema":
        value["schema_version"] = 99
    elif mutation == "wrong_artifact":
        value["artifact_type"] = "unrelated_artifact"
    elif mutation == "unknown_field":
        value["unknown"] = True
    elif mutation == "wrong_implementation":
        value["approved_implementation_commit"] = "0" * 40
    elif mutation in {"wrong_predecessor", "broken_chain"}:
        value["supersedes_release_implementation_approval_sha256"] = "0" * 64
    elif mutation == "wrong_ledger_hash":
        value["validated_operational_burn_in_ledger_sha256"] = "0" * 64
    elif mutation == "wrong_migration_hash":
        value["migration_set_sha256"] = "0" * 64
    elif mutation == "wrong_cli_hash":
        value["cli_sha256"] = "0" * 64
    elif mutation == "wrong_runbook_hash":
        value["runbook_sha256"] = "0" * 64
    elif mutation == "wrong_authorization_type":
        value["authorization_boundary"]["collection_authorized"] = 0
    elif mutation == "authorization_true":
        value["authorization_boundary"]["collection_authorized"] = True
    elif mutation == "nested_unknown":
        value["authorization_boundary"]["unknown"] = False
    else:
        raise AssertionError(mutation)
    _write_release(path, value)


@pytest.mark.parametrize(
    "mutation",
    (
        "active_schema_1",
        "unsupported_schema",
        "wrong_artifact",
        "unknown_field",
        "nested_unknown",
        "wrong_implementation",
        "wrong_predecessor",
        "broken_chain",
        "wrong_ledger_hash",
        "wrong_migration_hash",
        "wrong_cli_hash",
        "wrong_runbook_hash",
        "wrong_authorization_type",
        "authorization_true",
    ),
)
def test_invalid_active_release_rejected_by_every_path(
    release_root: Path,
    mutation: str,
    capsys,
) -> None:
    _mutate_release(release_root, mutation)
    direct = _active(release_root)
    marker = _marker(release_root)
    lifecycle = _lifecycle(release_root)
    collection = _collection(release_root)
    assert not direct.valid
    assert not marker["active_release_validation_valid"]
    assert not lifecycle["active_release_validation_valid"]
    assert not collection.active_release_validation.valid
    with pytest.raises(PermissionError, match="collection preflight"):
        command_run(_command_args(release_root))
    command_preflight_collection(_preflight_args(release_root))
    cli_report = json.loads(capsys.readouterr().out)
    assert not cli_report["active_release_validation"]["valid"]


def test_duplicate_key_rejected_by_every_path(
    release_root: Path,
    capsys,
) -> None:
    path = _paths(release_root)["release"]
    raw = path.read_text(encoding="utf-8")
    path.write_text(
        raw.replace(
            '"schema_version": 2,',
            '"schema_version": 2,\\n  "schema_version": 2,',
            1,
        ),
        encoding="utf-8",
    )
    assert not _active(release_root).valid
    assert not _marker(release_root)["active_release_validation_valid"]
    assert not _lifecycle(release_root)["active_release_validation_valid"]
    assert not _collection(release_root).active_release_validation.valid
    with pytest.raises(PermissionError, match="collection preflight"):
        command_run(_command_args(release_root))
    command_preflight_collection(_preflight_args(release_root))
    assert not json.loads(capsys.readouterr().out)[
        "active_release_validation"
    ]["valid"]


@pytest.mark.parametrize(
    ("relative", "replacement"),
    (
        (
            "data/resolver/rfc008_operational_burn_in_v1.sqlite",
            b"substituted ledger bytes",
        ),
        ("src/orev3/rfc008/cli.py", b"# modified CLI source\n"),
        (
            "docs/research/RFC-008-OPERATOR-RUNBOOK.md",
            b"modified runbook\n",
        ),
        (
            "src/orev3/rfc008/migrations.py",
            b"# modified migration source\n",
        ),
    ),
)
def test_derived_source_drift_rejected_by_all_launch_paths(
    release_root: Path,
    relative: str,
    replacement: bytes,
) -> None:
    (release_root / relative).write_bytes(replacement)
    assert not _active(release_root).valid
    assert not _lifecycle(release_root)["ready"]
    assert not _collection(release_root).ready
    with pytest.raises(PermissionError, match="collection preflight"):
        command_run(_command_args(release_root))


def test_invalid_release_stops_before_side_effect_boundaries(
    release_root: Path,
    monkeypatch,
) -> None:
    _mutate_release(release_root, "active_schema_1")
    reached = {
        "provider": 0,
        "writer": 0,
        "store": 0,
        "collector": 0,
        "socket": 0,
        "process": 0,
        "thread": 0,
    }

    def boundary(name):
        def fail(*args, **kwargs):
            reached[name] += 1
            raise AssertionError(f"side-effect boundary reached: {name}")

        return fail

    monkeypatch.setattr(cli_module, "RpcRecoveryProvider", boundary("provider"))
    monkeypatch.setattr(cli_module, "RFC008WriterLease", boundary("writer"))
    monkeypatch.setattr(cli_module, "RFC008Store", boundary("store"))
    monkeypatch.setattr(cli_module, "RFC008Collector", boundary("collector"))
    monkeypatch.setattr(socket, "socket", boundary("socket"))
    monkeypatch.setattr(
        multiprocessing.Process,
        "start",
        boundary("process"),
    )
    monkeypatch.setattr(threading.Thread, "start", boundary("thread"))
    with pytest.raises(PermissionError, match="collection preflight"):
        command_run(_command_args(release_root))
    assert reached == {
        "provider": 0,
        "writer": 0,
        "store": 0,
        "collector": 0,
        "socket": 0,
        "process": 0,
        "thread": 0,
    }
    assert not _paths(release_root)["ledger"].exists()


@pytest.mark.parametrize(
    "mutation",
    ("unknown", "missing", "alias", "authorization_integer", "nested_unknown"),
)
def test_untrusted_dictionary_never_bypasses_registry_structure(
    mutation: str,
) -> None:
    value = json.loads(
        (
            ROOT
            / "docs/research/rfc008/release_implementation_approval_v1.json"
        ).read_text()
    )
    if mutation == "unknown":
        value["unknown"] = True
    elif mutation == "missing":
        value.pop("rfc_identifier")
    elif mutation == "alias":
        value["rfc"] = value.pop("rfc_identifier")
    elif mutation == "authorization_integer":
        value["authorization_boundary"]["collection_authorized"] = 0
    else:
        value["authorization_boundary"]["unknown"] = False
    assert active_schema2_structure_failures(value)


def test_registry_is_only_active_authority_source(release_root: Path) -> None:
    result = _active(release_root)
    assert result.valid, result.as_dict()
    assert result.schema_valid
    assert result.field_contract_valid
    assert result.derived_field_valid
    assert result.policy_field_valid
    assert result.authorization_field_valid
    assert result.approval_chain_valid
    assert result.marker_binding_valid
