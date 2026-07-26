from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

from orev3.collection.tailer import new_cursor
from orev3.rfc008.analysis import analyze_dataset
from orev3.rfc008.burnin import run_resolver_burn_in
from orev3.collection.outcome_recovery import RpcRecoveryProvider
from orev3.rfc008.collector import (
    COLLECTION_AUTHORIZATION,
    RFC008Collector,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.dataset import build_dataset
from orev3.rfc008.freeze import freeze_experiment
from orev3.rfc008.marker import (
    MARKER_AUTHORIZATION,
    create_marker_pair,
    marker_preflight,
)
from orev3.rfc008.resolver import FinalizedOutcomeResolver
from orev3.rfc008.resolver_config import ResolverConfig
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
    value = marker_preflight(
        config_path=args.config,
        resolver_config_path=args.resolver_config,
        burn_in_evidence_path=args.burn_in_evidence,
        release_approval_path=args.release_approval,
        marker_path=args.marker,
        ledger_path=args.ledger,
        approval_manifest_path=args.approval_manifest,
        repository_root=args.repository_root,
        expected_branch=args.expected_branch,
    )
    _print(value)


def command_create_marker(args: argparse.Namespace) -> None:
    marker, digest = create_marker_pair(
        config_path=args.config,
        resolver_config_path=args.resolver_config,
        burn_in_evidence_path=args.burn_in_evidence,
        release_approval_path=args.release_approval,
        marker_path=args.marker,
        ledger_path=args.ledger,
        approval_manifest_path=args.approval_manifest,
        repository_root=args.repository_root,
        expected_branch=args.expected_branch,
        authorization_token=args.authorization_token,
    )
    hash_path = Path(str(args.marker) + ".sha256")
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
    resolver_config = ResolverConfig.from_path(args.resolver_config)
    provider_urls = tuple(
        _provider_url(variable)
        for variable in resolver_config.provider_url_environment_variables
    )
    if len(set(provider_urls)) != len(provider_urls):
        raise ValueError("Outcome-provider endpoints must be independent")
    expected_hash = _expected_marker_hash(args)
    with RFC008WriterLease(args.ledger):
        with RFC008Store(
            args.ledger,
            config=config,
            create=args.create_new_ledger,
        ) as store:
            providers = tuple(
                RpcRecoveryProvider(provider_id, url)
                for provider_id, url in zip(
                    resolver_config.provider_ids, provider_urls
                )
            )
            resolver = FinalizedOutcomeResolver(
                store=store,
                experiment_config=config,
                resolver_config=resolver_config,
                providers=providers,
            )
            resolver.validate_provider_networks()
            collector = RFC008Collector(
                store=store,
                config=config,
                marker_path=args.marker,
                expected_marker_sha256=expected_hash,
                resolver=resolver,
            )
            try:
                collector.run()
            finally:
                for provider in providers:
                    provider.close()


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
            freeze_path=args.freeze,
            expected_freeze_sha256=_expected_freeze_hash(args),
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
            expected_manifest_sha256=_expected_dataset_manifest_hash(args),
            output_path=args.output,
        )
    )


def command_burn_in(args: argparse.Namespace) -> None:
    _print(
        run_resolver_burn_in(
            ledger_path=args.ledger,
            output_path=args.output,
            experiment_config_path=args.config,
            resolver_config_path=args.resolver_config,
            mode=args.mode,
            control_round_id=args.control_round_id,
            authorization_token=args.authorization_token,
        )
    )


def command_final_freeze(args: argparse.Namespace) -> None:
    _print(
        freeze_experiment(
            ledger_path=args.ledger,
            config_path=args.config,
            marker_path=args.marker,
            expected_marker_sha256=_expected_marker_hash(args),
            output_path=args.output,
            collection_stop_reason=args.stop_reason,
            authorization_token=args.authorization_token,
        )
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="RFC-008 paper evaluation")
    sub = value.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight-marker")
    preflight.add_argument("--config", required=True)
    preflight.add_argument("--resolver-config", required=True)
    preflight.add_argument("--burn-in-evidence", required=True)
    preflight.add_argument("--release-approval", required=True)
    preflight.add_argument("--marker", required=True)
    preflight.add_argument("--ledger", required=True)
    preflight.add_argument("--approval-manifest", required=True)
    preflight.add_argument("--repository-root", required=True)
    preflight.add_argument("--expected-branch", required=True)
    preflight.set_defaults(func=command_preflight_marker)

    marker = sub.add_parser("create-marker")
    marker.add_argument("--config", required=True)
    marker.add_argument("--resolver-config", required=True)
    marker.add_argument("--burn-in-evidence", required=True)
    marker.add_argument("--release-approval", required=True)
    marker.add_argument("--marker", required=True)
    marker.add_argument("--ledger", required=True)
    marker.add_argument("--approval-manifest", required=True)
    marker.add_argument("--repository-root", required=True)
    marker.add_argument("--expected-branch", required=True)
    marker.add_argument("--authorization-token", required=True)
    marker.set_defaults(func=command_create_marker)

    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--resolver-config", required=True)
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
    dataset.add_argument("--freeze", required=True)
    _freeze_hash_arguments(dataset)
    dataset.add_argument("--output", required=True)
    dataset.set_defaults(func=command_build_dataset)

    analysis = sub.add_parser("analyze")
    analysis.add_argument("--config", required=True)
    analysis.add_argument("--dataset", required=True)
    analysis.add_argument("--output", required=True)
    _dataset_manifest_hash_arguments(analysis)
    analysis.add_argument("--authorization-token", required=True)
    analysis.set_defaults(func=command_analyze)

    burn_in = sub.add_parser("resolver-burn-in")
    burn_in.add_argument("--config", required=True)
    burn_in.add_argument("--resolver-config", required=True)
    burn_in.add_argument("--ledger", required=True)
    burn_in.add_argument("--output", required=True)
    burn_in.add_argument("--mode", choices=("fixture", "operational"), required=True)
    burn_in.add_argument("--control-round-id", type=int)
    burn_in.add_argument("--authorization-token")
    burn_in.set_defaults(func=command_burn_in)

    freeze = sub.add_parser("final-freeze")
    freeze.add_argument("--config", required=True)
    freeze.add_argument("--marker", required=True)
    _marker_hash_arguments(freeze)
    freeze.add_argument("--ledger", required=True)
    freeze.add_argument("--output", required=True)
    freeze.add_argument("--stop-reason", required=True)
    freeze.add_argument("--authorization-token", required=True)
    freeze.set_defaults(func=command_final_freeze)
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


def _freeze_hash_arguments(value: argparse.ArgumentParser) -> None:
    group = value.add_mutually_exclusive_group(required=True)
    group.add_argument("--expected-freeze-sha256")
    group.add_argument("--expected-freeze-sha256-file")


def _expected_freeze_hash(args: argparse.Namespace) -> str:
    direct = getattr(args, "expected_freeze_sha256", None)
    if direct:
        return str(direct)
    value = Path(args.expected_freeze_sha256_file).read_text().split()[0]
    if len(value) != 64:
        raise ValueError("Invalid final-freeze SHA-256 sidecar")
    return value


def _provider_url(variable: str) -> str:
    value = os.environ.get(variable)
    if not value:
        raise ValueError(f"Missing outcome-provider environment variable: {variable}")
    return value


def _dataset_manifest_hash_arguments(value: argparse.ArgumentParser) -> None:
    group = value.add_mutually_exclusive_group(required=True)
    group.add_argument("--expected-dataset-manifest-sha256")
    group.add_argument("--expected-dataset-manifest-sha256-file")


def _expected_dataset_manifest_hash(args: argparse.Namespace) -> str:
    direct = getattr(args, "expected_dataset_manifest_sha256", None)
    if direct:
        return str(direct)
    value = Path(
        args.expected_dataset_manifest_sha256_file
    ).read_text().split()[0]
    if len(value) != 64:
        raise ValueError("Invalid dataset manifest SHA-256 sidecar")
    return value


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
