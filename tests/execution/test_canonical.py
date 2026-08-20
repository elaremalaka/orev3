from __future__ import annotations

from pathlib import Path

import pytest

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    parse_canonical_bytes,
    validate_json_schema_instance,
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


def _validate_schema(
    instance: object,
    schema: object,
    *,
    schema_registry: dict[str, object] | None = None,
) -> None:
    validate_json_schema_instance(
        instance,
        schema,  # type: ignore[arg-type]
        schema_registry=schema_registry or {},  # type: ignore[arg-type]
    )


def test_all_of_combines_every_branch() -> None:
    schema = {
        "allOf": [
            {"type": "integer", "minimum": 1},
            {"type": "integer", "maximum": 3},
        ]
    }
    for value in (1, 2, 3):
        _validate_schema(value, schema)
    for value in (0, 4, "2"):
        with pytest.raises(CanonicalControlError):
            _validate_schema(value, schema)


def test_if_then_matches_fails_and_skips_deterministically() -> None:
    schema = {
        "type": "object",
        "properties": {
            "kind": {"enum": ["governed", "other"]},
            "value": {"type": "integer"},
        },
        "required": ["kind", "value"],
        "additionalProperties": False,
        "if": {
            "properties": {"kind": {"const": "governed"}},
            "required": ["kind"],
        },
        "then": {"properties": {"value": {"minimum": 1}}},
    }
    _validate_schema({"kind": "governed", "value": 1}, schema)
    _validate_schema({"kind": "other", "value": 0}, schema)
    with pytest.raises(CanonicalControlError):
        _validate_schema({"kind": "governed", "value": 0}, schema)


@pytest.mark.parametrize(
    "predicate",
    (
        {"not": {}},
        [],
    ),
)
def test_invalid_schema_nested_under_if_fails_closed(predicate: object) -> None:
    with pytest.raises(CanonicalControlError):
        _validate_schema(
            {"kind": "other"},
            {"if": predicate, "then": {"const": {"kind": "governed"}}},
        )


def test_prefix_items_and_items_apply_at_exact_positions() -> None:
    schema = {
        "type": "array",
        "prefixItems": [{"const": "head"}, {"type": "integer"}],
        "items": {"type": "boolean"},
    }
    for value in ([], ["head"], ["head", 1], ["head", 1, True, False]):
        _validate_schema(value, schema)
    for value in (["wrong"], ["head", "1"], ["head", 1, 0]):
        with pytest.raises(CanonicalControlError):
            _validate_schema(value, schema)


def test_contains_and_containment_bounds_are_enforced() -> None:
    one_or_more = {"type": "array", "contains": {"const": "match"}}
    with pytest.raises(CanonicalControlError):
        _validate_schema(["other"], one_or_more)
    _validate_schema(["match"], one_or_more)
    _validate_schema(["match", "match"], one_or_more)

    bounded = {
        "type": "array",
        "contains": {"const": "match"},
        "minContains": 1,
        "maxContains": 2,
    }
    _validate_schema(["match"], bounded)
    _validate_schema(["match", "match"], bounded)
    for value in (["other"], ["match", "match", "match"]):
        with pytest.raises(CanonicalControlError):
            _validate_schema(value, bounded)

    _validate_schema(["other"], {**bounded, "minContains": 0, "maxContains": 0})


@pytest.mark.parametrize(
    "schema",
    (
        {"contains": {"const": 1}, "minContains": -1},
        {"contains": {"const": 1}, "maxContains": -1},
    ),
)
def test_malformed_containment_bounds_fail_closed(schema: dict[str, object]) -> None:
    with pytest.raises(CanonicalControlError):
        _validate_schema([1], schema)


def test_unsatisfiable_containment_bounds_are_an_instance_mismatch() -> None:
    schema = {"contains": {"const": 1}, "minContains": 2, "maxContains": 1}
    with pytest.raises(CanonicalControlError):
        _validate_schema([1, 1], schema)

    _validate_schema(
        [1, 1],
        {"if": schema, "then": {"const": []}},
    )


def test_one_of_preserves_exactly_one_instance_match() -> None:
    schema = {"oneOf": [{"const": "one"}, {"const": "two"}]}
    _validate_schema("one", schema)
    with pytest.raises(CanonicalControlError):
        _validate_schema("neither", schema)
    with pytest.raises(CanonicalControlError):
        _validate_schema(1, {"oneOf": [{"type": "integer"}, {"const": 1}]})


def test_object_properties_and_array_uniqueness_remain_enforced() -> None:
    object_schema = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    _validate_schema({"value": 1}, object_schema)
    for invalid in ({}, {"value": "1"}, {"value": 1, "extra": True}):
        with pytest.raises(CanonicalControlError):
            _validate_schema(invalid, object_schema)

    _validate_schema([1, 2], {"type": "array", "uniqueItems": True})
    with pytest.raises(CanonicalControlError):
        _validate_schema([1, 1], {"type": "array", "uniqueItems": True})


@pytest.mark.parametrize(
    "schema",
    (
        {"enum": "abc"},
        {"if": {"enum": "abc"}, "then": {"const": "unused"}},
        {"oneOf": [{"const": "value"}, {"enum": "abc"}]},
        {"contains": {"enum": "abc"}, "minContains": 0},
    ),
)
def test_malformed_enum_fails_closed_in_every_branch(schema: object) -> None:
    with pytest.raises(CanonicalControlError):
        _validate_schema("value", schema)


@pytest.mark.parametrize(
    "schema",
    (
        {"uniqueItems": "yes"},
        {"if": {"uniqueItems": "yes"}, "then": {"const": []}},
        {"additionalProperties": "no"},
        {
            "if": {"additionalProperties": "no"},
            "then": {"const": {}},
        },
    ),
)
def test_boolean_schema_keywords_reject_non_boolean_values(schema: object) -> None:
    with pytest.raises(CanonicalControlError):
        _validate_schema([], schema)


def test_schema_validity_is_independent_of_instance_branch_selection() -> None:
    malformed = {"enum": "abc"}
    schemas = (
        {"if": {"const": "match"}, "then": malformed},
        {"oneOf": [{"const": "value"}, malformed]},
        {"contains": malformed, "minContains": 0},
        {
            "type": "object",
            "properties": {"absent": malformed},
            "additionalProperties": True,
        },
        {"$defs": {"unused": malformed}, "const": "value"},
    )
    for schema in schemas:
        with pytest.raises(CanonicalControlError):
            _validate_schema("value", schema)


@pytest.mark.parametrize(
    "schema",
    (
        {"$schema": "https://example.invalid/schema"},
        {"$id": ""},
        {"type": ["string", "integer"]},
        {"type": "number"},
        {"required": "value"},
        {"required": ["value", "value"]},
        {"properties": []},
        {"pattern": 1},
        {"pattern": "["},
        {"minimum": True},
        {"maximum": "1"},
        {"minLength": -1},
        {"maxLength": True},
        {"minItems": -1},
        {"maxItems": True},
        {"items": True},
        {"items": "schema"},
        {"prefixItems": {}},
        {"prefixItems": [{"enum": "abc"}]},
        {"oneOf": []},
        {"oneOf": "schemas"},
        {"allOf": []},
        {"allOf": "schemas"},
        {"if": "schema"},
        {"then": "schema"},
        {"contains": "schema"},
        {"minContains": -1},
        {"minContains": True},
        {"maxContains": -1},
        {"maxContains": True},
    ),
)
def test_supported_keywords_reject_malformed_schema_values(schema: object) -> None:
    with pytest.raises(CanonicalControlError):
        _validate_schema({}, schema)


@pytest.mark.parametrize(
    "schema",
    (
        {"$ref": 1},
        {"$ref": "#/missing"},
        {"$ref": "missing"},
        {"$ref": "target", "type": "string"},
    ),
)
def test_malformed_or_unresolved_schema_references_fail_closed(
    schema: object,
) -> None:
    with pytest.raises(CanonicalControlError):
        _validate_schema("value", schema)


def test_resolved_schema_references_are_recursively_preflighted() -> None:
    _validate_schema(
        "value",
        {"$ref": "target"},
        schema_registry={"target": {"const": "value"}},
    )
    with pytest.raises(CanonicalControlError):
        _validate_schema(
            "value",
            {"$ref": "target"},
            schema_registry={"target": {"enum": "abc"}},
        )
