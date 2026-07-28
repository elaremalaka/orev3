from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import uuid
from pathlib import Path

from orev3.collection.tailer import new_cursor
from orev3.rfc008.analysis import analyze_dataset
from orev3.rfc008.burnin import (
    DEFAULT_OPERATIONAL_SAMPLE_SIZE,
    run_resolver_burn_in,
)
from orev3.collection.outcome_recovery import RpcRecoveryProvider
from orev3.rfc008.authorization import (
    CollectionAuthorizationStore,
    build_authorization_record,
)
from orev3.rfc008.collector import RFC008Collector
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.dataset import build_dataset
from orev3.rfc008.freeze import freeze_experiment
from orev3.rfc008.marker import (
    create_marker_pair,
    marker_preflight,
    verify_marker,
)
from orev3.rfc008.lifecycle import validate_collection_preflight
from orev3.rfc008.resolver import FinalizedOutcomeResolver
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.release_validation import (
    repository_release_authority,
    validate_active_release,
)
from orev3.rfc008.schemas import RFC008_CLI_VERSION
from orev3.rfc008.status import status_report
from orev3.rfc008.storage import (
    LedgerInitialization,
    RFC008Store,
    create_authorized_ledger,
)
from orev3.rfc008.writer import RFC008WriterLease


ANALYSIS_AUTHORIZATION = "RFC008_FORMAL_ANALYSIS_AUTHORIZED"
CLI_VERSION = RFC008_CLI_VERSION


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


def _authorization_record_from_release(
    args: argparse.Namespace,
):
    release = validate_active_release(
        repository_root=args.repository_root,
        config_path=args.config,
        resolver_config_path=args.resolver_config,
        burn_in_evidence_path=args.burn_in_evidence,
        release_approval_path=args.release_approval,
        approval_manifest_path=args.approval_manifest,
        marker_path=args.marker,
    )
    if not release.valid or release.parsed_active_approval is None:
        raise PermissionError(
            "RFC-008 active release validation rejected authorization issuance"
        )
    expected_marker = _expected_marker_hash(args)
    approval = release.parsed_active_approval
    if approval["validated_production_marker_sha256"] != expected_marker:
        raise PermissionError(
            "RFC-008 expected marker hash differs from active release"
        )
    config = RFC008Config.from_path(args.config)
    verify_marker(args.marker, config, expected_sha256=expected_marker)
    root = Path(args.repository_root).resolve()
    authority = repository_release_authority(
        repository_root=root,
        release_path=Path(args.release_approval).resolve(),
    )
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return build_authorization_record(
        authorization_path=args.authorization,
        ledger_path=args.ledger,
        branch=authority.branch,
        repository_head=head,
        implementation_commit=authority.implementation_commit,
        active_approval_sha256=str(release.active_approval_sha256),
        immediate_predecessor_sha256=(
            authority.predecessor_approval_sha256
        ),
        approval_chain_anchor=release.approval_hashes[-1],
        marker_sha256=expected_marker,
        marker_sidecar_sha256=str(
            approval["validated_production_marker_sidecar_sha256"]
        ),
        candidate_sha256=config.candidate_configuration_sha256,
        experiment_id=config.experiment_id,
        protocol_version=config.protocol_version,
        configuration_fingerprint=config.configuration_fingerprint,
        resolver_fingerprint=str(
            approval["resolver_configuration_sha256"]
        ),
        migration_set_sha256=str(approval["migration_set_sha256"]),
        cli_sha256=str(approval["cli_sha256"]),
        runbook_sha256=str(approval["runbook_sha256"]),
        burn_in_evidence_sha256=str(
            approval["validated_operational_burn_in_evidence_sha256"]
        ),
        burn_in_ledger_sha256=str(
            approval["validated_operational_burn_in_ledger_sha256"]
        ),
        approval_manifest_sha256=str(
            approval["frozen_approval_manifest_sha256"]
        ),
        external_rpc_burn_in_performed=bool(
            approval["verification"]["external_rpc_burn_in_performed"]
        ),
    )


def _cursor_records(
    identities: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    values: list[dict[str, object]] = []
    for identity in identities:
        parts = identity.rsplit("|", 3)
        if len(parts) != 4:
            raise ValueError("RFC-008 marker cursor identity is invalid")
        path, inode, offset, line = parts
        values.append(
            {
                "source_path": path,
                "source_inode": int(inode),
                "source_byte_offset": int(offset),
                "source_line_number": int(line),
            }
        )
    return tuple(values)


def command_issue_collection_authorization(
    args: argparse.Namespace,
) -> None:
    record = _authorization_record_from_release(args)
    CollectionAuthorizationStore.issue(args.authorization, record)
    _print(
        {
            "authorization_identifier": record.authorization_identifier,
            "authorization_digest": record.authorization_digest,
            "authorization_path": record.authorization_storage_path,
            "ledger_path": record.canonical_ledger_path,
            "state": "issued",
            "mode": record.collection_mode,
            "target": record.collection_target,
            "analysis_authorized": False,
            "freeze_authorized": False,
            "live_actions_authorized": False,
        }
    )


def command_inspect_collection_authorization(
    args: argparse.Namespace,
) -> None:
    with CollectionAuthorizationStore(
        args.authorization, read_only=True
    ) as store:
        _print(store.status().model_dump(mode="json"))


def command_initialize_ledger(args: argparse.Namespace) -> None:
    readiness = validate_collection_preflight(
        repository_root=args.repository_root,
        config_path=args.config,
        resolver_config_path=args.resolver_config,
        burn_in_evidence_path=args.burn_in_evidence,
        release_approval_path=args.release_approval,
        approval_manifest_path=args.approval_manifest,
        marker_path=args.marker,
        authorization_path=args.authorization,
        ledger_path=args.ledger,
        action="initialize",
        collector_running=False,
    )
    if not readiness.ready:
        raise PermissionError(
            "RFC-008 ledger initialization preflight rejected: "
            + ", ".join(readiness.gate_reasons)
        )
    config = RFC008Config.from_path(args.config)
    expected_hash = _expected_marker_hash(args)
    marker = verify_marker(
        args.marker, config, expected_sha256=expected_hash
    )
    with CollectionAuthorizationStore(args.authorization) as authorization:
        status = authorization.status()
        if status.lifecycle_state == "issued":
            status = authorization.consume_initialization()
        elif status.lifecycle_state != "initialization_consumed":
            raise PermissionError(
                "RFC-008 initialization authorization is already consumed"
            )
        initialization = LedgerInitialization(
            authorization=status.record,
            collection_seed_cursors=_cursor_records(
                marker.source_identities
            ),
            publication_cursors=_cursor_records(
                marker.source_identities
            ),
        )
        if Path(args.ledger).exists():
            with RFC008Store(
                args.ledger, config=config, read_only=True
            ) as ledger:
                contract = ledger.validate_collection_contract(
                    config=config,
                    authorization=status.record,
                )
        else:
            contract = create_authorized_ledger(
                args.ledger,
                config=config,
                initialization=initialization,
            )
        authorization.mark_initialized()
    _print(
        {
            "ledger_path": contract.canonical_ledger_path,
            "ledger_instance_identifier": (
                contract.ledger_instance_identifier
            ),
            "authorization_identifier": (
                contract.authorization_identifier
            ),
            "collection_state": contract.collection_state,
            "target": contract.collection_target,
            "committed_opportunity_count": (
                contract.committed_opportunity_count
            ),
        }
    )


def command_inspect_ledger(args: argparse.Namespace) -> None:
    config = RFC008Config.from_path(args.config)
    with RFC008Store(
        args.ledger, config=config, read_only=True
    ) as store:
        contract = store.validate_collection_contract(config=config)
        _print(
            {
                **contract.__dict__,
                "immutable_release": contract.immutable_release.model_dump(
                    mode="json"
                ),
                "remaining_opportunity_count": (
                    contract.remaining_opportunity_count
                ),
            }
        )


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
    action = "recovery" if args.recovery else "launch"
    readiness = validate_collection_preflight(
        repository_root=getattr(args, "repository_root", "."),
        config_path=args.config,
        resolver_config_path=getattr(
            args,
            "resolver_config",
            "config/collection/rfc008_resolver_v1.json",
        ),
        burn_in_evidence_path=getattr(
            args,
            "burn_in_evidence",
            "data/resolver/rfc008_operational_burn_in_v1.json",
        ),
        release_approval_path=getattr(
            args,
            "release_approval",
            "docs/research/rfc008/release_implementation_approval_v1.json",
        ),
        approval_manifest_path=getattr(
            args,
            "approval_manifest",
            "docs/research/rfc008/approval_manifest_v1.json",
        ),
        marker_path=args.marker,
        authorization_path=args.authorization,
        ledger_path=args.ledger,
        action=action,
        collector_running=False,
    )
    if not readiness.ready:
        raise PermissionError(
            "RFC-008 collection preflight rejected launch: "
            + ", ".join(readiness.gate_reasons)
        )
    expected_hash = _expected_marker_hash(args)
    approved_marker_hash = (
        readiness.active_release_validation.parsed_active_approval[
            "validated_production_marker_sha256"
        ]
    )
    if expected_hash != approved_marker_hash:
        raise PermissionError(
            "RFC-008 expected marker hash differs from validated release"
        )
    config = RFC008Config.from_path(args.config)
    resolver_config = ResolverConfig.from_path(args.resolver_config)
    with RFC008WriterLease(args.ledger):
        second = validate_collection_preflight(
            repository_root=args.repository_root,
            config_path=args.config,
            resolver_config_path=args.resolver_config,
            burn_in_evidence_path=args.burn_in_evidence,
            release_approval_path=args.release_approval,
            approval_manifest_path=args.approval_manifest,
            marker_path=args.marker,
            authorization_path=args.authorization,
            ledger_path=args.ledger,
            action=action,
            collector_running=False,
        )
        if not second.ready:
            raise PermissionError(
                "RFC-008 collection preflight changed before launch: "
                + ", ".join(second.gate_reasons)
            )
        with (
            CollectionAuthorizationStore(args.authorization) as authorization,
            RFC008Store(args.ledger, config=config) as store,
        ):
            contract = store.validate_collection_contract(
                config=config,
                authorization=authorization.status().record,
            )
            if contract.completed:
                if not args.recovery:
                    raise PermissionError(
                        "RFC-008 completed collection cannot be relaunched"
                    )
                with store.connection:
                    contract = store.reconcile_completed_session()
                completed = authorization.reconcile_completed_ledger(
                    contract.ledger_instance_identifier
                )
                _print(
                    {
                        "collection_state": "completed",
                        "committed_opportunity_count": (
                            contract.committed_opportunity_count
                        ),
                        "target": contract.collection_target,
                        "authorization_state": (
                            completed.lifecycle_state
                        ),
                        "collector_started": False,
                    }
                )
                return
            provider_urls = tuple(
                _provider_url(variable)
                for variable in (
                    resolver_config.provider_url_environment_variables
                )
            )
            if len(set(provider_urls)) != len(provider_urls):
                raise ValueError(
                    "Outcome-provider endpoints must be independent"
                )
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
                authorization_store=authorization,
                recovery=args.recovery,
                session_identifier=str(uuid.uuid4()),
            )
            try:
                collector.run()
            finally:
                for provider in providers:
                    provider.close()


def command_preflight_collection(args: argparse.Namespace) -> None:
    value = validate_collection_preflight(
        repository_root=args.repository_root,
        config_path=args.config,
        resolver_config_path=args.resolver_config,
        burn_in_evidence_path=args.burn_in_evidence,
        release_approval_path=args.release_approval,
        approval_manifest_path=args.approval_manifest,
        marker_path=args.marker,
        authorization_path=args.authorization,
        ledger_path=args.ledger,
        action=args.action,
        collector_running=False,
    )
    _print(value.as_dict())


def command_status(args: argparse.Namespace) -> None:
    release = validate_active_release(
        repository_root=args.repository_root,
        config_path=args.config,
        resolver_config_path=args.resolver_config,
        burn_in_evidence_path=args.burn_in_evidence,
        release_approval_path=args.release_approval,
        approval_manifest_path=args.approval_manifest,
        marker_path=args.marker,
    )
    if not release.valid:
        raise PermissionError("RFC-008 active release validation failed")
    _print(
        status_report(
            ledger_path=args.ledger,
            config_path=args.config,
            marker_path=args.marker,
            expected_marker_sha256=_expected_marker_hash(args),
            authorization_path=args.authorization,
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
    result = run_resolver_burn_in(
        ledger_path=args.ledger,
        output_path=args.output,
        experiment_config_path=args.config,
        resolver_config_path=args.resolver_config,
        mode=args.mode,
        sample_size=args.sample_size,
        control_round_id=args.control_round_id,
        authorization_token=args.authorization_token,
        release_approval_path=args.release_approval,
        repository_root=args.repository_root,
        preserve_process_ids=tuple(args.preserve_pid),
    )
    _print(result)
    if not result["passed"]:
        raise SystemExit(1)


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

    issue = sub.add_parser("issue-collection-authorization")
    issue.add_argument("--config", required=True)
    issue.add_argument("--resolver-config", required=True)
    issue.add_argument("--marker", required=True)
    _marker_hash_arguments(issue)
    issue.add_argument("--ledger", required=True)
    issue.add_argument("--authorization", required=True)
    issue.add_argument("--repository-root", required=True)
    issue.add_argument("--burn-in-evidence", required=True)
    issue.add_argument("--release-approval", required=True)
    issue.add_argument("--approval-manifest", required=True)
    issue.set_defaults(func=command_issue_collection_authorization)

    inspect_authorization = sub.add_parser(
        "inspect-collection-authorization"
    )
    inspect_authorization.add_argument("--authorization", required=True)
    inspect_authorization.set_defaults(
        func=command_inspect_collection_authorization
    )

    initialize = sub.add_parser("initialize-ledger")
    initialize.add_argument("--config", required=True)
    initialize.add_argument("--resolver-config", required=True)
    initialize.add_argument("--marker", required=True)
    _marker_hash_arguments(initialize)
    initialize.add_argument("--ledger", required=True)
    initialize.add_argument("--authorization", required=True)
    initialize.add_argument("--repository-root", required=True)
    initialize.add_argument("--burn-in-evidence", required=True)
    initialize.add_argument("--release-approval", required=True)
    initialize.add_argument("--approval-manifest", required=True)
    initialize.set_defaults(func=command_initialize_ledger)

    inspect_ledger = sub.add_parser("inspect-ledger")
    inspect_ledger.add_argument("--config", required=True)
    inspect_ledger.add_argument("--ledger", required=True)
    inspect_ledger.set_defaults(func=command_inspect_ledger)

    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--resolver-config", required=True)
    run.add_argument("--marker", required=True)
    _marker_hash_arguments(run)
    run.add_argument("--ledger", required=True)
    run.add_argument("--authorization", required=True)
    run.add_argument("--recovery", action="store_true")
    run.add_argument("--repository-root", required=True)
    run.add_argument("--burn-in-evidence", required=True)
    run.add_argument("--release-approval", required=True)
    run.add_argument("--approval-manifest", required=True)
    run.set_defaults(func=command_run)

    collection_preflight = sub.add_parser("preflight-collection")
    collection_preflight.add_argument("--config", required=True)
    collection_preflight.add_argument("--resolver-config", required=True)
    collection_preflight.add_argument("--marker", required=True)
    collection_preflight.add_argument("--ledger", required=True)
    collection_preflight.add_argument("--authorization", required=True)
    collection_preflight.add_argument(
        "--action",
        choices=("initialize", "launch", "recovery"),
        default="launch",
    )
    collection_preflight.add_argument("--repository-root", required=True)
    collection_preflight.add_argument("--burn-in-evidence", required=True)
    collection_preflight.add_argument("--release-approval", required=True)
    collection_preflight.add_argument("--approval-manifest", required=True)
    collection_preflight.set_defaults(func=command_preflight_collection)

    status = sub.add_parser("status")
    status.add_argument("--config", required=True)
    status.add_argument("--marker", required=True)
    _marker_hash_arguments(status)
    status.add_argument("--ledger", required=True)
    status.add_argument("--authorization", required=True)
    status.add_argument("--repository-root", default=".")
    status.add_argument(
        "--resolver-config",
        default="config/collection/rfc008_resolver_v1.json",
    )
    status.add_argument(
        "--burn-in-evidence",
        default="data/resolver/rfc008_operational_burn_in_v1.json",
    )
    status.add_argument(
        "--release-approval",
        default=(
            "docs/research/rfc008/"
            "release_implementation_approval_v1.json"
        ),
    )
    status.add_argument(
        "--approval-manifest",
        default="docs/research/rfc008/approval_manifest_v1.json",
    )
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

    burn_in = sub.add_parser(
        "resolver-burn-in",
        description=(
            "Run an isolated non-production resolver burn-in. Operational mode "
            "requires at least five distinct real finalized rounds and does not "
            "authorize marker creation or collection."
        ),
    )
    burn_in.add_argument("--config", required=True)
    burn_in.add_argument("--resolver-config", required=True)
    burn_in.add_argument("--ledger", required=True)
    burn_in.add_argument("--output", required=True)
    burn_in.add_argument("--mode", choices=("fixture", "operational"), required=True)
    burn_in.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_OPERATIONAL_SAMPLE_SIZE,
        help="Operational real-round sample size (minimum and default: 5)",
    )
    burn_in.add_argument("--control-round-id", type=int)
    burn_in.add_argument("--authorization-token")
    burn_in.add_argument(
        "--release-approval",
        default="docs/research/rfc008/release_implementation_approval_v1.json",
    )
    burn_in.add_argument("--repository-root", default=".")
    burn_in.add_argument(
        "--preserve-pid",
        action="append",
        type=int,
        default=[],
        help=(
            "Process PID whose command hash must remain unchanged; repeat for "
            "each observer/collector process (required in operational mode)"
        ),
    )
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
