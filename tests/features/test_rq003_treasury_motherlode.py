from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
import textwrap
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import orev3.features.rq003_treasury_motherlode as measurement_module
from orev3.features import (
    ACTIVE_ROUND_MOTHERLODE_DEFINITION,
    ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION,
    ACTIVE_ROUND_MOTHERLODE_MEASUREMENT,
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    MINER_COUNT_DEFINITION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_MEASUREMENT,
    PRODUCTION_COST_EMA_DEFINITION,
    PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
    PRODUCTION_COST_EMA_MEASUREMENT,
    TOTAL_MINERS_DEFINITION,
    TOTAL_MINERS_ELIGIBILITY_DECISION,
    TOTAL_MINERS_MEASUREMENT,
    TREASURY_MOTHERLODE_DEFINITION,
    TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY,
    TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    TREASURY_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY,
    TREASURY_MOTHERLODE_FEATURE_GROUP,
    TREASURY_MOTHERLODE_FEATURE_NAME,
    TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY,
    TREASURY_MOTHERLODE_MEASUREMENT,
    TREASURY_MOTHERLODE_METADATA,
    TREASURY_MOTHERLODE_OUTPUT_NAME,
    TREASURY_MOTHERLODE_PROTOCOL_DEPENDENCIES,
    TREASURY_MOTHERLODE_PROTOCOL_SOURCE_REVISION,
    TREASURY_MOTHERLODE_REVISION_DEPENDENCIES,
    TREASURY_MOTHERLODE_SOURCE_PATH,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FrozenFeatureRegistry,
    MeasurementVector,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
    canonical_encode,
    reconstruct_executable_binding_identity,
    reconstruct_treasury_motherlode_dependency_identity,
    reconstruct_treasury_motherlode_implementation_identity,
    validate_treasury_motherlode_definition,
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
                    "production_cost_ema": 55_000,
                },
                "treasury": {"motherlode": value},
                "round": {
                    "round_id": 1234,
                    "deployed_lamports": tuple(
                        (index + 1) * 1_000 for index in range(25)
                    ),
                    "miner_counts": tuple(index + 1 for index in range(25)),
                    "total_miners": 100,
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
        definition=TREASURY_MOTHERLODE_DEFINITION,
        terminal_decision=TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
        computation=TREASURY_MOTHERLODE_MEASUREMENT,
    )


def make_view(value: int) -> DefinitionContextView:
    binding = make_binding()
    return DefinitionContextView(
        execution_context=make_execution_context(value),
        definition=binding.definition,
        executable_binding_identity=binding.executable_binding_identity,
    )


def make_pipeline() -> RQ003MeasurementPipeline:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=(TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,),
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=(TREASURY_MOTHERLODE_DEFINITION,),
    )
    return RQ003MeasurementPipeline(
        registry=registry,
        bindings=(make_binding(),),
    )


def test_metadata_is_immutable_direct_and_revision_bound() -> None:
    metadata = TREASURY_MOTHERLODE_METADATA

    assert metadata.feature_name == "treasury_motherlode"
    assert metadata.feature_group == "raw_current_state"
    assert metadata.input_fields == ("treasury.motherlode",)
    assert metadata.history_policy.mode == "current_observation_only"
    assert metadata.history_policy.maximum_history_length == 1
    assert metadata.output_fields == (
        measurement_module.FeatureOutputField(
            name="treasury_motherlode",
            scalar_type="integer",
            nullable=False,
            semantic_unit="indivisible_ore_units",
            candidate_scope="context_wide_replicated",
            tie_rule=None,
            canonical_encoding_rule="decimal_integer",
        ),
    )
    assert metadata.configuration_identity == (
        TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY
    )
    assert TREASURY_MOTHERLODE_PROTOCOL_SOURCE_REVISION not in (
        metadata.input_fields
    )
    with pytest.raises(FrozenInstanceError):
        metadata.feature_name = "replacement"  # type: ignore[misc]


@pytest.mark.parametrize("value", (0, 1, 55_000, (1 << 64) - 1))
def test_measurement_returns_exact_published_treasury_value(value: int) -> None:
    output = TREASURY_MOTHERLODE_MEASUREMENT.compute(make_view(value))

    assert dict(output) == {"treasury_motherlode": value}
    assert output["treasury_motherlode"] is value
    with pytest.raises(TypeError):
        output["treasury_motherlode"] = 1  # type: ignore[index]


@pytest.mark.parametrize("value", (-1, True, 1 << 64, 1.5, "1", None))
def test_execution_context_rejects_non_protocol_values(value: object) -> None:
    with pytest.raises(ValueError, match="unsigned 64-bit integer"):
        make_execution_context(value)


def test_context_binds_treasury_value_into_frozen_snapshot_identity() -> None:
    first = make_execution_context(100)
    same = make_execution_context(100)
    changed = make_execution_context(101)

    assert first == same
    assert first.treasury_motherlode == 100
    assert first.decision_snapshot_identity == same.decision_snapshot_identity
    assert first.context_identity == same.context_identity
    assert first.decision_snapshot_identity != changed.decision_snapshot_identity
    assert first.context_identity != changed.context_identity


def test_definition_view_exposes_only_declared_treasury_value() -> None:
    view = make_view(88)

    assert view.treasury.motherlode == 88
    with pytest.raises(AttributeError, match="undeclared treasury field"):
        _ = view.treasury.total_vaulted
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.round
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = view.board
    with pytest.raises(AttributeError, match="treasury is immutable"):
        view.treasury.motherlode = 1


def test_pipeline_and_vector_reconstruct_deterministically() -> None:
    vector = make_pipeline().compute(make_execution_context(777))
    reconstructed = MeasurementVector.from_canonical_bytes(
        vector.canonical_bytes()
    )

    assert vector.values == {"treasury_motherlode": 777}
    assert reconstructed == vector
    assert reconstructed.vector_identity == vector.vector_identity


def test_measurement_executes_with_existing_library_without_semantic_changes() -> None:
    decisions = (
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        MINER_COUNT_ELIGIBILITY_DECISION,
        TOTAL_MINERS_ELIGIBILITY_DECISION,
        PRODUCTION_COST_EMA_ELIGIBILITY_DECISION,
        ACTIVE_ROUND_MOTHERLODE_ELIGIBILITY_DECISION,
        TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    )
    definitions = (
        DEPLOYED_LAMPORTS_DEFINITION,
        MINER_COUNT_DEFINITION,
        TOTAL_MINERS_DEFINITION,
        PRODUCTION_COST_EMA_DEFINITION,
        ACTIVE_ROUND_MOTHERLODE_DEFINITION,
        TREASURY_MOTHERLODE_DEFINITION,
    )
    computations = (
        DEPLOYED_LAMPORTS_MEASUREMENT,
        MINER_COUNT_MEASUREMENT,
        TOTAL_MINERS_MEASUREMENT,
        PRODUCTION_COST_EMA_MEASUREMENT,
        ACTIVE_ROUND_MOTHERLODE_MEASUREMENT,
        TREASURY_MOTHERLODE_MEASUREMENT,
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
        bindings=tuple(
            ExecutableMeasurementBinding(
                definition=definition,
                terminal_decision=decision,
                computation=computation,
            )
            for definition, decision, computation in zip(
                definitions, decisions, computations, strict=True
            )
        ),
    )

    vector = pipeline.compute(make_execution_context(987_654))

    assert vector.values == {
        "deployed_lamports": 8_000,
        "miner_count": 8,
        "total_miners": 100,
        "board_production_cost_ema": 55_000,
        "active_round_motherlode": 0,
        "treasury_motherlode": 987_654,
    }


def test_canonical_output_round_trips_without_interpretation() -> None:
    raw = TREASURY_MOTHERLODE_MEASUREMENT.canonical_output(make_view(12_345))
    reconstructed = (
        TREASURY_MOTHERLODE_MEASUREMENT.reconstruct_canonical_output(raw)
    )

    assert raw == canonical_encode({"treasury_motherlode": 12_345})
    assert dict(reconstructed) == {"treasury_motherlode": 12_345}
    with pytest.raises(TypeError):
        reconstructed["treasury_motherlode"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "invalid_output",
    (
        {"other": 1},
        {"treasury_motherlode": -1},
        {"treasury_motherlode": True},
        {"treasury_motherlode": 1 << 64},
    ),
)
def test_canonical_output_reconstruction_fails_closed(
    invalid_output: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        TREASURY_MOTHERLODE_MEASUREMENT.reconstruct_canonical_output(
            canonical_encode(invalid_output)
        )


def test_all_measurement_identities_reconstruct() -> None:
    validate_treasury_motherlode_definition()

    assert (
        reconstruct_treasury_motherlode_dependency_identity()
        == TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY
    )
    assert (
        reconstruct_treasury_motherlode_implementation_identity()
        == TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY
    )
    assert (
        TREASURY_MOTHERLODE_METADATA.reconstruct_semantic_identity()
        == TREASURY_MOTHERLODE_METADATA.semantic_identity
    )
    assert (
        TREASURY_MOTHERLODE_METADATA.reconstruct_definition_identity()
        == TREASURY_MOTHERLODE_METADATA.definition_identity
    )
    assert (
        TREASURY_MOTHERLODE_ELIGIBILITY_DECISION
        .reconstruct_eligibility_decision_identity()
        == TREASURY_MOTHERLODE_ELIGIBILITY_DECISION
        .eligibility_decision_identity
    )
    assert (
        reconstruct_executable_binding_identity(
            TREASURY_MOTHERLODE_METADATA,
            TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
        )
        == TREASURY_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY
    )
    binding = make_binding()
    binding.validate()
    assert (
        binding.executable_binding_identity
        == TREASURY_MOTHERLODE_EXECUTABLE_BINDING_IDENTITY
    )


def test_dependency_and_implementation_changes_change_identities() -> None:
    protocol_variant = TREASURY_MOTHERLODE_PROTOCOL_DEPENDENCIES + (
        ("extra", "changed"),
    )
    revision_variant = TREASURY_MOTHERLODE_REVISION_DEPENDENCIES + (
        ("extra", "changed"),
    )
    implementation_variant = (
        ("implementation_schema_version", 1),
        ("implementation", "different"),
    )

    assert reconstruct_treasury_motherlode_dependency_identity(
        protocol_dependencies=protocol_variant,
    ) != TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY
    assert reconstruct_treasury_motherlode_dependency_identity(
        revision_dependencies=revision_variant,
    ) != TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY
    assert reconstruct_treasury_motherlode_implementation_identity(
        implementation_variant,
    ) != TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY


def test_definition_validator_rejects_dependency_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        measurement_module,
        "TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY",
        "0" * 64,
    )

    with pytest.raises(ValueError, match="dependency identity mismatch"):
        validate_treasury_motherlode_definition()


def test_compute_contains_no_arithmetic_or_interpretive_operation() -> None:
    source = textwrap.dedent(
        inspect.getsource(
            measurement_module.TreasuryMotherlodeMeasurement.compute
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
    assert source.count("context.treasury.motherlode") == 1
    assert "context.round" not in source
    assert "context.board" not in source
    assert "context.square" not in source


def test_protocol_revision_is_dependency_metadata_not_compute_input() -> None:
    assert "protocol_revision" not in TREASURY_MOTHERLODE_METADATA.input_fields
    assert TREASURY_MOTHERLODE_METADATA.configuration_identity == (
        TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY
    )
    assert TREASURY_MOTHERLODE_MEASUREMENT.compute(make_view(99)) == {
        "treasury_motherlode": 99
    }


def test_hash_seed_does_not_change_identity_output_or_vector() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    script = """
import json
from orev3.features import (
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    TREASURY_MOTHERLODE_DEFINITION,
    TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY,
    TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
    TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY,
    TREASURY_MOTHERLODE_MEASUREMENT,
    TREASURY_MOTHERLODE_METADATA,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FrozenFeatureRegistry,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
)
from orev3.strategy_lab.interfaces import DecisionContext
catalog = EligibilityCatalog(
    catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    decisions=(TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,),
)
registry = FrozenFeatureRegistry(
    registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    eligibility_catalog=catalog,
    definitions=(TREASURY_MOTHERLODE_DEFINITION,),
)
pipeline = RQ003MeasurementPipeline(
    registry=registry,
    bindings=(ExecutableMeasurementBinding(
        definition=TREASURY_MOTHERLODE_DEFINITION,
        terminal_decision=TREASURY_MOTHERLODE_ELIGIBILITY_DECISION,
        computation=TREASURY_MOTHERLODE_MEASUREMENT,
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
    'definition_identity': TREASURY_MOTHERLODE_METADATA.definition_identity,
    'dependency_identity': TREASURY_MOTHERLODE_DEPENDENCY_IDENTITY,
    'implementation_identity': TREASURY_MOTHERLODE_IMPLEMENTATION_IDENTITY,
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


def test_phase_scope_contains_only_treasury_motherlode_measurement() -> None:
    public_names = set(measurement_module.__all__)
    prohibited_fragments = (
        "total_vaulted",
        "total_winnings",
        "derived",
        "feature_set",
        "dataset",
        "baseline",
        "ranking",
        "strategy",
        "economics",
    )

    assert "TreasuryMotherlodeMeasurement" in public_names
    assert TREASURY_MOTHERLODE_FEATURE_GROUP == "raw_current_state"
    assert TREASURY_MOTHERLODE_OUTPUT_NAME == "treasury_motherlode"
    assert TREASURY_MOTHERLODE_SOURCE_PATH == "treasury.motherlode"
    assert not any(
        fragment in public_name.lower()
        for fragment in prohibited_fragments
        for public_name in public_names
    )
