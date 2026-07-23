from __future__ import annotations

import sys

from orev3.observer.accounts import (
    decode_round,
    derive_round_address,
)
from orev3.observer.rpc import SolanaRpcClient


LAMPORTS_PER_SOL = 1_000_000_000
RAW_UNITS_PER_ORE = 100_000_000_000


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: "
            "python -m orev3.observer.inspect_round "
            "<round_id>"
        )
        raise SystemExit(1)

    try:
        round_id = int(
            sys.argv[1]
        )
    except ValueError:
        print(
            "Round ID must be an integer."
        )
        raise SystemExit(1)

    rpc = SolanaRpcClient()

    try:
        address = derive_round_address(
            round_id
        )

        account = rpc.get_account_info(
            str(address)
        )

        if account is None:
            raise RuntimeError(
                f"Round {round_id} "
                f"was not found at {address}"
            )

        state = decode_round(
            account
        )

        print()
        print("ORE Miner V3 — Round Inspector")
        print("=============================")

        print(
            f"Round ID: {state.round_id}"
        )

        print(
            f"Round PDA: {address}"
        )

        print()
        print("Finalization State")
        print("------------------")

        print(
            f"Slot hash: "
            f"{state.slot_hash_hex}"
        )

        print(
            f"Entropy: "
            f"{state.entropy}"
        )

        print(
            f"Expires at slot: "
            f"{state.expires_at}"
        )

        print()
        print("Per-Square State")
        print("----------------")

        for square in range(25):
            deployed_sol = (
                state.deployed_lamports[square]
                / LAMPORTS_PER_SOL
            )

            reward_ore = (
                state.rewards[square]
                / RAW_UNITS_PER_ORE
            )

            print(
                f"{square:02d}: "
                f"{deployed_sol:.9f} SOL | "
                f"{state.miner_counts[square]:>4} miners | "
                f"mass {state.mass[square]} | "
                f"reward {reward_ore:.9f} ORE"
            )

        total_deployed_sol = (
            sum(
                state.deployed_lamports
            )
            / LAMPORTS_PER_SOL
        )

        total_winnings_sol = (
            state.total_winnings
            / LAMPORTS_PER_SOL
        )

        total_vaulted_sol = (
            state.total_vaulted
            / LAMPORTS_PER_SOL
        )

        motherlode_ore = (
            state.motherlode
            / RAW_UNITS_PER_ORE
        )

        print()
        print("Finalized Totals")
        print("----------------")

        print(
            f"Total deployed: "
            f"{total_deployed_sol:.9f} SOL"
        )

        print(
            f"Total unique miners: "
            f"{state.total_miners}"
        )

        print(
            f"Total returned/winnings pool: "
            f"{total_winnings_sol:.9f} SOL"
        )

        print(
            f"Total vaulted: "
            f"{total_vaulted_sol:.9f} SOL"
        )

        print(
            f"Round Motherlode payout: "
            f"{motherlode_ore:.9f} ORE"
        )

        print(
            f"Top miner / reward winner: "
            f"{state.top_miner}"
        )

        if state.entropy is not None:
            winning_square = (
                state.entropy
                % 25
            )

            print(
                f"Winning square: "
                f"{winning_square}"
            )

            print(
                f"Winning-square miners: "
                f"{state.miner_counts[winning_square]}"
            )

            print(
                f"Winning-square deployed: "
                f"{state.deployed_lamports[winning_square] / LAMPORTS_PER_SOL:.9f} SOL"
            )

        print()
        print("Mass Validation")
        print("---------------")

        nonzero_mass = [
            (i, value)
            for i, value in enumerate(
                state.mass
            )
            if value != 0
        ]

        if nonzero_mass:
            print(
                "Non-zero mass values found:"
            )

            for square, value in nonzero_mass:
                print(
                    f"Square {square}: "
                    f"{value}"
                )
        else:
            print(
                "All mass values are zero."
            )

            print(
                "This matches the current observed "
                "program behavior: deploy updates "
                "deployed and miner counts, while "
                "mass does not appear to be populated."
            )

    finally:
        rpc.close()


if __name__ == "__main__":
    main()
