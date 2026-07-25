from __future__ import annotations

from pathlib import Path

from orev3.ledger.transaction_observation import ALLOWED_RPC_METHODS


def test_generated_ledger_paths_are_ignored() -> None:
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "data/ledger/" in ignore
    assert "participant_ledger_v*.sqlite" in ignore
    assert "participant_*_v*.csv" in ignore
    assert "participant_*_v*.json" in ignore


def test_rpc_allowlist_contains_no_mutating_methods() -> None:
    assert ALLOWED_RPC_METHODS == {
        "getTransaction",
        "getSignatureStatuses",
        "getBalance",
        "getTokenAccountBalance",
    }
    assert ALLOWED_RPC_METHODS.isdisjoint(
        {"sendTransaction", "requestAirdrop", "simulateTransaction"}
    )


def test_ledger_package_has_no_private_key_or_submission_imports() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/orev3/ledger").glob("*.py")
    )
    assert "from solders.keypair" not in text
    assert "send_transaction(" not in text
    assert "sendTransaction" not in text
