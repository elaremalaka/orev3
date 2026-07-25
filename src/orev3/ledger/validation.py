from __future__ import annotations

import math
from typing import Any

from solders.pubkey import Pubkey
from solders.signature import Signature


SECRET_FRAGMENTS = (
    "private_key",
    "privatekey",
    "secret_key",
    "secretkey",
    "seed_phrase",
    "seedphrase",
    "mnemonic",
    "keypair",
    "signer",
)


def reject_non_finite(value: Any, path: str = "value") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} must be finite")
    if isinstance(value, dict):
        for key, child in value.items():
            reject_non_finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_non_finite(child, f"{path}[{index}]")


def reject_secret_fields(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_").replace(" ", "_")
            if any(fragment in normalized for fragment in SECRET_FRAGMENTS):
                raise ValueError(f"Secret material is forbidden: {path}.{key}")
            reject_secret_fields(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_secret_fields(child, f"{path}[{index}]")


def validate_wallet_public_key(value: str) -> str:
    try:
        Pubkey.from_string(value)
    except Exception as exc:
        raise ValueError("Invalid Solana wallet public key") from exc
    return value


def validate_transaction_signature(value: str) -> str:
    try:
        Signature.from_string(value)
    except Exception as exc:
        raise ValueError("Invalid Solana transaction signature") from exc
    return value


def validate_selected_squares(values: list[int]) -> list[int]:
    if len(values) != len(set(values)):
        raise ValueError("Selected squares must be unique")
    if any(value < 0 or value > 24 for value in values):
        raise ValueError("Selected square must be between 0 and 24")
    return values


def assert_observational_only(
    *,
    submit: bool = False,
    sign: bool = False,
    claim: bool = False,
    build_transaction: bool = False,
) -> None:
    requested = [
        name
        for name, enabled in {
            "submit": submit,
            "sign": sign,
            "claim": claim,
            "build_transaction": build_transaction,
        }.items()
        if enabled
    ]
    if requested:
        raise PermissionError(
            "RFC-006 is observational only; forbidden action(s): "
            + ", ".join(requested)
        )
