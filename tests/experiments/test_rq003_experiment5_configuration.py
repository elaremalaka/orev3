from __future__ import annotations

import copy
from pathlib import Path

import pytest

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    parse_json,
    validate_json_schema_instance,
)
from orev3.execution.phase3b_components import (
    execute_controller_pure_configuration_validation,
    reconstruct_experiment5_configuration_identity,
    reconstruct_profiled_experiment_configuration_identity,
    reconstruct_research_specification_profile_identity,
    rq003_canonical_encode,
)
from orev3.features.rq003_contracts import canonical_encode


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = parse_json(
    (ROOT / "src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json").read_bytes()
)


def _instance(schema: dict, root: dict) -> object:
    if "const" in schema:
        return copy.deepcopy(schema["const"])
    if "$ref" in schema:
        return _instance(root["$defs"][schema["$ref"].rsplit("/", 1)[1]], root)
    if schema.get("type") == "object":
        return {name: _instance(child, root) for name, child in schema["properties"].items()}
    if schema.get("pattern", "").endswith("{64}$"):
        return "a" * 64
    if "40}" in schema.get("pattern", ""):
        return "b" * 40
    raise AssertionError(schema)


def valid_configuration() -> dict:
    value = _instance(SCHEMA, SCHEMA)
    assert isinstance(value, dict)
    value["source_processing"]["configuration_git_blob_identity"] = "b" * 40
    value["execution_profile"]["research_specification_profile_identity"] = (
        reconstruct_research_specification_profile_identity("outcome_aware_v1")
    )
    value["configuration_identity"] = reconstruct_experiment5_configuration_identity(value)
    return value


def test_complete_configuration_schema_and_identity() -> None:
    material = valid_configuration()
    validate_json_schema_instance(material, SCHEMA, schema_registry={})
    assert reconstruct_experiment5_configuration_identity(material) == material["configuration_identity"]
    result = execute_controller_pure_configuration_validation(
        configuration_bytes=canonical_bytes(material), configuration_schema=SCHEMA
    )
    expected_profile = reconstruct_research_specification_profile_identity("outcome_aware_v1")
    assert result["research_specification_profile_identity"] == expected_profile
    assert result["profiled_experiment_configuration_identity"] == reconstruct_profiled_experiment_configuration_identity(
        experiment_specific_configuration_identity=material["configuration_identity"],
        profile_identity=expected_profile,
    )


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        ("protocol", "protocol_revision", "wrong"),
        ("decision_selection", "boundary", "wrong"),
        ("numeric_contract", "reported_arithmetic", "wrong"),
        ("bootstrap", "replicate_count", 9999),
        ("confirmation", "stopping_rule", "wrong"),
    ],
)
def test_closed_configuration_rejects_frozen_literal_mutations(
    section: str, field: str, replacement: object
) -> None:
    material = valid_configuration()
    material[section][field] = replacement
    material["configuration_identity"] = reconstruct_experiment5_configuration_identity(material)
    with pytest.raises(CanonicalControlError):
        validate_json_schema_instance(material, SCHEMA, schema_registry={})


@pytest.mark.parametrize(
    "value",
    [None, False, True, 0, -12, 1.25, "é", [], [1, {"z": False}], {}, {"z": 1, "a": [None]}],
)
def test_limited_rq003_encoder_has_exact_oracle_parity(value: object) -> None:
    assert rq003_canonical_encode(value) == canonical_encode(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: "bad"}, object()])
def test_limited_rq003_encoder_rejects_unsupported_values(value: object) -> None:
    with pytest.raises((CanonicalControlError, TypeError, ValueError)):
        rq003_canonical_encode(value)
