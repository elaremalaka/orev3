from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

import orev3.strategy_lab.constraints as constraints
from orev3.strategy_lab import (
    BudgetModel,
    CapitalReserveRules,
    CheckpointAssumptions,
    CheckpointState,
    ComponentIdentities,
    EconomicScenario,
    FeeAssumptions,
    LamportApportionmentRule,
    MissingOutcomePolicy,
    OutcomePolicy,
    ParticipantEconomicState,
    ProtocolConstraintCode,
    ProtocolConstraintModel,
    ProtocolConstraintViolation,
    ProtocolDeploymentPlan,
    ProtocolRejection,
    TransactionAssumptions,
)


PROTOCOL_REVISION = "ore-v3-program-3112ab78"


def test_valid_vector_produces_immutable_protocol_deployment_plan() -> None:
    vector = _vector({3: 25, 9: 50})
    state = _state(available=200, current_round=17)

    result = _model().validate(vector, _scenario(), state)

    assert isinstance(result, ProtocolDeploymentPlan)
    assert result.deployed_lamports == vector
    assert result.total_deployed_lamports == 75
    assert result.occupied_square_count == 2
    assert result.square_identifiers == tuple(range(25))
    assert result.protocol_revision == PROTOCOL_REVISION
    assert result.round_identifier == 17
    assert result.scenario_identity == _scenario().scenario_identity
    assert result.participant_state_identity == state.state_identity
    with pytest.raises(FrozenInstanceError):
        result.total_deployed_lamports = 0  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.deployed_lamports[3] = 0  # type: ignore[index]


def test_zero_deployment_is_pre_transaction_feasible() -> None:
    result = _model().validate(_vector({}), _scenario(), _state())

    assert isinstance(result, ProtocolDeploymentPlan)
    assert result.total_deployed_lamports == 0
    assert result.occupied_square_count == 0


def test_vector_must_be_one_immutable_twenty_five_position_tuple() -> None:
    model = _model()
    scenario = _scenario()
    state = _state()

    mutable = model.validate([0] * 25, scenario, state)  # type: ignore[arg-type]
    short = model.validate((0,) * 24, scenario, state)
    long = model.validate((0,) * 26, scenario, state)

    assert _codes(mutable) == {
        ProtocolConstraintCode.DEPLOYMENT_VECTOR_TYPE,
    }
    assert _codes(short) == {
        ProtocolConstraintCode.DEPLOYMENT_VECTOR_LENGTH,
    }
    assert _codes(long) == {
        ProtocolConstraintCode.DEPLOYMENT_VECTOR_LENGTH,
        ProtocolConstraintCode.INVALID_SQUARE_IDENTIFIER,
    }
    assert _violation(long, ProtocolConstraintCode.INVALID_SQUARE_IDENTIFIER).square_identifiers == (25,)


def test_deployed_values_must_be_positive_integer_lamports_or_zero() -> None:
    values: list[object] = [0] * 25
    values[2] = 1.5
    values[4] = True
    values[7] = -1

    result = _model().validate(tuple(values), _scenario(), _state())  # type: ignore[arg-type]

    assert _codes(result) == {
        ProtocolConstraintCode.DEPLOYMENT_LAMPORT_TYPE,
        ProtocolConstraintCode.DEPLOYMENT_LAMPORT_NEGATIVE,
    }
    assert _violation(
        result,
        ProtocolConstraintCode.DEPLOYMENT_LAMPORT_TYPE,
    ).square_identifiers == (2, 4)
    assert _violation(
        result,
        ProtocolConstraintCode.DEPLOYMENT_LAMPORT_NEGATIVE,
    ).square_identifiers == (7,)


def test_positional_vector_has_unique_valid_square_ownership() -> None:
    result = _model().validate(
        tuple(range(25)),
        _scenario(budget=1_000),
        _state(available=2_000),
    )

    assert isinstance(result, ProtocolDeploymentPlan)
    assert len(result.square_identifiers) == len(set(result.square_identifiers))
    assert result.square_identifiers == tuple(range(25))


def test_occupied_authority_round_square_cannot_be_redeployed() -> None:
    state = _state(
        available=200,
        deployed=_vector({6: 10, 8: 5}),
    )

    result = _model().validate(
        _vector({6: 1, 7: 1, 8: 1}),
        _scenario(),
        state,
    )

    assert _codes(result) == {ProtocolConstraintCode.OCCUPIED_SQUARE}
    assert _violation(
        result,
        ProtocolConstraintCode.OCCUPIED_SQUARE,
    ).square_identifiers == (6, 8)


def test_authority_state_identity_must_remain_self_consistent() -> None:
    state = _state()
    object.__setattr__(state, "available_sol_lamports", 999)

    result = _model().validate(_vector({}), _scenario(), state)

    assert ProtocolConstraintCode.AUTHORITY_STATE_INCONSISTENT in _codes(result)


@pytest.mark.parametrize(
    ("current_round", "last_settled", "corrupt_last_settled"),
    (
        (None, 16, None),
        (10, 9, 11),
    ),
)
def test_current_round_must_be_present_and_consistent(
    current_round: int | None,
    last_settled: int | None,
    corrupt_last_settled: int | None,
) -> None:
    state = _state(
        current_round=current_round,
        last_settled=last_settled,
    )
    if corrupt_last_settled is not None:
        object.__setattr__(
            state,
            "last_economically_settled_round",
            corrupt_last_settled,
        )

    result = _model().validate(_vector({}), _scenario(), state)

    assert ProtocolConstraintCode.CURRENT_ROUND_INCONSISTENT in _codes(result)


def test_required_checkpoint_rejects_deployment() -> None:
    result = _model().validate(
        _vector({1: 10}),
        _scenario(),
        _state(checkpoint=CheckpointState.REQUIRED),
    )

    assert ProtocolConstraintCode.CHECKPOINT_REQUIRED in _codes(result)


def test_completed_or_not_required_checkpoint_is_eligible() -> None:
    for checkpoint in (CheckpointState.COMPLETED, CheckpointState.NOT_REQUIRED):
        result = _model().validate(
            _vector({1: 10}),
            _scenario(),
            _state(checkpoint=checkpoint),
        )
        assert isinstance(result, ProtocolDeploymentPlan)


def test_protocol_revision_must_match_selected_model() -> None:
    result = ProtocolConstraintModel(
        protocol_revision="ore-v3-program-successor",
    ).validate(_vector({}), _scenario(), _state())

    assert _codes(result) == {
        ProtocolConstraintCode.PROTOCOL_REVISION_MISMATCH,
    }


def test_available_balance_required_reserves_and_budget_are_distinct() -> None:
    scenario = _scenario(budget=100)

    balance = _model().validate(
        _vector({1: 100}),
        scenario,
        _state(available=90),
    )
    reserve = _model().validate(
        _vector({1: 100}),
        scenario,
        _state(available=105),
    )
    budget = _model().validate(
        _vector({1: 101}),
        scenario,
        _state(available=200),
    )

    assert ProtocolConstraintCode.AVAILABLE_BALANCE_EXCEEDED in _codes(balance)
    assert ProtocolConstraintCode.CAPITAL_RESERVE_INSUFFICIENT in _codes(balance)
    assert _codes(reserve) == {
        ProtocolConstraintCode.CAPITAL_RESERVE_INSUFFICIENT,
    }
    assert _codes(budget) == {
        ProtocolConstraintCode.DEPLOYMENT_BUDGET_EXCEEDED,
    }


def test_rejection_aggregates_every_independent_failed_constraint() -> None:
    state = _state(
        available=5,
        deployed=_vector({1: 1}),
        checkpoint=CheckpointState.REQUIRED,
    )
    object.__setattr__(state, "state_identity", "stale-state-identity")
    result = ProtocolConstraintModel("wrong-revision").validate(
        _vector({1: 101}),
        _scenario(budget=100),
        state,
    )

    assert isinstance(result, ProtocolRejection)
    assert _codes(result) == {
        ProtocolConstraintCode.OCCUPIED_SQUARE,
        ProtocolConstraintCode.AUTHORITY_STATE_INCONSISTENT,
        ProtocolConstraintCode.CHECKPOINT_REQUIRED,
        ProtocolConstraintCode.PROTOCOL_REVISION_MISMATCH,
        ProtocolConstraintCode.AVAILABLE_BALANCE_EXCEEDED,
        ProtocolConstraintCode.CAPITAL_RESERVE_INSUFFICIENT,
        ProtocolConstraintCode.DEPLOYMENT_BUDGET_EXCEEDED,
    }
    assert len(result.violations) == 7


def test_rejection_and_violations_are_deeply_immutable() -> None:
    result = _model().validate(
        _vector({1: 101}),
        _scenario(budget=100),
        _state(available=200),
    )

    assert isinstance(result, ProtocolRejection)
    with pytest.raises(FrozenInstanceError):
        result.scenario_identity = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.violations[0].message = "changed"  # type: ignore[misc]


def test_validation_never_mutates_input_vector_scenario_or_state() -> None:
    vector = _vector({2: 10})
    scenario = _scenario()
    state = _state()
    before = (vector, scenario.scenario_identity, state.state_identity)

    first = _model().validate(vector, scenario, state)
    second = _model().validate(vector, scenario, state)

    assert first == second
    assert before == (vector, scenario.scenario_identity, state.state_identity)


def test_wrong_model_inputs_fail_at_the_public_boundary() -> None:
    with pytest.raises(ValueError, match="protocol_revision"):
        ProtocolConstraintModel("")
    with pytest.raises(TypeError, match="EconomicScenario"):
        _model().validate(_vector({}), object(), _state())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="ParticipantEconomicState"):
        _model().validate(_vector({}), _scenario(), object())  # type: ignore[arg-type]


def test_phase_three_does_not_expose_later_phase_implementations() -> None:
    forbidden = (
        "TransactionModel",
        "InclusionModel",
        "Settlement",
        "EconomicSimulationRunner",
        "EconomicMetrics",
        "EconomicSimulationRecord",
    )

    assert all(not hasattr(constraints, name) for name in forbidden)


def _codes(
    result: ProtocolDeploymentPlan | ProtocolRejection,
) -> set[ProtocolConstraintCode]:
    assert isinstance(result, ProtocolRejection)
    return {violation.code for violation in result.violations}


def _violation(
    result: ProtocolDeploymentPlan | ProtocolRejection,
    code: ProtocolConstraintCode,
) -> ProtocolConstraintViolation:
    assert isinstance(result, ProtocolRejection)
    return next(value for value in result.violations if value.code is code)


def _vector(values: dict[int, int]) -> tuple[int, ...]:
    result = [0] * 25
    for square, amount in values.items():
        result[square] = amount
    return tuple(result)


def _state(
    *,
    available: int = 200,
    deployed: tuple[int, ...] | None = None,
    checkpoint: CheckpointState = CheckpointState.NOT_REQUIRED,
    current_round: int | None = 17,
    last_settled: int | None = 16,
) -> ParticipantEconomicState:
    return ParticipantEconomicState(
        available_sol_lamports=available,
        accrued_sol_lamports=0,
        accrued_ore=0,
        deployed_lamports=deployed or _vector({}),
        checkpoint_state=checkpoint,
        cumulative_protocol_costs_lamports=0,
        cumulative_transaction_costs_lamports=0,
        current_round=current_round,
        last_economically_settled_round=last_settled,
    )


def _model() -> ProtocolConstraintModel:
    return ProtocolConstraintModel(protocol_revision=PROTOCOL_REVISION)


def _scenario(*, budget: int = 100) -> EconomicScenario:
    return EconomicScenario(
        protocol_revision=PROTOCOL_REVISION,
        budget=BudgetModel(
            participant_initial_sol_balance_lamports=budget + 20,
            per_round_deployment_budget_lamports=budget,
            capital_reserve_rules=CapitalReserveRules(10, 1, 2),
        ),
        lamport_apportionment_rule=(
            LamportApportionmentRule
            .LARGEST_REMAINDER_CANDIDATE_ORDER_V1
        ),
        fee_assumptions=FeeAssumptions(1, 0, 1, 1),
        checkpoint_assumptions=CheckpointAssumptions(True, 1),
        transaction_assumptions=TransactionAssumptions(1_232, 200_000, 8, 1),
        outcome_policy=OutcomePolicy(
            accepted_sources=("observed", "enriched"),
            missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
            require_contiguous_outcomes=True,
        ),
        replay_identity="replay-v1",
        dataset_identity="dataset-v1",
        component_identities=ComponentIdentities(
            allocation_materializer="rfc011-allocation-materializer-v1",
            protocol_constraint_model="rfc011-constraints-v1",
            transaction_model="rfc011-transactions-v1",
            inclusion_model="rfc011-inclusion-v1",
            settlement_model="rfc011-settlement-v1",
            simulation_runner="rfc011-runner-v1",
            metrics_engine="rfc011-metrics-v1",
        ),
    )
