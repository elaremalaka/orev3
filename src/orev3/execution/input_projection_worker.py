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
    if request.get("decoder_identifier") == "rq003-experiment-005-source-decoder-v1":
        # Broad package initializers expose unrelated outcome-aware APIs.
        # INPUT_PROJECTOR resolves only explicitly copied submodules through
        # these finite namespace packages.
        import types
        for package_name, relative in (
            ("orev3.datasets", "orev3/datasets"),
            ("orev3.experiments", "orev3/experiments"),
            ("orev3.features", "orev3/features"),
            ("orev3.strategy_lab", "orev3/strategy_lab"),
        ):
            package = types.ModuleType(package_name)
            package.__package__ = package_name
            package.__path__ = [str(source / "src" / relative)]
            sys.modules[package_name] = package
        from orev3.experiments.rq003_experiment5_source_processing import (
            SourceMember,
            authenticate_configuration,
            process_source_collection,
            reconstruct_source_authority,
        )
        from orev3.execution.canonical import parse_json
        projection_schema = parse_json(
            Path(request["projection_schema_path"]).read_bytes()
        )
        if not isinstance(projection_schema, dict):
            raise ValueError("PROJECTION_INVALID")
        configuration_bytes = Path(request["configuration_path"]).read_bytes()
        configuration, configuration_identity, schema_identity = (
            authenticate_configuration(
                configuration_bytes,
                expected_byte_count=request["expected_configuration_byte_count"],
                expected_sha256=request["expected_configuration_sha256"],
                configuration_path=request["decoder"]["configuration_path"],
                configuration_git_blob_identity=request["decoder"]["configuration_git_blob_identity"],
            )
        )
        if hashlib.sha256(
            Path(request["projection_schema_path"]).read_bytes()
        ).hexdigest() != configuration["projection_schema_sha256"]:
            raise ValueError("PROJECTION_INVALID")
        if request["decoder"]["configuration_identity"] != configuration_identity:
            raise ValueError("PROJECTION_INVALID")
        raw_schema = parse_json(Path(request["raw_schema_path"]).read_bytes())
        if not isinstance(raw_schema, dict):
            raise ValueError("PROJECTION_INVALID")
        authority = reconstruct_source_authority(
            declaration=request["external_input_declaration"],
            snapshot=request["immutable_input_snapshot"],
            decoder=request["decoder"],
            parser_component=request["parser_component"],
            projector_component=request["projector_component"],
            raw_schema=raw_schema,
            projection_schema=projection_schema,
        )
        if authority.projection_schema_identity != schema_identity:
            raise ValueError("PROJECTION_INVALID")
        members = tuple(
            SourceMember(
                logical_identifier=item["logical_identifier"],
                member_path=item["member_path"],
                member_order=item["member_order"],
                persisted_bytes=Path(item["capability_path"]).read_bytes(),
                expected_byte_count=item["byte_count"],
                expected_sha256=item["sha256"],
                declared_member_identity=item["member_identity"],
            )
            for item in request["members"]
        )
        result = process_source_collection(
            members,
            authority=authority,
            projection_schema=projection_schema,
            configuration=configuration,
        )
        target = Path(request["private_output"])
        with target.open("xb") as stream:
            stream.write(result.projection_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        sys.stdout.write(json.dumps({
            "byte_count": len(result.projection_bytes),
            "dataset_content_identity": result.dataset_content_identity,
            "logical_projection_content_identity": (
                result.logical_projection_content_identity
            ),
            "projection_identity": result.projection_identity,
            "projection_record_identities": list(
                result.projection_record_identities
            ),
            "record_count": len(result.records),
            "sha256": result.projection_sha256,
            "status": "evidence_passed",
        }, separators=(",", ":"), sort_keys=True))
        return 0
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
