from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

import orev3.strategy_lab.economic_runner as runner_module
from orev3.strategy_lab import (
    BudgetModel,
    CapitalReserveRules,
    CheckpointAssumptions,
    CheckpointState,
    ComponentIdentities,
    DeploymentAllocation,
    DeploymentDecision,
    EconomicReplayRound,
    EconomicRoundStatus,
    EconomicScenario,
    EconomicSimulationRunner,
    EvaluationObservation,
    Evaluator,
    ExperimentExecution,
    ExperimentRecord,
    FeeAssumptions,
    FinalizedReplayFacts,
    LamportApportionmentRule,
    MetricsEngine,
    MissingFinalizedOutcome,
    MissingOutcomePolicy,
    OutcomePolicy,
    ParticipantEconomicState,
    RankedCandidate,
    RankedCandidateSet,
    SPLIT_REWARD_ADDRESS,
    SettlementRejectionCode,
    TransactionAssumptions,
)


PROTOCOL_REVISION = "ore-v3-program-3112ab78"


def test_runner_executes_ordered_rounds_with_sequential_state() -> None:
    rounds = (17, 18, 19)
    replay = _replay(rounds, sources=("observed", "enriched", "observed"))

    first = _runner().run(
        _experiment(rounds),
        replay,
        _scenario(),
        _state(current_round=17, last_settled=16),
    )
    second = _runner().run(
        _experiment(rounds),
        replay,
        _scenario(),
        _state(current_round=17, last_settled=16),
    )

    assert first == second
    assert tuple(value.round_identifier for value in first) == rounds
    assert all(value.status is EconomicRoundStatus.SETTLED for value in first)
    assert tuple(value.outcome_source for value in first) == (
        "observed",
        "enriched",
        "observed",
    )
    assert len({value.result_identity for value in first}) == 3
    assert first[1].participant_state_before_identity != (
        first[0].participant_state_before_identity
    )
    assert first[1].participant_state_after.accrued_ore > (
        first[0].participant_state_after.accrued_ore
    )
    assert first[-1].participant_state_after.last_economically_settled_round == 19
    assert first[-1].scenario_identity == _scenario().scenario_identity


def test_runner_invokes_phase_components_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    original_materialize = runner_module.AllocationMaterializer.materialize
    original_validate = runner_module.ProtocolConstraintModel.validate
    original_evaluate = runner_module.TransactionModel.evaluate
    original_settle = runner_module.ORESettlementModel.settle

    def materialize(*args: object, **kwargs: object):
        calls.append("materialize")
        return original_materialize(*args, **kwargs)

    def validate(*args: object, **kwargs: object):
        calls.append("constraints")
        return original_validate(*args, **kwargs)

    def evaluate(*args: object, **kwargs: object):
        calls.append("transactions")
        return original_evaluate(*args, **kwargs)

    def settle(*args: object, **kwargs: object):
        calls.append("settlement")
        return original_settle(*args, **kwargs)

    monkeypatch.setattr(
        runner_module.AllocationMaterializer,
        "materialize",
        materialize,
    )
    monkeypatch.setattr(
        runner_module.ProtocolConstraintModel,
        "validate",
        validate,
    )
    monkeypatch.setattr(
        runner_module.TransactionModel,
        "evaluate",
        evaluate,
    )
    monkeypatch.setattr(
        runner_module.ORESettlementModel,
        "settle",
        settle,
    )

    _runner().run(
        _experiment((17,)),
        _replay((17,)),
        _scenario(),
        _state(current_round=17, last_settled=16),
    )

    assert calls == [
        "materialize",
        "constraints",
        "transactions",
        "settlement",
    ]


def test_checkpoint_transition_clears_prior_round_occupancy() -> None:
    results = _runner().run(
        _experiment((17, 18)),
        _replay((17, 18)),
        _scenario(),
        _state(current_round=17, last_settled=16),
    )

    assert len(results) == 2
    assert all(value.status is EconomicRoundStatus.SETTLED for value in results)
    assert results[0].materialized_deployment_lamports[2] == 100
    assert results[1].materialized_deployment_lamports[2] == 100
    assert results[0].participant_state_after.checkpoint_state is (
        CheckpointState.COMPLETED
    )


def test_broken_checkpoint_transition_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = runner_module.ORESettlementModel.settle

    def broken_settle(*args: object, **kwargs: object):
        result = original(*args, **kwargs)
        broken_state = replace(
            result.participant_state_after,
            checkpoint_state=CheckpointState.REQUIRED,
        )
        return replace(result, participant_state_after=broken_state)

    monkeypatch.setattr(
        runner_module.ORESettlementModel,
        "settle",
        broken_settle,
    )

    with pytest.raises(ValueError, match="did not complete checkpoint"):
        _runner().run(
            _experiment((17, 18)),
            _replay((17, 18)),
            _scenario(),
            _state(current_round=17, last_settled=16),
        )


def test_missing_outcome_is_reported_and_terminates_interval() -> None:
    rounds = (17, 18, 19)
    replay = list(_replay(rounds))
    replay[1] = EconomicReplayRound(
        round_identifier=18,
        decision_slot=30,
        round_deadline_slot=40,
        outcome=MissingFinalizedOutcome(
            round_identifier=18,
            replay_round_identity="replay-round-18",
            decision_identity="decision-18",
            replay_identity="replay-v1",
            dataset_identity="dataset-v1",
        ),
    )

    results = _runner().run(
        _experiment(rounds),
        tuple(replay),
        _scenario(),
        _state(current_round=17, last_settled=16),
    )

    assert tuple(value.round_identifier for value in results) == (17, 18)
    missing = results[-1]
    assert missing.status is EconomicRoundStatus.MISSING_OUTCOME
    assert {value.code for value in missing.rejection_reasons} == {
        SettlementRejectionCode.MISSING_FINALIZED_OUTCOME,
    }
    assert missing.replay_round_identity == "replay-round-18"
    assert missing.decision_identity == "decision-18"
    assert missing.finalized_outcome_identity is None
    assert missing.outcome_source is None
    assert missing.completeness_status == "missing"
    assert missing.gross_sol_outflow_lamports == 0
    assert missing.gross_sol_inflow_lamports == 0
    assert missing.ore_earned_raw == 0
    assert missing.participant_state_after.state_identity == (
        missing.participant_state_before_identity
    )


def test_missing_outcome_provenance_mismatch_fails_before_processing() -> None:
    missing = MissingFinalizedOutcome(
        round_identifier=17,
        replay_round_identity="replay-round-17",
        decision_identity="decision-17",
        replay_identity="other-replay",
        dataset_identity="other-dataset",
    )

    with pytest.raises(ValueError, match="replay outcome identity"):
        _runner().run(
            _experiment((17,)),
            (EconomicReplayRound(17, 10, 20, missing),),
            _scenario(),
            _state(current_round=17, last_settled=16),
        )


def test_later_complete_interval_requires_explicit_initial_state() -> None:
    experiment = _experiment((17, 18, 19))
    interval = _replay((18, 19), slot_start=30)

    with pytest.raises(ValueError, match="first round"):
        _runner().run(
            experiment,
            interval,
            _scenario(),
            _state(current_round=17, last_settled=16),
        )

    results = _runner().run(
        experiment,
        interval,
        _scenario(),
        _state(current_round=18, last_settled=17),
    )

    assert tuple(value.round_identifier for value in results) == (18, 19)


def test_noncontiguous_experiment_interval_fails_closed() -> None:
    selected = (_replay((17,))[0], _replay((19,), slot_start=50)[0])

    with pytest.raises(ValueError, match="contiguous experiment interval"):
        _runner().run(
            _experiment((17, 18, 19)),
            selected,
            _scenario(),
            _state(current_round=17, last_settled=16),
        )


def test_unincluded_round_preserves_state_and_later_round_can_settle() -> None:
    replay = (
        EconomicReplayRound(17, 10, 12, _facts(17)),
        EconomicReplayRound(18, 30, 40, _facts(18)),
    )

    results = _runner().run(
        _experiment((17, 18)),
        replay,
        _scenario(),
        _state(current_round=17, last_settled=16),
    )

    assert tuple(value.status for value in results) == (
        EconomicRoundStatus.UNINCLUDED,
        EconomicRoundStatus.SETTLED,
    )
    assert results[0].participant_state_after.state_identity == (
        results[0].participant_state_before_identity
    )
    assert results[1].participant_state_after.last_economically_settled_round == 18


def test_replay_order_and_round_identity_are_fail_closed() -> None:
    experiment = _experiment((17, 18))
    state = _state(current_round=17, last_settled=16)
    reversed_slots = (
        EconomicReplayRound(17, 30, 40, _facts(17)),
        EconomicReplayRound(18, 10, 20, _facts(18)),
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        _runner().run(experiment, reversed_slots, _scenario(), state)

    with pytest.raises(ValueError, match="replay round and outcome"):
        EconomicReplayRound(17, 10, 20, _facts(18))


def test_broken_participant_state_continuity_fails_closed() -> None:
    scenario = _scenario()
    replay = _replay((17,))
    with pytest.raises(ValueError, match="first round"):
        _runner().run(
            _experiment((17,)),
            replay,
            scenario,
            _state(current_round=18, last_settled=16),
        )

    corrupted = _state(current_round=17, last_settled=16)
    object.__setattr__(corrupted, "available_sol_lamports", 1)
    with pytest.raises(ValueError, match="identity is inconsistent"):
        _runner().run(_experiment((17,)), replay, scenario, corrupted)

    with pytest.raises(ValueError, match="cannot restart"):
        _runner().run(
            _experiment((17,)),
            replay,
            scenario,
            _state(current_round=17, last_settled=17),
        )

    with pytest.raises(ValueError, match="unresolved checkpoint"):
        _runner().run(
            _experiment((17,)),
            replay,
            scenario,
            _state(
                current_round=17,
                last_settled=16,
                checkpoint=CheckpointState.REQUIRED,
            ),
        )


def test_component_and_provenance_identities_are_preserved() -> None:
    scenario = _scenario()
    result = _runner().run(
        _experiment((17,)),
        _replay((17,), sources=("enriched",)),
        scenario,
        _state(current_round=17, last_settled=16),
    )[0]

    assert result.scenario_identity == scenario.scenario_identity
    assert result.protocol_revision == scenario.protocol_revision
    assert result.outcome_source == "enriched"
    assert result.replay_round_identity == "replay-round-17"
    with pytest.raises(ValueError, match="runner identity"):
        EconomicSimulationRunner("wrong-runner").run(
            _experiment((17,)),
            _replay((17,)),
            scenario,
            _state(current_round=17, last_settled=16),
        )

    mismatched = EconomicReplayRound(
        17,
        10,
        20,
        replace(_facts(17), replay_identity="other-replay"),
    )
    with pytest.raises(ValueError, match="replay outcome identity"):
        _runner().run(
            _experiment((17,)),
            (mismatched,),
            scenario,
            _state(current_round=17, last_settled=16),
        )


def test_runner_inputs_and_outputs_are_immutable() -> None:
    replay_round = _replay((17,))[0]
    result = _runner().run(
        _experiment((17,)),
        (replay_round,),
        _scenario(),
        _state(current_round=17, last_settled=16),
    )[0]

    with pytest.raises(FrozenInstanceError):
        replay_round.decision_slot = 11  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.round_identifier = 18  # type: ignore[misc]
    with pytest.raises(ValueError, match="cannot be marked complete"):
        MissingFinalizedOutcome(
            round_identifier=17,
            replay_round_identity="replay-round-17",
            decision_identity="decision-17",
            replay_identity="replay-v1",
            dataset_identity="dataset-v1",
            completeness_status="complete",
        )


def test_phase_six_contains_no_later_phase_functionality() -> None:
    forbidden = (
        "EconomicMetrics",
        "EconomicSimulationRecord",
        "CLI",
    )

    assert all(not hasattr(runner_module, value) for value in forbidden)


def _runner() -> EconomicSimulationRunner:
    return EconomicSimulationRunner("rfc011-runner-v1")


def _experiment(rounds: tuple[int, ...]) -> ExperimentExecution:
    candidates = tuple(
        RankedCandidateSet((RankedCandidate(2, 1.0),)) for _ in rounds
    )
    decisions = tuple(_decision() for _ in rounds)
    evaluations = tuple(
        Evaluator().evaluate(
            decision,
            EvaluationObservation(round_identifier, 2),
        )
        for round_identifier, decision in zip(rounds, decisions, strict=True)
    )
    metrics = MetricsEngine().aggregate(evaluations)
    record = ExperimentRecord(
        experiment_identifier="00000000-0000-4000-8000-000000000111",
        configuration_identifier="rfc010-configuration-v1",
        implementation_identifier="rfc010-implementation-v1",
        metrics=metrics,
    )
    return ExperimentExecution(
        ranked_candidate_sets=candidates,
        deployment_decisions=decisions,
        evaluation_results=evaluations,
        metrics=metrics,
        record=record,
    )


def _decision() -> DeploymentDecision:
    return DeploymentDecision(
        (
            DeploymentAllocation(
                square_identifier=2,
                allocation_amount=1.0,
                allocation_weight=1.0,
            ),
        )
    )


def _replay(
    rounds: tuple[int, ...],
    *,
    slot_start: int = 10,
    sources: tuple[str, ...] | None = None,
) -> tuple[EconomicReplayRound, ...]:
    provenance = sources or ("observed",) * len(rounds)
    return tuple(
        EconomicReplayRound(
            round_identifier=round_identifier,
            decision_slot=slot_start + index * 20,
            round_deadline_slot=slot_start + index * 20 + 10,
            outcome=_facts(round_identifier, source=source),
        )
        for index, (round_identifier, source) in enumerate(
            zip(rounds, provenance, strict=True)
        )
    )


def _facts(
    round_identifier: int,
    *,
    source: str = "observed",
) -> FinalizedReplayFacts:
    finalized = [0] * 25
    finalized[2] = 100
    finalized[3] = 900
    inclusion = [0] * 25
    inclusion[2] = 40
    inclusion[3] = 500
    miners = [0] * 25
    miners[2] = 2
    miners[3] = 5
    rewards = [0] * 25
    rewards[0] = 1_000
    return FinalizedReplayFacts(
        round_identifier=round_identifier,
        replay_round_identity=f"replay-round-{round_identifier}",
        decision_identity=f"decision-{round_identifier}",
        replay_identity="replay-v1",
        dataset_identity="dataset-v1",
        outcome_source=source,
        completeness_status="complete",
        entropy=2,
        winning_square_identifier=2,
        historical_deployed_lamports=tuple(finalized),
        historical_deployed_at_inclusion_lamports=tuple(inclusion),
        historical_miner_counts=tuple(miners),
        reward_buckets_raw=tuple(rewards),
        total_vaulted_lamports=89,
        total_winnings_lamports=802,
        motherlode_ore_raw=100,
        top_miner=SPLIT_REWARD_ADDRESS,
        synthetic_participant_absent=True,
    )


def _state(
    *,
    current_round: int,
    last_settled: int | None,
    checkpoint: CheckpointState = CheckpointState.NOT_REQUIRED,
) -> ParticipantEconomicState:
    return ParticipantEconomicState(
        available_sol_lamports=10_000,
        accrued_sol_lamports=0,
        accrued_ore=0,
        deployed_lamports=(0,) * 25,
        checkpoint_state=checkpoint,
        cumulative_protocol_costs_lamports=0,
        cumulative_transaction_costs_lamports=0,
        current_round=current_round,
        last_economically_settled_round=last_settled,
    )


def _scenario() -> EconomicScenario:
    return EconomicScenario(
        protocol_revision=PROTOCOL_REVISION,
        budget=BudgetModel(
            participant_initial_sol_balance_lamports=10_000,
            per_round_deployment_budget_lamports=100,
            capital_reserve_rules=CapitalReserveRules(10, 100, 2),
        ),
        lamport_apportionment_rule=(
            LamportApportionmentRule.LARGEST_REMAINDER_CANDIDATE_ORDER_V1
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
