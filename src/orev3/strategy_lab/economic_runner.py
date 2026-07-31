"""Sequential RFC-011 Phase 6 economic simulation orchestration."""

from __future__ import annotations

from dataclasses import dataclass, replace

from orev3.strategy_lab.constraints import (
    ProtocolConstraintModel,
    ProtocolDeploymentPlan,
)
from orev3.strategy_lab.economics import (
    SQUARE_COUNT,
    CheckpointState,
    EconomicScenario,
    ParticipantEconomicState,
)
from orev3.strategy_lab.deployment import DeploymentDecision
from orev3.strategy_lab.evaluation import EvaluationResult
from orev3.strategy_lab.experiment import ExperimentExecution
from orev3.strategy_lab.materialization import AllocationMaterializer
from orev3.strategy_lab.settlement import (
    EconomicRoundResult,
    EconomicRoundStatus,
    FinalizedReplayFacts,
    MissingFinalizedOutcome,
    ORESettlementModel,
    SettlementRejectionCode,
)
from orev3.strategy_lab.transactions import TransactionModel


@dataclass(frozen=True, slots=True)
class EconomicReplayRound:
    """Immutable timing and outcome facts for one economic replay round."""

    round_identifier: int
    decision_slot: int
    round_deadline_slot: int
    outcome: FinalizedReplayFacts | MissingFinalizedOutcome

    def __post_init__(self) -> None:
        _validate_nonnegative_integer("round_identifier", self.round_identifier)
        _validate_nonnegative_integer("decision_slot", self.decision_slot)
        _validate_nonnegative_integer(
            "round_deadline_slot",
            self.round_deadline_slot,
        )
        if self.round_deadline_slot <= self.decision_slot:
            raise ValueError("round deadline must follow the decision slot")
        if not isinstance(
            self.outcome,
            (FinalizedReplayFacts, MissingFinalizedOutcome),
        ):
            raise TypeError(
                "outcome must be finalized facts or a missing-outcome fact"
            )
        if self.outcome.round_identifier != self.round_identifier:
            raise ValueError("replay round and outcome identities must agree")


@dataclass(frozen=True, slots=True)
class EconomicSimulationRunner:
    """Run one contiguous RFC-011 interval in immutable replay order."""

    model_identity: str

    def __post_init__(self) -> None:
        _validate_identity("model_identity", self.model_identity)

    def run(
        self,
        experiment: ExperimentExecution,
        replay_rounds: tuple[EconomicReplayRound, ...],
        scenario: EconomicScenario,
        initial_state: ParticipantEconomicState,
    ) -> tuple[EconomicRoundResult, ...]:
        """Return ordered results through the first unresolved round."""

        if not isinstance(experiment, ExperimentExecution):
            raise TypeError("experiment must be an ExperimentExecution")
        if not isinstance(replay_rounds, tuple) or not all(
            isinstance(value, EconomicReplayRound) for value in replay_rounds
        ):
            raise TypeError(
                "replay_rounds must be an immutable EconomicReplayRound tuple"
            )
        if not isinstance(scenario, EconomicScenario):
            raise TypeError("scenario must be an EconomicScenario")
        if not isinstance(initial_state, ParticipantEconomicState):
            raise TypeError(
                "initial_state must be a ParticipantEconomicState"
            )
        if self.model_identity != scenario.component_identities.simulation_runner:
            raise ValueError(
                "simulation runner identity does not match the scenario"
            )

        paired = _validated_experiment_pairs(experiment)
        selected = _select_contiguous_interval(paired, replay_rounds)
        _validate_replay_order(replay_rounds)
        _validate_initial_state(initial_state, replay_rounds)
        if not replay_rounds:
            return ()

        materializer = AllocationMaterializer()
        constraints = ProtocolConstraintModel(scenario.protocol_revision)
        transactions = TransactionModel(
            scenario.component_identities.transaction_model
        )
        settlement = ORESettlementModel(
            scenario.protocol_revision,
            scenario.component_identities.settlement_model,
        )

        state = initial_state
        results: list[EconomicRoundResult] = []
        for index, (round_input, pair) in enumerate(
            zip(replay_rounds, selected, strict=True)
        ):
            decision, evaluation = pair
            _validate_round_state(state, round_input.round_identifier)
            _validate_outcome_binding(round_input, scenario)

            proposed = materializer.materialize(decision, scenario)
            deployment = constraints.validate(proposed, scenario, state)
            transaction_result = (
                transactions.evaluate(
                    deployment,
                    scenario,
                    decision_slot=round_input.decision_slot,
                    round_deadline_slot=round_input.round_deadline_slot,
                )
                if isinstance(deployment, ProtocolDeploymentPlan)
                else None
            )
            if isinstance(round_input.outcome, MissingFinalizedOutcome):
                result = settlement.classify_missing_outcome(
                    deployment,
                    transaction_result,
                    evaluation,
                    round_input.outcome,
                    scenario,
                    state,
                )
            else:
                result = settlement.settle(
                    deployment,
                    transaction_result,
                    evaluation,
                    round_input.outcome,
                    scenario,
                    state,
                )
            _validate_result_continuity(
                result,
                state,
                round_input,
                scenario,
            )
            results.append(result)

            if _breaks_interval(result):
                break
            if index + 1 < len(replay_rounds):
                state = _advance_to_round(
                    result,
                    state,
                    replay_rounds[index + 1].round_identifier,
                    scenario,
                )

        return tuple(results)


def _validated_experiment_pairs(
    experiment: ExperimentExecution,
) -> tuple[tuple[DeploymentDecision, EvaluationResult], ...]:
    decisions = tuple(experiment.deployment_decisions)
    evaluations = tuple(experiment.evaluation_results)
    if not all(isinstance(value, DeploymentDecision) for value in decisions):
        raise TypeError(
            "experiment decisions must be DeploymentDecision values"
        )
    if (
        len(experiment.ranked_candidate_sets) != len(decisions)
        or len(decisions) != len(evaluations)
        or experiment.metrics.evaluation_count != len(evaluations)
        or experiment.record.metrics != experiment.metrics
    ):
        raise ValueError(
            "RFC-010 experiment artifacts are not count-aligned"
        )
    pairs: list[tuple[DeploymentDecision, EvaluationResult]] = []
    round_identifiers: list[int] = []
    for decision, evaluation in zip(decisions, evaluations, strict=True):
        if not isinstance(evaluation, EvaluationResult):
            raise TypeError(
                "experiment evaluations must be EvaluationResult values"
            )
        if evaluation.deployment_decision != decision:
            raise ValueError(
                "experiment evaluation is not bound to its deployment decision"
            )
        round_identifiers.append(evaluation.observation.round_identifier)
        pairs.append((decision, evaluation))
    if len(set(round_identifiers)) != len(round_identifiers):
        raise ValueError("experiment round evaluations must be unique")
    return tuple(pairs)


def _select_contiguous_interval(
    pairs: tuple[tuple[DeploymentDecision, EvaluationResult], ...],
    replay_rounds: tuple[EconomicReplayRound, ...],
) -> tuple[tuple[DeploymentDecision, EvaluationResult], ...]:
    if not replay_rounds:
        return ()
    by_round = {
        evaluation.observation.round_identifier: index
        for index, (_, evaluation) in enumerate(pairs)
    }
    try:
        indices = tuple(
            by_round[value.round_identifier] for value in replay_rounds
        )
    except KeyError as exc:
        raise ValueError(
            "replay interval contains a round outside the experiment"
        ) from exc
    expected = tuple(range(indices[0], indices[0] + len(indices)))
    if indices != expected:
        raise ValueError(
            "replay rounds must be one contiguous experiment interval"
        )
    return tuple(pairs[index] for index in indices)


def _validate_replay_order(
    replay_rounds: tuple[EconomicReplayRound, ...],
) -> None:
    decision_slots = tuple(value.decision_slot for value in replay_rounds)
    if any(
        later <= earlier
        for earlier, later in zip(decision_slots, decision_slots[1:])
    ):
        raise ValueError("replay decision slots must be strictly increasing")


def _validate_initial_state(
    state: ParticipantEconomicState,
    replay_rounds: tuple[EconomicReplayRound, ...],
) -> None:
    _validate_state_identity(state)
    if any(state.deployed_lamports):
        raise ValueError(
            "an interval initial state must not contain an open deployment"
        )
    if state.checkpoint_state is CheckpointState.REQUIRED:
        raise ValueError(
            "an interval initial state cannot require an unresolved checkpoint"
        )
    if replay_rounds and state.current_round != replay_rounds[0].round_identifier:
        raise ValueError(
            "initial participant state must identify the interval's first round"
        )
    if (
        state.current_round is not None
        and state.last_economically_settled_round is not None
        and state.last_economically_settled_round >= state.current_round
    ):
        raise ValueError(
            "an interval cannot restart an economically settled round"
        )


def _validate_round_state(
    state: ParticipantEconomicState,
    round_identifier: int,
) -> None:
    _validate_state_identity(state)
    if state.current_round != round_identifier:
        raise ValueError("participant state continuity is broken")
    if (
        state.last_economically_settled_round is not None
        and state.last_economically_settled_round >= round_identifier
    ):
        raise ValueError("participant state would replay a settled round")
    if any(state.deployed_lamports):
        raise ValueError("participant state contains an unclosed deployment")
    if state.checkpoint_state is CheckpointState.REQUIRED:
        raise ValueError("participant state requires checkpoint completion")


def _validate_outcome_binding(
    round_input: EconomicReplayRound,
    scenario: EconomicScenario,
) -> None:
    outcome = round_input.outcome
    if outcome.replay_identity != scenario.replay_identity:
        raise ValueError("replay outcome identity does not match the scenario")
    if outcome.dataset_identity != scenario.dataset_identity:
        raise ValueError("dataset outcome identity does not match the scenario")
    if isinstance(outcome, FinalizedReplayFacts):
        if outcome.outcome_source not in scenario.outcome_policy.accepted_sources:
            raise ValueError("outcome provenance is not accepted by the scenario")
        if outcome.completeness_status != "complete":
            raise ValueError("finalized replay facts are not outcome-complete")


def _validate_state_identity(state: ParticipantEconomicState) -> None:
    try:
        identity_matches = replace(state).state_identity == state.state_identity
    except (TypeError, ValueError):
        identity_matches = False
    if not identity_matches:
        raise ValueError("participant state identity is inconsistent")


def _validate_result_continuity(
    result: EconomicRoundResult,
    state: ParticipantEconomicState,
    round_input: EconomicReplayRound,
    scenario: EconomicScenario,
) -> None:
    if result.round_identifier != round_input.round_identifier:
        raise ValueError("economic result round ordering is inconsistent")
    if result.participant_state_before_identity != state.state_identity:
        raise ValueError("economic result does not consume the current state")
    if (
        result.scenario_identity != scenario.scenario_identity
        or result.protocol_revision != scenario.protocol_revision
    ):
        raise ValueError("economic result identities are inconsistent")


def _breaks_interval(result: EconomicRoundResult) -> bool:
    if result.status is EconomicRoundStatus.MISSING_OUTCOME:
        return True
    if result.status is EconomicRoundStatus.SETTLED:
        return False
    if result.status is EconomicRoundStatus.UNINCLUDED:
        return False
    return any(
        reason.code is not SettlementRejectionCode.PROTOCOL_REJECTION
        for reason in result.rejection_reasons
    )


def _advance_to_round(
    result: EconomicRoundResult,
    prior_state: ParticipantEconomicState,
    next_round: int,
    scenario: EconomicScenario,
) -> ParticipantEconomicState:
    post = result.participant_state_after
    if result.status is EconomicRoundStatus.SETTLED:
        if post.last_economically_settled_round != result.round_identifier:
            raise ValueError("settled result did not advance settlement state")
        if (
            any(post.deployed_lamports)
            and scenario.checkpoint_assumptions.required_before_next_round
            and post.checkpoint_state is not CheckpointState.COMPLETED
        ):
            raise ValueError("settled deployment did not complete checkpoint")
    elif post.state_identity != prior_state.state_identity:
        raise ValueError("unsettled result must not mutate participant state")

    return ParticipantEconomicState(
        available_sol_lamports=post.available_sol_lamports,
        accrued_sol_lamports=post.accrued_sol_lamports,
        accrued_ore=post.accrued_ore,
        deployed_lamports=(0,) * SQUARE_COUNT,
        checkpoint_state=CheckpointState.NOT_REQUIRED,
        cumulative_protocol_costs_lamports=(
            post.cumulative_protocol_costs_lamports
        ),
        cumulative_transaction_costs_lamports=(
            post.cumulative_transaction_costs_lamports
        ),
        current_round=next_round,
        last_economically_settled_round=(
            post.last_economically_settled_round
        ),
    )


def _validate_identity(name: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
    ):
        raise ValueError(f"{name} must be a nonempty canonical string")


def _validate_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


__all__ = ("EconomicReplayRound", "EconomicSimulationRunner")
