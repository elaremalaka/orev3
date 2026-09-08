from __future__ import annotations

import json
import hashlib
import io
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from orev3.execution.evidence_preparation import reconstruct_projection_twice, reconstruct_replay_twice
from orev3.execution.canonical import CanonicalControlError, parse_canonical_bytes
from orev3.execution.runtime import (
    ControllerReservationSession,
    MACOS_SANDBOX_EXEC,
    authenticate_bounded_bootstrap_request_artifact,
    authenticate_bounded_time_wrapper,
    construct_bounded_spawn_file_actions,
    construct_bounded_launch_environment,
    create_bounded_bootstrap_request_artifact,
    authenticate_bounded_launch_environment,
    authenticate_bounded_process_argv,
    BoundedGateReleaseState,
    BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY,
    classify_bounded_worker_transport,
    decode_governed_wait_status,
    GovernedProcessInstanceV1,
    GovernedProcessObservation,
    GovernedWorkerFDObservation,
    GovernedWaitStatus,
    authenticate_bounded_process_topology,
    authenticate_bounded_worker_fd_set,
    parse_darwin_kern_procargs2,
    safely_terminate_bounded_process_group,
    query_darwin_process_group_pids,
    query_darwin_process_observation,
    query_darwin_process_path,
    query_darwin_process_argv,
    query_darwin_process_fds,
    authenticate_and_release_bounded_start_gate,
    BoundedInvocationResources,
    orchestrate_bounded_pre_gate_authentication,
    decode_darwin_pipe_fdinfo,
    decode_darwin_socket_fdinfo,
    decode_darwin_vnode_fdinfo,
    build_darwin_worker_fd_observations,
    reconstruct_bounded_streaming_launch_authority,
    release_bounded_start_gate,
    render_phase3b_sandbox_profile,
    run_phase3b_worker,
    sanitized_worker_environment,
)
from orev3.execution.test_policy import run_readiness_tests
from orev3.execution.test_policy import READINESS_TEST_COLLECTION_DOMAIN
from orev3.execution.canonical import canonical_bytes, domain_identity
from orev3.execution.bounded_streaming_worker_bootstrap import (
    MAX_RESERVATION_FRAME_BYTES,
    RESERVATION_UINT64_MAX,
    RESERVATION_KINDS,
    RESERVATION_FAILURE_CODES,
    ReservationProtocolError,
    ReservationAllowance,
    reservation_payload,
    parse_reservation_payload,
    reservation_frame,
    parse_reservation_frame,
    read_reservation_frame,
    BOOTSTRAP_REQUEST_DOMAIN,
    BOUNDED_GENERATION,
    BOUNDED_STREAMING_WORKER_DISPATCH,
    BoundedBootstrapError,
    bootstrap_canonical_bytes,
    bootstrap_domain_identity,
    bootstrap_parse_request_bytes,
    consume_start_gate,
    read_authenticated_request_fd,
    BoundedProjectImportError,
    BoundedProjectImportSession,
    MODEL_B_MODULE_PATHS,
    MODEL_A_CLOSURE_PATHS,
    authenticate_source_code_closure,
    SYNTHETIC_PACKAGES,
)



# Stage 3C Slice 2: synthetic controller-owned namespaces, never live paths.
def _operation_fixture(tmp_path):
    import orev3.execution.runtime as runtime
    anchor = tmp_path.resolve() / "private-store"
    anchor.mkdir(mode=0o700)
    owner = runtime.ControllerOperationNamespace(anchor)
    owner.recover()
    return runtime, owner, anchor, anchor / ".orev3-bounded-streaming-v1" / "operations"


def _operation_file(path, payload=b""):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, payload)
    finally:
        os.close(descriptor)


def _operation_orphan(owner, operations, payload=True):
    handle = owner.create_operation()
    name = handle.operation_id
    if payload:
        nested = operations / name / "worker" / "nested"
        nested.mkdir(mode=0o700)
        _operation_file(nested / "part", b"abc")
        _operation_file(operations / name / "bounded-bootstrap-request.json", b"partial")
    handle.close()
    return name


# R1: injected close outcomes are unknowable to the owner, even for EINTR.
@pytest.mark.parametrize("fault_indices", [(0,), (0, 1, 2), (4,)])
def test_operation_recovery_r1_root_independent_teardown(tmp_path, monkeypatch, fault_indices):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    handle = owner.create_operation()
    name = handle.operation_id
    descriptors = [entry.descriptor for entry in reversed(handle._entries)]
    real_close = os.close
    attempts = []

    def interrupted_after_close(fd):
        attempts.append(fd)
        real_close(fd)
        if descriptors.index(fd) in fault_indices:
            raise InterruptedError(4, "closed, but interrupted")

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", interrupted_after_close)
        with pytest.raises(runtime.CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            handle.close()
        assert attempts == descriptors
        assert [item.descriptor for item in handle.unresolved_closes] == [
            descriptors[index] for index in fault_indices]
        with pytest.raises(runtime.CanonicalControlError):
            handle.close()
        assert attempts == descriptors
        with pytest.raises(runtime.CanonicalControlError):
            _ = handle.lease_descriptor
    # The independently closable lease was not skipped; even an after-close
    # lease failure must remain explicitly unresolved rather than claim release.
    result = runtime.ControllerOperationNamespace(anchor).recover()
    assert result.live_operations == ()
    assert result.recovered_operations == (name,)


@pytest.mark.parametrize("fault_indices", [(0,), (0, 1, 2), (1,)])
def test_operation_recovery_r1_namespace_teardown(tmp_path, monkeypatch, fault_indices):
    runtime, owner, anchor, _ = _operation_fixture(tmp_path)
    real_close, real_recover = os.close, owner._recover
    descriptors, attempts = [], []

    def recover_and_arm():
        result = real_recover()
        descriptors.extend(reversed(owner._descriptors.pending))
        return result

    def interrupted_after_close(fd):
        if descriptors:
            attempts.append(fd)
        real_close(fd)
        if descriptors and descriptors.index(fd) in fault_indices:
            raise InterruptedError(4, "closed, but interrupted")

    with monkeypatch.context() as patch:
        patch.setattr(owner, "_recover", recover_and_arm)
        patch.setattr(os, "close", interrupted_after_close)
        with pytest.raises(runtime.CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            owner.recover()
        assert attempts == descriptors
        assert owner._busy is False
        assert len(owner.unresolved_closes) == len(fault_indices)
        # No stranded guard and no apparently clean owner: rejection is due
        # to explicit unresolved disposition, with no retry of uncertain FDs.
        with pytest.raises(runtime.CanonicalControlError):
            owner.recover()
        assert attempts == descriptors
    lock = os.open(anchor / ".orev3-bounded-streaming-v1" / "coordination.lock", os.O_RDONLY)
    try:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        real_close(lock)
    assert runtime.ControllerOperationNamespace(anchor).recover().live_operations == ()


@pytest.mark.parametrize("actually_closed", [False, True])
def test_operation_recovery_r1_uncertain_lease_not_retried(tmp_path, monkeypatch, actually_closed):
    runtime, owner, anchor, _ = _operation_fixture(tmp_path)
    handle = owner.create_operation()
    name, lease = handle.operation_id, handle.lease_descriptor
    real_close = os.close
    attempts = []

    def uncertain(fd):
        attempts.append(fd)
        if fd != lease or actually_closed:
            real_close(fd)
        if fd == lease:
            raise InterruptedError(4, "unknown close outcome")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "close", uncertain)
            with pytest.raises(runtime.CanonicalControlError):
                handle.close()
            assert len(attempts) == 6
            assert handle.unresolved_closes[0].descriptor == lease
            with pytest.raises(runtime.CanonicalControlError):
                handle.close()
            assert attempts.count(lease) == 1
        result = runtime.ControllerOperationNamespace(anchor).recover()
        assert result.live_operations == (() if actually_closed else (name,))
        assert result.recovered_operations == ((name,) if actually_closed else ())
    finally:
        # Only the fixture knows this injected failure left its lease open.
        # Production deliberately has no equivalent raw-integer retry.
        if not actually_closed:
            real_close(lease)


def test_operation_recovery_r1_reused_descriptor_survives_repeated_close(tmp_path, monkeypatch):
    runtime, owner, _, _ = _operation_fixture(tmp_path)
    handle = owner.create_operation()
    target = handle._entries[-1].descriptor
    source = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    real_close = os.close
    attempts = []
    reused = False

    def close_then_reuse(fd):
        nonlocal reused
        attempts.append(fd)
        real_close(fd)
        if fd == target:
            os.dup2(source, target)
            reused = True
            raise InterruptedError(4, "integer already reused")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "close", close_then_reuse)
            with pytest.raises(runtime.CanonicalControlError):
                handle.close()
            with pytest.raises(runtime.CanonicalControlError):
                handle.close()
            assert attempts.count(target) == 1
            assert os.fstat(target).st_ino == os.fstat(source).st_ino
    finally:
        if reused:
            real_close(target)
        real_close(source)


@pytest.mark.parametrize("also_fail_handle", [False, True])
def test_operation_recovery_r1_failed_handoff_disposes_lease(tmp_path, monkeypatch, also_fail_handle):
    runtime, owner, anchor, _ = _operation_fixture(tmp_path)
    real_init, real_close = runtime.ControllerOperationRoot.__init__, os.close
    handles, failures = [], []

    def capture_handle(self, *args):
        real_init(self, *args)
        handles.append(self)

    def interrupted_after_close(fd):
        real_close(fd)
        # Handle construction marks the end of admission's filesystem work.
        if handles and (not failures or (also_fail_handle and fd == handles[0]._entries[-1].descriptor)):
            failures.append(fd)
            raise InterruptedError(4, "handoff teardown interrupted")

    with monkeypatch.context() as patch:
        patch.setattr(runtime.ControllerOperationRoot, "__init__", capture_handle)
        patch.setattr(os, "close", interrupted_after_close)
        with pytest.raises(runtime.CanonicalControlError):
            owner.create_operation()
    assert len(handles) == 1
    assert owner._busy is False
    assert len(owner.unresolved_closes) == (2 if also_fail_handle else 1)
    assert handles[0]._entries == ()
    result = runtime.ControllerOperationNamespace(anchor).recover()
    assert result.live_operations == ()
    assert result.recovered_operations == (handles[0].operation_id,)


def test_operation_recovery_r1_failed_open_authentication_still_disposes_fd(tmp_path, monkeypatch):
    runtime, owner, anchor, _ = _operation_fixture(tmp_path)
    real_auth, real_close = runtime._RecoveryEntry.authenticate, os.close
    target, attempts = [], []

    def reject_open(entry, *args, **kwargs):
        if entry.name == "lease" and not target:
            target.append(entry.descriptor)
            raise runtime.CanonicalControlError("DISK_RESERVATION_STATE_MISMATCH")
        return real_auth(entry, *args, **kwargs)

    def uncertain(fd):
        if target:
            attempts.append(fd)
        real_close(fd)
        if target and fd == target[0]:
            raise InterruptedError(4, "closed during failed admission")

    with monkeypatch.context() as patch:
        patch.setattr(runtime._RecoveryEntry, "authenticate", reject_open)
        patch.setattr(os, "close", uncertain)
        with pytest.raises(runtime.CanonicalControlError):
            owner.create_operation()
    assert target and attempts.count(target[0]) == 1
    assert owner._busy is False
    assert owner.unresolved_closes[0].descriptor == target[0]
    assert runtime.ControllerOperationNamespace(anchor).recover().live_operations == ()


def test_operation_recovery_r1_successful_close_idempotent(tmp_path):
    _, owner, _, _ = _operation_fixture(tmp_path)
    handle = owner.create_operation()
    handle.close()
    handle.close()
    assert handle.unresolved_closes == ()
    owner.recover()
    owner.recover()
    assert owner.unresolved_closes == ()


@pytest.mark.parametrize("kind", ["directory", "regular"])
@pytest.mark.parametrize("outcome", ["closed-and-reused", "not-closed", "io-error", "both-fail"])
def test_operation_recovery_r1_helper_uncertain_parent_handoff(monkeypatch, kind, outcome):
    import stat
    from types import SimpleNamespace
    import orev3.execution.filesystem_capability as capability
    descriptors = iter((100, 101) if kind == "directory" else (101,))
    live = {} if kind == "directory" else {100: "parent"}
    attempts = []

    def opened(*args, **kwargs):
        fd = next(descriptors)
        live[fd] = "parent" if fd == 100 else "child"
        return fd

    def closed(fd):
        attempts.append(fd)
        assert live[fd] != "unrelated", "retried a reused parent integer"
        if fd == 100:
            if outcome != "not-closed":
                del live[fd]
            if outcome == "closed-and-reused":
                live[fd] = "unrelated"
            if outcome == "io-error":
                raise OSError(5, "unknown I/O close outcome")
            raise InterruptedError(4, "unknown parent close outcome")
        del live[fd]
        if outcome == "both-fail":
            raise InterruptedError(4, "child closed but interrupted")

    def inspected(fd):
        mode = stat.S_IFREG if kind == "regular" and fd == 101 else stat.S_IFDIR
        return SimpleNamespace(st_mode=mode | 0o600, st_nlink=1)

    with monkeypatch.context() as patch:
        patch.setattr(os, "open", opened)
        patch.setattr(os, "close", closed)
        patch.setattr(os, "fstat", inspected)
        if kind == "regular":
            patch.setattr(capability, "open_pinned_directory",
                          _synthetic_parent_owner)
        helper = capability.open_pinned_directory if kind == "directory" else capability.open_pinned_regular
        with pytest.raises(capability.DescriptorCloseError, match="INPUT_UNSAFE_TYPE") as caught:
            _call_owned_helper(helper, "/synthetic/leaf" if kind == "regular" else "/synthetic",
                   error_code="INPUT_UNSAFE_TYPE")
    assert attempts == [100, 101]
    assert 101 not in live
    assert live == ({100: "unrelated"} if outcome == "closed-and-reused" else
                    {100: "parent"} if outcome == "not-closed" else {})
    records = caught.value.unresolved_closes
    assert tuple(item.descriptor for item in records) == ((100, 101) if outcome == "both-fail" else (100,))
    with pytest.raises(AttributeError):
        records[0].descriptor = 999


@pytest.mark.parametrize("kind", ["directory", "regular"])
@pytest.mark.parametrize("failure", ["stat", "type", "open"])
def test_operation_recovery_r1_helper_failed_child_authentication(tmp_path, monkeypatch, kind, failure):
    import errno
    import stat
    from types import SimpleNamespace
    import orev3.execution.filesystem_capability as capability
    child = tmp_path / "child"
    if failure != "open":
        if kind == "directory": child.mkdir()
        else: child.write_bytes(b"input")
    captured = []
    receive = capability.DescriptorOwner._receive
    inspected = os.fstat

    def received(owner, cell):
        descriptor = receive(owner, cell)
        captured.append(descriptor)
        return descriptor

    def authenticated(descriptor):
        value = inspected(descriptor)
        if failure == "stat": raise OSError(errno.EIO, "fstat failed")
        if failure == "type": return SimpleNamespace(st_mode=stat.S_IFIFO, st_nlink=1)
        return value

    # Keep the real OS acquisition primitive: a Python fake raising OSError is
    # not evidence of the kernel's definitive no-acquisition outcome.
    with monkeypatch.context() as patch:
        patch.setattr(capability.DescriptorOwner, "_receive", received)
        patch.setattr(os, "fstat", authenticated)
        helper = capability.open_pinned_directory if kind == "directory" else capability.open_pinned_regular
        with pytest.raises((OSError, capability.CanonicalControlError)):
            _call_owned_helper(helper, str(child), error_code="INPUT_UNSAFE_TYPE")
    assert captured
    for descriptor in set(captured):
        with pytest.raises(OSError) as caught: inspected(descriptor)
        assert caught.value.errno == errno.EBADF


@pytest.mark.parametrize("kind", ["directory", "regular"])
def test_operation_recovery_r1_helper_successful_transfer(monkeypatch, kind):
    import stat
    from types import SimpleNamespace
    import orev3.execution.filesystem_capability as capability
    descriptors = iter((100, 101) if kind == "directory" else (101,))
    live = set() if kind == "directory" else {100}
    attempts = []

    def opened(*args, **kwargs):
        fd = next(descriptors)
        live.add(fd)
        return fd

    def closed(fd):
        attempts.append(fd)
        live.remove(fd)

    with monkeypatch.context() as patch, capability.DescriptorOwner("INPUT_UNSAFE_TYPE") as owned:
        patch.setattr(os, "open", opened)
        patch.setattr(os, "close", closed)
        patch.setattr(os, "fstat", lambda fd: SimpleNamespace(
            st_mode=stat.S_IFDIR if kind == "directory" else stat.S_IFREG, st_nlink=1))
        if kind == "regular":
            patch.setattr(capability, "open_pinned_directory",
                          _synthetic_parent_owner)
            result = capability.open_pinned_regular("/synthetic/leaf", error_code="INPUT_UNSAFE_TYPE", owner=owned)
            descriptor = result[0]
        else:
            result = capability.open_pinned_directory("/synthetic", error_code="INPUT_UNSAFE_TYPE", owner=owned)
            descriptor = result.descriptor
        assert descriptor == 101 and live == {101} and attempts == [100]
        owned.close_one(descriptor)
    assert live == set()


@pytest.mark.parametrize("at_repin", [False, True])
def test_operation_recovery_r1_runtime_retains_helper_uncertainty(tmp_path, monkeypatch, at_repin):
    import orev3.execution.filesystem_capability as capability
    runtime, owner, anchor, _ = _operation_fixture(tmp_path)
    real_pin, real_close = capability.open_pinned_directory, os.close
    calls, failures = [], []
    armed = False

    def pin(*args, **kwargs):
        nonlocal armed
        calls.append(True)
        armed = len(calls) == (2 if at_repin else 1)
        return real_pin(*args, **kwargs)

    def closed(fd):
        nonlocal armed
        real_close(fd)
        if armed:
            armed = False
            failures.append(fd)
            raise InterruptedError(4, "helper parent closed")

    with monkeypatch.context() as patch:
        patch.setattr(capability, "open_pinned_directory", pin)
        patch.setattr(os, "close", closed)
        with pytest.raises(runtime.CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            owner.recover()
    assert len(failures) == 1
    assert owner._busy is False
    assert tuple(item.descriptor for item in owner.unresolved_closes) == tuple(failures)
    with pytest.raises(runtime.CanonicalControlError):
        owner.recover()
    assert runtime.ControllerOperationNamespace(anchor).recover().live_operations == ()


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("close_failures", [False, True])
def test_operation_recovery_r1_handoff_every_boundary(tmp_path, monkeypatch, interruption, close_failures):
    """Interrupt every handoff/constructor line and the constructor return.

    No source-string or fixed-line-number expectation: verify actual disposal,
    lease release, FD reuse safety and lack of returned authority each time.
    """
    import fcntl
    runtime, owner, anchor, _ = _operation_fixture(tmp_path)
    create_code = runtime.ControllerOperationNamespace.create_operation.__code__
    init_code = runtime.ControllerOperationRoot.__init__.__code__

    def is_boundary(frame, event):
        return (frame.f_code is init_code and event in {"line", "return"}) or (
            event == "line" and frame.f_code is create_code and "owned" in frame.f_locals)

    boundaries = []
    def discover(frame, event, arg):
        if is_boundary(frame, event):
            boundaries.append((frame.f_code, frame.f_lineno))
        return discover

    sys.settrace(discover)
    try:
        successful = owner.create_operation()
    finally:
        sys.settrace(None)
    successful.close()
    owner.recover()
    assert boundaries and any(code is init_code for code, _ in boundaries)
    assert any(code is create_code for code, _ in boundaries)

    for target_index, target in enumerate(boundaries):
        current = runtime.ControllerOperationNamespace(anchor)
        source = os.open(anchor, os.O_RDONLY | os.O_DIRECTORY)
        real_close = os.close
        encountered, attempts, expected, owned = [], [], [], []
        injected = False
        reused = False
        lease = None

        def interrupt(frame, event, arg):
            nonlocal injected, lease
            if is_boundary(frame, event):
                encountered.append((frame.f_code, frame.f_lineno))
                if len(encountered) - 1 == target_index:
                    assert encountered[-1] == target
                    entries = frame.f_locals.get("owned", frame.f_locals.get("entries"))
                    owned.extend(entry.descriptor for entry in entries)
                    lease = owned[1]
                    expected.extend(current._descriptors.pending)
                    injected = True
                    raise interruption("synthetic admission handoff interruption")
            return interrupt

        def close_and_reuse(fd):
            nonlocal reused
            if injected:
                attempts.append(fd)
            real_close(fd)
            if injected and fd == lease:
                assert not reused, "automatic cleanup retried the lease integer"
                os.dup2(source, fd)
                reused = True
            if injected and close_failures and fd in (owned[-1], lease):
                raise InterruptedError(4, "closed, possibly already reused")

        try:
            with monkeypatch.context() as patch:
                patch.setattr(os, "close", close_and_reuse)
                sys.settrace(interrupt)
                try:
                    with pytest.raises((interruption, runtime.CanonicalControlError)):
                        current.create_operation()
                finally:
                    sys.settrace(None)
            assert injected, target_index
            assert len(attempts) == len(set(attempts)), (target_index, attempts)
            assert set(attempts) == set(expected), (target_index, attempts, expected)
            assert all(attempts.count(fd) == 1 for fd in owned)
            assert reused and os.fstat(lease).st_ino == os.fstat(source).st_ino
            assert current._busy is False
            if close_failures:
                assert {item.descriptor for item in current.unresolved_closes} == {owned[-1], lease}
            else:
                assert current.unresolved_closes == ()
            # Nonblocking probe avoids a hung test concealing a leaked flock.
            lock = os.open(anchor / ".orev3-bounded-streaming-v1" / "coordination.lock", os.O_RDONLY)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                real_close(lock)
        finally:
            sys.settrace(None)
            if reused:
                real_close(lease)  # fixture-owned unrelated replacement only
            real_close(source)
        recovered = runtime.ControllerOperationNamespace(anchor).recover()
        assert recovered.live_operations == ()
        assert len(recovered.recovered_operations) == 1


def test_operation_recovery_r1_handoff_independent_lifetimes(tmp_path):
    runtime, namespace, anchor, _ = _operation_fixture(tmp_path)
    first = namespace.create_operation()
    second = namespace.create_operation()
    try:
        assert first.operation_id != second.operation_id
        assert namespace.recover().live_operations == tuple(sorted((first.operation_id, second.operation_id)))
        # Closing one aggregate cannot dispose another operation or a later
        # namespace transition's descriptors, even if OS integers were reused.
        first.close()
        first.close()
        assert os.fstat(second.lease_descriptor).st_size == 0
        result = namespace.recover()
        assert result.recovered_operations == (first.operation_id,)
        assert result.live_operations == (second.operation_id,)
    finally:
        first.close()
        second.close()
    assert runtime.ControllerOperationNamespace(anchor).recover().recovered_operations == (second.operation_id,)


@pytest.fixture
def descriptor_accounting_case(tmp_path):
    runtime, ns, anchor, operations = _operation_fixture(tmp_path)
    owner = ns.create_operation()
    bridge = runtime.ControllerDescriptorAccounting(ns, owner, bootstrap_request_identity="a" * 64)
    opened = []
    def create(relative, payload=b""):
        path = operations / owner.operation_id / relative
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        opened.append(fd)
        if payload:
            os.write(fd, payload)
        return fd, path
    def bind(fd, role, producer="controller"):
        return bridge.bind_created(fd, operation_id=owner.operation_id,
            creation_role=role, producer=producer,
            request_identity="a" * 64 if role == "bootstrap_request" else None)
    yield runtime, ns, anchor, owner, bridge, create, bind
    for fd in opened:
        try:
            os.close(fd)
        except OSError:
            pass  # Closed explicitly by a stale-descriptor fixture.
    owner.close()


@pytest.mark.parametrize("role,producer,category", [
    ("source_snapshot_copy", "controller", "snapshot_growth"),
    ("source_publication_temporary", "controller", "snapshot_growth"),
    ("projection_publication_copy", "controller", "projection_publication"),
    ("projection_publication_temporary", "worker", "projection_publication"),
    ("projection_candidate", "worker", "reconstruction_growth"),
    ("reconstruction_candidate", "controller", "reconstruction_growth"),
    ("bootstrap_request", "controller", "controller_temporary_growth"),
    ("stdout_capture", "controller", "worker_output_growth"),
    ("stderr_capture", "controller", "worker_output_growth"),
    ("controller_temporary", "controller", "controller_temporary_growth"),
    ("worker_output", "worker", "worker_output_growth"),
])
def test_descriptor_accounting_creation_roles(descriptor_accounting_case, role, producer, category):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    # Placement/producer do not override specific creation authority.
    relative = "bounded-bootstrap-request.json" if role == "bootstrap_request" else "controller/nested/projection-looking-name"
    fd, _ = create(relative, b"abc")
    token = bind(fd, role, producer)
    assert token.operation_id == owner.operation_id
    assert token.category == category
    assert bridge.observe(category) == 3
    for other in bridge._wire.RESERVATION_KINDS:
        if other != category:
            assert bridge.observe(other) == 0
    bridge.start_session(max_temporary_disk_bytes=3)
    assert sum(bridge.snapshot.charged_bytes) == 3
    assert bridge.snapshot.charged_bytes == bridge.snapshot.reserved_bytes


@pytest.mark.parametrize("role,producer", [
    ("unknown", "controller"), (("projection_candidate", "projection_publication_copy"), "worker"),
    ("controller_temporary", "worker"), ("worker_output", "controller"),
    ("bootstrap_request", "worker"), ("stdout_capture", "wire"),
])
def test_descriptor_accounting_contradictory_role(descriptor_accounting_case, role, producer):
    _, _, _, _, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/file")
    with pytest.raises(Exception, match="DISK_RESERVATION_STATE_MISMATCH"):
        bind(fd, role, producer)


@pytest.mark.parametrize("fault", ["operation", "request_identity", "request_location", "root_generic", "duplicate", "transfer"])
def test_descriptor_accounting_binding_rejection(descriptor_accounting_case, fault):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    relative = "bounded-bootstrap-request.json" if fault in ("request_identity", "root_generic") else "controller/file"
    fd, _ = create(relative)
    if fault in ("duplicate", "transfer"):
        bind(fd, "projection_candidate", "worker")
    with pytest.raises(Exception, match="DISK_RESERVATION_STATE_MISMATCH"):
        if fault == "operation":
            bridge.bind_created(fd, operation_id="op-" + "f"*32, creation_role="controller_temporary", producer="controller")
        elif fault == "request_identity":
            bridge.bind_created(fd, operation_id=owner.operation_id, creation_role="bootstrap_request",
                                producer="controller", request_identity="b"*64)
        elif fault == "request_location":
            bind(fd, "bootstrap_request")
        elif fault == "root_generic":
            bind(fd, "controller_temporary")
        else:
            bind(fd, "projection_candidate" if fault == "duplicate" else "projection_publication_copy", "worker")


def test_descriptor_accounting_distinct_copies_and_fixed_rename(descriptor_accounting_case):
    _, _, _, _, bridge, create, bind = descriptor_accounting_case
    first, path = create("worker/candidate", b"same")
    second, _ = create("reconstruction/candidate", b"same")
    copy, _ = create("snapshot-publication/copy", b"same")
    bind(first, "projection_candidate", "worker")
    bind(second, "projection_candidate", "worker")
    bind(copy, "projection_publication_copy")
    path.rename(path.parent / "selected-for-publication")
    assert bridge.observe("reconstruction_growth") == 8
    assert bridge.observe("projection_publication") == 4
    bridge.start_session(max_temporary_disk_bytes=12)
    assert sum(bridge.snapshot.charged_bytes) == 12


@pytest.mark.parametrize("fault", ["unbound", "symlink", "fifo", "hardlink", "mode", "deleted", "closed", "substitution", "role_directory", "root_replacement"])
def test_descriptor_accounting_unsafe_or_stale_inventory(descriptor_accounting_case, fault):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, path = create("controller/data", b"x")
    bind(fd, "controller_temporary")
    bridge.start_session(max_temporary_disk_bytes=10)
    before = bridge.snapshot
    if fault == "unbound":
        create("worker/not-bound", b"secret")
    elif fault == "symlink":
        (path.parent / "alias").symlink_to(path)
    elif fault == "fifo":
        os.mkfifo(path.parent / "fifo", 0o600)
    elif fault == "hardlink":
        os.link(path, path.parent / "alias")
    elif fault == "mode":
        path.chmod(0o644)
    elif fault == "deleted":
        path.unlink()
    elif fault == "closed":
        os.close(fd)
    elif fault == "substitution":
        other, _ = create("controller/other", b"x")
        os.dup2(other, fd)
    elif fault == "role_directory":
        os.dup2(owner.category_directory_descriptor("worker"), owner.category_directory_descriptor("controller"))
    else:
        root = path.parent.parent
        root.rename(root.with_name("op-" + "f"*32))
        root.mkdir(mode=0o700)
    with pytest.raises(Exception):
        bridge.observe("controller_temporary_growth")
    assert bridge.snapshot.charged_bytes == before.charged_bytes
    assert bridge.snapshot.reserved_bytes == before.reserved_bytes
    assert bridge.snapshot.expected_sequence == 0
    assert bridge.snapshot.terminal


def test_descriptor_accounting_cross_operation_and_single_bridge(descriptor_accounting_case):
    runtime, ns, anchor, owner, bridge, _, _ = descriptor_accounting_case
    with pytest.raises(Exception):
        runtime.ControllerDescriptorAccounting(ns, owner)
    other = ns.create_operation()
    other_root = anchor / ".orev3-bounded-streaming-v1" / "operations" / other.operation_id
    fd = os.open(other_root / "worker" / "file", os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with pytest.raises(Exception):
            bridge.bind_created(fd, operation_id=owner.operation_id,
                                creation_role="worker_output", producer="worker")
    finally:
        os.close(fd)
        other.close()


def _descriptor_accounting_request(bridge, owner, category, current, growth, sequence=0):
    return bridge._wire.reservation_payload({
        "schema_version": 1, "message_type": "reserve_growth", "operation_id": owner.operation_id,
        "sequence_number": sequence, "reservation_kind": category,
        "current_logical_bytes": current, "requested_growth_bytes": growth,
    })


@pytest.mark.parametrize("growth,accepted", [(10, True), (11, False)])
def test_descriptor_accounting_exact_budget(descriptor_accounting_case, growth, accepted):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/file")
    token = bind(fd, "controller_temporary")
    bridge.start_session(max_temporary_disk_bytes=10)
    request = _descriptor_accounting_request(bridge, owner, token.category, 0, growth)
    if not accepted:
        with pytest.raises(Exception, match="RESOURCE_LIMIT_EXCEEDED"):
            bridge.prepare_request(token, request)
        assert sum(bridge.snapshot.reserved_bytes) == 0
        assert bridge.snapshot.expected_sequence == 0
        return
    bridge.prepare_request(token, request)
    assert sum(bridge.snapshot.charged_bytes) == sum(bridge.snapshot.reserved_bytes) == 0
    ack = bridge.issue_acknowledgment()
    assert bridge._wire.parse_reservation_payload(ack)["sequence_number"] == 0
    assert sum(bridge.snapshot.reserved_bytes) == 10
    assert bridge.snapshot.expected_sequence == 1
    allowance = bridge._wire.ReservationAllowance(owner.operation_id)
    assert allowance.request(token.category, 0, 10) == request
    allowance.accept_response(ack)
    allowance.consume(operation_id=owner.operation_id, sequence_number=0,
                      reservation_kind=token.category, growth_bytes=10)
    with pytest.raises(Exception):
        allowance.consume(operation_id=owner.operation_id, sequence_number=0,
                          reservation_kind=token.category, growth_bytes=10)


@pytest.mark.parametrize("ending", ["orderly", "uncertain", "next_request"])
def test_descriptor_accounting_short_write(descriptor_accounting_case, ending):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("worker/projection")
    token = bind(fd, "projection_candidate", "worker")
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 10))
    bridge.issue_acknowledgment()
    os.write(fd, b"abc")  # Synthetic fixture growth; no runtime writer activation.
    bridge.observe_completion(token)
    assert sum(bridge.snapshot.charged_bytes) == 3
    assert sum(bridge.snapshot.reserved_bytes) == 10
    if ending == "orderly":
        bridge.orderly_eof()
        assert sum(bridge.snapshot.reserved_bytes) == 3
    elif ending == "uncertain":
        bridge.fail_uncertain()
        assert sum(bridge.snapshot.reserved_bytes) == 10 and bridge.snapshot.uncertain
    else:
        bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 3, 1, 1))
        bridge.issue_acknowledgment()
        assert sum(bridge.snapshot.reserved_bytes) == 4
        assert bridge.snapshot.expected_sequence == 2


@pytest.mark.parametrize("fault", ["category", "sequence", "current", "forged_token", "growth_before_ack", "other_target"])
def test_descriptor_accounting_session_binding_failures(descriptor_accounting_case, fault):
    from dataclasses import replace
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("worker/one")
    fd2, _ = create("worker/two")
    token = bind(fd, "projection_candidate", "worker")
    bind(fd2, "projection_candidate", "worker")
    bridge.start_session(max_temporary_disk_bytes=10)
    payload = _descriptor_accounting_request(bridge, owner,
        "worker_output_growth" if fault == "category" else token.category,
        1 if fault == "current" else 0, 10, 1 if fault == "sequence" else 0)
    with pytest.raises(Exception):
        bridge.prepare_request(replace(token) if fault == "forged_token" else token, payload)
        if fault == "growth_before_ack":
            os.write(fd, b"x")
        bridge.issue_acknowledgment()
        if fault == "other_target":
            os.write(fd2, b"x")
            bridge.observe_completion(token)
    assert bridge.snapshot.terminal
    assert bridge.snapshot.expected_sequence == (1 if fault == "other_target" else 0)


def test_descriptor_accounting_overflow(descriptor_accounting_case, monkeypatch):
    from types import SimpleNamespace
    _, _, _, _, bridge, create, bind = descriptor_accounting_case
    identities = set()
    for name in ("a", "b"):
        fd, _ = create("controller/" + name, b"x")
        bind(fd, "controller_temporary")
        value = os.fstat(fd)
        identities.add((value.st_dev, value.st_ino))
    real_fstat, real_stat = os.fstat, os.stat
    def large(value):
        if (value.st_dev, value.st_ino) not in identities:
            return value
        fields = {name: getattr(value, name) for name in (
            "st_dev", "st_ino", "st_uid", "st_gid", "st_mode", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns")}
        fields["st_size"] = 1 << 63
        return SimpleNamespace(**fields)
    with monkeypatch.context() as patch:
        patch.setattr(os, "fstat", lambda fd: large(real_fstat(fd)))
        patch.setattr(os, "stat", lambda *a, **kw: large(real_stat(*a, **kw)))
        with pytest.raises(Exception, match="RESOURCE_LIMIT_EXCEEDED"):
            bridge.observe("controller_temporary_growth")


def test_descriptor_accounting_orphan_aggregate_only(descriptor_accounting_case):
    _, ns, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("reconstruction/candidate", b"abc")
    bind(fd, "projection_candidate", "worker")
    create("worker/unattributed-after-controller-loss", b"xy")
    owner.close()
    with pytest.raises(Exception):
        bridge.observe("reconstruction_growth")
    result = ns.recover()
    assert result.recovered_operations == (owner.operation_id,)
    assert result.inventoried_logical_bytes == 5


def test_descriptor_accounting_published_outside_not_authority(descriptor_accounting_case):
    _, _, anchor, _, bridge, _, _ = descriptor_accounting_case
    published = anchor / ("e" * 64)
    published.write_bytes(b"published")
    published.chmod(0o444)
    assert all(bridge.observe(kind) == 0 for kind in bridge._wire.RESERVATION_KINDS)
    assert published.read_bytes() == b"published"


def test_descriptor_accounting_closed_borrow_precedes_scratch_open(descriptor_accounting_case, monkeypatch):
    _, _, _, _, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/file")
    bind(fd, "controller_temporary")
    os.close(fd)
    def forbidden_open(*args, **kwargs):
        pytest.fail("scratch allocation preceded borrowed-FD authentication")
    with monkeypatch.context() as patch:
        patch.setattr(os, "open", forbidden_open)
        with pytest.raises(Exception, match="DISK_RESERVATION_STATE_MISMATCH"):
            bridge.observe("controller_temporary_growth")


def test_descriptor_accounting_uid_and_duplicate_binding(descriptor_accounting_case, monkeypatch):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/file", b"x")
    bind(fd, "controller_temporary")
    bridge.start_session(max_temporary_disk_bytes=10)
    with monkeypatch.context() as patch:
        patch.setattr(os, "geteuid", lambda: owner._entries[0].opened.st_uid + 1)
        with pytest.raises(Exception):
            bridge.observe("controller_temporary_growth")
    assert sum(bridge.snapshot.charged_bytes) == 1


@pytest.mark.parametrize("nonempty", [False, True])
def test_descriptor_accounting_new_object_after_session(descriptor_accounting_case, nonempty):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    bridge.start_session(max_temporary_disk_bytes=10)
    fd, _ = create("worker/new", b"x" if nonempty else b"")
    if nonempty:
        with pytest.raises(Exception):
            bind(fd, "worker_output", "worker")
        assert sum(bridge.snapshot.charged_bytes) == 0
    else:
        token = bind(fd, "worker_output", "worker")
        bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 1))
        bridge.issue_acknowledgment()
        assert sum(bridge.snapshot.reserved_bytes) == 1


def test_descriptor_accounting_overgrowth_retains_authenticated_actual(descriptor_accounting_case):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("worker/file")
    token = bind(fd, "worker_output", "worker")
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 10))
    bridge.issue_acknowledgment()
    os.write(fd, b"x" * 11)
    with pytest.raises(Exception):
        bridge.observe_completion(token)
    assert sum(bridge.snapshot.reserved_bytes) == 11
    assert sum(bridge.snapshot.charged_bytes) == 11
    assert bridge.snapshot.uncertain


def test_descriptor_accounting_uncertain_auth_failure_retains_floor(descriptor_accounting_case):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, path = create("worker/file")
    token = bind(fd, "worker_output", "worker")
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 10))
    bridge.issue_acknowledgment()
    os.write(fd, b"abc")
    path.chmod(0o644)
    with pytest.raises(Exception):
        bridge.fail_uncertain()
    assert sum(bridge.snapshot.reserved_bytes) == 10
    assert bridge.snapshot.uncertain


def test_descriptor_accounting_copy_deletion_cannot_release_original(descriptor_accounting_case):
    _, _, _, _, bridge, create, bind = descriptor_accounting_case
    original, _ = create("reconstruction/original", b"same")
    copy, path = create("snapshot-publication/copy", b"same")
    bind(original, "projection_candidate", "worker")
    bind(copy, "projection_publication_copy")
    bridge.start_session(max_temporary_disk_bytes=8)
    path.unlink()  # No publication/release proof API is present in this slice.
    with pytest.raises(Exception):
        bridge.orderly_eof()
    assert bridge.snapshot.reserved_bytes[3:] == (4, 4)
    assert bridge.snapshot.charged_bytes[3:] == (4, 4)


def test_descriptor_accounting_observation_teardown_failure_no_ack(descriptor_accounting_case, monkeypatch):
    _, ns, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/file")
    token = bind(fd, "controller_temporary")
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 10))
    original = type(bridge._session).issue_acknowledgment
    real_close = os.close
    armed = False
    def issue(session):
        nonlocal armed
        payload = original(session)
        armed = True
        return payload
    def interrupted(fd):
        nonlocal armed
        real_close(fd)
        if armed:
            armed = False
            raise InterruptedError(4, "already closed")
    with monkeypatch.context() as patch:
        patch.setattr(type(bridge._session), "issue_acknowledgment", issue)
        patch.setattr(os, "close", interrupted)
        with pytest.raises(Exception):
            bridge.issue_acknowledgment()
    assert sum(bridge.snapshot.reserved_bytes) == 10
    assert bridge.snapshot.uncertain
    assert not ns._busy
    assert os.fstat(owner.lease_descriptor).st_size == 0
    assert os.fstat(fd).st_size == 0


@pytest.mark.parametrize("fault", ["budget", "category", "reported_size"])
def test_descriptor_accounting_rejected_short_write_request_is_nonmutating(descriptor_accounting_case, fault):
    _, _, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/file")
    token = bind(fd, "controller_temporary")
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 10))
    bridge.issue_acknowledgment()
    os.write(fd, b"abc")
    before = bridge.snapshot
    payload = _descriptor_accounting_request(bridge, owner,
        "worker_output_growth" if fault == "category" else token.category,
        2 if fault == "reported_size" else 3, 8 if fault == "budget" else 1, 1)
    with pytest.raises(Exception):
        bridge.prepare_request(token, payload)
    after = bridge.snapshot
    assert (after.charged_bytes, after.reserved_bytes, after.expected_sequence) == (
        before.charged_bytes, before.reserved_bytes, before.expected_sequence)
    assert after.terminal and not after.uncertain



# Admission-serialization correction: synthetic controller sequencing only.
_ADMISSION_ROLES = (
    "source_snapshot_copy", "controller_temporary", "stdout_capture",
    "projection_publication_copy", "projection_candidate",
)


def _admission_objects(case):
    _, _, _, owner, bridge, create, bind = case
    objects = [create("controller/nested/object-" + str(i))[0] for i in range(5)]
    tokens = [bind(fd, role) for fd, role in zip(objects, _ADMISSION_ROLES)]
    return owner, bridge, objects, tokens


@pytest.mark.parametrize("changed", range(5))
@pytest.mark.parametrize("requested", range(5))
def test_descriptor_accounting_admission_unexplained_first(descriptor_accounting_case, changed, requested):
    owner, bridge, fds, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    before = bridge.snapshot
    os.write(fds[changed], b"12345")  # Explicit violation, never a new baseline.
    with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
        bridge.prepare_request(tokens[requested], _descriptor_accounting_request(
            bridge, owner, tokens[requested].category, 5 if requested == changed else 0, 10))
    after = bridge.snapshot
    assert (after.charged_bytes, after.reserved_bytes, after.expected_sequence) == (
        before.charged_bytes, before.reserved_bytes, before.expected_sequence)
    assert after.terminal and not after.pending_request


@pytest.mark.parametrize("later", [False, True])
def test_descriptor_accounting_admission_multiple_unexplained(descriptor_accounting_case, later):
    owner, bridge, fds, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=20)
    if later:
        bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
        bridge.issue_acknowledgment()
        with bridge.writer_activity(tokens[1], sequence=0):
            os.write(fds[1], b"abc")
        bridge.observe_completion(tokens[1])
    before = bridge.snapshot
    os.write(fds[0], b"x")
    os.write(fds[4], b"yy")
    with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
        bridge.prepare_request(tokens[2], _descriptor_accounting_request(
            bridge, owner, tokens[2].category, 0, 1, before.expected_sequence))
    after = bridge.snapshot
    assert (after.charged_bytes, after.reserved_bytes, after.expected_sequence) == (
        before.charged_bytes, before.reserved_bytes, before.expected_sequence)


@pytest.mark.parametrize("extra,accepted", [(7, True), (8, False)])
def test_descriptor_accounting_admission_accounted_budget(descriptor_accounting_case, extra, accepted):
    owner, bridge, fds, tokens = _admission_objects(descriptor_accounting_case)
    for fd in fds:
        os.write(fd, b"x")  # Governed authenticated initial retained objects.
    bridge.start_session(max_temporary_disk_bytes=15)
    bridge.prepare_request(tokens[4], _descriptor_accounting_request(bridge, owner, tokens[4].category, 1, 3))
    bridge.issue_acknowledgment()
    with bridge.writer_activity(tokens[4], sequence=0):
        os.write(fds[4], b"yy")
    before = bridge.snapshot
    payload = _descriptor_accounting_request(bridge, owner, tokens[1].category, 1, extra, 1)
    if not accepted:
        with pytest.raises(CanonicalControlError, match="RESOURCE_LIMIT_EXCEEDED"):
            bridge.prepare_request(tokens[1], payload)
        assert bridge.snapshot.charged_bytes == before.charged_bytes
        assert bridge.snapshot.reserved_bytes == before.reserved_bytes
        assert bridge.snapshot.expected_sequence == 1
    else:
        bridge.prepare_request(tokens[1], payload)
        assert bridge.snapshot.charged_bytes == before.charged_bytes
        ack = bridge._wire.parse_reservation_payload(bridge.issue_acknowledgment())
        assert ack["resulting_charged_bytes"] == 7
        assert ack["resulting_reserved_bytes"] == 15
        assert bridge.snapshot.expected_sequence == 2


@pytest.mark.parametrize("fault", ["growth", "cross_category", "recreated", "closed", "substituted"])
def test_descriptor_accounting_admission_stale_prepare(descriptor_accounting_case, fault):
    owner, bridge, fds, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    before = bridge.snapshot
    if fault == "growth":
        os.write(fds[1], b"x"*11)
    elif fault == "cross_category":
        os.write(fds[4], b"x")
    elif fault == "closed":
        os.close(fds[1])
    elif fault == "substituted":
        os.dup2(fds[4], fds[1])
    else:
        path = descriptor_accounting_case[2] / ".orev3-bounded-streaming-v1" / "operations" / owner.operation_id / "controller/nested/object-1"
        path.unlink()
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
    with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
        bridge.issue_acknowledgment()
    assert bridge.snapshot.charged_bytes == before.charged_bytes
    assert bridge.snapshot.reserved_bytes == before.reserved_bytes
    assert bridge.snapshot.expected_sequence == 0


@pytest.mark.parametrize("action", ["write", "dup2", "close", "binding", "root_close", "recovery", "competing", "writer"])
@pytest.mark.parametrize("swallow", [False, True])
def test_descriptor_accounting_admission_callback_mutation(descriptor_accounting_case, monkeypatch, action, swallow):
    owner, bridge, fds, tokens = _admission_objects(descriptor_accounting_case)
    ns = descriptor_accounting_case[1]
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    original = bridge._sample
    attempted = False
    def sample():
        nonlocal attempted
        result = original()
        attempted = True
        try:
            if action in ("write", "dup2", "close"):
                with bridge.controller_mutation():
                    if action == "write": os.write(fds[1], b"x"*11)
                    elif action == "dup2": os.dup2(fds[4], fds[1])
                    else: os.close(fds[1])
            elif action == "binding":
                bridge.bind_created(fds[1], operation_id=owner.operation_id,
                                    creation_role="worker_output", producer="worker")
            elif action == "root_close": owner.close()
            elif action == "recovery": ns.recover()
            elif action == "writer":
                with bridge.writer_activity(tokens[1], sequence=0): pass
            else: bridge.observe(tokens[1].category)
        except CanonicalControlError:
            if not swallow: raise
        return result
    with monkeypatch.context() as patch:
        patch.setattr(bridge, "_sample", sample)
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            bridge.issue_acknowledgment()
    assert attempted and bridge.snapshot.expected_sequence == 0
    assert sum(bridge.snapshot.reserved_bytes) == 0
    assert os.fstat(fds[1]).st_ino == tokens[1].identity[1]
    assert os.fstat(fds[1]).st_size == 0
    assert os.fstat(owner.lease_descriptor).st_size == 0
    assert not ns._busy and not bridge._busy


@pytest.mark.parametrize("stage", ["before_ack", "waiting_again", "active", "replay", "wrong_sequence"])
def test_descriptor_accounting_admission_writer_lifecycle(descriptor_accounting_case, stage):
    owner, bridge, fds, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=20)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    if stage != "before_ack":
        bridge.issue_acknowledgment()
    if stage in ("waiting_again", "replay"):
        with bridge.writer_activity(tokens[1], sequence=0):
            os.write(fds[1], b"abc")
    if stage == "waiting_again":
        bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 3, 1, 1))
    if stage == "active":
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            with bridge.writer_activity(tokens[1], sequence=0):
                bridge.prepare_request(tokens[2], _descriptor_accounting_request(bridge, owner, tokens[2].category, 0, 1, 1))
    else:
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            with bridge.writer_activity(tokens[1], sequence=1 if stage == "wrong_sequence" else 0):
                pytest.fail("unavailable/old allowance became active")
    assert bridge.snapshot.expected_sequence == (0 if stage == "before_ack" else 1)


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("point", ["_charged", "_reserved", "_pending", "_sequence", "publish_before", "publish_after"])
def test_descriptor_accounting_admission_atomic_publication(descriptor_accounting_case, exception, point):
    import dis
    runtime, ns, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/a")
    token = bind(fd, "controller_temporary")
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 10))
    if point.startswith("publish"):
        code = runtime.ControllerDescriptorAccounting._publish.__code__
        instructions = list(dis.get_instructions(code))
        index = next(i for i,x in enumerate(instructions) if x.opname.startswith("CALL"))
        offsets = {instructions[index + (point == "publish_after")].offset}
    else:
        code = runtime.ControllerReservationSession.issue_acknowledgment.__wrapped__.__code__
        offsets = {x.offset for x in dis.get_instructions(code) if x.opname == "STORE_ATTR" and x.argval == point}
    hit = False
    observed = []
    def trace(frame, event, arg):
        nonlocal hit
        if frame.f_code is code:
            frame.f_trace_opcodes = True
            observed.append((sum(bridge.snapshot.reserved_bytes), bridge.snapshot.expected_sequence))
            if event == "opcode" and frame.f_lasti in offsets and not hit:
                hit = True
                raise exception()
        return trace
    sys.settrace(trace)
    try:
        with pytest.raises(exception):
            bridge.issue_acknowledgment()
    finally:
        sys.settrace(None)
    assert hit and set(observed) <= {(0, 0), (10, 1)}
    assert (sum(bridge.snapshot.reserved_bytes), bridge.snapshot.expected_sequence) == (
        (10, 1) if point == "publish_after" else (0, 0))
    if point == "publish_after":
        ack = bridge._wire.parse_reservation_payload(bridge._state.acknowledgment)
        assert (ack["sequence_number"], ack["resulting_reserved_bytes"]) == (0, 10)
    else:
        assert bridge._state.acknowledgment is None
    assert bridge.snapshot.terminal and not ns._busy and not bridge._busy, (bridge._failed, ns._busy, bridge._busy, runtime._CONTROLLER_INTERVAL.current)
    assert os.fstat(fd).st_size == 0 and os.fstat(owner.lease_descriptor).st_size == 0


@pytest.mark.parametrize("where", ["observation", "ack"])
@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, RuntimeError])
def test_descriptor_accounting_admission_precommit_failure(descriptor_accounting_case, monkeypatch, where, exception):
    owner, bridge, _, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    def fail(*a, **kw): raise exception("injected")
    with monkeypatch.context() as patch:
        if where == "observation": patch.setattr(bridge, "_sample", fail)
        else: patch.setattr(bridge._wire, "reservation_payload", fail)
        with pytest.raises(CanonicalControlError if exception is RuntimeError else exception):
            bridge.issue_acknowledgment()
    assert bridge.snapshot.expected_sequence == 0
    assert sum(bridge.snapshot.charged_bytes) == sum(bridge.snapshot.reserved_bytes) == 0
    assert bridge.snapshot.terminal


@pytest.mark.parametrize("after", [False, True])
def test_descriptor_accounting_admission_orderly_teardown_finality(descriptor_accounting_case, monkeypatch, after):
    runtime, ns, _, owner, bridge, create, bind = descriptor_accounting_case
    fd, _ = create("controller/a")
    token = bind(fd, "controller_temporary")
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(token, _descriptor_accounting_request(bridge, owner, token.category, 0, 10))
    bridge.issue_acknowledgment()
    with bridge.writer_activity(token, sequence=0): os.write(fd, b"abc")
    real_close = os.close
    armed = not after
    injected = False
    def trace(frame, event, arg):
        nonlocal armed
        if frame.f_code.co_name == "orderly_eof" and isinstance(frame.f_locals.get("self"), runtime.ControllerReservationSession) and event == "return":
            armed = True
        return trace
    def close(descriptor):
        nonlocal injected
        real_close(descriptor)
        if armed and not injected:
            injected = True
            raise InterruptedError(4, "already closed")
    with monkeypatch.context() as patch:
        patch.setattr(os, "close", close)
        sys.settrace(trace)
        try:
            with pytest.raises(CanonicalControlError):
                bridge.orderly_eof()
        finally:
            sys.settrace(None)
    assert injected and sum(bridge.snapshot.reserved_bytes) == (3 if after else 10)
    assert bridge.snapshot.uncertain is (not after)
    assert bridge._failed and not ns._busy
    assert os.fstat(owner.lease_descriptor).st_size == 0



@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit])
def test_descriptor_accounting_admission_interrupted_gate_acquire(exception):
    import dis
    from orev3.execution import runtime
    gate = runtime._ControllerInterval()
    code = gate.enter.__wrapped__.__code__
    instructions = list(dis.get_instructions(code))
    index = next(i for i,x in enumerate(instructions) if x.opname == "LOAD_ATTR" and x.argval == "acquire")
    call = next(i for i in range(index, len(instructions)) if instructions[i].opname.startswith("CALL"))
    offset = instructions[call+1].offset
    hit = False
    def trace(frame, event, arg):
        nonlocal hit
        if frame.f_code is code:
            frame.f_trace_opcodes = True
            if event == "opcode" and frame.f_lasti == offset and not hit:
                hit = True
                raise exception()
        return trace
    sys.settrace(trace)
    try:
        with pytest.raises(exception):
            with gate.enter(): pytest.fail("interrupted acquire entered")
    finally: sys.settrace(None)
    assert hit and gate.current is None and not gate.lock._is_owned()
    with gate.enter() as token: gate.check(token)


def test_descriptor_accounting_admission_concurrent_authorized_mutator(descriptor_accounting_case, monkeypatch):
    import threading
    owner, bridge, fds, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    original = bridge._sample
    failures = []
    def mutate():
        try:
            with bridge.controller_mutation(): os.write(fds[1], b"x")
        except CanonicalControlError as error: failures.append(str(error))
    def sample():
        result = original()
        thread = threading.Thread(target=mutate)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
        return result
    with monkeypatch.context() as patch:
        patch.setattr(bridge, "_sample", sample)
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            bridge.issue_acknowledgment()
    assert failures == ["DISK_RESERVATION_STATE_MISMATCH"]
    assert os.fstat(fds[1]).st_size == 0 and bridge.snapshot.expected_sequence == 0


@pytest.mark.parametrize("action", ["write", "dup2", "binding", "teardown", "competing", "multiple"])
@pytest.mark.parametrize("boundary", ["entry", "before", "after", "every_pre_opcode"])
def test_descriptor_accounting_admission_finality_invalidation(descriptor_accounting_case, action, boundary):
    import dis
    runtime, ns, _, owner, bridge, _, _ = descriptor_accounting_case
    _, _, fds, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    previous = bridge.snapshot
    bindings = dict(bridge._state.bindings)
    identities = [os.fstat(fd) for fd in fds]
    code = runtime.ControllerDescriptorAccounting._publish.__code__
    instructions = list(dis.get_instructions(code))
    index = next(i for i, item in enumerate(instructions) if item.opname.startswith("CALL"))
    before, after = instructions[index].offset, instructions[index + 1].offset
    attempts = []

    def attempt(kind):
        # Every entry is an authorized modeled path; never bypass the gate.
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            if kind in ("write", "dup2"):
                with bridge.controller_mutation():
                    if kind == "write": os.write(fds[1], b"unreserved")
                    else: os.dup2(fds[4], fds[1])
            elif kind == "binding":
                bridge.bind_created(fds[1], operation_id=owner.operation_id,
                                    creation_role="worker_output", producer="worker")
            elif kind == "teardown": owner.close()
            else: bridge.issue_acknowledgment()
        attempts.append(kind)  # Deliberately swallow the rejection.

    def trace(frame, event, arg):
        if frame.f_code is code:
            frame.f_trace_opcodes = True
            selected = ((boundary == "entry" and event == "call")
                or (event == "opcode" and (
                    (boundary == "before" and frame.f_lasti == before)
                    or (boundary == "after" and frame.f_lasti == after)
                    or (boundary == "every_pre_opcode" and frame.f_lasti <= before))))
            if selected:
                for kind in (("write", "dup2", "binding", "teardown", "competing")
                             if action == "multiple" else (action,)):
                    attempt(kind)
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            bridge.issue_acknowledgment()
    finally:
        sys.settrace(None)
    assert attempts
    state = bridge.snapshot
    assert state.charged_bytes == previous.charged_bytes
    if boundary == "after":
        assert sum(state.reserved_bytes) == 10 and state.expected_sequence == 1
        ack = bridge._wire.parse_reservation_payload(bridge._state.acknowledgment)
        assert (ack["sequence_number"], ack["resulting_reserved_bytes"]) == (0, 10)
    else:
        assert state.reserved_bytes == previous.reserved_bytes
        assert state.expected_sequence == previous.expected_sequence == 0
        assert bridge._state.acknowledgment is None
    assert dict(bridge._state.bindings) == bindings
    assert state.terminal and bridge._failed
    assert not ns._busy and not bridge._busy and runtime._CONTROLLER_INTERVAL.current is None
    for fd, identity in zip(fds, identities):
        actual = os.fstat(fd)
        assert (actual.st_dev, actual.st_ino, actual.st_size) == (identity.st_dev, identity.st_ino, 0)
    assert os.fstat(owner.lease_descriptor).st_size == 0
    assert ns.recover().live_operations == (owner.operation_id,)


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("boundary", ["entry", "before", "after"])
def test_descriptor_accounting_admission_finality_interruption(descriptor_accounting_case, exception, boundary):
    import dis
    runtime, ns, _, owner, bridge, _, _ = descriptor_accounting_case
    _, _, _, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    code = runtime.ControllerDescriptorAccounting._publish.__code__
    instructions = list(dis.get_instructions(code))
    index = next(i for i, item in enumerate(instructions) if item.opname.startswith("CALL"))
    offset = instructions[index + (boundary == "after")].offset
    hit = False
    def trace(frame, event, arg):
        nonlocal hit
        if frame.f_code is code:
            frame.f_trace_opcodes = True
            if ((boundary == "entry" and event == "call") or
                    (boundary != "entry" and event == "opcode" and frame.f_lasti == offset)):
                hit = True
                raise exception()
        return trace
    sys.settrace(trace)
    try:
        with pytest.raises(exception): bridge.issue_acknowledgment()
    finally:
        sys.settrace(None)
    assert hit
    assert (sum(bridge.snapshot.reserved_bytes), bridge.snapshot.expected_sequence) == (
        (10, 1) if boundary == "after" else (0, 0))
    if boundary == "after":
        ack = bridge._wire.parse_reservation_payload(bridge._state.acknowledgment)
        assert (ack["sequence_number"], ack["resulting_reserved_bytes"]) == (0, 10)
    else: assert bridge._state.acknowledgment is None
    assert bridge.snapshot.terminal and not bridge._busy and not ns._busy


def test_descriptor_accounting_admission_finality_valid(descriptor_accounting_case):
    owner, bridge, _, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    payload = bridge.issue_acknowledgment()
    assert payload == bridge._state.acknowledgment
    ack = bridge._wire.parse_reservation_payload(payload)
    assert (ack["sequence_number"], ack["resulting_reserved_bytes"]) == (0, 10)
    assert bridge.snapshot.expected_sequence == 1
    assert sum(bridge.snapshot.reserved_bytes) == 10


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("point", ["owner", "busy_before", "busy_after", "state", "stage", "flock_before", "flock_after"])
def test_descriptor_accounting_entry_safety_boundaries(descriptor_accounting_case, monkeypatch, exception, point):
    import dis
    runtime, ns, anchor, owner, bridge, _, _ = descriptor_accounting_case
    _, _, _, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    payload = _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10)
    previous = bridge.snapshot
    code = (runtime._ControllerInterval.enter.__wrapped__.__code__ if point == "owner"
            else runtime.ControllerDescriptorAccounting._locked.__wrapped__.__code__)
    instructions = list(dis.get_instructions(code))
    attribute = "current" if point == "owner" else "_busy"
    index = next(i for i, x in enumerate(instructions) if x.opname == "STORE_ATTR" and x.argval == attribute)
    offset = instructions[index + (point != "busy_before")].offset
    hit = False
    def interrupt():
        nonlocal hit
        hit = True
        raise exception("entry interrupted")
    def trace(frame, event, arg):
        if hit: return trace
        if point in ("owner", "busy_before", "busy_after") and frame.f_code is code:
            frame.f_trace_opcodes = True
            if event == "opcode" and frame.f_lasti == offset: interrupt()
        if (point == "state" and frame.f_code is runtime.ControllerDescriptorAccounting._state.fget.__code__
                and event == "call" and frame.f_locals.get("self") is bridge and bridge._busy): interrupt()
        return trace
    real_flock = runtime.fcntl.flock
    def flock(fd, flags):
        if not hit and flags == runtime.fcntl.LOCK_EX:
            if point == "flock_before": interrupt()
            real_flock(fd, flags)
            if point == "flock_after": interrupt()
        else: real_flock(fd, flags)
    with monkeypatch.context() as patch:
        if point.startswith("flock"): patch.setattr(runtime.fcntl, "flock", flock)
        if point == "stage": patch.setattr(runtime.copy, "copy", lambda *args: interrupt())
        sys.settrace(trace)
        try:
            with pytest.raises(exception, match="entry interrupted"):
                bridge.prepare_request(tokens[1], payload)
        finally: sys.settrace(None)
    assert hit and not bridge._busy and not ns._busy
    assert runtime._CONTROLLER_INTERVAL.current is None
    assert not runtime._CONTROLLER_INTERVAL.lock._is_owned()
    assert bridge.snapshot.charged_bytes == previous.charged_bytes
    assert bridge.snapshot.reserved_bytes == previous.reserved_bytes
    assert bridge.snapshot.expected_sequence == previous.expected_sequence == 0
    if bridge._failed:
        with pytest.raises(bridge._wire.ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
            with bridge.controller_mutation(): pytest.fail("quarantined mutation")
        with pytest.raises(bridge._wire.ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
            bridge.prepare_request(tokens[1], payload)
    else:
        # Interruption before bridge entry leaves a clean, usable owner.
        with bridge.controller_mutation(): pass
        bridge.prepare_request(tokens[1], payload)
        bridge.issue_acknowledgment()
        assert bridge.snapshot.expected_sequence == 1
    assert runtime.ControllerOperationNamespace(anchor).recover().live_operations == (owner.operation_id,)


def test_descriptor_accounting_entry_safety_multiple_cleanup_failures(descriptor_accounting_case, monkeypatch):
    runtime, ns, anchor, owner, bridge, _, _ = descriptor_accounting_case
    _, _, _, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    real_flock, real_close = runtime.fcntl.flock, os.close
    armed = False
    closed = []
    def flock(fd, flags):
        nonlocal armed
        real_flock(fd, flags)
        if flags == runtime.fcntl.LOCK_EX:
            armed = True
            raise KeyboardInterrupt("after coordination acquisition")
    def close(fd):
        real_close(fd)
        if armed:
            closed.append(fd)
            if len(closed) <= 2: raise InterruptedError("actually closed")
    with monkeypatch.context() as patch:
        patch.setattr(runtime.fcntl, "flock", flock)
        patch.setattr(os, "close", close)
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    assert len(closed) >= 3 and len(closed) == len(set(closed))
    assert len(ns._descriptors.unresolved) == 2
    assert bridge._failed and not bridge._busy and not ns._busy
    assert runtime._CONTROLLER_INTERVAL.current is None
    assert sum(bridge.snapshot.reserved_bytes) == 0 and bridge.snapshot.expected_sequence == 0
    with pytest.raises(bridge._wire.ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        with bridge.controller_mutation(): pytest.fail("quarantine bypass")
    assert runtime.ControllerOperationNamespace(anchor).recover().live_operations == (owner.operation_id,)


def test_descriptor_accounting_entry_safety_success(descriptor_accounting_case):
    runtime, ns, _, _, bridge, _, _ = descriptor_accounting_case
    owner, _, _, tokens = _admission_objects(descriptor_accounting_case)
    bridge.start_session(max_temporary_disk_bytes=10)
    bridge.prepare_request(tokens[1], _descriptor_accounting_request(bridge, owner, tokens[1].category, 0, 10))
    bridge.issue_acknowledgment()
    assert not bridge._busy and not bridge._failed and not ns._busy
    assert runtime._CONTROLLER_INTERVAL.current is None
    assert bridge.snapshot.expected_sequence == 1 and sum(bridge.snapshot.reserved_bytes) == 10
    with bridge.controller_mutation(): pass


def test_operation_recovery_two_controllers_live_orphan_and_publication_separation(tmp_path):
    runtime, first, anchor, operations = _operation_fixture(tmp_path)
    published = anchor / ("e" * 64)
    published.write_bytes(b"published")
    published.chmod(0o444)
    second = runtime.ControllerOperationNamespace(anchor)
    live = first.create_operation()
    try:
        name = _operation_orphan(second, operations)
        result = first.recover()
        assert result.recovered_operations == (name,)
        assert result.live_operations == (live.operation_id,)
        assert result.inventoried_logical_bytes == 10
        assert set(p.name for p in operations.iterdir()) == {live.operation_id}
        assert published.read_bytes() == b"published"
        assert published.stat().st_mode & 0o7777 == 0o444
        assert os.fstat(live.lease_descriptor).st_mode & 0o7777 == 0o600
        for role in ("controller", "worker", "snapshot-publication", "reconstruction"):
            assert os.fstat(live.category_directory_descriptor(role)).st_mode & 0o7777 == 0o700
        with pytest.raises(runtime.CanonicalControlError):
            live.category_directory_descriptor("../operations")
    finally:
        live.close()
    second.recover()
    assert first.recover().recovered_operations == ()


@pytest.mark.parametrize("target", ("anchor", "coordination", "operations", "lock", "root", "lease", "worker", "payload"))
@pytest.mark.parametrize("bad_mode", (0o000, 0o400, 0o444, 0o755, 0o1600))
def test_operation_recovery_exact_modes_reject_before_deletion(tmp_path, target, bad_mode):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    paths = {"anchor": anchor, "coordination": operations.parent, "operations": operations,
             "lock": operations.parent / "coordination.lock", "root": operations / name,
             "lease": operations / name / "lease", "worker": operations / name / "worker",
             "payload": operations / name / "worker" / "nested" / "part"}
    path = paths[target]
    original = path.stat().st_mode & 0o7777
    path.chmod(bad_mode)
    try:
        with pytest.raises(runtime.CanonicalControlError):
            owner.recover()
    finally:
        path.chmod(original)  # Fixture teardown only; production never normalizes.
    assert (operations / name / "worker" / "nested" / "part").read_bytes() == b"abc"


@pytest.mark.parametrize("target", ("anchor", "coordination", "operations", "lock", "root", "lease", "worker", "payload"))
def test_operation_recovery_uid_mismatch(tmp_path, monkeypatch, target):
    from types import SimpleNamespace
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    paths = {"anchor": anchor, "coordination": operations.parent, "operations": operations,
             "lock": operations.parent / "coordination.lock", "root": operations / name,
             "lease": operations / name / "lease", "worker": operations / name / "worker",
             "payload": operations / name / "worker" / "nested" / "part"}
    inode = paths[target].stat().st_ino
    original = os.fstat
    def changed(fd):
        value = original(fd)
        if value.st_ino != inode:
            return value
        fields = {key: getattr(value, key) for key in dir(value) if key.startswith("st_")}
        return SimpleNamespace(**{**fields, "st_uid": value.st_uid + 1})
    with monkeypatch.context() as patch:
        patch.setattr(runtime.os, "fstat", changed)
        with pytest.raises(runtime.CanonicalControlError):
            owner.recover()
    assert (operations / name).exists()


@pytest.mark.parametrize("bad", ("symlink", "hardlink", "fifo", "unexpected-root-file", "wrong-root-directory", "missing-lease", "nonempty-lease", "lease-directory", "lease-symlink"))
def test_operation_recovery_unsafe_inventory_is_not_repaired(tmp_path, bad):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    root = operations / name
    outside = tmp_path / "outside"
    outside.write_bytes(b"untouched")
    if bad == "symlink": (root / "worker" / "bad").symlink_to(outside)
    elif bad == "hardlink": os.link(root / "worker" / "nested" / "part", root / "controller" / "alias")
    elif bad == "fifo": os.mkfifo(root / "worker" / "fifo", 0o600)
    elif bad == "unexpected-root-file": _operation_file(root / "surprise")
    elif bad == "wrong-root-directory": (root / "extra").mkdir(mode=0o700)
    elif bad == "nonempty-lease": (root / "lease").write_bytes(b"pid=1")
    else:
        (root / "lease").unlink()
        if bad == "lease-directory": (root / "lease").mkdir(mode=0o700)
        if bad == "lease-symlink": (root / "lease").symlink_to(outside)
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert (root / "worker" / "nested" / "part").read_bytes() == b"abc"
    assert outside.read_bytes() == b"untouched"


def test_operation_recovery_partial_ordinary_requires_lease(tmp_path):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations, False)
    for path in (operations / name).iterdir():
        if path.is_dir(): path.rmdir()
    assert owner.recover().recovered_operations == (name,)
    root = operations / ("op-" + "1" * 32)
    root.mkdir(mode=0o700)
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert root.exists()


@pytest.mark.parametrize("state,bad", [(state, bad) for state in ("T1", "T2")
    for bad in (None, "extra", "mode", "conflict", "name", "symlink", "uid", "lease-mode", "lease-contention")
    if not (state == "T2" and bad in {"lease-mode", "lease-contention"})])
def test_operation_recovery_terminal_restart_predicate(tmp_path, monkeypatch, state, bad):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    root = operations / ("cleanup-" + "2" * 32)
    root.mkdir(mode=0o700)  # Synthetic persisted-state injection, not an API for promotion.
    if state == "T1": _operation_file(root / "lease")
    held = None
    if bad == "extra": _operation_file(root / "payload")
    if bad == "mode": root.chmod(0o755)
    if bad == "conflict": (operations / ("op-" + "2" * 32)).mkdir(mode=0o700)
    if bad == "name": root.rename(operations / "cleanup-NONCANONICAL")
    if bad == "symlink":
        root.rename(tmp_path / "terminal-outside");root.symlink_to(tmp_path / "terminal-outside", target_is_directory=True)
    if bad == "lease-mode": (root / "lease").chmod(0o400)
    if bad == "lease-contention":
        held = os.open(root / "lease", os.O_RDONLY)
        runtime.fcntl.flock(held, runtime.fcntl.LOCK_EX | runtime.fcntl.LOCK_NB)
    try:
        with monkeypatch.context() as patch:
            if bad == "uid":
                from types import SimpleNamespace
                terminal_inode = root.stat().st_ino
                original_stat = os.fstat
                def wrong_terminal_uid(fd):
                    value = original_stat(fd)
                    if value.st_ino != terminal_inode: return value
                    fields = {key: getattr(value, key) for key in dir(value) if key.startswith("st_")}
                    return SimpleNamespace(**{**fields, "st_uid": value.st_uid + 1})
                patch.setattr(runtime.os, "fstat", wrong_terminal_uid)
            if bad is None:
                assert owner.recover().recovered_operations == ("op-" + "2" * 32,)
                assert not list(operations.iterdir())
            else:
                before = set(operations.iterdir())
                with pytest.raises(runtime.CanonicalControlError): owner.recover()
                assert set(operations.iterdir()) == before
    finally:
        if held is not None: os.close(held)


def test_operation_recovery_rng_failure_and_no_public_id_or_worker_factory(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    original = runtime._OPERATION_TOKEN_HEX
    def broken(count): raise OSError("entropy unavailable")
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "_OPERATION_TOKEN_HEX", broken)
        patch.setattr(runtime.secrets, "token_hex", broken)
        with pytest.raises(runtime.CanonicalControlError, match="DISK_OPERATION_IDENTIFIER_GENERATION_FAILED"):
            owner.create_operation()
    with monkeypatch.context() as patch:
        patch.setattr(runtime.secrets, "token_hex", lambda count: "0" * 32)
        with pytest.raises(runtime.CanonicalControlError, match="DISK_OPERATION_IDENTIFIER_GENERATION_FAILED"):
            owner.create_operation()
    assert runtime._OPERATION_TOKEN_HEX is original
    with pytest.raises(TypeError): owner.create_operation(operation_id="op-" + "a" * 32)
    assert not hasattr(ReservationAllowance(_RESERVATION_OP), "create_operation")
    assert not hasattr(owner, "promote")
    assert not list(operations.iterdir())


@pytest.mark.parametrize("collisions", (1, 127, 128))
def test_operation_recovery_exact_collision_boundary(tmp_path, monkeypatch, collisions):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    live = owner.create_operation()
    calls = []
    def tokens():
        calls.append(None)
        return live.operation_id[3:] if len(calls) <= collisions else "f" * 32
    try:
        with monkeypatch.context() as patch:
            patch.setattr(runtime, "_operation_suffix", tokens)  # Synthetic CSPRNG fixture only.
            if collisions == 128:
                with pytest.raises(runtime.CanonicalControlError, match="RESOURCE_LIMIT_EXCEEDED"):
                    owner.create_operation()
                assert len(calls) == 128
            else:
                handle = owner.create_operation()
                assert handle.operation_id == "op-" + "f" * 32
                assert len(calls) == collisions + 1
                handle.close()
        assert (operations / live.operation_id / "lease").exists()
    finally: live.close()


@pytest.mark.parametrize("total,size", (((1 << 64) - 1, 1), (0, 1 << 64), (0, -1), (0, True)))
def test_operation_recovery_checked_logical_arithmetic(total, size):
    import orev3.execution.runtime as runtime
    assert runtime._recovery_size_add(0, (1 << 64) - 1) == (1 << 64) - 1
    with pytest.raises(runtime.CanonicalControlError): runtime._recovery_size_add(total, size)


@pytest.mark.parametrize("call", ("fsync", "unlink", "rmdir", "promotion"))
def test_operation_recovery_every_observed_crash_boundary_restarts(tmp_path, monkeypatch, call):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    # First measure the real transition calls, then interrupt before/after each.
    def exercise(fail_index=None, after=False):
        name = _operation_orphan(owner, operations)
        original = runtime._rename_operation_exclusive if call == "promotion" else getattr(runtime.os, call)
        count = 0
        def intercepted(*args, **kwargs):
            nonlocal count
            count += 1
            if count == fail_index and not after: raise OSError("synthetic interruption")
            result = original(*args, **kwargs)
            if count == fail_index and after: raise OSError("synthetic interruption")
            return result
        with monkeypatch.context() as patch:
            if call == "promotion": patch.setattr(runtime, "_rename_operation_exclusive", intercepted)
            else: patch.setattr(runtime.os, call, intercepted)
            if fail_index is None: owner.recover()
            else:
                with pytest.raises(runtime.CanonicalControlError): owner.recover()
        # Fresh owner: no in-memory lease/proof survives the failed call.
        restarted = runtime.ControllerOperationNamespace(anchor)
        restarted.recover()
        assert not list(operations.iterdir())
        assert restarted.recover().recovered_operations == ()
        return count
    count = exercise()
    for index in range(1, count + 1):
        for after in (False, True): exercise(index, after)


def test_operation_recovery_promotion_collision_never_replaces(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    destination = operations / ("cleanup-" + name[3:])
    original = runtime._rename_operation_exclusive
    def collide(fd, source, target):
        destination.mkdir(mode=0o700)
        _operation_file(destination / "sentinel", b"keep")
        return original(fd, source, target)
    monkeypatch.setattr(runtime, "_rename_operation_exclusive", collide)
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert (destination / "sentinel").read_bytes() == b"keep"
    assert (operations / name / "lease").exists()


def test_operation_recovery_final_recheck_refuses_new_unresolved_state(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    original = os.rmdir
    def changed(path, *, dir_fd=None):
        result = original(path, dir_fd=dir_fd)
        if str(path).startswith("cleanup-"):
            os.mkdir("op-" + "b" * 32, mode=0o700, dir_fd=dir_fd)
        return result
    with monkeypatch.context() as patch:
        patch.setattr(runtime.os, "rmdir", changed)
        with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert not (operations / name).exists()
    assert (operations / ("op-" + "b" * 32)).exists()


def test_operation_recovery_readonly_structure_and_traversal_rejected(tmp_path):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    with pytest.raises(runtime.CanonicalControlError):
        runtime.ControllerOperationNamespace(anchor / ".." / "private-store").recover()
    alias = tmp_path / "alias"
    alias.symlink_to(anchor, target_is_directory=True)
    with pytest.raises(runtime.CanonicalControlError): runtime.ControllerOperationNamespace(alias).recover()
    _operation_file(operations.parent / "unexpected")
    with pytest.raises(runtime.CanonicalControlError): owner.recover()


def test_operation_recovery_coordination_contention_and_exception_release(tmp_path):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    script = """import os,sys,fcntl
fd=os.open(sys.argv[1],os.O_RDONLY)
try:
 try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError: print('contended')
 else: print('acquired')
finally: os.close(fd)
"""
    def contender():
        result = subprocess.run([sys.executable, "-B", "-c", script, str(operations.parent / "coordination.lock")],
                                capture_output=True, text=True, check=True, timeout=10)
        return result.stdout.strip()
    with pytest.raises(RuntimeError):
        with owner._locked():
            assert contender() == "contended"
            raise RuntimeError("synthetic controller failure")
    assert contender() == "acquired"
    assert runtime.ControllerOperationNamespace(anchor).recover().live_operations == ()
    assert owner.recover().live_operations == ()


@pytest.mark.parametrize("which", ("coordination", "operations", "lock", "ordinary"))
@pytest.mark.parametrize("kind", ("file", "symlink"))
def test_operation_recovery_structural_wrong_type(tmp_path, which, kind):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    if which == "ordinary":
        path = operations / ("op-" + "3" * 32)
    elif which == "lock":
        path = operations.parent / "coordination.lock"
        path.unlink()
    elif which == "operations":
        path = operations
        path.rmdir()
    else:
        path = operations.parent
        operations.rmdir(); (path / "coordination.lock").unlink(); path.rmdir()
    if kind == "symlink": path.symlink_to(tmp_path, target_is_directory=True)
    elif which == "lock": path.mkdir(mode=0o700)
    else: _operation_file(path)
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert path.exists()


def test_operation_recovery_missing_lock_cannot_replace_authority(tmp_path):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    lock = operations.parent / "coordination.lock"
    lock.unlink()
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert not lock.exists()
    assert (operations / name / "lease").exists()


@pytest.mark.parametrize("phase", ("coordination", "lease"))
def test_operation_recovery_lock_errors_are_not_liveness(tmp_path, monkeypatch, phase):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    original = runtime.fcntl.flock
    def broken(fd, flags):
        if bool(flags & runtime.fcntl.LOCK_NB) == (phase == "lease"):
            raise OSError("not contention")
        return original(fd, flags)
    with monkeypatch.context() as patch:
        patch.setattr(runtime.fcntl, "flock", broken)
        with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert (operations / name / "worker" / "nested" / "part").exists()
    owner.recover()


def test_operation_recovery_uid_change_during_pass_rejects(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    uid = os.geteuid()
    original = owner._inventory
    def inventory(*args):
        result = original(*args)
        monkeypatch.setattr(runtime.os, "geteuid", lambda: uid + 1)
        return result
    monkeypatch.setattr(owner, "_inventory", inventory)
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert (operations / name / "worker" / "nested" / "part").exists()


@pytest.mark.parametrize("substitute", ("root", "payload", "lease", "operations"))
def test_operation_recovery_inventory_to_cleanup_substitution(tmp_path, monkeypatch, substitute):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    root = operations / name
    original = owner._inventory
    target = {"root": root, "payload": root / "worker" / "nested" / "part",
              "lease": root / "lease", "operations": operations}[substitute]
    def inventory(*args):
        result = original(*args)
        moved = tmp_path / "pinned-original"
        target.rename(moved)
        if substitute in {"root", "operations"}:
            target.mkdir(mode=0o700)
            _operation_file(target / "sentinel", b"unrelated")
        else: _operation_file(target, b"unrelated")
        return result
    monkeypatch.setattr(owner, "_inventory", inventory)
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    if substitute in {"root", "operations"}: assert (target / "sentinel").read_bytes() == b"unrelated"
    else: assert target.read_bytes() == b"unrelated"


def test_operation_recovery_duplicate_identity_and_inventory_overflow_before_delete(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    root = operations / name
    # Model an identity already encountered in another root in this recovery pass.
    with owner._locked():
        pinned = owner._open(owner._operations, name, True)
        lease, acquired = owner._lease(pinned)
        assert acquired
        with pytest.raises(runtime.CanonicalControlError):
            owner._inventory(pinned, lease, {(pinned.opened.st_dev, pinned.opened.st_ino)})
    original = runtime._recovery_size_add
    def overflow(total, size):
        return original((1 << 64) - 1, size) if size else original(total, size)
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "_recovery_size_add", overflow)
        with pytest.raises(runtime.CanonicalControlError, match="RESOURCE_LIMIT_EXCEEDED"):
            owner.recover()
    assert (root / "worker" / "nested" / "part").exists()


def test_operation_recovery_parent_sync_precedes_terminal_lease_destruction(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    root = operations / ("cleanup-" + "4" * 32)
    root.mkdir(mode=0o700); _operation_file(root / "lease")
    original = os.fsync
    root_synced = False
    def failure(fd):
        nonlocal root_synced
        inode = os.fstat(fd).st_ino
        if inode == root.stat().st_ino: root_synced = True
        if root_synced and inode == operations.stat().st_ino: raise OSError("parent durability failed")
        return original(fd)
    with monkeypatch.context() as patch:
        patch.setattr(runtime.os, "fsync", failure)
        with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert (root / "lease").exists()
    owner.recover()
    assert not root.exists()


def test_operation_recovery_initialization_failure_is_not_terminal_authority(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    def failure(root): raise OSError("before lease creation")
    with monkeypatch.context() as patch:
        patch.setattr(owner, "_new_lease", failure)
        with pytest.raises(runtime.CanonicalControlError): owner.create_operation()
    roots = list(operations.iterdir())
    assert len(roots) == 1 and roots[0].name.startswith("op-")
    assert not list(roots[0].iterdir())
    with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert list(operations.iterdir()) == roots


def test_operation_recovery_restrictive_umask_mismatch_is_not_normalized(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    original = runtime.os.mkdir
    created = []
    def masked(name, mode=0o777, *, dir_fd=None):
        # Model umask clearing a requested bit, without changing process umask.
        if str(name).startswith("op-"):
            created.append(name)
            return original(name, mode & ~0o200, dir_fd=dir_fd)
        return original(name, mode, dir_fd=dir_fd)
    with monkeypatch.context() as patch:
        patch.setattr(runtime.os, "mkdir", masked)
        with pytest.raises(runtime.CanonicalControlError): owner.create_operation()
    assert len(created) == 1
    assert (operations / created[0]).stat().st_mode & 0o7777 == 0o500


def test_operation_recovery_creation_sync_failure_never_returns_admission(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    original = os.fsync
    def run(failure=None):
        calls = 0
        def synced(fd):
            nonlocal calls
            calls += 1
            if calls == failure: raise OSError("creation durability failure")
            return original(fd)
        with monkeypatch.context() as patch:
            patch.setattr(runtime.os, "fsync", synced)
            if failure is None:
                handle = owner.create_operation()
                handle.close()
            else:
                with pytest.raises(runtime.CanonicalControlError): owner.create_operation()
        owner.recover()
        assert not list(operations.iterdir())
        return calls
    count = run()
    for step in range(1, count + 1): run(step)


def test_operation_recovery_liveness_rechecked_before_new_admission(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    live = owner.create_operation()
    original = owner._new_lease
    def expire(root):
        result = original(root)
        # Model another holder's process death, not an authorized local close
        # callback (which the admission ownership contract now excludes).
        live._close_owned()
        return result
    with monkeypatch.context() as patch:
        patch.setattr(owner, "_new_lease", expire)
        with pytest.raises(runtime.CanonicalControlError): owner.create_operation()
    assert len(list(operations.iterdir())) == 2
    assert len(owner.recover().recovered_operations) == 2


def test_operation_recovery_unsupported_promotion_has_no_fallback(tmp_path, monkeypatch):
    runtime, owner, anchor, operations = _operation_fixture(tmp_path)
    name = _operation_orphan(owner, operations)
    with monkeypatch.context() as patch:
        patch.setattr(runtime.sys, "platform", "unsupported")
        with pytest.raises(runtime.CanonicalControlError): owner.recover()
    assert set(p.name for p in (operations / name).iterdir()) == {"lease"}
    owner.recover()
    assert not list(operations.iterdir())


# Stage 3C Slice 1: synthetic protocol/state tests, with no operational writes.
_RESERVATION_OP = "op-" + "a" * 32


def _reservation_request(**changes):
    value = {
        "schema_version": 1, "message_type": "reserve_growth",
        "operation_id": _RESERVATION_OP, "sequence_number": 0,
        "reservation_kind": "worker_output_growth",
        "current_logical_bytes": 0, "requested_growth_bytes": 4,
    }
    return {**value, **changes}


def _reservation_ack(**changes):
    return {
        "schema_version": 1, "message_type": "reservation_acknowledged",
        "operation_id": _RESERVATION_OP, "sequence_number": 0,
        "accepted_growth_bytes": 4, "resulting_reserved_bytes": 4,
        "resulting_charged_bytes": 0, **changes,
    }


def _reservation_rejection(**changes):
    return {
        "schema_version": 1, "message_type": "reservation_rejected",
        "operation_id": _RESERVATION_OP, "sequence_number": 0,
        "failure_code": "DISK_RESERVATION_PROTOCOL_REJECTED", **changes,
    }


def _reservation_json(value):
    # Independent test encoder, intentionally does not validate its input.
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _reservation_core(limit=20, **initial):
    observations = {kind: 0 for kind in RESERVATION_KINDS}
    observations.update(initial)
    session = ControllerReservationSession(
        operation_id=_RESERVATION_OP, max_temporary_disk_bytes=limit,
        controller_observe=observations.__getitem__,
    )
    return session, observations


def _reservation_grant(session, **changes):
    session.prepare_request(reservation_payload(_reservation_request(**changes)))
    return session.issue_acknowledgment()


def _reservation_ledger(session):
    value = session.snapshot
    return value.charged_bytes, value.reserved_bytes, value.expected_sequence


@pytest.mark.parametrize("factory", (_reservation_request, _reservation_ack, _reservation_rejection))
def test_reservation_exact_canonical_messages(factory):
    message = factory()
    expected = _reservation_json(message)
    assert reservation_payload(message) == expected
    assert not expected.endswith(b"\n")
    assert parse_reservation_payload(expected) == message
    framed = reservation_frame(message)
    assert framed == len(expected).to_bytes(4, "big") + expected
    assert parse_reservation_frame(framed) == message
    assert read_reservation_frame(io.BytesIO(framed).read) == expected


def test_reservation_maximum_payloads_are_governed_without_lf():
    maximum = RESERVATION_UINT64_MAX
    messages = (
        _reservation_request(
            sequence_number=maximum, reservation_kind="controller_temporary_growth",
            current_logical_bytes=maximum, requested_growth_bytes=maximum,
        ),
        _reservation_ack(
            sequence_number=maximum, accepted_growth_bytes=maximum,
            resulting_reserved_bytes=maximum, resulting_charged_bytes=maximum,
        ),
        _reservation_rejection(sequence_number=maximum),
    )
    assert MAX_RESERVATION_FRAME_BYTES == 294
    assert tuple(len(reservation_payload(value)) for value in messages) == (284, 294, 202)
    assert parse_reservation_frame(reservation_frame(messages[1])) == messages[1]
    with pytest.raises(ReservationProtocolError):
        parse_reservation_payload(reservation_payload(messages[1]) + b"\n")


def test_reservation_minimum_frame_is_not_a_valid_message():
    assert read_reservation_frame(io.BytesIO(b"\0\0\0\x010").read) == b"0"
    with pytest.raises(ReservationProtocolError):
        parse_reservation_frame(b"\0\0\0\x010")


@pytest.mark.parametrize("length", (0, 295, 2**32 - 1))
def test_reservation_bad_length_rejects_before_payload_read(length):
    calls = []
    def read(size):
        calls.append(size)
        assert len(calls) == 1, "invalid declaration must not request a payload"
        return length.to_bytes(4, "big")
    with pytest.raises(ReservationProtocolError):
        read_reservation_frame(read)
    assert calls == [4]


@pytest.mark.parametrize("fragment", (1, 2, 3, 5, 13))
def test_reservation_fragmented_header_and_payload(fragment):
    stream = io.BytesIO(reservation_frame(_reservation_request()))
    calls = []
    def read(size):
        calls.append(size)
        return stream.read(min(size, fragment))
    assert parse_reservation_payload(read_reservation_frame(read)) == _reservation_request()
    assert max(calls) <= MAX_RESERVATION_FRAME_BYTES


@pytest.mark.parametrize("cut", (0, 1, 2, 3, 4, 5, -1))
def test_reservation_truncated_frame(cut):
    framed = reservation_frame(_reservation_request())
    with pytest.raises(ReservationProtocolError, match="^DISK_RESERVATION_PROTOCOL_REJECTED$"):
        read_reservation_frame(io.BytesIO(framed[:cut]).read)


def test_reservation_frame_retries_interrupted_read_and_closes_transport_errors():
    stream = io.BytesIO(reservation_frame(_reservation_request()))
    interrupted = [True]
    def read(size):
        if interrupted and interrupted.pop():
            raise InterruptedError()
        return stream.read(size)
    assert read_reservation_frame(read) == reservation_payload(_reservation_request())
    def broken(_size):
        raise OSError("PRIVATE_TRANSPORT_DETAIL")
    with pytest.raises(ReservationProtocolError, match="^DISK_RESERVATION_PROTOCOL_REJECTED$"):
        read_reservation_frame(broken)


@pytest.mark.parametrize("suffix", (b"\n", b" ", b"\0", reservation_frame(_reservation_request())))
def test_reservation_trailing_or_concatenated_frame_rejected(suffix):
    with pytest.raises(ReservationProtocolError):
        parse_reservation_frame(reservation_frame(_reservation_request()) + suffix)


def test_reservation_wrong_endianness_and_reader_overdelivery_reject():
    payload = reservation_payload(_reservation_request())
    with pytest.raises(ReservationProtocolError):
        read_reservation_frame(io.BytesIO(len(payload).to_bytes(4, "little") + payload).read)
    with pytest.raises(ReservationProtocolError):
        read_reservation_frame(lambda size: b"x" * (size + 1))


@pytest.mark.parametrize("field,value", (
    ("schema_version", True), ("schema_version", 2),
    ("sequence_number", True), ("sequence_number", -1),
    ("sequence_number", RESERVATION_UINT64_MAX + 1),
    ("sequence_number", 0.0), ("sequence_number", float("inf")),
    ("sequence_number", float("nan")), ("sequence_number", None),
    ("current_logical_bytes", False), ("current_logical_bytes", -1),
    ("current_logical_bytes", RESERVATION_UINT64_MAX + 1),
    ("requested_growth_bytes", True), ("requested_growth_bytes", 0),
    ("requested_growth_bytes", -1), ("requested_growth_bytes", RESERVATION_UINT64_MAX + 1),
    ("reservation_kind", "worker"), ("reservation_kind", []),
    ("operation_id", "op-" + "A" * 32), ("operation_id", "op-" + "a" * 31),
    ("operation_id", "op-" + "a" * 32 + "\n"), ("operation_id", 1),
    ("message_type", []), ("message_type", "reserved"),
))
def test_reservation_request_rejects_wrong_fields_and_numeric_domains(field, value):
    with pytest.raises(ReservationProtocolError):
        parse_reservation_payload(_reservation_json(_reservation_request(**{field: value})))


@pytest.mark.parametrize("factory", (_reservation_request, _reservation_ack, _reservation_rejection))
@pytest.mark.parametrize("mutation", ("missing", "extra", "duplicate", "whitespace", "order", "lf", "utf8", "bom", "escape"))
def test_reservation_closed_shapes_and_noncanonical_bytes(factory, mutation):
    value = factory()
    raw = _reservation_json(value)
    if mutation == "missing":
        del value["schema_version"]
        raw = _reservation_json(value)
    elif mutation == "extra":
        value["path"] = "/private/forbidden"
        raw = _reservation_json(value)
    elif mutation == "duplicate":
        raw = b'{"schema_version":1,' + raw[1:]
    elif mutation == "whitespace":
        raw = b" " + raw
    elif mutation == "order":
        raw = json.dumps(value, separators=(",", ":")).encode()
    elif mutation == "lf":
        raw += b"\n"
    elif mutation == "utf8":
        raw = raw.replace(b"op-", b"\xffp-")
    elif mutation == "bom":
        raw = b"\xef\xbb\xbf" + raw
    else:
        raw = raw.replace(b"op-", b"\\u006fp-")
    with pytest.raises(ReservationProtocolError):
        parse_reservation_payload(raw)


@pytest.mark.parametrize("field", ("accepted_growth_bytes", "resulting_reserved_bytes", "resulting_charged_bytes"))
@pytest.mark.parametrize("value", (True, -1, RESERVATION_UINT64_MAX + 1, "1"))
def test_reservation_ack_integer_domains(field, value):
    with pytest.raises(ReservationProtocolError):
        parse_reservation_payload(_reservation_json(_reservation_ack(**{field: value})))


@pytest.mark.parametrize("value", ("ERROR", [], None, True))
def test_reservation_rejection_codes_are_closed(value):
    with pytest.raises(ReservationProtocolError):
        parse_reservation_payload(_reservation_json(_reservation_rejection(failure_code=value)))


@pytest.mark.parametrize("code", RESERVATION_FAILURE_CODES)
def test_reservation_each_governed_rejection_is_terminal(code):
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 0, 4)
    with pytest.raises(ReservationProtocolError, match=f"^{code}$"):
        worker.accept_response(reservation_payload(_reservation_rejection(failure_code=code)))
    assert worker.terminal
    with pytest.raises(ReservationProtocolError):
        worker.accept_response(reservation_payload(_reservation_ack()))


@pytest.mark.parametrize("value", (
    {"failure_code": "RESOURCE_LIMIT_EXCEEDED"},
    {"reserved": 4},
    {"authorized_new_size": 4},
    _reservation_request(path="/tmp/output"),
    {**{key: value for key, value in _reservation_request().items() if key != "requested_growth_bytes"}, "growth": 4},
))
def test_reservation_obsolete_shapes_and_aliases_reject(value):
    with pytest.raises(ReservationProtocolError):
        parse_reservation_payload(_reservation_json(value))


def test_reservation_prepare_ack_consume_and_observed_charge_are_distinct():
    controller, observations = _reservation_core(limit=4)
    worker = ReservationAllowance(_RESERVATION_OP)
    request = worker.request("worker_output_growth", 0, 4)
    assert controller.snapshot.expected_sequence == 0
    controller.prepare_request(request)
    assert controller.snapshot.pending_request
    assert sum(controller.snapshot.reserved_bytes) == sum(controller.snapshot.charged_bytes) == 0
    ack = controller.issue_acknowledgment()
    assert parse_reservation_payload(ack) == _reservation_ack()
    assert controller.snapshot.expected_sequence == 1
    assert sum(controller.snapshot.reserved_bytes) == 4
    assert sum(controller.snapshot.charged_bytes) == 0
    worker.accept_response(ack)
    assert worker.consume(
        operation_id=_RESERVATION_OP, sequence_number=0,
        reservation_kind="worker_output_growth", growth_bytes=4,
    ) == 4
    # A worker's consume call does not establish an observed filesystem result.
    assert sum(controller.snapshot.charged_bytes) == 0
    observations["worker_output_growth"] = 4
    controller.observe_completion("worker_output_growth")
    assert sum(controller.snapshot.charged_bytes) == 4
    controller.orderly_eof()
    assert controller.snapshot.terminal
    assert controller.snapshot.charged_bytes == controller.snapshot.reserved_bytes


@pytest.mark.parametrize("kind", RESERVATION_KINDS)
def test_reservation_controller_observations_bind_every_category(kind):
    controller, observations = _reservation_core()
    observations[kind] = 1
    before = _reservation_ledger(controller)
    # Worker-reported current size cannot substitute for the bound controller observation.
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        _reservation_grant(controller, reservation_kind=kind, current_logical_bytes=0)
    assert _reservation_ledger(controller) == before
    assert controller.snapshot.terminal
    assert parse_reservation_payload(controller.rejection_payload)["failure_code"] == "DISK_RESERVATION_STATE_MISMATCH"


def test_reservation_worker_claim_cannot_release_or_reassign_charge():
    controller, observations = _reservation_core(worker_output_growth=3)
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        _reservation_grant(controller, current_logical_bytes=0)
    assert observations["worker_output_growth"] == 3
    assert _reservation_ledger(controller) == before
    # Observation authority cannot be smuggled into the wire.
    controller, _ = _reservation_core()
    with pytest.raises(ReservationProtocolError):
        controller.prepare_request(_reservation_json(_reservation_request(controller_observe=0)))
    assert controller.rejection_payload is None


@pytest.mark.parametrize("case", ("one_over", "category_overflow", "total_overflow"))
def test_reservation_checked_budget_rejection_is_atomic(case):
    if case == "one_over":
        controller, _ = _reservation_core(limit=3)
        request = _reservation_request()
    elif case == "category_overflow":
        controller, _ = _reservation_core(
            limit=RESERVATION_UINT64_MAX, worker_output_growth=RESERVATION_UINT64_MAX,
        )
        request = _reservation_request(current_logical_bytes=RESERVATION_UINT64_MAX, requested_growth_bytes=1)
    else:
        controller, _ = _reservation_core(
            limit=RESERVATION_UINT64_MAX, snapshot_growth=RESERVATION_UINT64_MAX,
        )
        request = _reservation_request(requested_growth_bytes=1)
    before = _reservation_ledger(controller)
    controller_request = reservation_payload(request)
    with pytest.raises(ReservationProtocolError, match="RESOURCE_LIMIT_EXCEEDED"):
        controller.prepare_request(controller_request)
    assert _reservation_ledger(controller) == before
    assert not controller.snapshot.pending_request
    assert controller.snapshot.terminal
    assert parse_reservation_payload(controller.rejection_payload) == _reservation_rejection(failure_code="RESOURCE_LIMIT_EXCEEDED")
    with pytest.raises(ReservationProtocolError):
        controller.prepare_request(reservation_payload(_reservation_request(requested_growth_bytes=1)))
    assert _reservation_ledger(controller) == before


@pytest.mark.parametrize("sequence", (0, 2, 9))
def test_reservation_replayed_stale_skipped_future_sequence_rejects(sequence):
    controller, _ = _reservation_core()
    _reservation_grant(controller)
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError):
        _reservation_grant(controller, sequence_number=sequence)
    assert _reservation_ledger(controller) == before
    assert controller.snapshot.terminal


def test_reservation_operation_mismatch_rejects_without_ledger_mutation():
    controller, _ = _reservation_core()
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError):
        _reservation_grant(controller, operation_id="op-" + "b" * 32)
    assert _reservation_ledger(controller) == before
    assert parse_reservation_payload(controller.rejection_payload)["operation_id"] == "op-" + "b" * 32


def test_reservation_max_sequence_acknowledges_once_and_never_wraps():
    controller, observations = _reservation_core()
    worker = ReservationAllowance(_RESERVATION_OP)
    # Reach the boundary synthetically; neither constructor exposes a resume/sequence override.
    controller._sequence = worker._sequence = RESERVATION_UINT64_MAX
    controller.prepare_request(worker.request("worker_output_growth", 0, 4))
    ack = controller.issue_acknowledgment()
    assert parse_reservation_payload(ack)["sequence_number"] == RESERVATION_UINT64_MAX
    worker.accept_response(ack)
    worker.consume(operation_id=_RESERVATION_OP, sequence_number=RESERVATION_UINT64_MAX,
                   reservation_kind="worker_output_growth", growth_bytes=4)
    observations["worker_output_growth"] = 4
    assert controller.snapshot.expected_sequence is None
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError):
        controller.prepare_request(reservation_payload(_reservation_request(sequence_number=RESERVATION_UINT64_MAX)))
    assert _reservation_ledger(controller) == before
    with pytest.raises(ReservationProtocolError):
        worker.request("worker_output_growth", 4, 1)


@pytest.mark.parametrize("action", ("second_request", "second_ack", "ack_before_request"))
def test_reservation_pending_or_duplicate_controller_transition_rejects(action):
    controller, _ = _reservation_core()
    if action != "ack_before_request":
        controller.prepare_request(reservation_payload(_reservation_request()))
        if action == "second_ack":
            controller.issue_acknowledgment()
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError):
        if action == "second_request":
            controller.prepare_request(reservation_payload(_reservation_request()))
        else:
            controller.issue_acknowledgment()
    assert _reservation_ledger(controller) == before
    assert controller.snapshot.terminal


@pytest.mark.parametrize("changes", (
    {"operation_id": "op-" + "b" * 32}, {"sequence_number": 1},
    {"accepted_growth_bytes": 3}, {"resulting_reserved_bytes": 3},
    {"resulting_charged_bytes": 5},
))
def test_reservation_worker_rejects_substituted_acknowledgment(changes):
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 0, 4)
    with pytest.raises(ReservationProtocolError):
        worker.accept_response(reservation_payload(_reservation_ack(**changes)))
    assert worker.terminal


@pytest.mark.parametrize("changes", (
    {"sequence_number": True}, {"sequence_number": 1}, {"sequence_number": -1},
    {"operation_id": "op-" + "b" * 32},
    {"reservation_kind": "snapshot_growth"}, {"growth_bytes": 5},
    {"growth_bytes": True}, {"growth_bytes": 0},
))
def test_reservation_allowance_is_bound_to_identity_category_sequence_and_growth(changes):
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 0, 4)
    worker.accept_response(reservation_payload(_reservation_ack()))
    arguments = dict(operation_id=_RESERVATION_OP, sequence_number=0,
                     reservation_kind="worker_output_growth", growth_bytes=4)
    with pytest.raises(ReservationProtocolError):
        worker.consume(**{**arguments, **changes})
    assert worker.terminal


@pytest.mark.parametrize("action", ("pre_ack", "duplicate_ack", "duplicate_consume", "partial_reuse", "controller_eof", "next_before_consume"))
def test_reservation_allowance_never_authorizes_a_second_or_pre_ack_write(action):
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 0, 4)
    ack = reservation_payload(_reservation_ack())
    arguments = dict(operation_id=_RESERVATION_OP, sequence_number=0,
                     reservation_kind="worker_output_growth", growth_bytes=4)
    if action != "pre_ack":
        worker.accept_response(ack)
    if action in ("duplicate_consume", "partial_reuse"):
        worker.consume(**{**arguments, "growth_bytes": 2 if action == "partial_reuse" else 4})
    with pytest.raises(ReservationProtocolError):
        if action == "duplicate_ack":
            worker.accept_response(ack)
        elif action == "controller_eof":
            worker.controller_eof()
        elif action == "next_before_consume":
            worker.request("worker_output_growth", 0, 4)
        else:
            worker.consume(**arguments)
    assert worker.terminal
    with pytest.raises(ReservationProtocolError):
        worker.consume(**arguments)


def test_reservation_worker_advancement_does_not_allow_an_old_response():
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 0, 4)
    worker.accept_response(reservation_payload(_reservation_ack()))
    worker.consume(operation_id=_RESERVATION_OP, sequence_number=0,
                   reservation_kind="worker_output_growth", growth_bytes=4)
    assert parse_reservation_payload(worker.request("snapshot_growth", 0, 4))["sequence_number"] == 1
    with pytest.raises(ReservationProtocolError):
        worker.accept_response(reservation_payload(_reservation_ack()))


def test_reservation_short_write_retains_capacity_until_same_category_or_eof():
    controller, observations = _reservation_core(limit=20)
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    controller.observe_completion("worker_output_growth")
    assert sum(controller.snapshot.charged_bytes) == 3
    assert sum(controller.snapshot.reserved_bytes) == 10
    ack = parse_reservation_payload(_reservation_grant(
        controller, sequence_number=1, reservation_kind="snapshot_growth", requested_growth_bytes=2,
    ))
    assert ack["resulting_reserved_bytes"] == 12
    assert ack["resulting_charged_bytes"] == 3
    ack = parse_reservation_payload(_reservation_grant(
        controller, sequence_number=2, current_logical_bytes=3, requested_growth_bytes=4,
    ))
    assert ack["resulting_reserved_bytes"] == 9  # 3 observed + 4 new + 2 other category
    assert ack["resulting_charged_bytes"] == 3
    controller.orderly_eof()
    assert sum(controller.snapshot.reserved_bytes) == sum(controller.snapshot.charged_bytes) == 3


def test_reservation_rejected_next_request_does_not_release_short_write_capacity():
    controller, observations = _reservation_core(limit=10)
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError, match="RESOURCE_LIMIT_EXCEEDED"):
        _reservation_grant(controller, sequence_number=1, current_logical_bytes=3, requested_growth_bytes=8)
    assert _reservation_ledger(controller) == before


@pytest.mark.parametrize("actual,retained", ((0, 10), (3, 10), (10, 10), (12, 12)))
def test_reservation_uncertain_completion_keeps_greater_actual_or_prospective(actual, retained):
    controller, observations = _reservation_core(limit=10)
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = actual
    controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == retained
    assert sum(controller.snapshot.charged_bytes) == actual
    assert controller.snapshot.terminal and controller.snapshot.uncertain
    before = controller.snapshot
    with pytest.raises(ReservationProtocolError):
        controller.orderly_eof()
    assert controller.snapshot == before


def test_reservation_failed_observation_never_releases_uncertain_charge():
    controller, observations = _reservation_core()
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = None
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == 10
    assert controller.snapshot.terminal and controller.snapshot.uncertain


def test_reservation_uncertain_aggregate_overflow_retains_facts_without_wrapping():
    controller, observations = _reservation_core(limit=RESERVATION_UINT64_MAX)
    _reservation_grant(controller)
    observations["snapshot_growth"] = RESERVATION_UINT64_MAX
    with pytest.raises(ReservationProtocolError, match="RESOURCE_LIMIT_EXCEEDED"):
        controller.fail_uncertain()
    assert controller.snapshot.reserved_bytes[0] == RESERVATION_UINT64_MAX
    assert controller.snapshot.reserved_bytes[2] == 4
    assert controller.snapshot.terminal and controller.snapshot.uncertain


@pytest.mark.parametrize("state", ("idle", "pending", "acknowledged", "partial_header", "partial_payload", "rejected"))
def test_reservation_eof_states_are_explicit(state):
    controller, observations = _reservation_core()
    if state in ("pending", "acknowledged"):
        controller.prepare_request(reservation_payload(_reservation_request()))
        if state == "acknowledged":
            controller.issue_acknowledgment()
            observations["worker_output_growth"] = 2
    elif state == "rejected":
        with pytest.raises(ReservationProtocolError):
            controller.prepare_request(b"invalid")
    data = b"\0" if state == "partial_header" else b"\0\0\0\x04a" if state == "partial_payload" else b""
    if state in ("idle", "acknowledged"):
        before = _reservation_ledger(controller)
        controller.read_request(io.BytesIO(data).read)
        assert controller.snapshot.eof_pending_classification
        assert not controller.snapshot.terminal
        assert _reservation_ledger(controller) == before
        # This explicit controller call supplies the orderly classification;
        # the bare transport EOF above provides no such authority.
        controller.orderly_eof()
        assert controller.snapshot.terminal
        assert controller.snapshot.reserved_bytes == controller.snapshot.charged_bytes
    else:
        before = _reservation_ledger(controller)
        with pytest.raises(ReservationProtocolError):
            controller.read_request(io.BytesIO(data).read)
        assert _reservation_ledger(controller) == before
        assert controller.snapshot.terminal


def test_reservation_stream_does_not_discard_a_concatenated_request():
    controller, _ = _reservation_core()
    stream = io.BytesIO(reservation_frame(_reservation_request()) * 2)
    controller.read_request(stream.read)
    controller.issue_acknowledgment()
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError):
        controller.read_request(stream.read)
    assert _reservation_ledger(controller) == before


def test_reservation_orderly_reconciliation_is_atomic_on_invalid_observation():
    controller, observations = _reservation_core()
    _reservation_grant(controller, reservation_kind="snapshot_growth")
    _reservation_grant(controller, sequence_number=1)
    observations["snapshot_growth"] = 2
    observations["worker_output_growth"] = 5  # beyond ACK; no partial release
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.orderly_eof()
    assert _reservation_ledger(controller) == before


def test_reservation_unissued_request_does_not_become_uncertain_granted_charge():
    controller, _ = _reservation_core()
    controller.prepare_request(reservation_payload(_reservation_request()))
    controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == 0
    assert controller.snapshot.terminal and not controller.snapshot.pending_request


def test_reservation_core_remains_controller_only_and_unconnected():
    import inspect
    from orev3.execution import runtime
    assert "controller_observe" in inspect.signature(ControllerReservationSession).parameters
    assert tuple(inspect.signature(ControllerReservationSession.prepare_request).parameters) == ("self", "payload")
    assert "controller_observe" not in inspect.signature(ReservationAllowance).parameters
    # No operation-ID generator, socket/lease creation, or operational writer is activated.
    for function in (runtime.run_phase3b_worker, runtime.create_bounded_bootstrap_request_artifact):
        assert "ControllerReservationSession" not in inspect.getsource(function)
    assert "ControllerReservationSession" not in inspect.getsource(ReservationAllowance)


@pytest.mark.parametrize("growth", (1, RESERVATION_UINT64_MAX))
def test_reservation_positive_growth_extremes_pass_at_exact_budget(growth):
    controller, observations = _reservation_core(limit=growth)
    worker = ReservationAllowance(_RESERVATION_OP)
    controller.prepare_request(worker.request("worker_output_growth", 0, growth))
    ack = controller.issue_acknowledgment()
    worker.accept_response(ack)
    assert parse_reservation_payload(ack)["resulting_reserved_bytes"] == growth
    worker.consume(operation_id=_RESERVATION_OP, sequence_number=0,
                   reservation_kind="worker_output_growth", growth_bytes=growth)
    observations["worker_output_growth"] = growth
    controller.orderly_eof()
    assert sum(controller.snapshot.charged_bytes) == growth


def test_reservation_ack_cannot_claim_a_total_below_the_requested_current_length():
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 10, 4)
    with pytest.raises(ReservationProtocolError):
        worker.accept_response(reservation_payload(_reservation_ack()))
    assert worker.terminal


@pytest.mark.parametrize("payload", (b"invalid", b"\xff", reservation_payload(_reservation_ack())))
def test_reservation_malformed_or_response_as_request_preserves_existing_ledger(payload):
    controller, _ = _reservation_core()
    _reservation_grant(controller)
    before = _reservation_ledger(controller)
    with pytest.raises(ReservationProtocolError):
        controller.prepare_request(payload)
    assert _reservation_ledger(controller) == before
    assert controller.snapshot.terminal


def test_reservation_controller_eof_during_outstanding_request_never_allows_consumption():
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 0, 4)
    with pytest.raises(ReservationProtocolError):
        worker.controller_eof()
    with pytest.raises(ReservationProtocolError):
        worker.accept_response(reservation_payload(_reservation_ack()))
    with pytest.raises(ReservationProtocolError):
        worker.consume(operation_id=_RESERVATION_OP, sequence_number=0,
                       reservation_kind="worker_output_growth", growth_bytes=4)


@pytest.mark.parametrize("response", (
    _reservation_request(),
    _reservation_rejection(operation_id="op-" + "b" * 32),
    _reservation_rejection(sequence_number=1),
))
def test_reservation_response_direction_and_rejection_binding_are_enforced(response):
    worker = ReservationAllowance(_RESERVATION_OP)
    worker.request("worker_output_growth", 0, 4)
    with pytest.raises(ReservationProtocolError):
        worker.accept_response(reservation_payload(response))
    assert worker.terminal


@pytest.mark.parametrize("classification", ("uncertain", "orderly"))
def test_reservation_correction_unclassified_eof_preserves_ack_floor(classification):
    controller, observations = _reservation_core(limit=10)
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    before = _reservation_ledger(controller)
    controller.read_request(io.BytesIO(b"").read)
    assert _reservation_ledger(controller) == before
    assert sum(controller.snapshot.reserved_bytes) == 10
    assert controller.snapshot.eof_pending_classification
    assert not controller.snapshot.terminal and not controller.snapshot.uncertain
    if classification == "uncertain":
        controller.fail_uncertain()
        assert sum(controller.snapshot.reserved_bytes) == 10
        assert sum(controller.snapshot.charged_bytes) == 3
        assert controller.snapshot.uncertain
    else:
        # Controller has independently established genuinely orderly completion.
        controller.orderly_eof()
        assert sum(controller.snapshot.reserved_bytes) == 3
        assert sum(controller.snapshot.charged_bytes) == 3
        assert not controller.snapshot.uncertain
    assert controller.snapshot.terminal
    assert not controller.snapshot.eof_pending_classification


@pytest.mark.parametrize("action", ("read", "prepare", "ack", "observe"))
def test_reservation_correction_unclassified_eof_freezes_admission(action):
    controller, observations = _reservation_core(limit=10)
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    controller.read_request(io.BytesIO(b"").read)
    before = controller.snapshot
    with pytest.raises(ReservationProtocolError):
        if action == "read":
            controller.read_request(lambda _size: pytest.fail("must not read after EOF"))
        elif action == "prepare":
            controller.prepare_request(reservation_payload(_reservation_request(sequence_number=1)))
        elif action == "ack":
            controller.issue_acknowledgment()
        else:
            controller.observe_completion("worker_output_growth")
    assert controller.snapshot == before
    controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == 10


@pytest.mark.parametrize("classification", ("uncertain", "orderly"))
def test_reservation_correction_eof_before_ack_and_repeated_classification(classification):
    controller, _ = _reservation_core()
    controller.read_request(io.BytesIO(b"").read)
    assert sum(controller.snapshot.reserved_bytes) == 0
    assert controller.snapshot.eof_pending_classification
    if classification == "uncertain":
        controller.fail_uncertain()
        before = controller.snapshot
        controller.fail_uncertain()  # Same observations: conservative idempotence.
        assert controller.snapshot == before
    else:
        controller.orderly_eof()
        before = controller.snapshot
        with pytest.raises(ReservationProtocolError):
            controller.fail_uncertain()  # Cannot contradict a final classification.
        assert controller.snapshot == before
    for action in (controller.orderly_eof, lambda: controller.read_request(io.BytesIO(b"").read)):
        with pytest.raises(ReservationProtocolError):
            action()
        assert controller.snapshot == before


def test_reservation_correction_orderly_classification_releases_only_once():
    controller, observations = _reservation_core(limit=10)
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    controller.read_request(io.BytesIO(b"").read)
    controller.orderly_eof()
    before = controller.snapshot
    observations["worker_output_growth"] = 0
    for action in (controller.orderly_eof, controller.fail_uncertain):
        with pytest.raises(ReservationProtocolError):
            action()
        assert controller.snapshot == before
    assert sum(controller.snapshot.reserved_bytes) == 3


@pytest.mark.parametrize("observed", (None, 11))
def test_reservation_correction_failed_orderly_proof_keeps_ack_floor(observed):
    controller, observations = _reservation_core(limit=10)
    _reservation_grant(controller, requested_growth_bytes=10)
    controller.read_request(io.BytesIO(b"").read)
    before = _reservation_ledger(controller)
    observations["worker_output_growth"] = observed
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.orderly_eof()
    assert _reservation_ledger(controller) == before
    assert controller.snapshot.terminal
    observations["worker_output_growth"] = 3
    controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == 10


@pytest.mark.parametrize("swallow", (False, True))
def test_reservation_correction_reentrant_prepare_never_changes_outer_ack_sequence(swallow):
    observations = dict.fromkeys(RESERVATION_KINDS, 0)
    armed = False
    nested_acks = []
    def observe(kind):
        nonlocal armed
        if armed:
            armed = False
            try:
                controller.prepare_request(reservation_payload(_reservation_request(
                    reservation_kind="snapshot_growth", requested_growth_bytes=2,
                )))
                nested_acks.append(controller.issue_acknowledgment())
            except ReservationProtocolError:
                if not swallow:
                    raise
        return observations[kind]
    controller = ControllerReservationSession(
        operation_id=_RESERVATION_OP, max_temporary_disk_bytes=20,
        controller_observe=observe,
    )
    before = _reservation_ledger(controller)
    armed = True
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.prepare_request(reservation_payload(_reservation_request()))
    assert nested_acks == []
    assert _reservation_ledger(controller) == before
    assert controller.snapshot.expected_sequence == 0
    assert controller.snapshot.terminal and not controller.snapshot.pending_request
    with pytest.raises(ReservationProtocolError):
        controller.issue_acknowledgment()
    # A rejected request is terminal by governance, but the guard must not
    # obstruct the still-permitted conservative failure transition.
    controller.fail_uncertain()
    assert controller.snapshot.uncertain
    assert sum(controller.snapshot.reserved_bytes) == 0


@pytest.mark.parametrize("swallow", (False, True))
def test_reservation_correction_reentrant_uncertainty_cannot_be_overwritten(swallow):
    observations = dict.fromkeys(RESERVATION_KINDS, 0)
    armed = False
    nested_returned = []
    def observe(kind):
        nonlocal armed
        if armed:
            armed = False
            try:
                controller.fail_uncertain()
                nested_returned.append(True)
            except ReservationProtocolError:
                if not swallow:
                    raise
        return observations[kind]
    controller = ControllerReservationSession(
        operation_id=_RESERVATION_OP, max_temporary_disk_bytes=10,
        controller_observe=observe,
    )
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    controller.read_request(io.BytesIO(b"").read)
    before = _reservation_ledger(controller)
    armed = True
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.orderly_eof()
    assert nested_returned == []
    assert _reservation_ledger(controller) == before
    assert sum(controller.snapshot.reserved_bytes) == 10
    assert controller.snapshot.terminal
    controller.fail_uncertain()  # Guard was released; classify safely now.
    assert controller.snapshot.uncertain
    assert sum(controller.snapshot.reserved_bytes) == 10
    assert sum(controller.snapshot.charged_bytes) == 3


@pytest.mark.parametrize("nested", ("prepare", "ack", "observe", "orderly", "read", "uncertain", "initialize"))
def test_reservation_correction_guard_covers_every_public_mutating_transition(nested):
    observations = dict.fromkeys(RESERVATION_KINDS, 0)
    armed = False
    nested_errors = []
    snapshots = []
    def observe(kind):
        nonlocal armed
        if armed:
            armed = False
            snapshots.append(controller.snapshot)  # Read-only introspection is safe.
            actions = {
                "prepare": lambda: controller.prepare_request(reservation_payload(_reservation_request(sequence_number=1))),
                "ack": controller.issue_acknowledgment,
                "observe": lambda: controller.observe_completion("worker_output_growth"),
                "orderly": controller.orderly_eof,
                "read": lambda: controller.read_request(lambda _size: pytest.fail("nested read invoked")),
                "uncertain": controller.fail_uncertain,
                "initialize": lambda: controller.__init__(
                    operation_id="op-" + "b" * 32, max_temporary_disk_bytes=1,
                    controller_observe=lambda _kind: pytest.fail("nested initialization invoked"),
                ),
            }
            try:
                actions[nested]()
            except ReservationProtocolError as exc:
                nested_errors.append(exc.code)
            assert controller.snapshot == snapshots[-1]
            assert controller.rejection_payload is None
        return observations[kind]
    controller = ControllerReservationSession(
        operation_id=_RESERVATION_OP, max_temporary_disk_bytes=10,
        controller_observe=observe,
    )
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    before = _reservation_ledger(controller)
    armed = True
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.observe_completion("worker_output_growth")
    assert nested_errors == ["DISK_RESERVATION_STATE_MISMATCH"]
    assert _reservation_ledger(controller) == before
    controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == 10


@pytest.mark.parametrize("outer", ("prepare", "observe", "orderly", "uncertain"))
def test_reservation_correction_callback_exception_releases_guard_without_partial_commit(outer):
    observations = dict.fromkeys(RESERVATION_KINDS, 0)
    armed = False
    def observe(kind):
        if armed and kind == "worker_output_growth":
            raise RuntimeError("PRIVATE_CALLBACK_DETAIL")
        return observations[kind]
    controller = ControllerReservationSession(
        operation_id=_RESERVATION_OP, max_temporary_disk_bytes=20,
        controller_observe=observe,
    )
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    before = _reservation_ledger(controller)
    actions = {
        "prepare": lambda: controller.prepare_request(reservation_payload(_reservation_request(
            sequence_number=1, current_logical_bytes=3,
        ))),
        "observe": lambda: controller.observe_completion("worker_output_growth"),
        "orderly": controller.orderly_eof,
        "uncertain": controller.fail_uncertain,
    }
    armed = True
    with pytest.raises(ReservationProtocolError, match="^DISK_RESERVATION_STATE_MISMATCH$"):
        actions[outer]()
    assert _reservation_ledger(controller) == before
    assert controller.snapshot.terminal
    armed = False
    controller.fail_uncertain()
    assert controller.snapshot.uncertain
    assert sum(controller.snapshot.reserved_bytes) == 10
    assert sum(controller.snapshot.charged_bytes) == 3


@pytest.mark.parametrize("payload", (b"", reservation_frame(_reservation_request(sequence_number=1))))
def test_reservation_correction_read_callback_cannot_hide_reentrant_mutation(payload):
    controller, observations = _reservation_core(limit=10)
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    before = _reservation_ledger(controller)
    stream = io.BytesIO(payload)
    attempted = False
    def read(size):
        nonlocal attempted
        if not attempted:
            attempted = True
            with pytest.raises(ReservationProtocolError):
                controller.fail_uncertain()
        return stream.read(size)
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.read_request(read)
    assert _reservation_ledger(controller) == before
    assert not controller.snapshot.eof_pending_classification
    controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == 10


def test_reservation_correction_read_only_callback_introspection_does_not_poison_session():
    observations = dict.fromkeys(RESERVATION_KINDS, 0)
    controller = None
    snapshots = []
    def observe(kind):
        if controller is not None:
            snapshots.append(controller.snapshot)
            assert controller.rejection_payload is None
        return observations[kind]
    controller = ControllerReservationSession(
        operation_id=_RESERVATION_OP, max_temporary_disk_bytes=10,
        controller_observe=observe,
    )
    assert parse_reservation_payload(_reservation_grant(controller))["sequence_number"] == 0
    observations["worker_output_growth"] = 4
    assert parse_reservation_payload(_reservation_grant(
        controller, sequence_number=1, current_logical_bytes=4,
    ))["sequence_number"] == 1
    assert snapshots
    assert controller.snapshot.expected_sequence == 2
    assert not controller.snapshot.terminal


def test_reservation_correction_reentry_during_uncertain_retention_is_conservative():
    observations = dict.fromkeys(RESERVATION_KINDS, 0)
    armed = False
    def observe(kind):
        nonlocal armed
        if armed:
            armed = False
            with pytest.raises(ReservationProtocolError):
                controller.orderly_eof()
        return observations[kind]
    controller = ControllerReservationSession(
        operation_id=_RESERVATION_OP, max_temporary_disk_bytes=10,
        controller_observe=observe,
    )
    _reservation_grant(controller, requested_growth_bytes=10)
    observations["worker_output_growth"] = 3
    armed = True
    with pytest.raises(ReservationProtocolError, match="DISK_RESERVATION_STATE_MISMATCH"):
        controller.fail_uncertain()
    assert controller.snapshot.terminal and controller.snapshot.uncertain
    assert sum(controller.snapshot.reserved_bytes) == 10
    assert controller.snapshot.expected_sequence == 1
    controller.fail_uncertain()
    assert sum(controller.snapshot.reserved_bytes) == 10
    assert sum(controller.snapshot.charged_bytes) == 3


def _bootstrap_envelope() -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema_version": 1,
        "source_closure_identifier": "bounded-input-projector-import-closure-v1",
        "source_commit": "4" * 40,
        "root_tree_git_object_identity": "5" * 40,
        "git_object_format": "sha1",
        "members": [],
    }
    manifest["source_code_closure_manifest_identity"] = bootstrap_domain_identity(
        "orev3:bounded-streaming-source-code-closure-manifest:v1\n", manifest
    )
    closure = manifest["source_code_closure_manifest_identity"]
    worker_request = '{"command":"bounded"}'
    value: dict[str, object] = {
        "schema_version": 1,
        "request_kind": "input_projector",
        "operation_id": "op-" + "a" * 32,
        "authority_generation": BOUNDED_GENERATION,
        "execution_profile_identity": "2" * 64,
        "runtime_contract_identity": "3" * 64,
        "source_root_authority": {
            "absolute_root": "/private/source",
            "source_commit": "4" * 40,
            "root_tree_git_object_identity": "5" * 40,
            "source_code_closure_manifest": manifest,
        },
        "dependency_root_authority": {"present": False},
        "runtime_bundle_authority": {
            "runtime_bundle_identity": "6" * 64,
            "python_executable_path": "/usr/bin/python3",
            "stdlib_roots": ["/stdlib"],
            "dynamic_library_roots": ["/dynload"],
            "runtime_bundle_material": {},
        },
        "worker_entrypoint_identifier": "input-projector-v1",
        "worker_code_closure_identity": closure,
        "worker_request_byte_count": len(worker_request.encode()),
        "worker_request_sha256": hashlib.sha256(worker_request.encode()).hexdigest(),
        "worker_request_canonical_json": worker_request,
        "bootstrap_request_identity": "0" * 64,
    }
    material = dict(value)
    material.pop("bootstrap_request_identity")
    value["bootstrap_request_identity"] = bootstrap_domain_identity(
        BOOTSTRAP_REQUEST_DOMAIN, material
    )
    return value


def test_bounded_bootstrap_canonical_request_and_dispatch_are_closed() -> None:
    value = _bootstrap_envelope()
    raw = bootstrap_canonical_bytes(value)[:-1]
    assert bootstrap_parse_request_bytes(raw) == value
    assert set(BOUNDED_STREAMING_WORKER_DISPATCH) == {
        "phase3b-controller-v1", "phase3a-validator-v1", "input-projector-v1",
        "readiness-test-v1", "replay-preparation-v1",
    }
    with pytest.raises(BoundedBootstrapError):
        bootstrap_parse_request_bytes(raw + b"\n")
    with pytest.raises(BoundedBootstrapError):
        bootstrap_parse_request_bytes(raw.replace(b'"schema_version":1', b'"schema_version":1.0'))
    duplicate = raw.replace(b'{', b'{"schema_version":1,', 1)
    with pytest.raises(BoundedBootstrapError):
        bootstrap_parse_request_bytes(duplicate)


def test_bounded_bootstrap_gate_and_fd6_preserve_exact_bytes(tmp_path: Path) -> None:
    read_fd, write_fd = __import__("os").pipe()
    __import__("os").write(write_fd, b"\xa5")
    __import__("os").close(write_fd)
    consume_start_gate(read_fd)
    raw = bootstrap_canonical_bytes(_bootstrap_envelope())[:-1]
    request = tmp_path / "request"
    request.write_bytes(raw)
    request.chmod(0o600)
    descriptor = __import__("os").open(request, __import__("os").O_RDONLY)
    assert read_authenticated_request_fd(descriptor) == raw


def test_controller_request_artifact_uses_pread_without_offset_mutation(
    tmp_path: Path,
) -> None:
    value = _bootstrap_envelope()
    raw = bootstrap_canonical_bytes(value)[:-1]
    artifact = create_bounded_bootstrap_request_artifact(
        tmp_path, raw,
        bootstrap_request_identity=value["bootstrap_request_identity"],
        operation_id=value["operation_id"],
        authority_generation=value["authority_generation"],
        execution_profile_identity=value["execution_profile_identity"],
    )
    try:
        assert authenticate_bounded_bootstrap_request_artifact(artifact) == raw
        assert __import__("os").lseek(artifact.descriptor, 0, __import__("os").SEEK_CUR) == 0
        assert artifact.path.stat().st_mode & 0o777 == 0o600
    finally:
        artifact.close()


def test_fixed_fd_actions_use_unique_cloexec_scratches_and_preserve_parent() -> None:
    os_module = __import__("os")
    descriptors = []
    try:
        for _ in range(3):
            descriptors.extend(os_module.pipe())
        before = [os_module.fstat(fd) for fd in range(3) if _fd_open(fd)]
        actions = construct_bounded_spawn_file_actions(
            gate_fd=descriptors[0], reservation_fd=descriptors[1],
            lease_fd=descriptors[2], request_fd=descriptors[3],
            stdout_fd=descriptors[4], stderr_fd=descriptors[5],
        )
        assert len(set(actions.scratch_descriptors)) == 6
        assert min(actions.scratch_descriptors) > 6
        assert all(not os_module.get_inheritable(fd) for fd in actions.scratch_descriptors)
        assert [os_module.fstat(fd) for fd in range(3) if _fd_open(fd)] == before
        actions.close_scratches()
    finally:
        for descriptor in descriptors:
            try:
                os_module.close(descriptor)
            except OSError:
                pass


def _fd_open(descriptor: int) -> bool:
    try:
        __import__("os").fstat(descriptor)
    except OSError:
        return False
    return True


def test_exact_launch_vector_and_time_wrapper_authority() -> None:
    bootstrap = Path("/absolute/bounded_streaming_worker_bootstrap.py")
    vector = reconstruct_bounded_streaming_launch_authority(
        python_executable=Path(sys.executable).resolve(),
        bootstrap_script=bootstrap,
        sandbox_profile="(version 1)\n(allow default)\n",
    )
    assert vector == (
        "/usr/bin/time", "-l", "/usr/bin/sandbox-exec", "-p",
        "(version 1)\n(allow default)\n", str(Path(sys.executable).resolve()),
        "-I", "-S", str(bootstrap), "--governed-fixed-fds-v1",
    )
    authenticate_bounded_time_wrapper()


def test_gate_release_reauthenticates_request_before_write(tmp_path: Path) -> None:
    value = _bootstrap_envelope()
    raw = bootstrap_canonical_bytes(value)[:-1]
    artifact = create_bounded_bootstrap_request_artifact(
        tmp_path, raw,
        bootstrap_request_identity=value["bootstrap_request_identity"],
        operation_id=value["operation_id"],
        authority_generation=value["authority_generation"],
        execution_profile_identity=value["execution_profile_identity"],
    )
    read_fd, write_fd = __import__("os").pipe()
    try:
        release_bounded_start_gate(write_fd, artifact)
        assert __import__("os").read(read_fd, 2) == b"\xa5"
        assert __import__("os").read(read_fd, 1) == b""
    finally:
        artifact.close()
        __import__("os").close(read_fd)


def _kern_procargs(arguments: tuple[str, ...], environment: tuple[str, ...] = ()) -> bytes:
    executable = arguments[0].encode() + b"\0\0"
    argv = b"".join(argument.encode() + b"\0" for argument in arguments)
    env = b"".join(item.encode() + b"\0" for item in environment)
    return struct.pack("=i", len(arguments)) + executable + argv + env


def test_bounded_process_argv_parser_does_not_consume_environment_tail() -> None:
    expected = ("/python", "-I", "-S", "/bootstrap.py", "--governed-fixed-fds-v1")
    raw = _kern_procargs(expected, ("PYTHONPATH=/hostile",))
    assert parse_darwin_kern_procargs2(raw) == expected
    authenticate_bounded_process_argv(raw, expected)
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        authenticate_bounded_process_argv(raw, (*expected, "extra"))
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        parse_darwin_kern_procargs2(struct.pack("=i", 2) + b"/python\0\0only-one\0")


def test_bounded_environment_is_closed_and_rejects_ambient_authority(tmp_path: Path) -> None:
    environment = construct_bounded_launch_environment(tmp_path.resolve())
    authenticate_bounded_launch_environment(environment)
    hostile = dict(environment, PYTHONPATH="/working-tree")
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        authenticate_bounded_launch_environment(hostile)
    missing = dict(environment)
    missing.pop("PYTHONNOUSERSITE")
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        authenticate_bounded_launch_environment(missing)


def test_process_instance_wait_status_and_integrity_precedence() -> None:
    assert GovernedProcessInstanceV1(42, 10, 999_999).pbi_pid == 42
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        GovernedProcessInstanceV1(42, 10, 1_000_000)
    clean = decode_governed_wait_status(0)
    assert clean == GovernedWaitStatus("exited", 0)
    assert classify_bounded_worker_transport(clean, buffered_result={"ok": True}) == {"ok": True}
    with pytest.raises(Exception, match=BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY):
        classify_bounded_worker_transport(GovernedWaitStatus("exited", 70), buffered_result={"ok": True})


def test_process_topology_fd_identity_and_safe_termination(monkeypatch: pytest.MonkeyPatch) -> None:
    wrapper = GovernedProcessObservation(
        GovernedProcessInstanceV1(100, 10, 1), 50, 100, 100, "/usr/bin/time"
    )
    worker = GovernedProcessObservation(
        GovernedProcessInstanceV1(101, 10, 2), 100, 100, 100, "/usr/bin/python3"
    )
    authenticate_bounded_process_topology(wrapper, worker)
    observations = tuple(
        GovernedWorkerFDObservation(fd, kind, (kind, fd))
        for fd, kind in enumerate((
            "dev-null", "bounded-stdout", "bounded-stderr", "gate-pipe-read",
            "reservation-socket", "operation-lease-vnode", "request-vnode",
        ))
    )
    authenticate_bounded_worker_fd_set(observations)
    signals = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    safely_terminate_bounded_process_group(wrapper, worker, (wrapper, worker), signal_number=15)
    assert signals == [(100, 15)]
    substituted = GovernedProcessObservation(
        GovernedProcessInstanceV1(101, 11, 2), 100, 100, 100, "/usr/bin/python3"
    )
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        safely_terminate_bounded_process_group(wrapper, worker, (wrapper, substituted), signal_number=15)
    assert signals == [(100, 15)]


def test_bootstrap_rejects_role_closure_identifier_substitution() -> None:
    value = _bootstrap_envelope()
    value["source_root_authority"]["source_code_closure_manifest"]["source_closure_identifier"] = "bounded-phase3a-validator-import-closure-v1"
    manifest = value["source_root_authority"]["source_code_closure_manifest"]
    material = dict(manifest)
    material.pop("source_code_closure_manifest_identity")
    manifest["source_code_closure_manifest_identity"] = bootstrap_domain_identity(
        "orev3:bounded-streaming-source-code-closure-manifest:v1\n", material
    )
    value["worker_code_closure_identity"] = manifest["source_code_closure_manifest_identity"]
    material = dict(value)
    material.pop("bootstrap_request_identity")
    value["bootstrap_request_identity"] = bootstrap_domain_identity(BOOTSTRAP_REQUEST_DOMAIN, material)
    with pytest.raises(BoundedBootstrapError):
        bootstrap_parse_request_bytes(bootstrap_canonical_bytes(value)[:-1])


class _FakeProc:
    def proc_listpids(self, _kind, _group, buffer, _size):
        values = __import__("ctypes").cast(buffer, __import__("ctypes").POINTER(__import__("ctypes").c_int32))
        values[0], values[1] = 100, 101
        return 8

    def proc_pidpath(self, _pid, buffer, size):
        raw = b"/usr/bin/python3"
        assert len(raw) < size
        __import__("ctypes").memmove(buffer, raw, len(raw))
        return len(raw)

    def proc_pidinfo(self, pid, flavor, _arg, buffer, size):
        runtime = __import__("orev3.execution.runtime", fromlist=["_ProcBSDInfo", "_ProcFDInfo"])
        if flavor == runtime.PROC_PIDTBSDINFO:
            info = __import__("ctypes").cast(buffer, __import__("ctypes").POINTER(runtime._ProcBSDInfo)).contents
            info.pbi_pid = pid
            info.pbi_ppid = 100 if pid == 101 else 50
            info.pbi_pgid = 100
            info.pbi_start_tvsec = 10
            info.pbi_start_tvusec = pid
            return size
        entries = __import__("ctypes").cast(buffer, __import__("ctypes").POINTER(runtime._ProcFDInfo))
        entries[0].proc_fd, entries[0].proc_fdtype = 0, 1
        entries[1].proc_fd, entries[1].proc_fdtype = 3, 5
        return 2 * __import__("ctypes").sizeof(runtime._ProcFDInfo)


class _FakeLibC:
    def __init__(self, raw):
        self.raw = raw

    def sysctl(self, _mib, _count, output, size, _new, _new_size):
        size_pointer = __import__("ctypes").cast(size, __import__("ctypes").POINTER(__import__("ctypes").c_size_t))
        if output is None:
            size_pointer.contents.value = len(self.raw)
        else:
            __import__("ctypes").memmove(output, self.raw, len(self.raw))
            size_pointer.contents.value = len(self.raw)
        return 0


def test_darwin_query_owners_are_bounded_and_exact() -> None:
    fake = _FakeProc()
    assert query_darwin_process_group_pids(100, libproc=fake) == (100, 101)
    assert query_darwin_process_path(101, libproc=fake) == "/usr/bin/python3"
    observation = query_darwin_process_observation(101, libproc=fake, session_query=lambda _pid: 100)
    assert observation.instance == GovernedProcessInstanceV1(101, 10, 101)
    assert observation.parent_pid == 100 and observation.process_group == 100
    argv = ("/python", "-I", "-S", "/bootstrap", "--governed-fixed-fds-v1")
    assert query_darwin_process_argv(101, libc=_FakeLibC(_kern_procargs(argv))) == argv
    assert query_darwin_process_fds(101, libproc=fake) == ((0, 1), (3, 5))


def test_model_a_closure_tables_are_literal_and_closed() -> None:
    assert set(MODEL_A_CLOSURE_PATHS) == {
        "bounded-phase3b-controller-import-closure-v1",
        "bounded-phase3a-validator-import-closure-v1",
        "bounded-readiness-test-import-closure-v1",
        "bounded-replay-preparation-import-closure-v1",
    }
    assert len(MODEL_A_CLOSURE_PATHS["bounded-phase3b-controller-import-closure-v1"]) == 20
    assert len(MODEL_A_CLOSURE_PATHS["bounded-phase3a-validator-import-closure-v1"]) == 20
    assert len(MODEL_A_CLOSURE_PATHS["bounded-readiness-test-import-closure-v1"]) == 62
    assert len(MODEL_A_CLOSURE_PATHS["bounded-replay-preparation-import-closure-v1"]) == 6
    assert all(len(paths) == len(set(paths)) for paths in MODEL_A_CLOSURE_PATHS.values())


@pytest.mark.parametrize("closure_identifier", tuple(MODEL_A_CLOSURE_PATHS))
def test_model_a_closure_manifest_authenticates_exact_ordered_bytes(
    tmp_path: Path, closure_identifier: str,
) -> None:
    members = []
    for index, relative in enumerate(MODEL_A_CLOSURE_PATHS[closure_identifier]):
        raw = f"member-{index}\n".encode()
        path = tmp_path / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw); path.chmod(0o644)
        kind = "python_source" if relative.startswith("src/") and relative.endswith(".py") else "test_source" if relative.startswith("tests/") and relative.endswith(".py") else "test_configuration"
        members.append({
            "path": relative, "mode": "100644", "file_kind": kind,
            "git_object_identity": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
            "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        })
    manifest = {"members": members}
    assert tuple(authenticate_source_code_closure(tmp_path, manifest, closure_identifier=closure_identifier)) == MODEL_A_CLOSURE_PATHS[closure_identifier]
    manifest["members"] = members[:-1]
    with pytest.raises(BoundedBootstrapError):
        authenticate_source_code_closure(tmp_path, manifest, closure_identifier=closure_identifier)


@pytest.mark.parametrize("failure_position", (1, 2, 3, 4, 5))
def test_partial_hook_install_failure_exits_70_without_python_cleanup(
    tmp_path: Path, failure_position: int,
) -> None:
    sentinel = tmp_path / f"cleanup-{failure_position}"
    program = f'''\
import atexit
from pathlib import Path
from orev3.execution.bounded_streaming_worker_bootstrap import BoundedProjectImportSession
sentinel = Path({str(sentinel)!r})
atexit.register(lambda: sentinel.write_text("cleanup"))
count = 0
def assign(owner, name, value):
    global count
    count += 1
    if count == {failure_position}:
        raise RuntimeError("injected")
    setattr(owner, name, value)
BoundedProjectImportSession("/source", {{}}, hook_assignment=assign).__enter__()
'''
    completed = subprocess.run(
        (sys.executable, "-c", program), cwd=Path.cwd(),
        env=dict(os.environ, PYTHONPATH="src"), check=False,
    )
    assert completed.returncode == 70
    assert not sentinel.exists()


def test_invocation_owner_closes_only_owned_descriptors(tmp_path: Path) -> None:
    owned_read, owned_write = os.pipe()
    unrelated_read, unrelated_write = os.pipe()
    resources = BoundedInvocationResources([owned_read, owned_write])
    resources.fail_before_spawn()
    assert not _fd_open(owned_read) and not _fd_open(owned_write)
    assert _fd_open(unrelated_read) and _fd_open(unrelated_write)
    os.close(unrelated_read); os.close(unrelated_write)


def _fileinfo(raw: bytearray, fd_type: int, *, flags: int = os.O_RDONLY) -> None:
    struct.pack_into("=IIqiI", raw, 0, flags, 0, 0, fd_type, 0)


def _pipe_info(handle: int, peer: int, *, flags: int = os.O_RDONLY) -> bytes:
    raw = bytearray(184)
    _fileinfo(raw, 6, flags=flags)
    struct.pack_into("=QQii", raw, 160, handle, peer, 0, 0)
    return bytes(raw)


def _socket_info(handle: int, pcb: int) -> bytes:
    raw = bytearray(792)
    _fileinfo(raw, 2, flags=os.O_RDWR)
    struct.pack_into("=QQiii", raw, 160, handle, pcb, 1, 0, __import__("socket").AF_UNIX)
    return bytes(raw)


def _vnode_info(path: str, inode: int, *, character: bool = False) -> bytes:
    raw = bytearray(1200)
    _fileinfo(raw, 1)
    mode = (__import__("stat").S_IFCHR if character else __import__("stat").S_IFREG) | 0o600
    struct.pack_into("=IHHQII", raw, 24, 7, mode, 1, inode, os.getuid(), os.getgid())
    struct.pack_into("=i", raw, 160, 1)
    encoded = path.encode()
    raw[176:176 + len(encoded)] = encoded
    return bytes(raw)


def test_type_specific_darwin_fd_decoders_are_closed() -> None:
    assert decode_darwin_pipe_fdinfo(_pipe_info(10, 11))[0:3] == ("pipe", 10, 11)
    assert decode_darwin_socket_fdinfo(_socket_info(20, 21))[0:3] == ("socket", 20, 21)
    assert decode_darwin_vnode_fdinfo(_vnode_info("/private/request", 30), with_path=True)[1:4] == (7, 30, __import__("stat").S_IFREG | 0o600)
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        decode_darwin_pipe_fdinfo(_pipe_info(10, 11)[:-1])
    wrong = bytearray(_socket_info(20, 21)); struct.pack_into("=i", wrong, 16, 6)
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        decode_darwin_socket_fdinfo(bytes(wrong))


class _FakeFDProc:
    def __init__(self, *, mutate=False, alias=False):
        self.calls = 0
        self.mutate = mutate
        self.alias = alias

    def proc_pidinfo(self, _pid, flavor, _arg, buffer, _size):
        runtime = __import__("orev3.execution.runtime", fromlist=["_ProcFDInfo"])
        if flavor != runtime.PROC_PIDLISTFDS:
            raise AssertionError(flavor)
        self.calls += 1
        entries = __import__("ctypes").cast(buffer, __import__("ctypes").POINTER(runtime._ProcFDInfo))
        kinds = (1, 6, 6, 6, 2, 1, 1)
        for fd, kind in enumerate(kinds):
            entries[fd].proc_fd, entries[fd].proc_fdtype = fd, kind
        count = 7
        if self.alias or self.mutate and self.calls > 1:
            entries[7].proc_fd, entries[7].proc_fdtype = 7, 6
            count = 8
        return count * __import__("ctypes").sizeof(runtime._ProcFDInfo)

    def proc_pidfdinfo(self, _pid, fd, flavor, buffer, size):
        material = {
            0: _vnode_info("/dev/null", 1, character=True),
            1: _pipe_info(101, 201, flags=os.O_WRONLY),
            2: _pipe_info(102, 202, flags=os.O_WRONLY),
            3: _pipe_info(103, 203),
            4: _socket_info(104, 204),
            5: _vnode_info("/private/lease", 5),
            6: _vnode_info("/private/request", 6),
        }[fd]
        assert len(material) == size
        __import__("ctypes").memmove(buffer, material, size)
        return size


def test_live_fd_observation_build_is_exact_stable_and_rejects_aliases() -> None:
    observations = build_darwin_worker_fd_observations(101, libproc=_FakeFDProc())
    assert tuple(item.descriptor for item in observations) == tuple(range(7))
    assert observations[5].identity != observations[6].identity
    for candidate in (_FakeFDProc(alias=True), _FakeFDProc(mutate=True)):
        with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
            build_darwin_worker_fd_observations(101, libproc=candidate)


def test_live_pre_gate_orchestration_uses_authenticated_fd_observations(tmp_path: Path) -> None:
    value = _bootstrap_envelope(); raw = bootstrap_canonical_bytes(value)[:-1]
    artifact = create_bounded_bootstrap_request_artifact(
        tmp_path, raw, bootstrap_request_identity=value["bootstrap_request_identity"],
        operation_id=value["operation_id"], authority_generation=value["authority_generation"],
        execution_profile_identity=value["execution_profile_identity"],
    )
    wrapper = GovernedProcessObservation(GovernedProcessInstanceV1(100, 10, 1), 50, 100, 100, "/usr/bin/time")
    worker = GovernedProcessObservation(GovernedProcessInstanceV1(101, 10, 2), 100, 100, 100, "/usr/bin/python3")
    fds = build_darwin_worker_fd_observations(101, libproc=_FakeFDProc())
    wrapper_argv = ("/usr/bin/time", "-l", "/usr/bin/sandbox-exec")
    worker_argv = ("/usr/bin/python3", "-I", "-S", "/bootstrap", "--governed-fixed-fds-v1")
    read_fd, write_fd = os.pipe()
    try:
        authenticate_and_release_bounded_start_gate(
            wrapper_pid=100, expected_wrapper=wrapper, expected_worker=worker,
            expected_wrapper_argv=wrapper_argv, expected_worker_argv=worker_argv,
            expected_worker_fds=fds, gate_write_fd=write_fd, artifact=artifact,
            bootstrap_authenticator=lambda: None,
            group_query=lambda _group: (100, 101),
            process_query=lambda pid: wrapper if pid == 100 else worker,
            argv_query=lambda pid: wrapper_argv if pid == 100 else worker_argv,
            fd_query=lambda _pid: fds,
        )
        assert os.read(read_fd, 2) == b"\xa5"
        assert os.read(read_fd, 1) == b""
    finally:
        artifact.close(); os.close(read_fd)


def test_pre_gate_failure_closes_gate_without_release(tmp_path: Path) -> None:
    value = _bootstrap_envelope(); raw = bootstrap_canonical_bytes(value)[:-1]
    artifact = create_bounded_bootstrap_request_artifact(
        tmp_path, raw, bootstrap_request_identity=value["bootstrap_request_identity"],
        operation_id=value["operation_id"], authority_generation=value["authority_generation"],
        execution_profile_identity=value["execution_profile_identity"],
    )
    wrapper = GovernedProcessObservation(GovernedProcessInstanceV1(100, 10, 1), 50, 100, 100, "/usr/bin/time")
    worker = GovernedProcessObservation(GovernedProcessInstanceV1(101, 10, 2), 100, 100, 100, "/usr/bin/python3")
    read_fd, write_fd = os.pipe()
    try:
        with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
            authenticate_and_release_bounded_start_gate(
                wrapper_pid=100, expected_wrapper=wrapper, expected_worker=worker,
                expected_wrapper_argv=("wrapper",), expected_worker_argv=("worker",),
                expected_worker_fds=(), gate_write_fd=write_fd, artifact=artifact,
                bootstrap_authenticator=lambda: None,
                group_query=lambda _group: (100,),
            )
        assert os.read(read_fd, 1) == b""
    finally:
        artifact.close(); os.close(read_fd)


def test_post_spawn_pre_gate_cleanup_signals_only_closed_group_and_reaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrapper = GovernedProcessObservation(GovernedProcessInstanceV1(100, 10, 1), 50, 100, 100, "/usr/bin/time")
    worker = GovernedProcessObservation(GovernedProcessInstanceV1(101, 10, 2), 100, 100, 100, "/usr/bin/python3")
    owned_read, owned_write = os.pipe()
    class Handle:
        def __init__(self): self.waits = 0
        def wait(self):
            self.waits += 1
            return GovernedWaitStatus("signaled", 15)
    handle = Handle()
    resources = BoundedInvocationResources([owned_read, owned_write])
    resources.spawn_handle = handle
    signals = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    status = resources.fail_after_spawn_before_gate(
        wrapper=wrapper, worker=worker, current_members=(wrapper, worker), signal_number=15
    )
    assert status == GovernedWaitStatus("signaled", 15)
    assert signals == [(100, 15)] and handle.waits == 1
    assert not _fd_open(owned_read) and not _fd_open(owned_write)


def test_post_spawn_cleanup_refuses_substitution_but_still_reaps(monkeypatch: pytest.MonkeyPatch) -> None:
    wrapper = GovernedProcessObservation(GovernedProcessInstanceV1(100, 10, 1), 50, 100, 100, "/usr/bin/time")
    worker = GovernedProcessObservation(GovernedProcessInstanceV1(101, 10, 2), 100, 100, 100, "/usr/bin/python3")
    substituted = GovernedProcessObservation(GovernedProcessInstanceV1(101, 11, 2), 100, 100, 100, "/usr/bin/python3")
    class Handle:
        waits = 0
        def wait(self):
            self.waits += 1
            return GovernedWaitStatus("exited", 0)
    handle = Handle(); resources = BoundedInvocationResources([]); resources.spawn_handle = handle
    signals = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        resources.fail_after_spawn_before_gate(
            wrapper=wrapper, worker=worker, current_members=(wrapper, substituted), signal_number=15
        )
    assert signals == [] and handle.waits == 1


def test_pre_gate_controller_failure_has_single_gate_owner_and_reaper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _bootstrap_envelope(); raw = bootstrap_canonical_bytes(value)[:-1]
    artifact = create_bounded_bootstrap_request_artifact(
        tmp_path, raw, bootstrap_request_identity=value["bootstrap_request_identity"],
        operation_id=value["operation_id"], authority_generation=value["authority_generation"],
        execution_profile_identity=value["execution_profile_identity"],
    )
    wrapper = GovernedProcessObservation(GovernedProcessInstanceV1(100, 10, 1), 50, 100, 100, "/usr/bin/time")
    worker = GovernedProcessObservation(GovernedProcessInstanceV1(101, 10, 2), 100, 100, 100, "/usr/bin/python3")
    class Handle:
        waits = 0
        def wait(self): self.waits += 1; return GovernedWaitStatus("signaled", 15)
    read_fd, write_fd = os.pipe(); handle = Handle()
    resources = BoundedInvocationResources([write_fd], request_artifact=artifact, spawn_handle=handle)
    signals = []; monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
        orchestrate_bounded_pre_gate_authentication(
            resources=resources, wrapper=wrapper, worker=worker,
            gate_write_fd=write_fd, artifact=artifact,
            expected_wrapper_argv=("wrapper",), expected_worker_argv=("worker",),
            expected_worker_fds=(), bootstrap_authenticator=lambda: None,
            group_query=lambda _group: (100,),
            process_query=lambda _pid: wrapper,
            argv_query=lambda _pid: (), fd_query=lambda _pid: (),
        )
    assert os.read(read_fd, 1) == b""
    assert handle.waits == 1 and signals == [(100, 15)]
    assert resources.descriptors == [] and resources.request_artifact is None
    os.close(read_fd)


@pytest.mark.parametrize("mutation", ("delete", "replace", "original", "cross"))
def test_hook_mutation_after_session_entry_exits_70(tmp_path: Path, mutation: str) -> None:
    sentinel = tmp_path / mutation
    program = f'''\
import _thread, atexit, threading
from pathlib import Path
from orev3.execution.bounded_streaming_worker_bootstrap import BoundedProjectImportSession
sentinel = Path({str(sentinel)!r}); atexit.register(lambda: sentinel.write_text("cleanup"))
session = BoundedProjectImportSession("/source", {{}}).__enter__()
if {mutation!r} == "delete": del threading.Thread.start
elif {mutation!r} == "replace": threading.Thread.start = lambda self: None
elif {mutation!r} == "original": threading.Thread.start = session.original_hooks[0]
else: threading.Thread.start = session.denials[1]
session.check()
'''
    completed = subprocess.run((sys.executable, "-c", program), cwd=Path.cwd(), env=dict(os.environ, PYTHONPATH="src"), check=False)
    assert completed.returncode == 70
    assert not sentinel.exists()


@pytest.mark.parametrize("mutation", ("insert", "remove", "replace", "reorder"))
def test_model_b_meta_path_mutations_fail_and_restore(mutation: str) -> None:
    original = tuple(sys.meta_path)
    with pytest.raises(BoundedProjectImportError):
        with BoundedProjectImportSession("/source", {}) as session:
            if mutation == "insert": sys.meta_path.insert(1, object())
            elif mutation == "remove": sys.meta_path.pop(0)
            elif mutation == "replace": sys.meta_path[0] = object()
            else: sys.meta_path[:] = list(reversed(sys.meta_path))
            session.check()
    assert tuple(sys.meta_path) == original


@pytest.mark.parametrize("mutation", ("foreign", "shell_replace", "shell_delete", "forged_mapped"))
def test_model_b_cache_mutations_fail_and_restore(mutation: str) -> None:
    import types
    original = {
        name: value for name, value in sys.modules.items()
        if name == "orev3" or name.startswith("orev3.")
    }
    module_map = {"orev3.execution.fake_bounded": {"path": "src/fake.py"}}
    with pytest.raises(BoundedProjectImportError):
        with BoundedProjectImportSession("/source", module_map) as session:
            if mutation == "foreign": sys.modules["orev3.unauthorized"] = types.ModuleType("orev3.unauthorized")
            elif mutation == "shell_replace": sys.modules["orev3"] = types.ModuleType("orev3")
            elif mutation == "shell_delete": del sys.modules["orev3"]
            else: sys.modules["orev3.execution.fake_bounded"] = types.ModuleType("orev3.execution.fake_bounded")
            session.check()
    restored = {
        name: value for name, value in sys.modules.items()
        if name == "orev3" or name.startswith("orev3.")
    }
    assert set(restored) == set(original)
    assert all(restored[name] is value for name, value in original.items())


def test_preexisting_raw_thread_exits_70_before_session_mutation(tmp_path: Path) -> None:
    sentinel = tmp_path / "cleanup"
    program = f'''\
import _thread, atexit, time
from pathlib import Path
from orev3.execution.bounded_streaming_worker_bootstrap import BoundedProjectImportSession
sentinel = Path({str(sentinel)!r})
atexit.register(lambda: sentinel.write_text("cleanup"))
ready = _thread.allocate_lock(); ready.acquire()
stop = _thread.allocate_lock(); stop.acquire()
def worker():
    ready.release(); stop.acquire()
_thread.start_new_thread(worker, ())
ready.acquire()
BoundedProjectImportSession("/source", {{}}).__enter__()
'''
    completed = subprocess.run(
        (sys.executable, "-c", program), cwd=Path.cwd(),
        env=dict(os.environ, PYTHONPATH="src"), check=False, timeout=10,
    )
    assert completed.returncode == 70
    assert not sentinel.exists()


def test_mid_session_raw_thread_exits_70_without_cleanup(tmp_path: Path) -> None:
    sentinel = tmp_path / "cleanup"
    program = f'''\
import _thread, atexit
from pathlib import Path
from orev3.execution.bounded_streaming_worker_bootstrap import BoundedProjectImportSession
sentinel = Path({str(sentinel)!r})
atexit.register(lambda: sentinel.write_text("cleanup"))
original = _thread.start_new_thread
session = BoundedProjectImportSession("/source", {{}}).__enter__()
ready = _thread.allocate_lock(); ready.acquire()
stop = _thread.allocate_lock(); stop.acquire()
def worker():
    ready.release(); stop.acquire()
original(worker, ())
ready.acquire()
session.check()
'''
    completed = subprocess.run(
        (sys.executable, "-c", program), cwd=Path.cwd(),
        env=dict(os.environ, PYTHONPATH="src"), check=False, timeout=10,
    )
    assert completed.returncode == 70
    assert not sentinel.exists()


def test_all_five_thread_start_routes_are_denied_and_restored() -> None:
    import _thread, threading
    originals = (
        threading.Thread.start, threading._start_joinable_thread,
        _thread.start_new_thread, _thread.start_new, _thread.start_joinable_thread,
    )
    with BoundedProjectImportSession("/source", {}) as session:
        assert session.state == session.MUTATED
        for (owner, name), denial in zip(session.hooks, session.denials):
            assert getattr(owner, name) is denial
            with pytest.raises(BoundedProjectImportError):
                denial()
    assert (
        threading.Thread.start, threading._start_joinable_thread,
        _thread.start_new_thread, _thread.start_new, _thread.start_joinable_thread,
    ) == originals


def test_preexisting_raw_joinable_thread_exits_70_when_available(tmp_path: Path) -> None:
    sentinel = tmp_path / "cleanup-joinable"
    program = f'''\
import _thread, atexit
from pathlib import Path
from orev3.execution.bounded_streaming_worker_bootstrap import BoundedProjectImportSession
sentinel = Path({str(sentinel)!r}); atexit.register(lambda: sentinel.write_text("cleanup"))
ready = _thread.allocate_lock(); ready.acquire(); stop = _thread.allocate_lock(); stop.acquire()
def worker(): ready.release(); stop.acquire()
_thread.start_joinable_thread(worker)
ready.acquire()
BoundedProjectImportSession("/source", {{}}).__enter__()
'''
    completed = subprocess.run(
        (sys.executable, "-c", program), cwd=Path.cwd(),
        env=dict(os.environ, PYTHONPATH="src"), check=False, timeout=10,
    )
    assert completed.returncode == 70
    assert not sentinel.exists()


def test_gate_state_requires_every_authentication_in_frozen_order(tmp_path: Path) -> None:
    value = _bootstrap_envelope()
    raw = bootstrap_canonical_bytes(value)[:-1]
    artifact = create_bounded_bootstrap_request_artifact(
        tmp_path, raw,
        bootstrap_request_identity=value["bootstrap_request_identity"],
        operation_id=value["operation_id"],
        authority_generation=value["authority_generation"],
        execution_profile_identity=value["execution_profile_identity"],
    )
    read_fd, write_fd = os.pipe()
    try:
        state = BoundedGateReleaseState()
        with pytest.raises(Exception, match="RESOURCE_PROCESS_INSTANCE_MISMATCH"):
            state.authenticate("worker")
        for stage in state.REQUIRED:
            state.authenticate(stage)
        state.release(write_fd, artifact)
        assert os.read(read_fd, 2) == b"\xa5"
        assert os.read(read_fd, 1) == b""
    finally:
        artifact.close()
        os.close(read_fd)


def test_model_b_session_tracks_shell_and_module_object_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    module_map = {name: {"path": path} for name, path in MODEL_B_MODULE_PATHS}
    original_project = {
        name: module for name, module in sys.modules.items()
        if name == "orev3" or name.startswith("orev3.")
    }
    with BoundedProjectImportSession("/private/source", module_map) as session:
        assert set(session.shell_objects) == set(SYNTHETIC_PACKAGES)
        session.check()
        sys.modules["orev3"] = type(sys)("orev3")
        with pytest.raises(BoundedProjectImportError):
            session.check()
        sys.modules["orev3"] = session.shell_objects["orev3"]
    restored = {
        name: module for name, module in sys.modules.items()
        if name == "orev3" or name.startswith("orev3.")
    }
    assert set(restored) == set(original_project)
    assert all(restored[name] is module for name, module in original_project.items())


def _schemas(source: Path) -> tuple[Path, Path]:
    projection_properties = {"candidates": {"items": {"type": "integer"}, "minItems": 1, "type": "array", "uniqueItems": True}, "eligible": {"type": "boolean"}, "exclusion_reason": {"enum": ["missing_observation", "not_applicable"], "type": "string"}, "observation_index": {"minimum": 0, "type": "integer"}, "source_unit_key": {"pattern": "^[a-z0-9-]+$", "type": "string"}}
    projection = {"additionalProperties": False, "properties": projection_properties, "required": sorted(projection_properties), "type": "object"}
    raw_properties = {**projection_properties, "outcome": {"type": "string"}}
    raw = {"additionalProperties": False, "properties": raw_properties, "required": sorted(raw_properties), "type": "object"}
    raw_path = source / "raw-schema.json"; raw_path.write_bytes(canonical_bytes(raw))
    projection_path = source / "projection-schema.json"; projection_path.write_bytes(canonical_bytes(projection))
    return raw_path, projection_path


def _synthetic_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree("src", root / "src")
    (root / "tests").mkdir()
    subprocess.run(("git", "init", "-q", str(root)), check=True)
    subprocess.run(("git", "-C", str(root), "config", "user.email", "test@example.invalid"), check=True)
    subprocess.run(("git", "-C", str(root), "config", "user.name", "Test"), check=True)
    return root


def _commit(source: Path) -> str:
    subprocess.run(("git", "-C", str(source), "add", "."), check=True)
    subprocess.run(("git", "-C", str(source), "commit", "-qm", "fixture"), check=True)
    return subprocess.run(("git", "-C", str(source), "rev-parse", "HEAD"), check=True, stdout=subprocess.PIPE, text=True).stdout.strip()


def _policy() -> dict[str, object]:
    return parse_canonical_bytes(Path("config/research/readiness/evidence-preparation-policy-v1.json").read_bytes())


def _worker_args(source: Path, source_commit: str) -> dict[str, object]:
    return {
        "dependency_root": _dependencies(),
        "runtime_contract_identity": "1" * 64,
        "dependency_environment_identity": "2" * 64,
        "capability_policy": _policy(),
    }


def _dependencies() -> Path:
    return Path(pytest.__file__).resolve().parent.parent


def test_readiness_worker_has_real_network_denial_and_no_ambient_plugins(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_network.py").write_text(
        "import errno, socket\n"
        "def test_denied():\n"
        "    for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):\n"
        "        try:\n"
        "            candidate = socket.socket(socket.AF_INET, kind)\n"
        "            candidate.connect(('127.0.0.1', 9))\n"
        "        except PermissionError as exc:\n"
        "            assert exc.errno == errno.EPERM\n"
        "        else:\n"
        "            raise AssertionError('network was not structurally denied')\n",
        encoding="utf-8",
    )
    source_commit = _commit(source)
    result = run_phase3b_worker(source, source_commit, "READINESS_TEST", "readiness_test_worker.py", {"command": "run_exact", "selectors": ["tests/test_network.py"]}, timeout_seconds=30, **_worker_args(source, source_commit)).result
    assert result["exit_code"] == 0
    assert result["results"] == [{"node_id": "tests/test_network.py::test_denied", "status": "passed"}]


def test_projection_worker_is_deterministic_and_replay_worker_cannot_read_raw_store(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    raw_store = tmp_path / "raw"; raw_store.mkdir()
    raw = raw_store / "input"; raw.write_text('{"candidates":[1,2],"eligible":true,"exclusion_reason":"not_applicable","observation_index":0,"outcome":"secret","source_unit_key":"unit-a"}\n', encoding="utf-8")
    raw_schema, projection_schema = _schemas(source)
    source_commit = _commit(source)
    projection, projector_ids, _ = reconstruct_projection_twice(source_root=source, dependency_root=_dependencies(), raw_snapshot=raw, raw_schema_path=raw_schema, projection_schema_path=projection_schema, expected_raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), expected_raw_size=raw.stat().st_size, max_raw_bytes=10000, max_projection_bytes=10000, max_records=10, source_commit=source_commit, runtime_contract_identity="1" * 64, dependency_environment_identity="2" * 64, capability_policy=_policy(), raw_snapshot_identity="3" * 64)
    assert b"secret" not in projection
    assert len(projector_ids) == 2
    projection_path = tmp_path / "projection"; projection_path.write_bytes(projection)
    replay, replay_ids = reconstruct_replay_twice(source_root=source, dependency_root=_dependencies(), projection_path=projection_path, projection_schema_path=projection_schema, raw_store_root=raw_store, request_material={"allowed_exclusion_reasons": [], "candidate_order": [1, 2], "configuration_identity": "1" * 64, "dataset_identity": "2" * 64, "expected_projection_sha256": hashlib.sha256(projection).hexdigest(), "expected_projection_size": len(projection), "max_projection_bytes": 10000, "max_units": 10, "projection_identity": "3" * 64, "projection_schema_path": str(projection_schema), "selector_identifier": "latest-eligible-observation-selector-v1", "selector_component_identity": "4" * 64, "replay_preparer_component_identity": "5" * 64}, source_commit=source_commit, runtime_contract_identity="1" * 64, dependency_environment_identity="2" * 64, capability_policy=_policy(), projection_identity="3" * 64)
    assert b"replay_evidence_identity" in replay
    assert len(replay_ids) == 2


def test_projector_rejection_does_not_propagate_outcome_sentinel(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    raw_schema, projection_schema = _schemas(source)
    raw = tmp_path / "malformed-raw"
    raw.write_text(
        '{"candidates":[1,2],"eligible":true,"exclusion_reason":"not_applicable",'
        '"observation_index":0,"outcome":"OUTCOME-LEAK-SENTINEL",'
        '"source_unit_key":"unit-a","unexpected":"OUTCOME-LEAK-SENTINEL"}\n',
        encoding="utf-8",
    )
    source_commit = _commit(source)
    output = tmp_path / "projection-output"
    request = {
        "command": "project_canonical_jsonl",
        "expected_raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "expected_raw_size": raw.stat().st_size,
        "max_projection_bytes": 10_000,
        "max_raw_bytes": 10_000,
        "max_records": 10,
        "private_output": str(output),
        "projection_schema_path": str(projection_schema),
        "raw_schema_path": str(raw_schema),
        "raw_snapshot": str(raw),
    }
    with pytest.raises(Exception, match="PROJECTION_INVALID") as failure:
        run_phase3b_worker(
            source,
            source_commit,
            "INPUT_PROJECTOR",
            "input_projection_worker.py",
            request,
            read_files=(raw, raw_schema, projection_schema),
            write_roots=(tmp_path,),
            **_worker_args(source, source_commit),
        )
    assert "OUTCOME-LEAK-SENTINEL" not in str(failure.value)
    assert not output.exists()


def test_worker_names_and_pytest_arguments_are_not_caller_extensible(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    source_commit = _commit(source)
    with pytest.raises(Exception, match="not permitted"):
        run_phase3b_worker(source, source_commit, "ARBITRARY", "arbitrary.py", {}, **_worker_args(source, source_commit))
    with pytest.raises(Exception, match="requires exact readiness-test files"):
        run_phase3b_worker(source, source_commit, "READINESS_TEST", "readiness_test_worker.py", {"command": "run_exact", "selectors": ["--pyargs"]}, **_worker_args(source, source_commit))
    from orev3.execution.readiness_test_worker import _valid_selector

    assert _valid_selector("tests/test_ready.py::test_ok")
    assert _valid_selector(
        "tests/execution/test_attempts.py::"
        "test_repository_authority_identifier_is_closed[bad\\\\path]"
    )
    assert _valid_selector(
        "tests/execution/test_phase3c_schema_registry.py::"
        "test_allocation_authority_identifier_rejects_noncanonical_grammar"
        "[authority\\\\value]"
    )
    for unsafe_selector in (
        "tests\\test_ready.py::test_ok",
        "/tests/test_ready.py::test_ok",
        "tests/../test_ready.py::test_ok",
        "tests/./test_ready.py::test_ok",
        "tests//test_ready.py::test_ok",
        "tests/\x00test_ready.py::test_ok",
        "tests/test_ready.py::test\x00value",
        "--pyargs",
        "tests/test_ready.py::",
        "outside/test_ready.py::test_ok",
        "tests/../outside.py::test_ok",
    ):
        assert not _valid_selector(unsafe_selector)


@pytest.mark.parametrize(
    ("worker_kind", "worker_name", "forbidden_module", "request_material"),
    (
        ("READINESS_TEST", "readiness_test_worker.py", "orev3.execution.projection", {"command": "collect", "selectors": ["tests/test_dummy.py"]}),
        ("INPUT_PROJECTOR", "input_projection_worker.py", "orev3.execution.replay_preparation", {"command": "project_canonical_jsonl"}),
        ("REPLAY_PREPARATION", "replay_preparation_worker.py", "orev3.execution.projection", {"command": "reconstruct_replay"}),
    ),
)
def test_semantic_worker_code_projection_denies_cross_capability_import(
    tmp_path: Path, worker_kind: str, worker_name: str, forbidden_module: str, request_material: dict[str, str]
) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_dummy.py").write_text("def test_dummy(): assert True\n", encoding="utf-8")
    path = source / "src/orev3/execution" / worker_name
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("COMMANDS =", f"import {forbidden_module}\nCOMMANDS =", 1), encoding="utf-8")
    source_commit = _commit(source)
    with pytest.raises(Exception, match="READINESS_TEST_FAILED|PROJECTION_INVALID|REPLAY_IDENTITY_MISMATCH"):
        run_phase3b_worker(source, source_commit, worker_kind, worker_name, request_material, **_worker_args(source, source_commit))


def test_exact_readiness_test_policy_passes_only_all_passed_nodes(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_ready.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    source_commit = _commit(source)
    nodes = ["tests/test_ready.py::test_ok"]
    collection_identity = domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": nodes})
    evidence, worker_ids = run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_ready.py"], additional_selectors=[], expected_mandatory_collection_identity=collection_identity, expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(), timeout_seconds=30, max_output_bytes=65536)
    assert evidence["results"] == [{"node_id": "tests/test_ready.py::test_ok", "status": "passed"}]
    assert len(worker_ids) == 3

    (source / "tests/execution").mkdir()
    (source / "tests/execution/test_attempts.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', ['bad\\\\path'], ids=['bad\\\\path'])\n"
        "def test_repository_authority_identifier_is_closed(value):\n"
        "    assert value == 'bad\\\\path'\n",
        encoding="utf-8",
    )
    (source / "tests/execution/test_phase3c_schema_registry.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', ['authority\\\\value'], ids=['authority\\\\value'])\n"
        "def test_allocation_authority_identifier_rejects_noncanonical_grammar(value):\n"
        "    assert value == 'authority\\\\value'\n",
        encoding="utf-8",
    )
    source_commit = _commit(source)
    exact_nodes = [
        "tests/execution/test_attempts.py::"
        "test_repository_authority_identifier_is_closed[bad\\\\path]",
        "tests/execution/test_phase3c_schema_registry.py::"
        "test_allocation_authority_identifier_rejects_noncanonical_grammar"
        "[authority\\\\value]",
    ]
    exact_collection_identity = domain_identity(
        READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": exact_nodes}
    )
    exact_evidence, exact_worker_ids = run_readiness_tests(
        source_root=source,
        dependency_root=_dependencies(),
        source_commit=source_commit,
        environment_identity="1" * 64,
        runtime_contract_identity="2" * 64,
        capability_policy=_policy(),
        mandatory_selectors=[
            "tests/execution/test_attempts.py",
            "tests/execution/test_phase3c_schema_registry.py",
        ],
        additional_selectors=[],
        expected_mandatory_collection_identity=exact_collection_identity,
        expected_mandatory_node_count=2,
        expected_additional_nodes=[],
        policy_identity="3" * 64,
        denied_input_roots=(),
        timeout_seconds=30,
        max_output_bytes=65536,
    )
    assert exact_evidence["collected_node_ids"] == exact_nodes
    assert exact_evidence["results"] == [
        {"node_id": node, "status": "passed"} for node in exact_nodes
    ]
    assert len(exact_worker_ids) == 3

    (source / "tests/test_ready.py").write_text("import pytest\n@pytest.mark.skip(reason='no')\ndef test_skip(): pass\n", encoding="utf-8")
    source_commit = _commit(source)
    with pytest.raises(Exception, match="TEST_COLLECTION_MISMATCH"):
        run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_ready.py"], additional_selectors=[], expected_mandatory_collection_identity=collection_identity, expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(), timeout_seconds=30, max_output_bytes=65536)


def test_malicious_conftest_cannot_consistently_hide_mandatory_test(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    (source / "tests/test_mandatory.py").write_text("def test_mandatory_failure(): assert False\n", encoding="utf-8")
    (source / "tests/conftest.py").write_text("def pytest_collection_modifyitems(items): items[:] = []\n", encoding="utf-8")
    source_commit = _commit(source)
    expected = ["tests/test_mandatory.py::test_mandatory_failure"]
    with pytest.raises(Exception, match="TEST_COLLECTION_MISMATCH"):
        run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_mandatory.py"], additional_selectors=[], expected_mandatory_collection_identity=domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": expected}), expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(), timeout_seconds=30, max_output_bytes=65536)


def test_readiness_worker_cannot_open_known_scientific_locator(tmp_path: Path) -> None:
    source = _synthetic_source(tmp_path)
    secret = tmp_path / "scientific-input"; secret.write_text("outcome", encoding="utf-8")
    (source / "tests/test_capability.py").write_text(
        "import errno\nfrom pathlib import Path\n"
        f"def test_denied():\n    try: Path({str(secret)!r}).read_bytes()\n    except PermissionError as exc: assert exc.errno == errno.EPERM\n    else: raise AssertionError('scientific locator was readable')\n",
        encoding="utf-8",
    )
    source_commit = _commit(source)
    expected = ["tests/test_capability.py::test_denied"]
    evidence, _ = run_readiness_tests(source_root=source, dependency_root=_dependencies(), source_commit=source_commit, environment_identity="1" * 64, runtime_contract_identity="2" * 64, capability_policy=_policy(), mandatory_selectors=["tests/test_capability.py"], additional_selectors=[], expected_mandatory_collection_identity=domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": expected}), expected_mandatory_node_count=1, expected_additional_nodes=[], policy_identity="3" * 64, denied_input_roots=(secret,), timeout_seconds=30, max_output_bytes=65536)
    assert evidence["results"][0]["status"] == "passed"


@pytest.mark.parametrize(
    ("worker_kind", "worker_name", "command"),
    (
        ("READINESS_TEST", "readiness_test_worker.py", "collect"),
        ("INPUT_PROJECTOR", "input_projection_worker.py", "project_canonical_jsonl"),
        ("REPLAY_PREPARATION", "replay_preparation_worker.py", "reconstruct_replay"),
    ),
)
def test_real_sibling_profiles_deny_network_and_cross_capability_reads(
    tmp_path: Path, worker_kind: str, worker_name: str, command: str
) -> None:
    source = _synthetic_source(tmp_path)
    dependency = _dependencies()
    capability = tmp_path / "allowed-object"
    capability.write_text("allowed", encoding="utf-8")
    denied = tmp_path / "other-capability"
    denied.write_text("denied", encoding="utf-8")
    private = tmp_path / "sandbox-private"
    (private / "home").mkdir(parents=True)
    (private / "tmp").mkdir()
    request = private / "request.json"
    request.write_text("{}", encoding="utf-8")
    profile, _ = render_phase3b_sandbox_profile(
        policy=_policy(),
        worker_kind=worker_kind,
        worker_name=worker_name,
        command=command,
        source_root=source,
        dependency_root=dependency,
        request_path=request,
        temporary_root=private,
        read_files=(capability,),
    )
    probe = (
        "import errno,socket;from pathlib import Path;"
        f"assert Path({str(capability)!r}).read_text()=='allowed';"
        "\ntry:\n Path(" + repr(str(source / "src/orev3/execution" / worker_name)) + ").write_text('changed');raise AssertionError('worker code writable')"
        "\nexcept PermissionError as exc:\n assert exc.errno==errno.EPERM"
        "\ntry:\n Path(" + repr(str(denied)) + ").read_bytes();raise AssertionError('cross capability readable')"
        "\nexcept PermissionError as exc:\n assert exc.errno==errno.EPERM"
        "\nfor kind in (socket.SOCK_STREAM,socket.SOCK_DGRAM):"
        "\n try:\n  s=socket.socket(socket.AF_INET,kind);s.connect(('127.0.0.1',9));raise AssertionError('network available')"
        "\n except PermissionError as exc:\n  assert exc.errno==errno.EPERM\n"
    )
    completed = subprocess.run(
        (str(MACOS_SANDBOX_EXEC), "-p", profile, str(Path(sys.executable).resolve()), "-I", "-S", "-c", probe),
        cwd=source,
        env=sanitized_worker_environment(private),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")


@pytest.fixture(autouse=True)
def _synthetic_controller_acquisition_policy():
    # These direct-library fixtures are synthetic controller callers.
    from orev3.execution.runtime import controller_acquisition_policy
    with controller_acquisition_policy():
        yield


def _synthetic_parent_owner(*args, owner, **kwargs):
    from orev3.execution.filesystem_capability import DescriptorAcquisition, PinnedDirectory
    cell = DescriptorAcquisition(None, 0, 0, None)
    cell.descriptor = 100
    owner.cells.append(cell)
    return PinnedDirectory(cell, Path("/synthetic"), owner)


def _call_owned_helper(helper, path, *, error_code):
    from orev3.execution.filesystem_capability import DescriptorOwner
    with DescriptorOwner(error_code) as owner:
        return helper(path, owner=owner, error_code=error_code)


# Cross-layer acquisition lifetime: only synthetic resources and isolated actors.
@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("point", ["busy", "entries", "anchor", "child"])
def test_acquisition_lifetime_namespace_entry_safety(tmp_path, exception, point):
    import orev3.execution.runtime as runtime
    import orev3.execution.filesystem_capability as capability
    anchor = tmp_path.resolve() / "anchor"
    anchor.mkdir(mode=0o700)
    sentinel = exception("entry acquisition")
    namespace = runtime.ControllerOperationNamespace(anchor)
    armed = True
    acquired = []

    def trace(frame, event, arg):
        nonlocal armed
        if not armed:
            return trace
        if event == "return" and frame.f_code is capability.DescriptorAcquisition.acquire.__code__:
            cell = frame.f_locals["self"]
            if cell.descriptor is not None:
                acquired.append(cell.descriptor)
            if point == "anchor" or (point == "child" and len(acquired) == 2):
                armed = False
                sys.settrace(None)
                raise sentinel
        if event == "line" and frame.f_code is runtime.ControllerOperationNamespace._locked_resources.__wrapped__.__code__:
            line = __import__("linecache").getline(frame.f_code.co_filename, frame.f_lineno).strip()
            if (point == "busy" and line == "self._entries = []" and namespace._busy) or (point == "entries" and line == "self._uid = os.geteuid()"):
                armed = False
                sys.settrace(None)
                raise sentinel
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(exception) as caught:
            namespace.recover()
    finally:
        sys.settrace(None)
    assert caught.value is sentinel
    assert not namespace._busy and not namespace._descriptors.pending
    assert not namespace.unresolved_closes
    assert runtime._CONTROLLER_INTERVAL.current is None
    for fd in set(acquired):
        with pytest.raises(OSError):
            os.fstat(fd)
    assert namespace.recover().live_operations == ()


@pytest.mark.parametrize("kind", ["directory", "regular"])
@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("point", ["known", "return", "received"])
def test_acquisition_lifetime_helper_handoff(tmp_path, kind, exception, point):
    import orev3.execution.filesystem_capability as cap
    path = tmp_path.resolve() if kind == "directory" else tmp_path.resolve() / "input"
    if kind == "regular":
        path.write_bytes(b"input")
    helper = cap.open_pinned_directory if kind == "directory" else cap.open_pinned_regular
    owner = cap.DescriptorOwner("INPUT_MISMATCH")
    sentinel = exception("handoff")
    armed = True
    live_at_fault = []

    def trace(frame, event, arg):
        nonlocal armed
        target = cap.DescriptorAcquisition.acquire if point == "known" else helper
        if armed and point != "received" and event == "return" and frame.f_code is target.__code__:
            armed = False
            live_at_fault.extend(owner.pending)
            assert live_at_fault
            for fd in live_at_fault:
                os.fstat(fd)
            sys.settrace(None)
            raise sentinel
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(exception) as caught:
            with owner:
                result = helper(path, owner=owner, error_code="INPUT_MISMATCH")
                if point == "received":
                    live_at_fault.extend(owner.pending)
                    raise sentinel
    finally:
        sys.settrace(None)
    assert caught.value is sentinel and not owner.pending and not owner.unresolved
    for fd in live_at_fault:
        with pytest.raises(OSError):
            os.fstat(fd)


def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
def test_acquisition_lifetime_nested_coalesced_delivery(exception):
    import orev3.execution.runtime as runtime
    policy = runtime._CONTROLLER_ACQUISITION
    first = exception("first")
    with pytest.raises(exception) as caught:
        def _acquisition_body_25():
            def _acquisition_body_26():
                policy.request(first)
                policy.request(exception("coalesced"))
            _invoke_policy_work(policy, _acquisition_body_26)
            assert policy.depth == 1 and policy.pending is not None
        _invoke_policy_work(policy, _acquisition_body_25)
    assert caught.value is first
    assert policy.depth == 0 and policy.pending is None and not policy.delivering


def test_acquisition_lifetime_request_during_delivery_is_subsumed():
    import signal
    import orev3.execution.runtime as runtime
    policy = runtime._CONTROLLER_ACQUISITION
    original = signal.getsignal(signal.SIGUSR1)
    seen = []
    sentinel = KeyboardInterrupt("delivered")
    def handler(number, frame):
        seen.append(number)
        policy.request(SystemExit("subsumed"))
        raise sentinel
    signal.signal(signal.SIGUSR1, handler)
    try:
        with pytest.raises(KeyboardInterrupt) as caught:
            def _acquisition_body_27():
                os.kill(os.getpid(), signal.SIGUSR1)
                os.kill(os.getpid(), signal.SIGUSR1)
            _invoke_policy_work(policy, _acquisition_body_27)
        assert caught.value is sentinel and seen == [signal.SIGUSR1]
        assert policy.pending is None and not policy.delivering and policy.depth == 0
    finally:
        signal.signal(signal.SIGUSR1, original)


def _acquisition_actor_script(actor, scenario, exception):
    return f'''
import os, sys, signal, atexit, pathlib
from orev3.execution.filesystem_capability import DescriptorOwner, pinned_acquisition_policy
actor = {actor!r}
scenario = {scenario!r}
if actor == 'controller':
 from orev3.execution.runtime import _CONTROLLER_ACQUISITION as policy
else:
 module = __import__('orev3.execution.' + actor + '_worker', fromlist=['_pinned_input_acquisition'])
 policy = module._pinned_input_acquisition
residue = pathlib.Path(sys.argv[1])
residue.write_bytes(b'non-authoritative residue')
atexit.register(lambda: print('ATEXIT', flush=True))
real_open, real_dup = os.open, os.dup
source = real_open(residue, os.O_RDONLY)
if scenario == 'systemexit_signal':
 def raising(number, frame): raise SystemExit(0)
 signal.signal(signal.SIGINT, raising)
armed = True
def inject(frame, event, arg):
 global armed
 target = real_dup if scenario == 'dup' else real_open
 if armed and event == 'c_return' and arg is target:
  armed = False
  sys.setprofile(None)
  if scenario in ('signal', 'systemexit_signal'):
   os.kill(os.getpid(), signal.SIGINT)
  else:
   raise {exception}('unreceived acquisition')
print('ARMED:' + actor + ':' + scenario, flush=True)
with pinned_acquisition_policy(policy):
 try:
  with DescriptorOwner('INPUT_MISMATCH') as owner:
   if scenario != 'ordinary': sys.setprofile(inject)
   if scenario == 'dup': owner.duplicate(source)
   else: owner.open(str(residue) if scenario != 'ordinary' else str(residue) + '.missing', os.O_RDONLY)
 except BaseException:
  sys.setprofile(None)
  print('KNOWN_FAILURE', flush=True)
 else:
  print('SUCCESS', flush=True)
os.close(source)
'''


@pytest.mark.parametrize("actor", ["controller", "input_projection", "replay_preparation"])
@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "SystemExit", "BaseException"])
@pytest.mark.parametrize("scenario", ["profile", "signal", "systemexit_signal", "ordinary"])
def test_acquisition_lifetime_terminal_readiness(tmp_path, actor, exception, scenario):
    residue = tmp_path / "residue"
    run = subprocess.run([sys.executable, "-B", "-c", _acquisition_actor_script(actor, scenario, exception), str(residue)], capture_output=True, text=True, timeout=20)
    terminal = scenario == "profile" or (actor != "controller" and scenario in {"signal", "systemexit_signal"})
    assert run.returncode == ((12 if actor == "controller" else 10) if terminal else 0), run.stderr
    assert run.stdout.startswith(f"ARMED:{actor}:{scenario}\n")
    assert "SUCCESS" not in run.stdout
    assert ("KNOWN_FAILURE" not in run.stdout) == terminal
    assert ("ATEXIT" not in run.stdout) == terminal
    assert residue.read_bytes() == b"non-authoritative residue"
    assert not run.stderr


@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "SystemExit", "BaseException"])
def test_acquisition_lifetime_controller_unknown_dup(tmp_path, exception):
    run = subprocess.run([sys.executable, "-B", "-c", _acquisition_actor_script("controller", "dup", exception), str(tmp_path / "residue")], capture_output=True, text=True, timeout=20)
    assert run.returncode == 12 and run.stdout == "ARMED:controller:dup\n", run.stderr


@pytest.mark.parametrize("worker", ["input_projection", "replay_preparation"])
def test_acquisition_lifetime_worker_refuses_writable_or_dup(tmp_path, worker):
    import importlib
    from orev3.execution.filesystem_capability import DescriptorOwner, pinned_acquisition_policy
    module = importlib.import_module("orev3.execution." + worker + "_worker")
    with pinned_acquisition_policy(module._pinned_input_acquisition), DescriptorOwner("PROJECTION_INVALID") as owner:
        with pytest.raises(ValueError, match="PROJECTION_INVALID"):
            owner.open(tmp_path / "forbidden", os.O_WRONLY | os.O_CREAT)
        with pytest.raises(ValueError, match="PROJECTION_INVALID"):
            owner.duplicate(0)
        assert not owner.pending and not module._PINNED_INPUT_FAILED
    assert not (tmp_path / "forbidden").exists()


@pytest.mark.parametrize("point", ["initial", "delayed"])
@pytest.mark.parametrize("fault", ["normal", "missing", "known", "unknown"])
def test_acquisition_lifetime_replay_delayed_readiness(tmp_path, point, fault):
    script = r'''
import pathlib,sys,os,hashlib
from orev3.execution.replay_preparation import load_verified_projection
from orev3.execution.replay_preparation_worker import _pinned_input_acquisition
from orev3.execution.filesystem_capability import pinned_acquisition_policy,DescriptorAcquisition
p=pathlib.Path(sys.argv[1]);p.write_bytes(b'{}\n')
point,fault=sys.argv[2:]
def profile(frame,event,arg):
 if event=='c_return' and arg is os.open:
  sys.setprofile(None);raise BaseException('unknown replay input')
def trace(frame,event,arg):
 if event=='return' and frame.f_code is DescriptorAcquisition.acquire.__code__:
  sys.settrace(None);raise KeyboardInterrupt('known replay input')
 return trace
def arm():
 if fault=='unknown':sys.setprofile(profile)
 elif fault=='known':sys.settrace(trace)
 elif fault=='missing':p.unlink()
print('REPLAY:'+point+':'+fault,flush=True)
with pinned_acquisition_policy(_pinned_input_acquisition):
 try:
  if point=='initial':arm()
  records=load_verified_projection(p,expected_sha256=hashlib.sha256(b'{}\n').hexdigest(),expected_size=3,projection_schema={'type':'object'},max_bytes=3,max_units=1)
  if point=='delayed':arm()
  assert list(records)==[{}]
 except BaseException:
  sys.setprofile(None);sys.settrace(None);print('KNOWN_FAILURE',flush=True)
 else:print('SUCCESS',flush=True)
'''
    run = subprocess.run([sys.executable, "-B", "-c", script, str(tmp_path / "input"), point, fault], capture_output=True, text=True, timeout=20)
    assert run.returncode == (10 if fault == "unknown" else 0), run.stderr
    assert run.stdout.startswith(f"REPLAY:{point}:{fault}\n")
    assert ("SUCCESS" in run.stdout) == (fault == "normal")
    assert ("KNOWN_FAILURE" in run.stdout) == (fault in {"missing", "known"})


@pytest.mark.parametrize("kind,value,code", [("exited",12,"BOUNDED_WORKER_PROCESS_REJECTED"),("exited",10,"BOUNDED_WORKER_PROCESS_REJECTED"),("exited",70,"BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY"),("signaled",15,"BOUNDED_WORKER_PROCESS_REJECTED")])
def test_acquisition_lifetime_failed_transport_never_accepts_success(kind, value, code):
    with pytest.raises(CanonicalControlError, match=code):
        classify_bounded_worker_transport(GovernedWaitStatus(kind,value), buffered_result={"status":"evidence_passed"})


@pytest.mark.parametrize("worker", ["input_projection", "replay_preparation"])
def test_acquisition_lifetime_known_close_uncertainty_is_not_worker_terminal(tmp_path, monkeypatch, worker):
    import importlib
    from orev3.execution.filesystem_capability import DescriptorOwner, DescriptorCloseError, pinned_acquisition_policy
    module=importlib.import_module("orev3.execution."+worker+"_worker")
    path=tmp_path/"input";path.write_bytes(b"x")
    real_close=os.close
    attempts=[];replacement=[]
    with pinned_acquisition_policy(module._pinned_input_acquisition):
        owner=DescriptorOwner("INPUT_MISMATCH")
        fd=owner.open(path,os.O_RDONLY)
        def close(number):
            attempts.append(number)
            real_close(number)
            reuse=os.open(path,os.O_RDONLY)
            assert reuse==number
            replacement.append(reuse)
            raise InterruptedError("closed then reused")
        with monkeypatch.context() as patch:
            patch.setattr(os,"close",close)
            with pytest.raises(DescriptorCloseError, match="INPUT_MISMATCH"):
                owner.close()
            with pytest.raises(DescriptorCloseError, match="INPUT_MISMATCH"):
                owner.close()
        assert attempts==[fd] and os.fstat(replacement[0]).st_size==1
        assert not module._PINNED_INPUT_FAILED
        real_close(replacement[0])


@pytest.mark.parametrize("exception", [KeyboardInterrupt,SystemExit,BaseException])
def test_acquisition_lifetime_entry_cleanup_failure_composition(tmp_path,monkeypatch,exception):
    from orev3.execution.filesystem_capability import DescriptorAcquisition
    runtime,namespace,_,_=_operation_fixture(tmp_path)
    observed=[];attempts=[];real_close=os.close
    def trace(frame,event,arg):
        if event=='return' and frame.f_code is DescriptorAcquisition.acquire.__code__:
            observed.append(frame.f_locals['self'].descriptor)
            if len(namespace._descriptors.pending)>=2:
                sys.settrace(None)
                raise exception('known acquisition interrupted')
        return trace
    def close(fd):
        attempts.append(fd);real_close(fd)
        raise InterruptedError('closed outcome uncertain')
    with monkeypatch.context() as patch:
        patch.setattr(os,'close',close)
        sys.settrace(trace)
        try:
            with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):
                namespace.recover()
        finally:sys.settrace(None)
    assert not namespace._busy and not namespace._descriptors.pending
    assert len(attempts)==len(set(attempts)) and len(attempts)>=2
    assert len(namespace.unresolved_closes)==len(attempts)
    with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):
        namespace.recover()


@pytest.mark.parametrize("actor",['controller','input_projection','replay_preparation'])
def test_acquisition_lifetime_terminal_bypasses_housekeeping_and_reclaims_local_lock(tmp_path,actor):
    import fcntl
    script=_acquisition_actor_script(actor,'profile','BaseException')
    script=script.replace("armed = True", """
import fcntl,logging
fcntl.flock(source,fcntl.LOCK_EX)
def forbidden(*a,**k):raise SystemExit(0)
logging.error=forbidden
logging.exception=forbidden
os.close=forbidden
atexit.register(forbidden)
armed = True
""")
    path=tmp_path/'residue'
    run=subprocess.run([sys.executable,'-B','-c',script,str(path)],capture_output=True,text=True,timeout=20)
    assert run.returncode==(12 if actor=='controller' else 10),run.stderr
    assert run.stdout==f'ARMED:{actor}:profile\n'
    fd=os.open(path,os.O_RDONLY)
    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    finally:os.close(fd)
    assert path.read_bytes()==b'non-authoritative residue'


@pytest.mark.parametrize('call_name',['snapshot_declared_input','publish_projection_path','publish_projection'])
def test_acquisition_lifetime_detached_controller_callsite_policy(tmp_path,call_name):
    import ast
    from types import SimpleNamespace
    from orev3.execution import runtime, filesystem_capability as cap
    path=Path(__file__).parents[2]/'src/orev3/execution/evidence_preparation_worker.py'
    tree=ast.parse(path.read_text())
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.With) and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id==call_name for c in ast.walk(n)))
    seen=[]
    def called(*args,**kwargs):
        seen.append(cap._ACQUISITION_POLICY.get())
        return tmp_path
    scope=dict(controller_acquisition_policy=runtime.controller_acquisition_policy,
        snapshot_declared_input=called,publish_projection_path=called,publish_projection=called,
        declaration={},request={'operational_input_locators':{}},input_store=tmp_path,limits=None,
        projection_result=SimpleNamespace(path=tmp_path,byte_count=0),projection_store=tmp_path,
        projection={'sha256':'a'*64},projection_paths=[])
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
    assert seen==[runtime._CONTROLLER_ACQUISITION]


@pytest.mark.parametrize('worker',['input_projection','replay_preparation'])
def test_acquisition_lifetime_worker_callsite_and_delayed_policy(tmp_path,worker):
    import ast,importlib
    from collections import defaultdict
    from orev3.execution import filesystem_capability as cap
    module=importlib.import_module('orev3.execution.'+worker+'_worker')
    path=Path(module.__file__);tree=ast.parse(path.read_text())
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.With) and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id=='pinned_acquisition_policy' for c in ast.walk(n)))
    seen=[]
    def observe():seen.append(cap._ACQUISITION_POLICY.get())
    def project(*a,**kw):observe();return b'',0,'a'
    class Delayed:
        def __iter__(self):observe();yield {}
    def load(*a,**kw):observe();return Delayed()
    def build(records,**kw):list(records);return {},{}
    scope=dict(pinned_acquisition_policy=cap.pinned_acquisition_policy,
        _pinned_input_acquisition=module._pinned_input_acquisition,Path=Path,
        request=defaultdict(lambda:'synthetic'),projection=tmp_path,schema={},raw_schema={},projection_schema={},
        project_jsonl=project,load_verified_projection=load,build_replay_evidence=build)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),scope)
    assert seen==[module._pinned_input_acquisition]*(2 if worker=='replay_preparation' else 1)


def test_acquisition_lifetime_helpers_only_use_explicit_policy(tmp_path):
    from orev3.execution.filesystem_capability import DescriptorOwner,pinned_acquisition_policy,open_pinned_regular
    p=tmp_path.resolve()/'input';p.write_bytes(b'x');seen=[]
    with DescriptorOwner('INPUT_MISMATCH') as owner:
        def policy(cell):
            assert cell in owner.cells and cell.descriptor is None
            seen.append(cell);cell.acquire()
        with pinned_acquisition_policy(policy):
            fd,_=open_pinned_regular(p,owner=owner,error_code='INPUT_MISMATCH')
        assert os.read(fd,1)==b'x' and seen
    assert not owner.pending


@pytest.mark.parametrize('worker',['input_projection','replay_preparation'])
@pytest.mark.parametrize('signal_name',['SIGTERM','SIGKILL'])
def test_acquisition_lifetime_worker_hard_termination_is_signal(tmp_path,worker,signal_name):
    import signal
    script=f"import os,signal;from orev3.execution.{worker}_worker import _pinned_input_acquisition;os.kill(os.getpid(),signal.{signal_name})"
    run=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,timeout=20)
    assert run.returncode==-getattr(signal,signal_name)
    with pytest.raises(CanonicalControlError,match='BOUNDED_WORKER_PROCESS_REJECTED'):
        classify_bounded_worker_transport(GovernedWaitStatus('signaled',-run.returncode),buffered_result={'status':'evidence_passed'})


@pytest.mark.parametrize('actor',['controller','input_projection','replay_preparation'])
def test_acquisition_lifetime_repeated_signal_handler_systemexit(tmp_path,actor):
    script=_acquisition_actor_script(actor,'systemexit_signal','BaseException')
    script=script.replace('def raising(number, frame): raise SystemExit(0)', '''count=0
 def raising(number, frame):
  global count
  count+=1
  if count<3:os.kill(os.getpid(),signal.SIGINT)
  raise SystemExit(0)''')
    run=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path/'residue')],capture_output=True,text=True,timeout=20)
    assert run.returncode==(0 if actor=='controller' else 10),run.stderr
    assert 'SUCCESS' not in run.stdout
    assert ('KNOWN_FAILURE' in run.stdout)==(actor=='controller')


def test_acquisition_lifetime_pinned_close_uses_original_record_after_reuse(tmp_path):
    from orev3.execution.filesystem_capability import DescriptorOwner,open_pinned_directory
    with DescriptorOwner('INPUT_MISMATCH') as owner:
        pinned=open_pinned_directory(tmp_path.resolve(),owner=owner,error_code='INPUT_MISMATCH')
        fd=pinned.descriptor
        pinned.close()
        replacement=owner.open(tmp_path,os.O_RDONLY|os.O_DIRECTORY)
        if replacement!=fd:
            replacement=owner.open(tmp_path,os.O_RDONLY|os.O_DIRECTORY)
        assert replacement==fd
        pinned.close()
        assert os.fstat(replacement).st_ino==tmp_path.stat().st_ino
        with pytest.raises(CanonicalControlError,match='INPUT_MISMATCH'):
            unused=pinned.descriptor


def test_acquisition_lifetime_controller_terminal_semantic_identity(tmp_path):
    script=_acquisition_actor_script('controller','profile','BaseException')
    script=script.replace('armed = True', '''
from orev3.execution.runtime import BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
real_exit=policy._exit
def assert_selected(code):
 assert policy.retiring==BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
 assert code==12
 real_exit(code)
policy._exit=assert_selected
armed = True
''')
    run=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path/'residue')],capture_output=True,text=True,timeout=20)
    assert run.returncode==12 and not run.stderr
    assert run.stdout=='ARMED:controller:profile\n'


@pytest.mark.parametrize('restored',[True,False])
def test_acquisition_lifetime_late_cancellation_restoration(tmp_path,monkeypatch,restored):
    import signal
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    policy=_ControllerAcquisitionPolicy();sentinel=KeyboardInterrupt('late cancellation')
    real_signal=signal.signal;previous=signal.getsignal(signal.SIGUSR1);captured=[]
    def handler(number,frame):raise sentinel
    real_signal(signal.SIGUSR1,handler)
    armed=True
    def install(number,value):
        nonlocal armed
        if number==signal.SIGUSR1 and value is not handler:
            captured.append(value)
        if number==signal.SIGUSR1 and value is handler and armed and not policy.depth:
            armed=False
            if restored:real_signal(number,value)
            captured[-1](number,None)
        return real_signal(number,value)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(signal,'signal',install)
            with pytest.raises(KeyboardInterrupt) as caught:
                def _acquisition_body_28():
                    pass
                _invoke_policy_work(policy, _acquisition_body_28)
        assert caught.value is sentinel
        assert policy.depth==0 and policy.pending is None and not policy.delivering
        assert policy.failed is (not restored)
        if not restored:
            with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):
                def _acquisition_body_29():
                    pass
                _invoke_policy_work(policy, _acquisition_body_29)
    finally:real_signal(signal.SIGUSR1,previous)


def test_acquisition_lifetime_external_input_close_mapping(tmp_path,monkeypatch):
    from orev3.execution.external_inputs import snapshot_regular_file,InputSnapshotError
    from orev3.execution.filesystem_capability import DescriptorCloseError
    source=tmp_path/'source';source.write_bytes(b'x');real_close=os.close;armed=True
    def close(fd):
        nonlocal armed
        real_close(fd)
        if armed:
            armed=False
            raise InterruptedError('parent closed')
    with monkeypatch.context() as patch:
        patch.setattr(os,'close',close)
        with pytest.raises(InputSnapshotError,match='INPUT_UNSAFE_TYPE') as caught:
            snapshot_regular_file(source,logical_identifier='input',declared_byte_count=1,declared_sha256=hashlib.sha256(b'x').hexdigest(),object_store=tmp_path/'store',max_file_bytes=1)
    assert isinstance(caught.value.__cause__,DescriptorCloseError)
    assert len(caught.value.__cause__.unresolved_closes)==1


def test_acquisition_lifetime_non_main_controller_fails_before_open(tmp_path):
    import threading
    from orev3.execution import runtime
    namespace=runtime.ControllerOperationNamespace(tmp_path.resolve());seen=[]
    def run():
        try:namespace.recover()
        except CanonicalControlError as error:seen.append(str(error))
    thread=threading.Thread(target=run);thread.start();thread.join()
    assert seen==['DISK_RESERVATION_STATE_MISMATCH']
    assert not namespace._busy and not namespace._descriptors.pending
    assert not namespace.unresolved_closes and not runtime._CONTROLLER_ACQUISITION.retiring
    assert namespace.recover().live_operations==()


@pytest.mark.parametrize("actor", ["controller", "input_projection", "replay_preparation"])
@pytest.mark.parametrize("kind", ["directory", "regular"])
@pytest.mark.parametrize("fault", ["ordinary", "c_exception", "post_setup", "InterruptedError", "KeyboardInterrupt", "SystemExit", "BaseException"])
def test_acquisition_lifetime_f1_result_classification(tmp_path, actor, kind, fault):
    script = r'''
import os,sys,signal,atexit,pathlib,importlib
from orev3.execution.filesystem_capability import DescriptorOwner,pinned_acquisition_policy,open_pinned_directory,open_pinned_regular
actor,kind,fault,path=sys.argv[1:]
if actor=='controller':
 from orev3.execution.runtime import _CONTROLLER_ACQUISITION as policy,BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
 real_exit=policy._exit
 def terminal(status):
  assert policy.retiring==BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE and status==12
  print('AUTHENTICATED_CONTROLLER_RETIRING',flush=True);real_exit(status)
 policy._exit=terminal
else:
 module=importlib.import_module('orev3.execution.'+actor+'_worker');policy=module._pinned_input_acquisition
 real_exit=module._PINNED_INPUT_EXIT
 def terminal(status):
  assert module._PINNED_INPUT_FAILED and status==10
  print('AUTHENTICATED_FAILED_INVOCATION',flush=True);real_exit(status)
 module._PINNED_INPUT_EXIT=terminal
if fault not in ('ordinary','c_exception'):
 if kind=='directory':os.mkdir(path)
 else:pathlib.Path(path).write_bytes(b'residue')
owner=DescriptorOwner('INPUT_UNSAFE_TYPE');real_open=os.open;seen=[]
if fault=='post_setup':
 armed=True
 def post_setup(event,args):
  global armed
  if event=='open' and armed and args[0]==pathlib.Path(path).name:
   armed=False
   real_open(path,os.O_RDONLY)
   print('SYNTHETIC_POST_OPEN_C_EXCEPTION',flush=True)
   raise OSError(5,'post-acquisition setup failed',path)
 sys.addaudithook(post_setup)
def observer(frame,event,function):
 cell=frame.f_locals.get('self')
 if function is real_open and cell is not None and getattr(cell,'arguments',(None,))[0]==pathlib.Path(path).name:
  if event=='c_exception':seen.append(event)
  if event=='c_return' and fault not in ('ordinary','c_exception'):
   sys.setprofile(None);print('SUCCESSFUL_C_RETURN',flush=True)
   raise getattr(__import__('builtins'),fault)('unreceived result')
atexit.register(lambda:print('ATEXIT',flush=True))
try:
 with pinned_acquisition_policy(policy),owner:
  if fault!='ordinary':sys.setprofile(observer)
  helper=open_pinned_directory if kind=='directory' else open_pinned_regular
  helper(path,owner=owner,error_code='INPUT_UNSAFE_TYPE')
except BaseException:
 sys.setprofile(None)
 assert fault in ('ordinary','c_exception')
 assert owner.cells[-1].definitive_failure and not owner.cells[-1].unprovable
 assert seen==([] if fault=='ordinary' else ['c_exception']) and not owner.pending and not owner.unresolved
 print('DEFINITIVE_NO_ACQUISITION',flush=True)
else:raise AssertionError('unexpected success')
print('CONTINUED_AFTER_DEFINITIVE_FAILURE',flush=True)
'''
    path = tmp_path / "target"
    run = subprocess.run([sys.executable, "-B", "-c", script, actor, kind, fault, str(path)], capture_output=True, text=True, timeout=20)
    if fault in {"ordinary", "c_exception"}:
        assert run.returncode == 0, run.stderr
        assert run.stdout == "DEFINITIVE_NO_ACQUISITION\nCONTINUED_AFTER_DEFINITIVE_FAILURE\nATEXIT\n"
        assert not path.exists()
    else:
        assert run.returncode == (12 if actor == "controller" else 10), run.stderr
        assert run.stdout == ("SYNTHETIC_POST_OPEN_C_EXCEPTION\n" if fault == "post_setup" else "SUCCESSFUL_C_RETURN\n") + ("AUTHENTICATED_CONTROLLER_RETIRING\n" if actor == "controller" else "AUTHENTICATED_FAILED_INVOCATION\n")
        assert path.is_dir() if kind == "directory" else path.read_bytes() == b"residue"
    assert not run.stderr


@pytest.mark.parametrize("fault", ["KeyboardInterrupt", "SystemExit", "BaseException", "SIGINT"])
@pytest.mark.parametrize("point", ["setup", "loop", "advance", "select", "call", "identity", "publish", "complete", "failure_record"])
def test_acquisition_lifetime_f2_restoration_boundaries(fault, point):
    script = r'''def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())



import inspect, os, signal, sys
from orev3.execution.runtime import _ControllerAcquisitionPolicy
from orev3.execution.canonical import CanonicalControlError
p = _ControllerAcquisitionPolicy()
fault, point = sys.argv[1:]
real_signal = signal.signal
numbers = (signal.SIGINT, signal.SIGUSR1)
saved = {n: signal.getsignal(n) for n in numbers}
calls = []
injecting = False
def handler(n, f):
 calls.append(n)
 if injecting: raise KeyboardInterrupt("real restoration cancellation")
 def _acquisition_body_1():
     authority = p._signal_restoration
     wrapper = signal.getsignal(signal.SIGINT)
     def _acquisition_body_2():
         assert p._signal_restoration is authority
     _invoke_policy_work(p, _acquisition_body_2)
     assert signal.getsignal(signal.SIGINT) is wrapper
 _invoke_policy_work(p, _acquisition_body_1)
def other(n, f): raise SystemExit("other cancellation")
originals = {signal.SIGINT: handler, signal.SIGUSR1: other}
for n, h in originals.items(): real_signal(n, h)
signal.valid_signals = lambda: numbers
def failing_signal(n, h):
 if point == "failure_record" and n == signal.SIGUSR1 and h is other and not p.depth:
  raise InterruptedError("synthetic restoration failure")
 return real_signal(n, h)
signal.signal = failing_signal
code = p._invoke.__code__
lines, start = inspect.getsourcelines(code)
needles = {
 "setup": "restoration_error = None",
 "loop": "for number, (original, state) in installed.items():",
 "advance": "for number, (original, state) in installed.items():",
 "select": 'installed[number] = (original, "unresolved")',
 "call": "signal.signal(number, original)",
 "identity": "if signal.getsignal(number) is original:",
 "publish": 'installed[number] = (original, "restored")',
 "complete": "if restoration_error is not None:",
 "failure_record": "if restoration_error is None:",
}
target = start + next(i for i, s in enumerate(lines) if s.strip() == needles[point])
hit = False
loops = 0
def trace(frame, event, arg):
 global hit, loops, injecting
 if frame.f_code is code and event == "line" and frame.f_lineno == target and not p.depth and not p.delivering:
  loops += 1
  selected = (point not in {"select","call","identity","publish","failure_record"}
              or frame.f_locals.get("number") == signal.SIGUSR1)
  if point == "advance": selected = loops == 2
  if selected and not hit:
   hit = True
   sys.settrace(None)
   if fault == "SIGINT":
    injecting = True
    os.kill(os.getpid(), signal.SIGINT)
   else: raise getattr(__import__("builtins"), fault)("restoration interruption")
 return trace
try:
 sys.settrace(trace)
 try:
  def _acquisition_body_3():
      os.kill(os.getpid(), signal.SIGINT)
  _invoke_policy_work(p, _acquisition_body_3)
 except BaseException as error:
  assert type(error).__name__ == ("KeyboardInterrupt" if fault == "SIGINT" else fault)
 else: raise AssertionError("injection did not escape")
 finally:
  sys.settrace(None)
  injecting = False
 assert hit and calls.count(signal.SIGINT) == (2 if fault == "SIGINT" else 1)
 assert p.depth == 0 and not p.delivering and p.pending is None and not p.retiring
 assert set(p._signal_restoration) == set(numbers)
 for n, (h, state) in p._signal_restoration.items():
  assert h is originals[n]
  if state == "restored": assert signal.getsignal(n) is h
 if p.failed:
  assert any(s != "restored" for h, s in p._signal_restoration.values())
  try:
   def _acquisition_body_4():
       raise AssertionError("unrestored policy admitted")
   _invoke_policy_work(p, _acquisition_body_4)
  except CanonicalControlError as error: assert str(error) == "DISK_RESERVATION_STATE_MISMATCH"
  print("FAIL_CLOSED")
 else:
  assert all(signal.getsignal(n) is h for n,h in originals.items())
  before = len(calls)
  def _acquisition_body_5():
      os.kill(os.getpid(), signal.SIGINT)
  _invoke_policy_work(p, _acquisition_body_5)
  assert len(calls) == before + 1
  assert all(signal.getsignal(n) is h for n,h in originals.items())
  print("RESTORED_LATER_DELIVERY")
finally:
 for n,h in saved.items(): real_signal(n,h)
'''
    run = subprocess.run([sys.executable, "-B", "-c", script, fault, point],
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    assert run.stdout in {"FAIL_CLOSED\n", "RESTORED_LATER_DELIVERY\n"}
    if point == "complete":
        assert run.stdout == "RESTORED_LATER_DELIVERY\n"


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("point", ["owner", "record", "install", "body"])
def test_acquisition_lifetime_f2_restoration_installation(exception, point):
    import inspect
    import signal
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    policy = _ControllerAcquisitionPolicy()
    saved = {n: signal.getsignal(n) for n in signal.valid_signals()}
    code = policy._invoke.__code__
    lines, start = inspect.getsourcelines(code)
    text = {"owner": "self._signal_restoration = installed",
            "record": 'installed[number] = (original, "unrestored")',
            "install": "signal.signal(number, deferred)", "body": "acquisition.acquire()"}[point]
    target = start + next(i for i, line in enumerate(lines) if line.strip() == text)
    sentinel = exception(point)
    hit = False
    def trace(frame, event, arg):
        nonlocal hit
        if frame.f_code is code and event == "line" and frame.f_lineno == target and not hit:
            hit = True
            sys.settrace(None)
            raise sentinel
        return trace
    sys.settrace(trace)
    try:
        with pytest.raises(exception) as caught:
            def _acquisition_body_30():
                pass
            _invoke_policy_work(policy, _acquisition_body_30)
    finally:
        sys.settrace(None)
    assert hit and caught.value is sentinel
    assert policy.depth == 0 and not policy.delivering and not policy.failed
    assert all(signal.getsignal(n) is h for n,h in saved.items())


def test_acquisition_lifetime_f2_restoration_retiring():
    script = r'''def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())



import inspect, os, signal, sys
import orev3.execution.runtime as r
p = r._CONTROLLER_ACQUISITION
def terminal(status):
 assert status == 12 and p.retiring == r.BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
 print("AUTHENTICATED_RETIRING", flush=True)
 os._exit(status)
p._exit = terminal
code = p._invoke.__code__
lines, start = inspect.getsourcelines(code)
target = start + next(i for i,s in enumerate(lines) if "for number, (original, state)" in s)
def trace(frame,event,arg):
 if frame.f_code is code and event == "line" and frame.f_lineno == target:
  sys.settrace(None)
  p.retire()
 return trace
sys.settrace(trace)
try:
 def _acquisition_body_6():
     pass
 _invoke_policy_work(p, _acquisition_body_6)
except BaseException: print("BAD_RESUMPTION",flush=True)
print("BAD_SUCCESS",flush=True)
'''
    run = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, timeout=20)
    assert run.returncode == 12 and run.stdout == "AUTHENTICATED_RETIRING\n", run.stderr

@pytest.mark.parametrize("outcome", ["raise", "unchanged"])
def test_acquisition_lifetime_f2_restoration_multiple_unresolved(monkeypatch, outcome):
    import signal
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    policy = _ControllerAcquisitionPolicy()
    real_signal = signal.signal
    numbers = (signal.SIGINT, signal.SIGUSR1)
    previous = {n: signal.getsignal(n) for n in numbers}
    handlers = {n: (lambda n, f: None) for n in numbers}
    attempts = []
    for n,h in handlers.items():
        real_signal(n,h)
    def restore(n,h):
        if h is handlers[n] and not policy.depth:
            attempts.append(n)
            if outcome == "raise":
                raise InterruptedError("unresolved restoration")
            return signal.getsignal(n)
        return real_signal(n,h)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(signal, "valid_signals", lambda: numbers)
            patch.setattr(signal, "signal", restore)
            expected = InterruptedError if outcome == "raise" else CanonicalControlError
            with pytest.raises(expected) as caught:
                def _acquisition_body_31():
                    pass
                _invoke_policy_work(policy, _acquisition_body_31)
        if outcome == "unchanged":
            assert str(caught.value) == "DISK_RESERVATION_STATE_MISMATCH"
        assert attempts == list(numbers)
        assert policy.failed and not policy.retiring
        assert all(state == "unresolved" for _, state in policy._signal_restoration.values())
        policy.failed = False
        assert policy.failed  # Retained obligations cannot be erased by the flag.
        with pytest.raises(CanonicalControlError, match="DISK_RESERVATION_STATE_MISMATCH"):
            def _acquisition_body_32():
                pytest.fail("unresolved restoration admitted")
            _invoke_policy_work(policy, _acquisition_body_32)
    finally:
        for n,h in previous.items():
            real_signal(n,h)

@pytest.mark.parametrize("completion", ["return", "KeyboardInterrupt", "SystemExit", "BaseException"])
@pytest.mark.parametrize("shape", ["single", "sequential", "nested"])
@pytest.mark.parametrize("request_at", ["none", "before", "body", "exit", "finalize"])
def test_acquisition_lifetime_f2_reentry_real_sigint(completion, shape, request_at):
    script = r'''def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())



import os, signal, sys
from orev3.execution.runtime import _ControllerAcquisitionPolicy
p = _ControllerAcquisitionPolicy()
calls = []
completion, shape, request_at = sys.argv[1:]
active = None
def check():
 assert p.delivering and p.pending is active and not p.failed and not p.retiring
def request():
 p.request(SystemExit("B explicitly subsumed by A"))
 check()
def enter(level=0):
 def _acquisition_body_7():
     check()
     if request_at == "body": request()
     if shape == "nested" and level == 0: enter(1)
     if request_at == "exit": request()
 _invoke_policy_work(p, _acquisition_body_7)
 check()
def handler(number, frame):
 global active
 calls.append(number)
 assert len(calls) == 1, "duplicate delivery"
 active = p.pending
 check()
 if request_at == "before": request()
 enter()
 if shape == "sequential": enter()
 if request_at == "finalize": request()
 check()
 if completion != "return": raise getattr(__import__("builtins"), completion)("A")
old = signal.signal(signal.SIGINT, handler)
try:
 try:
  def _acquisition_body_8():
      os.kill(os.getpid(), signal.SIGINT)
  _invoke_policy_work(p, _acquisition_body_8)
 except BaseException as error:
  assert completion != "return" and type(error).__name__ == completion and str(error) == "A"
 else: assert completion == "return"
finally: signal.signal(signal.SIGINT, old)
assert calls == [signal.SIGINT]
assert (p.depth, p.delivering, p.pending, p.failed, p.retiring) == (0, False, None, False, False)
def _acquisition_body_9():
    pass
_invoke_policy_work(p, _acquisition_body_9)
later = KeyboardInterrupt("later")
try: p.request(later)
except KeyboardInterrupt as error: assert error is later
else: raise AssertionError("lost later cancellation")
print("ONE_DELIVERY_CLEAN")
'''
    run = subprocess.run([sys.executable, "-B", "-c", script, completion, shape, request_at],
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    assert run.stdout == "ONE_DELIVERY_CLEAN\n"


@pytest.mark.parametrize("exception", [Exception, KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("caught_inside", [False, True])
def test_acquisition_lifetime_f2_reentry_inner_exception(exception, caught_inside):
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    policy = _ControllerAcquisitionPolicy()
    sentinel = exception("inner")
    calls = []
    def handler(number, frame):
        calls.append(number)
        active = policy.pending
        try:
            def _acquisition_body_33():
                def _acquisition_body_34():
                    raise sentinel
                _invoke_policy_work(policy, _acquisition_body_34)
            _invoke_policy_work(policy, _acquisition_body_33)
        except exception as error:
            assert error is sentinel
            assert policy.delivering and policy.pending is active and not policy.failed
            policy.request(SystemExit("subsumed"))
            if not caught_inside:
                raise
    try:
        def _acquisition_body_35():
            policy.pending = (handler, 1, None)
        _invoke_policy_work(policy, _acquisition_body_35)
    except exception as error:
        assert not caught_inside and error is sentinel
    else:
        assert caught_inside
    assert calls == [1]
    assert (policy.depth, policy.delivering, policy.pending, policy.failed) == (0, False, None, False)


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("point", ["entry", "exit", "eligibility", "restoration", "final_depth"])
def test_acquisition_lifetime_f2_reentry_interrupted_scope(exception, point):
    import inspect
    import signal
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    policy = _ControllerAcquisitionPolicy()
    handlers = {number: signal.getsignal(number) for number in signal.valid_signals()}
    code = policy._invoke.__code__
    lines, start = inspect.getsourcelines(code)
    text = {"entry": "self.depth = previous + 1", "exit": "self.depth = previous",
            "eligibility": "if self.pending is not None and not self.delivering:",
            "restoration": "if owns_handlers:", "final_depth": "self.depth = previous"}[point]
    matches = [i for i, line in enumerate(lines) if line.strip() == text]
    target = start + matches[-1 if point in {"final_depth", "restoration"} else 0]
    sentinel = exception(point)
    hit = False
    calls = []
    def trace(frame, event, arg):
        nonlocal hit
        if frame.f_code is code and event == "line" and frame.f_lineno == target and policy.delivering and not hit:
            hit = True
            sys.settrace(None)
            policy.request(SystemExit("B during interrupted inner scope"))
            raise sentinel
        return trace
    def handler(number, frame):
        calls.append(number)
        active = policy.pending
        sys.settrace(trace)
        try:
            def _acquisition_body_36():
                pass
            _invoke_policy_work(policy, _acquisition_body_36)
        finally:
            sys.settrace(None)
            assert policy.delivering and policy.pending is active
    with pytest.raises(exception) as caught:
        def _acquisition_body_37():
            policy.pending = (handler, 1, None)
        _invoke_policy_work(policy, _acquisition_body_37)
    assert caught.value is sentinel and hit and calls == [1]
    assert (policy.depth, policy.delivering, policy.pending, policy.failed) == (0, False, None, False)
    assert all(signal.getsignal(number) is handler for number, handler in handlers.items())
    def _acquisition_body_38():
        pass
    _invoke_policy_work(policy, _acquisition_body_38)


def test_acquisition_lifetime_f2_reentry_retiring_subprocess():
    script = r'''def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())



import os, signal
from orev3.execution.runtime import _ControllerAcquisitionPolicy, BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
p = _ControllerAcquisitionPolicy()
def terminal(status):
 assert status == 12 and p.retiring == BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
 print("AUTHENTICATED_RETIRING", flush=True)
 os._exit(status)
p._exit = terminal
def handler(number, frame):
 def _acquisition_body_10():
     def _acquisition_body_11():
         p.retire()
     _invoke_policy_work(p, _acquisition_body_11)
 _invoke_policy_work(p, _acquisition_body_10)
 raise AssertionError("continued")
signal.signal(signal.SIGINT, handler)
try:
 def _acquisition_body_12():
     os.kill(os.getpid(), signal.SIGINT)
 _invoke_policy_work(p, _acquisition_body_12)
except BaseException: print("CAUGHT_AND_CONTINUED", flush=True)
print("SUCCESS", flush=True)
'''
    run = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, timeout=20)
    assert run.returncode == 12, run.stderr
    assert run.stdout == "AUTHENTICATED_RETIRING\n"


_INVOCATION_PROBE = r'''
import contextlib, gc, inspect, json, os, signal, sys, tempfile
from pathlib import Path
from orev3.execution.runtime import _ControllerAcquisitionPolicy
from orev3.execution.canonical import CanonicalControlError
from orev3.execution.filesystem_capability import DescriptorAcquisition, DescriptorOwner, pinned_acquisition_policy
gc.disable()
mode, point, exception, kind = sys.argv[1:]
E = getattr(__import__("builtins"), exception)
p = _ControllerAcquisitionPolicy()
owner = DescriptorOwner("INPUT_MISMATCH")
saved = {n: signal.getsignal(n) for n in signal.valid_signals()}
calls, hit, seeded, observed = [], False, False, []
def handler(n, f):
 calls.append(n)
 raise E("supported cancellation")
signal.signal(signal.SIGINT, handler)
code = p._invoke.__code__
lines, start = inspect.getsourcelines(code)
def line(text): return start + next(i for i,s in enumerate(lines) if s.strip() == text)
targets = {
 "established": line("acquisition.acquire()"),
 "confirmation": line("self.depth = previous"),
 "delivery": line("handler(value, frame)"),
 "teardown": start + next(i+1 for i,s in enumerate(lines) if s.strip()=="finally:" and lines[i+1].strip()=="try:"),
 "restoration": line("restoration_error = None"),
}
def after_return(): pass
def trace(f, event, arg):
 global hit, seeded
 if f.f_code is p.__call__.__code__ and event=="call":
  cell=f.f_locals["acquisition"]
  assert cell in owner.cells and cell.descriptor is None
  observed.append(cell)
 if f.f_code in (contextlib._GeneratorContextManager.__enter__.__code__,
                  contextlib._GeneratorContextManager.__exit__.__code__):
  # Actor routing is allowed; the acquisition lifetime cannot use contextlib.
  assert not p.depth
 if (mode=="signal" and point=="delivery" and f.f_code is DescriptorAcquisition.acquire.__code__
     and event=="return" and not seeded):
  seeded=True
  os.kill(os.getpid(),signal.SIGINT)
 selected = (
  point=="entry" and f.f_code is p.__call__.__code__ and event=="call"
  or point=="acquisition" and f.f_code is DescriptorAcquisition.acquire.__code__
     and event=="line" and "self.descriptor = operation(" in inspect.getframeinfo(f).code_context[0]
  or point=="classification" and f.f_code is DescriptorAcquisition.acquire.__code__ and event=="return"
  or point in targets and f.f_code is code and event=="line" and f.f_lineno==targets[point]
  or point=="return" and f.f_code is p.__call__.__code__ and event=="return"
  or point=="after" and f.f_code is after_return.__code__ and event=="call"
 )
 if selected and not hit:
  hit=True
  sys.settrace(None)
  if mode=="signal": os.kill(os.getpid(),signal.SIGINT)
  else: raise E("targeted instrumentation")
 return trace
with tempfile.TemporaryDirectory() as directory:
 path=Path(directory) if kind=="directory" else Path(directory)/"input"
 if kind=="regular": path.write_bytes(b"owned")
 flags=os.O_RDONLY|os.O_CLOEXEC|(os.O_DIRECTORY if kind=="directory" else 0)
 try:
  with pinned_acquisition_policy(p):
   sys.settrace(trace)
   try:
    owner.open(path,flags)
    after_return()
   except E: pass
   else: raise AssertionError("missing interruption")
   finally: sys.settrace(None)
  assert hit and observed and not p.retiring
  assert not hasattr(p,"protected")
  cell=observed[0]
  assert cell is owner.cells[0]
  if mode=="fault" or mode=="signal" and point=="restoration":
   assert p.failed and any(g.gi_frame is None and not done for g,done in p._protection_scopes)
   assert cell.descriptor is not None and not cell.unprovable
   os.fstat(cell.descriptor)
   before=len(owner.cells)
   with pinned_acquisition_policy(p):
    try: owner.open(path,flags)
    except CanonicalControlError: pass
    else: raise AssertionError("incomplete invocation admitted")
   assert len(owner.cells)==before+1 and not owner.cells[-1].attempted
  else:
   assert (p.depth,p.pending,p.delivering,p.failed)==(0,None,False,False)
   assert signal.getsignal(signal.SIGINT) is handler
   assert all(done and g.gi_frame is None for g,done in p._protection_scopes)
   if point=="entry":
    assert not cell.attempted and cell.descriptor is None
   else:
    assert cell.descriptor is not None and not cell.unprovable
    os.fstat(cell.descriptor)
   before=len(calls)
   try: os.kill(os.getpid(),signal.SIGINT)
   except E: pass
   else: raise AssertionError("later signal was lost")
   assert len(calls)==before+1
   with pinned_acquisition_policy(p): owner.open(path,flags)
   assert not p.failed and p.depth==0
  fds=owner.pending[:]
  owner.close()
  assert not owner.pending and not owner.unresolved
  for fd in fds:
   try: os.fstat(fd)
   except OSError as error: assert error.errno==9
   else: raise AssertionError("known descriptor not disposed")
  print(json.dumps(dict(mode=mode,point=point,depth=p.depth,failed=p.failed,
                       pending=p.pending is not None,delivering=p.delivering,
                       calls=len(calls),owned=cell.descriptor is not None)))
 finally:
  sys.settrace(None)
  for n,h in saved.items():
   if callable(h): signal.signal(n,h)
  owner.close()
'''


@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "SystemExit", "BaseException"])
@pytest.mark.parametrize("kind", ["regular", "directory"])
@pytest.mark.parametrize("point", [
    "entry", "established", "acquisition", "classification", "confirmation",
    "delivery", "teardown", "restoration", "return", "after",
])
def test_acquisition_lifetime_f2_invocation_real_signals(exception, kind, point):
    run = subprocess.run(
        [sys.executable, "-B", "-c", _INVOCATION_PROBE, "signal", point, exception, kind],
        capture_output=True, text=True, timeout=20,
    )
    assert run.returncode == 0, run.stderr
    state = json.loads(run.stdout)
    assert state["depth"] == 0
    if point == "restoration":
        assert state["failed"] and state["owned"] and state["calls"] == 1
    else:
        assert not state["failed"] and state["calls"] == 2


@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "SystemExit", "BaseException"])
@pytest.mark.parametrize("kind", ["regular", "directory"])
def test_acquisition_lifetime_f2_invocation_final_return(exception, kind):
    run = subprocess.run(
        [sys.executable, "-B", "-c", _INVOCATION_PROBE, "return", "return", exception, kind],
        capture_output=True, text=True, timeout=20,
    )
    assert run.returncode == 0, run.stderr
    state = json.loads(run.stdout)
    assert state["owned"] and not state["failed"] and state["depth"] == 0
    assert state["calls"] == 1


@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "SystemExit", "BaseException"])
@pytest.mark.parametrize("point", ["teardown", "restoration"])
def test_acquisition_lifetime_f2_invocation_known_owner_quarantine(exception, point):
    run = subprocess.run(
        [sys.executable, "-B", "-c", _INVOCATION_PROBE, "fault", point, exception, "regular"],
        capture_output=True, text=True, timeout=20,
    )
    assert run.returncode == 0, run.stderr
    state = json.loads(run.stdout)
    assert state["failed"] and state["owned"]


def test_acquisition_lifetime_f2_invocation_definitive_failure(tmp_path):
    import gc
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    from orev3.execution.filesystem_capability import DescriptorOwner, pinned_acquisition_policy
    policy = _ControllerAcquisitionPolicy()
    owner = DescriptorOwner("INPUT_MISMATCH")
    enabled = gc.isenabled()
    gc.disable()
    try:
        with pinned_acquisition_policy(policy):
            with pytest.raises(FileNotFoundError):
                owner.open(tmp_path / "missing", os.O_RDONLY)
        assert owner.cells[0].definitive_failure and not owner.cells[0].unprovable
        assert not owner.pending and not policy.retiring and not policy.failed
        assert policy.depth == 0 and policy.pending is None and not policy.delivering
    finally:
        owner.close()
        if enabled:
            gc.enable()


@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "SystemExit", "BaseException"])
def test_acquisition_lifetime_f2_invocation_unprovable_terminal(tmp_path, exception):
    script = _acquisition_actor_script("controller", "profile", exception)
    script = script.replace("armed = True", '''
import gc
gc.disable()
from orev3.execution.runtime import BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
real_exit = policy._exit
def terminal(status):
 assert status == 12
 assert policy.retiring == BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
 print("AUTHENTICATED_RETIRING", flush=True)
 real_exit(status)
policy._exit = terminal
armed = True
''')
    run = subprocess.run(
        [sys.executable, "-B", "-c", script, str(tmp_path / "residue")],
        capture_output=True, text=True, timeout=20,
    )
    assert run.returncode == 12 and not run.stderr
    assert run.stdout == "ARMED:controller:profile\nAUTHENTICATED_RETIRING\n"


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("point", ["before", "tuple", "unpack", "invoke", "handler", "return", "raise", "cleanup", "reset"])
def test_acquisition_lifetime_f2_delivery_entry(exception, point):
    import dis
    import inspect
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    policy = _ControllerAcquisitionPolicy()
    code = policy._invoke.__code__
    lines, start = inspect.getsourcelines(code)
    def line(text): return start + next(i for i, value in enumerate(lines) if text in value)
    locations = {"before":line("self.delivering = True"), "tuple":line("handler, value, frame = self.pending"),
                 "invoke":line("handler(value, frame)"), "cleanup":line("self.pending = None"), "reset":line("self.delivering = False")}
    unpack = next(x.offset for x in dis.get_instructions(code) if x.opname == 'UNPACK_SEQUENCE' and x.positions.lineno == locations['tuple'])
    sentinel = exception(point)
    calls = []
    def handler(number, frame):
        nonlocal hit
        calls.append(number)
        policy.request(SystemExit('subsumed'))
        if point == 'raise':
            hit = True
            raise sentinel
    hit = False
    def trace(frame, event, arg):
        nonlocal hit
        if frame.f_code is code: frame.f_trace_opcodes = True
        selected = ((frame.f_code is code and event == 'line' and frame.f_lineno == locations.get(point))
                    or (point == 'unpack' and frame.f_code is code and event == 'opcode' and frame.f_lasti == unpack)
                    or (frame.f_code is handler.__code__ and event == ('call' if point == 'handler' else 'return') and point in {'handler','return'}))
        if selected and not hit:
            hit = True;sys.settrace(None)
            if policy.delivering: policy.request(SystemExit('request during failed delivery'))
            raise sentinel
        return trace
    sys.settrace(trace)
    try:
        with pytest.raises(exception) as caught:
            def _acquisition_body_39():
                policy.pending = (handler, 1, None)
            _invoke_policy_work(policy, _acquisition_body_39)
    finally: sys.settrace(None)
    assert caught.value is sentinel and hit
    assert policy.depth == 0 and not policy.delivering
    if policy.pending is not None: assert policy.failed
    later = KeyboardInterrupt('later request')
    with pytest.raises(KeyboardInterrupt) as caught: policy.request(later)
    assert caught.value is later
    if policy.failed:
        with pytest.raises(CanonicalControlError, match='DISK_RESERVATION_STATE_MISMATCH'):
            def _acquisition_body_40():
                pytest.fail('quarantined delivery resumed')
            _invoke_policy_work(policy, _acquisition_body_40)
    else:
        def _acquisition_body_41():
            pass
        _invoke_policy_work(policy, _acquisition_body_41)
    assert len(calls) <= 1


@pytest.mark.parametrize("exception", [KeyboardInterrupt, SystemExit, BaseException])
@pytest.mark.parametrize("outcome", ["not_closed", "reused", "signal"])
def test_acquisition_lifetime_f3_recording_interruption(tmp_path, monkeypatch, exception, outcome):
    import errno
    import inspect
    import signal
    import orev3.execution.filesystem_capability as capability
    owned = capability.DescriptorOwner('INPUT_UNSAFE_TYPE')
    fds = [owned.open(tmp_path / str(i), os.O_CREAT | os.O_RDWR, 0o600) for i in range(3)]
    target = fds[-1]
    real_close, real_open = os.close, os.open
    attempts = []
    replacement = []
    sentinel = exception('close bookkeeping')
    code = owned.close_acquisition.__code__
    lines, start = inspect.getsourcelines(code)
    boundary = start + next(i for i,line in enumerate(lines) if 'descriptor, type(error).__name__' in line)
    hit = False
    def interrupted(fd):
        attempts.append(fd)
        if fd != target: real_close(fd);return
        if outcome == 'reused':
            real_close(fd)
            other = real_open(tmp_path / 'replacement', os.O_CREAT | os.O_RDWR, 0o600)
            if other != fd: os.dup2(other,fd);real_close(other)
            replacement.append(fd)
        raise InterruptedError(errno.EINTR,'uncertain original close')
    def trace(frame,event,arg):
        nonlocal hit
        if frame.f_code is code and event=='line' and frame.f_lineno==boundary and not hit:
            hit=True;sys.settrace(None)
            if outcome=='signal': os.kill(os.getpid(),signal.SIGINT)
            else: raise sentinel
        return trace
    with monkeypatch.context() as patch:
        patch.setattr(os,'close',interrupted)
        if outcome=='signal':
            prior=signal.signal(signal.SIGINT,signal.default_int_handler)
        sys.settrace(trace)
        try:
            with pytest.raises(capability.DescriptorCloseError) as caught: owned.close()
        finally:
            sys.settrace(None)
            if outcome=='signal': signal.signal(signal.SIGINT,prior)
        assert hit and [x.descriptor for x in caught.value.unresolved_closes]==[target]
        assert not owned.pending and len(owned.unresolved)==1
        with pytest.raises(capability.DescriptorCloseError): owned.close()
        assert attempts==list(reversed(fds))
    os.fstat(target)
    for fd in fds[:-1]:
        with pytest.raises(OSError) as caught: os.fstat(fd)
        assert caught.value.errno==errno.EBADF
    if replacement: os.write(target,b'unrelated descriptor survives')
    real_close(target)  # Harness knows the synthetic outcome; owner never retries.


@pytest.mark.parametrize('fault', [KeyboardInterrupt,SystemExit,BaseException,'SIGINT'])
@pytest.mark.parametrize('surface', ['root','namespace'])
def test_acquisition_lifetime_f3_runtime_disposition(tmp_path,monkeypatch,fault,surface):
    import errno
    import fcntl
    import inspect
    import signal
    from orev3.execution.filesystem_capability import DescriptorOwner
    runtime,namespace,anchor,operations = _operation_fixture(tmp_path)
    handle = namespace.create_operation() if surface=='root' else None
    target = handle.lease_descriptor if handle else None
    real_close = os.close
    attempts=[]
    hit=False
    code=DescriptorOwner.close_acquisition.__code__
    lines,start=inspect.getsourcelines(code)
    boundary=start+next(i for i,line in enumerate(lines) if 'descriptor, type(error).__name__' in line)
    def close(fd):
        attempts.append(fd)
        if fd==target:raise InterruptedError(errno.EINTR,'lease/scratch uncertainty')
        real_close(fd)
    def trace(frame,event,arg):
        nonlocal hit
        if frame.f_code is code and event=='line' and frame.f_lineno==boundary and not hit:
            hit=True;sys.settrace(None)
            if fault=='SIGINT':os.kill(os.getpid(),signal.SIGINT)
            else:raise fault('uncertainty recording')
        return trace
    previous=signal.signal(signal.SIGINT,signal.default_int_handler)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(os,'close',close)
            sys.settrace(trace)
            with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):
                if handle:handle.close()
                else:
                    with namespace._locked_resources(): target=namespace._descriptors.pending[-1]
            sys.settrace(None)
            owner=handle if handle else namespace
            assert hit and [item.descriptor for item in owner.unresolved_closes]==[target]
            assert not namespace._busy and runtime._CONTROLLER_INTERVAL.current is None
            before=list(attempts)
            with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):
                if handle:handle.close()
                else:namespace.recover()
            assert attempts==before and attempts.count(target)==1
        os.fstat(target)
        if handle:
            lease=operations/handle.operation_id/'lease'
            check=os.open(lease,os.O_RDONLY)
            try:
                with pytest.raises(BlockingIOError):fcntl.flock(check,fcntl.LOCK_EX|fcntl.LOCK_NB)
            finally:real_close(check)
    finally:
        sys.settrace(None);signal.signal(signal.SIGINT,previous)
        if target is not None:
            try:real_close(target)
            except OSError:pass
    runtime.ControllerOperationNamespace(anchor).recover()


@pytest.mark.parametrize('exception',[KeyboardInterrupt,SystemExit,BaseException])
def test_acquisition_lifetime_f3_unattempted_namespace_close_retains_owner(tmp_path,exception):
    import inspect
    from orev3.execution.filesystem_capability import DescriptorOwner
    runtime,namespace,anchor,_ = _operation_fixture(tmp_path)
    code=DescriptorOwner.close_acquisition.__code__
    lines,start=inspect.getsourcelines(code)
    boundary=start+next(i for i,line in enumerate(lines) if 'descriptor = cell.descriptor' in line)
    target=None
    hit=False
    sentinel=exception('before close attempt')
    def trace(frame,event,arg):
        nonlocal hit
        if frame.f_code is code and event=='line' and frame.f_lineno==boundary and not hit:
            hit=True;sys.settrace(None);raise sentinel
        return trace
    try:
        with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):
            with namespace._locked_resources():
                target=namespace._descriptors.pending[-1]
                sys.settrace(trace)
    finally:sys.settrace(None)
    assert hit
    assert not namespace._descriptors.pending and [x.descriptor for x in namespace.unresolved_closes]==[target]
    assert not namespace._busy
    os.fstat(target)
    ledger=namespace._descriptors
    with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):namespace.recover()
    assert namespace._descriptors is ledger and not ledger.pending
    with pytest.raises(CanonicalControlError,match='DISK_RESERVATION_STATE_MISMATCH'):ledger.close()
    os.fstat(target)
    os.close(target)  # Harness knows no close syscall was attempted.
    runtime.ControllerOperationNamespace(anchor).recover()


@pytest.mark.parametrize('exception',[KeyboardInterrupt,SystemExit,BaseException])
def test_acquisition_lifetime_f1_observer_restoration(tmp_path,exception):
    import errno
    import inspect
    from orev3.execution.filesystem_capability import DescriptorOwner,DescriptorAcquisition
    owned=DescriptorOwner('INPUT_UNSAFE_TYPE')
    code=DescriptorAcquisition.acquire.__code__
    lines,start=inspect.getsourcelines(code)
    boundary=start+next(i for i,line in enumerate(lines) if 'sys.setprofile(previous)' in line)
    sentinel=exception('observer restoration')
    hit=False
    observed=[]
    previous=sys.getprofile()
    def trace(frame,event,arg):
        nonlocal hit
        if frame.f_code is code and event=='line' and frame.f_lineno==boundary and not hit:
            hit=True;observed.append(frame.f_locals['self'].descriptor)
            sys.settrace(None);raise sentinel
        return trace
    sys.settrace(trace)
    try:
        with pytest.raises(exception) as caught:
            with owned:owned.open(tmp_path/'input',os.O_CREAT|os.O_RDWR,0o600)
    finally:sys.settrace(None)
    assert hit and caught.value is sentinel and sys.getprofile() is previous
    assert not owned.pending and not owned.unresolved
    with pytest.raises(OSError) as caught:os.fstat(observed[0])
    assert caught.value.errno==errno.EBADF


@pytest.mark.parametrize("fault", ["KeyboardInterrupt", "SystemExit", "BaseException"])
@pytest.mark.parametrize("mode", ["outer", "nested", "recursive", "reentry", "pinned"])
@pytest.mark.parametrize("point", ["first_try", "depth", "after_depth", "final_depth", "before_restore"])
def test_acquisition_lifetime_f2_teardown_boundaries(fault, mode, point):
    script = r'''def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())



import inspect, json, os, signal, sys, tempfile
from pathlib import Path
from orev3.execution.runtime import _ControllerAcquisitionPolicy
from orev3.execution.canonical import CanonicalControlError
from orev3.execution.filesystem_capability import DescriptorOwner, open_pinned_directory, pinned_acquisition_policy
fault, mode, point = sys.argv[1:]
p = _ControllerAcquisitionPolicy()
saved = {n: signal.getsignal(n) for n in signal.valid_signals()}
calls, descriptors = [], []
hit = False
code = p._invoke.__code__
lines, start = inspect.getsourcelines(code)
depth_lines = [start+i for i,s in enumerate(lines) if s.strip() == "self.depth = previous"]
targets = {
 "first_try": start+next(i+1 for i,s in enumerate(lines) if s.strip()=="finally:" and lines[i+1].strip()=="try:"),
 "depth": depth_lines[0],
 "after_depth": start+next(i for i,s in enumerate(lines) if s.strip()=="if not previous:"),
 "final_depth": depth_lines[-1],
 "before_restore": start+next(i for i,s in enumerate(lines) if s.strip()=="if not owns_handlers:"),
}
expected_previous = {"outer":0,"nested":1,"recursive":2,"reentry":0,"pinned":0}[mode]
def trace(frame, event, arg):
 global hit
 if (frame.f_code is code and event=="line" and frame.f_lineno==targets[point]
     and frame.f_locals["previous"]==expected_previous
     and bool(p.delivering)==(mode in {"reentry","pinned"}) and not hit):
  hit=True
  sys.settrace(None)
  raise getattr(__import__("builtins"), fault)("teardown boundary")
 return trace
with tempfile.TemporaryDirectory() as directory:
 def handler(n, f):
  calls.append(n)
  if mode in {"reentry","pinned"}:
   def _acquisition_body_13():
       if mode=="pinned":
        with pinned_acquisition_policy(p), DescriptorOwner("INPUT_UNSAFE_TYPE") as owner:
         pinned=open_pinned_directory(Path(directory).resolve(),owner=owner,error_code="INPUT_UNSAFE_TYPE")
         descriptors.append(pinned.descriptor)
         os.fstat(pinned.descriptor)
   _invoke_policy_work(p, _acquisition_body_13)
 def body(level):
  if level:
   def _acquisition_body_14():
       body(level-1)
   _invoke_policy_work(p, _acquisition_body_14)
  else: os.kill(os.getpid(),signal.SIGINT)
 signal.signal(signal.SIGINT,handler)
 try:
  sys.settrace(trace)
  try:
   def _acquisition_body_15():
       body(expected_previous if mode not in {"reentry","pinned"} else 0)
   _invoke_policy_work(p, _acquisition_body_15)
  except BaseException as error: assert type(error).__name__==fault
  else: raise AssertionError("missing interruption")
  finally: sys.settrace(None)
  assert hit and not p.retiring
  if mode in {"reentry","pinned"}: assert len(calls)==1
  if mode=="pinned":
   assert descriptors
   for fd in descriptors:
    try: os.fstat(fd)
    except OSError as error: assert error.errno==9
    else: raise AssertionError("known descriptor not disposed")
  # A closed generator is retained authority even if cleanup never ran.
  if point=="first_try":
   assert p.failed
   assert any(g.gi_frame is None and not done for g,done in p._protection_scopes)
  if p.failed:
   try:
    def _acquisition_body_16():
        raise AssertionError("uncertain teardown admitted")
    _invoke_policy_work(p, _acquisition_body_16)
   except CanonicalControlError as error: assert str(error)=="DISK_RESERVATION_STATE_MISMATCH"
   try: os.kill(os.getpid(),signal.SIGINT)
   except CanonicalControlError as error: assert str(error)=="DISK_RESERVATION_STATE_MISMATCH"
   assert p.failed
  else:
   assert p.depth==0 and not p.delivering and p.pending is None
   assert signal.getsignal(signal.SIGINT) is handler
   before=len(calls)
   def _acquisition_body_17():
       os.kill(os.getpid(),signal.SIGINT)
   _invoke_policy_work(p, _acquisition_body_17)
   assert len(calls)==before+1 and not p.failed
  print(json.dumps(dict(depth=p.depth,pending=p.pending is not None,delivering=p.delivering,
       failed=p.failed,retiring=p.retiring,restoration=[s for h,s in p._signal_restoration.values()])))
 finally:
  sys.settrace(None)
  for n,h in saved.items():
   if callable(h): signal.signal(n,h)
'''
    run = subprocess.run([sys.executable, "-B", "-c", script, fault, mode, point],
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    state = json.loads(run.stdout)
    assert state["failed"] or (
        state["depth"] == 0 and not state["pending"] and not state["delivering"]
        and all(s == "restored" for s in state["restoration"]))


@pytest.mark.parametrize("fault", ["KeyboardInterrupt", "SystemExit", "BaseException"])
@pytest.mark.parametrize("point", ["register", "registered", "inner_complete", "outer_complete"])
def test_acquisition_lifetime_f2_teardown_publication(fault, point):
    script = r'''def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())



import dis, inspect, os, signal, sys
from orev3.execution.runtime import _ControllerAcquisitionPolicy
from orev3.execution.canonical import CanonicalControlError
fault,point=sys.argv[1:]
p=_ControllerAcquisitionPolicy()
saved={n:signal.getsignal(n) for n in signal.valid_signals()}
code=p._invoke.__code__
lines,start=inspect.getsourcelines(code)
needle={"register":"self._protection_scopes.append(scope)", "registered":"if self.retiring:",
        "inner_complete":"scope[1] = self.depth == previous", "outer_complete":"scope[1] = True"}[point]
target=start+next(i for i,s in enumerate(lines) if s.strip()==needle)
if point=="registered": target=start+next(i+1 for i,s in enumerate(lines) if s.strip()=="self._protection_scopes.append(scope)")
hit=False
def trace(f,e,a):
 global hit
 if f.f_code is code and e=="line" and f.f_lineno==target and not hit:
  if point=="inner_complete" and f.f_locals.get("previous")!=1: return trace
  hit=True;sys.settrace(None);raise getattr(__import__("builtins"),fault)("publication")
 return trace
def handler(n,f): pass
signal.signal(signal.SIGINT,handler)
try:
 sys.settrace(trace)
 try:
  def _acquisition_body_18():
      if point=="inner_complete":
       def _acquisition_body_19():
           pass
       _invoke_policy_work(p, _acquisition_body_19)
      os.kill(os.getpid(),signal.SIGINT)
  _invoke_policy_work(p, _acquisition_body_18)
 except BaseException as error: assert type(error).__name__==fault
 else: raise AssertionError("no injection")
 finally: sys.settrace(None)
 assert hit
 if point!="register": assert p.failed
 if p.failed:
  try:
   def _acquisition_body_20():
       raise AssertionError("admitted")
   _invoke_policy_work(p, _acquisition_body_20)
  except CanonicalControlError as error: assert str(error)=="DISK_RESERVATION_STATE_MISMATCH"
 else:
  def _acquisition_body_21():
      pass
  _invoke_policy_work(p, _acquisition_body_21)
  assert signal.getsignal(signal.SIGINT) is handler
 print("COHERENT")
finally:
 sys.settrace(None)
 for n,h in saved.items():
  if callable(h): signal.signal(n,h)
'''
    run = subprocess.run([sys.executable, "-B", "-c", script, fault, point],
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    assert run.stdout == "COHERENT\n"


def test_acquisition_lifetime_f2_teardown_completed_scope_storage_is_bounded():
    from orev3.execution.runtime import _ControllerAcquisitionPolicy
    policy = _ControllerAcquisitionPolicy()
    for _ in range(100):
        def _acquisition_body_42():
            def _acquisition_body_43():
                pass
            _invoke_policy_work(policy, _acquisition_body_43)
        _invoke_policy_work(policy, _acquisition_body_42)
    assert not policy.failed and policy.depth == 0
    assert len(policy._protection_scopes) <= 2
    assert all(done for _, done in policy._protection_scopes)


@pytest.mark.parametrize("phase", ["nested", "reentry", "restoration", "failed"])
def test_acquisition_lifetime_f2_teardown_retiring(phase):
    script = r'''def _invoke_policy_work(policy, work):
    """Synthetic acquisition for invariant tests; never a production callback API."""
    class Acquisition:
        unprovable = False

        def acquire(self):
            work()

    policy(Acquisition())



import inspect,os,signal,sys
from orev3.execution.runtime import _ControllerAcquisitionPolicy,BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
phase=sys.argv[1];p=_ControllerAcquisitionPolicy()
def terminal(status):
 assert status==12 and p.retiring==BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
 print("AUTHENTICATED_RETIRING",flush=True);os._exit(status)
p._exit=terminal
code=p._invoke.__code__;lines,start=inspect.getsourcelines(code)
target=start+next(i+1 for i,s in enumerate(lines) if s.strip()=="finally:" and lines[i+1].strip()=="try:")
if phase=="restoration": target=start+next(i for i,s in enumerate(lines) if s.strip()=="restoration_error = None")
def trace(f,e,a):
 if f.f_code is code and e=="line" and f.f_lineno==target:
  selected=(phase in {"restoration","failed"} or
            phase=="nested" and f.f_locals["previous"]==1 or phase=="reentry" and p.delivering)
  if selected:
   sys.settrace(None)
   if phase=="failed": raise KeyboardInterrupt("teardown")
   p.retire()
 return trace
def handler(n,f):
 if phase=="reentry":
  def _acquisition_body_22():
      pass
  _invoke_policy_work(p, _acquisition_body_22)
signal.signal(signal.SIGINT,handler)
sys.settrace(trace)
try:
 def _acquisition_body_23():
     if phase=="nested":
      def _acquisition_body_24():
          pass
      _invoke_policy_work(p, _acquisition_body_24)
     else: os.kill(os.getpid(),signal.SIGINT)
 _invoke_policy_work(p, _acquisition_body_23)
except KeyboardInterrupt:
 assert phase=="failed" and p.failed
 p.retire()
print("CONTINUATION")
'''
    run = subprocess.run([sys.executable, "-B", "-c", script, phase],
                         capture_output=True, text=True, timeout=20)
    assert run.returncode == 12, run.stderr
    assert run.stdout == "AUTHENTICATED_RETIRING\n"
