from __future__ import annotations

from typing import Any, Protocol

from orev3.ledger.schemas import RpcTransactionObservation
from orev3.ledger.validation import (
    assert_observational_only,
    validate_transaction_signature,
)


class RpcReader(Protocol):
    def _rpc(self, method: str, params: list[Any] | None = None) -> Any: ...


ALLOWED_RPC_METHODS = frozenset(
    {
        "getTransaction",
        "getSignatureStatuses",
        "getBalance",
        "getTokenAccountBalance",
    }
)


class ReadOnlyRpcObserver:
    def __init__(self, rpc: RpcReader) -> None:
        self.rpc = rpc

    def call(self, method: str, params: list[Any]) -> Any:
        assert_observational_only()
        if method not in ALLOWED_RPC_METHODS:
            raise PermissionError(f"RPC method is not read-only approved: {method}")
        return self.rpc._rpc(method, params)

    def transaction(self, signature: str) -> RpcTransactionObservation:
        validate_transaction_signature(signature)
        result = self.call(
            "getTransaction",
            [
                signature,
                {
                    "commitment": "confirmed",
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
        )
        return parse_transaction_response(signature, result)


def _account_keys(transaction: dict[str, Any]) -> list[str]:
    keys = transaction.get("message", {}).get("accountKeys", [])
    return [
        str(item.get("pubkey")) if isinstance(item, dict) else str(item)
        for item in keys
    ]


def parse_transaction_response(
    signature: str,
    result: dict[str, Any] | None,
    *,
    ore_program_id: str | None = None,
    protocol_success_markers: tuple[str, ...] = ("Program log: Instruction: Mine",),
) -> RpcTransactionObservation:
    validate_transaction_signature(signature)
    if result is None:
        return RpcTransactionObservation(
            transaction_signature=signature,
            protocol_status="missing",
        )
    meta = result.get("meta") or {}
    transaction = result.get("transaction") or {}
    message = transaction.get("message") or {}
    keys = _account_keys(transaction)
    instructions = message.get("instructions") or []
    program_ids: list[str] = []
    instruction_types: list[str] = []
    for instruction in instructions:
        if not isinstance(instruction, dict):
            continue
        program = instruction.get("programId")
        if program is not None:
            program_ids.append(str(program))
        parsed = instruction.get("parsed")
        if isinstance(parsed, dict) and parsed.get("type") is not None:
            instruction_types.append(str(parsed["type"]))
    logs = [str(value) for value in (meta.get("logMessages") or [])]
    transaction_error = meta.get("err")
    if transaction_error is not None:
        protocol_status = "failed"
    elif ore_program_id and ore_program_id not in program_ids:
        protocol_status = "confirmed_protocol_failure"
    elif ore_program_id and not any(
        marker in line for marker in protocol_success_markers for line in logs
    ):
        protocol_status = "confirmed_protocol_failure"
    else:
        protocol_status = "confirmed_success"
    total_fee = meta.get("fee")
    priority_fee = meta.get("priorityFee")
    return RpcTransactionObservation(
        transaction_signature=signature,
        slot=result.get("slot"),
        block_time=result.get("blockTime"),
        confirmation_status=result.get("confirmationStatus") or "confirmed",
        transaction_error=transaction_error,
        protocol_status=protocol_status,
        fee_payer=keys[0] if keys else None,
        total_fee_lamports=total_fee,
        priority_fee_lamports=priority_fee,
        pre_sol_balances=[int(value) for value in meta.get("preBalances", [])],
        post_sol_balances=[int(value) for value in meta.get("postBalances", [])],
        pre_token_balances=list(meta.get("preTokenBalances") or []),
        post_token_balances=list(meta.get("postTokenBalances") or []),
        program_ids=sorted(set(program_ids)),
        instruction_types=instruction_types,
        logs=logs,
        account_keys=keys,
    )
