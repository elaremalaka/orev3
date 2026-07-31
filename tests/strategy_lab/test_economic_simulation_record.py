from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction

import pytest

import orev3.strategy_lab.economic_record as record_module
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
    EconomicSimulationRecord,
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
EXPERIMENT_IDENTITY = "00000000-0000-4000-8000-000000000117"


def test_record_preserves_every_reproduction_identity_and_hash() -> None:
    scenario, initial, results, metrics, terminal = _completed_artifacts()

    record = _record(scenario, initial, results, metrics, terminal)

    components = scenario.component_identities
    assert record.rfc010_experiment_identity == EXPERIMENT_IDENTITY
    assert record.economic_scenario is scenario
    assert record.economic_scenario_identity == scenario.scenario_identity
    assert record.economic_scenario_sha256 == scenario.scenario_identity.rsplit(
        ":", 1
    )[1]
    assert record.protocol_revision == PROTOCOL_REVISION
    assert record.dataset_identity == "dataset-v1"
    assert record.replay_identity == "replay-v1"
    assert record.allocation_materializer_identity == (
        components.allocation_materializer
    )
    assert record.protocol_constraint_model_identity == (
        components.protocol_constraint_model
    )
    assert record.transaction_model_identity == components.transaction_model
    assert record.inclusion_model_identity == components.inclusion_model
    assert record.ore_settlement_model_identity == components.settlement_model
    assert record.economic_simulation_runner_identity == (
        components.simulation_runner
    )
    assert record.economic_metrics_engine_identity == components.metrics_engine
    assert record.initial_participant_state_sha256 == (
        initial.state_identity.rsplit(":", 1)[1]
    )
    assert record.terminal_participant_state_sha256 == (
        terminal.state_identity.rsplit(":", 1)[1]
    )
    assert record.ordered_economic_round_result_identities == tuple(
        result.result_identity for result in results
    )
    assert record.economic_experiment_metrics is metrics
    assert record.record_identity.startswith(
        "rfc011-economic-simulation-record-sha256:"
    )


def test_result_hash_is_canonical_and_binds_ordered_results_and_metrics() -> None:
    scenario, initial, results, metrics, terminal = _completed_artifacts()

    first = _record(scenario, initial, results, metrics, terminal)
    second = _record(scenario, initial, results, metrics, terminal)
    payload = {
        "economic_experiment_metrics_identity": metrics.metrics_identity,
        "ordered_economic_round_result_identities": [
            result.result_identity for result in results
        ],
    }
    expected = hashlib.sha256(
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    assert first == second
    assert first.deterministic_result_sha256 == expected
    assert first.record_identity == second.record_identity
    assert first.ordered_economic_round_results == results
    assert tuple(result.round_identifier for result in results) == (17, 18)


def test_record_preserves_all_terminal_statuses_and_completeness() -> None:
    scenario = _scenario()
    initial = _state(17, 16)
    replay = (
        EconomicReplayRound(17, 10, 20, _facts(17, source="observed")),
        EconomicReplayRound(18, 30, 32, _facts(18, source="enriched")),
        EconomicReplayRound(19, 50, 60, _missing(19)),
    )
    results = _runner().run(
        _experiment((17, 18, 19)),
        replay,
        scenario,
        initial,
    )
    metrics = _metrics().aggregate(results)
    record = _record(
        scenario,
        initial,
        results,
        metrics,
        results[-1].participant_state_after,
    )

    assert tuple(result.status for result in record.ordered_economic_round_results) == (
        EconomicRoundStatus.SETTLED,
        EconomicRoundStatus.UNINCLUDED,
        EconomicRoundStatus.MISSING_OUTCOME,
    )
    assert record.completeness_metadata == (
        ("economically_processed_round_count", 3),
        ("outcome_complete_round_count", 2),
        ("missing_outcome_round_count", 1),
        ("completeness_percentage", Fraction(200, 3)),
    )
    assert record.outcome_provenance_summary == (
        ("observed", 1),
        ("enriched", 1),
        ("missing", 1),
    )


def test_record_construction_does_not_recompute_metrics_or_settlement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario, initial, results, metrics, terminal = _completed_artifacts()

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("record construction must only consume evidence")

    monkeypatch.setattr(EconomicMetricsEngine, "aggregate", forbidden)
    from orev3.strategy_lab import ORESettlementModel

    monkeypatch.setattr(ORESettlementModel, "settle", forbidden)

    record = _record(scenario, initial, results, metrics, terminal)

    assert record.economic_experiment_metrics is metrics
    assert record.ordered_economic_round_results is results


def test_record_is_deeply_immutable_and_does_not_mutate_sources() -> None:
    scenario, initial, results, metrics, terminal = _completed_artifacts()
    result_identities = tuple(result.result_identity for result in results)

    record = _record(scenario, initial, results, metrics, terminal)

    with pytest.raises(FrozenInstanceError):
        record.replay_identity = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        record.economic_experiment_metrics = metrics  # type: ignore[misc]
    assert scenario.scenario_identity == record.economic_scenario_identity
    assert initial.state_identity.endswith(
        record.initial_participant_state_sha256
    )
    assert terminal.state_identity.endswith(
        record.terminal_participant_state_sha256
    )
    assert tuple(result.result_identity for result in results) == result_identities


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("replay", "replay identity"),
        ("initial", "initial state"),
        ("terminal", "terminal state"),
    ),
)
def test_record_rejects_identity_and_endpoint_mismatches(
    case: str,
    message: str,
) -> None:
    scenario, initial, results, metrics, terminal = _completed_artifacts()
    arguments: dict[str, object] = {
        "rfc010_experiment_identity": EXPERIMENT_IDENTITY,
        "economic_scenario": scenario,
        "initial_participant_state": initial,
        "terminal_participant_state": terminal,
        "ordered_economic_round_results": results,
        "economic_experiment_metrics": metrics,
        "replay_identity": scenario.replay_identity,
    }
    if case == "replay":
        arguments["replay_identity"] = "another-replay"
    elif case == "initial":
        arguments["initial_participant_state"] = _state(18, 17)
    else:
        arguments["terminal_participant_state"] = _state(18, 17)

    with pytest.raises(ValueError, match=message):
        EconomicSimulationRecord(**arguments)  # type: ignore[arg-type]


def test_record_rejects_wrong_scenario_metrics_statuses_and_provenance() -> None:
    scenario, initial, results, metrics, terminal = _completed_artifacts()
    other_scenario = replace(scenario, dataset_identity="other-dataset")
    wrong_statuses = replace(
        metrics,
        settled_round_count=1,
        rejected_round_count=1,
        split_reward_round_count=1,
    )
    wrong_provenance = replace(
        metrics,
        observed_outcome_count=1,
        enriched_outcome_count=1,
    )

    with pytest.raises(ValueError, match="metrics do not match"):
        _record(other_scenario, initial, results, metrics, terminal)
    with pytest.raises(ValueError, match="statuses"):
        _record(scenario, initial, results, wrong_statuses, terminal)
    with pytest.raises(ValueError, match="provenance"):
        _record(scenario, initial, results, wrong_provenance, terminal)


def test_record_rejects_hidden_duplicate_and_tampered_results() -> None:
    scenario, initial, results, metrics, terminal = _completed_artifacts()

    with pytest.raises(ValueError, match="counts"):
        _record(
            scenario,
            initial,
            results[:1],
            metrics,
            results[0].participant_state_after,
        )
    with pytest.raises(ValueError, match="identities must be unique"):
        _record(
            scenario,
            initial,
            (results[0], results[0]),
            metrics,
            results[0].participant_state_after,
        )
    with pytest.raises(TypeError, match="immutable"):
        EconomicSimulationRecord(
            rfc010_experiment_identity=EXPERIMENT_IDENTITY,
            economic_scenario=scenario,
            initial_participant_state=initial,
            terminal_participant_state=terminal,
            ordered_economic_round_results=list(results),  # type: ignore[arg-type]
            economic_experiment_metrics=metrics,
            replay_identity=scenario.replay_identity,
        )

    tampered = _runner().run(
        _experiment((17,)),
        _replay((17,)),
        scenario,
        initial,
    )[0]
    object.__setattr__(tampered, "deployed_sol_lamports", 99)
    tampered_metrics = _metrics().aggregate(
        _runner().run(_experiment((17,)), _replay((17,)), scenario, initial)
    )
    with pytest.raises(ValueError, match="result identity"):
        _record(
            scenario,
            initial,
            (tampered,),
            tampered_metrics,
            tampered.participant_state_after,
        )


def test_empty_completed_interval_is_explicit_and_preserves_state() -> None:
    scenario = _scenario()
    state = _state(17, 16)
    metrics = _metrics().aggregate(())

    record = _record(scenario, state, (), metrics, state)

    assert record.ordered_economic_round_result_identities == ()
    assert record.completeness_metadata == (
        ("economically_processed_round_count", 0),
        ("outcome_complete_round_count", 0),
        ("missing_outcome_round_count", 0),
        ("completeness_percentage", None),
    )
    with pytest.raises(ValueError, match="preserve its initial state"):
        _record(scenario, state, (), metrics, _state(18, 17))


def test_phase_eight_contains_no_cli_integration() -> None:
    assert not hasattr(record_module, "CLI")
    assert not hasattr(record_module, "main")
    assert not hasattr(record_module, "argparse")


def _record(
    scenario: EconomicScenario,
    initial: ParticipantEconomicState,
    results: tuple,
    metrics: object,
    terminal: ParticipantEconomicState,
) -> EconomicSimulationRecord:
    return EconomicSimulationRecord(
        rfc010_experiment_identity=EXPERIMENT_IDENTITY,
        economic_scenario=scenario,
        initial_participant_state=initial,
        terminal_participant_state=terminal,
        ordered_economic_round_results=results,
        economic_experiment_metrics=metrics,  # type: ignore[arg-type]
        replay_identity=scenario.replay_identity,
    )


def _completed_artifacts():
    scenario = _scenario()
    initial = _state(17, 16)
    results = _runner().run(
        _experiment((17, 18)),
        _replay((17, 18)),
        scenario,
        initial,
    )
    metrics = _metrics().aggregate(results)
    return scenario, initial, results, metrics, results[-1].participant_state_after


def _metrics() -> EconomicMetricsEngine:
    return EconomicMetricsEngine("rfc011-metrics-v1")


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
    return ExperimentExecution(
        ranked_candidate_sets=candidates,
        deployment_decisions=decisions,
        evaluation_results=evaluations,
        metrics=metrics,
        record=ExperimentRecord(
            experiment_identifier=EXPERIMENT_IDENTITY,
            configuration_identifier="rfc010-configuration-v1",
            implementation_identifier="rfc010-implementation-v1",
            metrics=metrics,
        ),
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


def _replay(rounds: tuple[int, ...]) -> tuple[EconomicReplayRound, ...]:
    return tuple(
        EconomicReplayRound(
            round_identifier=round_identifier,
            decision_slot=10 + index * 20,
            round_deadline_slot=20 + index * 20,
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
