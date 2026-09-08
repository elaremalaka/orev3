"""Descriptor-pinned filesystem capabilities for readiness preparation.

Phase-3B accepts absolute, lexically normalized POSIX paths only.  Relative
paths, ``.``/``..`` components, repeated separators, trailing separators, and
NUL are rejected.  Unicode component names are permitted and are passed to
the operating system without normalization.  Operational paths never enter
scientific identity material.
"""

from __future__ import annotations

import hashlib
import fcntl
import os
import secrets
import stat
import sys
from dataclasses import dataclass
from contextlib import contextmanager
from contextvars import ContextVar
from os import PathLike
from pathlib import Path

from orev3.execution.canonical import CanonicalControlError


@dataclass(frozen=True, slots=True)
class PinnedDirectory:
    acquisition: DescriptorAcquisition
    path: Path
    owner: DescriptorOwner

    @property
    def descriptor(self):
        if self.acquisition.disposed:
            raise CanonicalControlError(self.owner.error_code)
        return self.acquisition.descriptor

    def close(self) -> None:
        self.owner.close_acquisition(self.acquisition)
        self.owner.check()


PathArgument = str | PathLike[str]


@dataclass(frozen=True)
class _OpeningCloseUncertainty:
    """Historical FD identity, never a safely retryable descriptor."""
    _identity: int | DescriptorAcquisition
    error_type: str
    error_number: int | None

    @property
    def descriptor(self):
        return self._identity if type(self._identity) is int else self._identity.descriptor


class DescriptorCloseError(CanonicalControlError):
    """Opening failed; kernel ownership of these single-attempt closes is unknown.

    The caller must retain this disposition rather than infer successful release
    or retry the recorded integers, which may already identify unrelated FDs.
    """
    def __init__(self, error_code: str, unresolved_closes: tuple[_OpeningCloseUncertainty, ...]):
        super().__init__(error_code)
        self.unresolved_closes = unresolved_closes


_ACQUISITION_POLICY = ContextVar("pinned_acquisition_policy", default=None)


@contextmanager
def pinned_acquisition_policy(policy):
    """Supply policy explicitly; this scope does not defer cancellation.

    Only the actor's per-acquisition callable establishes protection. Keeping
    this routing context through an iterator therefore protects no unrelated work.
    """
    previous = _ACQUISITION_POLICY.get()
    try:
        _ACQUISITION_POLICY.set(policy)
        yield
    finally:
        _ACQUISITION_POLICY.set(previous)


class DescriptorAcquisition:
    """Pre-registered result cell, owned before a syscall can create an FD."""
    def __init__(self, path, flags, mode, dir_fd, *, operation="open"):
        self.operation = operation
        self.arguments = (path, flags, mode)
        self.dir_fd = dir_fd
        self.descriptor = None
        self.attempted = False
        self.definitive_failure = False
        self.close_outcome = None
        self.close_order = None
        # Construct before any resource exists. It remains usable if later
        # close bookkeeping itself is interrupted or cannot allocate a record.
        self.close_fallback = _OpeningCloseUncertainty(self, "CloseOutcomeUnproven", None)

    @property
    def disposed(self):
        # Both terminal outcomes forbid another close of this integer.
        return self.close_outcome is not None

    @property
    def unprovable(self):
        return self.attempted and self.descriptor is None and not self.definitive_failure

    def acquire(self):
        operation = os.dup if self.operation == "dup" else os.open
        previous = sys.getprofile()
        acquisition_frame = sys._getframe()
        failed_call = False

        def classify(frame, event, function):
            nonlocal failed_call
            # Record this exact C call's exceptional return. A c_return
            # observer exception is NOT that evidence. See classification below.
            if frame is acquisition_frame and function is operation and event == "c_exception":
                failed_call = True
            if previous is not None:
                previous(frame, event, function)

        try:
            sys.setprofile(classify)
            self.attempted = True
            if self.operation == "dup":
                self.descriptor = operation(self.arguments[0])
            else:
                self.descriptor = operation(*self.arguments, dir_fd=self.dir_fd)
        except OSError as error:
            # Supported CPython/POSIX: open's syscall-error branch supplies a
            # filename; post-open inheritable-flag failures do not. dup uses one
            # atomic fcntl when F_DUPFD_CLOEXEC is available. Do not treat its
            # fallback's possible post-dup cleanup failure as no acquisition.
            no_result = (hasattr(fcntl, "F_DUPFD_CLOEXEC") if self.operation == "dup"
                         else error.filename is not None)
            # A Python observer/argument hook may replace an exception and its
            # metadata. Its traceback is not the native syscall-error result.
            native_error = error.__traceback__.tb_next is None
            self.definitive_failure = failed_call and no_result and native_error
            raise
        finally:
            try:
                sys.setprofile(previous)
            finally:
                # A one-shot interruption before restoration must not leave
                # this acquisition's observer installed on unrelated work.
                if sys.getprofile() is classify:
                    sys.setprofile(previous)


class DescriptorOwner:
    """One explicit enclosing disposal authority; returned FDs are borrowed.

    The cell is reachable here before acquisition begins. Neither helper return
    nor caller assignment transfers disposal authority. No finalizer is used.
    """
    def __init__(self, error_code: str):
        self.error_code = error_code
        self.cells: list[DescriptorAcquisition] = []
        self._close_sequence = 0

    @property
    def unresolved(self):
        return [cell.close_outcome for cell in sorted(
            (cell for cell in self.cells if isinstance(cell.close_outcome, _OpeningCloseUncertainty)),
            key=lambda cell: -1 if cell.close_order is None else cell.close_order)]

    @property
    def pending(self):
        return [cell.descriptor for cell in self.cells
                if cell.descriptor is not None and not cell.disposed]

    def open(self, path, flags, mode=0o777, *, dir_fd=None):
        return self._receive(DescriptorAcquisition(path, flags, mode, dir_fd))

    def duplicate(self, descriptor):
        return self._receive(DescriptorAcquisition(descriptor, 0, 0, None, operation="dup"))

    def _receive(self, cell):
        policy = _ACQUISITION_POLICY.get()
        if policy is None:
            raise CanonicalControlError(self.error_code)
        self.cells.append(cell)
        policy(cell)
        if type(cell.descriptor) is not int:
            raise CanonicalControlError(self.error_code)
        return cell.descriptor

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        try:
            self.close()
        except DescriptorCloseError as closing:
            # Preserve an already-reported disposition (including an existing
            # caller error mapping) only if teardown discovered no new outcome.
            reported = error if isinstance(error, DescriptorCloseError) else getattr(error, "__cause__", None)
            if (isinstance(reported, DescriptorCloseError)
                    and reported.unresolved_closes == closing.unresolved_closes):
                return None
            raise

    def close_one(self, descriptor: int) -> None:
        cell = next((item for item in self.cells
                     if item.descriptor == descriptor and not item.disposed), None)
        if cell is None:
            return
        self.close_acquisition(cell)

    def close_acquisition(self, cell) -> None:
        if cell.disposed:
            return
        if cell not in self.cells or cell.descriptor is None:
            raise CanonicalControlError(self.error_code)
        descriptor = cell.descriptor
        # Reachable uncertainty is authoritative BEFORE attempting close.
        # A later interruption may leave conservative uncertainty, never CLEAN.
        self._close_sequence += 1
        cell.close_order = self._close_sequence
        cell.close_outcome = cell.close_fallback
        try:
            os.close(descriptor)
        except BaseException as error:
            cell.close_outcome = _OpeningCloseUncertainty(
                descriptor, type(error).__name__, getattr(error, "errno", None))
        else:
            cell.close_outcome = "closed"

    def check(self) -> None:
        if self.unresolved:
            raise DescriptorCloseError(self.error_code, tuple(self.unresolved))

    def close(self) -> None:
        first_error = None
        for cell in tuple(reversed(self.cells)):
            if cell.descriptor is None or cell.disposed:
                continue
            try:
                self.close_acquisition(cell)
            except BaseException as error:
                if not cell.disposed:
                    cell.close_outcome = cell.close_fallback
                if first_error is None:
                    first_error = error
        self.cells[:] = [cell for cell in self.cells if cell.close_outcome != "closed"]
        self.check()
        if first_error is not None:
            raise first_error


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
    path: PathArgument, *, owner: DescriptorOwner, create: bool = False, mode: int = 0o700, error_code: str,
    missing_error_code: str | None = None,
) -> PinnedDirectory:
    """Borrow a directory from the enclosing owner, traversing pinned parents."""

    components = _absolute_components(path, error_code=error_code, allow_root=True)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    owned = owner
    try:
        current = owned.open("/", flags)
        for component in components:
            try:
                child = owned.open(component, flags, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise CanonicalControlError(missing_error_code or error_code) from None
                try:
                    os.mkdir(component, mode=mode, dir_fd=current)
                except FileExistsError:
                    pass
                child = owned.open(component, flags, dir_fd=current)
            except OSError as exc:
                raise CanonicalControlError(error_code) from exc
            opened = os.fstat(child)
            if not stat.S_ISDIR(opened.st_mode):
                raise CanonicalControlError(error_code)
            owned.close_one(current)
            owned.check()
            current = child
        cell = next(item for item in owned.cells if item.descriptor == current and not item.disposed)
        result = PinnedDirectory(cell, Path(os.fspath(path)), owned)
        return result
    except BaseException:
        # The enclosing owner survives this helper, including failed return.
        raise


def open_pinned_regular(
    path: PathArgument, *, owner: DescriptorOwner, error_code: str, missing_error_code: str | None = None,
    nonblocking: bool = False,
) -> tuple[int, os.stat_result]:
    """Borrow a regular FD from owner; returning the tuple transfers no ownership."""

    components = _absolute_components(path, error_code=error_code, allow_root=False)
    parent_path = Path("/", *components[:-1])
    parent = open_pinned_directory(
        parent_path, owner=owner, error_code=error_code, missing_error_code=missing_error_code
    )
    owned = owner
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    if nonblocking:
        flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        try:
            descriptor = owned.open(components[-1], flags, dir_fd=parent.descriptor)
        except FileNotFoundError as exc:
            raise CanonicalControlError(missing_error_code or error_code) from exc
        except OSError as exc:
            raise CanonicalControlError(error_code) from exc
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise CanonicalControlError(error_code)
        owned.close_one(parent.descriptor)
        owned.check()
        return descriptor, opened
    except BaseException:
        raise


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


def verify_opened_regular_digest(
    descriptor: int,
    *,
    expected_size: int,
    expected_sha256: str,
    limit: int,
    error_code: str,
) -> None:
    """Verify a regular object with bounded reads and no payload retention."""

    opened = os.fstat(descriptor)
    if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size != expected_size:
        raise CanonicalControlError(error_code)
    digest = hashlib.sha256()
    count = 0
    while True:
        chunk = os.read(descriptor, min(1024 * 1024, limit + 1 - count))
        if not chunk:
            break
        count += len(chunk)
        if count > limit:
            raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
        digest.update(chunk)
    closed = os.fstat(descriptor)
    stable = (
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mtime_ns,
        opened.st_ctime_ns,
    ) == (
        closed.st_dev,
        closed.st_ino,
        closed.st_size,
        closed.st_mtime_ns,
        closed.st_ctime_ns,
    )
    if not stable:
        raise CanonicalControlError(error_code)
    if count != expected_size or digest.hexdigest() != expected_sha256:
        raise CanonicalControlError(error_code)


def _open_unique_temporary(directory_fd: int, *, owner: DescriptorOwner, prefix: str) -> tuple[str, int]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    for _ in range(128):
        name = f".{prefix}.{secrets.token_hex(16)}.tmp"
        try:
            return name, owner.open(name, flags, 0o600, dir_fd=directory_fd)
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
    with DescriptorOwner(error_code) as owner:

        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected_sha256 or len(payload) > limit:
            raise CanonicalControlError(error_code)
        directory = open_pinned_directory(store, owner=owner, create=True, error_code=error_code)
        temporary_name = ""
        try:
            temporary_name, temporary_fd = _open_unique_temporary(directory.descriptor, owner=owner, prefix=actual)
            try:
                with os.fdopen(temporary_fd, "wb", buffering=0, closefd=False) as stream:
                    stream.write(payload)
                    os.fsync(stream.fileno())
            finally:
                owner.close_one(temporary_fd)
                owner.check()
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
            target_fd = owner.open(
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
                owner.close_one(target_fd)
                owner.check()
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


def publish_opened_regular_stream(
    source_fd: int,
    *,
    store: Path,
    expected_size: int,
    expected_sha256: str,
    limit: int,
    error_code: str,
    mutation_error_code: str,
) -> Path:
    """Stream one pinned source into an atomically published immutable object."""
    with DescriptorOwner(error_code) as owner:

        opened = os.fstat(source_fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or opened.st_size != expected_size
            or expected_size > limit
        ):
            raise CanonicalControlError(error_code)
        directory = open_pinned_directory(store, owner=owner, create=True, error_code=error_code)
        temporary_name = ""
        try:
            temporary_name, temporary_fd = _open_unique_temporary(
                directory.descriptor, owner=owner, prefix=expected_sha256
            )
            digest = hashlib.sha256()
            count = 0
            try:
                while True:
                    chunk = os.read(source_fd, min(1024 * 1024, limit + 1 - count))
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > limit:
                        raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
                    digest.update(chunk)
                    view = memoryview(chunk)
                    while view:
                        written = os.write(temporary_fd, view)
                        if written <= 0:
                            raise CanonicalControlError(error_code)
                        view = view[written:]
                os.fsync(temporary_fd)
            finally:
                owner.close_one(temporary_fd)
                owner.check()
            closed = os.fstat(source_fd)
            stable = (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
                opened.st_mtime_ns,
                opened.st_ctime_ns,
            ) == (
                closed.st_dev,
                closed.st_ino,
                closed.st_size,
                closed.st_mtime_ns,
                closed.st_ctime_ns,
            )
            if not stable:
                raise CanonicalControlError(mutation_error_code)
            if count != expected_size or digest.hexdigest() != expected_sha256:
                raise CanonicalControlError(error_code)
            try:
                os.link(
                    temporary_name,
                    expected_sha256,
                    src_dir_fd=directory.descriptor,
                    dst_dir_fd=directory.descriptor,
                    follow_symlinks=False,
                )
            except FileExistsError:
                pass
            os.unlink(temporary_name, dir_fd=directory.descriptor)
            temporary_name = ""
            collision_error = f"{error_code}: content-addressed collision"
            try:
                target_fd = owner.open(
                    expected_sha256,
                    os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=directory.descriptor,
                )
            except OSError as exc:
                raise CanonicalControlError(collision_error) from exc
            try:
                verify_opened_regular_digest(
                    target_fd,
                    expected_size=expected_size,
                    expected_sha256=expected_sha256,
                    limit=limit,
                    error_code=collision_error,
                )
                os.fchmod(target_fd, 0o444)
            finally:
                owner.close_one(target_fd)
                owner.check()
            os.fsync(directory.descriptor)
            return store / expected_sha256
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
    "DescriptorAcquisition",
    "DescriptorCloseError",
    "DescriptorOwner",
    "pinned_acquisition_policy",
    "PinnedDirectory",
    "open_pinned_directory",
    "open_pinned_regular",
    "publish_content_addressed_bytes",
    "publish_opened_regular_stream",
    "verify_opened_regular",
    "verify_opened_regular_digest",
]
