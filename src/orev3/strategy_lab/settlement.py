"""Deterministic protocol-native RFC-011 Phase 5 settlement."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from orev3.strategy_lab.constraints import (
    ProtocolDeploymentPlan,
    ProtocolRejection,
)
from orev3.strategy_lab.economics import (
    SQUARE_COUNT,
    CheckpointState,
    EconomicScenario,
    ParticipantEconomicState,
)
from orev3.strategy_lab.evaluation import EvaluationResult
from orev3.strategy_lab.transactions import (
    TransactionInclusionResult,
    protocol_deployment_plan_identity,
)


SUPPORTED_PROTOCOL_REVISION = "ore-v3-program-3112ab78"
SPLIT_REWARD_ADDRESS = "SpLiT11111111111111111111111111111111111112"


class EconomicRoundStatus(str, Enum):
    """Terminal Phase 5 status for one replay round."""

    SETTLED = "settled"
    REJECTED = "rejected"
    UNINCLUDED = "unincluded"


class ORERewardTreatment(str, Enum):
    """Protocol treatment of the base ORE reward."""

    NONE = "none"
    SPLIT = "split"
    SOLO = "solo"


class SettlementRejectionCode(str, Enum):
    """Stable fail-closed settlement rejection codes."""

    PROTOCOL_REJECTION = "protocol_rejection"
    TRANSACTION_REJECTION = "transaction_rejection"
    SETTLEMENT_MODEL_IDENTITY_MISMATCH = (
        "settlement_model_identity_mismatch"
    )
    PROTOCOL_REVISION_MISMATCH = "protocol_revision_mismatch"
    SCENARIO_IDENTITY_MISMATCH = "scenario_identity_mismatch"
    PARTICIPANT_STATE_IDENTITY_MISMATCH = (
        "participant_state_identity_mismatch"
    )
    TRANSACTION_BINDING_MISMATCH = "transaction_binding_mismatch"
    ROUND_IDENTITY_MISMATCH = "round_identity_mismatch"
    EVALUATION_WINNER_MISMATCH = "evaluation_winner_mismatch"
    EVALUATION_HIT_MISMATCH = "evaluation_hit_mismatch"
    REPLAY_IDENTITY_MISMATCH = "replay_identity_mismatch"
    DATASET_IDENTITY_MISMATCH = "dataset_identity_mismatch"
    OUTCOME_SOURCE_REJECTED = "outcome_source_rejected"
    OUTCOME_INCOMPLETE = "outcome_incomplete"
    HISTORICAL_PARTICIPANT_DOUBLE_COUNT = (
        "historical_participant_double_count"
    )
    COUNTERFACTUAL_REWARD_STATE_UNAVAILABLE = (
        "counterfactual_reward_state_unavailable"
    )
    AVAILABLE_BALANCE_EXCEEDED = "available_balance_exceeded"


@dataclass(frozen=True, slots=True)
class SettlementRejection:
    """One immutable reason an economic result was not settled."""

    code: SettlementRejectionCode
    message: str
    source_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, SettlementRejectionCode):
            raise TypeError("code must be a SettlementRejectionCode")
        _validate_string("message", self.message)
        if self.source_code is not None:
            _validate_string("source_code", self.source_code)


@dataclass(frozen=True, slots=True)
class FinalizedReplayFacts:
    """Outcome-complete immutable facts needed for one settlement."""

    round_identifier: int
    replay_round_identity: str
    decision_identity: str
    replay_identity: str
    dataset_identity: str
    outcome_source: str
    completeness_status: str
    entropy: int
    winning_square_identifier: int
    historical_deployed_lamports: tuple[int, ...]
    historical_deployed_at_inclusion_lamports: tuple[int, ...]
    historical_miner_counts: tuple[int, ...]
    reward_buckets_raw: tuple[int, ...]
    total_vaulted_lamports: int
    total_winnings_lamports: int
    motherlode_ore_raw: int
    top_miner: str
    synthetic_participant_absent: bool
    finalized_outcome_identity: str = field(init=False)

    def __post_init__(self) -> None:
        _validate_nonnegative_integer("round_identifier", self.round_identifier)
        for name, value in (
            ("replay_round_identity", self.replay_round_identity),
            ("decision_identity", self.decision_identity),
            ("replay_identity", self.replay_identity),
            ("dataset_identity", self.dataset_identity),
            ("outcome_source", self.outcome_source),
            ("completeness_status", self.completeness_status),
            ("top_miner", self.top_miner),
        ):
            _validate_string(name, value)
        _validate_nonnegative_integer("entropy", self.entropy)
        if self.entropy > (1 << 64) - 1:
            raise ValueError("entropy must fit in an unsigned 64-bit integer")
        if (
            isinstance(self.winning_square_identifier, bool)
            or not isinstance(self.winning_square_identifier, int)
            or not 0 <= self.winning_square_identifier < SQUARE_COUNT
        ):
            raise ValueError("winning_square_identifier must be in 0..24")
        if self.winning_square_identifier != self.entropy % SQUARE_COUNT:
            raise ValueError("winning square is inconsistent with entropy")

        finalized = _square_vector(
            "historical_deployed_lamports",
            self.historical_deployed_lamports,
        )
        at_inclusion = _square_vector(
            "historical_deployed_at_inclusion_lamports",
            self.historical_deployed_at_inclusion_lamports,
        )
        miners = _square_vector(
            "historical_miner_counts",
            self.historical_miner_counts,
        )
        rewards = _square_vector(
            "reward_buckets_raw",
            self.reward_buckets_raw,
        )
        if any(
            observed > final
            for observed, final in zip(at_inclusion, finalized, strict=True)
        ):
            raise ValueError(
                "inclusion-point deployment cannot exceed finalized deployment"
            )
        for name, value in (
            ("total_vaulted_lamports", self.total_vaulted_lamports),
            ("total_winnings_lamports", self.total_winnings_lamports),
            ("motherlode_ore_raw", self.motherlode_ore_raw),
        ):
            _validate_nonnegative_integer(name, value)
        if not isinstance(self.synthetic_participant_absent, bool):
            raise TypeError("synthetic_participant_absent must be a boolean")

        expected_winnings, expected_vaulted = _round_pool_values(
            finalized,
            self.winning_square_identifier,
        )
        if self.total_winnings_lamports != expected_winnings:
            raise ValueError(
                "total_winnings_lamports is inconsistent with protocol arithmetic"
            )
        if self.total_vaulted_lamports != expected_vaulted:
            raise ValueError(
                "total_vaulted_lamports is inconsistent with protocol arithmetic"
            )

        object.__setattr__(self, "historical_deployed_lamports", finalized)
        object.__setattr__(
            self,
            "historical_deployed_at_inclusion_lamports",
            at_inclusion,
        )
        object.__setattr__(self, "historical_miner_counts", miners)
        object.__setattr__(self, "reward_buckets_raw", rewards)
        object.__setattr__(
            self,
            "finalized_outcome_identity",
            _identity(
                "rfc011-finalized-outcome-sha256",
                self._identity_payload(),
            ),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "completeness_status": self.completeness_status,
            "dataset_identity": self.dataset_identity,
            "decision_identity": self.decision_identity,
            "entropy": self.entropy,
            "historical_deployed_at_inclusion_lamports": list(
                self.historical_deployed_at_inclusion_lamports
            ),
            "historical_deployed_lamports": list(
                self.historical_deployed_lamports
            ),
            "historical_miner_counts": list(self.historical_miner_counts),
            "motherlode_ore_raw": self.motherlode_ore_raw,
            "outcome_source": self.outcome_source,
            "replay_identity": self.replay_identity,
            "replay_round_identity": self.replay_round_identity,
            "reward_buckets_raw": list(self.reward_buckets_raw),
            "round_identifier": self.round_identifier,
            "synthetic_participant_absent": self.synthetic_participant_absent,
            "top_miner": self.top_miner,
            "total_vaulted_lamports": self.total_vaulted_lamports,
            "total_winnings_lamports": self.total_winnings_lamports,
            "winning_square_identifier": self.winning_square_identifier,
        }


@dataclass(frozen=True, slots=True)
class EconomicRoundResult:
    """Immutable factual protocol-economic result for one replay round."""

    status: EconomicRoundStatus
    round_identifier: int | None
    scenario_identity: str
    protocol_revision: str
    participant_state_before_identity: str
    participant_state_after: ParticipantEconomicState
    protocol_deployment_plan_identity: str | None
    transaction_plan_identity: str | None
    evaluation_result_identity: str | None
    finalized_outcome_identity: str | None
    replay_round_identity: str | None
    decision_identity: str | None
    outcome_source: str | None
    completeness_status: str
    finalized_entropy: int | None
    winning_square_identifier: int | None
    materialized_deployment_lamports: tuple[int, ...]
    historical_deployed_lamports: tuple[int, ...]
    counterfactual_deployed_lamports: tuple[int, ...]
    occupied_square_count: int
    instruction_count: int
    transaction_count: int
    rejection_reasons: tuple[SettlementRejection, ...]
    deployed_sol_lamports: int
    returned_principal_lamports: int
    sol_winnings_lamports: int
    protocol_deductions_lamports: int
    transaction_fees_lamports: int
    priority_fees_lamports: int
    checkpoint_costs_lamports: int
    gross_sol_outflow_lamports: int
    gross_sol_inflow_lamports: int
    net_sol_change_lamports: int
    base_ore_earned_raw: int
    motherlode_ore_earned_raw: int
    ore_earned_raw: int
    reward_treatment: ORERewardTreatment
    participant_winning_square_lamports: int
    historical_winning_square_lamports: int
    counterfactual_winning_square_lamports: int
    counterfactual_total_winnings_lamports: int
    counterfactual_total_vaulted_lamports: int
    dilution_numerator_lamports: int
    dilution_denominator_lamports: int
    capture_efficiency_ore_raw_numerator: int
    capture_efficiency_deployed_lamports_denominator: int
    result_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.status, EconomicRoundStatus):
            raise TypeError("status must be an EconomicRoundStatus")
        if self.round_identifier is not None:
            _validate_nonnegative_integer(
                "round_identifier",
                self.round_identifier,
            )
        for name, value in (
            ("scenario_identity", self.scenario_identity),
            ("protocol_revision", self.protocol_revision),
            (
                "participant_state_before_identity",
                self.participant_state_before_identity,
            ),
            ("completeness_status", self.completeness_status),
        ):
            _validate_string(name, value)
        for name, value in (
            (
                "protocol_deployment_plan_identity",
                self.protocol_deployment_plan_identity,
            ),
            ("transaction_plan_identity", self.transaction_plan_identity),
            ("evaluation_result_identity", self.evaluation_result_identity),
            ("finalized_outcome_identity", self.finalized_outcome_identity),
            ("replay_round_identity", self.replay_round_identity),
            ("decision_identity", self.decision_identity),
            ("outcome_source", self.outcome_source),
        ):
            if value is not None:
                _validate_string(name, value)
        if self.finalized_entropy is not None:
            _validate_nonnegative_integer(
                "finalized_entropy",
                self.finalized_entropy,
            )
        if self.winning_square_identifier is not None and (
            isinstance(self.winning_square_identifier, bool)
            or not isinstance(self.winning_square_identifier, int)
            or not 0 <= self.winning_square_identifier < SQUARE_COUNT
        ):
            raise ValueError("winning_square_identifier must be in 0..24")
        if not isinstance(
            self.participant_state_after,
            ParticipantEconomicState,
        ):
            raise TypeError(
                "participant_state_after must be ParticipantEconomicState"
            )
        materialized = _square_vector(
            "materialized_deployment_lamports",
            self.materialized_deployment_lamports,
        )
        historical = _square_vector(
            "historical_deployed_lamports",
            self.historical_deployed_lamports,
        )
        adjusted = _square_vector(
            "counterfactual_deployed_lamports",
            self.counterfactual_deployed_lamports,
        )
        for name, value in (
            ("occupied_square_count", self.occupied_square_count),
            ("instruction_count", self.instruction_count),
            ("transaction_count", self.transaction_count),
            ("deployed_sol_lamports", self.deployed_sol_lamports),
            ("returned_principal_lamports", self.returned_principal_lamports),
            ("sol_winnings_lamports", self.sol_winnings_lamports),
            ("protocol_deductions_lamports", self.protocol_deductions_lamports),
            ("transaction_fees_lamports", self.transaction_fees_lamports),
            ("priority_fees_lamports", self.priority_fees_lamports),
            ("checkpoint_costs_lamports", self.checkpoint_costs_lamports),
            ("gross_sol_outflow_lamports", self.gross_sol_outflow_lamports),
            ("gross_sol_inflow_lamports", self.gross_sol_inflow_lamports),
            ("base_ore_earned_raw", self.base_ore_earned_raw),
            ("motherlode_ore_earned_raw", self.motherlode_ore_earned_raw),
            ("ore_earned_raw", self.ore_earned_raw),
            (
                "participant_winning_square_lamports",
                self.participant_winning_square_lamports,
            ),
            (
                "historical_winning_square_lamports",
                self.historical_winning_square_lamports,
            ),
            (
                "counterfactual_winning_square_lamports",
                self.counterfactual_winning_square_lamports,
            ),
            (
                "counterfactual_total_winnings_lamports",
                self.counterfactual_total_winnings_lamports,
            ),
            (
                "counterfactual_total_vaulted_lamports",
                self.counterfactual_total_vaulted_lamports,
            ),
            ("dilution_numerator_lamports", self.dilution_numerator_lamports),
            (
                "dilution_denominator_lamports",
                self.dilution_denominator_lamports,
            ),
            (
                "capture_efficiency_ore_raw_numerator",
                self.capture_efficiency_ore_raw_numerator,
            ),
            (
                "capture_efficiency_deployed_lamports_denominator",
                self.capture_efficiency_deployed_lamports_denominator,
            ),
        ):
            _validate_nonnegative_integer(name, value)
        if isinstance(self.net_sol_change_lamports, bool) or not isinstance(
            self.net_sol_change_lamports,
            int,
        ):
            raise TypeError("net_sol_change_lamports must be an integer")
        if not isinstance(self.reward_treatment, ORERewardTreatment):
            raise TypeError("reward_treatment must be an ORERewardTreatment")
        reasons = tuple(self.rejection_reasons)
        if not all(isinstance(value, SettlementRejection) for value in reasons):
            raise TypeError("rejection_reasons must contain SettlementRejection")
        if self.status is EconomicRoundStatus.SETTLED and reasons:
            raise ValueError("settled results cannot contain rejection reasons")
        if self.status is not EconomicRoundStatus.SETTLED and not reasons:
            raise ValueError("unsettled results require rejection reasons")
        if self.ore_earned_raw != (
            self.base_ore_earned_raw + self.motherlode_ore_earned_raw
        ):
            raise ValueError("ORE components do not sum to total ORE")
        if self.gross_sol_inflow_lamports != (
            self.returned_principal_lamports + self.sol_winnings_lamports
        ):
            raise ValueError("SOL inflow components are inconsistent")
        if self.net_sol_change_lamports != (
            self.gross_sol_inflow_lamports
            - self.gross_sol_outflow_lamports
        ):
            raise ValueError("net SOL change is inconsistent")
        object.__setattr__(
            self,
            "materialized_deployment_lamports",
            materialized,
        )
        object.__setattr__(self, "historical_deployed_lamports", historical)
        object.__setattr__(self, "counterfactual_deployed_lamports", adjusted)
        object.__setattr__(self, "rejection_reasons", reasons)
        object.__setattr__(
            self,
            "result_identity",
            _identity(
                "rfc011-economic-round-result-sha256",
                self._identity_payload(),
            ),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            name: (
                value.value
                if isinstance(value, Enum)
                else value.state_identity
                if isinstance(value, ParticipantEconomicState)
                else [_rejection_payload(item) for item in value]
                if name == "rejection_reasons"
                else list(value)
                if isinstance(value, tuple)
                else value
            )
            for name, value in (
                (field_name, getattr(self, field_name))
                for field_name in self.__dataclass_fields__
                if field_name != "result_identity"
            )
        }


@dataclass(frozen=True, slots=True)
class ORESettlementModel:
    """Settle one included synthetic deployment under pinned ORE semantics."""

    protocol_revision: str
    model_identity: str

    def __post_init__(self) -> None:
        _validate_string("protocol_revision", self.protocol_revision)
        _validate_string("model_identity", self.model_identity)

    def settle(
        self,
        deployment: ProtocolDeploymentPlan | ProtocolRejection,
        transaction_result: TransactionInclusionResult | None,
        evaluation_result: EvaluationResult | None,
        finalized_facts: FinalizedReplayFacts | None,
        scenario: EconomicScenario,
        participant_state: ParticipantEconomicState,
    ) -> EconomicRoundResult:
        """Return a settled, rejected, or unincluded immutable result."""

        if not isinstance(deployment, (ProtocolDeploymentPlan, ProtocolRejection)):
            raise TypeError("deployment must be a plan or protocol rejection")
        if not isinstance(scenario, EconomicScenario):
            raise TypeError("scenario must be an EconomicScenario")
        if not isinstance(participant_state, ParticipantEconomicState):
            raise TypeError("participant_state must be ParticipantEconomicState")

        common_reasons = self._binding_reasons(scenario)
        if isinstance(deployment, ProtocolRejection):
            common_reasons.extend(
                SettlementRejection(
                    code=SettlementRejectionCode.PROTOCOL_REJECTION,
                    message=value.message,
                    source_code=value.code.value,
                )
                for value in deployment.violations
            )
            return _unsettled_result(
                status=EconomicRoundStatus.REJECTED,
                scenario=scenario,
                participant_state=participant_state,
                reasons=tuple(common_reasons),
            )

        plan_identity = protocol_deployment_plan_identity(deployment)
        reasons = common_reasons
        if deployment.scenario_identity != scenario.scenario_identity:
            reasons.append(
                _reason(
                    SettlementRejectionCode.SCENARIO_IDENTITY_MISMATCH,
                    "deployment scenario identity does not match the scenario",
                )
            )
        if deployment.protocol_revision != self.protocol_revision:
            reasons.append(
                _reason(
                    SettlementRejectionCode.PROTOCOL_REVISION_MISMATCH,
                    "deployment protocol revision does not match the model",
                )
            )
        if deployment.participant_state_identity != participant_state.state_identity:
            reasons.append(
                _reason(
                    SettlementRejectionCode.PARTICIPANT_STATE_IDENTITY_MISMATCH,
                    "deployment participant state identity does not match",
                )
            )
        if transaction_result is None:
            raise TypeError("a protocol deployment plan requires transaction_result")
        if not isinstance(transaction_result, TransactionInclusionResult):
            raise TypeError(
                "transaction_result must be TransactionInclusionResult"
            )
        if (
            transaction_result.protocol_deployment_plan_identity
            != plan_identity
            or transaction_result.scenario_identity != scenario.scenario_identity
        ):
            reasons.append(
                _reason(
                    SettlementRejectionCode.TRANSACTION_BINDING_MISMATCH,
                    "transaction result is not bound to this deployment and scenario",
                )
            )
        if reasons:
            return _unsettled_result(
                status=EconomicRoundStatus.REJECTED,
                scenario=scenario,
                participant_state=participant_state,
                reasons=tuple(reasons),
                deployment=deployment,
                transaction_result=transaction_result,
            )
        if not transaction_result.included:
            transaction_reasons = tuple(
                SettlementRejection(
                    code=SettlementRejectionCode.TRANSACTION_REJECTION,
                    message=value.message,
                    source_code=value.code.value,
                )
                for value in transaction_result.rejection_reasons
            )
            return _unsettled_result(
                status=EconomicRoundStatus.UNINCLUDED,
                scenario=scenario,
                participant_state=participant_state,
                reasons=transaction_reasons,
                deployment=deployment,
                transaction_result=transaction_result,
            )
        if evaluation_result is None or finalized_facts is None:
            raise TypeError(
                "included deployment requires evaluation_result and finalized_facts"
            )
        if not isinstance(evaluation_result, EvaluationResult):
            raise TypeError("evaluation_result must be EvaluationResult")
        if not isinstance(finalized_facts, FinalizedReplayFacts):
            raise TypeError("finalized_facts must be FinalizedReplayFacts")

        reconciliation = _reconciliation_reasons(
            deployment,
            evaluation_result,
            finalized_facts,
            scenario,
            participant_state,
        )
        if reconciliation:
            return _unsettled_result(
                status=EconomicRoundStatus.REJECTED,
                scenario=scenario,
                participant_state=participant_state,
                reasons=tuple(reconciliation),
                deployment=deployment,
                transaction_result=transaction_result,
                evaluation_result=evaluation_result,
                finalized_facts=finalized_facts,
            )
        return _settled_result(
            deployment,
            transaction_result,
            evaluation_result,
            finalized_facts,
            scenario,
            participant_state,
        )

    def _binding_reasons(
        self,
        scenario: EconomicScenario,
    ) -> list[SettlementRejection]:
        reasons: list[SettlementRejection] = []
        if self.protocol_revision != SUPPORTED_PROTOCOL_REVISION:
            reasons.append(
                _reason(
                    SettlementRejectionCode.PROTOCOL_REVISION_MISMATCH,
                    "settlement model does not support this protocol revision",
                )
            )
        if scenario.protocol_revision != self.protocol_revision:
            reasons.append(
                _reason(
                    SettlementRejectionCode.PROTOCOL_REVISION_MISMATCH,
                    "scenario protocol revision does not match the model",
                )
            )
        if self.model_identity != scenario.component_identities.settlement_model:
            reasons.append(
                _reason(
                    SettlementRejectionCode.SETTLEMENT_MODEL_IDENTITY_MISMATCH,
                    "settlement model identity does not match the scenario",
                )
            )
        return reasons


def _settled_result(
    deployment: ProtocolDeploymentPlan,
    transaction_result: TransactionInclusionResult,
    evaluation_result: EvaluationResult,
    facts: FinalizedReplayFacts,
    scenario: EconomicScenario,
    state: ParticipantEconomicState,
) -> EconomicRoundResult:
    winner = facts.winning_square_identifier
    participant_winner = deployment.deployed_lamports[winner]
    adjusted = tuple(
        historical + synthetic
        for historical, synthetic in zip(
            facts.historical_deployed_lamports,
            deployment.deployed_lamports,
            strict=True,
        )
    )
    adjusted_winner = adjusted[winner]
    adjusted_winnings, adjusted_vaulted = _round_pool_values(adjusted, winner)

    principal_deduction = (
        max(participant_winner // 100, 1) if participant_winner else 0
    )
    returned_principal = participant_winner - principal_deduction
    sol_winnings = (
        adjusted_winnings * participant_winner // adjusted_winner
        if participant_winner
        else 0
    )
    base_reward = sum(facts.reward_buckets_raw)
    if participant_winner == 0:
        treatment = ORERewardTreatment.NONE
        base_ore = 0
    elif facts.top_miner == SPLIT_REWARD_ADDRESS:
        treatment = ORERewardTreatment.SPLIT
        base_ore = base_reward * participant_winner // adjusted_winner
    else:
        treatment = ORERewardTreatment.SOLO
        sample = _reverse_u64(facts.entropy) % adjusted_winner
        cumulative = facts.historical_deployed_at_inclusion_lamports[winner]
        base_ore = (
            base_reward
            if cumulative <= sample < cumulative + participant_winner
            else 0
        )
    motherlode_ore = (
        facts.motherlode_ore_raw * participant_winner // adjusted_winner
        if participant_winner
        else 0
    )
    ore_earned = base_ore + motherlode_ore

    deployed = deployment.total_deployed_lamports
    transaction_fees = transaction_result.modeled_transaction_costs_lamports
    priority_fees = transaction_result.modeled_priority_costs_lamports
    if deployed:
        checkpoint_protocol = (
            scenario.checkpoint_assumptions
            .protocol_checkpoint_reserve_lamports
        )
        checkpoint_transaction = (
            scenario.fee_assumptions.checkpoint_transaction_fee_lamports
        )
    else:
        checkpoint_protocol = 0
        checkpoint_transaction = 0
    checkpoint_costs = checkpoint_protocol + checkpoint_transaction
    outflow = deployed + transaction_fees + priority_fees + checkpoint_costs
    inflow = returned_principal + sol_winnings
    available_after = state.available_sol_lamports - outflow
    if available_after < 0:
        return _unsettled_result(
            status=EconomicRoundStatus.REJECTED,
            scenario=scenario,
            participant_state=state,
            reasons=(
                _reason(
                    SettlementRejectionCode.AVAILABLE_BALANCE_EXCEEDED,
                    "settlement outflow exceeds participant available SOL",
                ),
            ),
            deployment=deployment,
            transaction_result=transaction_result,
            evaluation_result=evaluation_result,
            finalized_facts=facts,
        )

    post_state = ParticipantEconomicState(
        available_sol_lamports=available_after,
        accrued_sol_lamports=(
            state.accrued_sol_lamports + returned_principal + sol_winnings
        ),
        accrued_ore=state.accrued_ore + ore_earned,
        deployed_lamports=deployment.deployed_lamports,
        checkpoint_state=(
            CheckpointState.COMPLETED
            if deployed
            else state.checkpoint_state
        ),
        cumulative_protocol_costs_lamports=(
            state.cumulative_protocol_costs_lamports
            + principal_deduction
            + checkpoint_protocol
        ),
        cumulative_transaction_costs_lamports=(
            state.cumulative_transaction_costs_lamports
            + transaction_fees
            + priority_fees
            + checkpoint_transaction
        ),
        current_round=deployment.round_identifier,
        last_economically_settled_round=deployment.round_identifier,
    )
    return EconomicRoundResult(
        status=EconomicRoundStatus.SETTLED,
        round_identifier=deployment.round_identifier,
        scenario_identity=scenario.scenario_identity,
        protocol_revision=scenario.protocol_revision,
        participant_state_before_identity=state.state_identity,
        participant_state_after=post_state,
        protocol_deployment_plan_identity=(
            transaction_result.protocol_deployment_plan_identity
        ),
        transaction_plan_identity=transaction_result.transaction_plan_identity,
        evaluation_result_identity=_evaluation_result_identity(evaluation_result),
        finalized_outcome_identity=facts.finalized_outcome_identity,
        replay_round_identity=facts.replay_round_identity,
        decision_identity=facts.decision_identity,
        outcome_source=facts.outcome_source,
        completeness_status=facts.completeness_status,
        finalized_entropy=facts.entropy,
        winning_square_identifier=facts.winning_square_identifier,
        materialized_deployment_lamports=deployment.deployed_lamports,
        historical_deployed_lamports=facts.historical_deployed_lamports,
        counterfactual_deployed_lamports=adjusted,
        occupied_square_count=deployment.occupied_square_count,
        instruction_count=len(
            {value for value in deployment.deployed_lamports if value > 0}
        ),
        transaction_count=len(transaction_result.assumed_submission_slots),
        rejection_reasons=(),
        deployed_sol_lamports=deployed,
        returned_principal_lamports=returned_principal,
        sol_winnings_lamports=sol_winnings,
        protocol_deductions_lamports=principal_deduction,
        transaction_fees_lamports=transaction_fees,
        priority_fees_lamports=priority_fees,
        checkpoint_costs_lamports=checkpoint_costs,
        gross_sol_outflow_lamports=outflow,
        gross_sol_inflow_lamports=inflow,
        net_sol_change_lamports=inflow - outflow,
        base_ore_earned_raw=base_ore,
        motherlode_ore_earned_raw=motherlode_ore,
        ore_earned_raw=ore_earned,
        reward_treatment=treatment,
        participant_winning_square_lamports=participant_winner,
        historical_winning_square_lamports=(
            facts.historical_deployed_lamports[winner]
        ),
        counterfactual_winning_square_lamports=adjusted_winner,
        counterfactual_total_winnings_lamports=adjusted_winnings,
        counterfactual_total_vaulted_lamports=adjusted_vaulted,
        dilution_numerator_lamports=participant_winner,
        dilution_denominator_lamports=adjusted_winner,
        capture_efficiency_ore_raw_numerator=ore_earned,
        capture_efficiency_deployed_lamports_denominator=deployed,
    )


def _unsettled_result(
    *,
    status: EconomicRoundStatus,
    scenario: EconomicScenario,
    participant_state: ParticipantEconomicState,
    reasons: tuple[SettlementRejection, ...],
    deployment: ProtocolDeploymentPlan | None = None,
    transaction_result: TransactionInclusionResult | None = None,
    evaluation_result: EvaluationResult | None = None,
    finalized_facts: FinalizedReplayFacts | None = None,
) -> EconomicRoundResult:
    vector = deployment.deployed_lamports if deployment else (0,) * SQUARE_COUNT
    return EconomicRoundResult(
        status=status,
        round_identifier=(
            deployment.round_identifier
            if deployment
            else participant_state.current_round
        ),
        scenario_identity=scenario.scenario_identity,
        protocol_revision=scenario.protocol_revision,
        participant_state_before_identity=participant_state.state_identity,
        participant_state_after=participant_state,
        protocol_deployment_plan_identity=(
            protocol_deployment_plan_identity(deployment)
            if deployment
            else None
        ),
        transaction_plan_identity=(
            transaction_result.transaction_plan_identity
            if transaction_result
            else None
        ),
        evaluation_result_identity=(
            _evaluation_result_identity(evaluation_result)
            if evaluation_result
            else None
        ),
        finalized_outcome_identity=(
            finalized_facts.finalized_outcome_identity
            if finalized_facts
            else None
        ),
        replay_round_identity=(
            finalized_facts.replay_round_identity
            if finalized_facts
            else None
        ),
        decision_identity=(
            finalized_facts.decision_identity if finalized_facts else None
        ),
        outcome_source=(
            finalized_facts.outcome_source if finalized_facts else None
        ),
        completeness_status=(
            finalized_facts.completeness_status
            if finalized_facts
            else "not_evaluated"
        ),
        finalized_entropy=(
            finalized_facts.entropy if finalized_facts else None
        ),
        winning_square_identifier=(
            finalized_facts.winning_square_identifier
            if finalized_facts
            else None
        ),
        materialized_deployment_lamports=vector,
        historical_deployed_lamports=(
            finalized_facts.historical_deployed_lamports
            if finalized_facts
            else (0,) * SQUARE_COUNT
        ),
        counterfactual_deployed_lamports=(0,) * SQUARE_COUNT,
        occupied_square_count=(deployment.occupied_square_count if deployment else 0),
        instruction_count=(
            len({value for value in vector if value > 0}) if deployment else 0
        ),
        transaction_count=(
            len(transaction_result.assumed_submission_slots)
            if transaction_result
            else 0
        ),
        rejection_reasons=reasons,
        deployed_sol_lamports=0,
        returned_principal_lamports=0,
        sol_winnings_lamports=0,
        protocol_deductions_lamports=0,
        transaction_fees_lamports=0,
        priority_fees_lamports=0,
        checkpoint_costs_lamports=0,
        gross_sol_outflow_lamports=0,
        gross_sol_inflow_lamports=0,
        net_sol_change_lamports=0,
        base_ore_earned_raw=0,
        motherlode_ore_earned_raw=0,
        ore_earned_raw=0,
        reward_treatment=ORERewardTreatment.NONE,
        participant_winning_square_lamports=0,
        historical_winning_square_lamports=0,
        counterfactual_winning_square_lamports=0,
        counterfactual_total_winnings_lamports=0,
        counterfactual_total_vaulted_lamports=0,
        dilution_numerator_lamports=0,
        dilution_denominator_lamports=0,
        capture_efficiency_ore_raw_numerator=0,
        capture_efficiency_deployed_lamports_denominator=0,
    )


def _reconciliation_reasons(
    deployment: ProtocolDeploymentPlan,
    evaluation: EvaluationResult,
    facts: FinalizedReplayFacts,
    scenario: EconomicScenario,
    state: ParticipantEconomicState,
) -> list[SettlementRejection]:
    reasons: list[SettlementRejection] = []
    if (
        deployment.round_identifier != facts.round_identifier
        or evaluation.observation.round_identifier != facts.round_identifier
        or state.current_round != facts.round_identifier
    ):
        reasons.append(
            _reason(
                SettlementRejectionCode.ROUND_IDENTITY_MISMATCH,
                "deployment, evaluation, finalized facts, and state must share a round",
            )
        )
    if (
        evaluation.observation.winning_square_identifier
        != facts.winning_square_identifier
    ):
        reasons.append(
            _reason(
                SettlementRejectionCode.EVALUATION_WINNER_MISMATCH,
                "EvaluationResult winner does not match finalized replay facts",
            )
        )
    expected_hit = deployment.deployed_lamports[
        facts.winning_square_identifier
    ] > 0
    if evaluation.hit != expected_hit:
        reasons.append(
            _reason(
                SettlementRejectionCode.EVALUATION_HIT_MISMATCH,
                "EvaluationResult hit does not match materialized deployment",
            )
        )
    if facts.replay_identity != scenario.replay_identity:
        reasons.append(
            _reason(
                SettlementRejectionCode.REPLAY_IDENTITY_MISMATCH,
                "finalized replay identity does not match the scenario",
            )
        )
    if facts.dataset_identity != scenario.dataset_identity:
        reasons.append(
            _reason(
                SettlementRejectionCode.DATASET_IDENTITY_MISMATCH,
                "finalized dataset identity does not match the scenario",
            )
        )
    if facts.outcome_source not in scenario.outcome_policy.accepted_sources:
        reasons.append(
            _reason(
                SettlementRejectionCode.OUTCOME_SOURCE_REJECTED,
                "outcome provenance is not accepted by the scenario",
            )
        )
    if facts.completeness_status != "complete":
        reasons.append(
            _reason(
                SettlementRejectionCode.OUTCOME_INCOMPLETE,
                "finalized replay facts are not outcome-complete",
            )
        )
    if not facts.synthetic_participant_absent:
        reasons.append(
            _reason(
                SettlementRejectionCode.HISTORICAL_PARTICIPANT_DOUBLE_COUNT,
                "synthetic participant is already represented historically",
            )
        )
    winner = facts.winning_square_identifier
    if (
        facts.historical_deployed_lamports[winner] == 0
        and deployment.deployed_lamports[winner] > 0
    ):
        reasons.append(
            _reason(
                SettlementRejectionCode.COUNTERFACTUAL_REWARD_STATE_UNAVAILABLE,
                "synthetic deployment would change an empty-winner reward branch",
            )
        )
    return reasons


def _round_pool_values(
    deployed: tuple[int, ...],
    winning_square: int,
) -> tuple[int, int]:
    total_deployed = sum(deployed)
    winning_deployed = deployed[winning_square]
    if winning_deployed == 0:
        admin_fee = total_deployed // 100
        return 0, total_deployed - admin_fee
    nonwinning = total_deployed - winning_deployed
    winnings_admin_fee = nonwinning // 100
    after_admin = nonwinning - winnings_admin_fee
    vaulted = after_admin // 10
    return after_admin - vaulted, vaulted


def _evaluation_result_identity(result: EvaluationResult) -> str:
    return _identity(
        "rfc010-evaluation-result-sha256",
        {
            "allocations": [
                {
                    "allocation_amount": value.allocation_amount,
                    "allocation_weight": value.allocation_weight,
                    "metadata": _plain(value.metadata),
                    "square_identifier": value.square_identifier,
                }
                for value in result.deployment_decision
            ],
            "hit": result.hit,
            "round_identifier": result.observation.round_identifier,
            "winning_square_identifier": (
                result.observation.winning_square_identifier
            ),
        },
    )


def _reverse_u64(value: int) -> int:
    result = 0
    for _ in range(64):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def _square_vector(name: str, value: object) -> tuple[int, ...]:
    vector = tuple(value) if isinstance(value, (list, tuple)) else ()
    if len(vector) != SQUARE_COUNT:
        raise ValueError(f"{name} must contain exactly 25 values")
    if any(
        isinstance(item, bool)
        or not isinstance(item, int)
        or item < 0
        for item in vector
    ):
        raise ValueError(f"{name} must contain nonnegative integers")
    return vector


def _reason(
    code: SettlementRejectionCode,
    message: str,
) -> SettlementRejection:
    return SettlementRejection(code=code, message=message)


def _rejection_payload(value: SettlementRejection) -> dict[str, Any]:
    return {
        "code": value.code.value,
        "message": value.message,
        "source_code": value.source_code,
    }


def _plain(value: Any) -> Any:
    if isinstance(value, dict) or hasattr(value, "items"):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _identity(prefix: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _validate_string(name: str, value: object) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
    ):
        raise ValueError(f"{name} must be a nonempty canonical string")


def _validate_nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


__all__ = (
    "EconomicRoundResult",
    "EconomicRoundStatus",
    "FinalizedReplayFacts",
    "ORERewardTreatment",
    "ORESettlementModel",
    "SPLIT_REWARD_ADDRESS",
    "SUPPORTED_PROTOCOL_REVISION",
    "SettlementRejection",
    "SettlementRejectionCode",
)
