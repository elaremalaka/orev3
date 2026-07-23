from __future__ import annotations

import argparse
from datetime import datetime, timezone
import time

from orev3.data.models import ObserverSnapshot
from orev3.data.writer import JsonlSnapshotWriter
from orev3.observer.accounts import (
    BOARD_ADDRESS,
    TREASURY_ADDRESS,
    decode_board,
    decode_round,
    decode_treasury,
    derive_round_address,
)
from orev3.observer.rpc import SolanaRpcClient


def collect_snapshot(
    rpc: SolanaRpcClient,
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

    board_account = rpc.get_account_info(
        str(BOARD_ADDRESS)
    )

    if board_account is None:
        raise RuntimeError(
            "ORE Board account was not found."
        )

    board = decode_board(
        board_account
    )

    treasury_account = (
        rpc.get_account_info(
            str(TREASURY_ADDRESS)
        )
    )

    if treasury_account is None:
        raise RuntimeError(
            "ORE Treasury account was not found."
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
        schema_version=1,
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
        default=0.8,
        help=(
            "Seconds between snapshot attempts. "
            "Default: 0.8"
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

    rpc = SolanaRpcClient()
    writer = JsonlSnapshotWriter()

    print()
    print("ORE Miner V3 Snapshot Collector")
    print("===============================")

    if args.once:
        print("Mode: single snapshot")
    else:
        print(
            f"Mode: continuous "
            f"({args.interval:.2f}s interval)"
        )

    print(
        "Output: data/raw/"
        "observer_YYYY-MM-DD.jsonl"
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
                    rpc
                )

                path = writer.write(
                    snapshot
                )

                slots_remaining = max(
                    snapshot.board.end_slot
                    - snapshot.rpc_slot,
                    0,
                )

                print(
                    f"round={snapshot.board.round_id} "
                    f"slot={snapshot.rpc_slot} "
                    f"slots_remaining="
                    f"{slots_remaining} "
                    f"motherlode_raw="
                    f"{snapshot.treasury.motherlode} "
                    f"file={path}"
                )

            except Exception as exc:
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
                args.interval - elapsed,
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
        rpc.close()


if __name__ == "__main__":
    main()
