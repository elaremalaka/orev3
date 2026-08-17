from __future__ import annotations

from pathlib import Path

import pytest

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    parse_canonical_bytes,
    validate_repository_path,
)


GOLDEN = Path(__file__).parent / "golden/readiness_v1"


def test_golden_canonical_bytes_and_identity() -> None:
    raw = (GOLDEN / "canonical-accepted.json").read_bytes()
    value = parse_canonical_bytes(raw)

    assert value == {"a": "é", "b": [1, True]}
    assert canonical_bytes(value) == raw
    assert domain_identity("orev3:test:v1\n", value) == (
        "3e30867215ddcebad39c418e66ae3c8d15a65553dcb2d65b2376cbe4eb3653a8"
    )


@pytest.mark.parametrize(
    "name",
    ("canonical-invalid-null.json", "canonical-invalid-float.json"),
)
def test_golden_invalid_scalars_fail_closed(name: str) -> None:
    with pytest.raises(CanonicalControlError):
        parse_canonical_bytes((GOLDEN / name).read_bytes())


@pytest.mark.parametrize(
    "raw",
    (
        b'{"a":1,"a":2}\n',
        b'{"a":1 }\n',
        b'{"a":1}\n\n',
        b'{"value":1e0}\n',
        b'\xef\xbb\xbf{"a":1}\n',
        '{"e\u0301":1}\n'.encode("utf-8"),
    ),
)
def test_noncanonical_or_ambiguous_json_is_rejected(raw: bytes) -> None:
    with pytest.raises(CanonicalControlError):
        parse_canonical_bytes(raw)


def test_exact_string_escaping() -> None:
    assert canonical_bytes({"value": '"\\\b\t\n\f\r\x01/'}) == (
        b'{"value":"\\"\\\\\\b\\t\\n\\f\\r\\u0001/"}\n'
    )


@pytest.mark.parametrize(
    "path",
    ("/absolute", "a/../b", "a/./b", "a//b", "a\\b", "a\x00b"),
)
def test_repository_path_rejects_noncanonical_forms(path: str) -> None:
    with pytest.raises(CanonicalControlError):
        validate_repository_path(path)
