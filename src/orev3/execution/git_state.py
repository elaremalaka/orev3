"""Fail-closed Git authority primitives for readiness-v1 Phase 2."""

from __future__ import annotations

import hashlib
import os
import re
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

from orev3.execution.canonical import (
    CanonicalControlError,
    parse_canonical_bytes,
    parse_json,
    require_git_object,
    validate_json_schema_instance,
    validate_repository_path,
)
from orev3.execution.readiness_record import (
    PHASE2_SCHEMA_DOCUMENT_POLICY,
    PHASE2_SCHEMA_POLICY,
    READINESS_TEST_POLICY_PATH,
    REPOSITORY_AUTHORITY_PATH,
    ReadinessRecordV1,
    RepositoryAuthorityV1,
    SourceScopeDeclarationV1,
    load_repository_authority_bytes,
    reconstruct_document_binding_identity,
    reconstruct_protocol_binding_identity,
    validate_implementation_binding,
    validate_readiness_record,
    validate_readiness_test_policy,
)


DEFAULT_GIT_TIMEOUT_SECONDS = 60
MAX_GIT_OUTPUT_BYTES = 8 * 1024 * 1024


class GitDiagnosticCode(str, Enum):
    REMOTE_FETCH_FAILED = "REMOTE_FETCH_FAILED"
    REMOTE_ENDPOINT_NOT_AUTHORIZED = "REMOTE_ENDPOINT_NOT_AUTHORIZED"
    REMOTE_REF_INVALID = "REMOTE_REF_INVALID"
    SHALLOW_HISTORY_INCOMPLETE = "SHALLOW_HISTORY_INCOMPLETE"
    CANONICAL_RECORD_INVALID = "CANONICAL_RECORD_INVALID"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    OBJECT_TYPE_INVALID = "OBJECT_TYPE_INVALID"
    GOVERNED_OBJECT_MISSING = "GOVERNED_OBJECT_MISSING"
    GOVERNED_OBJECT_MISMATCH = "GOVERNED_OBJECT_MISMATCH"
    GOVERNED_SCOPE_DIRTY = "GOVERNED_SCOPE_DIRTY"
    LOCAL_REMOTE_DIVERGENCE = "LOCAL_REMOTE_DIVERGENCE"
    SEAL_NOT_FOUND = "SEAL_NOT_FOUND"
    SEAL_AMBIGUOUS = "SEAL_AMBIGUOUS"
    SEAL_COMMIT_SHAPE_INVALID = "SEAL_COMMIT_SHAPE_INVALID"
    FIRST_PARENT_ANCESTRY_INVALID = "FIRST_PARENT_ANCESTRY_INVALID"
    SOURCE_STALE = "SOURCE_STALE"
    GIT_OUTPUT_LIMIT_EXCEEDED = "GIT_OUTPUT_LIMIT_EXCEEDED"
    GIT_COMMAND_TIMEOUT = "GIT_COMMAND_TIMEOUT"
    GIT_COMMAND_FAILED = "GIT_COMMAND_FAILED"


class GitAuthorityError(RuntimeError):
    def __init__(
        self,
        code: GitDiagnosticCode,
        message: str,
        *,
        repository_path: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.repository_path = repository_path


@dataclass(frozen=True, slots=True)
class AuthorityDiagnostic:
    code: GitDiagnosticCode
    message: str
    repository_path: str = ""


@dataclass(frozen=True, slots=True)
class GitTreeEntry:
    mode: str
    object_type: str
    object_identity: str
    repository_path: str


@dataclass(frozen=True, slots=True)
class ResolvedRemoteHead:
    repository_authority_identifier: str
    approved_branch_ref: str
    remote_alias: str
    remote_head_commit: str
    fetched_ref: str


@dataclass(frozen=True, slots=True)
class RequiredCommittedObject:
    repository_path: str
    expected_sha256: str = ""
    expected_type: str = "blob"


@dataclass(frozen=True, slots=True)
class SourceCandidateRequirements:
    experiment_identifier: str
    required_objects: tuple[RequiredCommittedObject, ...]
    governed_scopes: tuple[tuple[str, str, str, str], ...]


@dataclass(frozen=True, slots=True)
class SourceCandidate:
    source_commit: str
    remote_head: ResolvedRemoteHead
    source_scopes: tuple[SourceScopeDeclarationV1, ...]
    unrelated_worktree_changes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReadinessSealDerivation:
    source_commit: str
    readiness_seal_commit: str
    remote_head_commit: str
    canonical_record_path: str
    readiness_record_blob_identity: str


@dataclass(frozen=True, slots=True)
class BoundSchemaRegistry:
    schemas_by_object_kind: dict[str, dict[str, Any]]

    def schema_for(self, object_kind: str) -> dict[str, Any]:
        try:
            return self.schemas_by_object_kind[object_kind]
        except KeyError as exc:
            raise CanonicalControlError(
                f"bound schema is unavailable: {object_kind}"
            ) from exc

    def filename_registry(self) -> dict[str, dict[str, Any]]:
        return {
            PHASE2_SCHEMA_POLICY[kind][1].rsplit("/", 1)[-1]: schema
            for kind, schema in self.schemas_by_object_kind.items()
        }


def _run_bounded_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: float,
    max_output_bytes: int,
) -> subprocess.CompletedProcess[bytes]:
    """Run one non-shell command while bounding both pipes during capture."""

    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout_seconds
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate_process_group(process)
                raise GitAuthorityError(
                    GitDiagnosticCode.GIT_COMMAND_TIMEOUT,
                    "Git command exceeded its timeout",
                )
            events = selector.select(min(remaining, 0.25))
            if not events and process.poll() is not None:
                # A terminated process may leave EOF notifications for one
                # selector cycle; continue until both descriptors are drained.
                continue
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 65_536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                target = buffers[key.data]
                if len(target) + len(chunk) > max_output_bytes:
                    _terminate_process_group(process)
                    raise GitAuthorityError(
                        GitDiagnosticCode.GIT_OUTPUT_LIMIT_EXCEEDED,
                        f"Git {key.data} exceeded the bounded limit",
                    )
                target.extend(chunk)
        return_code = process.wait(timeout=max(deadline - time.monotonic(), 0.001))
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process)
        raise GitAuthorityError(
            GitDiagnosticCode.GIT_COMMAND_TIMEOUT,
            "Git command exceeded its timeout",
        ) from exc
    finally:
        selector.close()
        for pipe in (process.stdout, process.stderr):
            if not pipe.closed:
                pipe.close()
        if process.poll() is None:
            _terminate_process_group(process)
    return subprocess.CompletedProcess(
        command,
        return_code,
        bytes(buffers["stdout"]),
        bytes(buffers["stderr"]),
    )


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


class GitRepository:
    """Checked, non-shell Git plumbing with structured failures."""

    def __init__(
        self,
        root: str | Path,
        *,
        git_executable: str = "git",
        timeout_seconds: int = DEFAULT_GIT_TIMEOUT_SECONDS,
        max_output_bytes: int = MAX_GIT_OUTPUT_BYTES,
    ) -> None:
        requested_root = Path(root)
        if requested_root.is_symlink():
            raise GitAuthorityError(
                GitDiagnosticCode.GIT_COMMAND_FAILED,
                "repository root must not be a symlink",
            )
        candidate = requested_root.resolve()
        self.root = candidate
        self.git_executable = git_executable
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        top = self.text("rev-parse", "--show-toplevel")
        if Path(top).resolve() != candidate:
            raise GitAuthorityError(
                GitDiagnosticCode.GIT_COMMAND_FAILED,
                "repository root is not the exact Git top level",
            )

    def _environment(self) -> dict[str, str]:
        environment = {
            "GIT_OPTIONAL_LOCKS": "0",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "TZ": "UTC",
        }
        for key in ("HOME", "SSH_AUTH_SOCK", "GIT_ASKPASS", "SSH_ASKPASS"):
            if key in os.environ:
                environment[key] = os.environ[key]
        return environment

    def run(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        if any(not isinstance(argument, str) or "\x00" in argument for argument in arguments):
            raise GitAuthorityError(
                GitDiagnosticCode.GIT_COMMAND_FAILED,
                "Git arguments must be NUL-free strings",
            )
        try:
            completed = _run_bounded_process(
                (self.git_executable, *arguments),
                cwd=self.root,
                environment=self._environment(),
                timeout_seconds=self.timeout_seconds,
                max_output_bytes=self.max_output_bytes,
            )
        except OSError as exc:
            raise GitAuthorityError(
                GitDiagnosticCode.GIT_COMMAND_FAILED,
                "Git command could not complete",
            ) from exc
        if check and completed.returncode != 0:
            raise GitAuthorityError(
                GitDiagnosticCode.GIT_COMMAND_FAILED,
                f"Git command failed with exit status {completed.returncode}",
            )
        return completed

    def bytes(self, *arguments: str) -> bytes:
        return self.run(*arguments).stdout

    def text(self, *arguments: str) -> str:
        try:
            return self.bytes(*arguments).decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise GitAuthorityError(
                GitDiagnosticCode.GIT_COMMAND_FAILED,
                "Git returned non-UTF-8 control output",
            ) from exc

    def object_format(self) -> str:
        completed = self.run("rev-parse", "--show-object-format", check=False)
        if completed.returncode == 0:
            value = completed.stdout.decode("ascii", errors="strict").strip()
        else:
            value = self.text("config", "--get", "extensions.objectFormat") or "sha1"
        if value not in {"sha1", "sha256"}:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "repository Git object format is unsupported",
            )
        return value

    def resolve_commit(self, revision: str) -> str:
        _require_revision_syntax(revision)
        completed = self.run(
            "rev-parse", "--verify", f"{revision}^{{commit}}", check=False
        )
        if completed.returncode != 0:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_NOT_FOUND,
                "required Git commit cannot be resolved",
            )
        try:
            resolved = completed.stdout.decode("ascii", errors="strict").strip()
        except UnicodeDecodeError as exc:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "resolved Git commit identity is malformed",
            ) from exc
        require_git_object("commit", resolved, self.object_format())
        return resolved

    def object_type(self, object_identity: str) -> str:
        require_git_object("object identity", object_identity, self.object_format())
        return self.text("cat-file", "-t", object_identity)

    def object_bytes(self, object_identity: str, *, max_bytes: int) -> bytes:
        require_git_object("object identity", object_identity, self.object_format())
        size_text = self.text("cat-file", "-s", object_identity)
        try:
            size = int(size_text)
        except ValueError as exc:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "Git object size is invalid",
            ) from exc
        if size < 0 or size > max_bytes:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "Git object exceeds permitted byte size",
            )
        data = self.bytes("cat-file", "blob", object_identity)
        if len(data) != size:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "Git object size changed during read",
            )
        return data

    def tree_entry(self, commit: str, repository_path: str) -> GitTreeEntry:
        commit = self.resolve_commit(commit)
        path = validate_repository_path(repository_path)
        raw = self.bytes("ls-tree", "-z", "--full-tree", commit, "--", path)
        records = [record for record in raw.split(b"\x00") if record]
        exact: list[GitTreeEntry] = []
        for record in records:
            try:
                header, encoded_path = record.split(b"\t", 1)
                mode, kind, object_identity = header.decode("ascii").split(" ")
                decoded_path = encoded_path.decode("utf-8", errors="strict")
            except (ValueError, UnicodeDecodeError) as exc:
                raise GitAuthorityError(
                    GitDiagnosticCode.OBJECT_TYPE_INVALID,
                    "Git tree entry is malformed",
                ) from exc
            if decoded_path == path:
                exact.append(GitTreeEntry(mode, kind, object_identity, decoded_path))
        if len(exact) != 1:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_NOT_FOUND,
                "required committed path is absent or ambiguous",
                repository_path=path,
            )
        return exact[0]

    def optional_tree_entry(self, commit: str, repository_path: str) -> GitTreeEntry | None:
        try:
            return self.tree_entry(commit, repository_path)
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.OBJECT_NOT_FOUND:
                return None
            raise

    def recursive_tree_entries(
        self, commit: str, repository_path: str
    ) -> tuple[GitTreeEntry, ...]:
        commit = self.resolve_commit(commit)
        path = validate_repository_path(repository_path)
        root = self.tree_entry(commit, path)
        if root.object_type != "tree" or root.mode != "040000":
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "governed tree scope is not an ordinary Git tree",
                repository_path=path,
            )
        raw = self.bytes(
            "ls-tree", "-r", "-t", "-z", "--full-tree", commit, "--", path
        )
        entries: list[GitTreeEntry] = []
        for record in (item for item in raw.split(b"\x00") if item):
            try:
                header, encoded_path = record.split(b"\t", 1)
                mode, kind, object_identity = header.decode("ascii").split(" ")
                decoded_path = encoded_path.decode("utf-8", errors="strict")
            except (ValueError, UnicodeDecodeError) as exc:
                raise GitAuthorityError(
                    GitDiagnosticCode.OBJECT_TYPE_INVALID,
                    "recursive Git tree entry is malformed",
                ) from exc
            validate_repository_path(decoded_path)
            entries.append(
                GitTreeEntry(mode, kind, object_identity, decoded_path)
            )
        return tuple(entries)

    def first_parent_history(self, head: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
        head = self.resolve_commit(head)
        lines = self.text("rev-list", "--first-parent", "--parents", head).splitlines()
        result: list[tuple[str, tuple[str, ...]]] = []
        for line in lines:
            fields = line.split()
            if not fields:
                continue
            for field in fields:
                require_git_object("history object", field, self.object_format())
            result.append((fields[0], tuple(fields[1:])))
        return tuple(result)

    def changed_paths(self, parent: str, commit: str) -> tuple[str, ...]:
        parent = self.resolve_commit(parent)
        commit = self.resolve_commit(commit)
        raw = self.bytes(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "-z",
            parent,
            commit,
            "--",
        )
        paths = tuple(
            item.decode("utf-8", errors="strict")
            for item in raw.split(b"\x00")
            if item
        )
        for path in paths:
            validate_repository_path(path)
        return paths

    def diff_paths(self, older: str, newer: str, paths: Iterable[str]) -> tuple[str, ...]:
        normalized = tuple(validate_repository_path(path) for path in paths)
        raw = self.bytes(
            "diff",
            "--name-only",
            "-z",
            older,
            newer,
            "--",
            *normalized,
        )
        return tuple(
            item.decode("utf-8", errors="strict")
            for item in raw.split(b"\x00")
            if item
        )

    def working_tree_changes(self, scopes: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        normalized = tuple(validate_repository_path(path) for path in scopes)
        inside: set[str] = set()
        for command in (
            ("diff", "--name-only", "-z", "--", *normalized),
            ("diff", "--cached", "--name-only", "-z", "--", *normalized),
            ("ls-files", "--others", "--exclude-standard", "-z", "--", *normalized),
            (
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "-z",
                "--",
                *normalized,
            ),
        ):
            inside.update(
                value.decode("utf-8", errors="strict")
                for value in self.bytes(*command).split(b"\x00")
                if value
            )
        all_status = self.bytes("status", "--porcelain=v1", "-z", "--untracked-files=all")
        all_paths: set[str] = set()
        records = [item for item in all_status.split(b"\x00") if item]
        index = 0
        while index < len(records):
            record = records[index]
            if len(record) >= 4:
                path = record[3:].decode("utf-8", errors="strict")
                all_paths.add(path)
                if record[:2] in {b"R ", b"C ", b"RM", b"CM"} and index + 1 < len(records):
                    index += 1
                    all_paths.add(records[index].decode("utf-8", errors="strict"))
            index += 1
        ignored = self.bytes(
            "ls-files", "--others", "--ignored", "--exclude-standard", "-z"
        )
        all_paths.update(
            value.decode("utf-8", errors="strict")
            for value in ignored.split(b"\x00")
            if value
        )
        return tuple(sorted(inside)), tuple(sorted(all_paths - inside))

    def is_shallow(self) -> bool:
        return self.text("rev-parse", "--is-shallow-repository") == "true"


def canonicalize_remote_endpoint(value: str, *, allow_test_file: bool = False) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "remote endpoint is invalid",
        )
    if value.startswith("file://"):
        if not allow_test_file:
            raise GitAuthorityError(
                GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
                "filesystem remotes are test-only",
            )
        return value
    split = urlsplit(value)
    if split.scheme not in {"https", "ssh"} or not split.hostname:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "remote endpoint transport is unsupported",
        )
    if split.password is not None or split.query or split.fragment:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "credential-bearing or parameterized remote endpoint is prohibited",
        )
    if split.username not in {None, "git"}:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "remote endpoint username is not canonical",
        )
    host = split.hostname.lower()
    port = f":{split.port}" if split.port is not None else ""
    user = "git@" if split.username == "git" else ""
    path = re.sub(r"/{2,}", "/", split.path)
    return urlunsplit((split.scheme, f"{user}{host}{port}", path, "", ""))


def validate_remote_alias(
    repository: GitRepository,
    authority: RepositoryAuthorityV1,
    remote_alias: str,
    *,
    allow_test_file: bool = False,
) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", remote_alias):
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "remote alias syntax is invalid",
        )
    completed = repository.run(
        "config", "--get-all", f"remote.{remote_alias}.url", check=False
    )
    if completed.returncode != 0:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "remote alias does not resolve",
        )
    urls = [line for line in completed.stdout.decode("utf-8", errors="strict").splitlines() if line]
    if len(urls) != 1:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "remote alias must resolve to exactly one fetch endpoint",
        )
    actual = canonicalize_remote_endpoint(urls[0], allow_test_file=allow_test_file)
    allowed = {
        canonicalize_remote_endpoint(
            endpoint.canonical_endpoint, allow_test_file=allow_test_file
        )
        for endpoint in authority.canonical_fetch_endpoints
    }
    if actual not in allowed:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_ENDPOINT_NOT_AUTHORIZED,
            "remote alias endpoint is not repository-authorized",
        )
    return actual


def fetch_remote_head(
    repository: GitRepository,
    authority: RepositoryAuthorityV1,
    remote_alias: str,
    *,
    allow_test_file: bool = False,
) -> ResolvedRemoteHead:
    validate_remote_alias(
        repository, authority, remote_alias, allow_test_file=allow_test_file
    )
    if repository.object_format() != authority.git_object_format:
        raise GitAuthorityError(
            GitDiagnosticCode.OBJECT_TYPE_INVALID,
            "repository object format differs from authority",
        )
    digest = hashlib.sha256(
        f"{authority.repository_authority_identifier}\n{authority.approved_branch_ref}".encode()
    ).hexdigest()[:24]
    fetched_ref = f"refs/orev3/readiness/fetched/{digest}"
    refspec = f"+{authority.approved_branch_ref}:{fetched_ref}"
    completed = repository.run(
        "fetch", "--no-tags", "--force", remote_alias, refspec, check=False
    )
    if completed.returncode != 0:
        raise GitAuthorityError(
            GitDiagnosticCode.REMOTE_FETCH_FAILED,
            "fresh approved-ref fetch failed",
        )
    head = repository.resolve_commit(fetched_ref)
    if repository.is_shallow():
        raise GitAuthorityError(
            GitDiagnosticCode.SHALLOW_HISTORY_INCOMPLETE,
            "shallow history cannot establish readiness authority",
        )
    return ResolvedRemoteHead(
        authority.repository_authority_identifier,
        authority.approved_branch_ref,
        remote_alias,
        head,
        fetched_ref,
    )


def resolve_source_candidate(
    repository: GitRepository,
    authority: RepositoryAuthorityV1,
    remote_alias: str,
    requirements: SourceCandidateRequirements,
    *,
    allow_test_file: bool = False,
) -> SourceCandidate:
    """Derive S from synchronized authority; no manual commit is accepted."""

    remote = fetch_remote_head(
        repository, authority, remote_alias, allow_test_file=allow_test_file
    )
    branch = repository.text("symbolic-ref", "--quiet", "HEAD")
    if branch != authority.approved_branch_ref:
        raise GitAuthorityError(
            GitDiagnosticCode.LOCAL_REMOTE_DIVERGENCE,
            "checked-out branch is not the approved full branch ref",
        )
    local_head = repository.resolve_commit("HEAD")
    if local_head != remote.remote_head_commit:
        raise GitAuthorityError(
            GitDiagnosticCode.LOCAL_REMOTE_DIVERGENCE,
            "local HEAD differs from freshly fetched approved head",
        )
    for required in requirements.required_objects:
        entry = repository.tree_entry(local_head, required.repository_path)
        if entry.object_type != required.expected_type:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "required committed object has the wrong Git type",
                repository_path=required.repository_path,
            )
        _validate_safe_governed_entry(repository, local_head, entry)
        if required.expected_sha256:
            raw = repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
            if hashlib.sha256(raw).hexdigest() != required.expected_sha256:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "required committed object digest differs from binding",
                    repository_path=required.repository_path,
                )
    scopes: list[SourceScopeDeclarationV1] = []
    for path, role, nesting, parent_path in sorted(requirements.governed_scopes):
        entry = repository.tree_entry(local_head, path)
        _validate_safe_governed_entry(repository, local_head, entry)
        material: dict[str, Any] = {
            "git_mode": entry.mode,
            "git_object_identity": entry.object_identity,
            "nesting": nesting,
            "repository_path": path,
            "role": role,
        }
        if nesting == "nested":
            material["parent_path"] = parent_path
        scopes.append(SourceScopeDeclarationV1.from_mapping(material))
    scope_paths = tuple(item[0] for item in requirements.governed_scopes)
    inside, outside = repository.working_tree_changes(scope_paths)
    if inside:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_SCOPE_DIRTY,
            "governed source scopes contain working-tree content",
            repository_path=inside[0],
        )
    return SourceCandidate(local_head, remote, tuple(scopes), outside)


def inspect_committed_requirements(
    repository: GitRepository,
    commit: str,
    requirements: SourceCandidateRequirements,
) -> tuple[SourceScopeDeclarationV1, ...]:
    """Read-only historical/test inspection; never an official authority API."""

    resolved = repository.resolve_commit(commit)
    for required in requirements.required_objects:
        entry = repository.tree_entry(resolved, required.repository_path)
        if entry.object_type != required.expected_type:
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "historical required object has the wrong type",
                repository_path=required.repository_path,
            )
        _validate_safe_governed_entry(repository, resolved, entry)
        if required.expected_sha256:
            raw = repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
            if hashlib.sha256(raw).hexdigest() != required.expected_sha256:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "historical required object digest differs from binding",
                    repository_path=required.repository_path,
                )
    result: list[SourceScopeDeclarationV1] = []
    for path, role, nesting, parent_path in sorted(requirements.governed_scopes):
        entry = repository.tree_entry(resolved, path)
        _validate_safe_governed_entry(repository, resolved, entry)
        material: dict[str, Any] = {
            "git_mode": entry.mode,
            "git_object_identity": entry.object_identity,
            "nesting": nesting,
            "repository_path": path,
            "role": role,
        }
        if nesting == "nested":
            material["parent_path"] = parent_path
        result.append(SourceScopeDeclarationV1.from_mapping(material))
    return tuple(result)


def _validate_safe_governed_entry(
    repository: GitRepository, commit: str, entry: GitTreeEntry
) -> None:
    if entry.object_type == "blob" and entry.mode in {"100644", "100755"}:
        return
    if entry.object_type == "tree" and entry.mode == "040000":
        for nested in repository.recursive_tree_entries(commit, entry.repository_path):
            if nested.object_type == "tree" and nested.mode == "040000":
                continue
            if nested.object_type == "blob" and nested.mode in {"100644", "100755"}:
                continue
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "governed tree contains a symlink, gitlink, or unsupported Git mode",
                repository_path=nested.repository_path,
            )
        return
    raise GitAuthorityError(
        GitDiagnosticCode.OBJECT_TYPE_INVALID,
        "governed path has a symlink, gitlink, or unsupported Git mode",
        repository_path=entry.repository_path,
    )


def derive_readiness_seal(
    repository: GitRepository,
    *,
    remote_head_commit: str,
    record: ReadinessRecordV1,
    record_blob_identity: str,
) -> ReadinessSealDerivation:
    head = repository.resolve_commit(remote_head_commit)
    current = repository.tree_entry(head, record.canonical_record_path)
    if current.object_type != "blob" or current.object_identity != record_blob_identity:
        raise GitAuthorityError(
            GitDiagnosticCode.SEAL_AMBIGUOUS,
            "current canonical record blob is not pinned at remote head",
            repository_path=record.canonical_record_path,
        )
    try:
        history = repository.first_parent_history(head)
    except GitAuthorityError as exc:
        if exc.code == GitDiagnosticCode.GIT_COMMAND_FAILED:
            raise GitAuthorityError(
                GitDiagnosticCode.FIRST_PARENT_ANCESTRY_INVALID,
                "required first-parent authority history cannot be reconstructed",
            ) from exc
        raise
    transition: tuple[str, tuple[str, ...]] | None = None
    for commit, parents in history:
        entry = repository.optional_tree_entry(commit, record.canonical_record_path)
        if entry is None or entry.object_identity != record_blob_identity:
            continue
        parent_entry = (
            repository.optional_tree_entry(parents[0], record.canonical_record_path)
            if parents
            else None
        )
        if parent_entry is None or parent_entry.object_identity != record_blob_identity:
            transition = (commit, parents)
            break
    if transition is None:
        raise GitAuthorityError(
            GitDiagnosticCode.SEAL_NOT_FOUND,
            "current record blob has no first-parent introduction",
        )
    seal, parents = transition
    if len(parents) != 1:
        raise GitAuthorityError(
            GitDiagnosticCode.SEAL_COMMIT_SHAPE_INVALID,
            "readiness seal introduction is not single-parent",
        )
    changed = repository.changed_paths(parents[0], seal)
    if changed != (record.canonical_record_path,):
        raise GitAuthorityError(
            GitDiagnosticCode.SEAL_COMMIT_SHAPE_INVALID,
            "readiness seal commit changes paths other than the canonical record",
        )
    commits = [commit for commit, _ in history]
    try:
        head_index = commits.index(head)
        seal_index = commits.index(seal)
        source_index = commits.index(record.source_commit)
    except ValueError as exc:
        raise GitAuthorityError(
            GitDiagnosticCode.FIRST_PARENT_ANCESTRY_INVALID,
            "S, R, and H are not on one first-parent authority history",
        ) from exc
    if not head_index <= seal_index <= source_index or seal == record.source_commit:
        raise GitAuthorityError(
            GitDiagnosticCode.FIRST_PARENT_ANCESTRY_INVALID,
            "required S ancestor-of R ancestor-of H ordering does not hold",
        )
    governed_paths = tuple(scope.repository_path for scope in record.source_scopes)
    changed_governed = tuple(
        path
        for path in repository.diff_paths(record.source_commit, head, governed_paths)
        if path != record.canonical_record_path
    )
    if changed_governed:
        raise GitAuthorityError(
            GitDiagnosticCode.SOURCE_STALE,
            "governed source changed after S",
            repository_path=changed_governed[0],
        )
    for scope in record.source_scopes:
        at_source = repository.tree_entry(record.source_commit, scope.repository_path)
        _validate_safe_governed_entry(repository, record.source_commit, at_source)
        if (
            at_source.object_identity != scope.git_object_identity
            or at_source.mode != scope.git_mode
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "recorded governed object differs from S",
                repository_path=scope.repository_path,
            )
    return ReadinessSealDerivation(
        record.source_commit,
        seal,
        head,
        record.canonical_record_path,
        record_blob_identity,
    )


def validate_record_git_bindings(
    repository: GitRepository,
    record: ReadinessRecordV1,
    authority: RepositoryAuthorityV1,
) -> BoundSchemaRegistry:
    """Reconstruct every Phase-2 byte/Git binding declared by the record at S."""

    source = record.source_commit
    for section_name, identity_field in (
        ("readiness_specification", "specification_identity"),
        ("protocol", "protocol_identity"),
        ("execution_specification", "specification_identity"),
    ):
        binding = record.material[section_name]
        _validate_blob_binding(repository, source, binding, section_name)
        if reconstruct_document_binding_identity(
            binding, identity_field=identity_field
        ) != binding[identity_field]:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "declared document identity does not reconstruct",
                repository_path=binding["path"],
            )
    runtime = record.material["runtime"]
    _validate_blob_binding(
        repository,
        source,
        {
            "path": runtime["dependency_manifest_path"],
            "byte_count": repository.tree_entry(
                source, runtime["dependency_manifest_path"]
            )
            and len(
                repository.object_bytes(
                    repository.tree_entry(
                        source, runtime["dependency_manifest_path"]
                    ).object_identity,
                    max_bytes=8 * 1024 * 1024,
                )
            ),
            "sha256": runtime["dependency_manifest_sha256"],
            "git_blob_identity": runtime["dependency_manifest_git_blob_identity"],
        },
        "dependency manifest",
    )
    schemas: dict[str, dict[str, Any]] = {}
    for declaration in record.material["schema"]["declarations"]:
        raw = _validate_blob_binding(
            repository, source, declaration, "schema declaration"
        )
        try:
            schema = parse_json(raw, max_bytes=1_048_576)
        except CanonicalControlError as exc:
            raise GitAuthorityError(
                GitDiagnosticCode.CANONICAL_RECORD_INVALID,
                "bound schema is malformed",
                repository_path=declaration["path"],
            ) from exc
        if not isinstance(schema, dict) or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise GitAuthorityError(
                GitDiagnosticCode.CANONICAL_RECORD_INVALID,
                "bound schema is not a supported JSON Schema document",
                repository_path=declaration["path"],
            )
        expected_schema_id, expected_digest = PHASE2_SCHEMA_DOCUMENT_POLICY[
            declaration["object_kind"]
        ]
        if (
            schema.get("$id") != expected_schema_id
            or hashlib.sha256(raw).hexdigest() != expected_digest
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.CANONICAL_RECORD_INVALID,
                "bound schema conflicts with the repository-owned v1 schema policy",
                repository_path=declaration["path"],
            )
        schemas[declaration["object_kind"]] = schema
    registry = BoundSchemaRegistry(schemas)
    try:
        validate_json_schema_instance(
            record.material,
            registry.schema_for("readiness-record"),
            schema_registry=registry.filename_registry(),
        )
    except CanonicalControlError as exc:
        raise GitAuthorityError(
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            "readiness record conflicts with its bound machine schema",
            repository_path=record.canonical_record_path,
        ) from exc

    authority_entry = repository.tree_entry(source, REPOSITORY_AUTHORITY_PATH)
    _validate_safe_governed_entry(repository, source, authority_entry)
    authority_raw = repository.object_bytes(
        authority_entry.object_identity, max_bytes=1_048_576
    )
    try:
        authority_material = parse_canonical_bytes(authority_raw)
        validate_json_schema_instance(
            authority_material,
            registry.schema_for("repository-authority"),
            schema_registry=registry.filename_registry(),
        )
        committed_authority = load_repository_authority_bytes(authority_raw)
    except CanonicalControlError as exc:
        raise GitAuthorityError(
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            "committed repository authority is malformed",
            repository_path=REPOSITORY_AUTHORITY_PATH,
        ) from exc
    if committed_authority != authority:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "runtime repository authority differs from committed S",
            repository_path=REPOSITORY_AUTHORITY_PATH,
        )

    implementation = record.material["implementation"]
    implementation_entry = repository.tree_entry(
        source, implementation["implementation_path"]
    )
    _validate_safe_governed_entry(repository, source, implementation_entry)
    implementation_raw = repository.object_bytes(
        implementation_entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    if (
        implementation_entry.object_identity
        != implementation["implementation_git_blob_identity"]
        or hashlib.sha256(implementation_raw).hexdigest()
        != implementation["implementation_sha256"]
    ):
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "implementation source differs from record",
            repository_path=implementation["implementation_path"],
        )
    binding_raw = _validate_blob_binding(
        repository,
        source,
        {
            "path": implementation["protocol_binding_path"],
            "byte_count": implementation["protocol_binding_byte_count"],
            "sha256": implementation["protocol_binding_sha256"],
            "git_blob_identity": implementation[
                "protocol_binding_git_blob_identity"
            ],
        },
        "implementation protocol binding",
    )
    try:
        binding_material = parse_canonical_bytes(binding_raw)
        validate_json_schema_instance(
            binding_material,
            registry.schema_for("implementation-binding"),
            schema_registry=registry.filename_registry(),
        )
        validate_implementation_binding(
            binding_material, object_format=repository.object_format()
        )
    except CanonicalControlError as exc:
        raise GitAuthorityError(
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            "implementation protocol binding is malformed",
            repository_path=implementation["protocol_binding_path"],
        ) from exc
    _validate_protocol_binding_relationship(record, binding_material)

    policy_entry = repository.tree_entry(source, READINESS_TEST_POLICY_PATH)
    _validate_safe_governed_entry(repository, source, policy_entry)
    policy_raw = repository.object_bytes(policy_entry.object_identity, max_bytes=1_048_576)
    try:
        policy_material = parse_canonical_bytes(
            policy_raw, validator=validate_readiness_test_policy
        )
        validate_json_schema_instance(
            policy_material,
            registry.schema_for("readiness-test-policy"),
            schema_registry=registry.filename_registry(),
        )
    except CanonicalControlError as exc:
        raise GitAuthorityError(
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            "mandatory readiness test policy is malformed",
            repository_path=READINESS_TEST_POLICY_PATH,
        ) from exc
    if (
        policy_material["policy_identity"]
        != record.material["validation"]["test_policy_identity"]
        or policy_material["required_selectors"]
        != record.material["validation"]["test_selectors"]
    ):
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "mandatory readiness test policy differs from record",
            repository_path=READINESS_TEST_POLICY_PATH,
        )
    for component in record.material["control_plane"]["components"]:
        entry = repository.tree_entry(source, component["path"])
        _validate_safe_governed_entry(repository, source, entry)
        if entry.object_identity != component["git_object_identity"]:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "control-plane Git object differs from record",
                repository_path=component["path"],
            )
        if entry.object_type != "blob":
            raise GitAuthorityError(
                GitDiagnosticCode.OBJECT_TYPE_INVALID,
                "Phase-2 control-plane component binding must name a file",
                repository_path=component["path"],
            )
        raw = repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
        if hashlib.sha256(raw).hexdigest() != component["sha256"]:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "control-plane component digest differs from record",
                repository_path=component["path"],
            )
    return registry


def _validate_protocol_binding_relationship(
    record: ReadinessRecordV1, binding: Mapping[str, Any]
) -> None:
    implementation = record.material["implementation"]
    protocol = record.material["protocol"]
    expected = {
        "adapter_identifier": implementation["adapter_identifier"],
        "entry_point": implementation["entry_point"],
        "experiment_identifier": record.experiment_identifier,
        "implementation_path": implementation["implementation_path"],
        "implementation_git_blob_identity": implementation[
            "implementation_git_blob_identity"
        ],
        "implementation_sha256": implementation["implementation_sha256"],
        "protocol_identifier": protocol["identifier"],
        "protocol_revision": protocol["revision"],
        "protocol_sha256": protocol["sha256"],
        "execution_specification_identity": record.material[
            "execution_specification"
        ]["specification_identity"],
        "profile_identity": record.material["execution_profile"]["profile_identity"],
        "experiment_configuration_identity": record.material["configuration"][
            "experiment_configuration_identity"
        ],
        "protocol_binding_identity": implementation["protocol_binding_identity"],
    }
    actual = {
        "adapter_identifier": binding["adapter_identifier"],
        "entry_point": binding["entry_point"],
        "experiment_identifier": binding["experiment_identifier"],
        "implementation_path": binding["implementation"]["path"],
        "implementation_git_blob_identity": binding["implementation"][
            "git_blob_identity"
        ],
        "implementation_sha256": binding["implementation"]["sha256"],
        "protocol_identifier": binding["protocol"]["identifier"],
        "protocol_revision": binding["protocol"]["revision"],
        "protocol_sha256": binding["protocol"]["sha256"],
        "execution_specification_identity": binding[
            "execution_specification_identity"
        ],
        "profile_identity": binding["profile_identity"],
        "experiment_configuration_identity": binding[
            "experiment_configuration_identity"
        ],
        "protocol_binding_identity": binding["protocol_binding_identity"],
    }
    if actual != expected or reconstruct_protocol_binding_identity(binding) != implementation["protocol_binding_identity"]:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "implementation binding is inconsistent with protocol or record",
            repository_path=implementation["protocol_binding_path"],
        )


def _validate_blob_binding(
    repository: GitRepository,
    source_commit: str,
    binding: Any,
    label: str,
) -> bytes:
    path = binding["path"]
    entry = repository.tree_entry(source_commit, path)
    _validate_safe_governed_entry(repository, source_commit, entry)
    if entry.object_type != "blob":
        raise GitAuthorityError(
            GitDiagnosticCode.OBJECT_TYPE_INVALID,
            f"{label} must bind a Git blob",
            repository_path=path,
        )
    if entry.object_identity != binding["git_blob_identity"]:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            f"{label} Git blob differs from record",
            repository_path=path,
        )
    raw = repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
    if len(raw) != binding["byte_count"] or hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            f"{label} byte binding differs from record",
            repository_path=path,
        )
    return raw


def _require_revision_syntax(value: str) -> None:
    if not isinstance(value, str) or not value or value.startswith("-") or "\x00" in value:
        raise CanonicalControlError("Git revision syntax is invalid")
    if not re.fullmatch(r"[A-Za-z0-9_./{}^~-]+", value):
        raise CanonicalControlError("Git revision contains prohibited characters")


__all__ = [
    "AuthorityDiagnostic",
    "BoundSchemaRegistry",
    "GitAuthorityError",
    "GitDiagnosticCode",
    "GitRepository",
    "ReadinessSealDerivation",
    "RequiredCommittedObject",
    "ResolvedRemoteHead",
    "SourceCandidate",
    "SourceCandidateRequirements",
    "canonicalize_remote_endpoint",
    "derive_readiness_seal",
    "fetch_remote_head",
    "inspect_committed_requirements",
    "resolve_source_candidate",
    "validate_record_git_bindings",
    "validate_remote_alias",
]
