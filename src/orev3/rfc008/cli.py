from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
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
from orev3.rfc008.supervision import (
    INTERNAL_CHILD_COMMAND,
    STARTUP_POLL_SECONDS,
    STARTUP_TIMEOUT_SECONDS,
    SupervisionError,
    approved_python_command,
    atomic_write_metadata,
    command_identity,
    consume_child_authority,
    controlled_environment,
    create_child_authority,
    install_sanitized_streams,
    launch_mutex,
    process_matches_metadata,
    process_snapshot,
    read_metadata,
    redact_exception,
    safe_open_log,
    spawn_detached,
    supervision_paths,
    terminate_unestablished_child,
    update_metadata,
    utc_now,
    validate_import_identity,
    wait_for_process_identity,
    writer_lease_status,
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


def _command_run(args: argparse.Namespace) -> None:
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


def _supervision_exit_state(args: argparse.Namespace) -> str:
    config = RFC008Config.from_path(args.config)
    with (
        CollectionAuthorizationStore(
            args.authorization, read_only=True
        ) as authorization,
        RFC008Store(
            args.ledger, config=config, read_only=True
        ) as store,
    ):
        authorization_state = authorization.status().lifecycle_state
        contract = store.validate_collection_contract(config=config)
    if contract.completed and authorization_state == "completed":
        return "completed"
    return "interrupted"


def command_run(args: argparse.Namespace) -> None:
    metadata_path = getattr(args, "supervision_metadata", None)
    launch_identifier = getattr(
        args, "supervision_launch_identifier", None
    )
    authority_fd = getattr(args, "supervision_authority_fd", None)
    log_fd = getattr(args, "supervision_log_fd", None)
    if (
        metadata_path is None
        or launch_identifier is None
        or authority_fd is None
        or log_fd is None
    ):
        raise SupervisionError(
            "RFC-008 collection requires supervised single-launch authority"
        )
    metadata = read_metadata(metadata_path)
    if (
        metadata is None
        or metadata["launch_identifier"] != launch_identifier
        or Path(metadata["ledger_path"]).resolve()
        != Path(args.ledger).resolve()
    ):
        raise SupervisionError(
            "RFC-008 supervised child metadata binding mismatch"
        )
    known_secrets = tuple(
        os.environ.get(name, "")
        for name in (
            "ORE_RECOVERY_PRIMARY_RPC_URL",
            "ORE_RECOVERY_SECONDARY_RPC_URL",
        )
    )
    install_sanitized_streams(log_fd, known_secrets=known_secrets)
    os.close(log_fd)
    consume_child_authority(
        authority_fd,
        expected_sha256=metadata["launch_authority_sha256"],
    )
    validate_import_identity(
        args.repository_root,
        expected_cli_sha256=metadata["cli_sha256"],
    )
    own_process = process_snapshot(os.getpid())
    if (
        not own_process["alive"]
        or f"-m orev3.rfc008.cli {INTERNAL_CHILD_COMMAND}"
        not in str(own_process["command"])
    ):
        raise SupervisionError("RFC-008 internal child process identity mismatch")
    update_metadata(
        metadata_path,
        collector_pid=os.getpid(),
        collector_start_timestamp=utc_now(),
        collector_process_start_identity=own_process["start_identity"],
        launch_authority_consumed_at=utc_now(),
    )
    try:
        _command_run(args)
    except BaseException as exc:
        try:
            state = _supervision_exit_state(args)
        except Exception:
            state = "failed"
        update_metadata(
            metadata_path,
            supervision_state=state,
            exit_code=1,
            failure_reason=redact_exception(exc),
        )
        raise
    else:
        state = _supervision_exit_state(args)
        update_metadata(
            metadata_path,
            supervision_state=state,
            exit_code=0,
            failure_reason=None,
        )


def _git_branch_and_head(repository_root: str | Path) -> tuple[str, str]:
    root = Path(repository_root).resolve()
    branch = subprocess.run(
        ("git", "branch", "--show-current"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=all"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise PermissionError(
            "RFC-008 supervised launch requires a clean Git worktree"
        )
    return branch, head


def _supervised_child_command(
    args: argparse.Namespace,
    *,
    metadata_path: Path,
    launch_identifier: str,
    authority_descriptor: int,
    log_descriptor: int,
) -> list[str]:
    command = [
        approved_python_command(args.repository_root),
        "-m",
        "orev3.rfc008.cli",
        INTERNAL_CHILD_COMMAND,
        "--config",
        str(args.config),
        "--resolver-config",
        str(args.resolver_config),
        "--marker",
        str(args.marker),
        "--ledger",
        str(args.ledger),
        "--authorization",
        str(args.authorization),
        "--repository-root",
        str(args.repository_root),
        "--burn-in-evidence",
        str(args.burn_in_evidence),
        "--release-approval",
        str(args.release_approval),
        "--approval-manifest",
        str(args.approval_manifest),
        "--supervision-metadata",
        str(metadata_path),
        "--supervision-launch-identifier",
        launch_identifier,
        "--supervision-authority-fd",
        str(authority_descriptor),
        "--supervision-log-fd",
        str(log_descriptor),
    ]
    if args.expected_marker_sha256:
        command.extend(
            (
                "--expected-marker-sha256",
                str(args.expected_marker_sha256),
            )
        )
    else:
        command.extend(
            (
                "--expected-marker-sha256-file",
                str(args.expected_marker_sha256_file),
            )
        )
    if args.recovery:
        command.append("--recovery")
    return command


def _startup_authoritative_state(
    args: argparse.Namespace,
    *,
    process_id: int | None = None,
) -> dict[str, object]:
    config = RFC008Config.from_path(args.config)
    with (
        CollectionAuthorizationStore(
            args.authorization, read_only=True
        ) as authorization_store,
        RFC008Store(
            args.ledger, config=config, read_only=True
        ) as store,
    ):
        authorization = authorization_store.status()
        contract = store.validate_collection_contract(
            config=config,
            authorization=authorization.record,
        )
        open_runs = store.connection.execute(
            """
            SELECT run_id,process_id,started_at
            FROM collector_runs
            WHERE ended_at IS NULL
            ORDER BY started_at
            """
        ).fetchall()
        matching_run = next(
            (
                row
                for row in open_runs
                if process_id is not None
                and int(row["process_id"]) == process_id
            ),
            None,
        )
        canonical_count = store.count("decision_snapshots")
        arm_count = store.count("arm_decisions")
    return {
        "authorization": authorization,
        "contract": contract,
        "open_runs": open_runs,
        "matching_run": matching_run,
        "canonical_count": canonical_count,
        "arm_count": arm_count,
    }


def command_start(args: argparse.Namespace) -> None:
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
        action="recovery" if args.recovery else "launch",
        collector_running=False,
    )
    if not readiness.ready:
        raise PermissionError(
            "RFC-008 supervised preflight rejected launch: "
            + ", ".join(readiness.gate_reasons)
        )
    branch, head = _git_branch_and_head(args.repository_root)
    approval = readiness.active_release_validation.parsed_active_approval
    cli_sha256 = str(approval["cli_sha256"])
    validate_import_identity(
        args.repository_root,
        expected_cli_sha256=cli_sha256,
    )
    paths = supervision_paths(args.ledger)
    with launch_mutex(args.ledger):
        state = _startup_authoritative_state(args)
        authorization = state["authorization"]
        contract = state["contract"]
        if contract.completed and not args.recovery:
            raise PermissionError(
                "RFC-008 completed collection cannot be relaunched"
            )
        if (
            not args.recovery
            and (
                state["open_runs"]
                or contract.active_session_identity is not None
            )
        ):
            raise PermissionError(
                "RFC-008 authoritative collector session already exists"
            )
        if (
            not args.recovery
            and authorization.consuming_session_identity is not None
        ):
            raise PermissionError(
                "RFC-008 authorization is already bound to a session"
            )
        expected_authorization_states = (
            {"active", "completed"}
            if args.recovery and contract.completed
            else ({"active"} if args.recovery else {"initialized"})
        )
        if authorization.lifecycle_state not in expected_authorization_states:
            raise PermissionError(
                "RFC-008 authorization state rejects supervised launch"
            )
        lease = writer_lease_status(args.ledger)
        if lease["active"]:
            raise PermissionError("RFC-008 writer lease is active")
        prior = read_metadata(paths["metadata"])
        stale_recovery = None
        if prior is not None:
            if process_matches_metadata(prior):
                raise PermissionError(
                    "An RFC-008 supervised collector is already active"
                )
            stale_recovery = {
                "launch_identifier": prior["launch_identifier"],
                "prior_state": prior["supervision_state"],
                "recovered_at": utc_now(),
            }
        launch_identifier = str(uuid.uuid4())
        authority_descriptor, authority_sha256 = create_child_authority()
        log_descriptor, log_stat = safe_open_log(paths["log"])
        child_command = _supervised_child_command(
            args,
            metadata_path=paths["metadata"],
            launch_identifier=launch_identifier,
            authority_descriptor=authority_descriptor,
            log_descriptor=log_descriptor,
        )
        metadata = {
            "schema_version": 2,
            "launch_identifier": launch_identifier,
            "launch_authority_sha256": authority_sha256,
            "launch_authority_consumed_at": None,
            "launcher_pid": os.getpid(),
            "collector_pid": None,
            "collector_start_timestamp": None,
            "collector_process_start_identity": None,
            "command_identity": command_identity(child_command),
            "log_path": str(paths["log"]),
            "log_device": int(log_stat.st_dev),
            "log_inode": int(log_stat.st_ino),
            "metadata_path": str(paths["metadata"]),
            "branch": branch,
            "head": head,
            "cli_sha256": cli_sha256,
            "authorization_identifier": (
                authorization.record.authorization_identifier
            ),
            "authorization_digest": authorization.record.authorization_digest,
            "ledger_instance_identifier": (
                contract.ledger_instance_identifier
            ),
            "ledger_path": str(Path(args.ledger).resolve()),
            "session_identity": None,
            "target_count": contract.collection_target,
            "supervision_state": "starting",
            "last_observed_status_timestamp": utc_now(),
            "exit_code": None,
            "failure_reason": None,
            "stale_recovery": stale_recovery,
        }
        child = None
        child_identity = None
        established = False
        try:
            atomic_write_metadata(paths["metadata"], metadata)
            child = spawn_detached(
                child_command,
                cwd=args.repository_root,
                log_descriptor=log_descriptor,
                authority_descriptor=authority_descriptor,
                environment=controlled_environment(args.repository_root),
            )
            os.close(log_descriptor)
            log_descriptor = -1
            os.close(authority_descriptor)
            authority_descriptor = -1
            try:
                child_snapshot = wait_for_process_identity(child.pid)
            except SupervisionError:
                if args.recovery and contract.completed:
                    recovered = _startup_authoritative_state(
                        args, process_id=child.pid
                    )
                    recovered_metadata = read_metadata(paths["metadata"])
                    if (
                        recovered["contract"].completed
                        and recovered["contract"].active_session_identity is None
                        and recovered["authorization"].lifecycle_state
                        == "completed"
                        and not recovered["open_runs"]
                        and recovered_metadata is not None
                        and recovered_metadata["supervision_state"]
                        == "completed"
                        and child.poll() is not None
                    ):
                        established = True
                        _print(
                            {
                                "supervised_launch": "completed_reconciliation",
                                "collector_pid": child.pid,
                                "session_identity": None,
                                "authorization_identifier": recovered_metadata[
                                    "authorization_identifier"
                                ],
                                "ledger_instance_identifier": recovered_metadata[
                                    "ledger_instance_identifier"
                                ],
                                "target": recovered_metadata["target_count"],
                                "metadata_path": recovered_metadata["metadata_path"],
                                "log_path": recovered_metadata["log_path"],
                                "writer_lease_active": False,
                            }
                        )
                        return
                raise
            child_identity = child_snapshot["start_identity"]
            deadline = time.monotonic() + args.startup_timeout_seconds
            while time.monotonic() < deadline:
                before = process_snapshot(child.pid)
                current_metadata = read_metadata(paths["metadata"])
                current = _startup_authoritative_state(
                    args, process_id=child.pid
                )
                lease = writer_lease_status(args.ledger)
                after = process_snapshot(child.pid)
                current_authorization = current["authorization"]
                current_contract = current["contract"]

                if args.recovery and current_contract.completed:
                    completed_ready = (
                        current_authorization.lifecycle_state == "completed"
                        and current_contract.active_session_identity is None
                        and not current["open_runs"]
                        and current_metadata is not None
                        and current_metadata["supervision_state"] == "completed"
                    )
                    if completed_ready and not after["alive"]:
                        established = True
                        _print(
                            {
                                "supervised_launch": "completed_reconciliation",
                                "collector_pid": child.pid,
                                "session_identity": None,
                                "authorization_identifier": current_metadata[
                                    "authorization_identifier"
                                ],
                                "ledger_instance_identifier": current_metadata[
                                    "ledger_instance_identifier"
                                ],
                                "target": current_metadata["target_count"],
                                "metadata_path": current_metadata["metadata_path"],
                                "log_path": current_metadata["log_path"],
                                "writer_lease_active": False,
                            }
                        )
                        return
                    time.sleep(STARTUP_POLL_SECONDS)
                    continue

                if not before["alive"]:
                    reason = (
                        current_metadata["failure_reason"]
                        if current_metadata is not None
                        else None
                    )
                    raise SupervisionError(
                        "RFC-008 supervised child exited before startup "
                        f"completed: {reason or 'no failure detail'}"
                    )
                run = current["matching_run"]
                session = current_contract.active_session_identity
                metadata_agrees = (
                    current_metadata is not None
                    and current_metadata["collector_pid"] == child.pid
                    and current_metadata["collector_process_start_identity"]
                    == child_identity
                    and current_metadata["launch_authority_consumed_at"]
                    is not None
                )
                authoritative_agrees = (
                    current_authorization.lifecycle_state == "active"
                    and session is not None
                    and current_authorization.consuming_session_identity
                    == session
                    and run is not None
                    and str(run["run_id"]) == session
                    and int(run["process_id"]) == child.pid
                    and lease["active"]
                    and lease["recorded_process_id"] == child.pid
                )
                process_agrees = (
                    before["alive"]
                    and after["alive"]
                    and before["start_identity"] == child_identity
                    and after["start_identity"] == child_identity
                )
                if metadata_agrees and authoritative_agrees and process_agrees:
                    time.sleep(STARTUP_POLL_SECONDS)
                    final_process = process_snapshot(child.pid)
                    final_lease = writer_lease_status(args.ledger)
                    if (
                        not final_process["alive"]
                        or final_process["start_identity"] != child_identity
                        or not final_lease["active"]
                        or final_lease["recorded_process_id"] != child.pid
                    ):
                        raise SupervisionError(
                            "RFC-008 child exited during final startup verification"
                        )
                    value = update_metadata(
                        paths["metadata"],
                        session_identity=session,
                        supervision_state="active",
                        failure_reason=None,
                    )
                    established = True
                    _print(
                        {
                            "supervised_launch": "active",
                            "collector_pid": child.pid,
                            "collector_start_timestamp": value[
                                "collector_start_timestamp"
                            ],
                            "session_identity": session,
                            "authorization_identifier": value[
                                "authorization_identifier"
                            ],
                            "ledger_instance_identifier": value[
                                "ledger_instance_identifier"
                            ],
                            "target": value["target_count"],
                            "metadata_path": value["metadata_path"],
                            "log_path": value["log_path"],
                            "writer_lease_active": True,
                        }
                    )
                    return
                time.sleep(STARTUP_POLL_SECONDS)
            raise SupervisionError("RFC-008 supervised startup timed out")
        except BaseException as exc:
            if child is not None and not established:
                terminate_unestablished_child(child, child_identity)
            try:
                current_metadata = read_metadata(paths["metadata"])
                if (
                    current_metadata is not None
                    and current_metadata["supervision_state"]
                    in {"starting", "active"}
                ):
                    update_metadata(
                        paths["metadata"],
                        supervision_state=(
                            "interrupted"
                            if current_metadata["session_identity"] is not None
                            else "failed"
                        ),
                        exit_code=(
                            child.poll() if child is not None else None
                        ),
                        failure_reason=redact_exception(exc),
                    )
            except Exception:
                pass
            raise
        finally:
            if log_descriptor >= 0:
                os.close(log_descriptor)
            if authority_descriptor >= 0:
                os.close(authority_descriptor)


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
    value = status_report(
        ledger_path=args.ledger,
        config_path=args.config,
        marker_path=args.marker,
        expected_marker_sha256=_expected_marker_hash(args),
        authorization_path=args.authorization,
    )
    root = Path(args.repository_root).resolve()
    value["current_branch"] = subprocess.run(
        ("git", "branch", "--show-current"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    value["current_head"] = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    value["worktree_clean"] = not bool(
        subprocess.run(
            ("git", "status", "--porcelain", "--untracked-files=all"),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    _print(value)


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

    internal = sub.add_parser(INTERNAL_CHILD_COMMAND, help=argparse.SUPPRESS)
    internal.add_argument("--config", required=True)
    internal.add_argument("--resolver-config", required=True)
    internal.add_argument("--marker", required=True)
    _marker_hash_arguments(internal)
    internal.add_argument("--ledger", required=True)
    internal.add_argument("--authorization", required=True)
    internal.add_argument("--recovery", action="store_true")
    internal.add_argument("--repository-root", required=True)
    internal.add_argument("--burn-in-evidence", required=True)
    internal.add_argument("--release-approval", required=True)
    internal.add_argument("--approval-manifest", required=True)
    internal.add_argument("--supervision-metadata", required=True)
    internal.add_argument("--supervision-launch-identifier", required=True)
    internal.add_argument(
        "--supervision-authority-fd", required=True, type=int
    )
    internal.add_argument("--supervision-log-fd", required=True, type=int)
    internal.set_defaults(func=command_run)

    start = sub.add_parser(
        "start",
        description=(
            "Launch one fail-closed detached RFC-008 paper collector and wait "
            "for its authoritative session handshake."
        ),
    )
    start.add_argument("--config", required=True)
    start.add_argument(
        "--resolver-config",
        default="config/collection/rfc008_resolver_v1.json",
    )
    start.add_argument("--marker", required=True)
    _marker_hash_arguments(start)
    start.add_argument("--ledger", required=True)
    start.add_argument("--authorization", required=True)
    start.add_argument("--recovery", action="store_true")
    start.add_argument("--repository-root", default=".")
    start.add_argument(
        "--burn-in-evidence",
        default="data/resolver/rfc008_operational_burn_in_v1.json",
    )
    start.add_argument(
        "--release-approval",
        default=(
            "docs/research/rfc008/"
            "release_implementation_approval_v1.json"
        ),
    )
    start.add_argument(
        "--approval-manifest",
        default="docs/research/rfc008/approval_manifest_v1.json",
    )
    start.add_argument(
        "--startup-timeout-seconds",
        type=float,
        default=STARTUP_TIMEOUT_SECONDS,
        help=argparse.SUPPRESS,
    )
    start.set_defaults(func=command_start)

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
