from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from orev3.rfc008.cli import command_burn_in, command_run
from orev3.rfc008.writer import DuplicateRFC008Writer, RFC008WriterLease


def test_collection_command_fails_before_io_without_authorization() -> None:
    args = argparse.Namespace(
        authorization="/does/not/exist.authorization",
        config="/does/not/exist",
        marker="/does/not/exist",
        expected_marker_sha256="0" * 64,
        expected_marker_sha256_file=None,
        ledger="/does/not/exist",
        recovery=False,
    )
    with pytest.raises(PermissionError, match="collection preflight"):
        command_run(args)


def test_single_writer_lease(tmp_path: Path) -> None:
    ledger = tmp_path / "rfc008.sqlite"
    first = RFC008WriterLease(ledger)
    second = RFC008WriterLease(ledger)
    first.acquire()
    try:
        with pytest.raises(DuplicateRFC008Writer):
            second.acquire()
    finally:
        first.release()


def test_rfc008_package_has_no_rpc_or_wallet_adapter() -> None:
    package = Path(__file__).parents[2] / "src/orev3/rfc008"
    names = {path.name for path in package.glob("*.py")}
    assert not {"rpc.py", "wallet.py", "transactions.py", "claims.py"} & names
    source = "\n".join(path.read_text() for path in package.glob("*.py"))
    assert "import httpx" not in source
    assert "from solders" not in source


def test_incomplete_burn_in_exits_nonzero_after_reporting(monkeypatch) -> None:
    monkeypatch.setattr(
        "orev3.rfc008.cli.run_resolver_burn_in",
        lambda **kwargs: {
            "passed": False,
            "mode": "operational",
            "primary_authoritative_capable": False,
        },
    )
    args = argparse.Namespace(
        ledger="burnin.sqlite",
        output="burnin.json",
        config="config.json",
        resolver_config="resolver.json",
        mode="operational",
        sample_size=5,
        control_round_id=None,
        authorization_token="authorized-for-test",
        release_approval="release.json",
        repository_root=".",
        preserve_pid=[],
    )
    with pytest.raises(SystemExit) as exc:
        command_burn_in(args)
    assert exc.value.code == 1
