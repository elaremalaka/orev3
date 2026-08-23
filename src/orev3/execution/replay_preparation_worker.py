"""Fixed outcome-blind Replay evidence worker."""

from __future__ import annotations

import json
import hashlib
import os
import resource
import sys
from pathlib import Path

COMMANDS = frozenset({"reconstruct_replay"})


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    limits = request["resource_limits"]
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits["max_open_files"], limits["max_open_files"]))
    resource.setrlimit(resource.RLIMIT_NPROC, (limits["max_processes"], limits["max_processes"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits["max_temporary_disk_bytes"], limits["max_temporary_disk_bytes"]))
    if request.get("command") not in COMMANDS or "raw_snapshot" in request or "outcome" in request:
        return 3
    source = Path(request["source_root"]).resolve(); dependency = Path(request["dependency_root"]).resolve()
    sys.path[:] = [str(source / "src"), str(dependency), *[entry for entry in sys.path if "lib/python" in entry and "site-packages" not in entry]]
    from orev3.execution.canonical import canonical_bytes, parse_canonical_bytes
    from orev3.execution.replay_preparation import build_replay_evidence, load_verified_projection
    projection = Path(request["projection_path"])
    schema = parse_canonical_bytes(Path(request["projection_schema_path"]).read_bytes())
    records = load_verified_projection(
        projection, expected_sha256=request["expected_projection_sha256"],
        expected_size=request["expected_projection_size"], projection_schema=schema,
        max_bytes=request["max_projection_bytes"], max_units=request["max_units"],
    )
    replay, population = build_replay_evidence(
        records, dataset_identity=request["dataset_identity"],
        projection_identity=request["projection_identity"],
        selector_identifier=request["selector_identifier"],
        selector_component_identity=request["selector_component_identity"],
        replay_preparer_component_identity=request["replay_preparer_component_identity"],
        configuration_identity=request["configuration_identity"],
        candidate_order=request["candidate_order"],
        allowed_exclusion_reasons=request["allowed_exclusion_reasons"],
        max_units=request["max_units"],
        decision_selection_identity=request.get("decision_selection_identity"),
        schema_version=request.get("schema_version", 1),
    )
    target = Path(request["private_output"])
    payload = canonical_bytes({"population": population, "replay": replay})
    with target.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    sys.stdout.write(json.dumps({"byte_count": len(payload), "population_identity": population["population_accounting_evidence_identity"], "replay_identity": replay["replay_evidence_identity"], "sha256": hashlib.sha256(payload).hexdigest(), "status": "evidence_passed"}, separators=(",", ":"), sort_keys=True))
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
                    "OUTCOME_ISOLATION_VIOLATION",
                    "POPULATION_MISMATCH",
                    "PROJECTION_INVALID",
                    "REPLAY_IDENTITY_MISMATCH",
                    "RESOURCE_LIMIT_EXCEEDED",
                )
                if candidate in str(exc)
            ),
            "REPLAY_IDENTITY_MISMATCH",
        )
        sys.stdout.write(json.dumps({"failure_code": code, "status": "evidence_rejected"}, separators=(",", ":"), sort_keys=True))
        sys.stderr.write("REPLAY_PREPARATION_REJECTED\n")
        raise SystemExit(10)
