from __future__ import annotations

import base64
import struct
from typing import Any

from solders.pubkey import Pubkey

from orev3.data.models import (
    BoardState,
    RoundState,
    TreasuryState,
)


ORE_PROGRAM_ID = Pubkey.from_string(
    "oreV3EG1i9BEgiAJ8b177Z2S2rMarzak4NMv1kULvWv"
)

BOARD_ADDRESS = Pubkey.from_string(
    "BrcSxdp1nXFzou1YyDnQJcPNBNHgoypZmTsyKBSLLXzi"
)

TREASURY_ADDRESS = Pubkey.from_string(
    "45db2FSR4mcXdSVVZbKbwojU6uYDpMyhpEi7cC8nHaWG"
)

ACCOUNT_HEADER_SIZE = 8

BOARD_ACCOUNT_TYPE = 105
ROUND_ACCOUNT_TYPE = 109
TREASURY_ACCOUNT_TYPE = 104


def decode_account_data(
    account_info: dict[str, Any],
) -> bytes:
    """Decode base64 account data returned by Solana JSON-RPC."""

    data_field = account_info.get("data")

    if (
        not isinstance(data_field, list)
        or len(data_field) < 2
        or data_field[1] != "base64"
    ):
        raise ValueError(
            "Expected Solana account data encoded as base64."
        )

    return base64.b64decode(
        data_field[0]
    )


def validate_account_type(
    raw_data: bytes,
    expected_type: int,
) -> None:
    """Validate the Steel account discriminator/type."""

    if len(raw_data) < ACCOUNT_HEADER_SIZE:
        raise ValueError(
            "Account data is too short."
        )

    actual_type = raw_data[0]

    if actual_type != expected_type:
        raise ValueError(
            f"Unexpected account type: "
            f"expected {expected_type}, got {actual_type}"
        )


def decode_board(
    account_info: dict[str, Any],
) -> BoardState:
    """Decode the ORE Board account."""

    raw_data = decode_account_data(
        account_info
    )

    validate_account_type(
        raw_data,
        BOARD_ACCOUNT_TYPE,
    )

    body = raw_data[
        ACCOUNT_HEADER_SIZE:
    ]

    if len(body) < 32:
        raise ValueError(
            "Board account body is too short."
        )

    (
        round_id,
        start_slot,
        end_slot,
        production_cost_ema,
    ) = struct.unpack_from(
        "<QQQQ",
        body,
        0,
    )

    return BoardState(
        round_id=round_id,
        start_slot=start_slot,
        end_slot=end_slot,
        production_cost_ema=production_cost_ema,
    )


def decode_treasury(
    account_info: dict[str, Any],
) -> TreasuryState:
    """
    Decode the verified leading field
    of the ORE Treasury account.
    """

    raw_data = decode_account_data(
        account_info
    )

    validate_account_type(
        raw_data,
        TREASURY_ACCOUNT_TYPE,
    )

    body = raw_data[
        ACCOUNT_HEADER_SIZE:
    ]

    if len(body) < 8:
        raise ValueError(
            "Treasury account body is too short."
        )

    motherlode = struct.unpack_from(
        "<Q",
        body,
        0,
    )[0]

    return TreasuryState(
        motherlode=motherlode,
    )


def derive_round_address(
    round_id: int,
) -> Pubkey:
    """Derive the PDA for an ORE round."""

    round_id_bytes = round_id.to_bytes(
        8,
        byteorder="little",
        signed=False,
    )

    address, _bump = Pubkey.find_program_address(
        [
            b"round",
            round_id_bytes,
        ],
        ORE_PROGRAM_ID,
    )

    return address


def decode_round(
    account_info: dict[str, Any],
) -> RoundState:
    """Decode the full current ORE Round account."""

    raw_data = decode_account_data(
        account_info
    )

    validate_account_type(
        raw_data,
        ROUND_ACCOUNT_TYPE,
    )

    body = raw_data[
        ACCOUNT_HEADER_SIZE:
    ]

    offset = 0

    def read_u64() -> int:
        nonlocal offset

        value = struct.unpack_from(
            "<Q",
            body,
            offset,
        )[0]

        offset += 8

        return value

    def read_u64_array(
        length: int,
    ) -> list[int]:
        nonlocal offset

        values = list(
            struct.unpack_from(
                f"<{length}Q",
                body,
                offset,
            )
        )

        offset += length * 8

        return values

    round_id = read_u64()

    deployed = read_u64_array(25)

    mass = read_u64_array(25)

    miner_counts = read_u64_array(25)

    slot_hash = body[
        offset:offset + 32
    ]
    offset += 32

    expires_at = read_u64()

    motherlode = read_u64()

    # rent_payer
    offset += 32

    rewards = read_u64_array(25)

    total_vaulted = read_u64()

    total_winnings = read_u64()

    total_miners = read_u64()

    top_miner_bytes = body[
        offset:offset + 32
    ]
    offset += 32

    top_miner = str(
        Pubkey.from_bytes(
            top_miner_bytes
        )
    )

    entropy = None

    if slot_hash not in (
        bytes(32),
        bytes([255]) * 32,
    ):
        r1, r2, r3, r4 = struct.unpack(
            "<QQQQ",
            slot_hash,
        )

        entropy = (
            r1
            ^ r2
            ^ r3
            ^ r4
        )

    return RoundState(
        round_id=round_id,
        deployed_lamports=deployed,
        mass=mass,
        miner_counts=miner_counts,
        slot_hash_hex=slot_hash.hex(),
        expires_at=expires_at,
        motherlode=motherlode,
        rewards=rewards,
        total_vaulted=total_vaulted,
        total_winnings=total_winnings,
        total_miners=total_miners,
        top_miner=top_miner,
        entropy=entropy,
    )
