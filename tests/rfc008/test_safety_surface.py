from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from orev3.rfc008.cli import command_run
from orev3.rfc008.writer import DuplicateRFC008Writer, RFC008WriterLease


def test_collection_command_fails_before_io_without_authorization() -> None:
    args = argparse.Namespace(
        authorization_token="not-authorized",
        config="/does/not/exist",
        marker="/does/not/exist",
        expected_marker_sha256="0" * 64,
        expected_marker_sha256_file=None,
        ledger="/does/not/exist",
        create_new_ledger=True,
    )
    with pytest.raises(PermissionError, match="collection authorization"):
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
