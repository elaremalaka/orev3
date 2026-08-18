"""Fixed pytest collection/run worker with no scientific-input capability."""

from __future__ import annotations

import json
import os
import resource
import sys
from pathlib import Path

COMMANDS = frozenset({"collect", "run_exact"})


class Plugin:
    def __init__(self) -> None:
        self.collected: list[str] = []
        self.results: dict[str, str] = {}
        self.warnings = 0

    def pytest_collection_finish(self, session: object) -> None:
        self.collected = sorted(item.nodeid for item in session.items)

    def pytest_runtest_logreport(self, report: object) -> None:
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            status = "xpass" if getattr(report, "wasxfail", False) and report.outcome == "passed" else (
                "xfail" if getattr(report, "wasxfail", False) else report.outcome
            )
            self.results[report.nodeid] = status

    def pytest_warning_recorded(self, *args: object, **kwargs: object) -> None:
        self.warnings += 1


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    limits = request["resource_limits"]
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits["max_open_files"], limits["max_open_files"]))
    resource.setrlimit(resource.RLIMIT_NPROC, (limits["max_processes"], limits["max_processes"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits["max_temporary_disk_bytes"], limits["max_temporary_disk_bytes"]))
    if request.get("command") not in COMMANDS or os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1":
        return 3
    source = Path(request["source_root"]).resolve()
    dependency = Path(request["dependency_root"]).resolve()
    sys.path[:] = [str(source / "src"), str(dependency), *[entry for entry in sys.path if "lib/python" in entry and "site-packages" not in entry]]
    import pytest
    plugin = Plugin()
    selectors = request["selectors"]
    if not isinstance(selectors, list) or not selectors or any(not isinstance(item, str) or item.startswith("-") or not item.startswith("tests/") or "\\" in item or "\x00" in item or any(part in {"", ".", ".."} for part in item.split("::", 1)[0].split("/")) for item in selectors):
        return 4
    args = ["-p", "no:cacheprovider", "-p", "no:terminal", "--strict-markers", *selectors]
    if request["command"] == "collect":
        args[0:0] = ["--collect-only"]
    code = int(pytest.main(args, plugins=[plugin]))
    result = {"collected_node_ids": plugin.collected, "exit_code": code, "results": [{"node_id": key, "status": plugin.results[key]} for key in sorted(plugin.results)], "status": "evidence_passed", "warning_count": plugin.warnings}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.stderr.write("READINESS_TEST_REJECTED\n")
        raise SystemExit(10)
