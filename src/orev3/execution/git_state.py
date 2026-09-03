"""Fail-closed Git authority primitives for readiness-v1 Phase 2."""

from __future__ import annotations

import hashlib
import os
import re
import selectors
import signal
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

from orev3.execution.canonical import (
    CanonicalControlError,
    domain_identity,
    parse_canonical_bytes,
    parse_json,
    require_git_object,
    validate_json_schema_instance,
    validate_repository_path,
)
from orev3.execution.readiness_record import (
    PHASE2_SCHEMA_DOCUMENT_POLICY,
    PHASE2_SCHEMA_POLICY,
    READINESS_V1_1_SCHEMA_DOCUMENT_POLICY,
    READINESS_V1_1_SCHEMA_POLICY,
    READINESS_TEST_POLICY_PATH,
    REPOSITORY_AUTHORITY_PATH,
    ReadinessRecordV1,
    ReadinessRecordV2,
    RepositoryAuthorityV1,
    SourceScopeDeclarationV1,
    load_repository_authority_bytes,
    reconstruct_document_binding_identity,
    reconstruct_protocol_binding_identity,
    validate_implementation_binding,
    validate_readiness_record,
    validate_readiness_record_v2,
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
        result: dict[str, dict[str, Any]] = {}
        for kind, schema in self.schemas_by_object_kind.items():
            if (
                kind in READINESS_V1_1_SCHEMA_POLICY
                and schema.get("$id")
                == READINESS_V1_1_SCHEMA_DOCUMENT_POLICY[kind][0]
            ):
                path = READINESS_V1_1_SCHEMA_POLICY[kind][1]
            else:
                path = PHASE2_SCHEMA_POLICY[kind][1]
            result[path.rsplit("/", 1)[-1]] = schema
        return result


def _run_bounded_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: float,
    max_output_bytes: int,
    periodic_guard: Callable[[], None] | None = None,
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
            if periodic_guard is not None:
                periodic_guard()
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
    record: ReadinessRecordV1 | ReadinessRecordV2,
    record_blob_identity: str,
    validate_governed_source: bool = True,
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
    if validate_governed_source and changed_governed:
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


def validate_record_v2_git_bindings(
    repository: GitRepository,
    record: ReadinessRecordV2,
    *,
    prerequisites: Any | None = None,
    phase3b_evidence: Mapping[str, Any] | None = None,
) -> BoundSchemaRegistry:
    """Independently reconstruct prospective record authority at ``S``.

    ``prerequisites`` is the already-reconstructed Slice-2 bundle.  It is
    optional only to support schema/Git-only diagnostics; a complete
    readiness candidate requires it and detached Phase-3B evidence.
    """

    source = repository.resolve_commit(record.source_commit)
    if prerequisites is None or phase3b_evidence is None:
        raise GitAuthorityError(
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            "complete readiness-v2 validation requires reconstructed prerequisites and detached Phase-3B evidence",
        )
    adapter_schema_version = prerequisites.adapter.material["schema_version"]
    authenticated_configuration = (
        prerequisites.authenticated_experiment_configuration_resource
    )
    if adapter_schema_version == 3 and authenticated_configuration is not None:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "legacy adapter cannot carry authenticated configuration-resource authority",
        )
    if adapter_schema_version == 4 and authenticated_configuration is None:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "adapter-v4 requires authenticated configuration-resource authority",
        )
    if adapter_schema_version not in {3, 4}:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "readiness-v2 adapter schema generation is unsupported",
        )
    if adapter_schema_version == 4:
        from orev3.execution.readiness_record import (
            PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_DOCUMENT_POLICY,
            PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_POLICY,
        )

        selected_schema_policy = PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_POLICY
        selected_document_policy = (
            PROSPECTIVE_ADAPTER_V4_READINESS_SCHEMA_DOCUMENT_POLICY
        )
    else:
        selected_schema_policy = READINESS_V1_1_SCHEMA_POLICY
        selected_document_policy = READINESS_V1_1_SCHEMA_DOCUMENT_POLICY
    # Slice 4 and the final independent validator intentionally share the
    # same owner-level reconstruction primitives.  The legacy whole-record
    # checks below remain defense in depth, but do not define a parallel
    # first-failure algorithm.
    from orev3.execution.readiness_candidate import (
        PHASE3C_EVALUATION_ORDER,
        Phase3CEvaluationInput,
        validate_phase3c_invariant_bindings,
    )

    owner_material = dict(record.material)
    owner_material.pop("readiness_identity", None)
    owner_evaluation = Phase3CEvaluationInput(
        repository=repository,
        experiment_identifier=record.experiment_identifier,
        repository_authority_identifier=record.material["git_authority"][
            "repository_authority_identifier"
        ],
        approved_branch_ref=record.material["git_authority"][
            "approved_branch_ref"
        ],
        readiness_material=owner_material,
        prerequisites=prerequisites,
        phase3b_evidence=phase3b_evidence,
    )
    owner_failure: Exception | None = None
    try:
        for invariant_identifier in PHASE3C_EVALUATION_ORDER[:-1]:
            validate_phase3c_invariant_bindings(
                owner_evaluation, invariant_identifier
            )
    except Exception as exc:
        owner_failure = exc
    authority_entry = repository.tree_entry(source, REPOSITORY_AUTHORITY_PATH)
    _validate_safe_governed_entry(repository, source, authority_entry)
    try:
        committed_authority = load_repository_authority_bytes(
            repository.object_bytes(authority_entry.object_identity, max_bytes=1_048_576)
        )
    except CanonicalControlError as exc:
        raise GitAuthorityError(
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            "repository authority at S is malformed",
            repository_path=REPOSITORY_AUTHORITY_PATH,
        ) from exc
    git_authority = record.material["git_authority"]
    if (
        committed_authority.repository_authority_identifier
        != git_authority["repository_authority_identifier"]
        or committed_authority.approved_branch_ref
        != git_authority["approved_branch_ref"]
        or committed_authority.git_object_format != repository.object_format()
    ):
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "repository authority differs from readiness record",
            repository_path=REPOSITORY_AUTHORITY_PATH,
        )
    schemas: dict[str, dict[str, Any]] = {}
    schema_registry: dict[str, dict[str, Any]] = {}
    for declaration in record.material["schema"]["declarations"]:
        raw = _validate_blob_binding(repository, source, declaration, "prospective schema")
        schema = parse_json(raw, max_bytes=1_048_576)
        kind = declaration["object_kind"]
        expected_id, expected_digest = selected_document_policy[kind]
        _, expected_path = selected_schema_policy[kind]
        if (
            schema.get("$id") != expected_id
            or hashlib.sha256(raw).hexdigest() != expected_digest
            or declaration["path"] != expected_path
            or declaration["byte_count"] != len(raw)
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "prospective schema declaration does not reconstruct",
                repository_path=declaration["path"],
            )
        schemas[kind] = schema
        schema_registry[expected_path.rsplit("/", 1)[-1]] = schema
    try:
        validate_json_schema_instance(
            record.material,
            schemas["readiness-record"],
            schema_registry=schema_registry,
        )
        validate_readiness_record_v2(record.material)
    except CanonicalControlError as exc:
        raise GitAuthorityError(
            GitDiagnosticCode.CANONICAL_RECORD_INVALID,
            "prospective readiness record is invalid",
        ) from exc
    for section_name in ("readiness_specification", "protocol", "execution_specification"):
        _validate_blob_binding(repository, source, record.material[section_name], section_name)
    runtime = record.material["runtime"]
    runtime_raw: bytes | None = None
    for prefix in ("dependency_lock", "offline_artifact_manifest", "runtime_contract"):
        binding = {
            "path": runtime[f"{prefix}_path"],
            "sha256": runtime[f"{prefix}_sha256"],
            "git_blob_identity": runtime[f"{prefix}_git_blob_identity"],
        }
        if prefix == "runtime_contract":
            binding["byte_count"] = runtime["runtime_contract_byte_count"]
        else:
            entry = repository.tree_entry(source, binding["path"])
            binding["byte_count"] = len(repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024))
        raw = _validate_blob_binding(repository, source, binding, prefix)
        if prefix == "runtime_contract":
            runtime_raw = raw
    from orev3.execution.runtime import (
        PHASE3B_WORKER_EVIDENCE_DOMAIN,
        load_offline_artifact_manifest_bytes,
        load_runtime_contract_bytes,
        validate_dependency_lock,
    )

    assert runtime_raw is not None
    runtime_contract = load_runtime_contract_bytes(
        runtime_raw, schema=schemas["runtime-contract"]
    )
    lock_entry = repository.tree_entry(source, runtime_contract.dependency_lock_path)
    lock_raw = repository.object_bytes(lock_entry.object_identity, max_bytes=8 * 1024 * 1024)
    dependency_lock = validate_dependency_lock(
        lock_raw, expected_sha256=runtime_contract.dependency_lock_sha256
    )
    manifest_entry = repository.tree_entry(source, runtime_contract.artifact_manifest_path)
    manifest_raw = repository.object_bytes(
        manifest_entry.object_identity, max_bytes=8 * 1024 * 1024
    )
    manifest = load_offline_artifact_manifest_bytes(
        manifest_raw,
        schema=schemas["offline-artifact-manifest"],
        expected_sha256=runtime_contract.artifact_manifest_sha256,
        dependency_lock_sha256=runtime_contract.dependency_lock_sha256,
        dependency_lock=dependency_lock,
    )
    runtime_material = runtime_contract.material
    expected_runtime = {
        "dependency_environment_identity": runtime_material["dependency_lock"]["closed_environment_identity"],
        "dependency_lock_git_blob_identity": lock_entry.object_identity,
        "dependency_lock_identity": runtime_material["dependency_lock"]["lock_identity"],
        "dependency_lock_path": runtime_contract.dependency_lock_path,
        "dependency_lock_sha256": runtime_contract.dependency_lock_sha256,
        "host_system_identity": runtime_material["host_system"]["host_system_identity"],
        "offline_artifact_manifest_git_blob_identity": manifest_entry.object_identity,
        "offline_artifact_manifest_identity": manifest.manifest_identity,
        "offline_artifact_manifest_path": runtime_contract.artifact_manifest_path,
        "offline_artifact_manifest_sha256": runtime_contract.artifact_manifest_sha256,
        "python_implementation": runtime_material["python"]["implementation"],
        "python_version": runtime_material["python"]["version"],
        "runtime_bundle_identity": runtime_material["python"]["runtime_bundle_identity"],
        "runtime_contract_byte_count": len(runtime_raw),
        "runtime_contract_git_blob_identity": repository.tree_entry(
            source, runtime["runtime_contract_path"]
        ).object_identity,
        "runtime_contract_identity": runtime_contract.runtime_contract_identity,
        "runtime_contract_path": "config/research/readiness/runtime-contract-v1.json",
        "runtime_contract_sha256": hashlib.sha256(runtime_raw).hexdigest(),
    }
    if runtime != expected_runtime:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "runtime authority differs from the committed runtime contract",
        )
    for scope in record.material["source_scopes"]:
        entry = repository.tree_entry(source, scope["repository_path"])
        _validate_safe_governed_entry(repository, source, entry)
        if entry.object_identity != scope["git_object_identity"] or entry.mode != scope["git_mode"]:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "source scope differs from S",
                repository_path=scope["repository_path"],
            )
    for component in record.material["control_plane"]["components"]:
        entry = repository.tree_entry(source, component["path"])
        _validate_safe_governed_entry(repository, source, entry)
        raw = repository.object_bytes(entry.object_identity, max_bytes=8 * 1024 * 1024)
        if entry.object_type != "blob" or entry.mode != "100644" or entry.object_identity != component["git_object_identity"] or hashlib.sha256(raw).hexdigest() != component["sha256"]:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "control component differs from S",
                repository_path=component["path"],
            )
    attempt = record.material["attempt_policy"]
    _validate_blob_binding(repository, source, {
        "path": attempt["attempt_authority_contract_path"],
        "byte_count": attempt["attempt_authority_contract_byte_count"],
        "sha256": attempt["attempt_authority_contract_sha256"],
        "git_blob_identity": attempt["attempt_authority_contract_git_blob_identity"],
    }, "attempt authority contract")
    if prerequisites is not None:
        adapter = prerequisites.adapter.material
        authority = prerequisites.attempt_authority
        policy = prerequisites.readiness_test_policy.material
        implementation = record.material["implementation"]
        if (
            adapter["schema_version"] != adapter_schema_version
            or adapter["adapter_identity"] != implementation["adapter_identity"]
            or adapter["adapter_identifier"] != implementation["adapter_identifier"]
            or adapter["external_inputs"]["declarations"] != record.material["external_inputs"]["declarations"]
            or adapter["artifacts"]["declarations"] != record.material["artifacts"]["declarations"]
        ):
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "adapter authority differs from record")
        if adapter_schema_version == 4:
            authenticated = prerequisites.authenticated_experiment_configuration_resource
            resource = adapter["configuration"]["experiment_configuration_resource"]
            if (
                authenticated.approved_source_commit != source
                or authenticated.adapter_identifier != adapter["adapter_identifier"]
                or authenticated.adapter_identity != adapter["adapter_identity"]
                or authenticated.configuration_resource_identity
                != resource["configuration_resource_identity"]
                or authenticated.experiment_specific_configuration_identity
                != resource["experiment_specific_configuration_identity"]
                or authenticated.profiled_experiment_configuration_identity
                != resource["profiled_experiment_configuration_identity"]
            ):
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "authenticated configuration-resource authority differs from record",
                )
        authority_material = authority.material
        control_by_role = {
            item["role"]: item
            for item in record.material["control_plane"]["components"]
        }
        registry_component = control_by_role["adapter_registry"]
        if (
            registry_component["component_identifier"]
            != prerequisites.adapter_registry.material["registry_identifier"]
            or implementation["adapter_registry_identity"]
            != prerequisites.adapter_registry.material["adapter_registry_identity"]
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "adapter-registry authority differs from record control authority",
            )
        if (
            control_by_role["allocator_client"]["component_identifier"]
            != authority_material["allocator_client_identifier"]
            or control_by_role["allocator_client"]["component_identity"]
            != authority.allocator_client_component_identity
            or control_by_role["allocator_contract"]["component_identifier"]
            != authority_material["allocator_implementation_identifier"]
            or control_by_role["allocator_contract"]["component_identity"]
            != authority.allocator_contract_identity
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "allocator control authority differs from attempt contract",
            )
        expected_attempt = {
            "allocation_authority_identity": authority.allocation_authority_identity,
            "allocator_contract_identity": authority.allocator_contract_identity,
            "control_storage_component_identity": authority_material["control_storage_component"]["component_identity"],
            "control_storage_contract_identity": authority.control_storage_contract_identity,
            "output_namespace_identity_policy": authority_material["output_namespace_identity_policy"],
            "supported_attempt_kinds": authority_material["supported_attempt_kinds"],
            "attempt_authority_contract_git_blob_identity": authority.git_object_identity,
            "attempt_authority_contract_path": authority.repository_path,
            "attempt_authority_contract_sha256": authority.sha256,
        }
        if any(attempt[key] != expected for key, expected in expected_attempt.items()):
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "attempt authority differs from record")
        if attempt["attempt_output_declaration_identity"] != adapter["attempt_output_declaration_identity"] or attempt["output_policy_identity"] != adapter["attempt_output_declaration_identity_material"]["output_policy_identity"]:
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "attempt-output authority differs from record")
        validation = record.material["validation"]
        if validation["test_policy_identity"] != policy["policy_identity"] or validation["mandatory_test_selectors"] != policy["required_selectors"] or validation["launch_smoke_selectors"] != policy["launch_smoke_selectors"]:
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "readiness-test policy differs from record")
        expected_scopes = []
        for scope in prerequisites.source_scopes:
            scope_material = {
                "git_mode": scope.git_mode,
                "git_object_identity": scope.git_object_identity,
                "nesting": scope.nesting,
                "repository_path": scope.repository_path,
                "role": scope.role,
            }
            if scope.nesting == "nested":
                scope_material["parent_path"] = scope.parent_path
            expected_scopes.append(scope_material)
        expected_scopes.sort(
            key=lambda item: (item["repository_path"], item["role"])
        )
        if record.material["source_scopes"] != expected_scopes:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "record source scopes differ from reconstructed prerequisites",
            )
        scopes = record.material["source_scopes"]
        component_paths = [
            item["path"] for item in record.material["control_plane"]["components"]
        ]
        component_paths.append(authority_material["control_storage_component"]["path"])
        for path in component_paths:
            if not any(
                scope["role"] in {"control_plane", "implementation"}
                and (
                    scope["repository_path"] == path
                    or (
                        scope["git_mode"] == "040000"
                        and path.startswith(scope["repository_path"] + "/")
                    )
                )
                for scope in scopes
            ):
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "governed component is not covered by its source scope",
                    repository_path=path,
                )
        configuration = record.material["configuration"]
        if (
            configuration["experiment_configuration_identity"]
            != adapter["configuration"]["experiment_configuration_identity"]
            or configuration["decision_selection_identity"]
            != adapter["configuration"]["decision_selection_identity"]
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "adapter configuration authority differs from record",
            )
        if (
            record.material["protocol"]["path"] != adapter["protocol"]["path"]
            or record.material["protocol"]["revision"] != adapter["protocol"]["revision"]
            or record.material["protocol"]["sha256"] != adapter["protocol"]["sha256"]
            or record.material["execution_specification"]["path"]
            != adapter["execution_specification"]["path"]
            or record.material["execution_specification"]["revision"]
            != adapter["execution_specification"]["revision"]
            or record.material["execution_specification"]["sha256"]
            != adapter["execution_specification"]["sha256"]
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "adapter document authority differs from record",
            )
    if phase3b_evidence is not None:
        from orev3.execution.contract_validation import (
            ARTIFACT_EVIDENCE_DOMAIN,
            PROFILE_EVIDENCE_DOMAIN,
        )
        from orev3.execution.dataset_validation import (
            DATASET_EVIDENCE_DOMAIN,
            PROJECTION_EVIDENCE_DOMAIN,
            dataset_evidence,
        )
        from orev3.execution.evidence_preparation import (
            EVIDENCE_POLICY_PATH,
            EVIDENCE_PREPARATION_DOMAIN,
            load_evidence_policy,
        )
        from orev3.execution.external_inputs import INPUT_SNAPSHOT_DOMAIN
        from orev3.execution.replay_preparation import (
            POPULATION_EVIDENCE_DOMAIN,
            REPLAY_EVIDENCE_DOMAIN,
        )
        from orev3.execution.test_policy import READINESS_TEST_EVIDENCE_DOMAIN

        required_bundle = {
            "aggregate", "artifacts", "datasets", "population", "profile",
            "projections", "readiness_test", "replay", "snapshots", "workers",
        }
        if set(phase3b_evidence) != required_bundle:
            raise GitAuthorityError(
                GitDiagnosticCode.CANONICAL_RECORD_INVALID,
                "detached Phase-3B evidence bundle is incomplete or extended",
            )
        aggregate = phase3b_evidence["aggregate"]
        objects = {
            "readiness-test-evidence": (phase3b_evidence["readiness_test"], READINESS_TEST_EVIDENCE_DOMAIN, "readiness_test_evidence_identity"),
            "replay-evidence": (phase3b_evidence["replay"], REPLAY_EVIDENCE_DOMAIN, "replay_evidence_identity"),
            "population-accounting-evidence": (phase3b_evidence["population"], POPULATION_EVIDENCE_DOMAIN, "population_accounting_evidence_identity"),
            "profile-conformance-evidence": (phase3b_evidence["profile"], PROFILE_EVIDENCE_DOMAIN, "profile_conformance_evidence_identity"),
            "artifact-declaration-evidence": (phase3b_evidence["artifacts"], ARTIFACT_EVIDENCE_DOMAIN, "artifact_declaration_evidence_identity"),
            "evidence-preparation": (aggregate, EVIDENCE_PREPARATION_DOMAIN, "evidence_preparation_identity"),
        }
        for kind, (evidence_object, domain, identity_field) in objects.items():
            try:
                validate_json_schema_instance(
                    evidence_object, schemas[kind], schema_registry=schema_registry
                )
                identity_material = dict(evidence_object)
                claimed = identity_material.pop(identity_field)
                if domain_identity(domain, identity_material) != claimed:
                    raise CanonicalControlError("evidence identity mismatch")
            except (CanonicalControlError, KeyError, TypeError) as exc:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    f"detached {kind} does not reconstruct",
                ) from exc
        for collection_name, kind, domain, identity_field in (
            ("snapshots", "immutable-input-snapshot", INPUT_SNAPSHOT_DOMAIN, "input_snapshot_identity"),
            ("datasets", "dataset-validation-evidence", DATASET_EVIDENCE_DOMAIN, "dataset_validation_evidence_identity"),
            ("projections", "outcome-blind-projection-evidence", PROJECTION_EVIDENCE_DOMAIN, "projection_evidence_identity"),
        ):
            for evidence_object in phase3b_evidence[collection_name]:
                try:
                    validate_json_schema_instance(evidence_object, schemas[kind], schema_registry=schema_registry)
                    identity_material = dict(evidence_object); claimed = identity_material.pop(identity_field)
                    if domain_identity(domain, identity_material) != claimed:
                        raise CanonicalControlError("evidence identity mismatch")
                except (CanonicalControlError, KeyError, TypeError) as exc:
                    raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, f"detached {kind} does not reconstruct") from exc
        worker_ids: list[str] = []
        worker_materials: list[Mapping[str, Any]] = []
        worker_results: dict[str, list[Mapping[str, Any]]] = {}
        for worker_bundle in phase3b_evidence["workers"]:
            try:
                if set(worker_bundle) != {"material", "result"}:
                    raise CanonicalControlError("worker evidence bundle is open")
                worker = worker_bundle["material"]
                result = worker_bundle["result"]
                if not isinstance(worker, Mapping) or not isinstance(result, Mapping):
                    raise CanonicalControlError("worker evidence bundle is malformed")
                worker_material = dict(worker)
                worker_identity = worker_material.pop("worker_evidence_identity")
                if (
                    domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, worker_material)
                    != worker_identity
                    or domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, result)
                    != worker_material["output_identity"]
                ):
                    raise CanonicalControlError("worker evidence identity mismatch")
                worker_ids.append(worker_identity)
                worker_materials.append(worker)
                worker_results.setdefault(worker["worker_kind"], []).append(result)
            except (CanonicalControlError, KeyError, TypeError) as exc:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "detached worker evidence does not reconstruct",
                ) from exc
        if worker_ids != sorted(worker_ids) or len(worker_ids) != len(set(worker_ids)):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "worker evidence collection is not canonical",
            )
        validation = record.material["validation"]
        readiness_test = phase3b_evidence["readiness_test"]
        direct_validation = {
            "additional_test_selectors": readiness_test["additional_selectors"],
            "collected_node_ids": readiness_test["collected_node_ids"],
            "mandatory_test_selectors": readiness_test["mandatory_selectors"],
            "readiness_test_evidence_identity": readiness_test["readiness_test_evidence_identity"],
            "test_policy_identity": readiness_test["policy_identity"],
            "test_results": readiness_test["results"],
        }
        if any(validation[key] != expected for key, expected in direct_validation.items()):
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "readiness-test evidence differs from direct record fields")
        replay_evidence = phase3b_evidence["replay"]
        direct_replay = {key: replay_evidence[key] for key in (
            "candidate_order", "decision_selection_identity", "ordered_decision_identities",
            "ordered_replay_unit_identities", "ordered_source_unit_identities",
            "projection_identity", "replay_evidence_identity", "replay_identity",
            "replay_preparer_component_identity", "selector_component_identity",
        )}
        if any(record.material["replay"][key] != expected for key, expected in direct_replay.items()) or record.material["replay"]["population_accounting"] != {key: value for key, value in phase3b_evidence["population"].items() if key != "schema_version"}:
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "Replay/population evidence differs from direct record fields")
        artifact_evidence = phase3b_evidence["artifacts"]
        if (
            record.material["artifacts"]["artifact_declaration_evidence_identity"] != artifact_evidence["artifact_declaration_evidence_identity"]
            or record.material["artifacts"]["dependency_order"] != artifact_evidence["dependency_order"]
            or record.material["artifacts"]["output_policy_identity"] != artifact_evidence["output_policy_identity"]
            or [item["declaration_identity"] for item in record.material["artifacts"]["declarations"]] != artifact_evidence["declaration_identities"]
        ):
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "artifact evidence differs from direct record fields")
        profile_evidence = phase3b_evidence["profile"]
        if (
            profile_evidence != prerequisites.profile_contracts.profile_evidence
            or record.material["outcome_policy"][
                "profile_conformance_evidence_identity"
            ]
            != profile_evidence["profile_conformance_evidence_identity"]
        ):
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "profile evidence differs from direct record fields")
        direct_profile = record.material["outcome_policy"]
        for key in (
            "outcome_capability",
            "profile_contract_identities",
            "profile_identity",
            "profile_name",
        ):
            if direct_profile[key] != profile_evidence[key]:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "profile evidence content differs from direct outcome policy",
                )
        if direct_profile["profile_name"] == "outcome_aware_v1" and (
            direct_profile["authorization_contract_identity"]
            != profile_evidence["authorization_contract_identity"]
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "profile authorization evidence differs from direct outcome policy",
            )
        snapshot_ids = [item["input_snapshot_identity"] for item in phase3b_evidence["snapshots"]]
        dataset_ids = sorted(item["dataset_validation_evidence_identity"] for item in phase3b_evidence["datasets"])
        projection_ids = sorted(item["projection_evidence_identity"] for item in phase3b_evidence["projections"])
        direct_inputs = record.material["external_inputs"]
        if direct_inputs["input_snapshot_identities"] != snapshot_ids or direct_inputs["dataset_validation_evidence_identities"] != dataset_ids or direct_inputs["projection_evidence_identities"] != projection_ids:
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "input evidence differs from direct record fields")
        declarations = prerequisites.adapter.material["external_inputs"]["declarations"]
        zero_input = declarations == []
        if len(phase3b_evidence["snapshots"]) != len(declarations):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "snapshot/declaration cardinality differs",
            )
        contracts = {
            item["external_input_identifier"]: item
            for item in prerequisites.adapter.material["evidence_preparation"][
                "dataset_contracts"
            ]
        }
        datasets_by_snapshot = {
            item["input_snapshot_identity"]: item
            for item in phase3b_evidence["datasets"]
        }
        if len(datasets_by_snapshot) != len(phase3b_evidence["datasets"]):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "dataset evidence snapshot binding is duplicated",
            )
        projections_by_dataset = {
            item["dataset_identity"]: item
            for item in phase3b_evidence["projections"]
        }
        if len(projections_by_dataset) != len(phase3b_evidence["projections"]):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "projection evidence dataset binding is duplicated",
            )
        from orev3.execution.phase3b_components import resolve_component

        semantic_component_ids: set[str] = set()
        for declaration, snapshot in zip(
            declarations, phase3b_evidence["snapshots"], strict=True
        ):
            expected_snapshot_members = [
                {
                    "byte_count": member["byte_count"],
                    "logical_member_identifier": member["logical_identifier"],
                    "member_order": index,
                    "sha256": member["sha256"],
                }
                for index, member in enumerate(declaration["members"])
            ]
            if (
                snapshot["external_input_identifier"]
                != declaration["external_input_identifier"]
                or snapshot["input_kind"] != declaration["input_kind"]
                or snapshot["members"] != expected_snapshot_members
            ):
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "immutable snapshot differs from adapter-v3 declaration",
                )
            try:
                dataset = datasets_by_snapshot[snapshot["input_snapshot_identity"]]
            except KeyError as exc:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "dataset evidence is absent for governed snapshot",
                ) from exc
            contract = contracts[declaration["external_input_identifier"]]
            parser = resolve_component(
                repository,
                source,
                declaration["parser_configuration"]["parser_identifier"],
            )
            validator = resolve_component(
                repository, source, contract["dataset_validator_identifier"]
            )
            semantic_component_ids.update(
                {parser.component_identity, validator.component_identity}
            )
            expected_dataset = dataset_evidence(
                external_input_identity=declaration["external_input_identity"],
                snapshot_identity=snapshot["input_snapshot_identity"],
                source_class=contract["source_class"],
                dataset_version=contract["dataset_version"],
                container=contract["container"],
                parser_component_identity=parser.component_identity,
                validator_component_identity=validator.component_identity,
                schema_identity=declaration["schema_identity"],
                protocol_revision=contract["protocol_revision"],
                record_count=dataset["ordered_record_count"],
                record_ordering=contract["record_ordering"],
                candidate_order=contract["candidate_order"],
                projection_required=contract["projection_required"],
                dataset_content_identity=dataset["dataset_content_identity"],
            )
            if dataset != expected_dataset:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "dataset evidence first-order authority does not reconstruct",
                )
            projection = projections_by_dataset.get(dataset["dataset_identity"])
            if contract["projection_required"] and projection is None:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "required projection evidence is absent",
                )
            if projection is not None:
                projector = resolve_component(
                    repository, source, contract["projector_identifier"]
                )
                semantic_component_ids.add(projector.component_identity)
                projection_schema_raw = repository.object_bytes(
                    repository.tree_entry(
                        source, contract["projection_schema_path"]
                    ).object_identity,
                    max_bytes=1_048_576,
                )
                projection_schema = parse_canonical_bytes(projection_schema_raw)
                projection_identity = domain_identity(
                    PROJECTION_EVIDENCE_DOMAIN,
                    {
                        "byte_count": projection["byte_count"],
                        "ordered_record_count": projection["ordered_record_count"],
                        "parser_component_identity": parser.component_identity,
                        "projection_schema_identity": contract[
                            "projection_schema_identity"
                        ],
                        "projector_component_identity": projector.component_identity,
                        "sha256": projection["sha256"],
                    },
                )
                if (
                    projection["projection_identity"] != projection_identity
                    or projection["raw_input_snapshot_identity"]
                    != snapshot["input_snapshot_identity"]
                    or projection["parser_component_identity"]
                    != parser.component_identity
                    or projection["projector_component_identity"]
                    != projector.component_identity
                    or projection["projection_schema_identity"]
                    != contract["projection_schema_identity"]
                    or projection["allowed_fields"]
                    != sorted(projection_schema["properties"])
                ):
                    raise GitAuthorityError(
                        GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                        "projection evidence first-order authority does not reconstruct",
                    )
        if set(datasets_by_snapshot) != set(snapshot_ids):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "dataset evidence contains an ungoverned snapshot binding",
            )
        if set(projections_by_dataset) != {
            item["dataset_identity"]
            for item in phase3b_evidence["datasets"]
            if contracts[
                next(
                    declaration["external_input_identifier"]
                    for declaration, snapshot in zip(
                        declarations, phase3b_evidence["snapshots"], strict=True
                    )
                    if snapshot["input_snapshot_identity"]
                    == item["input_snapshot_identity"]
                )
            ]["projection_required"]
        }:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "projection evidence membership differs from governed contracts",
            )
        decision = prerequisites.adapter.material["evidence_preparation"][
            "decision_selection"
        ]
        if (
            phase3b_evidence["population"]["permitted_exclusion_reasons"]
            != decision["permitted_exclusion_reasons"]
            or replay_evidence["decision_selection_identity"]
            != decision["configuration_identity"]
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "population/decision-selection authority differs from adapter-v3",
            )
        input_results = worker_results.get("INPUT_PROJECTOR", [])
        for dataset in phase3b_evidence["datasets"]:
            projection = projections_by_dataset.get(dataset["dataset_identity"])
            matching_results = [
                result
                for result in input_results
                if result.get("status") == "evidence_passed"
                and result.get("dataset_content_identity")
                == dataset["dataset_content_identity"]
                and result.get("record_count") == dataset["ordered_record_count"]
                and projection is not None
                and result.get("byte_count") == projection["byte_count"]
                and result.get("sha256") == projection["sha256"]
            ]
            if len(matching_results) < 2:
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "dataset/projection authority lacks two detached worker reconstructions",
                )
        replay_results = worker_results.get("REPLAY_PREPARATION", [])
        if zero_input and replay_results:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "zero-input authority cannot contain Replay workers",
            )
        if not zero_input and sum(
            result.get("status") == "evidence_passed"
            and result.get("replay_identity")
            == replay_evidence["replay_evidence_identity"]
            and result.get("population_identity")
            == phase3b_evidence["population"][
                "population_accounting_evidence_identity"
            ]
            for result in replay_results
        ) < 2:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "Replay/population authority lacks two detached worker reconstructions",
            )
        if not any(
            result.get("status") == "evidence_passed"
            and result.get("exit_code") == 0
            and result.get("warning_count") == 0
            and result.get("collected_node_ids")
            == readiness_test["collected_node_ids"]
            and result.get("results") == readiness_test["results"]
            for result in worker_results.get("READINESS_TEST", [])
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "readiness-test evidence lacks detached execution authority",
            )
        for identifier in (
            decision["selector_identifier"],
            decision["replay_preparer_identifier"],
            "static-profile-validator-v1",
            "static-artifact-validator-v1",
        ):
            semantic_component_ids.add(
                resolve_component(repository, source, identifier).component_identity
            )
        evidence_policy_entry = repository.tree_entry(source, EVIDENCE_POLICY_PATH)
        evidence_policy_raw = repository.object_bytes(
            evidence_policy_entry.object_identity, max_bytes=1_048_576
        )
        evidence_policy = load_evidence_policy(
            evidence_policy_raw, schema=schemas["evidence-preparation-policy"]
        )
        if (
            record.material["configuration"][
                "evidence_preparation_policy_identity"
            ]
            != evidence_policy["policy_identity"]
            or prerequisites.adapter.material["evidence_preparation"][
                "resource_policy_identity"
            ]
            != evidence_policy["policy_identity"]
        ):
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "evidence-preparation policy authority differs from record",
            )
        worker_profiles = {
            item["worker_kind"]: item
            for item in evidence_policy["worker_profiles"]
        }
        worker_modules = {
            "INPUT_PROJECTOR": "src/orev3/execution/input_projection_worker.py",
            "READINESS_TEST": "src/orev3/execution/readiness_test_worker.py",
            "REPLAY_PREPARATION": "src/orev3/execution/replay_preparation_worker.py",
        }
        from orev3.execution.phase3b_components import WORKER_CODE_CLOSURES

        expected_worker_authorities: Counter[tuple[str, str, tuple[str, ...]]] = Counter()

        def require_worker_authority(
            worker_kind: str,
            command: str,
            invocation_identifier: str,
            input_capability_identities: tuple[str, ...] = (),
        ) -> None:
            command_identity = domain_identity(
                PHASE3B_WORKER_EVIDENCE_DOMAIN,
                {
                    "command": command,
                    "invocation_identifier": invocation_identifier,
                    "worker_kind": worker_kind,
                },
            )
            capabilities = tuple(sorted(input_capability_identities))
            expected_worker_authorities[
                (worker_kind, command_identity, capabilities)
            ] += 1

        for snapshot_identity in snapshot_ids:
            for invocation_identifier in ("projection-1", "projection-2"):
                require_worker_authority(
                    "INPUT_PROJECTOR",
                    "project_canonical_jsonl",
                    invocation_identifier,
                    (snapshot_identity,),
                )
        for invocation_identifier in ("collection-a", "collection-b"):
            require_worker_authority(
                "READINESS_TEST", "collect", invocation_identifier
            )
        require_worker_authority("READINESS_TEST", "run_exact", "execution")
        if not zero_input:
            for invocation_identifier in ("replay-1", "replay-2"):
                require_worker_authority(
                    "REPLAY_PREPARATION",
                    "reconstruct_replay",
                    invocation_identifier,
                    (replay_evidence["projection_identity"],),
                )

        actual_worker_authorities: Counter[
            tuple[str, str, tuple[str, ...]]
        ] = Counter()

        for worker in worker_materials:
            if worker.get("worker_kind") == "PHASE3A_VALIDATOR":
                # The shared owner-level validator above reconstructs the
                # prospective normalized Phase-3A output and worker.  It is
                # intentionally disjoint from the historical generic shape.
                continue
            expected_fields = {
                "capability_policy_identity",
                "closed_dependency_identity",
                "code_capability_git_identities",
                "command_identity",
                "input_capability_identities",
                "output_identity",
                "runtime_contract_identity",
                "sandbox_template_identity",
                "source_commit",
                "successful_worker_disposition",
                "worker_evidence_identity",
                "worker_kind",
                "worker_module_git_identity",
            }
            kind = worker.get("worker_kind")
            profile = worker_profiles.get(kind)
            module_path = worker_modules.get(kind)
            if (
                set(worker) != expected_fields
                or profile is None
                or module_path is None
                or profile["module"] != module_path
                or worker["capability_policy_identity"]
                != evidence_policy["policy_identity"]
                or worker["closed_dependency_identity"]
                != runtime["dependency_environment_identity"]
                or worker["runtime_contract_identity"]
                != runtime_contract.runtime_contract_identity
                or worker["sandbox_template_identity"]
                != profile["sandbox_template_identity"]
                or worker["source_commit"] != source
                or worker["successful_worker_disposition"] != "evidence_passed"
                or worker["worker_module_git_identity"]
                != repository.tree_entry(source, module_path).object_identity
            ):
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "Phase-3B worker authority differs from committed policy",
                )
            expected_code_ids = {
                repository.tree_entry(source, path).object_identity
                for path in WORKER_CODE_CLOSURES[kind]
            }
            supplied_code_ids = worker["code_capability_git_identities"]
            if (
                supplied_code_ids != sorted(set(supplied_code_ids))
                or not expected_code_ids.issubset(set(supplied_code_ids))
            ):
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "Phase-3B worker code authority differs from S",
                )
            supplied_capabilities = worker["input_capability_identities"]
            if supplied_capabilities != sorted(set(supplied_capabilities)):
                raise GitAuthorityError(
                    GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                    "Phase-3B worker input capabilities are not canonical",
                )
            actual_worker_authorities[
                (
                    kind,
                    worker["command_identity"],
                    tuple(supplied_capabilities),
                )
            ] += 1
        if actual_worker_authorities != expected_worker_authorities:
            raise GitAuthorityError(
                GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
                "Phase-3B worker command/input authority differs from governed invocation",
            )
        aggregate_expected = {
            "adapter_identity": record.material["implementation"]["adapter_identity"],
            "artifact_evidence_identity": artifact_evidence["artifact_declaration_evidence_identity"],
            "dataset_evidence_identities": dataset_ids,
            "evidence_preparation_identity": validation["evidence_preparation_identity"],
            "input_snapshot_identities": sorted(snapshot_ids),
            "population_evidence_identity": phase3b_evidence["population"]["population_accounting_evidence_identity"],
            "profile_evidence_identity": profile_evidence["profile_conformance_evidence_identity"],
            "projection_evidence_identities": projection_ids,
            "readiness_test_evidence_identity": readiness_test["readiness_test_evidence_identity"],
            "replay_evidence_identity": replay_evidence["replay_evidence_identity"],
            "source_commit": source,
            "runtime_contract_identity": runtime_contract.runtime_contract_identity,
            "dependency_environment_identity": runtime[
                "dependency_environment_identity"
            ],
            "capability_policy_identity": evidence_policy["policy_identity"],
            "semantic_component_identities": sorted(semantic_component_ids),
            "worker_evidence_identities": worker_ids,
        }
        if any(aggregate[key] != expected for key, expected in aggregate_expected.items()):
            raise GitAuthorityError(GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH, "Phase-3B aggregate cross-binding differs from record")
    if owner_failure is not None:
        raise GitAuthorityError(
            GitDiagnosticCode.GOVERNED_OBJECT_MISMATCH,
            "owner-level readiness authority does not reconstruct",
        ) from owner_failure
    return BoundSchemaRegistry(schemas)


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
    "validate_record_v2_git_bindings",
    "validate_remote_alias",
]
