"""Descriptor-pinned filesystem capabilities for readiness preparation.

Phase-3B accepts absolute, lexically normalized POSIX paths only.  Relative
paths, ``.``/``..`` components, repeated separators, trailing separators, and
NUL are rejected.  Unicode component names are permitted and are passed to
the operating system without normalization.  Operational paths never enter
scientific identity material.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import stat
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from orev3.execution.canonical import CanonicalControlError


@dataclass(frozen=True, slots=True)
class PinnedDirectory:
    descriptor: int
    path: Path

    def close(self) -> None:
        os.close(self.descriptor)


PathArgument = str | PathLike[str]


def _absolute_components(path: PathArgument, *, error_code: str, allow_root: bool) -> tuple[str, ...]:
    raw = os.fspath(path)
    if not isinstance(raw, str) or not raw or "\x00" in raw or not raw.startswith("/"):
        raise CanonicalControlError(error_code)
    if raw != "/" and (raw.endswith("/") or "//" in raw):
        raise CanonicalControlError(error_code)
    components = tuple(raw.split("/")[1:])
    if any(component in {"", ".", ".."} for component in components):
        raise CanonicalControlError(error_code)
    if not allow_root and not components:
        raise CanonicalControlError(error_code)
    return components


def open_pinned_directory(
    path: PathArgument, *, create: bool = False, mode: int = 0o700, error_code: str,
    missing_error_code: str | None = None,
) -> PinnedDirectory:
    """Open every directory component relative to its pinned parent."""

    components = _absolute_components(path, error_code=error_code, allow_root=True)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current = os.open("/", flags)
    try:
        for component in components:
            try:
                child = os.open(component, flags, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise CanonicalControlError(missing_error_code or error_code) from None
                try:
                    os.mkdir(component, mode=mode, dir_fd=current)
                except FileExistsError:
                    pass
                child = os.open(component, flags, dir_fd=current)
            except OSError as exc:
                raise CanonicalControlError(error_code) from exc
            opened = os.fstat(child)
            if not stat.S_ISDIR(opened.st_mode):
                os.close(child)
                raise CanonicalControlError(error_code)
            os.close(current)
            current = child
        return PinnedDirectory(current, Path(os.fspath(path)))
    except BaseException:
        os.close(current)
        raise


def open_pinned_regular(
    path: PathArgument, *, error_code: str, missing_error_code: str | None = None,
    nonblocking: bool = False,
) -> tuple[int, os.stat_result]:
    """Open a regular leaf relative to a descriptor-pinned parent chain."""

    components = _absolute_components(path, error_code=error_code, allow_root=False)
    parent_path = Path("/", *components[:-1])
    parent = open_pinned_directory(
        parent_path, error_code=error_code, missing_error_code=missing_error_code
    )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    if nonblocking:
        flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        try:
            descriptor = os.open(components[-1], flags, dir_fd=parent.descriptor)
        except FileNotFoundError as exc:
            raise CanonicalControlError(missing_error_code or error_code) from exc
        except OSError as exc:
            raise CanonicalControlError(error_code) from exc
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            os.close(descriptor)
            raise CanonicalControlError(error_code)
        return descriptor, opened
    finally:
        parent.close()


def verify_opened_regular(
    descriptor: int,
    *,
    expected_size: int,
    expected_sha256: str,
    limit: int,
    error_code: str,
    mutation_error_code: str | None = None,
) -> bytes:
    """Read, bound, and verify the exact already-open regular object."""

    digest = hashlib.sha256()
    payload = bytearray()
    opened = os.fstat(descriptor)
    if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != expected_size:
        raise CanonicalControlError(error_code)
    while True:
        chunk = os.read(descriptor, min(1024 * 1024, limit + 1 - len(payload)))
        if not chunk:
            break
        payload.extend(chunk)
        digest.update(chunk)
        if len(payload) > limit:
            raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    closed = os.fstat(descriptor)
    stable = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) == (
        closed.st_dev, closed.st_ino, closed.st_size, closed.st_mtime_ns, closed.st_ctime_ns
    )
    if not stable:
        raise CanonicalControlError(mutation_error_code or error_code)
    if len(payload) != expected_size or digest.hexdigest() != expected_sha256:
        raise CanonicalControlError(error_code)
    return bytes(payload)


def _open_unique_temporary(directory_fd: int, *, prefix: str) -> tuple[str, int]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    for _ in range(128):
        name = f".{prefix}.{secrets.token_hex(16)}.tmp"
        try:
            return name, os.open(name, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            continue
    raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")


def publish_content_addressed_bytes(
    payload: bytes,
    *,
    store: Path,
    expected_sha256: str,
    limit: int,
    error_code: str,
) -> Path:
    """Publish bytes atomically inside one descriptor-pinned store."""

    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_sha256 or len(payload) > limit:
        raise CanonicalControlError(error_code)
    directory = open_pinned_directory(store, create=True, error_code=error_code)
    temporary_name = ""
    try:
        temporary_name, temporary_fd = _open_unique_temporary(directory.descriptor, prefix=actual)
        try:
            with os.fdopen(temporary_fd, "wb", buffering=0, closefd=False) as stream:
                stream.write(payload)
                os.fsync(stream.fileno())
        finally:
            os.close(temporary_fd)
        try:
            os.link(
                temporary_name,
                actual,
                src_dir_fd=directory.descriptor,
                dst_dir_fd=directory.descriptor,
                follow_symlinks=False,
            )
        except FileExistsError:
            pass
        finally:
            try:
                os.unlink(temporary_name, dir_fd=directory.descriptor)
            except FileNotFoundError:
                pass
            temporary_name = ""
        target_fd = os.open(
            actual,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory.descriptor,
        )
        try:
            verified = verify_opened_regular(
                target_fd,
                expected_size=len(payload),
                expected_sha256=actual,
                limit=limit,
                error_code=error_code,
            )
            if verified != payload:
                raise CanonicalControlError(error_code)
            os.fchmod(target_fd, 0o444)
        finally:
            os.close(target_fd)
        os.fsync(directory.descriptor)
        return store / actual
    except OSError as exc:
        raise CanonicalControlError(error_code) from exc
    finally:
        if temporary_name:
            try:
                os.unlink(temporary_name, dir_fd=directory.descriptor)
            except FileNotFoundError:
                pass
        directory.close()


__all__ = [
    "PinnedDirectory",
    "open_pinned_directory",
    "open_pinned_regular",
    "publish_content_addressed_bytes",
    "verify_opened_regular",
]
