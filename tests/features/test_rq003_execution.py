from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from types import MappingProxyType

import pytest

from orev3.features import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    MINER_COUNT_DEFINITION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_MEASUREMENT,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FeatureEligibilityStatus,
    FeatureDefinition,
    FrozenFeatureRegistry,
    MeasurementVector,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
)
from orev3.features.base import Feature
from orev3.features.context import FeatureContext
from orev3.features.rq003_execution import DefinitionContextView
from orev3.features.types import BoardSnapshot, FeatureValues, SquareSnapshot
from orev3.strategy_lab.interfaces import DecisionContext


def make_feature_context(*, square_index: int = 7) -> FeatureContext:
    squares = tuple(
        SquareSnapshot(
            observation_index=4,
            miner_count=100 + index,
            deployed_lamports=10_000 + index,
            reward_raw=900 + index,
            mass=0,
        )
        for index in range(25)
    )
    board = BoardSnapshot(
        round_id=4321,
        observation_index=4,
        observation_count=9,
        slots_remaining=17,
        squares=squares,
    )
    return FeatureContext(
        board=board,
        square_index=square_index,
        square_history=(squares[square_index],),
        board_history=(board,),
    )


def make_decision_context(*, total_miners: int = 777) -> DecisionContext:
    return DecisionContext(
        information={
            "round_id": 4321,
            "board": {
                "round_id": 4321,
                "production_cost_ema": 55_000,
            },
            "treasury": {"motherlode": 987_654},
            "round": {
                "round_id": 4321,
                "deployed_lamports": tuple(
                    10_000 + index for index in range(25)
                ),
                "miner_counts": tuple(100 + index for index in range(25)),
                "total_miners": total_miners,
                "motherlode": 0,
                "total_vaulted": 123_456,
            },
        }
    )


def make_execution_context(*, square_index: int = 7) -> RQ003ExecutionContext:
    return RQ003ExecutionContext.from_decision_context(
        make_decision_context(),
        observation_index=4,
        structural_candidate_key=square_index,
        decision_point_configuration_identity="a" * 64,
    )


def make_pipeline() -> RQ003MeasurementPipeline:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=(
            DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
            MINER_COUNT_ELIGIBILITY_DECISION,
        ),
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=(
            DEPLOYED_LAMPORTS_DEFINITION,
            MINER_COUNT_DEFINITION,
        ),
    )
    return RQ003MeasurementPipeline(
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
        ),
    )


def test_execution_context_is_deeply_immutable_and_reconstructable() -> None:
    source = make_decision_context()
    context = RQ003ExecutionContext.from_decision_context(
        source,
        observation_index=4,
        structural_candidate_key=7,
        decision_point_configuration_identity="a" * 64,
    )

    assert context.deployed_lamports == tuple(
        10_000 + index for index in range(25)
    )
    assert context.miner_counts == tuple(100 + index for index in range(25))
    assert context.total_miners == 777
    assert context.pre_finalization_total_vaulted == 123_456
    assert context.treasury_motherlode == 987_654
    context.validate_identities()
    assert context.reconstruct_context_identity() == context.context_identity
    with pytest.raises(FrozenInstanceError):
        context.observation_index = 5  # type: ignore[misc]


def test_execution_context_defensively_freezes_one_decision_source() -> None:
    mutable_deployments = list(range(25))
    source = DecisionContext(
        information={
            "round_id": 1,
            "board": {"round_id": 1, "production_cost_ema": 50},
            "treasury": {"motherlode": 10},
            "round": {
                "round_id": 1,
                "deployed_lamports": mutable_deployments,
                "miner_counts": tuple(range(25)),
                "total_miners": 25,
                "motherlode": 0,
                "total_vaulted": 123,
            },
        }
    )
    mutable_deployments[0] = 999
    context = RQ003ExecutionContext.from_decision_context(
        source,
        observation_index=1,
        structural_candidate_key=0,
        decision_point_configuration_identity="a" * 64,
    )

    assert context.deployed_lamports[0] == 0


def test_execution_context_rejects_noncanonical_source_values() -> None:
    with pytest.raises(ValueError, match="unsigned 64-bit"):
        RQ003ExecutionContext(
            decision_context=DecisionContext(
                information={
                    "round_id": 1,
                    "board": {"round_id": 1, "production_cost_ema": 50},
                    "treasury": {"motherlode": 10},
                    "round": {
                        "round_id": 1,
                        "deployed_lamports": (True,) + (0,) * 24,
                        "miner_counts": (0,) * 25,
                        "total_miners": 0,
                        "motherlode": 0,
                        "total_vaulted": 0,
                    },
                }
            ),
            observation_index=1,
            structural_candidate_key=0,
            decision_point_configuration_identity="a" * 64,
        )


def test_execution_context_rejects_incoherent_round_identity() -> None:
    source = DecisionContext(
        information={
            "round_id": 1,
            "board": {"round_id": 1, "production_cost_ema": 50},
            "treasury": {"motherlode": 10},
            "round": {
                "round_id": 2,
                "deployed_lamports": tuple(range(25)),
                "miner_counts": tuple(range(25)),
                "total_miners": 25,
                "motherlode": 0,
                "total_vaulted": 123,
            },
        }
    )

    with pytest.raises(ValueError, match="Round identity is inconsistent"):
        RQ003ExecutionContext.from_decision_context(
            source,
            observation_index=1,
            structural_candidate_key=0,
            decision_point_configuration_identity="a" * 64,
        )


def test_execution_context_rejects_incomplete_participant_state() -> None:
    source = DecisionContext(
        information={
            "round_id": 1,
            "board": {"round_id": 1, "production_cost_ema": 50},
            "treasury": {"motherlode": 10},
            "round": {
                "round_id": 1,
                "deployed_lamports": tuple(range(25)),
                "miner_counts": tuple(range(25)),
                "motherlode": 0,
                "total_vaulted": 123,
            },
        }
    )

    with pytest.raises(ValueError, match="round.total_miners"):
        RQ003ExecutionContext.from_decision_context(
            source,
            observation_index=1,
            structural_candidate_key=0,
            decision_point_configuration_identity="a" * 64,
        )


def test_definition_views_expose_only_the_exact_declared_square_field() -> None:
    context = make_execution_context()
    deployed_binding = ExecutableMeasurementBinding(
        definition=DEPLOYED_LAMPORTS_DEFINITION,
        terminal_decision=DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        computation=DEPLOYED_LAMPORTS_MEASUREMENT,
    )
    deployed = DefinitionContextView(
        execution_context=context,
        definition=deployed_binding.definition,
        executable_binding_identity=deployed_binding.executable_binding_identity,
    )
    miner_binding = ExecutableMeasurementBinding(
        definition=MINER_COUNT_DEFINITION,
        terminal_decision=MINER_COUNT_ELIGIBILITY_DECISION,
        computation=MINER_COUNT_MEASUREMENT,
    )
    miner = DefinitionContextView(
        execution_context=context,
        definition=miner_binding.definition,
        executable_binding_identity=miner_binding.executable_binding_identity,
    )

    assert isinstance(deployed, FeatureContext)
    assert deployed.square.deployed_lamports == 10_007
    assert miner.square.miner_count == 107
    with pytest.raises(AttributeError, match="square is immutable"):
        deployed.square._values = {}  # type: ignore[attr-defined]
    with pytest.raises(AttributeError, match="ContextView is immutable"):
        deployed.board = None  # type: ignore[misc]
    with pytest.raises(AttributeError, match="undeclared square field"):
        _ = deployed.square.miner_count
    with pytest.raises(AttributeError, match="undeclared square field"):
        _ = miner.square.deployed_lamports
    with pytest.raises(AttributeError, match="undeclared context field"):
        _ = deployed.round
    for prohibited in (
        "board",
        "square_index",
        "square_history",
        "board_history",
        "previous_square",
        "round_progress",
    ):
        with pytest.raises(AttributeError, match="undeclared context field"):
            getattr(deployed, prohibited)


def test_bindings_are_immutable_and_validate_exact_computations() -> None:
    binding = ExecutableMeasurementBinding(
        definition=DEPLOYED_LAMPORTS_DEFINITION,
        terminal_decision=DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        computation=DEPLOYED_LAMPORTS_MEASUREMENT,
    )

    binding.validate()
    with pytest.raises(FrozenInstanceError):
        binding.computation = MINER_COUNT_MEASUREMENT  # type: ignore[misc]
    with pytest.raises(ValueError, match="feature name"):
        ExecutableMeasurementBinding(
            definition=DEPLOYED_LAMPORTS_DEFINITION,
            terminal_decision=DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
            computation=MINER_COUNT_MEASUREMENT,
        )

    deferred = replace(
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        status=FeatureEligibilityStatus.DEFERRED,
    )
    with pytest.raises(ValueError, match="requires an approved decision"):
        ExecutableMeasurementBinding(
            definition=DEPLOYED_LAMPORTS_DEFINITION,
            terminal_decision=deferred,
            computation=DEPLOYED_LAMPORTS_MEASUREMENT,
        )

    tampered = replace(DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION)
    object.__setattr__(tampered, "eligibility_decision_identity", "b" * 64)
    with pytest.raises(ValueError, match="does not reconstruct"):
        ExecutableMeasurementBinding(
            definition=DEPLOYED_LAMPORTS_DEFINITION,
            terminal_decision=tampered,
            computation=DEPLOYED_LAMPORTS_MEASUREMENT,
        )


@pytest.mark.parametrize(
    "path",
    (
        "outcome.winning_square",
        "round.finalized",
        "rfc012.evidence",
        "protocol.revision",
        "round.future_observation",
        "round.unknown_field",
    ),
)
def test_unknown_prohibited_and_future_paths_fail_closed(path: str) -> None:
    metadata = replace(
        DEPLOYED_LAMPORTS_DEFINITION.metadata,
        input_fields=(path,),
    )
    definition = FeatureDefinition(metadata=metadata)

    with pytest.raises(ValueError, match="unsupported context path"):
        DefinitionContextView(
            execution_context=make_execution_context(),
            definition=definition,
            executable_binding_identity="a" * 64,
        )


def test_both_existing_measurements_execute_unchanged_in_registry_order() -> None:
    pipeline = make_pipeline()
    vector = pipeline.compute(make_execution_context())

    assert vector.values == {
        "deployed_lamports": 10_007,
        "miner_count": 107,
    }
    assert tuple(vector.values) == ("deployed_lamports", "miner_count")
    assert vector.ordered_output_fields == (
        DEPLOYED_LAMPORTS_DEFINITION.output_fields
        + MINER_COUNT_DEFINITION.output_fields
    )
    assert vector.ordered_output_owner_definition_identities == (
        DEPLOYED_LAMPORTS_DEFINITION.definition_identity,
        MINER_COUNT_DEFINITION.definition_identity,
    )
    with pytest.raises(TypeError):
        vector.values["miner_count"] = 0  # type: ignore[index]
    with pytest.raises(AttributeError, match="immutable"):
        pipeline._bindings = ()  # type: ignore[attr-defined]


def test_measurement_vector_round_trips_canonically_and_rejects_tampering() -> None:
    vector = make_pipeline().compute(make_execution_context())
    raw = vector.canonical_bytes()
    reconstructed = MeasurementVector.from_canonical_bytes(raw)

    assert reconstructed == vector
    assert reconstructed.canonical_bytes() == raw
    assert reconstructed.reconstruct_vector_identity() == vector.vector_identity
    with pytest.raises(FrozenInstanceError):
        reconstructed.ordered_values = ()  # type: ignore[misc]

    decoded = json.loads(raw)
    decoded["value"]["value"][0][0] = "z_allowed_history_identity"
    with pytest.raises(ValueError):
        MeasurementVector.from_canonical_bytes(
            json.dumps(decoded, separators=(",", ":"), sort_keys=True).encode()
        )


class _UndeclaredAccessMeasurement(Feature):
    name = DEPLOYED_LAMPORTS_MEASUREMENT.name
    family = DEPLOYED_LAMPORTS_MEASUREMENT.family
    output_columns = DEPLOYED_LAMPORTS_MEASUREMENT.output_columns
    metadata = DEPLOYED_LAMPORTS_DEFINITION.metadata
    definition = DEPLOYED_LAMPORTS_DEFINITION

    def compute(self, context: FeatureContext) -> FeatureValues:
        _ = context.square.miner_count
        return MappingProxyType({"deployed_lamports": 1})


def test_undeclared_access_aborts_without_a_partial_vector() -> None:
    catalog = EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=(DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,),
    )
    registry = FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog,
        definitions=(DEPLOYED_LAMPORTS_DEFINITION,),
    )
    pipeline = RQ003MeasurementPipeline(
        registry=registry,
        bindings=(
            ExecutableMeasurementBinding(
                definition=DEPLOYED_LAMPORTS_DEFINITION,
                terminal_decision=DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
                computation=_UndeclaredAccessMeasurement(),
            ),
        ),
    )

    with pytest.raises(AttributeError, match="undeclared square field"):
        pipeline.compute(make_execution_context())


class _InvalidOutputMeasurement(Feature):
    name = MINER_COUNT_MEASUREMENT.name
    family = MINER_COUNT_MEASUREMENT.family
    output_columns = MINER_COUNT_MEASUREMENT.output_columns
    metadata = MINER_COUNT_DEFINITION.metadata
    definition = MINER_COUNT_DEFINITION

    def compute(self, context: FeatureContext) -> FeatureValues:
        return MappingProxyType({"miner_count": True})


def test_late_failure_does_not_return_a_partial_measurement_vector() -> None:
    good_pipeline = make_pipeline()
    registry = object.__getattribute__(good_pipeline, "_registry")
    bindings = object.__getattribute__(good_pipeline, "_bindings")
    failing_pipeline = RQ003MeasurementPipeline(
        registry=registry,
        bindings=(
            bindings[0],
            ExecutableMeasurementBinding(
                definition=MINER_COUNT_DEFINITION,
                terminal_decision=MINER_COUNT_ELIGIBILITY_DECISION,
                computation=_InvalidOutputMeasurement(),
            ),
        ),
    )

    with pytest.raises(TypeError, match="must be an integer"):
        failing_pipeline.compute(make_execution_context())


@pytest.mark.parametrize(
    "invalid_output, message",
    (
        (MappingProxyType({"wrong": 1}), "membership or order"),
        (MappingProxyType({"miner_count": None}), "cannot be null"),
        (MappingProxyType({"miner_count": 1.0}), "must be an integer"),
    ),
)
def test_output_validation_fails_closed(
    invalid_output: FeatureValues,
    message: str,
) -> None:
    class InvalidMeasurement(Feature):
        name = MINER_COUNT_MEASUREMENT.name
        family = MINER_COUNT_MEASUREMENT.family
        output_columns = MINER_COUNT_MEASUREMENT.output_columns
        metadata = MINER_COUNT_DEFINITION.metadata
        definition = MINER_COUNT_DEFINITION

        def compute(self, context: FeatureContext) -> FeatureValues:
            return invalid_output

    valid = make_pipeline()
    registry = object.__getattribute__(valid, "_registry")
    bindings = object.__getattribute__(valid, "_bindings")
    pipeline = RQ003MeasurementPipeline(
        registry=registry,
        bindings=(
            bindings[0],
            ExecutableMeasurementBinding(
                definition=MINER_COUNT_DEFINITION,
                terminal_decision=MINER_COUNT_ELIGIBILITY_DECISION,
                computation=InvalidMeasurement(),
            ),
        ),
    )

    with pytest.raises((TypeError, ValueError), match=message):
        pipeline.compute(make_execution_context())


def test_tampered_context_identity_fails_before_measurement_execution() -> None:
    context = make_execution_context()
    object.__setattr__(context, "decision_snapshot_identity", "b" * 64)

    with pytest.raises(ValueError, match="snapshot identity"):
        make_pipeline().compute(context)


def test_protocol_revision_is_validation_metadata_not_execution_input() -> None:
    context_fields = {item.name for item in fields(RQ003ExecutionContext)}
    vector_fields = {item.name for item in fields(MeasurementVector)}

    assert not any("protocol_revision" in name for name in context_fields)
    assert not any("protocol_revision" in name for name in vector_fields)
    assert all(
        "protocol_revision" not in descriptor.path
        for descriptor in __import__(
            "orev3.features.rq003_execution", fromlist=["RQ003_PATH_DESCRIPTORS"]
        ).RQ003_PATH_DESCRIPTORS
    )


def test_rfc010_decision_context_contract_is_unchanged() -> None:
    assert tuple(item.name for item in fields(DecisionContext)) == (
        "information",
    )


def test_measurement_vector_is_hash_seed_deterministic() -> None:
    repository = Path(__file__).resolve().parents[2]
    script = """
import json
from orev3.features import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    MINER_COUNT_DEFINITION,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_MEASUREMENT,
    EligibilityCatalog,
    ExecutableMeasurementBinding,
    FrozenFeatureRegistry,
    RQ003ExecutionContext,
    RQ003MeasurementPipeline,
)
from orev3.strategy_lab.interfaces import DecisionContext
catalog = EligibilityCatalog(
    catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    decisions=(
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
        MINER_COUNT_ELIGIBILITY_DECISION,
    ),
)
registry = FrozenFeatureRegistry(
    registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    eligibility_catalog=catalog,
    definitions=(DEPLOYED_LAMPORTS_DEFINITION, MINER_COUNT_DEFINITION),
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
    ),
)
context = RQ003ExecutionContext(
    decision_context=DecisionContext(information={
        'round_id': 4321,
        'board': {'round_id': 4321, 'production_cost_ema': 55000},
        'treasury': {'motherlode': 987654},
        'round': {
            'round_id': 4321,
            'deployed_lamports': tuple(range(25)),
            'miner_counts': tuple(range(100, 125)),
            'total_miners': 777,
            'motherlode': 0,
            'total_vaulted': 123456,
        },
    }),
    observation_index=4,
    structural_candidate_key=7,
    decision_point_configuration_identity='a' * 64,
)
vector = pipeline.compute(context)
print(json.dumps({
    'bytes': vector.canonical_bytes().hex(),
    'identity': vector.vector_identity,
}))
"""
    outputs = []
    for seed in ("1", "947"):
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(repository / "src")
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repository,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))

    assert outputs[0] == outputs[1]


def test_phase_scope_exports_only_execution_contracts() -> None:
    import orev3.features.rq003_execution as execution

    prohibited_fragments = (
        "Dataset",
        "Baseline",
        "Ranking",
        "Strategy",
        "FeatureSet",
    )
    assert not any(
        fragment in name
        for name in execution.__all__
        for fragment in prohibited_fragments
    )
