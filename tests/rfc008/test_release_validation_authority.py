from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import subprocess
from pathlib import Path

import pytest

from orev3.rfc008.cli import (
    _command_run,
    command_preflight_collection,
    command_status,
)
from orev3.rfc008.lifecycle import (
    validate_collection_preflight,
    validate_post_marker_pre_collection_state,
)
from orev3.rfc008.marker import marker_preflight
from orev3.rfc008.release_validation import (
    repository_release_authority,
    validate_active_release,
)

from .test_release_validation_paths import (
    BRANCH,
    ROOT,
    _copy_runtime_inputs,
)


@pytest.fixture
def authority_root(tmp_path: Path) -> Path:
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
        "authorization": (
            root / "data/ledger/rfc008_paper_authorization_v1.sqlite"
        ),
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
        authorization_path=path["authorization"],
        ledger_path=path["ledger"],
        action="launch",
        collector_running=False,
    )


def _args(root: Path) -> argparse.Namespace:
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
        authorization=str(path["authorization"]),
        action="launch",
        recovery=False,
        expected_marker_sha256=hashlib.sha256(
            path["marker"].read_bytes()
        ).hexdigest(),
        expected_marker_sha256_file=None,
    )


def _write_release(root: Path, mutate) -> None:
    path = _paths(root)["release"]
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _other_branch_commit(root: Path) -> str:
    tree = subprocess.check_output(
        ("git", "rev-parse", "HEAD^{tree}"),
        cwd=root,
        text=True,
    ).strip()
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "RFC-008 audit",
        "GIT_AUTHOR_EMAIL": "audit@example.invalid",
        "GIT_COMMITTER_NAME": "RFC-008 audit",
        "GIT_COMMITTER_EMAIL": "audit@example.invalid",
    }
    commit = subprocess.check_output(
        ("git", "commit-tree", tree),
        cwd=root,
        env=environment,
        input="unrelated branch commit\n",
        text=True,
    ).strip()
    subprocess.run(
        ("git", "update-ref", "refs/heads/audit-unrelated", commit),
        cwd=root,
        check=True,
    )
    return commit


def _commit_path(root: Path, relative: str, content: str, message: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(("git", "add", relative), cwd=root, check=True)
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "RFC-008 audit",
        "GIT_AUTHOR_EMAIL": "audit@example.invalid",
        "GIT_COMMITTER_NAME": "RFC-008 audit",
        "GIT_COMMITTER_EMAIL": "audit@example.invalid",
    }
    subprocess.run(
        ("git", "commit", "-q", "-m", message),
        cwd=root,
        env=environment,
        check=True,
    )
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        text=True,
    ).strip()


def _assert_rejected_everywhere(
    root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _paths(root)
    direct = _active(root)
    lifecycle = _lifecycle(root)
    collection = _collection(root)
    marker = marker_preflight(
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
    assert not direct.valid
    assert not lifecycle["active_release_validation_valid"]
    assert not collection.active_release_validation.valid
    assert not marker["active_release_validation_valid"]
    with pytest.raises(PermissionError, match="collection preflight"):
        _command_run(_args(root))
    with pytest.raises(PermissionError, match="active release"):
        command_status(_args(root))
    command_preflight_collection(_args(root))
    report = json.loads(capsys.readouterr().out)
    assert not report["active_release_validation"]["valid"]
    assert not path["ledger"].exists()


def test_active_authority_is_derived_from_git(
    authority_root: Path,
) -> None:
    path = _paths(authority_root)
    authority = repository_release_authority(
        repository_root=authority_root,
        release_path=path["release"],
    )
    approval_commit = subprocess.check_output(
        (
            "git",
            "log",
            "-1",
            "--format=%H",
            "--",
            str(path["release"].relative_to(authority_root)),
        ),
        cwd=authority_root,
        text=True,
    ).strip()
    assert authority.branch == BRANCH
    assert authority.approval_commit == approval_commit
    assert authority.implementation_commit == subprocess.check_output(
        ("git", "rev-parse", f"{approval_commit}^"),
        cwd=authority_root,
        text=True,
    ).strip()
    assert authority.approval_committed_at_head
    assert authority.approval_commit_is_approval_only
    assert _active(authority_root).valid


def test_research_domain_commit_does_not_require_approval_only_child(
    authority_root: Path,
) -> None:
    path = _paths(authority_root)
    approval_before = repository_release_authority(
        repository_root=authority_root,
        release_path=path["release"],
    )
    research_path = "src/orev3/strategy_lab/research_fixture.py"
    research_head = _commit_path(
        authority_root,
        research_path,
        '"""Offline RFC-010 research fixture."""\n',
        "Add offline research fixture",
    )

    authority_after = repository_release_authority(
        repository_root=authority_root,
        release_path=path["release"],
    )

    assert research_head != authority_after.approval_commit
    assert authority_after == approval_before
    assert _active(authority_root).valid


def test_production_release_closure_commit_requires_approval_only_child(
    authority_root: Path,
) -> None:
    path = _paths(authority_root)
    production_path = "src/orev3/rfc008/release_fixture.py"
    _commit_path(
        authority_root,
        production_path,
        '"""Production Release Closure fixture."""\n',
        "Change production closure",
    )

    with pytest.raises(
        ValueError,
        match="Production Release Closure change requires",
    ):
        repository_release_authority(
            repository_root=authority_root,
            release_path=path["release"],
        )
    assert not _active(authority_root).valid


def test_unclassified_commit_fails_closed_as_production_change(
    authority_root: Path,
) -> None:
    path = _paths(authority_root)
    _commit_path(
        authority_root,
        "unclassified-runtime-input.txt",
        "unknown authority\n",
        "Add unclassified input",
    )

    with pytest.raises(
        ValueError,
        match="Production Release Closure change requires",
    ):
        repository_release_authority(
            repository_root=authority_root,
            release_path=path["release"],
        )


def test_research_package_becomes_closure_when_production_imports_it(
    authority_root: Path,
) -> None:
    path = _paths(authority_root)
    _commit_path(
        authority_root,
        "src/orev3/rfc008/research_dependency_fixture.py",
        "from orev3.strategy_lab import Strategy\n",
        "Add approved production dependency",
    )
    release_text = path["release"].read_text(encoding="utf-8")
    _commit_path(
        authority_root,
        str(path["release"].relative_to(authority_root)),
        release_text + "\n",
        "Approve production dependency",
    )
    _commit_path(
        authority_root,
        "src/orev3/strategy_lab/research_dependency_change.py",
        '"""Now reachable from production."""\n',
        "Change production-reachable research package",
    )

    with pytest.raises(
        ValueError,
        match="Production Release Closure change requires",
    ):
        repository_release_authority(
            repository_root=authority_root,
            release_path=path["release"],
        )


def test_caller_git_authority_parameters_are_removed() -> None:
    active = inspect.signature(validate_active_release).parameters
    lifecycle = inspect.signature(
        validate_post_marker_pre_collection_state
    ).parameters
    forbidden = {
        "expected_branch",
        "expected_implementation_commit",
        "expected_predecessor_sha256",
    }
    assert forbidden.isdisjoint(active)
    assert forbidden.isdisjoint(lifecycle)


@pytest.mark.parametrize(
    "claim",
    ("approval_commit", "grandparent", "unrelated_branch", "nonexistent"),
)
def test_wrong_implementation_rejected_by_every_interface(
    authority_root: Path,
    claim: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if claim == "approval_commit":
        value = subprocess.check_output(
            ("git", "rev-parse", "HEAD"),
            cwd=authority_root,
            text=True,
        ).strip()
    elif claim == "grandparent":
        release = _paths(authority_root)["release"]
        approval_commit = subprocess.check_output(
            (
                "git",
                "log",
                "-1",
                "--format=%H",
                "--",
                str(release.relative_to(authority_root)),
            ),
            cwd=authority_root,
            text=True,
        ).strip()
        value = subprocess.check_output(
            ("git", "rev-parse", f"{approval_commit}^^"),
            cwd=authority_root,
            text=True,
        ).strip()
    elif claim == "unrelated_branch":
        value = _other_branch_commit(authority_root)
    else:
        value = "0" * 40
    _write_release(
        authority_root,
        lambda document: document.__setitem__(
            "approved_implementation_commit",
            value,
        ),
    )
    _assert_rejected_everywhere(authority_root, capsys)


@pytest.mark.parametrize(
    "claim",
    ("skipped", "grand_predecessor", "self", "nonexistent", "missing"),
)
def test_wrong_predecessor_rejected_by_every_interface(
    authority_root: Path,
    claim: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    values = {
        "skipped": (
            "e85f36935f6e639212ff678e035cf051222ce5af9744459271e52e4c0e0f5974"
        ),
        "grand_predecessor": (
            "0724f705905021912ab65ac048c14ee6c8372678c4336c77a40d5f0868f01a80"
        ),
        "self": hashlib.sha256(
            _paths(authority_root)["release"].read_bytes()
        ).hexdigest(),
        "nonexistent": "0" * 64,
    }

    def mutate(document: dict[str, object]) -> None:
        field = "supersedes_release_implementation_approval_sha256"
        if claim == "missing":
            document.pop(field)
        else:
            document[field] = values[claim]

    _write_release(authority_root, mutate)
    _assert_rejected_everywhere(authority_root, capsys)


@pytest.mark.parametrize(
    ("function", "arguments"),
    (
        (
            validate_active_release,
            {
                "expected_implementation_commit": "0" * 40,
            },
        ),
        (
            validate_active_release,
            {
                "expected_predecessor_sha256": "0" * 64,
            },
        ),
        (
            validate_post_marker_pre_collection_state,
            {
                "expected_implementation_commit": "0" * 40,
            },
        ),
        (
            validate_post_marker_pre_collection_state,
            {
                "expected_predecessor_sha256": "0" * 64,
            },
        ),
    ),
)
def test_removed_authority_arguments_fail_at_api_boundary(
    function,
    arguments: dict[str, str],
) -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        function(**arguments)


def test_pending_approval_cannot_approve_an_approval_only_head(
    authority_root: Path,
) -> None:
    path = _paths(authority_root)
    value = json.loads(path["release"].read_text(encoding="utf-8"))
    value["approved_implementation_commit"] = subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=authority_root,
        text=True,
    ).strip()
    value["supersedes_release_implementation_approval_sha256"] = (
        hashlib.sha256(path["release"].read_bytes()).hexdigest()
    )
    path["release"].write_text(
        json.dumps(value, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = _active(authority_root)
    assert not result.valid
    assert any(
        check.check == "active_release_git_authority_available"
        and not check.passed
        for check in result.checks
    )
