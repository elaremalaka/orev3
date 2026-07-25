from __future__ import annotations

from orev3.ledger.schemas import WalletDeltaRecord, WalletSnapshot


def calculate_wallet_delta(
    before: WalletSnapshot,
    after: WalletSnapshot,
    *,
    known_deployment_lamports: int = 0,
    known_return_lamports: int = 0,
    known_fee_lamports: int = 0,
    known_claim_ore_raw: int = 0,
    external_funding_threshold_lamports: int = 100_000_000,
    transaction_signature: str | None = None,
    unrelated_transfer_evidence: bool = False,
) -> WalletDeltaRecord:
    if before.wallet_public_key != after.wallet_public_key:
        raise ValueError("Wallet snapshots must refer to the same wallet")
    if after.snapshot_time <= before.snapshot_time:
        raise ValueError("After snapshot must be later than before snapshot")
    sol_delta = after.sol_balance_lamports - before.sol_balance_lamports
    ore_delta = (
        None
        if before.ore_token_balance_raw is None or after.ore_token_balance_raw is None
        else after.ore_token_balance_raw - before.ore_token_balance_raw
    )
    expected = known_return_lamports - known_deployment_lamports - known_fee_lamports
    mining_delta: int | None = expected if any(
        (known_deployment_lamports, known_return_lamports, known_fee_lamports)
    ) else None
    manual = False
    if sol_delta == 0 and (ore_delta in {0, None}):
        classification, evidence = "no_change", "balances unchanged"
    elif unrelated_transfer_evidence:
        classification, evidence = "unrelated_transfer", "RPC counterparty is unrelated"
    elif mining_delta is not None and sol_delta == expected:
        if known_deployment_lamports and not known_return_lamports:
            classification = "deployment"
        elif known_return_lamports:
            classification = "reward"
        else:
            classification = "fee"
        evidence = "wallet delta exactly matches known mining components"
    elif known_claim_ore_raw and ore_delta == known_claim_ore_raw:
        classification, evidence = "claim", "ORE delta matches known claim"
    elif sol_delta >= external_funding_threshold_lamports:
        classification = "external_funding"
        evidence = "unexplained positive delta exceeds configured funding threshold"
        mining_delta = 0
    elif sol_delta < 0 and mining_delta is None:
        classification, evidence = "withdrawal", "unexplained negative wallet delta"
        mining_delta = 0
    else:
        classification = "ambiguous"
        evidence = "wallet delta is not uniquely explained by known records"
        manual = True
    return WalletDeltaRecord(
        wallet_public_key=before.wallet_public_key,
        before_time=before.snapshot_time,
        after_time=after.snapshot_time,
        raw_sol_delta_lamports=sol_delta,
        raw_ore_delta=ore_delta,
        mining_attributed_sol_delta_lamports=mining_delta,
        classification=classification,
        evidence=evidence,
        related_transaction_signature=transaction_signature,
        manual_review=manual,
    )
