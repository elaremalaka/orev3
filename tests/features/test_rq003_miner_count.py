from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import orev3.features.rq003_miner_count as measurement_module
from orev3.features import (
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    MINER_COUNT_DEFINITION,
    MINER_COUNT_DEPENDENCY_IDENTITY,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
    MINER_COUNT_FEATURE_GROUP,
    MINER_COUNT_FEATURE_NAME,
    MINER_COUNT_IMPLEMENTATION_IDENTITY,
    MINER_COUNT_MEASUREMENT,
    MINER_COUNT_METADATA,
    MINER_COUNT_OUTPUT_NAME,
    MINER_COUNT_PROTOCOL_DEPENDENCIES,
    MINER_COUNT_PROTOCOL_SOURCE_REVISION,
    MINER_COUNT_REVISION_DEPENDENCIES,
    MINER_COUNT_SOURCE_PATH,
    EligibilityCatalog,
    FeatureEligibilityStatus,
    FeatureOutputField,
    FeaturePipeline,
    FeatureRegistry,
    FrozenFeatureRegistry,
    canonical_encode,
    reconstruct_executable_binding_identity,
    reconstruct_miner_count_dependency_identity,
    reconstruct_miner_count_implementation_identity,
    validate_miner_count_definition,
)
from orev3.features.context import FeatureContext
from orev3.features.types import BoardSnapshot, SquareSnapshot


def make_context(
    miner_count: int,
    *,
    square_index: int = 7,
    historical_miner_count: int | None = None,
) -> FeatureContext:
    current_squares = tuple(
        SquareSnapshot(
            observation_index=1,
            miner_count=(
                miner_count if index == square_index else index + 1
            ),
            deployed_lamports=(index + 1) * 1_000,
            reward_raw=900 + index,
            mass=0,
        )
        for index in range(25)
    )
    history = ()
    if historical_miner_count is not None:
        history = (
            SquareSnapshot(
                observation_index=0,
                miner_count=historical_miner_count,
                deployed_lamports=999_999,
                reward_raw=999,
                mass=0,
            ),
        )
    return FeatureContext(
        board=BoardSnapshot(
            round_id=1234,
            observation_index=1,
            observation_count=8,
            slots_remaining=17,
            squares=current_squares,
        ),
        square_index=square_index,
        square_history=history + (current_squares[square_index],),
    )


def test_metadata_is_immutable_atomic_and_context_direct() -> None:
    metadata = MINER_COUNT_METADATA

    assert metadata.feature_name == "per_square_miner_count"
    assert metadata.feature_group == "raw_current_state"
    assert metadata.input_fields == ("round.miner_counts",)
    assert metadata.history_policy.mode == "current_observation_only"
    assert metadata.history_policy.maximum_history_length == 1
    assert metadata.output_fields == (
        FeatureOutputField(
            name="miner_count",
            scalar_type="integer",
            nullable=False,
            semantic_unit="miner_authority_count",
            candidate_scope="per_square",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    )
    with pytest.raises(FrozenInstanceError):
        metadata.feature_name = "replacement"  # type: ignore[misc]


def test_computation_returns_only_the_exact_protocol_published_value() -> None:
    context = make_context(314, historical_miner_count=271)

    output = MINER_COUNT_MEASUREMENT.compute(context)

    assert dict(output) == {"miner_count": 314}
    assert tuple(output) == ("miner_count",)
    with pytest.raises(TypeError):
        output["miner_count"] = 1  # type: ignore[index]


def test_history_and_square_position_do_not_change_the_observed_value() -> None:
    first = MINER_COUNT_MEASUREMENT.compute(
        make_context(99, square_index=1, historical_miner_count=0)
    )
    second = MINER_COUNT_MEASUREMENT.compute(
        make_context(
            99,
            square_index=23,
            historical_miner_count=(1 << 64) - 1,
        )
    )

    assert first == second == {"miner_count": 99}


@pytest.mark.parametrize("value", (0, (1 << 64) - 1))
def test_computation_accepts_protocol_u64_boundaries(value: int) -> None:
    assert MINER_COUNT_MEASUREMENT.compute(make_context(value)) == {
        "miner_count": value
    }


def test_existing_pipeline_executes_only_the_single_measurement() -> None:
    registry = FeatureRegistry((MINER_COUNT_MEASUREMENT,))
    pipeline = FeaturePipeline(registry)

    assert registry.output_columns == ("miner_count",)
    assert pipeline.compute(make_context(42)) == {"miner_count": 42}


@pytest.mark.parametrize(
    "invalid_value",
    (-1, True, 1 << 64, 1.5, "1"),
)
def test_computation_fails_closed_on_non_protocol_integer_values(
    invalid_value: object,
) -> None:
    context = make_context(invalid_value)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="unsigned 64-bit integer"):
        MINER_COUNT_MEASUREMENT.compute(context)


def test_canonical_output_round_trips_without_interpretation() -> None:
    raw = MINER_COUNT_MEASUREMENT.canonical_output(make_context(12_345))
    reconstructed = MINER_COUNT_MEASUREMENT.reconstruct_canonical_output(raw)

    assert raw == canonical_encode({"miner_count": 12_345})
    assert dict(reconstructed) == {"miner_count": 12_345}
    with pytest.raises(TypeError):
        reconstructed["miner_count"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "invalid_output",
    (
        {"other": 1},
        {"miner_count": -1},
        {"miner_count": True},
        {"miner_count": 1 << 64},
    ),
)
def test_canonical_output_reconstruction_fails_closed(
    invalid_output: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        MINER_COUNT_MEASUREMENT.reconstruct_canonical_output(
            canonical_encode(invalid_output)
        )


def test_all_measurement_identities_reconstruct() -> None:
    validate_miner_count_definition()

    assert (
        reconstruct_miner_count_dependency_identity()
        == MINER_COUNT_DEPENDENCY_IDENTITY
    )
    assert (
        reconstruct_miner_count_implementation_identity()
        == MINER_COUNT_IMPLEMENTATION_IDENTITY
    )
    assert (
        MINER_COUNT_METADATA.reconstruct_semantic_identity()
        == MINER_COUNT_METADATA.semantic_identity
    )
    assert (
        MINER_COUNT_METADATA.reconstruct_definition_identity()
        == MINER_COUNT_METADATA.definition_identity
    )
    assert (
        reconstruct_executable_binding_identity(
            MINER_COUNT_METADATA,
            MINER_COUNT_ELIGIBILITY_DECISION,
        )
        == MINER_COUNT_EXECUTABLE_BINDING_IDENTITY
    )


def test_dependency_and_implementation_changes_are_identity_sensitive() -> None:
    protocol_variant = MINER_COUNT_PROTOCOL_DEPENDENCIES + (
        ("unexpected_protocol_dependency", "different"),
    )
    revision_variant = tuple(
        (
            key,
            "different" if key == "official_source_revision" else value,
        )
        for key, value in MINER_COUNT_REVISION_DEPENDENCIES
    )
    implementation_variant = (
        ("implementation_schema_version", 1),
        ("implementation", "different"),
    )

    assert reconstruct_miner_count_dependency_identity(
        protocol_variant,
        MINER_COUNT_REVISION_DEPENDENCIES,
    ) != MINER_COUNT_DEPENDENCY_IDENTITY
    assert reconstruct_miner_count_dependency_identity(
        MINER_COUNT_PROTOCOL_DEPENDENCIES,
        revision_variant,
    ) != MINER_COUNT_DEPENDENCY_IDENTITY
    assert reconstruct_miner_count_implementation_identity(
        implementation_variant
    ) != MINER_COUNT_IMPLEMENTATION_IDENTITY


def test_dependency_declarations_are_canonical_immutable_and_validated() -> None:
    assert dict(MINER_COUNT_PROTOCOL_DEPENDENCIES) == {
        "board_square_count": 25,
        "canonical_square_order": "zero_based_ascending_0_through_24",
        "source_path": MINER_COUNT_SOURCE_PATH,
        "source_scalar": "unsigned_64_bit_integer",
        "semantic_unit": "miner_authority_count",
        "measurement_scope": "one_square_at_frozen_normal_observation",
        "protocol_semantics": "distinct_miner_authorities_recorded_on_square",
    }
    assert dict(MINER_COUNT_REVISION_DEPENDENCIES) == {
        "official_source_revision": MINER_COUNT_PROTOCOL_SOURCE_REVISION,
        "cross_revision_reuse": (
            "requires_authoritative_semantic_compatibility_declaration"
        ),
        "revision_information_role": (
            "validation_and_population_control_only"
        ),
        "revision_feature_visibility": "prohibited",
    }
    with pytest.raises(TypeError, match="immutable tuple"):
        reconstruct_miner_count_dependency_identity(
            list(MINER_COUNT_PROTOCOL_DEPENDENCIES),  # type: ignore[arg-type]
            MINER_COUNT_REVISION_DEPENDENCIES,
        )
    with pytest.raises(ValueError, match="keys must be unique"):
        reconstruct_miner_count_dependency_identity(
            (("duplicate", "one"), ("duplicate", "two")),
            MINER_COUNT_REVISION_DEPENDENCIES,
        )


def test_exact_definition_is_eligible_for_ephemeral_registry_validation() -> None:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=(MINER_COUNT_ELIGIBILITY_DECISION,),
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=(MINER_COUNT_DEFINITION,),
    )

    assert MINER_COUNT_ELIGIBILITY_DECISION.status is (
        FeatureEligibilityStatus.APPROVED
    )
    assert registry.definitions == (MINER_COUNT_DEFINITION,)
    assert registry.ordered_executable_feature_identities == (
        MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
    )
    assert tuple(field.name for field in registry.ordered_output_fields) == (
        "miner_count",
    )


def test_canonical_definition_validator_rejects_dependency_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        measurement_module,
        "MINER_COUNT_DEPENDENCY_IDENTITY",
        "0" * 64,
    )

    with pytest.raises(ValueError, match="dependency identity mismatch"):
        validate_miner_count_definition()


def test_hash_seed_does_not_change_identity_or_canonical_output() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    script = """
import json
from orev3.features import (
    MINER_COUNT_DEPENDENCY_IDENTITY,
    MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
    MINER_COUNT_IMPLEMENTATION_IDENTITY,
    MINER_COUNT_MEASUREMENT,
    MINER_COUNT_METADATA,
)
from orev3.features.context import FeatureContext
from orev3.features.types import BoardSnapshot, SquareSnapshot
squares = tuple(
    SquareSnapshot(0, 777 if index == 4 else index, index, 0, 0)
    for index in range(25)
)
context = FeatureContext(
    BoardSnapshot(1, 0, 1, 10, squares),
    4,
    (squares[4],),
)
print(json.dumps({
    "canonical_output": MINER_COUNT_MEASUREMENT.canonical_output(context).hex(),
    "definition_identity": MINER_COUNT_METADATA.definition_identity,
    "dependency_identity": MINER_COUNT_DEPENDENCY_IDENTITY,
    "executable_identity": MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
    "implementation_identity": MINER_COUNT_IMPLEMENTATION_IDENTITY,
    "semantic_identity": MINER_COUNT_METADATA.semantic_identity,
}, sort_keys=True))
"""

    outputs = []
    for seed in ("1", "8675309"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(repository_root / "src")
        outputs.append(
            subprocess.check_output(
                [sys.executable, "-c", script],
                cwd=repository_root,
                env=environment,
                text=True,
            ).strip()
        )

    assert outputs[0] == outputs[1]
    assert json.loads(outputs[0])["canonical_output"]


def test_phase_scope_contains_only_the_fundamental_miner_count() -> None:
    public_names = set(measurement_module.__all__)
    prohibited_fragments = (
        "total_miners",
        "production_cost",
        "motherlode",
        "total_vaulted",
        "total_winnings",
        "deployment_share",
        "miner_share",
        "rank",
        "normalization",
        "history",
        "feature_set",
        "dataset",
        "baseline",
        "ranking",
    )

    assert MINER_COUNT_FEATURE_NAME in {
        MINER_COUNT_MEASUREMENT.name,
        MINER_COUNT_METADATA.feature_name,
    }
    assert MINER_COUNT_FEATURE_GROUP == "raw_current_state"
    assert MINER_COUNT_OUTPUT_NAME == "miner_count"
    assert not any(
        fragment in public_name.lower()
        for fragment in prohibited_fragments
        for public_name in public_names
    )
    assert not hasattr(MINER_COUNT_MEASUREMENT, "update")
    assert not hasattr(MINER_COUNT_MEASUREMENT, "rank")
    assert not hasattr(MINER_COUNT_MEASUREMENT, "select")


def test_protocol_revision_is_bound_to_metadata_not_visible_to_compute() -> None:
    assert MINER_COUNT_PROTOCOL_SOURCE_REVISION not in (
        MINER_COUNT_METADATA.input_fields
    )
    assert "protocol_revision" not in MINER_COUNT_METADATA.input_fields
    assert MINER_COUNT_METADATA.configuration_identity == (
        MINER_COUNT_DEPENDENCY_IDENTITY
    )
    assert MINER_COUNT_MEASUREMENT.compute(make_context(99)) == {
        "miner_count": 99
    }


def test_semantic_identity_changes_if_dependency_binding_changes() -> None:
    changed = replace(
        MINER_COUNT_METADATA,
        configuration_identity="f" * 64,
    )

    assert changed.semantic_identity != MINER_COUNT_METADATA.semantic_identity
    assert changed.definition_identity != MINER_COUNT_METADATA.definition_identity
