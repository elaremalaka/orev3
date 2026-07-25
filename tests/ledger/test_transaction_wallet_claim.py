from __future__ import annotations

from datetime import timedelta

import pytest

from orev3.ledger.claim_attribution import attribute_claim
from orev3.ledger.schemas import Provenance, WalletSnapshot
from orev3.ledger.reward_observation import observe_total_only_ore
from orev3.ledger.transaction_observation import parse_transaction_response
from orev3.ledger.wallet_snapshots import calculate_wallet_delta

from .conftest import NOW, SIGNATURE, WALLET


def rpc_result(*, error=None, logs=None) -> dict:
    return {
        "slot": 100,
        "blockTime": 1,
        "meta": {
            "err": error,
            "fee": 5000,
            "priorityFee": 100,
            "preBalances": [10000, 0],
            "postBalances": [4000, 1000],
            "preTokenBalances": [],
            "postTokenBalances": [{"mint": "mint", "uiTokenAmount": {"amount": "2"}}],
            "logMessages": logs or ["Program log: Instruction: Mine"],
        },
        "transaction": {
            "message": {
                "accountKeys": [{"pubkey": WALLET}, {"pubkey": "program"}],
                "instructions": [
                    {"programId": "ore", "parsed": {"type": "mine"}}
                ],
            }
        },
    }


def test_transaction_success_fee_and_balance_extraction() -> None:
    value = parse_transaction_response(
        SIGNATURE, rpc_result(), ore_program_id="ore"
    )
    assert value.protocol_status == "confirmed_success"
    assert value.total_fee_lamports == 5000
    assert value.priority_fee_lamports == 100
    assert value.pre_sol_balances == [10000, 0]
    assert value.post_token_balances[0]["mint"] == "mint"


def test_confirmed_protocol_failure_rpc_failure_and_missing_metadata() -> None:
    protocol = parse_transaction_response(
        SIGNATURE,
        rpc_result(logs=["Program log: unrelated"]),
        ore_program_id="ore",
    )
    failed = parse_transaction_response(
        SIGNATURE, rpc_result(error={"InstructionError": [0, "Custom"]})
    )
    missing = parse_transaction_response(SIGNATURE, None)
    sparse = parse_transaction_response(
        SIGNATURE, {"transaction": {"message": {"accountKeys": []}}}
    )
    assert protocol.protocol_status == "confirmed_protocol_failure"
    assert failed.protocol_status == "failed"
    assert missing.protocol_status == "missing"
    assert sparse.total_fee_lamports is None


def snapshots(delta: int, ore_delta: int = 0) -> tuple[WalletSnapshot, WalletSnapshot]:
    before = WalletSnapshot(
        wallet_public_key=WALLET,
        snapshot_time=NOW,
        sol_balance_lamports=1_000_000_000,
        ore_token_balance_raw=10,
        source="fixture",
        commitment="confirmed",
    )
    after = WalletSnapshot(
        wallet_public_key=WALLET,
        snapshot_time=NOW + timedelta(seconds=1),
        sol_balance_lamports=before.sol_balance_lamports + delta,
        ore_token_balance_raw=10 + ore_delta,
        source="fixture",
        commitment="confirmed",
    )
    return before, after


def test_wallet_known_deployment_reward_and_fee() -> None:
    before, after = snapshots(-105)
    deployment = calculate_wallet_delta(
        before, after, known_deployment_lamports=100, known_fee_lamports=5
    )
    assert deployment.classification == "deployment"
    before, after = snapshots(95)
    reward = calculate_wallet_delta(
        before, after, known_return_lamports=100, known_fee_lamports=5
    )
    assert reward.classification == "reward"


def test_wallet_external_funding_withdrawal_transfer_and_ambiguity() -> None:
    before, after = snapshots(1000)
    funding = calculate_wallet_delta(
        before, after, external_funding_threshold_lamports=500
    )
    assert funding.classification == "external_funding"
    assert funding.mining_attributed_sol_delta_lamports == 0
    before, after = snapshots(-10)
    assert calculate_wallet_delta(before, after).classification == "withdrawal"
    before, after = snapshots(10)
    transfer = calculate_wallet_delta(
        before, after, unrelated_transfer_evidence=True
    )
    assert transfer.classification == "unrelated_transfer"
    ambiguous = calculate_wallet_delta(
        before, after, external_funding_threshold_lamports=100
    )
    assert ambiguous.classification == "ambiguous"
    assert ambiguous.manual_review


@pytest.mark.parametrize(
    ("method", "expected_confidence"),
    [
        ("direct", "high"),
        ("balance_difference", "medium"),
        ("fifo", "low"),
        ("proportional", "low"),
    ],
)
def test_claim_attribution_methods(method: str, expected_confidence: str) -> None:
    claim = attribute_claim(
        claim_signature=SIGNATURE,
        wallet_public_key=WALLET,
        claim_time=NOW,
        claimed_ore_raw=10,
        claim_fee_lamports=5,
        pending_rewards=[("one", 4), ("two", 6)],
        method=method,
        direct_opportunity_ids=["one", "two"],
    )
    assert claim.unattributed_ore_raw == 0
    assert claim.attribution_confidence == expected_confidence


def test_partial_and_unattributed_claim() -> None:
    partial = attribute_claim(
        claim_signature=SIGNATURE,
        wallet_public_key=WALLET,
        claim_time=NOW,
        claimed_ore_raw=10,
        claim_fee_lamports=5,
        pending_rewards=[("one", 4)],
        method="fifo",
    )
    unattributed = attribute_claim(
        claim_signature=SIGNATURE,
        wallet_public_key=WALLET,
        claim_time=NOW,
        claimed_ore_raw=10,
        claim_fee_lamports=5,
        pending_rewards=[],
        method="unattributed",
    )
    assert partial.unattributed_ore_raw == 6
    assert unattributed.unattributed_ore_raw == 10


def test_base_motherlode_and_total_only_reward_semantics() -> None:
    from orev3.ledger.schemas import RewardRecord

    decomposed = RewardRecord(
        opportunity_id="one",
        round_id=1,
        base_ore_raw=4,
        motherlode_ore_raw=6,
        total_ore_raw=10,
        reward_time=NOW,
        provenance=Provenance.DIRECT_PROGRAM_EVENT,
    )
    total_only = observe_total_only_ore(
        opportunity_id="two",
        round_id=1,
        wallet_public_key=None,
        total_ore_raw=10,
        reward_time=NOW,
        provenance=Provenance.DIRECT_WALLET_OBSERVATION,
    )
    assert decomposed.total_ore_raw == 10
    assert total_only.base_ore_raw is None
    assert total_only.motherlode_ore_raw is None
