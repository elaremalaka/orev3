from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction

import pytest

import orev3.strategy_lab.economic_metrics as metrics_module
from orev3.strategy_lab import (
    BudgetModel,
    CapitalReserveRules,
    CheckpointAssumptions,
    CheckpointState,
    ComponentIdentities,
    DeploymentAllocation,
    DeploymentDecision,
    EconomicMetricsEngine,
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
    TransactionAssumptions,
)


PROTOCOL_REVISION = "ore-v3-program-3112ab78"


def test_settled_capital_reward_and_native_return_metrics_are_exact() -> None:
    results = _run((17, 18, 19), _replay((17, 18, 19)))

    metrics = _engine().aggregate(results)

    assert metrics.economically_processed_round_count == 3
    assert metrics.settled_round_count == 3
    assert metrics.rejected_round_count == 0
    assert metrics.unincluded_round_count == 0
    assert metrics.missing_outcome_round_count == 0
    assert metrics.total_deployed_lamports == 300
    assert metrics.mean_deployed_lamports == Fraction(100, 1)
    assert metrics.total_returned_principal_lamports == 297
    assert metrics.total_sol_winnings_lamports == 1_203
    assert metrics.total_returned_sol_lamports == 1_500
    assert metrics.total_protocol_fees_lamports == 3
    assert metrics.total_transaction_fees_lamports == 30
    assert metrics.total_priority_fees_lamports == 6
    assert metrics.total_checkpoint_costs_lamports == 6
    assert metrics.total_gross_sol_outflow_lamports == 342
    assert metrics.total_gross_sol_inflow_lamports == 1_500
    assert metrics.net_sol_change_lamports == 1_158
    assert metrics.deployment_budget_utilization == Fraction(1, 1)
    assert metrics.maximum_concurrent_sol_exposure_lamports == 100
    assert metrics.total_ore_earned_raw == 1_650
    assert metrics.mean_ore_earned_raw == Fraction(550, 1)
    assert metrics.ore_per_sol_deployed == Fraction(11, 2)
    assert metrics.solo_reward_frequency == Fraction(0, 1)
    assert metrics.split_reward_frequency == Fraction(1, 1)
    assert metrics.mean_winning_square_capital_share == Fraction(1, 2)
    assert metrics.mean_dilution == Fraction(1, 2)
    assert metrics.capture_efficiency_ore_raw_numerator == 1_650
    assert metrics.capture_efficiency_deployed_lamports_denominator == 300
    assert metrics.capture_efficiency == Fraction(11, 2)
    assert metrics.net_sol_return_rate == Fraction(193, 57)


def test_completeness_and_status_metrics_preserve_provenance() -> None:
    replay = (
        EconomicReplayRound(17, 10, 20, _facts(17, source="observed")),
        EconomicReplayRound(18, 30, 32, _facts(18, source="enriched")),
        EconomicReplayRound(19, 50, 60, _missing(19)),
    )
    results = _run((17, 18, 19), replay)

    metrics = _engine().aggregate(results)

    assert tuple(value.status for value in results) == (
        EconomicRoundStatus.SETTLED,
        EconomicRoundStatus.UNINCLUDED,
        EconomicRoundStatus.MISSING_OUTCOME,
    )
    assert results[1].outcome_source == "enriched"
    assert metrics.economically_processed_round_count == 3
    assert metrics.settled_round_count == 1
    assert metrics.unincluded_round_count == 1
    assert metrics.missing_outcome_round_count == 1
    assert metrics.observed_outcome_count == 1
    assert metrics.enriched_outcome_count == 1
    assert metrics.missing_outcome_count == 1
    assert metrics.completeness_percentage == Fraction(200, 3)
    assert metrics.provenance_summary == (
        ("observed", 1),
        ("enriched", 1),
        ("missing", 1),
    )
    assert metrics.total_deployed_lamports == 100


def test_rejected_round_is_counted_without_recomputing_settlement() -> None:
    result = _run(
        (17,),
        (EconomicReplayRound(17, 10, 20, _facts(17, winner=3)),),
    )[0]
    before = result.participant_state_after

    metrics = _engine().aggregate((result,))

    assert result.status is EconomicRoundStatus.REJECTED
    assert metrics.rejected_round_count == 1
    assert metrics.settled_round_count == 0
    assert metrics.total_deployed_lamports == 0
    assert metrics.total_ore_earned_raw == 0
    assert metrics.mean_deployed_lamports is None
    assert metrics.ore_per_sol_deployed is None
    assert result.participant_state_after is before


def test_empty_metrics_are_explicit_and_deterministic() -> None:
    first = _engine().aggregate(())
    second = _engine().aggregate(())

    assert first == second
    assert first.metrics_identity == second.metrics_identity
    assert first.economically_processed_round_count == 0
    assert first.scenario_identity is None
    assert first.protocol_revision is None
    assert first.mean_deployed_lamports is None
    assert first.completeness_percentage is None
    assert first.provenance_summary == (
        ("observed", 0),
        ("enriched", 0),
        ("missing", 0),
    )


def test_zero_and_partial_deployment_ratios_remain_exact() -> None:
    zero = _engine().aggregate(
        _run((17,), _replay((17,)), allocation_amount=0.0)
    )
    partial = _engine().aggregate(
        _run((17,), _replay((17,)), allocation_amount=0.5)
    )

    assert zero.mean_deployed_lamports == Fraction(0, 1)
    assert zero.deployment_budget_utilization == Fraction(0, 1)
    assert zero.ore_per_sol_deployed is None
    assert zero.capture_efficiency is None
    assert zero.net_sol_return_rate is None
    assert partial.total_deployed_lamports == 50
    assert partial.deployment_budget_utilization == Fraction(1, 2)
    assert isinstance(partial.ore_per_sol_deployed, Fraction)


def test_metrics_are_deterministic_immutable_and_do_not_mutate_results() -> None:
    results = _run((17, 18), _replay((17, 18)))
    identities = tuple(value.result_identity for value in results)
    state_identities = tuple(
        value.participant_state_after.state_identity for value in results
    )

    first = _engine().aggregate(results)
    second = _engine().aggregate(results)

    assert first == second
    assert first.metrics_identity == second.metrics_identity
    assert tuple(value.result_identity for value in results) == identities
    assert tuple(
        value.participant_state_after.state_identity for value in results
    ) == state_identities
    with pytest.raises(FrozenInstanceError):
        first.total_deployed_lamports = 0  # type: ignore[misc]
    with pytest.raises(ValueError, match="returned SOL components"):
        replace(first, total_returned_sol_lamports=0)


def test_engine_rejects_duplicates_mixed_scenarios_and_tampering() -> None:
    results = _run((17, 18), _replay((17, 18)))
    with pytest.raises(TypeError, match="immutable"):
        _engine().aggregate(list(results))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="identities must be unique"):
        _engine().aggregate((results[0], results[0]))
    rebound = replace(results[1], scenario_identity="another-scenario")
    with pytest.raises(ValueError, match="share one scenario"):
        _engine().aggregate((results[0], rebound))

    tampered = results[0]
    object.__setattr__(tampered, "deployed_sol_lamports", 99)
    with pytest.raises(ValueError, match="identity is inconsistent"):
        _engine().aggregate((tampered,))


def test_missing_outcome_must_terminate_the_ordered_interval() -> None:
    settled = _run((17,), _replay((17,)))[0]
    missing = _run(
        (18,),
        (EconomicReplayRound(18, 30, 40, _missing(18)),),
        initial_round=18,
        last_settled=17,
    )[0]
    later = _run(
        (19,),
        _replay((19,), slot_start=50),
        initial_round=19,
        last_settled=18,
    )[0]

    with pytest.raises(ValueError, match="must terminate"):
        _engine().aggregate((settled, missing, later))


def test_engine_preserves_scenario_protocol_and_component_identity() -> None:
    results = _run((17,), _replay((17,)))
    metrics = _engine().aggregate(results)

    assert metrics.metrics_engine_identity == "rfc011-metrics-v1"
    assert metrics.scenario_identity == results[0].scenario_identity
    assert metrics.protocol_revision == PROTOCOL_REVISION
    assert metrics.metrics_identity.startswith(
        "rfc011-economic-experiment-metrics-sha256:"
    )
    with pytest.raises(ValueError, match="canonical"):
        EconomicMetricsEngine(" metrics ")


def test_phase_seven_contains_no_record_or_cli_functionality() -> None:
    forbidden = ("EconomicSimulationRecord", "CLI")

    assert all(not hasattr(metrics_module, name) for name in forbidden)
    metrics = _engine().aggregate(())
    assert not hasattr(metrics, "combined_roi")
    assert not hasattr(metrics, "ore_valued_in_sol")
    assert not hasattr(metrics, "fiat_value")


def _engine() -> EconomicMetricsEngine:
    return EconomicMetricsEngine("rfc011-metrics-v1")


def _run(
    rounds: tuple[int, ...],
    replay: tuple[EconomicReplayRound, ...],
    *,
    initial_round: int | None = None,
    last_settled: int | None = None,
    allocation_amount: float = 1.0,
):
    first_round = initial_round if initial_round is not None else rounds[0]
    prior_round = (
        last_settled if last_settled is not None else first_round - 1
    )
    return EconomicSimulationRunner("rfc011-runner-v1").run(
        _experiment(rounds, allocation_amount=allocation_amount),
        replay,
        _scenario(),
        _state(first_round, prior_round),
    )


def _experiment(
    rounds: tuple[int, ...],
    *,
    allocation_amount: float = 1.0,
) -> ExperimentExecution:
    candidates = tuple(
        RankedCandidateSet((RankedCandidate(2, 1.0),)) for _ in rounds
    )
    decisions = tuple(_decision(allocation_amount) for _ in rounds)
    evaluations = tuple(
        Evaluator().evaluate(
            decision,
            EvaluationObservation(round_identifier, 2),
        )
        for round_identifier, decision in zip(rounds, decisions, strict=True)
    )
    metrics = MetricsEngine().aggregate(evaluations)
    return ExperimentExecution(
        ranked_candidate_sets=candidates,
        deployment_decisions=decisions,
        evaluation_results=evaluations,
        metrics=metrics,
        record=ExperimentRecord(
            experiment_identifier="00000000-0000-4000-8000-000000000117",
            configuration_identifier="rfc010-configuration-v1",
            implementation_identifier="rfc010-implementation-v1",
            metrics=metrics,
        ),
    )


def _decision(allocation_amount: float = 1.0) -> DeploymentDecision:
    return DeploymentDecision(
        (
            DeploymentAllocation(
                square_identifier=2,
                allocation_amount=allocation_amount,
                allocation_weight=allocation_amount,
            ),
        )
    )


def _replay(
    rounds: tuple[int, ...],
    *,
    slot_start: int = 10,
) -> tuple[EconomicReplayRound, ...]:
    return tuple(
        EconomicReplayRound(
            round_identifier=round_identifier,
            decision_slot=slot_start + index * 20,
            round_deadline_slot=slot_start + index * 20 + 10,
            outcome=_facts(round_identifier),
        )
        for index, round_identifier in enumerate(rounds)
    )


def _missing(round_identifier: int) -> MissingFinalizedOutcome:
    return MissingFinalizedOutcome(
        round_identifier=round_identifier,
        replay_round_identity=f"replay-round-{round_identifier}",
        decision_identity=f"decision-{round_identifier}",
        replay_identity="replay-v1",
        dataset_identity="dataset-v1",
    )


def _facts(
    round_identifier: int,
    *,
    source: str = "observed",
    winner: int = 2,
) -> FinalizedReplayFacts:
    finalized = [0] * 25
    finalized[winner] = 100
    finalized[(winner + 1) % 25] = 900
    inclusion = [0] * 25
    inclusion[winner] = 40
    inclusion[(winner + 1) % 25] = 500
    miners = [0] * 25
    miners[winner] = 2
    miners[(winner + 1) % 25] = 5
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
        entropy=winner,
        winning_square_identifier=winner,
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
    current_round: int,
    last_settled: int,
) -> ParticipantEconomicState:
    return ParticipantEconomicState(
        available_sol_lamports=10_000,
        accrued_sol_lamports=0,
        accrued_ore=0,
        deployed_lamports=(0,) * 25,
        checkpoint_state=CheckpointState.NOT_REQUIRED,
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
