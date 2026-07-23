from __future__ import annotations

import argparse
from datetime import datetime, timezone
import time
import uuid

from orev3.data.models import (
    ObserverSnapshot,
)
from orev3.data.writer import (
    CollectorEventWriter,
    JsonlSnapshotWriter,
)
from orev3.observer.accounts import (
    BOARD_ADDRESS,
    TREASURY_ADDRESS,
    decode_board,
    decode_round,
    decode_treasury,
    derive_round_address,
)
from orev3.observer.rpc import (
    SolanaRpcClient,
)


U64_MAX = (2 ** 64) - 1


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def collect_snapshot(
    rpc: SolanaRpcClient,
    session_id: str,
) -> ObserverSnapshot:
    """
    Read one point-in-time ORE snapshot.

    No wallet, signing, or transaction functionality
    is involved.
    """

    observed_at_utc = datetime.now(
        timezone.utc
    )

    rpc_slot = rpc.get_slot()

    # Board and Treasury are fixed addresses,
    # so fetch them in a single RPC request.
    accounts = rpc.get_multiple_accounts(
        [
            str(BOARD_ADDRESS),
            str(TREASURY_ADDRESS),
        ]
    )

    board_account = accounts[0]
    treasury_account = accounts[1]

    if board_account is None:
        raise RuntimeError(
            "ORE Board account was not found."
        )

    if treasury_account is None:
        raise RuntimeError(
            "ORE Treasury account was not found."
        )

    board = decode_board(
        board_account
    )

    treasury = decode_treasury(
        treasury_account
    )

    round_address = derive_round_address(
        board.round_id
    )

    round_account = rpc.get_account_info(
        str(round_address)
    )

    if round_account is None:
        raise RuntimeError(
            f"ORE Round account "
            f"{board.round_id} "
            f"was not found at "
            f"{round_address}."
        )

    round_state = decode_round(
        round_account
    )

    return ObserverSnapshot(
        schema_version=2,
        collector_session_id=session_id,
        observed_at_utc=observed_at_utc,
        rpc_slot=rpc_slot,
        board=board,
        treasury=treasury,
        round=round_state,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect immutable ORE Miner V3 "
            "Observer snapshots."
        )
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help=(
            "Seconds between snapshot attempts. "
            "Default: 1.0"
        ),
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help=(
            "Collect one snapshot and exit."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.interval <= 0:
        raise SystemExit(
            "--interval must be greater than 0."
        )

    session_id = str(
        uuid.uuid4()
    )

    rpc = SolanaRpcClient()
    writer = JsonlSnapshotWriter()
    event_writer = CollectorEventWriter()

    previous_round_id: int | None = None

    event_writer.write(
        {
            "event": "session_start",
            "timestamp_utc": utc_now_iso(),
            "collector_session_id": session_id,
            "interval_seconds": args.interval,
        }
    )

    print()
    print("ORE Miner V3 Snapshot Collector")
    print("===============================")

    print(
        f"Session ID: {session_id}"
    )

    if args.once:
        print(
            "Mode: single snapshot"
        )
    else:
        print(
            f"Mode: continuous "
            f"({args.interval:.2f}s interval)"
        )

    print(
        "Output: data/raw/"
        "observer_YYYY-MM-DD.jsonl"
    )

    print(
        "Events: logs/"
        "collector_events_YYYY-MM-DD.jsonl"
    )

    print()
    print(
        "Press Control+C to stop."
    )

    try:
        while True:
            started_at = time.monotonic()

            try:
                snapshot = collect_snapshot(
                    rpc,
                    session_id,
                )

                path = writer.write(
                    snapshot
                )

                round_id = (
                    snapshot.board.round_id
                )

                if (
                    previous_round_id is not None
                    and round_id
                    != previous_round_id
                ):
                    event_writer.write(
                        {
                            "event":
                                "round_transition",
                            "timestamp_utc":
                                utc_now_iso(),
                            "collector_session_id":
                                session_id,
                            "from_round_id":
                                previous_round_id,
                            "to_round_id":
                                round_id,
                            "rpc_slot":
                                snapshot.rpc_slot,
                        }
                    )

                previous_round_id = (
                    round_id
                )

                if (
                    snapshot.board.end_slot
                    == U64_MAX
                ):
                    round_status = (
                        "initializing"
                    )

                    slots_remaining_text = (
                        "unknown"
                    )
                else:
                    round_status = "active"

                    slots_remaining = max(
                        snapshot.board.end_slot
                        - snapshot.rpc_slot,
                        0,
                    )

                    slots_remaining_text = str(
                        slots_remaining
                    )

                print(
                    f"round={round_id} "
                    f"slot={snapshot.rpc_slot} "
                    f"status={round_status} "
                    f"slots_remaining="
                    f"{slots_remaining_text} "
                    f"motherlode_raw="
                    f"{snapshot.treasury.motherlode} "
                    f"file={path}"
                )

            except Exception as exc:
                event = {
                    "event":
                        "snapshot_error",
                    "timestamp_utc":
                        utc_now_iso(),
                    "collector_session_id":
                        session_id,
                    "error_type":
                        type(exc).__name__,
                    "error_message":
                        str(exc),
                }

                event_writer.write(
                    event
                )

                print(
                    f"snapshot_error: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

            if args.once:
                break

            elapsed = (
                time.monotonic()
                - started_at
            )

            sleep_for = max(
                args.interval
                - elapsed,
                0,
            )

            time.sleep(
                sleep_for
            )

    except KeyboardInterrupt:
        print()
        print(
            "Snapshot collection stopped."
        )

    finally:
        event_writer.write(
            {
                "event": "session_stop",
                "timestamp_utc":
                    utc_now_iso(),
                "collector_session_id":
                    session_id,
            }
        )

        rpc.close()


if __name__ == "__main__":
    main()
