from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

import orev3.strategy_lab.settlement as settlement_module
from orev3.strategy_lab import (
    BudgetModel,
    CapitalReserveRules,
    CheckpointAssumptions,
    CheckpointState,
    ComponentIdentities,
    DeploymentAllocation,
    DeploymentDecision,
    EconomicRoundStatus,
    EconomicScenario,
    EvaluationObservation,
    EvaluationResult,
    Evaluator,
    FeeAssumptions,
    FinalizedReplayFacts,
    LamportApportionmentRule,
    MissingOutcomePolicy,
    ORERewardTreatment,
    ORESettlementModel,
    OutcomePolicy,
    ParticipantEconomicState,
    ProtocolConstraintCode,
    ProtocolConstraintViolation,
    ProtocolDeploymentPlan,
    ProtocolRejection,
    SPLIT_REWARD_ADDRESS,
    SettlementRejectionCode,
    TransactionAssumptions,
    TransactionModel,
)


PROTOCOL_REVISION = "ore-v3-program-3112ab78"


def test_split_settlement_recomputes_counterfactual_pool_and_state() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100, 4: 100})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 2, (2, 4))
    facts = _facts(
        entropy=2,
        winner=2,
        top_miner=SPLIT_REWARD_ADDRESS,
    )

    result = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )

    assert result.status is EconomicRoundStatus.SETTLED
    assert result.rejection_reasons == ()
    assert result.deployed_sol_lamports == 200
    assert result.counterfactual_deployed_lamports[2] == 200
    assert result.counterfactual_deployed_lamports[4] == 100
    assert result.historical_deployed_lamports == (
        facts.historical_deployed_lamports
    )
    assert result.finalized_entropy == facts.entropy
    assert result.winning_square_identifier == 2
    assert result.counterfactual_total_winnings_lamports == 891
    assert result.counterfactual_total_vaulted_lamports == 99
    assert result.returned_principal_lamports == 99
    assert result.protocol_deductions_lamports == 1
    assert result.sol_winnings_lamports == 445
    assert result.transaction_fees_lamports == 10
    assert result.priority_fees_lamports == 2
    assert result.checkpoint_costs_lamports == 2
    assert result.gross_sol_outflow_lamports == 214
    assert result.gross_sol_inflow_lamports == 544
    assert result.net_sol_change_lamports == 330
    assert result.reward_treatment is ORERewardTreatment.SPLIT
    assert result.base_ore_earned_raw == 500
    assert result.motherlode_ore_earned_raw == 50
    assert result.ore_earned_raw == 550
    assert result.dilution_numerator_lamports == 100
    assert result.dilution_denominator_lamports == 200
    assert result.capture_efficiency_ore_raw_numerator == 550
    assert result.capture_efficiency_deployed_lamports_denominator == 200

    post = result.participant_state_after
    assert post.available_sol_lamports == state.available_sol_lamports - 214
    assert post.accrued_sol_lamports == state.accrued_sol_lamports + 544
    assert post.accrued_ore == state.accrued_ore + 550
    assert post.deployed_lamports == plan.deployed_lamports
    assert post.checkpoint_state is CheckpointState.COMPLETED
    assert post.cumulative_protocol_costs_lamports == 2
    assert post.cumulative_transaction_costs_lamports == 13
    assert post.current_round == 17
    assert post.last_economically_settled_round == 17


def test_solo_reward_uses_reversed_entropy_and_inclusion_cumulative() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 2, (2,))
    facts = _facts(entropy=2, winner=2, top_miner="historical-miner")

    result = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )

    assert result.reward_treatment is ORERewardTreatment.SOLO
    assert result.base_ore_earned_raw == 1_000
    assert result.motherlode_ore_earned_raw == 50
    assert result.ore_earned_raw == 1_050


def test_solo_reward_is_zero_when_sample_precedes_synthetic_interval() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {1: 100})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 1, (1,))
    facts = _facts(
        entropy=1,
        winner=1,
        top_miner="historical-miner",
        winner_inclusion_deployed=40,
    )

    result = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )

    assert result.reward_treatment is ORERewardTreatment.SOLO
    assert result.base_ore_earned_raw == 0
    assert result.motherlode_ore_earned_raw == 50


def test_losing_deployment_has_no_return_and_preserves_native_units() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {4: 200})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 2, (4,))
    facts = _facts(
        entropy=2,
        winner=2,
        top_miner=SPLIT_REWARD_ADDRESS,
    )

    result = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )

    assert result.status is EconomicRoundStatus.SETTLED
    assert result.returned_principal_lamports == 0
    assert result.sol_winnings_lamports == 0
    assert result.protocol_deductions_lamports == 0
    assert result.reward_treatment is ORERewardTreatment.NONE
    assert result.ore_earned_raw == 0
    assert result.net_sol_change_lamports == -214
    assert isinstance(result.net_sol_change_lamports, int)
    assert isinstance(result.ore_earned_raw, int)


def test_settlement_is_deterministic_and_does_not_mutate_inputs() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 2, (2,))
    facts = _facts(
        entropy=2,
        winner=2,
        top_miner=SPLIT_REWARD_ADDRESS,
    )
    before = (
        facts.historical_deployed_lamports,
        state.state_identity,
        plan.deployed_lamports,
    )

    first = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )
    second = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )

    assert first == second
    assert first.result_identity == second.result_identity
    assert before == (
        facts.historical_deployed_lamports,
        state.state_identity,
        plan.deployed_lamports,
    )
    with pytest.raises(FrozenInstanceError):
        first.deployed_sol_lamports = 0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        facts.outcome_source = "changed"  # type: ignore[misc]


def test_evaluation_winner_mismatch_fails_closed_without_transition() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 3, (2,))
    facts = _facts(
        entropy=2,
        winner=2,
        top_miner=SPLIT_REWARD_ADDRESS,
    )

    result = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )

    assert result.status is EconomicRoundStatus.REJECTED
    assert _codes(result) == {
        SettlementRejectionCode.EVALUATION_WINNER_MISMATCH,
        SettlementRejectionCode.EVALUATION_HIT_MISMATCH,
    }
    assert result.participant_state_after is state
    _assert_no_settlement(result)


def test_abstract_hit_must_match_materialized_winning_support() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 2, (4,))

    result = _model().settle(
        plan,
        transaction,
        evaluation,
        _facts(
            entropy=2,
            winner=2,
            top_miner=SPLIT_REWARD_ADDRESS,
        ),
        scenario,
        state,
    )

    assert _codes(result) == {
        SettlementRejectionCode.EVALUATION_HIT_MISMATCH,
    }
    _assert_no_settlement(result)


@pytest.mark.parametrize(
    ("facts_change", "expected"),
    (
        (
            {"replay_identity": "replay-v2"},
            SettlementRejectionCode.REPLAY_IDENTITY_MISMATCH,
        ),
        (
            {"dataset_identity": "dataset-v2"},
            SettlementRejectionCode.DATASET_IDENTITY_MISMATCH,
        ),
        (
            {"outcome_source": "other"},
            SettlementRejectionCode.OUTCOME_SOURCE_REJECTED,
        ),
        (
            {"completeness_status": "partial"},
            SettlementRejectionCode.OUTCOME_INCOMPLETE,
        ),
        (
            {"synthetic_participant_absent": False},
            SettlementRejectionCode.HISTORICAL_PARTICIPANT_DOUBLE_COUNT,
        ),
    ),
)
def test_provenance_and_double_counting_fail_closed(
    facts_change: dict[str, object],
    expected: SettlementRejectionCode,
) -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    facts = replace(
        _facts(
            entropy=2,
            winner=2,
            top_miner=SPLIT_REWARD_ADDRESS,
        ),
        **facts_change,
    )

    result = _model().settle(
        plan,
        transaction,
        _evaluation(17, 2, (2,)),
        facts,
        scenario,
        state,
    )

    assert _codes(result) == {expected}
    assert result.outcome_source == facts.outcome_source
    _assert_no_settlement(result)


def test_transaction_binding_mismatch_fails_closed() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    object.__setattr__(
        transaction,
        "protocol_deployment_plan_identity",
        "wrong-plan",
    )

    result = _model().settle(
        plan,
        transaction,
        _evaluation(17, 2, (2,)),
        _facts(
            entropy=2,
            winner=2,
            top_miner=SPLIT_REWARD_ADDRESS,
        ),
        scenario,
        state,
    )

    assert _codes(result) == {
        SettlementRejectionCode.TRANSACTION_BINDING_MISMATCH,
    }
    _assert_no_settlement(result)


def test_empty_historical_winner_branch_change_fails_closed() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    facts = _facts(
        entropy=2,
        winner=2,
        top_miner="historical-miner",
    )
    historical = list(facts.historical_deployed_lamports)
    historical[3] += historical[2]
    historical[2] = 0
    inclusion = list(facts.historical_deployed_at_inclusion_lamports)
    inclusion[3] += inclusion[2]
    inclusion[2] = 0
    facts = replace(
        facts,
        historical_deployed_lamports=tuple(historical),
        historical_deployed_at_inclusion_lamports=tuple(inclusion),
        total_winnings_lamports=0,
        total_vaulted_lamports=990,
    )

    result = _model().settle(
        plan,
        transaction,
        _evaluation(17, 2, (2,)),
        facts,
        scenario,
        state,
    )

    assert _codes(result) == {
        SettlementRejectionCode.COUNTERFACTUAL_REWARD_STATE_UNAVAILABLE,
    }
    _assert_no_settlement(result)


def test_unincluded_transaction_produces_result_without_settlement() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = TransactionModel("rfc011-transactions-v1").evaluate(
        plan,
        scenario,
        decision_slot=10,
        round_deadline_slot=12,
    )

    result = _model().settle(
        plan,
        transaction,
        None,
        None,
        scenario,
        state,
    )

    assert result.status is EconomicRoundStatus.UNINCLUDED
    assert _codes(result) == {SettlementRejectionCode.TRANSACTION_REJECTION}
    assert result.rejection_reasons[0].source_code == "round_deadline_reached"
    assert result.participant_state_after is state
    assert result.transaction_count == 1
    _assert_no_settlement(result)


def test_protocol_rejection_produces_result_without_settlement() -> None:
    scenario = _scenario()
    state = _state()
    rejection = ProtocolRejection(
        violations=(
            ProtocolConstraintViolation(
                ProtocolConstraintCode.OCCUPIED_SQUARE,
                "an authority-round-square may receive one deployment",
                (2,),
            ),
        ),
        scenario_identity=scenario.scenario_identity,
        participant_state_identity=state.state_identity,
    )

    result = _model().settle(
        rejection,
        None,
        None,
        None,
        scenario,
        state,
    )

    assert result.status is EconomicRoundStatus.REJECTED
    assert _codes(result) == {SettlementRejectionCode.PROTOCOL_REJECTION}
    assert result.rejection_reasons[0].source_code == "occupied_square"
    assert result.participant_state_after is state
    _assert_no_settlement(result)


def test_wrong_settlement_component_and_protocol_fail_closed() -> None:
    scenario = _scenario()
    state = _state()
    rejection = ProtocolRejection(
        violations=(
            ProtocolConstraintViolation(
                ProtocolConstraintCode.CHECKPOINT_REQUIRED,
                "checkpoint required",
            ),
        ),
        scenario_identity=scenario.scenario_identity,
        participant_state_identity=state.state_identity,
    )

    result = ORESettlementModel(
        "unsupported-protocol",
        "wrong-model",
    ).settle(rejection, None, None, None, scenario, state)

    assert _codes(result) == {
        SettlementRejectionCode.PROTOCOL_REVISION_MISMATCH,
        SettlementRejectionCode.SETTLEMENT_MODEL_IDENTITY_MISMATCH,
        SettlementRejectionCode.PROTOCOL_REJECTION,
    }


def test_insufficient_available_balance_cannot_transition_state() -> None:
    scenario = _scenario()
    state = _state(available=100)
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)

    result = _model().settle(
        plan,
        transaction,
        _evaluation(17, 2, (2,)),
        _facts(
            entropy=2,
            winner=2,
            top_miner=SPLIT_REWARD_ADDRESS,
        ),
        scenario,
        state,
    )

    assert _codes(result) == {
        SettlementRejectionCode.AVAILABLE_BALANCE_EXCEEDED,
    }
    assert result.participant_state_after is state
    _assert_no_settlement(result)


def test_finalized_facts_validate_protocol_arithmetic_and_chronology() -> None:
    facts = _facts(
        entropy=2,
        winner=2,
        top_miner=SPLIT_REWARD_ADDRESS,
    )
    with pytest.raises(ValueError, match="winning square"):
        replace(facts, winning_square_identifier=3)
    with pytest.raises(ValueError, match="total_winnings"):
        replace(facts, total_winnings_lamports=801)
    with pytest.raises(ValueError, match="total_vaulted"):
        replace(facts, total_vaulted_lamports=88)
    inclusion = list(facts.historical_deployed_at_inclusion_lamports)
    inclusion[2] = 101
    with pytest.raises(ValueError, match="cannot exceed"):
        replace(
            facts,
            historical_deployed_at_inclusion_lamports=tuple(inclusion),
        )


def test_result_preserves_complete_provenance_and_bindings() -> None:
    scenario = _scenario()
    state = _state()
    plan = _plan(scenario, state, {2: 100})
    transaction = _transaction(plan, scenario)
    evaluation = _evaluation(17, 2, (2,))
    facts = _facts(
        entropy=2,
        winner=2,
        top_miner=SPLIT_REWARD_ADDRESS,
    )

    result = _model().settle(
        plan,
        transaction,
        evaluation,
        facts,
        scenario,
        state,
    )

    assert result.scenario_identity == scenario.scenario_identity
    assert result.protocol_revision == PROTOCOL_REVISION
    assert result.protocol_deployment_plan_identity == (
        transaction.protocol_deployment_plan_identity
    )
    assert result.transaction_plan_identity == transaction.transaction_plan_identity
    assert result.finalized_outcome_identity == facts.finalized_outcome_identity
    assert result.replay_round_identity == "replay-round-17"
    assert result.decision_identity == "decision-17"
    assert result.outcome_source == "observed"
    assert result.completeness_status == "complete"


def test_phase_five_module_contains_no_later_phase_functionality() -> None:
    forbidden = (
        "EconomicSimulationRunner",
        "EconomicMetrics",
        "EconomicSimulationRecord",
        "CLI",
    )

    assert all(not hasattr(settlement_module, name) for name in forbidden)


def _assert_no_settlement(result: object) -> None:
    assert getattr(result, "deployed_sol_lamports") == 0
    assert getattr(result, "gross_sol_outflow_lamports") == 0
    assert getattr(result, "gross_sol_inflow_lamports") == 0
    assert getattr(result, "ore_earned_raw") == 0


def _codes(result: object) -> set[SettlementRejectionCode]:
    return {value.code for value in getattr(result, "rejection_reasons")}


def _model() -> ORESettlementModel:
    return ORESettlementModel(PROTOCOL_REVISION, "rfc011-settlement-v1")


def _transaction(
    plan: ProtocolDeploymentPlan,
    scenario: EconomicScenario,
):
    return TransactionModel("rfc011-transactions-v1").evaluate(
        plan,
        scenario,
        decision_slot=10,
        round_deadline_slot=20,
    )


def _evaluation(
    round_identifier: int,
    winner: int,
    deployed_squares: tuple[int, ...],
) -> EvaluationResult:
    decision = DeploymentDecision(
        DeploymentAllocation(
            square_identifier=square,
            allocation_amount=1 / len(deployed_squares),
            allocation_weight=1 / len(deployed_squares),
        )
        for square in deployed_squares
    )
    return Evaluator().evaluate(
        decision,
        EvaluationObservation(round_identifier, winner),
    )


def _plan(
    scenario: EconomicScenario,
    state: ParticipantEconomicState,
    values: dict[int, int],
) -> ProtocolDeploymentPlan:
    vector = [0] * 25
    for square, amount in values.items():
        vector[square] = amount
    return ProtocolDeploymentPlan(
        deployed_lamports=tuple(vector),
        total_deployed_lamports=sum(vector),
        occupied_square_count=sum(value > 0 for value in vector),
        protocol_revision=PROTOCOL_REVISION,
        scenario_identity=scenario.scenario_identity,
        participant_state_identity=state.state_identity,
        round_identifier=17,
    )


def _facts(
    *,
    entropy: int,
    winner: int,
    top_miner: str,
    winner_inclusion_deployed: int = 40,
) -> FinalizedReplayFacts:
    finalized = [0] * 25
    finalized[winner] = 100
    finalized[(winner + 1) % 25] = 900
    inclusion = [0] * 25
    inclusion[winner] = winner_inclusion_deployed
    inclusion[(winner + 1) % 25] = 500
    miners = [0] * 25
    miners[winner] = 2
    miners[(winner + 1) % 25] = 5
    rewards = [0] * 25
    rewards[0] = 1_000
    return FinalizedReplayFacts(
        round_identifier=17,
        replay_round_identity="replay-round-17",
        decision_identity="decision-17",
        replay_identity="replay-v1",
        dataset_identity="dataset-v1",
        outcome_source="observed",
        completeness_status="complete",
        entropy=entropy,
        winning_square_identifier=winner,
        historical_deployed_lamports=tuple(finalized),
        historical_deployed_at_inclusion_lamports=tuple(inclusion),
        historical_miner_counts=tuple(miners),
        reward_buckets_raw=tuple(rewards),
        total_vaulted_lamports=89,
        total_winnings_lamports=802,
        motherlode_ore_raw=100,
        top_miner=top_miner,
        synthetic_participant_absent=True,
    )


def _state(*, available: int = 2_000) -> ParticipantEconomicState:
    return ParticipantEconomicState(
        available_sol_lamports=available,
        accrued_sol_lamports=5,
        accrued_ore=7,
        deployed_lamports=(0,) * 25,
        checkpoint_state=CheckpointState.NOT_REQUIRED,
        cumulative_protocol_costs_lamports=0,
        cumulative_transaction_costs_lamports=0,
        current_round=17,
        last_economically_settled_round=16,
    )


def _scenario() -> EconomicScenario:
    return EconomicScenario(
        protocol_revision=PROTOCOL_REVISION,
        budget=BudgetModel(
            participant_initial_sol_balance_lamports=2_000,
            per_round_deployment_budget_lamports=1_000,
            capital_reserve_rules=CapitalReserveRules(10, 100, 2),
        ),
        lamport_apportionment_rule=(
            LamportApportionmentRule
            .LARGEST_REMAINDER_CANDIDATE_ORDER_V1
        ),
        fee_assumptions=FeeAssumptions(10, 2, 7, 1),
        checkpoint_assumptions=CheckpointAssumptions(True, 1),
        transaction_assumptions=TransactionAssumptions(
            maximum_transaction_size_bytes=1_232,
            compute_unit_limit=200_000,
            maximum_instructions_per_transaction=4,
            inclusion_latency_slots=2,
            transaction_base_size_bytes=200,
            deploy_instruction_size_bytes=40,
            transaction_base_compute_units=10_000,
            deploy_instruction_compute_units=50_000,
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
