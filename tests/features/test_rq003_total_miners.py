from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import orev3.features.rq003_total_miners as measurement_module
from orev3.features import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    MINER_COUNT_DEFINITION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_MEASUREMENT,
    TOTAL_MINERS_DEFINITION,
    TOTAL_MINERS_DEPENDENCY_IDENTITY,
    TOTAL_MINERS_ELIGIBILITY_DECISION,
    TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY,
    TOTAL_MINERS_FEATURE_GROUP,
    TOTAL_MINERS_FEATURE_NAME,
    TOTAL_MINERS_IMPLEMENTATION_IDENTITY,
    TOTAL_MINERS_MEASUREMENT,
    TOTAL_MINERS_METADATA,
    TOTAL_MINERS_OUTPUT_NAME,
    TOTAL_MINERS_PROTOCOL_DEPENDENCIES,
    TOTAL_MINERS_PROTOCOL_SOURCE_REVISION,
    TOTAL_MINERS_REVISION_DEPENDENCIES,
    TOTAL_MINERS_SOURCE_PATH,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FrozenFeatureRegistry,
    MeasurementVector,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
    canonical_encode,
    reconstruct_executable_binding_identity,
    reconstruct_total_miners_dependency_identity,
    reconstruct_total_miners_implementation_identity,
    validate_total_miners_definition,
)
from orev3.features.rq003_execution import DefinitionContextView
from orev3.strategy_lab.interfaces import DecisionContext


def make_execution_context(total_miners: int) -> RQ003ExecutionContext:
    return RQ003ExecutionContext(
        decision_context=DecisionContext(
            information={
                "round_id": 1234,
                "board": {
                    "round_id": 1234,
                    "production_cost_ema": 55_000,
                },
                "treasury": {"motherlode": 987_654},
                "round": {
                    "round_id": 1234,
                    "deployed_lamports": tuple(
                        (index + 1) * 1_000 for index in range(25)
                    ),
                    "miner_counts": tuple(index + 1 for index in range(25)),
                    "total_miners": total_miners,
                    "motherlode": 0,
                    "total_vaulted": 123_456,
                    "total_winnings": 654_321,
                },
            }
        ),
        observation_index=3,
        structural_candidate_key=7,
        decision_point_configuration_identity="a" * 64,
    )


def make_binding() -> ExecutableMeasurementBinding:
    return ExecutableMeasurementBinding(
        definition=TOTAL_MINERS_DEFINITION,
        terminal_decision=TOTAL_MINERS_ELIGIBILITY_DECISION,
        computation=TOTAL_MINERS_MEASUREMENT,
    )


def make_view(total_miners: int) -> DefinitionContextView:
    context = make_execution_context(total_miners)
    binding = make_binding()
    return DefinitionContextView(
        execution_context=context,
        definition=binding.definition,
        executable_binding_identity=binding.executable_binding_identity,
    )


def make_pipeline() -> RQ003MeasurementPipeline:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=(TOTAL_MINERS_ELIGIBILITY_DECISION,),
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=(TOTAL_MINERS_DEFINITION,),
    )
    return RQ003MeasurementPipeline(
        registry=registry,
        bindings=(make_binding(),),
    )


def test_metadata_is_immutable_atomic_and_context_direct() -> None:
    metadata = TOTAL_MINERS_METADATA

    assert metadata.feature_name == "total_miners"
    assert metadata.feature_group == "raw_current_state"
    assert metadata.input_fields == ("round.total_miners",)
    assert metadata.history_policy.mode == "current_observation_only"
    assert metadata.history_policy.maximum_history_length == 1
    assert metadata.output_fields == (
        measurement_module.FeatureOutputField(
            name="total_miners",
            scalar_type="integer",
            nullable=False,
            semantic_unit="unique_miner_authority_count",
            candidate_scope="context_wide_replicated",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    )
    with pytest.raises(FrozenInstanceError):
        metadata.feature_name = "replacement"  # type: ignore[misc]


def test_computation_returns_only_the_published_round_value() -> None:
    output = TOTAL_MINERS_MEASUREMENT.compute(make_view(987_654_321))

    assert dict(output) == {"total_miners": 987_654_321}
    assert tuple(output) == ("total_miners",)
    with pytest.raises(TypeError):
        output["total_miners"] = 1  # type: ignore[index]


def test_computation_does_not_reconstruct_from_per_square_counts() -> None:
    context = make_execution_context(7)
    assert sum(context.miner_counts) == 325

    assert TOTAL_MINERS_MEASUREMENT.compute(make_view(7)) == {
        "total_miners": 7
    }


def test_context_builder_uses_one_frozen_participant_state_boundary() -> None:
    source = DecisionContext(
        information={
            "round_id": 1,
            "board": {"round_id": 1, "production_cost_ema": 50},
            "treasury": {"motherlode": 10},
            "round": {
                "round_id": 1,
                "deployed_lamports": tuple(range(25)),
                "miner_counts": tuple(index + 1 for index in range(25)),
                "total_miners": 7,
                "motherlode": 0,
                "total_vaulted": 123,
                "total_winnings": 321,
            },
        }
    )

    context = RQ003ExecutionContext.from_decision_context(
        source,
        observation_index=0,
        structural_candidate_key=4,
        decision_point_configuration_identity="a" * 64,
    )

    assert sum(context.miner_counts) == 325
    assert context.total_miners == 7


@pytest.mark.parametrize("value", (0, (1 << 64) - 1))
def test_pipeline_accepts_protocol_u64_boundaries(value: int) -> None:
    vector = make_pipeline().compute(make_execution_context(value))

    assert vector.values == {"total_miners": value}


def test_pipeline_vector_reconstructs_deterministically() -> None:
    vector = make_pipeline().compute(make_execution_context(777))
    reconstructed = MeasurementVector.from_canonical_bytes(
        vector.canonical_bytes()
    )

    assert reconstructed == vector
    assert reconstructed.vector_identity == vector.vector_identity
    assert reconstructed.canonical_bytes() == vector.canonical_bytes()


@pytest.mark.parametrize("invalid_value", (-1, True, 1 << 64, 1.5, "1"))
def test_execution_context_rejects_non_protocol_values(
    invalid_value: object,
) -> None:
    with pytest.raises(ValueError, match="unsigned 64-bit integer"):
        make_execution_context(invalid_value)  # type: ignore[arg-type]


def test_definition_view_exposes_only_declared_round_value() -> None:
    view = make_view(88)

    assert view.round.total_miners == 88
    with pytest.raises(AttributeError, match="undeclared round field"):
        _ = view.round.motherlode
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.square
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.board
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.square_history


def test_canonical_output_round_trips_without_interpretation() -> None:
    raw = TOTAL_MINERS_MEASUREMENT.canonical_output(make_view(12_345))
    reconstructed = TOTAL_MINERS_MEASUREMENT.reconstruct_canonical_output(raw)

    assert raw == canonical_encode({"total_miners": 12_345})
    assert dict(reconstructed) == {"total_miners": 12_345}
    with pytest.raises(TypeError):
        reconstructed["total_miners"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "invalid_output",
    (
        {"other": 1},
        {"total_miners": -1},
        {"total_miners": True},
        {"total_miners": 1 << 64},
    ),
)
def test_canonical_output_reconstruction_fails_closed(
    invalid_output: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        TOTAL_MINERS_MEASUREMENT.reconstruct_canonical_output(
            canonical_encode(invalid_output)
        )


def test_all_measurement_identities_reconstruct() -> None:
    validate_total_miners_definition()

    assert (
        reconstruct_total_miners_dependency_identity()
        == TOTAL_MINERS_DEPENDENCY_IDENTITY
    )
    assert (
        reconstruct_total_miners_implementation_identity()
        == TOTAL_MINERS_IMPLEMENTATION_IDENTITY
    )
    assert (
        TOTAL_MINERS_METADATA.reconstruct_semantic_identity()
        == TOTAL_MINERS_METADATA.semantic_identity
    )
    assert (
        TOTAL_MINERS_METADATA.reconstruct_definition_identity()
        == TOTAL_MINERS_METADATA.definition_identity
    )
    assert (
        reconstruct_executable_binding_identity(
            TOTAL_MINERS_METADATA,
            TOTAL_MINERS_ELIGIBILITY_DECISION,
        )
        == TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY
    )


def test_dependency_and_implementation_changes_are_identity_sensitive() -> None:
    protocol_variant = TOTAL_MINERS_PROTOCOL_DEPENDENCIES + (
        ("unexpected_protocol_dependency", "different"),
    )
    revision_variant = TOTAL_MINERS_REVISION_DEPENDENCIES + (
        ("unexpected_revision_dependency", "different"),
    )
    implementation_variant = (
        ("implementation_schema_version", 1),
        ("implementation", "different"),
    )

    assert reconstruct_total_miners_dependency_identity(
        protocol_dependencies=protocol_variant,
    ) != TOTAL_MINERS_DEPENDENCY_IDENTITY
    assert reconstruct_total_miners_dependency_identity(
        revision_dependencies=revision_variant,
    ) != TOTAL_MINERS_DEPENDENCY_IDENTITY
    assert reconstruct_total_miners_implementation_identity(
        implementation_variant,
    ) != TOTAL_MINERS_IMPLEMENTATION_IDENTITY


def test_three_measurements_execute_through_the_common_pipeline() -> None:
    decisions = (
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        MINER_COUNT_ELIGIBILITY_DECISION,
        TOTAL_MINERS_ELIGIBILITY_DECISION,
    )
    definitions = (
        DEPLOYED_LAMPORTS_DEFINITION,
        MINER_COUNT_DEFINITION,
        TOTAL_MINERS_DEFINITION,
    )
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=decisions,
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=definitions,
    )
    pipeline = RQ003MeasurementPipeline(
        registry=registry,
        bindings=(
            ExecutableMeasurementBinding(
                definition=DEPLOYED_LAMPORTS_DEFINITION,
                terminal_decision=DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
                computation=DEPLOYED_LAMPORTS_MEASUREMENT,
            ),
            ExecutableMeasurementBinding(
                definition=MINER_COUNT_DEFINITION,
                terminal_decision=MINER_COUNT_ELIGIBILITY_DECISION,
                computation=MINER_COUNT_MEASUREMENT,
            ),
            make_binding(),
        ),
    )

    vector = pipeline.compute(make_execution_context(777))

    assert vector.values == {
        "deployed_lamports": 8_000,
        "miner_count": 8,
        "total_miners": 777,
    }
    assert tuple(vector.values) == (
        "deployed_lamports",
        "miner_count",
        "total_miners",
    )


def test_definition_validator_rejects_dependency_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        measurement_module,
        "TOTAL_MINERS_DEPENDENCY_IDENTITY",
        "0" * 64,
    )

    with pytest.raises(ValueError, match="dependency identity mismatch"):
        validate_total_miners_definition()


def test_hash_seed_does_not_change_identity_output_or_vector() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    script = """
import json
from orev3.features import (
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    TOTAL_MINERS_DEFINITION,
    TOTAL_MINERS_DEPENDENCY_IDENTITY,
    TOTAL_MINERS_ELIGIBILITY_DECISION,
    TOTAL_MINERS_IMPLEMENTATION_IDENTITY,
    TOTAL_MINERS_MEASUREMENT,
    TOTAL_MINERS_METADATA,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FrozenFeatureRegistry,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
)
catalog = EligibilityCatalog(
    catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    decisions=(TOTAL_MINERS_ELIGIBILITY_DECISION,),
)
registry = FrozenFeatureRegistry(
    registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    eligibility_catalog=catalog,
    definitions=(TOTAL_MINERS_DEFINITION,),
)
pipeline = RQ003MeasurementPipeline(
    registry=registry,
    bindings=(ExecutableMeasurementBinding(
        definition=TOTAL_MINERS_DEFINITION,
        terminal_decision=TOTAL_MINERS_ELIGIBILITY_DECISION,
        computation=TOTAL_MINERS_MEASUREMENT,
    ),),
)
context = RQ003ExecutionContext(
    decision_context=DecisionContext(information={
        'round_id': 1,
        'board': {'round_id': 1, 'production_cost_ema': 50},
        'treasury': {'motherlode': 10},
        'round': {
            'round_id': 1,
            'deployed_lamports': tuple(range(25)),
            'miner_counts': tuple(range(25)),
            'total_miners': 777,
            'motherlode': 0,
            'total_vaulted': 123456,
            'total_winnings': 654321,
        },
    }),
    observation_index=0,
    structural_candidate_key=4,
    decision_point_configuration_identity='a' * 64,
)
vector = pipeline.compute(context)
print(json.dumps({
    'canonical_output': TOTAL_MINERS_MEASUREMENT.canonical_output(
        DefinitionContextView(
            execution_context=context,
            definition=TOTAL_MINERS_DEFINITION,
            executable_binding_identity=(
                pipeline._bindings[0].executable_binding_identity
            ),
        )
    ).hex(),
    'definition_identity': TOTAL_MINERS_METADATA.definition_identity,
    'dependency_identity': TOTAL_MINERS_DEPENDENCY_IDENTITY,
    'implementation_identity': TOTAL_MINERS_IMPLEMENTATION_IDENTITY,
    'vector': vector.canonical_bytes().hex(),
}, sort_keys=True))
"""
    script = script.replace(
        "import json\n",
        "import json\n"
        "from orev3.features.rq003_execution import DefinitionContextView\n"
        "from orev3.strategy_lab.interfaces import DecisionContext\n",
    )

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


def test_protocol_revision_is_dependency_metadata_not_compute_input() -> None:
    assert TOTAL_MINERS_PROTOCOL_SOURCE_REVISION not in (
        TOTAL_MINERS_METADATA.input_fields
    )
    assert "protocol_revision" not in TOTAL_MINERS_METADATA.input_fields
    assert TOTAL_MINERS_METADATA.configuration_identity == (
        TOTAL_MINERS_DEPENDENCY_IDENTITY
    )
    assert TOTAL_MINERS_MEASUREMENT.compute(make_view(99)) == {
        "total_miners": 99
    }


def test_phase_scope_contains_only_total_miners_measurement() -> None:
    public_names = set(measurement_module.__all__)
    prohibited_fragments = (
        "production_cost",
        "motherlode",
        "total_vaulted",
        "total_winnings",
        "share",
        "rank",
        "normalization",
        "history",
        "feature_set",
        "dataset",
        "baseline",
        "ranking",
    )

    assert TOTAL_MINERS_FEATURE_NAME in {
        TOTAL_MINERS_MEASUREMENT.name,
        TOTAL_MINERS_METADATA.feature_name,
    }
    assert TOTAL_MINERS_FEATURE_GROUP == "raw_current_state"
    assert TOTAL_MINERS_OUTPUT_NAME == "total_miners"
    assert TOTAL_MINERS_SOURCE_PATH == "round.total_miners"
    assert not any(
        fragment in public_name.lower()
        for fragment in prohibited_fragments
        for public_name in public_names
    )
    assert not hasattr(TOTAL_MINERS_MEASUREMENT, "update")
    assert not hasattr(TOTAL_MINERS_MEASUREMENT, "rank")
    assert not hasattr(TOTAL_MINERS_MEASUREMENT, "select")


def test_semantic_identity_changes_if_dependency_binding_changes() -> None:
    changed = replace(
        TOTAL_MINERS_METADATA,
        configuration_identity="f" * 64,
    )

    assert changed.semantic_identity != TOTAL_MINERS_METADATA.semantic_identity
    assert changed.definition_identity != TOTAL_MINERS_METADATA.definition_identity
