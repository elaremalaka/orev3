from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

from orev3.collection.tailer import new_cursor
from orev3.rfc008.analysis import analyze_dataset
from orev3.rfc008.collector import (
    COLLECTION_AUTHORIZATION,
    RFC008Collector,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.dataset import build_dataset
from orev3.rfc008.marker import (
    MARKER_AUTHORIZATION,
    create_marker,
    marker_preflight,
    sha256_file,
)
from orev3.rfc008.status import status_report
from orev3.rfc008.storage import RFC008Store
from orev3.rfc008.writer import RFC008WriterLease


ANALYSIS_AUTHORIZATION = "RFC008_FORMAL_ANALYSIS_AUTHORIZED"


def _print(value: object) -> None:
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def _source_identities(config: RFC008Config) -> tuple[str, ...]:
    identities = []
    for name in sorted(glob.glob(config.source_glob)):
        path = Path(name)
        cursor = new_cursor(path, start_at_end=True)
        identities.append(
            "|".join(
                (
                    str(path.resolve()),
                    str(cursor.source_inode),
                    str(cursor.byte_offset),
                    str(cursor.line_number),
                )
            )
        )
    if not identities:
        raise ValueError("No observer source files match the RFC-008 configuration")
    return tuple(identities)


def command_preflight_marker(args: argparse.Namespace) -> None:
    config = RFC008Config.from_path(args.config)
    value = marker_preflight(
        config_path=args.config,
        marker_path=args.marker,
        approval_manifest_path=args.approval_manifest,
        repository_root=args.repository_root,
        expected_branch=args.expected_branch,
    )
    value["source_identities"] = list(_source_identities(config))
    value["observer_compatible"] = True
    _print(value)


def command_create_marker(args: argparse.Namespace) -> None:
    config = RFC008Config.from_path(args.config)
    marker = create_marker(
        config_path=args.config,
        marker_path=args.marker,
        approval_manifest_path=args.approval_manifest,
        repository_root=args.repository_root,
        expected_branch=args.expected_branch,
        latest_preholdout_round_id=args.latest_preholdout_round_id,
        source_identities=_source_identities(config),
        authorization_token=args.authorization_token,
    )
    digest = sha256_file(args.marker)
    hash_path = Path(str(args.marker) + ".sha256")
    with hash_path.open("x", encoding="utf-8") as handle:
        handle.write(f"{digest}  {Path(args.marker).name}\n")
    _print(
        {
            "marker": marker.model_dump(mode="json"),
            "marker_sha256": digest,
            "marker_sha256_path": str(hash_path),
            "collection_started": False,
        }
    )


def command_run(args: argparse.Namespace) -> None:
    if args.authorization_token != COLLECTION_AUTHORIZATION:
        raise PermissionError("Explicit RFC-008 collection authorization required")
    config = RFC008Config.from_path(args.config)
    expected_hash = _expected_marker_hash(args)
    with RFC008WriterLease(args.ledger):
        with RFC008Store(
            args.ledger,
            config=config,
            create=args.create_new_ledger,
        ) as store:
            collector = RFC008Collector(
                store=store,
                config=config,
                marker_path=args.marker,
                expected_marker_sha256=expected_hash,
            )
            collector.run()


def command_status(args: argparse.Namespace) -> None:
    _print(
        status_report(
            ledger_path=args.ledger,
            config_path=args.config,
            marker_path=args.marker,
            expected_marker_sha256=_expected_marker_hash(args),
        )
    )


def command_build_dataset(args: argparse.Namespace) -> None:
    _print(
        build_dataset(
            ledger_path=args.ledger,
            config_path=args.config,
            marker_path=args.marker,
            expected_marker_sha256=_expected_marker_hash(args),
            output_dir=args.output,
        )
    )


def command_analyze(args: argparse.Namespace) -> None:
    if args.authorization_token != ANALYSIS_AUTHORIZATION:
        raise PermissionError("Separate formal-analysis authorization required")
    _print(
        analyze_dataset(
            dataset_dir=args.dataset,
            config_path=args.config,
            output_path=args.output,
        )
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="RFC-008 paper evaluation")
    sub = value.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight-marker")
    preflight.add_argument("--config", required=True)
    preflight.add_argument("--marker", required=True)
    preflight.add_argument("--approval-manifest", required=True)
    preflight.add_argument("--repository-root", required=True)
    preflight.add_argument("--expected-branch", required=True)
    preflight.set_defaults(func=command_preflight_marker)

    marker = sub.add_parser("create-marker")
    marker.add_argument("--config", required=True)
    marker.add_argument("--marker", required=True)
    marker.add_argument("--approval-manifest", required=True)
    marker.add_argument("--repository-root", required=True)
    marker.add_argument("--expected-branch", required=True)
    marker.add_argument("--latest-preholdout-round-id", type=int, required=True)
    marker.add_argument("--authorization-token", required=True)
    marker.set_defaults(func=command_create_marker)

    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--marker", required=True)
    _marker_hash_arguments(run)
    run.add_argument("--ledger", required=True)
    run.add_argument("--create-new-ledger", action="store_true")
    run.add_argument("--authorization-token", required=True)
    run.set_defaults(func=command_run)

    status = sub.add_parser("status")
    status.add_argument("--config", required=True)
    status.add_argument("--marker", required=True)
    _marker_hash_arguments(status)
    status.add_argument("--ledger", required=True)
    status.set_defaults(func=command_status)

    dataset = sub.add_parser("build-dataset")
    dataset.add_argument("--config", required=True)
    dataset.add_argument("--marker", required=True)
    _marker_hash_arguments(dataset)
    dataset.add_argument("--ledger", required=True)
    dataset.add_argument("--output", required=True)
    dataset.set_defaults(func=command_build_dataset)

    analysis = sub.add_parser("analyze")
    analysis.add_argument("--config", required=True)
    analysis.add_argument("--dataset", required=True)
    analysis.add_argument("--output", required=True)
    analysis.add_argument("--authorization-token", required=True)
    analysis.set_defaults(func=command_analyze)
    return value


def _marker_hash_arguments(value: argparse.ArgumentParser) -> None:
    group = value.add_mutually_exclusive_group(required=True)
    group.add_argument("--expected-marker-sha256")
    group.add_argument("--expected-marker-sha256-file")


def _expected_marker_hash(args: argparse.Namespace) -> str:
    direct = getattr(args, "expected_marker_sha256", None)
    if direct:
        return str(direct)
    path = Path(args.expected_marker_sha256_file)
    value = path.read_text(encoding="utf-8").split()[0]
    if len(value) != 64:
        raise ValueError("Invalid marker SHA-256 sidecar")
    return value


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
