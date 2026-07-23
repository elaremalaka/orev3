from __future__ import annotations

from orev3.observer.accounts import (
    BOARD_ADDRESS,
    TREASURY_ADDRESS,
    decode_board,
    decode_round,
    decode_treasury,
    derive_round_address,
)
from orev3.observer.rpc import SolanaRpcClient


LAMPORTS_PER_SOL = 1_000_000_000
RAW_UNITS_PER_ORE = 100_000_000_000


def main() -> None:
    rpc = SolanaRpcClient()

    try:
        current_slot = rpc.get_slot()

        # Read global ORE Board.
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

        # Read global ORE Treasury.
        treasury_account = rpc.get_account_info(
            str(TREASURY_ADDRESS)
        )

        if treasury_account is None:
            raise RuntimeError(
                "ORE Treasury account was not found."
            )

        treasury = decode_treasury(
            treasury_account
        )

        # Derive and read current Round account.
        round_address = derive_round_address(
            board.round_id
        )

        round_account = rpc.get_account_info(
            str(round_address)
        )

        if round_account is None:
            raise RuntimeError(
                f"ORE Round account {board.round_id} "
                f"was not found at {round_address}."
            )

        round_state = decode_round(
            round_account
        )

        print()
        print("ORE Miner V3 Observer")
        print("=====================")

        print(
            f"Current Solana slot: {current_slot}"
        )

        print()
        print("ORE Board")
        print("---------")

        print(
            f"Round ID:   {board.round_id}"
        )

        print(
            f"Start slot: {board.start_slot}"
        )

        print(
            f"End slot:   {board.end_slot}"
        )

        slots_remaining = max(
            board.end_slot - current_slot,
            0,
        )

        print(
            f"Slots remaining: {slots_remaining}"
        )

        print()
        print(
            f"Round PDA: {round_address}"
        )

        print()
        print("ORE Treasury")
        print("------------")

        motherlode_ore = (
            treasury.motherlode
            / RAW_UNITS_PER_ORE
        )

        print(
            f"Current Motherlode: "
            f"{motherlode_ore:.6f} ORE"
        )

        print(
            f"Motherlode raw units: "
            f"{treasury.motherlode}"
        )

        print()
        print("Squares")
        print("-------")

        for square in range(25):
            deployed_sol = (
                round_state.deployed_lamports[square]
                / LAMPORTS_PER_SOL
            )

            miners = (
                round_state.miner_counts[square]
            )

            mass = (
                round_state.mass[square]
            )

            print(
                f"{square:02d}: "
                f"{deployed_sol:.9f} SOL | "
                f"{miners:>4} miners | "
                f"mass {mass}"
            )

        total_deployed = (
            sum(
                round_state.deployed_lamports
            )
            / LAMPORTS_PER_SOL
        )

        print()
        print("Round Totals")
        print("------------")

        print(
            f"Total deployed: "
            f"{total_deployed:.9f} SOL"
        )

        print(
            f"Total unique miners: "
            f"{round_state.total_miners}"
        )

        print(
            f"Round Motherlode payout raw units: "
            f"{round_state.motherlode}"
        )

        print(
            f"Total vaulted: "
            f"{round_state.total_vaulted}"
        )

        print(
            f"Total winnings: "
            f"{round_state.total_winnings}"
        )

    finally:
        rpc.close()


if __name__ == "__main__":
    main()
