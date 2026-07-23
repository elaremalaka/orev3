from __future__ import annotations

from orev3.observer.rpc import SolanaRpcClient


def main() -> None:
    rpc = SolanaRpcClient()

    try:
        slot = rpc.get_slot()

        print("ORE Miner V3 Observer")
        print("---------------------")
        print(f"Connected to Solana RPC")
        print(f"Current confirmed slot: {slot}")

    finally:
        rpc.close()


if __name__ == "__main__":
    main()
