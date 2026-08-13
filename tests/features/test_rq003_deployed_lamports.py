from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import orev3.features.rq003_deployed_lamports as measurement_module
from orev3.features import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
    DEPLOYED_LAMPORTS_FEATURE_GROUP,
    DEPLOYED_LAMPORTS_FEATURE_NAME,
    DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    DEPLOYED_LAMPORTS_METADATA,
    DEPLOYED_LAMPORTS_OUTPUT_NAME,
    DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES,
    DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION,
    DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES,
    DEPLOYED_LAMPORTS_SOURCE_PATH,
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    EligibilityCatalog,
    FeatureEligibilityStatus,
    FeaturePipeline,
    FeatureRegistry,
    FrozenFeatureRegistry,
    canonical_encode,
    reconstruct_deployed_lamports_dependency_identity,
    reconstruct_deployed_lamports_implementation_identity,
    reconstruct_executable_binding_identity,
    validate_deployed_lamports_definition,
)
from orev3.features.context import FeatureContext
from orev3.features.types import BoardSnapshot, SquareSnapshot


def make_context(
    deployed_lamports: int,
    *,
    square_index: int = 7,
    historical_deployed_lamports: int | None = None,
) -> FeatureContext:
    current_squares = tuple(
        SquareSnapshot(
            observation_index=1,
            miner_count=index + 3,
            deployed_lamports=(
                deployed_lamports
                if index == square_index
                else (index + 1) * 10
            ),
            reward_raw=900 + index,
            mass=0,
        )
        for index in range(25)
    )
    history = ()
    if historical_deployed_lamports is not None:
        history = (
            SquareSnapshot(
                observation_index=0,
                miner_count=999,
                deployed_lamports=historical_deployed_lamports,
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
    metadata = DEPLOYED_LAMPORTS_METADATA

    assert metadata.feature_name == "per_square_deployed_lamports"
    assert metadata.feature_group == "raw_current_state"
    assert metadata.input_fields == ("round.deployed_lamports",)
    assert metadata.history_policy.mode == "current_observation_only"
    assert metadata.history_policy.maximum_history_length == 1
    assert metadata.output_fields == (
        measurement_module.FeatureOutputField(
            name="deployed_lamports",
            scalar_type="integer",
            nullable=False,
            semantic_unit="lamports",
            candidate_scope="per_square",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    )
    with pytest.raises(FrozenInstanceError):
        metadata.feature_name = "replacement"  # type: ignore[misc]


def test_computation_returns_only_the_exact_protocol_published_value() -> None:
    context = make_context(
        987_654_321,
        historical_deployed_lamports=123,
    )

    output = DEPLOYED_LAMPORTS_MEASUREMENT.compute(context)

    assert dict(output) == {"deployed_lamports": 987_654_321}
    assert tuple(output) == ("deployed_lamports",)
    with pytest.raises(TypeError):
        output["deployed_lamports"] = 1  # type: ignore[index]


@pytest.mark.parametrize("value", (0, (1 << 64) - 1))
def test_computation_accepts_protocol_u64_boundaries(value: int) -> None:
    assert DEPLOYED_LAMPORTS_MEASUREMENT.compute(make_context(value)) == {
        "deployed_lamports": value
    }


def test_existing_pipeline_executes_only_the_single_measurement() -> None:
    registry = FeatureRegistry((DEPLOYED_LAMPORTS_MEASUREMENT,))
    pipeline = FeaturePipeline(registry)

    assert registry.output_columns == ("deployed_lamports",)
    assert pipeline.compute(make_context(42)) == {"deployed_lamports": 42}


@pytest.mark.parametrize(
    "invalid_value",
    (-1, True, 1 << 64, 1.5, "1"),
)
def test_computation_fails_closed_on_non_protocol_integer_values(
    invalid_value: object,
) -> None:
    context = make_context(invalid_value)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError,
        match="unsigned 64-bit integer",
    ):
        DEPLOYED_LAMPORTS_MEASUREMENT.compute(context)


def test_canonical_output_round_trips_without_interpretation() -> None:
    raw = DEPLOYED_LAMPORTS_MEASUREMENT.canonical_output(
        make_context(12_345)
    )
    reconstructed = (
        DEPLOYED_LAMPORTS_MEASUREMENT.reconstruct_canonical_output(raw)
    )

    assert raw == canonical_encode({"deployed_lamports": 12_345})
    assert dict(reconstructed) == {"deployed_lamports": 12_345}
    with pytest.raises(TypeError):
        reconstructed["deployed_lamports"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "invalid_output",
    (
        {"other": 1},
        {"deployed_lamports": -1},
        {"deployed_lamports": True},
        {"deployed_lamports": 1 << 64},
    ),
)
def test_canonical_output_reconstruction_fails_closed(
    invalid_output: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        DEPLOYED_LAMPORTS_MEASUREMENT.reconstruct_canonical_output(
            canonical_encode(invalid_output)
        )


def test_all_measurement_identities_reconstruct() -> None:
    validate_deployed_lamports_definition()

    assert (
        reconstruct_deployed_lamports_dependency_identity()
        == DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY
    )
    assert (
        reconstruct_deployed_lamports_implementation_identity()
        == DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY
    )
    assert (
        DEPLOYED_LAMPORTS_METADATA.reconstruct_semantic_identity()
        == DEPLOYED_LAMPORTS_METADATA.semantic_identity
    )
    assert (
        DEPLOYED_LAMPORTS_METADATA.reconstruct_definition_identity()
        == DEPLOYED_LAMPORTS_METADATA.definition_identity
    )
    assert (
        reconstruct_executable_binding_identity(
            DEPLOYED_LAMPORTS_METADATA,
            DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        )
        == DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY
    )


def test_dependency_and_implementation_changes_are_identity_sensitive() -> None:
    protocol_variant = DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES + (
        ("unexpected_protocol_dependency", "different"),
    )
    revision_variant = tuple(
        (
            key,
            "different" if key == "official_source_revision" else value,
        )
        for key, value in DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES
    )
    implementation_variant = (
        ("implementation_schema_version", 1),
        ("implementation", "different"),
    )

    assert reconstruct_deployed_lamports_dependency_identity(
        protocol_variant,
        DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES,
    ) != DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY
    assert reconstruct_deployed_lamports_dependency_identity(
        DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES,
        revision_variant,
    ) != DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY
    assert reconstruct_deployed_lamports_implementation_identity(
        implementation_variant
    ) != DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY


def test_dependency_declarations_are_canonical_immutable_and_validated() -> None:
    assert dict(DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES) == {
        "board_square_count": 25,
        "canonical_square_order": "zero_based_ascending_0_through_24",
        "source_path": DEPLOYED_LAMPORTS_SOURCE_PATH,
        "source_scalar": "unsigned_64_bit_integer",
        "semantic_unit": "lamports",
        "measurement_scope": "one_square_at_frozen_normal_observation",
        "protocol_semantics": "aggregate_deployed_lamports_per_square",
    }
    assert dict(DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES) == {
        "official_source_revision": (
            DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION
        ),
        "cross_revision_reuse": (
            "requires_authoritative_semantic_compatibility_declaration"
        ),
        "revision_information_role": (
            "validation_and_population_control_only"
        ),
        "revision_feature_visibility": "prohibited",
    }
    with pytest.raises(TypeError, match="immutable tuple"):
        reconstruct_deployed_lamports_dependency_identity(
            list(DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES),  # type: ignore[arg-type]
            DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES,
        )
    with pytest.raises(ValueError, match="keys must be unique"):
        reconstruct_deployed_lamports_dependency_identity(
            (
                ("duplicate", "one"),
                ("duplicate", "two"),
            ),
            DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES,
        )


def test_exact_definition_is_eligible_for_ephemeral_registry_validation() -> None:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=(DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,),
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=(DEPLOYED_LAMPORTS_DEFINITION,),
    )

    assert DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION.status is (
        FeatureEligibilityStatus.APPROVED
    )
    assert registry.definitions == (DEPLOYED_LAMPORTS_DEFINITION,)
    assert registry.ordered_executable_feature_identities == (
        DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
    )
    assert tuple(field.name for field in registry.ordered_output_fields) == (
        "deployed_lamports",
    )


def test_canonical_definition_validator_rejects_dependency_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        measurement_module,
        "DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY",
        "0" * 64,
    )

    with pytest.raises(ValueError, match="dependency identity mismatch"):
        validate_deployed_lamports_definition()


def test_hash_seed_does_not_change_identity_or_canonical_output() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    script = """
import json
from orev3.features import (
    DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY,
    DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
    DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    DEPLOYED_LAMPORTS_METADATA,
)
from orev3.features.context import FeatureContext
from orev3.features.types import BoardSnapshot, SquareSnapshot
squares = tuple(
    SquareSnapshot(0, index, 777 if index == 4 else index, 0, 0)
    for index in range(25)
)
context = FeatureContext(
    BoardSnapshot(1, 0, 1, 10, squares),
    4,
    (squares[4],),
)
print(json.dumps({
    "canonical_output": DEPLOYED_LAMPORTS_MEASUREMENT.canonical_output(
        context
    ).hex(),
    "definition_identity": DEPLOYED_LAMPORTS_METADATA.definition_identity,
    "dependency_identity": DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY,
    "executable_identity": DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
    "implementation_identity": DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY,
    "semantic_identity": DEPLOYED_LAMPORTS_METADATA.semantic_identity,
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


def test_phase_scope_contains_only_the_fundamental_deployment_measurement() -> None:
    public_names = set(measurement_module.__all__)
    prohibited_fragments = (
        "share",
        "rank",
        "concentration",
        "history",
        "miner_count",
        "motherlode",
        "total_vaulted",
        "total_winnings",
        "feature_set",
        "baseline",
        "ranking",
        "dataset",
    )

    assert DEPLOYED_LAMPORTS_FEATURE_NAME in {
        DEPLOYED_LAMPORTS_MEASUREMENT.name,
        DEPLOYED_LAMPORTS_METADATA.feature_name,
    }
    assert DEPLOYED_LAMPORTS_FEATURE_GROUP == "raw_current_state"
    assert DEPLOYED_LAMPORTS_OUTPUT_NAME == "deployed_lamports"
    assert not any(
        fragment in public_name.lower()
        for fragment in prohibited_fragments
        for public_name in public_names
    )
    assert not hasattr(DEPLOYED_LAMPORTS_MEASUREMENT, "update")
    assert not hasattr(DEPLOYED_LAMPORTS_MEASUREMENT, "rank")
    assert not hasattr(DEPLOYED_LAMPORTS_MEASUREMENT, "select")


def test_protocol_revision_is_bound_to_metadata_not_visible_to_compute() -> None:
    assert DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION not in (
        DEPLOYED_LAMPORTS_METADATA.input_fields
    )
    assert "protocol_revision" not in (
        DEPLOYED_LAMPORTS_METADATA.input_fields
    )
    assert DEPLOYED_LAMPORTS_METADATA.configuration_identity == (
        DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY
    )
    assert DEPLOYED_LAMPORTS_MEASUREMENT.compute(make_context(99)) == {
        "deployed_lamports": 99
    }


def test_semantic_identity_changes_if_dependency_binding_changes() -> None:
    changed = replace(
        DEPLOYED_LAMPORTS_METADATA,
        configuration_identity="f" * 64,
    )

    assert changed.semantic_identity != (
        DEPLOYED_LAMPORTS_METADATA.semantic_identity
    )
    assert changed.definition_identity != (
        DEPLOYED_LAMPORTS_METADATA.definition_identity
    )
