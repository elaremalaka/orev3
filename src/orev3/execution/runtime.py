"""Detached, sanitized, non-scientific preparation runtime foundation."""

from __future__ import annotations

import csv
import copy
import ctypes
import ctypes.util
import fcntl
import hashlib
import importlib
import importlib.metadata
import io
import json
import os
import platform
import re
import secrets
import signal
import shutil
import socket
import stat
import struct
import sys
import sysconfig
import tempfile
import threading
import tomllib
import unicodedata
import zipfile
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, replace
from functools import wraps
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from orev3.execution.canonical import (
    CanonicalControlError,
    domain_identity,
    parse_canonical_bytes,
    require_sha256,
    validate_json_schema_instance,
    validate_repository_path,
)
from orev3.execution.git_state import GitAuthorityError, GitDiagnosticCode, GitRepository, _run_bounded_process

RUNTIME_CONTRACT_DOMAIN = "orev3:readiness-runtime-contract:v1\n"
RUNTIME_BUNDLE_DOMAIN = "orev3:readiness-python-runtime-bundle:v1\n"
DEPENDENCY_ENVIRONMENT_DOMAIN = "orev3:readiness-closed-dependency-root:v1\n"
DEPENDENCY_LOCK_DOMAIN = "orev3:readiness-dependency-lock:v1\n"
OFFLINE_ARTIFACT_MANIFEST_DOMAIN = "orev3:readiness-offline-artifact-manifest:v1\n"
HOST_SYSTEM_DOMAIN = "orev3:readiness-host-system:v1\n"
NETWORK_SANDBOX_DOMAIN = "orev3:readiness-network-sandbox:v1\n"
PHASE3B_PROFILE_RENDERER_DOMAIN = "orev3:phase3b-seatbelt-profile-renderer:v1\n"
PHASE3B_WORKER_EVIDENCE_DOMAIN = "orev3:phase3b-worker-evidence:v1\n"
MAX_RUNTIME_CONTRACT_BYTES = 262_144
MAX_ARTIFACT_MANIFEST_BYTES = 1_048_576
MAX_DEPENDENCY_LOCK_BYTES = 8 * 1024 * 1024
MAX_WORKER_OUTPUT_BYTES = 1_048_576
WORKER_TIMEOUT_SECONDS = 180
SAFE_WORKER_COMMANDS = frozenset({"validate_imports", "validate_runtime"})
SAFE_PHASE3B_WORKERS = frozenset({
    "input_projection_worker.py",
    "readiness_test_worker.py",
    "replay_preparation_worker.py",
})
PHASE3B_CONTROLLER = "evidence_preparation_worker.py"
MACOS_SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")
OTOOL = Path("/usr/bin/otool")
SW_VERS = Path("/usr/bin/sw_vers")
NETWORK_SANDBOX_PROFILE = "(version 1)\n(allow default)\n(deny network*)\n"
PHASE3B_PROFILE_RENDERER_IDENTITY = domain_identity(
    PHASE3B_PROFILE_RENDERER_DOMAIN,
    {
        "filesystem_policy": "default_deny_named_capability_roots",
        "network_policy": "deny_network_star",
        "renderer_revision": "macos-seatbelt-capability-renderer-v4",
        "python_framework_app_runtime": "allowed_if_present_beneath_bound_base_prefix",
        "system_base_profile": "system.sb",
    },
)
PHASE3A_SANDBOX_TEMPLATE_IDENTITY = "e55dba9a5ec1fb87d8237cd95c8a29dd49c0919fc7380c38678ee6669a3ed7bc"
_NORMALIZED_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LOCK_FILENAME = re.compile(r"^pylock(?:\.[a-z0-9][a-z0-9.-]*)?\.toml$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
BOUNDED_TIME_PATH = Path("/usr/bin/time")
BOUNDED_TIME_SHA256 = "22cd4718fa94a354326fa565cac137cb535bdc81d218d092b850733df7a1fa10"
BOUNDED_TIME_IDENTITY = "09cc63835b888387783d32d0011fd0a0d344c3ba9620a947dfabd5bcfd521201"
BOUNDED_BOOTSTRAP_ARGUMENT = "--governed-fixed-fds-v1"
BOUNDED_STREAMING_BOOTSTRAP_REQUEST_MAX_BYTES = 4_194_304
BOUNDED_PROCESS_ARGUMENTS_MAX_BYTES = 1_048_576
PROC_PGRP_ONLY = 2
PROC_PIDLISTFDS = 1
PROC_PIDTBSDINFO = 3
PROC_PIDPATHINFO_MAXSIZE = 4096
PROC_PIDFDVNODEINFO = 1
PROC_PIDFDVNODEPATHINFO = 2
PROC_PIDFDSOCKETINFO = 3
PROC_PIDFDPIPEINFO = 6
PROX_FDTYPE_VNODE = 1
PROX_FDTYPE_SOCKET = 2
PROX_FDTYPE_PIPE = 6
PROC_FILEINFO_SIZE = 24
VNODE_FDINFO_SIZE = 176
VNODE_FDINFOWITHPATH_SIZE = 1200
SOCKET_FDINFO_SIZE = 792
PIPE_FDINFO_SIZE = 184
CTL_KERN = 1
KERN_PROCARGS2 = 49
MAX_BOUNDED_PROCESS_GROUP_PIDS = 256
MAX_BOUNDED_PROCESS_FDS = 256
BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY = "BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY"
_BOUNDED_LAUNCH_ENVIRONMENT_KEYS = frozenset({
    "HOME", "LANG", "LC_ALL", "PATH", "PYTHONDONTWRITEBYTECODE",
    "PYTHONHASHSEED", "PYTHONNOUSERSITE", "PYTHONUTF8",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "TMPDIR", "TZ",
})


@dataclass(frozen=True, slots=True)
class GovernedProcessInstanceV1:
    pbi_pid: int
    pbi_start_tvsec: int
    pbi_start_tvusec: int

    def __post_init__(self) -> None:
        if (
            type(self.pbi_pid) is not int or self.pbi_pid <= 0
            or type(self.pbi_start_tvsec) is not int or self.pbi_start_tvsec < 0
            or type(self.pbi_start_tvusec) is not int
            or not 0 <= self.pbi_start_tvusec < 1_000_000
        ):
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")


@dataclass(frozen=True, slots=True)
class GovernedWaitStatus:
    kind: str
    value: int


@dataclass(frozen=True, slots=True)
class GovernedProcessObservation:
    instance: GovernedProcessInstanceV1
    parent_pid: int
    process_group: int
    session_id: int
    executable_path: str

    def __post_init__(self) -> None:
        if (
            type(self.parent_pid) is not int or self.parent_pid < 0
            or type(self.process_group) is not int or self.process_group <= 0
            or type(self.session_id) is not int or self.session_id <= 0
            or not isinstance(self.executable_path, str)
            or not self.executable_path.startswith("/")
        ):
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")


@dataclass(frozen=True, slots=True)
class GovernedWorkerFDObservation:
    descriptor: int
    kind: str
    identity: tuple[object, ...]


def _decode_proc_fileinfo(raw: bytes) -> tuple[int, int, int, int, int]:
    if len(raw) < PROC_FILEINFO_SIZE:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return struct.unpack_from("=IIqiI", raw, 0)


def decode_darwin_pipe_fdinfo(raw: bytes) -> tuple[object, ...]:
    if not isinstance(raw, bytes) or len(raw) != PIPE_FDINFO_SIZE:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    open_flags, status, offset, file_type, guard_flags = _decode_proc_fileinfo(raw)
    pipe_handle, peer_handle, pipe_status, reserved = struct.unpack_from("=QQii", raw, 160)
    if file_type != PROX_FDTYPE_PIPE or not pipe_handle or reserved != 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return ("pipe", pipe_handle, peer_handle, open_flags, status, offset, guard_flags, pipe_status)


def decode_darwin_socket_fdinfo(raw: bytes) -> tuple[object, ...]:
    if not isinstance(raw, bytes) or len(raw) != SOCKET_FDINFO_SIZE:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    open_flags, status, offset, file_type, guard_flags = _decode_proc_fileinfo(raw)
    socket_handle, pcb_handle, socket_type, protocol, family = struct.unpack_from("=QQiii", raw, 160)
    if file_type != PROX_FDTYPE_SOCKET or not socket_handle or family != socket.AF_UNIX:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return ("socket", socket_handle, pcb_handle, socket_type, protocol, family, open_flags, status, offset, guard_flags)


def decode_darwin_vnode_fdinfo(
    raw: bytes, *, with_path: bool,
) -> tuple[object, ...]:
    required = VNODE_FDINFOWITHPATH_SIZE if with_path else VNODE_FDINFO_SIZE
    if not isinstance(raw, bytes) or len(raw) != required:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    open_flags, status, offset, file_type, guard_flags = _decode_proc_fileinfo(raw)
    device, mode, links, inode, uid, gid = struct.unpack_from("=IHHQII", raw, 24)
    vnode_type = struct.unpack_from("=i", raw, 160)[0]
    if file_type != PROX_FDTYPE_VNODE or not inode or links < 1 or not stat.S_ISREG(mode) and not stat.S_ISCHR(mode):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    path = None
    if with_path:
        path_raw = raw[176:1200]
        terminator = path_raw.find(b"\0")
        if terminator <= 0:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        try:
            path = path_raw[:terminator].decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH") from exc
        if not path.startswith("/") or unicodedata.normalize("NFC", path) != path:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return ("vnode", device, inode, mode, uid, gid, vnode_type, open_flags, status, offset, guard_flags, path)


class _ProcBSDInfo(ctypes.Structure):
    _fields_ = (
        ("pbi_flags", ctypes.c_uint32), ("pbi_status", ctypes.c_uint32),
        ("pbi_xstatus", ctypes.c_uint32), ("pbi_pid", ctypes.c_uint32),
        ("pbi_ppid", ctypes.c_uint32), ("pbi_uid", ctypes.c_uint32),
        ("pbi_gid", ctypes.c_uint32), ("pbi_ruid", ctypes.c_uint32),
        ("pbi_rgid", ctypes.c_uint32), ("pbi_svuid", ctypes.c_uint32),
        ("pbi_svgid", ctypes.c_uint32), ("rfu_1", ctypes.c_uint32),
        ("pbi_comm", ctypes.c_char * 16), ("pbi_name", ctypes.c_char * 32),
        ("pbi_nfiles", ctypes.c_uint32), ("pbi_pgid", ctypes.c_uint32),
        ("pbi_pjobc", ctypes.c_uint32), ("e_tdev", ctypes.c_uint32),
        ("e_tpgid", ctypes.c_uint32), ("pbi_nice", ctypes.c_int32),
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    )


class _ProcFDInfo(ctypes.Structure):
    _fields_ = (("proc_fd", ctypes.c_int32), ("proc_fdtype", ctypes.c_uint32))


def _darwin_library(name: str) -> ctypes.CDLL:
    if sys.platform != "darwin":
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    located = ctypes.util.find_library(name)
    if not located:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return ctypes.CDLL(located, use_errno=True)


def query_darwin_process_group_pids(
    process_group: int, *, libproc: object | None = None,
) -> tuple[int, ...]:
    if type(process_group) is not int or process_group <= 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    library = libproc or _darwin_library("proc")
    values = (ctypes.c_int32 * MAX_BOUNDED_PROCESS_GROUP_PIDS)()
    returned = library.proc_listpids(
        PROC_PGRP_ONLY, process_group, ctypes.byref(values), ctypes.sizeof(values)
    )
    if type(returned) is not int or returned < 0 or returned > ctypes.sizeof(values) or returned % ctypes.sizeof(ctypes.c_int32):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    pids = tuple(values[: returned // 4])
    if not pids or any(pid <= 0 for pid in pids) or len(pids) != len(set(pids)):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return pids


def query_darwin_process_observation(
    pid: int, *, libproc: object | None = None, session_query: object = os.getsid,
) -> GovernedProcessObservation:
    if type(pid) is not int or pid <= 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    library = libproc or _darwin_library("proc")
    info = _ProcBSDInfo()
    returned = library.proc_pidinfo(
        pid, PROC_PIDTBSDINFO, 0, ctypes.byref(info), ctypes.sizeof(info)
    )
    if returned != ctypes.sizeof(info) or info.pbi_pid != pid:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    path = query_darwin_process_path(pid, libproc=library)
    try:
        session_id = session_query(pid)
    except OSError as exc:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH") from exc
    return GovernedProcessObservation(
        GovernedProcessInstanceV1(pid, info.pbi_start_tvsec, info.pbi_start_tvusec),
        info.pbi_ppid, info.pbi_pgid, session_id, path,
    )


def query_darwin_process_path(pid: int, *, libproc: object | None = None) -> str:
    library = libproc or _darwin_library("proc")
    buffer = ctypes.create_string_buffer(PROC_PIDPATHINFO_MAXSIZE)
    returned = library.proc_pidpath(pid, buffer, ctypes.sizeof(buffer))
    if type(returned) is not int or returned <= 0 or returned >= ctypes.sizeof(buffer):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    raw = bytes(buffer.raw[:returned])
    if raw.endswith(b"\0"):
        raw = raw[:-1]
    try:
        path = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH") from exc
    if not path.startswith("/") or "\0" in path or unicodedata.normalize("NFC", path) != path:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return path


def query_darwin_process_argv(pid: int, *, libc: object | None = None) -> tuple[str, ...]:
    if type(pid) is not int or pid <= 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    library = libc or _darwin_library("c")
    mib = (ctypes.c_int * 3)(CTL_KERN, KERN_PROCARGS2, pid)
    required = ctypes.c_size_t()
    if library.sysctl(mib, 3, None, ctypes.byref(required), None, 0) != 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    if required.value < 4 or required.value > BOUNDED_PROCESS_ARGUMENTS_MAX_BYTES:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    buffer = ctypes.create_string_buffer(required.value)
    received = ctypes.c_size_t(required.value)
    if library.sysctl(mib, 3, buffer, ctypes.byref(received), None, 0) != 0 or received.value != required.value:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return parse_darwin_kern_procargs2(bytes(buffer.raw[:received.value]))


def query_darwin_process_fds(
    pid: int, *, libproc: object | None = None,
) -> tuple[tuple[int, int], ...]:
    library = libproc or _darwin_library("proc")
    entries = (_ProcFDInfo * MAX_BOUNDED_PROCESS_FDS)()
    returned = library.proc_pidinfo(
        pid, PROC_PIDLISTFDS, 0, ctypes.byref(entries), ctypes.sizeof(entries)
    )
    size = ctypes.sizeof(_ProcFDInfo)
    if type(returned) is not int or returned < 0 or returned > ctypes.sizeof(entries) or returned % size:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    result = tuple((item.proc_fd, item.proc_fdtype) for item in entries[: returned // size])
    if any(fd < 0 for fd, _kind in result) or len({fd for fd, _kind in result}) != len(result):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return result


def query_darwin_fdinfo(
    pid: int, descriptor: int, flavor: int, expected_size: int,
    *, libproc: object | None = None,
) -> bytes:
    if (
        type(pid) is not int or pid <= 0
        or any(type(value) is not int or value < 0 for value in (descriptor, flavor, expected_size))
        or expected_size < 1 or expected_size > 65_536
    ):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    library = libproc or _darwin_library("proc")
    buffer = ctypes.create_string_buffer(expected_size)
    returned = library.proc_pidfdinfo(pid, descriptor, flavor, buffer, expected_size)
    if returned != expected_size:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return bytes(buffer.raw)


def build_darwin_worker_fd_observations(
    pid: int, *, libproc: object | None = None,
) -> tuple[GovernedWorkerFDObservation, ...]:
    """Construct the exact seven-FD worker authority and prove enumeration stability."""
    library = libproc or _darwin_library("proc")
    first = tuple(sorted(query_darwin_process_fds(pid, libproc=library)))
    expected_types = {
        0: PROX_FDTYPE_VNODE, 1: PROX_FDTYPE_PIPE, 2: PROX_FDTYPE_PIPE,
        3: PROX_FDTYPE_PIPE, 4: PROX_FDTYPE_SOCKET,
        5: PROX_FDTYPE_VNODE, 6: PROX_FDTYPE_VNODE,
    }
    if dict(first) != expected_types or len(first) != 7:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    observations: list[GovernedWorkerFDObservation] = []
    labels = {
        0: "dev-null", 1: "bounded-stdout", 2: "bounded-stderr",
        3: "gate-pipe-read", 4: "reservation-socket",
        5: "operation-lease-vnode", 6: "request-vnode",
    }
    for descriptor, fd_type in first:
        if fd_type == PROX_FDTYPE_PIPE:
            raw = query_darwin_fdinfo(pid, descriptor, PROC_PIDFDPIPEINFO, PIPE_FDINFO_SIZE, libproc=library)
            identity = decode_darwin_pipe_fdinfo(raw)
            if descriptor == 3 and identity[3] & os.O_ACCMODE != os.O_RDONLY:
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
            if descriptor in (1, 2) and identity[3] & os.O_ACCMODE != os.O_WRONLY:
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        elif fd_type == PROX_FDTYPE_SOCKET:
            raw = query_darwin_fdinfo(pid, descriptor, PROC_PIDFDSOCKETINFO, SOCKET_FDINFO_SIZE, libproc=library)
            identity = decode_darwin_socket_fdinfo(raw)
            if identity[6] & os.O_ACCMODE != os.O_RDWR:
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        else:
            raw = query_darwin_fdinfo(pid, descriptor, PROC_PIDFDVNODEPATHINFO, VNODE_FDINFOWITHPATH_SIZE, libproc=library)
            identity = decode_darwin_vnode_fdinfo(raw, with_path=True)
            mode, open_flags, path = identity[3], identity[7], identity[-1]
            if descriptor == 0:
                if path != "/dev/null" or not stat.S_ISCHR(mode) or open_flags & os.O_ACCMODE != os.O_RDONLY:
                    raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
            elif not stat.S_ISREG(mode) or open_flags & os.O_ACCMODE != os.O_RDONLY:
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        observations.append(GovernedWorkerFDObservation(descriptor, labels[descriptor], identity))
    second = tuple(sorted(query_darwin_process_fds(pid, libproc=library)))
    if second != first:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    result = tuple(observations)
    authenticate_bounded_worker_fd_set(result)
    return result


def authenticate_bounded_process_topology(
    wrapper: GovernedProcessObservation,
    worker: GovernedProcessObservation,
) -> None:
    wrapper_pid = wrapper.instance.pbi_pid
    if (
        wrapper.parent_pid == wrapper_pid
        or wrapper.process_group != wrapper_pid
        or wrapper.session_id != wrapper_pid
        or worker.instance.pbi_pid == wrapper_pid
        or worker.parent_pid != wrapper_pid
        or worker.process_group != wrapper_pid
        or worker.session_id != wrapper_pid
    ):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")


def authenticate_bounded_worker_fd_set(
    observations: tuple[GovernedWorkerFDObservation, ...],
) -> None:
    expected_kinds = {
        0: "dev-null", 1: "bounded-stdout", 2: "bounded-stderr",
        3: "gate-pipe-read", 4: "reservation-socket",
        5: "operation-lease-vnode", 6: "request-vnode",
    }
    if len(observations) != 7 or {item.descriptor for item in observations} != set(expected_kinds):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    governed_identities: set[tuple[object, ...]] = set()
    for item in observations:
        if item.kind != expected_kinds[item.descriptor] or not item.identity:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        if item.descriptor >= 3:
            if item.identity in governed_identities:
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
            governed_identities.add(item.identity)


def safely_terminate_bounded_process_group(
    wrapper: GovernedProcessObservation,
    worker: GovernedProcessObservation,
    current_members: tuple[GovernedProcessObservation, ...],
    *, signal_number: int,
) -> None:
    if type(signal_number) is not int or signal_number <= 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    if len(current_members) not in (1, 2):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    expected = {wrapper.instance: wrapper, worker.instance: worker}
    for current in current_members:
        authenticated = expected.get(current.instance)
        if authenticated is None or current != authenticated:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    if wrapper not in current_members:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    os.killpg(wrapper.instance.pbi_pid, signal_number)


def parse_darwin_kern_procargs2(raw: bytes) -> tuple[str, ...]:
    """Decode one bounded KERN_PROCARGS2 result without treating env as argv."""
    if not isinstance(raw, bytes) or not 4 <= len(raw) <= BOUNDED_PROCESS_ARGUMENTS_MAX_BYTES:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    argc = struct.unpack_from("=i", raw)[0]
    if argc <= 0 or argc > 4096:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    cursor = 4
    executable_end = raw.find(b"\0", cursor)
    if executable_end < cursor:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    cursor = executable_end + 1
    while cursor < len(raw) and raw[cursor] == 0:
        cursor += 1
    arguments: list[str] = []
    for _ in range(argc):
        end = raw.find(b"\0", cursor)
        if end < cursor:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        try:
            argument = raw[cursor:end].decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH") from exc
        if not argument or unicodedata.normalize("NFC", argument) != argument:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        arguments.append(argument)
        cursor = end + 1
    return tuple(arguments)


def authenticate_bounded_process_argv(
    raw: bytes, expected: tuple[str, ...],
) -> None:
    if parse_darwin_kern_procargs2(raw) != expected:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")


def construct_bounded_launch_environment(temp_root: Path) -> dict[str, str]:
    if not temp_root.is_absolute():
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    environment = sanitized_worker_environment(temp_root)
    if frozenset(environment) != _BOUNDED_LAUNCH_ENVIRONMENT_KEYS:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return environment


def authenticate_bounded_launch_environment(environment: Mapping[str, str]) -> None:
    if (
        frozenset(environment) != _BOUNDED_LAUNCH_ENVIRONMENT_KEYS
        or any(type(key) is not str or type(value) is not str for key, value in environment.items())
        or environment.get("PYTHONNOUSERSITE") != "1"
        or environment.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1"
        or any(name in environment for name in ("PYTHONPATH", "PYTHONHOME", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"))
    ):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")


def decode_governed_wait_status(status: int) -> GovernedWaitStatus:
    if type(status) is not int or status < 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    if os.WIFEXITED(status):
        return GovernedWaitStatus("exited", os.WEXITSTATUS(status))
    if os.WIFSIGNALED(status):
        return GovernedWaitStatus("signaled", os.WTERMSIG(status))
    raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")


def classify_bounded_worker_transport(
    wait_status: GovernedWaitStatus, *, buffered_result: object = None,
) -> object:
    if wait_status.kind == "exited" and wait_status.value == 70:
        raise CanonicalControlError(BOUNDED_PROJECT_IMPORT_SESSION_INTEGRITY)
    if wait_status.kind != "exited" or wait_status.value != 0:
        raise CanonicalControlError("BOUNDED_WORKER_PROCESS_REJECTED")
    return buffered_result


class BoundedGateReleaseState:
    """Closed controller ordering: every independent check precedes gate release."""

    REQUIRED = (
        "wrapper", "worker", "process_instances", "group_session",
        "python_transition", "argv", "interpreter", "bootstrap_closure",
        "worker_fds", "no_fd_aliases", "request_artifact",
    )

    def __init__(self) -> None:
        self._completed: list[str] = []
        self._released = False

    def authenticate(self, stage: str) -> None:
        if self._released or stage not in self.REQUIRED or stage in self._completed:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        expected = self.REQUIRED[len(self._completed)]
        if stage != expected:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        self._completed.append(stage)

    def release(self, write_fd: int, artifact: "BoundedBootstrapRequestArtifact") -> None:
        if tuple(self._completed) != self.REQUIRED or self._released:
            try:
                os.close(write_fd)
            except OSError:
                pass
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        release_bounded_start_gate(write_fd, artifact)
        self._released = True


def authenticate_and_release_bounded_start_gate(
    *, wrapper_pid: int, expected_wrapper: GovernedProcessObservation,
    expected_worker: GovernedProcessObservation, expected_wrapper_argv: tuple[str, ...],
    expected_worker_argv: tuple[str, ...], expected_worker_fds: tuple[GovernedWorkerFDObservation, ...],
    gate_write_fd: int, artifact: "BoundedBootstrapRequestArtifact",
    bootstrap_authenticator: object,
    group_query: object = query_darwin_process_group_pids,
    process_query: object = query_darwin_process_observation,
    argv_query: object = query_darwin_process_argv,
    fd_query: object = build_darwin_worker_fd_observations,
) -> None:
    """Perform the complete independent pre-gate chain; any failure closes the gate."""
    state = BoundedGateReleaseState()
    released = False
    try:
        pids = group_query(wrapper_pid)
        if set(pids) != {expected_wrapper.instance.pbi_pid, expected_worker.instance.pbi_pid}:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        wrapper = process_query(expected_wrapper.instance.pbi_pid)
        if wrapper != expected_wrapper:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        state.authenticate("wrapper")
        worker = process_query(expected_worker.instance.pbi_pid)
        if worker != expected_worker:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        state.authenticate("worker")
        state.authenticate("process_instances")
        authenticate_bounded_process_topology(wrapper, worker)
        state.authenticate("group_session")
        if worker.executable_path != expected_worker.executable_path:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        state.authenticate("python_transition")
        if argv_query(wrapper.instance.pbi_pid) != expected_wrapper_argv or argv_query(worker.instance.pbi_pid) != expected_worker_argv:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        state.authenticate("argv")
        state.authenticate("interpreter")
        bootstrap_authenticator()
        state.authenticate("bootstrap_closure")
        observed_fds = fd_query(worker.instance.pbi_pid)
        if tuple(observed_fds) != expected_worker_fds:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        authenticate_bounded_worker_fd_set(tuple(observed_fds))
        state.authenticate("worker_fds")
        state.authenticate("no_fd_aliases")
        authenticate_bounded_bootstrap_request_artifact(artifact)
        state.authenticate("request_artifact")
        state.release(gate_write_fd, artifact)
        released = True
    finally:
        if not released:
            try:
                os.close(gate_write_fd)
            except OSError:
                pass


@dataclass(slots=True)
class BoundedBootstrapRequestArtifact:
    path: Path
    descriptor: int
    byte_count: int
    sha256: str
    bootstrap_request_identity: str
    operation_id: str
    authority_generation: str
    execution_profile_identity: str

    def close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1


def _pread_exact_digest(descriptor: int, byte_count: int) -> tuple[bytes, str]:
    if os.lseek(descriptor, 0, os.SEEK_CUR) != 0:
        raise CanonicalControlError("BOUNDED_BOOTSTRAP_REQUEST_INVALID")
    digest = hashlib.sha256()
    material = bytearray()
    offset = 0
    while offset < byte_count:
        chunk = os.pread(descriptor, min(64 * 1024, byte_count - offset), offset)
        if not chunk:
            raise CanonicalControlError("BOUNDED_BOOTSTRAP_REQUEST_INVALID")
        material.extend(chunk)
        digest.update(chunk)
        offset += len(chunk)
    if os.pread(descriptor, 1, byte_count) or os.lseek(descriptor, 0, os.SEEK_CUR) != 0:
        raise CanonicalControlError("BOUNDED_BOOTSTRAP_REQUEST_INVALID")
    return bytes(material), digest.hexdigest()


def authenticate_bounded_bootstrap_request_artifact(
    artifact: BoundedBootstrapRequestArtifact,
) -> bytes:
    opened = os.fstat(artifact.descriptor)
    if (
        not stat.S_ISREG(opened.st_mode) or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1 or opened.st_size != artifact.byte_count
        or artifact.byte_count < 1
        or artifact.byte_count > BOUNDED_STREAMING_BOOTSTRAP_REQUEST_MAX_BYTES
    ):
        raise CanonicalControlError("BOUNDED_BOOTSTRAP_REQUEST_INVALID")
    raw, digest = _pread_exact_digest(artifact.descriptor, artifact.byte_count)
    closed = os.fstat(artifact.descriptor)
    before = (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_uid, opened.st_gid, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
    after = (closed.st_dev, closed.st_ino, closed.st_mode, closed.st_uid, closed.st_gid, closed.st_size, closed.st_mtime_ns, closed.st_ctime_ns)
    if before != after or digest != artifact.sha256:
        raise CanonicalControlError("BOUNDED_BOOTSTRAP_REQUEST_INVALID")
    from orev3.execution.bounded_streaming_worker_bootstrap import bootstrap_parse_request_bytes
    material = bootstrap_parse_request_bytes(raw)
    if (
        material["bootstrap_request_identity"] != artifact.bootstrap_request_identity
        or material["operation_id"] != artifact.operation_id
        or material["authority_generation"] != artifact.authority_generation
        or material["execution_profile_identity"] != artifact.execution_profile_identity
    ):
        raise CanonicalControlError("BOUNDED_BOOTSTRAP_REQUEST_INVALID")
    return raw


def create_bounded_bootstrap_request_artifact(
    operation_root: Path,
    canonical_request_bytes: bytes,
    *,
    bootstrap_request_identity: str,
    operation_id: str,
    authority_generation: str,
    execution_profile_identity: str,
) -> BoundedBootstrapRequestArtifact:
    if len(canonical_request_bytes) > BOUNDED_STREAMING_BOOTSTRAP_REQUEST_MAX_BYTES:
        raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    path = operation_root / "bounded-bootstrap-request.json"
    write_fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        view = memoryview(canonical_request_bytes)
        while view:
            written = os.write(write_fd, view)
            if written <= 0:
                raise CanonicalControlError("BOUNDED_BOOTSTRAP_REQUEST_INVALID")
            view = view[written:]
        os.fsync(write_fd)
    finally:
        os.close(write_fd)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    artifact = BoundedBootstrapRequestArtifact(
        path, descriptor, len(canonical_request_bytes),
        hashlib.sha256(canonical_request_bytes).hexdigest(),
        bootstrap_request_identity, operation_id, authority_generation,
        execution_profile_identity,
    )
    try:
        authenticate_bounded_bootstrap_request_artifact(artifact)
    except BaseException:
        artifact.close()
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    return artifact


@dataclass(slots=True)
class BoundedSpawnFileActions:
    actions: tuple[tuple[Any, ...], ...]
    scratch_descriptors: tuple[int, ...]

    def close_scratches(self) -> None:
        for descriptor in self.scratch_descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


@dataclass(slots=True)
class BoundedInvocationResources:
    """Single-invocation descriptor ownership; never adopts caller-owned FDs."""

    descriptors: list[int]
    request_artifact: BoundedBootstrapRequestArtifact | None = None
    spawn_handle: GovernedSpawnHandle | None = None
    gate_released: bool = False

    def own(self, descriptor: int) -> int:
        if type(descriptor) is not int or descriptor < 0 or descriptor in self.descriptors:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        self.descriptors.append(descriptor)
        return descriptor

    def disown(self, descriptor: int) -> None:
        try:
            self.descriptors.remove(descriptor)
        except ValueError as exc:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH") from exc

    def close_descriptors(self) -> None:
        descriptors, self.descriptors = self.descriptors, []
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        if self.request_artifact is not None:
            path = self.request_artifact.path
            self.request_artifact.close()
            self.request_artifact = None
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def fail_before_spawn(self) -> None:
        if self.spawn_handle is not None or self.gate_released:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        self.close_descriptors()

    def fail_after_spawn_before_gate(
        self,
        *,
        wrapper: GovernedProcessObservation,
        worker: GovernedProcessObservation,
        current_members: tuple[GovernedProcessObservation, ...] | None,
        signal_number: int,
    ) -> GovernedWaitStatus:
        if self.spawn_handle is None or self.gate_released:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        signal_error = None
        if current_members is not None:
            try:
                safely_terminate_bounded_process_group(
                    wrapper, worker, current_members, signal_number=signal_number
                )
            except CanonicalControlError as exc:
                signal_error = exc
        self.close_descriptors()
        status = self.spawn_handle.wait()
        if signal_error is not None:
            raise signal_error
        return status


def orchestrate_bounded_pre_gate_authentication(
    *, resources: BoundedInvocationResources,
    wrapper: GovernedProcessObservation, worker: GovernedProcessObservation,
    gate_write_fd: int, artifact: BoundedBootstrapRequestArtifact,
    expected_wrapper_argv: tuple[str, ...], expected_worker_argv: tuple[str, ...],
    expected_worker_fds: tuple[GovernedWorkerFDObservation, ...],
    bootstrap_authenticator: object,
    group_query: object = query_darwin_process_group_pids,
    process_query: object = query_darwin_process_observation,
    argv_query: object = query_darwin_process_argv,
    fd_query: object = build_darwin_worker_fd_observations,
    signal_number: int = 15,
) -> None:
    if resources.spawn_handle is None or resources.gate_released or gate_write_fd not in resources.descriptors:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    try:
        authenticate_and_release_bounded_start_gate(
            wrapper_pid=wrapper.instance.pbi_pid,
            expected_wrapper=wrapper, expected_worker=worker,
            expected_wrapper_argv=expected_wrapper_argv,
            expected_worker_argv=expected_worker_argv,
            expected_worker_fds=expected_worker_fds,
            gate_write_fd=gate_write_fd, artifact=artifact,
            bootstrap_authenticator=bootstrap_authenticator,
            group_query=group_query, process_query=process_query,
            argv_query=argv_query, fd_query=fd_query,
        )
    except BaseException:
        # The authentication routine owns closing the gate on every failure.
        resources.disown(gate_write_fd)
        current = None
        try:
            pids = group_query(wrapper.instance.pbi_pid)
            current = tuple(process_query(pid) for pid in pids)
        except BaseException:
            current = None
        resources.fail_after_spawn_before_gate(
            wrapper=wrapper, worker=worker, current_members=current,
            signal_number=signal_number,
        )
        raise
    resources.disown(gate_write_fd)
    resources.gate_released = True


def construct_bounded_spawn_file_actions(
    *, gate_fd: int, reservation_fd: int, lease_fd: int, request_fd: int,
    stdout_fd: int, stderr_fd: int,
) -> BoundedSpawnFileActions:
    sources = (stdout_fd, stderr_fd, gate_fd, reservation_fd, lease_fd, request_fd)
    scratches: list[int] = []
    try:
        for source in sources:
            if os.get_inheritable(source):
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
            scratch = fcntl.fcntl(source, fcntl.F_DUPFD_CLOEXEC, 7)
            if scratch <= 6 or scratch in scratches:
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
            scratches.append(scratch)
        destinations = (1, 2, 3, 4, 5, 6)
        actions: list[tuple[Any, ...]] = [
            (os.POSIX_SPAWN_OPEN, 0, "/dev/null", os.O_RDONLY, 0),
        ]
        actions.extend(
            (os.POSIX_SPAWN_DUP2, scratch, destination)
            for scratch, destination in zip(scratches, destinations, strict=True)
        )
        actions.extend((os.POSIX_SPAWN_CLOSE, scratch) for scratch in scratches)
        return BoundedSpawnFileActions(tuple(actions), tuple(scratches))
    except BaseException:
        for descriptor in scratches:
            os.close(descriptor)
        raise


def reconstruct_bounded_streaming_launch_authority(
    *, python_executable: Path, bootstrap_script: Path, sandbox_profile: str,
) -> tuple[str, ...]:
    for path in (BOUNDED_TIME_PATH, MACOS_SANDBOX_EXEC, python_executable, bootstrap_script):
        if not path.is_absolute() or "\x00" in os.fspath(path):
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    if "\x00" in sandbox_profile or unicodedata.normalize("NFC", sandbox_profile) != sandbox_profile:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    return (
        os.fspath(BOUNDED_TIME_PATH), "-l", os.fspath(MACOS_SANDBOX_EXEC), "-p",
        sandbox_profile, os.fspath(python_executable), "-I", "-S",
        os.fspath(bootstrap_script), BOUNDED_BOOTSTRAP_ARGUMENT,
    )


def authenticate_bounded_time_wrapper() -> None:
    opened = BOUNDED_TIME_PATH.stat()
    if (
        not stat.S_ISREG(opened.st_mode) or stat.S_IMODE(opened.st_mode) != 0o755
        or opened.st_uid != 0 or opened.st_gid != 0 or opened.st_size != 135_248
    ):
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    digest = hashlib.sha256()
    with BOUNDED_TIME_PATH.open("rb", buffering=0) as stream:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    if digest.hexdigest() != BOUNDED_TIME_SHA256:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")


@dataclass(slots=True)
class GovernedSpawnHandle:
    pid: int
    _reaped: bool = False

    def wait(self) -> GovernedWaitStatus:
        if self._reaped:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        while True:
            try:
                returned, status = os.waitpid(self.pid, 0)
                break
            except InterruptedError:
                continue
            except ChildProcessError as exc:
                raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH") from exc
        self._reaped = True
        if returned != self.pid:
            raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
        return decode_governed_wait_status(status)


def spawn_bounded_streaming_worker(
    argv: tuple[str, ...], environment: Mapping[str, str],
    file_actions: BoundedSpawnFileActions,
    *, resources: BoundedInvocationResources | None = None,
) -> GovernedSpawnHandle:
    try:
        pid = os.posix_spawn(argv[0], argv, dict(environment), file_actions=file_actions.actions, setsid=True)
    except BaseException:
        if resources is not None:
            resources.fail_before_spawn()
        raise
    finally:
        file_actions.close_scratches()
    if type(pid) is not int or pid <= 0:
        raise CanonicalControlError("RESOURCE_PROCESS_INSTANCE_MISMATCH")
    handle = GovernedSpawnHandle(pid)
    if resources is not None:
        resources.spawn_handle = handle
    return handle


def release_bounded_start_gate(write_fd: int, artifact: BoundedBootstrapRequestArtifact) -> None:
    authenticate_bounded_bootstrap_request_artifact(artifact)
    try:
        if os.write(write_fd, b"\xa5") != 1:
            raise CanonicalControlError("START_GATE_PROTOCOL_REJECTED")
    finally:
        os.close(write_fd)


_OPERATION_TOKEN_HEX = secrets.token_hex
_OPERATION_DIRECTORIES = ("controller", "worker", "snapshot-publication", "reconstruction")
_OPERATION_PATTERN = re.compile(r"(op|cleanup)-([0-9a-f]{32})\Z")
_RECOVERY_FAILURE = "DISK_RESERVATION_STATE_MISMATCH"


def _recovery_reject() -> None:
    raise CanonicalControlError(_RECOVERY_FAILURE)


def _operation_suffix() -> str:
    # No public entropy/identifier injection. Substitution is not a fallback.
    if secrets.token_hex is not _OPERATION_TOKEN_HEX:
        raise CanonicalControlError("DISK_OPERATION_IDENTIFIER_GENERATION_FAILED")
    try:
        value = _OPERATION_TOKEN_HEX(16)
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{32}", value) is None:
            raise ValueError
        return value
    except Exception:
        raise CanonicalControlError("DISK_OPERATION_IDENTIFIER_GENERATION_FAILED") from None


def _rename_operation_exclusive(parent_fd: int, source: str, destination: str) -> None:
    """Darwin same-parent RENAME_EXCL; never emulate with replacing rename."""
    if sys.platform != "darwin":
        _recovery_reject()
    match = _OPERATION_PATTERN.fullmatch(source)
    if match is None or match[1] != "op" or destination != "cleanup-" + match[2]:
        _recovery_reject()
    try:
        library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        rename = library.renameatx_np
        rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        if rename(parent_fd, source.encode("ascii"), parent_fd, destination.encode("ascii"), 0x4) != 0:
            _recovery_reject()
    except (AttributeError, OSError):
        _recovery_reject()


def _recovery_signature(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _recovery_size_add(total: int, size: int) -> int:
    maximum = (1 << 64) - 1
    if type(total) is not int or type(size) is not int or not 0 <= total <= maximum or not 0 <= size <= maximum - total:
        raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    return total + size


@dataclass
class _RecoveryEntry:
    descriptor: int
    parent: "_RecoveryEntry | None"
    name: str
    opened: os.stat_result
    directory: bool

    def authenticate(self, uid: int, *, unchanged: bool = False) -> os.stat_result:
        if os.geteuid() != uid:
            _recovery_reject()
        value = os.fstat(self.descriptor)
        expected_mode = 0o700 if self.directory else 0o600
        if (stat.S_IMODE(value.st_mode) != expected_mode or value.st_uid != uid
                or (stat.S_ISDIR(value.st_mode) if self.directory else stat.S_ISREG(value.st_mode)) is not True
                or (not self.directory and value.st_nlink != 1)
                or (value.st_dev, value.st_ino, value.st_gid) != (self.opened.st_dev, self.opened.st_ino, self.opened.st_gid)):
            _recovery_reject()
        if unchanged and _recovery_signature(value) != _recovery_signature(self.opened):
            _recovery_reject()
        if self.parent is not None:
            bound = os.stat(self.name, dir_fd=self.parent.descriptor, follow_symlinks=False)
            if _recovery_signature(bound) != _recovery_signature(value):
                _recovery_reject()
        return value


@dataclass(frozen=True, slots=True)
class OperationRecoveryResult:
    """Synthetic lifecycle evidence only; no reservation release/launch authority."""
    recovered_operations: tuple[str, ...]
    live_operations: tuple[str, ...]
    inventoried_logical_bytes: int


@dataclass(frozen=True, slots=True)
class _RecoveryCloseUncertainty:
    """Historical identity only: this integer MUST NOT be used or retried.

    A failed close may have released the FD, including when EINTR is reported.
    It may instead still hold a flock. Neither release nor safe reuse is proven.
    """
    descriptor: int
    error_type: str
    error_number: int | None


BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE = "BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE"


class _ControllerAcquisitionPolicy:
    """Controller-only bounded cancellation deferral and terminal ownership loss.

    Signal delivery is a main-interpreter-thread operation. Other threads fail
    before acquiring resources; no thread-local mask is presented as protection.
    Requests coalesce with the first pending delivery, including requests made
    while that delivery is running. No normal work runs inside delivery.
    """
    def __init__(self):
        self.depth = 0
        self.pending = None
        self.delivering = False
        self.retiring = False
        self._signal_restoration = {}
        self._protection_scopes = []
        self.failed = False
        self._exit = os._exit

    @property
    def failed(self):
        # Obligations precede signal mutation and survive aborted teardown,
        # including interruption before failure-reporting code can execute.
        return self._failed or any(
            generator.gi_frame is None and not complete
            for generator, complete in self._protection_scopes
        ) or (
            not self.depth and not self.delivering
            and any(state != "restored"
                    for _, state in self._signal_restoration.values())
        )

    @failed.setter
    def failed(self, value):
        self._failed = value

    def retire(self):
        self.retiring = BOUNDED_CONTROLLER_ACQUISITION_OWNERSHIP_UNPROVABLE
        self._exit(12)

    def request(self, error):
        if self.retiring:
            self.retire()
        if self.delivering:
            return  # Explicitly subsumed by the in-progress cancellation.
        if self.depth:
            if self.pending is None:
                self.pending = (None, error, None)
            return
        raise error

    def __call__(self, acquisition):
        # The enclosing DescriptorOwner already owns this result cell. Drive
        # the entire acquisition and teardown before returning borrowed access.
        # No active generator/context is handed to the caller. An exception
        # escaping _invoke closes its retained CPython frame immediately, so
        # incomplete teardown remains discoverable without GC or resumption.
        scope = [None, False]
        invocation = self._invoke(acquisition, scope)
        scope[0] = invocation
        next(invocation, None)

    def _invoke(self, acquisition, scope):
        if self.retiring:
            self.retire()
        if self.failed:
            _recovery_reject()
        if self.pending is not None and not self.depth and not self.delivering:
            # An aborted eligible delivery must not admit unrelated work, even
            # if interruption prevented recording its additional failure flag.
            _recovery_reject()
        if threading.current_thread() is not threading.main_thread():
            _recovery_reject()
        # Publish after ordinary entry rejection, before depth/signal mutation.
        # CPython closes a generator on exceptional exit even when its first
        # finally instruction fails. Closed, incomplete scopes cannot masquerade
        # as nesting. Completed records are discarded; uncertain owners remain.
        self._protection_scopes = [item for item in self._protection_scopes if not item[1]]
        self._protection_scopes.append(scope)
        previous = self.depth
        installed = {}
        owns_handlers = not previous and not self.delivering
        try:
            self.depth = previous + 1
            if owns_handlers:
                self._signal_restoration = installed
                for number in signal.valid_signals():
                    original = signal.getsignal(number)
                    if not callable(original):
                        continue
                    def deferred(signum, frame, original=original):
                        if self.retiring:
                            self.retire()
                        if not self.depth and not self.delivering:
                            # Ownership is classified. A late request during
                            # handler restoration must be delivered, not parked.
                            original(signum, frame)
                            return
                        if not self.delivering and self.pending is None:
                            self.pending = (original, signum, frame)
                    # Record restoration authority before installation.
                    installed[number] = (original, "unrestored")
                    signal.signal(number, deferred)
            try:
                acquisition.acquire()
            except BaseException:
                if acquisition.unprovable:
                    self.retire()
                raise
        finally:
            try:
                self.depth = previous
                if not previous:
                    if self.retiring:
                        self.retire()
                    # A handler may acquire under protection while its delivery
                    # is active. Only the scope that selected that delivery may
                    # invoke/finalize it; reentrant scopes only restore their
                    # own protection depth. New requests remain
                    # explicitly subsumed by the active delivery in request().
                    if self.pending is not None and not self.delivering:
                        try:
                            self.delivering = True
                            handler, value, frame = self.pending
                            if handler is None:
                                raise value
                            handler(value, frame)
                        finally:
                            try:
                                if self.delivering:
                                    # Selection is authoritative: invocation or
                                    # its exceptional failure subsumes requests.
                                    self.pending = None
                                else:
                                    # Entry aborted before selection. Retain the
                                    # request and prohibit unclassified service.
                                    self.failed = True
                            except BaseException:
                                self.failed = True
                                raise
                            finally:
                                try:
                                    self.delivering = False
                                except BaseException:
                                    self.failed = True
                                    self.delivering = False
                                    raise
            finally:
                try:
                    # Reentry may abort before its first depth restoration.
                    # Restore scope depth without bypassing signal restoration.
                    self.depth = previous
                finally:
                    if not owns_handlers:
                        # Inner scopes own depth only, never outer delivery or
                        # handler restoration. Their depth is restored above.
                        scope[1] = self.depth == previous
                    if owns_handlers:
                        restoration_error = None
                        for number, (original, state) in installed.items():
                            if self.retiring:
                                self.retire()
                            installed[number] = (original, "unresolved")
                            try:
                                signal.signal(number, original)
                            except BaseException as error:
                                if restoration_error is None:
                                    restoration_error = error
                            finally:
                                if signal.getsignal(number) is original:
                                    installed[number] = (original, "restored")
                        if (self.depth == previous and not self.delivering
                                and self.pending is None
                                and all(state == "restored" for _, state in installed.values())):
                            scope[1] = True
                        if self.retiring:
                            self.retire()
                        if restoration_error is not None:
                            raise restoration_error
                        if any(state != "restored" for _, state in installed.values()):
                            _recovery_reject()

        # Preserve native generator completion authority, but yield no value
        # and never suspend while acquisition protection is active.
        yield from ()


_CONTROLLER_ACQUISITION = _ControllerAcquisitionPolicy()


@contextmanager
def controller_acquisition_policy():
    """Explicit actor routing, not cancellation deferral for the whole body."""
    from orev3.execution.filesystem_capability import pinned_acquisition_policy
    if _CONTROLLER_ACQUISITION.retiring:
        _CONTROLLER_ACQUISITION.retire()
    with pinned_acquisition_policy(_CONTROLLER_ACQUISITION):
        yield


from orev3.execution.filesystem_capability import DescriptorOwner, DescriptorAcquisition


class _RecoveryDescriptors(DescriptorOwner):
    """The sole disposal authority, including across an interrupted handoff.

    Namespace and handle may reference this same ledger, never duplicate its
    pending list. ``retained`` selects one aggregate for successful handoff;
    it does not create a second owner or make disposed integers retryable.
    """
    def __init__(self, descriptors=()):
        super().__init__(_RECOVERY_FAILURE)
        for descriptor in descriptors:
            cell = DescriptorAcquisition(None, 0, 0, None)
            cell.descriptor = descriptor
            self.cells.append(cell)
        self.retained: tuple[int, ...] = ()

    def close_one(self, descriptor: int) -> None:
        super().close_one(descriptor)

    def close(self, *, only: tuple[int, ...] | None = None, retain: bool = False) -> None:
        def selected(descriptor: int) -> bool:
            return (only is None or descriptor in only) and (not retain or descriptor not in self.retained)

        first_error = None
        for cell in tuple(reversed(self.cells)):
            if cell.descriptor is not None and not cell.disposed and selected(cell.descriptor):
                try:
                    self.close_acquisition(cell)
                except BaseException as error:
                    if not cell.disposed:
                        cell.close_outcome = cell.close_fallback
                    if first_error is None:
                        first_error = error
        self.cells[:] = [cell for cell in self.cells if cell.close_outcome != "closed"]
        if any(selected(item.descriptor) for item in self.unresolved):
            _recovery_reject()
        if first_error is not None:
            raise first_error


class _ControllerInterval:
    """Process-local exclusion shared by all modeled controller mutators.

    The coordination flock remains cross-process authority. This gate is
    nonblocking: recursive/concurrent attempts invalidate the owning interval.
    It does not intercept malicious trusted-code calls to raw OS primitives.
    """
    def __init__(self):
        # CPython RLock ownership lets finally classify an interrupted acquire
        # even before Python stores its return value. Reentry is still forbidden.
        self.lock = threading.RLock()
        self.current = None

    @contextmanager
    def enter(self):
        token = [threading.get_ident(), False, {}]
        if self.lock._is_owned():
            if self.current is not None:
                self.invalidate(self.current)
            _recovery_reject()
        try:
            if not self.lock.acquire(blocking=False):
                if self.current is not None:
                    self.invalidate(self.current)
                _recovery_reject()
            self.current = token
            yield token
        finally:
            if self.lock._is_owned():
                try:
                    self.current = None
                finally:
                    self.lock.release()

    @staticmethod
    def invalidate(token):
        # Compete with publication BEFORE marking subsequent work invalid.
        # Exact built-in dict/str operations invoke no application callbacks.
        token[2].setdefault("decision", None)
        token[1] = True

    def check(self, token):
        if (self.current is not token or token[0] != threading.get_ident() or token[1]
                or token[2].get("decision", False) is None):
            _recovery_reject()


_CONTROLLER_INTERVAL = _ControllerInterval()


class ControllerOperationRoot:
    """Controller-owned descriptors. Never give the root/parent to a worker.

    Only the separately governed launch mechanism may inherit the lease at FD5.
    Closing uses close, not LOCK_UN: an inherited open description must retain
    its flock until its final holder closes it. No cleanup is inferred here.
    """
    def __init__(self, operation_id: str, entries: tuple[_RecoveryEntry, ...], recovery: OperationRecoveryResult,
                 descriptors: _RecoveryDescriptors | None = None):
        self._operation_id = operation_id
        self._recovery = recovery
        self._entries = entries
        self._owned_descriptors = tuple(entry.descriptor for entry in entries)
        self._descriptors = descriptors if descriptors is not None else _RecoveryDescriptors(self._owned_descriptors)

    @property
    def unresolved_closes(self) -> tuple[_RecoveryCloseUncertainty, ...]:
        return tuple(item for item in self._descriptors.unresolved if item.descriptor in self._owned_descriptors)

    @property
    def operation_id(self) -> str:
        return self._operation_id

    @property
    def recovery(self) -> OperationRecoveryResult:
        return self._recovery

    @property
    def root_descriptor(self) -> int:
        if not self._entries:
            _recovery_reject()
        return self._entries[0].descriptor

    @property
    def lease_descriptor(self) -> int:
        if not self._entries:
            _recovery_reject()
        return self._entries[1].descriptor

    def category_directory_descriptor(self, name: str) -> int:
        # Directory roles, not worker-supplied paths or accounting observations.
        if name not in _OPERATION_DIRECTORIES or not self._entries:
            _recovery_reject()
        return self._entries[2 + _OPERATION_DIRECTORIES.index(name)].descriptor

    def close(self) -> None:
        with _CONTROLLER_INTERVAL.enter():
            self._close_owned()

    def _close_owned(self) -> None:
        try:
            self._descriptors.close(only=self._owned_descriptors)
        finally:
            self._entries = ()

    def __enter__(self) -> "ControllerOperationRoot":
        return self

    def __exit__(self, *unused: Any) -> None:
        self.close()


class ControllerOperationNamespace:
    """Isolated controller lifecycle foundation, disconnected from all writers.

    The caller must own structural mutation authority for the explicit private
    anchor. This is a controller API, not a wire capability or worker factory.
    Synthetic fixtures establish that premise by giving no worker structural
    access. Production use still requires the separately authenticated Stage3
    launcher/Seatbelt boundary; modes alone never prove same-UID isolation.
    No operational code constructs this owner, and results do not authorize a
    launch, numeric adoption, or charge release in ControllerReservationSession.
    """
    def __init__(self, private_snapshot_store: Path):
        self._anchor_path = private_snapshot_store
        self._busy = False
        self._entries: list[_RecoveryEntry] = []
        self._descriptors = _RecoveryDescriptors()

    @property
    def unresolved_closes(self) -> tuple[_RecoveryCloseUncertainty, ...]:
        return tuple(self._descriptors.unresolved)

    def _open(self, parent: _RecoveryEntry, name: str, directory: bool, *, create: bool = False) -> _RecoveryEntry:
        if type(name) is not str or name in {"", ".", ".."} or "/" in name or "\0" in name:
            _recovery_reject()
        parent.authenticate(self._uid)
        if create and directory:
            os.mkdir(name, 0o700, dir_fd=parent.descriptor)
        before = None if create and not directory else os.stat(name, dir_fd=parent.descriptor, follow_symlinks=False)
        if before is not None and (not (stat.S_ISDIR(before.st_mode) if directory else stat.S_ISREG(before.st_mode))):
            _recovery_reject()
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        if directory:
            flags |= os.O_DIRECTORY
        if create and not directory:
            flags |= os.O_CREAT | os.O_EXCL
        with controller_acquisition_policy():
            fd = self._descriptors.open(name, flags, 0o600, dir_fd=parent.descriptor)
        opened = os.fstat(fd)
        entry = _RecoveryEntry(fd, parent, name, opened, directory)
        if before is not None and _recovery_signature(before) != _recovery_signature(opened):
            _recovery_reject()
        entry.authenticate(self._uid, unchanged=True)
        self._entries.append(entry)
        return entry

    def _names(self, entry: _RecoveryEntry) -> set[str]:
        entry.authenticate(self._uid)
        before = os.fstat(entry.descriptor)
        names = set(os.listdir(entry.descriptor))
        after = entry.authenticate(self._uid)
        if _recovery_signature(before) != _recovery_signature(after):
            _recovery_reject()
        return names

    def _base(self) -> None:
        from orev3.execution.filesystem_capability import open_pinned_directory
        # Re-pin the configured chain as well as every held descriptor binding.
        with controller_acquisition_policy():
            pinned = open_pinned_directory(self._anchor_path, owner=self._descriptors, error_code=_RECOVERY_FAILURE)
        try:
            value = os.fstat(pinned.descriptor)
            if (value.st_dev, value.st_ino) != (self._anchor.opened.st_dev, self._anchor.opened.st_ino):
                _recovery_reject()
        finally:
            self._descriptors.close_one(pinned.descriptor)
            if self._descriptors.unresolved:
                _recovery_reject()
        for entry in (self._anchor, self._coordination, self._lock, self._operations):
            entry.authenticate(self._uid)
        if self._names(self._coordination) != {"coordination.lock", "operations"}:
            _recovery_reject()

    def _structure(self) -> set[str]:
        self._base()
        names = self._names(self._operations)
        ids: set[str] = set()
        for name in names:
            match = _OPERATION_PATTERN.fullmatch(name)
            if match is None or match[2] in ids:
                _recovery_reject()
            ids.add(match[2])
            value = os.stat(name, dir_fd=self._operations.descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(value.st_mode) or stat.S_IMODE(value.st_mode) != 0o700 or value.st_uid != self._uid:
                _recovery_reject()
        return names

    @contextmanager
    def _locked(self, *, ownership=None):
        if ownership is None:
            with _CONTROLLER_INTERVAL.enter() as token:
                with self._locked_resources():
                    yield
                    _CONTROLLER_INTERVAL.check(token)
        else:
            _CONTROLLER_INTERVAL.check(ownership)
            with self._locked_resources():
                yield
                _CONTROLLER_INTERVAL.check(ownership)

    @contextmanager
    def _locked_resources(self):
        from orev3.execution.filesystem_capability import DescriptorCloseError, open_pinned_directory
        if (self._busy or self._descriptors.unresolved
                or any(fd not in self._descriptors.retained for fd in self._descriptors.pending)):
            # A failed close quarantines this owner, not its transition guard.
            # Reusing an uncertain integer cannot reconcile kernel ownership.
            # An interrupted pre-close bookkeeping step can also leave a known
            # unattempted FD. Do not replace and forget that existing ledger.
            _recovery_reject()
        # A successfully returned handle retains its ledger independently of
        # later namespace operations. Never repopulate that ledger with new FDs.
        self._descriptors = _RecoveryDescriptors()
        try:
            self._busy = True
            self._entries = []
            self._uid = os.geteuid()
            with controller_acquisition_policy():
                pinned = open_pinned_directory(self._anchor_path, owner=self._descriptors, error_code=_RECOVERY_FAILURE)
            self._anchor = _RecoveryEntry(pinned.descriptor, None, "", os.fstat(pinned.descriptor), True)
            self._entries.append(self._anchor)
            self._anchor.authenticate(self._uid)
            try:
                self._coordination = self._open(self._anchor, ".orev3-bounded-streaming-v1", True)
            except FileNotFoundError:
                try:
                    self._coordination = self._open(self._anchor, ".orev3-bounded-streaming-v1", True, create=True)
                except FileExistsError:
                    self._coordination = self._open(self._anchor, ".orev3-bounded-streaming-v1", True)
            names = self._names(self._coordination)
            if not names <= {"coordination.lock", "operations"}:
                _recovery_reject()
            if "coordination.lock" not in names and "operations" in names:
                existing = self._open(self._coordination, "operations", True)
                if self._names(existing):
                    _recovery_reject()
            try:
                self._lock = self._open(self._coordination, "coordination.lock", False)
            except FileNotFoundError:
                try:
                    self._lock = self._open(self._coordination, "coordination.lock", False, create=True)
                except FileExistsError:
                    self._lock = self._open(self._coordination, "coordination.lock", False)
            fcntl.flock(self._lock.descriptor, fcntl.LOCK_EX)
            self._lock.authenticate(self._uid)
            if not self._names(self._coordination) <= {"coordination.lock", "operations"}:
                _recovery_reject()
            try:
                self._operations = self._open(self._coordination, "operations", True)
            except FileNotFoundError:
                self._operations = self._open(self._coordination, "operations", True, create=True)
            self._base()
            # Also repeat these barriers for recovered initialization/removal.
            for entry in (self._lock, self._operations, self._coordination, self._anchor):
                os.fsync(entry.descriptor)
            yield
        except DescriptorCloseError as error:
            # Helpers now share this exact owner; their uncertainty is already
            # retained here rather than transferred from a second ledger.
            raise
        except CanonicalControlError:
            raise
        except (OSError, ValueError, OverflowError, RecursionError):
            raise CanonicalControlError(_RECOVERY_FAILURE) from None
        finally:
            try:
                self._descriptors.close(retain=True)
            finally:
                try:
                    self._entries = []
                finally:
                    self._busy = False

    def _lease(self, root: _RecoveryEntry) -> tuple[_RecoveryEntry, bool]:
        lease = self._open(root, "lease", False)
        if lease.opened.st_size != 0:
            _recovery_reject()
        try:
            fcntl.flock(lease.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lease.authenticate(self._uid, unchanged=True)
            return lease, False
        lease.authenticate(self._uid, unchanged=True)
        return lease, True

    def _chain(self, entry: _RecoveryEntry) -> None:
        self._structure()
        current: _RecoveryEntry | None = entry
        while current is not None:
            current.authenticate(self._uid)
            current = current.parent

    def _inventory(self, root: _RecoveryEntry, lease: _RecoveryEntry, seen: set[tuple[int, int]]) -> tuple[list[_RecoveryEntry], int]:
        nodes = [root]
        total = 0
        index = 0
        while index < len(nodes):
            entry = nodes[index]
            index += 1
            value = entry.authenticate(self._uid, unchanged=True)
            identity = (value.st_dev, value.st_ino)
            if identity in seen:
                _recovery_reject()
            seen.add(identity)
            if not entry.directory:
                total = _recovery_size_add(total, value.st_size)
                continue
            names = self._names(entry)
            if entry is root and ("lease" not in names or not names <= set(_OPERATION_DIRECTORIES) | {"lease", "bounded-bootstrap-request.json"}):
                _recovery_reject()
            for name in sorted(names):
                if entry is root and name == "lease":
                    child = lease
                else:
                    value = os.stat(name, dir_fd=entry.descriptor, follow_symlinks=False)
                    directory = stat.S_ISDIR(value.st_mode)
                    if entry is root and directory != (name in _OPERATION_DIRECTORIES):
                        _recovery_reject()
                    child = self._open(entry, name, directory)
                nodes.append(child)
        # Validate the entire scan before the first destructive step.
        for entry in nodes:
            entry.authenticate(self._uid, unchanged=True)
        return nodes, total

    def _terminal(self, root: _RecoveryEntry, lease: _RecoveryEntry | None) -> None:
        self._chain(root)
        if not root.name.startswith("cleanup-") or self._names(root) != ({"lease"} if lease else set()):
            _recovery_reject()
        if lease is not None:
            lease.authenticate(self._uid, unchanged=True)
            os.fsync(root.descriptor)
            os.fsync(self._operations.descriptor)  # Mandatory even on restarted T1.
            self._chain(lease)
            if self._names(root) != {"lease"}:
                _recovery_reject()
            lease.authenticate(self._uid, unchanged=True)
            os.unlink("lease", dir_fd=root.descriptor)
        os.fsync(root.descriptor)
        self._chain(root)
        if self._names(root):
            _recovery_reject()
        os.rmdir(root.name, dir_fd=self._operations.descriptor)
        os.fsync(self._operations.descriptor)
        names = self._structure()
        if root.name in names or "op-" + root.name[8:] in names:
            _recovery_reject()

    def _drain(self, root: _RecoveryEntry, lease: _RecoveryEntry, nodes: list[_RecoveryEntry]) -> None:
        for entry in reversed(nodes[1:]):
            if entry is lease:
                continue
            self._chain(entry)
            if entry.directory:
                if self._names(entry):
                    _recovery_reject()
                os.fsync(entry.descriptor)
                os.rmdir(entry.name, dir_fd=entry.parent.descriptor)
            else:
                entry.authenticate(self._uid, unchanged=True)
                os.unlink(entry.name, dir_fd=entry.parent.descriptor)
            os.fsync(entry.parent.descriptor)
        self._chain(root)
        lease.authenticate(self._uid, unchanged=True)
        if self._names(root) != {"lease"}:
            _recovery_reject()
        os.fsync(lease.descriptor)
        os.fsync(root.descriptor)
        self._chain(lease)
        if self._names(root) != {"lease"}:
            _recovery_reject()
        old_name = root.name
        destination = "cleanup-" + old_name[3:]
        if destination in self._structure():
            _recovery_reject()
        _rename_operation_exclusive(self._operations.descriptor, old_name, destination)
        root.name = destination
        self._chain(root)
        if old_name in self._structure() or self._names(root) != {"lease"}:
            _recovery_reject()
        lease.authenticate(self._uid, unchanged=True)
        self._terminal(root, lease)

    def _recover(self) -> OperationRecoveryResult:
        initial = self._structure()  # Detect every same-ID conflict before deletion.
        live: dict[str, tuple[_RecoveryEntry, _RecoveryEntry]] = {}
        recovered: list[str] = []
        seen: set[tuple[int, int]] = set()
        total = 0
        for name in sorted(initial):
            self._structure()
            root = self._open(self._operations, name, True)
            if name.startswith("op-"):
                lease, acquired = self._lease(root)
                if not acquired:
                    live[name] = root, lease
                    continue
                nodes, size = self._inventory(root, lease, seen)
                total = _recovery_size_add(total, size)
                self._drain(root, lease, nodes)
                recovered.append(name)
            else:
                names = self._names(root)
                if names not in (set(), {"lease"}):
                    _recovery_reject()
                lease = None
                if names:
                    lease, acquired = self._lease(root)
                    if not acquired:
                        _recovery_reject()
                for entry in (root,) if lease is None else (root, lease):
                    identity = (entry.opened.st_dev, entry.opened.st_ino)
                    if identity in seen:
                        _recovery_reject()
                    seen.add(identity)
                self._terminal(root, lease)
                recovered.append("op-" + name[8:])
        os.fsync(self._operations.descriptor)
        if self._structure() != set(live):
            _recovery_reject()
        for root, lease in live.values():
            self._chain(root)
            lease.authenticate(self._uid, unchanged=True)
            try:
                fcntl.flock(lease.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            # Became orphan during the pass: defer it to a fresh complete pass.
            _recovery_reject()
        if self._structure() != set(live):
            _recovery_reject()
        return OperationRecoveryResult(tuple(recovered), tuple(sorted(live)), total)

    def recover(self) -> OperationRecoveryResult:
        with self._locked():
            return self._recover()

    def create_operation(self) -> ControllerOperationRoot:
        handle = None
        try:
            with self._locked():
                recovery = self._recover()
                for _ in range(128):
                    suffix = _operation_suffix()
                    name = "op-" + suffix
                    if "cleanup-" + suffix in self._structure():
                        _recovery_reject()
                    try:
                        root = self._open(self._operations, name, True, create=True)
                    except FileExistsError:
                        continue
                    break
                else:
                    raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
                lease, acquired = self._new_lease(root)
                if not acquired:
                    _recovery_reject()
                directories = tuple(self._open(root, name, True, create=True) for name in _OPERATION_DIRECTORIES)
                if self._names(root) != {"lease", *_OPERATION_DIRECTORIES}:
                    _recovery_reject()
                for entry in (lease, *directories, root, self._operations):
                    entry.authenticate(self._uid)
                    os.fsync(entry.descriptor)
                self._chain(lease)
                # Initial recovery is not a durable liveness claim. A previously
                # live operation may have died while this root was initialized.
                for live_name in recovery.live_operations:
                    live_root = self._open(self._operations, live_name, True)
                    _, acquired = self._lease(live_root)
                    if acquired:
                        _recovery_reject()
                if self._structure() != set(recovery.live_operations) | {name}:
                    _recovery_reject()
                owned = (root, lease, *directories)
                handle = ControllerOperationRoot(name, owned, recovery, self._descriptors)
                # One aggregate transition; before it namespace teardown drains
                # all FDs, after it failed-handoff cleanup drains the bundle.
                # Both routes consult the same single-attempt disposal ledger.
                self._descriptors.retained = handle._owned_descriptors
            return handle
        except BaseException:
            if handle is not None:
                handle.close()
            raise

    def _new_lease(self, root: _RecoveryEntry) -> tuple[_RecoveryEntry, bool]:
        lease = self._open(root, "lease", False, create=True)
        if lease.opened.st_size != 0:
            _recovery_reject()
        fcntl.flock(lease.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lease.authenticate(self._uid, unchanged=True)
        return lease, True


def _reservation_transition(method):
    """Serialize public core transitions against synchronous callback reentry.

    This is not a thread lock. A nested attempt changes no ledger state, but
    invalidates the outer callback result even if the callback catches the
    rejection. The owning transition alone clears the guard in ``finally``.
    """
    @wraps(method)
    def guarded(self, *args, **kwargs):
        if getattr(self, "_transition_active", False):
            self._transition_reentered = True
            raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")
        self._transition_active = True
        self._transition_reentered = False
        try:
            return method(self, *args, **kwargs)
        finally:
            self._transition_active = False
            self._transition_reentered = False
    return guarded


@dataclass(frozen=True, slots=True)
class ReservationAccountingSnapshot:
    """Immutable controller view, ordered by the five governed categories.

    Reserved bytes are the total prospective capacity held (including charged
    bytes), not an additional charge to add to ``charged_bytes``. The latter
    contains only controller-observed logical lengths. An uncertain terminal
    snapshot cannot be used to admit any further work.
    """

    charged_bytes: tuple[int, ...]
    reserved_bytes: tuple[int, ...]
    expected_sequence: int | None
    pending_request: bool
    terminal: bool
    uncertain: bool
    eof_pending_classification: bool


class ControllerReservationSession:
    """Unconnected Section 9.1 transition core; NOT operational enforcement.

    Construct only in the controller for an already-established operation.
    ``controller_observe(kind)`` is a controller-owned observation boundary:
    future integration must bind confined descriptors under the coordination
    lock. It is never taken from request material or passed to a worker.
    Synthetic callbacks are useful for core tests but are not filesystem proof.
    This class creates no operation ID, path, lease, socket, journal, or writer.

    Preparing a request does not grant capacity. Issuing its ACK commits the
    transition; a transport failure after issuance must call ``fail_uncertain``.
    Short-write capacity is released only atomically with the next accepted
    same-category request, or after verified orderly EOF. Rejected requests
    leave all ledger values and the sequence unchanged.

    Bare transport EOF freezes request admission without releasing capacity.
    Only an explicit controller classification via ``orderly_eof`` may release
    it; ``fail_uncertain`` retains the acknowledged floor. Neither classification
    is worker wire authority. Observation/read callbacks may inspect snapshots
    but may not reenter public transitions, even if they catch the rejection.
    """

    @_reservation_transition
    def __init__(
        self, *, operation_id: str, max_temporary_disk_bytes: int,
        controller_observe: Callable[[str], int],
    ) -> None:
        from orev3.execution import bounded_streaming_worker_bootstrap as wire

        self._wire = wire
        self._operation_id = wire.reservation_operation_id(operation_id)
        self._limit = wire.reservation_uint64(max_temporary_disk_bytes, positive=True)
        if not callable(controller_observe):
            raise wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")
        self._observe = controller_observe
        self._charged = tuple(self._observation(kind) for kind in wire.RESERVATION_KINDS)
        self._reserved = self._charged
        if self._total(self._reserved) > self._limit:
            raise wire.ReservationProtocolError("RESOURCE_LIMIT_EXCEEDED")
        self._sequence: int | None = 0
        self._pending: tuple[bytes, tuple[int, ...], tuple[int, ...]] | None = None
        self._terminal = False
        self._uncertain = False
        self._eof_received = False
        self._orderly_completed = False
        self._rejection: bytes | None = None

    @property
    def snapshot(self) -> ReservationAccountingSnapshot:
        return ReservationAccountingSnapshot(
            self._charged, self._reserved, self._sequence,
            self._pending is not None, self._terminal, self._uncertain,
            self._eof_received and not self._terminal,
        )

    @property
    def rejection_payload(self) -> bytes | None:
        # No fabricated identity/sequence for an unparseable request.
        return self._rejection

    def _total(self, values: tuple[int, ...]) -> int:
        total = 0
        for value in values:
            if value > self._wire.RESERVATION_UINT64_MAX - total:
                raise self._wire.ReservationProtocolError("RESOURCE_LIMIT_EXCEEDED")
            total += value
        return total

    def _observation(self, kind: str) -> int:
        try:
            self._reject_reentry()
            actual = self._observe(kind)
            self._reject_reentry()
            return self._wire.reservation_uint64(actual)
        except Exception:
            raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH") from None

    def _reject_reentry(self) -> None:
        if self._transition_reentered:
            raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")

    def _open(self, *, allow_eof: bool = False) -> None:
        if self._terminal or (self._eof_received and not allow_eof):
            raise self._wire.ReservationProtocolError()

    def _terminate(self) -> None:
        self._terminal = True
        self._pending = None

    def _reconciled(self, index: int) -> int:
        actual = self._observation(self._wire.RESERVATION_KINDS[index])
        if not self._charged[index] <= actual <= self._reserved[index]:
            raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")
        return actual

    @_reservation_transition
    def prepare_request(self, payload: bytes) -> None:
        self._prepare_request(payload)

    def _prepare_request(self, payload: bytes) -> None:
        # Internal delegation from read_request shares its owning guard.
        self._open()
        request = None
        try:
            if self._pending is not None or self._sequence is None:
                raise self._wire.ReservationProtocolError()
            request = self._wire.parse_reservation_payload(payload)
            if request["message_type"] != "reserve_growth":
                raise self._wire.ReservationProtocolError()
            if (
                request["operation_id"] != self._operation_id
                or request["sequence_number"] != self._sequence
            ):
                raise self._wire.ReservationProtocolError()
            index = self._wire.RESERVATION_KINDS.index(request["reservation_kind"])
            actual = self._reconciled(index)
            if request["current_logical_bytes"] != actual:
                raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")
            growth = request["requested_growth_bytes"]
            if growth > self._wire.RESERVATION_UINT64_MAX - actual:
                raise self._wire.ReservationProtocolError("RESOURCE_LIMIT_EXCEEDED")
            charged = list(self._charged)
            reserved = list(self._reserved)
            charged[index] = actual
            reserved[index] = actual + growth
            total = self._total(tuple(reserved))
            if total > self._limit:
                raise self._wire.ReservationProtocolError("RESOURCE_LIMIT_EXCEEDED")
            acknowledgement = self._wire.reservation_payload({
                "schema_version": 1, "message_type": "reservation_acknowledged",
                "operation_id": self._operation_id, "sequence_number": self._sequence,
                "accepted_growth_bytes": growth, "resulting_reserved_bytes": total,
                "resulting_charged_bytes": self._total(tuple(charged)),
            })
            self._pending = (acknowledgement, tuple(charged), tuple(reserved))
        except self._wire.ReservationProtocolError as exc:
            self._terminate()
            if request is not None and request["message_type"] == "reserve_growth":
                self._rejection = self._wire.reservation_payload({
                    "schema_version": 1, "message_type": "reservation_rejected",
                    "operation_id": request["operation_id"],
                    "sequence_number": request["sequence_number"], "failure_code": exc.code,
                })
            raise

    @_reservation_transition
    def issue_acknowledgment(self) -> bytes:
        self._open()
        if self._pending is None:
            self._terminate()
            raise self._wire.ReservationProtocolError()
        payload, charged, reserved = self._pending
        self._charged, self._reserved = charged, reserved
        self._pending = None
        self._sequence = None if self._sequence == self._wire.RESERVATION_UINT64_MAX else self._sequence + 1
        return payload

    @_reservation_transition
    def observe_completion(self, reservation_kind: str) -> None:
        """Record verified growth, but retain unused allowance until reconciliation."""
        self._open()
        try:
            if self._pending is not None or reservation_kind not in self._wire.RESERVATION_KINDS:
                raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")
            index = self._wire.RESERVATION_KINDS.index(reservation_kind)
            actual = self._reconciled(index)
            charged = list(self._charged)
            charged[index] = actual
            self._charged = tuple(charged)
        except self._wire.ReservationProtocolError:
            self._terminate()
            raise

    @_reservation_transition
    def orderly_eof(self) -> None:
        """Affirmative controller classification, never inferred from socket EOF.

        The caller must independently establish orderly worker completion;
        ambiguous completion or death must instead use fail_uncertain. This
        deterministic core neither detects process death nor authenticates that
        controller fact. All descriptor observations must then reconcile before
        any unused capacity is released. Successful classification is final.
        """
        self._open(allow_eof=True)
        try:
            if self._pending is not None:
                raise self._wire.ReservationProtocolError()
            # All observations validate before any capacity can be released.
            actual = tuple(self._reconciled(i) for i in range(len(self._charged)))
            self._charged = self._reserved = actual
            self._terminal = True
            self._orderly_completed = True
        except self._wire.ReservationProtocolError:
            self._terminate()
            raise

    @_reservation_transition
    def read_request(self, read: Callable[[int], bytes]) -> None:
        """Synthetic/transport adapter; does not open or service a live endpoint."""
        self._open()
        try:
            if self._pending is not None:
                raise self._wire.ReservationProtocolError()
            payload = self._wire.read_reservation_frame(read, allow_orderly_eof=True)
            self._reject_reentry()
            if payload is None:
                self._eof_received = True
            else:
                self._prepare_request(payload)
        except self._wire.ReservationProtocolError:
            self._terminate()
            raise

    @_reservation_transition
    def fail_uncertain(self) -> None:
        """Retain max(actual, acknowledged prospective) until later root removal.

        No release/recovery API exists here. Missing observations preserve the
        previous floor. Even an over-budget actual size is retained, never
        clamped. Overflow rejects after retaining per-category facts; no wire
        total is emitted for the failed operation.
        """
        if self._orderly_completed:
            raise self._wire.ReservationProtocolError()
        self._terminate()
        self._uncertain = True
        charged, reserved = list(self._charged), list(self._reserved)
        invalid = False
        for index, kind in enumerate(self._wire.RESERVATION_KINDS):
            try:
                actual = self._observation(kind)
            except self._wire.ReservationProtocolError:
                invalid = True
                continue
            charged[index] = max(charged[index], actual)
            reserved[index] = max(reserved[index], actual)
        self._charged, self._reserved = tuple(charged), tuple(reserved)
        self._total(self._reserved)
        if invalid:
            raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")



# Fixed creation roles from the Git-effective category-attribution clarification.
_ACCOUNTING_ROLES = {
    "source_snapshot_copy": "snapshot_growth",
    "source_publication_temporary": "snapshot_growth",
    "projection_publication_copy": "projection_publication",
    "projection_publication_temporary": "projection_publication",
    "projection_candidate": "reconstruction_growth",
    "reconstruction_candidate": "reconstruction_growth",
    "bootstrap_request": "controller_temporary_growth",
    "stdout_capture": "worker_output_growth",
    "stderr_capture": "worker_output_growth",
    "controller_temporary": "controller_temporary_growth",
    "worker_output": "worker_output_growth",
}


@dataclass(frozen=True, slots=True)
class _ControllerAccountingBinding:
    operation_id: str
    creation_role: str
    category: str
    descriptor: int
    identity: tuple[int, int]
    group: int


@dataclass(frozen=True)
class _AccountingDecision:
    # Session objects are private staged copies, never mutated after publication.
    session: ControllerReservationSession | None = None
    bindings: Mapping = None
    target: _ControllerAccountingBinding | None = None
    prepared_sizes: tuple | None = None
    prepared_payload: bytes | None = None
    granted_sizes: tuple | None = None
    growth: int = 0
    spent: bool = False
    acknowledgment: bytes | None = None


class ControllerDescriptorAccounting:
    """Isolated controller creation-role binding; no writer, IPC or release API.

    Only trusted controller creation code may call bind_created. Its role and
    producer describe a separately authorized creation operation, never worker
    material. Source/copy input authority remains that creation code's duty.
    The optional request identity comes from the controller's authenticated
    bootstrap envelope before growth; accounting does not certify its bytes.

    Object FDs are BORROWED from that controller creator, which must keep them
    open. Inventory uses the namespace's existing single disposal ledger for
    temporary observation FDs. No root/lease/object ownership is transferred.
    No persistent role metadata or category recovery is introduced.
    """
    def __init__(self, namespace: ControllerOperationNamespace, operation: ControllerOperationRoot,
                 *, bootstrap_request_identity: str | None = None):
        from orev3.execution import bounded_streaming_worker_bootstrap as wire
        if type(namespace) is not ControllerOperationNamespace or type(operation) is not ControllerOperationRoot:
            _recovery_reject()
        if getattr(operation, "_accounting_bridge", None) is not None:
            _recovery_reject()
        if bootstrap_request_identity is not None and (
            type(bootstrap_request_identity) is not str
            or re.fullmatch(r"[0-9a-f]{64}", bootstrap_request_identity) is None
        ):
            _recovery_reject()
        self._namespace = namespace
        self._operation = operation
        self._operation_id = wire.reservation_operation_id(operation.operation_id)
        self._request_identity = bootstrap_request_identity
        self._wire = wire
        self._state = _AccountingDecision(bindings={})
        self._staged = None
        self._busy = False
        self._failed = False
        self._observations: tuple[int, ...] | None = None
        with self._locked():
            if getattr(operation, "_accounting_bridge", None) is not None:
                self._reject()
            self._inventory()
            operation._accounting_bridge = self

    @property
    def _state(self):
        previous, slot = self._publication
        decision = slot.get("decision")
        return previous if decision is None else decision

    @_state.setter
    def _state(self, value):
        self._publication = (value, {})

    @property
    def _session(self):
        return (self._staged if self._staged is not None else self._state).session

    @_session.setter
    def _session(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, session=value)

    @property
    def _bindings(self):
        return (self._staged if self._staged is not None else self._state).bindings

    @_bindings.setter
    def _bindings(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, bindings=value)

    @property
    def _target(self):
        return (self._staged if self._staged is not None else self._state).target

    @_target.setter
    def _target(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, target=value)

    @property
    def _prepared_sizes(self):
        return (self._staged if self._staged is not None else self._state).prepared_sizes

    @_prepared_sizes.setter
    def _prepared_sizes(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, prepared_sizes=value)

    @property
    def _prepared_payload(self):
        return (self._staged if self._staged is not None else self._state).prepared_payload

    @_prepared_payload.setter
    def _prepared_payload(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, prepared_payload=value)

    @property
    def _granted_sizes(self):
        return (self._staged if self._staged is not None else self._state).granted_sizes

    @_granted_sizes.setter
    def _granted_sizes(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, granted_sizes=value)

    @property
    def _growth(self):
        return (self._staged if self._staged is not None else self._state).growth

    @_growth.setter
    def _growth(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, growth=value)

    @property
    def _spent(self):
        return (self._staged if self._staged is not None else self._state).spent

    @_spent.setter
    def _spent(self, value):
        if self._staged is None:
            self._reject()
        self._staged = replace(self._staged, spent=value)

    def _reject(self) -> None:
        raise self._wire.ReservationProtocolError("DISK_RESERVATION_STATE_MISMATCH")

    def _borrowed_live(self) -> None:
        # Run before opening scratch FDs: a closed borrowed integer must not be
        # accidentally authenticated after inventory reuses that same number.
        owner = self._operation
        if (len(owner._entries) != 6 or owner.unresolved_closes
                or any(fd not in owner._descriptors.pending for fd in owner._owned_descriptors)):
            self._reject()
        uid = owner._entries[0].opened.st_uid
        if os.geteuid() != uid:
            self._reject()
        for entry in owner._entries:
            actual = os.fstat(entry.descriptor)
            if ((actual.st_dev, actual.st_ino, actual.st_uid, actual.st_gid, actual.st_mode) !=
                    (entry.opened.st_dev, entry.opened.st_ino, uid, entry.opened.st_gid, entry.opened.st_mode)):
                self._reject()
        for binding in self._bindings.values():
            actual = os.fstat(binding.descriptor)
            if ((actual.st_dev, actual.st_ino, actual.st_gid) != (*binding.identity, binding.group)
                    or actual.st_uid != uid or not stat.S_ISREG(actual.st_mode)
                    or stat.S_IMODE(actual.st_mode) != 0o600 or actual.st_nlink != 1):
                self._reject()

    @contextmanager
    def _locked(self, *, failed_ok: bool = False, request_rejection: bool = False):
        # Ownership precedes even descriptor preflight and the coordination flock.
        with _CONTROLLER_INTERVAL.enter() as ownership:
            if self._busy or (self._failed and not failed_ok):
                self._reject()
            previous = None
            try:
                self._busy = True
                previous = self._state
                # Reads see previous until this interval's write-once slot wins
                # publication. Invalidation writes the same slot, not a second
                # flag checked before a later state assignment.
                self._publication = (previous, ownership[2])
                self._staged = replace(previous, session=copy.copy(previous.session),
                                       bindings=dict(previous.bindings))
                self._borrowed_live()
                with self._namespace._locked(ownership=ownership):
                    try:
                        yield
                        _CONTROLLER_INTERVAL.check(ownership)
                        self._publish()
                    except self._wire.ReservationProtocolError as error:
                        raise CanonicalControlError(error.code) from None
            except BaseException as error:
                self._failed = True
                if previous is None:
                    # Entry failed before its prior state was captured. Nothing
                    # was staged or committed; quarantine without re-reading the
                    # failing accessor or masking the original BaseException.
                    raise
                committed = self._state is not previous
                # Discard partial staged core assignments. Failure state is also
                # built privately and published whole, never repaired in place.
                failed = copy.copy(self._state.session)
                if failed is not None:
                    if failed._orderly_completed:
                        pass  # Proven reconciliation is final even if close fails.
                    elif request_rejection and not committed:
                        failed._terminate()
                    else:
                        try:
                            failed.fail_uncertain()
                        except self._wire.ReservationProtocolError:
                            pass
                    self._state = replace(self._state, session=failed)
                if isinstance(error, Exception) and not isinstance(error, CanonicalControlError):
                    raise CanonicalControlError("DISK_RESERVATION_STATE_MISMATCH") from None
                raise
            finally:
                try:
                    self._staged = None
                finally:
                    try:
                        self._observations = None
                    finally:
                        self._busy = False

    def _publish(self):
        # Linearization is this exact built-in setdefault, shared with invalidate.
        # Under CPython it cannot run Python callbacks between choosing the winner
        # and inserting it (exact dict, literal str key, no replacement/decref).
        # Before it, invalidation wins with None; after it, the complete decision
        # is already authoritative through _state, even if this call is interrupted.
        decision = self._publication[1].setdefault("decision", self._staged)
        if decision is not self._staged:
            self._reject()

    @contextmanager
    def controller_mutation(self):
        """Exclusion for separately authorized controller creation/FD mutations.

        This grants no creation, write, publication or descriptor ownership.
        Authorized callbacks/handlers must use this boundary and defer on failure;
        raw OS bypass by equivalent trusted-controller code is outside the model.
        """
        with _CONTROLLER_INTERVAL.enter() as ownership:
            if self._failed:
                self._reject()
            with self._namespace._locked(ownership=ownership):
                yield
                _CONTROLLER_INTERVAL.check(ownership)

    @contextmanager
    def writer_activity(self, binding: _ControllerAccountingBinding, *, sequence: int):
        """Unactivated synchronous writer-lifecycle boundary, not a writer.

        Caller must be the trusted governed creator/writer integration. No worker
        boolean establishes quiescence. Only one matching grant can enter; the
        owner excludes admission for the whole activity. Leaving this context
        establishes stopped/completed activity. Request-wait cannot spend old
        allowance. Real integration must keep every sampled writer in this model.
        """
        with self._locked():
            self._binding(binding)
            if (self._session is None or self._session.snapshot.terminal
                    or self._prepared_sizes is not None or binding is not self._target
                    or self._granted_sizes is None or self._spent
                    or type(sequence) is not int or sequence != self._grant_sequence()):
                self._reject()
            self._check_granted(self._sample())
            self._spent = True
            yield
            self._check_granted(self._sample())

    def _grant_sequence(self):
        sequence = self._session.snapshot.expected_sequence
        return self._wire.RESERVATION_UINT64_MAX if sequence is None else sequence - 1

    def _validate_existing(self):
        snapshot = self._session.snapshot
        for actual, charged, reserved in zip(self._observations,
                snapshot.charged_bytes, snapshot.reserved_bytes, strict=True):
            if not charged <= actual <= reserved:
                self._reject()

    def _inventory(self) -> dict[tuple[int, int], tuple[_RecoveryEntry, tuple[str, ...]]]:
        ns, owner = self._namespace, self._operation
        if (not self._busy or owner.operation_id != self._operation_id
                or len(owner._entries) != 6 or owner.unresolved_closes
                or any(fd not in owner._descriptors.pending for fd in owner._owned_descriptors)):
            self._reject()
        root = ns._open(ns._operations, self._operation_id, True)
        # Match all borrowed role/root/lease descriptors to the newly pinned
        # namespace bindings. Do not authenticate via old, already-closed parents.
        lease, acquired = ns._lease(root)
        if acquired:
            self._reject()  # An unlocked/orphan root is not live accounting authority.
        directories = tuple(ns._open(root, name, True) for name in _OPERATION_DIRECTORIES)
        for held, fresh in zip(owner._entries, (root, lease, *directories), strict=True):
            actual = os.fstat(held.descriptor)
            if ((actual.st_dev, actual.st_ino, actual.st_gid) !=
                    (held.opened.st_dev, held.opened.st_ino, held.opened.st_gid)
                    or _recovery_signature(actual) != _recovery_signature(fresh.authenticate(ns._uid))):
                self._reject()
        nodes, _ = ns._inventory(root, lease, set())
        objects = {}
        for entry in nodes:
            if entry.directory or entry is lease:
                continue
            path = []
            current = entry
            while current is not root:
                path.append(current.name)
                current = current.parent
            identity = (entry.opened.st_dev, entry.opened.st_ino)
            objects[identity] = entry, tuple(reversed(path))
        return objects

    def _totals(self, objects) -> tuple[int, ...]:
        if set(objects) != set(self._bindings):
            self._reject()  # Missing, deleted or unattributable active objects.
        totals = [0] * len(self._wire.RESERVATION_KINDS)
        for identity, binding in self._bindings.items():
            entry, path = objects[identity]
            actual = os.fstat(binding.descriptor)
            if (binding.operation_id != self._operation_id
                    or (actual.st_dev, actual.st_ino, actual.st_gid) != (*identity, binding.group)
                    or _recovery_signature(actual) != _recovery_signature(entry.authenticate(self._namespace._uid, unchanged=True))
                    or ((path == ("bounded-bootstrap-request.json",)) != (binding.creation_role == "bootstrap_request"))):
                self._reject()
            index = self._wire.RESERVATION_KINDS.index(binding.category)
            totals[index] = _recovery_size_add(totals[index], actual.st_size)
        total = 0
        for size in totals:
            total = _recovery_size_add(total, size)
        return tuple(totals)

    def bind_created(self, descriptor: int, *, operation_id: str, creation_role: str,
                     producer: str, request_identity: str | None = None) -> _ControllerAccountingBinding:
        """Trusted controller call after authorized creation, before first growth.

        A specific role wins over generic producer identity. Contradictory roles
        or duplicate binding fail; there is no replacement/reclassification API.
        """
        if type(descriptor) is not int or descriptor < 0:
            self._reject()
        try:
            before = os.fstat(descriptor)
        except OSError:
            raise CanonicalControlError("DISK_RESERVATION_STATE_MISMATCH") from None
        with self._locked():
            if (type(descriptor) is not int or descriptor < 0 or type(operation_id) is not str or operation_id != self._operation_id
                    or type(creation_role) is not str or creation_role not in _ACCOUNTING_ROLES
                    or type(producer) is not str or producer not in ("controller", "worker")
                    or (creation_role in ("controller_temporary", "bootstrap_request") and producer != "controller")
                    or (creation_role == "worker_output" and producer != "worker")
                    or (creation_role == "bootstrap_request" and
                        (self._request_identity is None or request_identity != self._request_identity))
                    or (creation_role != "bootstrap_request" and request_identity is not None)
                    or (self._session is not None and
                        (self._session.snapshot.pending_request or self._session.snapshot.terminal))):
                self._reject()
            objects = self._inventory()
            actual = os.fstat(descriptor)
            if _recovery_signature(actual) != _recovery_signature(before):
                self._reject()
            identity = actual.st_dev, actual.st_ino
            if identity not in objects or identity in self._bindings:
                self._reject()
            entry, path = objects[identity]
            if (_recovery_signature(actual) != _recovery_signature(entry.authenticate(self._namespace._uid, unchanged=True))
                    or ((path == ("bounded-bootstrap-request.json",)) != (creation_role == "bootstrap_request"))):
                self._reject()
            if self._session is not None:
                if actual.st_size != 0 or set(objects) != set(self._bindings) | {identity}:
                    self._reject()
            binding = _ControllerAccountingBinding(self._operation_id, creation_role,
                _ACCOUNTING_ROLES[creation_role], descriptor, identity, actual.st_gid)
            self._bindings = {**self._bindings, identity: binding}
            if self._granted_sizes is not None:
                self._granted_sizes = tuple(sorted((*self._granted_sizes, (identity, 0))))
        return binding

    def _observe(self, category: str) -> int:
        if not self._busy or self._observations is None:
            self._reject()
        return self._observations[self._wire.RESERVATION_KINDS.index(category)]

    def _sample(self):
        self._observations = None
        objects = self._inventory()
        self._observations = self._totals(objects)
        return tuple(sorted((identity, entry.opened.st_size) for identity, (entry, _) in objects.items()))

    def _binding(self, binding):
        if type(binding) is not _ControllerAccountingBinding or self._bindings.get(binding.identity) is not binding:
            self._reject()

    def _check_granted(self, sizes) -> None:
        if self._granted_sizes is None:
            return
        before, after = dict(self._granted_sizes), dict(sizes)
        if set(before) != set(after):
            self._reject()
        for identity, size in before.items():
            maximum = _recovery_size_add(size, self._growth) if self._target is not None and identity == self._target.identity else size
            if not size <= after[identity] <= maximum:
                self._reject()

    def observe(self, category: str) -> int:
        with self._locked():
            self._sample()
            if category not in self._wire.RESERVATION_KINDS:
                self._reject()
            result = self._observe(category)
        return result

    def start_session(self, *, max_temporary_disk_bytes: int) -> None:
        with self._locked():
            if self._session is not None:
                self._reject()
            self._granted_sizes = self._sample()
            self._session = ControllerReservationSession(operation_id=self._operation_id,
                max_temporary_disk_bytes=max_temporary_disk_bytes, controller_observe=self._observe)

    @property
    def snapshot(self) -> ReservationAccountingSnapshot:
        session = self._state.session
        if session is None:
            self._reject()
        return session.snapshot

    def prepare_request(self, binding: _ControllerAccountingBinding, payload: bytes) -> None:
        with self._locked(request_rejection=True):
            self._binding(binding)
            sizes = self._sample()
            self._check_granted(sizes)
            request = self._wire.parse_reservation_payload(payload)
            if (request["message_type"] != "reserve_growth"
                    or request["operation_id"] != self._operation_id
                    or request["reservation_kind"] != binding.category or self._session is None):
                self._reject()
            self._validate_existing()
            self._session.prepare_request(payload)
            self._target, self._prepared_sizes = binding, sizes
            self._growth = request["requested_growth_bytes"]
            self._prepared_payload = payload

    def issue_acknowledgment(self) -> bytes:
        with self._locked(request_rejection=True):
            if self._session is None or self._target is None:
                self._reject()
            self._binding(self._target)
            if self._sample() != self._prepared_sizes:
                self._reject()
            self._validate_existing()
            # All observed growth has been explained by existing allowances.
            # Stage complete current charge; preserve every other category's
            # conservative reserved floor. Nothing is visible before publication.
            self._session._charged = self._observations
            self._session._pending = None
            self._session.prepare_request(self._prepared_payload)
            result = self._session.issue_acknowledgment()
            self._granted_sizes = self._prepared_sizes
            self._prepared_sizes = None
            self._prepared_payload = None
            self._spent = False
            self._staged = replace(self._staged, acknowledgment=result)
        return result

    def observe_completion(self, binding: _ControllerAccountingBinding) -> None:
        with self._locked():
            self._binding(binding)
            if self._session is None or binding is not self._target or self._prepared_sizes is not None:
                self._reject()
            self._check_granted(self._sample())
            self._session.observe_completion(binding.category)

    def orderly_eof(self) -> None:
        with self._locked():
            if self._session is None:
                self._reject()
            self._check_granted(self._sample())
            self._session.orderly_eof()

    def fail_uncertain(self) -> None:
        with self._locked(failed_ok=True):
            if self._session is None:
                self._reject()
            self._sample()
            self._session.fail_uncertain()


@dataclass(frozen=True, slots=True)
class LockedWheel:
    package_name: str
    version: str
    filename: str
    url: str
    sha256: str


@dataclass(frozen=True, slots=True)
class DependencyLockV1:
    wheels: tuple[LockedWheel, ...]

    @property
    def packages(self) -> tuple[tuple[str, str], ...]:
        return tuple((item.package_name, item.version) for item in self.wheels)


@dataclass(frozen=True, slots=True)
class OfflineArtifactManifestV1:
    material: Mapping[str, Any]
    manifest_identity: str
    artifacts_by_digest: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ClosedDependencyRoot:
    path: Path
    identity: str
    distributions: tuple[tuple[str, str], ...]
    file_count: int


@dataclass(frozen=True, slots=True)
class RuntimeContractV1:
    material: Mapping[str, Any]
    runtime_contract_identity: str
    dependency_lock_path: str
    dependency_lock_sha256: str
    artifact_manifest_path: str
    artifact_manifest_sha256: str


@dataclass(frozen=True, slots=True)
class PreparationWorkerEvidence:
    command: str
    material: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Phase3BWorkerEvidence:
    worker_kind: str
    evidence_identity: str
    material: Mapping[str, Any]
    result: Mapping[str, Any]


def _normalized_distribution_name(value: str) -> str:
    normalized = re.sub(r"[-_.]+", "-", value).lower()
    if not _NORMALIZED_NAME.fullmatch(normalized):
        raise CanonicalControlError("dependency distribution name is invalid")
    return normalized


def reconstruct_runtime_contract_identity(material: Mapping[str, Any]) -> str:
    require_sha256("runtime_contract_identity", material.get("runtime_contract_identity"))
    identity_material = dict(material)
    del identity_material["runtime_contract_identity"]
    return domain_identity(RUNTIME_CONTRACT_DOMAIN, identity_material)


def reconstruct_offline_artifact_manifest_identity(material: Mapping[str, Any]) -> str:
    require_sha256("artifact_manifest_identity", material.get("artifact_manifest_identity"))
    identity_material = dict(material)
    del identity_material["artifact_manifest_identity"]
    return domain_identity(OFFLINE_ARTIFACT_MANIFEST_DOMAIN, identity_material)


def load_runtime_contract_bytes(raw: bytes, *, schema: Mapping[str, Any]) -> RuntimeContractV1:
    material = parse_canonical_bytes(raw, max_bytes=MAX_RUNTIME_CONTRACT_BYTES)
    validate_json_schema_instance(material, schema, schema_registry={})
    if reconstruct_runtime_contract_identity(material) != material["runtime_contract_identity"]:
        raise CanonicalControlError("runtime contract identity does not reconstruct")
    lock = material["dependency_lock"]
    validate_repository_path(lock["path"])
    if not _LOCK_FILENAME.fullmatch(PurePosixPath(lock["path"]).name):
        raise CanonicalControlError("dependency lock filename is not PEP 751 conformant")
    lock_identity_material = {
        "format": lock["format"],
        "git_blob_binding": lock["git_blob_binding"],
        "path": lock["path"],
        "sha256": lock["sha256"],
    }
    if domain_identity(DEPENDENCY_LOCK_DOMAIN, lock_identity_material) != lock["lock_identity"]:
        raise CanonicalControlError("dependency lock identity does not reconstruct")
    artifact_manifest = lock["offline_artifact_manifest"]
    validate_repository_path(artifact_manifest["path"])
    profile = material["network_isolation"]
    if domain_identity(
        NETWORK_SANDBOX_DOMAIN,
        {"mechanism": profile["mechanism"], "profile": NETWORK_SANDBOX_PROFILE},
    ) != profile["profile_identity"]:
        raise CanonicalControlError("network-isolation profile identity differs")
    return RuntimeContractV1(
        material,
        material["runtime_contract_identity"],
        lock["path"],
        lock["sha256"],
        artifact_manifest["path"],
        artifact_manifest["sha256"],
    )


def validate_dependency_lock(raw: bytes, *, expected_sha256: str) -> DependencyLockV1:
    if len(raw) > MAX_DEPENDENCY_LOCK_BYTES:
        raise CanonicalControlError("dependency lock exceeds the byte limit")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CanonicalControlError("dependency lock digest differs from runtime contract")
    try:
        material = tomllib.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CanonicalControlError("dependency lock is not strict UTF-8 PEP 751 TOML") from exc
    if set(material) != {"lock-version", "created-by", "packages"}:
        raise CanonicalControlError("dependency lock contains unsupported top-level fields")
    if material["lock-version"] != "1.0" or not isinstance(material["created-by"], str):
        raise CanonicalControlError("dependency lock is not the supported PEP 751 form")
    packages = material["packages"]
    if not isinstance(packages, list) or not packages:
        raise CanonicalControlError("dependency lock package set is empty")
    wheels: list[LockedWheel] = []
    names: list[str] = []
    for package in packages:
        if not isinstance(package, dict) or set(package) != {"name", "version", "wheels"}:
            raise CanonicalControlError("dependency lock package is malformed")
        name = _normalized_distribution_name(package["name"])
        version = package["version"]
        package_wheels = package["wheels"]
        if not isinstance(version, str) or not version or not isinstance(package_wheels, list):
            raise CanonicalControlError("dependency lock package is incomplete")
        if name in names:
            raise CanonicalControlError("dependency lock package is duplicated")
        names.append(name)
        if len(package_wheels) != 1:
            raise CanonicalControlError("v1 requires exactly one selected wheel per package")
        wheel = package_wheels[0]
        if not isinstance(wheel, dict) or set(wheel) != {"name", "url", "hashes"}:
            raise CanonicalControlError("dependency wheel declaration is malformed")
        hashes = wheel["hashes"]
        if not isinstance(hashes, dict) or set(hashes) != {"sha256"}:
            raise CanonicalControlError("dependency wheel hashes are malformed")
        digest = hashes["sha256"]
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise CanonicalControlError("dependency wheel lacks a normalized SHA-256")
        filename, url = wheel["name"], wheel["url"]
        if not isinstance(filename, str) or not filename.endswith(".whl"):
            raise CanonicalControlError("dependency artifact is not a wheel")
        if not isinstance(url, str):
            raise CanonicalControlError("dependency wheel URL is invalid")
        split = urlsplit(url)
        if split.scheme != "https" or not split.hostname or split.username or split.password or split.query or split.fragment:
            raise CanonicalControlError("dependency wheel URL is not credential-free HTTPS")
        if PurePosixPath(split.path).name != filename:
            raise CanonicalControlError("dependency wheel filename and URL disagree")
        wheels.append(LockedWheel(name, version, filename, url, digest))
    if names != sorted(names):
        raise CanonicalControlError("dependency lock packages are not canonically ordered")
    return DependencyLockV1(tuple(wheels))


def load_offline_artifact_manifest_bytes(
    raw: bytes,
    *,
    schema: Mapping[str, Any],
    expected_sha256: str,
    dependency_lock_sha256: str,
    dependency_lock: DependencyLockV1,
) -> OfflineArtifactManifestV1:
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CanonicalControlError("offline artifact manifest digest differs")
    material = parse_canonical_bytes(raw, max_bytes=MAX_ARTIFACT_MANIFEST_BYTES)
    validate_json_schema_instance(material, schema, schema_registry={})
    if reconstruct_offline_artifact_manifest_identity(material) != material["artifact_manifest_identity"]:
        raise CanonicalControlError("offline artifact manifest identity does not reconstruct")
    if material["dependency_lock_sha256"] != dependency_lock_sha256:
        raise CanonicalControlError("offline artifact manifest binds another lock")
    expected = [
        {
            "filename": item.filename,
            "package_name": item.package_name,
            "relative_store_path": f"sha256/{item.sha256}.whl",
            "sha256": item.sha256,
            "version": item.version,
        }
        for item in dependency_lock.wheels
    ]
    if material["artifacts"] != expected:
        raise CanonicalControlError("offline artifact manifest differs from the dependency lock")
    return OfflineArtifactManifestV1(
        material,
        material["artifact_manifest_identity"],
        {item["sha256"]: item for item in material["artifacts"]},
    )


def _safe_wheel_member_path(value: str) -> PurePosixPath:
    if not value or "\\" in value or "\x00" in value:
        raise CanonicalControlError("wheel member path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CanonicalControlError("wheel member path escapes the dependency root")
    return path


def _wheel_target_path(path: PurePosixPath) -> PurePosixPath | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if part.endswith(".data"):
            if index + 2 > len(parts):
                raise CanonicalControlError("wheel .data member is malformed")
            scheme = parts[index + 1]
            if scheme not in {"purelib", "platlib"}:
                raise CanonicalControlError("wheel contains a non-import dependency payload")
            remainder = parts[index + 2 :]
            return PurePosixPath(*remainder) if remainder else None
    return path


def _validate_wheel_record(archive: zipfile.ZipFile, names: set[str]) -> None:
    records = [name for name in names if name.endswith(".dist-info/RECORD")]
    if len(records) != 1:
        raise CanonicalControlError("wheel must contain exactly one RECORD")
    try:
        rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode("utf-8", errors="strict"))))
    except (UnicodeDecodeError, csv.Error, KeyError) as exc:
        raise CanonicalControlError("wheel RECORD is malformed") from exc
    declared: set[str] = set()
    for row in rows:
        if len(row) != 3 or not row[0]:
            raise CanonicalControlError("wheel RECORD row is malformed")
        member = _safe_wheel_member_path(row[0]).as_posix()
        if member in declared:
            raise CanonicalControlError("wheel RECORD path is duplicated")
        declared.add(member)
        if member == records[0]:
            if row[1] or row[2]:
                raise CanonicalControlError("wheel RECORD self-entry must be unhashed")
            continue
        if not row[1].startswith("sha256=") or not row[2].isdigit():
            raise CanonicalControlError("wheel RECORD entry lacks a deterministic identity")
        raw = archive.read(member)
        import base64

        encoded = row[1][7:]
        expected = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        if hashlib.sha256(raw).digest() != expected or len(raw) != int(row[2]):
            raise CanonicalControlError("wheel RECORD identity differs from member bytes")
    file_names = {name for name in names if not name.endswith("/")}
    if declared != file_names:
        raise CanonicalControlError("wheel contains an unrecorded file")


def construct_closed_dependency_root(
    dependency_lock: DependencyLockV1,
    manifest: OfflineArtifactManifestV1,
    artifact_store_root: Path,
    destination: Path,
) -> ClosedDependencyRoot:
    store = artifact_store_root.resolve()
    if artifact_store_root.is_symlink() or not store.is_dir():
        raise CanonicalControlError("offline artifact store is unavailable or is a symlink")
    if destination.exists() and any(destination.iterdir()):
        raise CanonicalControlError("closed dependency root is not empty")
    destination.mkdir(parents=True, exist_ok=True)
    owners: dict[str, str] = {}
    written: set[str] = set()
    artifact_material: list[dict[str, object]] = []
    for wheel in dependency_lock.wheels:
        declaration = manifest.artifacts_by_digest.get(wheel.sha256)
        if declaration is None:
            raise CanonicalControlError("required offline dependency artifact is undeclared")
        candidate = store / declaration["relative_store_path"]
        if candidate.is_symlink() or not candidate.is_file():
            raise CanonicalControlError(f"offline dependency artifact is unavailable: {wheel.package_name}")
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != wheel.sha256:
            raise CanonicalControlError(f"offline dependency artifact digest differs: {wheel.package_name}")
        top_levels: set[str] = set()
        try:
            with zipfile.ZipFile(candidate) as archive:
                infos = archive.infolist()
                names = {info.filename for info in infos}
                if len(names) != len(infos):
                    raise CanonicalControlError("wheel archive member path is duplicated")
                _validate_wheel_record(archive, names)
                for info in sorted(infos, key=lambda item: item.filename):
                    source_path = _safe_wheel_member_path(info.filename)
                    mode = (info.external_attr >> 16) & 0o170000
                    if mode not in {0, stat.S_IFREG, stat.S_IFDIR}:
                        raise CanonicalControlError("wheel contains a non-regular member")
                    target_path = _wheel_target_path(source_path)
                    if target_path is None or info.is_dir():
                        continue
                    normalized = target_path.as_posix()
                    if normalized in written:
                        raise CanonicalControlError("locked wheels contain a path collision")
                    written.add(normalized)
                    first = target_path.parts[0]
                    if not first.endswith((".dist-info", ".data")):
                        top_levels.add(first.removesuffix(".py"))
                    target = destination.joinpath(*target_path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(info.filename))
        except zipfile.BadZipFile as exc:
            raise CanonicalControlError("offline dependency artifact is not a valid wheel") from exc
        for top_level in sorted(top_levels):
            previous = owners.setdefault(top_level, wheel.package_name)
            if previous != wheel.package_name:
                raise CanonicalControlError("locked wheels contain a top-level package collision")
        artifact_material.append(
            {
                "filename": wheel.filename,
                "package_name": wheel.package_name,
                "sha256": wheel.sha256,
                "top_level_names": sorted(top_levels),
                "version": wheel.version,
            }
        )
    files: list[dict[str, object]] = []
    for path in sorted(destination.rglob("*")):
        if path.is_symlink():
            raise CanonicalControlError("closed dependency root contains a symlink")
        if path.is_file():
            relative = path.relative_to(destination).as_posix()
            raw = path.read_bytes()
            files.append({"byte_count": len(raw), "path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
    distributions: dict[str, str] = {}
    for distribution in importlib.metadata.distributions(path=[str(destination)]):
        name_value = distribution.metadata.get("Name")
        if not name_value:
            raise CanonicalControlError("closed dependency distribution lacks a name")
        name = _normalized_distribution_name(name_value)
        if name in distributions:
            raise CanonicalControlError("closed dependency distribution is duplicated")
        if distribution.read_text("direct_url.json") is not None:
            raise CanonicalControlError("direct/editable dependency installation is prohibited")
        distributions[name] = distribution.version
    if tuple(sorted(distributions.items())) != dependency_lock.packages:
        raise CanonicalControlError("closed dependency root distribution set differs from lock")
    material = {
        "artifacts": artifact_material,
        "distributions": [{"name": name, "version": version} for name, version in sorted(distributions.items())],
        "files": files,
        "root_format": "wheel-projection-v1",
    }
    return ClosedDependencyRoot(destination, domain_identity(DEPENDENCY_ENVIRONMENT_DOMAIN, material), tuple(sorted(distributions.items())), len(files))


def reconstruct_runtime_bundle_identity(*, interpreter: Path | None = None) -> str:
    executable = (interpreter or Path(sys.executable)).resolve()
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    files: list[dict[str, object]] = []
    for path in sorted(stdlib.rglob("*")):
        relative = path.relative_to(stdlib)
        if "site-packages" in relative.parts or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            resolved = path.resolve()
            if not resolved.is_file():
                raise CanonicalControlError("runtime bundle symlink target is unavailable")
            files.append({"byte_count": resolved.stat().st_size, "path": relative.as_posix(), "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(), "symlink_target": path.readlink().as_posix()})
        elif path.is_file():
            files.append({"byte_count": path.stat().st_size, "path": relative.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return domain_identity(
        RUNTIME_BUNDLE_DOMAIN,
        {
            "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "files": files,
            "python": {"abi_tag": sysconfig.get_config_var("SOABI"), "cache_tag": sys.implementation.cache_tag, "implementation": platform.python_implementation(), "platform_tag": sysconfig.get_platform(), "version": platform.python_version()},
        },
    )


def _bounded_tool(path: Path, *arguments: str) -> str:
    result = _run_bounded_process((str(path), *arguments), cwd=Path("/"), environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}, timeout_seconds=30, max_output_bytes=4 * 1024 * 1024)
    if result.returncode != 0:
        raise CanonicalControlError(f"runtime identity tool failed: {path.name}")
    return result.stdout.decode("utf-8", errors="strict")


def _normalize_install_name(value: str) -> tuple[str, str]:
    if "Python.framework/Versions/" in value and value.endswith("/Python"):
        resolved = Path(value)
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest() if resolved.is_file() else ""
        return "python-framework/Python", digest
    return value, ""


def reconstruct_host_system_material(dependency_root: Path, *, interpreter: Path | None = None) -> Mapping[str, Any]:
    executable = (interpreter or Path(sys.executable)).resolve()
    consumers: list[tuple[str, Path]] = [("python", executable)]
    for path in sorted(dependency_root.rglob("*")):
        if path.is_file() and path.suffix in {".so", ".dylib"}:
            consumers.append((f"dependency/{path.relative_to(dependency_root).as_posix()}", path))
    links: list[dict[str, str]] = []
    pattern = re.compile(r"^\s+(.+?) \(compatibility version ([^,]+), current version ([^)]+)\)$")
    for consumer, path in consumers:
        output = _bounded_tool(OTOOL, "-L", str(path))
        for line in output.splitlines()[1:]:
            match = pattern.match(line)
            if match:
                install_name, digest = _normalize_install_name(match.group(1))
                links.append({"compatibility_version": match.group(2), "consumer": consumer, "current_version": match.group(3), "install_name": install_name, "resolved_sha256": digest})
    unique_links = {
        (
            item["consumer"],
            item["install_name"],
            item["compatibility_version"],
            item["current_version"],
            item["resolved_sha256"],
        ): item
        for item in links
    }
    material: dict[str, Any] = {
        "architecture": platform.machine(),
        "darwin_release": platform.release(),
        "dynamic_links": sorted(unique_links.values(), key=lambda item: (item["consumer"], item["install_name"])),
        "macos_build": _bounded_tool(SW_VERS, "-buildVersion").strip(),
        "macos_version": platform.mac_ver()[0],
        "operating_system": "macOS",
    }
    material["host_system_identity"] = domain_identity(HOST_SYSTEM_DOMAIN, material)
    return material


def validate_host_runtime(contract: RuntimeContractV1, dependency_root: ClosedDependencyRoot, *, interpreter: Path | None = None) -> None:
    material = contract.material
    actual = {
        "abi_tag": sysconfig.get_config_var("SOABI"),
        "cache_tag": sys.implementation.cache_tag,
        "implementation": platform.python_implementation(),
        "platform_tag": sysconfig.get_platform(),
        "runtime_bundle_identity": reconstruct_runtime_bundle_identity(interpreter=interpreter),
        "version": platform.python_version(),
    }
    if actual != material["python"]:
        raise CanonicalControlError("host Python/runtime differs from runtime contract")
    executable_paths = {"otool": OTOOL, "python": (interpreter or Path(sys.executable)).resolve(), "sandbox-exec": MACOS_SANDBOX_EXEC, "sw-vers": SW_VERS}
    expected = {item["executable_identifier"]: item["sha256"] for item in material["allowed_executables"]}
    actual_executables = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in executable_paths.items() if path.is_file()}
    if actual_executables != expected:
        raise CanonicalControlError("allowed executable bytes differ from runtime contract")
    if dependency_root.identity != material["dependency_lock"]["closed_environment_identity"]:
        raise CanonicalControlError("closed dependency environment identity differs")
    if reconstruct_host_system_material(dependency_root.path, interpreter=interpreter) != material["host_system"]:
        raise CanonicalControlError("host/system runtime differs from runtime contract")


def validate_closed_dependency_imports(contract: RuntimeContractV1, dependency_root: ClosedDependencyRoot, source_root: Path) -> tuple[str, ...]:
    source_package_root = (source_root / "src").resolve()
    root = dependency_root.path.resolve()
    if str(root) not in sys.path:
        sys.path.append(str(root))
    origins: list[str] = []
    for probe in contract.material["import_policy"]["dependency_import_probes"]:
        module = importlib.import_module(probe["module"])
        origin = getattr(module, "__file__", "")
        if not origin:
            raise CanonicalControlError("dependency import probe lacks a file origin")
        try:
            relative = Path(origin).resolve().relative_to(root)
        except ValueError as exc:
            raise CanonicalControlError("dependency module escaped the closed root") from exc
        origins.append(relative.as_posix())
    try:
        importlib.import_module("pip")
    except ModuleNotFoundError:
        pass
    else:
        raise CanonicalControlError("undeclared ambient distribution is importable")
    for name, module in tuple(sys.modules.items()):
        if not name.startswith("orev3.execution"):
            continue
        origin = getattr(module, "__file__", "")
        if not origin:
            continue
        try:
            Path(origin).resolve().relative_to(source_package_root)
        except ValueError as exc:
            raise CanonicalControlError("project control-plane module escaped detached S") from exc
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    runtime_lib = stdlib.parent
    for entry in sys.path:
        if not entry:
            continue
        resolved = Path(entry).resolve()
        if resolved in {source_package_root, root}:
            continue
        try:
            resolved.relative_to(runtime_lib)
        except ValueError as exc:
            raise CanonicalControlError("module search path contains an unbound root") from exc
    return tuple(origins)


def sanitized_worker_environment(temp_root: Path) -> dict[str, str]:
    return {"HOME": str(temp_root / "home"), "LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "TMPDIR": str(temp_root / "tmp"), "TZ": "UTC"}


def _seatbelt_path(path: Path) -> tuple[Path, str]:
    resolved = path.resolve(strict=True)
    value = str(resolved)
    if any(character in value for character in ('"', "\\", "\n", "\r", "\x00")):
        raise CanonicalControlError("sandbox capability path cannot be represented safely")
    return resolved, f'"{value}"'


def render_phase3b_sandbox_profile(
    *,
    policy: Mapping[str, Any],
    worker_kind: str,
    worker_name: str,
    command: str,
    source_root: Path,
    dependency_root: Path,
    request_path: Path,
    temporary_root: Path,
    read_files: tuple[Path, ...] = (),
    read_roots: tuple[Path, ...] = (),
    write_roots: tuple[Path, ...] = (),
    interpreter: Path | None = None,
) -> tuple[str, Mapping[str, Any]]:
    """Render one default-deny profile from a governed worker-kind policy."""

    if policy.get("profile_renderer_identity") != PHASE3B_PROFILE_RENDERER_IDENTITY:
        raise CanonicalControlError("Phase-3B profile renderer identity differs")
    workers = policy.get("worker_profiles")
    if not isinstance(workers, list):
        raise CanonicalControlError("Phase-3B worker profile policy is absent")
    matches = [item for item in workers if item.get("worker_kind") == worker_kind]
    if len(matches) != 1:
        raise CanonicalControlError("Phase-3B worker kind is missing or duplicated")
    declaration = matches[0]
    expected_module = f"src/orev3/execution/{worker_name}"
    if declaration.get("module") != expected_module or command not in declaration.get("commands", ()):
        raise CanonicalControlError("Phase-3B worker mapping or command differs from policy")
    if declaration.get("network_policy") != "prohibited" or declaration.get("sandbox_template_revision") != "macos-seatbelt-capability-v4":
        raise CanonicalControlError("Phase-3B sandbox policy is weakened")
    template_material = {
        "allowed_read_roles": declaration.get("allowed_read_roles"),
        "allowed_write_roles": declaration.get("allowed_write_roles"),
        "commands": declaration.get("commands"),
        "denied_roles": declaration.get("denied_roles"),
        "module": declaration.get("module"),
        "network_policy": declaration.get("network_policy"),
        "sandbox_template_revision": declaration.get("sandbox_template_revision"),
        "worker_kind": declaration.get("worker_kind"),
    }
    if domain_identity(PHASE3B_PROFILE_RENDERER_DOMAIN, template_material) != declaration.get("sandbox_template_identity"):
        raise CanonicalControlError("Phase-3B sandbox template identity differs")

    interpreter_path = (interpreter or Path(sys.executable)).resolve(strict=True)
    base_prefix = Path(sys.base_prefix).resolve(strict=True)
    fixed_read_roots = tuple(path for path in (
        source_root,
        dependency_root,
        temporary_root,
        base_prefix,
        Path("/System"),
        Path("/usr/lib"),
        Path("/private/var/db/dyld"),
        Path("/private/etc"),
        Path("/dev"),
    ) if path.exists())
    normalized_read_roots = sorted({_seatbelt_path(path)[0] for path in (*fixed_read_roots, *read_roots)}, key=str)
    normalized_write_roots = sorted({
        _seatbelt_path(path)[0]
        for path in (temporary_root / "home", temporary_root / "tmp", *write_roots)
    }, key=str)
    exact_read_paths: set[Path] = set()
    for path in (request_path, *read_files):
        resolved = _seatbelt_path(path)[0]
        exact_read_paths.add(resolved)
        # Descriptor-relative no-follow traversal needs directory descriptors
        # for the lexical ancestor chain.  Literal directory capabilities do
        # not grant access to sibling children (unlike a Seatbelt subpath).
        exact_read_paths.update(resolved.parents)
    normalized_read_files = sorted(exact_read_paths, key=str)
    _, interpreter_literal = _seatbelt_path(interpreter_path)
    process_executables = [interpreter_literal]
    app_runtime = base_prefix / "Resources/Python.app/Contents/MacOS/Python"
    if app_runtime.exists():
        process_executables.append(_seatbelt_path(app_runtime)[1])
    lines = [
        "(version 1)",
        "(deny default)",
        '(import "system.sb")',
        "(allow process-exec " + " ".join(f"(literal {value})" for value in process_executables) + ")",
        "(allow process-info*)",
        "(allow sysctl-read)",
        "(allow mach-lookup)",
        "(allow ipc-posix*)",
        "(allow file-read-metadata)",
    ]
    for root in normalized_read_roots:
        lines.append(f'(allow file-read* (subpath "{root}"))')
    for path in normalized_read_files:
        lines.append(f'(allow file-read* (literal "{path}"))')
    for root in normalized_write_roots:
        lines.append(f'(allow file-write* (subpath "{root}"))')
    lines.append("(deny network*)")
    profile = "\n".join(lines) + "\n"
    rendered = {
        "sandbox_template_identity": declaration["sandbox_template_identity"],
        "worker_kind": worker_kind,
    }
    return profile, rendered


def _enforce_temporary_disk_limit(roots: tuple[Path, ...], limit: int) -> None:
    total = 0
    entries = 0
    pending = list(roots)
    seen: set[tuple[int, int]] = set()
    while pending:
        root = pending.pop()
        try:
            opened = os.lstat(root)
        except FileNotFoundError:
            continue
        identity = (opened.st_dev, opened.st_ino)
        if identity in seen:
            continue
        seen.add(identity); entries += 1
        if entries > 100_000:
            raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
        if stat.S_ISREG(opened.st_mode):
            total += opened.st_size
        elif stat.S_ISDIR(opened.st_mode):
            with os.scandir(root) as directory:
                pending.extend(Path(item.path) for item in directory)
        if total > limit:
            raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")


def _readiness_test_code_paths(
    repository: GitRepository, source_commit: str, selectors: object
) -> tuple[str, ...]:
    """Return the exact committed code/configuration capability for pytest.

    Phase-3B v1 intentionally supports exact test-file selectors only.  This
    makes collection authority finite and prevents pytest from discovering or
    importing unrelated experiment, parser, Replay, or outcome-capable code.
    """

    if not isinstance(selectors, list) or not selectors:
        raise CanonicalControlError("readiness-test selectors are absent")
    selected: set[str] = set()
    for selector in selectors:
        if not isinstance(selector, str):
            raise CanonicalControlError("readiness-test selector is invalid")
        path = validate_repository_path(selector.split("::", 1)[0])
        if not path.startswith("tests/") or not path.endswith(".py"):
            raise CanonicalControlError("Phase-3B v1 requires exact readiness-test files")
        entry = repository.tree_entry(source_commit, path)
        if entry.object_type != "blob" or entry.mode not in {"100644", "100755"}:
            raise CanonicalControlError("readiness-test selector is not an ordinary committed file")
        selected.add(path)

        parts = path.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            parent = "/".join(parts[:index])
            for candidate in (f"{parent}/conftest.py", f"{parent}/__init__.py"):
                if repository.optional_tree_entry(source_commit, candidate) is not None:
                    selected.add(candidate)

    for candidate in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
        if repository.optional_tree_entry(source_commit, candidate) is not None:
            selected.add(candidate)
    return tuple(sorted(selected))


def run_phase3b_worker(
    source_root: Path,
    source_commit: str,
    worker_kind: str,
    worker_name: str,
    request_material: Mapping[str, Any],
    *,
    dependency_root: Path,
    runtime_contract_identity: str,
    dependency_environment_identity: str,
    capability_policy: Mapping[str, Any],
    invocation_identifier: str = "single",
    input_capability_identities: tuple[str, ...] = (),
    read_files: tuple[Path, ...] = (),
    read_roots: tuple[Path, ...] = (),
    write_roots: tuple[Path, ...] = (),
    timeout_seconds: int = WORKER_TIMEOUT_SECONDS,
    max_output_bytes: int = MAX_WORKER_OUTPUT_BYTES,
    interpreter: Path | None = None,
) -> Phase3BWorkerEvidence:
    """Run one fixed Phase-3B worker; returned material is evidence, not authority."""

    if worker_name not in SAFE_PHASE3B_WORKERS:
        raise CanonicalControlError("Phase-3B worker is not permitted")
    if not invocation_identifier or len(invocation_identifier) > 64 or not all(
        character.islower() or character.isdigit() or character in "-_" for character in invocation_identifier
    ):
        raise CanonicalControlError("Phase-3B worker invocation identifier is invalid")
    temporary_root = Path(tempfile.mkdtemp(prefix="orev3-evidence-worker-"))
    try:
        (temporary_root / "home").mkdir()
        (temporary_root / "tmp").mkdir()
        repository = GitRepository(source_root)
        module_path = f"src/orev3/execution/{worker_name}"
        module_identity = repository.tree_entry(source_commit, module_path).object_identity
        execution_source = source_root
        code_closure_identities: list[str] = []
        if worker_kind in {"READINESS_TEST", "INPUT_PROJECTOR", "REPLAY_PREPARATION"}:
            from orev3.execution.phase3b_components import WORKER_CODE_CLOSURES
            try:
                code_paths = list(WORKER_CODE_CLOSURES[worker_kind])
            except KeyError as exc:
                raise CanonicalControlError("Phase-3B code capability is absent") from exc
            if worker_kind == "READINESS_TEST":
                code_paths.extend(
                    _readiness_test_code_paths(
                        repository, source_commit, request_material.get("selectors")
                    )
                )
            execution_source = temporary_root / "code-capability"
            for relative in sorted(set(code_paths)):
                entry = repository.tree_entry(source_commit, relative)
                raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
                target = execution_source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                code_closure_identities.append(entry.object_identity)
        request = dict(request_material)
        limits = capability_policy.get("limits", {})
        request["resource_limits"] = {
            "max_open_files": limits.get("max_open_files", 256),
            "max_processes": limits.get("max_processes", 16),
            "max_temporary_disk_bytes": limits.get("max_temporary_disk_bytes", 1_073_741_824),
        }
        request["source_root"] = str(execution_source.resolve())
        request["dependency_root"] = str(dependency_root.resolve())
        request_path = temporary_root / "request.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        worker = execution_source / "src/orev3/execution" / worker_name
        profile, profile_material = render_phase3b_sandbox_profile(
            policy=capability_policy,
            worker_kind=worker_kind,
            worker_name=worker_name,
            command=str(request_material.get("command", "")),
            source_root=execution_source,
            dependency_root=dependency_root,
            request_path=request_path,
            temporary_root=temporary_root,
            read_files=read_files,
            read_roots=read_roots,
            write_roots=write_roots,
            interpreter=interpreter,
        )
        try:
            completed = _run_bounded_process(
                (str(MACOS_SANDBOX_EXEC), "-p", profile, str((interpreter or Path(sys.executable)).resolve()), "-I", "-S", str(worker), str(request_path)),
                cwd=execution_source,
                environment=sanitized_worker_environment(temporary_root),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
                periodic_guard=lambda: _enforce_temporary_disk_limit(
                    (temporary_root, *write_roots),
                    int(limits.get("max_temporary_disk_bytes", 1_073_741_824)),
                ),
            )
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.GIT_COMMAND_TIMEOUT:
                raise CanonicalControlError("WORKER_TIMEOUT") from exc
            if exc.code == GitDiagnosticCode.GIT_OUTPUT_LIMIT_EXCEEDED:
                raise CanonicalControlError("WORKER_OUTPUT_LIMIT_EXCEEDED") from exc
            raise
        if completed.returncode != 0:
            default_code = {
                "INPUT_PROJECTOR": "PROJECTION_INVALID",
                "READINESS_TEST": "READINESS_TEST_FAILED",
                "REPLAY_PREPARATION": "REPLAY_IDENTITY_MISMATCH",
            }.get(worker_kind, "EVIDENCE_PREPARATION_INTERNAL_REJECTED")
            stable_code = default_code
            try:
                rejection = json.loads(completed.stdout.decode("utf-8", errors="strict"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                rejection = None
            permitted_failure_codes = {
                "INPUT_MISMATCH",
                "INPUT_MUTATED",
                "INPUT_SCHEMA_MISMATCH",
                "OUTCOME_ISOLATION_VIOLATION",
                "POPULATION_MISMATCH",
                "PROJECTION_INVALID",
                "READINESS_TEST_FAILED",
                "REPLAY_IDENTITY_MISMATCH",
                "RESOURCE_LIMIT_EXCEEDED",
            }
            if (
                isinstance(rejection, dict)
                and rejection.get("status") == "evidence_rejected"
                and rejection.get("failure_code") in permitted_failure_codes
                and set(rejection) == {"failure_code", "status"}
            ):
                stable_code = rejection["failure_code"]
            raise CanonicalControlError(stable_code)
        try:
            result = json.loads(completed.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalControlError("Phase-3B worker result is malformed") from exc
        if not isinstance(result, dict) or result.get("status") != "evidence_passed":
            raise CanonicalControlError("Phase-3B worker did not return evidence")
        result_identity = domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, result)
        material = {
            "capability_policy_identity": capability_policy["policy_identity"],
            "closed_dependency_identity": dependency_environment_identity,
            "command_identity": domain_identity(
                PHASE3B_WORKER_EVIDENCE_DOMAIN,
                {
                    "command": request_material["command"],
                    "invocation_identifier": invocation_identifier,
                    "worker_kind": worker_kind,
                },
            ),
            "code_capability_git_identities": sorted(code_closure_identities),
            "input_capability_identities": list(sorted(input_capability_identities)),
            "output_identity": result_identity,
            "runtime_contract_identity": runtime_contract_identity,
            "sandbox_template_identity": profile_material["sandbox_template_identity"],
            "source_commit": source_commit,
            "successful_worker_disposition": "evidence_passed",
            "worker_kind": worker_kind,
            "worker_module_git_identity": module_identity,
        }
        evidence_identity = domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, material)
        return Phase3BWorkerEvidence(worker_kind, evidence_identity, {**material, "worker_evidence_identity": evidence_identity}, result)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def run_phase3b_controller(
    source_root: Path,
    request_material: Mapping[str, Any],
    *,
    timeout_seconds: int,
    max_output_bytes: int,
    interpreter: Path | None = None,
) -> Mapping[str, Any]:
    """Launch the fixed detached-S controller without Seatbelt so it can create sibling sandboxes."""

    temporary_root = Path(tempfile.mkdtemp(prefix="orev3-evidence-controller-"))
    try:
        (temporary_root / "home").mkdir()
        (temporary_root / "tmp").mkdir()
        request = dict(request_material)
        request["source_root"] = str(source_root.resolve())
        request_path = temporary_root / "request.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        controller = source_root / "src/orev3/execution" / PHASE3B_CONTROLLER
        try:
            completed = _run_bounded_process(
                (str((interpreter or Path(sys.executable)).resolve()), "-I", "-S", str(controller), str(request_path)),
                cwd=source_root,
                environment=sanitized_worker_environment(temporary_root),
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_bytes,
            )
        except GitAuthorityError as exc:
            if exc.code == GitDiagnosticCode.GIT_COMMAND_TIMEOUT:
                raise CanonicalControlError("WORKER_TIMEOUT") from exc
            if exc.code == GitDiagnosticCode.GIT_OUTPUT_LIMIT_EXCEEDED:
                raise CanonicalControlError("WORKER_OUTPUT_LIMIT_EXCEEDED") from exc
            raise
        if completed.returncode != 0:
            raise CanonicalControlError(
                f"detached Phase-3B controller rejected evidence (code {completed.returncode})"
            )
        try:
            result = json.loads(completed.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalControlError("detached Phase-3B controller result is malformed") from exc
        if not isinstance(result, dict) or result.get("status") != "controller_evidence_passed":
            raise CanonicalControlError("detached Phase-3B controller did not return evidence")
        return result
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


class DetachedSource(AbstractContextManager[Path]):
    """Temporary detached Git worktree at an exact committed S."""

    def __init__(self, repository: GitRepository, source_commit: str) -> None:
        self.repository = repository
        self.source_commit = repository.resolve_commit(source_commit)
        self._root = Path(tempfile.mkdtemp(prefix="orev3-readiness-source-"))
        self.path = self._root / "source"
        self._registered = False

    def __enter__(self) -> Path:
        try:
            self.repository.run("worktree", "add", "--detach", "--no-checkout", str(self.path), self.source_commit)
            self._registered = True
            self.repository.run("-C", str(self.path), "checkout", "--detach", self.source_commit)
            return self.path
        except (GitAuthorityError, OSError):
            self._cleanup()
            raise

    def _cleanup(self) -> None:
        try:
            if self._registered:
                self.repository.run("worktree", "remove", "--force", str(self.path), check=False)
        except (GitAuthorityError, OSError):
            # Cleanup is best effort and must not mask the trust-bearing failure.
            pass
        finally:
            shutil.rmtree(self._root, ignore_errors=True)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._cleanup()


def _run_preparation_worker(source_root: Path, command: str, request_material: Mapping[str, Any], *, interpreter: Path | None = None) -> PreparationWorkerEvidence:
    """Return detached predicate evidence; this function cannot mint authority."""

    if command not in SAFE_WORKER_COMMANDS:
        raise CanonicalControlError("preparation worker command is not permitted")
    interpreter_path = (interpreter or Path(sys.executable)).resolve()
    temp_root = Path(tempfile.mkdtemp(prefix="orev3-readiness-worker-"))
    try:
        (temp_root / "home").mkdir()
        (temp_root / "tmp").mkdir()
        request = dict(request_material)
        request["command"] = command
        request["source_root"] = str(source_root.resolve())
        request_path = temp_root / "request.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        worker = source_root / "src/orev3/execution/preparation_worker.py"
        completed = _run_bounded_process(
            (str(MACOS_SANDBOX_EXEC), "-p", NETWORK_SANDBOX_PROFILE, str(interpreter_path), "-I", "-S", str(worker), str(request_path)),
            cwd=source_root,
            environment=sanitized_worker_environment(temp_root),
            timeout_seconds=WORKER_TIMEOUT_SECONDS,
            max_output_bytes=MAX_WORKER_OUTPUT_BYTES,
        )
        if completed.returncode != 0:
            raise CanonicalControlError(f"detached preparation worker rejected the environment (code {completed.returncode})")
        try:
            result = json.loads(completed.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalControlError("preparation worker result is malformed") from exc
        if not isinstance(result, dict) or result.get("command") != command or result.get("status") != "evidence_passed":
            raise CanonicalControlError("preparation worker did not produce predicate evidence")
        return PreparationWorkerEvidence(command, result)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


__all__ = [
    "ClosedDependencyRoot", "DependencyLockV1", "DetachedSource", "LockedWheel", "NETWORK_SANDBOX_PROFILE", "OfflineArtifactManifestV1", "PHASE3A_SANDBOX_TEMPLATE_IDENTITY", "PHASE3B_CONTROLLER", "PHASE3B_PROFILE_RENDERER_IDENTITY", "PHASE3B_WORKER_EVIDENCE_DOMAIN", "Phase3BWorkerEvidence", "PreparationWorkerEvidence", "RuntimeContractV1", "SAFE_PHASE3B_WORKERS", "SAFE_WORKER_COMMANDS", "construct_closed_dependency_root", "load_offline_artifact_manifest_bytes", "load_runtime_contract_bytes", "reconstruct_host_system_material", "reconstruct_offline_artifact_manifest_identity", "reconstruct_runtime_bundle_identity", "reconstruct_runtime_contract_identity", "render_phase3b_sandbox_profile", "run_phase3b_controller", "run_phase3b_worker", "sanitized_worker_environment", "validate_closed_dependency_imports", "validate_dependency_lock", "validate_host_runtime",
]
