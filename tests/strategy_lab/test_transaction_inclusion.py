from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

import orev3.strategy_lab.transactions as transactions_module
from orev3.strategy_lab import (
    BudgetModel,
    CapitalReserveRules,
    CheckpointAssumptions,
    ComponentIdentities,
    DeployInstruction,
    EconomicScenario,
    FeeAssumptions,
    InclusionModel,
    LamportApportionmentRule,
    MissingOutcomePolicy,
    OutcomePolicy,
    PlannedTransaction,
    ProtocolDeploymentPlan,
    TransactionAssumptions,
    TransactionInclusionResult,
    TransactionInclusionStatus,
    TransactionModel,
    TransactionPlan,
    TransactionViolationCode,
)


PROTOCOL_REVISION = "ore-v3-program-3112ab78"


def test_equal_amounts_pack_into_one_mask_and_different_amounts_do_not() -> None:
    scenario = _scenario(maximum_instructions=4)
    deployment = _deployment(scenario, {0: 10, 1: 20, 2: 10})

    plan = _model().plan(deployment, scenario, decision_slot=100)

    assert plan.is_feasible
    assert len(plan.instructions) == 2
    first, second = plan.instructions
    assert first.amount_lamports == 10
    assert first.square_identifiers == (0, 2)
    assert first.square_mask == (1 << 0) | (1 << 2)
    assert second.amount_lamports == 20
    assert second.square_identifiers == (1,)
    assert second.square_mask == 1 << 1
    assert plan.transaction_count == 1
    assert plan.transactions[0].instructions == plan.instructions
    assert plan.transactions[0].assumed_size_bytes == 280
    assert plan.transactions[0].assumed_compute_units == 110_000


def test_grouping_fees_and_scheduling_are_deterministic() -> None:
    scenario = _scenario(maximum_instructions=1)
    deployment = _deployment(scenario, {0: 10, 1: 20, 2: 10})

    first = _model().plan(deployment, scenario, decision_slot=100)
    second = _model().plan(deployment, scenario, decision_slot=100)

    assert first == second
    assert first.transaction_plan_identity == second.transaction_plan_identity
    assert first.transaction_count == 2
    assert tuple(
        value.assumed_submission_slot for value in first.transactions
    ) == (101, 102)
    assert tuple(
        value.assumed_inclusion_slot for value in first.transactions
    ) == (103, 104)
    assert first.planned_transaction_fees_lamports == 20
    assert first.planned_priority_fees_lamports == 4


def test_included_result_preserves_plan_timing_costs_and_identity() -> None:
    scenario = _scenario(maximum_instructions=1)
    deployment = _deployment(scenario, {0: 10, 1: 20})
    plan = _model().plan(deployment, scenario, decision_slot=100)

    result = _inclusion().evaluate(
        plan,
        scenario,
        round_deadline_slot=105,
    )

    assert isinstance(result, TransactionInclusionResult)
    assert result.status is TransactionInclusionStatus.INCLUDED
    assert result.included is True
    assert result.transaction_plan_identity == plan.transaction_plan_identity
    assert result.assumed_submission_slots == (101, 102)
    assert result.assumed_inclusion_slots == (103, 104)
    assert result.modeled_transaction_costs_lamports == 20
    assert result.modeled_priority_costs_lamports == 4
    assert result.rejection_reasons == ()
    assert result.result_identity.startswith(
        "rfc011-transaction-inclusion-result-sha256:"
    )


def test_deadline_is_exclusive_and_unincluded_costs_are_modeled() -> None:
    scenario = _scenario(maximum_instructions=1)
    deployment = _deployment(scenario, {0: 10, 1: 20})
    plan = _model().plan(deployment, scenario, decision_slot=100)

    result = _inclusion().evaluate(
        plan,
        scenario,
        round_deadline_slot=104,
    )

    assert result.status is TransactionInclusionStatus.UNINCLUDED
    assert result.included is False
    assert _codes(result) == {TransactionViolationCode.ROUND_DEADLINE_REACHED}
    reason = result.rejection_reasons[0]
    assert reason.transaction_sequence_numbers == (2,)
    assert result.modeled_transaction_costs_lamports == 14
    assert result.modeled_priority_costs_lamports == 0


def test_zero_deployment_requires_no_instruction_transaction_or_fee() -> None:
    scenario = _scenario()
    deployment = _deployment(scenario, {})

    plan = _model().plan(deployment, scenario, decision_slot=100)
    result = _inclusion().evaluate(
        plan,
        scenario,
        round_deadline_slot=101,
    )

    assert plan.instructions == ()
    assert plan.transactions == ()
    assert plan.transaction_count == 0
    assert plan.planned_transaction_fees_lamports == 0
    assert plan.planned_priority_fees_lamports == 0
    assert result.included
    assert result.assumed_submission_slots == ()
    assert result.assumed_inclusion_slots == ()
    assert result.modeled_transaction_costs_lamports == 0


def test_size_and_compute_failures_report_every_intrinsic_reason() -> None:
    scenario = _scenario(
        maximum_size=230,
        compute_limit=55_000,
        instruction_size=40,
        instruction_compute=50_000,
    )
    deployment = _deployment(scenario, {0: 10})

    plan = _model().plan(deployment, scenario, decision_slot=100)
    result = _inclusion().evaluate(
        plan,
        scenario,
        round_deadline_slot=200,
    )

    assert not plan.is_feasible
    assert plan.transactions == ()
    assert {value.code for value in plan.violations} == {
        TransactionViolationCode.INSTRUCTION_SIZE_EXCEEDED,
        TransactionViolationCode.INSTRUCTION_COMPUTE_EXCEEDED,
    }
    assert _codes(result) == {
        TransactionViolationCode.INSTRUCTION_SIZE_EXCEEDED,
        TransactionViolationCode.INSTRUCTION_COMPUTE_EXCEEDED,
    }
    assert result.modeled_transaction_costs_lamports == 0


def test_grouping_uses_size_compute_and_instruction_limits() -> None:
    scenario = _scenario(
        maximum_instructions=8,
        maximum_size=280,
        compute_limit=110_000,
    )
    deployment = _deployment(scenario, {0: 10, 1: 20, 2: 30})

    plan = _model().plan(deployment, scenario, decision_slot=10)

    assert plan.is_feasible
    assert tuple(len(value.instructions) for value in plan.transactions) == (
        2,
        1,
    )
    assert all(
        value.assumed_size_bytes <= 280 for value in plan.transactions
    )
    assert all(
        value.assumed_compute_units <= 110_000
        for value in plan.transactions
    )


def test_transaction_cost_reserve_exhaustion_fails_closed() -> None:
    scenario = _scenario(maximum_instructions=1, transaction_reserve=12)
    deployment = _deployment(scenario, {0: 10, 1: 20})

    plan = _model().plan(deployment, scenario, decision_slot=10)
    result = _inclusion().evaluate(
        plan,
        scenario,
        round_deadline_slot=20,
    )

    assert {value.code for value in plan.violations} == {
        TransactionViolationCode.TRANSACTION_COST_RESERVE_EXCEEDED,
    }
    assert _codes(result) == {
        TransactionViolationCode.TRANSACTION_COST_RESERVE_EXCEEDED,
    }
    assert not result.included


def test_scenario_protocol_and_component_identity_mismatches_fail_closed() -> None:
    scenario = _scenario()
    deployment = _deployment(scenario, {0: 10})
    changed_scenario = replace(
        scenario,
        replay_identity="replay-v2",
    )
    object.__setattr__(deployment, "protocol_revision", "ore-v3-other")

    plan = TransactionModel("wrong-transaction-model").plan(
        deployment,
        changed_scenario,
        decision_slot=10,
    )
    result = InclusionModel("wrong-inclusion-model").evaluate(
        plan,
        changed_scenario,
        round_deadline_slot=20,
    )

    assert {value.code for value in plan.violations} == {
        TransactionViolationCode.PROTOCOL_REVISION_MISMATCH,
        TransactionViolationCode.SCENARIO_IDENTITY_MISMATCH,
        TransactionViolationCode.TRANSACTION_MODEL_IDENTITY_MISMATCH,
    }
    assert _codes(result) == {
        TransactionViolationCode.PROTOCOL_REVISION_MISMATCH,
        TransactionViolationCode.SCENARIO_IDENTITY_MISMATCH,
        TransactionViolationCode.TRANSACTION_MODEL_IDENTITY_MISMATCH,
        TransactionViolationCode.INCLUSION_MODEL_IDENTITY_MISMATCH,
    }


def test_transaction_model_evaluate_runs_the_offline_combined_boundary() -> None:
    scenario = _scenario()
    deployment = _deployment(scenario, {4: 25, 9: 25})

    result = _model().evaluate(
        deployment,
        scenario,
        decision_slot=100,
        round_deadline_slot=104,
    )

    assert result.included
    assert result.assumed_submission_slots == (101,)
    assert result.assumed_inclusion_slots == (103,)


def test_phase_four_artifacts_are_deeply_immutable() -> None:
    scenario = _scenario()
    plan = _model().plan(
        _deployment(scenario, {0: 10}),
        scenario,
        decision_slot=1,
    )
    result = _inclusion().evaluate(
        plan,
        scenario,
        round_deadline_slot=10,
    )

    with pytest.raises(FrozenInstanceError):
        plan.decision_slot = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        plan.instructions[0].amount_lamports = 1  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.status = TransactionInclusionStatus.UNINCLUDED  # type: ignore[misc]


def test_supporting_artifacts_validate_internal_consistency() -> None:
    instruction = DeployInstruction(10, (0, 2), 5, 40, 50_000)
    with pytest.raises(ValueError, match="square_mask"):
        replace(instruction, square_mask=1)
    with pytest.raises(ValueError, match="unique and ascending"):
        replace(instruction, square_identifiers=(2, 0))

    transaction = PlannedTransaction(1, (instruction,), 240, 60_000, 1, 2)
    with pytest.raises(ValueError, match="cannot precede"):
        replace(transaction, assumed_inclusion_slot=0)


def test_public_boundaries_reject_wrong_types_and_slots() -> None:
    scenario = _scenario()
    deployment = _deployment(scenario, {0: 10})
    with pytest.raises(TypeError, match="ProtocolDeploymentPlan"):
        _model().plan(object(), scenario, decision_slot=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="EconomicScenario"):
        _model().plan(deployment, object(), decision_slot=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nonnegative integer"):
        _model().plan(deployment, scenario, decision_slot=-1)
    with pytest.raises(TypeError, match="TransactionPlan"):
        _inclusion().evaluate(  # type: ignore[arg-type]
            object(),
            scenario,
            round_deadline_slot=1,
        )
    plan = _model().plan(deployment, scenario, decision_slot=1)
    with pytest.raises(ValueError, match="nonnegative integer"):
        _inclusion().evaluate(plan, scenario, round_deadline_slot=False)


def test_phase_four_module_contains_no_later_phase_functionality() -> None:
    forbidden = (
        "Settlement",
        "ParticipantStateTransition",
        "EconomicSimulationRunner",
        "EconomicMetrics",
        "EconomicSimulationRecord",
    )

    assert all(
        not hasattr(transactions_module, name) for name in forbidden
    )


def _codes(
    result: TransactionInclusionResult,
) -> set[TransactionViolationCode]:
    return {value.code for value in result.rejection_reasons}


def _model() -> TransactionModel:
    return TransactionModel("rfc011-transactions-v1")


def _inclusion() -> InclusionModel:
    return InclusionModel("rfc011-inclusion-v1")


def _deployment(
    scenario: EconomicScenario,
    amounts: dict[int, int],
) -> ProtocolDeploymentPlan:
    vector = [0] * 25
    for square, amount in amounts.items():
        vector[square] = amount
    return ProtocolDeploymentPlan(
        deployed_lamports=tuple(vector),
        total_deployed_lamports=sum(vector),
        occupied_square_count=sum(value > 0 for value in vector),
        protocol_revision=scenario.protocol_revision,
        scenario_identity=scenario.scenario_identity,
        participant_state_identity="participant-state-v1",
        round_identifier=17,
    )


def _scenario(
    *,
    maximum_instructions: int = 4,
    maximum_size: int = 1_232,
    compute_limit: int = 200_000,
    instruction_size: int = 40,
    instruction_compute: int = 50_000,
    transaction_reserve: int = 100,
) -> EconomicScenario:
    return EconomicScenario(
        protocol_revision=PROTOCOL_REVISION,
        budget=BudgetModel(
            participant_initial_sol_balance_lamports=(
                1_000 + 10 + transaction_reserve + 2
            ),
            per_round_deployment_budget_lamports=1_000,
            capital_reserve_rules=CapitalReserveRules(
                minimum_liquid_reserve_lamports=10,
                transaction_cost_reserve_lamports=transaction_reserve,
                checkpoint_cost_reserve_lamports=2,
            ),
        ),
        lamport_apportionment_rule=(
            LamportApportionmentRule
            .LARGEST_REMAINDER_CANDIDATE_ORDER_V1
        ),
        fee_assumptions=FeeAssumptions(
            base_transaction_fee_lamports=10,
            priority_fee_lamports=2,
            failed_transaction_fee_lamports=7,
            checkpoint_transaction_fee_lamports=1,
        ),
        checkpoint_assumptions=CheckpointAssumptions(True, 1),
        transaction_assumptions=TransactionAssumptions(
            maximum_transaction_size_bytes=maximum_size,
            compute_unit_limit=compute_limit,
            maximum_instructions_per_transaction=maximum_instructions,
            inclusion_latency_slots=2,
            transaction_base_size_bytes=200,
            deploy_instruction_size_bytes=instruction_size,
            transaction_base_compute_units=10_000,
            deploy_instruction_compute_units=instruction_compute,
            maximum_transactions_per_slot=1,
            submission_delay_slots=1,
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
