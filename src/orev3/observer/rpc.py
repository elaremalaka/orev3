from __future__ import annotations

import os
import random
import time
from typing import Any

import httpx


DEFAULT_SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"


class SolanaRpcClient:
    """
    Read-only Solana JSON-RPC client.

    Includes bounded retry/backoff for:
    - HTTP 429 rate limits
    - HTTP 5xx transient server failures
    - Network timeouts / request failures

    Contains no wallet, signing, or transaction functionality.
    """

    def __init__(
        self,
        rpc_url: str | None = None,
        max_retries: int = 5,
    ) -> None:
        self.rpc_url = rpc_url or os.getenv(
            "ORE_RPC_URL",
            DEFAULT_SOLANA_RPC_URL,
        )

        self.max_retries = max_retries

        self._client = httpx.Client(
            timeout=httpx.Timeout(
                connect=10.0,
                read=15.0,
                write=10.0,
                pool=10.0,
            ),
            headers={
                "Content-Type": "application/json",
            },
        )

        self._request_id = 0

    def _rpc(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> Any:
        self._request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }

        last_error: Exception | None = None

        for attempt in range(
            self.max_retries + 1
        ):
            try:
                response = self._client.post(
                    self.rpc_url,
                    json=payload,
                )

                if response.status_code == 429:
                    retry_after = (
                        response.headers.get(
                            "Retry-After"
                        )
                    )

                    if retry_after:
                        try:
                            delay = float(
                                retry_after
                            )
                        except ValueError:
                            delay = 1.0
                    else:
                        delay = min(
                            0.5 * (2 ** attempt),
                            8.0,
                        )

                    delay += random.uniform(
                        0.0,
                        0.25,
                    )

                    last_error = RuntimeError(
                        "Solana RPC returned "
                        "HTTP 429 Too Many Requests"
                    )

                    if attempt >= self.max_retries:
                        break

                    time.sleep(delay)
                    continue

                if 500 <= response.status_code < 600:
                    last_error = RuntimeError(
                        "Solana RPC returned "
                        f"HTTP {response.status_code}"
                    )

                    if attempt >= self.max_retries:
                        break

                    delay = min(
                        0.5 * (2 ** attempt),
                        8.0,
                    )

                    delay += random.uniform(
                        0.0,
                        0.25,
                    )

                    time.sleep(delay)
                    continue

                response.raise_for_status()

                data = response.json()

                if "error" in data:
                    raise RuntimeError(
                        "Solana RPC error calling "
                        f"{method}: "
                        f"{data['error']}"
                    )

                return data["result"]

            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
            ) as exc:
                last_error = exc

                if attempt >= self.max_retries:
                    break

                delay = min(
                    0.5 * (2 ** attempt),
                    8.0,
                )

                delay += random.uniform(
                    0.0,
                    0.25,
                )

                time.sleep(delay)

        raise RuntimeError(
            f"Solana RPC request failed "
            f"after {self.max_retries + 1} attempts "
            f"for method {method}: "
            f"{last_error}"
        )

    def get_slot(self) -> int:
        result = self._rpc(
            "getSlot",
            [
                {
                    "commitment": "confirmed",
                }
            ],
        )

        return int(result)

    def get_account_info(
        self,
        address: str,
    ) -> dict[str, Any] | None:
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

    def get_multiple_accounts(
        self,
        addresses: list[str],
    ) -> list[dict[str, Any] | None]:
        result = self._rpc(
            "getMultipleAccounts",
            [
                addresses,
                {
                    "encoding": "base64",
                    "commitment": "confirmed",
                },
            ],
        )

        return result["value"]

    def get_genesis_hash(self) -> str:
        return str(self._rpc("getGenesisHash"))

    def get_account_info_with_context(
        self,
        address: str,
        *,
        commitment: str = "finalized",
    ) -> dict[str, Any]:
        return self._rpc(
            "getAccountInfo",
            [
                address,
                {
                    "encoding": "base64",
                    "commitment": commitment,
                },
            ],
        )

    def get_signatures_for_address(
        self,
        address: str,
        *,
        commitment: str = "finalized",
        limit: int = 1,
    ) -> list[dict[str, Any]]:
        return self._rpc(
            "getSignaturesForAddress",
            [
                address,
                {
                    "commitment": commitment,
                    "limit": limit,
                },
            ],
        )

    def close(self) -> None:
        self._client.close()
