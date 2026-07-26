from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

from orev3.collection.collector import PaperCollector
from orev3.collection.config import CollectionConfig
from orev3.collection.cursor_store import CollectionStore
from orev3.collection.health import (
    deterministic_health,
    health_snapshot,
)
from orev3.collection.gate_b import (
    freeze_gate_b_marker,
    gate_b_status,
)
from orev3.collection.gate_b_analysis_dataset import (
    build_gate_b_analysis_dataset,
)
from orev3.collection.metrics import evaluate_burn_in
from orev3.collection.outcome_recovery import (
    DEFAULT_GATE_B_MARKER,
    DEFAULT_LIVE_LEDGER,
    RpcRecoveryProvider,
    create_recovery_artifact,
    requery_recovery_artifact,
    verify_recovery_artifact,
)
from orev3.collection.reporting import export_collection
from orev3.collection.writer_lock import WriterLease
from orev3.ledger.reporting import write_strict_json
from orev3.ledger.validation import assert_observational_only


DEFAULT_CONFIG = Path("config/collection/rfc007_burn_in_v1.json")


def _reject_live(args: argparse.Namespace) -> None:
    assert_observational_only(
        submit=getattr(args, "submit", False),
        sign=getattr(args, "sign", False),
        claim=getattr(args, "claim", False),
        build_transaction=getattr(args, "build_transaction", False),
    )


def _remove_generated_ledger(path: Path) -> None:
    for candidate in (
        path,
        path.with_name(path.name + "-wal"),
        path.with_name(path.name + "-shm"),
        Path(str(path) + ".writer.lock"),
    ):
        candidate.unlink(missing_ok=True)


def command_validate_config(args: argparse.Namespace) -> None:
    _reject_live(args)
    config = CollectionConfig.from_path(args.config)
    print(
        json.dumps(
            {
                "valid": True,
                "schema_version": config.schema_version,
                "configuration_hash": config.configuration_hash,
                "strategy_id": config.strategy_id,
                "model_strategy_available": False,
            },
            allow_nan=False,
            sort_keys=True,
        )
    )


def _open_store(path: Path, config: CollectionConfig) -> CollectionStore:
    store = CollectionStore(
        path, busy_timeout_ms=config.busy_timeout_ms
    )
    store.initialize()
    with store.connection:
        store.set_metadata("configuration_hash", config.configuration_hash)
        store.set_metadata("collector_version", config.collector_version)
        store.set_metadata("observer_modified", "0")
    return store


def command_replay(args: argparse.Namespace) -> None:
    _reject_live(args)
    config = CollectionConfig.from_path(args.config)
    if args.ledger.exists() and not args.resume:
        if not args.force:
            raise FileExistsError(
                f"Refusing to overwrite {args.ledger}; use --force or --resume"
            )
        _remove_generated_ledger(args.ledger)
    with WriterLease(args.ledger):
        store = _open_store(args.ledger, config)
        try:
            collector = PaperCollector(
                store=store,
                config=config,
                mode="historical_replay_burn_in",
            )
            restart_at = min(args.restart_after, args.max_opportunities)
            if restart_at > 0 and store.ledger.count("opportunities") < restart_at:
                collector.replay(
                    args.source, max_opportunities=restart_at
                )
                store.close()
                store = _open_store(args.ledger, config)
                collector = PaperCollector(
                    store=store,
                    config=config,
                    mode="historical_replay_burn_in",
                )
                with store.connection:
                    store.set_metadata("restart_resume_proven", "1")
            total = collector.replay(
                args.source, max_opportunities=args.max_opportunities
            )
            if restart_at == 0:
                with store.connection:
                    store.set_metadata("restart_resume_proven", "0")
            print(
                json.dumps(
                    {
                        "opportunities": total,
                        "integrity": store.integrity_check(),
                        "restart_resume_proven": (
                            store.metadata().get("restart_resume_proven") == "1"
                        ),
                    },
                    allow_nan=False,
                    sort_keys=True,
                )
            )
        finally:
            store.close()


def command_run(args: argparse.Namespace) -> None:
    _reject_live(args)
    config = CollectionConfig.from_path(args.config)
    with WriterLease(args.ledger):
        with _open_store(args.ledger, config) as store:
            collector = PaperCollector(
                store=store,
                config=config,
                mode="real_time_burn_in",
            )
            collector.begin_real_time_run(lease_exclusive=True)
            print(
                "RFC-007 paper collector starting; observer remains untouched; "
                "no transaction can be built or submitted",
                flush=True,
            )
            collector.run_forever()
            collector.finish_real_time_run()
            print("RFC-007 paper collector stopped cleanly", flush=True)


def command_health(args: argparse.Namespace) -> None:
    _reject_live(args)
    with CollectionStore(args.ledger, read_only=True) as store:
        value = deterministic_health(
            health_snapshot(store, mode=args.mode)
        )
    if args.output:
        write_strict_json(args.output, value, force=args.force)
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def command_evaluate(args: argparse.Namespace) -> None:
    _reject_live(args)
    with CollectionStore(args.ledger, read_only=True) as store:
        value = evaluate_burn_in(
            store, mode=args.mode
        ).model_dump(mode="json")
    if args.output:
        write_strict_json(args.output, value, force=args.force)
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def command_export(args: argparse.Namespace) -> None:
    _reject_live(args)
    with CollectionStore(args.ledger, read_only=True) as store:
        outputs = export_collection(
            store,
            args.output_dir,
            mode=args.mode,
            force=args.force,
        )
    print(f"Wrote {len(outputs)} deterministic RFC-007 exports")


def command_archive(args: argparse.Namespace) -> None:
    _reject_live(args)
    if args.output.exists() and not args.force:
        raise FileExistsError(
            f"Refusing to overwrite {args.output}; use --force"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.ledger, args.output)
    print(f"Archived ledger without deleting source: {args.output}")


def command_freeze_gate_b(args: argparse.Namespace) -> None:
    _reject_live(args)
    config = CollectionConfig.from_path(args.config)
    with CollectionStore(args.ledger, read_only=True) as store:
        marker = freeze_gate_b_marker(
            store,
            repository_commit=args.repository_commit,
            branch=args.branch,
            configuration_hash=config.configuration_hash,
        )
    write_strict_json(
        args.output,
        marker.model_dump(mode="json"),
        force=False,
    )
    print(
        json.dumps(
            marker.model_dump(mode="json"),
            allow_nan=False,
            sort_keys=True,
        )
    )


def command_gate_b_status(args: argparse.Namespace) -> None:
    _reject_live(args)
    with CollectionStore(args.ledger, read_only=True) as store:
        value = gate_b_status(
            store,
            args.marker,
            expected_marker_sha256=args.expected_marker_sha256,
        )
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def _recovery_providers(
    args: argparse.Namespace,
) -> tuple[RpcRecoveryProvider, RpcRecoveryProvider]:
    primary_url = os.getenv(args.primary_rpc_env)
    secondary_url = os.getenv(args.secondary_rpc_env)
    if not primary_url:
        raise ValueError(
            f"Primary RPC environment variable is unset: "
            f"{args.primary_rpc_env}"
        )
    if not secondary_url:
        raise ValueError(
            f"Secondary RPC environment variable is unset: "
            f"{args.secondary_rpc_env}"
        )
    primary = RpcRecoveryProvider(
        args.primary_provider_id,
        primary_url,
    )
    secondary = RpcRecoveryProvider(
        args.secondary_provider_id,
        secondary_url,
    )
    if primary.endpoint_fingerprint == secondary.endpoint_fingerprint:
        primary.close()
        secondary.close()
        raise ValueError(
            "Primary and secondary RPC endpoints must be independent"
        )
    return primary, secondary


def command_recover_outcome_evidence_create(
    args: argparse.Namespace,
) -> None:
    _reject_live(args)
    primary, secondary = _recovery_providers(args)
    try:
        value = create_recovery_artifact(
            output=args.output,
            round_ids=args.round_id,
            primary=primary,
            secondary=secondary,
            network=args.network,
            expected_genesis_hash=args.expected_genesis_hash,
            expected_program_id=args.expected_program_id,
            sample_id=args.sample_id,
            marker_path=args.marker,
            expected_marker_sha256=args.expected_marker_sha256,
            repository_commit=args.repository_commit,
            branch=args.branch,
            decoder_version=args.decoder_version,
            recovery_protocol_version=args.recovery_protocol_version,
            recovery_method_version=args.recovery_method_version,
            live_ledger_path=args.live_ledger,
            control_round_id=args.control_round_id,
            formal_gate_b=args.formal_gate_b,
            force=args.force,
        )
    finally:
        primary.close()
        secondary.close()
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def command_recover_outcome_evidence_verify(
    args: argparse.Namespace,
) -> None:
    _reject_live(args)
    value = verify_recovery_artifact(args.artifact)
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def command_recover_outcome_evidence_requery(
    args: argparse.Namespace,
) -> None:
    _reject_live(args)
    primary, secondary = _recovery_providers(args)
    try:
        value = requery_recovery_artifact(
            args.artifact,
            primary=primary,
            secondary=secondary,
        )
    finally:
        primary.close()
        secondary.close()
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def command_build_gate_b_analysis_dataset(
    args: argparse.Namespace,
) -> None:
    _reject_live(args)
    value = build_gate_b_analysis_dataset(
        output=args.output,
        ledger_path=args.ledger,
        marker_path=args.marker,
        expected_marker_sha256=args.expected_marker_sha256,
        recovery_artifact=args.recovery_artifact,
        expected_recovery_evidence_sha256=(
            args.expected_recovery_evidence_sha256
        ),
        expected_recovery_manifest_sha256=(
            args.expected_recovery_manifest_sha256
        ),
        expected_recovery_content_sha256=(
            args.expected_recovery_content_sha256
        ),
        repository_root=args.repository_root,
        repository_commit=args.repository_commit,
        branch=args.branch,
    )
    print(json.dumps(value, allow_nan=False, sort_keys=True))


def _live_tripwires(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--submit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--sign", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--claim", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--build-transaction", action="store_true", help=argparse.SUPPRESS
    )


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="RFC-007 continuous read-only paper collector"
    )
    sub = root.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-config")
    validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    _live_tripwires(validate)
    validate.set_defaults(handler=command_validate_config)

    replay = sub.add_parser("replay")
    replay.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    replay.add_argument("--source", type=Path, required=True)
    replay.add_argument("--ledger", type=Path, required=True)
    replay.add_argument("--max-opportunities", type=int, default=100)
    replay.add_argument("--restart-after", type=int, default=50)
    replay.add_argument("--resume", action="store_true")
    replay.add_argument("--force", action="store_true")
    _live_tripwires(replay)
    replay.set_defaults(handler=command_replay)

    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    run.add_argument("--ledger", type=Path, required=True)
    _live_tripwires(run)
    run.set_defaults(handler=command_run)

    for name, handler in (
        ("health", command_health),
        ("evaluate-burn-in", command_evaluate),
    ):
        command = sub.add_parser(name)
        command.add_argument("--ledger", type=Path, required=True)
        command.add_argument(
            "--mode",
            choices=("historical_replay_burn_in", "real_time_burn_in"),
            default="historical_replay_burn_in",
        )
        command.add_argument("--output", type=Path)
        command.add_argument("--force", action="store_true")
        _live_tripwires(command)
        command.set_defaults(handler=handler)

    export = sub.add_parser("export")
    export.add_argument("--ledger", type=Path, required=True)
    export.add_argument("--output-dir", type=Path, required=True)
    export.add_argument(
        "--mode",
        choices=("historical_replay_burn_in", "real_time_burn_in"),
        default="historical_replay_burn_in",
    )
    export.add_argument("--force", action="store_true")
    _live_tripwires(export)
    export.set_defaults(handler=command_export)

    archive = sub.add_parser("archive")
    archive.add_argument("--ledger", type=Path, required=True)
    archive.add_argument("--output", type=Path, required=True)
    archive.add_argument("--force", action="store_true")
    _live_tripwires(archive)
    archive.set_defaults(handler=command_archive)

    freeze_gate_b = sub.add_parser("freeze-gate-b")
    freeze_gate_b.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    freeze_gate_b.add_argument("--ledger", type=Path, required=True)
    freeze_gate_b.add_argument("--output", type=Path, required=True)
    freeze_gate_b.add_argument("--repository-commit", required=True)
    freeze_gate_b.add_argument("--branch", required=True)
    _live_tripwires(freeze_gate_b)
    freeze_gate_b.set_defaults(handler=command_freeze_gate_b)

    gate_b = sub.add_parser("gate-b-status")
    gate_b.add_argument("--ledger", type=Path, required=True)
    gate_b.add_argument("--marker", type=Path, required=True)
    gate_b.add_argument("--expected-marker-sha256", required=True)
    _live_tripwires(gate_b)
    gate_b.set_defaults(handler=command_gate_b_status)

    dataset = sub.add_parser("build-gate-b-analysis-dataset")
    dataset.add_argument("--ledger", type=Path, required=True)
    dataset.add_argument("--marker", type=Path, required=True)
    dataset.add_argument("--expected-marker-sha256", required=True)
    dataset.add_argument(
        "--recovery-artifact",
        type=Path,
        required=True,
    )
    dataset.add_argument(
        "--expected-recovery-evidence-sha256",
        required=True,
    )
    dataset.add_argument(
        "--expected-recovery-manifest-sha256",
        required=True,
    )
    dataset.add_argument(
        "--expected-recovery-content-sha256",
        required=True,
    )
    dataset.add_argument(
        "--repository-root",
        type=Path,
        default=Path("."),
    )
    dataset.add_argument("--repository-commit", required=True)
    dataset.add_argument("--branch", required=True)
    dataset.add_argument("--output", type=Path, required=True)
    _live_tripwires(dataset)
    dataset.set_defaults(handler=command_build_gate_b_analysis_dataset)

    recovery = sub.add_parser("recover-outcome-evidence")
    recovery_modes = recovery.add_subparsers(
        dest="recovery_mode",
        required=True,
    )

    create = recovery_modes.add_parser("create")
    create.add_argument(
        "--round-id",
        action="append",
        type=int,
        required=True,
    )
    create.add_argument("--primary-provider-id", required=True)
    create.add_argument("--primary-rpc-env", required=True)
    create.add_argument("--secondary-provider-id", required=True)
    create.add_argument("--secondary-rpc-env", required=True)
    create.add_argument("--network", required=True)
    create.add_argument("--expected-genesis-hash", required=True)
    create.add_argument("--expected-program-id", required=True)
    create.add_argument("--sample-id", required=True)
    create.add_argument(
        "--marker",
        type=Path,
        default=DEFAULT_GATE_B_MARKER,
    )
    create.add_argument("--expected-marker-sha256", required=True)
    create.add_argument("--repository-commit", required=True)
    create.add_argument("--branch", required=True)
    create.add_argument("--decoder-version", required=True)
    create.add_argument("--recovery-protocol-version", required=True)
    create.add_argument("--recovery-method-version", required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument(
        "--live-ledger",
        type=Path,
        default=DEFAULT_LIVE_LEDGER,
    )
    create.add_argument("--control-round-id", type=int)
    create.add_argument("--formal-gate-b", action="store_true")
    create.add_argument("--force", action="store_true")
    _live_tripwires(create)
    create.set_defaults(
        handler=command_recover_outcome_evidence_create
    )

    verify = recovery_modes.add_parser("verify")
    verify.add_argument("--artifact", type=Path, required=True)
    _live_tripwires(verify)
    verify.set_defaults(
        handler=command_recover_outcome_evidence_verify
    )

    requery = recovery_modes.add_parser("requery")
    requery.add_argument("--artifact", type=Path, required=True)
    requery.add_argument("--primary-provider-id", required=True)
    requery.add_argument("--primary-rpc-env", required=True)
    requery.add_argument("--secondary-provider-id", required=True)
    requery.add_argument("--secondary-rpc-env", required=True)
    _live_tripwires(requery)
    requery.set_defaults(
        handler=command_recover_outcome_evidence_requery
    )
    return root


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (
        FileExistsError,
        PermissionError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
