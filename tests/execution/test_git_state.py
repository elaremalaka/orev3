from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from orev3.execution.git_state import (
    GitAuthorityError,
    GitDiagnosticCode,
    GitRepository,
    GitTreeEntry,
    RequiredCommittedObject,
    SourceCandidateRequirements,
    _run_bounded_process,
    _validate_safe_governed_entry,
    resolve_source_candidate,
    validate_remote_alias,
)
from orev3.execution.readiness_record import (
    RepositoryAuthorityV1,
    RepositoryEndpoint,
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def initialized_remote(tmp_path: Path) -> tuple[Path, Path, RepositoryAuthorityV1]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    remote.mkdir()
    git(remote, "init", "--bare", "-q")
    work.mkdir()
    git(work, "init", "-q", "-b", "research/post-v1")
    git(work, "config", "user.email", "readiness@example.invalid")
    git(work, "config", "user.name", "Readiness Test")
    git(work, "remote", "add", "origin", remote.as_uri())
    authority = RepositoryAuthorityV1(
        1,
        "synthetic-repository-v1",
        "sha1",
        "refs/heads/research/post-v1",
        (RepositoryEndpoint("file", remote.as_uri()),),
    )
    return work, remote, authority


def requirements() -> SourceCandidateRequirements:
    return SourceCandidateRequirements(
        "synthetic-experiment",
        (
            RequiredCommittedObject("docs/protocol.md"),
            RequiredCommittedObject("src/orev3/adapter.py"),
        ),
        (
            ("docs/protocol.md", "protocol", "top_level", ""),
            ("src/orev3", "source_tree", "top_level", ""),
        ),
    )


def commit_candidate(work: Path) -> str:
    (work / "src/orev3").mkdir(parents=True)
    (work / "docs").mkdir()
    (work / "src/orev3/adapter.py").write_text("VALUE = 1\n", encoding="utf-8")
    (work / "docs/protocol.md").write_text("# Protocol\n", encoding="utf-8")
    (work / ".gitignore").write_text("*.ignored\n", encoding="utf-8")
    git(work, "add", ".gitignore", "docs/protocol.md", "src/orev3/adapter.py")
    git(work, "commit", "-qm", "source candidate")
    git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    return git(work, "rev-parse", "HEAD")


def test_source_candidate_is_derived_from_synchronized_remote(tmp_path: Path) -> None:
    work, _, authority = initialized_remote(tmp_path)
    expected = commit_candidate(work)
    candidate = resolve_source_candidate(
        GitRepository(work),
        authority,
        "origin",
        requirements(),
        allow_test_file=True,
    )
    assert candidate.source_commit == expected
    assert tuple(scope.repository_path for scope in candidate.source_scopes) == (
        "docs/protocol.md",
        "src/orev3",
    )


def test_governed_dirtiness_rejects_but_unrelated_dirtiness_is_reported(
    tmp_path: Path,
) -> None:
    work, _, authority = initialized_remote(tmp_path)
    commit_candidate(work)
    (work / "notes.txt").write_text("unrelated\n", encoding="utf-8")
    candidate = resolve_source_candidate(
        GitRepository(work), authority, "origin", requirements(), allow_test_file=True
    )
    assert candidate.unrelated_worktree_changes == ("notes.txt",)

    (work / "src/orev3/adapter.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(GitAuthorityError) as error:
        resolve_source_candidate(
            GitRepository(work), authority, "origin", requirements(), allow_test_file=True
        )
    assert error.value.code == GitDiagnosticCode.GOVERNED_SCOPE_DIRTY


@pytest.mark.parametrize(
    "mutation",
    ("staged", "deleted", "renamed", "untracked", "ignored", "nested_ignored"),
)
def test_all_governed_worktree_content_is_rejected(
    tmp_path: Path, mutation: str
) -> None:
    work, _, authority = initialized_remote(tmp_path)
    commit_candidate(work)
    adapter = work / "src/orev3/adapter.py"
    if mutation == "staged":
        adapter.write_text("VALUE = 2\n", encoding="utf-8")
        git(work, "add", "src/orev3/adapter.py")
    elif mutation == "deleted":
        adapter.unlink()
    elif mutation == "renamed":
        adapter.rename(work / "src/orev3/renamed.py")
    elif mutation == "untracked":
        (work / "src/orev3/new.py").write_text("NEW = 1\n", encoding="utf-8")
    elif mutation == "ignored":
        (work / "src/orev3/hidden.ignored").write_text("ignored\n", encoding="utf-8")
    else:
        nested = work / "src/orev3/nested"
        nested.mkdir()
        (nested / "hidden.ignored").write_text("ignored\n", encoding="utf-8")
    with pytest.raises(GitAuthorityError) as error:
        resolve_source_candidate(
            GitRepository(work), authority, "origin", requirements(), allow_test_file=True
        )
    assert error.value.code == GitDiagnosticCode.GOVERNED_SCOPE_DIRTY


def test_ignored_content_outside_governed_scope_is_allowed_and_reported(
    tmp_path: Path,
) -> None:
    work, _, authority = initialized_remote(tmp_path)
    commit_candidate(work)
    (work / "notes.ignored").write_text("ignored but unrelated\n", encoding="utf-8")
    candidate = resolve_source_candidate(
        GitRepository(work), authority, "origin", requirements(), allow_test_file=True
    )
    assert candidate.unrelated_worktree_changes == ("notes.ignored",)


def test_governed_symlink_and_nested_symlink_are_rejected(tmp_path: Path) -> None:
    for case in ("direct", "nested"):
        root = tmp_path / case
        root.mkdir()
        work, _, authority = initialized_remote(root)
        commit_candidate(work)
        if case == "direct":
            target = work / "src/orev3/adapter.py"
            target.unlink()
            target.symlink_to("../../../docs/protocol.md")
        else:
            target = work / "src/orev3/nested-link"
            target.symlink_to("../../docs")
        git(work, "add", "src/orev3")
        git(work, "commit", "-qm", "unsafe governed symlink")
        git(work, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
        with pytest.raises(GitAuthorityError) as error:
            resolve_source_candidate(
                GitRepository(work), authority, "origin", requirements(), allow_test_file=True
            )
        assert error.value.code == GitDiagnosticCode.OBJECT_TYPE_INVALID


def test_governed_gitlink_is_rejected(tmp_path: Path) -> None:
    work, _, authority = initialized_remote(tmp_path)
    head = commit_candidate(work)
    git(
        work,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{head},src/orev3/vendor",
    )
    git(work, "commit", "-qm", "unsafe governed gitlink")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    with pytest.raises(GitAuthorityError) as error:
        resolve_source_candidate(
            GitRepository(work), authority, "origin", requirements(), allow_test_file=True
        )
    assert error.value.code == GitDiagnosticCode.OBJECT_TYPE_INVALID


def test_governed_executable_regular_file_is_deterministic(tmp_path: Path) -> None:
    work, _, authority = initialized_remote(tmp_path)
    commit_candidate(work)
    adapter = work / "src/orev3/adapter.py"
    adapter.chmod(0o755)
    git(work, "add", "src/orev3/adapter.py")
    git(work, "commit", "-qm", "permitted executable mode")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    candidate = resolve_source_candidate(
        GitRepository(work), authority, "origin", requirements(), allow_test_file=True
    )
    adapter_scope = next(
        scope for scope in candidate.source_scopes if scope.repository_path == "src/orev3"
    )
    assert adapter_scope.git_mode == "040000"


def test_unsupported_governed_git_mode_fails_closed(tmp_path: Path) -> None:
    work, _, _ = initialized_remote(tmp_path)
    commit_candidate(work)
    repository = GitRepository(work)
    with pytest.raises(GitAuthorityError) as error:
        _validate_safe_governed_entry(
            repository,
            git(work, "rev-parse", "HEAD"),
            GitTreeEntry("100600", "blob", "0" * 40, "src/orev3/unsafe.py"),
        )
    assert error.value.code == GitDiagnosticCode.OBJECT_TYPE_INVALID


@pytest.mark.parametrize("stream", ("stdout", "stderr"))
def test_bounded_process_stops_oversized_output(tmp_path: Path, stream: str) -> None:
    code = "import sys; sys.%s.buffer.write(b'x' * 65536)" % stream
    with pytest.raises(GitAuthorityError) as error:
        _run_bounded_process(
            (sys.executable, "-c", code),
            cwd=tmp_path,
            environment={"PATH": "/usr/bin:/bin"},
            timeout_seconds=5,
            max_output_bytes=1024,
        )
    assert error.value.code == GitDiagnosticCode.GIT_OUTPUT_LIMIT_EXCEEDED


def test_bounded_process_times_out_and_reaps(tmp_path: Path) -> None:
    with pytest.raises(GitAuthorityError) as error:
        _run_bounded_process(
            (sys.executable, "-c", "import time; time.sleep(10)"),
            cwd=tmp_path,
            environment={"PATH": "/usr/bin:/bin"},
            timeout_seconds=0.05,
            max_output_bytes=1024,
        )
    assert error.value.code == GitDiagnosticCode.GIT_COMMAND_TIMEOUT


def test_preparation_rejects_local_remote_divergence(tmp_path: Path) -> None:
    work, _, authority = initialized_remote(tmp_path)
    commit_candidate(work)
    (work / "local.txt").write_text("local commit\n", encoding="utf-8")
    git(work, "add", "local.txt")
    git(work, "commit", "-qm", "local only")
    with pytest.raises(GitAuthorityError) as error:
        resolve_source_candidate(
            GitRepository(work), authority, "origin", requirements(), allow_test_file=True
        )
    assert error.value.code == GitDiagnosticCode.LOCAL_REMOTE_DIVERGENCE


def test_remote_alias_must_match_repository_authority(tmp_path: Path) -> None:
    work, _, authority = initialized_remote(tmp_path)
    commit_candidate(work)
    wrong = RepositoryAuthorityV1(
        1,
        authority.repository_authority_identifier,
        "sha1",
        authority.approved_branch_ref,
        (RepositoryEndpoint("file", (tmp_path / "other.git").as_uri()),),
    )
    with pytest.raises(GitAuthorityError) as error:
        validate_remote_alias(
            GitRepository(work), wrong, "origin", allow_test_file=True
        )
    assert error.value.code == GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED
