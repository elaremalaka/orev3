from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import orev3.strategy_lab.materialization as materialization
from orev3.strategy_lab import (
    AllocationMaterializer,
    BudgetModel,
    CapitalReserveRules,
    CheckpointAssumptions,
    ComponentIdentities,
    DeploymentAllocation,
    DeploymentDecision,
    EconomicScenario,
    FeeAssumptions,
    LamportApportionmentRule,
    MissingOutcomePolicy,
    OutcomePolicy,
    TransactionAssumptions,
)


def test_materializer_applies_full_budget_to_top_ranked_square() -> None:
    result = AllocationMaterializer().materialize(
        DeploymentDecision((DeploymentAllocation(7, 1.0, 1.0),)),
        _scenario(budget_lamports=101),
    )

    assert len(result) == 25
    assert result[7] == 101
    assert sum(result) == 101
    assert all(value == 0 for index, value in enumerate(result) if index != 7)


def test_largest_remainder_uses_candidate_order_for_equal_remainders() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(8, 1 / 3, 1 / 3),
            DeploymentAllocation(2, 1 / 3, 1 / 3),
            DeploymentAllocation(5, 1 / 3, 1 / 3),
        )
    )

    result = AllocationMaterializer().materialize(
        decision,
        _scenario(budget_lamports=10),
    )

    assert (result[8], result[2], result[5]) == (4, 3, 3)
    assert sum(result) == 10


def test_equal_weight_twenty_five_square_decision_is_deterministic() -> None:
    allocations = tuple(
        DeploymentAllocation(square, 1 / 25, 1 / 25)
        for square in reversed(range(25))
    )
    decision = DeploymentDecision(allocations)
    materializer = AllocationMaterializer()
    scenario = _scenario(budget_lamports=101)

    first = materializer.materialize(decision, scenario)
    second = materializer.materialize(decision, scenario)

    assert first == second
    assert first[24] == 5
    assert sum(value == 4 for value in first) == 24
    assert sum(first) == 101


def test_partial_budget_share_preserves_undeployed_lamports() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(9, 0.3, 0.6),
            DeploymentAllocation(1, 0.2, 0.4),
        )
    )

    result = AllocationMaterializer().materialize(
        decision,
        _scenario(budget_lamports=10),
    )

    assert result[9] == 3
    assert result[1] == 2
    assert sum(result) == 5


def test_fractional_partial_budget_is_floored_before_apportionment() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(4, 0.25, 0.5),
            DeploymentAllocation(3, 0.25, 0.5),
        )
    )

    result = AllocationMaterializer().materialize(
        decision,
        _scenario(budget_lamports=7),
    )

    assert result[4] == 2
    assert result[3] == 1
    assert sum(result) == 3


def test_empty_and_explicit_zero_allocations_produce_zero_vector() -> None:
    materializer = AllocationMaterializer()
    scenario = _scenario()

    empty = materializer.materialize(DeploymentDecision(()), scenario)
    explicit = materializer.materialize(
        DeploymentDecision(
            (
                DeploymentAllocation(2, 0.0, 0.0),
                DeploymentAllocation(8, 0.0, 0.0),
            )
        ),
        scenario,
    )

    assert empty == explicit == (0,) * 25


@pytest.mark.parametrize(
    "allocations",
    (
        (
            DeploymentAllocation(1, 0.4, 0.4),
            DeploymentAllocation(2, 0.3, 0.6),
        ),
        (DeploymentAllocation(1, 0.5, 0.0),),
        (DeploymentAllocation(1, 0.0, 0.5),),
    ),
)
def test_inconsistent_amount_and_weight_fail_closed(
    allocations: tuple[DeploymentAllocation, ...],
) -> None:
    with pytest.raises(ValueError, match="inconsistent|requires"):
        AllocationMaterializer().materialize(
            DeploymentDecision(allocations),
            _scenario(),
        )


def test_total_allocation_above_one_fails_closed() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(1, 0.6, 0.5),
            DeploymentAllocation(2, 0.6, 0.5),
        )
    )

    with pytest.raises(ValueError, match="must not exceed one"):
        AllocationMaterializer().materialize(decision, _scenario())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("allocation_amount", -0.1, "finite and nonnegative"),
        ("allocation_amount", float("nan"), "finite and nonnegative"),
        ("allocation_amount", float("inf"), "finite and nonnegative"),
        ("allocation_weight", -0.1, "finite and nonnegative"),
        ("allocation_weight", float("nan"), "finite and nonnegative"),
        ("allocation_weight", float("inf"), "finite and nonnegative"),
        ("allocation_weight", 1.1, "at most 1"),
    ),
)
def test_materializer_defensively_rejects_corrupted_numeric_values(
    field: str,
    value: float,
    message: str,
) -> None:
    allocation = DeploymentAllocation(1, 1.0, 1.0)
    object.__setattr__(allocation, field, value)

    with pytest.raises(ValueError, match=message):
        AllocationMaterializer().materialize(
            DeploymentDecision((allocation,)),
            _scenario(),
        )


def test_materializer_defensively_rejects_invalid_or_duplicate_squares() -> None:
    invalid = DeploymentAllocation(1, 1.0, 1.0)
    object.__setattr__(invalid, "square_identifier", 25)
    with pytest.raises(ValueError, match="between 0 and 24"):
        AllocationMaterializer().materialize(
            DeploymentDecision((invalid,)),
            _scenario(),
        )

    first = DeploymentAllocation(1, 0.5, 0.5)
    second = DeploymentAllocation(2, 0.5, 0.5)
    decision = DeploymentDecision((first, second))
    object.__setattr__(second, "square_identifier", 1)
    with pytest.raises(ValueError, match="duplicate square"):
        AllocationMaterializer().materialize(decision, _scenario())


def test_positive_share_that_cannot_receive_one_lamport_is_rejected() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(1, 0.5, 0.5),
            DeploymentAllocation(2, 0.5, 0.5),
        )
    )

    with pytest.raises(ValueError, match="unrepresentable in lamports"):
        AllocationMaterializer().materialize(
            decision,
            _scenario(budget_lamports=1),
        )


def test_unknown_apportionment_rule_fails_closed() -> None:
    scenario = _scenario()
    object.__setattr__(
        scenario,
        "lamport_apportionment_rule",
        "unknown",
    )

    with pytest.raises(ValueError, match="unsupported"):
        AllocationMaterializer().materialize(
            DeploymentDecision((DeploymentAllocation(1, 1.0, 1.0),)),
            scenario,
        )


def test_materializer_rejects_wrong_input_types() -> None:
    materializer = AllocationMaterializer()

    with pytest.raises(TypeError, match="DeploymentDecision"):
        materializer.materialize(object(), _scenario())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="EconomicScenario"):
        materializer.materialize(
            DeploymentDecision(()),
            object(),  # type: ignore[arg-type]
        )


def test_materializer_and_result_are_immutable() -> None:
    materializer = AllocationMaterializer()
    result = materializer.materialize(
        DeploymentDecision((DeploymentAllocation(1, 1.0, 1.0),)),
        _scenario(),
    )

    with pytest.raises(FrozenInstanceError):
        materializer.extra = True  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        result[1] = 0  # type: ignore[index]


def test_phase_two_does_not_expose_later_phase_implementations() -> None:
    forbidden = (
        "ProtocolConstraintModel",
        "TransactionModel",
        "InclusionModel",
        "Settlement",
        "EconomicSimulationRunner",
        "EconomicMetrics",
        "EconomicSimulationRecord",
    )

    assert all(not hasattr(materialization, name) for name in forbidden)


def _scenario(*, budget_lamports: int = 100) -> EconomicScenario:
    fees = FeeAssumptions(
        base_transaction_fee_lamports=1,
        priority_fee_lamports=0,
        failed_transaction_fee_lamports=1,
        checkpoint_transaction_fee_lamports=1,
    )
    checkpoint = CheckpointAssumptions(
        required_before_next_round=True,
        protocol_checkpoint_reserve_lamports=1,
    )
    return EconomicScenario(
        protocol_revision="ore-v3-program-3112ab78",
        budget=BudgetModel(
            participant_initial_sol_balance_lamports=budget_lamports + 20,
            per_round_deployment_budget_lamports=budget_lamports,
            capital_reserve_rules=CapitalReserveRules(
                minimum_liquid_reserve_lamports=10,
                transaction_cost_reserve_lamports=1,
                checkpoint_cost_reserve_lamports=2,
            ),
        ),
        lamport_apportionment_rule=(
            LamportApportionmentRule
            .LARGEST_REMAINDER_CANDIDATE_ORDER_V1
        ),
        fee_assumptions=fees,
        checkpoint_assumptions=checkpoint,
        transaction_assumptions=TransactionAssumptions(
            maximum_transaction_size_bytes=1_232,
            compute_unit_limit=200_000,
            maximum_instructions_per_transaction=8,
            inclusion_latency_slots=1,
            transaction_base_size_bytes=200,
            deploy_instruction_size_bytes=40,
            transaction_base_compute_units=10_000,
            deploy_instruction_compute_units=50_000,
            maximum_transactions_per_slot=2,
            submission_delay_slots=0,
        ),
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
