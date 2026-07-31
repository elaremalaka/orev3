"""RFC-011 Phase 9 command-line orchestration helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, replace
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any

from orev3.replay.engine import select_by_slots_remaining
from orev3.replay.loader import load_round_index
from orev3.strategy_lab.economic_metrics import EconomicMetricsEngine
from orev3.strategy_lab.economic_record import EconomicSimulationRecord
from orev3.strategy_lab.economic_runner import (
    EconomicReplayRound,
    EconomicSimulationRunner,
)
from orev3.strategy_lab.economics import (
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
    TransactionAssumptions,
)
from orev3.strategy_lab.experiment import ExperimentExecution
from orev3.strategy_lab.runner import ExperimentConfiguration
from orev3.strategy_lab.settlement import FinalizedReplayFacts


def load_economic_scenario(
    path: Path,
    *,
    dataset_identity: str,
    replay_identity: str,
    deployment_budget_lamports: int | None,
    protocol_revision: str | None,
) -> EconomicScenario:
    """Load one immutable scenario template and bind this replay."""

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    root = _mapping("economic scenario", raw)
    _exact_fields(
        "economic scenario",
        root,
        {
            "capital_reserve_rules",
            "checkpoint_assumptions",
            "component_identities",
            "fee_assumptions",
            "lamport_apportionment_rule",
            "outcome_policy",
            "participant_initial_sol_balance_lamports",
            "per_round_deployment_budget_lamports",
            "protocol_revision",
            "transaction_assumptions",
        },
    )
    reserves = _mapping(
        "capital_reserve_rules",
        root["capital_reserve_rules"],
    )
    _exact_fields(
        "capital_reserve_rules",
        reserves,
        {
            "checkpoint_cost_reserve_lamports",
            "minimum_liquid_reserve_lamports",
            "transaction_cost_reserve_lamports",
        },
    )
    fees = _mapping("fee_assumptions", root["fee_assumptions"])
    _exact_fields(
        "fee_assumptions",
        fees,
        {
            "base_transaction_fee_lamports",
            "checkpoint_transaction_fee_lamports",
            "failed_transaction_fee_lamports",
            "priority_fee_lamports",
        },
    )
    checkpoint = _mapping(
        "checkpoint_assumptions",
        root["checkpoint_assumptions"],
    )
    _exact_fields(
        "checkpoint_assumptions",
        checkpoint,
        {
            "protocol_checkpoint_reserve_lamports",
            "required_before_next_round",
        },
    )
    transactions = _mapping(
        "transaction_assumptions",
        root["transaction_assumptions"],
    )
    _exact_fields(
        "transaction_assumptions",
        transactions,
        {
            "compute_unit_limit",
            "deploy_instruction_compute_units",
            "deploy_instruction_size_bytes",
            "inclusion_latency_slots",
            "maximum_instructions_per_transaction",
            "maximum_transaction_size_bytes",
            "maximum_transactions_per_slot",
            "submission_delay_slots",
            "transaction_base_compute_units",
            "transaction_base_size_bytes",
        },
    )
    policy = _mapping("outcome_policy", root["outcome_policy"])
    _exact_fields(
        "outcome_policy",
        policy,
        {
            "accepted_sources",
            "missing_outcome_policy",
            "require_contiguous_outcomes",
        },
    )
    components = _mapping(
        "component_identities",
        root["component_identities"],
    )
    _exact_fields(
        "component_identities",
        components,
        {
            "allocation_materializer",
            "inclusion_model",
            "metrics_engine",
            "protocol_constraint_model",
            "settlement_model",
            "simulation_runner",
            "transaction_model",
        },
    )

    configured_budget = (
        root["per_round_deployment_budget_lamports"]
        if deployment_budget_lamports is None
        else deployment_budget_lamports
    )
    configured_protocol = (
        root["protocol_revision"]
        if protocol_revision is None
        else protocol_revision
    )
    return EconomicScenario(
        protocol_revision=configured_protocol,
        budget=BudgetModel(
            participant_initial_sol_balance_lamports=(
                root["participant_initial_sol_balance_lamports"]
            ),
            per_round_deployment_budget_lamports=configured_budget,
            capital_reserve_rules=CapitalReserveRules(**reserves),
        ),
        lamport_apportionment_rule=LamportApportionmentRule(
            root["lamport_apportionment_rule"]
        ),
        fee_assumptions=FeeAssumptions(**fees),
        checkpoint_assumptions=CheckpointAssumptions(**checkpoint),
        transaction_assumptions=TransactionAssumptions(**transactions),
        outcome_policy=OutcomePolicy(
            accepted_sources=tuple(policy["accepted_sources"]),
            missing_outcome_policy=MissingOutcomePolicy(
                policy["missing_outcome_policy"]
            ),
            require_contiguous_outcomes=policy[
                "require_contiguous_outcomes"
            ],
        ),
        replay_identity=replay_identity,
        dataset_identity=dataset_identity,
        component_identities=ComponentIdentities(**components),
    )


def execute_economic_simulation(
    *,
    experiment: ExperimentExecution,
    configuration: ExperimentConfiguration,
    scenario: EconomicScenario,
) -> EconomicSimulationRecord:
    """Delegate a completed RFC-010 experiment to existing RFC-011 layers."""

    if not isinstance(experiment, ExperimentExecution):
        raise TypeError("experiment must be an ExperimentExecution")
    if not isinstance(configuration, ExperimentConfiguration):
        raise TypeError("configuration must be ExperimentConfiguration")
    if not isinstance(scenario, EconomicScenario):
        raise TypeError("scenario must be EconomicScenario")

    replay_rounds = _economic_replay_rounds(
        experiment,
        configuration,
        scenario,
    )
    initial_state = ParticipantEconomicState(
        available_sol_lamports=(
            scenario.participant_initial_sol_balance_lamports
        ),
        accrued_sol_lamports=0,
        accrued_ore=0,
        deployed_lamports=(0,) * 25,
        checkpoint_state=CheckpointState.NOT_REQUIRED,
        cumulative_protocol_costs_lamports=0,
        cumulative_transaction_costs_lamports=0,
        current_round=(
            replay_rounds[0].round_identifier if replay_rounds else None
        ),
        last_economically_settled_round=None,
    )
    results = EconomicSimulationRunner(
        scenario.component_identities.simulation_runner
    ).run(
        experiment,
        replay_rounds,
        scenario,
        initial_state,
    )
    metrics = EconomicMetricsEngine(
        scenario.component_identities.metrics_engine
    ).aggregate(results)
    terminal_state = (
        results[-1].participant_state_after if results else initial_state
    )
    return EconomicSimulationRecord(
        rfc010_experiment_identity=(
            experiment.record.experiment_identifier
        ),
        economic_scenario=scenario,
        initial_participant_state=initial_state,
        terminal_participant_state=terminal_state,
        ordered_economic_round_results=results,
        economic_experiment_metrics=metrics,
        replay_identity=scenario.replay_identity,
    )


def write_economic_simulation_record(
    record: EconomicSimulationRecord,
    path: Path,
) -> None:
    """Write one canonical immutable Phase 8 record without overwriting."""

    if not isinstance(record, EconomicSimulationRecord):
        raise TypeError("record must be EconomicSimulationRecord")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                _record_mapping(record),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        )


def dataset_and_replay_identities(
    *,
    dataset_sha256: str,
    configuration_identifier: str,
) -> tuple[str, str]:
    """Return deterministic identities bound to one RFC-010 replay."""

    _canonical_string("dataset_sha256", dataset_sha256)
    _canonical_string("configuration_identifier", configuration_identifier)
    dataset_identity = f"rfc011-dataset-sha256:{dataset_sha256}"
    replay_identity = _identity(
        "rfc011-replay-sha256",
        {
            "configuration_identifier": configuration_identifier,
            "dataset_identity": dataset_identity,
        },
    )
    return dataset_identity, replay_identity


def _economic_replay_rounds(
    experiment: ExperimentExecution,
    configuration: ExperimentConfiguration,
    scenario: EconomicScenario,
) -> tuple[EconomicReplayRound, ...]:
    lifecycles = tuple(
        sorted(
            load_round_index(configuration.dataset_path).values(),
            key=lambda lifecycle: (lifecycle.start_slot, lifecycle.round_id),
        )
    )
    positions = {
        lifecycle.round_id: index
        for index, lifecycle in enumerate(lifecycles)
    }
    evaluations = tuple(experiment.evaluation_results)
    selected_positions: list[int] = []
    replay_rounds: list[EconomicReplayRound] = []
    for evaluation in evaluations:
        round_identifier = evaluation.observation.round_identifier
        try:
            position = positions[round_identifier]
        except KeyError as exc:
            raise ValueError(
                "RFC-010 evaluation round is absent from replay data"
            ) from exc
        lifecycle = lifecycles[position]
        outcome = lifecycle.finalized_outcome
        if outcome is None or lifecycle.finalized_outcome_source is None:
            raise ValueError(
                "RFC-010 evaluated a round without finalized outcome evidence"
            )
        if (
            outcome.entropy is None
            or outcome.winning_square is None
            or lifecycle.end_slot is None
        ):
            raise ValueError(
                "economic replay requires complete finalized protocol facts"
            )
        selection = select_by_slots_remaining(
            lifecycle,
            requested_slots_remaining=(
                configuration.requested_slots_remaining
            ),
            max_slot_distance=configuration.max_slot_distance,
        )
        if not selection.within_tolerance:
            raise ValueError(
                "economic replay point is outside the configured tolerance"
            )
        point = selection.replay_point
        replay_round_identity = _identity(
            "rfc011-economic-replay-round-sha256",
            {
                "dataset_identity": scenario.dataset_identity,
                "decision_slot": point.rpc_slot,
                "outcome_observed_at_utc": (
                    outcome.observed_at_utc.isoformat()
                ),
                "outcome_source": lifecycle.finalized_outcome_source,
                "replay_identity": scenario.replay_identity,
                "round_identifier": round_identifier,
            },
        )
        replay_rounds.append(
            EconomicReplayRound(
                round_identifier=round_identifier,
                decision_slot=point.rpc_slot,
                round_deadline_slot=lifecycle.end_slot,
                outcome=FinalizedReplayFacts(
                    round_identifier=round_identifier,
                    replay_round_identity=replay_round_identity,
                    decision_identity=_decision_identity(
                        evaluation.deployment_decision
                    ),
                    replay_identity=scenario.replay_identity,
                    dataset_identity=scenario.dataset_identity,
                    outcome_source=lifecycle.finalized_outcome_source,
                    completeness_status="complete",
                    entropy=outcome.entropy,
                    winning_square_identifier=outcome.winning_square,
                    historical_deployed_lamports=tuple(
                        outcome.deployed_lamports
                    ),
                    historical_deployed_at_inclusion_lamports=tuple(
                        point.round.deployed_lamports
                    ),
                    historical_miner_counts=tuple(outcome.miner_counts),
                    reward_buckets_raw=tuple(outcome.reward_buckets),
                    total_vaulted_lamports=outcome.total_vaulted,
                    total_winnings_lamports=outcome.total_winnings,
                    motherlode_ore_raw=outcome.round_motherlode,
                    top_miner=outcome.top_miner,
                    synthetic_participant_absent=True,
                ),
            )
        )
        selected_positions.append(position)

    if selected_positions and selected_positions != list(
        range(selected_positions[0], selected_positions[-1] + 1)
    ):
        raise ValueError(
            "economic simulation requires one contiguous outcome-complete "
            "replay interval"
        )
    return tuple(replay_rounds)


def _decision_identity(decision: object) -> str:
    allocations = getattr(decision, "allocations", None)
    if not isinstance(allocations, tuple):
        raise TypeError("evaluation deployment decision is invalid")
    return _identity(
        "rfc010-deployment-decision-sha256",
        {
            "allocations": [
                {
                    "allocation_amount": allocation.allocation_amount,
                    "allocation_weight": allocation.allocation_weight,
                    "metadata": _plain(allocation.metadata),
                    "square_identifier": allocation.square_identifier,
                }
                for allocation in allocations
            ]
        },
    )


def _record_mapping(record: EconomicSimulationRecord) -> dict[str, Any]:
    metrics = record.economic_experiment_metrics
    metric_values = {
        value.name: _plain(getattr(metrics, value.name))
        for value in fields(metrics)
    }
    metric_values.update(
        {
            "capture_efficiency": _plain(metrics.capture_efficiency),
            "completeness_percentage": _plain(
                metrics.completeness_percentage
            ),
            "deployment_budget_utilization": _plain(
                metrics.deployment_budget_utilization
            ),
            "mean_deployed_lamports": _plain(
                metrics.mean_deployed_lamports
            ),
            "mean_dilution": _plain(metrics.mean_dilution),
            "mean_ore_earned_raw": _plain(metrics.mean_ore_earned_raw),
            "mean_winning_square_capital_share": _plain(
                metrics.mean_winning_square_capital_share
            ),
            "net_sol_return_rate": _plain(metrics.net_sol_return_rate),
            "ore_per_sol_deployed": _plain(metrics.ore_per_sol_deployed),
            "solo_reward_frequency": _plain(metrics.solo_reward_frequency),
            "split_reward_frequency": _plain(metrics.split_reward_frequency),
        }
    )
    return {
        "allocation_materializer_identity": (
            record.allocation_materializer_identity
        ),
        "completeness_metadata": _plain(record.completeness_metadata),
        "dataset_identity": record.dataset_identity,
        "deterministic_result_sha256": record.deterministic_result_sha256,
        "economic_experiment_metrics": metric_values,
        "economic_metrics_engine_identity": (
            record.economic_metrics_engine_identity
        ),
        "economic_scenario_identity": record.economic_scenario_identity,
        "economic_scenario_sha256": record.economic_scenario_sha256,
        "economic_simulation_runner_identity": (
            record.economic_simulation_runner_identity
        ),
        "inclusion_model_identity": record.inclusion_model_identity,
        "initial_participant_state_sha256": (
            record.initial_participant_state_sha256
        ),
        "ore_settlement_model_identity": (
            record.ore_settlement_model_identity
        ),
        "ordered_economic_round_result_identities": list(
            record.ordered_economic_round_result_identities
        ),
        "outcome_provenance_summary": _plain(
            record.outcome_provenance_summary
        ),
        "protocol_constraint_model_identity": (
            record.protocol_constraint_model_identity
        ),
        "protocol_revision": record.protocol_revision,
        "record_identity": record.record_identity,
        "replay_identity": record.replay_identity,
        "rfc010_experiment_identity": record.rfc010_experiment_identity,
        "terminal_participant_state_sha256": (
            record.terminal_participant_state_sha256
        ),
        "transaction_model_identity": record.transaction_model_identity,
    }


def _plain(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {
            "denominator": value.denominator,
            "numerator": value.numerator,
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _plain(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _mapping(name: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _exact_fields(name: str, value: dict[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError(f"{name} fields are invalid")


def _canonical_string(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be a canonical string")


def _identity(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


__all__ = (
    "dataset_and_replay_identities",
    "execute_economic_simulation",
    "load_economic_scenario",
    "write_economic_simulation_record",
)
