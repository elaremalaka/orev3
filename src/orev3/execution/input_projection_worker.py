"""Fixed raw-input verifier/projector; the only Phase-3B worker seeing raw records."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
from pathlib import Path

COMMANDS = frozenset({"project_canonical_jsonl"})


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    limits = request["resource_limits"]
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits["max_open_files"], limits["max_open_files"]))
    resource.setrlimit(resource.RLIMIT_NPROC, (limits["max_processes"], limits["max_processes"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits["max_temporary_disk_bytes"], limits["max_temporary_disk_bytes"]))
    if request.get("command") not in COMMANDS:
        return 3
    source = Path(request["source_root"]).resolve()
    dependency = Path(request["dependency_root"]).resolve()
    sys.path[:] = [str(source / "src"), str(dependency), *[entry for entry in sys.path if "lib/python" in entry and "site-packages" not in entry]]
    from orev3.execution.canonical import parse_canonical_bytes
    from orev3.execution.projection import project_jsonl
    raw_schema = parse_canonical_bytes(Path(request["raw_schema_path"]).read_bytes())
    projection_schema = parse_canonical_bytes(Path(request["projection_schema_path"]).read_bytes())
    output, count, dataset_content_identity = project_jsonl(
        Path(request["raw_snapshot"]),
        raw_schema=raw_schema,
        projection_schema=projection_schema,
        expected_raw_sha256=request["expected_raw_sha256"],
        expected_raw_size=request["expected_raw_size"],
        max_raw_bytes=request["max_raw_bytes"],
        max_projection_bytes=request["max_projection_bytes"],
        max_records=request["max_records"],
    )
    target = Path(request["private_output"])
    with target.open("xb") as stream:
        stream.write(output); stream.flush(); os.fsync(stream.fileno())
    sys.stdout.write(json.dumps({"byte_count": len(output), "dataset_content_identity": dataset_content_identity, "record_count": count, "sha256": hashlib.sha256(output).hexdigest(), "status": "evidence_passed"}, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        code = next(
            (
                candidate
                for candidate in (
                    "INPUT_MUTATED",
                    "INPUT_MISMATCH",
                    "INPUT_SCHEMA_MISMATCH",
                    "PROJECTION_INVALID",
                    "RESOURCE_LIMIT_EXCEEDED",
                )
                if candidate in str(exc)
            ),
            "PROJECTION_INVALID",
        )
        sys.stdout.write(json.dumps({"failure_code": code, "status": "evidence_rejected"}, separators=(",", ":"), sort_keys=True))
        sys.stderr.write("INPUT_PROJECTOR_REJECTED\n")
        raise SystemExit(10)
