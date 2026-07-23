from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"


class SolanaRpcClient:
    """
    Minimal read-only Solana JSON-RPC client.

    This class intentionally contains no wallet, signing,
    or transaction-submission functionality.
    """

    def __init__(self, rpc_url: str | None = None) -> None:
        self.rpc_url = rpc_url or os.getenv(
            "ORE_RPC_URL",
            DEFAULT_SOLANA_RPC_URL,
        )

        self._client = httpx.Client(
            timeout=20.0,
            headers={"Content-Type": "application/json"},
        )

        self._request_id = 0

    def _rpc(self, method: str, params: list[Any] | None = None) -> Any:
        self._request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }

        response = self._client.post(
            self.rpc_url,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise RuntimeError(
                f"Solana RPC error calling {method}: {data['error']}"
            )

        return data["result"]

    def get_slot(self) -> int:
        result = self._rpc(
            "getSlot",
            [{"commitment": "confirmed"}],
        )

        return int(result)

    def get_account_info(self, address: str) -> dict[str, Any] | None:
        result = self._rpc(
            "getAccountInfo",
            [
                address,
                {
                    "encoding": "base64",
                    "commitment": "confirmed",
                },
            ],
        )

        return result["value"]

    def close(self) -> None:
        self._client.close()
