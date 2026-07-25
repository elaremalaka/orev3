from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from orev3.ledger.decision_capture import (
    capture_paper_decision,
    capture_passive_decision,
)
from orev3.ledger.historical_import import import_history
from orev3.ledger.identifiers import deterministic_id, source_record_id
from orev3.ledger.observation_capture import capture_observation
from orev3.ledger.reconciliation import reconcile
from orev3.ledger.reporting import (
    export_tables,
    ledger_report,
    write_strict_json,
)
from orev3.ledger.storage import LedgerStore
from orev3.ledger.validation import assert_observational_only


DEFAULT_LEDGER = Path("data/ledger/participant_ledger_v1.sqlite")


def _store(path: Path, *, initialize: bool = False) -> LedgerStore:
    store = LedgerStore(path)
    if initialize:
        store.initialize()
    return store


def command_init(args: argparse.Namespace) -> None:
    assert_observational_only()
    if args.ledger.exists():
        if not args.force:
            raise FileExistsError(
                f"Refusing to overwrite {args.ledger}; use --force"
            )
        args.ledger.unlink()
    with _store(args.ledger, initialize=True):
        pass
    print(f"Initialized read-only participant ledger: {args.ledger}")


def command_import(args: argparse.Namespace) -> None:
    assert_observational_only()
    if args.dry_run:
        result = import_history(args.source, None, dry_run=True)
    else:
        with _store(args.ledger, initialize=True) as store:
            result = import_history(args.source, store)
    if args.report:
        write_strict_json(args.report, result, force=args.force)
    print(json.dumps(result, allow_nan=False, sort_keys=True))


def command_reconcile(args: argparse.Namespace) -> None:
    assert_observational_only()
    with _store(args.ledger, initialize=True) as store:
        records = reconcile(store)
    print(f"Reconciled {len(records)} opportunities")


def command_report(args: argparse.Namespace) -> None:
    assert_observational_only()
    with LedgerStore(args.ledger, read_only=True) as store:
        report = ledger_report(store)
    write_strict_json(args.output, report, force=args.force)
    print(f"Wrote deterministic report: {args.output}")


def command_export(args: argparse.Namespace) -> None:
    assert_observational_only()
    with LedgerStore(args.ledger, read_only=True) as store:
        outputs = export_tables(
            store,
            args.output_dir,
            pseudonymize_wallets=args.pseudonymize_wallets,
            force=args.force,
        )
    print(f"Wrote {len(outputs)} deterministic exports")


def command_observe(args: argparse.Namespace) -> None:
    assert_observational_only(
        submit=args.submit,
        sign=args.sign,
        claim=args.claim,
        build_transaction=args.build_transaction,
    )
    if args.snapshot is not None:
        raw = json.loads(args.snapshot.read_text(encoding="utf-8"))
        source_name = str(args.snapshot)
    else:
        from orev3.observer.collect import collect_snapshot
        from orev3.observer.rpc import SolanaRpcClient

        rpc = SolanaRpcClient()
        try:
            raw = collect_snapshot(rpc, args.session_id).model_dump(mode="json")
        finally:
            rpc.close()
        source_name = "solana_rpc_live_read_only"
    sid = source_record_id(source_name, 1, raw)
    opportunity, event = capture_observation(
        raw,
        observation_index=args.observation_index,
        source=source_name,
        source_record_id=sid,
        run_id=deterministic_id("observe-run", sid),
        session_id=args.session_id,
    )
    decision_time = datetime.fromisoformat(
        str(raw["observed_at_utc"]).replace("Z", "+00:00")
    )
    if args.mode == "passive":
        decision = capture_passive_decision(
            opportunity_id=opportunity.opportunity_id,
            decision_time=decision_time,
        )
    else:
        if args.strategy.startswith(("random_forest", "hist_gradient_boosting")):
            raise ValueError(
                "Frozen RFC-004 artifacts do not contain complete live ranking "
                "vectors or a serialized inference pipeline"
            )
        decision = capture_paper_decision(
            opportunity_id=opportunity.opportunity_id,
            strategy_id=args.strategy,
            strategy_version="1",
            selected_squares=args.selected_squares,
            ranking_scores=None,
            deployment_total_lamports=args.deployment_lamports,
            decision_time=decision_time,
            decision_latency_ms=0,
        )
    with _store(args.ledger, initialize=True) as store:
        with store.connection:
            store.upsert_record("opportunities", opportunity)
            store.insert_event(event)
            store.upsert_record("decisions", decision)
    print(
        f"Recorded {args.mode} opportunity {opportunity.opportunity_id}; "
        "no transaction was built, signed, or submitted"
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="RFC-006 read-only participant economic ledger"
    )
    sub = root.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    init.add_argument("--force", action="store_true")
    init.set_defaults(handler=command_init)

    history = sub.add_parser("import-history")
    history.add_argument("--source", type=Path, required=True)
    history.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    history.add_argument("--report", type=Path)
    history.add_argument("--dry-run", action="store_true")
    history.add_argument("--force", action="store_true")
    history.set_defaults(handler=command_import)

    reconciliation = sub.add_parser("reconcile")
    reconciliation.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    reconciliation.set_defaults(handler=command_reconcile)

    report = sub.add_parser("report")
    report.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    report.add_argument(
        "--output",
        type=Path,
        default=Path("data/ledger/participant_ledger_report_v1.json"),
    )
    report.add_argument("--force", action="store_true")
    report.set_defaults(handler=command_report)

    export = sub.add_parser("export")
    export.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    export.add_argument("--output-dir", type=Path, default=Path("data/ledger"))
    export.add_argument("--pseudonymize-wallets", action="store_true")
    export.add_argument("--force", action="store_true")
    export.set_defaults(handler=command_export)

    observe = sub.add_parser("observe")
    observe.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    observe.add_argument(
        "--snapshot",
        type=Path,
        help="Offline snapshot JSON; omit for one read-only live RPC observation",
    )
    observe.add_argument("--observation-index", type=int, default=0)
    observe.add_argument("--session-id", default="rfc006-observe")
    observe.add_argument("--mode", choices=("passive", "paper"), required=True)
    observe.add_argument("--strategy", default="none")
    observe.add_argument("--deployment-lamports", type=int, default=0)
    observe.add_argument("--selected-squares", type=int, nargs="*", default=[])
    # Deliberate tripwires: any requested live action fails before I/O.
    observe.add_argument("--submit", action="store_true", help=argparse.SUPPRESS)
    observe.add_argument("--sign", action="store_true", help=argparse.SUPPRESS)
    observe.add_argument("--claim", action="store_true", help=argparse.SUPPRESS)
    observe.add_argument(
        "--build-transaction", action="store_true", help=argparse.SUPPRESS
    )
    observe.set_defaults(handler=command_observe)
    return root


def main() -> None:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (ValueError, PermissionError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
