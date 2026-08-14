from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
import textwrap
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import orev3.features.rq003_production_cost_ema as measurement_module
from orev3.features import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    MINER_COUNT_DEFINITION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_MEASUREMENT,
    PRODUCTION_COST_EMA_DEFINITION,
    PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY,
    PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    PRODUCTION_COST_EMA_EXECUTABLE_BINDING_IDENTITY,
    PRODUCTION_COST_EMA_FEATURE_GROUP,
    PRODUCTION_COST_EMA_FEATURE_NAME,
    PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY,
    PRODUCTION_COST_EMA_MEASUREMENT,
    PRODUCTION_COST_EMA_METADATA,
    PRODUCTION_COST_EMA_OUTPUT_NAME,
    PRODUCTION_COST_EMA_PROTOCOL_DEPENDENCIES,
    PRODUCTION_COST_EMA_PROTOCOL_SOURCE_REVISION,
    PRODUCTION_COST_EMA_REVISION_DEPENDENCIES,
    PRODUCTION_COST_EMA_SOURCE_PATH,
    TOTAL_MINERS_DEFINITION,
    TOTAL_MINERS_ELIGIBILITY_DECISION,
    TOTAL_MINERS_MEASUREMENT,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FrozenFeatureRegistry,
    MeasurementVector,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
    canonical_encode,
    reconstruct_executable_binding_identity,
    reconstruct_production_cost_ema_dependency_identity,
    reconstruct_production_cost_ema_implementation_identity,
    validate_production_cost_ema_definition,
)
from orev3.features.rq003_execution import DefinitionContextView
from orev3.strategy_lab.interfaces import DecisionContext


def make_execution_context(value: object) -> RQ003ExecutionContext:
    return RQ003ExecutionContext(
        decision_context=DecisionContext(
            information={
                "round_id": 1234,
                "board": {
                    "round_id": 1234,
                    "production_cost_ema": value,
                },
                "treasury": {"motherlode": 987_654},
                "round": {
                    "round_id": 1234,
                    "deployed_lamports": tuple(
                        (index + 1) * 1_000 for index in range(25)
                    ),
                    "miner_counts": tuple(index + 1 for index in range(25)),
                    "total_miners": 100,
                    "motherlode": 0,
                },
            }
        ),
        observation_index=3,
        structural_candidate_key=7,
        decision_point_configuration_identity="a" * 64,
    )


def make_binding() -> ExecutableMeasurementBinding:
    return ExecutableMeasurementBinding(
        definition=PRODUCTION_COST_EMA_DEFINITION,
        terminal_decision=PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
        computation=PRODUCTION_COST_EMA_MEASUREMENT,
    )


def make_view(value: int) -> DefinitionContextView:
    context = make_execution_context(value)
    binding = make_binding()
    return DefinitionContextView(
        execution_context=context,
        definition=binding.definition,
        executable_binding_identity=binding.executable_binding_identity,
    )


def make_pipeline() -> RQ003MeasurementPipeline:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=(PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,),
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=(PRODUCTION_COST_EMA_DEFINITION,),
    )
    return RQ003MeasurementPipeline(
        registry=registry,
        bindings=(make_binding(),),
    )


def test_metadata_is_immutable_direct_and_revision_bound() -> None:
    metadata = PRODUCTION_COST_EMA_METADATA

    assert metadata.feature_name == "board_production_cost_ema"
    assert metadata.feature_group == "raw_current_state"
    assert metadata.input_fields == ("board.production_cost_ema",)
    assert metadata.history_policy.mode == "current_observation_only"
    assert metadata.history_policy.maximum_history_length == 1
    assert metadata.output_fields == (
        measurement_module.FeatureOutputField(
            name="board_production_cost_ema",
            scalar_type="integer",
            nullable=False,
            semantic_unit="lamports_per_whole_ore",
            candidate_scope="context_wide_replicated",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    )
    assert metadata.configuration_identity == (
        PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY
    )
    assert PRODUCTION_COST_EMA_PROTOCOL_SOURCE_REVISION not in (
        metadata.input_fields
    )
    with pytest.raises(FrozenInstanceError):
        metadata.feature_name = "replacement"  # type: ignore[misc]


@pytest.mark.parametrize("value", (0, 1, 55_000, (1 << 64) - 1))
def test_measurement_returns_exact_published_board_value(value: int) -> None:
    output = PRODUCTION_COST_EMA_MEASUREMENT.compute(make_view(value))

    assert dict(output) == {"board_production_cost_ema": value}
    assert output["board_production_cost_ema"] is value
    with pytest.raises(TypeError):
        output["board_production_cost_ema"] = 1  # type: ignore[index]


@pytest.mark.parametrize("value", (-1, True, 1 << 64, 1.5, "1", None))
def test_execution_context_rejects_non_protocol_values(value: object) -> None:
    with pytest.raises(ValueError, match="unsigned 64-bit integer"):
        make_execution_context(value)


def test_context_binds_board_value_into_frozen_snapshot_identity() -> None:
    first = make_execution_context(100)
    same = make_execution_context(100)
    changed = make_execution_context(101)

    assert first == same
    assert first.production_cost_ema == 100
    assert first.decision_snapshot_identity == same.decision_snapshot_identity
    assert first.context_identity == same.context_identity
    assert first.decision_snapshot_identity != changed.decision_snapshot_identity
    assert first.context_identity != changed.context_identity


def test_execution_context_rejects_inconsistent_board_identity() -> None:
    source = DecisionContext(
        information={
            "round_id": 1,
            "board": {"round_id": 2, "production_cost_ema": 50},
            "treasury": {"motherlode": 10},
            "round": {
                "round_id": 1,
                "deployed_lamports": tuple(range(25)),
                "miner_counts": tuple(range(25)),
                "total_miners": 25,
                "motherlode": 0,
            },
        }
    )

    with pytest.raises(ValueError, match="Board identity is inconsistent"):
        RQ003ExecutionContext.from_decision_context(
            source,
            observation_index=0,
            structural_candidate_key=0,
            decision_point_configuration_identity="a" * 64,
        )


def test_definition_view_exposes_only_declared_board_value() -> None:
    view = make_view(88)

    assert view.board.production_cost_ema == 88
    with pytest.raises(AttributeError, match="undeclared board field"):
        _ = view.board.round_id
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.round
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.square
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.board_history
    with pytest.raises(AttributeError, match="board is immutable"):
        view.board.production_cost_ema = 1


def test_canonical_output_round_trips_without_interpretation() -> None:
    raw = PRODUCTION_COST_EMA_MEASUREMENT.canonical_output(make_view(12_345))
    reconstructed = (
        PRODUCTION_COST_EMA_MEASUREMENT.reconstruct_canonical_output(raw)
    )

    assert raw == canonical_encode({"board_production_cost_ema": 12_345})
    assert dict(reconstructed) == {"board_production_cost_ema": 12_345}
    with pytest.raises(TypeError):
        reconstructed["board_production_cost_ema"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "invalid_output",
    (
        {"other": 1},
        {"board_production_cost_ema": -1},
        {"board_production_cost_ema": True},
        {"board_production_cost_ema": 1 << 64},
    ),
)
def test_canonical_output_reconstruction_fails_closed(
    invalid_output: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        PRODUCTION_COST_EMA_MEASUREMENT.reconstruct_canonical_output(
            canonical_encode(invalid_output)
        )


def test_all_measurement_identities_reconstruct() -> None:
    validate_production_cost_ema_definition()

    assert (
        reconstruct_production_cost_ema_dependency_identity()
        == PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY
    )
    assert (
        reconstruct_production_cost_ema_implementation_identity()
        == PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY
    )
    assert (
        PRODUCTION_COST_EMA_METADATA.reconstruct_semantic_identity()
        == PRODUCTION_COST_EMA_METADATA.semantic_identity
    )
    assert (
        PRODUCTION_COST_EMA_METADATA.reconstruct_definition_identity()
        == PRODUCTION_COST_EMA_METADATA.definition_identity
    )
    assert (
        PRODUCTION_COST_EMA_ELIGIBILITY_DECISION
        .reconstruct_eligibility_decision_identity()
        == PRODUCTION_COST_EMA_ELIGIBILITY_DECISION
        .eligibility_decision_identity
    )
    assert (
        reconstruct_executable_binding_identity(
            PRODUCTION_COST_EMA_METADATA,
            PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
        )
        == PRODUCTION_COST_EMA_EXECUTABLE_BINDING_IDENTITY
    )
    make_binding().validate()


def test_dependency_and_implementation_changes_are_identity_sensitive() -> None:
    protocol_variant = PRODUCTION_COST_EMA_PROTOCOL_DEPENDENCIES + (
        ("unexpected_protocol_dependency", "different"),
    )
    revision_variant = PRODUCTION_COST_EMA_REVISION_DEPENDENCIES + (
        ("unexpected_revision_dependency", "different"),
    )
    implementation_variant = (
        ("implementation_schema_version", 1),
        ("implementation", "different"),
    )

    assert reconstruct_production_cost_ema_dependency_identity(
        protocol_dependencies=protocol_variant,
    ) != PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY
    assert reconstruct_production_cost_ema_dependency_identity(
        revision_dependencies=revision_variant,
    ) != PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY
    assert reconstruct_production_cost_ema_implementation_identity(
        implementation_variant,
    ) != PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY
    changed = replace(
        PRODUCTION_COST_EMA_METADATA,
        configuration_identity="f" * 64,
    )
    assert changed.semantic_identity != PRODUCTION_COST_EMA_METADATA.semantic_identity
    assert (
        changed.definition_identity
        != PRODUCTION_COST_EMA_METADATA.definition_identity
    )


def test_pipeline_vector_reconstructs_deterministically() -> None:
    vector = make_pipeline().compute(make_execution_context(777))
    reconstructed = MeasurementVector.from_canonical_bytes(
        vector.canonical_bytes()
    )

    assert vector.values == {"board_production_cost_ema": 777}
    assert reconstructed == vector
    assert reconstructed.vector_identity == vector.vector_identity
    assert reconstructed.canonical_bytes() == vector.canonical_bytes()


def test_four_measurements_execute_in_explicit_registry_order() -> None:
    decisions = (
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        MINER_COUNT_ELIGIBILITY_DECISION,
        TOTAL_MINERS_ELIGIBILITY_DECISION,
        PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    )
    definitions = (
        DEPLOYED_LAMPORTS_DEFINITION,
        MINER_COUNT_DEFINITION,
        TOTAL_MINERS_DEFINITION,
        PRODUCTION_COST_EMA_DEFINITION,
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
            ExecutableMeasurementBinding(
                definition=TOTAL_MINERS_DEFINITION,
                terminal_decision=TOTAL_MINERS_ELIGIBILITY_DECISION,
                computation=TOTAL_MINERS_MEASUREMENT,
            ),
            make_binding(),
        ),
    )

    vector = pipeline.compute(make_execution_context(55_000))

    assert vector.values == {
        "deployed_lamports": 8_000,
        "miner_count": 8,
        "total_miners": 100,
        "board_production_cost_ema": 55_000,
    }
    assert tuple(vector.values) == (
        "deployed_lamports",
        "miner_count",
        "total_miners",
        "board_production_cost_ema",
    )


def test_definition_validator_rejects_dependency_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        measurement_module,
        "PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY",
        "0" * 64,
    )

    with pytest.raises(ValueError, match="dependency identity mismatch"):
        validate_production_cost_ema_definition()


def test_compute_contains_no_arithmetic_or_interpretive_operation() -> None:
    source = textwrap.dedent(
        inspect.getsource(
            measurement_module.ProductionCostEmaMeasurement.compute
        )
    )
    tree = ast.parse(source)

    prohibited_nodes = (
        ast.BinOp,
        ast.BoolOp,
        ast.Compare,
        ast.IfExp,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    assert not any(isinstance(node, prohibited_nodes) for node in ast.walk(tree))
    assert source.count("context.board.production_cost_ema") == 1
    assert "context.round" not in source
    assert "context.square" not in source


def test_protocol_revision_is_dependency_metadata_not_compute_input() -> None:
    assert "protocol_revision" not in PRODUCTION_COST_EMA_METADATA.input_fields
    assert PRODUCTION_COST_EMA_METADATA.configuration_identity == (
        PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY
    )
    assert PRODUCTION_COST_EMA_MEASUREMENT.compute(make_view(99)) == {
        "board_production_cost_ema": 99
    }


def test_hash_seed_does_not_change_identity_output_or_vector() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    script = """
import json
from orev3.features import (
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    PRODUCTION_COST_EMA_DEFINITION,
    PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY,
    PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY,
    PRODUCTION_COST_EMA_MEASUREMENT,
    PRODUCTION_COST_EMA_METADATA,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FrozenFeatureRegistry,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
)
from orev3.strategy_lab.interfaces import DecisionContext
catalog = EligibilityCatalog(
    catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    decisions=(PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,),
)
registry = FrozenFeatureRegistry(
    registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    eligibility_catalog=catalog,
    definitions=(PRODUCTION_COST_EMA_DEFINITION,),
)
pipeline = RQ003MeasurementPipeline(
    registry=registry,
    bindings=(ExecutableMeasurementBinding(
        definition=PRODUCTION_COST_EMA_DEFINITION,
        terminal_decision=PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
        computation=PRODUCTION_COST_EMA_MEASUREMENT,
    ),),
)
context = RQ003ExecutionContext(
    decision_context=DecisionContext(information={
        'round_id': 1,
        'board': {'round_id': 1, 'production_cost_ema': 55000},
        'treasury': {'motherlode': 987654},
        'round': {
            'round_id': 1,
            'deployed_lamports': tuple(range(25)),
            'miner_counts': tuple(range(25)),
            'total_miners': 25,
            'motherlode': 0,
        },
    }),
    observation_index=0,
    structural_candidate_key=4,
    decision_point_configuration_identity='a' * 64,
)
vector = pipeline.compute(context)
print(json.dumps({
    'definition_identity': PRODUCTION_COST_EMA_METADATA.definition_identity,
    'dependency_identity': PRODUCTION_COST_EMA_DEPENDENCY_IDENTITY,
    'implementation_identity': PRODUCTION_COST_EMA_IMPLEMENTATION_IDENTITY,
    'vector': vector.canonical_bytes().hex(),
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
    assert json.loads(outputs[0])["vector"]


def test_phase_scope_contains_only_production_cost_ema_measurement() -> None:
    public_names = set(measurement_module.__all__)
    prohibited_fragments = (
        "motherlode",
        "total_vaulted",
        "total_winnings",
        "share",
        "rank",
        "normalization",
        "feature_set",
        "dataset",
        "baseline",
        "strategy",
        "settlement",
    )

    assert PRODUCTION_COST_EMA_FEATURE_NAME in {
        PRODUCTION_COST_EMA_MEASUREMENT.name,
        PRODUCTION_COST_EMA_METADATA.feature_name,
    }
    assert PRODUCTION_COST_EMA_FEATURE_GROUP == "raw_current_state"
    assert PRODUCTION_COST_EMA_OUTPUT_NAME == "board_production_cost_ema"
    assert PRODUCTION_COST_EMA_SOURCE_PATH == "board.production_cost_ema"
    assert not any(
        fragment in public_name.lower()
        for fragment in prohibited_fragments
        for public_name in public_names
    )
    assert not hasattr(PRODUCTION_COST_EMA_MEASUREMENT, "update")
    assert not hasattr(PRODUCTION_COST_EMA_MEASUREMENT, "rank")
    assert not hasattr(PRODUCTION_COST_EMA_MEASUREMENT, "select")
