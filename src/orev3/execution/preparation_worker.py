"""Fixed-capability detached worker for Phase-3A authority validation."""

from __future__ import annotations

import errno
import json
import os
import socket
import sys
from pathlib import Path

COMMANDS = frozenset({"validate_imports", "validate_runtime"})
MAX_REQUEST_BYTES = 4 * 1024 * 1024


def _network_is_structurally_denied() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.settimeout(0.2)
            candidate.connect(("127.0.0.1", 9))
    except PermissionError as exc:
        return exc.errno == errno.EPERM
    except OSError:
        return False
    return False


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    request_path = Path(sys.argv[1])
    if request_path.is_symlink() or not request_path.is_file() or request_path.stat().st_size > MAX_REQUEST_BYTES:
        return 3
    try:
        request = json.loads(request_path.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        return 4
    command = request.get("command")
    if command not in COMMANDS:
        return 5
    source_root = Path(request["source_root"]).resolve()
    source_package_root = source_root / "src"
    if Path.cwd().resolve() != source_root:
        return 6
    if os.environ.get("PYTHONPATH") or os.environ.get("PYTHONNOUSERSITE") != "1":
        return 7
    expected_environment = {
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "TZ": "UTC",
    }
    if any(os.environ.get(key) != value for key, value in expected_environment.items()):
        return 8
    if not _network_is_structurally_denied():
        return 9
    initial_paths = tuple(Path(value).resolve() for value in sys.path if value)
    if any("site-packages" in path.parts for path in initial_paths):
        return 10
    sys.path.insert(0, str(source_package_root))
    try:
        from orev3.execution.preparation import _validate_detached_preparation_environment

        result = _validate_detached_preparation_environment(request)
    except Exception as exc:  # normalized, outcome-free worker rejection
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        return 11
    result = dict(result)
    result["command"] = command
    result["network_denial_verified"] = True
    result["status"] = "evidence_passed"
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
